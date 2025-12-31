"""
Celery Tasks for NLAI Scraper
-----------------------------------------------------
Features:
- Handles 'Max Results' limit.
- Intelligent Error Handling (Network vs Server).
- Smart Recovery (Handshake Loop on Network Disconnect).
- Stores 'author_index' in Logs and Books.
- [FIXED] Supports 'params' payload from DB (restored functionality).
"""

import asyncio
from datetime import datetime
from typing import Optional
from celery import shared_task
import structlog
from prometheus_client import Counter, Gauge

# Import Exception
from src.scrapers.sources.nlai import (
    NLAIScraper, 
    MaxResultsLimitExceeded, 
    NetworkConnectionError, 
    ServerResponseError,
    ContentParsingError
)
from src.repositories.book_repo import BookRepository
from src.repositories.scraping_log_repo import ScrapingLogRepository
from src.core.database.mongodb import MongoDBClient
from src.models.scraping_log import ScrapingStatus
from src.repositories.author_repo import AuthorRepository

logger = structlog.get_logger(__name__)

# -----------------------------------------------------
# 🔹 Prometheus Metrics
# -----------------------------------------------------
TASK_INSERTED_BOOKS = Counter("nlai_scrape_inserted_total", "Total books inserted")
TASK_ERRORS = Counter("nlai_scrape_errors_total", "Total errors")
TASK_SKIPPED_AUTHORS = Counter("nlai_scrape_skipped_authors", "Authors skipped due to limit")
TASK_PROGRESS = Gauge("nlai_scrape_progress_percent", "Progress percent", ["task_id"])

@shared_task(bind=True, autoretry_for=())
def scrape_nlai(self, author_list: list[str], max_results: Optional[int] = None) -> dict:
    task_id = self.request.id
    logger.info("task.nlai.init", task_id=task_id, total=len(author_list), limit=max_results)
    TASK_PROGRESS.labels(task_id=task_id).set(0)

    async def _run_scraping():
        mongodb_client = MongoDBClient()
        await mongodb_client.connect()

        book_repo = BookRepository(mongodb_client)
        log_repo = ScrapingLogRepository(mongodb_client)
        author_repo = AuthorRepository(mongodb_client)
        scraper = NLAIScraper()

        # -----------------------------
        # State (DERIVED COUNTS ONLY)
        # -----------------------------
        total_books_found = 0
        total_inserted_count = 0

        skipped_authors_ids: list[dict] = []
        failed_authors_ids: list[dict] = []

        consecutive_network_errors = 0
        consecutive_server_errors = 0

        # -----------------------------
        # Prepare author list
        # -----------------------------
        final_task_label = "Manual List"
        authors_data: list[dict] = []

        if len(author_list) == 1 and "to" in author_list[0]:
            try:
                start, end = map(int, author_list[0].split("to"))
                fetched = await author_repo.get_by_index_range(start, end)

                authors_data = [
                    {
                        "name": a.get("author_name"),
                        "index": a.get("author_index_number"),
                        "params": a.get("params"),
                    }
                    for a in fetched
                ]
                final_task_label = f"Range: {start} to {end}"
            except ValueError:
                authors_data = [{"name": author_list[0], "index": None, "params": None}]
        else:
            FIXED_INDEX = 0  
            authors_data = [{"name": a, "index": FIXED_INDEX, "params": None} for a in author_list]
            if len(authors_data) == 1:
                final_task_label = authors_data[0]["name"]

        total_steps = len(authors_data)

        # -----------------------------
        # Parent log (INIT)
        # -----------------------------
        await log_repo.insert_log({
            "task_id": task_id,
            "source": "nlai",
            "status": ScrapingStatus.RUNNING,
            "current_author": f"Init {total_steps} items...",
            "started_at": datetime.utcnow(),
            "books_found": 0,
            "books_saved": 0,
            "skipped_authors_count": 0,
            "failed_authors_count": 0,
            "skipped_authors_ids": [],
            "failed_authors_ids": [],
            "is_parent": True,
        })

        if total_steps == 0:
            await log_repo.update_progress(task_id, {
                "status": ScrapingStatus.SUCCESS,
                "current_author": final_task_label + " (Empty)",
                "completed_at": datetime.utcnow(),
            })
            return {"status": "completed_empty"}

        # ======================================================
        # MAIN LOOP
        # ======================================================
        for i, author_obj in enumerate(authors_data, start=1):

            author_name = author_obj.get("name")
            author_index = author_obj.get("index")
            author_params = author_obj.get("params")

            display_name = author_name or f"Index_{author_index or i}"

            # ✅ 1) UPDATE PARENT **BEFORE** CHILD WORK
            await log_repo.update_progress(task_id, {
                "current_author": f"Processing: {display_name} (Idx: {author_index or i})",
                "current_author_index": author_index or i,
                "status": ScrapingStatus.RUNNING,
            })

            sub_task_id = f"{task_id}_{i}"

            # Child log
            await log_repo.insert_log({
                "task_id": sub_task_id,
                "parent_task_id": task_id,
                "source": "nlai",
                "status": ScrapingStatus.RUNNING,
                "current_author": display_name,
                "current_author_index": author_index,
                "started_at": datetime.utcnow(),
            })

            try:
                # ----------------------------
                # SCRAPING
                # ----------------------------
                if author_params:
                    profiles = await scraper.fetch_with_custom_payload(
                        author_params, max_results=max_results
                    )
                elif author_name:
                    profiles = await scraper.fetch_by_author_name(
                        author_name, max_results=max_results
                    )
                else:
                    raise ValueError("Missing author name & params")

                consecutive_network_errors = 0
                consecutive_server_errors = 0

                local_found = len(profiles)
                local_inserted = 0

                for item in profiles:
                    book_data = {
                        "source": "nlai",
                        "author": item.get("author") or author_name or "Unknown",
                        "author_index_number": author_index,
                        **item,
                    }
                    await book_repo.create(book_data)
                    local_inserted += 1
                    TASK_INSERTED_BOOKS.inc()

                total_books_found += local_found
                total_inserted_count += local_inserted

                await log_repo.update_progress(sub_task_id, {
                    "status": ScrapingStatus.SUCCESS,
                    "progress": 100.0,
                    "books_found": local_found,
                    "books_saved": local_inserted,
                    "completed_at": datetime.utcnow(),
                })

            except MaxResultsLimitExceeded as e:
                skipped_authors_ids.append({
                    "index": author_index or i,
                    "name": display_name,
                    "found": e.found,
                })
                TASK_SKIPPED_AUTHORS.inc()

                await log_repo.update_progress(sub_task_id, {
                    "status": "SKIPPED",
                    "error_message": f"Limit exceeded ({e.found} > {e.limit})",
                    "books_found": e.found,
                    "completed_at": datetime.utcnow(),
                })

            except NetworkConnectionError as e:
                consecutive_network_errors += 1
                failed_authors_ids.append({
                    "index": author_index or i,
                    "name": display_name,
                    "reason": f"network: {e}",
                })
                TASK_ERRORS.inc()

                await log_repo.update_progress(sub_task_id, {
                    "status": ScrapingStatus.FAILED,
                    "error_message": f"Network error: {e}",
                    "completed_at": datetime.utcnow(),
                })

                if consecutive_network_errors >= 3:
                    logger.warning("task.nlai.enter_handshake_loop")
                    while True:
                        try:
                            await asyncio.sleep(5)
                            await scraper.perform_handshake()
                            consecutive_network_errors = 0
                            break
                        except NetworkConnectionError:
                            pass

            except (ServerResponseError, ContentParsingError) as e:
                consecutive_server_errors += 1
                failed_authors_ids.append({
                    "index": author_index or i,
                    "name": display_name,
                    "reason": str(e),
                })
                TASK_ERRORS.inc()

                await log_repo.update_progress(sub_task_id, {
                    "status": ScrapingStatus.FAILED,
                    "error_message": str(e),
                    "completed_at": datetime.utcnow(),
                })

                if consecutive_server_errors >= 3:
                    await log_repo.update_progress(task_id, {
                        "status": "STOPPED_ON_SERVER_ERROR",
                        "error_message": "Stopped after 3 consecutive server errors",
                        "completed_at": datetime.utcnow(),
                        "books_found": total_books_found,
                        "books_saved": total_inserted_count,
                        "failed_authors_ids": failed_authors_ids,
                    })
                    await scraper.close()
                    await mongodb_client.disconnect()
                    return {"status": "stopped", "reason": "server_error"}

            except Exception as e:
                failed_authors_ids.append({
                    "index": author_index or i,
                    "name": display_name,
                    "reason": f"unexpected: {e}",
                })
                TASK_ERRORS.inc()

                await log_repo.update_progress(sub_task_id, {
                    "status": ScrapingStatus.FAILED,
                    "error_message": str(e),
                    "completed_at": datetime.utcnow(),
                })

            # -----------------------------
            # UPDATE PARENT (END ITERATION)
            # -----------------------------
            progress = round((i / total_steps) * 100, 2)

            parent_stats = {
                "progress": progress,
                "books_found": total_books_found,
                "books_saved": total_inserted_count,
                "failed_authors_count": len(failed_authors_ids),
                "skipped_authors_count": len(skipped_authors_ids),
                "failed_authors_ids": failed_authors_ids,
                "skipped_authors_ids": skipped_authors_ids,
            }

            self.update_state(state="PROGRESS", meta=parent_stats)
            await log_repo.update_progress(task_id, parent_stats)
            TASK_PROGRESS.labels(task_id=task_id).set(progress)

        # =============================
        # FINALIZATION
        # =============================
        await log_repo.update_progress(task_id, {
            "status": ScrapingStatus.SUCCESS,
            "current_author": final_task_label + " (Done)",
            "completed_at": datetime.utcnow(),
            "books_found": total_books_found,
            "books_saved": total_inserted_count,
            "skipped_authors_count": len(skipped_authors_ids),
            "failed_authors_count": len(failed_authors_ids),
            "progress": 100.0,
        })

        await scraper.close()
        await mongodb_client.disconnect()

        return {
            "status": "completed",
            "found": total_books_found,
            "skipped": len(skipped_authors_ids),
            "failed": len(failed_authors_ids),
        }

    return asyncio.run(_run_scraping())
