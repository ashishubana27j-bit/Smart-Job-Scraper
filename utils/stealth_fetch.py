"""
utils/stealth_fetch.py — Bypass 403 blocks using curl_cffi (Chrome TLS fingerprint).
"""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from curl_cffi import requests as curl_requests
except ImportError:
    curl_requests = None


def _sync_get(
    url: str,
    params: dict = None,
    headers: dict = None,
    impersonate: str = "chrome124",
) -> tuple[Optional[str], int]:
    """Sync GET via curl_cffi. Returns (body, status_code)."""
    if curl_requests is None:
        return None, 0
    try:
        r = curl_requests.get(
            url,
            params=params,
            headers=headers or {},
            impersonate=impersonate,
            timeout=45,
            allow_redirects=True,
        )
        return r.text, r.status_code
    except Exception as e:
        logger.warning(f"stealth_fetch error for {url}: {e}")
        return None, 0


async def stealth_get(
    url: str,
    params: dict = None,
    extra_headers: dict = None,
) -> Optional[str]:
    """Async wrapper — returns HTML text or None."""
    body, status = await asyncio.to_thread(_sync_get, url, params, extra_headers)
    if status == 200 and body:
        return body
    logger.warning(f"stealth_get failed ({status}) for {url}")
    return None
