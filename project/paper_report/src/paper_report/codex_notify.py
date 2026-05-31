from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable


@dataclass(slots=True)
class CodexEmailResult:
    ok: bool
    recipient: str
    subject: str
    workdir: str
    raw_response: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


CodexRunner = Callable[[list[str], Path, int], subprocess.CompletedProcess[str]]


def default_codex_runner(command: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False, timeout=timeout)


def ensure_git_workdir(path: str | Path) -> Path:
    """Codex CLI expects a git repository; create a tiny scratch repo if needed."""
    workdir = Path(path)
    workdir.mkdir(parents=True, exist_ok=True)
    if (workdir / ".git").exists():
        return workdir
    subprocess.run(["git", "init"], cwd=workdir, capture_output=True, text=True, check=False, timeout=30)
    return workdir


def _json_status(result: dict) -> str:
    ok = result.get("ok")
    status = "成功" if ok else "失敗"
    error = result.get("error") or ""
    github = result.get("github_publish") or {}
    youtube = result.get("youtube_uploads") or []
    urls = []
    for item in youtube:
        if item.get("youtube_url"):
            urls.append(f"- {item.get('paper_title', 'Untitled')}: {item.get('youtube_url')}")
    lines = [
        f"Paper Report cron job 執行{status}。",
        f"cleanup_done: {result.get('cleanup_done')}",
        f"hunt_json: {result.get('hunt_json')}",
        f"generated_manifest: {result.get('generated_manifest')}",
    ]
    if github:
        lines.append(f"GitHub publish ok: {github.get('ok')}; pushed: {github.get('pushed')}; commit: {github.get('commit')}")
        if github.get("error"):
            lines.append(f"GitHub error: {github.get('error')}")
    if urls:
        lines.append("YouTube links:")
        lines.extend(urls)
    if error:
        lines.append(f"Error reason: {error}")
    return "\n".join(lines)


class CodexGmailNotifier:
    def __init__(
        self,
        *,
        recipient: str = "openclaw572@gmail.com",
        workdir: str | Path = "tmp/codex-email-workdir",
        timeout_seconds: int = 900,
        runner: CodexRunner = default_codex_runner,
    ):
        self.recipient = recipient
        self.workdir = Path(workdir)
        self.timeout_seconds = timeout_seconds
        self.runner = runner

    def send_pipeline_result(self, pipeline_result: dict) -> CodexEmailResult:
        workdir = ensure_git_workdir(self.workdir)
        subject = "Paper Report cron job 完成" if pipeline_result.get("ok") else "Paper Report cron job 失敗"
        body = _json_status(pipeline_result)
        prompt = self._build_prompt(subject, body, pipeline_result)
        codex = shutil.which("codex")
        if not codex:
            return CodexEmailResult(False, self.recipient, subject, str(workdir), error="codex CLI not found in PATH")
        try:
            completed = self.runner([codex, "exec", "--full-auto", prompt], workdir, self.timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            output = "\n".join(part for part in (exc.stdout or "", exc.stderr or "") if part)
            return CodexEmailResult(False, self.recipient, subject, str(workdir), raw_response=output, error=f"codex timed out after {self.timeout_seconds}s")
        raw = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
        if completed.returncode != 0:
            return CodexEmailResult(False, self.recipient, subject, str(workdir), raw_response=raw, error=f"codex exited with {completed.returncode}")
        return CodexEmailResult(True, self.recipient, subject, str(workdir), raw_response=raw)

    def _build_prompt(self, subject: str, body: str, pipeline_result: dict) -> str:
        status_json = json.dumps(pipeline_result, ensure_ascii=False, indent=2)
        return f"""
你正在替 Paper Report cron job 寄出執行結果通知。

請實際傳送 Gmail，不要只輸出草稿。收件人：{self.recipient}
主旨：{subject}
內文請使用繁體中文，內容如下：

{body}

如果本機有 gws / Google Workspace CLI / Gmail API token / himalaya 等可用寄信工具，請直接使用它們寄出。
如果無法寄出，請在最終輸出中明確寫出失敗原因，例如缺少 OAuth token、Gmail API 權限不足、指令不存在或網路錯誤。
不要要求 Google 密碼，也不要嘗試繞過 2FA。

完整 pipeline status JSON 供你參考：
```json
{status_json}
```

完成後請輸出 JSON，格式：{{"success": true, "email_sent": true}}；若失敗：{{"success": false, "error": "原因"}}。
""".strip()
