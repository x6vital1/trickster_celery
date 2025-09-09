import os
import asyncio
import weakref
import redis.asyncio as aioredis

from worker.settings import BROKER_URL


class _LoopLocalRedis:
    def __init__(self, url: str, **kwargs):
        self.url = url
        self.kwargs = kwargs
        self._clients = weakref.WeakKeyDictionary()  # loop -> Redis

    def _client(self) -> aioredis.Redis:
        loop = asyncio.get_running_loop()
        client = self._clients.get(loop)
        if client is None:
            client = aioredis.from_url(self.url, **self.kwargs)
            self._clients[loop] = client
        return client

    def __getattr__(self, name):
        return getattr(self._client(), name)

    async def aclose(self):
        loop = asyncio.get_running_loop()
        client = self._clients.get(loop)
        if client is not None:
            await client.aclose()

r = _LoopLocalRedis(BROKER_URL, decode_responses=True)

# Ключи как и раньше
def job_key(job_id: str) -> str: return f"job:{job_id}"
def task_key(job_id: str, item_id: int) -> str: return f"task:{job_id}:{item_id}"
def mbox_list_key(box_id: str) -> str: return f"mbox:{box_id}:messages"

