# 🔗 Author Linking Job (Bibliograph AI)

## 📌 Overview
The **Author Linking Job** is a core component of the Scraper Service for Bibliograph AI. It is responsible for bridging the gap between raw extracted book data and the standardized authors' database. 

By utilizing **MongoDB** for data persistence and **Elasticsearch (ES)** for advanced fuzzy text matching, these scripts autonomously read unlinked author strings from scraped books, normalize the text, find the most statistically relevant author entities, and establish relational links within the database.

This module contains two distinct pipelines optimized for different linguistic characteristics:
1. `run_job_latin.py`: For Latin-based scripts (English, European languages).
2. `run_job_persian.py`: For Arabic-script languages (Persian, Arabic) with complex morphological normalization.

---

## 🏗 System Architecture & Workflow

Both scripts follow a robust, fault-tolerant ETL (Extract, Transform, Load) pattern:

1. **Connectivity Validation:** Ensures stable connections to both MongoDB and Elasticsearch.
2. **Elasticsearch Indexing:** Rebuilds an optimized search index and bulk-indexes author names from the master `authors` collection.
3. **Data Retrieval:** Iterates through the `books` collection where unlinked author fields exist.
4. **Normalization & Querying:** Cleans the raw input string and queries Elasticsearch.
5. **Evaluation & Matching:** Evaluates the returned Elasticsearch documents based on scoring algorithms and secondary mathematical validations.
6. **Bulk Updating:** Writes the linked author metadata back to the MongoDB `books` collection in batches ($BatchSize = 500$) to optimize memory and network I/O.

---

## 📜 Script Specifications

### 1. Latin Author Linking (`run_job_latin.py`)
Designed to handle standard Latin character sets, accounting for punctuation, case variances, and standard typographical errors.

*   **Target Field:** `extracted_add_authors.latin`
*   **Text Processing:** 
    *   Implements a custom ES analyzer (`latin_name_analyzer`).
    *   Utilizes a `pattern_replace` char filter to strip all punctuation: `[^\p{L}\p{Nd}\s]`.
    *   Applies `asciifolding` to normalize characters (e.g., `é` $\rightarrow$ `e`).
*   **Search Algorithm:**
    *   Executes an Elasticsearch `bool` query.
    *   **MUST clause:** Requires a match with a Levenshtein edit distance of $Fuzziness = 1$ and a $PrefixLength = 2$.
    *   **SHOULD clause:** Isolates the last token (typically the surname) and applies a query boost ($Boost = 2.0$) to prioritize correct surname matching.
*   **Output:** Returns and stores the Top 3 probable matches for manual or automated downstream review.

### 2. Persian Author Linking (`run_job_persian.py`)
A highly specialized pipeline engineered to overcome the complexities of the Persian/Arabic alphabet, including varying Unicode representations, diacritics (Erab), and zero-width non-joiners (ZWNJ).

*   **Target Field:** `names_in_main_entry.persian`
*   **Advanced Normalization:**
    *   **Character Unification:** Standardizes Arabic specific letters to Persian (e.g., `ي` $\rightarrow$ `ی`, `ك` $\rightarrow$ `ک`).
    *   **Diacritic Removal:** Strips all Arabic/Persian vowel marks (Fatha, Kasra, Damma, etc.).
    *   **ZWNJ Handling:** Converts half-spaces (`\u200c`) to standard spaces to ensure consistent tokenization.
*   **Indexing Strategy:** Indexes up to two transliterations (`Persian_translitration_1`, `Persian_translitration_2`), deduplicating them at runtime via Python `set()` before pushing to Elasticsearch.
*   **In-Memory Caching:** Pre-loads the MongoDB `_id` and `Author` names into a Python dictionary. This provides $O(1)$ lookup time during the matching phase, drastically reducing database read operations.
*   **Two-Tier Validation Engine:**
    1.  **Elasticsearch Base Score:** Only processes matches where $Score \ge 4.0$.
    2.  **Algorithmic Verification:** Implements a secondary Python-side validation using `difflib.SequenceMatcher`. Calculates the ratio of text similarity. The match is **rejected** if the similarity ratio is less than the threshold ($Similarity < 0.20$), effectively eliminating false positives caused by aggressive Elasticsearch stemming.
*   **Output:** Stores the single highest-confidence match per author string.

---

## ⚙️ Configuration & Execution

### Prerequisites
*   Python 3.8+
*   Elasticsearch 7.x or 8.x
*   MongoDB 4.x+
*   Required Python packages: `elasticsearch`, `pymongo`, `bson`

### Environment Setup
Before executing the scripts, ensure the constants at the top of each file are correctly populated with your environment variables:
```python
MONGO_URI = "mongodb://user:pass@host:port"
ES_HOST = "http://host:port"
DB_NAME = "bibliograph_db"
AUTHORS_COLLECTION = "authors"
BOOKS_COLLECTION = "books"
INDEX_NAME = "your_target_es_index"

### Running the Jobs
Run the scripts directly from the terminal:
bash
# Run Latin linking job
python scripts/author_linking_job/run_job_latin.py

# Run Persian linking job
python scripts/author_linking_job/run_job_persian.py

---

## 📊 Logging & Monitoring
Both scripts employ production-grade logging utilizing `RotatingFileHandler`. 
*   **Log Locations:** `logs/author_linking.log` & `logs/author_linking_persian.log`
*   **Rotation Policy:** Maximum file size of $50 MB$ with a backup count of $5$.
*   **Stdout:** Real-time progress is also streamed to the console, detailing processing speeds, database connection statuses, and periodic batch update metrics.
