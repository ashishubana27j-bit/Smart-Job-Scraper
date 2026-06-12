"""scrapers/jooble.py — Jooble aggregator (official REST API, free key at jooble.org/api/about)."""

import logging
import os
from models import ScraperResult
from scrapers.base import BaseScraper
from utils.stealth_fetch import stealth_get
import asyncio
import json

logger = logging.getLogger(__name__)


class JoobleScraper(BaseScraper):
    name = "jooble"
    rate_limit = 1.5

    async def scrape(self) -> ScraperResult:
        api_key = os.getenv("JOOBLE_API_KEY", "")
        if not api_key:
            return self._build_result(
                [], success=False,
                error="Set JOOBLE_API_KEY in .env (free at https://jooble.org/api/about)",
            )

        url = f"https://jooble.org/api/{api_key}"
        payload = {
            "keywords": self.query.query_string,
            "location": self.query.location,
            "radius": "25",
            "page": "1",
            "searchMode": "1",
        }

        body, status = await asyncio.to_thread(self._post_api, url, payload)
        if status != 200 or not body:
            return self._build_result([], success=False, error=f"Jooble API error ({status})")

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return self._build_result([], success=False, error="Invalid Jooble API response")

        jobs = []
        for raw in data.get("jobs", [])[: self.query.max_results_per_portal]:
            title = raw.get("title", "")
            description = raw.get("snippet", "") or raw.get("description", "")
            if not self._text_matches_query(f"{title} {description}"):
                continue
            jobs.append(self._build_job(
                title=title,
                company=raw.get("company", ""),
                location=raw.get("location", self.query.location),
                url=raw.get("link", "") or raw.get("url", ""),
                description=description,
                salary=raw.get("salary", "") or "",
                posted_date=raw.get("updated", "") or "",
                remote="remote" in f"{title} {description}".lower(),
            ))

        return self._build_result(jobs)

    @staticmethod
    def _post_api(url: str, payload: dict) -> tuple[str, int]:
        from curl_cffi import requests
        try:
            r = requests.post(
                url,
                json=payload,
                impersonate="chrome124",
                timeout=30,
                headers={"Content-Type": "application/json"},
            )
            return r.text, r.status_code
        except Exception:
            return "", 0
