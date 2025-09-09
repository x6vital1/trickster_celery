# worker/celery_app.py
import os
from urllib.parse import urlsplit
from celery import Celery
from worker.settings import BROKER_DSN, RESULT_BACKEND  # см. ниже

for envvar in ("CELERY_BROKER_URL", "BROKER_URL", "REDIS_URL", "CLOUDAMQP_URL", "RABBITMQ_URL"):
    if os.getenv(envvar):
        print("Removing env", envvar, "=", os.getenv(envvar))
        os.environ.pop(envvar, None)

print("Using DSN:", BROKER_DSN)
print("Split:", urlsplit(BROKER_DSN))

app = Celery("trickster_worker")
app.conf.update(
    broker_url=BROKER_DSN,
    result_backend=RESULT_BACKEND,
    task_default_queue="emailq",
    worker_prefetch_multiplier=1,
)
