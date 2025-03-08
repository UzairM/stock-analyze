from celery import Celery
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Celery configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "biotech_analysis",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.utils.tasks"]
)

# Celery configuration
celery_app.conf.update(
    result_expires=3600,  # Results expire after 1 hour
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Optional: Configure task routes
celery_app.conf.task_routes = {
    "app.utils.tasks.analyze_company_sec_filings": {"queue": "analysis"}
} 