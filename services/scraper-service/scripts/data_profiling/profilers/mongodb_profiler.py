# services/scraper-service/scripts/data_profiling/profilers/mongodb_profiler.py

from typing import Dict, Any, Optional
from collections import defaultdict
from datetime import datetime
from bson import ObjectId
import logging
import sys
from pathlib import Path

# اضافه کردن parent directory به sys.path
script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

from utils.stats_tracker import FieldMetadata

logger = logging.getLogger(__name__)

class MongoDBProfiler:
    """پروفایلر پیشرفته برای MongoDB با قابلیت‌های تولید صنعتی"""
    
    def __init__(self, mongodb_client):
        self.db = mongodb_client.get_database()
        self.logger = logger
        self.MAX_UNIQUE_TRACKING = 10000 
    
    async def profile_collection(
        self,
        collection_name: str,
        sample_size: Optional[int] = None,
        use_random_sampling: bool = True
    ) -> Dict[str, Any]:
        
        collection = self.db[collection_name]
        total_count = await collection.count_documents({})
        
        if total_count == 0:
            return {
                "collection": collection_name,
                "total_documents": 0,
                "documents_sampled": 0,
                "error": "Collection is empty"
            }
        
        actual_sample_size = min(sample_size or total_count, total_count)
        
        self.logger.info(
            f"Profiling {collection_name}: "
            f"total={total_count}, sample={actual_sample_size}, "
            f"random={use_random_sampling}"
        )
        
        if use_random_sampling and sample_size and sample_size < total_count:
            cursor = collection.aggregate([{"$sample": {"size": actual_sample_size}}])
        else:
            cursor = collection.find({}).limit(actual_sample_size)
        
        field_metadata: Dict[str, FieldMetadata] = defaultdict(FieldMetadata)
        documents_sampled = 0
        
        async for doc in cursor:
            documents_sampled += 1
            self._process_document(doc, field_metadata)
            if documents_sampled % 1000 == 0:
                self.logger.info(f"Processed {documents_sampled} documents...")
        
        profile = self._finalize_profile(
            collection_name=collection_name,
            total_documents=total_count,
            documents_sampled=documents_sampled,
            field_metadata=field_metadata,
            actual_sample_size=actual_sample_size,
            use_random_sampling=use_random_sampling
        )
        
        return profile
    
    def _process_document(self, doc: Dict[str, Any], field_metadata: Dict[str, FieldMetadata], prefix: str = ""):
        for key, value in doc.items():
            field_path = f"{prefix}.{key}" if prefix else key
            meta = field_metadata[field_path]
            
            meta.occurrence_count += 1
            
            if value is None:
                meta.null_count += 1
                meta.types["null"] += 1
                continue
            
            value_type = type(value).__name__
            meta.types[value_type] += 1
            
            # ✅ FIX: هندل کردن خطای TypeError: has no len()
            def safe_add_unique(val):
                tracker = meta.unique_tracker
                should_add = True
                
                # تلاش برای چک کردن سایز فعلی برای جلوگیری از پر شدن حافظه
                try:
                    # حالت ۱: کلاس استاندارد که len دارد
                    if len(tracker) >= self.MAX_UNIQUE_TRACKING:
                        should_add = False
                except TypeError:
                    # حالت ۲: کلاس کاستوم که len ندارد (مثل کلاس شما)
                    # چک می‌کنیم آیا ویژگی values دارد؟ (معمولا در wrapper ها وجود دارد)
                    if hasattr(tracker, 'values') and hasattr(tracker.values, '__len__'):
                        if len(tracker.values) >= self.MAX_UNIQUE_TRACKING:
                            should_add = False
                    else:
                        # حالت ۳: هیچ راهی برای فهمیدن سایز نیست
                        # بیخیال محدودیت می‌شویم و اضافه می‌کنیم (بهتر از کرش کردن است)
                        pass

                if should_add:
                    tracker.add(val)

            if isinstance(value, ObjectId):
                safe_add_unique(str(value))
            
            elif isinstance(value, str):
                meta.string_lengths.add(len(value))
                if value == "":
                    meta.empty_string_count += 1
                if self._is_important_field(field_path):
                    safe_add_unique(value)
            
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                meta.numeric_values.add(float(value))
                if self._is_important_field(field_path):
                    safe_add_unique(value)
            
            elif isinstance(value, datetime):
                meta.date_range.add(value)
            
            elif isinstance(value, bool):
                safe_add_unique(value)
            
            elif isinstance(value, list):
                meta.array_lengths.add(len(value))
                for item in value:
                    item_type = type(item).__name__ if item is not None else "null"
                    meta.array_element_types[item_type] += 1
                
                if len(value) > 0 and isinstance(value[0], ObjectId):
                    for obj_id in value:
                        safe_add_unique(str(obj_id))
            
            elif isinstance(value, dict):
                self._process_document(value, field_metadata, prefix=field_path)
    
    def _is_important_field(self, field_path: str) -> bool:
        important_keywords = ["_id", "nlai_id", "isbn", "nlai_permalink"]
        return any(keyword in field_path.lower() for keyword in important_keywords)
    
    def _finalize_profile(
        self,
        collection_name: str,
        total_documents: int,
        documents_sampled: int,
        field_metadata: Dict[str, FieldMetadata],
        actual_sample_size: int,
        use_random_sampling: bool
    ) -> Dict[str, Any]:
        
        fields = {}
        for field_path, meta in field_metadata.items():
            fields[field_path] = meta.to_dict(documents_sampled)
        
        sorted_fields = dict(sorted(fields.items(), key=lambda x: x[1]["occurrence_count"], reverse=True))
        
        return {
            "collection": collection_name,
            "total_documents": total_documents,
            "documents_sampled": documents_sampled,
            "actual_sample_size": actual_sample_size,
            "sampling_method": "random ($sample)" if use_random_sampling else "sequential",
            "total_distinct_fields": len(sorted_fields),
            "all_field_name_counts": {
                field: data["occurrence_count"] 
                for field, data in sorted_fields.items()
            },
            "fields": sorted_fields,
            "profiled_at": datetime.utcnow().isoformat()
        }
