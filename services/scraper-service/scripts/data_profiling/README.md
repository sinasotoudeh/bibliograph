run command:
cd C:\Users\sinas\bibliograph-ai\services\scraper-service

docker-compose -f docker-compose.scraper.yml `
  -f ..\..\infrastructure\docker\docker-compose.dev.yml `
  run --rm --no-deps `
  -v ".\scripts:/app/scripts" `
  scraper-api `
  python scripts/data_profiling/run.py


چطور Sample Size را تغییر دهیم؟

# در run.py
result = await profile_single_collection(
    collection_name="books",
    schema_class=BookInDB,
    sample_size=10000,  # 🔴 تغییر از 5000 به 10000
    # ...
)

چطور فیلدهای مهم را تغییر دهیم؟

# در mongodb_profiler.py
def _is_important_field(self, field_path: str) -> bool:
    important_keywords = [
        "_id", "id", "isbn", "doi",
        "title",  # ➕ اضافه کردن
        "email"   # ➕ اضافه کردن
    ]
    return any(keyword in field_path.lower() for keyword in important_keywords)


چطور تمام دیتا را بررسی کنیم (بدون Sampling)?

# در run.py
result = await profile_single_collection(
    collection_name="books",
    sample_size=None,  # 🔴 None = همه document ها
    # ...
)

review this

 # توضیح کامل متریک‌ها و آمار در سیستم Data Profiling

این سیستم یک **پروفایلر جامع کیفیت داده** برای MongoDB است که چندین لایه تحلیل دارد.

---

## 1️⃣ **MongoDBProfiler** - متریک‌های پروفایلینگ پایه

### خروجی کلی Collection:

```python
{
  "collection": "books",
  "total_documents": 10000,           # تعداد کل اسناد در collection
  "documents_sampled": 5000,          # تعداد اسنادی که بررسی شده‌اند
  "actual_sample_size": 5000,         # سایز نمونه واقعی
  "sampling_method": "random",        # روش نمونه‌گیری (تصادفی یا ترتیبی)
  "total_distinct_fields": 25,        # تعداد فیلدهای یکتای یافت شده
  "profiled_at": "2026-01-01T10:30:00" # زمان پروفایل
}
```

### متریک‌های هر Field:

```python
"fields": {
  "title": {
    "occurrence_count": 4950,        # تعداد دفعاتی که این فیلد وجود داشته
    "occurrence_rate": 0.99,         # درصد حضور (4950/5000)
    "missing_rate": 0.01,            # درصد غیبت (50/5000)
    
    "null_count": 10,                # تعداد مقادیر null
    "null_rate": 0.002,              # درصد null نسبت به کل
    
    "types": {                       # توزیع انواع داده
      "str": 4940,
      "null": 10
    },
    "dominant_type": "str",          # نوع غالب
    "type_consistency": 0.998,       # یکنواختی نوع (4940/4950)
    
    # برای فیلدهای رشته‌ای:
    "empty_string_count": 5,         # تعداد رشته‌های خالی ""
    "empty_string_rate": 0.001,      # نسبت رشته‌های خالی
    
    "string_length_stats": {
      "min": 5,
      "max": 250,
      "avg": 45.3
    },
    
    "unique_values_sample": ["Book1", "Book2", ...], # نمونه مقادیر یکتا (حداکثر 100)
    "estimated_cardinality": 4800    # تخمین تعداد مقادیر یکتا
  }
}
```

### متریک‌های خاص برای انواع مختلف:

#### **فیلدهای عددی:**
```python
"price": {
  "numeric_stats": {
    "min": 10.5,
    "max": 250.0,
    "mean": 89.3,
    "median": 75.0
  }
}
```

#### **فیلدهای تاریخ:**
```python
"created_at": {
  "date_range": {
    "earliest": "2020-01-01T00:00:00",
    "latest": "2026-01-01T00:00:00"
  }
}
```

#### **فیلدهای آرایه‌ای:**
```python
"author_ids": {
  "array_length_stats": {
    "min": 0,
    "max": 5,
    "avg": 1.8
  },
  "array_element_types": {       # انواع عناصر داخل آرایه
    "ObjectId": 8900,
    "null": 100
  }
}
```

---

## 2️⃣ **RelationshipChecker** - متریک‌های یکپارچگی روابط

### Book-Author Integrity:

```python
{
  "relationship": "books → authors",
  "integrity_score": 85.5,           # امتیاز یکپارچگی (0-100)
  
  "total_books": 10000,
  "total_authors": 3500,
  
  # کتاب‌های بدون نویسنده:
  "orphan_books_count": 250,
  "orphan_rate": 0.025,              # 2.5% کتاب‌ها نویسنده ندارند
  
  # کتاب‌هایی با رفرنس اشتباه:
  "books_with_invalid_authors": 100,
  "invalid_author_references_count": 150,
  "invalid_rate": 0.01,              # 1% رفرنس‌های نامعتبر
  
  "sample_orphan_books": ["id1", "id2", ...],
  "sample_invalid_references": [
    {
      "book_id": "66abc...",
      "invalid_author_id": "55xyz..."
    }
  ]
}
```

**فرمول Integrity Score:**
```python
integrity_score = 100 - (orphan_rate × 50 + invalid_rate × 50)
```

### Scraping Log Integrity:

```python
{
  "collection": "scraping_logs",
  "integrity_score": 92.0,
  
  "total_logs": 5000,
  "logs_without_task_id": 200,
  "missing_task_id_rate": 0.04,     # 4% بدون task_id
  
  "duplicate_task_ids_count": 50,
  "duplicate_rate": 0.01,            # 1% تکراری
  
  "unique_task_ids": 4750
}
```

**فرمول Integrity Score:**
```python
integrity_score = 100 - (missing_task_id_rate × 60 + duplicate_rate × 40)
```

---

## 3️⃣ **SchemaValidator** - متریک‌های انطباق با Schema

```python
{
  "collection": "books",
  "schema_class": "BookInDB",
  "compliance_score": 88.5,          # امتیاز انطباق (0-100)
  
  "required_fields_count": 8,        # تعداد فیلدهای اجباری در schema
  "optional_fields_count": 12,       # تعداد فیلدهای اختیاری
  
  # فیلدهای اجباری که در DB نیستند:
  "missing_required_fields": ["isbn", "publisher"],
  
  # فیلدهای اجباری با missing rate بالا:
  "high_missing_rate_fields": [
    {
      "field": "title",
      "missing_rate": 0.15,          # 15% از اسناد ندارند
      "severity": "warning"          # یا "critical" اگر >20%
    }
  ],
  
  # فیلدهای اضافی در DB که در schema نیستند:
  "extra_fields_in_db": ["legacy_id", "temp_field"]
}
```

**فرمول Compliance Score:**
```python
issues_count = len(missing_required) + len(high_missing_rate)
compliance_score = max(0, 100 - (issues_count / total_required × 100))
```

---

## 4️⃣ **DataQualityScorer** - امتیاز کیفیت جامع

### Overall Score (وزن‌دار از 4 بُعد):

```python
{
  "collection": "books",
  "overall_score": 82.3,             # امتیاز کلی (0-100)
  "grade": "B (Good)",               # رتبه‌بندی
  
  "dimensions": {
    "completeness": {                # میزان پر بودن فیلدها
      "score": 85.0,
      "weight": "40%"
    },
    "validity": {                    # مطابقت با schema
      "score": 88.5,
      "weight": "30%"
    },
    "consistency": {                 # یکنواختی داده‌ها
      "score": 75.0,
      "weight": "20%"
    },
    "integrity": {                   # صحت روابط
      "score": 80.0,
      "weight": "10%"
    }
  }
}
```

**فرمول Overall Score:**
```python
overall_score = (
    completeness × 0.40 +
    validity × 0.30 +
    consistency × 0.20 +
    integrity × 0.10
)
```

### محاسبه هر بُعد:

#### **1. Completeness (40%):**
```python
# میانگین missing_rate تمام فیلدها
avg_missing = sum(field.missing_rate for field in fields) / len(fields)
completeness = (1 - avg_missing) × 100
```

#### **2. Validity (30%):**
```python
# مستقیماً از SchemaValidator می‌آید
validity = schema_validation.compliance_score
```

#### **3. Consistency (20%):**
```python
# برای هر فیلد:
type_consistency = dominant_type_count / total_count
empty_score = 1 - empty_string_rate
field_score = (type_consistency × 0.7 + empty_score × 0.3) × 100

# میانگین تمام فیلدها:
consistency = mean(field_scores)
```

#### **4. Integrity (10%):**
```python
# از RelationshipChecker می‌آید (اگر موجود باشد، وگرنه 100)
integrity = relationship_check.integrity_score
```

### رتبه‌بندی (Grade):
- **A (Excellent)**: 90-100
- **B (Good)**: 80-89
- **C (Fair)**: 70-79
- **D (Poor)**: 60-69
- **F (Critical)**: 0-59

### خلاصه مشکلات:

```python
"issues_summary": {
  "critical": [
    "2 required fields missing in DB",
    "5.0% of records have invalid references"
  ],
  "warnings": [
    "Field 'description' has 15.0% missing rate",
    "10.5% of records are orphaned"
  ],
  "info": []
}
```

---

## 5️⃣ **Summary Report** - گزارش نهایی

```python
{
  "metadata": {
    "started_at": "2026-01-01T10:00:00",
    "duration_seconds": 125.5,
    "scope": "books_only"
  },
  "results": {
    "books": {
      "docs": 10000,
      "score": 82.3,
      "grade": "B (Good)"
    }
  }
}
```

---

## 📊 تفسیر عملی:

- **occurrence_rate < 0.95** → فیلد مشکل دارد
- **null_rate > 0.10** → 10% null - نیاز به بررسی
- **type_consistency < 0.90** → نوع داده یکنواخت نیست
- **empty_string_rate > 0.05** → رشته‌های خالی زیاد
- **orphan_rate > 0.10** → 10% بدون رابطه - مشکل جدی
- **overall_score < 70** → کیفیت داده پایین - نیاز به اقدام فوری


or read this

---

## 1️⃣ MongoDBProfiler – متریک‌های پروفایل داده

این بخش **واقعیت داده‌های موجود در MongoDB** را بدون توجه به schema بررسی می‌کند.

### ✅ متریک‌های سطح Collection

در فایل `<collection>_profile.json`:

| فیلد | معنی |
|-----|-----|
| `collection` | نام collection |
| `total_documents` | تعداد کل اسناد در MongoDB |
| `documents_sampled` | تعداد واقعی اسنادی که بررسی شده‌اند |
| `actual_sample_size` | min(sample_size, total_documents) |
| `sampling_method` | `random ($sample)` یا `sequential` |
| `total_distinct_fields` | تعداد فیلدهای یکتای شناسایی‌شده (flatten شده) |
| `profiled_at` | زمان اجرای profiling (UTC) |

📌 **نکته مهم**  
فیلدها به صورت **flatten** ذخیره می‌شوند:
```json
author.name
author.birth_date
publisher.address.city
```

---

### ✅ متریک‌های سطح Field (مهم‌ترین بخش)

هر ورودی داخل `fields` یک فیلد دیتابیس است.

### 1. `occurrence_count`

```json
"occurrence_count": 4321
```

**معنی:**  
این فیلد در چند سند از نمونه دیده شده است.

📌 اگر:
- `occurrence_count < documents_sampled` → فیلد اختیاری یا داده ناقص
- `occurrence_count ≈ documents_sampled` → فیلد پایدار

---

### 2. `missing_rate`

```json
"missing_rate": 0.134
```

**فرمول:**
```
1 - (occurrence_count / documents_sampled)
```

**معنی:**  
در چه درصدی از اسناد، این فیلد وجود نداشته یا null بوده است.

| مقدار | تفسیر |
|-----|-----|
| < 5% | عالی |
| 5–20% | هشدار |
| > 20% | بحرانی (برای required ها) |

---

### 3. `null_count`

```json
"null_count": 220
```

**معنی:**  
چند بار مقدار field صراحتاً `null` بوده (نه missing).

📌 تفاوت مهم:
- missing = فیلد وجود ندارد
- null = فیلد وجود دارد ولی مقدار ندارد

---

### 4. `types`

```json
"types": {
  "str": 4100,
  "int": 120,
  "null": 220
}
```

**معنی:**  
توزیع نوع داده‌ای که واقعاً در DB ذخیره شده.

📌 کاربرد:
- تشخیص type drift
- محاسبه consistency

---

### 5. `unique_count` (غیرمستقیم)

از طریق:
```python
meta.unique_tracker
```

**معنی:**  
تعداد مقادیر یکتای فیلد (با سقف 10,000).

📌 فقط برای فیلدهای مهم:
- `_id`, `isbn`, `doi`, `code`, `key`

---

### 6. متریک‌های متنی (String)

#### `string_length_stats`
(از `string_lengths`)

- min
- max
- avg

📌 برای:
- تشخیص truncate شدن
- تشخیص داده‌های غیرعادی

---

#### `empty_string_count` + `empty_string_rate`

```json
"empty_string_rate": 0.08
```

**معنی:**  
چند درصد stringها مقدار `""` دارند (داده بد).

---

### 7. متریک‌های عددی (Numeric)

از `numeric_values`:

- min
- max
- avg

📌 برای کشف:
- outlier
- مقدارهای غیرمنطقی

---

### 8. متریک‌های تاریخ (Datetime)

```json
"date_range": {
  "min": "1992-01-01",
  "max": "2024-05-12"
}
```

📌 کاربرد:
- sanity check
- کشف داده‌های future یا ancient

---

### 9. آرایه‌ها (Array)

#### `array_lengths`
- min, max, avg طول آرایه

#### `array_element_types`
```json
{
  "ObjectId": 980,
  "null": 10,
  "str": 3
}
```

📌 برای تشخیص:
- آرایه ناهمگون
- داده خراب (mixed types)

---

## 2️⃣ RelationshipChecker – متریک‌های یکپارچگی رابطه

### ✅ books → authors

در خروجی:

### 1. `total_books`, `total_authors`

تعداد رکوردها در هر collection.

---

### 2. `orphan_books_count`

**کتاب‌هایی که:**
```python
author_ids == []
```

یا اصلاً وجود ندارد.

📌 خطرناک برای:
- recommendation
- analytics
- joins

---

### 3. `orphan_rate`

```json
0.12
```

➡️ 12٪ کتاب‌ها بدون نویسنده‌اند.

---

### 4. `books_with_invalid_authors`

کتاب‌هایی که حداقل یک author_id نامعتبر دارند.

---

### 5. `invalid_author_references_count`

**تعداد کل referenceهای خراب**  
(مهم‌تر از count کتاب)

---

### 6. `integrity_score`

```text
100 - (orphan_rate*50 + invalid_rate*50)
```

| Score | وضعیت |
|-----|-----|
| >90 | سالم |
| 70–90 | هشدار |
| <70 | خطرناک |

---

## 3️⃣ SchemaValidator – متریک‌های انطباق با Schema

### ✅ compliance_score

```json
"compliance_score": 78.4
```

**یعنی:**  
چه درصدی از required fieldها واقعاً درست و پایدارند.

📌 محاسبه:
- missing required
- required با missing_rate > 5%

---

### ✅ missing_required_fields

```json
["isbn", "title"]
```

❌ این‌ها اصلاً در DB وجود ندارند.

---

### ✅ high_missing_rate_fields

```json
{
  "field": "published_year",
  "missing_rate": 0.27,
  "severity": "critical"
}
```

📌 Required هست، ولی داده ندارد → داده **غیرقابل اعتماد**

---

### ✅ extra_fields_in_db

فیلدهایی که:
- در MongoDB هستند
- ولی در Pydantic Schema تعریف نشده‌اند

📌 نشانه:
- schema drift
- technical debt

---

## 4️⃣ DataQualityScorer – امتیاز کیفیت داده (0–100)

### ✅ overall_score

میانگین وزنی:

| بعد | وزن |
|---|---|
| Completeness | 40% |
| Validity | 30% |
| Consistency | 20% |
| Integrity | 10% |

---

### 1️⃣ Completeness

```text
(1 - avg_missing_rate) * 100
```

📌 فقط based on profiling (نه schema).

---

### 2️⃣ Validity

همان `compliance_score` از SchemaValidator.

---

### 3️⃣ Consistency

برای هر فیلد:

- **Type uniformity (70%)**
- **Empty string rate (30%)**

📌 mixed types → امتیاز پایین

---

### 4️⃣ Integrity

از RelationshipChecker  
(اگر غیرفعال → 100)

---

### ✅ grade

| Score | Grade |
|---|---|
| ≥90 | A |
| 80–89 | B |
| 70–79 | C |
| 60–69 | D |
| <60 | F |

---

### ✅ issues_summary

```json
{
  "critical": [...],
  "warnings": [...],
  "info": [...]
}
```

📌 خلاصه مدیریتی قابل ارسال به PM / CTO

---

## 5️⃣ Summary Report (run.py)

در `summary_report.json`:

```json
{
  "docs": 120450,
  "score": 82.3,
  "grade": "B (Good)"
}
```

📌 مناسب برای:
- داشبورد
- CI/CD data quality checks
- alerting

---

