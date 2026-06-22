package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"net"
	"os"
	"os/signal"
	"syscall"

	"google.golang.org/grpc"
	"google.golang.org/grpc/reflection"

	pb "github.com/quant-atlas/gateway/proto"
	"github.com/quant-atlas/gateway/internal/broker"
	"github.com/quant-atlas/gateway/internal/market"
	"github.com/quant-atlas/gateway/internal/order"
	"github.com/quant-atlas/gateway/internal/server"
	"github.com/quant-atlas/gateway/internal/version"
	"github.com/quant-atlas/gateway/internal/ws"
)

func main() {
	grpcPort := flag.Int("port", 9090, "gRPC server port")
	wsPort := flag.Int("ws-port", 9091, "WebSocket gateway port")
	pythonURL := flag.String("python-url", "http://127.0.0.1:5000", "Python backend URL")
	flag.Parse()

	// ── Market Service ──
	marketSvc := market.NewService(*pythonURL)
	ctx := context.Background()
	if err := marketSvc.Start(ctx); err != nil {
		log.Fatalf("failed to start market service: %v", err)
	}

	// ── Order Service ──
	orderSvc := order.NewService(*pythonURL)

	// ── WebSocket Gateway ──
	wsServer := ws.NewServer(marketSvc, orderSvc)
	go func() {
		log.Printf("[gateway] WebSocket gateway on port %d", *wsPort)
		if err := wsServer.Listen(fmt.Sprintf(":%d", *wsPort)); err != nil {
			log.Fatalf("WebSocket gateway failed: %v", err)
		}
	}()

	// ── Wire market quotes to WS broadcast ──
	marketSvc.SetQuoteHandler(wsServer.HandleMarketQuote)

	// ── gRPC Trade Server ──
	lis, err := net.Listen("tcp", fmt.Sprintf(":%d", *grpcPort))
	if err != nil {
		log.Fatalf("failed to listen: %v", err)
	}

	reg := broker.NewRegistry()
	reg.Register("simulator", broker.NewSimulatorBroker())

	gs := grpc.NewServer(
		grpc.UnaryInterceptor(server.LoggingInterceptor),
	)

	srv := server.NewTradeServer(reg)
	pb.RegisterTradeExecutionServer(gs, srv)
	reflection.Register(gs)

	go func() {
		log.Printf("[gateway] gRPC listening on port %d (version %s)", *grpcPort, version.Version)
		if err := gs.Serve(lis); err != nil {
			log.Fatalf("gRPC server failed: %v", err)
		}
	}()

	// ── Wait for shutdown ──
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Println("[gateway] shutting down...")
	gs.GracefulStop()
	wsServer.Shutdown(ctx)
	marketSvc.Stop()
}

