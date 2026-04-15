# 🔍 Bibliograph AI — Scraper Service

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Celery](https://img.shields.io/badge/Celery-5.x-37814A?style=for-the-badge&logo=celery&logoColor=white)](https://docs.celeryq.dev)
[![MongoDB](https://img.shields.io/badge/MongoDB-Motor_Async-47A248?style=for-the-badge&logo=mongodb&logoColor=white)](https://motor.readthedocs.io)
[![RabbitMQ](https://img.shields.io/badge/RabbitMQ-Broker-FF6600?style=for-the-badge&logo=rabbitmq&logoColor=white)](https://rabbitmq.com)
[![Redis](https://img.shields.io/badge/Redis-Cache_&_Backend-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![Prometheus](https://img.shields.io/badge/Prometheus-Metrics-E6522C?style=for-the-badge&logo=prometheus&logoColor=white)](https://prometheus.io)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)
[![Maintainer](https://img.shields.io/badge/Maintainer-Sina_Sotoudeh-blue?style=for-the-badge)](https://sinasotoudeh.ir)

**A production-grade, async bibliographic data scraping microservice**
targeting the National Library and Archives of Iran (NLAI / کتابخانه ملی ایران).

[📖 API Docs](#-api-reference) · [🚀 Quick Start](#-quick-start) · [🏗 Architecture](#-architecture-overview) · [📊 Monitoring](#-monitoring--observability)

</div>

---

## 📋 Table of Contents

1. [Project Overview](#-project-overview)
2. [Feature Highlights](#-feature-highlights)
3. [Architecture Overview](#-architecture-overview)
4. [Tech Stack](#-tech-stack)
5. [Repository Structure](#-repository-structure)
6. [Data Flow — End-to-End](#-data-flow--end-to-end)
7. [Infrastructure & Services](#-infrastructure--services)
8. [Configuration & Environment Variables](#-configuration--environment-variables)
9. [Quick Start](#-quick-start)
10. [API Reference](#-api-reference)
11. [Scraper Deep Dive](#-scraper-deep-dive)
12. [Task System (Celery)](#-task-system-celery)
13. [Database Layer](#-database-layer)
14. [Monitoring & Observability](#-monitoring--observability)
15. [Development Guide](#-development-guide)
16. [Architecture & Code Quality (Reviewer Section)](#-architecture--code-quality-reviewer-section)
17. [Author](#-author)

---

## 🎯 Project Overview

The **Bibliograph AI Scraper Service** is a standalone microservice within the larger
`bibliograph-ai` platform. Its sole responsibility is to **discover, extract, normalize,
and persist bibliographic records** (books, authors, metadata) from external library
catalogs — starting with the National Library and Archives of Iran
([opac.nlai.ir](https://opac.nlai.ir)).

The service exposes a **REST API** (FastAPI) for triggering and monitoring scrape jobs,
delegates all heavy lifting to **Celery workers** backed by RabbitMQ, and stores results
in **MongoDB**. It is fully containerized and ships with a complete observability stack.

---

## ✨ Feature Highlights

- 🕷️ **Async HTTP Scraper** — `httpx` + `BeautifulSoup` with session management (JSESSIONID),
  bulk-fetch strategy, and smart retry logic
- 🔄 **Resilient Error Handling** — distinguishes `NetworkConnectionError` vs
  `ServerResponseError` vs `ContentParsingError` with per-type recovery strategies
- 🔁 **Handshake Recovery Loop** — automatically re-establishes NLAI session after
  3 consecutive network failures without losing task state
- 📊 **Hierarchical Task Logging** — parent task + per-author child tasks logged in
  MongoDB with full lifecycle tracking (`PENDING → RUNNING → SUCCESS/FAILED`)
- ⚡ **Celery + RabbitMQ** — distributed async task execution with Flower dashboard
- 🗄️ **Polyglot Persistence** — MongoDB (books/logs), PostgreSQL (relational models),
  Redis (cache + Celery backend), Elasticsearch (search index)
- 📈 **Prometheus Metrics** — multiprocess-safe metrics exported from both API and
  Celery workers
- 🐳 **Fully Containerized** — Docker Compose for infrastructure, service, and debug modes
- 📝 **Structured Logging** — `structlog` with JSON output in production

---

## 🏗 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        bibliograph-network                          │
│                                                                     │
│  ┌──────────────┐   REST    ┌──────────────────────────────────┐    │
│  │   API Client │ ────────► │   scraper-api  (FastAPI :8082)   │    │
│  └──────────────┘           │                                  │    │
│                             │  /api/v1/scraper/start           │    │
│                             │  /api/v1/scraper/status/{id}     │    │
│                             │  /api/v1/books/*                 │    │
│                             │  /api/v1/health/*                │    │
│                             └──────────┬───────────────────────┘    │
│                                        │ enqueue task               │
│                                        ▼                            │
│                             ┌──────────────────┐                    │
│                             │  RabbitMQ :5672  │  (broker)          │
│                             └────────┬─────────┘                    │
│                                      │ consume                      │
│                             ┌────────▼─────────┐                    │
│                             │  celery-worker   │                    │
│                             │  scrape_nlai()   │                    │
│                             └──┬──────────┬────┘                    │
│                                │          │                         │
│              ┌─────────────────▼─┐   ┌───▼───────────────────┐      │
│              │  NLAIScraper      │   │  MongoDB :27017       │      │
│              │  (httpx + BS4)    │   │  • books collection   │      │
│              │                   │   │  • scraping_logs      │      │
│              │  opac.nlai.ir     │   │  • authors            │      │
│              └───────────────────┘   └───────────────────────┘      │
│                                                                     │
│  ┌────────────────┐  ┌───────────────┐  ┌──────────────────────┐    │
│  │  Redis :6379   │  │  PostgreSQL   │  │  Elasticsearch :9200 │    │
│  │  (cache+state) │  │  :5435        │  │  (search index)      │    │
│  └────────────────┘  └───────────────┘  └──────────────────────┘    │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Observability Stack                                         │   │
│  │  Prometheus :9090 │ Grafana :3001 │ Loki :3100 │ Flower :5555│   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 🧩 Architectural Patterns

| Pattern                        | Implementation                                                |
| ------------------------------ | ------------------------------------------------------------- |
| **Microservice**               | Isolated Docker service with its own DB connections           |
| **Repository Pattern**         | `BookRepository`, `ScrapingLogRepository`, `AuthorRepository` |
| **Dependency Injection**       | FastAPI `Depends()` wires DB clients into route handlers      |
| **Event-Driven (Async Tasks)** | Celery tasks triggered via API, tracked via MongoDB           |
| **Polyglot Persistence**       | Each storage technology used for its optimal purpose          |
| **Structured Logging**         | `structlog` with consistent key-value pairs across all layers |
| **Health-First Design**        | Per-service health endpoints for readiness/liveness probes    |

---

## 🛠 Tech Stack

| Category             | Technology                  | Role                                        |
| -------------------- | --------------------------- | ------------------------------------------- |
| **API Framework**    | FastAPI 0.109               | REST endpoints, lifespan management         |
| **Task Queue**       | Celery 5.3 + RabbitMQ       | Async scraping job execution                |
| **Primary Store**    | MongoDB + Motor 3.x         | Raw scraped data (async)                    |
| **Relational Store** | PostgreSQL + SQLAlchemy 2.0 | Structured metadata (async)                 |
| **Search Engine**    | Elasticsearch 8.x           | Author fuzzy matching + book search         |
| **Cache / Results**  | Redis + aioredis            | Celery result backend + key-value cache     |
| **Object Storage**   | MinIO                       | Book covers, PDFs, binary assets            |
| **Scraping**         | httpx + BeautifulSoup4      | HTTP requests + HTML parsing                |
| **NLP**              | hazm + difflib              | Persian text normalization + similarity     |
| **Logging**          | structlog                   | Structured JSON logs (prod) / colored (dev) |
| **Metrics**          | Prometheus client           | Request counters, duration histograms       |
| **Monitoring**       | Flower                      | Celery task dashboard                       |
| **Containerization** | Docker + Compose            | Multi-stage builds, service orchestration   |

---

## 📁 Repository Structure

```
scraper-service/
│
├── docker-compose.dev.yml          # Full infrastructure stack (DBs, monitoring)
├── docker-compose.scraper.yml      # Scraper service (api + worker + beat + flower)
├── docker-compose.scraper.debug.yml# Debug mode with remote debugger on port 5679
├── Dockerfile                      # Multi-stage build (dev + production)
├── pyproject.toml                  # Poetry + tool configs (black, ruff, mypy)
├── requirements.txt                # Python dependencies
│
└── src/
    ├── api/
    │   ├── main.py                 # FastAPI app entry point, lifespan, middleware
    │   ├── dependencies.py         # DI providers (DB clients, repositories)
    │   └── routes/
    │       ├── books.py            # CRUD endpoints for books (MongoDB)
    │       ├── health.py           # Health check endpoints (all services)
    │       └── scraper.py          # Scrape job control & status endpoints
    │
    ├── config/
    │   ├── settings.py             # Pydantic Settings — all env vars
    │   └── logging_config.py       # structlog configuration (dev/prod)
    │
    ├── core/
    │   └── database/
    │       ├── __init__.py         # DatabaseManager (connect/disconnect all)
    │       ├── postgres.py         # SQLAlchemy async client
    │       ├── mongodb.py          # Motor async client
    │       ├── redis_client.py     # aioredis client with key-prefix namespacing
    │       ├── elasticsearch.py    # Async Elasticsearch client
    │       └── minio_client.py     # MinIO object storage client
    │
    ├── models/
    │   ├── base.py                 # SQLAlchemy DeclarativeBase + mixins
    │   ├── book.py                 # Book ORM model (PostgreSQL)
    │   └── scraping_log.py         # ScrapingLog ORM model (PostgreSQL)
    │
    ├── repositories/
    │   ├── book_repo.py            # BookRepository — MongoDB CRUD
    │   ├── scraping_log_repo.py    # ScrapingLogRepository — MongoDB log ops
    │   └── author_repo.py          # AuthorRepository — MongoDB author range queries
    │
    ├── schemas/
    │   ├── book.py                 # Pydantic schemas: BookCreate/Update/Response
    │   └── scraper.py              # ScrapingStatsResponse schema
    │
    ├── scrapers/
    │   └── sources/
    │       └── nlai.py             # NLAIScraper — full NLAI OPAC scraping engine
    │
    ├── tasks/
    │   ├── celery_app.py           # Celery app config, Prometheus multiprocess setup
    │   └── scraping_tasks.py       # scrape_nlai() Celery task implementation
    ├── scripts/
    │   ├── author_linking_job/
    │   │   ├── run_job_latin.py         # ES fuzzy match for Latin author names
    │   │   ├── run_job_persian.py       # ES + difflib for Persian author names
    │   │   └── README.md
    │   ├── data_profiling/
    │   │   ├── run.py                   # Orchestrator
    │   │   ├── mongodb_profiler.py      # Field-level stats (recursive)
    │   │   ├── schema_validator.py      # Profile vs. Pydantic model comparison
    │   │   ├── relationship_checker.py  # Cross-collection integrity
    │   │   ├── data_quality_scorer.py   # Weighted 4-dimension scoring
    │   │   ├── stats_tracker.py         # Streaming stats (no full data in memory)
    │   │   └── README.md
    │   └──copy_collection.py           # MongoDB collection migration with validation
    │
    └── pipelines/                      # (Reserved for future ETL pipelines)
```

---

## 🔄 Data Flow — End-to-End

The complete lifecycle of a scrape job from API call to persisted data:

```
Step 1: API Request
───────────────────
POST /api/v1/scraper/start
Body: { "source": "nlai", "author_list": ["رضا براهنی"] }
        │
        ▼
Step 2: Route Handler (scraper.py)
────────────────────────────────────
Validates request → calls scrape_nlai.delay(author_list)
Returns: { "task_id": "abc-123", "status": "queued" }
        │
        ▼
Step 3: RabbitMQ (queue: "scraping")
─────────────────────────────────────
Task message serialized to JSON and enqueued
        │
        ▼
Step 4: Celery Worker picks up task
────────────────────────────────────
scrape_nlai(self, author_list, max_results)
  │
  ├─ Connects to MongoDB (MongoDBClient)
  ├─ Creates parent ScrapingLog entry (status=RUNNING)
  │
  └─ FOR EACH AUTHOR:
       │
       ├─ Creates child ScrapingLog (sub_task_id = f"{task_id}_{i}")
       │
       ├─ Step 5: NLAIScraper.fetch_by_author_name(author_name)
       │     │
       │     ├─ perform_handshake() → GET OPAC → acquire JSESSIONID
       │     ├─ POST search → get total result count
       │     ├─ POST resize page → get all record IDs
       │     ├─ POST SAVE_PRINT → bulk HTML with all records
       │     └─ parse_bulk_print_view() → List[Dict]
       │
       ├─ Step 6: Persist to MongoDB
       │     BookRepository.create(book_data) × N books
       │
       └─ Step 7: Update logs
             log_repo.update_progress(sub_task_id, SUCCESS)
             log_repo.update_progress(task_id, progress%)
             self.update_state(state="PROGRESS", meta={...})

Step 8: Client polls status
────────────────────────────
GET /api/v1/scraper/status/abc-123
Returns live progress, counts, current_author, etc.

Step 9: Completion
───────────────────
Parent log updated: status=SUCCESS, books_found=N, books_saved=M
Prometheus counters incremented
```

---

## 🐳 Infrastructure & Services

All infrastructure services are defined in `docker-compose.dev.yml`.
The scraper service itself is defined in `docker-compose.scraper.yml`.

### Service Port Map

| Service            | Container Name              | Host Port        | Purpose                 |
| ------------------ | --------------------------- | ---------------- | ----------------------- |
| **scraper-api**    | `bibliograph-scraper-api`   | `8082`           | FastAPI REST API        |
| **celery-worker**  | `bibliograph-celery-worker` | —                | Task execution          |
| **celery-beat**    | `bibliograph-celery-beat`   | —                | Scheduled tasks         |
| **flower**         | `bibliograph-flower`        | `5555`           | Celery monitoring UI    |
| **PostgreSQL**     | `bibliograph-postgres`      | `5435`           | Relational data         |
| **MongoDB**        | `bibliograph-mongodb`       | `27017`          | Books & logs            |
| **Redis**          | `bibliograph-redis`         | `6379`           | Cache & task backend    |
| **RabbitMQ**       | `bibliograph-rabbitmq`      | `5672` / `15672` | Task broker / UI        |
| **Elasticsearch**  | `bibliograph-elasticsearch` | `9200`           | Full-text search        |
| **MinIO**          | `bibliograph-minio`         | `9000` / `9001`  | Object storage          |
| **Prometheus**     | `bibliograph-prometheus`    | `9090`           | Metrics scraping        |
| **Grafana**        | `bibliograph-grafana`       | `3001`           | Dashboards              |
| **Loki**           | `bibliograph-loki`          | `3100`           | Log aggregation         |
| **Celery Metrics** | (worker process)            | `8001`           | Prometheus multiprocess |
| **Celery Debug**   | `bibliograph-celery-worker` | `5679`           | Remote debugger         |

> **Note:** In debug mode (`docker-compose.scraper.debug.yml`), the Celery worker
> exposes port `5679` for `debugpy` remote debugging (VS Code / PyCharm).

---

## ⚙️ Configuration & Environment Variables

All settings are managed through `src/config/settings.py` using **Pydantic Settings**.
Values are loaded from environment variables or a `.env` file at the project root.

### Setup

```bash
cp .env.example .env
# Edit .env with your values
```

### Complete Environment Variable Reference

#### 🗄️ PostgreSQL

| Variable                | Default                | Description          |
| ----------------------- | ---------------------- | -------------------- |
| `POSTGRES_HOST`         | `bibliograph-postgres` | DB host              |
| `POSTGRES_PORT`         | `5435`                 | DB port              |
| `POSTGRES_USER`         | `bibliograph`          | DB user              |
| `POSTGRES_PASSWORD`     | _(required)_           | DB password          |
| `POSTGRES_DB`           | `bibliograph_db`       | Database name        |
| `POSTGRES_POOL_SIZE`    | `10`                   | Connection pool size |
| `POSTGRES_MAX_OVERFLOW` | `20`                   | Pool overflow limit  |

#### 🍃 MongoDB

| Variable              | Default               | Description   |
| --------------------- | --------------------- | ------------- |
| `MONGODB_HOST`        | `bibliograph-mongodb` | Host          |
| `MONGODB_PORT`        | `27017`               | Port          |
| `MONGODB_USER`        | `bibliograph`         | User          |
| `MONGODB_PASSWORD`    | _(required)_          | Password      |
| `MONGODB_DATABASE`    | `bibliograph_db`      | Database name |
| `MONGODB_AUTH_SOURCE` | `admin`               | Auth database |

#### 🔴 Redis

| Variable                | Default             | Description            |
| ----------------------- | ------------------- | ---------------------- |
| `REDIS_HOST`            | `bibliograph-redis` | Host                   |
| `REDIS_PORT`            | `6379`              | Port                   |
| `REDIS_PASSWORD`        | _(optional)_        | Password               |
| `REDIS_DB`              | `0`                 | Database index (cache) |
| `REDIS_MAX_CONNECTIONS` | `20`                | Connection pool size   |

#### 🐰 RabbitMQ

| Variable            | Default                | Description  |
| ------------------- | ---------------------- | ------------ |
| `RABBITMQ_HOST`     | `bibliograph-rabbitmq` | Host         |
| `RABBITMQ_PORT`     | `5672`                 | AMQP port    |
| `RABBITMQ_USER`     | `bibliograph`          | User         |
| `RABBITMQ_PASSWORD` | _(required)_           | Password     |
| `RABBITMQ_VHOST`    | `/`                    | Virtual host |

#### ⚙️ Celery

| Variable                | Default                                 | Description       |
| ----------------------- | --------------------------------------- | ----------------- |
| `CELERY_BROKER_URL`     | `amqp://...@bibliograph-rabbitmq:5672/` | Broker connection |
| `CELERY_RESULT_BACKEND` | `redis://bibliograph-redis:6379/1`      | Result storage    |

#### 🔍 Elasticsearch

| Variable                 | Default                     | Description |
| ------------------------ | --------------------------- | ----------- |
| `ELASTICSEARCH_HOST`     | `bibliograph-elasticsearch` | Host        |
| `ELASTICSEARCH_PORT`     | `9200`                      | Port        |
| `ELASTICSEARCH_USER`     | `elastic`                   | User        |
| `ELASTICSEARCH_PASSWORD` | _(required)_                | Password    |

#### 🪣 MinIO

| Variable           | Default                  | Description            |
| ------------------ | ------------------------ | ---------------------- |
| `MINIO_ENDPOINT`   | `bibliograph-minio:9000` | S3-compatible endpoint |
| `MINIO_ACCESS_KEY` | _(required)_             | Access key             |
| `MINIO_SECRET_KEY` | _(required)_             | Secret key             |
| `MINIO_BUCKET`     | `bibliograph`            | Default bucket         |

#### 🔧 Application

| Variable              | Default       | Description                   |
| --------------------- | ------------- | ----------------------------- |
| `APP_ENV`             | `development` | `development` or `production` |
| `APP_HOST`            | `0.0.0.0`     | API bind host                 |
| `APP_PORT`            | `8082`        | API bind port                 |
| `LOG_LEVEL`           | `INFO`        | Logging verbosity             |
| `SCRAPER_MAX_RESULTS` | `500`         | Default per-author result cap |

---

## 🚀 Quick Start

### Prerequisites

- Docker ≥ 24.x
- Docker Compose ≥ 2.x
- (Optional) Python 3.11+ for local development
- A running instance of the shared infrastructure stack (MongoDB, PostgreSQL, Redis, RabbitMQ, Elasticsearch, MinIO)

> The shared infrastructure is defined in `../../infrastructure/docker/docker-compose.dev.yml`.

### 1. Start the Infrastructure

```bash

# Create the shared Docker network
docker network create bibliograph-network

# Start all backing services (DBs, broker, monitoring)
docker compose -f docker-compose.dev.yml up -d

# Verify all services are healthy
docker compose -f docker-compose.dev.yml ps
```

### 2. Start the Scraper Service

```bash
# Normal mode
docker compose -f docker-compose.scraper.yml up -d

# OR — Debug mode (exposes port 5679 for remote debugger)
docker compose -f docker-compose.scraper.debug.yml up -d
```

### 3. Verify Everything is Running

```bash
# API health check
curl http://localhost:8082/api/v1/health

# Flower (Celery monitoring)
open http://localhost:5555

# RabbitMQ Management UI
open http://localhost:15672  # user: bibliograph

# Grafana Dashboards
open http://localhost:3001   # user: admin
```

### 4. Trigger Your First Scrape

```bash
curl -X POST http://localhost:8082/api/v1/scraper/start \
  -H "Content-Type: application/json" \
  -d '{
    "source": "nlai",
    "author_list": ["رضا براهنی"],
    "max_results": 50
  }'
```

### 5. Monitor Progress

```bash
# Replace TASK_ID with the id returned above
curl http://localhost:8082/api/v1/scraper/status/TASK_ID
```

---

## 📡 API Reference

**Base URL:** `http://localhost:8082`
**Interactive Docs:** `http://localhost:8082/docs` (Swagger UI)
**ReDoc:** `http://localhost:8082/redoc`

---

### 🏥 Health Endpoints

#### `GET /api/v1/health`

Returns aggregated health status of all connected services.

**Response `200 OK`:**

```json
{
  "status": "healthy",
  "timestamp": "2026-04-15T10:30:00Z",
  "services": {
    "mongodb": { "status": "connected", "healthy": true },
    "postgres": { "status": "connected", "healthy": true },
    "redis": { "status": "connected", "healthy": true, "latency_ms": 0.82 },
    "elasticsearch": { "status": "connected", "healthy": true }
  }
}
```

#### `GET /api/v1/health/{service}`

Check health of a specific service. `service` can be:
`mongodb` | `postgres` | `redis` | `elasticsearch`

**Response `200 OK` (Redis example):**

```json
{
  "status": "connected",
  "healthy": true,
  "version": "7.2.0",
  "latency_ms": 0.82,
  "connected_clients": 5,
  "used_memory_mb": 12.4,
  "uptime_days": 3.2
}
```

---

### 🕷️ Scraper Endpoints

#### `POST /api/v1/scraper/start`

Enqueue a new scraping job.

**Request Body:**

```json
{
  "source": "nlai",
  "author_list": ["رضا براهنی", "احمد شاملو"],
  "max_results": 100
}
```

| Field         | Type            | Required | Description                                             |
| ------------- | --------------- | -------- | ------------------------------------------------------- |
| `source`      | `string`        | ✅       | Scraping source. Currently only `"nlai"`                |
| `author_list` | `array[string]` | ✅       | List of author names **OR** range string `["100to200"]` |
| `max_results` | `integer`       | ❌       | Per-author result cap. Omit for unlimited               |

**Range Mode** — scrape authors by database index range:

```json
{
  "source": "nlai",
  "author_list": ["100to200"],
  "max_results": 500
}
```

> This fetches authors with `author_index_number` between 100 and 200 from MongoDB
> `authors` collection and uses their stored `params` payloads for precision searching.

**Response `202 Accepted`:**

```json
{
  "task_id": "3f7a8b2c-1d4e-4f9a-8b3c-2e1f5a6d7890",
  "status": "queued",
  "source": "nlai",
  "author_count": 2,
  "message": "Scraping task enqueued successfully"
}
```

---

#### `GET /api/v1/scraper/status/{task_id}`

Get live status and progress of a running or completed task.

**Path Parameter:** `task_id` — UUID returned from the start endpoint.

**Response `200 OK` (task in progress):**

```json
{
  "task_id": "3f7a8b2c-1d4e-4f9a-8b3c-2e1f5a6d7890",
  "status": "RUNNING",
  "progress": 45.5,
  "current_author": "Processing: احمد شاملو (Idx: 12)",
  "current_author_index": 12,
  "books_found": 320,
  "books_saved": 318,
  "failed_authors_count": 1,
  "skipped_authors_count": 0,
  "failed_authors_ids": [
    {
      "index": 7,
      "name": "محمد مختاری",
      "reason": "network: Connection refused"
    }
  ],
  "skipped_authors_ids": [],
  "started_at": "2026-04-15T10:30:00Z",
  "updated_at": "2026-04-15T10:35:22Z"
}
```

**Response `200 OK` (completed):**

```json
{
  "task_id": "3f7a8b2c-1d4e-4f9a-8b3c-2e1f5a6d7890",
  "status": "SUCCESS",
  "progress": 100.0,
  "books_found": 712,
  "books_saved": 708,
  "failed_authors_count": 1,
  "skipped_authors_count": 2,
  "started_at": "2026-04-15T10:30:00Z",
  "completed_at": "2026-04-15T10:52:10Z"
}
```

---

#### `GET /api/v1/scraper/stats`

Returns aggregated scraping statistics across all completed tasks.

**Query Parameters:**

| Parameter | Type     | Default | Description      |
| --------- | -------- | ------- | ---------------- |
| `source`  | `string` | `nlai`  | Filter by source |

**Response `200 OK`:**

```json
{
  "source": "nlai",
  "total_books_scraped": 125430,
  "total_tasks": 48,
  "success_tasks": 45,
  "failed_tasks": 3,
  "avg_duration_seconds": 842.5,
  "avg_success_rate": 97.3,
  "last_run": "2026-04-15T10:52:10Z"
}
```

---

#### `GET /api/v1/scraper/sources`

List all available scraping sources.

**Response `200 OK`:**

```json
{
  "sources": [
    {
      "id": "nlai",
      "name": "National Library and Archives of Iran",
      "url": "https://opac.nlai.ir",
      "status": "active"
    }
  ]
}
```

---

### 📚 Books Endpoints

#### `GET /api/v1/books`

Paginated list of all scraped books from MongoDB.

**Query Parameters:**

| Parameter  | Type      | Default | Description                                |
| ---------- | --------- | ------- | ------------------------------------------ |
| `skip`     | `integer` | `0`     | Number of records to skip                  |
| `limit`    | `integer` | `10`    | Max records to return (max: 100)           |
| `language` | `string`  | —       | Filter by language code (`fa`, `en`, `ar`) |
| `source`   | `string`  | —       | Filter by scrape source                    |

**Response `200 OK`:**

```json
{
  "total": 125430,
  "skip": 0,
  "limit": 10,
  "books": [
    {
      "_id": "6642a1f3e4b0c8d9f1234567",
      "title": "آواز کشتگان",
      "authors": ["احمد شاملو"],
      "isbn": "9789641234567",
      "publisher": "نگاه",
      "published_date": "1379",
      "language": "fa",
      "description": "...",
      "page_count": 312,
      "categories": ["شعر", "ادبیات فارسی"],
      "cover_url": null,
      "source_url": "https://opac.nlai.ir/opac-prod/bibliographic/12345",
      "nlai_id": "12345",
      "nlai_permalink": "https://opac.nlai.ir/opac-prod/bibliographic/12345",
      "created_at": "2026-04-15T10:35:00Z",
      "updated_at": "2026-04-15T10:35:00Z"
    }
  ]
}
```

---

#### `POST /api/v1/books`

Manually create a book record.

**Request Body (`BookCreate`):**

```json
{
  "title": "بوف کور",
  "authors": ["صادق هدایت"],
  "isbn": "9789641234568",
  "publisher": "جاویدان",
  "published_date": "1315",
  "language": "fa",
  "description": "رمان کلاسیک فارسی",
  "page_count": 128,
  "categories": ["رمان", "ادبیات فارسی"],
  "source_url": "https://opac.nlai.ir/..."
}
```

**Response `201 Created`:** Returns created `BookResponse` object.

---

#### `GET /api/v1/books/{book_id}`

Retrieve a single book by MongoDB ObjectId.

**Response `200 OK`:** Returns `BookResponse` object.
**Response `404 Not Found`:**

```json
{ "detail": "Book not found" }
```

---

#### `PUT /api/v1/books/{book_id}`

Update an existing book (partial update supported).

**Request Body (`BookUpdate`):** All fields optional.

---

#### `DELETE /api/v1/books/{book_id}`

Delete a book by ID.

**Response `204 No Content`**

---

#### `GET /api/v1/books/isbn/{isbn}`

Look up a book by its ISBN-10 or ISBN-13.

**Response `200 OK`:** Returns `BookResponse` or `404`.

---

### 🔧 System Endpoints

#### `GET /`

Service info and version.

**Response `200 OK`:**

```json
{
  "service": "bibliograph-scraper",
  "version": "1.0.0",
  "status": "running",
  "environment": "development"
}
```

#### `GET /metrics_raw`

Raw Prometheus metrics in text exposition format.
Used by Prometheus scraper (not for direct human consumption).

---

## 🕷️ Scraper Deep Dive

### NLAIScraper — `src/scrapers/sources/nlai.py`

The scraper implements a **5-phase bulk extraction strategy** against
the NLAI OPAC system:

```
Phase 1: Handshake
──────────────────
GET /search/bibliographicAdvancedSearch.do?command=NEW_SEARCH
→ Acquires JSESSIONID cookie required for all subsequent requests

Phase 2: Search Submission
───────────────────────────
POST /search/bibliographicAdvancedSearchProcess.do;jsessionid=X
Body: { author_name, search_params... }
→ Returns result page with total record count

Phase 3: Page Resize
─────────────────────
POST /search/briefListSearch.do?command=BRIEF_LIST_SETUP
Body: { pageSize: total_count, pageNum: 1 }
→ Loads ALL results in a single page
→ Also extracts NLAI record IDs from href attributes

Phase 4: Bulk Print Fetch
──────────────────────────
POST /search/briefListSearch.do?command=SAVE_PRINT
→ Returns full bibliographic detail for ALL records in one HTML response

Phase 5: Parse & Normalize
───────────────────────────
_parse_bulk_print_view(html)
→ Extracts structured data from <table id="printTable">
→ Maps Persian field labels to English keys via FIELD_TRANSLATION
→ Merges NLAI IDs and permalinks
→ Returns List[Dict[str, Any]]
```

### Field Mapping

The scraper translates Persian bibliographic field names to English keys:

| Persian Label         | English Key            | Description                        |
| --------------------- | ---------------------- | ---------------------------------- |
| `شابک`                | `isbn`                 | ISBN                               |
| `عنوان و نام پديدآور` | `title_statement`      | Title & author statement           |
| `سرشناسه`             | `main_entry`           | Main entry (primary author)        |
| `مشخصات نشر`          | `publication`          | Publication details                |
| `مشخصات ظاهری`        | `physical_description` | Physical description               |
| `موضوع`               | `subjects`             | Subject headings                   |
| `رده بندی کنگره`      | `lcc`                  | Library of Congress Classification |
| `رده بندی دیویی`      | `ddc`                  | Dewey Decimal Classification       |
| `شماره کتابشناسی ملی` | `nli_number`           | National Library number            |
| `خلاصه`               | `abstract`             | Abstract/summary                   |

### Error Handling Strategy

```
Exception Type          │ Cause                    │ Recovery
────────────────────────┼──────────────────────────┼──────────────────────────────
NetworkConnectionError  │ DNS fail, no internet,   │ Log + skip author.
                        │ connection refused       │ After 3 consecutive:
                        │                          │ → Enter handshake loop
                        │                          │   (retry every 5s until OK)
────────────────────────┼──────────────────────────┼──────────────────────────────
ServerResponseError     │ HTTP 5xx, 429, max       │ Log + skip author.
                        │ retries exhausted        │ After 3 consecutive:
                        │                          │ → STOP task entirely
────────────────────────┼──────────────────────────┼──────────────────────────────
ContentParsingError     │ 200 OK but no result     │ Log + skip author.
                        │ count found in HTML      │ Counted as server error
────────────────────────┼──────────────────────────┼──────────────────────────────
MaxResultsLimitExceeded │ Author has more results  │ Log as SKIPPED.
                        │ than configured limit    │ Continue next author
────────────────────────┼──────────────────────────┼──────────────────────────────
Exception (generic)     │ Unexpected runtime error │ Log + skip author.
                        │                          │ Task continues
```

### Retry Logic (`_safe_request`)

Every HTTP request goes through `_safe_request` with:

- **3 max retries**
- **Random jitter delay** (`0.5s–1.5s`) before each request (polite crawling)
- **429 handling:** exponential backoff `(attempt+1) × 10s`
- **5xx handling:** fixed `10s` wait between retries
- **Network errors:** `2s` backoff, raises `NetworkConnectionError` after exhaustion

---

## ⚙️ Task System (Celery)

### Configuration — `src/tasks/celery_app.py`

```python
# Key settings
task_serializer       = "json"
task_time_limit       = 3000 * 60        # 50 hours max (large scrape jobs)
worker_prefetch_multiplier = 1           # One task at a time per worker
worker_max_tasks_per_child = 1000        # Recycle worker after 1000 tasks
task_track_started    = True             # Track STARTED state in backend
worker_send_task_events = True           # Enable Flower monitoring
```

**Task Route:**

src.tasks.scraping_tasks.\* → queue: "scraping"

### `scrape_nlai` Task — `src/tasks/scraping_tasks.py`

```python
@shared_task(bind=True, autoretry_for=())
def scrape_nlai(self, author_list: list[str], max_results: Optional[int] = None) -> dict
```

**Input Modes:**

| Mode            | `author_list` Example | Behavior                                                        |
| --------------- | --------------------- | --------------------------------------------------------------- |
| **Name List**   | `["شاملو", "براهنی"]` | Searches by author name directly                                |
| **Range Mode**  | `["100to200"]`        | Fetches authors from MongoDB by index range, uses stored params |
| **Single Name** | `["رضا براهنی"]`      | Same as name list with 1 item                                   |

**Return Value:**

```python
# Success
{"status": "completed", "found": 712, "skipped": 2, "failed": 1}

# Stopped by server errors
{"status": "stopped", "reason": "server_error"}

# Empty result (valid)
{"status": "completed_empty"}
```

### Task State Updates

The task calls `self.update_state()` at each iteration:

```python
self.update_state(
    state="PROGRESS",
    meta={
        "progress": 45.5,          # float, 0–100
        "books_found": 320,
        "books_saved": 318,
        "failed_authors_count": 1,
        "skipped_authors_count": 0,
        "failed_authors_ids": [...],
        "skipped_authors_ids": [...]
    }
)
```

This is readable via `AsyncResult(task_id).info` and exposed by the status endpoint.

### Prometheus Metrics (Worker)

| Metric                                  | Type    | Description                              |
| --------------------------------------- | ------- | ---------------------------------------- |
| `nlai_scrape_inserted_total`            | Counter | Total books inserted across all tasks    |
| `nlai_scrape_errors_total`              | Counter | Total error events                       |
| `nlai_scrape_skipped_authors`           | Counter | Authors skipped due to `MaxResultsLimit` |
| `nlai_scrape_progress_percent{task_id}` | Gauge   | Current progress % per task              |

> **Multiprocess Safety:** Metrics are stored in `/tmp/prometheus_multiproc` and
> aggregated via `MultiProcessCollector` — safe for multi-worker deployments.

---

## 🗄️ Database Layer

### Dual Storage Strategy

A deliberate architectural choice separates concerns across two databases:

| Store          | Purpose                                             | Client           |
| -------------- | --------------------------------------------------- | ---------------- |
| **MongoDB**    | Raw scraped documents, scraping logs, author links  | Motor (async)    |
| **PostgreSQL** | Normalized book/author entities, relational queries | SQLAlchemy async |

Raw scraped documents are written to **MongoDB** at ingestion speed with no schema enforcement. A separate normalization pipeline populates **PostgreSQL** with validated, relational data. This avoids blocking the scraping pipeline on schema validation while still providing a clean relational model for downstream consumers.

---

### MongoDB Collections

#### `books`

Primary storage for all scraped bibliographic records.

**Indexes:**

```
isbn          (unique)    — fast ISBN lookup
title         (single)    — title search
author+title  (compound)  — author+title compound queries
created_at    (single)    — time-based pagination
```

**Document Schema:**

```json
{
  "_id": "ObjectId",
  "title": "string",
  "authors": ["string"],
  "isbn": "string (optional)",
  "publisher": "string",
  "published_date": "string",
  "language": "fa|en|ar",
  "description": "string",
  "page_count": "integer",
  "categories": ["string"],
  "source": "nlai",
  "source_url": "string",
  "nlai_id": "string",
  "nlai_permalink": "string",
  "author_index_number": "integer",
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

#### `scraping_logs`

Tracks every scraping task lifecycle.

**Document Schema:**

```json
{
  "_id": "ObjectId",
  "task_id": "string (unique)",
  "parent_task_id": "string (for child logs)",
  "is_parent": "boolean",
  "source": "nlai",
  "status": "PENDING|RUNNING|SUCCESS|FAILED|RETRYING|STOPPED",
  "current_author": "string",
  "current_author_index": "integer",
  "books_found": "integer",
  "books_saved": "integer",
  "failed_authors_count": "integer",
  "skipped_authors_count": "integer",
  "failed_authors_ids": [{ "index": 0, "name": "...", "reason": "..." }],
  "skipped_authors_ids": [{ "index": 0, "name": "...", "found": 0 }],
  "progress": "float (0-100)",
  "error_message": "string",
  "started_at": "ISODate",
  "completed_at": "ISODate",
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

#### `authors`

Stores known authors with their NLAI search parameters.
Used in **range mode** scraping.

```json
{
  "_id": "ObjectId",
  "author_name": "string",
  "author_index_number": "integer",
  "params": { "...": "NLAI search payload" },
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

### Redis Key Namespacing

The `RedisClient` uses prefixed keys to avoid collisions:

bibliograph:cache:<key> — Application cache (TTL-based)
bibliograph:celery:<key> — Celery-related keys

### PostgreSQL Models

While MongoDB is the primary store, SQLAlchemy ORM models exist for
relational use cases:

| Model         | Table           | Purpose                                                          |
| ------------- | --------------- | ---------------------------------------------------------------- |
| `Book`        | `books`         | Relational book store with enum types                            |
| `ScrapingLog` | `scraping_logs` | Audit log with computed `duration` and `success_rate` properties |

Both models inherit from `TimestampMixin` (`created_at`, `updated_at`)
and `Book` additionally inherits `SoftDeleteMixin` (`deleted_at`).

---

## 📊 Monitoring & Observability

### Prometheus Scrape Targets

Add these to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: "scraper-api"
    static_configs:
      - targets: ["bibliograph-scraper-api:8082"]
    metrics_path: "/metrics_raw"

  - job_name: "celery-worker"
    static_configs:
      - targets: ["bibliograph-celery-worker:8001"]
```

### Grafana

Access at `http://localhost:3001` (default: `admin/admin`).

Recommended dashboards to import:

- **Celery Worker Dashboard** — task rates, error rates, queue depth
- **FastAPI Dashboard** — request latency, error rates
- **MongoDB Dashboard** — operations/sec, connection pool
- **Redis Dashboard** — memory usage, hit/miss ratio

### Loki + Promtail

All container logs are shipped to Loki via Promtail.
Query in Grafana using LogQL:

```logql
# All scraper service logs
{container_name="bibliograph-scraper-api"}

# Only errors
{container_name="bibliograph-celery-worker"} |= "ERROR"

# Track specific task
{container_name="bibliograph-celery-worker"} |= "3f7a8b2c"
```

### Flower — Celery Monitoring

Access at `http://localhost:5555`

Provides real-time visibility into:

- Active, reserved, and completed tasks
- Worker status and resource usage
- Task result inspection
- Queue depth monitoring

---

## 🛠️ Development Guide

### Local Python Setup (without Docker)

```bash
# 1. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start infrastructure only
docker compose -f docker-compose.dev.yml up -d

# 4. Configure environment
cp .env.example .env
# Set POSTGRES_HOST=localhost, MONGODB_HOST=localhost etc.

# 5. Run API
uvicorn src.api.main:app --host 0.0.0.0 --port 8082 --reload

# 6. Run Celery worker (separate terminal)
celery -A src.tasks.celery_app worker -Q scraping --loglevel=info

# 7. Run Celery beat (separate terminal)
celery -A src.tasks.celery_app beat --loglevel=info
```

### Debug Mode

A dedicated debug compose file launches the Celery worker with **debugpy** attached, waiting for a remote debugger connection before starting:

```bash
docker-compose -f docker-compose.scraper.debug.yml up --build

Connect your IDE to `localhost:5679` (Python remote attach).
```

> Debug mode uses `--pool=solo --concurrency=1` to ensure single-threaded execution compatible with debugger breakpoints.

### Running Tests

```bash

# From inside the container or with Poetry

pytest --cov=src --cov-report=html
```

Test configuration in `pyproject.toml`:

- Framework: `pytest` + `pytest-asyncio`
- Coverage: `pytest-cov` with HTML report
- Mocking: `pytest-mock` + `vcrpy` for HTTP cassettes
- Data generation: `faker` + `hypothesis`

### Code Quality

```bash

# Format

black src/ --line-length 100

# Lint

ruff check src/

# Type check

mypy src/
```

### Hot Reload (Development)

The development compose target mounts `./src` as a volume and runs uvicorn with `--reload`, so code changes are reflected immediately without rebuilding the container.

### Adding a New Scraper Source

1. Create `src/scrapers/sources/{source_name}.py`
2. Implement your scraper class with at minimum:
   ```python
   async def fetch_by_author_name(self, name: str, max_results=None) -> List[Dict]
   async def close(self) -> None
   ```
3. Add source to `scraper.py` route's source registry
4. Update `scraping_tasks.py` to handle the new source
5. Add source entry to `GET /api/v1/scraper/sources`

### Running Tests

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests (requires running infrastructure)
pytest tests/integration/ -v --env=test

# With coverage
pytest --cov=src --cov-report=html
```

---

## 🔬 Architecture & Code Quality (Reviewer Section)

_This section is written for engineering leads, senior developers, and technical
reviewers evaluating the codebase._

### Design Principles Applied

#### 1. Single Responsibility Principle

Each module has one clear job:

- `NLAIScraper` — only knows how to talk to NLAI OPAC
- `BookRepository` — only knows how to persist/query books in MongoDB
- `scrape_nlai` task — orchestrates the scraping pipeline; delegates to scraper + repos
- `DatabaseManager` — only manages connection lifecycle

#### 2. Repository Pattern

All database interactions are encapsulated in repository classes.
Route handlers never touch database drivers directly — they receive repository
instances via **FastAPI's Dependency Injection** system (`src/api/dependencies.py`).
This makes every route handler independently unit-testable with mocked repositories.

#### 3. Lifespan-Managed Database Connections

All five database clients are initialized in FastAPI's `lifespan` context manager and stored on `app.state`. Dependencies retrieve them via `request.app.state`, ensuring:

- A single connection pool per process
- Clean shutdown on SIGTERM
- No global state or module-level singletons in the request path

#### 4. Layered Error Classification

The scraper defines a strict exception hierarchy:

```
Exception
├── MaxResultsLimitExceeded   — business rule violation (not an error)
├── NetworkConnectionError    — infrastructure problem (retry/recover)
├── ServerResponseError       — remote server problem (back-off/stop)
└── ContentParsingError       — data contract violation (skip/log)
```

Each exception type triggers a different recovery path in the task layer,
preventing unnecessary task failures and enabling intelligent retry behavior.

#### 5. Async-First Design

- FastAPI routes: fully async
- Database clients: Motor (MongoDB async), aioredis, async SQLAlchemy
- Scraper: `httpx.AsyncClient` throughout
- Celery tasks: execute async coroutines via `asyncio.run()`

#### 6. Structured Logging

Every significant event is logged as a key-value structured event:
python
logger.info("book_created", book_id=str(id), isbn=isbn, title=title)
This makes logs machine-parseable, directly queryable in Loki/Grafana,
and trivially filterable by any field.

#### 7. Configuration as Code

`Pydantic Settings` provides:

- Type validation of all environment variables at startup
- Auto-construction of connection URLs from individual components
- A single source of truth — no scattered `os.getenv()` calls

#### 8. Observability by Design

Prometheus metrics are not an afterthought — they are instrumented directly
in the task code at the point where state changes (`Counter.inc()` on insert,
`Gauge.set()` on progress). The multiprocess-safe setup ensures metrics
are correctly aggregated across multiple Celery workers.

### Identified Technical Considerations

> The following notes reflect honest observations for a production hardening review:

- **`asyncio.run()` in Celery tasks** — The current pattern of calling
  `asyncio.run(_run_scraping())` inside a synchronous Celery task is functional
  but creates a new event loop per task execution. For high-throughput scenarios,
  consider using `celery-pool-asyncio` or structuring workers with a persistent
  event loop.

- **MongoDB as primary scraping log store** — Using MongoDB for `scraping_logs`
  provides schema flexibility during development. For production reporting,
  consider mirroring finalized logs to PostgreSQL for complex analytical queries.

- **`DuplicateBookError` silent handling** — In `scraping_tasks.py`, duplicate
  books are caught implicitly (the `create()` call raises `DuplicateBookError`
  which falls through to the generic `Exception` handler). An explicit
  `except DuplicateBookError: pass` with a dedicated metric would improve
  observability.

- **`verify=False` in httpx client** — SSL verification is disabled for the NLAI
  OPAC. This is likely required due to the target server's certificate chain.
  This is acceptable for a known internal scraping target but should be documented
  as a conscious security trade-off.

---

## 👨‍💻 Author

<div align="center">

**Sina Sotoudeh**

_Backend Engineer · Python · Distributed Systems · Data Engineering_

[![Website](https://img.shields.io/badge/Website-sinasotoudeh.ir-0A66C2?style=for-the-badge&logo=safari&logoColor=white)](https://sinasotoudeh.ir)
[![GitHub](https://img.shields.io/badge/GitHub-sinasotoudeh-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/sinasotoudeh)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-sinasotoudeh-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://linkedin.com/in/sinasotoudeh)
[![Email](https://img.shields.io/badge/Email-s.sotoudeh1%40gmail.com-EA4335?style=for-the-badge&logo=gmail&logoColor=white)](mailto:s.sotoudeh1@gmail.com)

</div>

---

<div align="center">

_Part of the **Bibliograph AI** platform — an intelligent bibliographic data
aggregation and analysis system._

**⭐ If this project was useful, consider giving it a star.**

</div>
