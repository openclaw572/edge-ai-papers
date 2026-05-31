from datetime import date

from paper_report.models import Paper, ResearchProfile
from paper_report.workflow import build_date_windows, normalize_and_deduplicate


def test_build_date_windows_prefers_recent_then_fallbacks():
    profile = ResearchProfile(
        topic_name="Agent Coordination",
        description="agent coordination",
        search_policy={
            "primary_months": 4,
            "fallback_windows": [
                {"name": "fallback_4_to_12_months", "start_months_ago": 12, "end_months_ago": 4},
                {"name": "fallback_13_to_36_months", "start_months_ago": 36, "end_months_ago": 13},
                {"name": "fallback_36_to_60_months", "start_months_ago": 60, "end_months_ago": 36},
            ],
        },
    )

    windows = build_date_windows(profile, today=date(2026, 5, 26))

    assert [w.name for w in windows] == [
        "recent_0_to_4_months",
        "fallback_4_to_12_months",
        "fallback_13_to_36_months",
        "fallback_36_to_60_months",
    ]
    assert windows[0].start.isoformat() == "2026-01-26"
    assert windows[0].end.isoformat() == "2026-05-26"
    assert windows[1].start.isoformat() == "2025-05-26"
    assert windows[1].end.isoformat() == "2026-01-26"
    assert windows[2].start.isoformat() == "2023-05-26"
    assert windows[2].end.isoformat() == "2025-04-26"
    assert windows[3].start.isoformat() == "2021-05-26"
    assert windows[3].end.isoformat() == "2023-05-26"


def test_default_date_windows_fallback_to_five_years():
    profile = ResearchProfile(
        topic_name="Agent Coordination",
        description="agent coordination",
    )

    windows = build_date_windows(profile, today=date(2026, 5, 26))

    assert [w.name for w in windows] == [
        "recent_0_to_4_months",
        "fallback_4_to_12_months",
        "fallback_13_to_36_months",
        "fallback_36_to_60_months",
    ]
    assert [(w.start.isoformat(), w.end.isoformat()) for w in windows] == [
        ("2026-01-26", "2026-05-26"),
        ("2025-05-26", "2026-01-26"),
        ("2023-05-26", "2025-04-26"),
        ("2021-05-26", "2023-05-26"),
    ]


def test_normalize_and_deduplicate_prefers_doi_then_arxiv_then_title():
    papers = [
        Paper(title="Shared Workspace for AI Agents", abstract="A", doi="10.1/demo", arxiv_id="2601.00001"),
        Paper(title="Shared Workspace for AI Agents", abstract="A newer metadata", doi="10.1/demo", arxiv_id="2601.00001", pdf_url="https://arxiv.org/pdf/2601.00001"),
        Paper(title="File Based Coordination", abstract="B", arxiv_id="2601.00002"),
        Paper(title="file-based coordination!", abstract="B duplicate title"),
    ]

    deduped = normalize_and_deduplicate(papers)

    assert len(deduped) == 3
    doi_paper = next(p for p in deduped if p.doi == "10.1/demo")
    assert doi_paper.pdf_url == "https://arxiv.org/pdf/2601.00001"
