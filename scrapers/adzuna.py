"""scrapers/adzuna.py — Adzuna official API (requires free app_id + app_key)."""

import logging
import os
from urllib.parse import quote_plus
from models import ScraperResult
from scrapers.base import BaseScraper
from utils.parser_helpers import clean_text, is_remote_job

logger = logging.getLogger(__name__)

# Country code: gb, us, ae, etc.
DEFAULT_COUNTRY = os.getenv("ADZUNA_COUNTRY", "gb")


class AdzunaScraper(BaseScraper):
    name = "adzuna"
    rate_limit = 1.0

    async def scrape(self) -> ScraperResult:
        app_id = os.getenv("ADZUNA_APP_ID", "")
        app_key = os.getenv("ADZUNA_APP_KEY", "")
        if not app_id or not app_key:
            return self._build_result(
                [], success=False,
                error="Set ADZUNA_APP_ID and ADZUNA_APP_KEY in .env (free at developer.adzuna.com)",
            )

        country = DEFAULT_COUNTRY
        if self.query.location.lower() in ("uae", "dubai", "abu dhabi"):
            country = "ae"

        url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
        params = {
            "app_id": app_id,
            "app_key": app_key,
            "results_per_page": min(self.query.max_results_per_portal, 50),
            "what": self.query.query_string,
            "where": self.query.location,
        }

        data = await self.client.get(url, params=params, as_json=True)
        if not data or "results" not in data:
            return self._build_result([], success=False, error="Empty Adzuna API response")

        jobs = []
        for raw in data["results"]:
            title = raw.get("title", "")
            description = clean_text(raw.get("description", ""))
            company = raw.get("company", {}).get("display_name", "")
            location = raw.get("location", {}).get("display_name", self.query.location)
            job_url = raw.get("redirect_url", "")

            jobs.append(self._build_job(
                title=title,
                company=company,
                location=location,
                url=job_url,
                description=description,
                salary=raw.get("salary_min", "") and str(raw.get("salary_min", "")),
                posted_date=raw.get("created", "") or "",
                remote=is_remote_job(title, description, location),
            ))

        return self._build_result(jobs)
