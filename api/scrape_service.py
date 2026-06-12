"""Shared scraping logic for API and scheduled jobs."""

import asyncio
import os
import sys
import time
import uuid
import logging
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models import SearchQuery
from core.scheduler import Scheduler
from core.deduplicator import deduplicate
from core.filters import filter_and_rank
from storage.storage import save_json, save_csv, save_sqlite, save_excel
from scrapers import SCRAPER_REGISTRY
from config import OUTPUT_DIR
from utils.logger import setup_logger

logger = logging.getLogger(__name__)

# In-memory task status store
_tasks: dict[str, dict] = {}


def build_query_from_params(
    skills: str,
    location: str = "Remote",
    remote_only: bool = False,
    job_type: str = "full-time",
    experience_level: str = "",
    min_salary: Optional[int] = None,
    max_salary: Optional[int] = None,
    portals: Optional[list[str]] = None,
    max_results: int = 50,
) -> SearchQuery:
    skill_list = [s.strip() for s in skills.split() if s.strip()]
    return SearchQuery(
        skills=skill_list,
        location=location,
        remote_only=remote_only,
        min_salary=min_salary,
        max_salary=max_salary,
        job_type=job_type,
        experience_level=experience_level,
        portals=portals or list(SCRAPER_REGISTRY.keys()),
        max_results_per_portal=max_results,
    )


async def run_scrape_pipeline(
    query: SearchQuery,
    output_formats: Optional[list[str]] = None,
) -> tuple[list, list, float, list[str]]:
    """Run scrape pipeline and save outputs. Returns (results, jobs, elapsed, saved_files)."""
    formats = output_formats or ["excel", "json", "csv"]
    scheduler = Scheduler(query)
    start = time.monotonic()
    results = await scheduler.run_all()
    elapsed = time.monotonic() - start

    all_jobs = scheduler.collect_jobs(results)
    jobs = deduplicate(all_jobs)
    jobs = filter_and_rank(jobs, query)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved_files = []

    if "json" in formats:
        saved_files.append(save_json(jobs, f"{OUTPUT_DIR}/jobs_{timestamp}.json"))
    if "csv" in formats:
        saved_files.append(save_csv(jobs, f"{OUTPUT_DIR}/jobs_{timestamp}.csv"))
    if "excel" in formats:
        saved_files.append(save_excel(jobs, f"{OUTPUT_DIR}/jobs_{timestamp}.xlsx"))
    if "sqlite" in formats:
        saved_files.append(save_sqlite(jobs))

    return results, jobs, elapsed, saved_files


def create_task() -> str:
    task_id = str(uuid.uuid4())[:8]
    _tasks[task_id] = {
        "status": "pending",
        "progress": "Queued",
        "job_count": 0,
        "elapsed_seconds": 0,
        "saved_files": [],
        "portal_summary": [],
        "jobs": [],
        "error": None,
    }
    return task_id


def get_task(task_id: str) -> Optional[dict]:
    return _tasks.get(task_id)


async def run_scrape_task(task_id: str, query: SearchQuery, output_formats: list[str]):
    """Background scrape with status updates."""
    task = _tasks.get(task_id)
    if not task:
        return

    task["status"] = "running"
    task["progress"] = "Scraping portals..."

    try:
        results, jobs, elapsed, saved_files = await run_scrape_pipeline(query, output_formats)

        task["status"] = "completed"
        task["progress"] = "Done"
        task["job_count"] = len(jobs)
        task["elapsed_seconds"] = round(elapsed, 1)
        task["saved_files"] = [os.path.basename(f) for f in saved_files]
        task["portal_summary"] = [
            {
                "portal": r.portal,
                "success": r.success,
                "total_found": r.total_found,
                "duration_seconds": round(r.duration_seconds, 1),
                "error": r.error,
            }
            for r in results
        ]
        task["jobs"] = [j.to_dict() for j in jobs[:100]]
        logger.info(f"Task {task_id} completed: {len(jobs)} jobs")
    except Exception as e:
        logger.exception(f"Task {task_id} failed")
        task["status"] = "failed"
        task["error"] = str(e)
        task["progress"] = "Failed"


def run_scrape_sync(query: SearchQuery, output_formats: list[str]) -> dict:
    """Synchronous wrapper for scheduled jobs."""
    setup_logger()
    results, jobs, elapsed, saved_files = asyncio.run(
        run_scrape_pipeline(query, output_formats)
    )
    excel_file = next((f for f in saved_files if f.endswith(".xlsx")), None)
    return {
        "job_count": len(jobs),
        "elapsed_seconds": elapsed,
        "saved_files": saved_files,
        "excel_file": excel_file,
        "timestamp": datetime.now().isoformat(),
    }
