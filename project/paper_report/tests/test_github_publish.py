from __future__ import annotations

import json
from pathlib import Path

from paper_report.github_publish import copy_project, publish_reports_to_site, reset_to_site_only


def test_reset_to_site_only_removes_pipeline_materials_and_rewrites_readme(tmp_path):
    for name in ["css", "js", "reports"]:
        (tmp_path / name).mkdir()
    (tmp_path / "index.html").write_text("<html></html>", encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "pipeline.py").write_text("old", encoding="utf-8")
    (tmp_path / "prompts").mkdir()
    (tmp_path / "completion-notice.md").write_text("old", encoding="utf-8")
    (tmp_path / "README.md").write_text("old methods", encoding="utf-8")

    removed = reset_to_site_only(tmp_path)

    assert "scripts" in removed
    assert not (tmp_path / "scripts").exists()
    assert not (tmp_path / "prompts").exists()
    assert (tmp_path / "index.html").exists()
    assert "網站架構" in (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "產線流程" not in (tmp_path / "README.md").read_text(encoding="utf-8")


def test_publish_reports_to_site_follows_existing_reports_index_shape(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "reports").mkdir()
    (repo / "reports" / "index.json").write_text(json.dumps({"lastUpdated": "2026-01-01", "dates": []}), encoding="utf-8")
    report = tmp_path / "report.md"
    report.write_text("---\nsource: arXiv\n---\n# Paper A\n\n## 影片連結\n\n- YouTube: 待上傳\n", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"artifacts": [{"paper_title": "Paper A", "markdown_path": str(report), "youtube_url": "https://youtu.be/abc"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    selection = tmp_path / "daily_report.json"
    selection.write_text(
        json.dumps(
            {
                "selected_papers": [
                    {
                        "paper": {
                            "title": "Paper A",
                            "categories": ["cs.AI"],
                            "pdf_url": "https://example.org/a.pdf",
                            "extra": {"paper_type": "review"},
                        }
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    copied = publish_reports_to_site(manifest, repo, selection_json_path=selection, run_date="2026-05-26")

    assert len(copied) == 1
    daily = json.loads((repo / "reports" / "2026-05-26" / "index.json").read_text(encoding="utf-8"))
    assert daily["papers"][0]["category"] == "cs.AI"
    assert daily["papers"][0]["youtubeUrl"] == "https://youtu.be/abc"
    assert "https://youtu.be/abc" in Path(copied[0]).read_text(encoding="utf-8")
    global_index = json.loads((repo / "reports" / "index.json").read_text(encoding="utf-8"))
    assert global_index["dates"][0]["date"] == "2026-05-26"


def test_copy_project_excludes_outputs_and_caches(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "README.md").write_text("readme", encoding="utf-8")
    (project / "src").mkdir()
    (project / "src" / "x.py").write_text("x=1", encoding="utf-8")
    (project / "outputs").mkdir()
    (project / "outputs" / "secret.mp4").write_text("video", encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()

    dest = copy_project(project, repo)

    assert (dest / "README.md").exists()
    assert (dest / "src" / "x.py").exists()
    assert not (dest / "outputs").exists()
