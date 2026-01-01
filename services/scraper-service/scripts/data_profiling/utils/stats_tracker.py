from typing import Dict, Any
from datetime import datetime
from collections import defaultdict


class StreamingStats:
    """محاسبه آماری بدون نگهداری تمام داده‌ها در حافظه"""
    
    def __init__(self):
        self.count = 0
        self.sum = 0.0
        self.min_val = float('inf')
        self.max_val = float('-inf')
        self.sum_squared = 0.0
    
    def add(self, value: float):
        self.count += 1
        self.sum += value
        self.min_val = min(self.min_val, value)
        self.max_val = max(self.max_val, value)
        self.sum_squared += value ** 2
    
    def get_stats(self) -> Dict[str, Any]:
        if self.count == 0:
            return {}
        
        mean = self.sum / self.count
        variance = (self.sum_squared / self.count) - (mean ** 2)
        std = variance ** 0.5 if variance > 0 else 0
        
        return {
            "count": self.count,
            "min": round(self.min_val, 2) if self.min_val != float('inf') else None,
            "max": round(self.max_val, 2) if self.max_val != float('-inf') else None,
            "mean": round(mean, 2),
            "std": round(std, 2)
        }


class DateRangeTracker:
    """ردیابی محدوده تاریخ‌ها"""
    
    def __init__(self):
        self.min_date = None
        self.max_date = None
        self.count = 0
    
    def add(self, date_value: datetime):
        self.count += 1
        if self.min_date is None:
            self.min_date = date_value
            self.max_date = date_value
        else:
            self.min_date = min(self.min_date, date_value)
            self.max_date = max(self.max_date, date_value)
    
    def get_range(self) -> Dict[str, Any]:
        if self.min_date is None:
            return {}
        
        return {
            "min": self.min_date.isoformat(),
            "max": self.max_date.isoformat(),
            "range_days": (self.max_date - self.min_date).days,
            "count": self.count
        }


class UniqueValueTracker:
    """ردیابی unique values با محدودیت حافظه"""
    
    def __init__(self, max_unique: int = 1000):
        self.values = set()
        self.max_unique = max_unique
        self.total_count = 0
        self.overflow = False
    
    def add(self, value):
        self.total_count += 1
        
        if not self.overflow and len(self.values) < self.max_unique:
            self.values.add(str(value))
        elif len(self.values) >= self.max_unique:
            self.overflow = True
    
    # ✅ بدون پارامتر - از self.total_count استفاده می‌کند
    def get_stats(self) -> dict:
        """محاسبه آمار uniqueness"""
        
        unique_count = len(self.values) if not self.overflow else None
        
        # ✅ اصلاح duplicate_rate
        unique_count = len(self.values) if not self.overflow else None

        if self.overflow or unique_count is None:
            duplicate_rate = None # یا یک مقدار پیش‌فرض
        else:
            duplicate_rate = round((1 - (unique_count / self.total_count)) * 100, 2
                                   ) if self.total_count > 0 and unique_count is not None else 0.0
        
        return {
            "unique_count": unique_count,
            "duplicate_rate": duplicate_rate,
            "overflow": self.overflow,
            "total_count": self.total_count,
            "sample_values": list(self.values)[:10]
        }


class FieldMetadata:
    """متادیتای کامل یک فیلد"""
    
    def __init__(self):
        self.occurrence_count = 0
        self.null_count = 0
        self.empty_string_count = 0
        
        self.types = defaultdict(int)
        
        # برای string
        self.string_lengths = StreamingStats()
        
        # برای number
        self.numeric_values = StreamingStats()
        
        # برای datetime
        self.date_range = DateRangeTracker()
        
        # برای array
        self.array_lengths = StreamingStats()
        self.array_element_types = defaultdict(int)
        
        # برای uniqueness
        self.unique_tracker = UniqueValueTracker()
    
    def to_dict(self, total_docs: int) -> Dict[str, Any]:
        result = {
            "occurrence_count": self.occurrence_count,
            "missing_rate": round(1 - (self.occurrence_count / total_docs), 4) if total_docs > 0 else 0,
            "null_count": self.null_count,
            "null_rate": round(self.null_count / self.occurrence_count, 4) if self.occurrence_count > 0 else 0,
            "types": dict(self.types)
        }
        
        # String stats
        if self.string_lengths.count > 0:
            result["string_stats"] = self.string_lengths.get_stats()
            result["empty_string_count"] = self.empty_string_count
            result["empty_string_rate"] = round(
                self.empty_string_count / self.string_lengths.count, 4
            ) if self.string_lengths.count > 0 else 0
        
        # Numeric stats
        if self.numeric_values.count > 0:
            result["numeric_stats"] = self.numeric_values.get_stats()
        
        # Date range
        date_stats = self.date_range.get_range()
        if date_stats:
            result["date_range"] = date_stats
        
        # Array stats
        if self.array_lengths.count > 0:
            result["array_stats"] = {
                "lengths": self.array_lengths.get_stats(),
                "element_types": dict(self.array_element_types)
            }
        
        # Uniqueness - ✅ بدون پارامتر
        unique_stats = self.unique_tracker.get_stats()
        if unique_stats["total_count"] > 0:
            result["uniqueness"] = unique_stats
        
        return result
