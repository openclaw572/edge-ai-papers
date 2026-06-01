from __future__ import annotations

import calendar
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from datetime import date
from typing import Iterable

from .models import Paper, RankedPaper, ResearchProfile, SelectionResult, Window, WindowSummary
from .ranking import rank_papers
from .review import heuristic_llm_review
from .source_utils import assign_source_metadata, candidate_source_order
from .paper_type import filter_papers_for_profile_type, normalize_requested_paper_type


def subtract_months(value: date, months: int) -> date:
    month_index = value.month - 1 - months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def build_date_windows(profile: ResearchProfile, today: date | None = None) -> list[Window]:
    today = today or date.today()
    policy = profile.search_policy or {}
    primary_months = int(policy.get("primary_months", 4))
    windows = [
        Window(
            name=f"recent_0_to_{primary_months}_months",
            start=subtract_months(today, primary_months),
            end=today,
            is_fallback=False,
        )
    ]
    for fallback in policy.get("fallback_windows", []):
        windows.append(
            Window(
                name=fallback.get("name") or f"fallback_{fallback['end_months_ago']}_to_{fallback['start_months_ago']}_months",
                start=subtract_months(today, int(fallback["start_months_ago"])),
                end=subtract_months(today, int(fallback["end_months_ago"])),
                is_fallback=True,
            )
        )
    return windows


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", (title or "").lower())).strip()


def dedupe_key(paper: Paper) -> str:
    if paper.doi:
        return f"doi:{paper.doi.lower()}"
    if paper.arxiv_id:
        return f"arxiv:{paper.arxiv_id.lower().removesuffix('v1')}"
    if paper.semantic_scholar_id:
        return f"s2:{paper.semantic_scholar_id.lower()}"
    return f"title:{normalize_title(paper.title)}"


def merge_paper(existing: Paper, incoming: Paper) -> Paper:
    data = existing.to_dict()
    incoming_data = incoming.to_dict()
    for key, value in incoming_data.items():
        if key == "extra":
            merged_extra = dict(data.get("extra") or {})
            merged_extra.update(value or {})
            data["extra"] = merged_extra
        elif key in {"authors", "categories"}:
            merged = list(dict.fromkeys((data.get(key) or []) + (value or [])))
            data[key] = merged
        elif key == "abstract" and value and len(value) > len(data.get(key) or ""):
            data[key] = value
        elif value and not data.get(key):
            data[key] = value
    return Paper.from_dict(data)


def normalize_and_deduplicate(papers: Iterable[Paper]) -> list[Paper]:
    deduped: dict[str, Paper] = {}
    for paper in papers:
        key = dedupe_key(paper)
        if key in deduped:
            deduped[key] = merge_paper(deduped[key], paper)
        else:
            deduped[key] = paper
    return list(deduped.values())


def qualified_papers(profile: ResearchProfile, ranked: Iterable[RankedPaper]) -> list[RankedPaper]:
    threshold = profile.quality_threshold
    min_final = float(threshold.get("min_final_score", 0.72))
    min_relevance = float(threshold.get("min_relevance_score", 0.75))
    qualified = [p for p in ranked if p.final_score >= min_final and p.semantic_relevance >= min_relevance]
    requested = normalize_requested_paper_type(getattr(profile, "paper_type", "review"))
    if requested == "any":
        return qualified
    return [p for p in qualified if p.paper.extra.get("paper_type") == requested]


def select_final_papers(profile: ResearchProfile, ranked: list[RankedPaper]) -> list[RankedPaper]:
    max_results = int(profile.quality_threshold.get("max_papers_to_output", 5))
    eligible = [p for p in ranked if p.llm_review is None or p.llm_review.is_relevant]
    if not eligible:
        eligible = ranked
    requested = normalize_requested_paper_type(getattr(profile, "paper_type", "review"))
    if requested != "any":
        requested_qualified = qualified_papers(profile, eligible)
        if requested_qualified:
            eligible = requested_qualified
    sorted_eligible = sorted(eligible, key=lambda p: (p.final_llm_score or p.final_score, p.final_score), reverse=True)
    return dedupe_ranked_by_title(sorted_eligible)[:max_results]


def dedupe_ranked_by_title(ranked: Iterable[RankedPaper]) -> list[RankedPaper]:
    """Keep at most one selected paper per normalized title.

    Candidate sources can return the same paper with different DOI/arXiv/S2 IDs.
    The user-facing cron report should never include duplicated titles in the
    same run, so final selection uses title-level de-duplication after sorting
    by quality score.
    """
    seen_titles: set[str] = set()
    unique: list[RankedPaper] = []
    for item in ranked:
        key = normalize_title(item.paper.title)
        if key and key in seen_titles:
            continue
        if key:
            seen_titles.add(key)
        unique.append(item)
    return unique


def _assign_window(papers: Iterable[Paper], window_name: str) -> list[Paper]:
    return [paper if paper.time_window else replace(paper, time_window=window_name) for paper in papers]


def run_with_candidates_by_window(
    profile: ResearchProfile,
    candidates_by_window: Mapping[str, Iterable[Paper]],
    today: date | None = None,
) -> SelectionResult:
    today = today or date.today()
    all_ranked: list[RankedPaper] = []
    summaries: list[WindowSummary] = []
    fallback_used = False
    min_required = int(profile.quality_threshold.get("min_papers_required", 3))

    for index, window in enumerate(build_date_windows(profile, today=today)):
        raw_candidates = _assign_window(candidates_by_window.get(window.name, []), window.name)
        candidates = filter_papers_for_profile_type(profile, normalize_and_deduplicate(raw_candidates))
        ranked = rank_papers(profile, candidates, today=today)
        qualified = qualified_papers(profile, ranked)
        summaries.append(WindowSummary(window.name, len(candidates), len(qualified)))
        all_ranked.extend(ranked)

        if index == 0 and len(qualified) >= min_required:
            break
        if index == 0 and len(qualified) < min_required:
            fallback_used = True
            continue
        if fallback_used and len(qualified_papers(profile, all_ranked)) >= min_required:
            break

    reviewed = heuristic_llm_review(profile, sorted(all_ranked, key=lambda p: p.final_score, reverse=True), top_n=20)
    selected = select_final_papers(profile, reviewed)
    return SelectionResult(
        selected_papers=selected,
        all_ranked_papers=reviewed,
        window_summaries=summaries,
        fallback_used=fallback_used,
    )


def _review_and_select(profile: ResearchProfile, ranked: list[RankedPaper], summaries: list[WindowSummary], fallback_used: bool) -> SelectionResult:
    reviewed = heuristic_llm_review(profile, sorted(ranked, key=lambda p: p.final_score, reverse=True), top_n=20)
    selected = select_final_papers(profile, reviewed)
    return SelectionResult(
        selected_papers=selected,
        all_ranked_papers=reviewed,
        window_summaries=summaries,
        fallback_used=fallback_used,
    )


def _rank_window_candidates(profile: ResearchProfile, papers: Iterable[Paper], window: Window, today: date) -> tuple[list[Paper], list[RankedPaper]]:
    candidates = filter_papers_for_profile_type(profile, normalize_and_deduplicate(_assign_window(papers, window.name)))
    return candidates, rank_papers(profile, candidates, today=today)


def run_with_ordered_fetchers(
    profile: ResearchProfile,
    fetchers: Mapping[str, Callable[[Window], Iterable[Paper]]],
    source_order: Sequence[str] | None = None,
    today: date | None = None,
) -> SelectionResult:
    """Fetch candidates in source order, stopping as soon as quality gate is met.

    Within each date window the source order is:
    arXiv -> Semantic Scholar -> OpenAlex -> Google Scholar by default. The next
    source is queried only when the cumulative candidates in the current window do
    not meet the quality threshold. Older fallback windows are reached only after
    all configured sources for the newer window remain insufficient.
    """
    today = today or date.today()
    min_required = int(profile.quality_threshold.get("min_papers_required", 3))
    order = candidate_source_order(profile, override=source_order)
    all_ranked: list[RankedPaper] = []
    summaries: list[WindowSummary] = []
    fallback_used = False

    for window_index, window in enumerate(build_date_windows(profile, today=today)):
        window_candidates_raw: list[Paper] = []
        window_candidates: list[Paper] = []
        window_ranked: list[RankedPaper] = []

        for source_name in order:
            fetcher = fetchers.get(source_name)
            if fetcher is None:
                continue
            try:
                fetched_raw = list(fetcher(window))
            except Exception:
                # External paper APIs are best-effort candidate sources. If one is
                # rate-limited or temporarily unavailable, keep the cron job useful
                # by continuing to the next source in the configured order.
                continue
            fetched = [assign_source_metadata(paper, source_name=source_name, window=window) for paper in fetched_raw]
            window_candidates_raw.extend(fetched)
            window_candidates, window_ranked = _rank_window_candidates(profile, window_candidates_raw, window, today)
            current_window_qualified = qualified_papers(profile, window_ranked)
            combined_ranked = all_ranked + window_ranked

            if window_index == 0 and len(current_window_qualified) >= min_required:
                summaries.append(WindowSummary(window.name, len(window_candidates), len(current_window_qualified)))
                return _review_and_select(profile, combined_ranked, summaries, fallback_used=False)

            if window_index > 0 and len(qualified_papers(profile, combined_ranked)) >= min_required:
                summaries.append(WindowSummary(window.name, len(window_candidates), len(current_window_qualified)))
                return _review_and_select(profile, combined_ranked, summaries, fallback_used=True)

        # Either no fetcher was configured for this window, or every source was insufficient.
        summaries.append(WindowSummary(window.name, len(window_candidates), len(qualified_papers(profile, window_ranked))))
        all_ranked.extend(window_ranked)

        if window_index == 0 and len(qualified_papers(profile, window_ranked)) < min_required:
            fallback_used = True
            continue

        if len(qualified_papers(profile, all_ranked)) >= min_required:
            break

    return _review_and_select(profile, all_ranked, summaries, fallback_used=fallback_used)


def run_with_fetcher(
    profile: ResearchProfile,
    fetcher: Callable[[Window], Iterable[Paper]],
    today: date | None = None,
) -> SelectionResult:
    today = today or date.today()
    candidates_by_window: dict[str, list[Paper]] = {}
    for window in build_date_windows(profile, today=today):
        candidates_by_window[window.name] = list(fetcher(window))
        partial = run_with_candidates_by_window(profile, candidates_by_window, today=today)
        if not partial.fallback_used or len(qualified_papers(profile, partial.all_ranked_papers)) >= int(profile.quality_threshold.get("min_papers_required", 3)):
            return partial
    return run_with_candidates_by_window(profile, candidates_by_window, today=today)
