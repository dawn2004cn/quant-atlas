package broker

import "fmt"

// Broker runs an order on an external trading system.
type Broker interface {
	Name() string
	Submit(order *OrderEnvelope) (*BrokerResult, error)
}

type OrderEnvelope struct {
	OrderID    string
	Symbol     string
	Side       string
	Price      float64
	Quantity   int64
	StrategyID string
	UserID     string
	Metadata   map[string]string
}

type BrokerResult struct {
	Accepted bool
	State    string // pending / accepted / rejected
	Reason   string
}

// Registry maps broker names to Broker instances.
type Registry struct {
	brokers map[string]Broker
}

func NewRegistry() *Registry {
	return &Registry{brokers: make(map[string]Broker)}
}

func (r *Registry) Register(name string, b Broker) {
	r.brokers[name] = b
}

func (r *Registry) Get(name string) (Broker, error) {
	b, ok := r.brokers[name]
	if !ok {
		return nil, fmt.Errorf("broker %q not registered", name)
	}
	return b, nil
}

func (r *Registry) List() []string {
	names := make([]string, 0, len(r.brokers))
	for n := range r.brokers {
		names = append(names, n)
	}
	return names
}