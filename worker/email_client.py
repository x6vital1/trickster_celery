import asyncio
import os
import re
import uuid
from html import unescape
from typing import Dict

import httpx

from worker.settings import (
    API_BASE, EMAIL_API_KEY, EMAIL_API_KEY_HEADER,
    MAIL_WAIT_TIMEOUT_SEC, POLL_INTERVAL_SEC
)

VERIFY_TLS = os.getenv("EMAIL_API_VERIFY_TLS", "true").lower() not in {"0", "false", "no"}
ALLOCATE_TIMEOUT = int(os.getenv("EMAIL_API_ALLOCATE_TIMEOUT", "30"))
MESSAGES_TIMEOUT = int(os.getenv("EMAIL_API_MESSAGES_TIMEOUT", "15"))

# ❌ УБРАНО: глобальный клиент
# client = httpx.AsyncClient(...)

HEADERS = {EMAIL_API_KEY_HEADER: EMAIL_API_KEY} if EMAIL_API_KEY else {}

def _url(path: str) -> str:
    if not path.startswith("/"):
        path = "/" + path
    return API_BASE + path

async def allocate_one(site: str, domain: str) -> dict:
    async with httpx.AsyncClient(verify=VERIFY_TLS, headers=HEADERS, follow_redirects=True) as client:
        resp = await client.post(
            _url("/v1/email/allocate"),
            params={"site": site, "domain": domain},
            timeout=ALLOCATE_TIMEOUT
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

async def wait_code(box_id: str, timeout_sec: int = MAIL_WAIT_TIMEOUT_SEC) -> Dict:
    start_time = asyncio.get_event_loop().time()
    url = _url(f"/v1/email/{box_id}/code")
    attempt = 0
    async with httpx.AsyncClient(verify=VERIFY_TLS, headers=HEADERS, follow_redirects=True) as client:
        while asyncio.get_event_loop().time() - start_time < timeout_sec:
            attempt += 1
            remaining_time = timeout_sec - (asyncio.get_event_loop().time() - start_time)
            if remaining_time <= 0:
                break

            try:
                request_timeout = min(MESSAGES_TIMEOUT, max(1, int(remaining_time)))
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
                await asyncio.sleep(min(POLL_INTERVAL_SEC, remaining_time))
                continue
    raise TimeoutError(f"Code wait timeout for box_id={box_id} after {timeout_sec}s. Attempts={attempt}")
