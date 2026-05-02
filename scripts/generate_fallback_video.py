#!/usr/bin/env python3
"""Generate a fallback MP4 video from paper text, falling back to markdown.

This is used when NotebookLM creates a video artifact but the Google-hosted
MP4/HLS/DASH URLs cannot be downloaded (for example rd-notebooklm 404s).
The preferred source is the full paper PDF text; if the PDF cannot be read or
looks incomplete, the script falls back to the generated markdown report.
The generated video is intentionally simple but valid for YouTube upload:
Traditional-Chinese narration from Edge TTS + slide-style text rendered by
ffmpeg with a CJK font.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import re
import shutil
import subprocess
import textwrap
from pathlib import Path

try:
    import edge_tts
except ImportError as exc:  # pragma: no cover - runtime environment check
    raise SystemExit("edge_tts is required for fallback video generation") from exc

try:
    from deep_translator import GoogleTranslator
except ImportError:  # pragma: no cover - optional quality improvement
    GoogleTranslator = None

DEFAULT_VOICE = "zh-TW-HsiaoChenNeural"
DEFAULT_FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"


def run(cmd: list[str], *, timeout: int = 600) -> subprocess.CompletedProcess:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(cmd)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def strip_markdown(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"^[#>*\-+\s]+", "", text, flags=re.M)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"[_*]{1,3}", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    text = strip_markdown(text)
    pieces = re.split(r"(?<=[。！？!?.;])\s*|\n+", text)
    out = []
    for piece in pieces:
        piece = re.sub(r"\s+", " ", piece).strip()
        if len(piece) >= 12:
            out.append(piece)
    return out


def extract_pdf_text(pdf_path: Path) -> str:
    if not pdf_path.exists() or not shutil.which("pdftotext"):
        return ""
    result = subprocess.run(["pdftotext", "-layout", str(pdf_path), "-"], capture_output=True, text=True, timeout=180)
    if result.returncode != 0:
        return ""
    text = re.sub(r"\f", "\n", result.stdout)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def usable_full_paper_text(text: str) -> bool:
    lowered = text.lower()
    return len(text) >= 3000 and any(k in lowered for k in ["abstract", "introduction", "references"])


def pick_full_paper_snippets(text: str, max_chars: int) -> str:
    sections = []
    patterns = [
        ("摘要", r"(?is)\babstract\b[:\s]*(.{300,1800}?)(?=\n\s*(?:keywords|index terms|1\.?\s*introduction|introduction)\b)"),
        ("研究動機與問題", r"(?is)(?:^|\n)\s*(?:1\.?\s*)?introduction\b[:\s]*(.{500,2200}?)(?=\n\s*(?:2\.?|related work|background|method|approach)\b)"),
        ("結論與限制", r"(?is)(?:^|\n)\s*(?:conclusion|conclusions|discussion)\b[:\s]*(.{400,1800}?)(?=\n\s*(?:references|acknowledg|appendix)\b)"),
    ]
    for label, pattern in patterns:
        m = re.search(pattern, text)
        if m:
            snippet = re.sub(r"\s+", " ", m.group(1)).strip()
            sections.append(f"{label}：{snippet}")
    if not sections:
        sentences = split_sentences(text)[:18]
        sections = sentences
    raw = "\n".join(sections)[:max_chars]
    return raw


def maybe_translate_to_zh_tw(text: str) -> str:
    # If the selected source is mostly English, translate the compact snippet for narration/slides.
    ascii_letters = sum(ch.isascii() and ch.isalpha() for ch in text)
    cjk = sum("\u4e00" <= ch <= "\u9fff" for ch in text)
    if GoogleTranslator is None or ascii_letters < max(80, cjk * 2):
        return text
    chunks = textwrap.wrap(text, width=1200, break_long_words=False, replace_whitespace=False)[:3]
    translated = []
    try:
        translator = GoogleTranslator(source="auto", target="zh-TW")
        for chunk in chunks:
            translated.append(translator.translate(chunk))
        return "\n".join(x for x in translated if x).strip() or text
    except Exception:
        return text


def load_preferred_source(markdown_path: Path, paper_pdf: Path | None, max_chars: int) -> tuple[str, str]:
    if paper_pdf:
        pdf_text = extract_pdf_text(paper_pdf)
        if usable_full_paper_text(pdf_text):
            snippets = pick_full_paper_snippets(pdf_text, max_chars=max_chars * 2)
            return maybe_translate_to_zh_tw(snippets), "full_paper_pdf"
    return markdown_path.read_text(encoding="utf-8"), "markdown_report"


def build_narration(source_text: str, title: str, category: str, max_chars: int, source_kind: str) -> str:
    sentences = split_sentences(source_text)
    source_label = "論文全文" if source_kind == "full_paper_pdf" else "已生成的 Markdown 報告"
    lead = [
        f"本影片是 {category} 論文的備援影片摘要。",
        f"論文標題是：{title}。",
        f"以下內容優先根據{source_label}整理研究動機、方法、主要結果、限制與應用場景。",
    ]
    body: list[str] = []
    current = sum(len(x) for x in lead)
    for sentence in sentences:
        # Skip generated metadata lines that sound awkward as narration.
        if any(k in sentence for k in ["YouTube", "影片報告", "報告語言", "類別：", "來源：", "作者："]):
            continue
        if current + len(sentence) + 1 > max_chars:
            break
        body.append(sentence)
        current += len(sentence) + 1
    closing = "以上是本篇論文的自動備援影片摘要。詳細內容請參考同頁的 Markdown 報告。"
    if current + len(closing) + 1 <= max_chars:
        body.append(closing)
    return "\n".join(lead + body).strip() + "\n"


def wrap_display_line(text: str, width: int = 28) -> list[str]:
    # textwrap is byte/character based; for CJK this gives acceptable slide lines.
    return textwrap.wrap(text, width=width, break_long_words=True, replace_whitespace=False) or [""]


def make_slide_texts(source_text: str, title: str, category: str, source_kind: str, max_slides: int = 6) -> list[str]:
    headings = [h.strip(" #") for h in re.findall(r"^#{1,3}\s+(.+)$", source_text, flags=re.M)]
    sentences = split_sentences(source_text)
    source_label = "論文全文" if source_kind == "full_paper_pdf" else "Markdown 報告"
    slides = [f"{category}\n{title}\n\nNotebookLM 影片下載失敗時的自動備援影片\n來源：{source_label}"]
    important = []
    for heading in headings:
        if 4 <= len(heading) <= 40 and heading not in important:
            important.append(heading)
    for sentence in sentences:
        if len(important) >= (max_slides - 1) * 2:
            break
        if 20 <= len(sentence) <= 80 and sentence not in important:
            important.append(sentence)
    for i in range(0, len(important), 2):
        bullets = important[i:i + 2]
        if not bullets:
            continue
        lines = ["重點摘要"]
        for bullet in bullets:
            wrapped = wrap_display_line(bullet, 26)
            lines.append("• " + wrapped[0])
            lines.extend("  " + x for x in wrapped[1:3])
        slides.append("\n".join(lines))
        if len(slides) >= max_slides:
            break
    if len(slides) == 1:
        slides.append("本報告已產生 Markdown 內容。\n此影片提供可上傳 YouTube 的自動備援版本。")
    return slides


async def synthesize_tts(text: str, output: Path, voice: str) -> None:
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output))


def ffprobe_duration(path: Path) -> float:
    result = run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ], timeout=120)
    return float(result.stdout.strip())


def escape_filter_path(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def render_video(audio: Path, slides: list[str], output: Path, font: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    duration = max(ffprobe_duration(audio), 1.0)
    per_slide = max(duration / len(slides), 3.0)
    work = output.parent / "fallback_video_assets"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    filter_parts: list[str] = []
    concat_inputs: list[str] = []
    for idx, slide in enumerate(slides):
        text_file = work / f"slide_{idx:02d}.txt"
        text_file.write_text(slide, encoding="utf-8")
        # Slight color variation to make slide cuts visible.
        color = "0x111827" if idx % 2 == 0 else "0x172033"
        filter_parts.append(
            f"color=c={color}:s=1280x720:d={per_slide:.3f}[base{idx}];"
            f"[base{idx}]drawtext=fontfile='{escape_filter_path(Path(font))}':"
            f"textfile='{escape_filter_path(text_file)}':fontcolor=white:fontsize=34:"
            f"line_spacing=12:x=(w-text_w)/2:y=(h-text_h)/2,"
            f"drawtext=fontfile='{escape_filter_path(Path(font))}':text='edge-ai-papers fallback video':"
            f"fontcolor=0x9CA3AF:fontsize=20:x=w-tw-32:y=h-th-24,format=yuv420p[v{idx}]"
        )
        concat_inputs.append(f"[v{idx}]")
    filter_complex = ";".join(filter_parts) + ";" + "".join(concat_inputs) + f"concat=n={len(slides)}:v=1:a=0[v]"
    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(audio),
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "0:a:0",
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest", "-movflags", "+faststart", str(output),
    ], timeout=900)


def validate_mp4(path: Path) -> dict[str, object]:
    if not path.exists() or path.stat().st_size < 10_000:
        raise RuntimeError(f"Fallback video missing or too small: {path}")
    head = path.read_bytes()[:16]
    if head[4:8] != b"ftyp":
        raise RuntimeError(f"Fallback video is not an MP4 file: head={head!r}")
    duration = ffprobe_duration(path)
    if duration < 2:
        raise RuntimeError(f"Fallback video duration too short: {duration}")
    return {"path": str(path), "size": path.stat().st_size, "duration": duration, "head_hex": head.hex()}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a narrated fallback MP4 from paper text, falling back to markdown")
    parser.add_argument("--markdown", required=True, type=Path, help="Generated markdown report used if full paper text is unavailable")
    parser.add_argument("--paper-pdf", type=Path, default=None, help="Preferred full paper PDF source for fallback narration/slides")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--category", default="Edge AI")
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--max-chars", type=int, default=1800)
    parser.add_argument("--font", default=DEFAULT_FONT)
    args = parser.parse_args()

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise SystemExit("ffmpeg and ffprobe are required")
    if not Path(args.font).exists():
        raise SystemExit(f"CJK font not found: {args.font}")
    source_text, source_kind = load_preferred_source(args.markdown, args.paper_pdf, args.max_chars)
    narration = build_narration(source_text, args.title, args.category, args.max_chars, source_kind)
    slides = make_slide_texts(source_text, args.title, args.category, source_kind)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    audio = args.output.with_suffix(".fallback-tts.mp3")
    narration_path = args.output.with_suffix(".fallback-narration.txt")
    narration_path.write_text(narration, encoding="utf-8")
    asyncio.run(synthesize_tts(narration, audio, args.voice))
    render_video(audio, slides, args.output, args.font)
    result = validate_mp4(args.output)
    result.update({"audio": str(audio), "narration": str(narration_path), "slides": len(slides), "voice": args.voice, "source_kind": source_kind})
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
