import asyncio
import weakref
import redis.asyncio as aioredis
from worker.settings import (
    REDIS_HOST, REDIS_PORT, REDIS_USER, REDIS_PASS, REDIS_DB_BROKER, REDIS_SSL
)
from redis.asyncio import Redis as RedisType
from typing import cast

class _LoopLocalRedis:
    """
    По одному Redis-клиенту на event loop.
    Создаём ИСКЛЮЧИТЕЛЬНО через явные параметры, без URL.
    """
    def __init__(self, *, host: str, port: int, db: int,
                 username: str | None = None, password: str | None = None,
                 ssl: bool = False, **kwargs):
        self.params = dict(
            host=host, port=port, db=db,
            username=username, password=password,
            ssl=ssl,
            **kwargs
        )
        self._clients = weakref.WeakKeyDictionary()  # loop -> Redis

    def _client(self) -> aioredis.Redis:
        loop = asyncio.get_running_loop()
        client = self._clients.get(loop)
        if client is None:
            client = aioredis.Redis(**self.params)
            self._clients[loop] = client
        return client

    def __getattr__(self, name):
        # Проксируем методы (get, set, hgetall, etc.)
        return getattr(self._client(), name)

    async def aclose(self):
        loop = asyncio.get_running_loop()
        client = self._clients.get(loop)
        if client is not None:
            await client.aclose()

# Единый экземпляр для брокерной БД (если нужна другая БД — создай ещё один)
_r = _LoopLocalRedis(
    host=REDIS_HOST,
    username=REDIS_USER,
    port=REDIS_PORT,
    db=REDIS_DB_BROKER,
    password=REDIS_PASS,
    ssl=REDIS_SSL,
    decode_responses=True,
)
r: RedisType = cast(RedisType, _r)

# Ключи как и раньше
def job_key(job_id: str) -> str: return f"job:{job_id}"
def task_key(job_id: str, item_id: int) -> str: return f"task:{job_id}:{item_id}"
def mbox_list_key(box_id: str) -> str: return f"mbox:{box_id}:messages"
def wait_lock_key(job_id: str, item_id: int) -> str:
    return f"lock:wait:{job_id}:{item_id}"