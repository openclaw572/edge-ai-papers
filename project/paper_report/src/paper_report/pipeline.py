from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from .codex_notify import CodexEmailResult, CodexGmailNotifier
from .github_publish import GitHubPublishResult, GitHubSitePublisher
from .references import record_references
from .youtube_openclaw import OpenClawYouTubeUploader, YouTubeUploadResult


@dataclass(slots=True)
class FullPipelineResult:
    ok: bool
    hunt_json: str
    generated_manifest: str
    references_json: str = ""
    references_markdown: str = ""
    youtube_uploads: list[dict] | None = None
    github_publish: dict | None = None
    email_notification: dict | None = None
    cleanup_done: bool = False
    cleanup_deleted_paths: list[str] | None = None
    cleanup_errors: list[str] | None = None
    error: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        data["youtube_uploads"] = self.youtube_uploads or []
        data["github_publish"] = self.github_publish or {}
        data["email_notification"] = self.email_notification or {}
        data["cleanup_deleted_paths"] = self.cleanup_deleted_paths or []
        data["cleanup_errors"] = self.cleanup_errors or []
        return data


class FullPipelineRunner:
    def __init__(
        self,
        *,
        project_dir: str | Path,
        profile: str = "configs/research_profile.yaml",
        profile_id: str | None = None,
        repo_url: str = "https://github.com/openclaw572/edge-ai-papers.git",
        repo_checkout_dir: str | Path = "tmp/edge-ai-papers-publish",
        run_date: str | None = None,
        max_workers: int = 4,
        youtube_workers: int = 1,
        push_github: bool = True,
        cleanup: bool = True,
        enable_tts: bool = False,
        email_recipient: str = "openclaw572@gmail.com",
        skip_email: bool = False,
    ):
        self.project_dir = Path(project_dir)
        self.profile = profile
        self.profile_id = profile_id
        self.repo_url = repo_url
        self.repo_checkout_dir = Path(repo_checkout_dir)
        if not self.repo_checkout_dir.is_absolute():
            self.repo_checkout_dir = self.project_dir / self.repo_checkout_dir
        self.run_date = run_date or date.today().isoformat()
        self.max_workers = max_workers
        self.youtube_workers = youtube_workers
        self.push_github = push_github
        self.cleanup = cleanup
        self.enable_tts = enable_tts
        self.email_recipient = email_recipient
        self.skip_email = skip_email

    def run(self) -> FullPipelineResult:
        outputs = self.project_dir / "outputs"
        daily_md = outputs / "daily_report.md"
        daily_json = outputs / "daily_report.json"
        generated_dir = outputs / "generated_reports"
        references_dir = outputs / "references" / self.run_date
        final_status = outputs / "pipeline_status.json"
        try:
            hunt_args = ["hunt", "--profile", self.profile, "--output", str(daily_md)]
            if self.profile_id:
                hunt_args.extend(["--profile-id", self.profile_id])
            self._run_cli(hunt_args)
            self._run_cli(
                [
                    "generate-reports",
                    "--input",
                    str(daily_json),
                    "--output-dir",
                    str(generated_dir),
                    "--max-workers",
                    str(self.max_workers),
                    *( ["--enable-tts"] if self.enable_tts else [] ),
                ]
            )
            manifest = generated_dir / "manifest.json"
            refs_json, refs_md = record_references(daily_json, references_dir)
            youtube_results = OpenClawYouTubeUploader(max_workers=self.youtube_workers).upload_artifacts(manifest, write_back=True)
            github_result = GitHubSitePublisher(
                repo_url=self.repo_url,
                checkout_dir=self.repo_checkout_dir,
                project_dir=self.project_dir,
                push=self.push_github,
            ).publish(manifest, selection_json_path=daily_json, run_date=self.run_date)
            all_youtube_ok = all(item.ok for item in youtube_results)
            ok = all_youtube_ok and github_result.ok
            cleanup_done = False
            cleanup_deleted_paths: list[str] = []
            cleanup_errors: list[str] = []
            if ok and self.cleanup:
                cleanup_deleted_paths, cleanup_errors = self._cleanup_after_success(manifest, generated_dir, daily_md, daily_json)
                cleanup_done = not cleanup_errors
            result = FullPipelineResult(
                ok=ok,
                hunt_json=str(daily_json),
                generated_manifest=str(manifest),
                references_json=str(refs_json),
                references_markdown=str(refs_md),
                youtube_uploads=[item.to_dict() for item in youtube_results],
                github_publish=github_result.to_dict(),
                cleanup_done=cleanup_done,
                cleanup_deleted_paths=cleanup_deleted_paths,
                cleanup_errors=cleanup_errors,
                error="" if ok else "YouTube upload or GitHub publish did not fully succeed; local artifacts were preserved.",
            )
        except Exception as exc:  # noqa: BLE001 - status file should capture operational failures.
            result = FullPipelineResult(False, str(daily_json), str(generated_dir / "manifest.json"), error=str(exc))
        if not self.skip_email:
            email_result = self._send_email_notification(result)
            result.email_notification = email_result.to_dict()
            if not email_result.ok:
                result.ok = False
                result.error = "; ".join(
                    part for part in (result.error, f"Codex Gmail notification failed: {email_result.error}") if part
                )
        final_status.parent.mkdir(parents=True, exist_ok=True)
        final_status.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    def _send_email_notification(self, result: FullPipelineResult) -> CodexEmailResult:
        codex_workdir = self.repo_checkout_dir if (self.repo_checkout_dir / ".git").exists() else self.project_dir / "tmp" / "codex-email-workdir"
        return CodexGmailNotifier(
            recipient=self.email_recipient,
            workdir=codex_workdir,
        ).send_pipeline_result(result.to_dict())

    def _run_cli(self, args: list[str]) -> None:
        command = [sys.executable, "-m", "paper_report.cli", *args]
        env = os.environ.copy()
        existing_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = "src" if not existing_pythonpath else f"src{os.pathsep}{existing_pythonpath}"
        completed = subprocess.run(
            command,
            cwd=self.project_dir,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=7200,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"command failed: {' '.join(command)}\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}")

    def _cleanup_after_success(self, manifest: Path, generated_dir: Path, daily_md: Path, daily_json: Path) -> tuple[list[str], list[str]]:
        """Delete external NotebookLM notebooks and local transient artifacts after publish/upload success."""
        deleted: list[str] = []
        errors: list[str] = []
        deleted.extend(self._cleanup_notebooklm_notebooks(manifest, errors))
        for path in (generated_dir, daily_md, daily_json):
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                    deleted.append(str(path))
                elif path.exists():
                    path.unlink()
                    deleted.append(str(path))
            except OSError as exc:
                errors.append(f"Failed to delete {path}: {exc}")
        return deleted, errors

    def _cleanup_notebooklm_notebooks(self, manifest: Path, errors: list[str]) -> list[str]:
        if not manifest.exists():
            return []
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"Failed to read manifest for NotebookLM cleanup: {exc}")
            return []
        notebook_ids = sorted({str(item.get("notebook_id") or "").strip() for item in data.get("artifacts") or [] if item.get("notebook_id")})
        deleted: list[str] = []
        for notebook_id in notebook_ids:
            if self._delete_notebooklm_notebook(notebook_id, errors):
                deleted.append(f"notebooklm:{notebook_id}")
        return deleted

    def _delete_notebooklm_notebook(self, notebook_id: str, errors: list[str]) -> bool:
        commands = [
            ["nlm", "notebook", "delete", notebook_id, "--confirm"],
            ["nlm", "notebook", "delete", notebook_id, "-y"],
        ]
        last_output = ""
        for command in commands:
            try:
                completed = subprocess.run(
                    command,
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=120,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                last_output = str(exc)
                continue
            if completed.returncode == 0:
                return True
            last_output = (completed.stdout + completed.stderr).strip()
        errors.append(f"Failed to delete NotebookLM notebook {notebook_id}: {last_output[:300]}")
        return False
