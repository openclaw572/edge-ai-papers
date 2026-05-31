from __future__ import annotations

from .models import RankedPaper, ResearchProfile, ReviewResult


def heuristic_llm_review(profile: ResearchProfile, ranked: list[RankedPaper], top_n: int = 20) -> list[RankedPaper]:
    """可替換成真實 LLM 的審查階段。

    預設不用外部 API，以 deterministic heuristic 模擬 LLM review 輸出欄位，讓 cron / CI / 測試可穩定運作。
    後續可在此處串接 OpenAI、NotebookLM 或其他內部模型。
    """
    reviewed: list[RankedPaper] = []
    for paper in ranked[:top_n]:
        practical = min(1.0, 0.45 * paper.full_text_score + 0.35 * paper.semantic_relevance + 0.20 * paper.code_or_project_signal)
        novelty = min(1.0, 0.70 * paper.recency_score + 0.30 * (1.0 - min(1.0, paper.citation_signal)))
        full_available = paper.full_text_score >= 0.7
        is_relevant = paper.semantic_relevance >= profile.quality_threshold.get("min_relevance_score", 0.75)
        if paper.negative_keyword_penalty:
            reason = "此論文雖有部分關鍵詞相似，但命中排除詞，已降低相關性分數。"
        elif is_relevant:
            reason = "此論文與研究描述、seed paper 語意向量及正向訊號高度接近，且具備可取得全文或實作價值。"
        else:
            reason = "此論文保留為候選，但與目前 research profile 的語意相關性不足。"
        action = "download_and_summarize_full_text" if is_relevant and full_available else "keep_for_manual_review"
        paper.llm_review = ReviewResult(
            is_relevant=is_relevant,
            relevance_score=round(paper.semantic_relevance, 4),
            novelty_score=round(novelty, 4),
            practical_value_score=round(practical, 4),
            full_text_available=full_available,
            reason=reason,
            recommended_action=action,
        )
        paper.final_llm_score = round(
            0.40 * paper.llm_review.relevance_score
            + 0.25 * paper.llm_review.practical_value_score
            + 0.20 * paper.llm_review.novelty_score
            + 0.15 * (1.0 if full_available else 0.0),
            4,
        )
        reviewed.append(paper)
    # Keep lower-ranked papers in the output for transparency, but they are not selected unless needed.
    reviewed.extend(ranked[top_n:])
    return sorted(reviewed, key=lambda p: (p.final_llm_score or p.final_score, p.final_score), reverse=True)
