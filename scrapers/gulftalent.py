"""scrapers/gulftalent.py — GulfTalent UAE jobs."""

import logging
from urllib.parse import quote_plus
from models import ScraperResult
from scrapers.base import BaseScraper
from utils.stealth_fetch import stealth_get
from utils.parser_helpers import make_soup, safe_text, safe_attr, absolute_url, is_remote_job

logger = logging.getLogger(__name__)

BASE_URL = "https://www.gulftalent.com"


class GulfTalentScraper(BaseScraper):
    name = "gulftalent"
    rate_limit = 2.5

    async def scrape(self) -> ScraperResult:
        url = f"{BASE_URL}/uae/jobs?q={quote_plus(self.query.query_string)}"
        self.logger.info(f"Scraping GulfTalent: {url}")
        html = await stealth_get(url, extra_headers={"Referer": BASE_URL})
        if not html:
            return self._build_result([], success=False, error="GulfTalent blocked request")

        soup = make_soup(html)
        jobs = []
        seen = set()

        for h2 in soup.select("h2"):
            a = h2.select_one("a")
            if not a:
                continue
            href = safe_attr(a, "href")
            if "/jobs/" not in href or href in seen:
                continue
            seen.add(href)
            title = safe_text(a)
            if not title or len(title) < 3:
                continue

            card = h2.find_parent("div")
            company = safe_text(card.select_one("[class*='company'], [class*='employer']")) if card else ""
            location = "UAE"

            jobs.append(self._build_job(
                title=title,
                company=company,
                location=location,
                url=absolute_url(BASE_URL, href),
                description="",
                remote=is_remote_job(title, "", location),
            ))
            if len(jobs) >= self.query.max_results_per_portal:
                break

        return self._build_result(jobs)
