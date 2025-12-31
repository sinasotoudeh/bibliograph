"""Celery application configuration."""

import os
import shutil
from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown
from prometheus_client import start_http_server, CollectorRegistry, multiprocess
import logging

logger = logging.getLogger(__name__)

# Get broker URL from environment
CELERY_BROKER_URL = os.getenv(
    "CELERY_BROKER_URL",
    "amqp://bibliograph:bibliograph_dev_2024@bibliograph-rabbitmq:5672/"
)
CELERY_RESULT_BACKEND = os.getenv(
    "CELERY_RESULT_BACKEND",
    "redis://bibliograph-redis:6379/1"
)

# ✅ Configure multiprocess directory for Prometheus
PROMETHEUS_MULTIPROC_DIR = '/tmp/prometheus_multiproc'
os.environ.setdefault('PROMETHEUS_MULTIPROC_DIR', PROMETHEUS_MULTIPROC_DIR)

# Create Celery application
celery_app = Celery(
    "bibliograph_scraper",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["src.tasks.scraping_tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3000 * 60,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    worker_send_task_events=True,  # ✅ فعال‌سازی events
)

# Task routes
celery_app.conf.task_routes = {
    "src.tasks.scraping_tasks.*": {"queue": "scraping"},
}

# Global flag to prevent duplicate server start
_metrics_server_started = False


@worker_process_init.connect
def setup_metrics_server(**kwargs):
    """
    Start Prometheus metrics server when worker process initializes.
    This runs once per worker process (not per task).
    """
    global _metrics_server_started
    
    if _metrics_server_started:
        logger.debug("Metrics server already started, skipping...")
        return
    
    try:
        # Clean up old metrics files on first worker startup
        if os.path.exists(PROMETHEUS_MULTIPROC_DIR):
            logger.info(f"Cleaning old metrics from {PROMETHEUS_MULTIPROC_DIR}")
            shutil.rmtree(PROMETHEUS_MULTIPROC_DIR, ignore_errors=True)
        
        # Recreate directory
        os.makedirs(PROMETHEUS_MULTIPROC_DIR, exist_ok=True)
        logger.info(f"Created metrics directory: {PROMETHEUS_MULTIPROC_DIR}")
        
        # Use multiprocess collector to gather metrics from all worker processes
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
        
        # Start HTTP server
        start_http_server(8001, addr='0.0.0.0', registry=registry)
        
        _metrics_server_started = True
        logger.info("✅ Prometheus multiprocess metrics server started on 0.0.0.0:8001")
        
    except OSError as e:
        if "Address already in use" in str(e):
            logger.warning(f"⚠️ Metrics server port 8001 already in use (this is normal in multi-worker setup)")
            _metrics_server_started = True  # Mark as started to avoid retry
        else:
            logger.error(f"❌ Failed to start metrics server: {e}")
            raise
    except Exception as e:
        logger.error(f"❌ Unexpected error starting metrics server: {e}")
        raise


@worker_process_shutdown.connect
def cleanup_metrics(**kwargs):
    """
    Clean up metrics when worker process shuts down.
    """
    try:
        logger.info("Cleaning up Prometheus multiprocess metrics...")
        multiprocess.mark_process_dead(os.getpid())
    except Exception as e:
        logger.error(f"Error cleaning up metrics: {e}")
