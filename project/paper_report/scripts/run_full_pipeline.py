#!/usr/bin/env python3
"""Run the full Paper Report workflow for Hermes cron.

This wrapper intentionally delegates to the package CLI so the cron command is
self-contained and easy to update.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_DIR)
os.environ["PYTHONPATH"] = f"src{os.pathsep}{os.environ.get('PYTHONPATH', '')}" if os.environ.get("PYTHONPATH") else "src"

from paper_report.cli import main  # noqa: E402

args = [
    "run-full-pipeline",
    "--project-dir",
    str(PROJECT_DIR),
    "--profile",
    "configs/research_profile.yaml",
    "--repo-url",
    "https://github.com/openclaw572/edge-ai-papers.git",
    "--checkout-dir",
    "tmp/edge-ai-papers-publish",
    "--push-github",
    "--enable-tts",
]

# Optional runtime overrides for cron/profile experiments.
if os.getenv("PAPER_REPORT_RUN_DATE"):
    args.extend(["--run-date", os.environ["PAPER_REPORT_RUN_DATE"]])
if os.getenv("PAPER_REPORT_PROFILE_ID"):
    args.extend(["--profile-id", os.environ["PAPER_REPORT_PROFILE_ID"]])
if os.getenv("PAPER_REPORT_NO_CLEANUP") == "1":
    args.append("--no-cleanup")
if os.getenv("PAPER_REPORT_EMAIL_RECIPIENT"):
    args.extend(["--email-recipient", os.environ["PAPER_REPORT_EMAIL_RECIPIENT"]])
if os.getenv("PAPER_REPORT_SKIP_EMAIL") == "1":
    args.append("--skip-email")

raise SystemExit(main(args + sys.argv[1:]))
