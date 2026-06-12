"""
scrapers/remotive.py — Remotive.com scraper.
Remotive has a FREE public JSON API — no HTML parsing needed.
API docs: https://remotive.com/api/remote-jobs
"""

import logging
from models import Job, ScraperResult
from scrapers.base import BaseScraper
from utils.parser_helpers import extract_skills_from_text, is_remote_job, clean_text

logger = logging.getLogger(__name__)

API_URL = "https://remotive.com/api/remote-jobs"


class RemotiveScraper(BaseScraper):
    name = "remotive"
    rate_limit = 1.0  # Very polite, they have a free API

    async def scrape(self) -> ScraperResult:
        jobs = []

        # Remotive API accepts a 'search' param and optional 'category'
        params = {
            "search": self.query.query_string,
            "limit": self.query.max_results_per_portal,
        }

        self.logger.info(f"Fetching Remotive API: {params}")
        data = await self.client.get(API_URL, params=params, as_json=True)

        if not data:
            return self._build_result([], success=False, error="Empty API response")

        raw_jobs = data.get("jobs", [])
        self.logger.info(f"Remotive returned {len(raw_jobs)} jobs")

        for raw in raw_jobs:
            try:
                description = clean_text(raw.get("description", ""))
                title = raw.get("title", "")
                company = raw.get("company_name", "")
                location = raw.get("candidate_required_location", "Remote")
                url = raw.get("url", "")
                salary = raw.get("salary", "")
                job_type = raw.get("job_type", "")
                tags = raw.get("tags", [])

                job = Job(
                    title=title,
                    company=company,
                    location=location,
                    url=url,
                    source_portal=self.name,
                    description=description,
                    salary=salary,
                    job_type=job_type,
                    skills_required=tags,
                    posted_date=raw.get("publication_date", ""),
                    remote=True,
                )

                # Match skills
                matched = extract_skills_from_text(
                    f"{title} {description} {' '.join(tags)}",
                    self.query.skills
                )
                job.matched_skills = matched
                job.skill_match_score = len(matched) / len(self.query.skills) if self.query.skills else 0.0

                jobs.append(job)

            except Exception as e:
                self.logger.warning(f"Error parsing Remotive job: {e}")
                continue

        return self._build_result(jobs)
