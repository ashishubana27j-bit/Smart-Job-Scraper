"""scrapers/arbeitnow.py — Arbeitnow free job board API."""

import logging
from models import ScraperResult
from scrapers.base import BaseScraper
from utils.parser_helpers import clean_text, is_remote_job

logger = logging.getLogger(__name__)

API_URL = "https://www.arbeitnow.com/api/job-board-api"


class ArbeitnowScraper(BaseScraper):
    name = "arbeitnow"
    rate_limit = 1.0

    async def scrape(self) -> ScraperResult:
        data = await self.client.get(API_URL, as_json=True)
        if not data or "data" not in data:
            return self._build_result([], success=False, error="Empty API response")

        jobs = []
        for raw in data["data"]:
            title = raw.get("title", "")
            description = clean_text(raw.get("description", ""))
            tags = raw.get("tags", []) or []
            text = f"{title} {description} {' '.join(tags)}"
            if not self._text_matches_query(text):
                continue

            slug = raw.get("slug", "")
            url = raw.get("url") or (f"https://www.arbeitnow.com/jobs/{slug}" if slug else "")
            location = raw.get("location", "") or "Remote"
            jobs.append(self._build_job(
                title=title,
                company=raw.get("company_name", ""),
                location=location,
                url=url,
                description=description,
                skills_required=tags,
                posted_date=raw.get("created_at", "") or "",
                remote=is_remote_job(title, description, location),
            ))

            if len(jobs) >= self.query.max_results_per_portal:
                break

        return self._build_result(jobs)
