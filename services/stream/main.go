package main

import (
	"context"
	"database/sql"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/almuzky/iot/services/stream/internal/client/mediamtx"
	"github.com/almuzky/iot/services/stream/internal/client/minio"
	mlclient "github.com/almuzky/iot/services/stream/internal/client/ml"
	"github.com/almuzky/iot/services/stream/internal/config"
	"github.com/almuzky/iot/services/stream/internal/handler"
	"github.com/almuzky/iot/services/stream/internal/middleware"
	"github.com/almuzky/iot/services/stream/internal/repository"
	"github.com/almuzky/iot/services/stream/internal/service"
	"github.com/go-chi/chi/v5"
	chimw "github.com/go-chi/chi/v5/middleware"
	_ "github.com/go-sql-driver/mysql"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("config error: %v", err)
	}

	// ─── MariaDB (stream metadata) ──────────────────────────────────────
	db, err := openDB(cfg.DBDSN)
	if err != nil {
		log.Fatalf("db error: %v", err)
	}
	defer db.Close()
	log.Println("mariadb connected")

	if err := runMigrations(cfg.DBDSN); err != nil {
		log.Fatalf("migration error: %v", err)
	}

	// ─── Wire dependencies ──────────────────────────────────────────────
	repo := repository.New(db)
	media := mediamtx.New(cfg.MediaMTXAPIURL).WithHTTPURL(cfg.MediaMTXHTTPURL).WithRTSPURL(cfg.MediaMTXRTSPURL)
	minioClient, err := minio.New(cfg.MinIOEndpoint, cfg.MinIOAccessKey, cfg.MinIOSecretKey, cfg.MinIOUseSSL, cfg.MinIOStreamBucket)
	if err != nil {
		log.Printf("[startup] minio unavailable (snapshots disabled): %v", err)
	}
	mlClient := mlclient.New(cfg.MLBaseURL, cfg.MLVisionModelID, cfg.JWTSecret)
	svc := service.New(repo, media, minioClient, mlClient, cfg.KongPublicURL, cfg.CCTVRTSPURL)
	h := handler.New(svc)

	// ─── MediaMTX path reconciliation ─────────────────────────────────
	// API-registered MediaMTX paths are ephemeral and disappear when
	// MediaMTX restarts, while the DB streams persist — that drift is what
	// surfaces as `path 'X' is not configured`. Re-register all enabled
	// streams on startup and keep it in sync on a timer so a MediaMTX
	// restart self-heals.
	go func() {
		ctx := context.Background()
		// Best-effort initial reconcile; if MediaMTX is not up yet the timer
		// below retries until it succeeds.
		svc.ReconcilePaths(ctx)
		if cfg.ReconcileInterval <= 0 {
			return
		}
		ticker := time.NewTicker(cfg.ReconcileInterval)
		defer ticker.Stop()
		for range ticker.C {
			svc.ReconcilePaths(context.Background())
		}
	}()

	// ─── Router ──────────────────────────────────────────────────────────
	r := chi.NewRouter()
	r.Use(chimw.Logger)
	r.Use(chimw.Recoverer)
	r.Use(chimw.RequestID)
	r.Use(chimw.RealIP)
	r.Use(middleware.PrometheusMiddleware)

	r.Handle("/metrics", promhttp.Handler())
	r.Get("/health", handler.Health)

	secret := cfg.JWTSecret
	r.Route("/streams", func(r chi.Router) {
		r.Use(middleware.JWTAuth(secret))

		// Read routes — any authenticated user.
		r.Get("/", h.ListStreams)
		r.Get("/{id}", h.GetStream)

		// Write routes — operator/admin only.
		r.Group(func(r chi.Router) {
			r.Use(middleware.RequireRole(secret, "admin", "operator"))

			r.Post("/", h.CreateStream)
			r.Put("/{id}", h.UpdateStream)
			r.Delete("/{id}", h.DeleteStream)

			// Snapshot capture & recording control.
			r.Post("/{id}/snapshot", h.CaptureSnapshot)
			r.Post("/{id}/record/start", h.StartRecording)
			r.Post("/{id}/record/stop", h.StopRecording)
		})
	})

	// Snapshots & recordings — served from MinIO (private bucket, proxied
	// through this service using its scoped credentials; JWT required).
	r.Route("/snapshots", func(r chi.Router) {
		r.Use(middleware.JWTAuth(secret))

		// Read — any authenticated user.
		r.Get("/", h.ListSnapshots)
		r.Get("/{id}", h.GetSnapshot)

		// Delete — operator/admin only.
		r.Group(func(r chi.Router) {
			r.Use(middleware.RequireRole(secret, "admin", "operator"))
			r.Delete("/{id}", h.DeleteSnapshot)
		})
	})

	// Object storage proxy — serves MinIO objects (snapshots/recordings/
	// detection images) through this service using scoped credentials.
	// The bucket is private (no public-read policy); every read is
	// authenticated here and the object key is validated (no traversal).
	r.Group(func(r chi.Router) {
		r.Use(middleware.JWTAuth(secret))
		r.Get("/storage/*", h.GetObject)
	})

	// ─── HTTP Server ────────────────────────────────────────────────────
	srv := &http.Server{
		Addr:        ":" + cfg.Port,
		Handler:     r,
		ReadTimeout: 15 * time.Second,
		// Snapshot capture pulls a frame from MediaMTX's HTTP snapshot endpoint
		// (may retry on a cold on-demand source) and, with ?detect=true, also runs
		// ML inference. Keep this comfortably above the retry budget plus model
		// load + inference so the response is never aborted mid-write (which would
		// surface as a Kong 504).
		WriteTimeout: 120 * time.Second,
		IdleTimeout:  150 * time.Second,
	}

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		log.Printf("stream-svc listening on :%s", cfg.Port)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("server error: %v", err)
		}
	}()

	<-quit
	log.Println("shutting down stream-svc...")
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := srv.Shutdown(ctx); err != nil {
		log.Printf("shutdown error: %v", err)
	}
	log.Println("stream-svc stopped")
}

// ensureMySQLTimeouts appends connection timeouts to a MySQL DSN when missing.
// Without readTimeout/writeTimeout, a query against a dead connection hangs
// until the OS TCP timeout, exhausting the pool and making the service
// unreachable during/after a DB outage (chaos test failure).
func ensureMySQLTimeouts(dsn string) string {
	if strings.Contains(dsn, "readTimeout=") &&
		strings.Contains(dsn, "writeTimeout=") &&
		strings.Contains(dsn, "timeout=") {
		return dsn
	}
	sep := "?"
	if strings.Contains(dsn, "?") {
		sep = "&"
	}
	return dsn + sep + "timeout=10s&readTimeout=10s&writeTimeout=10s&maxAllowedPacket=4194304"
}

func openDB(dsn string) (*sql.DB, error) {
	db, err := sql.Open("mysql", ensureMySQLTimeouts(dsn))
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(25)
	db.SetMaxIdleConns(10)
	db.SetConnMaxLifetime(5 * time.Minute)
	db.SetConnMaxIdleTime(1 * time.Minute)

	for i := range 10 {
		if err = db.Ping(); err == nil {
			return db, nil
		}
		log.Printf("db ping attempt %d/10 failed: %v", i+1, err)
		time.Sleep(3 * time.Second)
	}
	return nil, fmt.Errorf("database unreachable after 10 attempts: %w", err)
}
