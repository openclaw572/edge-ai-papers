from __future__ import annotations

import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from .models import Paper, RankedPaper, SelectionResult

Runner = Callable[[list[str], int | float | None], "CommandResult"]
OpenClawRunner = Callable[[str, int | float | None], "CommandResult"]
NotebookGenerator = Callable[[RankedPaper, int], "GenerationArtifact"]

DEFAULT_LOCAL_VIDEO_MIN_DURATION_SECONDS = 9 * 60


@dataclass(slots=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    @property
    def combined_output(self) -> str:
        return "\n".join(part for part in (self.stdout, self.stderr) if part)


@dataclass(slots=True)
class GenerationAssignment:
    paper: RankedPaper
    index: int
    method: str


@dataclass(slots=True)
class GenerationArtifact:
    paper_title: str
    method: str
    markdown_path: str = ""
    video_path: str = ""
    markdown_status: str = "created"
    video_status: str = "created"
    notebook_id: str = ""
    report_artifact_id: str = ""
    video_artifact_id: str = ""
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class GenerationConfig:
    local_count_floor_half: bool = True
    notebooklm_video_wait_timeout_seconds: int = 30 * 60
    local_video_min_duration_seconds: int = DEFAULT_LOCAL_VIDEO_MIN_DURATION_SECONDS
    max_workers: int = 4
    enable_tts: bool = False


def slugify(value: str, fallback: str = "paper") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return slug[:80] or fallback


def _split_sentences(text: str, *, max_items: int = 4) -> list[str]:
    pieces = re.split(r"(?<=[.!?。！？])\s+", (text or "").strip())
    return [piece.strip() for piece in pieces if piece.strip()][:max_items]


def _drawtext_escape(text: str) -> str:
    # ffmpeg drawtext treats ':', '\'', '\\' and '%' specially.
    return (text or "Paper Report")[:90].replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'").replace("%", "\\%")


def split_generation_methods(papers: list[RankedPaper]) -> list[GenerationAssignment]:
    """Assign floor(n/2) selected papers to local generation, remaining to NotebookLM."""
    local_count = len(papers) // 2
    assignments: list[GenerationAssignment] = []
    for idx, paper in enumerate(papers, start=1):
        method = "local" if idx <= local_count else "notebooklm"
        assignments.append(GenerationAssignment(paper=paper, index=idx, method=method))
    return assignments


def run_command(command: list[str], timeout: int | float | None = None) -> CommandResult:
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        return CommandResult(completed.returncode, completed.stdout, completed.stderr)
    except FileNotFoundError as exc:
        return CommandResult(127, "", str(exc))
    except subprocess.TimeoutExpired as exc:
        return CommandResult(124, exc.stdout or "", exc.stderr or f"timeout after {timeout}s")


def run_openclaw_webbridge(message: str, timeout: int | float | None = None) -> CommandResult:
    return run_command(
        ["openclaw", "agent", "--agent", "main", "--timeout", str(int(timeout or 1800)), "--json", "--message", message],
        timeout=timeout or 1800,
    )


def ranked_paper_from_dict(data: dict) -> RankedPaper:
    paper_data = data.get("paper") or {}
    return RankedPaper(
        paper=Paper.from_dict(paper_data),
        semantic_relevance=float(data.get("semantic_relevance", 0.0)),
        recency_score=float(data.get("recency_score", 0.0)),
        full_text_score=float(data.get("full_text_score", 0.0)),
        citation_signal=float(data.get("citation_signal", 0.0)),
        code_or_project_signal=float(data.get("code_or_project_signal", 0.0)),
        final_score=float(data.get("final_score", 0.0)),
        profile_similarity=float(data.get("profile_similarity", 0.0)),
        seed_similarity=float(data.get("seed_similarity", 0.0)),
        positive_keyword_score=float(data.get("positive_keyword_score", 0.0)),
        negative_keyword_penalty=float(data.get("negative_keyword_penalty", 0.0)),
        final_llm_score=float(data.get("final_llm_score", 0.0)),
    )


def load_selected_papers(result_json_path: str | Path) -> list[RankedPaper]:
    data = json.loads(Path(result_json_path).read_text(encoding="utf-8"))
    return [ranked_paper_from_dict(item) for item in data.get("selected_papers", [])]


class LocalReportGenerator:
    def __init__(
        self,
        output_dir: str | Path,
        *,
        enable_tts: bool = False,
        min_video_duration_seconds: int = DEFAULT_LOCAL_VIDEO_MIN_DURATION_SECONDS,
    ):
        self.output_dir = Path(output_dir)
        self.enable_tts = enable_tts
        self.min_video_duration_seconds = max(8 * 60, int(min_video_duration_seconds))

    def generate(self, ranked: RankedPaper, index: int) -> GenerationArtifact:
        paper = ranked.paper
        paper_dir = self.output_dir / "local" / f"{index:02d}-{slugify(paper.title)}"
        paper_dir.mkdir(parents=True, exist_ok=True)
        markdown_path = paper_dir / "report.md"
        video_path = paper_dir / "video.mp4"
        script_path = paper_dir / "script.txt"
        markdown = self.render_markdown(ranked)
        script = self.render_video_script(ranked)
        markdown_path.write_text(markdown, encoding="utf-8")
        script_path.write_text(script, encoding="utf-8")
        errors = self.create_video(script, video_path, paper_dir)
        return GenerationArtifact(
            paper_title=paper.title,
            method="local",
            markdown_path=str(markdown_path),
            video_path=str(video_path),
            video_status="created" if video_path.exists() else "failed",
            errors=errors,
        )

    def render_markdown(self, ranked: RankedPaper) -> str:
        paper = ranked.paper
        authors = ", ".join(paper.authors) if paper.authors else "未知"
        categories = ", ".join(paper.categories) if paper.categories else "未標示"
        paper_type = (paper.extra or {}).get("paper_type", "review")
        paper_type_label = "回顧／綜述論文" if paper_type == "review" else "一般研究論文"
        title = paper.title or "Untitled"
        link = paper.url or paper.pdf_url or "未提供"
        abstract = paper.abstract or "未提供 abstract。"
        abstract_sentences = _split_sentences(abstract, max_items=5)
        representative_quotes = abstract_sentences[:3] or [abstract]
        method_focus = (
            "這是一篇 review / survey 類型論文，因此閱讀重點應放在作者如何界定研究範圍、如何建立 taxonomy、如何比較不同研究路線，以及最後整理出的挑戰與 future directions。"
            if paper_type == "review"
            else "這是一篇一般研究論文，因此閱讀重點應放在研究問題、核心方法、系統或模型架構、實驗設計、baseline、metrics 與主要結果。"
        )
        lines = [
            f"## {title}",
            "",
            f"**類別：** {categories}  ",
            f"**論文類型：** {paper_type_label}  ",
            f"**來源：** {paper.source or '未知'}  ",
            f"**發表年份：** {paper.year}  ",
            f"**作者：** {authors}  ",
            f"**連結：** {link}  ",
            f"**PDF：** {paper.pdf_url or '未找到'}  ",
            "**報告語言：** 繁體中文  ",
            "**生成方式：** 本地方法（metadata + abstract-based，自動排版成網站既有報告格式）",
            "",
            "### 自動產生報告（本地方法）",
            "",
            f"# {title}",
            "",
            "## 執行摘要",
            "",
            f"本報告依據論文 metadata、abstract 與本專案的研究 profile 自動產生。`{title}` 的主題與目前追蹤方向具有明顯關聯；本次語意相關分數為 **{ranked.semantic_relevance:.2f}**，final score 為 **{ranked.final_score:.2f}**。",
            "",
            f"{method_focus}",
            "",
            "**原始摘要重點整理：**",
        ]
        for sentence in abstract_sentences[:4]:
            lines.append(f"- {sentence}")
        if not abstract_sentences:
            lines.append("- 尚未取得可用摘要；此報告需在後續全文解析階段補強。")
        lines.extend([
            "",
            "---",
            "",
            "## 核心主題分析",
            "",
            "### 1. 研究背景與問題意識",
            "本篇論文被選入本次批次，代表它在主題相關性、時間新近性、全文可取得性或引用/metadata 訊號上通過品質門檻。從摘要可見，作者聚焦於一個正在快速成形的研究問題，並嘗試用系統化方式整理現有方法、指出缺口，或提出可評估的新架構。",
            "",
            "### 2. 方法、分類或系統設計",
            "目前本地流程尚未解析 PDF 全文，因此不假裝已讀取完整方法章節；以下先根據 abstract 做保守整理。若這是 review paper，應優先檢查 taxonomy、納入/排除標準與比較表；若是一般 paper，則應優先檢查模型/系統流程、資料集、baseline 與 metrics。",
            "",
            "| 面向 | 本地初步判讀 | 後續全文確認重點 |",
            "| :--- | :--- | :--- |",
            f"| 研究類型 | {paper_type_label} | 確認 paper 是否真的符合此類型，以及是否需要改標為 general/review |",
            f"| 主題關聯 | semantic={ranked.semantic_relevance:.2f}, final={ranked.final_score:.2f} | 檢查 introduction 與 conclusion 是否和研究 profile 的核心問題一致 |",
            f"| 全文取得 | {'有 PDF' if paper.pdf_url else '尚未找到 PDF'} | 下載 PDF 後解析章節、圖表與 reference |",
            "| 可行輸出 | Markdown 報告、影片腳本、YouTube 發布 | 若內容重要，加入 seed papers 或後續實作 backlog |",
            "",
            "### 3. 可能的貢獻",
            "- 提供一個可快速掌握該研究方向的入口，適合納入週期性 paper monitoring。",
            "- 若為 review paper，可用來更新技術地圖、taxonomy、關鍵挑戰與 future-work backlog。",
            "- 若為一般 paper，可用來追蹤新方法、新 benchmark、新資料集或新系統設計。",
            "- 可作為後續 NotebookLM / LLM 深度摘要、引用蒐集與影片講解的基礎資料。",
            "",
            "---",
            "",
            "## 重要引言與背景脈絡",
            "",
            "以下引用為 abstract / metadata 層級的原文節錄，用於保留可追溯依據；不是全文逐段翻譯。",
        ])
        for quote in representative_quotes:
            lines.extend(["", f"> {quote}", "", "*背景：此句揭示作者在摘要中強調的研究動機、方法範圍或主要觀察。後續若能解析全文，應回到原文脈絡確認其精確含義。*"])
        lines.extend([
            "",
            "---",
            "",
            "## 對本專案的啟發",
            "",
            "1. **更新研究地圖：** 將此論文的主題、分類與 reference 併入後續趨勢追蹤。",
            "2. **補強選文 seed：** 如果全文確認與研究 profile 高度相關，可把它加入 positive seed papers，提高後續 ranking 品質。",
            "3. **形成實作 backlog：** 若論文提出可操作的系統架構、benchmark 或安全機制，可拆成後續工程任務。",
            "4. **對照既有報告：** 報告格式沿用網站既有輸出：標題、metadata、執行摘要、核心主題、引言脈絡、行動建議與影片連結。",
            "",
            "## 限制與待確認",
            "",
            "- 本地方法目前只保守使用 metadata 與 abstract；尚未宣稱已完整閱讀 PDF。",
            "- 方法、實驗、圖表與 reference 的精確解讀需依後續 PDF parser / NotebookLM / 人工複核補強。",
            "- 若外部 API 回傳 metadata 不完整，作者、年份、分類或 paper type 可能需要人工校正。",
            "",
            "## 後續閱讀建議",
            "",
            "- 先閱讀 introduction 與 conclusion，確認此論文是否真的值得納入長期追蹤。",
            "- 對 review paper，優先擷取 taxonomy、比較表、future directions 與 reference list。",
            "- 對一般 paper，優先擷取方法流程圖、實驗設定、主要表格與失敗案例。",
            "",
            "### 影片報告",
            "- YouTube：待上傳",
            "",
        ])
        return "\n".join(lines)

    def render_video_script(self, ranked: RankedPaper) -> str:
        paper = ranked.paper
        paper_type = (paper.extra or {}).get("paper_type", "review")
        authors = ", ".join(paper.authors) if paper.authors else "未知作者"
        intro = (
            f"這是一份繁體中文論文影片報告。題目是：{paper.title or '未命名論文'}。"
            f"作者：{authors}。來源：{paper.source or '未知來源'}。發表年份：{paper.year}。"
            f"語意相關分數：{ranked.semantic_relevance:.2f}，總分：{ranked.final_score:.2f}。"
        )
        if paper_type == "general":
            sections = [
                ("開場：paper title、作者、年份、來源", intro),
                ("研究問題：它想解決什麼問題", "說明這篇 paper 想處理的核心研究問題，以及它希望改善的系統或方法缺口。"),
                ("背景與動機：為什麼這個問題重要", "說明這個問題對目前研究領域、工程系統或 agent workflow 的重要性。"),
                ("相關工作簡述：以前方法有什麼不足", "整理既有方法的限制，包含可擴充性、穩定性、協調成本、工具使用或評估不足。"),
                ("核心方法：這篇 paper 提出什麼新方法", "摘要作者提出的新模型、演算法、系統設計或流程。"),
                ("系統/模型架構：方法流程圖、模組說明", "用文字描述主要模組、資料流、控制流，以及各模組如何互動。"),
                ("實驗設計：dataset、baseline、metrics", "說明資料集、比較基準、評估指標，以及實驗設定。"),
                ("實驗結果：主要表格與圖", "摘要最重要的結果、表格、圖，以及結果代表的意義。"),
                ("優點與貢獻：這篇 paper 做得好的地方", "列出這篇 paper 的主要貢獻、創新點與實用價值。"),
                ("限制與問題：可能的缺點", "指出方法可能的限制、失敗情境、假設條件或尚未解決的問題。"),
                ("你的觀點：跟你的研究/專案有什麼關係", "說明它可如何啟發目前的研究 profile、系統設計、工具協調或後續實作。"),
                ("總結", "用一到兩句話總結這篇 paper 是否值得深入閱讀或納入後續工作。"),
            ]
        else:
            sections = [
                ("開場：這篇 review paper 在整理什麼領域", intro),
                ("研究背景：為什麼這個領域重要", "說明此 review 整理的研究領域，以及它和目前研究 profile 的關係。"),
                ("Review 範圍：作者收集哪些論文、時間範圍、篩選條件", "摘要作者收集的論文類型、可能的時間範圍、納入與排除標準。若原文未明確提供，先標記為待全文確認。"),
                ("分類架構：作者怎麼把相關研究分類", "描述作者如何建立 taxonomy，例如依方法、任務、系統架構、資料來源或評估方式分類。"),
                ("各類方法重點：每一類代表什麼方向", "逐類說明各研究方向的核心想法、典型方法與代表性應用。"),
                ("比較與趨勢：不同方法的優缺點、發展趨勢", "整理不同研究路線的優缺點，並指出近年的技術趨勢與轉向。"),
                ("挑戰與限制：目前領域還有哪些問題沒解", "列出 review 中提到或可推論的未解問題，例如可靠性、安全、評估、資料、部署或可擴充性。"),
                ("未來方向：作者建議未來可以怎麼做", "摘要作者提出的 future work，也補上可延伸的研究方向。"),
                ("你的觀點：這篇 review 對你的研究/系統有什麼幫助", "說明這篇 review 如何幫助建立 seed papers、整理技術地圖、設計系統模組或規劃實作 backlog。"),
                ("總結", "用一到兩句話總結這篇 review paper 的價值，以及是否應該優先深入閱讀。"),
            ]
        return "\n\n".join([f"## {title}\n{body}" for title, body in sections])

    def create_video(self, script: str, video_path: Path, workdir: Path) -> list[str]:
        errors: list[str] = []
        audio_path = workdir / "narration.mp3"
        if self.enable_tts and shutil.which("edge-tts"):
            tts = run_command(["edge-tts", "--voice", "zh-TW-HsiaoChenNeural", "--text", script, "--write-media", str(audio_path)], timeout=60)
            if not tts.ok:
                errors.append(f"edge-tts failed: {tts.combined_output[:300]}")
        if shutil.which("ffmpeg"):
            duration = self._target_video_duration_seconds(audio_path if audio_path.exists() else None)
            title = _drawtext_escape(script.splitlines()[0] if script.strip() else "Paper Report")
            command = [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"color=c=0x101827:s=1280x720:r=1:d={duration}",
            ]
            if audio_path.exists():
                command.extend(["-i", str(audio_path)])
            else:
                command.extend(["-f", "lavfi", "-i", f"anullsrc=channel_layout=stereo:sample_rate=44100:d={duration}"])
            command.extend([
                "-t",
                str(duration),
                "-vf",
                f"drawtext=text='{title}':fontcolor=white:fontsize=34:x=60:y=300",
                "-r",
                "1",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-tune",
                "stillimage",
                "-pix_fmt",
                "yuv420p",
            ])
            if audio_path.exists():
                command.extend(["-af", "apad"])
            command.extend([
                "-c:a",
                "aac",
                str(video_path),
            ])
            result = run_command(command, timeout=180)
            if result.ok and video_path.exists():
                return errors
            errors.append(f"ffmpeg failed: {result.combined_output[:300]}")
        # Last resort: create an inspectable placeholder so the pipeline can continue.
        video_path.write_bytes(b"PAPER_REPORT_VIDEO_PLACEHOLDER\n" + script.encode("utf-8"))
        return errors

    def _target_video_duration_seconds(self, audio_path: Path | None) -> int:
        duration = self.min_video_duration_seconds
        if audio_path and audio_path.exists() and shutil.which("ffprobe"):
            probed = run_command(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
                timeout=10,
            )
            if probed.ok:
                try:
                    duration = max(duration, int(float(probed.stdout.strip())) + 2)
                except ValueError:
                    pass
        return duration


class NotebookLMGenerator:
    def __init__(
        self,
        output_dir: str | Path,
        *,
        runner: Runner = run_command,
        openclaw_runner: OpenClawRunner = run_openclaw_webbridge,
        video_wait_timeout_seconds: int = 30 * 60,
        poll_interval_seconds: int = 30,
        local_video_fallback: LocalReportGenerator | None = None,
    ):
        self.output_dir = Path(output_dir)
        self.runner = runner
        self.openclaw_runner = openclaw_runner
        self.video_wait_timeout_seconds = video_wait_timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self.local_video_fallback = local_video_fallback or LocalReportGenerator(output_dir)

    def generate(self, ranked: RankedPaper, index: int) -> GenerationArtifact:
        paper = ranked.paper
        paper_dir = self.output_dir / "notebooklm" / f"{index:02d}-{slugify(paper.title)}"
        paper_dir.mkdir(parents=True, exist_ok=True)
        report_path = paper_dir / "report.md"
        video_path = paper_dir / "video.mp4"
        errors: list[str] = []

        notebook = self._create_notebook(paper, errors)
        if notebook:
            self._add_source(notebook, paper, report_path, video_path, errors)
        else:
            self._openclaw("create notebook and upload paper", paper, report_path, video_path, errors)

        report_artifact = ""
        if notebook:
            report_artifact = self._create_artifact(["nlm", "report", "create", notebook, "--format", "Briefing Doc", "--confirm"], errors)
            if report_artifact:
                self._download_or_openclaw("report", notebook, report_artifact, report_path, paper, video_path, errors)

        video_artifact = ""
        video_status = "created"
        if notebook:
            video_artifact = self._create_artifact(["nlm", "video", "create", notebook, "--format", "explainer", "--confirm"], errors)
            if video_artifact:
                video_status = self._download_video_with_timeout(notebook, video_artifact, video_path, paper, report_path, errors)

        if not report_path.exists():
            report_path.write_text(self._fallback_markdown(ranked, errors), encoding="utf-8")
        if not video_path.exists():
            local = self.local_video_fallback.generate(ranked, index)
            if local.video_path:
                Path(local.video_path).replace(video_path)
            video_status = "local_fallback"

        return GenerationArtifact(
            paper_title=paper.title,
            method="notebooklm",
            markdown_path=str(report_path),
            video_path=str(video_path),
            markdown_status="created" if report_path.exists() else "failed",
            video_status=video_status,
            notebook_id=notebook,
            report_artifact_id=report_artifact,
            video_artifact_id=video_artifact,
            errors=errors,
        )

    def _create_notebook(self, paper: Paper, errors: list[str]) -> str:
        result = self.runner(["nlm", "notebook", "create", paper.title or "Paper Report"], 120)
        if not result.ok:
            errors.append(f"NotebookLM notebook create failed: {result.combined_output[:300]}")
            return ""
        return self._extract_id(result.combined_output, prefixes=("notebook", "notebook_id", "id"))

    def _add_source(self, notebook: str, paper: Paper, report_path: Path, video_path: Path, errors: list[str]) -> None:
        source = paper.pdf_url or paper.url
        if not source:
            errors.append("NotebookLM source add skipped: no PDF or URL")
            self._openclaw("upload paper", paper, report_path, video_path, errors)
            return
        command = ["nlm", "source", "add", notebook]
        if source.startswith("http://") or source.startswith("https://"):
            command.extend(["--url", source])
        else:
            command.extend(["--file", source])
        result = self.runner(command, 300)
        if not result.ok:
            errors.append(f"NotebookLM source add failed: {result.combined_output[:300]}")
            self._openclaw("upload paper", paper, report_path, video_path, errors)

    def _create_artifact(self, command: list[str], errors: list[str]) -> str:
        result = self.runner(command, 300)
        if not result.ok:
            errors.append(f"NotebookLM create artifact failed: {result.combined_output[:300]}")
            return ""
        return self._extract_id(result.combined_output, prefixes=("artifact", "artifact_id", "id"))

    def _download_or_openclaw(self, artifact_type: str, notebook: str, artifact_id: str, output: Path, paper: Paper, video_path: Path, errors: list[str]) -> bool:
        result = self.runner(["nlm", "download", artifact_type, notebook, artifact_id, "--output", str(output)], 300)
        if result.ok and output.exists():
            return True
        errors.append(f"NotebookLM download {artifact_type} failed: {result.combined_output[:300]}")
        self._openclaw(f"download {artifact_type}", paper, output if artifact_type == "report" else output.with_suffix(".md"), video_path, errors)
        return output.exists()

    def _download_video_with_timeout(self, notebook: str, artifact_id: str, video_path: Path, paper: Paper, report_path: Path, errors: list[str]) -> str:
        deadline = time.monotonic() + self.video_wait_timeout_seconds
        first = True
        while first or time.monotonic() <= deadline:
            first = False
            result = self.runner(["nlm", "download", "video", notebook, artifact_id, "--output", str(video_path)], 300)
            if result.ok and video_path.exists():
                return "created"
            message = result.combined_output.lower()
            if "download" in message and "error" in message:
                errors.append(f"NotebookLM download video failed: {result.combined_output[:300]}")
                self._openclaw("download video", paper, report_path, video_path, errors)
                return "created_by_openclaw" if video_path.exists() else "download_error"
            if self.video_wait_timeout_seconds <= 0:
                break
            time.sleep(min(self.poll_interval_seconds, max(0, deadline - time.monotonic())))
        errors.append("NotebookLM video was not ready within 30 minutes; falling back to local video generation")
        local = self.local_video_fallback.generate(RankedPaper(paper=paper, semantic_relevance=0, recency_score=0, full_text_score=0, citation_signal=0, code_or_project_signal=0, final_score=0), 0)
        if local.video_path:
            Path(local.video_path).replace(video_path)
        return "local_fallback_after_timeout"

    def _openclaw(self, action: str, paper: Paper, report_path: Path, video_path: Path, errors: list[str]) -> None:
        message = (
            "Use webbridge in the browser to operate NotebookLM. "
            f"Task: {action}. Paper title: {paper.title}. "
            f"Paper URL/PDF: {paper.pdf_url or paper.url}. "
            f"Save markdown report to: {report_path}. Save video report to: {video_path}. "
            "Return JSON with success status and file paths."
        )
        result = self.openclaw_runner(message, 1800)
        if not result.ok:
            errors.append(f"OpenClaw webbridge fallback failed: {result.combined_output[:300]}")

    def _fallback_markdown(self, ranked: RankedPaper, errors: list[str]) -> str:
        return LocalReportGenerator(self.output_dir).render_markdown(ranked) + "\n\n> NotebookLM markdown 產生或下載失敗，已暫時使用本地方法補上。\n"

    @staticmethod
    def _extract_id(text: str, prefixes: Iterable[str]) -> str:
        for prefix in prefixes:
            patterns = [
                rf"{re.escape(prefix)}[=: ]+([A-Za-z0-9_.:-]+)",
                rf"{re.escape(prefix)}[_ -]?id[=: ]+([A-Za-z0-9_.:-]+)",
            ]
            for pattern in patterns:
                match = re.search(pattern, text or "", flags=re.IGNORECASE)
                if match:
                    return match.group(1).strip().strip('"\'')
        match = re.search(r"\b(nb_[A-Za-z0-9_.:-]+|[A-Za-z]+_[A-Za-z0-9_.:-]+)\b", text or "")
        return match.group(1) if match else ""


class ReportGenerationOrchestrator:
    def __init__(
        self,
        output_dir: str | Path,
        *,
        max_workers: int = 4,
        notebooklm_generator: NotebookGenerator | None = None,
        enable_tts: bool = False,
        video_wait_timeout_seconds: int = 30 * 60,
        local_video_min_duration_seconds: int = DEFAULT_LOCAL_VIDEO_MIN_DURATION_SECONDS,
    ):
        self.output_dir = Path(output_dir)
        self.max_workers = max_workers
        self.local_generator = LocalReportGenerator(
            output_dir,
            enable_tts=enable_tts,
            min_video_duration_seconds=local_video_min_duration_seconds,
        )
        self.notebooklm_generator = notebooklm_generator or NotebookLMGenerator(
            output_dir,
            video_wait_timeout_seconds=video_wait_timeout_seconds,
            local_video_fallback=self.local_generator,
        ).generate

    def generate_local(self, ranked: RankedPaper, index: int) -> GenerationArtifact:
        return self.local_generator.generate(ranked, index)

    def generate_for_selection(self, result: SelectionResult) -> list[GenerationArtifact]:
        return self.generate_for_papers(result.selected_papers)

    def generate_for_papers(self, papers: list[RankedPaper]) -> list[GenerationArtifact]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        assignments = split_generation_methods(papers)
        artifacts: list[GenerationArtifact] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, self.max_workers)) as executor:
            future_to_assignment = {
                executor.submit(self._generate_assignment, assignment): assignment for assignment in assignments
            }
            for future in concurrent.futures.as_completed(future_to_assignment):
                artifacts.append(future.result())
        artifacts.sort(key=lambda artifact: [p.paper.title for p in papers].index(artifact.paper_title) if artifact.paper_title in [p.paper.title for p in papers] else 999)
        self.write_manifest(artifacts)
        return artifacts

    def _generate_assignment(self, assignment: GenerationAssignment) -> GenerationArtifact:
        if assignment.method == "local":
            return self.local_generator.generate(assignment.paper, assignment.index)
        return self.notebooklm_generator(assignment.paper, assignment.index)

    def write_manifest(self, artifacts: list[GenerationArtifact]) -> Path:
        manifest = self.output_dir / "manifest.json"
        manifest.write_text(json.dumps({"artifacts": [item.to_dict() for item in artifacts]}, ensure_ascii=False, indent=2), encoding="utf-8")
        return manifest
