#!/usr/bin/env python3
"""Convenience wrapper for local runs.

Usage:
  PYTHONPATH=src python scripts/run_paper_hunter.py --sample-candidates fixtures/sample_candidates.yaml --today 2026-05-26
"""
from paper_report.cli import main

raise SystemExit(main(["hunt", *(__import__("sys").argv[1:])]))
