package mqtt

import (
	"encoding/json"
	"fmt"
	"log"
	"strings"
	"time"

	paho "github.com/eclipse/paho.mqtt.golang"
)

// Config for the MQTT client.
type Config struct {
	BrokerURL   string
	Username    string
	Password    string
	ClientID    string
	TopicPrefix string
}

// ConfirmHandler is invoked when a firmware /confirm message arrives.
type ConfirmHandler func(nodeID, reqID, target string, value int)

// TelemetryHandler is invoked with the raw telemetry payload of a node.
type TelemetryHandler func(nodeID string, payload []byte)

// Client wraps the paho MQTT client for the Control Service: it publishes
// actuator commands to smartfarm/actuator/{node_id} and subscribes to the
// firmware /confirm (ACK) and /telemetry (target discovery + sensor cache).
type Client struct {
	client      paho.Client
	topicPrefix string
	onConfirm   ConfirmHandler
	onTelemetry TelemetryHandler
}

// confirmPayload mirrors the firmware confirm message (MqttManager.cpp).
type confirmPayload struct {
	ReqID  string `json:"req_id"`
	Target string `json:"target"`
	Value  int    `json:"value"`
	Status string `json:"status"`
}

// New connects to the broker and returns a Client (not yet subscribed).
func New(cfg Config, onConfirm ConfirmHandler, onTelemetry TelemetryHandler) (*Client, error) {
	c := &Client{topicPrefix: cfg.TopicPrefix, onConfirm: onConfirm, onTelemetry: onTelemetry}

	clientID := cfg.ClientID
	if clientID == "" {
		clientID = "control-svc"
	}
	clientID = fmt.Sprintf("%s-%d", clientID, time.Now().UnixNano()%1000000)

	opts := paho.NewClientOptions().
		AddBroker(cfg.BrokerURL).
		SetClientID(clientID).
		SetAutoReconnect(true).
		SetConnectRetry(true).
		SetConnectRetryInterval(5 * time.Second).
		SetKeepAlive(30 * time.Second).
		SetCleanSession(false)

	if cfg.Username != "" {
		opts.SetUsername(cfg.Username)
		opts.SetPassword(cfg.Password)
	}

	opts.SetOnConnectHandler(func(pc paho.Client) {
		log.Println("[mqtt] connected to broker")
		c.subscribe()
	})
	opts.SetConnectionLostHandler(func(pc paho.Client, err error) {
		log.Printf("[mqtt] connection lost: %v", err)
	})

	c.client = paho.NewClient(opts)
	log.Printf("[mqtt] connecting to broker %s (prefix=%q)...", cfg.BrokerURL, cfg.TopicPrefix)
	c.client.Connect()

	go func() {
		for i := 0; i < 12; i++ {
			time.Sleep(10 * time.Second)
			if c.client.IsConnected() {
				return
			}
			log.Printf("[mqtt] still not connected to %s — retrying", cfg.BrokerURL)
		}
	}()
	return c, nil
}

func (c *Client) subscribe() {
	confirmTopic := c.topicPrefix + "/+/confirm"
	if tok := c.client.Subscribe(confirmTopic, 1, c.onConfirmMessage); tok.Wait() && tok.Error() != nil {
		log.Printf("[mqtt] subscribe %s failed: %v", confirmTopic, tok.Error())
	} else {
		log.Printf("[mqtt] subscribed: %s", confirmTopic)
	}

	telemetryTopic := c.topicPrefix + "/+/telemetry"
	if tok := c.client.Subscribe(telemetryTopic, 0, c.onTelemetryMessage); tok.Wait() && tok.Error() != nil {
		log.Printf("[mqtt] subscribe %s failed: %v", telemetryTopic, tok.Error())
	} else {
		log.Printf("[mqtt] subscribed: %s", telemetryTopic)
	}
}

// IsConnected reports broker connectivity.
func (c *Client) IsConnected() bool {
	return c.client != nil && c.client.IsConnected()
}

// PublishSetOutput sends a set_output command to smartfarm/actuator/{node_id}.
// The req_id lets us correlate the firmware /confirm ACK back to the command.
func (c *Client) PublishSetOutput(nodeID, target string, value int, reqID string) error {
	if !c.IsConnected() {
		return fmt.Errorf("mqtt not connected")
	}
	topic := c.topicPrefix + "/actuator/" + nodeID
	payload := fmt.Sprintf(`{"action":"set_output","target":%q,"value":%d,"req_id":%q}`,
		target, value, reqID)
	tok := c.client.Publish(topic, 1, false, payload)
	tok.Wait()
	return tok.Error()
}

// Disconnect gracefully closes the connection.
func (c *Client) Disconnect() {
	if c.client != nil {
		c.client.Disconnect(250)
	}
}

func (c *Client) onConfirmMessage(_ paho.Client, m paho.Message) {
	nodeID := c.nodeIDFromTopic(m.Topic())
	if nodeID == "" || c.onConfirm == nil {
		return
	}
	var p confirmPayload
	if err := json.Unmarshal(m.Payload(), &p); err != nil {
		log.Printf("[mqtt] bad confirm payload node=%s: %v", nodeID, err)
		return
	}
	c.onConfirm(nodeID, p.ReqID, p.Target, p.Value)
}

func (c *Client) onTelemetryMessage(_ paho.Client, m paho.Message) {
	nodeID := c.nodeIDFromTopic(m.Topic())
	if nodeID == "" || c.onTelemetry == nil {
		return
	}
	c.onTelemetry(nodeID, m.Payload())
}

// nodeIDFromTopic extracts {node_id} from {prefix}/{node_id}/{suffix}.
func (c *Client) nodeIDFromTopic(topic string) string {
	rel := strings.TrimPrefix(topic, c.topicPrefix+"/")
	if rel == topic {
		return ""
	}
	parts := strings.Split(rel, "/")
	if len(parts) >= 2 && parts[0] != "" {
		return parts[0]
	}
	return ""
}
