from typing import Dict, Any, List
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)


class RelationshipChecker:
    """بررسی روابط بین collection ها"""
    
    def __init__(self, mongodb_client):
        self.db = mongodb_client.get_database()
        self.logger = logger
    
    async def check_book_author_integrity(self) -> Dict[str, Any]:
        """
        بررسی یکپارچگی رابطه books → authors
        """
        
        self.logger.info("Checking book-author relationships...")
        
        books_col = self.db["books"]
        authors_col = self.db["authors"]
        
        # دریافت تمام author IDs موجود
        valid_author_ids = set()
        async for author in authors_col.find({}, {"_id": 1}):
            valid_author_ids.add(author["_id"])
        
        self.logger.info(f"Found {len(valid_author_ids)} valid authors")
        
        # بررسی books
        total_books = 0
        orphan_books = []
        books_with_invalid_authors = 0
        invalid_author_references = []
        
        async for book in books_col.find({}):
            total_books += 1
            
            author_ids = book.get("author_ids", [])
            
            if not author_ids:
                orphan_books.append(str(book["_id"]))
                continue
            
            # بررسی هر author_id
            has_invalid = False
            for author_id in author_ids:
                if author_id not in valid_author_ids:
                    has_invalid = True
                    invalid_author_references.append({
                        "book_id": str(book["_id"]),
                        "invalid_author_id": str(author_id)
                    })
            
            if has_invalid:
                books_with_invalid_authors += 1
        
        orphan_rate = len(orphan_books) / total_books if total_books > 0 else 0
        invalid_rate = books_with_invalid_authors / total_books if total_books > 0 else 0
        
        # محاسبه integrity score
        integrity_score = max(0, 100 - (orphan_rate * 50 + invalid_rate * 50))
        
        return {
            "relationship": "books → authors",
            "integrity_score": round(integrity_score, 2),
            "total_books": total_books,
            "total_authors": len(valid_author_ids),
            "orphan_books_count": len(orphan_books),
            "orphan_rate": round(orphan_rate, 4),
            "books_with_invalid_authors": books_with_invalid_authors,
            "invalid_author_references_count": len(invalid_author_references),
            "invalid_rate": round(invalid_rate, 4),
            "sample_orphan_books": orphan_books[:10],
            "sample_invalid_references": invalid_author_references[:10]
        }
    
    async def check_scraping_log_integrity(self) -> Dict[str, Any]:
        """بررسی یکپارچگی scraping logs"""
        
        self.logger.info("Checking scraping log integrity...")
        
        logs_col = self.db["scraping_logs"]
        
        total_logs = 0
        logs_without_task_id = 0
        duplicate_task_ids = []
        
        task_ids_seen = set()
        
        async for log in logs_col.find({}):
            total_logs += 1
            
            task_id = log.get("task_id")
            
            if not task_id:
                logs_without_task_id += 1
                continue
            
            if task_id in task_ids_seen:
                duplicate_task_ids.append(task_id)
            else:
                task_ids_seen.add(task_id)
        
        missing_task_id_rate = logs_without_task_id / total_logs if total_logs > 0 else 0
        duplicate_rate = len(duplicate_task_ids) / total_logs if total_logs > 0 else 0
        
        integrity_score = max(0, 100 - (missing_task_id_rate * 60 + duplicate_rate * 40))
        
        return {
            "collection": "scraping_logs",
            "integrity_score": round(integrity_score, 2),
            "total_logs": total_logs,
            "logs_without_task_id": logs_without_task_id,
            "missing_task_id_rate": round(missing_task_id_rate, 4),
            "duplicate_task_ids_count": len(duplicate_task_ids),
            "duplicate_rate": round(duplicate_rate, 4),
            "unique_task_ids": len(task_ids_seen)
        }
