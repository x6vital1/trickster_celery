import uuid
import asyncio
import datetime as dt
from celery import shared_task
from worker.redis_store import r, job_key, task_key, mbox_list_key, wait_lock_key
from worker.settings import MESSAGE_TTL_SEC, MAIL_WAIT_TIMEOUT_SEC, ALLOCATE_PAUSE_SEC
from worker.email_client import allocate_one, wait_code

MAX_CONCURRENT_ALLOCATIONS = 10
ALLOCATE_RETRIES = 3
ALLOCATE_RETRY_DELAY = 2
CHUNK_SIZE = 20

semaphore = asyncio.Semaphore(MAX_CONCURRENT_ALLOCATIONS)

def now_iso(): return dt.datetime.utcnow().replace(microsecond=0).isoformat()+"Z"

async def safe_allocate(site: str, domain: str, retries=ALLOCATE_RETRIES, delay=ALLOCATE_RETRY_DELAY):
    for attempt in range(1, retries + 1):
        try:
            async with semaphore:
                return await allocate_one(site, domain)
        except Exception as e:
            if attempt == retries:
                raise
            print(f"Attempt {attempt} failed: {e}, retrying in {delay}s")
            await asyncio.sleep(delay)

@shared_task(name="tasks.allocate_batch", max_retries=0)
def allocate_batch(site: str, domain: str, job_id: str, total: int):
    asyncio.run(_allocate_batch_async(site, domain, job_id, total))

async def _allocate_batch_async(site: str, domain: str, job_id: str, total: int):

    async def handle_item(item_id: int):
        try:
            it = await safe_allocate(site, domain)
            email, box_id = it["email"], it["box_id"]

            await r.hset(task_key(job_id, item_id), mapping={
                "email": email,
                "box_id": box_id,
                "state": "allocated",
                "updated_at": now_iso()
            })
            await r.hincrby(job_key(job_id), "allocated", 1)
        except Exception as e:
            await r.hset(task_key(job_id, item_id), mapping={
                "state": "failed",
                "error": f"allocate_one error: {e}",
                "updated_at": now_iso()
            })
        finally:
            await _after_item_done(job_id)

    for start in range(0, total, CHUNK_SIZE):
        end = min(start + CHUNK_SIZE, total)
        tasks_chunk = [handle_item(i) for i in range(start, end)]
        await asyncio.gather(*tasks_chunk)
        if ALLOCATE_PAUSE_SEC > 0:
            await asyncio.sleep(ALLOCATE_PAUSE_SEC)

@shared_task(name="tasks.wait_for_code", max_retries=0)
def wait_for_code(box_id: str, job_id: str, item_id: int):
    asyncio.run(_wait_for_code_async(box_id, job_id, item_id))

async def _wait_for_code_async(box_id: str, job_id: str, item_id: int):
    try:
        msg = await wait_code(box_id=box_id, timeout_sec=MAIL_WAIT_TIMEOUT_SEC)
        msg_id = msg["msg_id"]

        record = {"box_id": msg["box_id"], "ts": now_iso()}
        for k in ("from", "subject", "snippet", "text", "html", "headers", "code"):
            if msg.get(k) is not None:
                record[k] = msg[k]

        await r.hset(msg_id, mapping=record)
        await r.rpush(mbox_list_key(box_id), msg_id)
        await r.expire(msg_id, MESSAGE_TTL_SEC)
        await r.expire(mbox_list_key(box_id), MESSAGE_TTL_SEC)

        await r.hset(task_key(job_id, item_id), mapping={
            "state": "message_received",
            "msg_id": msg_id,
            "updated_at": now_iso()
        })
    except Exception as e:
        await r.hset(task_key(job_id, item_id), mapping={
            "state": "failed",
            "error": str(e),
            "updated_at": now_iso()
        })
    finally:
        await r.delete(wait_lock_key(job_id, item_id))
        await _after_item_done(job_id)
        await r.aclose()


async def _after_item_done(job_id: str):
    total = int(await r.hget(job_key(job_id), "total") or 0)
    done = await r.hincrby(job_key(job_id), "done", 1)
    if done >= total:
        await r.hset(job_key(job_id), mapping={
            "state": "completed",
            "updated_at": now_iso()
        })
