from __future__ import annotations

import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import date
from typing import Iterable

import requests

from .models import Paper, ResearchProfile, Window
from .paper_type import normalize_requested_paper_type

ARXIV_API = "https://export.arxiv.org/api/query"
# arXiv Terms of Use: legacy arXiv API clients should make no more than one
# request every three seconds and use a single connection at a time.
ARXIV_REQUEST_INTERVAL_SECONDS = 3.0
ATOM_NS = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def _text(entry: ET.Element, path: str) -> str:
    node = entry.find(path, ATOM_NS)
    return " ".join((node.text or "").split()) if node is not None else ""


def parse_arxiv_atom(xml_text: str) -> list[Paper]:
    root = ET.fromstring(xml_text)
    papers: list[Paper] = []
    for entry in root.findall("a:entry", ATOM_NS):
        raw_id = _text(entry, "a:id")
        arxiv_id = raw_id.split("/abs/")[-1] if raw_id else ""
        title = _text(entry, "a:title")
        abstract = _text(entry, "a:summary")
        published = _text(entry, "a:published")[:10]
        authors = [_text(author, "a:name") for author in entry.findall("a:author", ATOM_NS)]
        categories = [cat.get("term", "") for cat in entry.findall("a:category", ATOM_NS) if cat.get("term")]
        pdf_url = ""
        url = raw_id.replace("http://", "https://") if raw_id else ""
        for link in entry.findall("a:link", ATOM_NS):
            if link.get("title") == "pdf" or link.get("type") == "application/pdf":
                pdf_url = link.get("href", "")
            if link.get("rel") == "alternate" and link.get("href"):
                url = link.get("href", "")
        papers.append(
            Paper(
                title=title,
                abstract=abstract,
                authors=[a for a in authors if a],
                published_date=published,
                source="arXiv",
                arxiv_id=arxiv_id,
                url=url,
                pdf_url=pdf_url,
                open_access=bool(pdf_url),
                categories=categories,
            )
        )
    return papers


def _date_filter(window: Window) -> str:
    return f"submittedDate:[{window.start:%Y%m%d}0000+TO+{window.end:%Y%m%d}2359]"


def build_arxiv_queries(profile: ResearchProfile, window: Window) -> list[str]:
    category_query = " OR ".join(f"cat:{cat}" for cat in profile.arxiv_categories) if profile.arxiv_categories else "cat:cs.AI"
    date_query = _date_filter(window)
    keywords = profile.positive_keywords or [profile.topic_name]
    paper_type = normalize_requested_paper_type(getattr(profile, "paper_type", "review"))
    if paper_type == "review":
        type_query = '(all:"review" OR all:"survey" OR all:"systematic literature review")'
    elif paper_type == "general":
        type_query = '(all:"method" OR all:"experiment" OR all:"empirical" OR all:"architecture")'
    else:
        type_query = ""
    queries: list[str] = []
    for keyword in keywords:
        keyword_query = f'all:"{keyword}"'
        parts = [f"({keyword_query})", f"({category_query})", date_query]
        if type_query:
            parts.insert(1, type_query)
        queries.append(" AND ".join(parts))
    # Add one broad category query so new papers without exact positive keywords can still enter candidate pool.
    queries.append(f"({category_query}) AND {type_query} AND {date_query}" if type_query else f"({category_query}) AND {date_query}")
    return list(dict.fromkeys(queries))


def fetch_arxiv(
    profile: ResearchProfile,
    window: Window,
    max_results_per_query: int = 25,
    sleep_seconds: float = ARXIV_REQUEST_INTERVAL_SECONDS,
    session: requests.Session | None = None,
) -> list[Paper]:
    http = session or requests.Session()
    all_papers: list[Paper] = []
    for query in build_arxiv_queries(profile, window):
        params = {
            "search_query": query,
            "start": 0,
            "max_results": max_results_per_query,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        url = f"{ARXIV_API}?{urllib.parse.urlencode(params)}"
        response = http.get(url, timeout=30, headers={"User-Agent": "paper-report/0.1"})
        response.raise_for_status()
        papers = parse_arxiv_atom(response.text)
        for paper in papers:
            parsed = paper.parsed_date()
            if parsed is None or window.start <= parsed <= window.end:
                paper.time_window = window.name
                all_papers.append(paper)
        if sleep_seconds:
            time.sleep(sleep_seconds)
    return all_papers
