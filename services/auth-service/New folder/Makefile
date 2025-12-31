# Makefile
# Helper commands for development and deployment

# Variables
APP_NAME := bibliograph
VERSION := $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")
BUILD_TIME := $(shell date +%Y-%m-%dT%H:%M:%S%z)
LDFLAGS := -ldflags "-X main.Version=$(VERSION) -X main.BuildTime=$(BUILD_TIME)"

# Go settings
GO := go
GOFMT := gofmt
GOLINT := golangci-lint

# Docker settings
DOCKER_IMAGE := $(APP_NAME):$(VERSION)
DOCKER_COMPOSE := docker-compose

.PHONY: help build run test clean docker-build docker-up docker-down docker-logs fmt lint migrate

# Default target
help: ## Show this help message
@echo 'Usage: make [target]'
@echo ''
@echo 'Available targets:'
@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Development targets
deps: ## Download dependencies
$(GO) mod download
$(GO) mod tidy

build: deps ## Build the application
$(GO) build $(LDFLAGS) -o bin/$(APP_NAME) cmd/main.go

run: ## Run the application
$(GO) run cmd/main.go

dev: ## Run in development mode with hot reload (requires air)
@if ! command -v air &> /dev/null; then \
echo "Installing air for hot reload..."; \
$(GO) install github.com/cosmtrek/air@latest; \
fi
air

# Testing targets
test: ## Run tests
$(GO) test -v ./...

test-coverage: ## Run tests with coverage
$(GO) test -v -coverprofile=coverage.out ./...
$(GO) tool cover -html=coverage.out -o coverage.html

# Code quality targets
fmt: ## Format code
$(GOFMT) -s -w .

lint: ## Lint code
@if ! command -v $(GOLINT) &> /dev/null; then \
echo "Installing golangci-lint..."; \
curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b $(shell $(GO) env GOPATH)/bin v1.54.2; \
fi
$(GOLINT) run

# Database targets
migrate-up: ## Run database migrations up
$(GO) run cmd/migrate/main.go up

migrate-down: ## Run database migrations down
$(GO) run cmd/migrate/main.go down

migrate-create: ## Create new migration (usage: make migrate-create name=add_users_table)
@if [ -z "$(name)" ]; then echo "Error: name parameter is required. Usage: make migrate-create name=migration_name"; exit 1; fi
migrate create -ext sql -dir migrations $(name)

# Docker targets
docker-build: ## Build Docker image
docker build -t $(DOCKER_IMAGE) .

docker-up: ## Start services with Docker Compose
$(DOCKER_COMPOSE) up -d

docker-down: ## Stop services with Docker Compose
$(DOCKER_COMPOSE) down

docker-logs: ## Show Docker logs
$(DOCKER_COMPOSE) logs -f

docker-restart: ## Restart Docker services
$(DOCKER_COMPOSE) restart

# Production targets
clean: ## Clean build artifacts
rm -rf bin/
rm -f coverage.out coverage.html

clean-docker: ## Clean Docker images and containers
docker system prune -f
docker volume prune -f

# Install tools
install-tools: ## Install development tools
$(GO) install github.com/cosmtrek/air@latest
$(GO) install github.com/golangci/golangci-lint/cmd/golangci-lint@latest
$(GO) install github.com/golang-migrate/migrate/v4/cmd/migrate@latest

# Quick start
quick-start: ## Quick start for development (install deps, start DB, run app)
make deps
make docker-up
sleep 10
make migrate-up
make run