<div align="center">

# 📚 BiblioGraph AI

### Distributed Bibliographic Intelligence Platform

_A production-grade microservices monorepo for scraping, processing, and serving Persian bibliographic data_

[![Go](https://img.shields.io/badge/Go-1.21-00ADD8?style=flat-square&logo=go&logoColor=white)](https://golang.org)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![MongoDB](https://img.shields.io/badge/MongoDB-7-47A248?style=flat-square&logo=mongodb&logoColor=white)](https://mongodb.com)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io)
[![RabbitMQ](https://img.shields.io/badge/RabbitMQ-3-FF6600?style=flat-square&logo=rabbitmq&logoColor=white)](https://rabbitmq.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![Prometheus](https://img.shields.io/badge/Prometheus-Monitored-E6522C?style=flat-square&logo=prometheus&logoColor=white)](https://prometheus.io)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Monorepo](https://img.shields.io/badge/Monorepo-Turborepo-EF4444?style=flat-square&logo=turborepo&logoColor=white)](https://turbo.build)

<br/>

**[Website](https://sinasotoudeh.ir)** · **[Report Bug](https://github.com/sinasotoudeh/bibliograph-ai/issues)** · **[Request Feature](https://github.com/sinasotoudeh/bibliograph-ai/issues)**

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [System Architecture](#-system-architecture)
- [Monorepo Structure](#-monorepo-structure)
- [Services](#-services)
  - [Auth Service](#auth-service-go)
  - [Scraper Service](#scraper-service-python)
- [Shared Infrastructure](#-shared-infrastructure)
- [Database Architecture](#-database-architecture)
- [Observability Stack](#-observability-stack)
- [Getting Started](#-getting-started)
- [Development Workflow](#-development-workflow)
- [Environment Configuration](#-environment-configuration)
- [Port Reference](#-port-reference)
- [Security](#-security)
- [Author](#-author)

---

## 🌐 Overview

**BiblioGraph AI** is a distributed, microservices-based platform designed to collect, normalize, and serve Persian bibliographic data at scale. It targets sources such as the National Library of Iran, Fidibo, FIPA, and Cheshmeh Publications, transforming raw scraped data into a structured, searchable knowledge base.

The platform is built as a **pnpm + Turborepo monorepo**, enabling shared packages, unified build pipelines, and independent service deployments — all orchestrated via Docker Compose.

### ✨ Key Capabilities

- **JWT-based authentication** with role-based access control (RBAC), session management, and OAuth2 (Google)
- **Async web scraping** pipeline powered by Celery + RabbitMQ with support for Scrapy, Playwright, and Selenium
- **Multi-database strategy**: PostgreSQL for relational data, MongoDB for raw scrape storage, Redis for caching and sessions, Elasticsearch for full-text search
- **Object storage** via MinIO (S3-compatible) for cover images and file assets
- **Full observability**: Prometheus metrics, Grafana dashboards, Loki log aggregation, and domain-specific alerting rules
- **Persian NLP** normalization using `hazm` for text processing and `jdatetime` for Jalali calendar support

---

## 🏛 System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        bibliograph-network                          │
│                                                                     │
│  ┌──────────────────┐          ┌──────────────────────────────────┐ │
│  │   Auth Service   │          │        Scraper Service           │ │
│  │   (Go / :4000)   │          │     (Python/FastAPI / :8082)     │ │
│  │                  │          │                                  │ │
│  │  ┌────────────┐  │          │  ┌──────────┐  ┌─────────────┐   │ │
│  │  │  REST API  │  │          │  │ FastAPI  │  │Celery Worker│   │ │
│  │  │  JWT Auth  │  │          │  │   API    │  │  (x4 conc.) │   │ │
│  │  │   RBAC     │  │          │  └──────────┘  └─────────────┘   │ │
│  │  └────────────┘  │          │  ┌──────────┐  ┌─────────────┐   │ │
│  └────────┬─────────┘          │  │  Celery  │  │   Flower    │   │ │
│           │                    │  │   Beat   │  │  (:5555)    │   │ │
│           │                    │  └──────────┘  └─────────────┘   │ │
│           │                    └──────────────────────────────────┘ │
│           │                                  │                      │
│    ┌──────▼──────────────────────────────────▼───────┐              │
│    │              Shared Infrastructure              │              │
│    │                                                 │              │
│    │  PostgreSQL:5435  MongoDB:27017  Redis:6379     │              │
│    │  RabbitMQ:5672    Elasticsearch:9200            │              │
│    │  MinIO:9000       MinIO Console:9001            │              │
│    └─────────────────────────────────────────────────┘              │
│                                                                     │
│    ┌─────────────────────────────────────────────────┐              │
│    │              Observability Stack                │              │
│    │                                                 │              │
│    │  Prometheus:9090  Grafana:3001  Loki:3100       │              │
│    │  Promtail  RabbitMQ-Exporter  Redis-Exporter    │              │
│    │  Postgres-Exporter  MongoDB-Exporter            │              │
│    │  Celery-Exporter  Blackbox-Exporter:9115        │              │
│    │  Node-Exporter:9100  cAdvisor:8081              │              │
│    └─────────────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
```

All services communicate over a shared Docker bridge network named **`bibliograph-network`**. The scraper service attaches to this network as an **external** consumer, while the shared infrastructure stack defines and owns it.

---

## 🗂 Monorepo Structure

```
bibliograph-ai/
├── apps/                          # Frontend applications (Next.js, etc.)
├── services/
│   ├── auth-service/              # Go — JWT auth, RBAC, session management
│   │   ├── cmd/main.go
│   │   ├── docker/
│   │   │   ├── Dockerfile         # Multi-stage Go build
│   │   │   ├── docker-compose.yml # Standalone dev stack
│   │   │   └── .env.example
│   │   └── ...
│   └── scraper-service/           # Python — async scraping pipeline
│       ├── src/
│       │   ├── api/               # FastAPI application
│       │   ├── tasks/             # Celery tasks & app config
│       │   └── scrapers/          # Scrapy spiders & Playwright scrapers
│       ├── Dockerfile             # Multi-stage Python build
│       ├── docker-compose.scraper.yml
│       └── pyproject.toml
├── packages/
│   └── database/
│       ├── prisma/
│       │   └── schema.prisma      # Shared PostgreSQL schema (Prisma ORM)
│       └── pg_hba.conf
├── infrastructure/
│   └── docker/
│       ├── docker-compose.dev.yml # Full shared infrastructure stack
│       └── monitoring/
│           ├── prometheus.yml
│           ├── alert_rules.yml
│           ├── blackbox.yml
│           └── grafana/
│               └── dashboards/
├── pnpm-workspace.yaml            # Workspace definition
├── turbo.json                     # Build pipeline config
└── README.md
```

The monorepo is managed with **pnpm workspaces** and **Turborepo**, covering three workspace scopes: `apps/*`, `services/*`, and `packages/*`.

---

## ⚙️ Services

### Auth Service _(Go)_

> `services/auth-service` · Port `4000`

A stateless, layered Go service responsible for all identity and access management across the platform.

**Responsibilities**

- User registration, login, and profile management
- JWT access token issuance and refresh token rotation
- Role-based access control: `USER`, `MODERATOR`, `ADMIN`, `SUPER_ADMIN`
- OAuth2 integration (Google)
- Email verification and password reset flows
- Session tracking via Redis
- Rate limiting and CORS enforcement

**Tech Stack**

| Layer            | Technology               |
| ---------------- | ------------------------ |
| Language         | Go 1.21                  |
| ORM              | Prisma Client Go         |
| Primary DB       | PostgreSQL 16            |
| Cache / Sessions | Redis 7                  |
| Object Storage   | MinIO                    |
| Container        | Multi-stage Alpine build |

**Build**

The Dockerfile uses a two-stage build:

1. `builder` — `golang:1.21-alpine`, compiles a static binary via `CGO_ENABLED=0`
2. `runtime` — `alpine:latest`, runs as a non-root `bibliograph` user

```bash
# Build and run standalone
cd services/auth-service/docker
docker compose up --build
```

The service is available at `http://localhost:4000`.

---

### Scraper Service _(Python)_

> `services/scraper-service` · Port `8082`

An async data collection pipeline that scrapes, normalizes, and stores Persian bibliographic records from external sources.

**Responsibilities**

- Scheduled and on-demand scraping via Celery Beat + Worker
- Multi-engine scraping: Scrapy spiders, Playwright (JS-rendered pages), Selenium
- Persian text normalization with `hazm`
- Jalali ↔ Gregorian date conversion with `jdatetime`
- Raw data persistence to MongoDB; structured data to PostgreSQL via Prisma
- Full-text indexing to Elasticsearch
- Prometheus metrics exposure on `:8001`

**Tech Stack**

| Layer              | Technology                                  |
| ------------------ | ------------------------------------------- |
| Language           | Python 3.11                                 |
| API Framework      | FastAPI 0.109 + Uvicorn                     |
| Task Queue         | Celery 5.3 + RabbitMQ                       |
| Scheduler          | Celery Beat                                 |
| Scraping           | Scrapy 2.11, Playwright 1.40, Selenium 4.16 |
| Raw Storage        | MongoDB 7 (Motor async driver)              |
| Structured Storage | PostgreSQL (Prisma + asyncpg)               |
| Search             | Elasticsearch 8.11                          |
| Cache              | Redis 5                                     |
| NLP                | hazm 0.9                                    |
| Monitoring         | prometheus-client (multiprocess), Flower    |

**Compose Services**

| Container                   | Role                          | Port             |
| --------------------------- | ----------------------------- | ---------------- |
| `bibliograph-scraper-api`   | FastAPI HTTP API              | `8082`           |
| `bibliograph-celery-worker` | Task executor (concurrency=4) | `8001` (metrics) |
| `bibliograph-celery-beat`   | Periodic task scheduler       | —                |
| `bibliograph-flower`        | Celery task dashboard         | `5555`           |

```bash
# Run scraper stack (requires shared infra network to exist first)
cd services/scraper-service
docker compose -f docker-compose.scraper.yml up --build
```

> **Note:** The scraper compose file declares `bibliograph-network` as **external**. The shared infrastructure stack must be running before starting the scraper.

---

## 🔧 Shared Infrastructure

Defined in `infrastructure/docker/docker-compose.dev.yml`. This is the **single source of truth** for all backing services.

### Databases

| Service         | Image                  | Port          | Purpose                                          |
| --------------- | ---------------------- | ------------- | ------------------------------------------------ |
| `postgres`      | `postgres:16`          | `5435:5432`   | Primary relational store (users, books, reviews) |
| `mongo`         | `mongo:latest`         | `27017:27017` | Raw scrape data, analytics                       |
| `elasticsearch` | `elasticsearch:8.11.0` | `9200:9200`   | Full-text book search                            |

### Cache & Messaging

| Service    | Image                          | Port                     | Purpose                                          |
| ---------- | ------------------------------ | ------------------------ | ------------------------------------------------ |
| `redis`    | `redis:7-alpine`               | `6379:6379`              | Session store, task results, rate limiting       |
| `rabbitmq` | `rabbitmq:3-management-alpine` | `5672`, `15672`, `15692` | Celery broker, management UI, Prometheus metrics |

### Object Storage

| Service | Image                | Port           | Purpose                                           |
| ------- | -------------------- | -------------- | ------------------------------------------------- |
| `minio` | `minio/minio:latest` | `9000`, `9001` | S3-compatible storage for cover images and assets |

### Starting the Full Stack

```bash
cd infrastructure/docker
docker compose -f docker-compose.dev.yml up -d
```

All services include **healthchecks** and persist data via named Docker volumes.

---

## 🗄 Database Architecture

### PostgreSQL — Relational Core

Managed via **Prisma ORM** from the shared `packages/database` package. The schema covers the full bibliographic domain:

```
User ──────────────────────────────────────────────────────────────────
  │  role: USER | MODERATOR | ADMIN | SUPER_ADMIN
  ├── Review[] ──► Comment[]
  ├── Rating[]
  ├── ReadingList[] ──► ReadingListItem[] ──► Book
  ├── Favorite[] ──► Book
  ├── ReadingProgress[] ──► Book  (status: TO_READ|READING|COMPLETED|ABANDONED)
  └── Annotation[] ──► Book

Book ──────────────────────────────────────────────────────────────────
  │  status: DRAFT | PUBLISHED | ARCHIVED
  ├── Author
  ├── BookCategory[] ──► Category (hierarchical, self-referencing)
  └── Translation[] ──► Translator
       quality: EXCELLENT | GOOD | AVERAGE | POOR
```

**Key design decisions:**

- All primary keys use `cuid()` for globally unique, URL-safe identifiers
- `fullTextSearch` and `fullTextIndex` preview features enabled for PostgreSQL FTS
- Cascade deletes on all user-owned content (reviews, favorites, annotations)
- `Category` supports unlimited nesting via a self-referencing `parentId`

### MongoDB — Raw & Analytics

Database: `bibliograph_analytics`
Used by the scraper service to store raw HTML, intermediate scrape results, and analytics events before normalization into PostgreSQL.

### Redis — Cache & Sessions

- **DB 0**: Auth sessions, rate limiting counters, CORS state
- **DB 1**: Celery task result backend
- Persistence enabled via `appendonly yes`
- Password-protected in all environments

### Elasticsearch

- Version: `8.11.0`, single-node, security disabled for development
- Used for full-text search across book titles, authors, descriptions
- Indexed from PostgreSQL after normalization

---

## 📊 Observability Stack

### Metrics — Prometheus + Grafana

Prometheus scrapes **14 targets** across the platform:

| Job                  | Target                             | Interval |
| -------------------- | ---------------------------------- | -------- |
| `prometheus`         | `localhost:9090`                   | 5s       |
| `bibliograph-worker` | `celery-worker:8001`               | 5s       |
| `celery-exporter`    | `celery-exporter:9808`             | 5s       |
| `redis-exporter`     | `redis-exporter:9121`              | 30s      |
| `postgres-exporter`  | `postgres-exporter:9187`           | 30s      |
| `mongodb-exporter`   | `mongodb-exporter:9216`            | 30s      |
| `rabbitmq`           | `rabbitmq:15692`                   | 30s      |
| `minio`              | `minio:9000/minio/v2/metrics/node` | 30s      |
| `scraper-api`        | `scraper-api:8000/metrics`         | 30s      |
| `blackbox-http`      | fidibo.com, fipa.ir, cheshmeh.ir   | —        |

Grafana is available at `http://localhost:3001` (default credentials: `admin` / `admin123`).

TSDB retention: **30 days / 10 GB**.

### Logs — Loki + Promtail

Promtail collects container logs via the Docker socket and ships them to Loki (`localhost:3100`). Logs are queryable from Grafana using LogQL.

### Alerting Rules

Alerts are grouped under `bibliograph_scraping_alerts`:

| Alert               | Condition                    | Severity |
| ------------------- | ---------------------------- | -------- |
| `RedisDown`         | `up == 0` for 2m             | critical |
| `PostgreSQLDown`    | `up == 0` for 2m             | critical |
| `ElasticsearchDown` | `up == 0` for 2m             | critical |
| `ScraperAPIDown`    | `up == 0` for 1m             | critical |
| `HighErrorRate`     | HTTP 5xx > 10% for 5m        | warning  |
| `ScrapingJobStuck`  | job duration > 3600s for 10m | warning  |
| `LowScrapingRate`   | < 0.1 books/min for 15m      | warning  |
| `HighDuplicateRate` | duplicates > 80% for 10m     | warning  |
| `HighMemoryUsage`   | container mem > 90% for 5m   | warning  |
| `HighCPUUsage`      | container CPU > 80% for 10m  | warning  |

Alerts route to **Alertmanager** at `alertmanager:9093`.

### Host & Container Monitoring

| Exporter        | Port   | Purpose                         |
| --------------- | ------ | ------------------------------- |
| `node-exporter` | `9100` | Host CPU, memory, disk, network |
| `cAdvisor`      | `8081` | Per-container resource usage    |

---

## 🚀 Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) ≥ 24
- [Docker Compose](https://docs.docker.com/compose/) ≥ 2.20
- [pnpm](https://pnpm.io/installation) ≥ 8
- [Node.js](https://nodejs.org/) ≥ 20 _(for Turborepo and frontend apps)_
- [Go](https://golang.org/dl/) ≥ 1.21 _(for local auth-service development)_
- [Python](https://python.org) ≥ 3.11 _(for local scraper development)_

### 1. Clone the Repository

```bash
git clone https://github.com/sinasotoudeh/bibliograph-ai.git
cd bibliograph-ai
```

### 2. Install Node Dependencies

```bash
pnpm install
```

### 3. Start Shared Infrastructure

```bash
cd infrastructure/docker
docker compose -f docker-compose.dev.yml up -d
```

Wait for all healthchecks to pass:

```bash
docker compose -f docker-compose.dev.yml ps
```

### 4. Run Database Migrations

```bash
cd packages/database
pnpm prisma migrate dev
pnpm prisma generate
```

### 5. Start Auth Service

```bash
cd services/auth-service/docker
cp .env.example .env
# Edit .env with your secrets
docker compose up --build
```

Auth API: `http://localhost:4000`

### 6. Start Scraper Service

```bash
cd services/scraper-service
cp .env.example .env
# Edit .env with your secrets
docker compose -f docker-compose.scraper.yml up --build
```

Scraper API: `http://localhost:8082`
Flower dashboard: `http://localhost:5555` _(admin / bibliograph_flower_2024)_

---

## 🔄 Development Workflow

### Turborepo Pipeline

The `turbo.json` defines the following task graph:

```
build   → depends on upstream ^build   → outputs: dist/**, .next/**
dev     → no cache, persistent
lint    → depends on upstream ^lint
test    → depends on ^build            → outputs: coverage/**
clean   → no cache
```

```bash
# Run all services in dev mode
pnpm turbo dev

# Build all packages and services
pnpm turbo build

# Run all tests
pnpm turbo test

# Lint everything
pnpm turbo lint
```

### Working on a Single Service

```bash
# Auth service only
pnpm turbo dev --filter=auth-service

# Scraper service only
pnpm turbo dev --filter=scraper-service
```

### Database Schema Changes

```bash
cd packages/database

# Create a new migration
pnpm prisma migrate dev --name <migration_name>

# Regenerate Prisma client after schema changes
pnpm prisma generate

# Open Prisma Studio (visual DB browser)
pnpm prisma studio
```

---

## 🔐 Environment Configuration

### Auth Service — `services/auth-service/docker/.env`

| Variable                   | Description                     | Example                   |
| -------------------------- | ------------------------------- | ------------------------- |
| `PORT`                     | HTTP server port                | `4000`                    |
| `DATABASE_URL`             | PostgreSQL connection string    | `postgresql://...`        |
| `JWT_SECRET`               | Secret for signing JWTs         | _(strong random string)_  |
| `JWT_EXPIRES_IN`           | Access token TTL                | `1d`                      |
| `REFRESH_TOKEN_EXPIRES_IN` | Refresh token TTL               | `7d`                      |
| `GOOGLE_CLIENT_ID`         | OAuth2 client ID                | —                         |
| `GOOGLE_CLIENT_SECRET`     | OAuth2 client secret            | —                         |
| `REDIS_URL`                | Redis connection string         | `redis://:pass@host:6379` |
| `RATE_LIMIT_REQUESTS`      | Max requests per window         | `100`                     |
| `RATE_LIMIT_WINDOW`        | Rate limit window               | `1m`                      |
| `CORS_ALLOWED_ORIGINS`     | Comma-separated allowed origins | `http://localhost:3000`   |
| `MINIO_ENDPOINT`           | MinIO host:port                 | `localhost:9000`          |
| `SMTP_HOST`                | SMTP server for email           | —                         |
| `LOG_LEVEL`                | Logging verbosity               | `info`                    |

### Scraper Service — `services/scraper-service/.env`

Refer to the scraper service README for the full variable reference. Key variables include broker URLs, MongoDB URI, Elasticsearch host, and Sentry DSN.

### Grafana

| Variable           | Default    |
| ------------------ | ---------- |
| `GRAFANA_PASSWORD` | `admin123` |

> ⚠️ **All default credentials are for development only.** Rotate all secrets before any production deployment.

---

## 🌐 Port Reference

| Port    | Service                     | Protocol |
| ------- | --------------------------- | -------- |
| `4000`  | Auth Service API            | HTTP     |
| `5435`  | PostgreSQL                  | TCP      |
| `27017` | MongoDB                     | TCP      |
| `9200`  | Elasticsearch HTTP          | HTTP     |
| `9300`  | Elasticsearch Transport     | TCP      |
| `6379`  | Redis                       | TCP      |
| `5672`  | RabbitMQ AMQP               | AMQP     |
| `15672` | RabbitMQ Management UI      | HTTP     |
| `15692` | RabbitMQ Prometheus metrics | HTTP     |
| `9000`  | MinIO S3 API                | HTTP     |
| `9001`  | MinIO Console               | HTTP     |
| `8082`  | Scraper API                 | HTTP     |
| `8001`  | Celery Worker metrics       | HTTP     |
| `5555`  | Flower (Celery UI)          | HTTP     |
| `9090`  | Prometheus                  | HTTP     |
| `3001`  | Grafana                     | HTTP     |
| `3100`  | Loki                        | HTTP     |
| `9121`  | Redis Exporter              | HTTP     |
| `9187`  | PostgreSQL Exporter         | HTTP     |
| `9216`  | MongoDB Exporter            | HTTP     |
| `9808`  | Celery Exporter             | HTTP     |
| `9115`  | Blackbox Exporter           | HTTP     |
| `9100`  | Node Exporter               | HTTP     |
| `8081`  | cAdvisor                    | HTTP     |

---

## 🔒 Security

### Authentication & Authorization

- **JWT** access tokens with configurable TTL (default: 1 day)
- **Refresh token rotation** with 7-day TTL stored in Redis
- **RBAC** with four roles: `USER`, `MODERATOR`, `ADMIN`, `SUPER_ADMIN`
- **OAuth2** via Google for social login

### Transport & API Security

- **CORS** with explicit origin, method, and header allowlists
- **Rate limiting** (100 req/min default) enforced at the middleware layer
- All services run as **non-root users** inside containers (`bibliograph` / `scraper`)

### Data Security

- All database passwords are environment-variable-driven — no hardcoded secrets in application code
- Redis requires password authentication (`requirepass`)
- PostgreSQL access restricted by `pg_hba.conf` (host-based authentication)
- MinIO credentials are environment-injected

### Container Security

- Auth service binary compiled with `CGO_ENABLED=0` for a fully static, minimal attack surface
- Both Dockerfiles use **multi-stage builds** to exclude build tooling from runtime images
- Elasticsearch security (`xpack.security`) is disabled in development — **must be enabled in production**

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m 'feat: add your feature'`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

Please follow [Conventional Commits](https://www.conventionalcommits.org/) for commit messages.

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 👤 Author

<div align="center">

**Sina Sotoudeh**

_Software Engineer & Backend Architect_

[![Website](https://img.shields.io/badge/Website-sinasotoudeh.ir-0A66C2?style=flat-square&logo=safari&logoColor=white)](https://sinasotoudeh.ir)
[![GitHub](https://img.shields.io/badge/GitHub-sinasotoudeh-181717?style=flat-square&logo=github&logoColor=white)](https://github.com/sinasotoudeh)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-sinasotoudeh-0A66C2?style=flat-square&logo=linkedin&logoColor=white)](https://linkedin.com/in/sinasotoudeh)
[![Email](https://img.shields.io/badge/Email-s.sotoudeh1@gmail.com-EA4335?style=flat-square&logo=gmail&logoColor=white)](mailto:s.sotoudeh1@gmail.com)

</div>

---

<div align="center">

_Built with precision for the Persian bibliographic ecosystem._

</div>
