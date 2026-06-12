"""
scrapers/base.py — Abstract base class all scrapers must implement.
"""

import pathfix  # noqa
import asyncio
import random
import time
import logging
from abc import ABC, abstractmethod
from typing import Optional

from models import Job, SearchQuery, ScraperResult
from utils.http_client import HttpClient
from utils.parser_helpers import extract_skills_from_text, clean_text
from config import PAGE_LOAD_DELAY

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """
    Every job portal scraper inherits from this.

    Responsibilities:
    - Implement `scrape()` to return a ScraperResult
    - Use `self.client` for all HTTP requests (handles retries)
    - Call `self._polite_delay()` between page requests
    - Build Job objects and return them in ScraperResult
    """

    name: str = "base"          # Portal name, override in subclass
    rate_limit: float = 2.0     # Seconds between requests

    def __init__(self, query: SearchQuery, client: HttpClient):
        self.query = query
        self.client = client
        self.logger = logging.getLogger(f"scraper.{self.name}")

    @abstractmethod
    async def scrape(self) -> ScraperResult:
        """
        Main scraping method. Must return a ScraperResult.
        Implement pagination logic here.
        """
        ...

    async def _polite_delay(self):
        """Wait a random amount of time between requests (anti-bot)."""
        delay = random.uniform(*PAGE_LOAD_DELAY)
        await asyncio.sleep(max(delay, self.rate_limit))

    def _build_job(
        self,
        title: str,
        company: str,
        location: str,
        url: str,
        description: str = "",
        **kwargs,
    ) -> Job:
        """Create a Job with skill-match scoring."""
        skills_required = kwargs.pop("skills_required", [])
        job = Job(
            title=title,
            company=company,
            location=location,
            url=url,
            source_portal=self.name,
            description=clean_text(description),
            skills_required=skills_required,
            **kwargs,
        )
        text = f"{title} {job.description} {' '.join(skills_required)}"
        matched = extract_skills_from_text(text, self.query.skills)
        job.matched_skills = matched
        job.skill_match_score = len(matched) / len(self.query.skills) if self.query.skills else 0.0
        return job

    def _text_matches_query(self, text: str) -> bool:
        if not self.query.skills:
            return True
        return bool(extract_skills_from_text(text, self.query.skills))

    def _build_result(
        self,
        jobs: list[Job],
        success: bool = True,
        error: Optional[str] = None,
        duration: float = 0.0,
    ) -> ScraperResult:
        return ScraperResult(
            portal=self.name,
            jobs=jobs,
            success=success,
            error=error,
            total_found=len(jobs),
            duration_seconds=duration,
        )

    async def _safe_scrape(self) -> ScraperResult:
        """Wrap scrape() with timing and error catching."""
        start = time.monotonic()
        try:
            result = await self.scrape()
            result.duration_seconds = time.monotonic() - start
            return result
        except Exception as e:
            duration = time.monotonic() - start
            self.logger.error(f"Scraper {self.name} crashed: {e}", exc_info=True)
            return ScraperResult(
                portal=self.name,
                success=False,
                error=str(e),
                duration_seconds=duration,
            )
