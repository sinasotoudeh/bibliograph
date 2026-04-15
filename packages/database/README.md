# 🗄️ Bibliograph AI - Database Package (`@bibliograph-ai/database`)

![Prisma](https://img.shields.io/badge/Prisma-ORM-2D3748?style=flat&logo=prisma)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-DB-4169E1?style=flat&logo=postgresql)
![TypeScript](https://img.shields.io/badge/TypeScript-Ready-3178C6?style=flat&logo=typescript)
![Architecture](https://img.shields.io/badge/Architecture-Monorepo_Package-blue)

## 📖 Overview

The `@bibliograph-ai/database` package serves as the **Single Source of Truth (SSOT)** for the data layer across the Bibliograph AI monorepo. Built with **Prisma ORM** and **PostgreSQL**, it encapsulates the entire database schema, migrations, and seed logic. By exposing the generated Prisma Client, it ensures strict type safety and consistent data access patterns for all consuming microservices (e.g., `auth-service`, `scraper-service`).

---

## ✨ Key Domains & Features

The schema is modeled for a comprehensive, Goodreads-style platform, divided into four distinct logical domains:

- **User Management:** Handles user profiles, authentication metadata, and Role-Based Access Control (RBAC) supporting $4$ levels: `$USER$, $MODERATOR$, $ADMIN$, $SUPER_ADMIN$`.
- **Core Entities:** Manages the primary catalog including `Book`, `Author`, and `Category`. It features an $M2M$ (Many-to-Many) relationship between books and categories.
- **Translations:** A specialized domain to track `Translator` profiles and specific `Translation` editions of books, supporting multiple languages.
- **User Interactions:** A rich social and tracking layer encompassing `Review`, `Rating` (on a $1-5$ scale), `Comment`, `Favorite`, `ReadingList`, `ReadingProgress`, and page-specific `Annotation`.

---

## 🚀 Installation & Usage (User-Centric)

### Prerequisites

- Node.js & `pnpm` workspace setup.
- A running PostgreSQL instance.

### Environment Setup

Create a `.env` file in the root of the `packages/database` directory:

| Variable       | Default / Example                                   | Description                                    |
| :------------- | :-------------------------------------------------- | :--------------------------------------------- |
| `DATABASE_URL` | `postgresql://user:pass@localhost:5432/bibliograph` | Connection string for the PostgreSQL database. |

### Available Commands

Use the following commands to manage the database lifecycle:

| Command                  | Description                                                         |
| :----------------------- | :------------------------------------------------------------------ |
| `pnpm install`           | Installs dependencies including the Prisma CLI.                     |
| `npx prisma generate`    | Generates the strongly-typed Prisma Client in `node_modules`.       |
| `npx prisma migrate dev` | Applies migrations to the database and keeps the schema in sync.    |
| `npx prisma db seed`     | Executes the `seed.ts` script to populate the DB with initial data. |
| `npx prisma studio`      | Opens a local web UI to view and edit database records.             |

### Initial Data Seeding

The package includes an idempotent seed script. Running `npx prisma db seed` will provision:

- A default admin user (`admin@bibliograph.ai`).
- Core literature categories (Novel, Poetry, History, etc.).
- Sample renowned authors (e.g., Sadegh Hedayat) and translators.
- Sample books with established $M2M$ relationships.

---

## 🏗 Architecture & Code Quality (Developer/Reviewer-Centric)

This package is designed with a focus on modularity, data integrity, and performance.

### 📐 Design Choices

- **Headless Package Design:** The `src/` directory is intentionally kept empty. This package does not wrap the Prisma Client with custom logic. Instead, it natively exports the generated `@prisma/client`, allowing consuming services (like Go or Python services via custom generators, or Node.js services directly) to instantiate the client themselves. This prevents dependency injection bottlenecks.
- **Idempotent Seeding:** The `seed.ts` utilizes Prisma's `upsert` and existence checks (e.g., `findFirst`). This guarantees that the seed script can be executed multiple times without throwing unique constraint violations or duplicating $1:N$ and $M2M$ relations.

### 🛡 Data Integrity & Constraints

- **Cascading Deletes:** Strict `onDelete: Cascade` rules are implemented on interaction models (`Review`, `Rating`, `ReadingList`, etc.). If a `User` or `Book` is deleted, all associated user-generated content is automatically purged, preventing orphan records.
- **Unique Compound Indexes:** Models like `Rating` and `Favorite` utilize `@@unique([userId, bookId])` to ensure a user can only rate or favorite a specific book exactly $1$ time.

### ⚡ Performance Optimization

- **Strategic Indexing:** Foreign keys and highly queried fields (like `email`, `slug`, `isbn`, and `authorId`) are explicitly indexed using `@@index()` to reduce scan times from $O(N)$ to $O(\log N)$ during complex joins.
- **Full-Text Search Prep:** The schema is pre-configured with `previewFeatures = ["fullTextSearch", "fullTextIndex"]`, laying the groundwork for high-performance, native PostgreSQL text searching across book titles and descriptions.

---

## 👤 Author

Developed and meticulously maintained by **Sina Sotoudeh**.

- 🌍 **Website:** [sinasotoudeh.ir](https://sinasotoudeh.ir)
- 💻 **GitHub:** [@sinasotoudeh](https://github.com/sinasotoudeh)
- 💼 **LinkedIn:** [Sina Sotoudeh](https://linkedin.com/in/sinasotoudeh)
- 📧 **Email:** [s.sotoudeh1@gmail.com](mailto:s.sotoudeh1@gmail.com)
