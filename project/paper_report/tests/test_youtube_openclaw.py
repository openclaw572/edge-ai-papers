from __future__ import annotations

import json
from pathlib import Path

from paper_report.report_generation import CommandResult
from paper_report.youtube_openclaw import OpenClawYouTubeUploader, parse_youtube_url


def test_parse_youtube_url_accepts_watch_and_short_urls():
    assert parse_youtube_url('done https://www.youtube.com/watch?v=abc_DEF-12') == 'https://www.youtube.com/watch?v=abc_DEF-12'
    assert parse_youtube_url('done https://youtu.be/abc_DEF-12') == 'https://youtu.be/abc_DEF-12'


def test_openclaw_youtube_uploader_updates_manifest_and_markdown(tmp_path):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake video")
    markdown = tmp_path / "report.md"
    markdown.write_text("# Report\n\n## 影片連結\n\n- YouTube: 待上傳\n", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"artifacts": [{"paper_title": "Paper A", "video_path": str(video), "markdown_path": str(markdown)}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    prompts: list[str] = []

    def runner(message: str, timeout=None):
        prompts.append(message)
        return CommandResult(
            0,
            json.dumps(
                {
                    "success": True,
                    "youtube_url": "https://www.youtube.com/watch?v=abc123XYZ",
                    "thumbnail_path": str(tmp_path / "youtube_thumbnail.png"),
                }
            ),
        )

    results = OpenClawYouTubeUploader(runner=runner, max_workers=1).upload_artifacts(manifest)

    assert results[0].ok
    assert "webbridge" in prompts[0]
    assert "image2.0" in prompts[0]
    assert "custom thumbnail" in prompts[0]
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["artifacts"][0]["youtube_url"] == "https://www.youtube.com/watch?v=abc123XYZ"
    assert data["artifacts"][0]["youtube_thumbnail_path"].endswith("youtube_thumbnail.png")
    assert "https://www.youtube.com/watch?v=abc123XYZ" in markdown.read_text(encoding="utf-8")
