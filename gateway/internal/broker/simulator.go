package broker

import "fmt"

// SimulatorBroker accepts every order and simulates immediate fill.
type SimulatorBroker struct{}

func NewSimulatorBroker() *SimulatorBroker {
	return &SimulatorBroker{}
}

func (s *SimulatorBroker) Name() string { return "simulator" }

func (s *SimulatorBroker) Submit(env *OrderEnvelope) (*BrokerResult, error) {
	return &BrokerResult{
		Accepted: true,
		State:    "accepted",
		Reason:   fmt.Sprintf("simulator accepted order %s", env.OrderID),
	}, nil
}