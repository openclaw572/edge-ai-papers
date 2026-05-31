from __future__ import annotations

from datetime import date

from paper_report.models import Paper, RankedPaper, ResearchProfile
from paper_report.report_generation import LocalReportGenerator
from paper_report.source_utils import build_profile_queries
from paper_report.workflow import run_with_candidates_by_window


def profile() -> ResearchProfile:
    return ResearchProfile(
        topic_name="AI Agent Coordination and File-based Collaboration",
        description=(
            "AI agents coordinate through shared workspaces, append-only event logs, "
            "memory stores, file locks, tool invocation, and access-controlled workflows."
        ),
        positive_keywords=["agent coordination", "shared workspace", "append-only log"],
        negative_keywords=["robot swarm", "traffic control"],
        arxiv_categories=["cs.AI", "cs.MA"],
        quality_threshold={
            "min_final_score": 0.60,
            "min_relevance_score": 0.55,
            "min_papers_required": 1,
            "max_papers_to_output": 2,
        },
    )


def paper(title: str, abstract: str) -> Paper:
    return Paper(
        title=title,
        abstract=abstract,
        authors=["Fixture Author"],
        published_date="2026-04-01",
        source="fixture",
        url="https://example.org/paper",
        pdf_url="https://example.org/paper.pdf",
        open_access=True,
        time_window="recent_0_to_4_months",
    )


def ranked_with_type(paper_type: str) -> RankedPaper:
    p = paper(
        "A Survey of Shared Workspace Coordination for Autonomous Agents" if paper_type == "review" else "Shared Workspace Coordination for Autonomous Agents",
        "This review surveys the field." if paper_type == "review" else "We propose and evaluate a new architecture.",
    )
    p.extra["paper_type"] = paper_type
    return RankedPaper(
        paper=p,
        semantic_relevance=0.9,
        recency_score=1.0,
        full_text_score=1.0,
        citation_signal=0.1,
        code_or_project_signal=0.0,
        final_score=0.8,
    )


def test_research_profile_defaults_to_review_papers_and_filters_general_candidates():
    prof = profile()
    candidates = [
        paper(
            "A Survey of Shared Workspace Coordination for Autonomous Agents",
            "This review paper surveys autonomous AI agent coordination, shared workspaces, append-only logs, memory stores, file locks, tool use, and access control from 2023 to 2026.",
        ),
        paper(
            "Shared Workspace Coordination for Autonomous Agents",
            "We propose a new system where autonomous AI agents coordinate through shared files, locks, and event logs.",
        ),
    ]

    result = run_with_candidates_by_window(prof, {"recent_0_to_4_months": candidates}, today=date(2026, 5, 26))

    assert result.selected_papers
    assert all(item.paper.extra["paper_type"] == "review" for item in result.selected_papers)
    assert {item.paper.extra["paper_type"] for item in result.all_ranked_papers} == {"review", "general"}


def test_research_profile_can_request_general_papers_instead_of_default_review_papers():
    prof = profile()
    prof.paper_type = "general"
    candidates = [
        paper(
            "A Survey of Shared Workspace Coordination for Autonomous Agents",
            "This survey reviews autonomous AI agent coordination, shared workspaces, memory stores, and tool use.",
        ),
        paper(
            "Shared Workspace Coordination for Autonomous Agents",
            "We propose and evaluate a new architecture for autonomous AI agents using shared files, locks, and event logs.",
        ),
    ]

    result = run_with_candidates_by_window(prof, {"recent_0_to_4_months": candidates}, today=date(2026, 5, 26))

    assert result.selected_papers
    assert all(item.paper.extra["paper_type"] == "general" for item in result.selected_papers)


def test_candidate_queries_include_review_intent_by_default_and_general_when_requested():
    prof = profile()
    default_queries = build_profile_queries(prof)

    prof.paper_type = "general"
    general_queries = build_profile_queries(prof)

    assert any("review" in query.lower() or "survey" in query.lower() for query in default_queries)
    assert any("research paper" in query.lower() or "empirical" in query.lower() for query in general_queries)


def test_local_review_video_script_uses_review_paper_structure():
    script = LocalReportGenerator("/tmp").render_video_script(ranked_with_type("review"))

    expected_sections = [
        "開場：這篇 review paper 在整理什麼領域",
        "研究背景：為什麼這個領域重要",
        "Review 範圍：作者收集哪些論文、時間範圍、篩選條件",
        "分類架構：作者怎麼把相關研究分類",
        "各類方法重點：每一類代表什麼方向",
        "比較與趨勢：不同方法的優缺點、發展趨勢",
        "挑戰與限制：目前領域還有哪些問題沒解",
        "未來方向：作者建議未來可以怎麼做",
        "你的觀點：這篇 review 對你的研究/系統有什麼幫助",
        "總結",
    ]
    for section in expected_sections:
        assert section in script


def test_local_general_video_script_uses_regular_paper_structure():
    script = LocalReportGenerator("/tmp").render_video_script(ranked_with_type("general"))

    expected_sections = [
        "開場：paper title、作者、年份、來源",
        "研究問題：它想解決什麼問題",
        "背景與動機：為什麼這個問題重要",
        "相關工作簡述：以前方法有什麼不足",
        "核心方法：這篇 paper 提出什麼新方法",
        "系統/模型架構：方法流程圖、模組說明",
        "實驗設計：dataset、baseline、metrics",
        "實驗結果：主要表格與圖",
        "優點與貢獻：這篇 paper 做得好的地方",
        "限制與問題：可能的缺點",
        "你的觀點：跟你的研究/專案有什麼關係",
        "總結",
    ]
    for section in expected_sections:
        assert section in script
