<div align="center">

# 📊 BiblioGraph AI — Data Profiling Engine

**A production-grade, async MongoDB data quality analysis framework**  
_Part of the [BiblioGraph AI](https://github.com/sinasotoudeh) microservices ecosystem_

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Motor_Async-47A248?style=flat-square&logo=mongodb&logoColor=white)](https://motor.readthedocs.io/)
[![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063?style=flat-square&logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](../../LICENSE)
[![Author](https://img.shields.io/badge/Author-Sina_Sotoudeh-blueviolet?style=flat-square)](https://sinasotoudeh.ir)

</div>

---

## 📌 Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Module Reference](#-module-reference)
  - [MongoDBProfiler](#1️⃣-mongodbprofiler--field-level-statistical-analysis)
  - [SchemaValidator](#2️⃣-schemavalidator--schema-drift-detection)
  - [RelationshipChecker](#3️⃣-relationshipchecker--referential-integrity)
  - [DataQualityScorer](#4️⃣-dataqualityscorer--composite-scoring-engine)
  - [Streaming Stats Design](#5️⃣-streaming-stats-design--memory-efficient-primitives)
- [Output Reports](#-output-reports)
- [Metrics & Interpretation Guide](#-metrics--interpretation-guide)
- [Quick Start](#-quick-start)
- [Configuration](#️-configuration)
- [Project Structure](#-project-structure)
- [Author](#-author)

---

## 🔍 Overview

The **Data Profiling Engine** is a standalone analytical subsystem inside the `scraper-service`. It performs multi-dimensional, schema-aware quality assessment of MongoDB collections without modifying any production data.

### ✨ Key Capabilities

- **Schema-Agnostic Structural Profiling** — discovers and statistically describes every field in a collection, including deeply nested and polymorphic ones, without prior knowledge of the schema
- **Pydantic Schema Drift Detection** — compares live database state against declared `BookInDB` Pydantic models to surface missing, extra, or degraded fields
- **Referential Integrity Validation** — verifies `books → authors` cross-collection relationships and detects orphaned or dangling references
- **Memory-Efficient Streaming Statistics** — uses online algorithms (`StreamingStats`, `UniqueValueTracker`, `DateRangeTracker`) to process millions of documents without loading them into memory
- **Composite Quality Scoring (0–100)** — produces a weighted, multi-dimensional score with actionable `critical`, `warning`, and `info` issue classification
- **Flexible Sampling** — supports both random (`$sample` aggregation pipeline) and sequential sampling with configurable sample sizes
- **Structured JSON Reports** — generates per-collection and summary JSON reports, suitable for CI/CD gates, dashboards, or executive reporting

---

## 🏗 Architecture

```text
scripts/data_profiling/
│
├── run.py                          # Async entrypoint & orchestration
│
├── profilers/
│   ├── mongodb_profiler.py         # Core field-level statistical profiler
│   ├── schema_validator.py         # Pydantic schema compliance checker
│   └── relationship_checker.py     # Cross-collection referential integrity
│
├── analyzers/
│   ├── quality_scorer.py           # Composite scoring engine (4 dimensions)
│   └── anomaly_detector.py         # (Reserved for future anomaly detection)
│
├── utils/
│   └── stats_tracker.py            # Memory-efficient streaming statistics
│
└── reports/
    └── <run_id>/                   # Auto-generated per-run output directory
        ├── books_profile.json
        ├── books_schema_validation.json
        ├── books_quality_score.json
        └── summary_report.json

```

### Data Flow

```text
MongoDB Collection
       │
       ▼
 MongoDBProfiler          ← Async cursor, streaming, field-level stats
       │
       ├──► SchemaValidator       ← Compare profile vs. BookInDB (Pydantic v2)
       │
       ├──► RelationshipChecker   ← books → authors referential integrity
       │
       └──► DataQualityScorer     ← Weighted composite score (Completeness 40%
                                     + Validity 30% + Consistency 20%
                                     + Integrity 10%)
                  │
                  └──► JSON Reports  (per-collection + summary)
```

---

## 📦 Module Reference

### 1️⃣ `MongoDBProfiler` — Field-Level Statistical Analysis

**File:** `profilers/mongodb_profiler.py`

The profiler iterates an async Motor cursor over sampled documents and maintains a `Dict[field_path, FieldMetadata]` registry. Fields from nested documents are **flattened** using dot notation (e.g., `publisher.address.city`), enabling uniform analysis regardless of nesting depth.

#### Collection-Level Output

```json
{
  "collection": "books",
  "total_documents": 120450,
  "documents_sampled": 10000,
  "actual_sample_size": 10000,
  "sampling_method": "random ($sample)",
  "total_distinct_fields": 47,
  "profiled_at": "2026-04-15T09:00:00.000Z"
}
```

#### Field-Level Metrics

Every entry inside `fields` exposes the following metrics:

| Metric               | Formula                                      | Description                                                                    |
| -------------------- | -------------------------------------------- | ------------------------------------------------------------------------------ |
| `occurrence_count`   | direct count                                 | Number of documents in the sample where this field exists                      |
| `missing_rate`       | `1 - (occurrence_count / documents_sampled)` | Fraction of documents where the field is absent                                |
| `null_count`         | direct count                                 | Count of explicit `null` values (distinct from absence)                        |
| `null_rate`          | `null_count / occurrence_count`              | Rate of null among present occurrences                                         |
| `types`              | frequency map                                | Distribution of Python types observed (`str`, `int`, `list`, `ObjectId`, etc.) |
| `empty_string_count` | direct count                                 | Strings with value `""`                                                        |
| `empty_string_rate`  | `empty_string_count / string_count`          | Rate of empty strings                                                          |

> **`missing` vs `null`:** A `missing` field does not exist in the document at all. A `null` field exists but carries a `None` value. These are tracked separately because they imply different data quality issues.

#### Type-Conditional Metrics

**String fields:**

```json
"string_stats": { "count": 9840, "min": 3, "max": 312, "mean": 52.4, "std": 28.1 }
```

**Numeric fields:**

```json
"numeric_stats": { "count": 9120, "min": 1.0, "max": 9800.0, "mean": 245.3, "std": 410.7 }
```

**Datetime fields:**

```json
"date_range": { "min": "1900-01-01T00:00:00", "max": "2026-04-15T00:00:00", "range_days": 45700, "count": 9800 }
```

**Array fields:**

```json
"array_stats": {
  "lengths": { "count": 8900, "min": 0.0, "max": 12.0, "mean": 2.1, "std": 1.4 },
  "element_types": { "ObjectId": 18290, "null": 43 }
}
```

**Uniqueness tracking** (only for fields matching `_id`, `nlai_id`, `isbn`, `nlai_permalink`):

```json
"uniqueness": {
  "unique_count": 9998,
  "duplicate_rate": 0.02,
  "overflow": false,
  "total_count": 10000,
  "sample_values": ["9789643690123", "..."]
}
```

> **Memory guard:** `UniqueValueTracker` caps at `10,000` unique values per field. Once exceeded, `overflow: true` is set and duplicate rate becomes `null` rather than producing a misleading result.

---

### 2️⃣ `SchemaValidator` — Schema Drift Detection

**File:** `profilers/schema_validator.py`

Compares the live profiling results against a **Pydantic v2** model class using `model_fields` introspection. No database query is issued — it operates purely on the profile dict.

#### Output

```json
{
  "collection": "books",
  "schema_class": "BookInDB",
  "compliance_score": 88.5,
  "required_fields_count": 8,
  "optional_fields_count": 12,
  "missing_required_fields": ["isbn"],
  "high_missing_rate_fields": [
    {
      "field": "publication_year",
      "missing_rate": 0.27,
      "severity": "critical"
    }
  ],
  "extra_fields_in_db": ["legacy_nlai_code", "temp_scrape_flag"]
}
```

#### Compliance Score Formula

$$\text{compliance\_score} = \max\!\left(0,\; 100 - \frac{|\text{missing\_required}| + |\text{high\_missing\_rate}|}{|\text{required\_fields}|} \times 100\right)$$

#### Severity Thresholds

| Missing Rate       | Severity   |
| ------------------ | ---------- |
| `> 5%` and `≤ 20%` | `warning`  |
| `> 20%`            | `critical` |

> **`extra_fields_in_db`** are fields present in MongoDB but absent from the Pydantic schema. These are not penalised in the score but are surfaced as potential schema drift or technical debt indicators.

---

### 3️⃣ `RelationshipChecker` — Referential Integrity

**File:** `profilers/relationship_checker.py`

Performs full cross-collection scans to verify referential integrity. Currently supports two checks:

#### Check 1: `books → authors`

Validates that every `ObjectId` in a book's `author_ids` array resolves to an existing document in the `authors` collection.

```json
{
  "relationship": "books → authors",
  "integrity_score": 91.5,
  "total_books": 120450,
  "total_authors": 8200,
  "orphan_books_count": 1820,
  "orphan_rate": 0.0151,
  "books_with_invalid_authors": 430,
  "invalid_author_references_count": 512,
  "invalid_rate": 0.0036,
  "sample_orphan_books": ["66abc..."],
  "sample_invalid_references": [
    { "book_id": "...", "invalid_author_id": "..." }
  ]
}
```

$$\text{integrity\_score} = 100 - (\text{orphan\_rate} \times 50 + \text{invalid\_rate} \times 50)$$

#### Check 2: `scraping_logs` internal consistency

Validates that every log entry has a `task_id` and that task IDs are unique.

$$\text{integrity\_score} = 100 - (\text{missing\_task\_id\_rate} \times 60 + \text{duplicate\_rate} \times 40)$$

| Score     | Status      |
| --------- | ----------- |
| `≥ 90`    | ✅ Healthy  |
| `70 – 89` | ⚠️ Warning  |
| `< 70`    | ❌ Critical |

> **Note:** In the current `run.py` configuration, `RelationshipChecker` is **intentionally disabled** (`books_relationship = None`) for books-only runs to prevent false positives when the authors collection is not available in scope. Pass the checker result to `DataQualityScorer` to activate the `integrity` dimension.

---

### 4️⃣ `DataQualityScorer` — Composite Scoring Engine

**File:** `analyzers/quality_scorer.py`

Aggregates results from all three upstream components into a single, weighted quality score.

#### Overall Score Formula

$$\text{overall\_score} = C \times 0.40 + V \times 0.30 + K \times 0.20 + I \times 0.10$$

Where:

| Symbol | Dimension        | Weight | Source                |
| ------ | ---------------- | ------ | --------------------- |
| $C$    | **Completeness** | 40%    | `MongoDBProfiler`     |
| $V$    | **Validity**     | 30%    | `SchemaValidator`     |
| $K$    | **Consistency**  | 20%    | `MongoDBProfiler`     |
| $I$    | **Integrity**    | 10%    | `RelationshipChecker` |

#### Dimension Calculations

**Completeness** — measures field population rate across all fields:

$$C = \left(1 - \frac{\sum_{f \in \text{fields}} \text{missing\_rate}(f)}{|\text{fields}|}\right) \times 100$$

**Validity** — directly sourced from `SchemaValidator.compliance_score`:

$$V = \text{compliance\_score}$$

**Consistency** — measures type uniformity and absence of empty strings per field:

$$K_f = \left(\frac{\max(\text{type\_counts})}{\sum(\text{type\_counts})} \times 0.7 + (1 - \text{empty\_string\_rate}) \times 0.3\right) \times 100$$

$$K = \frac{\sum_{f} K_f}{|\text{fields}|}$$

**Integrity** — sourced from `RelationshipChecker`, defaults to `100` when disabled:

$$I = \text{integrity\_score} \quad (\text{or } 100 \text{ if checker not run})$$

#### Grading Scale

| Score      | Grade             | Action                             |
| ---------- | ----------------- | ---------------------------------- |
| `90 – 100` | **A — Excellent** | ✅ No action required              |
| `80 – 89`  | **B — Good**      | 🔍 Monitor flagged fields          |
| `70 – 79`  | **C — Fair**      | ⚠️ Address warnings in next sprint |
| `60 – 69`  | **D — Poor**      | 🔴 Schedule data repair task       |
| `< 60`     | **F — Critical**  | 🚨 Immediate intervention required |

#### Sample Output

```json
{
  "collection": "books",
  "overall_score": 83.7,
  "grade": "B (Good)",
  "dimensions": {
    "completeness": { "score": 87.2, "weight": "40%" },
    "validity": { "score": 88.5, "weight": "30%" },
    "consistency": { "score": 74.1, "weight": "20%" },
    "integrity": { "score": 100.0, "weight": "10%" }
  },
  "issues_summary": {
    "critical": ["Field 'publication_year' has 27.0% missing rate"],
    "warnings": ["Field 'description' has 12.0% missing rate"],
    "info": []
  }
}
```

---

### 5️⃣ Streaming Stats Design — Memory-Efficient Primitives

**File:** `utils/stats_tracker.py`

All statistical accumulation is performed using **online algorithms** — documents are processed once, streamed, and never held in memory as a batch. This enables profiling collections of any size within a constant memory footprint.

#### `StreamingStats`

Computes `min`, `max`, `mean`, and `std` using Welford-style accumulation:

$$\mu = \frac{\sum x_i}{n}, \quad \sigma = \sqrt{\frac{\sum x_i^2}{n} - \mu^2}$$

Used for: string lengths, numeric values, array lengths.

#### `UniqueValueTracker`

Maintains a Python `set` with a configurable cap (`max_unique = 1,000` per tracker, `10,000` per field in the profiler). Once the cap is exceeded, `overflow = True` is set and `duplicate_rate` is reported as `null` to avoid misleading results.

#### `DateRangeTracker`

Tracks `min_date` and `max_date` using simple comparison — $O(1)$ per document, $O(1)$ space.

#### `FieldMetadata`

The composite container class aggregating all trackers for a single field path:

```python
class FieldMetadata:
    occurrence_count: int
    null_count: int
    empty_string_count: int
    types: defaultdict(int)        # type distribution
    string_lengths: StreamingStats
    numeric_values: StreamingStats
    date_range: DateRangeTracker
    array_lengths: StreamingStats
    array_element_types: defaultdict(int)
    unique_tracker: UniqueValueTracker
```

> **`safe_add_unique()` guard:** The profiler wraps all `UniqueValueTracker.add()` calls in a `try/except TypeError` block to safely handle tracker objects that do not implement `__len__`, preventing crashes on custom wrapper classes.

---

## 📁 Output Reports

Each run generates a timestamped directory under `reports/<YYYYMMDD_HHMMSS>/`:

| File                           | Contents                                               |
| ------------------------------ | ------------------------------------------------------ |
| `books_profile.json`           | Full field-level statistical profile of the collection |
| `books_schema_validation.json` | Schema drift report vs. `BookInDB`                     |
| `books_quality_score.json`     | 4-dimensional quality score with issues summary        |
| `summary_report.json`          | Aggregated overview for dashboards/CI                  |

#### `summary_report.json` structure

```json
{
  "metadata": {
    "started_at": "2026-04-15T09:00:00",
    "duration_seconds": 184.32,
    "scope": "books_only"
  },
  "results": {
    "books": {
      "docs": 120450,
      "score": 83.7,
      "grade": "B (Good)"
    }
  }
}
```

---

## 📊 Metrics & Interpretation Guide

Use this table as a quick reference when reviewing output reports:

| Metric                            | Healthy | Warning     | Critical |
| --------------------------------- | ------- | ----------- | -------- |
| `missing_rate` (required field)   | `< 5%`  | `5% – 20%`  | `> 20%`  |
| `null_rate`                       | `< 5%`  | `5% – 10%`  | `> 10%`  |
| `empty_string_rate`               | `< 2%`  | `2% – 5%`   | `> 5%`   |
| `type_consistency`                | `> 95%` | `90% – 95%` | `< 90%`  |
| `orphan_rate` (books w/o authors) | `< 3%`  | `3% – 10%`  | `> 10%`  |
| `invalid_rate` (bad references)   | `< 1%`  | `1% – 5%`   | `> 5%`   |
| `overall_score`                   | `≥ 80`  | `70 – 79`   | `< 70`   |

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose installed
- The `bibliograph-network` external Docker network exists
- A running MongoDB instance accessible from the network

### Run via Docker (Recommended)

From the **repository root** (`bibliograph-ai/`):

```bash
cd services/scraper-service

docker-compose -f docker-compose.scraper.yml \
  -f ../../infrastructure/docker/docker-compose.dev.yml \
  run --rm --no-deps \
  -v "$(pwd)/scripts:/app/scripts" \
  scraper-api \
  python scripts/data_profiling/run.py
```

> **Windows (PowerShell):**
>
> ```powershell
> cd C:\Users\sinas\bibliograph-ai\services\scraper-service
>
> docker-compose -f docker-compose.scraper.yml `
>   -f ..\..\infrastructure\docker\docker-compose.dev.yml `
>   run --rm --no-deps `
>   -v ".\scripts:/app/scripts" `
>   scraper-api `
>   python scripts/data_profiling/run.py
> ```

### Environment Setup

The script resolves environment variables in the following priority order:

1. `scripts/data_profiling/.env.profiler` _(profiling-specific overrides)_
2. `services/scraper-service/.env` _(service-wide defaults)_

A minimal `.env.profiler`:

```env
MONGODB_URI=mongodb://user:pass@host:27017
MONGODB_DB_NAME=bibliograph_db
```

---

## ⚙️ Configuration

### Changing Sample Size

In `run.py`, modify the `sample_size` parameter:

python

# Profile 10,000 random documents

result = await profile_single_collection(
profiler=profiler,
validator=validator,
scorer=scorer,
collection_name="books",
schema_class=BookInDB,
sample_size=10000, # ← change here
relationship_check=None
)

```python
# Profile ALL documents (no sampling)
result = await profile_single_collection(
    ...
    sample_size=None,           # ← None = full scan
    ...
)
```

### Adding Important Fields for Uniqueness Tracking

In `mongodb_profiler.py`, extend the keyword list:

```python
def _is_important_field(self, field_path: str) -> bool:
    important_keywords = [
        "_id", "nlai_id", "isbn", "nlai_permalink",
        "doi",    # ← add custom identifiers here
        "oclc_id"
    ]
    return any(keyword in field_path.lower() for keyword in important_keywords)
```

### Enabling Relationship Checks

In `run.py`, uncomment the checker section:

```python
from profilers.relationship_checker import RelationshipChecker

checker = RelationshipChecker(mongodb_client)
books_relationship = await checker.check_book_author_integrity()

result = await profile_single_collection(
    ...
    relationship_check=books_relationship   # ← pass here
)
```

### Adjusting the Unique Value Cap

In `stats_tracker.py`:

```python
class UniqueValueTracker:
    def __init__(self, max_unique: int = 1000):   # ← default per tracker
        ...
```

In `mongodb_profiler.py`:

```python
self.MAX_UNIQUE_TRACKING = 10000   # ← global cap per field in profiler
```

---

## 📂 Project Structure

```text
scripts/data_profiling/
│
├── run.py                              # Async orchestration entrypoint
│
├── profilers/
│   ├── mongodb_profiler.py             # Async field-level profiler (Motor)
│   ├── schema_validator.py             # Pydantic v2 schema drift detection
│   └── relationship_checker.py         # Cross-collection integrity checker
│
├── analyzers/
│   ├── quality_scorer.py               # Weighted composite scoring engine
│   └── anomaly_detector.py             # (Reserved)
│
├── utils/
│   └── stats_tracker.py                # StreamingStats, UniqueValueTracker,
│                                       # DateRangeTracker, FieldMetadata
│
├── reports/                            # Auto-generated, gitignored
│   └── <run_id>/
│       ├── books_profile.json
│       ├── books_schema_validation.json
│       ├── books_quality_score.json
│       └── summary_report.json
│
├── .env.profiler                       # Local env overrides (gitignored)
└── README.md                           # This file
```

---

## 👤 Author

<div align="center">

**Sina Sotoudeh**  
_Backend Engineer & Data Systems Developer_

[![Website](https://img.shields.io/badge/Website-sinasotoudeh.ir-0A66C2?style=flat-square&logo=safari&logoColor=white)](https://sinasotoudeh.ir)
[![GitHub](https://img.shields.io/badge/GitHub-sinasotoudeh-181717?style=flat-square&logo=github&logoColor=white)](https://github.com/sinasotoudeh)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-sinasotoudeh-0A66C2?style=flat-square&logo=linkedin&logoColor=white)](https://linkedin.com/in/sinasotoudeh)
[![Email](https://img.shields.io/badge/Email-s.sotoudeh1%40gmail.com-D14836?style=flat-square&logo=gmail&logoColor=white)](mailto:s.sotoudeh1@gmail.com)

_Part of the **BiblioGraph AI** project — a microservices platform for bibliographic data acquisition, enrichment, and analysis._

</div>

---

<div align="center">
<sub>BiblioGraph AI · Scraper Service · Data Profiling Engine</sub>
</div>
