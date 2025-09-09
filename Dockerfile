FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY worker ./worker
ENV PYTHONUNBUFFERED=1
CMD ["celery","-A","worker.celery_app.app","worker","-Q","emailq","-l","INFO","--concurrency","50","--prefetch-multiplier","1"]
