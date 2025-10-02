import asyncio
import re
import uuid
from html import unescape
from typing import Dict
from worker.erros import MessageTimeout
import httpx

from worker.settings import settings

HEADERS = {settings.EMAIL_API_KEY_HEADER: settings.EMAIL_API_KEY} if settings.EMAIL_API_KEY else {}


def _url(path: str) -> str:
    if not path.startswith("/"):
        path = "/" + path
    return settings.API_BASE + path


async def allocate_one(site: str, domain: str) -> dict:
    async with httpx.AsyncClient(verify=settings.EMAIL_API_VERIFY_TLS, headers=HEADERS,
                                 follow_redirects=True) as client:
        resp = await client.post(
            _url("/v1/email/allocate"),
            params={"site": site, "domain": domain},
            timeout=settings.EMAIL_API_ALLOCATE_TIMEOUT
        )
        resp.raise_for_status()
        data = resp.json()
        email = data.get("email")
        box_id = data.get("id") or data.get("box_id")
        if not (email and box_id):
            raise ValueError(f"bad allocate response: {data}")
        return {"email": str(email), "box_id": str(box_id)}


_tag_re = re.compile(r"<[^>]+>")
_ws_re = re.compile(r"\s+")


def _html_to_text(html: str) -> str:
    return _ws_re.sub(" ", unescape(_tag_re.sub(" ", html))).strip()


async def wait_code(box_id: str, timeout_sec: int = settings.MAIL_WAIT_TIMEOUT_SEC) -> Dict:
    loop = asyncio.get_event_loop()
    start = loop.time()
    url = _url(f"/v1/email/{box_id}/code")
    attempt, delay = 0, 2

    async with httpx.AsyncClient(verify=settings.EMAIL_API_VERIFY_TLS, headers=HEADERS,
                                 follow_redirects=True) as client:
        while loop.time() - start < timeout_sec:
            attempt += 1
            remaining = timeout_sec - (loop.time() - start)
            if remaining <= 0:
                break

            try:
                request_timeout = min(settings.EMAIL_API_MESSAGES_TIMEOUT, max(1, int(remaining)))
                resp = await client.get(url, timeout=request_timeout)
                resp.raise_for_status()
                data = resp.json()

                status = str(data.get("status")).lower()
                if status == "success":
                    code = data.get("value") or ""
                    html = data.get("message") or ""
                    text = _html_to_text(html) if html else ""
                    snippet = (text or html)[:160]

                    return {
                        "msg_id": f"msg:{uuid.uuid4().hex[:20]}",
                        "box_id": str(box_id),
                        "from": None,
                        "subject": None,
                        "text": text or None,
                        "html": html or None,
                        "snippet": snippet or None,
                        "code": code or None
                    }

                elif status == "error":
                    raise RuntimeError(f"API returned error for box {box_id}: {data.get('message', 'unknown')}")

            except httpx.RequestError as e:
                print(f"Attempt {attempt}: request failed {e}, retrying...")
                await asyncio.sleep(min(settings.POLL_INTERVAL_SEC, remaining))
                continue

            await asyncio.sleep(min(delay, remaining))
            delay = min(int(delay * 1.5), 10)

    raise MessageTimeout(box_id, timeout_sec, attempt)
