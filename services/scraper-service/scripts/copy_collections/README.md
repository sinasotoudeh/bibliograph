<div align="center">

# 🗂️ MongoDB Collection Copy Utility

**A safe, interactive, and fully-validated MongoDB collection cloning script**
_Part of the [BiblioGraph AI](https://github.com/sinasotoudeh) post-processing pipeline_

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![MongoDB](https://img.shields.io/badge/MongoDB-PyMongo_4.6-47A248?style=flat-square&logo=mongodb&logoColor=white)](https://pymongo.readthedocs.io/)
[![Type](https://img.shields.io/badge/Type-Standalone_Script-orange?style=flat-square)]()
[![Pipeline Stage](https://img.shields.io/badge/Pipeline_Stage-Post--Processing-blueviolet?style=flat-square)]()
[![Author](https://img.shields.io/badge/Author-Sina_Sotoudeh-0A66C2?style=flat-square)](https://sinasotoudeh.ir)

</div>

---

## 📌 Table of Contents

- [Overview](#-overview)
- [Role in the BiblioGraph AI Pipeline](#-role-in-the-bibliograph-ai-pipeline)
- [How It Works](#-how-it-works)
- [Design & Architecture](#-design--architecture)
- [Configuration Reference](#️-configuration-reference)
- [Execution & Output](#-execution--output)
- [Validation Logic](#-validation-logic)
- [Safety Guarantees](#-safety-guarantees)
- [Quick Start](#-quick-start)
- [Project Structure](#-project-structure)
- [Author](#-author)

---

## 🔍 Overview

`copy_collection.py` is a **standalone, interactive Python script** for safely cloning one MongoDB collection into another within the same database. It is designed for **controlled, human-supervised data operations** — not automated pipelines — and enforces a strict four-phase execution model with confirmation gates between each phase.

### ✨ Key Features

- **Interactive confirmation gates** — requires explicit `Enter` keypress before each destructive or irreversible step
- **Configurable document filtering** — supports arbitrary MongoDB query filters via `SOURCE_QUERY` to copy a subset of documents
- **`_id` remapping** — strips the original `_id` to let MongoDB generate new ones, while preserving the source `_id` in a named field for full traceability
- **`pipeline_state` injection** — stamps every copied document with a configurable flag inside a `pipeline_state` subdocument, enabling downstream pipeline tracking
- **Batched writes** — processes documents in configurable batches (`BATCH_SIZE = 1000`) to avoid memory pressure on large collections
- **Three-layer post-copy validation** — verifies count integrity, `_id` reference presence, and uniqueness of source IDs in the target
- **Fail-fast error handling** — any anomaly triggers an immediate `sys.exit(1)` with a descriptive error message

---

## 🔗 Role in the BiblioGraph AI Pipeline

This script occupies the **post-processing** stage of the BiblioGraph AI data pipeline. It is typically run **after** a scraping or enrichment job has completed and **before** a downstream processing stage (such as author linking or data profiling) that requires a clean, isolated working copy of the data.

```text
┌─────────────────────────────────────────────────────────────────────┐
│                    BiblioGraph AI Data Pipeline                     │
└─────────────────────────────────────────────────────────────────────┘

  [1] Scraper Service (Celery)
       └─► Writes raw book records to MongoDB
            └─► Collection: books_raw

  [2] copy_collection.py  ◄─── YOU ARE HERE
       └─► Clones books_raw → books_processing
            ├─► Preserves source _id as nlai_id (or configured field)
            ├─► Injects pipeline_state.ready_for_linking = True
            └─► Validates copy integrity before proceeding

  [3] Author Linking Jobs (run_job_latin.py / run_job_persian.py)
       └─► Reads from books_processing
            └─► Matches authors via Elasticsearch + difflib

  [4] Data Profiling Engine (scripts/data_profiling/run.py)
       └─► Profiles books_processing or books_final
            └─► Generates quality score & schema drift report
```

> **Why a copy instead of in-place mutation?**
> The scraper writes to a canonical source collection. Downstream enrichment jobs (author linking, NLP tagging) mutate documents heavily. Cloning preserves the raw source as an immutable audit trail and allows re-running enrichment from scratch without re-scraping.

---

## ⚙️ How It Works

The script executes in four sequential phases, each separated by an interactive confirmation prompt:

```text
Phase 1: CONNECT
  └─► Establish MongoClient connection
  └─► Optionally create target collection (with existence guard)

        ── Press Enter to continue ──

Phase 2: PRE-CHECKS
  └─► Count total source documents
  └─► Count documents matching SOURCE_QUERY
  └─► Count existing documents in target
  └─► Abort if query matches 0 documents

        ── Press Enter to continue ──

Phase 3: COPY
  └─► Open no_cursor_timeout cursor on source
  └─► For each document:
        ├─► Strip _id → store in SOURCE_ID_FIELD_NAME
        ├─► Inject pipeline_state.{FIELD} = VALUE
        └─► Accumulate into batch → insert_many (ordered=False)
  └─► Verify copied count == source_selected

        ── Press Enter to continue ──

Phase 4: VALIDATION
  └─► Check: target docs with pipeline_state flag == source_selected
  └─► Check: no target doc missing SOURCE_ID_FIELD_NAME
  └─► Check: SOURCE_ID_FIELD_NAME values are unique (no duplicates)
  └─► Print final summary
```

---

## 🏗 Design & Architecture

### Design Principles

This script is intentionally **not** a library or a class — it is a **procedural, top-to-bottom execution script** designed for one-shot, supervised use by a developer or data engineer. This is a deliberate choice:

- **Transparency over abstraction** — every step is visible and auditable in the terminal output
- **Fail-fast over resilience** — the `fatal()` helper calls `sys.exit(1)` immediately on any anomaly, preventing partial or corrupt states
- **Human-in-the-loop** — `wait_for_confirmation()` gates prevent accidental execution of destructive steps

### `_id` Remapping Strategy

MongoDB's `_id` field is immutable and unique per collection. When copying documents:

```python
target_doc = doc.copy()
target_doc.pop("_id")                          # Remove original _id
target_doc[SOURCE_ID_FIELD_NAME] = src_id      # Preserve it in a named field
# MongoDB auto-generates a new _id on insert
```

This produces documents in the target that have:

- A **new** `_id` (MongoDB-generated `ObjectId`) — unique within the target collection
- A **`SOURCE_ID_FIELD_NAME`** field (e.g., `nlai_id`) — the original source `_id`, enabling bidirectional traceability

### `pipeline_state` Injection

Every copied document receives a structured `pipeline_state` subdocument:

```python
state = target_doc.get("pipeline_state", {})
state[PIPELINE_STATE_FIELD] = PIPELINE_STATE_VALUE
target_doc["pipeline_state"] = state
```

This is **non-destructive** — if a `pipeline_state` dict already exists on the source document, it is preserved and the new key is merged in. This design is consistent with how the author linking jobs (`run_job_latin.py`, `run_job_persian.py`) read and write `pipeline_state` flags to track processing progress.

### Batched Writes with `ordered=False`

```python
target_col.insert_many(batch, ordered=False, session=session)
```

`ordered=False` allows MongoDB to continue inserting remaining documents in a batch even if one fails (e.g., a duplicate key error). Combined with the pre-copy existence guard, this maximises throughput while the validation phase catches any anomalies after the fact.

### Session Usage

The entire copy loop runs inside a `client.start_session()` context. While this does not provide multi-document ACID transactions (which would require a replica set), it ensures the cursor and write operations share a consistent server session, improving cursor stability on long-running copies.

---

## 🛠️ Configuration Reference

All configuration is done by editing the constants at the top of the script. There are no CLI arguments or environment variables.

| Parameter                  | Type   | Default | Description                                                                                   |
| -------------------------- | ------ | ------- | --------------------------------------------------------------------------------------------- |
| `MONGO_URI`                | `str`  | `""`    | Full MongoDB connection string (e.g., `mongodb://user:pass@host:27017`)                       |
| `DB_NAME`                  | `str`  | `""`    | Target database name                                                                          |
| `SOURCE_COLLECTION`        | `str`  | `""`    | Name of the source collection to copy from                                                    |
| `TARGET_COLLECTION`        | `str`  | `""`    | Name of the destination collection                                                            |
| `TARGET_COLLECTION_EXISTS` | `bool` | `False` | Set `True` to allow writing into an existing collection; `False` enforces a clean-slate guard |
| `SOURCE_ID_FIELD_NAME`     | `str`  | `""`    | Field name in the target doc where the source `_id` will be stored (e.g., `"nlai_id"`)        |
| `SOURCE_QUERY`             | `dict` | `{}`    | MongoDB filter query. `{}` copies all documents. Example: `{"status": "published"}`           |
| `PIPELINE_STATE_FIELD`     | `str`  | `""`    | Key to set inside `pipeline_state` (e.g., `"ready_for_linking"`)                              |
| `PIPELINE_STATE_VALUE`     | `any`  | `True`  | Value to assign to `PIPELINE_STATE_FIELD`                                                     |
| `BATCH_SIZE`               | `int`  | `1000`  | Number of documents per `insert_many` call                                                    |

### Example Configuration

```python
MONGO_URI = "mongodb://admin:secret@localhost:27017"
DB_NAME = "bibliograph_db"

SOURCE_COLLECTION = "books_raw"
TARGET_COLLECTION = "books_processing"

TARGET_COLLECTION_EXISTS = False
SOURCE_ID_FIELD_NAME = "nlai_id"

SOURCE_QUERY = {"pipeline_state.scraped": True}

PIPELINE_STATE_FIELD = "ready_for_linking"
PIPELINE_STATE_VALUE = True

BATCH_SIZE = 1000
```

This configuration copies all scraped books from `books_raw` into a fresh `books_processing` collection, preserving the original `_id` as `nlai_id` and flagging each document as ready for the author linking job.

---

## 🖥 Execution & Output

### Running the Script

```bash
# From the repository root
cd services/scraper-service

python scripts/copy_collections/copy_collection.py
```

> **No virtual environment?** Install the single dependency first:
>
> ```bash
> pip install pymongo==4.6.0
> ```

### Terminal Output Walkthrough

```text
🔌 Connecting to MongoDB ...
📦 Creating target collection: books_processing
✅ Connected successfully

📊 Pre-check statistics:
Source collection total docs     : 120450
Source docs matching query       : 98320
Target collection existing docs  : 0

================================================================================
✅ Pre-checks completed
Press Enter to continue...

🚚 Starting copy process ...
✅ Copy finished | Copied docs: 98320

================================================================================
✅ Copy step completed
Press Enter to continue...

🔍 Validation phase started ...
Target docs with pipeline_state flag: 98320
✅ All validations passed successfully

🎉 Copy operation completed successfully.
Source collection : books_raw
Target collection : books_processing
Copied documents  : 98320
```

### Error Output Example

```text
❌ ERROR: Target collection 'books_processing' already exists
```

```text
❌ ERROR: Copied count mismatch: copied=98319, expected=98320
```

All errors exit with code `1`, making the script safe to use in shell pipelines or CI scripts that check exit codes.

---

## ✅ Validation Logic

After the copy phase, three independent checks run automatically:

### Check 1 — Count Integrity

```python
copied_docs_count = target_col.count_documents({
    f"pipeline_state.{PIPELINE_STATE_FIELD}": PIPELINE_STATE_VALUE
})
assert copied_docs_count == source_selected
```

Verifies that the number of documents carrying the new `pipeline_state` flag exactly matches the number of documents selected from the source. Guards against silent partial writes.

### Check 2 — Source ID Presence

```python
missing_source_id = target_col.count_documents({
    SOURCE_ID_FIELD_NAME: {"$exists": False}
})
assert missing_source_id == 0
```

Ensures every copied document has the `SOURCE_ID_FIELD_NAME` field populated. A missing field would break traceability back to the source collection.

### Check 3 — Source ID Uniqueness

```python
duplicates = target_col.aggregate([
    {"$match": {f"pipeline_state.{PIPELINE_STATE_FIELD}": PIPELINE_STATE_VALUE}},
    {"$group": {"_id": f"${SOURCE_ID_FIELD_NAME}", "count": {"$sum": 1}}},
    {"$match": {"count": {"$gt": 1}}}
])
assert len(list(duplicates)) == 0
```

Detects duplicate source IDs in the target, which would indicate a document was copied more than once — a critical data integrity violation.

---

## 🛡 Safety Guarantees

| Scenario                                                              | Behaviour                              |
| --------------------------------------------------------------------- | -------------------------------------- |
| Target collection already exists (`TARGET_COLLECTION_EXISTS = False`) | `fatal()` — aborts before any write    |
| Source query matches 0 documents                                      | `fatal()` — aborts before any write    |
| Source document has no `_id`                                          | `fatal()` — aborts mid-copy            |
| Copied count ≠ expected count                                         | `fatal()` — aborts before validation   |
| Any document missing `SOURCE_ID_FIELD_NAME`                           | `fatal()` — caught in validation       |
| Duplicate source IDs detected                                         | `fatal()` — caught in validation       |
| Existing `pipeline_state` on source doc                               | Preserved and merged — not overwritten |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- `pymongo==4.6.0` (`pip install pymongo==4.6.0`)
- Network access to the target MongoDB instance

### Steps

**1. Edit the configuration block at the top of the script:**

```python
MONGO_URI = "mongodb://user:pass@host:27017"
DB_NAME = "bibliograph_db"
SOURCE_COLLECTION = "books_raw"
TARGET_COLLECTION = "books_processing"
TARGET_COLLECTION_EXISTS = False
SOURCE_ID_FIELD_NAME = "nlai_id"
SOURCE_QUERY = {}
PIPELINE_STATE_FIELD = "ready_for_linking"
PIPELINE_STATE_VALUE = True
BATCH_SIZE = 1000
```

**2. Run the script:**

```bash
python scripts/copy_collections/copy_collection.py
```

**3. Follow the interactive prompts** — review the pre-check statistics and press `Enter` at each gate to proceed.

**4. Verify the output** — the final summary confirms the source collection, target collection, and exact document count copied.

> **Windows (PowerShell):**
>
> ```powershell
> cd C:\Users\sinas\bibliograph-ai\services\scraper-service
> python scripts\copy_collections\copy_collection.py
> ```

---

## 📂 Project Structure

```text
scripts/copy_collections/
│
└── copy_collection.py      # Self-contained copy & validation script

**Related scripts in the same pipeline:**

text
scripts/
├── copy_collections/
│   └── copy_collection.py          ◄── This script (post-processing gate)
│
├── author_linking_job/
│   ├── run_job_latin.py            ← Reads from target collection
│   ├── run_job_persian.py          ← Reads from target collection
│   └── README.md
│
└── data_profiling/
    ├── run.py                      ← Profiles target collection
    └── README.md
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
<sub>BiblioGraph AI · Scraper Service · Post-Processing Utilities</sub>
</div>
