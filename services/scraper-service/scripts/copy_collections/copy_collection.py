# =========================
# CONFIGURATION (EDIT HERE)
# =========================

MONGO_URI = ""
DB_NAME = ""

SOURCE_COLLECTION = ""
TARGET_COLLECTION = ""

# آیا کالکشن مقصد از قبل وجود دارد؟
TARGET_COLLECTION_EXISTS = False  # True / False

# نام فیلدی که _id مبدا در مقصد با آن ذخیره می‌شود
SOURCE_ID_FIELD_NAME = ""

# کویری انتخاب اسناد از مبدا
# اگر None باشد، همه اسناد کپی می‌شوند
SOURCE_QUERY = {}

# مقدار جدید pipeline_state
PIPELINE_STATE_FIELD = ""
PIPELINE_STATE_VALUE = True

BATCH_SIZE = 1000


# =========================
# IMPORTS
# =========================

from pymongo import MongoClient
from pymongo.errors import BulkWriteError
from pprint import pprint
import sys


# =========================
# HELPERS
# =========================

def wait_for_confirmation(message):
    print("\n" + "=" * 80)
    print(message)
    input("Press Enter to continue...")


def fatal(msg):
    print(f"\n❌ ERROR: {msg}")
    sys.exit(1)


# =========================
# STEP 1: CONNECT
# =========================

print("🔌 Connecting to MongoDB ...")
client = MongoClient(MONGO_URI)
db = client[DB_NAME]

source_col = db[SOURCE_COLLECTION]

if not TARGET_COLLECTION_EXISTS:
    if TARGET_COLLECTION in db.list_collection_names():
        fatal(f"Target collection '{TARGET_COLLECTION}' already exists")
    print(f"📦 Creating target collection: {TARGET_COLLECTION}")
    db.create_collection(TARGET_COLLECTION)

target_col = db[TARGET_COLLECTION]

print("✅ Connected successfully")


# =========================
# STEP 2: PRE-CHECKS
# =========================

source_total = source_col.count_documents({})
source_selected = source_col.count_documents(SOURCE_QUERY)

target_existing = target_col.count_documents({})

print("\n📊 Pre-check statistics:")
print(f"Source collection total docs     : {source_total}")
print(f"Source docs matching query       : {source_selected}")
print(f"Target collection existing docs  : {target_existing}")

if source_selected == 0:
    fatal("No documents matched SOURCE_QUERY")

wait_for_confirmation("✅ Pre-checks completed")


# =========================
# STEP 3: COPY PROCESS
# =========================

print("\n🚚 Starting copy process ...")

with client.start_session() as session:
    cursor = source_col.find(
        SOURCE_QUERY,
        no_cursor_timeout=True,
        session=session
    )

    batch = []
    copied = 0

    try:
        for doc in cursor:
            src_id = doc.get("_id")

            if src_id is None:
                fatal("Source document without _id detected")

            target_doc = doc.copy()
            target_doc.pop("_id")

            # store original _id
            target_doc[SOURCE_ID_FIELD_NAME] = src_id

            # handle pipeline_state
            state = target_doc.get("pipeline_state")
            if not isinstance(state, dict):
                state = {}

            state[PIPELINE_STATE_FIELD] = PIPELINE_STATE_VALUE
            target_doc["pipeline_state"] = state

            batch.append(target_doc)

            if len(batch) >= BATCH_SIZE:
                target_col.insert_many(batch, ordered=False, session=session)
                copied += len(batch)
                batch.clear()

        if batch:
            target_col.insert_many(batch, ordered=False, session=session)
            copied += len(batch)

    finally:
        cursor.close()

print(f"✅ Copy finished | Copied docs: {copied}")

if copied != source_selected:
    fatal(
        f"Copied count mismatch: copied={copied}, expected={source_selected}"
    )

wait_for_confirmation("✅ Copy step completed")


# =========================
# STEP 4: VALIDATION
# =========================

print("\n🔍 Validation phase started ...")

# 1. فقط اسنادی که pipeline_state جدید دارند
copied_docs_count = target_col.count_documents({
    f"pipeline_state.{PIPELINE_STATE_FIELD}": PIPELINE_STATE_VALUE
})

print(f"Target docs with pipeline_state flag: {copied_docs_count}")

if copied_docs_count != source_selected:
    fatal(
        "Mismatch between source query count and copied pipeline_state docs"
    )

# 2. نبودن فیلد ارجاع به مبدا
missing_source_id = target_col.count_documents({
    f"pipeline_state.{PIPELINE_STATE_FIELD}": PIPELINE_STATE_VALUE,
    SOURCE_ID_FIELD_NAME: {"$exists": False}
})

if missing_source_id != 0:
    fatal(f"{missing_source_id} docs without {SOURCE_ID_FIELD_NAME}")

# 3. چک یکتا بودن source id ها در مقصد
duplicates = target_col.aggregate([
    {
        "$match": {
            f"pipeline_state.{PIPELINE_STATE_FIELD}": PIPELINE_STATE_VALUE
        }
    },
    {
        "$group": {
            "_id": f"${SOURCE_ID_FIELD_NAME}",
            "count": {"$sum": 1}
        }
    },
    {
        "$match": {"count": {"$gt": 1}}
    }
])

dups = list(duplicates)

if dups:
    fatal(f"Duplicate source IDs found: {len(dups)}")

print("✅ All validations passed successfully")


# =========================
# FINISH
# =========================

print("\n🎉 Copy operation completed successfully.")
print(f"Source collection : {SOURCE_COLLECTION}")
print(f"Target collection : {TARGET_COLLECTION}")
print(f"Copied documents  : {copied}")
