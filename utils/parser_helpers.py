"""
utils/parser_helpers.py — Common HTML parsing helpers used by all scrapers.
"""

import re
from bs4 import BeautifulSoup, Tag
from typing import Optional


def make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def safe_text(element: Optional[Tag], default: str = "") -> str:
    """Extract clean text from a BeautifulSoup tag."""
    if element is None:
        return default
    return element.get_text(separator=" ", strip=True)


def safe_attr(element: Optional[Tag], attr: str, default: str = "") -> str:
    """Get an attribute from a tag safely."""
    if element is None:
        return default
    return element.get(attr, default) or default


def clean_text(text: str) -> str:
    """Strip extra whitespace and newlines."""
    return re.sub(r"\s+", " ", text).strip()


def extract_salary(text: str) -> str:
    """
    Try to extract a salary string from job description or title.
    Examples: "$80,000 - $120,000", "€60K", "£50k/year"
    """
    pattern = r'[\$£€][\d,]+[Kk]?\s*(?:[-–]\s*[\$£€]?[\d,]+[Kk]?)?\s*(?:\/?\s*(?:year|yr|month|mo|hour|hr|annum|pa))?'
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(0).strip() if match else ""


def extract_skills_from_text(text: str, known_skills: list[str]) -> list[str]:
    """
    Check which known skills appear in a job description.
    Case-insensitive, whole-word matching.
    """
    found = []
    text_lower = text.lower()
    for skill in known_skills:
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, text_lower):
            found.append(skill)
    return found


def normalize_location(location: str) -> str:
    """Clean up location strings."""
    location = clean_text(location)
    # Common patterns to normalize
    location = re.sub(r"\bUS\b", "United States", location)
    location = re.sub(r"\bUK\b", "United Kingdom", location)
    location = re.sub(r"\bRemote\b", "Remote", location, flags=re.IGNORECASE)
    return location


def is_remote_job(title: str, description: str, location: str) -> bool:
    """Guess if a job is remote from its text."""
    text = f"{title} {description} {location}".lower()
    remote_keywords = ["remote", "work from home", "wfh", "distributed", "fully remote", "anywhere"]
    return any(kw in text for kw in remote_keywords)


def absolute_url(base: str, href: str) -> str:
    """Turn relative paths into absolute URLs."""
    if not href:
        return ""
    if href.startswith("http"):
        return href
    from urllib.parse import urljoin
    return urljoin(base, href)
