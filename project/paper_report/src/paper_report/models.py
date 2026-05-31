from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any


DEFAULT_SEARCH_POLICY = {
    "primary_months": 4,
    "candidate_sources": ["arxiv", "semantic_scholar", "openalex", "google_scholar"],
    "fallback_windows": [
        {"name": "fallback_4_to_12_months", "start_months_ago": 12, "end_months_ago": 4},
        {"name": "fallback_13_to_36_months", "start_months_ago": 36, "end_months_ago": 13},
        {"name": "fallback_36_to_60_months", "start_months_ago": 60, "end_months_ago": 36},
    ],
}

DEFAULT_QUALITY_THRESHOLD = {
    "min_final_score": 0.72,
    "min_relevance_score": 0.75,
    "min_papers_required": 3,
    "max_papers_to_output": 5,
}


@dataclass(slots=True)
class ResearchProfile:
    topic_name: str
    description: str
    paper_type: str = "review"
    positive_seed_papers: list[Any] = field(default_factory=list)
    positive_keywords: list[str] = field(default_factory=list)
    negative_keywords: list[str] = field(default_factory=list)
    arxiv_categories: list[str] = field(default_factory=list)
    prefer_full_text: bool = True
    search_policy: dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_SEARCH_POLICY))
    quality_threshold: dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_QUALITY_THRESHOLD))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResearchProfile":
        merged = dict(data or {})
        merged.setdefault("positive_seed_papers", [])
        merged.setdefault("paper_type", "review")
        merged.setdefault("positive_keywords", [])
        merged.setdefault("negative_keywords", [])
        merged.setdefault("arxiv_categories", [])
        merged.setdefault("prefer_full_text", True)
        policy = dict(DEFAULT_SEARCH_POLICY)
        policy.update(merged.get("search_policy") or {})
        if "fallback_windows" not in (merged.get("search_policy") or {}):
            policy["fallback_windows"] = DEFAULT_SEARCH_POLICY["fallback_windows"]
        merged["search_policy"] = policy
        threshold = dict(DEFAULT_QUALITY_THRESHOLD)
        threshold.update(merged.get("quality_threshold") or {})
        merged["quality_threshold"] = threshold
        return cls(**merged)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Window:
    name: str
    start: date
    end: date
    is_fallback: bool = False


@dataclass(slots=True)
class Paper:
    title: str = ""
    abstract: str = ""
    authors: list[str] = field(default_factory=list)
    published_date: str = ""
    source: str = ""
    doi: str = ""
    arxiv_id: str = ""
    semantic_scholar_id: str = ""
    url: str = ""
    pdf_url: str = ""
    open_access: bool = False
    citation_count: int = 0
    influential_citation_count: int = 0
    categories: list[str] = field(default_factory=list)
    time_window: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Paper":
        known = {field_name for field_name in cls.__dataclass_fields__}
        kwargs = {k: v for k, v in (data or {}).items() if k in known}
        if kwargs.get("authors") is None:
            kwargs["authors"] = []
        if kwargs.get("categories") is None:
            kwargs["categories"] = []
        return cls(**kwargs)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def year(self) -> str:
        if not self.published_date:
            return "未知"
        return self.published_date[:4]

    def parsed_date(self) -> date | None:
        if not self.published_date:
            return None
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"):
            try:
                return datetime.strptime(self.published_date, fmt).date()
            except ValueError:
                continue
        try:
            return date.fromisoformat(self.published_date[:10])
        except ValueError:
            return None


@dataclass(slots=True)
class ReviewResult:
    is_relevant: bool
    relevance_score: float
    novelty_score: float
    practical_value_score: float
    full_text_available: bool
    reason: str
    recommended_action: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RankedPaper:
    paper: Paper
    semantic_relevance: float
    recency_score: float
    full_text_score: float
    citation_signal: float
    code_or_project_signal: float
    final_score: float
    profile_similarity: float = 0.0
    seed_similarity: float = 0.0
    positive_keyword_score: float = 0.0
    negative_keyword_penalty: float = 0.0
    llm_review: ReviewResult | None = None
    final_llm_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["paper"] = self.paper.to_dict()
        if self.llm_review:
            data["llm_review"] = self.llm_review.to_dict()
        return data


@dataclass(slots=True)
class WindowSummary:
    window_name: str
    candidate_count: int
    qualified_count: int


@dataclass(slots=True)
class SelectionResult:
    selected_papers: list[RankedPaper]
    all_ranked_papers: list[RankedPaper]
    window_summaries: list[WindowSummary]
    fallback_used: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_papers": [p.to_dict() for p in self.selected_papers],
            "all_ranked_papers": [p.to_dict() for p in self.all_ranked_papers],
            "window_summaries": [asdict(w) for w in self.window_summaries],
            "fallback_used": self.fallback_used,
        }
