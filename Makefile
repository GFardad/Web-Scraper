# ═══════════════════════════════════════════════════════════════════
# SCRAPER MAKEFILE - One-Command Deployment
# ═══════════════════════════════════════════════════════════════════

.PHONY: help deploy up down logs restart build clean test validate prerequisites

# Default target
help:
	@echo "═══════════════════════════════════════════════════════════"
	@echo "📦 Enterprise Scraper - Docker Deployment"
	@echo "═══════════════════════════════════════════════════════════"
	@echo ""
	@echo "Available commands:"
	@echo "  make deploy          - Full deployment (check prerequisites + build + up)"
	@echo "  make up              - Start all containers"
	@echo "  make down            - Stop all containers"
	@echo "  make restart         - Restart all containers"
	@echo "  make logs            - Follow logs (scraper service)"
	@echo "  make logs-all        - Follow logs (all services)"
	@echo "  make logs-postgres   - Follow PostgreSQL logs"
	@echo "  make logs-mongo      - Follow MongoDB logs"
	@echo "  make logs-ollama     - Follow Ollama logs"
	@echo "  make build           - Build Docker images"
	@echo "  make clean           - Stop and remove containers (keeps volumes)"
	@echo "  make destroy         - ⚠️  DANGER: Remove everything including data volumes"
	@echo "  make test            - Run integration tests"
	@echo "  make validate        - Validate config.yaml syntax"
	@echo "  make prerequisites   - Check system prerequisites"
	@echo "  make env             - Create .env from .env.example"
	@echo ""

# ─────────────────────────────────────────────────────────────────
# DEPLOYMENT COMMANDS
# ─────────────────────────────────────────────────────────────────

deploy: prerequisites env-check
	@echo "🚀 Deploying Scraper Stack..."
	docker-compose up -d --build
	@echo ""
	@echo "✅ Stack deployed successfully!"
	@echo ""
	@echo "📊 Access points:"
	@echo "  - Health Check: http://localhost:8080/health"
	@echo "  - Prometheus:   http://localhost:9091"
	@echo "  - Postgres:     localhost:5432"
	@echo "  - MongoDB:      localhost:27017"
	@echo ""
	@echo "📝 View logs:"
	@echo "  make logs"
	@echo ""

up:
	@echo "▶️  Starting containers..."
	docker-compose up -d

down:
	@echo "⏹️  Stopping containers..."
	docker-compose down

restart:
	@echo "🔄 Restarting containers..."
	docker-compose restart

# ─────────────────────────────────────────────────────────────────
# LOGGING COMMANDS
# ─────────────────────────────────────────────────────────────────

logs:
	docker-compose logs -f --tail=100 scraper

logs-all:
	docker-compose logs -f --tail=50

logs-postgres:
	docker-compose logs -f postgres

logs-mongo:
	docker-compose logs -f mongo

logs-ollama:
	docker-compose logs -f ollama

logs-paddleocr:
	docker-compose logs -f paddleocr

# ─────────────────────────────────────────────────────────────────
# BUILD & CLEANUP
# ─────────────────────────────────────────────────────────────────

build:
	@echo "🔨 Building Docker images..."
	docker-compose build --no-cache

clean:
	@echo "🧹 Cleaning up containers..."
	docker-compose down --remove-orphans
	@echo "✅ Cleanup complete (volumes preserved)"

destroy:
	@echo "⚠️  WARNING: This will DELETE ALL DATA including volumes!"
	@read -p "Are you sure? Type 'yes' to confirm: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		docker-compose down -v --remove-orphans; \
		echo "💥 Everything destroyed!"; \
	else \
		echo "❌ Cancelled"; \
	fi

# ─────────────────────────────────────────────────────────────────
# VALIDATION & TESTING
# ─────────────────────────────────────────────────────────────────

prerequisites:
	@echo "🔍 Checking prerequisites..."
	@./scripts/check_prerequisites.sh

validate:
	@echo "✅ Validating config.yaml..."
	@python -c "import yaml; yaml.safe_load(open('config.yaml'))" && echo "Config is valid!" || echo "❌ Config has errors!"

test:
	@echo "🧪 Running integration tests..."
	docker exec scraper-app pytest tests/test_integration.py -v

# ─────────────────────────────────────────────────────────────────
# ENVIRONMENT SETUP
# ─────────────────────────────────────────────────────────────────

env:
	@if [ ! -f .env ]; then \
		echo "📝 Creating .env from .env.example..."; \
		cp .env.example .env; \
		echo "✅ Created .env - Please edit it with your credentials!"; \
	else \
		echo "⚠️  .env already exists, skipping"; \
	fi

env-check:
	@if [ ! -f .env ]; then \
		echo "❌ .env file not found! Run: make env"; \
		exit 1; \
	fi

# ─────────────────────────────────────────────────────────────────
# GPU & NVIDIA TOOLKIT
# ─────────────────────────────────────────────────────────────────

install-nvidia-toolkit:
	@echo "🔧 Installing NVIDIA Container Toolkit..."
	@./scripts/install_nvidia_toolkit.sh

gpu-test:
	@echo "🧪 Testing GPU access in Docker..."
	docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi

# ─────────────────────────────────────────────────────────────────
# MAINTENANCE
# ─────────────────────────────────────────────────────────────────

status:
	@echo "📊 Container Status:"
	@docker-compose ps

stats:
	@echo "📈 Resource Usage:"
	@docker stats --no-stream

shell:
	docker exec -it scraper-app /bin/bash

db-shell:
	docker exec -it scraper-postgres psql -U scraper -d scraper_db

mongo-shell:
	docker exec -it scraper-mongo mongosh --username scraper --authenticationDatabase admin

redis-cli:
	docker exec -it scraper-redis redis-cli -a $$(grep REDIS_PASSWORD .env | cut -d '=' -f2)
