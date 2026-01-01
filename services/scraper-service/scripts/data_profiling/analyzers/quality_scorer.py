from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class DataQualityScorer:
    """محاسبه امتیاز کیفیت داده (0-100)"""
    
    def __init__(self):
        self.logger = logger
    
    def calculate_collection_score(
        self,
        profile: Dict[str, Any],
        schema_validation: Dict[str, Any],
        relationship_check: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        محاسبه امتیاز کلی کیفیت یک collection
        
        امتیاز از 4 بخش تشکیل می‌شود:
        1. Completeness (40%) - میزان پر بودن فیلدها
        2. Validity (30%) - مطابقت با schema
        3. Consistency (20%) - consistency داده‌ها
        4. Integrity (10%) - روابط صحیح
        """
        
        # 1. Completeness Score
        completeness = self._calculate_completeness(profile)
        
        # 2. Validity Score
        validity = schema_validation.get("compliance_score", 0)
        
        # 3. Consistency Score
        consistency = self._calculate_consistency(profile)
        
        # 4. Integrity Score
        integrity = relationship_check.get("integrity_score", 100) if relationship_check else 100
        
        # محاسبه امتیاز وزن‌دار
        total_score = (
            completeness * 0.40 +
            validity * 0.30 +
            consistency * 0.20 +
            integrity * 0.10
        )
        
        # تعیین grade
        grade = self._determine_grade(total_score)
        
        return {
            "collection": profile["collection"],
            "overall_score": round(total_score, 2),
            "grade": grade,
            "dimensions": {
                "completeness": {
                    "score": round(completeness, 2),
                    "weight": "40%"
                },
                "validity": {
                    "score": round(validity, 2),
                    "weight": "30%"
                },
                "consistency": {
                    "score": round(consistency, 2),
                    "weight": "20%"
                },
                "integrity": {
                    "score": round(integrity, 2),
                    "weight": "10%"
                }
            },
            "issues_summary": self._summarize_issues(
                profile, schema_validation, relationship_check
            )
        }
    
    def _calculate_completeness(self, profile: Dict[str, Any]) -> float:
        """محاسبه completeness بر اساس missing rates"""
        
        fields = profile.get("fields", {})
        if not fields:
            return 0
        
        total_missing_rate = 0
        field_count = 0
        
        for field_data in fields.values():
            missing_rate = field_data.get("missing_rate", 0)
            total_missing_rate += missing_rate
            field_count += 1
        
        avg_missing_rate = total_missing_rate / field_count if field_count > 0 else 0
        
        # تبدیل به امتیاز (هرچه missing کمتر، امتیاز بیشتر)
        completeness_score = (1 - avg_missing_rate) * 100
        
        return max(0, completeness_score)
    
    def _calculate_consistency(self, profile: Dict[str, Any]) -> float:
        """محاسبه consistency بر اساس type uniformity و empty values"""
        
        fields = profile.get("fields", {})
        if not fields:
            return 0
        
        scores = []
        
        for field_data in fields.values():
            # بررسی تک‌نوع بودن
            types = field_data.get("types", {})
            if types:
                dominant_type_count = max(types.values())
                total_count = sum(types.values())
                type_consistency = dominant_type_count / total_count if total_count > 0 else 0
            else:
                type_consistency = 1.0
            
            # بررسی empty string rate
            empty_rate = field_data.get("empty_string_rate", 0)
            empty_score = 1 - empty_rate
            
            # میانگین
            field_score = (type_consistency * 0.7 + empty_score * 0.3) * 100
            scores.append(field_score)
        
        return sum(scores) / len(scores) if scores else 0
    
    def _determine_grade(self, score: float) -> str:
        """تعیین رتبه بر اساس امتیاز"""
        if score >= 90:
            return "A (Excellent)"
        elif score >= 80:
            return "B (Good)"
        elif score >= 70:
            return "C (Fair)"
        elif score >= 60:
            return "D (Poor)"
        else:
            return "F (Critical)"
    
    def _summarize_issues(
        self,
        profile: Dict[str, Any],
        schema_validation: Dict[str, Any],
        relationship_check: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """خلاصه مشکلات یافت شده"""
        
        issues = {
            "critical": [],
            "warnings": [],
            "info": []
        }
        
        # مشکلات schema
        missing_required = schema_validation.get("missing_required_fields", [])
        if missing_required:
            issues["critical"].append(
                f"{len(missing_required)} required fields missing in DB"
            )
        
        high_missing = schema_validation.get("high_missing_rate_fields", [])
        for field_info in high_missing:
            severity = field_info.get("severity", "warning")
            msg = f"Field '{field_info['field']}' has {field_info['missing_rate']*100:.1f}% missing rate"
            
            if severity == "critical":
                issues["critical"].append(msg)
            else:
                issues["warnings"].append(msg)
        
        # مشکلات relationship
        if relationship_check:
            orphan_rate = relationship_check.get("orphan_rate", 0)
            if orphan_rate > 0.10:
                issues["warnings"].append(
                    f"{orphan_rate*100:.1f}% of records are orphaned"
                )
            
            invalid_rate = relationship_check.get("invalid_rate", 0)
            if invalid_rate > 0.05:
                issues["critical"].append(
                    f"{invalid_rate*100:.1f}% of records have invalid references"
                )
        
        return issues
