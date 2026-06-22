package main

import (
    "context"
    "fmt"
    "log"
    "net/http"
    "os"
    "os/signal"
    "syscall"
    "time"

    "quant-atlas-gateway/internal/market"
    "quant-atlas-gateway/internal/order"
    "quant-atlas-gateway/internal/ws"
)

var (
    Version   = "0.1.0"
    BuildTime = "unknown"
)

func main() {
    fmt.Printf("Quant Atlas Go Gateway v%s (built %s)\n", Version, BuildTime)

    // Configuration from environment
    port := envOrDefault("GATEWAY_PORT", "8080")
    pythonURL := envOrDefault("PYTHON_BACKEND_URL", "http://localhost:5000")
    wsPort := envOrDefault("GATEWAY_WS_PORT", "8081")

    // Initialize subsystems
    ctx, cancel := context.WithCancel(context.Background())
    defer cancel()

    // Market data pipeline (Phase 2: async WebSocket replaces pytdx polling)
    marketSvc := market.NewService(pythonURL)
    if err := marketSvc.Start(ctx); err != nil {
        log.Fatalf("failed to start market service: %v", err)
    }
    defer marketSvc.Stop()

    // Order execution gateway (Phase 2: dedicated order routing)
    orderSvc := order.NewService(pythonURL)
    if err := orderSvc.Start(ctx); err != nil {
        log.Fatalf("failed to start order service: %v", err)
    }
    defer orderSvc.Stop()

    // WebSocket cluster coordinator (Phase 2: dedicated WS gateway)
    wsSrv := ws.NewServer(marketSvc, orderSvc)

    // HTTP API gateway (reverse proxy to Python backend)
    mux := http.NewServeMux()
    mux.HandleFunc("/health", healthHandler(marketSvc, orderSvc))
    mux.HandleFunc("/ws", wsSrv.HandleUpgrade)

    httpSrv := &http.Server{
        Addr:         ":" + port,
        Handler:      mux,
        ReadTimeout:  15 * time.Second,
        WriteTimeout: 30 * time.Second,
        IdleTimeout:  60 * time.Second,
    }

    // Start HTTP server
    go func() {
        log.Printf("HTTP gateway listening on :%s", port)
        if err := httpSrv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
            log.Fatalf("HTTP server error: %v", err)
        }
    }()

    // Start WebSocket server
    go func() {
        log.Printf("WebSocket gateway listening on :%s", wsPort)
        if err := wsSrv.Listen(":" + wsPort); err != nil {
            log.Printf("WebSocket server error: %v", err)
        }
    }()

    // Graceful shutdown
    quit := make(chan os.Signal, 1)
    signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
    <-quit

    log.Println("Shutting down gateway...")
    shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 10*time.Second)
    defer shutdownCancel()

    httpSrv.Shutdown(shutdownCtx)
    wsSrv.Shutdown(shutdownCtx)
    cancel()
}

func healthHandler(marketSvc *market.Service, orderSvc *order.Service) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("Content-Type", "application/json")
        status := "healthy"
        if !marketSvc.IsReady() || !orderSvc.IsReady() {
            status = "degraded"
        }
        fmt.Fprintf(w, "{\"status\":\"%s\",\"version\":\"%s\"}", status, Version)
    }
}

func envOrDefault(key, fallback string) string {
    if v := os.Getenv(key); v != "" {
        return v
    }
    return fallback
}
