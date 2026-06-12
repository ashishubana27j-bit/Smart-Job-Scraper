"""
scrapers/stackoverflow.py — Stack Overflow Jobs scraper.
SO Jobs is developer-focused with good tech job coverage.
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

BASE_URL = "https://stackoverflow.com"
SEARCH_URL = "https://stackoverflow.com/jobs?q={query}&l={location}&r={remote}&pg={page}"


class StackOverflowScraper(BaseScraper):
    name = "stackoverflow"
    rate_limit = 2.0

    async def scrape(self) -> ScraperResult:
        jobs = []
        page = 1

        while len(jobs) < self.query.max_results_per_portal:
            url = SEARCH_URL.format(
                query=quote_plus(self.query.query_string),
                location=quote_plus(self.query.location),
                remote="true" if self.query.remote_only else "false",
                page=page,
            )

            self.logger.info(f"Scraping StackOverflow page {page}: {url}")
            html = await self.client.get(url)

            if not html:
                break

            soup = make_soup(html)
            cards = soup.select("div.-job")

            if not cards:
                cards = soup.select("div[data-jobid]")

            if not cards:
                self.logger.warning("No SO cards found")
                break

            self.logger.info(f"Found {len(cards)} SO cards on page {page}")

            for card in cards:
                try:
                    title_el = card.select_one("h2 a, .job-link")
                    title = safe_text(title_el)

                    company_el = card.select_one("h3.fc-black-700, .employer")
                    company = safe_text(company_el)

                    location_el = card.select_one("span.fc-black-500, .location")
                    location = safe_text(location_el) or self.query.location

                    href = safe_attr(title_el, "href")
                    job_url = absolute_url(BASE_URL, href)

                    # Tags = skills on Stack Overflow
                    tag_els = card.select("a.post-tag")
                    tags = [safe_text(t) for t in tag_els]

                    description = ""
                    salary = ""
                    if job_url:
                        await self._polite_delay()
                        detail_html = await self.client.get(job_url)
                        if detail_html:
                            detail_soup = make_soup(detail_html)
                            desc_el = detail_soup.select_one("section.job-details--content")
                            description = clean_text(safe_text(desc_el))
                            salary_el = detail_soup.select_one("span.salary")
                            salary = safe_text(salary_el) or extract_salary(description)

                    job = Job(
                        title=title,
                        company=company,
                        location=location,
                        url=job_url,
                        source_portal=self.name,
                        description=description,
                        salary=salary,
                        skills_required=tags,
                        remote=is_remote_job(title, description, location),
                    )

                    matched = extract_skills_from_text(
                        f"{title} {description} {' '.join(tags)}", self.query.skills
                    )
                    job.matched_skills = matched
                    job.skill_match_score = len(matched) / len(self.query.skills) if self.query.skills else 0.0

                    jobs.append(job)

                except Exception as e:
                    self.logger.warning(f"Error parsing SO card: {e}")

            if len(cards) < 25:
                break

            page += 1
            await self._polite_delay()

        return self._build_result(jobs)
