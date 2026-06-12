"""
scrapers/__init__.py — Scraper registry.
Maps portal names to scraper classes.
"""

import pathfix  # noqa
from scrapers.remotive import RemotiveScraper
from scrapers.weworkremotely import WeWorkRemotelyScraper
from scrapers.linkedin import LinkedInScraper
from scrapers.indeed import IndeedScraper
from scrapers.glassdoor import GlassdoorScraper
from scrapers.stackoverflow import StackOverflowScraper

# Tier 1 — APIs & remote boards
from scrapers.remoteok import RemoteOKScraper
from scrapers.arbeitnow import ArbeitnowScraper
from scrapers.workingnomads import WorkingNomadsScraper
from scrapers.adzuna import AdzunaScraper
from scrapers.jobspresso import JobspressoScraper
from scrapers.jooble import JoobleScraper
from scrapers.startupjobs import StartupJobsScraper

# Tier 2 — UAE / Gulf (dedicated stealth/browser scrapers)
from scrapers.indeed_uae import IndeedUAEScraper
from scrapers.naukrigulf import NaukrigulfScraper
from scrapers.bayt import BaytScraper
from scrapers.foundit import FounditScraper
from scrapers.gulftalent import GulfTalentScraper

# Tier 3 — ATS APIs
from scrapers.ats_api import GreenhouseScraper, LeverScraper, SmartRecruitersScraper, AshbyScraper

# Configurable HTML portals (sites that work with standard HTTP)
from scrapers.html_portal import create_html_scraper

JobrapidoScraper = create_html_scraper(
    name="jobrapido",
    base_url="https://www.jobrapido.com",
    search_url="https://www.jobrapido.com/jobs?q={query}&l={location}",
    list_selector="article, div.result, li.result, div.job",
    title_selector="h2 a, h3 a, .title a, a.title",
    company_selector=".company, .employer, .company-name",
    location_selector=".location, .place, .city",
    rate_limit=2.5,
)

TalentScraper = create_html_scraper(
    name="talent",
    base_url="https://www.talent.com",
    search_url="https://www.talent.com/jobs?k={query}&l={location}",
    list_selector="article[data-testid='job-card-unified'], article[class*='JobCard']",
    title_selector="h2, h3, [class*='JobCard_title'], [class*='job-title']",
    company_selector="[class*='JobCard_company'], .company, .company-name",
    location_selector="[class*='JobCard_location'], .location, .place",
    rate_limit=2.5,
)

SCRAPER_REGISTRY: dict = {
    # Original portals
    "remotive": RemotiveScraper,
    "weworkremotely": WeWorkRemotelyScraper,
    "linkedin": LinkedInScraper,
    "indeed": IndeedScraper,
    "glassdoor": GlassdoorScraper,
    "stackoverflow": StackOverflowScraper,
    # Tier 1
    "remoteok": RemoteOKScraper,
    "arbeitnow": ArbeitnowScraper,
    "workingnomads": WorkingNomadsScraper,
    "adzuna": AdzunaScraper,
    "jooble": JoobleScraper,
    "jobrapido": JobrapidoScraper,
    "talent": TalentScraper,
    "jobspresso": JobspressoScraper,
    "startupjobs": StartupJobsScraper,
    # Tier 2 — UAE / Gulf
    "bayt": BaytScraper,
    "gulftalent": GulfTalentScraper,
    "naukrigulf": NaukrigulfScraper,
    "indeed_uae": IndeedUAEScraper,
    "foundit": FounditScraper,
    # Tier 3 — ATS APIs
    "greenhouse": GreenhouseScraper,
    "lever": LeverScraper,
    "smartrecruiters": SmartRecruitersScraper,
    "ashby": AshbyScraper,
}

PORTAL_GROUPS = {
    "remote_api": ["remotive", "remoteok", "arbeitnow", "workingnomads", "weworkremotely", "jobspresso"],
    "aggregators": ["jooble", "jobrapido", "talent", "adzuna", "startupjobs"],
    "uae_gulf": ["bayt", "gulftalent", "naukrigulf", "indeed_uae", "foundit"],
    "ats_careers": ["greenhouse", "lever", "smartrecruiters", "ashby"],
    "difficult": ["linkedin", "indeed", "glassdoor", "stackoverflow"],
}

__all__ = ["SCRAPER_REGISTRY", "PORTAL_GROUPS"]
