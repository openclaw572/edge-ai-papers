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
import unicodedata
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


def display_width(text: str) -> int:
    """Approximate rendered width in monospace/CJK cells for safe ffmpeg wrapping."""
    width = 0
    for ch in text:
        width += 2 if unicodedata.east_asian_width(ch) in {"F", "W"} else 1
    return width


def wrap_display_line(text: str, width: int = 36) -> list[str]:
    """Wrap text to a conservative visual cell width so drawtext stays inside the frame."""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return [""]
    lines: list[str] = []
    current = ""
    current_width = 0
    for ch in text:
        ch_width = 2 if unicodedata.east_asian_width(ch) in {"F", "W"} else 1
        if current and current_width + ch_width > width:
            # Prefer breaking English titles at the last space; CJK text usually has no spaces
            # and can wrap safely at character boundaries.
            space_at = current.rfind(" ")
            if space_at > 0 and display_width(current[:space_at]) >= width * 0.55:
                lines.append(current[:space_at].rstrip())
                current = current[space_at + 1:] + ch
                current_width = display_width(current)
            else:
                lines.append(current.rstrip())
                current = ch
                current_width = ch_width
        else:
            current += ch
            current_width += ch_width
    if current.strip():
        lines.append(current.rstrip())
    return lines or [""]


def clamp_lines(lines: list[str], max_lines: int) -> list[str]:
    if len(lines) <= max_lines:
        return lines
    clipped = lines[:max_lines]
    clipped[-1] = clipped[-1].rstrip("。,.，") + "…"
    return clipped


def fit_slide_text(lines: list[str], *, width: int = 34, max_lines: int = 10) -> str:
    """Normalize a slide into a safe text block that fits the decorative frame."""
    fitted: list[str] = []
    for raw in lines:
        for wrapped in wrap_display_line(raw, width=width):
            if len(fitted) >= max_lines:
                break
            fitted.append(wrapped)
        if len(fitted) >= max_lines:
            break
    if len(fitted) == max_lines and lines:
        fitted[-1] = fitted[-1].rstrip("。,.，") + "…"
    return "\n".join(fitted)


def make_slide_texts(source_text: str, title: str, category: str, source_kind: str, max_slides: int = 6) -> list[str]:
    headings = [h.strip(" #") for h in re.findall(r"^#{1,3}\s+(.+)$", source_text, flags=re.M)]
    sentences = split_sentences(source_text)
    source_label = "論文全文" if source_kind == "full_paper_pdf" else "Markdown 報告"
    title_lines = clamp_lines(wrap_display_line(title, width=32), 4)
    slides = [fit_slide_text([
        "AI Research Lens",
        category,
        *title_lines,
        "研究導讀｜重點摘要",
        f"來源：{source_label}",
    ], width=32, max_lines=9)]
    important = []
    for heading in headings:
        if 4 <= len(heading) <= 40 and heading not in important:
            important.append(heading)
    for sentence in sentences:
        if len(important) >= (max_slides - 1) * 2:
            break
        if 20 <= len(sentence) <= 90 and sentence not in important:
            important.append(sentence)
    for i in range(0, len(important), 2):
        bullets = important[i:i + 2]
        if not bullets:
            continue
        lines = ["Research Signal", "重點摘要"]
        for bullet in bullets:
            wrapped = wrap_display_line(bullet, 30)
            lines.append("• " + wrapped[0])
            lines.extend("  " + x for x in wrapped[1:3])
        slides.append(fit_slide_text(lines, width=34, max_lines=10))
        if len(slides) >= max_slides:
            break
    if len(slides) == 1:
        slides.append(fit_slide_text([
            "Research Signal",
            "本報告已產生 Markdown 內容。",
            "此影片整理核心問題、方法線索與應用情境。",
        ], width=34, max_lines=8))
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
    palettes = [
        ("0x07111F", "0x38BDF8", "0x0EA5E9"),
        ("0x111827", "0xA78BFA", "0x7C3AED"),
        ("0x101820", "0x34D399", "0x059669"),
        ("0x1F172A", "0xF472B6", "0xDB2777"),
        ("0x172033", "0xFBBF24", "0xD97706"),
        ("0x0F172A", "0x67E8F9", "0x0891B2"),
    ]
    for idx, slide in enumerate(slides):
        text_file = work / f"slide_{idx:02d}.txt"
        safe_slide = fit_slide_text(slide.splitlines(), width=32 if idx == 0 else 34, max_lines=9 if idx == 0 else 10)
        text_file.write_text(safe_slide, encoding="utf-8")
        bg, accent, accent_dark = palettes[idx % len(palettes)]
        font_size = 34 if idx == 0 else 32
        filter_parts.append(
            f"color=c={bg}:s=1280x720:d={per_slide:.3f}[base{idx}];"
            f"[base{idx}]"
            # Outer safety frame and translucent content card.
            f"drawbox=x=56:y=52:w=1168:h=616:color={accent}@0.95:t=3,"
            f"drawbox=x=82:y=84:w=1116:h=552:color=0x020617@0.34:t=fill,"
            # Research-dashboard accents: signal rail, corner ticks, and abstract bars.
            f"drawbox=x=96:y=108:w=10:h=504:color={accent}:t=fill,"
            f"drawbox=x=112:y=108:w=190:h=4:color={accent}:t=fill,"
            f"drawbox=x=112:y=608:w=250:h=4:color={accent_dark}:t=fill,"
            f"drawbox=x=928:y=112:w=184:h=4:color={accent}@0.72:t=fill,"
            f"drawbox=x=1060:y=120:w=52:h=52:color={accent_dark}@0.38:t=fill,"
            f"drawbox=x=1028:y=188:w=84:h=8:color={accent}@0.42:t=fill,"
            f"drawbox=x=984:y=212:w=128:h=8:color={accent}@0.28:t=fill,"
            f"drawbox=x=940:y=236:w=172:h=8:color={accent}@0.18:t=fill,"
            f"drawtext=fontfile='{escape_filter_path(Path(font))}':"
            f"textfile='{escape_filter_path(text_file)}':fontcolor=0xF8FAFC:fontsize={font_size}:"
            f"line_spacing=13:x=max(120\\,(w-text_w)/2):y=(h-text_h)/2,"
            f"drawtext=fontfile='{escape_filter_path(Path(font))}':text='edge-ai-papers · research digest':"
            f"fontcolor=0xCBD5E1:fontsize=20:x=96:y=h-th-74,"
            f"drawtext=fontfile='{escape_filter_path(Path(font))}':text='safe-frame layout':"
            f"fontcolor={accent}:fontsize=18:x=w-tw-96:y=h-th-74,format=yuv420p[v{idx}]"
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
