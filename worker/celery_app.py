from celery import Celery
from worker.settings import BROKER_URL

print(BROKER_URL)
app = Celery("trickster_worker", broker=BROKER_URL)

app.conf.update(
    task_default_queue="emailq",
    task_acks_late=False,
    worker_prefetch_multiplier=1,
    task_time_limit=1800,
    broker_connection_retry_on_startup=True,
    imports=("worker.tasks",),
)