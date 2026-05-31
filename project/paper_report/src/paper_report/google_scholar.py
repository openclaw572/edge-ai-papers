from __future__ import annotations

import os
import re
import time

import requests

from .models import Paper, ResearchProfile, Window
from .source_utils import build_profile_queries, paper_within_window

SERPAPI_URL = "https://serpapi.com/search.json"


def _parse_publication_summary(summary: str) -> tuple[list[str], str]:
    if not summary:
        return [], ""
    year_match = re.search(r"\b(19|20)\d{2}\b", summary)
    year = year_match.group(0) if year_match else ""
    before_year = summary[: year_match.start()] if year_match else summary.split(" - ")[0]
    before_year = before_year.strip(" -")
    # SerpAPI usually formats this as "A Author, B Author - 2026 - venue".
    authors_text = before_year.split(" - ")[0].strip()
    authors = [part.strip() for part in authors_text.split(",") if part.strip()]
    return authors, year


def _authors(publication_info: dict) -> list[str]:
    raw_authors = publication_info.get("authors") or []
    authors = [item.get("name", "") for item in raw_authors if isinstance(item, dict) and item.get("name")]
    if authors:
        return authors
    parsed, _ = _parse_publication_summary(publication_info.get("summary") or "")
    return parsed


def _published_year(publication_info: dict) -> str:
    _, year = _parse_publication_summary(publication_info.get("summary") or "")
    return year


def _pdf_url(result: dict) -> str:
    for resource in result.get("resources") or []:
        title = str(resource.get("title") or "").lower()
        fmt = str(resource.get("file_format") or "").lower()
        if "pdf" in title or fmt == "pdf":
            return resource.get("link") or ""
    return ""


def parse_serpapi_google_scholar(data: dict, window: Window) -> list[Paper]:
    papers: list[Paper] = []
    for result in data.get("organic_results") or []:
        publication_info = result.get("publication_info") or {}
        pdf_url = _pdf_url(result)
        paper = Paper(
            title=result.get("title") or "",
            abstract=result.get("snippet") or "",
            authors=_authors(publication_info),
            published_date=_published_year(publication_info),
            source="Google Scholar",
            url=result.get("link") or "",
            pdf_url=pdf_url,
            open_access=bool(pdf_url),
            citation_count=int(((result.get("inline_links") or {}).get("cited_by") or {}).get("total") or 0),
            time_window=window.name,
            extra={"candidate_source": "google_scholar", "result_id": result.get("result_id") or ""},
        )
        if paper.title and paper_within_window(paper, window):
            papers.append(paper)
    return papers


def fetch_google_scholar(
    profile: ResearchProfile,
    window: Window,
    max_results_per_query: int = 20,
    sleep_seconds: float = 2.0,
    session: requests.Session | None = None,
    api_key: str | None = None,
) -> list[Paper]:
    """Search Google Scholar via SerpAPI.

    Google Scholar has no official free JSON API and direct scraping is fragile / CAPTCHA-prone.
    This fetcher therefore uses SerpAPI when SERPAPI_API_KEY or
    GOOGLE_SCHOLAR_SERPAPI_KEY is configured. Without a key it returns no candidates
    so the rest of the pipeline remains deterministic and non-interactive.
    """
    key = api_key or os.getenv("GOOGLE_SCHOLAR_SERPAPI_KEY") or os.getenv("SERPAPI_API_KEY")
    if not key:
        return []
    http = session or requests.Session()
    all_papers: list[Paper] = []
    for query in build_profile_queries(profile):
        response = http.get(
            SERPAPI_URL,
            params={
                "engine": "google_scholar",
                "q": query,
                "api_key": key,
                "num": min(max_results_per_query, 20),
                "as_ylo": window.start.year,
                "as_yhi": window.end.year,
                "scisbd": 1,  # sort by date when supported by SerpAPI/Google Scholar
            },
            timeout=30,
            headers={"User-Agent": "paper-report/0.1"},
        )
        response.raise_for_status()
        all_papers.extend(parse_serpapi_google_scholar(response.json(), window))
        if sleep_seconds:
            time.sleep(sleep_seconds)
    return all_papers
