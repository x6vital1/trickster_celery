# worker/settings.py
import os
from urllib.parse import quote

def _env_bool(name: str, default: str = "0") -> bool:
    return (os.getenv(name, default) or "").lower() in {"1", "true", "yes", "on"}

# Общие настройки окружения
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

# Redis как набор явных полей (никаких URL в ENV не надо)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_USER = os.getenv("REDIS_USER") or None
REDIS_PASS = os.getenv("REDIS_PASS") or None
REDIS_SSL  = _env_bool("REDIS_SSL", "0")

# Базы для разных назначений (если используешь одну — оставь одинаковые)
REDIS_DB_BROKER  = int(os.getenv("REDIS_DB_BROKER", "0"))  # Celery broker
REDIS_DB_BACKEND = int(os.getenv("REDIS_DB_BACKEND", "1")) # Celery result backend (опц.)

# Сервисные ключи/URL-ы
API_BASE = (os.getenv("API_BASE", "https://api.trickster-shop.cloud") or "").rstrip("/")
EMAIL_API_KEY = os.getenv("EMAIL_API_KEY", "")
EMAIL_API_KEY_HEADER = os.getenv("EMAIL_API_KEY_HEADER", "api-key")

# Прочие тайминги
ALLOCATE_PAUSE_SEC   = float(os.getenv("ALLOCATE_PAUSE_SEC", "0.3"))
MAIL_WAIT_TIMEOUT_SEC = int(os.getenv("MAIL_WAIT_TIMEOUT_SEC", "90"))
POLL_INTERVAL_SEC     = float(os.getenv("POLL_INTERVAL_SEC", "10.0"))
MESSAGE_TTL_SEC       = int(os.getenv("MESSAGE_TTL_SEC", "259200"))

# --- ВНУТРЕННЕЕ: сборка DSN для Celery (нужно только Celery) ---
def _build_redis_dsn(db: int) -> str:
    scheme = "rediss" if REDIS_SSL else "redis"
    # username/password кодируем корректно
    if REDIS_USER and REDIS_PASS is not None:
        auth = f"{quote(REDIS_USER)}:{quote(REDIS_PASS)}@"
    elif REDIS_PASS is not None:
        auth = f":{quote(REDIS_PASS)}@"
    elif REDIS_USER:
        auth = f"{quote(REDIS_USER)}@"
    else:
        auth = ""
    return f"{scheme}://{auth}{REDIS_HOST}:{REDIS_PORT}/{db}"

# Эти строки используются только при инициализации Celery
BROKER_DSN = _build_redis_dsn(REDIS_DB_BROKER)
RESULT_BACKEND = _build_redis_dsn(REDIS_DB_BACKEND)
  # если нужен backend
