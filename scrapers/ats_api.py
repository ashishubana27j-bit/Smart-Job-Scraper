"""
scrapers/ats_api.py — Multi-company ATS API scrapers (Greenhouse, Lever, SmartRecruiters, Ashby).
"""

import logging
from models import ScraperResult
from scrapers.base import BaseScraper
from utils.parser_helpers import clean_text, is_remote_job
from config import GREENHOUSE_BOARDS, LEVER_COMPANIES, SMARTRECRUITER_COMPANIES, ASHBY_BOARDS

logger = logging.getLogger(__name__)


class GreenhouseScraper(BaseScraper):
    name = "greenhouse"
    rate_limit = 1.0

    async def scrape(self) -> ScraperResult:
        jobs = []
        for board in GREENHOUSE_BOARDS:
            if len(jobs) >= self.query.max_results_per_portal:
                break
            url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
            data = await self.client.get(url, as_json=True)
            if not data or "jobs" not in data:
                continue

            for raw in data["jobs"]:
                title = raw.get("title", "")
                location = raw.get("location", {}).get("name", "")
                text = f"{title} {location}"
                if not self._text_matches_query(text):
                    continue

                jobs.append(self._build_job(
                    title=title,
                    company=raw.get("company_name", board.title()),
                    location=location,
                    url=raw.get("absolute_url", ""),
                    description="",
                    posted_date=raw.get("first_published", "") or "",
                    remote=is_remote_job(title, "", location),
                ))
                if len(jobs) >= self.query.max_results_per_portal:
                    break

            await self._polite_delay()

        return self._build_result(jobs)


class LeverScraper(BaseScraper):
    name = "lever"
    rate_limit = 1.0

    async def scrape(self) -> ScraperResult:
        jobs = []
        for company in LEVER_COMPANIES:
            if len(jobs) >= self.query.max_results_per_portal:
                break
            url = f"https://api.lever.co/v0/postings/{company}?mode=json"
            data = await self.client.get(url, as_json=True)
            if not data or not isinstance(data, list):
                continue

            for raw in data:
                title = raw.get("text", "")
                categories = raw.get("categories", {}) or {}
                location = categories.get("location", "") or categories.get("team", "")
                description = clean_text(raw.get("descriptionPlain", "") or raw.get("description", ""))
                text = f"{title} {description}"
                if not self._text_matches_query(text):
                    continue

                jobs.append(self._build_job(
                    title=title,
                    company=company.title(),
                    location=location,
                    url=raw.get("hostedUrl", "") or raw.get("applyUrl", ""),
                    description=description,
                    job_type=categories.get("commitment", ""),
                    posted_date=raw.get("createdAt", "") or "",
                    remote=raw.get("workplaceType", "").lower() == "remote",
                ))
                if len(jobs) >= self.query.max_results_per_portal:
                    break

            await self._polite_delay()

        return self._build_result(jobs)


class SmartRecruitersScraper(BaseScraper):
    name = "smartrecruiters"
    rate_limit = 1.0

    async def scrape(self) -> ScraperResult:
        jobs = []
        for company in SMARTRECRUITER_COMPANIES:
            if len(jobs) >= self.query.max_results_per_portal:
                break
            url = f"https://api.smartrecruiters.com/v1/companies/{company}/postings"
            data = await self.client.get(url, as_json=True)
            if not data or "content" not in data:
                continue

            for raw in data["content"]:
                title = raw.get("name", "")
                location = raw.get("location", {}).get("city", "") if isinstance(raw.get("location"), dict) else ""
                text = f"{title} {location}"
                if not self._text_matches_query(text):
                    continue

                ref = raw.get("ref", "")
                job_url = f"https://jobs.smartrecruiters.com/{company}/{ref}" if ref else ""
                jobs.append(self._build_job(
                    title=title,
                    company=company.title(),
                    location=location,
                    url=job_url,
                    description="",
                    job_type=raw.get("typeOfEmployment", {}).get("label", "") if isinstance(raw.get("typeOfEmployment"), dict) else "",
                    posted_date=raw.get("releasedDate", "") or "",
                    remote=is_remote_job(title, "", location),
                ))
                if len(jobs) >= self.query.max_results_per_portal:
                    break

            await self._polite_delay()

        return self._build_result(jobs)


class AshbyScraper(BaseScraper):
    name = "ashby"
    rate_limit = 1.0

    async def scrape(self) -> ScraperResult:
        jobs = []
        for board in ASHBY_BOARDS:
            if len(jobs) >= self.query.max_results_per_portal:
                break
            url = f"https://api.ashbyhq.com/posting-api/job-board/{board}"
            data = await self.client.get(url, as_json=True)
            if not data or "jobs" not in data:
                continue

            for raw in data["jobs"]:
                title = raw.get("title", "")
                location = raw.get("location", "") or ""
                description = clean_text(raw.get("descriptionPlain", "") or "")
                text = f"{title} {description} {location}"
                if not self._text_matches_query(text):
                    continue

                jobs.append(self._build_job(
                    title=title,
                    company=board.title(),
                    location=location,
                    url=raw.get("jobUrl", "") or raw.get("applyUrl", ""),
                    description=description,
                    posted_date=raw.get("publishedAt", "") or "",
                    remote=is_remote_job(title, description, location),
                ))
                if len(jobs) >= self.query.max_results_per_portal:
                    break

            await self._polite_delay()

        return self._build_result(jobs)
