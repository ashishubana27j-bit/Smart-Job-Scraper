"""scrapers/workingnomads.py — Working Nomads exposed jobs API."""

import logging
from models import ScraperResult
from scrapers.base import BaseScraper
from utils.parser_helpers import clean_text

logger = logging.getLogger(__name__)

API_URL = "https://www.workingnomads.com/api/exposed_jobs/"


class WorkingNomadsScraper(BaseScraper):
    name = "workingnomads"
    rate_limit = 1.0

    async def scrape(self) -> ScraperResult:
        data = await self.client.get(API_URL, as_json=True)
        if not data or not isinstance(data, list):
            return self._build_result([], success=False, error="Empty API response")

        jobs = []
        for raw in data:
            title = raw.get("title", "")
            description = clean_text(raw.get("description", ""))
            tags = raw.get("tags", []) or []
            text = f"{title} {description} {' '.join(tags)} {raw.get('category_name', '')}"
            if not self._text_matches_query(text):
                continue

            jobs.append(self._build_job(
                title=title,
                company=raw.get("company_name", ""),
                location=raw.get("location", "") or "Remote",
                url=raw.get("url", ""),
                description=description,
                skills_required=tags,
                posted_date=raw.get("pub_date", "") or "",
                remote=True,
            ))

            if len(jobs) >= self.query.max_results_per_portal:
                break

        return self._build_result(jobs)
