"""scrapers/bayt.py — Bayt.com UAE jobs (stealth HTTP)."""

import logging
from urllib.parse import quote_plus
from models import ScraperResult
from scrapers.base import BaseScraper
from utils.stealth_fetch import stealth_get
from utils.parser_helpers import make_soup, safe_text, safe_attr, absolute_url, clean_text, is_remote_job

logger = logging.getLogger(__name__)

BASE_URL = "https://www.bayt.com"


class BaytScraper(BaseScraper):
    name = "bayt"
    rate_limit = 2.5

    async def scrape(self) -> ScraperResult:
        url = f"{BASE_URL}/en/uae/jobs/?keywords={quote_plus(self.query.query_string)}"
        self.logger.info(f"Scraping Bayt: {url}")
        html = await stealth_get(url, extra_headers={"Referer": BASE_URL})
        if not html:
            return self._build_result([], success=False, error="Bayt blocked request")

        soup = make_soup(html)
        items = soup.select("li[data-js-job], li.has-pointer-d")
        jobs = []

        for item in items[: self.query.max_results_per_portal]:
            try:
                title_el = item.select_one("h2 a, a.t-large, .job-title a")
                title = safe_text(title_el)
                if not title:
                    continue
                job_url = absolute_url(BASE_URL, safe_attr(title_el, "href"))
                company_el = item.select_one(".job-company-location-wrapper a, [class*='company'] a")
                company = safe_text(company_el)
                location = safe_text(item.select_one(".job-company-location-wrapper, [class*='location']")) or "UAE"
                description = clean_text(safe_text(item))

                jobs.append(self._build_job(
                    title=title,
                    company=company,
                    location=location,
                    url=job_url,
                    description=description,
                    remote=is_remote_job(title, description, location),
                ))
            except Exception as e:
                self.logger.warning(f"Bayt parse error: {e}")

        return self._build_result(jobs)
