"""
core/scheduler.py — Async orchestrator that runs all scrapers concurrently.
Controls concurrency, collects results, handles failures gracefully.
"""

import pathfix  # noqa — adds project root to sys.path
import asyncio
import logging
from models import SearchQuery, ScraperResult, Job
from scrapers import SCRAPER_REGISTRY
from utils.http_client import HttpClient
from config import CONCURRENT_SCRAPERS

logger = logging.getLogger(__name__)


class Scheduler:
    """
    Runs multiple scrapers concurrently using asyncio.
    Limits concurrency to avoid overwhelming the machine or getting IP-banned.
    """

    def __init__(self, query: SearchQuery):
        self.query = query
        self.semaphore = asyncio.Semaphore(CONCURRENT_SCRAPERS)

    async def _run_one(self, portal: str, client: HttpClient) -> ScraperResult:
        """Run a single scraper, guarded by semaphore."""
        scraper_cls = SCRAPER_REGISTRY.get(portal)
        if not scraper_cls:
            logger.warning(f"Unknown portal: {portal}")
            return ScraperResult(portal=portal, success=False, error="Unknown portal")

        async with self.semaphore:
            try:
                scraper = scraper_cls(self.query, client)
                logger.info(f"▶ Starting scraper: {portal}")
                result = await scraper._safe_scrape()
                logger.info(f"◀ Done [{portal}]: {result}")
                return result
            except Exception as e:
                logger.error(f"Scraper {portal} failed: {e}", exc_info=True)
                return ScraperResult(portal=portal, success=False, error=str(e))

    async def run_all(self) -> list[ScraperResult]:
        """
        Run all selected portal scrapers concurrently.
        Returns list of ScraperResult (one per portal).
        """
        portals = [p for p in self.query.portals if p in SCRAPER_REGISTRY]

        if not portals:
            logger.error("No valid portals selected!")
            return []

        logger.info(f"Starting scrape: {portals} | skills={self.query.skills} | location={self.query.location}")

        async with HttpClient() as client:
            tasks = [self._run_one(portal, client) for portal in portals]
            raw = await asyncio.gather(*tasks, return_exceptions=True)

        results = []
        for portal, item in zip(portals, raw):
            if isinstance(item, Exception):
                logger.error(f"Scraper {portal} raised: {item}")
                results.append(ScraperResult(portal=portal, success=False, error=str(item)))
            else:
                results.append(item)
        return results

    def collect_jobs(self, results: list[ScraperResult]) -> list[Job]:
        """Flatten all results into a single job list."""
        all_jobs = []
        for result in results:
            if result.success:
                all_jobs.extend(result.jobs)
        return all_jobs
