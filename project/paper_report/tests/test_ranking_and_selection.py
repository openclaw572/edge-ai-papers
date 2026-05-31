from datetime import date

from paper_report.models import Paper, ResearchProfile
from paper_report.ranking import rank_papers
from paper_report.workflow import run_with_candidates_by_window


def make_profile():
    return ResearchProfile(
        topic_name="AI Agent Coordination and File-based Collaboration",
        description=(
            "AI agents, multi-agent systems, autonomous agents, shared workspace, "
            "file-based communication, event brokers, append-only logs, locks, memory stores"
        ),
        positive_seed_papers=[
            {
                "title": "Shared Workspace Coordination for Tool-Using Agents",
                "abstract": "Autonomous AI agents coordinate through shared memory and append-only logs.",
            }
        ],
        positive_keywords=["multi-agent systems", "shared workspace", "append-only log"],
        negative_keywords=["robot swarm", "traffic control"],
        arxiv_categories=["cs.AI", "cs.MA"],
        quality_threshold={
            "min_final_score": 0.60,
            "min_relevance_score": 0.55,
            "min_papers_required": 2,
            "max_papers_to_output": 3,
        },
    )


def test_rank_papers_uses_embedding_relevance_not_only_keywords():
    profile = make_profile()
    papers = [
        Paper(
            title="Workspace Memory for Autonomous Tool-Using Agents",
            abstract="Agents coordinate by writing events to an append-only shared memory log with locks.",
            published_date="2026-04-01",
            pdf_url="https://arxiv.org/pdf/2604.00001",
            open_access=True,
            citation_count=2,
            time_window="recent_0_to_4_months",
        ),
        Paper(
            title="Multi-agent traffic control with robot swarm",
            abstract="Traffic control and robot swarm routing use reinforcement learning.",
            published_date="2026-04-02",
            pdf_url="https://arxiv.org/pdf/2604.00002",
            open_access=True,
            citation_count=100,
            time_window="recent_0_to_4_months",
        ),
    ]

    ranked = rank_papers(profile, papers, today=date(2026, 5, 26))

    assert ranked[0].paper.title == "Workspace Memory for Autonomous Tool-Using Agents"
    assert ranked[0].semantic_relevance > ranked[1].semantic_relevance
    assert ranked[1].negative_keyword_penalty > 0


def test_run_with_candidates_triggers_fallback_only_when_recent_quality_is_insufficient():
    profile = make_profile()
    recent = [
        Paper(
            title="Barely Related Tool Paper",
            abstract="A generic benchmark for tools with little coordination detail.",
            published_date="2026-04-01",
            pdf_url="https://arxiv.org/pdf/2604.01001",
            time_window="recent_0_to_4_months",
        )
    ]
    fallback = [
        Paper(
            title="Shared File Workspace for Autonomous Agents",
            abstract="Autonomous agents coordinate by appending events to shared files, using locks and memory stores.",
            published_date="2025-12-01",
            pdf_url="https://arxiv.org/pdf/2512.00001",
            open_access=True,
            citation_count=4,
            time_window="fallback_4_to_12_months",
        ),
        Paper(
            title="Event Broker Coordination for Multi-Agent Tool Use",
            abstract="A broker mediates tool-using AI agents through event logs, access control, and shared workspaces.",
            published_date="2025-11-20",
            pdf_url="https://arxiv.org/pdf/2511.00002",
            open_access=True,
            citation_count=3,
            time_window="fallback_4_to_12_months",
        ),
    ]

    result = run_with_candidates_by_window(
        profile,
        {
            "recent_0_to_4_months": recent,
            "fallback_4_to_12_months": fallback,
        },
        today=date(2026, 5, 26),
    )

    assert result.fallback_used is True
    assert result.window_summaries[0].qualified_count < profile.quality_threshold["min_papers_required"]
    assert any(p.paper.time_window == "fallback_4_to_12_months" for p in result.selected_papers)
    assert len(result.selected_papers) <= 3
