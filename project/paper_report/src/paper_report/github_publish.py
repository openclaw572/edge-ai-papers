from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable

from .report_generation import slugify

SITE_KEEP = {"index.html", "css", "js", "reports", ".git"}
PROJECT_EXCLUDE_DIRS = {".git", "__pycache__", ".pytest_cache", ".venv", "venv", "outputs", "tmp"}
PROJECT_EXCLUDE_FILES = {".env"}


@dataclass(slots=True)
class GitHubPublishResult:
    ok: bool
    repo_dir: str
    commit: str = ""
    branch: str = ""
    report_urls: list[str] | None = None
    error: str = ""
    pushed: bool = False

    def to_dict(self) -> dict:
        data = asdict(self)
        data["report_urls"] = self.report_urls or []
        return data


def run_git(args: list[str], cwd: Path, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False, timeout=timeout)


def ensure_repo(repo_url: str, checkout_dir: str | Path) -> Path:
    dest = Path(checkout_dir)
    if (dest / ".git").exists():
        run_git(["fetch", "origin"], dest)
        branch = current_branch(dest) or "main"
        run_git(["checkout", branch], dest)
        run_git(["pull", "--ff-only", "origin", branch], dest)
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", repo_url, str(dest)], capture_output=True, text=True, check=False, timeout=180)
    return dest


def current_branch(repo_dir: Path) -> str:
    result = run_git(["rev-parse", "--abbrev-ref", "HEAD"], repo_dir)
    return result.stdout.strip() if result.returncode == 0 else ""


def reset_to_site_only(repo_dir: str | Path) -> list[str]:
    """Remove old method/task/pipeline materials; keep static website architecture and reports."""
    root = Path(repo_dir)
    removed: list[str] = []
    for child in root.iterdir():
        if child.name in SITE_KEEP:
            continue
        if child.name.startswith(".git"):
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
        removed.append(child.name)
    write_site_readme(root / "README.md")
    return removed


def write_site_readme(path: Path) -> None:
    path.write_text(
        """# Paper Reports Website

這個 repo 只保留靜態網站架構與已發布的論文報告資料。

## 網站架構

```text
index.html          # 靜態網站入口
css/                # 網站樣式
js/                 # 前端邏輯，讀取 reports/index.json 與每日 index
reports/            # 已發布 Markdown 報告與索引
project/paper_report/ # 產生本網站內容的 Paper Report 專案程式與文件
```

## 更新方式

網站前端會讀取：

1. `reports/index.json`：全域日期索引。
2. `reports/YYYY-MM-DD/index.json`：單日 paper 清單。
3. `reports/YYYY-MM-DD/*.md`：單篇繁體中文 Markdown 報告。

新增報告時，只要把 Markdown 放入對應日期資料夾，並更新上述兩個 JSON index，網站就會顯示新內容。
""",
        encoding="utf-8",
    )


def copy_project(project_dir: str | Path, repo_dir: str | Path, dest_rel: str = "project/paper_report") -> Path:
    src = Path(project_dir)
    dest = Path(repo_dir) / dest_rel
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    def ignore(directory: str, names: list[str]) -> set[str]:
        ignored: set[str] = set()
        for name in names:
            if name in PROJECT_EXCLUDE_DIRS or name in PROJECT_EXCLUDE_FILES:
                ignored.add(name)
        return ignored

    shutil.copytree(src, dest, ignore=ignore)
    return dest


def _load_json(path: Path, default: dict) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def _artifact_title(artifact: dict) -> str:
    return str(artifact.get("paper_title") or artifact.get("title") or "Untitled Paper")


def _paper_type(artifact: dict, paper: dict | None = None) -> str:
    extra = ((paper or {}).get("paper") or {}).get("extra") if paper else None
    if isinstance(extra, dict) and extra.get("paper_type"):
        return str(extra["paper_type"]).lower()
    text = f"{_artifact_title(artifact)} {artifact.get('method', '')}".lower()
    return "review" if any(token in text for token in ("review", "survey", "綜述")) else "general"


def _category(paper_data: dict | None) -> str:
    paper = (paper_data or {}).get("paper") or {}
    categories = paper.get("categories") or []
    if categories:
        return ", ".join(str(item) for item in categories)
    return paper.get("source") or "Paper Report"


def _source_link(paper_data: dict | None) -> str:
    paper = (paper_data or {}).get("paper") or {}
    return paper.get("pdf_url") or paper.get("url") or ""


def _selected_by_title(selection_json_path: str | Path | None) -> dict[str, dict]:
    if not selection_json_path:
        return {}
    path = Path(selection_json_path)
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    mapping = {}
    for item in data.get("selected_papers") or []:
        title = ((item.get("paper") or {}).get("title") or "").strip()
        if title:
            mapping[title] = item
    return mapping


def append_youtube_to_markdown(markdown: str, youtube_url: str) -> str:
    if youtube_url:
        markdown = re.sub(r"YouTube:\s*(待上傳|https?://\S+)", f"YouTube: {youtube_url}", markdown)
        if "## 影片連結" not in markdown:
            markdown += f"\n\n## 影片連結\n\n- YouTube: {youtube_url}\n"
        elif youtube_url not in markdown:
            markdown += f"\n- YouTube: {youtube_url}\n"
    return markdown


def publish_reports_to_site(
    manifest_path: str | Path,
    repo_dir: str | Path,
    *,
    selection_json_path: str | Path | None = None,
    run_date: str | None = None,
) -> list[str]:
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    selected = _selected_by_title(selection_json_path)
    artifacts = list(manifest.get("artifacts") or [])
    date_str = run_date or date.today().isoformat()
    root = Path(repo_dir)
    report_dir = root / "reports" / date_str
    report_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    papers_index: list[dict] = []
    for idx, artifact in enumerate(artifacts, start=1):
        markdown_path = Path(str(artifact.get("markdown_path") or ""))
        if not markdown_path.exists():
            continue
        title = _artifact_title(artifact)
        selected_data = selected.get(title)
        filename = f"paper-{idx}-{slugify(title)}.md"
        youtube_url = str(artifact.get("youtube_url") or (artifact.get("youtube_upload") or {}).get("youtube_url") or "")
        markdown = append_youtube_to_markdown(markdown_path.read_text(encoding="utf-8"), youtube_url)
        (report_dir / filename).write_text(markdown, encoding="utf-8")
        copied.append(str(report_dir / filename))
        ptype = _paper_type(artifact, selected_data)
        papers_index.append(
            {
                "id": f"paper-{idx}",
                "category": _category(selected_data),
                "title": title,
                "path": filename,
                "link": _source_link(selected_data),
                "type": "REVIEW PAPER" if ptype == "review" else "GENERAL PAPER",
                "paperType": ptype,
                "youtubeUrl": youtube_url,
            }
        )
    paper_type = "review" if any((p.get("paperType") == "review") for p in papers_index) else "general"
    daily = {
        "date": date_str,
        "paperCount": len(papers_index),
        "paperType": paper_type,
        "papers": papers_index,
        "notebookLM": {},
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    (report_dir / "index.json").write_text(json.dumps(daily, ensure_ascii=False, indent=2), encoding="utf-8")
    update_global_index(root / "reports" / "index.json", daily)
    return copied


def update_global_index(index_path: Path, daily: dict) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index = _load_json(index_path, {"lastUpdated": daily["date"], "dates": []})
    dates = [entry for entry in index.get("dates", []) if entry.get("date") != daily["date"]]
    dates.insert(
        0,
        {
            "date": daily["date"],
            "path": f"{daily['date']}/index.json",
            "paperCount": daily["paperCount"],
            "paperType": daily["paperType"],
            "papers": [
                {"title": paper.get("title", ""), "tags": [paper.get("category", ""), paper.get("type", "")]} for paper in daily.get("papers", [])
            ],
        },
    )
    dates.sort(key=lambda entry: entry.get("date", ""), reverse=True)
    index["lastUpdated"] = dates[0]["date"] if dates else daily["date"]
    index["dates"] = dates
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


class GitHubSitePublisher:
    def __init__(
        self,
        *,
        repo_url: str,
        checkout_dir: str | Path,
        project_dir: str | Path,
        branch: str = "main",
        push: bool = False,
    ):
        self.repo_url = repo_url
        self.checkout_dir = Path(checkout_dir)
        self.project_dir = Path(project_dir)
        self.branch = branch
        self.push = push

    def publish(self, manifest_path: str | Path, *, selection_json_path: str | Path | None = None, run_date: str | None = None) -> GitHubPublishResult:
        repo = ensure_repo(self.repo_url, self.checkout_dir)
        if self.branch:
            run_git(["checkout", self.branch], repo)
        reset_to_site_only(repo)
        copy_project(self.project_dir, repo)
        report_paths = publish_reports_to_site(manifest_path, repo, selection_json_path=selection_json_path, run_date=run_date)
        run_git(["add", "README.md", "index.html", "css", "js", "reports", "project/paper_report"], repo)
        status = run_git(["status", "--porcelain"], repo)
        if not status.stdout.strip():
            return GitHubPublishResult(True, str(repo), branch=current_branch(repo), report_urls=report_paths, pushed=False)
        commit_msg = f"docs: publish paper report batch {run_date or date.today().isoformat()}"
        commit = run_git(["commit", "-m", commit_msg], repo)
        if commit.returncode != 0:
            return GitHubPublishResult(False, str(repo), branch=current_branch(repo), report_urls=report_paths, error=commit.stderr or commit.stdout)
        sha = run_git(["rev-parse", "HEAD"], repo).stdout.strip()
        pushed = False
        if self.push:
            push = run_git(["push", "origin", current_branch(repo) or self.branch or "main"], repo, timeout=180)
            if push.returncode != 0:
                return GitHubPublishResult(False, str(repo), commit=sha, branch=current_branch(repo), report_urls=report_paths, error=push.stderr or push.stdout)
            pushed = True
        return GitHubPublishResult(True, str(repo), commit=sha, branch=current_branch(repo), report_urls=report_paths, pushed=pushed)
