from datetime import datetime
from pydantic import BaseModel, Field

class ScrapingStatsResponse(BaseModel):
    """Aggregated scraping stats response for dashboards."""
    source: str
    total_books_scraped: int
    total_tasks: int
    success_tasks: int
    failed_tasks: int
    avg_duration_seconds: float = Field(..., description="Average duration of completed scraping tasks")
    avg_success_rate: float = Field(..., description="Average saved/book ratio across tasks (%)")
    last_run: datetime
