"""
utils/http_client.py — Shared async HTTP client.
Handles session management, retries, backoff, and user-agent rotation.
"""

import asyncio
import random
import logging
from typing import Optional
import aiohttp
from aiohttp import ClientSession, ClientTimeout, TCPConnector

from config import (
    REQUEST_TIMEOUT, MAX_RETRIES, RETRY_DELAY,
    USER_AGENTS, BASE_HEADERS, USE_PROXIES, PROXY_LIST_PATH
)

logger = logging.getLogger(__name__)


class HttpClient:
    """
    Async HTTP client with:
    - Automatic retries with exponential backoff
    - Random User-Agent rotation
    - Optional proxy rotation
    - Shared session (efficient connection pooling)
    """

    def __init__(self):
        self._session: Optional[ClientSession] = None
        self._proxies: list[str] = []
        if USE_PROXIES:
            self._load_proxies()

    def _load_proxies(self):
        try:
            with open(PROXY_LIST_PATH) as f:
                self._proxies = [line.strip() for line in f if line.strip()]
            logger.info(f"Loaded {len(self._proxies)} proxies")
        except FileNotFoundError:
            logger.warning("Proxy file not found, running without proxies")

    def _random_headers(self, extra: dict = None) -> dict:
        headers = {**BASE_HEADERS, "User-Agent": random.choice(USER_AGENTS)}
        if extra:
            headers.update(extra)
        return headers

    def _random_proxy(self) -> Optional[str]:
        return random.choice(self._proxies) if self._proxies else None

    async def __aenter__(self):
        connector = TCPConnector(ssl=False, limit=20)
        timeout = ClientTimeout(total=REQUEST_TIMEOUT)
        self._session = ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self._random_headers(),
        )
        return self

    async def __aexit__(self, *args):
        if self._session:
            await self._session.close()

    async def get(
        self,
        url: str,
        params: dict = None,
        extra_headers: dict = None,
        as_json: bool = False,
    ) -> Optional[str | dict]:
        """
        GET a URL with automatic retries.
        Returns HTML string or parsed JSON dict, or None on failure.
        """
        headers = self._random_headers(extra_headers)
        proxy = self._random_proxy()

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with self._session.get(
                    url,
                    params=params,
                    headers=headers,
                    proxy=proxy,
                    allow_redirects=True,
                ) as response:
                    if response.status == 200:
                        if as_json:
                            return await response.json(content_type=None)
                        return await response.text()

                    elif response.status == 429:
                        wait = RETRY_DELAY * (2 ** attempt) + random.uniform(0, 1)
                        logger.warning(f"Rate limited on {url}, waiting {wait:.1f}s")
                        await asyncio.sleep(wait)

                    elif response.status in (403, 401):
                        logger.warning(f"Blocked ({response.status}) on {url}, trying stealth fetch")
                        from utils.stealth_fetch import stealth_get
                        stealth_body = await stealth_get(url, params=params, extra_headers=extra_headers)
                        if stealth_body:
                            return stealth_body
                        return None

                    elif response.status >= 500:
                        wait = RETRY_DELAY * attempt
                        logger.warning(f"Server error {response.status} on {url}, retry {attempt}/{MAX_RETRIES}")
                        await asyncio.sleep(wait)

                    else:
                        logger.warning(f"HTTP {response.status} for {url}")
                        return None

            except asyncio.TimeoutError:
                logger.warning(f"Timeout on {url} (attempt {attempt}/{MAX_RETRIES})")
                await asyncio.sleep(RETRY_DELAY * attempt)

            except aiohttp.ClientError as e:
                logger.warning(f"Client error on {url}: {e} (attempt {attempt}/{MAX_RETRIES})")
                await asyncio.sleep(RETRY_DELAY * attempt)

        logger.error(f"All {MAX_RETRIES} retries failed for {url}")
        return None
