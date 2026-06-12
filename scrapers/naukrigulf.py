"""
scrapers/naukrigulf.py — NaukriGulf UAE/Gulf jobs.
Uses Firefox + internal jobapi/search JSON (SPA site).
"""

import logging
from urllib.parse import quote_plus
from models import ScraperResult
from scrapers.base import BaseScraper
from utils.parser_helpers import clean_text

logger = logging.getLogger(__name__)

BASE_URL = "https://www.naukrigulf.com"


class NaukrigulfScraper(BaseScraper):
    name = "naukrigulf"
    rate_limit = 2.0

    async def scrape(self) -> ScraperResult:
        from utils.playwright_fetch import playwright_fetch

        slug = self.query.query_string.lower().replace(" ", "-")
        location = self.query.location.lower().replace(" ", "-")
        if location in ("remote", "uae", "dubai", "abu-dhabi"):
            location = "uae"
        page_url = f"{BASE_URL}/{slug}-jobs-in-{location}"

        all_raw_jobs = []

        async def capture_api(resp):
            if "jobapi/search" in resp.url and resp.status == 200:
                try:
                    data = await resp.json()
                    if data.get("jobs"):
                        return data
                except Exception:
                    pass
            return None

        self.logger.info(f"Loading NaukriGulf: {page_url}")
        html, captured = await playwright_fetch(page_url, on_response=capture_api, wait_ms=4000)

        for data in captured:
            all_raw_jobs.extend(data.get("jobs", []))

        if not all_raw_jobs:
            return self._build_result(
                [], success=False,
                error="Could not load NaukriGulf jobs (SPA/API). Try location UAE or Dubai.",
            )

        jobs = []
        seen = set()
        for raw in all_raw_jobs:
            if len(jobs) >= self.query.max_results_per_portal:
                break
            job_id = raw.get("jobId", "")
            if job_id in seen:
                continue
            seen.add(job_id)

            title = raw.get("designation", "")
            company = raw.get("company", {})
            company_name = company.get("name", "") if isinstance(company, dict) else str(company)
            location = raw.get("location", "")
            if isinstance(location, dict):
                location = location.get("city", "") or location.get("country", "")
            description = clean_text(raw.get("description", "") or "")
            jd_url = raw.get("jdURL", "")
            if jd_url and not jd_url.startswith("http"):
                jd_url = f"{BASE_URL}{jd_url}"

            exp = raw.get("experience", {})
            exp_str = exp.get("min", "") if isinstance(exp, dict) else ""
            jobs.append(self._build_job(
                title=title,
                company=company_name,
                location=str(location),
                url=jd_url,
                description=description,
                experience_level=str(exp_str),
                posted_date=raw.get("latestPostedDate", "") or "",
                remote=False,
            ))

        return self._build_result(jobs)
