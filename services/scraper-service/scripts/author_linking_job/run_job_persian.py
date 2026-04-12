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
import difflib

# =====================================================
# Logging configuration (UNCHANGED)
# =====================================================
LOG_FILE = "logs/author_linking_persian.log"

logger = logging.getLogger("author_linking_persian")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

# Avoid adding handlers multiple times if script is re-run in an interactive session
if not logger.handlers:
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=50_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

# =====================================================
# Constants (UPDATED)
# =====================================================
MONGO_URI = ""
ES_HOST = ""

DB_NAME = ""
AUTHORS_COLLECTION = ""
BOOKS_COLLECTION = ""

# New index name for Persian authors
INDEX_NAME = ""
BATCH_SIZE = 500
MIN_SCORE_THRESHOLD = 4.0  # Minimum score to consider a match valid
MIN_TEXT_SIMILARITY = 0.20 # تطبیق متنی باید بالای 80 درصد باشد (فیلتر نهایی)
AUTHOR_LINKS_FIELD = "" # Field to store matched author data in MongoDB

# =====================================================
# Normalization Function (CRITICAL NEW PART)
# =====================================================
def normalize_persian_text(text):
    """
    Applies the same normalization rules as the Elasticsearch analyzer.
    This symmetry is crucial for accurate matching.
    """
    if not isinstance(text, str):
        return ""
    # 1. Character normalization (Arabic to Persian)
    text = text.replace('ي', 'ی').replace('ك', 'ک')
    text = text.replace('آ', 'ا').replace('أ', 'ا').replace('إ', 'ا')
    text = text.replace('ئ', 'ی').replace('ؤ', 'و')
    # 2. Remove diacritics (fatha, kasra, etc.) and hidden chars
    text = re.sub(r'[\u064B-\u065F\u0670]', '', text)
    # 3. Replace half-space with standard space
    text = text.replace('\u200c', ' ')
    # 4. Remove all punctuation except spaces
    text = re.sub(r'[^\w\s]', ' ', text)
    # 5. Normalize multiple spaces to a single space
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# =====================================================
# 1️⃣ Connectivity checks (UNCHANGED)
# =====================================================
try:
    es = Elasticsearch(ES_HOST, timeout=30)
    if es.ping():
        logger.info("✅ Elasticsearch connected")
    else:
        logger.error("❌ Elasticsearch ping failed")
        sys.exit(1)
except Exception as e:
    logger.exception("❌ Elasticsearch connection error")
    sys.exit(1)

logger.info("-" * 50)

try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_client.admin.command("ping")
    logger.info("✅ MongoDB connected")
except Exception as e:
    logger.exception("❌ MongoDB connection error")
    sys.exit(1)

# =====================================================
# 2️⃣ Index creation & author indexing (COMPLETELY REVISED)
# =====================================================
db = mongo_client[DB_NAME]
authors_collection = db[AUTHORS_COLLECTION]

# New settings with a powerful custom Persian analyzer
settings = {
    "settings": {
        "analysis": {
            "char_filter": {
                "persian_char_normalizer": {
                    "type": "mapping",
                    "mappings": [
                        "ي => ی", "ك => ک", "آ => ا", "أ => ا",
                        "إ => ا", "ئ => ی", "ؤ => و",
                    ]
                },
                "punctuation_and_half_space_remover": {
                    "type": "pattern_replace",
                    # Removes all non-letter, non-digit chars, and converts half-space to space
                    "pattern": "[\\u200c]|[\\p{P}\\p{S}]",
                    "replacement": " "
                }
            },
            "filter": {
                # This filter helps remove diacritics
                "persian_stop": {
                    "type": "stop",
                    "stopwords": "_persian_"
                }
            },
            "analyzer": {
                "persian_custom_analyzer": {
                    "type": "custom",
                    "char_filter": [
                        "persian_char_normalizer",
                        "punctuation_and_half_space_remover"
                    ],
                    "tokenizer": "standard",
                    "filter": [
                        "lowercase",
                        "arabic_normalization", # Removes Tatweel and most diacritics
                        "persian_normalization",
                        "persian_stop"
                    ]
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "mongo_id": {"type": "keyword"},
            "persian_name": {
                "type": "text",
                "analyzer": "persian_custom_analyzer",
                "search_analyzer": "persian_custom_analyzer"
            }
        }
    }
}

try:
    if es.indices.exists(index=INDEX_NAME):
        es.indices.delete(index=INDEX_NAME)
        logger.info(f"🗑 Deleted old index `{INDEX_NAME}`")

    es.indices.create(index=INDEX_NAME, body=settings)
    logger.info(f"✅ Index `{INDEX_NAME}` created with custom Persian analyzer")
except Exception:
    logger.exception("❌ Index creation failed")
    sys.exit(1)


def generate_author_actions():
    """
    Generates actions for bulk indexing from the new Persian fields,
    with normalization and deduplication.
    """
    for doc in authors_collection.find(
        {
            "$or": [
                {"Persian_translitration_1": {"$exists": True, "$ne": ""}},
                {"Persian_translitration_2": {"$exists": True, "$ne": ""}}
            ]
        },
        {"_id": 1, "Persian_translitration_1": 1, "Persian_translitration_2": 1}
    ):
        
        normalized_names = set()
        
        # Get and normalize both transliterations
        name1 = doc.get("Persian_translitration_1")
        if name1:
            normalized_names.add(normalize_persian_text(name1))
            
        name2 = doc.get("Persian_translitration_2")
        if name2:
            normalized_names.add(normalize_persian_text(name2))
            
        # Yield a document for each unique, non-empty normalized name
        for name in normalized_names:
            if name: # Ensure the name is not empty after normalization
                yield {
                    "_index": INDEX_NAME,
                    "_source": {
                        "mongo_id": str(doc["_id"]),
                        "persian_name": name
                    }
                }

logger.info("🚀 Indexing Persian author names...")
try:
    success, failed = helpers.bulk(es, generate_author_actions())
    if failed:
        logger.error(f"❌ Failed to index {len(failed)} documents.")
    logger.info(f"✅ Indexed {success} Persian author name variations.")
except Exception:
    logger.exception("❌ Error during author indexing")
    sys.exit(1)
# =====================================================
# 0️⃣ Pre-load Author Names for fast lookups (NEW SECTION)
# =====================================================
logger.info("- Pre-loading author names from MongoDB into memory...")
author_name_map = {}
try:
    # We only need the _id and the original Author name
    author_cursor = authors_collection.find({}, {"_id": 1, "Author": 1})
    for author_doc in author_cursor:
        # Store as string for easy dictionary lookup
        author_name_map[str(author_doc["_id"])] = author_doc.get("Author", "N/A")
    logger.info(f"✅ Loaded {len(author_name_map)} author names into cache.")
except Exception as e:
    logger.exception("❌ Failed to pre-load author names from MongoDB.")
    sys.exit(1)
# =====================================================
# 3️⃣ Author matching & Update (COMPLETELY REVISED)
# =====================================================
books_collection = db[BOOKS_COLLECTION]
processed = 0
total_links_found = 0
updates = []

def get_text_similarity(str1, str2):
    """
    محاسبه درصد شباهت دو رشته بین 0 تا 1
    """
    return difflib.SequenceMatcher(None, str1, str2).ratio()

def find_persian_author(author_name):
    """
    Searches for a single normalized Persian author name.
    Returns the highest-scoring hit if it meets the threshold.
    """
    if not author_name:
        return None

    query = {
        "size": 1,
        "query": {
            "match": {
                "persian_name": {
                    "query": author_name,
                    "operator": "and",
                    "fuzziness": 1 # Allows 1 character errors
                }
            }
        }
    }
    
    try:
        res = es.search(index=INDEX_NAME, body=query)
        hits = res["hits"]["hits"]
        if hits and hits[0]["_score"] >= MIN_SCORE_THRESHOLD:
            return hits[0]
    except Exception as e:
        logger.error(f"Error searching for '{author_name}': {e}")

    return None

logger.info("🚀 Starting Persian author linking process...")

# Query for books that have the target field as a non-empty array
cursor = books_collection.find({
    "names_in_main_entry.persian": {"$exists": True, "$not": {"$size": 0}}
}, {"_id": 1, "names_in_main_entry.persian": 1},
no_cursor_timeout=True
)

start_time = time.time()

for book in cursor:
    author_names_from_book = book.get("names_in_main_entry", {}).get("persian", [])
    
    # This list will hold all successful matches for this one book
    found_links = []

    if isinstance(author_names_from_book, list):
        for original_name in author_names_from_book:
            if not isinstance(original_name, str) or not original_name.strip():
                continue
                
            normalized_name = normalize_persian_text(original_name)
            hit = find_persian_author(normalized_name)

            if hit:
                # === SAFETY CHECK (لایه امنیتی پایتون) ===
                matched_es_name = hit["_source"]["persian_name"]
                similarity = get_text_similarity(normalized_name, matched_es_name)
                
                # اگر شباهت کمتر از 80٪ بود، حتی با وجود مچ شدن در ES، آن را دور بریز
                if similarity < MIN_TEXT_SIMILARITY:
                # برای دیباگ می‌توانید لاگ کنید که چه چیزهایی رد شده‌اند
                # logger.warning(f"⚠️ Rejected match: '{normalized_search_name}' vs '{matched_es_name}' (Score: {hit['_score']}, Sim: {similarity:.2f})")
                    continue
                # ========================================
                # A match was found for this specific author name
                author_mongo_id_str = hit["_source"]["mongo_id"]
                # Use the pre-loaded map to get the original name
                # Provide a fallback just in case the ID is not in the map
                original_author_name = author_name_map.get(author_mongo_id_str, hit["_source"]["persian_name"])
                link_data = {
                    "name_from_book": original_name,
                    "matched_persian_name": hit["_source"]["persian_name"],
                    "ref_author_id": ObjectId(hit["_source"]["mongo_id"]),
                    "matched_name": original_author_name,
                    "confidence_score": hit["_score"],
                    "text_similarity": similarity
                }
                found_links.append(link_data)
                total_links_found += 1
    
    # After checking all names for the book, decide whether to $set or $unset
    if found_links:
        # At least one author was linked, update the document
        updates.append(UpdateOne(
            {"_id": book["_id"]},
            {"$set": {AUTHOR_LINKS_FIELD: found_links}}
        ))
    else:
        # No authors were linked, ensure the field is removed
        updates.append(UpdateOne(
            {"_id": book["_id"]},
            {"$unset": {AUTHOR_LINKS_FIELD: ""}}
        ))

    # Perform bulk write when batch size is reached
    if len(updates) >= BATCH_SIZE:
        try:
            books_collection.bulk_write(updates, ordered=False)
            processed += len(updates)
            updates = []
            logger.info(f"📊 Processed={processed} | Total Links Found={total_links_found}")
        except Exception as e:
            logger.exception("❌ MongoDB bulk_write failed")

# Flush any remaining updates
if updates:
    try:
        books_collection.bulk_write(updates, ordered=False)
        processed += len(updates)
    except Exception as e:
        logger.exception("❌ MongoDB final bulk_write failed")


elapsed = time.time() - start_time
logger.info("🏁 Finished author linking.")
logger.info(f"Total books processed: {processed}")
logger.info(f"Total individual author links created: {total_links_found}")
logger.info(f"Total time elapsed: {elapsed:.2f} seconds")