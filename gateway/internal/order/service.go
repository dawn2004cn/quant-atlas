package order

import (
    "context"
    "log"
    "sync"
)

// Service manages order execution routing.
// Phase 2: single-broker proxy to Python backend.
// Phase 4: multi-broker smart order routing (SOR).
type Service struct {
    pythonURL string
    ready     bool
    mu        sync.RWMutex
}

// NewService creates an order execution service.
func NewService(pythonURL string) *Service {
    return &Service{
        pythonURL: pythonURL,
    }
}

// Start initializes the order service.
func (s *Service) Start(ctx context.Context) error {
    log.Println("[order] Starting execution gateway")
    s.mu.Lock()
    s.ready = true
    s.mu.Unlock()
    return nil
}

// Stop shuts down the order service.
func (s *Service) Stop() {
    s.mu.Lock()
    s.ready = false
    s.mu.Unlock()
}

// IsReady returns whether the order service is operational.
func (s *Service) IsReady() bool {
    s.mu.RLock()
    defer s.mu.RUnlock()
    return s.ready
}
