"""Pydantic models for API request/response."""

from typing import Optional
from pydantic import BaseModel, Field


class ScrapeRequest(BaseModel):
    skills: str = Field(..., description='Space-separated skills, e.g. "Python Django"')
    location: str = "Remote"
    remote_only: bool = False
    job_type: str = "full-time"
    experience_level: str = ""
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    portals: Optional[list[str]] = None
    max_results: int = 50
    output_formats: list[str] = Field(default=["excel", "json", "csv"])


class PortalSummary(BaseModel):
    portal: str
    success: bool
    total_found: int
    duration_seconds: float
    error: Optional[str] = None


class ScrapeResponse(BaseModel):
    task_id: str
    status: str
    message: str


class ScrapeStatusResponse(BaseModel):
    task_id: str
    status: str  # pending | running | completed | failed
    progress: Optional[str] = None
    job_count: int = 0
    elapsed_seconds: float = 0
    saved_files: list[str] = []
    portal_summary: list[PortalSummary] = []
    jobs: list[dict] = []
    error: Optional[str] = None


class ScheduleRequest(BaseModel):
    name: str = "Daily scrape"
    skills: str
    location: str = "Remote"
    remote_only: bool = False
    job_type: str = "full-time"
    experience_level: str = ""
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    portals: Optional[list[str]] = None
    max_results: int = 50
    run_time: str = Field(..., description='Time to run daily, e.g. "09:00" or "14:30"')
    enabled: bool = True


class ScheduleItem(BaseModel):
    id: str
    name: str
    skills: str
    location: str
    run_time: str
    enabled: bool
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    last_job_count: Optional[int] = None
    last_file: Optional[str] = None


class FileInfo(BaseModel):
    filename: str
    path: str
    format: str
    size_bytes: int
    created_at: str
