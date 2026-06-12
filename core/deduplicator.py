"""
core/deduplicator.py — Remove duplicate jobs across portals.
Uses title+company fingerprint (MD5 hash) to detect dupes.
"""

import logging
from models import Job

logger = logging.getLogger(__name__)


def deduplicate(jobs: list[Job]) -> list[Job]:
    """
    Remove duplicate jobs based on their unique_id (title+company hash).
    When duplicates exist, prefer the one with a richer description.
    """
    seen: dict[str, Job] = {}

    for job in jobs:
        uid = job.unique_id
        if uid not in seen:
            seen[uid] = job
        else:
            # Keep the version with the longer description
            existing = seen[uid]
            if len(job.description) > len(existing.description):
                seen[uid] = job

    deduped = list(seen.values())
    removed = len(jobs) - len(deduped)
    if removed:
        logger.info(f"Deduplication removed {removed} duplicate jobs")

    return deduped
