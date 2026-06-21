package main

import (
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
	"github.com/quant-atlas/gateway/internal/server"
	"github.com/quant-atlas/gateway/internal/version"
)

func main() {
	port := flag.Int("port", 9090, "gRPC server port")
	flag.Parse()

	lis, err := net.Listen("tcp", fmt.Sprintf(":%d", *port))
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
		log.Printf("[gateway] listening on port %d (version %s)", *port, version.Version)
		if err := gs.Serve(lis); err != nil {
			log.Fatalf("failed to serve: %v", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Println("[gateway] shutting down...")
	gs.GracefulStop()
}
