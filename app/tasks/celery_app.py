from app.core.settings import get_settings
from celery import Celery 

settings = get_settings()
celery_app = Celery("ai_support_desk",
                    broker=settings.celery_broker_url,
                    backend=settings.celery_result_backend,
                    include=["app.tasks.ticket_tasks"])

celery_app.conf.task_track_started = True
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]

