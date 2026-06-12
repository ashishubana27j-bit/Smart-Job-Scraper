"""
scrapers/indeed.py — Indeed.com job scraper.

NOTE: Indeed actively blocks scrapers. Strategies used here:
  - Random delays
  - User-agent rotation
  - Limiting requests per session
  For production, consider Indeed's Publisher API (free for small usage).
"""

import logging
from urllib.parse import quote_plus
from models import Job, ScraperResult
from scrapers.base import BaseScraper
from utils.parser_helpers import (
    make_soup, safe_text, safe_attr, absolute_url,
    extract_skills_from_text, is_remote_job, clean_text, extract_salary
)

logger = logging.getLogger(__name__)

BASE_URL = "https://www.indeed.com"
SEARCH_URL = "https://www.indeed.com/jobs?q={query}&l={location}&sort=date&start={start}"


class IndeedScraper(BaseScraper):
    name = "indeed"
    rate_limit = 2.5

    async def scrape(self) -> ScraperResult:
        jobs = []
        start = 0
        per_page = 15  # Indeed shows ~15 results per page

        while len(jobs) < self.query.max_results_per_portal:
            url = SEARCH_URL.format(
                query=quote_plus(self.query.query_string),
                location=quote_plus(self.query.location),
                start=start,
            )

            self.logger.info(f"Scraping Indeed offset={start}: {url}")
            html = await self.client.get(url, extra_headers={
                "Referer": "https://www.indeed.com/",
            })

            if not html:
                break

            soup = make_soup(html)

            # Indeed job cards (selector changes frequently!)
            cards = soup.select("div.job_seen_beacon")
            if not cards:
                cards = soup.select("div[data-jk]")  # Alternate

            if not cards:
                self.logger.warning("No Indeed cards found — layout may have changed")
                break

            self.logger.info(f"Found {len(cards)} Indeed cards at offset {start}")

            for card in cards:
                try:
                    title_el = card.select_one("h2.jobTitle span, h2 a span")
                    title = safe_text(title_el)

                    company_el = card.select_one("span.companyName, [data-testid='company-name']")
                    company = safe_text(company_el)

                    location_el = card.select_one("div.companyLocation, [data-testid='text-location']")
                    location = safe_text(location_el) or self.query.location

                    salary_el = card.select_one("div.salary-snippet-container, div.metadata")
                    salary = safe_text(salary_el)

                    # Build job URL
                    jk = card.get("data-jk", "")
                    job_url = f"{BASE_URL}/viewjob?jk={jk}" if jk else ""

                    link_el = card.select_one("h2 a")
                    if not job_url and link_el:
                        href = safe_attr(link_el, "href")
                        job_url = absolute_url(BASE_URL, href)

                    # Fetch description
                    description = ""
                    if job_url:
                        await self._polite_delay()
                        detail_html = await self.client.get(job_url)
                        if detail_html:
                            detail_soup = make_soup(detail_html)
                            desc_el = detail_soup.select_one(
                                "div#jobDescriptionText, div.jobsearch-jobDescriptionText"
                            )
                            description = clean_text(safe_text(desc_el))
                            if not salary:
                                salary = extract_salary(description)

                    job = Job(
                        title=title,
                        company=company,
                        location=location,
                        url=job_url,
                        source_portal=self.name,
                        description=description,
                        salary=salary,
                        remote=is_remote_job(title, description, location),
                    )

                    matched = extract_skills_from_text(
                        f"{title} {description}", self.query.skills
                    )
                    job.matched_skills = matched
                    job.skill_match_score = len(matched) / len(self.query.skills) if self.query.skills else 0.0

                    jobs.append(job)

                except Exception as e:
                    self.logger.warning(f"Error parsing Indeed card: {e}")
                    continue

            if len(cards) < per_page:
                break

            start += per_page
            await self._polite_delay()

        return self._build_result(jobs)
