# services/scraper-service/scripts/data_profiling/run.py

import asyncio
import json
from pathlib import Path
from datetime import datetime
import logging
import sys
from dotenv import load_dotenv

script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
sys.path.insert(0, str(project_root))

# Load Env
env_path = script_dir / ".env.profiler"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv(script_dir.parent.parent / ".env")

from src.core.database.mongodb import mongodb_client
from src.schemas.book import BookInDB

from profilers.mongodb_profiler import MongoDBProfiler
from profilers.schema_validator import SchemaValidator
# relationship_checker را نگه می‌داریم اما هوشمندانه استفاده می‌کنیم
from analyzers.quality_scorer import DataQualityScorer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
OUTPUT_DIR = Path(__file__).parent / "reports" / run_id
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

async def profile_single_collection(
    profiler: MongoDBProfiler,
    validator: SchemaValidator,
    scorer: DataQualityScorer,
    collection_name: str,
    schema_class,
    sample_size: int = None,
    relationship_check: dict = None
):
    logger.info(f"\n{'='*60}\nProfiling: {collection_name}\n{'='*60}")
    
    # 1. Profile
    profile = await profiler.profile_collection(collection_name, sample_size, True)
    
    # Save Profile
    with open(OUTPUT_DIR / f"{collection_name}_profile.json", 'w', encoding='utf-8') as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)
    
    # 2. Validate
    schema_validation = validator.validate_against_schema(profile, schema_class)
    with open(OUTPUT_DIR / f"{collection_name}_schema_validation.json", 'w', encoding='utf-8') as f:
        json.dump(schema_validation, f, indent=2, ensure_ascii=False)
    
    # 3. Score
    quality_score = scorer.calculate_collection_score(profile, schema_validation, relationship_check)
    with open(OUTPUT_DIR / f"{collection_name}_quality_score.json", 'w', encoding='utf-8') as f:
        json.dump(quality_score, f, indent=2, ensure_ascii=False)
    
    return {
        "collection": collection_name,
        "profile": profile,
        "schema_validation": schema_validation,
        "quality_score": quality_score
    }

async def main():
    start_time = datetime.utcnow()
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info("\n" + "="*80 + "\n🚀 MONGODB DATA PROFILING - BOOKS ONLY RUN\n" + "="*80)
    
    try:
        await mongodb_client.connect()
        logger.info("✓ MongoDB connected successfully")
        
        profiler = MongoDBProfiler(mongodb_client)
        validator = SchemaValidator()
        scorer = DataQualityScorer()
        
        results = {}
        
        # ==========================================
        # 1️⃣ BOOKS COLLECTION (ONLY)
        # ==========================================
        
        # نکته: Relationship Check را موقتاً غیرفعال می‌کنیم
        # چون در حالت "فقط بوک"، بررسی رفرنس به نویسنده‌ها (که شاید نباشند)
        # باعث ایجاد خطاهای کاذب (False Positives) در گزارش می‌شود.
        books_relationship = None 
        # اگر دیتای Authors دارید، خط زیر را از کامنت درآورید:
        # from profilers.relationship_checker import RelationshipChecker
        # checker = RelationshipChecker(mongodb_client)
        # books_relationship = await checker.check_book_author_integrity()

        try:
            result = await profile_single_collection(
                profiler=profiler,
                validator=validator,
                scorer=scorer,
                collection_name="books",
                schema_class=BookInDB,
                sample_size=None,
                relationship_check=books_relationship
            )
            results["books"] = result
        except Exception as e:
            logger.error(f"❌ Failed to profile books: {str(e)}", exc_info=True)
            raise

        # ==========================================
        # 📊 SUMMARY REPORT
        # ==========================================
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        summary_report = {
            "metadata": {
                "started_at": start_time.isoformat(),
                "duration_seconds": round(duration, 2),
                "scope": "books_only"
            },
            "results": {
                name: {
                    "docs": res['profile']['total_documents'],
                    "score": res['quality_score']['overall_score'],
                    "grade": res['quality_score']['grade']
                } for name, res in results.items()
            }
        }
        
        with open(OUTPUT_DIR / "summary_report.json", 'w', encoding='utf-8') as f:
            json.dump(summary_report, f, indent=2, ensure_ascii=False)
            
        logger.info("\n" + "="*80)
        logger.info("✅ PROFILING COMPLETED")
        logger.info(f"📂 Reports: {OUTPUT_DIR.absolute()}")
        logger.info("="*80 + "\n")

    except Exception as e:
        logger.error(f"FATAL ERROR: {e}", exc_info=True)
    finally:
        await mongodb_client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
