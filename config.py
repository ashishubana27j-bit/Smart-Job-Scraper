"""
config.py — Global configuration for the Job Scraper.
Edit portal URLs, headers, delays, and storage settings here.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ─── HTTP Settings ────────────────────────────────────────────────────────────
REQUEST_TIMEOUT = 30        # Seconds per request
MAX_RETRIES = 3             # Retry failed requests
RETRY_DELAY = 2.0           # Seconds between retries (exponential backoff applied)
CONCURRENT_SCRAPERS = 10    # How many scrapers run in parallel
PAGE_LOAD_DELAY = (1.5, 3.5)  # Random delay range (min, max) seconds between pages

# ─── User-Agent rotation pool ─────────────────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
]

# ─── Common headers (per-scraper can override) ────────────────────────────────
BASE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
}

# ─── Portal configurations ────────────────────────────────────────────────────
PORTAL_CONFIGS = {
    "remotive": {
        "enabled": True,
        "base_url": "https://remotive.com/api/remote-jobs",
        "rate_limit": 1.0,    # Seconds between requests (polite)
        "type": "api",        # "api" = uses JSON API, "html" = scrape HTML
    },
    "weworkremotely": {
        "enabled": True,
        "base_url": "https://weworkremotely.com",
        "search_url": "https://weworkremotely.com/remote-jobs/search?term={query}",
        "rate_limit": 2.0,
        "type": "html",
    },
    "stackoverflow": {
        "enabled": True,
        "base_url": "https://stackoverflow.com/jobs",
        "search_url": "https://stackoverflow.com/jobs?q={query}&l={location}&r={remote}",
        "rate_limit": 2.0,
        "type": "html",
    },
    "linkedin": {
        "enabled": True,
        "search_url": "https://www.linkedin.com/jobs/search/?keywords={query}&location={location}&f_TPR=r86400",
        "rate_limit": 3.0,    # LinkedIn is aggressive, be polite
        "type": "html",
        "requires_js": False,  # Can scrape public listings without JS
    },
    "indeed": {
        "enabled": True,
        "search_url": "https://www.indeed.com/jobs?q={query}&l={location}&sort=date",
        "rate_limit": 2.5,
        "type": "html",
    },
    "glassdoor": {
        "enabled": True,
        "search_url": "https://www.glassdoor.com/Job/jobs.htm?sc.keyword={query}&locT=C&locId=0",
        "rate_limit": 3.0,
        "type": "html",
    },
    # Tier 1 — aggregators & remote boards
    "remoteok": {"enabled": True, "type": "api", "rate_limit": 1.5},
    "arbeitnow": {"enabled": True, "type": "api", "rate_limit": 1.0},
    "workingnomads": {"enabled": True, "type": "api", "rate_limit": 1.0},
    "adzuna": {"enabled": True, "type": "api", "rate_limit": 1.0},
    "jooble": {"enabled": True, "type": "html", "rate_limit": 2.5},
    "jobrapido": {"enabled": True, "type": "html", "rate_limit": 2.5},
    "talent": {"enabled": True, "type": "html", "rate_limit": 2.5},
    "jobspresso": {"enabled": True, "type": "html", "rate_limit": 2.0},
    "startupjobs": {"enabled": True, "type": "html", "rate_limit": 2.5},
    # Tier 2 — UAE / Gulf
    "bayt": {"enabled": True, "type": "html", "rate_limit": 3.0},
    "gulftalent": {"enabled": True, "type": "html", "rate_limit": 3.0},
    "naukrigulf": {"enabled": True, "type": "html", "rate_limit": 3.0},
    "indeed_uae": {"enabled": True, "type": "html", "rate_limit": 3.0},
    "foundit": {"enabled": True, "type": "html", "rate_limit": 3.0},
    # Tier 3 — ATS career-page APIs (multi-company)
    "greenhouse": {"enabled": True, "type": "api", "rate_limit": 1.0},
    "lever": {"enabled": True, "type": "api", "rate_limit": 1.0},
    "smartrecruiters": {"enabled": True, "type": "api", "rate_limit": 1.0},
    "ashby": {"enabled": True, "type": "api", "rate_limit": 1.0},
}

# Companies/boards queried by ATS scrapers (add your targets in .env or here)
def _csv_env(key: str, default: str) -> list[str]:
    return [x.strip() for x in os.getenv(key, default).split(",") if x.strip()]


GREENHOUSE_BOARDS = _csv_env(
    "GREENHOUSE_BOARDS",
    "stripe,airbnb,discord,figma,notion,cloudflare,gitlab,doordash,dropbox",
)

LEVER_COMPANIES = _csv_env(
    "LEVER_COMPANIES",
    "palantir,netflix,spotify,reddit,lyft,twitch,canva",
)

SMARTRECRUITER_COMPANIES = _csv_env(
    "SMARTRECRUITER_COMPANIES",
    "SmartRecruiters,Visa,Skechers,Equinix",
)

ASHBY_BOARDS = _csv_env(
    "ASHBY_BOARDS",
    "ramp,linear,deel,vercel,anthropic",
)

# ─── Storage settings ─────────────────────────────────────────────────────────
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./output")
SQLITE_DB_PATH = os.path.join(OUTPUT_DIR, "jobs.db")
JSON_OUTPUT_PATH = os.path.join(OUTPUT_DIR, "jobs.json")
CSV_OUTPUT_PATH = os.path.join(OUTPUT_DIR, "jobs.csv")

# ─── Proxy settings (optional) ────────────────────────────────────────────────
USE_PROXIES = os.getenv("USE_PROXIES", "false").lower() == "true"
PROXY_LIST_PATH = os.getenv("PROXY_LIST_PATH", "./proxies.txt")

# ─── Logging ──────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.path.join(OUTPUT_DIR, "scraper.log")
