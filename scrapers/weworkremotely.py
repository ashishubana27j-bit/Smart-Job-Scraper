"""
scrapers/weworkremotely.py — We Work Remotely via public RSS feed.
Avoids 403 blocks on the HTML search page.
"""

import logging
import re
import xml.etree.ElementTree as ET
from html import unescape
from models import ScraperResult
from scrapers.base import BaseScraper
from utils.stealth_fetch import stealth_get
from utils.parser_helpers import clean_text, extract_salary

logger = logging.getLogger(__name__)

RSS_URL = "https://weworkremotely.com/remote-jobs.rss"
CATEGORY_RSS = "https://weworkremotely.com/categories/remote-programming-jobs.rss"


class WeWorkRemotelyScraper(BaseScraper):
    name = "weworkremotely"
    rate_limit = 1.0

    async def scrape(self) -> ScraperResult:
        self.logger.info("Fetching WeWorkRemotely RSS feed")
        xml_text = await stealth_get(RSS_URL)
        if not xml_text:
            xml_text = await stealth_get(CATEGORY_RSS)
        if not xml_text:
            return self._build_result([], success=False, error="Could not fetch WeWorkRemotely RSS")

        jobs = []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            return self._build_result([], success=False, error=f"Invalid RSS: {e}")

        for item in root.findall(".//item"):
            if len(jobs) >= self.query.max_results_per_portal:
                break
            title_raw = item.findtext("title", "")
            link = item.findtext("link", "")
            description = clean_text(unescape(item.findtext("description", "") or ""))
            # title format: "Company: Job Title"
            company, title = self._split_title(title_raw)
            text = f"{title} {description} {company}"
            if not self._text_matches_query(text):
                continue

            region = item.findtext("{http://purl.org/dc/elements/1.1/}creator", "") or "Remote"
            jobs.append(self._build_job(
                title=title,
                company=company,
                location=region or "Remote",
                url=link,
                description=description,
                salary=extract_salary(f"{title} {description}"),
                posted_date=item.findtext("pubDate", "") or "",
                remote=True,
            ))

        return self._build_result(jobs)

    @staticmethod
    def _split_title(raw: str) -> tuple[str, str]:
        raw = unescape(raw).strip()
        if ":" in raw:
            company, title = raw.split(":", 1)
            return company.strip(), title.strip()
        return "", raw
