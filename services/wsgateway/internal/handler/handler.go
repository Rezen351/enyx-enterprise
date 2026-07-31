package handler

import (
	"encoding/json"
	"log"
	"net/http"
	"regexp"
	"strings"
	"sync"
	"time"

	"github.com/almuzky/iot/services/wsgateway/internal/auth"
	"github.com/go-chi/chi/v5"
	"github.com/gorilla/websocket"
	"github.com/nats-io/nats.go"
)

// nodeIDRe restricts the WS path parameter to the same character set accepted
// by the Module/Alert services so a malformed id cannot be forwarded to NATS.
var nodeIDRe = regexp.MustCompile(`^[A-Za-z0-9_.:*-]{1,64}$`)

// writeJSONError writes a standard error envelope (AGENTS.md §4.4).
func writeJSONError(w http.ResponseWriter, status int, code, message string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(map[string]any{
		"success": false,
		"error":   map[string]string{"code": code, "message": message},
	})
}

// Handler bridges NATS topics to dashboard websocket clients.
type Handler struct {
	nc        *nats.Conn
	jwtSecret string

	// lastMu/last caches the most recent live payload per node so a freshly
	// connected dashboard client receives an immediate frame instead of waiting
	// for the next telemetry tick (which can be infrequent and make the Live
	// MQTT Monitor appear stuck on "Listening for live MQTT payload...").
	lastMu    sync.RWMutex
	last      map[string][]byte
	latestSub *nats.Subscription
}

func New(nc *nats.Conn, jwtSecret string) *Handler {
	return &Handler{nc: nc, jwtSecret: jwtSecret, last: make(map[string][]byte)}
}

// Health is a liveness probe.
func Health(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_ = json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}

var upgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 4096,
	CheckOrigin:     func(r *http.Request) bool { return true },
}

// client wraps a single websocket connection with a buffered send channel.
type client struct {
	conn *websocket.Conn
	send chan []byte
}

// authenticate validates the WS handshake token (Bearer header or ?token=
// query param). On failure it writes an HTTP 401 and returns false.
func (h *Handler) authenticate(w http.ResponseWriter, r *http.Request) bool {
	token := auth.ExtractToken(r.Header.Get("Authorization"), r.URL.Query().Get("token"))
	if token == "" {
		writeJSONError(w, http.StatusUnauthorized, "UNAUTHORIZED", "missing or invalid Authorization header")
		return false
	}
	if _, err := auth.ValidateToken(token, h.jwtSecret); err != nil {
		log.Printf("[ws-gateway] auth failed: %v", err)
		writeJSONError(w, http.StatusUnauthorized, "UNAUTHORIZED", "invalid or expired token")
		return false
	}
	return true
}

// StartLatestCache subscribes to every node's live subject (mqtt.>) and keeps
// the most recent payload in memory for replay on client connect. This avoids
// the "Loading terus" UX when a device reports infrequently.
func (h *Handler) StartLatestCache() error {
	sub, err := h.nc.Subscribe("mqtt.>", func(m *nats.Msg) {
		nodeID := strings.TrimPrefix(m.Subject, "mqtt.")
		h.lastMu.Lock()
		h.last[nodeID] = m.Data
		h.lastMu.Unlock()
	})
	if err != nil {
		return err
	}
	h.latestSub = sub
	return nil
}

// getLast returns the cached most-recent payload for a node (nil if none yet).
func (h *Handler) getLast(nodeID string) []byte {
	h.lastMu.RLock()
	defer h.lastMu.RUnlock()
	return h.last[nodeID]
}

// NodeLive upgrades to a websocket and streams every NATS message published on
// the node's live subject (mqtt.{node_id}) to the connecting dashboard client.
// Requires a valid JWT (Bearer header or ?token= query param).
func (h *Handler) NodeLive(w http.ResponseWriter, r *http.Request) {
	nodeID := chi.URLParam(r, "node_id")
	if nodeID == "" {
		writeJSONError(w, http.StatusBadRequest, "BAD_REQUEST", "node_id is required")
		return
	}
	if !nodeIDRe.MatchString(nodeID) {
		writeJSONError(w, http.StatusBadRequest, "BAD_REQUEST", "node_id contains invalid characters")
		return
	}

	if !h.authenticate(w, r) {
		return
	}

	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("[ws-gateway] upgrade failed node=%s: %v", nodeID, err)
		return
	}

	c := &client{conn: conn, send: make(chan []byte, 128)}
	subject := "mqtt." + nodeID

	// Replay the last known payload (if any) so the dashboard isn't stuck on
	// "Listening for live MQTT payload..." when a device reports infrequently.
	// Written directly before the pumps start to guarantee ordering.
	if data := h.getLast(nodeID); data != nil {
		_ = conn.WriteMessage(websocket.TextMessage, data)
	}

	conn.SetPingHandler(func(appData string) error {
		return conn.WriteMessage(websocket.PongMessage, []byte(appData))
	})
	conn.SetPongHandler(func(appData string) error {
		return nil
	})

	sub, err := h.nc.Subscribe(subject, func(m *nats.Msg) {
		select {
		case c.send <- m.Data:
		default:
			// Slow client — drop frame to avoid blocking the NATS reader.
			log.Printf("[ws-gateway] dropping frame node=%s (slow client)", nodeID)
		}
	})
	if err != nil {
		log.Printf("[ws-gateway] nats subscribe failed node=%s: %v", nodeID, err)
		_ = conn.Close()
		return
	}
	log.Printf("[ws-gateway] client connected node=%s (subject=%s)", nodeID, subject)

	go c.writePump()
	go c.pingPump()

	// Reader goroutine: detects close and tears down the NATS subscription.
	go func() {
		defer func() {
			_ = sub.Unsubscribe()
			_ = conn.Close()
			log.Printf("[ws-gateway] client disconnected node=%s", nodeID)
		}()
		for {
			if _, _, err := conn.ReadMessage(); err != nil {
				return
			}
		}
	}()
}

// SystemStatus upgrades to a websocket and streams system-level notifications to
// authenticated dashboard clients. It bridges the relevant NATS subjects
// (system.status, alert.triggered, alert.resolved) onto the websocket so the
// dashboard NotificationContext receives alerts and system notices as soon as a
// publisher (Alert/Monitor Service) emits them. The connection is held open
// until a notification arrives.
func (h *Handler) SystemStatus(w http.ResponseWriter, r *http.Request) {
	if !h.authenticate(w, r) {
		return
	}

	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("[ws-gateway] upgrade failed system-status: %v", err)
		return
	}

	c := &client{conn: conn, send: make(chan []byte, 128)}

	conn.SetPingHandler(func(appData string) error {
		return conn.WriteMessage(websocket.PongMessage, []byte(appData))
	})
	conn.SetPongHandler(func(appData string) error {
		return nil
	})

	// Bridge every notification subject onto the client's send channel.
	subjects := []string{"system.status", "alert.triggered", "alert.resolved"}
	subs := make([]*nats.Subscription, 0, len(subjects))
	for _, subject := range subjects {
		sub, serr := h.nc.Subscribe(subject, func(m *nats.Msg) {
			select {
			case c.send <- m.Data:
			default:
				// Slow client — drop frame to avoid blocking the NATS reader.
				log.Printf("[ws-gateway] dropping %s frame (slow client)", m.Subject)
			}
		})
		if serr != nil {
			log.Printf("[ws-gateway] nats subscribe failed %s: %v", subject, serr)
			for _, s := range subs {
				_ = s.Unsubscribe()
			}
			_ = conn.Close()
			return
		}
		subs = append(subs, sub)
	}
	log.Printf("[ws-gateway] client connected system-status (subjects: %v)", subjects)

	go c.writePump()
	go c.pingPump()

	// Reader goroutine: detects close and tears down the NATS subscriptions.
	go func() {
		defer func() {
			for _, s := range subs {
				_ = s.Unsubscribe()
			}
			_ = conn.Close()
			log.Printf("[ws-gateway] client disconnected system-status")
		}()
		for {
			if _, _, err := conn.ReadMessage(); err != nil {
				return
			}
		}
	}()
}

// writePump drains the send channel onto the websocket connection.
func (c *client) writePump() {
	for data := range c.send {
		if err := c.conn.WriteMessage(websocket.TextMessage, data); err != nil {
			return
		}
	}
}

// pingPump sends a websocket ping every 25s to keep the connection alive
// through load balancers, proxies, and browser background throttling.
func (c *client) pingPump() {
	ticker := time.NewTicker(25 * time.Second)
	defer ticker.Stop()
	for range ticker.C {
		if err := c.conn.WriteMessage(websocket.PingMessage, nil); err != nil {
			return
		}
	}
}
