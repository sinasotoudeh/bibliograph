#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from elasticsearch import Elasticsearch, helpers
from pymongo import MongoClient, UpdateOne
from bson import ObjectId
import logging
from logging.handlers import RotatingFileHandler
import sys
import time
import re
import unicodedata

# =====================================================
# Logging configuration (FAST & production-safe)
# =====================================================
LOG_FILE = "logs/author_linking.log"

logger = logging.getLogger("author_linking")
logger.setLevel(logging.INFO)

formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(message)s"
)

file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=50_000_000,
    backupCount=5,
    encoding="utf-8"
)
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# =====================================================
# Constants
# =====================================================
MONGO_URI = ""
ES_HOST = ""

DB_NAME = ""
AUTHORS_COLLECTION = ""
BOOKS_COLLECTION = ""

INDEX_NAME = ""
BATCH_SIZE = 500

# =====================================================
# 1️⃣ Connectivity checks
# =====================================================
try:
    es = Elasticsearch(ES_HOST)
    if es.ping():
        logger.info("✅ Elasticsearch connected")
        logger.info(f"Elasticsearch version: {es.info()['version']['number']}")
    else:
        logger.error("❌ Elasticsearch ping failed")
        sys.exit(1)
except Exception:
    logger.exception("❌ Elasticsearch connection error")
    sys.exit(1)

logger.info("-" * 50)

try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
    mongo_client.admin.command("ping")
    logger.info("✅ MongoDB connected")
except Exception:
    logger.exception("❌ MongoDB connection error")
    sys.exit(1)

# =====================================================
# 2️⃣ Index creation & author indexing
# =====================================================
db = mongo_client[DB_NAME]
authors_collection = db[AUTHORS_COLLECTION]

settings = {
    "settings": {
        "analysis": {
            "char_filter": {
                "punctuation_remover": {
                    "type": "pattern_replace",
                    "pattern": "[^\\p{L}\\p{Nd}\\s]",
                    "replacement": " "
                }
            },
            "analyzer": {
                "latin_name_analyzer": {
                    "type": "custom",
                    "char_filter": ["punctuation_remover"],
                    "tokenizer": "standard",
                    "filter": ["lowercase", "asciifolding"]
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "mongo_id": {"type": "keyword"},
            "latin_name": {
                "type": "text",
                "analyzer": "latin_name_analyzer",
                "search_analyzer": "latin_name_analyzer"
            }
        }
    }
}

try:
    if es.indices.exists(index=INDEX_NAME):
        es.indices.delete(index=INDEX_NAME)
        logger.info(f"🗑 Deleted index `{INDEX_NAME}`")

    es.indices.create(index=INDEX_NAME, body=settings)
    logger.info(f"✅ Index `{INDEX_NAME}` created")
except Exception:
    logger.exception("❌ Index creation failed")
    sys.exit(1)

def generate_actions():
    for doc in authors_collection.find({}):
        author_name = doc.get("Author")
        if not author_name:
            continue
        yield {
            "_index": INDEX_NAME,
            "_source": {
                "mongo_id": str(doc["_id"]),
                "latin_name": author_name
            }
        }

logger.info("🚀 Indexing authors...")
try:
    success, _ = helpers.bulk(es, generate_actions())
    logger.info(f"✅ Indexed authors: {success}")
except Exception:
    logger.exception("❌ Error during author indexing")
    sys.exit(1)

# =====================================================
# 3️⃣ Author matching (FINAL VERSION)
# =====================================================
books_collection = db[BOOKS_COLLECTION]

processed = 0
linked = 0
updates = []

# ---------- Normalization (exactly aligned with ES analyzer) ----------
PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)

def normalize_latin_name(name: str) -> str:
    if not name:
        return ""
    name = unicodedata.normalize("NFKD", name)
    name = PUNCT_RE.sub(" ", name)
    name = name.lower()
    name = " ".join(name.split())
    return name

# ---------- Elasticsearch matching ----------
def find_author_top3(normalized_name: str):
    if not normalized_name or len(normalized_name.split()) < 2:
        return []
    tokens = normalized_name.split()
    last_token = tokens[-1]
    query = {
        "size": 3,
        "query": {
            "bool": {
                "must": {
                    "match": {
                        "latin_name": {
                            "query": normalized_name,
                            "operator": "and",
                            "fuzziness": 1,
                            "prefix_length": 2
                        }
                    }
                },
                "should": [
                    {
                        "match": {
                            "latin_name": {
                                "query": last_token,
                                "boost": 2
                            }
                        }
                    }
                ]
            }
        }
    }

    res = es.search(index=INDEX_NAME, body=query)
    return res["hits"]["hits"]
logger.info("🚀 Start multi-author strict linking...")

cursor = books_collection.find({
    "extracted_add_authors.latin": {
        "$exists": True,
        "$type": "array",
        "$ne": []
    }
})

start_time = time.time()

for book in cursor:
    raw_names = book["extracted_add_authors"]["latin"]
    author_links = []

    for raw_name in raw_names:
        normalized = normalize_latin_name(raw_name)
        hits = find_author_top3(normalized)

        if not hits:
            continue

        matches = []
        for rank, hit in enumerate(hits, start=1):
            matches.append({
                "rank": rank,
                "ref_author_id": ObjectId(hit["_source"]["mongo_id"]),
                "matched_name": hit["_source"]["latin_name"],
                "confidence_score": hit["_score"]
            })


        author_links.append({
            "input_latin": raw_name,
            "normalized_latin": normalized,
            "matches": matches
        })

        linked += 1

    if author_links:
        updates.append(UpdateOne(
            {"_id": book["_id"]},
            {"$set": {"author_links": author_links}}
        ))
    else:
        updates.append(UpdateOne(
            {"_id": book["_id"]},
            {"$unset": {"author_links": ""}}
        ))

    if len(updates) >= BATCH_SIZE:
        books_collection.bulk_write(updates)
        processed += len(updates)
        updates = []
        logger.info(f"📊 processed={processed} | linked={linked}")

# Flush باقی‌مانده
if updates:
    books_collection.bulk_write(updates)
    processed += len(updates)

elapsed = time.time() - start_time
logger.info("🏁 Finished")
logger.info(f"Total processed books: {processed}")
logger.info(f"Total linked author strings: {linked}")
logger.info(f"Elapsed time: {elapsed:.2f} sec")
