from __future__ import annotations

import re
from collections.abc import Iterable

from .models import Paper, ResearchProfile, Window
from .paper_type import normalize_requested_paper_type

DEFAULT_CANDIDATE_SOURCE_ORDER = ["arxiv", "semantic_scholar", "openalex", "google_scholar"]


def candidate_source_order(profile: ResearchProfile, override: Iterable[str] | None = None) -> list[str]:
    configured = list(override or profile.search_policy.get("candidate_sources") or DEFAULT_CANDIDATE_SOURCE_ORDER)
    return list(dict.fromkeys(str(item) for item in configured if str(item).strip()))


def build_profile_queries(profile: ResearchProfile, max_queries: int = 8) -> list[str]:
    """Build broad recall queries for non-arXiv sources.

    Keywords are used only to fetch candidates. Ranking still happens later via
    profile/seed semantic relevance, negative filters, recency, full text, and metadata.
    """
    queries: list[str] = []
    paper_type = normalize_requested_paper_type(getattr(profile, "paper_type", "review"))
    if profile.topic_name:
        if paper_type == "review":
            queries.append(f"{profile.topic_name} review survey")
        elif paper_type == "general":
            queries.append(f"{profile.topic_name} research paper empirical")
        else:
            queries.append(profile.topic_name)
    queries.extend(profile.positive_keywords or [])

    # One broad description-derived query helps discover papers that do not contain
    # exact positive keyword phrases while avoiding overlong API query strings.
    description_terms = [token for token in re.findall(r"[A-Za-z][A-Za-z0-9+-]+", profile.description or "") if len(token) > 3]
    if description_terms:
        queries.append(" ".join(description_terms[:10]))

    if paper_type == "review":
        queries.extend(["review paper", "survey paper", "systematic literature review"])
    elif paper_type == "general":
        queries.extend(["research paper", "empirical study", "method experiment"])

    return list(dict.fromkeys(q.strip() for q in queries if q and q.strip()))[:max_queries]


def year_range(window: Window) -> str:
    if window.start.year == window.end.year:
        return str(window.start.year)
    return f"{window.start.year}-{window.end.year}"


def paper_year(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"\b(19|20)\d{2}\b", str(value))
    return int(match.group(0)) if match else None


def paper_within_window(paper: Paper, window: Window) -> bool:
    parsed = paper.parsed_date()
    if parsed is not None:
        return window.start <= parsed <= window.end
    year = paper_year(paper.published_date)
    if year is None:
        # Metadata-only sources sometimes omit publication dates; keep candidate for
        # ranking rather than silently losing a potentially relevant paper.
        return True
    return window.start.year <= year <= window.end.year


def assign_source_metadata(paper: Paper, *, source_name: str, window: Window) -> Paper:
    if not paper.time_window:
        paper.time_window = window.name
    paper.extra.setdefault("candidate_source", source_name)
    return paper
