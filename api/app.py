"""
api/app.py — FastAPI REST API for Job Scraper.
Run with: python run_api.py
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.schemas import (
    ScrapeRequest, ScrapeResponse, ScrapeStatusResponse,
    ScheduleRequest, ScheduleItem, FileInfo, PortalSummary,
)
from api.scrape_service import (
    build_query_from_params, create_task, get_task, run_scrape_task,
)
from api import schedule_service
from scrapers import SCRAPER_REGISTRY, PORTAL_GROUPS
from config import OUTPUT_DIR
from utils.logger import setup_logger

setup_logger()

app = FastAPI(
    title="Job Scraper API",
    description="Scrape jobs, export to Excel, and schedule automatic runs",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.on_event("startup")
def on_startup():
    schedule_service.start_scheduler()


@app.on_event("shutdown")
async def on_shutdown():
    schedule_service.stop_scheduler()
    try:
        from utils.playwright_fetch import close_browser
        await close_browser()
    except Exception:
        pass


@app.get("/api/health")
def health():
    return {"status": "ok", "time": datetime.now().isoformat()}


@app.get("/api/portals")
def list_portals():
    return {
        "portals": list(SCRAPER_REGISTRY.keys()),
        "groups": PORTAL_GROUPS,
        "total": len(SCRAPER_REGISTRY),
    }


@app.post("/api/scrape", response_model=ScrapeResponse)
async def start_scrape(req: ScrapeRequest, background_tasks: BackgroundTasks):
    query = build_query_from_params(
        skills=req.skills,
        location=req.location,
        remote_only=req.remote_only,
        job_type=req.job_type,
        experience_level=req.experience_level,
        min_salary=req.min_salary,
        max_salary=req.max_salary,
        portals=req.portals,
        max_results=req.max_results,
    )
    task_id = create_task()
    background_tasks.add_task(run_scrape_task, task_id, query, req.output_formats)
    return ScrapeResponse(
        task_id=task_id,
        status="pending",
        message="Scrape started. Poll /api/scrape/status/{task_id} for progress.",
    )


@app.get("/api/scrape/status/{task_id}", response_model=ScrapeStatusResponse)
def scrape_status(task_id: str):
    task = get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return ScrapeStatusResponse(
        task_id=task_id,
        status=task["status"],
        progress=task.get("progress"),
        job_count=task.get("job_count", 0),
        elapsed_seconds=task.get("elapsed_seconds", 0),
        saved_files=task.get("saved_files", []),
        portal_summary=[PortalSummary(**p) for p in task.get("portal_summary", [])],
        jobs=task.get("jobs", []),
        error=task.get("error"),
    )


@app.get("/api/files", response_model=list[FileInfo])
def list_files():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    files = []
    for name in sorted(os.listdir(OUTPUT_DIR), reverse=True):
        if not name.endswith((".xlsx", ".csv", ".json")):
            continue
        path = os.path.join(OUTPUT_DIR, name)
        ext = name.rsplit(".", 1)[-1]
        mtime = os.path.getmtime(path)
        files.append(FileInfo(
            filename=name,
            path=path,
            format=ext,
            size_bytes=os.path.getsize(path),
            created_at=datetime.fromtimestamp(mtime).isoformat(),
        ))
    return files


@app.get("/api/files/download/{filename}")
def download_file(filename: str):
    safe_name = os.path.basename(filename)
    path = os.path.join(OUTPUT_DIR, safe_name)
    if not os.path.isfile(path):
        raise HTTPException(404, "File not found")

    media = {
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "csv": "text/csv",
        "json": "application/json",
    }
    ext = safe_name.rsplit(".", 1)[-1]
    return FileResponse(path, filename=safe_name, media_type=media.get(ext, "application/octet-stream"))


@app.get("/api/schedule", response_model=list[ScheduleItem])
def get_schedules():
    return [ScheduleItem(**s) for s in schedule_service.list_schedules()]


@app.post("/api/schedule", response_model=ScheduleItem)
def add_schedule(req: ScheduleRequest):
    try:
        result = schedule_service.create_schedule(req.model_dump())
        return ScheduleItem(**result)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/schedule/{schedule_id}")
def remove_schedule(schedule_id: str):
    if not schedule_service.delete_schedule(schedule_id):
        raise HTTPException(404, "Schedule not found")
    return {"ok": True}


@app.patch("/api/schedule/{schedule_id}/toggle")
def toggle_schedule(schedule_id: str, enabled: bool = True):
    result = schedule_service.toggle_schedule(schedule_id, enabled)
    if not result:
        raise HTTPException(404, "Schedule not found")
    return ScheduleItem(**result)


@app.get("/")
def serve_frontend():
    index = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.isfile(index):
        return FileResponse(index)
    return {"message": "Job Scraper API is running. Open /static/index.html or use /docs."}
