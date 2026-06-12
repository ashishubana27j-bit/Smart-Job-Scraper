"""
scrapers/html_portal.py — Configurable HTML job portal scraper.
Used for aggregators and regional boards with similar list-page layouts.
"""

from urllib.parse import quote_plus
from models import ScraperResult
from scrapers.base import BaseScraper
from utils.parser_helpers import (
    make_soup, safe_text, safe_attr, absolute_url,
    clean_text, extract_salary, is_remote_job,
)


def create_html_scraper(
    name: str,
    base_url: str,
    search_url: str,
    list_selector: str,
    title_selector: str = "h2, h3, .title",
    company_selector: str = ".company, .company-name, span.company",
    location_selector: str = ".location, .region, .place",
    link_selector: str = "a",
    rate_limit: float = 2.5,
    fetch_details: bool = False,
    detail_selector: str = "article, .description, .job-description, #job-description",
):
    """Factory: returns a scraper class for a configured HTML portal."""

    async def scrape(self) -> ScraperResult:
        slug = self.query.query_string.lower().replace(" ", "-")
        url = search_url.format(
            query=quote_plus(self.query.query_string),
            query_slug=slug,
            location=quote_plus(self.query.location),
        )
        self.logger.info(f"Scraping {name}: {url}")
        html = await self.client.get(url, extra_headers={"Referer": base_url})
        if not html:
            return self._build_result(
                [], success=False,
                error="Blocked or unreachable (site returned 403/timeout — anti-bot protection)",
            )

        soup = make_soup(html)
        items = soup.select(list_selector)
        self.logger.info(f"Found {len(items)} listings on {name}")
        if not items:
            return self._build_result(
                [], success=False,
                error="Page loaded but no job listings found (layout may have changed)",
            )

        jobs = []
        for item in items[: self.query.max_results_per_portal]:
            try:
                title_el = item.select_one(title_selector)
                title = safe_text(title_el)
                if not title:
                    title = safe_text(item.select_one("h2, h3, h4, [class*='title'], [class*='Title']"))
                if not title or len(title) < 3:
                    continue

                company = safe_text(item.select_one(company_selector)) or "Unknown"
                location = safe_text(item.select_one(location_selector)) or self.query.location

                link_el = item.select_one(link_selector)
                href = safe_attr(link_el, "href")
                job_url = absolute_url(base_url, href)

                description = safe_text(item)
                if fetch_details and job_url:
                    await self._polite_delay()
                    detail_html = await self.client.get(job_url, extra_headers={"Referer": base_url})
                    if detail_html:
                        detail_soup = make_soup(detail_html)
                        description = clean_text(safe_text(detail_soup.select_one(detail_selector)))

                if not self._text_matches_query(f"{title} {description}"):
                    continue

                jobs.append(self._build_job(
                    title=title,
                    company=company,
                    location=location,
                    url=job_url,
                    description=description,
                    salary=extract_salary(f"{title} {description}"),
                    remote=is_remote_job(title, description, location),
                ))
            except Exception as e:
                self.logger.warning(f"Error parsing {name} listing: {e}")

        return self._build_result(jobs)

    class_name = "".join(part.title() for part in name.split("_")) + "Scraper"
    return type(
        class_name,
        (BaseScraper,),
        {"name": name, "rate_limit": rate_limit, "scrape": scrape},
    )
