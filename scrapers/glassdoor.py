"""
scrapers/glassdoor.py — Glassdoor jobs via stealth HTTP.
"""

import logging
from urllib.parse import quote_plus
from models import ScraperResult
from scrapers.base import BaseScraper
from utils.stealth_fetch import stealth_get
from utils.parser_helpers import make_soup, safe_text, safe_attr, absolute_url, is_remote_job, extract_salary

logger = logging.getLogger(__name__)

BASE_URL = "https://www.glassdoor.com"
SEARCH_URL = (
    "https://www.glassdoor.com/Job/jobs.htm?sc.keyword={query}"
    "&locT=N&locId=0&jobType=all&fromAge=-1&minSalary=0&includeNoSalaryJobs=true"
)


class GlassdoorScraper(BaseScraper):
    name = "glassdoor"
    rate_limit = 3.0

    async def scrape(self) -> ScraperResult:
        url = SEARCH_URL.format(query=quote_plus(self.query.query_string))
        self.logger.info(f"Scraping Glassdoor: {url}")
        html = await stealth_get(url, extra_headers={"Referer": BASE_URL})
        if not html:
            return self._build_result([], success=False, error="Glassdoor blocked request")

        soup = make_soup(html)
        cards = soup.select("li[data-test='jobListing'], [data-test='jobListing'], div.jobCard")
        self.logger.info(f"Found {len(cards)} Glassdoor cards")
        jobs = []

        for card in cards[: self.query.max_results_per_portal]:
            try:
                title_el = card.select_one("a[data-test='job-title'], [data-test='job-title']")
                title = safe_text(title_el)
                if not title:
                    continue

                company = safe_text(card.select_one(
                    "[data-test='employer-name'], .EmployerProfile_compactEmployerName__9MGcV, [class*='employerName']"
                ))
                location = safe_text(card.select_one(
                    "[data-test='emp-location'], span.loc"
                )) or self.query.location
                salary = safe_text(card.select_one("[data-test='detailSalary'], span.salaryEstimate"))
                href = safe_attr(title_el, "href") or safe_attr(
                    card.select_one("a[data-test='job-link'], a[href*='/job-listing/']"), "href"
                )
                job_url = absolute_url(BASE_URL, href)

                jobs.append(self._build_job(
                    title=title,
                    company=company,
                    location=location,
                    url=job_url,
                    description="",
                    salary=salary or extract_salary(safe_text(card)),
                    remote=is_remote_job(title, "", location),
                ))
            except Exception as e:
                self.logger.warning(f"Glassdoor parse error: {e}")

        return self._build_result(jobs)
