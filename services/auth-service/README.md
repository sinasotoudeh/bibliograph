# 🔐 Auth Service

[![Go Version](https://img.shields.io/badge/Go-1.21-00ADD8?style=flat-square&logo=go)](https://golang.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?style=flat-square&logo=postgresql)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat-square&logo=redis)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat-square&logo=docker)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Author](https://img.shields.io/badge/Author-Sina%20Sotoudeh-blueviolet?style=flat-square)](https://sinasotoudeh.ir)

A production-ready **JWT-based authentication microservice** built with Go, designed as part of the [Bibliograph AI](https://github.com/sinasotoudeh/bibliograph-ai) platform. Handles user registration, login, session management, and role-based access control with a clean layered architecture.

---

## 📑 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Project Structure](#-project-structure)
- [Domain Model](#-domain-model)
- [API Reference](#-api-reference)
- [Configuration](#-configuration)
- [Getting Started](#-getting-started)
- [Running Migrations](#-running-migrations)
- [Middleware Stack](#-middleware-stack)
- [Design Decisions](#-design-decisions)
- [Author](#-author)

---

## ✨ Features

- 🔑 JWT access & refresh token pair (HS256, configurable expiry)
- 👤 Role-based user model: `researcher`, `translator`, `publisher`, `student`, `admin`
- 💳 Subscription tiers: `free`, `basic`, `premium`, `research`
- 🔄 Session management with refresh token rotation
- 🛡️ bcrypt password hashing (cost factor 12)
- 🚦 In-memory rate limiting (per-IP and per-user)
- 🌐 Configurable CORS middleware
- 📋 Structured logging via `go.uber.org/zap`
- 🐳 Multi-stage Docker build with non-root user
- ⚡ Graceful shutdown with configurable timeout
- 🔁 Auto-migration via GORM on startup

---

## 🏛️ Architecture

The service follows a **clean layered architecture** with strict dependency direction:

```
HTTP Request
     │
     ▼
┌─────────────┐
│   Router    │  gorilla/mux — route definitions & auth middleware injection
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Handler   │  Decode → Validate → Delegate → Respond
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Service   │  Business logic, JWT generation, password hashing
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Repository  │  GORM-backed data access (UserRepository, SessionRepository)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  PostgreSQL │
└─────────────┘
```

Each layer communicates only through **interfaces**, making every component independently testable and swappable.

---

## 📁 Project Structure

```
auth-service/
├── cmd/
│   ├── main.go                  # Entry point — wires all dependencies
│   └── migrate/
│       └── migrate.go           # Standalone migration runner
├── config/
│   └── config.go                # Top-level config loader (used by pkg/database)
├── docker/
│   ├── Dockerfile               # Multi-stage build
│   └── docker-compose.yml       # Full dev stack (Postgres, Redis, Mongo, RabbitMQ, MinIO)
├── internal/
│   ├── config/
│   │   └── config.go            # Env-based config structs & loader
│   ├── database/
│   │   └── database.go          # GORM connection + AutoMigrate (internal use)
│   ├── domain/
│   │   ├── user.go              # User entity, UserRole, SubscriptionTier
│   │   ├── session.go           # Session entity
│   │   ├── account.go           # OAuth account entity
│   │   ├── token.go             # TokenPair value object
│   │   └── JWT.go               # Claims struct (jwt.RegisteredClaims embedded)
│   ├── dto/
│   │   ├── auth_dto.go          # Register/Login/Refresh/ChangePassword request & response
│   │   ├── user_dto.go          # UserResponse, SessionResponse, UpgradeSubscriptionRequest
│   │   ├── missing.go           # AuthResponse, UpdateUserRequest
│   │   └── response.go          # Generic APIResponse, ErrorInfo, helper constructors
│   ├── handler/
│   │   ├── auth_handler.go      # Register, Login, RefreshToken, Logout, ChangePassword
│   │   ├── user_handler.go      # GetProfile, UpdateProfile, GetSessions, UpgradeSubscription
│   │   ├── health_handler.go    # /health and /ready endpoints
│   │   └── response.go          # Shared HTTP response helpers
│   ├── middleware/
│   │   ├── auth_middleware.go   # JWT validation, context injection (user_id, email, role)
│   │   ├── cors.go              # Configurable CORS
│   │   ├── logger.go            # HTTP request logger
│   │   ├── rate_limit.go        # Sliding-window in-memory rate limiter
│   │   └── recovery.go          # Panic recovery → 500 JSON response
│   ├── repository/              # GORM implementations of UserRepository & SessionRepository
│   ├── router/
│   │   └── router.go            # Route registration & authenticateMiddleware
│   ├── service/
│   │   ├── interface.go         # AuthService & UserService interfaces
│   │   ├── auth_service.go      # Register, Login, RefreshToken, Logout, ChangePassword
│   │   ├── user_service.go      # GetUserByID, UpdateUser, DeleteUser
│   │   └── jwt_helper.go        # JWTHelper interface + HS256 implementation
│   └── utils/
│       └── hash.go              # bcrypt wrapper (cost 12)
└── pkg/
    ├── database/
    │   ├── database.go          # Shared GORM connect, pool config, HealthCheck, Close
    │   ├── postgres.go          # PostgresDB wrapper with pool defaults
    │   └── redis.go             # RedisClient wrapper (go-redis v8)
    └── logger/
        └── ...                  # Zap logger initializer
```

---

## 🗄️ Domain Model

### User

| Field                 | Type           | Notes                         |
| --------------------- | -------------- | ----------------------------- |
| `id`                  | `uuid`         | Primary key, auto-generated   |
| `name`                | `varchar(255)` | Required                      |
| `email`               | `varchar(255)` | Unique, required              |
| `password_hash`       | `varchar(255)` | bcrypt, never exposed in JSON |
| `role`                | `varchar(50)`  | Default: `student`            |
| `subscription_tier`   | `varchar(50)`  | Default: `free`               |
| `email_verified`      | `bool`         | Default: `false`              |
| `searches_this_month` | `int`          | Usage quota tracking          |
| `exports_this_month`  | `int`          | Usage quota tracking          |

**Roles:** `admin` · `researcher` · `translator` · `publisher` · `student`

**Subscription Tiers:** `free` · `basic` · `premium` · `research`

### Session

| Field           | Type           | Notes                |
| --------------- | -------------- | -------------------- |
| `id`            | `uuid`         | Primary key          |
| `user_id`       | `uuid`         | FK → users (CASCADE) |
| `refresh_token` | `text`         | Unique per session   |
| `user_agent`    | `varchar(500)` | Optional             |
| `ip_address`    | `varchar(45)`  | Optional             |
| `expires_at`    | `timestamp`    | Required             |

### OAuth Account (`oauth_accounts`)

Supports `google` and `github` providers, linked to a `User` via `user_id`.

---

## 📡 API Reference

Base path: `/api`

### Public Endpoints

| Method | Path            | Description                         |
| ------ | --------------- | ----------------------------------- |
| `GET`  | `/api/health`   | Readiness check (DB + Redis status) |
| `POST` | `/api/register` | Register a new user                 |
| `POST` | `/api/login`    | Authenticate and receive token pair |
| `POST` | `/api/refresh`  | Rotate access & refresh tokens      |

### Protected Endpoints

> Require `Authorization: Bearer <access_token>` header.

| Method | Path                        | Description                              |
| ------ | --------------------------- | ---------------------------------------- |
| `POST` | `/api/auth/logout`          | Invalidate all sessions for the user     |
| `POST` | `/api/auth/change-password` | Change password (requires old password)  |
| `GET`  | `/api/user/profile`         | Get authenticated user's profile         |
| `PUT`  | `/api/user/profile`         | Update profile (`email`, `name`, `role`) |
| `GET`  | `/api/user/sessions`        | List active sessions _(stub)_            |
| `POST` | `/api/user/upgrade`         | Upgrade subscription plan _(stub)_       |

---

### Request & Response Schemas

#### `POST /api/register`

```json
// Request
{
  "email": "user@example.com",
  "password": "min8chars",
  "name": "Jane Doe",
  "role": "researcher"
}

// Response 201
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "expires_in": 900,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "Jane Doe",
    "role": "researcher",
    "created_at": "...",
    "updated_at": "..."
  }
}
```

#### `POST /api/login`

```json
// Request
{ "email": "user@example.com", "password": "min8chars" }

// Response 200 — same shape as register response
```

#### `POST /api/refresh`

```json
// Request
{ "refresh_token": "eyJ..." }

// Response 200 — new token pair with rotated refresh token
```

#### `POST /api/auth/change-password`

```json
// Request
{ "old_password": "current", "new_password": "newmin8" }

// Response 204 No Content
```

#### `PUT /api/user/profile`

```json
// Request (all fields optional)
{ "email": "new@example.com", "name": "New Name", "role": "translator" }

// Response 204 No Content
```

#### Error Response Shape

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": "..."
  }
}
```

**Error codes:** `BAD_REQUEST` · `UNAUTHORIZED` · `FORBIDDEN` · `NOT_FOUND` · `CONFLICT` · `VALIDATION_ERROR` · `INTERNAL_ERROR` · `RATE_LIMIT_EXCEEDED`

---

## ⚙️ Configuration

All configuration is loaded from environment variables. A `.env` file in the service root is auto-loaded at startup.

| Variable               | Default              | Description                             |
| ---------------------- | -------------------- | --------------------------------------- |
| `SERVER_HOST`          | `0.0.0.0`            | Bind address                            |
| `SERVER_PORT`          | `8080`               | HTTP port                               |
| `ENVIRONMENT`          | `development`        | `development` or `production`           |
| `SERVER_READ_TIMEOUT`  | `15s`                | HTTP read timeout                       |
| `SERVER_WRITE_TIMEOUT` | `15s`                | HTTP write timeout                      |
| `DB_HOST`              | `localhost`          | PostgreSQL host                         |
| `DB_PORT`              | `5435`               | PostgreSQL port                         |
| `DB_USER`              | `bibliograph`        | Database user                           |
| `DB_PASSWORD`          | _(required)_         | Database password                       |
| `DB_NAME`              | `auth_service`       | Database name                           |
| `DB_SSLMODE`           | `disable`            | SSL mode                                |
| `DATABASE_URL`         | —                    | Full DSN (overrides individual DB vars) |
| `JWT_SECRET`           | _(required in prod)_ | HS256 signing secret                    |
| `JWT_ACCESS_EXPIRY`    | `15m`                | Access token lifetime                   |
| `JWT_REFRESH_EXPIRY`   | `168h`               | Refresh token lifetime (7 days)         |
| `JWT_ISSUER`           | `auth-service`       | JWT `iss` claim                         |
| `REDIS_HOST`           | `localhost`          | Redis host                              |
| `REDIS_PORT`           | `6379`               | Redis port                              |
| `REDIS_PASSWORD`       | —                    | Redis password                          |
| `REDIS_DB`             | `0`                  | Redis database index                    |

> ⚠️ **Production requirement:** `JWT_SECRET` must be explicitly set. The service will refuse to start if the default placeholder value is detected in `production` environment.

---

## 🚀 Getting Started

### Prerequisites

- [Go 1.21+](https://golang.org/dl/)
- [Docker & Docker Compose](https://docs.docker.com/get-docker/)

### Run with Docker Compose

```bash
# From the auth-service directory
cd services/auth-service

# Copy and configure environment
cp .env.example .env

# Start all infrastructure + app
docker compose -f docker/docker-compose.yml up -d
```

This starts:

- **PostgreSQL 16** on port `5435`
- **Redis 7** on port `6379`
- **MongoDB 7** on port `27017`
- **RabbitMQ 3** on ports `5672` / `15672` (management UI)
- **MinIO** on ports `9000` / `9001` (console)
- **Auth Service** on port `4000`

### Run Locally

```bash
cd services/auth-service

# Install dependencies
go mod download

# Set environment variables (or create .env)
export DB_HOST=localhost
export DB_PORT=5435
export JWT_SECRET=your-local-dev-secret

# Run
go run cmd/main.go
```

### Verify

```bash
curl http://localhost:4000/api/health
# {"status":"ready","checks":{"database":"connected","redis":"connected"}}
```

---

## 🗃️ Running Migrations

Migrations run **automatically on startup** via GORM `AutoMigrate`. The following tables are created/updated:

- `users`
- `sessions`
- `oauth_accounts`

To run migrations manually (without starting the server):

```bash
cd services/auth-service
go run cmd/migrate/migrate.go
```

---

## 🛡️ Middleware Stack

| Middleware               | Scope            | Behavior                                                                            |
| ------------------------ | ---------------- | ----------------------------------------------------------------------------------- |
| `Recoverer`              | Global           | Catches panics, returns `500` JSON                                                  |
| `LoggerMiddleware`       | Global           | Logs method, path, status, duration, IP                                             |
| `CORSMiddleware`         | Global           | Permissive by default; configurable via `NewCORSMiddleware`                         |
| `authenticateMiddleware` | Protected routes | Validates Bearer JWT, injects `user_id`, `email`, `role` into context               |
| `RateLimiter`            | Configurable     | Sliding-window; `NewAPIRateLimiter` (100 req/min), `NewAuthRateLimiter` (5 req/min) |

---

## 🧠 Design Decisions

**Interface-driven layers** — `AuthService`, `UserService`, `JWTHelper`, and `JWTValidator` are all defined as interfaces. Concrete implementations are injected at startup in `main.go`, enabling clean unit testing without infrastructure dependencies.

**JWT claim embedding** — `domain.Claims` embeds `jwt.RegisteredClaims` and carries `UserID`, `Email`, `Role`, and `SubscriptionTier`. This allows downstream services to make authorization decisions from the token alone, without a database round-trip.

**Refresh token rotation** — On every `/refresh` call, both the access token and refresh token are regenerated and the session record is updated. This limits the blast radius of a leaked refresh token.

**Dual database package** — `pkg/database` is the production-grade connection manager (connection pooling, health check, graceful close) used by `main.go`. `internal/database` is a lightweight connector used exclusively by the standalone migration runner.

**Non-root Docker image** — The runtime image runs as a dedicated `bibliograph` user on Alpine, with no shell or package manager, minimizing the attack surface.

---

## 👤 Author

**Sina Sotoudeh**

|             |                                                                      |
| ----------- | -------------------------------------------------------------------- |
| 🌐 Website  | [sinasotoudeh.ir](https://sinasotoudeh.ir)                           |
| 🐙 GitHub   | [@sinasotoudeh](https://github.com/sinasotoudeh)                     |
| 💼 LinkedIn | [linkedin.com/in/sinasotoudeh](https://linkedin.com/in/sinasotoudeh) |
| 📧 Email    | [s.sotoudeh1@gmail.com](mailto:s.sotoudeh1@gmail.com)                |

---

_Part of the [Bibliograph AI](https://github.com/sinasotoudeh/bibliograph-ai) microservices platform._
