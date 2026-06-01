from __future__ import annotations

import json

from paper_report.pipeline import FullPipelineRunner


def test_cleanup_after_success_deletes_notebooklm_notebooks_and_local_artifacts(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    generated = project / "outputs" / "generated_reports"
    generated.mkdir(parents=True)
    (generated / "report.md").write_text("# report", encoding="utf-8")
    (generated / "video.mp4").write_bytes(b"video")
    manifest = generated / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "artifacts": [
                    {"paper_title": "A", "notebook_id": "nb_1"},
                    {"paper_title": "B", "notebook_id": "nb_1"},
                    {"paper_title": "C", "notebook_id": "nb_2"},
                ]
            }
        ),
        encoding="utf-8",
    )
    daily_md = project / "outputs" / "daily_report.md"
    daily_json = project / "outputs" / "daily_report.json"
    daily_md.write_text("daily", encoding="utf-8")
    daily_json.write_text("{}", encoding="utf-8")

    runner = FullPipelineRunner(project_dir=project, skip_email=True)
    deleted_notebooks: list[str] = []

    def fake_delete(notebook_id, errors):
        deleted_notebooks.append(notebook_id)
        return True

    runner._delete_notebooklm_notebook = fake_delete  # type: ignore[method-assign]

    deleted, errors = runner._cleanup_after_success(manifest, generated, daily_md, daily_json)

    assert errors == []
    assert deleted_notebooks == ["nb_1", "nb_2"]
    assert not generated.exists()
    assert not daily_md.exists()
    assert not daily_json.exists()
    assert str(generated) in deleted
    assert "notebooklm:nb_1" in deleted
    assert "notebooklm:nb_2" in deleted
