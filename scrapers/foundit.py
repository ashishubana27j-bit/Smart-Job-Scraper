"""scrapers/foundit.py — Foundit Gulf (formerly Monster Gulf) jobs."""

import logging
from models import ScraperResult
from scrapers.base import BaseScraper
from utils.stealth_fetch import stealth_get
from utils.parser_helpers import make_soup, safe_text, safe_attr, absolute_url, clean_text, is_remote_job

logger = logging.getLogger(__name__)

BASE_URL = "https://www.founditgulf.com"


class FounditScraper(BaseScraper):
    name = "foundit"
    rate_limit = 2.5

    async def scrape(self) -> ScraperResult:
        slug = self.query.query_string.lower().replace(" ", "-")
        url = f"{BASE_URL}/search/{slug}-jobs-in-uae"
        self.logger.info(f"Scraping Foundit: {url}")
        html = await stealth_get(url, extra_headers={"Referer": BASE_URL})
        if not html:
            return self._build_result([], success=False, error="Foundit blocked request")

        soup = make_soup(html)
        jobs = []
        seen = set()

        for h2 in soup.select("h2"):
            a = h2.select_one("a")
            if not a:
                continue
            title = safe_text(a)
            href = safe_attr(a, "href")
            if not title or href in seen:
                continue
            seen.add(href)

            card = h2.find_parent("div")
            company = ""
            location = "UAE"
            if card:
                for span in card.select("span, p"):
                    txt = safe_text(span)
                    if txt and txt != title and len(txt) < 80 and not company:
                        if any(c in txt.lower() for c in ("dubai", "uae", "abu dhabi", "sharjah")):
                            location = txt
                        elif not txt.startswith("http"):
                            company = txt

            job_url = absolute_url(BASE_URL, href)
            if not self._text_matches_query(title):
                continue

            jobs.append(self._build_job(
                title=title,
                company=company,
                location=location,
                url=job_url,
                description="",
                remote=is_remote_job(title, "", location),
            ))
            if len(jobs) >= self.query.max_results_per_portal:
                break

        return self._build_result(jobs)
