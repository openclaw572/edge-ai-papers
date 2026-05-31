from datetime import date

from paper_report.arxiv_client import parse_arxiv_atom
from paper_report.models import RankedPaper, Paper, ResearchProfile, ReviewResult, SelectionResult, WindowSummary
from paper_report.report import render_daily_report


def test_parse_arxiv_atom_extracts_metadata_and_pdf_url():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
      <entry>
        <id>http://arxiv.org/abs/2601.12345v1</id>
        <updated>2026-01-29T12:00:00Z</updated>
        <published>2026-01-28T12:00:00Z</published>
        <title>File-Based Coordination for AI Agents</title>
        <summary>We study shared files, locks, and append-only logs for agents.</summary>
        <author><name>Alice Example</name></author>
        <author><name>Bob Example</name></author>
        <category term="cs.AI" />
        <category term="cs.MA" />
        <link href="http://arxiv.org/abs/2601.12345v1" rel="alternate" type="text/html"/>
        <link title="pdf" href="http://arxiv.org/pdf/2601.12345v1" rel="related" type="application/pdf"/>
      </entry>
    </feed>"""

    papers = parse_arxiv_atom(xml)

    assert len(papers) == 1
    assert papers[0].arxiv_id == "2601.12345v1"
    assert papers[0].pdf_url == "http://arxiv.org/pdf/2601.12345v1"
    assert papers[0].authors == ["Alice Example", "Bob Example"]
    assert papers[0].categories == ["cs.AI", "cs.MA"]


def test_render_daily_report_is_traditional_chinese_and_transparent_about_fallback():
    profile = ResearchProfile(topic_name="AI Agent Coordination", description="agents")
    paper = Paper(
        title="Shared Workspace for Agents",
        abstract="agents coordinate",
        authors=["Alice", "Bob"],
        published_date="2025-12-01",
        source="arXiv",
        url="https://arxiv.org/abs/2512.00001",
        pdf_url="https://arxiv.org/pdf/2512.00001",
        categories=["cs.AI"],
        time_window="fallback_4_to_12_months",
    )
    ranked = RankedPaper(
        paper=paper,
        semantic_relevance=0.88,
        recency_score=0.7,
        full_text_score=1.0,
        citation_signal=0.1,
        code_or_project_signal=0.0,
        final_score=0.78,
        llm_review=ReviewResult(
            is_relevant=True,
            relevance_score=0.9,
            novelty_score=0.7,
            practical_value_score=0.8,
            full_text_available=True,
            reason="與共享工作區及 agent 協調高度相關。",
            recommended_action="download_and_summarize_full_text",
        ),
        final_llm_score=0.82,
    )
    result = SelectionResult(
        selected_papers=[ranked],
        all_ranked_papers=[ranked],
        window_summaries=[
            WindowSummary("recent_0_to_4_months", candidate_count=1, qualified_count=0),
            WindowSummary("fallback_4_to_12_months", candidate_count=1, qualified_count=1),
        ],
        fallback_used=True,
    )

    report = render_daily_report(profile, result, run_date=date(2026, 5, 26))

    assert "# Daily Paper Hunter Report" in report
    assert "## 執行摘要" in report
    assert "Fallback used: Yes" in report
    assert "Fallback windows: 4–12 months ago, then 13–36 months ago, then 36–60 months ago" in report
    assert "本次最近四個月內未找到足夠高品質論文" in report
    assert "類別：cs.AI" in report
    assert "作者：Alice, Bob" in report
    assert "影片連結：待上傳" in report
