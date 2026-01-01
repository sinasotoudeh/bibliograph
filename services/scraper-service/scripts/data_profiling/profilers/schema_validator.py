from typing import Dict, Any, Type, List
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class SchemaValidator:
    """مقایسه profiling واقعی با Pydantic schemas"""
    
    def __init__(self):
        self.logger = logger
    
    def validate_against_schema(
        self,
        profile: Dict[str, Any],
        schema_class: Type[BaseModel]
    ) -> Dict[str, Any]:
        """
        مقایسه profile با Pydantic model
        
        Returns:
            گزارش schema drift
        """
        
        collection_name = profile["collection"]
        profiled_fields = set(profile["fields"].keys())
        
        # استخراج فیلدهای required از Pydantic
        required_fields = []
        optional_fields = []
        
        for field_name, field_info in schema_class.model_fields.items():
            if field_info.is_required():
                required_fields.append(field_name)
            else:
                optional_fields.append(field_name)
        
        # پیدا کردن مشکلات
        missing_required = []
        high_missing_rate = []
        type_mismatches = []
        
        for required_field in required_fields:
            if required_field not in profiled_fields:
                missing_required.append(required_field)
            else:
                field_profile = profile["fields"][required_field]
                missing_rate = field_profile.get("missing_rate", 0)
                
                # اگر فیلد required است اما missing rate بالا دارد
                if missing_rate > 0.05:  # بیش از 5%
                    high_missing_rate.append({
                        "field": required_field,
                        "missing_rate": missing_rate,
                        "severity": "critical" if missing_rate > 0.20 else "warning"
                    })
        
        # فیلدهای اضافی در DB که در schema نیست
        schema_fields = set(required_fields + optional_fields)
        extra_fields = profiled_fields - schema_fields
        
        # محاسبه schema compliance score
        total_required = len(required_fields)
        issues_count = len(missing_required) + len(high_missing_rate)
        
        if total_required > 0:
            compliance_score = max(0, 100 - (issues_count / total_required * 100))
        else:
            compliance_score = 100
        
        return {
            "collection": collection_name,
            "schema_class": schema_class.__name__,
            "compliance_score": round(compliance_score, 2),
            "required_fields_count": len(required_fields),
            "optional_fields_count": len(optional_fields),
            "missing_required_fields": missing_required,
            "high_missing_rate_fields": high_missing_rate,
            "extra_fields_in_db": list(extra_fields),
            "validated_at": profile["profiled_at"]
        }
