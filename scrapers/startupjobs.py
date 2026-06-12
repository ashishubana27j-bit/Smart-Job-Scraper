"""
scrapers/startupjobs.py — startup.jobs listings.
Uses stealth HTTP on skill slug pages (e.g. /python-jobs).
"""

import logging
import re
from models import ScraperResult
from scrapers.base import BaseScraper
from utils.stealth_fetch import stealth_get
from utils.parser_helpers import make_soup, safe_text, safe_attr, absolute_url, clean_text

logger = logging.getLogger(__name__)

BASE_URL = "https://startup.jobs"


class StartupJobsScraper(BaseScraper):
    name = "startupjobs"
    rate_limit = 2.5

    async def scrape(self) -> ScraperResult:
        slug = self.query.query_string.lower().replace(" ", "-")
        url = f"{BASE_URL}/{slug}-jobs"
        self.logger.info(f"Scraping Startup.jobs: {url}")
        html = await stealth_get(url, extra_headers={"Referer": BASE_URL})
        if not html:
            return self._build_result([], success=False, error="Startup.jobs blocked request")

        jobs = []
        seen = set()

        # Embedded JSON job blobs in page scripts
        for block in re.findall(r'\{[^{}]*"title"\s*:\s*"[^"]+"[^{}]*\}', html):
            try:
                import json
                obj = json.loads(block)
                title = obj.get("title", "")
                link = obj.get("url") or obj.get("link") or ""
                if title and link and link not in seen:
                    seen.add(link)
                    if self._text_matches_query(title):
                        jobs.append(self._build_job(
                            title=title,
                            company=obj.get("company", "") or obj.get("startup_name", ""),
                            location=obj.get("location", "") or "Remote",
                            url=absolute_url(BASE_URL, link),
                            description=clean_text(obj.get("description", "") or ""),
                            remote=True,
                        ))
            except Exception:
                pass

        # Fallback: parse anchor links
        if not jobs:
            soup = make_soup(html)
            for a in soup.select("a[href*='/jobs/'], a[href*='/job/']"):
                href = safe_attr(a, "href")
                title = safe_text(a)
                if not title or len(title) < 5 or href in seen:
                    continue
                seen.add(href)
                if not self._text_matches_query(title):
                    continue
                jobs.append(self._build_job(
                    title=title,
                    company="",
                    location="Remote",
                    url=absolute_url(BASE_URL, href),
                    description="",
                    remote=True,
                ))
                if len(jobs) >= self.query.max_results_per_portal:
                    break

        if not jobs:
            return self._build_result(
                [], success=False,
                error="Startup.jobs is a JS-only SPA with no public API/RSS — cannot scrape reliably",
            )
        return self._build_result(jobs)
