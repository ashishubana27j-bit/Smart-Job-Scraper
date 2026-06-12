"""scrapers/indeed_uae.py — Indeed UAE (ae.indeed.com)."""

import logging
from urllib.parse import quote_plus
from models import ScraperResult
from scrapers.base import BaseScraper
from utils.parser_helpers import (
    make_soup, safe_text, safe_attr, absolute_url,
    clean_text, extract_salary, is_remote_job,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://ae.indeed.com"
SEARCH_URL = "https://ae.indeed.com/jobs?q={query}&l={location}&sort=date&start={start}"


class IndeedUAEScraper(BaseScraper):
    name = "indeed_uae"
    rate_limit = 3.0

    async def scrape(self) -> ScraperResult:
        jobs = []
        start = 0
        per_page = 15
        location = self.query.location if self.query.location.lower() not in ("remote",) else "UAE"

        while len(jobs) < self.query.max_results_per_portal:
            url = SEARCH_URL.format(
                query=quote_plus(self.query.query_string),
                location=quote_plus(location),
                start=start,
            )
            self.logger.info(f"Scraping Indeed UAE offset={start}")
            html = await self.client.get(url, extra_headers={"Referer": BASE_URL})
            if not html:
                break

            soup = make_soup(html)
            cards = soup.select("div.job_seen_beacon, div[data-jk]")
            if not cards:
                break

            for card in cards:
                try:
                    title = safe_text(card.select_one("h2.jobTitle span, h2 a span"))
                    if not title:
                        continue
                    company = safe_text(card.select_one("span.companyName, [data-testid='company-name']"))
                    loc = safe_text(card.select_one("div.companyLocation, [data-testid='text-location']")) or location
                    jk = card.get("data-jk", "")
                    job_url = f"{BASE_URL}/viewjob?jk={jk}" if jk else ""
                    link_el = card.select_one("h2 a")
                    if not job_url and link_el:
                        job_url = absolute_url(BASE_URL, safe_attr(link_el, "href"))

                    description = ""
                    if job_url:
                        await self._polite_delay()
                        detail_html = await self.client.get(job_url)
                        if detail_html:
                            detail_soup = make_soup(detail_html)
                            description = clean_text(safe_text(
                                detail_soup.select_one("div#jobDescriptionText, div.jobsearch-jobDescriptionText")
                            ))

                    if not self._text_matches_query(f"{title} {description}"):
                        continue

                    jobs.append(self._build_job(
                        title=title,
                        company=company,
                        location=loc,
                        url=job_url,
                        description=description,
                        salary=extract_salary(f"{title} {description}"),
                        remote=is_remote_job(title, description, loc),
                    ))
                except Exception as e:
                    self.logger.warning(f"Indeed UAE parse error: {e}")

            if len(cards) < per_page:
                break
            start += per_page
            await self._polite_delay()

        return self._build_result(jobs)
