"""
models.py — Core data models for the Job Scraper system.
All dataclasses used across scrapers, storage, and filters.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import hashlib


@dataclass
class SearchQuery:
    """What the user wants to search for."""
    skills: list[str]           # e.g. ["Python", "Django", "AWS"]
    location: str = "Remote"    # e.g. "Dubai", "Remote", "New York"
    remote_only: bool = False
    min_salary: Optional[int] = None   # Annual USD
    max_salary: Optional[int] = None
    job_type: str = "full-time"        # full-time | part-time | contract | internship
    experience_level: str = ""         # junior | mid | senior | ""
    portals: list[str] = field(default_factory=lambda: [
        "remotive", "remoteok", "arbeitnow", "workingnomads", "weworkremotely",
        "jobspresso", "jooble", "talent", "greenhouse", "lever",
    ])
    max_results_per_portal: int = 50

    @property
    def query_string(self) -> str:
        """Build a search string from skills."""
        return " ".join(self.skills)


@dataclass
class Job:
    """A single job listing."""
    title: str
    company: str
    location: str
    url: str
    source_portal: str
    description: str = ""
    salary: str = ""
    job_type: str = ""
    experience_level: str = ""
    skills_required: list[str] = field(default_factory=list)
    posted_date: Optional[str] = None
    apply_url: str = ""
    remote: bool = False
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Computed after scraping
    skill_match_score: float = 0.0      # 0.0 to 1.0 — how well job matches query skills
    matched_skills: list[str] = field(default_factory=list)

    @property
    def unique_id(self) -> str:
        """Fingerprint a job to detect duplicates across portals."""
        raw = f"{self.title.lower().strip()}{self.company.lower().strip()}"
        return hashlib.md5(raw.encode()).hexdigest()

    def to_dict(self) -> dict:
        return {
            "id": self.unique_id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "url": self.url,
            "source_portal": self.source_portal,
            "description": self.description[:500] + "..." if len(self.description) > 500 else self.description,
            "salary": self.salary,
            "job_type": self.job_type,
            "experience_level": self.experience_level,
            "skills_required": self.skills_required,
            "posted_date": self.posted_date,
            "apply_url": self.apply_url or self.url,
            "remote": self.remote,
            "skill_match_score": round(self.skill_match_score, 3),
            "matched_skills": self.matched_skills,
            "scraped_at": self.scraped_at,
        }


@dataclass
class ScraperResult:
    """Result returned by each scraper."""
    portal: str
    jobs: list[Job] = field(default_factory=list)
    success: bool = True
    error: Optional[str] = None
    total_found: int = 0
    duration_seconds: float = 0.0

    def __repr__(self):
        status = "✅" if self.success else "❌"
        return f"{status} [{self.portal}] {len(self.jobs)} jobs in {self.duration_seconds:.1f}s"
