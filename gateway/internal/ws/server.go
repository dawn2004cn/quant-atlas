package ws

import (
	"context"
	"encoding/json"
	"log"
	"net/http"
	"sync"
	"time"

	"github.com/gorilla/websocket"

	"quant-atlas-gateway/internal/market"
	"quant-atlas-gateway/internal/order"
)

var upgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 1024,
	CheckOrigin: func(r *http.Request) bool {
		return true
	},
}

type Client struct {
	conn    *websocket.Conn
	send    chan []byte
	symbols map[string]bool
	userID  string
	mu      sync.RWMutex
}

type Server struct {
	marketSvc  *market.Service
	orderSvc   *order.Service
	clients    map[*Client]bool
	register   chan *Client
	unregister chan *Client
	broadcast  chan []byte
	mu         sync.RWMutex
}

type Message struct {
	Type    string          `json:"type"`
	Payload json.RawMessage `json:"payload"`
	Ts      int64           `json:"ts"`
}

type SubscriptionPayload struct {
	Symbols []string `json:"symbols"`
}

func NewServer(ms *market.Service, os *order.Service) *Server {
	s := &Server{
		marketSvc:  ms,
		orderSvc:   os,
		clients:    make(map[*Client]bool),
		register:   make(chan *Client),
		unregister: make(chan *Client),
		broadcast:  make(chan []byte, 256),
	}
	go s.run()
	return s
}

func (s *Server) run() {
	for {
		select {
		case client := <-s.register:
			s.mu.Lock()
			s.clients[client] = true
			s.mu.Unlock()
			log.Printf("[ws] client registered (total: %d)", len(s.clients))

		case client := <-s.unregister:
			s.mu.Lock()
			if _, ok := s.clients[client]; ok {
				delete(s.clients, client)
				close(client.send)
			}
			s.mu.Unlock()
			log.Printf("[ws] client unregistered (total: %d)", len(s.clients))

		case message := <-s.broadcast:
			s.mu.RLock()
			for client := range s.clients {
				select {
				case client.send <- message:
				default:
					close(client.send)
					delete(s.clients, client)
				}
			}
			s.mu.RUnlock()
		}
	}
}

func (s *Server) Listen(addr string) error {
	mux := http.NewServeMux()
	mux.HandleFunc("/ws", s.HandleUpgrade)
	mux.HandleFunc("/health", s.HandleHealth)
	log.Printf("[ws] listening on %s", addr)
	return http.ListenAndServe(addr, mux)
}

func (s *Server) HandleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":  "ok",
		"version": "0.2.0",
		"clients": len(s.clients),
		"market":  s.marketSvc.IsReady(),
	})
}

func (s *Server) HandleUpgrade(w http.ResponseWriter, r *http.Request) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("[ws] upgrade error: %v", err)
		return
	}
	client := &Client{conn: conn, send: make(chan []byte, 64), symbols: make(map[string]bool)}
	s.register <- client
	go client.writePump()
	go s.readPump(client)
}

func (s *Server) readPump(client *Client) {
	defer func() {
		s.unregister <- client
		client.conn.Close()
	}()
	client.conn.SetReadLimit(4096)
	client.conn.SetReadDeadline(time.Now().Add(60 * time.Second))
	client.conn.SetPongHandler(func(string) error {
		client.conn.SetReadDeadline(time.Now().Add(60 * time.Second))
		return nil
	})
	for {
		_, raw, err := client.conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseNormalClosure) {
				log.Printf("[ws] read error: %v", err)
			}
			break
		}
		var msg Message
		if err := json.Unmarshal(raw, &msg); err != nil {
			continue
		}
		switch msg.Type {
		case "subscribe":
			var sub SubscriptionPayload
			json.Unmarshal(msg.Payload, &sub)
			client.mu.Lock()
			for _, sym := range sub.Symbols {
				client.symbols[sym] = true
				s.marketSvc.Subscribe(sym)
			}
			client.mu.Unlock()
			ack, _ := json.Marshal(map[string]interface{}{"type": "subscribed", "symbols": sub.Symbols, "ts": time.Now().UnixMilli()})
			client.send <- ack
		case "unsubscribe":
			var unsub SubscriptionPayload
			json.Unmarshal(msg.Payload, &unsub)
			client.mu.Lock()
			for _, sym := range unsub.Symbols {
				delete(client.symbols, sym)
			}
			client.mu.Unlock()
		case "ping":
			pong, _ := json.Marshal(map[string]string{"type": "pong"})
			client.send <- pong
		}
	}
}

func (client *Client) writePump() {
	ticker := time.NewTicker(30 * time.Second)
	defer func() { ticker.Stop(); client.conn.Close() }()
	for {
		select {
		case message, ok := <-client.send:
			client.conn.SetWriteDeadline(time.Now().Add(10 * time.Second))
			if !ok {
				client.conn.WriteMessage(websocket.CloseMessage, []byte{})
				return
			}
			if err := client.conn.WriteMessage(websocket.TextMessage, message); err != nil {
				return
			}
		case <-ticker.C:
			client.conn.SetWriteDeadline(time.Now().Add(10 * time.Second))
			if err := client.conn.WriteMessage(websocket.PingMessage, nil); err != nil {
				return
			}
		}
	}
}

func (s *Server) BroadcastQuote(q market.Quote) {
	data, err := json.Marshal(map[string]interface{}{"type": "quote", "payload": q, "ts": q.Timestamp})
	if err != nil {
		return
	}
	s.mu.RLock()
	defer s.mu.RUnlock()
	for client := range s.clients {
		client.mu.RLock()
		subscribed := client.symbols[q.Symbol]
		client.mu.RUnlock()
		if !subscribed {
			continue
		}
		select {
		case client.send <- data:
		default:
		}
	}
}

func (s *Server) HandleMarketQuote(q market.Quote) {
	s.BroadcastQuote(q)
}

func (s *Server) Shutdown(ctx context.Context) {
	s.mu.Lock()
	defer s.mu.Unlock()
	for client := range s.clients {
		client.conn.Close()
	}
	log.Println("[ws] WebSocket gateway shut down")
}

func (s *Server) WaitForReady(timeout time.Duration) bool {
	deadline := time.After(timeout)
	for {
		select {
		case <-deadline:
			return false
		default:
			if s.marketSvc.IsReady() && s.orderSvc.IsReady() {
				return true
			}
			time.Sleep(100 * time.Millisecond)
		}
	}
}
