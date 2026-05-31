from __future__ import annotations

import os
import time

import requests

from .models import Paper, ResearchProfile, Window
from .source_utils import build_profile_queries, paper_within_window, year_range

FIELDS = (
    "paperId,title,abstract,authors,year,publicationDate,citationCount,"
    "influentialCitationCount,isOpenAccess,openAccessPdf,externalIds,url,fieldsOfStudy"
)
SEARCH_API = "https://api.semanticscholar.org/graph/v1/paper/search"
PAPER_API = "https://api.semanticscholar.org/graph/v1/paper"
# Semantic Scholar product page: introductory API-key rate limit is 1 RPS.
# Unauthenticated traffic is documented as a shared public pool and can be
# throttled during heavy use, so the cron job keeps the same conservative pace.
SEMANTIC_SCHOLAR_REQUEST_INTERVAL_SECONDS = 1.0


def semantic_scholar_headers() -> dict[str, str]:
    headers = {"User-Agent": "paper-report/0.1"}
    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY") or os.getenv("S2_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key
    return headers


def _authors(raw: list[dict] | None) -> list[str]:
    return [item.get("name", "") for item in raw or [] if item.get("name")]


def _external_ids(data: dict) -> dict:
    external = data.get("externalIds") or {}
    return external if isinstance(external, dict) else {}


def _pdf_url(data: dict) -> str:
    pdf = data.get("openAccessPdf") or {}
    if isinstance(pdf, dict):
        return pdf.get("url") or ""
    return ""


def parse_semantic_scholar_search(data: dict, window: Window) -> list[Paper]:
    papers: list[Paper] = []
    for item in data.get("data") or []:
        external = _external_ids(item)
        published_date = item.get("publicationDate") or (str(item.get("year")) if item.get("year") else "")
        paper = Paper(
            title=item.get("title") or "",
            abstract=item.get("abstract") or "",
            authors=_authors(item.get("authors")),
            published_date=published_date,
            source="Semantic Scholar",
            doi=external.get("DOI") or external.get("doi") or "",
            arxiv_id=external.get("ArXiv") or external.get("arXiv") or external.get("ARXIV") or "",
            semantic_scholar_id=item.get("paperId") or "",
            url=item.get("url") or "",
            pdf_url=_pdf_url(item),
            open_access=bool(item.get("isOpenAccess") or _pdf_url(item)),
            citation_count=int(item.get("citationCount") or 0),
            influential_citation_count=int(item.get("influentialCitationCount") or 0),
            categories=[str(field) for field in item.get("fieldsOfStudy") or [] if field],
            time_window=window.name,
            extra={"candidate_source": "semantic_scholar"},
        )
        if paper.title and paper_within_window(paper, window):
            papers.append(paper)
    return papers


def fetch_semantic_scholar(
    profile: ResearchProfile,
    window: Window,
    max_results_per_query: int = 20,
    sleep_seconds: float = SEMANTIC_SCHOLAR_REQUEST_INTERVAL_SECONDS,
    session: requests.Session | None = None,
) -> list[Paper]:
    """Search Semantic Scholar for additional candidates in the given date window."""
    http = session or requests.Session()
    all_papers: list[Paper] = []
    for query in build_profile_queries(profile):
        response = http.get(
            SEARCH_API,
            params={
                "query": query,
                "limit": max_results_per_query,
                "fields": FIELDS,
                "year": year_range(window),
            },
            timeout=30,
            headers=semantic_scholar_headers(),
        )
        response.raise_for_status()
        all_papers.extend(parse_semantic_scholar_search(response.json(), window))
        if sleep_seconds:
            time.sleep(sleep_seconds)
    return all_papers


def enrich_with_semantic_scholar(
    papers: list[Paper],
    sleep_seconds: float = SEMANTIC_SCHOLAR_REQUEST_INTERVAL_SECONDS,
    session: requests.Session | None = None,
) -> list[Paper]:
    """用 Semantic Scholar 補引用數、OA PDF、DOI 等 metadata；失敗時保留原資料。"""
    http = session or requests.Session()
    enriched: list[Paper] = []
    for paper in papers:
        identifier = paper.arxiv_id and f"arXiv:{paper.arxiv_id.split('v')[0]}"
        if not identifier and paper.doi:
            identifier = f"DOI:{paper.doi}"
        if not identifier:
            enriched.append(paper)
            continue
        url = f"{PAPER_API}/{identifier}"
        try:
            response = http.get(url, params={"fields": FIELDS}, timeout=30, headers=semantic_scholar_headers())
            if response.status_code == 404:
                enriched.append(paper)
                continue
            response.raise_for_status()
            data = response.json()
            paper.semantic_scholar_id = data.get("paperId") or paper.semantic_scholar_id
            paper.citation_count = int(data.get("citationCount") or paper.citation_count or 0)
            paper.influential_citation_count = int(data.get("influentialCitationCount") or paper.influential_citation_count or 0)
            paper.open_access = bool(data.get("isOpenAccess") or paper.open_access)
            pdf_url = _pdf_url(data)
            if pdf_url and not paper.pdf_url:
                paper.pdf_url = pdf_url
            external = _external_ids(data)
            if external.get("DOI") and not paper.doi:
                paper.doi = external["DOI"]
            if data.get("url") and not paper.url:
                paper.url = data["url"]
        except requests.RequestException as exc:
            paper.extra.setdefault("semantic_scholar_error", str(exc))
        enriched.append(paper)
        if sleep_seconds:
            time.sleep(sleep_seconds)
    return enriched
