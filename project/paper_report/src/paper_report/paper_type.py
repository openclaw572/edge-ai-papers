from __future__ import annotations

import re
from dataclasses import replace
from typing import Iterable

from .models import Paper, ResearchProfile

REVIEW_PATTERNS = [
    r"\breview\b",
    r"\bsurvey\b",
    r"\boverview\b",
    r"\btaxonomy\b",
    r"\btutorial\b",
    r"\bscoping review\b",
    r"\bsystematic literature review\b",
    r"\bliterature review\b",
    r"\bmeta-analysis\b",
    r"\bbibliometric\b",
]

GENERAL_PATTERNS = [
    r"\bwe propose\b",
    r"\bwe introduce\b",
    r"\bwe present\b",
    r"\bwe develop\b",
    r"\bwe evaluate\b",
    r"\bexperiments?\b",
    r"\bdataset\b",
    r"\bbaseline\b",
]


def normalize_requested_paper_type(value: str | None) -> str:
    normalized = (value or "review").strip().lower().replace("-", "_")
    aliases = {
        "review_paper": "review",
        "survey": "review",
        "survey_paper": "review",
        "regular": "general",
        "regular_paper": "general",
        "ordinary": "general",
        "normal": "general",
        "paper": "general",
        "research": "general",
        "research_paper": "general",
    }
    normalized = aliases.get(normalized, normalized)
    return normalized if normalized in {"review", "general", "any"} else "review"


def classify_paper_type(paper: Paper) -> str:
    explicit = (paper.extra or {}).get("paper_type") or (paper.extra or {}).get("publication_type")
    if explicit:
        return normalize_requested_paper_type(str(explicit))
    text = "\n".join([paper.title or "", paper.abstract or "", " ".join(paper.categories or [])]).lower()
    if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in REVIEW_PATTERNS):
        return "review"
    if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in GENERAL_PATTERNS):
        return "general"
    return "general"


def with_paper_type(paper: Paper) -> Paper:
    paper_type = classify_paper_type(paper)
    extra = dict(paper.extra or {})
    extra["paper_type"] = paper_type
    return replace(paper, extra=extra)


def filter_papers_for_profile_type(profile: ResearchProfile, papers: Iterable[Paper]) -> list[Paper]:
    """Annotate each candidate with `paper.extra['paper_type']`.

    The workflow uses the annotation in quality gates and final selection. It does
    not delete non-matching candidates here, because if no requested paper type is
    found the run should still be able to produce transparent fallback results.
    """
    return [with_paper_type(paper) for paper in papers]
