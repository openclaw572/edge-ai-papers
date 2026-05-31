from __future__ import annotations

import concurrent.futures
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

from .report_generation import CommandResult, run_openclaw_webbridge

OpenClawRunner = Callable[[str, int | float | None], CommandResult]

YOUTUBE_URL_RE = re.compile(r"https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[A-Za-z0-9_-]+")


@dataclass(slots=True)
class YouTubeUploadResult:
    paper_title: str
    video_path: str
    ok: bool
    youtube_url: str = ""
    thumbnail_path: str = ""
    raw_response: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _artifact_video_path(artifact: dict) -> str:
    return str(artifact.get("video_path") or artifact.get("local_video") or "")


def _artifact_title(artifact: dict) -> str:
    return str(artifact.get("paper_title") or artifact.get("title") or "Untitled Paper")


def parse_youtube_url(text: str) -> str:
    match = YOUTUBE_URL_RE.search(text or "")
    return match.group(0) if match else ""


def _parse_openclaw_response(text: str) -> tuple[str, str, str]:
    """Return (youtube_url, thumbnail_path, error). Accepts JSON or plain visible text."""
    if not text:
        return "", "", "OpenClaw did not return any output"
    stripped = text.strip()
    try:
        data = json.loads(stripped)
        thumbnail_path = str(data.get("thumbnail_path") or data.get("thumbnailPath") or data.get("custom_thumbnail") or "")
        candidates = [
            data.get("youtube_url"),
            data.get("youtubeUrl"),
            data.get("url"),
            data.get("video_url"),
            data.get("watch_url"),
            data.get("finalAssistantVisibleText"),
            data.get("message"),
        ]
        for candidate in candidates:
            if isinstance(candidate, str):
                url = parse_youtube_url(candidate)
                if url:
                    return url, thumbnail_path, ""
        # OpenClaw CLI often wraps visible text in nested result fields.
        serialized = json.dumps(data, ensure_ascii=False)
        url = parse_youtube_url(serialized)
        if url:
            return url, thumbnail_path, ""
        if data.get("success") is False or data.get("ok") is False:
            return "", thumbnail_path, str(data.get("error") or data.get("reason") or "OpenClaw reported failure")
    except json.JSONDecodeError:
        pass
    url = parse_youtube_url(stripped)
    if url:
        return url, "", ""
    return "", "", "No YouTube URL found in OpenClaw response"


class OpenClawYouTubeUploader:
    def __init__(
        self,
        *,
        runner: OpenClawRunner = run_openclaw_webbridge,
        privacy_status: str = "unlisted",
        max_workers: int = 2,
        timeout_seconds: int = 3600,
    ):
        self.runner = runner
        self.privacy_status = privacy_status
        self.max_workers = max(1, max_workers)
        self.timeout_seconds = timeout_seconds

    def upload_artifacts(self, manifest_path: str | Path, *, write_back: bool = True) -> list[YouTubeUploadResult]:
        manifest_file = Path(manifest_path)
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        artifacts = list(manifest.get("artifacts") or [])
        results: list[YouTubeUploadResult] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.upload_one, artifact): idx for idx, artifact in enumerate(artifacts)}
            for future in concurrent.futures.as_completed(futures):
                idx = futures[future]
                result = future.result()
                results.append(result)
                artifacts[idx]["youtube_upload"] = result.to_dict()
                if result.thumbnail_path:
                    artifacts[idx]["youtube_thumbnail_path"] = result.thumbnail_path
                if result.ok:
                    artifacts[idx]["youtube_url"] = result.youtube_url
                    self._patch_markdown_youtube_url(artifacts[idx], result.youtube_url)
        results.sort(key=lambda item: next((i for i, artifact in enumerate(artifacts) if _artifact_title(artifact) == item.paper_title), 999))
        manifest["artifacts"] = artifacts
        manifest["youtube_uploads"] = [item.to_dict() for item in results]
        if write_back:
            manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return results

    def upload_one(self, artifact: dict) -> YouTubeUploadResult:
        title = _artifact_title(artifact)
        video_path = _artifact_video_path(artifact)
        if not video_path:
            return YouTubeUploadResult(title, video_path, False, error="artifact has no video_path")
        video = Path(video_path)
        if not video.exists():
            return YouTubeUploadResult(title, video_path, False, error=f"video file does not exist: {video}")
        prompt = self._build_prompt(artifact, video)
        result = self.runner(prompt, self.timeout_seconds)
        raw = result.combined_output
        if not result.ok:
            return YouTubeUploadResult(title, str(video), False, raw_response=raw, error=f"OpenClaw CLI failed: {raw[:500]}")
        youtube_url, thumbnail_path, parse_error = _parse_openclaw_response(raw)
        if not youtube_url:
            return YouTubeUploadResult(title, str(video), False, thumbnail_path=thumbnail_path, raw_response=raw, error=parse_error)
        return YouTubeUploadResult(title, str(video), True, youtube_url=youtube_url, thumbnail_path=thumbnail_path, raw_response=raw)

    def _build_prompt(self, artifact: dict, video: Path) -> str:
        title = _artifact_title(artifact)
        markdown_path = artifact.get("markdown_path") or artifact.get("local_markdown") or ""
        thumbnail_path = video.with_name("youtube_thumbnail.png")
        description_bits = [
            "繁體中文論文影片報告。",
            f"論文：{title}",
        ]
        if markdown_path:
            description_bits.append(f"文字報告：{markdown_path}")
        return (
            "請使用 webbridge 操作已登入的瀏覽器，把指定影片上傳到 YouTube Studio。"
            "如果 OpenClaw 支援安全的 subagent/parallel worker，可自行使用，但不要同時操作同一個瀏覽器對話框造成衝突。"
            "不要要求或處理 Google 密碼；若需要登入、2FA、頻道選擇或人工確認，請停止並回報 blocker。"
            f"影片路徑：{video}\n"
            f"封面圖輸出路徑：{thumbnail_path}\n"
            f"標題：{title}\n"
            f"描述：{' '.join(description_bits)}\n"
            f"可見性：{self.privacy_status}\n"
            "上傳前請先使用 image2.0 生成一張適合該論文主題的 YouTube 封面圖，風格應專業、清楚、適合技術/論文介紹，不要出現不存在的作者照片或誤導性標誌。"
            f"請將 image2.0 生成的封面存成：{thumbnail_path}，並在 YouTube Studio 上傳影片時把 custom thumbnail 換成這張圖。"
            "若 YouTube Studio 因頻道未驗證或 UI 限制無法設定自訂縮圖，請停止並回報 blocker，不要假裝已成功設定。"
            "Audience 請選擇 not made for kids（除非 YouTube UI 要求其他合法選項）。"
            "上傳完成後請回傳 JSON，至少包含 success、youtube_url 與 thumbnail_path；若失敗請包含 error。"
        )

    @staticmethod
    def _patch_markdown_youtube_url(artifact: dict, youtube_url: str) -> None:
        markdown_path = artifact.get("markdown_path") or artifact.get("local_markdown")
        if not markdown_path:
            return
        path = Path(markdown_path)
        if not path.exists():
            return
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"YouTube:\s*(待上傳|https?://\S+)", f"YouTube: {youtube_url}", text)
        text = re.sub(r"youtube_url:\s*(待上傳|null|https?://\S+)", f"youtube_url: {youtube_url}", text)
        if "## 影片連結" not in text:
            text += f"\n\n## 影片連結\n\n- YouTube: {youtube_url}\n"
        elif youtube_url not in text:
            text += f"\n- YouTube: {youtube_url}\n"
        path.write_text(text, encoding="utf-8")
