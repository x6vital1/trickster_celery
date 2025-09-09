import os
from urllib.parse import quote

def redis_url(
    host: str,
    port: int = 6379,
    db: int = 0,
    password: str | None = None,
    username: str | None = None,
    ssl: bool = False,
) -> str:
    scheme = "rediss" if ssl else "redis"
    auth = ""
    if username and password:
        auth = f"{quote(username)}:{quote(password)}@"
    elif password:  # без ACL
        auth = f":{quote(password)}@"
    return f"{scheme}://{auth}{host}:{port}/{db}"

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB_BROKER = int(os.getenv("REDIS_DB_BROKER", "0"))
REDIS_DB_BACKEND = int(os.getenv("REDIS_DB_BACKEND", "1"))
REDIS_USER = os.getenv("REDIS_USER")          # если используешь ACL
REDIS_PASS = os.getenv("REDIS_PASS")          # пароль



BROKER_URL = redis_url(
    host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB_BROKER,
    username=REDIS_USER, password=REDIS_PASS,
)

API_BASE = os.getenv("API_BASE", "http://host.docker.internal:8080").rstrip("/")
EMAIL_API_KEY = os.getenv("EMAIL_API_KEY", "3831b9faf5db89911585a580a8afb3d7c2a36067568e64c5d628062488d28c02")
EMAIL_API_KEY_HEADER = os.getenv("EMAIL_API_KEY_HEADER", "api-key")

ALLOCATE_PAUSE_SEC = float(os.getenv("ALLOCATE_PAUSE_SEC", "0.3"))

MAIL_WAIT_TIMEOUT_SEC = int(os.getenv("MAIL_WAIT_TIMEOUT_SEC", "90"))
POLL_INTERVAL_SEC = float(os.getenv("POLL_INTERVAL_SEC", "10.0"))

MESSAGE_TTL_SEC = int(os.getenv("MESSAGE_TTL_SEC", "259200"))