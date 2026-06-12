"""
run_api.py — Start the Job Scraper web API + frontend.

Usage:
  python run_api.py
  python run_api.py --port 8080
"""

import argparse
import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Job Scraper API server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    print(f"\n  Job Scraper API: http://{args.host}:{args.port}")
    print(f"  API docs:        http://{args.host}:{args.port}/docs\n")

    uvicorn.run("api.app:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
