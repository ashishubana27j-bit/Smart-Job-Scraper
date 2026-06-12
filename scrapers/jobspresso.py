"""scrapers/jobspresso.py — Jobspresso remote tech jobs."""

import logging
from urllib.parse import quote_plus
from models import ScraperResult
from scrapers.base import BaseScraper
from utils.parser_helpers import make_soup, safe_text, safe_attr, absolute_url, clean_text

logger = logging.getLogger(__name__)

BASE_URL = "https://jobspresso.co"
SEARCH_URL = "https://jobspresso.co/?s={query}"


class JobspressoScraper(BaseScraper):
    name = "jobspresso"
    rate_limit = 2.0

    async def scrape(self) -> ScraperResult:
        url = SEARCH_URL.format(query=quote_plus(self.query.query_string))
        html = await self.client.get(url, extra_headers={"Referer": BASE_URL})
        if not html:
            return self._build_result([], success=False, error="Could not fetch page")

        soup = make_soup(html)
        items = soup.select("article")
        jobs = []

        for item in items[: self.query.max_results_per_portal]:
            try:
                title_el = item.select_one("h2 a, h1.entry-title a, .entry-title a")
                title = safe_text(title_el)
                if not title:
                    continue
                job_url = absolute_url(BASE_URL, safe_attr(title_el, "href"))
                excerpt = clean_text(safe_text(item.select_one(".entry-content, .post-content, p")))
                if not self._text_matches_query(f"{title} {excerpt}"):
                    continue

                jobs.append(self._build_job(
                    title=title,
                    company="",
                    location="Remote",
                    url=job_url,
                    description=excerpt,
                    remote=True,
                ))
            except Exception as e:
                self.logger.warning(f"Jobspresso parse error: {e}")

        return self._build_result(jobs)
