from __future__ import annotations

import os
import time

import requests

from .models import Paper, ResearchProfile, Window
from .source_utils import build_profile_queries, paper_within_window

OPENALEX_API = "https://api.openalex.org/works"


def reconstruct_openalex_abstract(inverted_index: dict | None) -> str:
    if not inverted_index:
        return ""
    positions: dict[int, str] = {}
    for word, indexes in inverted_index.items():
        for index in indexes or []:
            positions[int(index)] = str(word)
    return " ".join(positions[index] for index in sorted(positions))


def _doi(raw: str | None) -> str:
    if not raw:
        return ""
    return raw.replace("https://doi.org/", "").replace("http://doi.org/", "")


def _authors(authorships: list[dict] | None) -> list[str]:
    names: list[str] = []
    for item in authorships or []:
        author = item.get("author") or {}
        if author.get("display_name"):
            names.append(author["display_name"])
    return names


def parse_openalex_works(data: dict, window: Window) -> list[Paper]:
    papers: list[Paper] = []
    for item in data.get("results") or []:
        primary_location = item.get("primary_location") or {}
        open_access = item.get("open_access") or {}
        pdf_url = primary_location.get("pdf_url") or open_access.get("oa_url") or ""
        url = primary_location.get("landing_page_url") or item.get("id") or ""
        paper = Paper(
            title=item.get("display_name") or item.get("title") or "",
            abstract=reconstruct_openalex_abstract(item.get("abstract_inverted_index")),
            authors=_authors(item.get("authorships")),
            published_date=item.get("publication_date") or "",
            source="OpenAlex",
            doi=_doi(item.get("doi")),
            url=url,
            pdf_url=pdf_url,
            open_access=bool(open_access.get("is_oa") or pdf_url),
            citation_count=int(item.get("cited_by_count") or 0),
            categories=[concept.get("display_name", "") for concept in item.get("concepts") or [] if concept.get("display_name")],
            time_window=window.name,
            extra={"candidate_source": "openalex", "openalex_id": item.get("id") or ""},
        )
        if paper.title and paper_within_window(paper, window):
            papers.append(paper)
    return papers


def fetch_openalex(
    profile: ResearchProfile,
    window: Window,
    max_results_per_query: int = 20,
    sleep_seconds: float = 0.2,
    session: requests.Session | None = None,
) -> list[Paper]:
    """Search OpenAlex works for additional candidates in the given date window."""
    http = session or requests.Session()
    all_papers: list[Paper] = []
    params_base = {
        "filter": f"from_publication_date:{window.start.isoformat()},to_publication_date:{window.end.isoformat()}",
        "per-page": max_results_per_query,
        "sort": "publication_date:desc",
        "select": "id,doi,title,display_name,publication_date,authorships,primary_location,open_access,cited_by_count,concepts,abstract_inverted_index",
    }
    mailto = os.getenv("OPENALEX_MAILTO")
    if mailto:
        params_base["mailto"] = mailto
    for query in build_profile_queries(profile):
        params = dict(params_base)
        params["search"] = query
        response = http.get(OPENALEX_API, params=params, timeout=30, headers={"User-Agent": "paper-report/0.1"})
        response.raise_for_status()
        all_papers.extend(parse_openalex_works(response.json(), window))
        if sleep_seconds:
            time.sleep(sleep_seconds)
    return all_papers
