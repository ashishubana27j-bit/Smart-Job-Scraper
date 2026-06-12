"""
utils/playwright_fetch.py — Browser-based fetch for SPAs (NaukriGulf, etc.).
Uses Firefox to avoid HTTP/2 issues with some Gulf job sites.
"""

import asyncio
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)

_playwright = None
_browser = None
_lock = asyncio.Lock()


async def _ensure_browser():
    global _playwright, _browser
    if _browser is not None:
        return _browser
    from playwright.async_api import async_playwright
    _playwright = await async_playwright().start()
    _browser = await _playwright.firefox.launch(headless=True)
    return _browser


async def close_browser():
    global _playwright, _browser
    if _browser:
        await _browser.close()
        _browser = None
    if _playwright:
        await _playwright.stop()
        _playwright = None


async def playwright_fetch(
    url: str,
    on_response: Optional[Callable] = None,
    wait_ms: int = 3000,
) -> tuple[Optional[str], list]:
    """
    Load URL in Firefox. Optionally collect JSON from on_response callback.
    Returns (html, captured_json_list).
    """
    captured = []

    async with _lock:
        browser = await _ensure_browser()
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:150.0) "
                "Gecko/20100101 Firefox/150.0"
            ),
            locale="en-US",
        )
        page = await ctx.new_page()

        async def _on_response(resp):
            if on_response:
                try:
                    result = await on_response(resp)
                    if result is not None:
                        captured.append(result)
                except Exception as e:
                    logger.debug(f"response handler error: {e}")

        page.on("response", _on_response)
        try:
            await page.goto(url, wait_until="networkidle", timeout=90000)
            await page.wait_for_timeout(wait_ms)
            html = await page.content()
            return html, captured
        except Exception as e:
            logger.warning(f"playwright_fetch failed for {url}: {e}")
            return None, captured
        finally:
            await ctx.close()
