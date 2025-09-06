from celery import Celery
from .config import get_settings

settings = get_settings()

celery_app = Celery(
    "tasks",
    broker=f"redis://{settings.redis_host}:{settings.redis_port}/0",
    backend=f"redis://{settings.redis_host}:{settings.redis_port}/0",
)

celery_app.autodiscover_tasks(["backend"])
