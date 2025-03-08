from celery import Celery
import os
import logging
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging for Celery
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout,
    force=True  # Force reconfiguration of the root logger
)

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Celery configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Log environment settings
logger.info(f"🔧 CELERY CONFIG:")
logger.info(f"REDIS_URL: {REDIS_URL}")
logger.info(f"Current directory: {os.getcwd()}")

# DEBUG MODE - Change this to True to run tasks locally (no Redis needed)
DEBUG_MODE = True

if DEBUG_MODE:
    logger.info("⚠️ RUNNING IN DEBUG MODE - Tasks will execute synchronously")
    
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
    worker_redirect_stdouts=True,
    worker_redirect_stdouts_level="INFO",
    broker_connection_retry_on_startup=True,
    task_always_eager=DEBUG_MODE,   # Run tasks locally in DEBUG_MODE
    task_eager_propagates=True,  # Propagate exceptions when in eager mode
    task_acks_late=True,  # Only acknowledge tasks after successful completion
    worker_prefetch_multiplier=1,  # Restrict to one task per worker process at a time
    task_track_started=True,  # Track when a task is started
    task_send_sent_event=True  # Send events when tasks are sent
)

# Enable debug events
celery_app.conf.worker_send_task_events = True
celery_app.conf.task_send_sent_event = True

# Optional: Configure task routes
celery_app.conf.task_routes = {
    "app.utils.tasks.analyze_company_sec_filings": {"queue": "analysis"}
}

logger.info("✅ Celery application configured successfully")
logger.info(f"🔍 Task execution mode: {'LOCAL/SYNCHRONOUS' if DEBUG_MODE else 'DISTRIBUTED/ASYNCHRONOUS'}")

@celery_app.task(name="debug.ping")
def ping():
    """Simple task to test Celery connection"""
    logger.info("🔔 Ping task executed successfully")
    return "pong" 