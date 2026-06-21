package server

import (
	"context"
	"fmt"
	"log"
	"sync/atomic"
	"time"

	pb "github.com/quant-atlas/gateway/proto"
	"github.com/quant-atlas/gateway/internal/broker"
	"github.com/quant-atlas/gateway/internal/version"
)

var startTime = time.Now()

// TradeServer implements the TradeExecution gRPC service.
type TradeServer struct {
	pb.UnimplementedTradeExecutionServer
	registry       *broker.Registry
	ordersTotal    atomic.Uint64
	ordersFailed   atomic.Uint64
}

func NewTradeServer(reg *broker.Registry) *TradeServer {
	return &TradeServer{registry: reg}
}

func (s *TradeServer) SubmitOrder(ctx context.Context, req *pb.OrderRequest) (*pb.OrderResponse, error) {
	s.ordersTotal.Add(1)

	// ── 1. Pre-trade risk checks ──
	var failures []*pb.RiskCheck

	if req.Price <= 0 {
		failures = append(failures, &pb.RiskCheck{
			Check: "price_check", Detail: fmt.Sprintf("price %.4f must be > 0", req.Price), Passed: false,
		})
	}
	if req.Quantity <= 0 {
		failures = append(failures, &pb.RiskCheck{
			Check: "quantity_check", Detail: fmt.Sprintf("quantity %d must be > 0", req.Quantity), Passed: false,
		})
	}
	tradeAmount := req.Price * float64(req.Quantity)
	if req.MaxTradeAmount > 0 && tradeAmount > req.MaxTradeAmount {
		failures = append(failures, &pb.RiskCheck{
			Check: "max_amount", Detail: fmt.Sprintf("trade amount %.2f exceeds limit %.2f", tradeAmount, req.MaxTradeAmount), Passed: false,
		})
	}

	if len(failures) > 0 {
		s.ordersFailed.Add(1)
		return &pb.OrderResponse{
			OrderId:  req.OrderId,
			Accepted: false,
			Reason:   "risk checks failed",
			State:    "rejected",
			Failures: failures,
		}, nil
	}

	// ── 2. Dry-run short-circuit ──
	if req.DryRun {
		return &pb.OrderResponse{
			OrderId:  req.OrderId,
			Accepted: true,
			Reason:   "dry-run passed",
			State:    "accepted",
		}, nil
	}

	// ── 3. Route to broker ──
	env := &broker.OrderEnvelope{
		OrderID:    req.OrderId,
		Symbol:     req.Symbol,
		Side:       req.Side,
		Price:      req.Price,
		Quantity:   req.Quantity,
		StrategyID: req.StrategyId,
		UserID:     req.UserId,
		Metadata:   req.Metadata,
	}

	brk, err := s.registry.Get("simulator")
	if err != nil {
		s.ordersFailed.Add(1)
		return &pb.OrderResponse{
			OrderId:  req.OrderId,
			Accepted: false,
			Reason:   err.Error(),
			State:    "rejected",
		}, nil
	}

	result, err := brk.Submit(env)
	if err != nil {
		s.ordersFailed.Add(1)
		return &pb.OrderResponse{
			OrderId:  req.OrderId,
			Accepted: false,
			Reason:   err.Error(),
			State:    "failed",
		}, nil
	}

	return &pb.OrderResponse{
		OrderId:        req.OrderId,
		Accepted:       result.Accepted,
		Reason:         result.Reason,
		State:          result.State,
		GatewayVersion: version.Version,
	}, nil
}

func (s *TradeServer) RegisterBroker(ctx context.Context, req *pb.RegisterBrokerRequest) (*pb.RegisterBrokerResponse, error) {
	return &pb.RegisterBrokerResponse{
		Ok:    false,
		Error: "dynamic registration not supported yet",
	}, nil
}

func (s *TradeServer) CheckHealth(ctx context.Context, req *pb.HealthRequest) (*pb.HealthResponse, error) {
	uptime := uint32(time.Since(startTime).Seconds())
	return &pb.HealthResponse{
		Healthy:          true,
		Version:          version.Version,
		UptimeSeconds:    uptime,
		OrdersProcessed:  s.ordersTotal.Load(),
		OrdersFailed:     s.ordersFailed.Load(),
		RegisteredBrokers: s.registry.List(),
	}, nil
}

// LoggingInterceptor logs every gRPC call.
func LoggingInterceptor(ctx context.Context, req interface{}, info *grpc.UnaryServerInfo, handler grpc.UnaryHandler) (interface{}, error) {
	start := time.Now()
	resp, err := handler(ctx, req)
	log.Printf("[gateway] %s duration=%s err=%v", info.FullMethod, time.Since(start), err)
	return resp, err
}