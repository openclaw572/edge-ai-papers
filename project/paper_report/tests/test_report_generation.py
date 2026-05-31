from __future__ import annotations

import json
from pathlib import Path

from paper_report.models import Paper, RankedPaper, SelectionResult, WindowSummary
from paper_report.report_generation import (
    CommandResult,
    GenerationArtifact,
    NotebookLMGenerator,
    ReportGenerationOrchestrator,
    split_generation_methods,
)


def ranked(title: str, score: float = 0.8, pdf_url: str = "https://example.org/paper.pdf") -> RankedPaper:
    return RankedPaper(
        paper=Paper(
            title=title,
            abstract="Autonomous AI agents coordinate through shared workspaces, memory, locks, event logs, and tools.",
            authors=["Alice", "Bob"],
            published_date="2026-04-01",
            source="arXiv",
            url="https://example.org/paper",
            pdf_url=pdf_url,
            categories=["cs.AI"],
            time_window="recent_0_to_4_months",
        ),
        semantic_relevance=0.9,
        recency_score=1.0,
        full_text_score=1.0,
        citation_signal=0.1,
        code_or_project_signal=0.0,
        final_score=score,
    )


def test_split_generation_methods_uses_floor_half_for_local_method():
    papers = [ranked(f"Paper {idx}") for idx in range(5)]

    assignments = split_generation_methods(papers)

    assert [item.method for item in assignments] == ["local", "local", "notebooklm", "notebooklm", "notebooklm"]


def test_local_generation_writes_traditional_chinese_markdown_and_video(tmp_path):
    orchestrator = ReportGenerationOrchestrator(output_dir=tmp_path, max_workers=2)

    artifact = orchestrator.generate_local(ranked("Shared Workspace Agents"), index=1)

    assert artifact.method == "local"
    assert artifact.markdown_path and Path(artifact.markdown_path).exists()
    assert artifact.video_path and Path(artifact.video_path).exists()
    assert "## 論文摘要" in Path(artifact.markdown_path).read_text(encoding="utf-8")
    assert Path(artifact.video_path).suffix == ".mp4"


def test_notebooklm_download_error_delegates_to_openclaw_webbridge(tmp_path):
    calls: list[list[str]] = []

    def runner(command, timeout=None):
        calls.append(command)
        if command[:3] == ["nlm", "notebook", "create"]:
            return CommandResult(0, "notebook nb_123")
        if command[:3] == ["nlm", "source", "add"]:
            return CommandResult(0, "source added")
        if command[:3] == ["nlm", "report", "create"]:
            return CommandResult(0, "artifact report_123")
        if command[:3] == ["nlm", "video", "create"]:
            return CommandResult(0, "artifact video_123")
        if command[:3] == ["nlm", "download", "report"]:
            return CommandResult(1, "download failed")
        if command[:3] == ["nlm", "download", "video"]:
            output = Path(command[command.index("--output") + 1])
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"video")
            return CommandResult(0, "downloaded")
        raise AssertionError(command)

    openclaw_tasks: list[str] = []

    def openclaw_runner(message, timeout=None):
        openclaw_tasks.append(message)
        report_path = tmp_path / "notebooklm" / "shared-workspace-agents" / "report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("# NotebookLM report", encoding="utf-8")
        return CommandResult(0, json.dumps({"ok": True}))

    generator = NotebookLMGenerator(output_dir=tmp_path, runner=runner, openclaw_runner=openclaw_runner, video_wait_timeout_seconds=0)

    artifact = generator.generate(ranked("Shared Workspace Agents"), index=1)

    assert artifact.method == "notebooklm"
    assert artifact.markdown_path and Path(artifact.markdown_path).exists()
    assert artifact.video_path and Path(artifact.video_path).exists()
    assert any("webbridge" in task and "download report" in task for task in openclaw_tasks)


def test_notebooklm_video_timeout_falls_back_to_local_video(tmp_path):
    def runner(command, timeout=None):
        if command[:3] == ["nlm", "notebook", "create"]:
            return CommandResult(0, "notebook nb_123")
        if command[:3] == ["nlm", "source", "add"]:
            return CommandResult(0, "source added")
        if command[:3] == ["nlm", "report", "create"]:
            return CommandResult(0, "artifact report_123")
        if command[:3] == ["nlm", "video", "create"]:
            return CommandResult(0, "artifact video_123")
        if command[:3] == ["nlm", "download", "report"]:
            output = Path(command[command.index("--output") + 1])
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text("# NotebookLM report", encoding="utf-8")
            return CommandResult(0, "downloaded")
        if command[:3] == ["nlm", "download", "video"]:
            return CommandResult(2, "not ready")
        raise AssertionError(command)

    generator = NotebookLMGenerator(output_dir=tmp_path, runner=runner, video_wait_timeout_seconds=0)

    artifact = generator.generate(ranked("Timeout Video Paper"), index=1)

    assert artifact.method == "notebooklm"
    assert artifact.video_status == "local_fallback_after_timeout"
    assert artifact.video_path and Path(artifact.video_path).exists()


def test_orchestrator_processes_assignments_in_parallel_and_writes_manifest(tmp_path):
    selected = [ranked(f"Paper {idx}") for idx in range(4)]
    result = SelectionResult(selected_papers=selected, all_ranked_papers=selected, window_summaries=[WindowSummary("recent_0_to_4_months", 4, 4)])

    def notebook_generator(paper, index):
        out = tmp_path / "stub" / f"{index}.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(paper.paper.title, encoding="utf-8")
        return GenerationArtifact(paper_title=paper.paper.title, method="notebooklm", markdown_path=str(out), video_path=str(out.with_suffix(".mp4")))

    orchestrator = ReportGenerationOrchestrator(output_dir=tmp_path, max_workers=4, notebooklm_generator=notebook_generator)

    artifacts = orchestrator.generate_for_selection(result)

    manifest = tmp_path / "manifest.json"
    assert manifest.exists()
    assert [a.method for a in artifacts].count("local") == 2
    assert [a.method for a in artifacts].count("notebooklm") == 2
    assert len(json.loads(manifest.read_text(encoding="utf-8"))["artifacts"]) == 4
