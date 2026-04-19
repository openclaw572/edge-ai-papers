#!/usr/bin/env python3
"""Upload one or more NotebookLM-generated videos to YouTube.

Supports two modes:
1. Single upload via --video-file + metadata flags
2. Batch upload via --manifest JSON used by publish_notebooklm_batch.py

The script reuses Hermes' Google OAuth token at ~/.hermes/google_token.json.
Default privacy is UNLISTED for safety.

Examples:
  python scripts/upload_youtube_batch.py --channel-info

  python scripts/upload_youtube_batch.py \
    --video-file /tmp/video.mp4 \
    --title "Edge AI paper summary" \
    --description-file /tmp/desc.txt \
    --privacy-status unlisted

  python scripts/upload_youtube_batch.py \
    --manifest /tmp/batch.json \
    --dry-run

  python scripts/upload_youtube_batch.py \
    --manifest /tmp/batch.json \
    --privacy-status unlisted \
    --write-back
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import sys
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]
TOKEN_PATH = Path.home() / ".hermes" / "google_token.json"
DEFAULT_CATEGORY_ID = "28"  # Science & Technology


def load_credentials(token_path: Path = TOKEN_PATH) -> Credentials:
    if not token_path.exists():
        raise FileNotFoundError(
            f"Google OAuth token not found: {token_path}. Run google-workspace setup first."
        )
    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json())
    return creds


def youtube_service():
    creds = load_credentials()
    return build("youtube", "v3", credentials=creds)


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", text)
    return text.strip("-") or "video"


def load_text_file(path: str | None) -> str | None:
    if not path:
        return None
    p = Path(path)
    return p.read_text(encoding="utf-8")


def trim(s: str, limit: int) -> str:
    s = s.strip()
    return s if len(s) <= limit else s[: limit - 1].rstrip() + "…"


def infer_tags(paper: dict[str, Any]) -> list[str]:
    tags = []
    for key in ("category", "source", "year"):
        val = paper.get(key)
        if isinstance(val, str) and val.strip():
            tags.append(val.strip())
    for tag in paper.get("tags", []) or []:
        if isinstance(tag, str) and tag.strip():
            tags.append(tag.strip())
    tags.extend(["NotebookLM", "論文解讀", "Edge AI"])

    seen = set()
    result = []
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            result.append(tag)
    return result[:15]


def build_title(paper: dict[str, Any]) -> str:
    if paper.get("youtube_title"):
        return trim(str(paper["youtube_title"]), 100)

    category = paper.get("category", "Paper")
    year = paper.get("year")
    title = paper.get("title", "Untitled")
    prefix = f"[{category}] "
    suffix = f" ({year})" if year else ""
    return trim(f"{prefix}{title}{suffix}｜NotebookLM 影片摘要", 100)


def build_description(paper: dict[str, Any]) -> str:
    if paper.get("youtube_description"):
        return str(paper["youtube_description"]).strip()

    lines = []
    lines.append("這支影片由 NotebookLM 協助生成，內容為論文重點的繁體中文摘要與解說。")
    lines.append("")
    lines.append(f"論文標題：{paper.get('title', '')}")
    if paper.get("authors"):
        lines.append(f"作者：{paper['authors']}")
    if paper.get("year"):
        lines.append(f"年份：{paper['year']}")
    if paper.get("source"):
        lines.append(f"來源：{paper['source']}")
    if paper.get("type"):
        lines.append(f"類型：{paper['type']}")
    if paper.get("link"):
        lines.append(f"原文連結：{paper['link']}")
    lines.append("")
    lines.append("這是 edge-ai-papers 自動化 pipeline 的輸出之一。")
    return trim("\n".join(lines).strip(), 5000)


def validate_video_file(path: str) -> Path:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Video file not found: {p}")
    if not p.is_file():
        raise ValueError(f"Not a file: {p}")
    return p


def list_my_channel(youtube) -> dict[str, Any]:
    response = (
        youtube.channels()
        .list(part="snippet,statistics,status", mine=True)
        .execute()
    )
    items = response.get("items", [])
    if not items:
        return {"authenticated": True, "channel": None}
    item = items[0]
    return {
        "authenticated": True,
        "channel": {
            "id": item.get("id"),
            "title": item.get("snippet", {}).get("title"),
            "customUrl": item.get("snippet", {}).get("customUrl"),
            "privacyStatus": item.get("status", {}).get("privacyStatus"),
            "subscriberCount": item.get("statistics", {}).get("subscriberCount"),
            "videoCount": item.get("statistics", {}).get("videoCount"),
        },
    }


def upload_video(
    youtube,
    *,
    video_file: str,
    title: str,
    description: str,
    privacy_status: str,
    category_id: str,
    tags: list[str] | None = None,
    playlist_id: str | None = None,
    thumbnail_file: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    video_path = validate_video_file(video_file)
    mime_type = mimetypes.guess_type(str(video_path))[0] or "video/mp4"

    payload = {
        "snippet": {
            "title": trim(title, 100),
            "description": trim(description, 5000),
            "tags": tags or [],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }

    if dry_run:
        return {
            "dryRun": True,
            "video_file": str(video_path),
            "payload": payload,
            "playlist_id": playlist_id,
            "thumbnail_file": thumbnail_file,
        }

    insert_request = youtube.videos().insert(
        part="snippet,status",
        body=payload,
        media_body=MediaFileUpload(str(video_path), mimetype=mime_type, resumable=True),
    )

    response = None
    while response is None:
        _status, response = insert_request.next_chunk()

    video_id = response["id"]
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    thumbnail_warning = None

    if thumbnail_file:
        thumb_path = Path(thumbnail_file)
        if thumb_path.exists() and thumb_path.is_file():
            try:
                youtube.thumbnails().set(videoId=video_id, media_body=str(thumb_path)).execute()
            except HttpError as exc:
                thumbnail_warning = {
                    "error": "thumbnail_set_failed",
                    "status": getattr(exc, "status_code", None),
                    "detail": exc.content.decode("utf-8", errors="ignore") if getattr(exc, "content", None) else str(exc),
                }
        
    if playlist_id:
        youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {"kind": "youtube#video", "videoId": video_id},
                }
            },
        ).execute()

    return {
        "videoId": video_id,
        "url": video_url,
        "title": payload["snippet"]["title"],
        "privacyStatus": privacy_status,
        **({"thumbnailWarning": thumbnail_warning} if thumbnail_warning else {}),
    }


def upload_manifest(
    youtube,
    manifest: dict[str, Any],
    *,
    privacy_status: str,
    category_id: str,
    playlist_id: str | None,
    dry_run: bool,
) -> dict[str, Any]:
    results = []
    for paper in manifest.get("papers", []):
        video_file = paper.get("video_file")
        if not video_file:
            results.append(
                {
                    "paperId": paper.get("id"),
                    "skipped": True,
                    "reason": "missing video_file",
                }
            )
            continue

        result = upload_video(
            youtube,
            video_file=video_file,
            title=build_title(paper),
            description=build_description(paper),
            privacy_status=paper.get("privacy_status", privacy_status),
            category_id=str(paper.get("youtube_category_id", category_id)),
            tags=paper.get("youtube_tags") or infer_tags(paper),
            playlist_id=paper.get("playlist_id", playlist_id),
            thumbnail_file=paper.get("figure_file"),
            dry_run=dry_run,
        )

        if not dry_run and result.get("url"):
            paper["youtube_url"] = result["url"]
            paper["youtube_video_id"] = result["videoId"]
            paper["youtube_title"] = result["title"]
            paper["privacy_status"] = result["privacyStatus"]

        results.append({"paperId": paper.get("id"), **result})

    return {"manifest": manifest, "results": results}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload NotebookLM videos to YouTube")
    parser.add_argument("--manifest", help="Path to batch manifest JSON")
    parser.add_argument("--write-back", action="store_true", help="Write updated manifest back in place")
    parser.add_argument("--output-manifest", help="Write updated manifest to another path")
    parser.add_argument("--channel-info", action="store_true", help="Show authenticated YouTube channel info and exit")
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs and print intended upload payloads without uploading")
    parser.add_argument("--privacy-status", default="unlisted", choices=["private", "unlisted", "public"])
    parser.add_argument("--category-id", default=DEFAULT_CATEGORY_ID)
    parser.add_argument("--playlist-id")

    parser.add_argument("--video-file")
    parser.add_argument("--title")
    parser.add_argument("--description")
    parser.add_argument("--description-file")
    parser.add_argument("--tags", nargs="*")
    parser.add_argument("--thumbnail-file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    youtube = youtube_service()

    if args.channel_info:
        print(json.dumps(list_my_channel(youtube), ensure_ascii=False, indent=2))
        return 0

    try:
        if args.manifest:
            manifest_path = Path(args.manifest)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            result = upload_manifest(
                youtube,
                manifest,
                privacy_status=args.privacy_status,
                category_id=args.category_id,
                playlist_id=args.playlist_id,
                dry_run=args.dry_run,
            )
            if not args.dry_run:
                if args.write_back:
                    manifest_path.write_text(json.dumps(result["manifest"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                if args.output_manifest:
                    Path(args.output_manifest).write_text(
                        json.dumps(result["manifest"], ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8",
                    )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0

        if not args.video_file or not args.title:
            raise SystemExit("Single-upload mode requires --video-file and --title")

        description = args.description or load_text_file(args.description_file) or ""
        result = upload_video(
            youtube,
            video_file=args.video_file,
            title=args.title,
            description=description,
            privacy_status=args.privacy_status,
            category_id=args.category_id,
            tags=args.tags,
            thumbnail_file=args.thumbnail_file,
            playlist_id=args.playlist_id,
            dry_run=args.dry_run,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except HttpError as exc:
        detail = exc.content.decode("utf-8", errors="ignore") if getattr(exc, "content", None) else str(exc)
        print(json.dumps({"error": "HttpError", "status": getattr(exc, "status_code", None), "detail": detail}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    except Exception as exc:
        print(json.dumps({"error": type(exc).__name__, "detail": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
