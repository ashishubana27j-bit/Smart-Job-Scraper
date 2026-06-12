"""
scrapers/linkedin.py — LinkedIn Jobs scraper.
Scrapes public LinkedIn job listing pages (no login required for listings).

NOTE: LinkedIn aggressively blocks scrapers. Tips to avoid blocks:
  - Use long delays (3-5s between requests)
  - Rotate user agents
  - Use proxies if scraping at scale
  - Consider LinkedIn's official Jobs API for production use
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

SEARCH_URL = (
    "https://www.linkedin.com/jobs/search/"
    "?keywords={query}&location={location}&f_TPR=r86400&start={start}"
)


class LinkedInScraper(BaseScraper):
    name = "linkedin"
    rate_limit = 3.5  # LinkedIn is strict

    async def scrape(self) -> ScraperResult:
        jobs = []
        start = 0
        per_page = 25  # LinkedIn returns 25 per page

        while len(jobs) < self.query.max_results_per_portal:
            url = SEARCH_URL.format(
                query=quote_plus(self.query.query_string),
                location=quote_plus(self.query.location),
                start=start,
            )

            self.logger.info(f"Scraping LinkedIn page offset={start}: {url}")
            html = await self.client.get(url)

            if not html:
                break

            soup = make_soup(html)

            # LinkedIn public job cards
            cards = soup.select("div.base-card")
            if not cards:
                # Try alternate selector
                cards = soup.select("li.jobs-search-results__list-item")

            if not cards:
                self.logger.warning("No LinkedIn job cards found — may be blocked or layout changed")
                break

            self.logger.info(f"Found {len(cards)} LinkedIn cards at offset {start}")

            for card in cards:
                try:
                    title_el = card.select_one("h3.base-search-card__title, h3.job-search-card__title")
                    title = safe_text(title_el)

                    company_el = card.select_one("h4.base-search-card__subtitle, a.job-search-card__company-name")
                    company = safe_text(company_el)

                    location_el = card.select_one("span.job-search-card__location")
                    location = safe_text(location_el) or self.query.location

                    link_el = card.select_one("a.base-card__full-link, a.job-search-card__title-link")
                    job_url = safe_attr(link_el, "href")

                    # Clean LinkedIn tracking params
                    if "?" in job_url:
                        job_url = job_url.split("?")[0]

                    date_el = card.select_one("time")
                    posted_date = safe_attr(date_el, "datetime")

                    job = Job(
                        title=title,
                        company=company,
                        location=location,
                        url=job_url,
                        source_portal=self.name,
                        posted_date=posted_date,
                        remote=is_remote_job(title, "", location),
                    )

                    # Optionally fetch detail page for description
                    # (Comment this out if you want speed over detail)
                    if job_url:
                        await self._polite_delay()
                        detail_html = await self.client.get(job_url)
                        if detail_html:
                            detail_soup = make_soup(detail_html)
                            desc_el = detail_soup.select_one(
                                "div.description__text, section.show-more-less-html"
                            )
                            job.description = clean_text(safe_text(desc_el))
                            job.salary = extract_salary(job.description)

                    matched = extract_skills_from_text(
                        f"{title} {job.description}", self.query.skills
                    )
                    job.matched_skills = matched
                    job.skill_match_score = len(matched) / len(self.query.skills) if self.query.skills else 0.0

                    jobs.append(job)

                except Exception as e:
                    self.logger.warning(f"Error parsing LinkedIn card: {e}")
                    continue

            if len(cards) < per_page:
                break  # No more pages

            start += per_page
            await self._polite_delay()

        return self._build_result(jobs)
