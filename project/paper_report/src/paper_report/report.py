from __future__ import annotations

from datetime import date

from .models import RankedPaper, ResearchProfile, SelectionResult


def _score(value: float) -> str:
    return f"{value:.2f}"


def _authors(paper) -> str:
    return ", ".join(paper.authors) if paper.authors else "未知"


def _categories(paper) -> str:
    return ", ".join(paper.categories) if paper.categories else "未標示"


def _paper_type(paper) -> str:
    paper_type = (paper.extra or {}).get("paper_type", "review")
    return "Review paper" if paper_type == "review" else "一般 paper" if paper_type == "general" else str(paper_type)


def render_selected_paper(index: int, ranked: RankedPaper) -> str:
    paper = ranked.paper
    review = ranked.llm_review
    lines = [
        f"### {index}. {paper.title or 'Untitled'}",
        "",
        f"- 類別：{_categories(paper)}",
        f"- 論文類型：{_paper_type(paper)}",
        f"- 來源：{paper.source or '未知'}",
        f"- 發表年份：{paper.year}",
        f"- Published date：{paper.published_date or '未知'}",
        f"- 作者：{_authors(paper)}",
        f"- 連結：{paper.url or paper.pdf_url or '未提供'}",
        f"- PDF：{paper.pdf_url or '未找到'}",
        f"- Time window：{paper.time_window or '未標示'}",
        f"- Final score：{_score(ranked.final_score)}",
        f"- Semantic relevance：{_score(ranked.semantic_relevance)}",
        f"- LLM relevance score：{_score(review.relevance_score) if review else '未執行'}",
        f"- Why selected：{review.reason if review else '依 final_score 排序選出'}",
        f"- Recommended next action：{review.recommended_action if review else 'manual_review'}",
        "- 影片連結：待上傳",
    ]
    return "\n".join(lines)


def render_daily_report(profile: ResearchProfile, result: SelectionResult, run_date: date | None = None) -> str:
    run_date = run_date or date.today()
    primary = next((s for s in result.window_summaries if s.window_name.startswith("recent_")), None)
    total_candidates = sum(s.candidate_count for s in result.window_summaries)
    qualified_recent = primary.qualified_count if primary else 0
    fallback_text = "Yes" if result.fallback_used else "No"

    lines = [
        "# Daily Paper Hunter Report",
        "",
        "## 主題",
        "",
        profile.topic_name,
        "",
        "## 搜尋策略",
        "",
        "- Primary window: recent 4 months",
        "- Fallback policy: search older papers only if fewer than the configured minimum qualified papers are found",
        "- Fallback windows: 4–12 months ago, then 13–36 months ago, then 36–60 months ago",
        "- Ranking: research profile / seed paper vector similarity + recency + full-text availability + metadata signals",
        f"- Paper type preference: {getattr(profile, 'paper_type', 'review')}",
        "",
        "## 執行摘要",
        "",
        f"- Run date: {run_date.isoformat()}",
        f"- Candidate papers found: {total_candidates}",
        f"- Qualified recent papers: {qualified_recent}",
        f"- Fallback used: {fallback_text}",
        f"- Final selected papers: {len(result.selected_papers)}",
        "",
    ]
    if result.fallback_used:
        lines.extend([
            "## Fallback 說明",
            "",
            "本次最近四個月內未找到足夠高品質論文，因此包含較舊但相關性高的論文。",
            "",
        ])
    lines.extend(["## Selected Papers", ""])
    if not result.selected_papers:
        lines.append("本次沒有找到符合條件的論文。")
    for idx, paper in enumerate(result.selected_papers, start=1):
        lines.append(render_selected_paper(idx, paper))
        lines.append("")
    lines.extend(["## Notes", ""])
    for summary in result.window_summaries:
        lines.append(f"- {summary.window_name}: candidates={summary.candidate_count}, qualified={summary.qualified_count}")
    return "\n".join(lines).rstrip() + "\n"
