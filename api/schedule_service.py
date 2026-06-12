"""Scheduled scraping using APScheduler."""

import json
import os
import uuid
import logging
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from api.scrape_service import build_query_from_params, run_scrape_sync
from config import OUTPUT_DIR

logger = logging.getLogger(__name__)

SCHEDULES_FILE = os.path.join(OUTPUT_DIR, "schedules.json")
_scheduler: Optional[BackgroundScheduler] = None
_schedules: dict[str, dict] = {}


def _load_schedules():
    global _schedules
    if os.path.exists(SCHEDULES_FILE):
        with open(SCHEDULES_FILE, "r", encoding="utf-8") as f:
            _schedules = json.load(f)
    else:
        _schedules = {}


def _save_schedules():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(SCHEDULES_FILE, "w", encoding="utf-8") as f:
        json.dump(_schedules, f, indent=2)


def _parse_time(run_time: str) -> tuple[int, int]:
    """Parse HH:MM into hour and minute."""
    parts = run_time.strip().split(":")
    if len(parts) != 2:
        raise ValueError('Time must be in HH:MM format, e.g. "09:00"')
    hour, minute = int(parts[0]), int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError("Invalid hour or minute")
    return hour, minute


def _run_scheduled_job(schedule_id: str):
    schedule = _schedules.get(schedule_id)
    if not schedule or not schedule.get("enabled"):
        return

    logger.info(f"Running scheduled scrape: {schedule['name']} ({schedule_id})")
    try:
        query = build_query_from_params(
            skills=schedule["skills"],
            location=schedule.get("location", "Remote"),
            remote_only=schedule.get("remote_only", False),
            job_type=schedule.get("job_type", "full-time"),
            experience_level=schedule.get("experience_level", ""),
            min_salary=schedule.get("min_salary"),
            max_salary=schedule.get("max_salary"),
            portals=schedule.get("portals"),
            max_results=schedule.get("max_results", 50),
        )
        result = run_scrape_sync(query, ["excel", "json", "csv"])
        schedule["last_run"] = result["timestamp"]
        schedule["last_job_count"] = result["job_count"]
        if result.get("excel_file"):
            schedule["last_file"] = os.path.basename(result["excel_file"])
        _save_schedules()
        logger.info(f"Schedule {schedule_id} finished: {result['job_count']} jobs")
    except Exception:
        logger.exception(f"Scheduled job {schedule_id} failed")


def _add_job_to_scheduler(schedule_id: str, schedule: dict):
    if not _scheduler:
        return
    hour, minute = _parse_time(schedule["run_time"])
    _scheduler.add_job(
        _run_scheduled_job,
        CronTrigger(hour=hour, minute=minute),
        id=schedule_id,
        args=[schedule_id],
        replace_existing=True,
    )
    job = _scheduler.get_job(schedule_id)
    if job and job.next_run_time:
        schedule["next_run"] = job.next_run_time.isoformat()


def start_scheduler():
    global _scheduler
    _load_schedules()
    _scheduler = BackgroundScheduler()
    for sid, schedule in _schedules.items():
        if schedule.get("enabled"):
            try:
                _add_job_to_scheduler(sid, schedule)
            except Exception as e:
                logger.warning(f"Could not load schedule {sid}: {e}")
    _scheduler.start()
    logger.info("Scheduler started")


def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def list_schedules() -> list[dict]:
    items = []
    for sid, s in _schedules.items():
        item = {**s, "id": sid}
        if _scheduler:
            job = _scheduler.get_job(sid)
            if job and job.next_run_time:
                item["next_run"] = job.next_run_time.isoformat()
        items.append(item)
    return items


def create_schedule(data: dict) -> dict:
    _parse_time(data["run_time"])
    schedule_id = str(uuid.uuid4())[:8]
    schedule = {
        "name": data.get("name", "Daily scrape"),
        "skills": data["skills"],
        "location": data.get("location", "Remote"),
        "remote_only": data.get("remote_only", False),
        "job_type": data.get("job_type", "full-time"),
        "experience_level": data.get("experience_level", ""),
        "min_salary": data.get("min_salary"),
        "max_salary": data.get("max_salary"),
        "portals": data.get("portals"),
        "max_results": data.get("max_results", 50),
        "run_time": data["run_time"],
        "enabled": data.get("enabled", True),
        "last_run": None,
        "next_run": None,
        "last_job_count": None,
        "last_file": None,
    }
    _schedules[schedule_id] = schedule
    if schedule["enabled"]:
        _add_job_to_scheduler(schedule_id, schedule)
    _save_schedules()
    return {**schedule, "id": schedule_id}


def delete_schedule(schedule_id: str) -> bool:
    if schedule_id not in _schedules:
        return False
    if _scheduler:
        try:
            _scheduler.remove_job(schedule_id)
        except Exception:
            pass
    del _schedules[schedule_id]
    _save_schedules()
    return True


def toggle_schedule(schedule_id: str, enabled: bool) -> Optional[dict]:
    if schedule_id not in _schedules:
        return None
    schedule = _schedules[schedule_id]
    schedule["enabled"] = enabled
    if _scheduler:
        if enabled:
            _add_job_to_scheduler(schedule_id, schedule)
        else:
            try:
                _scheduler.remove_job(schedule_id)
            except Exception:
                pass
            schedule["next_run"] = None
    _save_schedules()
    return {**schedule, "id": schedule_id}
