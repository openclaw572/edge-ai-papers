#!/usr/bin/env python3
"""Publish a daily NotebookLM paper batch into the edge-ai-papers repo.

Input: a JSON manifest, for example:
{
  "date": "2026-04-19",
  "paperType": "review",
  "generatedAt": "2026-04-19T23:59:00+08:00",
  "notebookLM": {"notebookId": "...", "singleSourceQueries": []},
  "papers": [
    {
      "id": "paper-1",
      "category": "Edge AI",
      "title": "Paper title",
      "slug": "paper-1-edge-ai-foo-bar",
      "link": "https://arxiv.org/abs/...",
      "type": "REVIEW PAPER",
      "tags": ["Edge AI", "Review Paper"],
      "markdown_source": "/tmp/report.md",
      "video_file": "/tmp/video.mp4",
      "youtube_url": "https://youtube.com/watch?v=...",
      "figure_file": "/tmp/cover.png",
      "source": "arXiv",
      "year": "2026",
      "authors": "Author A, Author B"
    }
  ]
}

Behavior:
- Creates reports/YYYY-MM-DD/
- Copies markdown into daily folder
- Optionally copies figures into daily figures/
- Optionally copies videos into daily videos/
- Appends a video section to markdown when video/youtube is provided
- Writes reports/YYYY-MM-DD/index.json
- Updates reports/index.json (newest date first)
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_ROOT = REPO_ROOT / "reports"
MAX_LOCAL_VIDEO_BYTES = 25 * 1024 * 1024


def read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def ensure_parent(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)


def copy_if_present(src: str | None, dest: Path) -> str | None:
    if not src:
        return None
    src_path = Path(src)
    if not src_path.exists():
        raise FileNotFoundError(f"Missing source file: {src_path}")
    ensure_parent(dest)
    shutil.copy2(src_path, dest)
    return dest.name


def should_publish_local_video(src: str | None, youtube_url: str | None) -> bool:
    if not src:
        return False
    if youtube_url:
        return False
    src_path = Path(src)
    if not src_path.exists():
        raise FileNotFoundError(f"Missing source file: {src_path}")
    return src_path.stat().st_size <= MAX_LOCAL_VIDEO_BYTES


def append_video_section(markdown_text: str, rel_video: str | None, youtube_url: str | None) -> str:
    parts = [markdown_text.rstrip(), ""]
    if rel_video or youtube_url:
        parts.append("### 影片報告")
        if rel_video:
            parts.append(f"- 本地影片：[{rel_video}]({rel_video})")
        if youtube_url:
            parts.append(f"- YouTube：{youtube_url}")
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def build_daily_index(manifest: dict, paper_entries: list[dict]) -> dict:
    return {
        "date": manifest["date"],
        "paperCount": len(paper_entries),
        "paperType": manifest.get("paperType", "general"),
        "papers": [
            {
                "id": p["id"],
                "category": p["category"],
                "title": p["title"],
                "path": p["path"],
                "link": p["link"],
                "type": p.get("type", "GENERAL PAPER"),
                **({"youtubeUrl": p["youtubeUrl"]} if p.get("youtubeUrl") else {}),
                **({"videoPath": p["videoPath"]} if p.get("videoPath") else {}),
            }
            for p in paper_entries
        ],
        "notebookLM": manifest.get("notebookLM", {}),
        "generatedAt": manifest.get("generatedAt"),
    }


def update_global_index(manifest: dict, paper_entries: list[dict]):
    index_path = REPORTS_ROOT / "index.json"
    global_index = read_json(index_path, {"lastUpdated": manifest["date"], "dates": []})

    summary_entry = {
        "date": manifest["date"],
        "path": f"{manifest['date']}/index.json",
        "paperCount": len(paper_entries),
        "paperType": manifest.get("paperType", "general"),
        "papers": [
            {
                "title": p["title"],
                "tags": p.get("tags", []),
            }
            for p in paper_entries
        ],
    }

    filtered = [d for d in global_index.get("dates", []) if d.get("date") != manifest["date"]]
    filtered.insert(0, summary_entry)
    global_index["lastUpdated"] = manifest["date"]
    global_index["dates"] = filtered
    write_json(index_path, global_index)


def publish_manifest(manifest_path: Path):
    manifest = json.loads(manifest_path.read_text())
    date = manifest["date"]
    daily_dir = REPORTS_ROOT / date
    figures_dir = daily_dir / "figures"
    videos_dir = daily_dir / "videos"
    logs_dir = daily_dir / "logs"
    daily_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    videos_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    paper_entries = []
    for idx, paper in enumerate(manifest.get("papers", []), start=1):
        paper_id = paper.get("id") or f"paper-{idx}"
        slug = paper.get("slug") or paper_id
        md_filename = f"{slug}.md"
        md_dest = daily_dir / md_filename

        md_src = Path(paper["markdown_source"])
        md_text = md_src.read_text()

        rel_video_name = None
        if should_publish_local_video(paper.get("video_file"), paper.get("youtube_url")):
            rel_video_name = copy_if_present(paper.get("video_file"), videos_dir / f"{paper_id}.mp4")
            if rel_video_name:
                rel_video_name = f"videos/{rel_video_name}"

        rel_figure_name = None
        if paper.get("figure_file"):
            rel_figure_name = copy_if_present(paper.get("figure_file"), figures_dir / f"{paper_id}{Path(paper['figure_file']).suffix}")
            if rel_figure_name:
                rel_figure_name = f"figures/{rel_figure_name}"

        final_md = append_video_section(md_text, rel_video_name, paper.get("youtube_url"))
        md_dest.write_text(final_md)

        entry = {
            "id": paper_id,
            "category": paper["category"],
            "title": paper["title"],
            "path": md_filename,
            "link": paper["link"],
            "type": paper.get("type", "GENERAL PAPER"),
            "tags": paper.get("tags", []),
            "youtubeUrl": paper.get("youtube_url"),
            "videoPath": rel_video_name,
            "figurePath": rel_figure_name,
        }
        paper_entries.append(entry)

    daily_index = build_daily_index(manifest, paper_entries)
    write_json(daily_dir / "index.json", daily_index)
    update_global_index(manifest, paper_entries)
    return {
        "date": date,
        "daily_dir": str(daily_dir),
        "paper_count": len(paper_entries),
        "daily_index": str(daily_dir / 'index.json'),
        "global_index": str(REPORTS_ROOT / 'index.json'),
    }


def main():
    if len(sys.argv) != 2:
        print("Usage: publish_notebooklm_batch.py /path/to/manifest.json", file=sys.stderr)
        sys.exit(1)
    manifest_path = Path(sys.argv[1])
    if not manifest_path.exists():
        print(f"Manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)
    result = publish_manifest(manifest_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
