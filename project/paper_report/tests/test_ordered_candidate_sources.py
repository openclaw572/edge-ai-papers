from datetime import date

from paper_report.models import Paper, ResearchProfile
from paper_report.workflow import run_with_ordered_fetchers

TODAY = date(2026, 5, 26)


def profile(min_required=2):
    return ResearchProfile(
        topic_name="AI Agent Coordination and File-based Collaboration",
        paper_type="general",
        description=(
            "AI agents coordinate through shared workspaces, append-only event logs, "
            "memory stores, file locks, tool invocation, and access-controlled workflows."
        ),
        positive_seed_papers=[
            {
                "title": "Shared Workspace Coordination for Tool-Using Agents",
                "abstract": "Autonomous AI agents coordinate through shared memory, file locks, and append-only logs.",
            }
        ],
        positive_keywords=["agent coordination", "shared workspace", "append-only log"],
        negative_keywords=["robot swarm", "traffic control", "wireless sensor network"],
        arxiv_categories=["cs.AI", "cs.MA"],
        quality_threshold={
            "min_final_score": 0.60,
            "min_relevance_score": 0.55,
            "min_papers_required": min_required,
            "max_papers_to_output": 5,
        },
    )


def good_paper(title, *, source="fixture", published_date="2026-04-01"):
    return Paper(
        title=title,
        abstract=(
            "Autonomous language-model agents coordinate tool use by writing events to a shared workspace, "
            "using memory stores, file locks, append-only logs, and access control to complete multi-step workflows."
        ),
        authors=["Fixture Author"],
        published_date=published_date,
        source=source,
        url=f"https://example.org/{title.replace(' ', '-').lower()}",
        pdf_url=f"https://example.org/{title.replace(' ', '-').lower()}.pdf",
        open_access=True,
        citation_count=2,
    )


def weak_paper():
    return Paper(
        title="Robot Swarm Traffic Control with Reinforcement Learning",
        abstract="Robot swarm traffic control and wireless sensor routing with no shared workspace or tool-mediated agent workflow.",
        published_date="2026-04-02",
        source="arXiv",
        url="https://example.org/weak",
    )


def test_ordered_fetchers_stop_after_arxiv_when_recent_quality_gate_is_satisfied():
    calls = []

    def record(source, papers):
        def fetch(window):
            calls.append((source, window.name))
            return papers

        return fetch

    fetchers = {
        "arxiv": record("arxiv", [good_paper("Shared File Logs for Tool-Using Agents", source="arXiv"), good_paper("Memory Locks for Agent Workspaces", source="arXiv")]),
        "semantic_scholar": record("semantic_scholar", [good_paper("Should Not Be Fetched", source="Semantic Scholar")]),
        "openalex": record("openalex", [good_paper("Should Not Be Fetched", source="OpenAlex")]),
        "google_scholar": record("google_scholar", [good_paper("Should Not Be Fetched", source="Google Scholar")]),
    }

    result = run_with_ordered_fetchers(profile(), fetchers, today=TODAY)

    assert calls == [("arxiv", "recent_0_to_4_months")]
    assert result.fallback_used is False
    assert all(item.paper.source == "arXiv" for item in result.selected_papers)


def test_ordered_fetchers_try_semantic_scholar_after_arxiv_is_insufficient_before_openalex():
    calls = []

    def fetch(source, papers):
        def inner(window):
            calls.append((source, window.name))
            return papers

        return inner

    fetchers = {
        "arxiv": fetch("arxiv", [weak_paper()]),
        "semantic_scholar": fetch(
            "semantic_scholar",
            [
                good_paper("Semantic Scholar Agent Workspace Discovery", source="Semantic Scholar"),
                good_paper("Semantic Scholar Tool Coordination Discovery", source="Semantic Scholar"),
            ],
        ),
        "openalex": fetch("openalex", [good_paper("OpenAlex Should Not Be Fetched", source="OpenAlex")]),
        "google_scholar": fetch("google_scholar", [good_paper("Google Scholar Should Not Be Fetched", source="Google Scholar")]),
    }

    result = run_with_ordered_fetchers(profile(), fetchers, today=TODAY)

    assert calls == [("arxiv", "recent_0_to_4_months"), ("semantic_scholar", "recent_0_to_4_months")]
    assert result.fallback_used is False
    assert any(item.paper.source == "Semantic Scholar" for item in result.selected_papers)


def test_ordered_fetchers_continue_to_next_source_when_a_source_fails():
    calls = []

    def broken_semantic(window):
        calls.append(("semantic_scholar", window.name))
        raise RuntimeError("Semantic Scholar rate limited")

    def openalex(window):
        calls.append(("openalex", window.name))
        return [
            good_paper("OpenAlex Agent Workspace Match", source="OpenAlex"),
            good_paper("OpenAlex Tool Coordination Match", source="OpenAlex"),
        ]

    fetchers = {
        "arxiv": lambda window: calls.append(("arxiv", window.name)) or [],
        "semantic_scholar": broken_semantic,
        "openalex": openalex,
        "google_scholar": lambda window: calls.append(("google_scholar", window.name)) or [],
    }

    result = run_with_ordered_fetchers(profile(), fetchers, today=TODAY)

    assert calls == [
        ("arxiv", "recent_0_to_4_months"),
        ("semantic_scholar", "recent_0_to_4_months"),
        ("openalex", "recent_0_to_4_months"),
    ]
    assert result.fallback_used is False
    assert any(item.paper.source == "OpenAlex" for item in result.selected_papers)


def test_ordered_fetchers_exhaust_primary_sources_before_moving_to_fallback_window():
    calls = []

    by_source_and_window = {
        ("arxiv", "recent_0_to_4_months"): [],
        ("semantic_scholar", "recent_0_to_4_months"): [good_paper("One Recent Semantic Scholar Match", source="Semantic Scholar")],
        ("openalex", "recent_0_to_4_months"): [],
        ("google_scholar", "recent_0_to_4_months"): [],
        ("arxiv", "fallback_4_to_12_months"): [
            good_paper("Fallback arXiv Agent Workspace Match", source="arXiv", published_date="2025-12-01")
        ],
    }

    def make_fetcher(source):
        def fetch(window):
            calls.append((source, window.name))
            return by_source_and_window.get((source, window.name), [])

        return fetch

    fetchers = {source: make_fetcher(source) for source in ["arxiv", "semantic_scholar", "openalex", "google_scholar"]}

    result = run_with_ordered_fetchers(profile(), fetchers, today=TODAY)

    assert calls == [
        ("arxiv", "recent_0_to_4_months"),
        ("semantic_scholar", "recent_0_to_4_months"),
        ("openalex", "recent_0_to_4_months"),
        ("google_scholar", "recent_0_to_4_months"),
        ("arxiv", "fallback_4_to_12_months"),
    ]
    assert result.fallback_used is True
    assert any(item.paper.time_window == "fallback_4_to_12_months" for item in result.selected_papers)
