package main

import (
	"context"
	"database/sql"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/almuzky/iot/services/notification/internal/config"
	"github.com/almuzky/iot/services/notification/internal/handler"
	"github.com/almuzky/iot/services/notification/internal/middleware"
	"github.com/almuzky/iot/services/notification/internal/repository"
	"github.com/almuzky/iot/services/notification/internal/service"
	"github.com/go-chi/chi/v5"
	chimw "github.com/go-chi/chi/v5/middleware"
	_ "github.com/go-sql-driver/mysql"
	"github.com/nats-io/nats.go"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/redis/go-redis/v9"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("config error: %v", err)
	}

	// ─── MariaDB (settings + delivery log history) ──────────────────────
	db, err := openDB(cfg.DBDSN)
	if err != nil {
		log.Fatalf("db error: %v", err)
	}
	defer db.Close()
	log.Println("mariadb connected")

	if err := runMigrations(cfg.DBDSN); err != nil {
		log.Fatalf("migration error: %v", err)
	}

	gdb, err := gorm.Open(mysql.Open(cfg.DBDSN), &gorm.Config{
		Logger: logger.Default.LogMode(logger.Warn),
	})
	if err != nil {
		log.Fatalf("gorm error: %v", err)
	}
	store := repository.New(gdb)

	// ─── Redis (delivery queue) ─────────────────────────────────────────
	rdb := redis.NewClient(&redis.Options{
		Addr:     cfg.RedisAddr,
		Password: cfg.RedisPassword,
		DB:       cfg.RedisDB,
	})
	rctx, rcancel := context.WithTimeout(context.Background(), 5*time.Second)
	if err := rdb.Ping(rctx).Err(); err != nil {
		log.Printf("WARN: redis ping failed: %v — notification queue degraded", err)
	} else {
		log.Println("redis connected")
	}
	rcancel()
	defer func() { _ = rdb.Close() }()

	// ─── Service + settings cache ───────────────────────────────────────
	svc := service.New(cfg, store, rdb, nil)
	if err := svc.ReloadSettings(context.Background()); err != nil {
		log.Printf("WARN: load settings failed: %v", err)
	}
	if cfg.TelegramBotToken != "" || cfg.SMTPHost != "" {
		_ = svc.SeedFromEnv(context.Background(), cfg)
	}

	// ─── NATS (subscribe alert.*) ──────────────────────────────────────
	natsConn, err := nats.Connect(cfg.NATSUrl,
		nats.Name("notification-svc"),
		nats.MaxReconnects(-1),
		nats.ReconnectWait(3*time.Second),
		nats.DisconnectErrHandler(func(c *nats.Conn, e error) {
			log.Printf("WARN: NATS disconnected: %v", e)
		}),
		nats.ReconnectHandler(func(c *nats.Conn) {
			log.Printf("NATS reconnected -> %s", c.ConnectedUrl())
		}),
	)
	if err != nil {
		log.Printf("WARN: NATS connect failed: %v — alert-driven notifications disabled until reconnect", err)
	} else {
		defer natsConn.Drain()
		svc.SetNATS(natsConn)
		log.Println("NATS connected")
		if err := svc.RunSubscriber(natsConn); err != nil {
			log.Printf("WARN: notification subscriber not started: %v", err)
		}
	}

	// ─── Delivery worker (retry + throttle) ────────────────────────────
	rootCtx, cancel := context.WithCancel(context.Background())
	defer cancel()
	svc.StartWorker(rootCtx)

	h := handler.New(svc)

	// ─── Router ─────────────────────────────────────────────────────────
	r := chi.NewRouter()
	r.Use(chimw.Logger)
	r.Use(chimw.Recoverer)
	r.Use(chimw.RequestID)
	r.Use(chimw.RealIP)
	r.Use(middleware.PrometheusMiddleware)

	r.Handle("/metrics", promhttp.Handler())
	r.Get("/health", handler.Health)

	secret := cfg.JWTSecret
	authMw := middleware.JWTAuth(secret)
	adminMw := middleware.RequireRole(secret, "admin")

	r.With(authMw).Get("/notifications/settings", h.GetSettings)
	r.With(authMw, adminMw).Put("/notifications/settings", h.PutSettings)
	r.With(authMw).Get("/notifications/logs", h.GetLogs)
	r.With(authMw, adminMw).Post("/notifications/test", h.TestSend)

	r.With(authMw, adminMw).Post("/notifications/receive/telegram", h.ReceiveTelegram)
	r.With(authMw, adminMw).Post("/notifications/receive/email", h.ReceiveEmail)
	r.With(authMw, adminMw).Post("/notifications/receive/generic", h.ReceiveGeneric)
	r.With(authMw, adminMw).Post("/notifications/receive/delivery", h.ReceiveDelivery)

	srv := &http.Server{
		Addr:         ":" + cfg.Port,
		Handler:      r,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 10 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		log.Printf("notification-svc listening on :%s", cfg.Port)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("server error: %v", err)
		}
	}()

	<-quit
	log.Println("shutting down notification-svc...")
	cancel()
	if natsConn != nil {
		_ = natsConn.Drain()
	}
	ctx, c := context.WithTimeout(context.Background(), 10*time.Second)
	defer c()
	if err := srv.Shutdown(ctx); err != nil {
		log.Printf("shutdown error: %v", err)
	}
	log.Println("notification-svc stopped")
}

func openDB(dsn string) (*sql.DB, error) {
	db, err := sql.Open("mysql", dsn)
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(25)
	db.SetMaxIdleConns(10)
	db.SetConnMaxLifetime(5 * time.Minute)

	for i := range 10 {
		if err = db.Ping(); err == nil {
			return db, nil
		}
		log.Printf("db ping attempt %d/10 failed: %v", i+1, err)
		time.Sleep(3 * time.Second)
	}
	return nil, fmt.Errorf("database unreachable after 10 attempts: %w", err)
}
