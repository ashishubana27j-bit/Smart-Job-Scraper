"""
main.py — Job Scraper entry point.
Supports both CLI usage and programmatic import.

Usage:
  python main.py --skills "Python Django REST API" --location "Remote" --portals remotive weworkremotely linkedin
  python main.py --skills "React TypeScript" --remote --min-salary 80000
  python main.py --skills "Data Science Machine Learning" --output json csv sqlite
"""

import asyncio
import argparse
import sys
import os
import time
import logging
from datetime import datetime

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(__file__))

from models import SearchQuery
from core.scheduler import Scheduler
from core.deduplicator import deduplicate
from core.filters import filter_and_rank
from storage.storage import save_json, save_csv, save_sqlite, save_excel
from utils.logger import setup_logger
from scrapers import SCRAPER_REGISTRY


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="🔍 Job Scraper — Find jobs by skill across multiple portals",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --skills "Python Django" --location "Remote"
  python main.py --skills "React TypeScript Node" --remote --output json csv
  python main.py --skills "Machine Learning PyTorch" --location "Dubai" --min-salary 100000
  python main.py --skills "Java Spring Boot" --portals linkedin indeed --max-results 30
        """
    )

    parser.add_argument(
        "--skills", required=True,
        help='Space-separated skills to search for. E.g. "Python Django REST API"'
    )
    parser.add_argument(
        "--location", default="Remote",
        help="Location to search in (default: Remote)"
    )
    parser.add_argument(
        "--remote", action="store_true",
        help="Filter to remote jobs only"
    )
    parser.add_argument(
        "--job-type", default="full-time",
        choices=["full-time", "part-time", "contract", "internship", "any"],
        help="Job type filter (default: full-time)"
    )
    parser.add_argument(
        "--experience", default="",
        choices=["junior", "mid", "senior", "manager", ""],
        help="Experience level filter"
    )
    parser.add_argument(
        "--min-salary", type=int, default=None,
        help="Minimum annual salary in USD"
    )
    parser.add_argument(
        "--max-salary", type=int, default=None,
        help="Maximum annual salary in USD"
    )
    parser.add_argument(
        "--portals", nargs="+",
        default=list(SCRAPER_REGISTRY.keys()),
        choices=list(SCRAPER_REGISTRY.keys()),
        help="Which portals to scrape (default: all)"
    )
    parser.add_argument(
        "--max-results", type=int, default=50,
        help="Max results per portal (default: 50)"
    )
    parser.add_argument(
        "--output", nargs="+", default=["json", "csv", "excel", "sqlite"],
        choices=["json", "csv", "excel", "sqlite"],
        help="Output formats (default: json csv excel sqlite)"
    )

    return parser.parse_args()


def print_banner():
    print("\n" + "=" * 60)
    print("  🔍  JOB SCRAPER  —  Multi-Portal Job Finder")
    print("=" * 60)


def print_summary(results, final_jobs, elapsed):
    print("\n" + "─" * 60)
    print("📊 SCRAPE SUMMARY")
    print("─" * 60)

    for r in results:
        status = "✅" if r.success else "❌"
        err = f" ({r.error})" if r.error else ""
        print(f"  {status} {r.portal:<20} {r.total_found:>4} jobs  {r.duration_seconds:.1f}s{err}")

    total_raw = sum(r.total_found for r in results)
    print("─" * 60)
    print(f"  Raw total:      {total_raw}")
    print(f"  After dedupe:   {len(final_jobs)}")
    print(f"  Total time:     {elapsed:.1f}s")
    print()


def print_top_jobs(jobs: list, n: int = 10):
    print(f"🏆 TOP {min(n, len(jobs))} JOBS BY SKILL MATCH")
    print("─" * 60)
    for i, job in enumerate(jobs[:n], 1):
        score = f"{job.skill_match_score * 100:.0f}%"
        remote = "🌐 " if job.remote else "🏢 "
        print(f"\n  {i}. [{score}] {remote}{job.title}")
        print(f"     Company:  {job.company}")
        print(f"     Location: {job.location}")
        print(f"     Matched:  {', '.join(job.matched_skills) or 'none'}")
        if job.salary:
            print(f"     Salary:   {job.salary}")
        print(f"     Source:   {job.source_portal}")
        print(f"     URL:      {job.url[:80]}{'...' if len(job.url) > 80 else ''}")
    print()


async def run(query: SearchQuery, output_formats: list[str]) -> list:
    """Main async scraping pipeline."""
    logger = logging.getLogger("job_scraper.main")

    # Step 1: Scrape all portals concurrently
    scheduler = Scheduler(query)
    start = time.monotonic()
    results = await scheduler.run_all()
    elapsed = time.monotonic() - start

    # Step 2: Collect all jobs
    all_jobs = scheduler.collect_jobs(results)
    logger.info(f"Collected {len(all_jobs)} raw jobs from {len(results)} portals")

    # Step 3: Deduplicate
    jobs = deduplicate(all_jobs)

    # Step 4: Filter + rank
    jobs = filter_and_rank(jobs, query)
    logger.info(f"After filter+rank: {len(jobs)} jobs")

    # Step 5: Save outputs
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    from config import OUTPUT_DIR
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    saved_files = []
    if "json" in output_formats:
        path = save_json(jobs, f"{OUTPUT_DIR}/jobs_{timestamp}.json")
        saved_files.append(path)
    if "csv" in output_formats:
        path = save_csv(jobs, f"{OUTPUT_DIR}/jobs_{timestamp}.csv")
        saved_files.append(path)
    if "excel" in output_formats:
        path = save_excel(jobs, f"{OUTPUT_DIR}/jobs_{timestamp}.xlsx")
        saved_files.append(path)
    if "sqlite" in output_formats:
        path = save_sqlite(jobs)
        saved_files.append(path)

    return results, jobs, elapsed, saved_files


def main():
    args = parse_args()
    setup_logger()
    print_banner()

    # Build query
    skills = [s.strip() for s in args.skills.split() if s.strip()]
    query = SearchQuery(
        skills=skills,
        location=args.location,
        remote_only=args.remote,
        min_salary=args.min_salary,
        max_salary=args.max_salary,
        job_type=args.job_type,
        experience_level=args.experience,
        portals=args.portals,
        max_results_per_portal=args.max_results,
    )

    print(f"\n🎯 Searching for: {', '.join(skills)}")
    print(f"📍 Location:      {query.location}")
    print(f"🌐 Remote only:   {query.remote_only}")
    print(f"🏗  Portals:       {', '.join(query.portals)}")
    print()

    # Run
    results, jobs, elapsed, saved_files = asyncio.run(run(query, args.output))

    # Print results
    print_summary(results, jobs, elapsed)
    print_top_jobs(jobs, n=10)

    print("💾 SAVED FILES")
    print("─" * 60)
    for f in saved_files:
        print(f"  → {f}")
    print()
    print(f"✅ Done! Found {len(jobs)} matching jobs.\n")

    return jobs


if __name__ == "__main__":
    main()
