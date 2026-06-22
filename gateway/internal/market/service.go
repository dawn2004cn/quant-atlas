package market

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"sync"
	"time"
)

// QuoteHandler is called with every fetched quote for downstream broadcast.
type QuoteHandler func(Quote)

// Service manages the async market data pipeline.
type Service struct {
	pythonURL    string
	ready        bool
	mu           sync.RWMutex
	subs         map[string]chan Quote
	quoteHandler QuoteHandler
	done         chan struct{}
}

type Quote struct {
	Symbol    string  "json:\"symbol\""
	Market    string  "json:\"market\""
	Price     float64 "json:\"price\""
	ChangePct float64 "json:\"change_pct\""
	Volume    int64   "json:\"volume\""
	Timestamp int64   "json:\"ts\""
}

func NewService(pythonURL string) *Service {
	return &Service{
		pythonURL: pythonURL,
		subs:      make(map[string]chan Quote),
		done:      make(chan struct{}),
	}
}

// SetQuoteHandler registers a callback for quote broadcast.
func (s *Service) SetQuoteHandler(h QuoteHandler) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.quoteHandler = h
}

func (s *Service) Start(ctx context.Context) error {
	log.Println("[market] Starting async market data pipeline")
	s.mu.Lock()
	s.ready = true
	s.mu.Unlock()
	go s.pollLoop(ctx)
	return nil
}

func (s *Service) Stop() {
	close(s.done)
}

func (s *Service) IsReady() bool {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.ready
}

func (s *Service) Subscribe(symbol string) (<-chan Quote, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	ch, exists := s.subs[symbol]
	if !exists {
		ch = make(chan Quote, 16)
		s.subs[symbol] = ch
	}
	return ch, nil
}

func (s *Service) pollLoop(ctx context.Context) {
	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()
	for {
		select {
		case <-s.done:
			return
		case <-ctx.Done():
			return
		case <-ticker.C:
			s.pollQuotes(ctx)
		}
	}
}

func (s *Service) pollQuotes(ctx context.Context) {
	s.mu.RLock()
	symbols := make([]string, 0, len(s.subs))
	for sym := range s.subs {
		symbols = append(symbols, sym)
	}
	s.mu.RUnlock()

	if len(symbols) == 0 {
		return
	}

	for _, sym := range symbols {
		quote, err := s.fetchQuote(ctx, sym)
		if err != nil {
			continue
		}
		s.mu.RLock()
		ch, ok := s.subs[sym]
		handler := s.quoteHandler
		s.mu.RUnlock()

		if ok {
			select {
			case ch <- quote:
			default:
			}
		}
		if handler != nil {
			handler(quote)
		}
	}
}

func (s *Service) fetchQuote(ctx context.Context, symbol string) (Quote, error) {
	url := fmt.Sprintf("%s/api/v1/stock/quote/%s", s.pythonURL, symbol)
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return Quote{}, err
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return Quote{}, fmt.Errorf("quote fetch: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return Quote{}, fmt.Errorf("quote fetch %s: HTTP %d", symbol, resp.StatusCode)
	}
	var q Quote
	if err := json.NewDecoder(resp.Body).Decode(&q); err != nil {
		return Quote{}, fmt.Errorf("quote decode: %w", err)
	}
	q.Timestamp = time.Now().UnixMilli()
	return q, nil
}
