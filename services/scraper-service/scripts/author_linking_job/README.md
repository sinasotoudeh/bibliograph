# 🔗 Author Linking Job

<p align="center">
  <a href="https://www.python.org/downloads/release/python-3110/"><img src="https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11"></a>
  <a href="https://www.elastic.co/"><img src="https://img.shields.io/badge/Elasticsearch-8.11-005571?style=flat-square&logo=elasticsearch&logoColor=white" alt="Elasticsearch 8.11"></a>
  <a href="https://www.mongodb.com/"><img src="https://img.shields.io/badge/MongoDB-4.6+-47A248?style=flat-square&logo=mongodb&logoColor=white" alt="MongoDB"></a>
  <img src="https://img.shields.io/badge/NLP-Persian%20%7C%20Latin-orange?style=flat-square" alt="NLP">
  <img src="https://img.shields.io/badge/Status-Production-brightgreen?style=flat-square" alt="Status">
</p>

<p align="center">
  A bilingual, production-grade ETL pipeline that resolves raw author strings from scraped book records against a canonical authors database, using Elasticsearch fuzzy matching and a two-tier validation engine.
</p>

---

## 📑 Table of Contents

- [Overview](#-overview)
- [System Architecture](#-system-architecture)
- [Pipeline Specifications](#-pipeline-specifications)
  - [Latin Pipeline](#1-latin-author-linking-run_job_latinpy)
  - [Persian Pipeline](#2-persian-author-linking-run_job_persianpy)
- [Data Model](#-data-model)
- [Configuration](#-configuration)
- [Installation & Execution](#-installation--execution)
- [Performance Tuning](#-performance-tuning)
- [Edge Cases & Known Behaviors](#-edge-cases--known-behaviors)
- [Logging & Monitoring](#-logging--monitoring)
- [Architecture & Code Quality](#-architecture--code-quality)
- [Author](#-author)

---

## 🔍 Overview

The **Author Linking Job** is a post-processing component within the `scraper-service` of the BiblioGraph AI platform. Its responsibility is to bridge the semantic gap between raw, unstructured author strings extracted during scraping and the normalized, canonical author entities stored in the master `authors` collection.

**The core problem it solves:** Scraped book records contain author names as free-text strings (e.g., `"محمد علی جمال‌زاده"` or `"Eco, Umberto"`). These strings are inconsistent — they may contain diacritics, alternate Unicode representations, punctuation variants, or transliteration differences. This job resolves each string to a specific `ObjectId` in the `authors` collection, enabling downstream graph construction, analytics, and recommendation features.

**Two specialized pipelines handle distinct linguistic domains:**

| Pipeline | Script               | Source Field                  | Script Type       |
| -------- | -------------------- | ----------------------------- | ----------------- |
| Latin    | `run_job_latin.py`   | `extracted_add_authors.latin` | Top-3 candidates  |
| Persian  | `run_job_persian.py` | `names_in_main_entry.persian` | Single best match |

---

## 🏗 System Architecture

Both pipelines follow the same fault-tolerant ETL pattern, executed as standalone Python scripts against live MongoDB and Elasticsearch instances.

```
┌─────────────────────────────────────────────────────────────────┐
│                    AUTHOR LINKING PIPELINE                      │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │   MongoDB    │    │Elasticsearch │    │    MongoDB       │  │
│  │  (authors)   │───▶│    Index     │    │    (books)       │  │
│  └──────────────┘    └──────────────┘    └────────┬─────────┘  │
│         │                   │                     │            │
│         ▼                   ▼                     ▼            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   MATCHING ENGINE                       │   │
│  │                                                         │   │
│  │  normalize_text() ──▶ ES fuzzy query ──▶ score filter   │   │
│  │                                              │          │   │
│  │                              text_similarity check      │   │
│  │                                              │          │   │
│  │                                        link_data{}      │   │
│  └──────────────────────────────────────────────┬──────────┘   │
│                                                 │              │
│                                                 ▼              │
│                                    bulk_write (batch=500)      │
│                                    $set / $unset               │
└─────────────────────────────────────────────────────────────────┘
```

### Execution Phases

1. **Connectivity Validation** — Pings both MongoDB and Elasticsearch; exits with code `1` on failure.
2. **Index Rebuild** — Drops and recreates the ES index with a custom analyzer on every run, ensuring a clean, consistent state.
3. **Author Indexing** — Bulk-indexes all author name variants from MongoDB into Elasticsearch.
4. **In-Memory Cache Build** _(Persian only)_ — Pre-loads `{ _id → Author }` map for O(1) lookups during matching.
5. **Book Iteration** — Streams books cursor with `no_cursor_timeout=True` to handle large collections safely.
6. **Normalization & Matching** — Normalizes each author string and queries Elasticsearch.
7. **Two-Tier Validation** — Applies ES score threshold, then Python-side text similarity check.
8. **Batch Write** — Accumulates `UpdateOne` operations and flushes every 500 documents via `bulk_write(ordered=False)`.

---

## 📜 Pipeline Specifications

### 1. Latin Author Linking (`run_job_latin.py`)

Handles Latin-script author names with punctuation variance, case differences, and standard typographical errors.

#### Elasticsearch Analyzer: `latin_name_analyzer`

| Component    | Type              | Configuration                                              |
| ------------ | ----------------- | ---------------------------------------------------------- |
| Char Filter  | `pattern_replace` | Strips all non-letter, non-digit chars: `[^\p{L}\p{Nd}\s]` |
| Tokenizer    | `standard`        | Unicode-aware word boundary splitting                      |
| Token Filter | `lowercase`       | Full case normalization                                    |
| Token Filter | `asciifolding`    | Accent folding: `é → e`, `ü → u`                           |

#### Search Strategy

```python
# bool query with boosted surname matching
{
  "bool": {
    "must": {
      "match": {
        "latin_name": {
          "query": author_name,
          "fuzziness": 1,       # Levenshtein edit distance ≤ 1
          "prefix_length": 2    # First 2 chars must match exactly
        }
      }
    },
    "should": {
      "match": {
        "latin_name": {
          "query": last_token,  # Isolated surname
          "boost": 2.0          # Surname match weighted 2×
        }
      }
    }
  }
}
```

#### Output Structure

Stores the **top 3 candidates** per book to support downstream manual review or automated selection:

```python
"author_links": [
  {
    "rank": 1,
    "ref_author_id": ObjectId("..."),
    "confidence_score": 12.4,
    "matched_name": "Umberto Eco"
  },
  # ... up to rank 3
]
```

---

### 2. Persian Author Linking (`run_job_persian.py`)

A specialized pipeline engineered for the morphological complexity of Persian/Arabic script: varying Unicode codepoints for the same glyph, diacritics (Erab/Tashkil), zero-width non-joiners (ZWNJ), and dual transliteration variants per author.

#### Normalization Symmetry

A critical design principle: **the Python `normalize_persian_text()` function and the Elasticsearch `persian_custom_analyzer` apply identical transformations.** This symmetry ensures that query strings and indexed strings are always in the same normalized form.

```python
def normalize_persian_text(text):
    # 1. Unify Arabic/Persian character variants
    text = text.replace('ي', 'ی').replace('ك', 'ک')
    text = text.replace('آ', 'ا').replace('أ', 'ا').replace('إ', 'ا')
    text = text.replace('ئ', 'ی').replace('ؤ', 'و')
    # 2. Strip diacritics (U+064B–U+065F, U+0670)
    text = re.sub(r'[\u064B-\u065F\u0670]', '', text)
    # 3. ZWNJ → standard space
    text = text.replace('\u200c', ' ')
    # 4. Remove punctuation
    text = re.sub(r'[^\w\s]', ' ', text)
    # 5. Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text
```

#### Elasticsearch Analyzer: `persian_custom_analyzer`

| Component                            | Type                          | Purpose                                      |
| ------------------------------------ | ----------------------------- | -------------------------------------------- |
| `persian_char_normalizer`            | `mapping` char filter         | Unifies Arabic/Persian Unicode variants      |
| `punctuation_and_half_space_remover` | `pattern_replace` char filter | Removes punctuation and ZWNJ                 |
| `standard`                           | tokenizer                     | Word boundary splitting                      |
| `lowercase`                          | token filter                  | Case normalization                           |
| `arabic_normalization`               | token filter                  | Removes Tatweel (`ـ`) and most diacritics    |
| `persian_normalization`              | token filter                  | Elasticsearch built-in Persian normalization |
| `persian_stop`                       | token filter                  | Removes Persian stopwords                    |

#### Dual Transliteration Indexing

Each author document may contain two Persian name variants. Both are normalized, deduplicated via Python `set()`, and indexed as separate ES documents pointing to the same `mongo_id`:

Author { \_id: X, Persian_translitration_1: "محمد علی", Persian_translitration_2: "محمدعلی" }
↓
ES Doc 1: { mongo_id: "X", persian_name: "محمد علی" }
ES Doc 2: { mongo_id: "X", persian_name: "محمدعلی" }

#### Two-Tier Validation Engine

Matches pass through two independent gates before being accepted:

ES Score ≥ 4.0 ──▶ difflib.SequenceMatcher ratio ≥ 0.20 ──▶ ACCEPTED
│ │
REJECTED REJECTED

**Why two tiers?** Elasticsearch's `persian_normalization` and `persian_stop` filters can be aggressive — they may produce high scores for semantically distant strings after heavy stemming. The Python-side `SequenceMatcher` check operates on the _normalized_ strings directly, catching false positives that ES scoring alone would miss.

#### Output Structure

Stores the **single highest-confidence match** per author string:

```python
"author_links_persian": [
  {
    "name_from_book": "محمد علی جمال‌زاده",
    "matched_persian_name": "محمد علی جمالزاده",
    "ref_author_id": ObjectId("..."),
    "matched_name": "Mohammad Ali Jamalzadeh",
    "confidence_score": 8.7,
    "text_similarity": 0.94
  }
]
```

---

## 📦 Data Model

### Input: `books` Collection

**Latin pipeline reads:**

books.extracted_add_authors.latin → ["Eco, Umberto", "Calvino, Italo"]

**Persian pipeline reads:**

books.names_in_main_entry.persian → ["محمد علی جمال‌زاده"]

### Output: Written back to `books`

| Condition       | Operation | Field                |
| --------------- | --------- | -------------------- |
| ≥ 1 match found | `$set`    | `AUTHOR_LINKS_FIELD` |
| 0 matches found | `$unset`  | `AUTHOR_LINKS_FIELD` |

The `$unset` on no-match is intentional — it keeps the collection clean and prevents stale data from previous runs persisting on re-runs.

### Source: `authors` Collection

| Field                      | Used By                                    |
| -------------------------- | ------------------------------------------ |
| `_id`                      | Both pipelines — stored as `ref_author_id` |
| `Author`                   | Both pipelines — stored as `matched_name`  |
| `Persian_translitration_1` | Persian pipeline — indexed into ES         |
| `Persian_translitration_2` | Persian pipeline — indexed into ES         |

---

## ⚙️ Configuration

All configuration is defined as constants at the top of each script. Edit these before running.

### Common Constants

```python
MONGO_URI            = "mongodb://user:pass@host:port"
ES_HOST              = "http://host:port"
DB_NAME              = "bibliograph_db"
AUTHORS_COLLECTION   = "authors"
BOOKS_COLLECTION     = "books"
INDEX_NAME           = "bibliograph_authors_persian"  # or latin variant
AUTHOR_LINKS_FIELD   = "author_links_persian"         # MongoDB field name
BATCH_SIZE           = 500
```

### Persian-Specific Thresholds

```python
MIN_SCORE_THRESHOLD  = 4.0   # Minimum Elasticsearch relevance score
MIN_TEXT_SIMILARITY  = 0.20  # Minimum difflib.SequenceMatcher ratio (0.0–1.0)
```

### Latin-Specific Thresholds

```python
MIN_SCORE_THRESHOLD  = 5.0   # Higher bar due to Latin scoring characteristics
TOP_K_RESULTS        = 3     # Number of candidates to store per author string
```

---

## 🚀 Installation & Execution

### Prerequisites

- Python **3.11+**
- Elasticsearch **8.x** (tested on 8.11)
- MongoDB **4.6+**
- RabbitMQ + Redis (for the broader scraper-service; not required for standalone script execution)

### Install Dependencies

```bash
cd scripts/author_linking_job
pip install -r requirements.txt
```

**`requirements.txt`:**

elasticsearch==8.11.0
pymongo==4.6.0
python-dotenv==1.0.0

### Create Log Directory

```bash
mkdir -p logs
```

### Run

```bash
# Latin linking
python scripts/author_linking_job/run_job_latin.py

# Persian linking
python scripts/author_linking_job/run_job_persian.py
```

### Run via Docker (scraper-service container)

```bash
docker-compose -f docker-compose.scraper.yml \
  run --rm --no-deps \
  -v "$(pwd)/scripts:/app/scripts" \
  scraper-api \
  python scripts/author_linking_job/run_job_persian.py
```

---

## ⚡ Performance Tuning

### Batch Size

`BATCH_SIZE = 500` controls how many `UpdateOne` operations are accumulated before a `bulk_write` call. This is the primary lever for balancing memory usage against MongoDB round-trip overhead.

| Batch Size | Memory     | Throughput   | Recommended For                        |
| ---------- | ---------- | ------------ | -------------------------------------- |
| 100        | Low        | Slower       | Memory-constrained environments        |
| **500**    | **Medium** | **Balanced** | **Default — production**               |
| 1000       | Higher     | Faster       | High-memory servers, large collections |
| 2000+      | High       | Fastest      | Bulk re-indexing runs only             |

### Elasticsearch Analyzer Tweaks

**Adjusting fuzziness (Persian pipeline):**

```python
# In find_persian_author()
"fuzziness": 1   # Default: allows 1 character edit
"fuzziness": 2   # More lenient: catches more typos, increases false positives
"fuzziness": 0   # Exact match only after normalization
```

**Adjusting score threshold:**

```python
MIN_SCORE_THRESHOLD = 4.0   # Default
MIN_SCORE_THRESHOLD = 6.0   # Stricter: fewer matches, higher precision
MIN_SCORE_THRESHOLD = 2.0   # Looser: more matches, lower precision
```

**Adjusting text similarity (second-tier filter):**

```python
MIN_TEXT_SIMILARITY = 0.20  # Default (permissive — catches normalized variants)
MIN_TEXT_SIMILARITY = 0.60  # Stricter: requires strings to look similar post-normalization
MIN_TEXT_SIMILARITY = 0.80  # Very strict: near-exact match required
```

> **Note:** The comment in the source code states `"باید بالای 80 درصد باشد"` (should be above 80%) but the actual value is `0.20`. This is intentional — after Persian normalization, two strings representing the same name can look quite different (e.g., ZWNJ removal, diacritic stripping). The low threshold acts as a coarse false-positive filter, not a strict similarity gate. Raise it only after profiling your specific dataset.

### ES Bulk Indexing Performance

The `generate_author_actions()` generator streams documents to `helpers.bulk()` without loading the full authors collection into memory. For very large author collections (>500k), consider adding `chunk_size` and `request_timeout` to the bulk call:

```python
helpers.bulk(es, generate_author_actions(), chunk_size=1000, request_timeout=60)
```

### MongoDB Cursor Timeout

Both scripts use `no_cursor_timeout=True` on the books cursor. For collections with millions of documents, the default 10-minute cursor timeout would cause the job to fail mid-run. This flag keeps the cursor alive for the full duration of the job.

---

## 🧩 Edge Cases & Known Behaviors

### Index Rebuild on Every Run

Both scripts **drop and recreate** the Elasticsearch index at startup. This is a deliberate design choice — it guarantees a clean, consistent index state and avoids stale data from previous runs. The trade-off is that the indexing phase adds startup time proportional to the size of the `authors` collection.

_If you need incremental updates, the index creation block must be modified to use `update_by_query` or conditional indexing._

### `$unset` on No Match

When a book has no author strings that pass both validation tiers, the script issues a `$unset` on `AUTHOR_LINKS_FIELD`. This means **re-running the job is safe and idempotent** — previously linked books that no longer match will have their link field removed.

### Deduplication of Persian Transliterations

If `Persian_translitration_1` and `Persian_translitration_2` normalize to the same string, only one ES document is indexed (via Python `set()`). This prevents duplicate hits inflating confidence scores.

### In-Memory Author Cache (Persian)

The full `{ str(_id) → Author }` map is loaded into memory before matching begins. For an `authors` collection with ~100k documents, this is approximately 10–30 MB of RAM — acceptable for a batch job. If the collection grows significantly larger, consider replacing this with a MongoDB `find_one` lookup per match (at the cost of additional DB round-trips).

### Mixed-Type `names_in_main_entry.persian`

The Persian pipeline defensively checks:

```python
if not isinstance(original_name, str) or not original_name.strip():
    continue
```

This handles cases where the array contains `None`, integers, or empty strings from upstream scraping inconsistencies.

### `ordered=False` in `bulk_write`

Both pipelines use `ordered=False`, meaning MongoDB will continue processing the batch even if individual operations fail. Failed operations are logged but do not halt the job. This is the correct behavior for a best-effort linking job.

### Elasticsearch `persian_stop` Filter

The `persian_stop` filter removes common Persian stopwords. This can cause issues if an author's name contains a word that is also a stopword (rare but possible). If you observe systematic misses for specific authors, inspect whether their name tokens are being removed by this filter using the ES Analyze API:

```bash
GET /your_index/_analyze
{
  "analyzer": "persian_custom_analyzer",
  "text": "نام نویسنده مورد نظر"
}
```

---

## 📊 Logging & Monitoring

Both scripts use Python's `RotatingFileHandler` for production-grade, persistent logging alongside real-time console output.

| Property       | Latin                     | Persian                           |
| -------------- | ------------------------- | --------------------------------- |
| Log file       | `logs/author_linking.log` | `logs/author_linking_persian.log` |
| Max file size  | 50 MB                     | 50 MB                             |
| Backup count   | 5                         | 5                                 |
| Console output | ✅                        | ✅                                |
| Encoding       | UTF-8                     | UTF-8                             |

### Log Output Pattern

```
2026-04-15 10:23:41 | INFO | ✅ Elasticsearch connected
2026-04-15 10:23:41 | INFO | ✅ MongoDB connected
2026-04-15 10:23:42 | INFO | 🗑 Deleted old index `bibliograph_authors_persian`
2026-04-15 10:23:43 | INFO | ✅ Index created with custom Persian analyzer
2026-04-15 10:23:55 | INFO | ✅ Indexed 84320 Persian author name variations.
2026-04-15 10:24:01 | INFO | ✅ Loaded 62100 author names into cache.
2026-04-15 10:24:01 | INFO | 🚀 Starting Persian author linking process...
2026-04-15 10:24:12 | INFO | 📊 Processed=500 | Total Links Found=312
2026-04-15 10:24:23 | INFO | 📊 Processed=1000 | Total Links Found=634
...
2026-04-15 10:31:05 | INFO | 🏁 Finished author linking.
2026-04-15 10:31:05 | INFO | Total books processed: 12500
2026-04-15 10:31:05 | INFO | Total individual author links created: 8943
2026-04-15 10:31:05 | INFO | Total time elapsed: 424.18 seconds
```

### Key Metrics to Monitor

- **Links Found / Books Processed ratio** — a sudden drop indicates a threshold misconfiguration or data quality issue.
- **Elapsed time** — baseline this on first run; significant increases suggest index growth or network degradation.
- **`bulk_write` exceptions** — logged at `ERROR` level; investigate immediately as they indicate data loss.

---

## 🏛 Architecture & Code Quality

_This section is intended for technical reviewers and senior engineers evaluating the codebase._

### Design Decisions

**Why rebuild the ES index on every run?**
Guarantees deterministic, reproducible results. The authors collection is the source of truth; the ES index is a derived, disposable artifact. Incremental sync would require change tracking (e.g., MongoDB change streams) which adds significant complexity for a batch job.

**Why a two-tier validation engine?**
Elasticsearch scoring is optimized for recall, not precision. After aggressive Persian normalization and stopword removal, the ES score alone is insufficient to reject false positives. The `difflib.SequenceMatcher` second tier operates on the normalized strings directly — it is language-agnostic, deterministic, and adds negligible overhead (~microseconds per comparison).

**Why `$unset` instead of `$set: []` on no match?**
An empty array `[]` is semantically different from "no linking has been performed." `$unset` removes the field entirely, making it trivial to query for unlinked books: `{ "author_links_persian": { "$exists": false } }`.

**Why `no_cursor_timeout=True`?**
The matching loop includes ES network calls per author string. For a book with 3 author names, that's 3 sequential ES queries before the next MongoDB document is fetched. On large collections, this easily exceeds MongoDB's default 10-minute cursor timeout.

### Identified Technical Debt

| Item                                                | Location                      | Impact                                                                                               |
| --------------------------------------------------- | ----------------------------- | ---------------------------------------------------------------------------------------------------- |
| Hardcoded constants (no `.env` support)             | Top of each script            | Low — acceptable for batch scripts, but `.env` loading via `python-dotenv` would improve portability |
| `MIN_TEXT_SIMILARITY = 0.20` vs. comment saying 80% | `run_job_persian.py` line ~50 | Medium — misleading comment; should be corrected or the value raised after dataset profiling         |
| Sequential ES queries per author string             | `find_persian_author()`       | Medium — for books with many authors, consider batching ES queries using `msearch` API               |
| No retry logic on `bulk_write` failure              | Both scripts                  | Low — failed batches are logged but not retried; data may be silently skipped                        |

### Relationship to Broader Service

```
scraper-service/
├── src/
│   ├── api/          ← FastAPI endpoints (trigger scraping tasks)
│   ├── tasks/        ← Celery tasks (scrape_nlai)
│   ├── scrapers/     ← NLAI scraper implementation
│   └── repositories/ ← MongoDB repositories
└── scripts/
    └── author_linking_job/   ← THIS MODULE
        ├── run_job_latin.py   (post-processing, run after scraping)
        └── run_job_persian.py (post-processing, run after scraping)
```

These scripts are **post-processing jobs**, not part of the real-time scraping pipeline. They are intended to be run after a scraping task completes, either manually or via a scheduled Celery Beat task.

---

## 👤 Author

<table>
  <tr>
    <td align="center">
      <strong>Sina Sotoudeh</strong><br>
      <a href="https://sinasotoudeh.ir">🌐 sinasotoudeh.ir</a><br>
      <a href="https://github.com/sinasotoudeh">🐙 github.com/sinasotoudeh</a><br>
      <a href="https://linkedin.com/in/sinasotoudeh">💼 linkedin.com/in/sinasotoudeh</a><br>
      <a href="mailto:s.sotoudeh1@gmail.com">✉️ s.sotoudeh1@gmail.com</a>
    </td>
  </tr>
</table>

---

<p align="center">
  Part of the <strong>BiblioGraph AI</strong> platform — scraper-service
</p>
