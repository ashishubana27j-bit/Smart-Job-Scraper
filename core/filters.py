"""
core/filters.py — Filter and rank jobs by relevance to the search query.
"""

import re
import logging
from models import Job, SearchQuery

logger = logging.getLogger(__name__)


def filter_and_rank(jobs: list[Job], query: SearchQuery) -> list[Job]:
    """
    Apply all filters and sort by skill_match_score descending.
    Steps:
      1. Filter out zero-match jobs (unless no skills given)
      2. Apply remote filter
      3. Apply salary filter (if set)
      4. Apply experience level filter
      5. Sort by skill_match_score descending
    """
    filtered = jobs

    # 1. Require at least one skill match
    if query.skills:
        before = len(filtered)
        filtered = [j for j in filtered if j.skill_match_score > 0]
        logger.info(f"Skill filter: {before} → {len(filtered)} jobs")

    # 2. Remote only
    if query.remote_only:
        before = len(filtered)
        filtered = [j for j in filtered if j.remote]
        logger.info(f"Remote filter: {before} → {len(filtered)} jobs")

    # 3. Salary filter
    if query.min_salary or query.max_salary:
        before = len(filtered)
        filtered = [j for j in filtered if _salary_matches(j.salary, query)]
        logger.info(f"Salary filter: {before} → {len(filtered)} jobs")

    # 4. Experience level
    if query.experience_level:
        before = len(filtered)
        filtered = [j for j in filtered if _experience_matches(j, query.experience_level)]
        logger.info(f"Experience filter: {before} → {len(filtered)} jobs")

    # 5. Sort: by skill_match_score desc, then by most-recently-posted
    filtered.sort(key=lambda j: j.skill_match_score, reverse=True)

    return filtered


def _salary_matches(salary_str: str, query: SearchQuery) -> bool:
    """Parse salary string and check against min/max."""
    if not salary_str:
        return True  # Keep jobs with unknown salary unless strict filtering is needed

    # Extract numbers from salary string
    numbers = re.findall(r"[\d,]+", salary_str.replace(",", ""))
    if not numbers:
        return True

    try:
        amounts = [int(n) for n in numbers if len(n) >= 4]  # At least 4 digits = salary
        # Normalize: if values look like thousands (e.g. "80K"), multiply
        if "k" in salary_str.lower():
            amounts = [a * 1000 if a < 1000 else a for a in amounts]

        if not amounts:
            return True

        job_salary = sum(amounts) / len(amounts)  # Use midpoint if range

        if query.min_salary and job_salary < query.min_salary:
            return False
        if query.max_salary and job_salary > query.max_salary:
            return False

    except (ValueError, OverflowError):
        return True

    return True


def _experience_matches(job: Job, level: str) -> bool:
    """Check if job description matches experience level."""
    level = level.lower()
    text = f"{job.title} {job.description}".lower()

    level_keywords = {
        "junior": ["junior", "entry level", "entry-level", "0-2 years", "0-1 year", "graduate", "trainee"],
        "mid": ["mid-level", "mid level", "3-5 years", "2-4 years", "intermediate"],
        "senior": ["senior", "sr.", "lead", "5+ years", "7+ years", "principal", "staff"],
        "manager": ["manager", "head of", "director", "vp of", "team lead"],
    }

    keywords = level_keywords.get(level, [])
    if not keywords:
        return True  # Unknown level — don't filter

    return any(kw in text for kw in keywords)
