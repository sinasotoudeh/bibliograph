# Bibliograph AI

## Overview
Bibliograph AI is a production-grade monorepo designed for large-scale
book data collection, processing, and analytics.

The system is containerized and composed of multiple services
written in Go, Python, and Node.js, orchestrated via Docker.

---

## Repository Structure

.
├── apps/
├── services/
│   ├── auth-service
│   └── scraper-service
├── packages/
├── infrastructure/
│   └── docker/
├── backups/           # ignored – local / logical backups
└── README.md


---

## Core Services

- **auth-service** – Authentication & authorization (Go)
- **scraper-service**
  - FastAPI API
  - Celery workers
  - Celery Beat & Flower

---

## Infrastructure Stack

- PostgreSQL
- MongoDB
- Redis
- RabbitMQ
- Elasticsearch
- MinIO
- Prometheus + Grafana + Loki

---

## Requirements

- Docker & Docker Compose
- Git
- (Optional) Go, Python, Node.js for local development

---

## Development

Start the full development stack:

docker compose -f infrastructure/docker/docker-compose.dev.yml up -d

---

## Notes

- Sensitive files (`.env*`, keys, backups) are intentionally excluded from Git.
- This repository follows modern Git best practices (`main` branch, `.gitattributes`).


---

