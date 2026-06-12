"""scrapers/remoteok.py — Remote OK public JSON API."""

import logging
from models import ScraperResult
from scrapers.base import BaseScraper
from utils.parser_helpers import clean_text, is_remote_job

logger = logging.getLogger(__name__)

API_URL = "https://remoteok.com/api"


class RemoteOKScraper(BaseScraper):
    name = "remoteok"
    rate_limit = 1.5

    async def scrape(self) -> ScraperResult:
        self.logger.info("Fetching Remote OK API")
        data = await self.client.get(
            API_URL,
            extra_headers={"User-Agent": "JobScraper/1.0 (research; +https://remoteok.com)"},
            as_json=True,
        )

        if not data or not isinstance(data, list):
            return self._build_result([], success=False, error="Empty API response")

        jobs = []
        for raw in data:
            if not isinstance(raw, dict) or "position" not in raw:
                continue

            title = raw.get("position", "")
            description = clean_text(raw.get("description", ""))
            text = f"{title} {description} {' '.join(raw.get('tags') or [])}"
            if not self._text_matches_query(text):
                continue

            slug = raw.get("slug", "")
            url = raw.get("url") or (f"https://remoteok.com/remote-jobs/{slug}" if slug else "")
            jobs.append(self._build_job(
                title=title,
                company=raw.get("company", ""),
                location=raw.get("location") or "Remote",
                url=url,
                description=description,
                salary=raw.get("salary", "") or "",
                job_type=raw.get("job_type", "") or "",
                skills_required=raw.get("tags") or [],
                posted_date=raw.get("date", "") or "",
                remote=True,
            ))

            if len(jobs) >= self.query.max_results_per_portal:
                break

        return self._build_result(jobs)
