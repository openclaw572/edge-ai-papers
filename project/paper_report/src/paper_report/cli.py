from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from .arxiv_client import ARXIV_REQUEST_INTERVAL_SECONDS, fetch_arxiv
from .google_scholar import fetch_google_scholar
from .openalex import fetch_openalex
from .profile import ProfileStore, load_research_profile, load_yaml
from .report import render_daily_report
from .report_generation import ReportGenerationOrchestrator, load_selected_papers
from .semantic_scholar import SEMANTIC_SCHOLAR_REQUEST_INTERVAL_SECONDS, enrich_with_semantic_scholar, fetch_semantic_scholar
from .workflow import run_with_candidates_by_window, run_with_ordered_fetchers
from .models import Paper
from .github_publish import GitHubSitePublisher
from .pipeline import FullPipelineRunner
from .references import record_references
from .youtube_openclaw import OpenClawYouTubeUploader


def parse_today(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def load_sample_candidates(path: str | Path) -> dict[str, list[Paper]]:
    data = load_yaml(path)
    return {window: [Paper.from_dict(item) for item in papers or []] for window, papers in data.items()}


def cmd_profiles(args: argparse.Namespace) -> int:
    store = ProfileStore(args.store)
    if args.profile_action == "list":
        for profile_id in store.list_profiles():
            print(profile_id)
        return 0
    if args.profile_action == "show":
        print(yaml.safe_dump(store.get_profile(args.id), allow_unicode=True, sort_keys=False))
        return 0
    if args.profile_action == "delete":
        store.delete_profile(args.id)
        print(f"deleted profile: {args.id}")
        return 0
    if args.profile_action == "upsert":
        if args.data_file:
            data = load_yaml(args.data_file)
            if "profiles" in data and args.id in data["profiles"]:
                data = data["profiles"][args.id]
        else:
            data = json.loads(args.json)
        saved = store.add_or_update_profile(args.id, data)
        print(yaml.safe_dump({args.id: saved}, allow_unicode=True, sort_keys=False))
        return 0
    raise ValueError(args.profile_action)


def cmd_hunt(args: argparse.Namespace) -> int:
    profile = load_research_profile(args.profile, profile_id=args.profile_id)
    today = parse_today(args.today)
    if args.sample_candidates:
        candidates = load_sample_candidates(args.sample_candidates)
        result = run_with_candidates_by_window(profile, candidates, today=today)
    else:
        def arxiv_source(window):
            papers = fetch_arxiv(
                profile,
                window,
                max_results_per_query=args.max_results_per_query,
                sleep_seconds=args.arxiv_sleep_seconds,
            )
            if not args.skip_semantic_scholar and not args.skip_semantic_scholar_enrichment:
                papers = enrich_with_semantic_scholar(papers, sleep_seconds=args.semantic_sleep_seconds)
            return papers

        fetchers = {
            "arxiv": arxiv_source,
            "semantic_scholar": lambda window: fetch_semantic_scholar(
                profile,
                window,
                max_results_per_query=args.max_results_per_query,
                sleep_seconds=args.semantic_sleep_seconds,
            ),
            "openalex": lambda window: fetch_openalex(
                profile,
                window,
                max_results_per_query=args.max_results_per_query,
                sleep_seconds=args.openalex_sleep_seconds,
            ),
            "google_scholar": lambda window: fetch_google_scholar(
                profile,
                window,
                max_results_per_query=args.max_results_per_query,
                sleep_seconds=args.google_scholar_sleep_seconds,
                api_key=args.google_scholar_api_key,
            ),
        }
        if args.skip_semantic_scholar:
            fetchers.pop("semantic_scholar")
        source_order = [item.strip() for item in args.candidate_sources.split(",") if item.strip()] if args.candidate_sources else None
        result = run_with_ordered_fetchers(profile, fetchers, source_order=source_order, today=today)

    report = render_daily_report(profile, result, run_date=today)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    json_output = output.with_suffix(".json")
    json_output.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote report: {output}")
    print(f"wrote json: {json_output}")
    return 0


def cmd_generate_reports(args: argparse.Namespace) -> int:
    papers = load_selected_papers(args.input)
    orchestrator = ReportGenerationOrchestrator(
        output_dir=args.output_dir,
        max_workers=args.max_workers,
        enable_tts=args.enable_tts,
        video_wait_timeout_seconds=args.video_wait_timeout_seconds,
    )
    artifacts = orchestrator.generate_for_papers(papers)
    print(f"generated artifacts: {len(artifacts)}")
    print(f"wrote manifest: {Path(args.output_dir) / 'manifest.json'}")
    return 0


def cmd_record_references(args: argparse.Namespace) -> int:
    json_path, md_path = record_references(
        args.input,
        args.output_dir,
        limit_per_paper=args.limit_per_paper,
        sleep_seconds=args.semantic_sleep_seconds,
    )
    print(f"wrote references json: {json_path}")
    print(f"wrote references markdown: {md_path}")
    return 0


def cmd_upload_videos(args: argparse.Namespace) -> int:
    results = OpenClawYouTubeUploader(
        privacy_status=args.privacy_status,
        max_workers=args.max_workers,
        timeout_seconds=args.timeout_seconds,
    ).upload_artifacts(args.manifest, write_back=True)
    ok_count = sum(1 for item in results if item.ok)
    print(json.dumps({"ok_count": ok_count, "total": len(results), "results": [item.to_dict() for item in results]}, ensure_ascii=False, indent=2))
    return 0 if ok_count == len(results) else 2


def cmd_publish_github(args: argparse.Namespace) -> int:
    result = GitHubSitePublisher(
        repo_url=args.repo_url,
        checkout_dir=args.checkout_dir,
        project_dir=args.project_dir,
        branch=args.branch,
        push=args.push,
    ).publish(args.manifest, selection_json_path=args.selection_json, run_date=args.run_date)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0 if result.ok else 2


def cmd_run_full_pipeline(args: argparse.Namespace) -> int:
    result = FullPipelineRunner(
        project_dir=args.project_dir,
        profile=args.profile,
        profile_id=args.profile_id,
        repo_url=args.repo_url,
        repo_checkout_dir=args.checkout_dir,
        run_date=args.run_date,
        max_workers=args.max_workers,
        youtube_workers=args.youtube_workers,
        push_github=args.push_github,
        cleanup=not args.no_cleanup,
        enable_tts=args.enable_tts,
        email_recipient=args.email_recipient,
        skip_email=args.skip_email,
    ).run()
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0 if result.ok else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Paper Report automation CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    profiles = sub.add_parser("profiles", help="新增、刪除、修改、查詢研究領域設定")
    profiles.add_argument("--store", default="configs/research_profiles.yaml")
    profiles_sub = profiles.add_subparsers(dest="profile_action", required=True)
    profiles_sub.add_parser("list")
    show = profiles_sub.add_parser("show")
    show.add_argument("--id", required=True)
    delete = profiles_sub.add_parser("delete")
    delete.add_argument("--id", required=True)
    upsert = profiles_sub.add_parser("upsert")
    upsert.add_argument("--id", required=True)
    upsert.add_argument("--data-file")
    upsert.add_argument("--json", default="{}")
    profiles.set_defaults(func=cmd_profiles)

    hunt = sub.add_parser("hunt", help="執行 Daily Paper Hunter")
    hunt.add_argument("--profile", default="configs/research_profile.yaml")
    hunt.add_argument("--profile-id")
    hunt.add_argument("--sample-candidates", help="離線測試用候選論文 YAML")
    hunt.add_argument("--output", default="outputs/daily_report.md")
    hunt.add_argument("--today", help="YYYY-MM-DD；測試時可固定日期")
    hunt.add_argument("--max-results-per-query", type=int, default=20)
    hunt.add_argument("--candidate-sources", help="逗號分隔候選來源順序，預設 arxiv,semantic_scholar,openalex,google_scholar")
    hunt.add_argument("--arxiv-sleep-seconds", type=float, default=ARXIV_REQUEST_INTERVAL_SECONDS)
    hunt.add_argument("--semantic-sleep-seconds", type=float, default=SEMANTIC_SCHOLAR_REQUEST_INTERVAL_SECONDS)
    hunt.add_argument("--openalex-sleep-seconds", type=float, default=0.2)
    hunt.add_argument("--google-scholar-sleep-seconds", type=float, default=2.0)
    hunt.add_argument("--google-scholar-api-key", help="SerpAPI key；未提供時會讀 GOOGLE_SCHOLAR_SERPAPI_KEY 或 SERPAPI_API_KEY")
    hunt.add_argument("--skip-semantic-scholar", action="store_true", help="略過 Semantic Scholar candidate source，也略過 arXiv metadata enrichment")
    hunt.add_argument("--skip-semantic-scholar-enrichment", action="store_true", help="只略過 arXiv 結果的 Semantic Scholar metadata enrichment；仍可用 Semantic Scholar 搜候選")
    hunt.set_defaults(func=cmd_hunt)

    generate = sub.add_parser("generate-reports", help="依 selected papers 平行生成 Markdown / 影片報告：floor(n/2) 本地，其餘 NotebookLM")
    generate.add_argument("--input", default="outputs/daily_report.json", help="hunt 產生的 JSON 結果")
    generate.add_argument("--output-dir", default="outputs/generated_reports", help="報告與影片輸出目錄")
    generate.add_argument("--max-workers", type=int, default=4, help="平行處理 worker 數")
    generate.add_argument("--video-wait-timeout-seconds", type=int, default=30 * 60, help="NotebookLM video overview 最多等待秒數；預設 30 分鐘")
    generate.add_argument("--enable-tts", action="store_true", help="本地影片嘗試使用 edge-tts 產生繁中旁白；失敗則 fallback 靜音音軌")
    generate.set_defaults(func=cmd_generate_reports)

    refs = sub.add_parser("record-references", help="在清理本地報告/影片前，記錄本次 selected papers 引用的 references")
    refs.add_argument("--input", default="outputs/daily_report.json", help="hunt 產生的 JSON 結果")
    refs.add_argument("--output-dir", default="outputs/references/latest")
    refs.add_argument("--limit-per-paper", type=int, default=50)
    refs.add_argument("--semantic-sleep-seconds", type=float, default=SEMANTIC_SCHOLAR_REQUEST_INTERVAL_SECONDS)
    refs.set_defaults(func=cmd_record_references)

    upload = sub.add_parser("upload-videos", help="用 OpenClaw CLI + webbridge 上傳 generated manifest 內的影片到 YouTube")
    upload.add_argument("--manifest", default="outputs/generated_reports/manifest.json")
    upload.add_argument("--privacy-status", default="unlisted", choices=["public", "unlisted", "private"])
    upload.add_argument("--max-workers", type=int, default=2, help="平行上傳 worker 數；避免同一瀏覽器互搶，預設 2")
    upload.add_argument("--timeout-seconds", type=int, default=3600)
    upload.set_defaults(func=cmd_upload_videos)

    publish = sub.add_parser("publish-github", help="清理目標 repo 的非網站產線說明，加入本 project，並把報告發布到 reports/")
    publish.add_argument("--manifest", default="outputs/generated_reports/manifest.json")
    publish.add_argument("--selection-json", default="outputs/daily_report.json")
    publish.add_argument("--repo-url", default="https://github.com/openclaw572/edge-ai-papers.git")
    publish.add_argument("--checkout-dir", default="tmp/edge-ai-papers-publish")
    publish.add_argument("--project-dir", default=".")
    publish.add_argument("--branch", default="main")
    publish.add_argument("--run-date")
    publish.add_argument("--push", action="store_true", help="確認 commit 後推到 GitHub；未加時只在本地 commit")
    publish.set_defaults(func=cmd_publish_github)

    full = sub.add_parser("run-full-pipeline", help="串起 hunt → 生成報告/影片 → reference 紀錄 → YouTube → GitHub → 驗證後清理")
    full.add_argument("--project-dir", default=".")
    full.add_argument("--profile", default="configs/research_profile.yaml")
    full.add_argument("--profile-id")
    full.add_argument("--repo-url", default="https://github.com/openclaw572/edge-ai-papers.git")
    full.add_argument("--checkout-dir", default="tmp/edge-ai-papers-publish")
    full.add_argument("--run-date")
    full.add_argument("--max-workers", type=int, default=4)
    full.add_argument("--youtube-workers", type=int, default=2)
    full.add_argument("--push-github", action="store_true")
    full.add_argument("--no-cleanup", action="store_true", help="即使遠端發布成功也保留本地 generated reports/videos")
    full.add_argument("--enable-tts", action="store_true")
    full.add_argument("--email-recipient", default="openclaw572@gmail.com", help="完整任務結束後由 Codex CLI 寄送 Gmail 通知的收件人")
    full.add_argument("--skip-email", action="store_true", help="測試或手動重跑時略過 Codex Gmail 通知")
    full.set_defaults(func=cmd_run_full_pipeline)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
