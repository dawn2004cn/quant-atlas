.PHONY: help build up down logs clean test deploy-k8s

help:
	@echo "quant-atlas Microservices Deployment"
	@echo ""
	@echo "Targets:"
	@echo "  build        Build all Docker images"
	@echo "  up           Start all services with Docker Compose"
	@echo "  down         Stop all services"
	@echo "  logs         Show service logs"
	@echo "  clean        Remove all containers and volumes"
	@echo "  test         Run integration tests"
	@echo "  deploy-k8s   Deploy to Kubernetes cluster"
	@echo "  gateway-setup Configure Kong API Gateway"

build:
	@echo "Building microservice images..."
	docker compose build

up:
	@echo "Starting quant-atlas microservices..."
	docker compose up -d
	@echo "Waiting for services to be healthy..."
	@sleep 10
	@echo "Gateway: http://localhost:8000"
	@echo "Kong Admin: http://localhost:8001"

down:
	@echo "Stopping services..."
	docker compose down

logs:
	docker compose logs -f --tail=100

clean:
	@echo "Removing containers and volumes..."
	docker compose down -v
	docker system prune -f

test:
	@echo "Running integration tests..."
	python scripts/test_microservices.py

deploy-k8s:
	@echo "Deploying to Kubernetes..."
	kubectl apply -f infrastructure/k8s/namespace.yaml
	kubectl apply -f infrastructure/k8s/configmap.yaml
	kubectl apply -f infrastructure/k8s/secrets.yaml
	kubectl apply -f infrastructure/k8s/mysql/
	kubectl apply -f infrastructure/k8s/redis/
	kubectl apply -f infrastructure/k8s/market-data/
	kubectl apply -f infrastructure/k8s/strategy/
	kubectl apply -f infrastructure/k8s/ai-agent/
	kubectl apply -f infrastructure/k8s/portfolio-risk/
	kubectl apply -f infrastructure/k8s/execution/
	kubectl apply -f infrastructure/k8s/system-user/
	kubectl apply -f infrastructure/k8s/data/
	kubectl apply -f infrastructure/k8s/research/
	kubectl apply -f infrastructure/k8s/ingress/

gateway-setup:
	@echo "Configuring Kong API Gateway..."
	curl -i -X POST http://localhost:8001/services \
		--data name=market-data-service \
		--data url=http://market-data:5101
	curl -i -X POST http://localhost:8001/services \
		--data name=strategy-service \
		--data url=http://strategy:5201
	curl -i -X POST http://localhost:8001/services \
		--data name=ai-agent-service \
		--data url=http://ai-agent:5301
	curl -i -X POST http://localhost:8001/services \
		--data name=portfolio-risk-service \
		--data url=http://portfolio-risk:5401
	curl -i -X POST http://localhost:8001/services \
		--data name=execution-service \
		--data url=http://execution:5501
	curl -i -X POST http://localhost:8001/services \
		--data name=system-user-service \
		--data url=http://system-user:5601
	curl -i -X POST http://localhost:8001/services \
		--data name=data-service \
		--data url=http://data:5701
	curl -i -X POST http://localhost:8001/services \
		--data name=research-service \
		--data url=http://research:5801
