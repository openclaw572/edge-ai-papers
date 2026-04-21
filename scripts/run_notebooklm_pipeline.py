#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from pathlib import Path
from threading import Lock
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
HERMES_HOME = Path.home() / '.hermes'
DISCOVERY_SCRIPT = HERMES_HOME / 'skills' / 'research' / 'paper-discovery' / 'scripts' / 'paper_discovery.py'
NOTEBOOK_UPLOAD_SCRIPT = HERMES_HOME / 'scripts' / 'notebooklm_upload_probe.js'
NOTEBOOK_REPORT_SCRIPT = HERMES_HOME / 'scripts' / 'notebooklm_generate_report.js'
NOTEBOOK_VIDEO_SCRIPT = HERMES_HOME / 'scripts' / 'notebooklm_generate_video_summary.js'
NOTEBOOK_EXPORT_SCRIPT = REPO_ROOT / 'scripts' / 'notebooklm_export_report_markdown.js'
NOTEBOOK_DELETE_SCRIPT = REPO_ROOT / 'scripts' / 'notebooklm_delete_notebook.js'
NOTEBOOK_WAIT_VIDEO_SCRIPT = HERMES_HOME / 'scripts' / 'notebooklm_wait_for_video.js'
NOTEBOOK_DOWNLOAD_VIDEO_SCRIPT = HERMES_HOME / 'scripts' / 'notebooklm_download_video_artifact.sh'
YOUTUBE_UPLOAD_SCRIPT = REPO_ROOT / 'scripts' / 'upload_youtube_batch.py'
PUBLISH_SCRIPT = REPO_ROOT / 'scripts' / 'publish_notebooklm_batch.py'

TOPIC_TO_CATEGORY = {
    'edge-ai': 'Edge AI',
    'edge-ai-security': 'Edge AI Security',
    'embedded-security': 'Embedded Systems Security',
}
TOPIC_ORDER = ['edge-ai', 'edge-ai-security', 'embedded-security']
DEFAULT_NOTEBOOK_PROFILES = [
    str(Path.home() / '.hermes' / 'browser-profiles' / 'notebooklm'),
    str(Path.home() / '.hermes' / 'browser-profiles' / 'notebooklm-b'),
]
REVIEW_RE = re.compile(r'\b(review|survey|overview|tutorial|primer|systematic review|sok)\b', re.I)
PROCESSED_PAPERS_PATH = HERMES_HOME / 'papers' / 'processed_papers.json'
REVIEW_FALLBACK_QUERIES = {
    'edge-ai': [
        'edge ai review',
        'tinyml survey',
        'on-device machine learning review',
    ],
    'edge-ai-security': [
        'edge ai security survey',
        'federated learning security survey',
        'privacy attacks defenses survey federated learning',
    ],
    'embedded-security': [
        'embedded system security review',
        'hardware security review embedded',
        'iot embedded security survey',
    ],
}
CURATED_REVIEW_FALLBACKS = {
    'edge-ai': [
        {'title': 'Affordable Precision Agriculture: A Deployment-Oriented Review of Low-Cost, Low-Power Edge AI and TinyML for Resource-Constrained Farming Systems', 'arxiv_id': '2603.15085'},
        {'title': 'From Tiny Machine Learning to Tiny Deep Learning: A Survey', 'arxiv_id': '2506.18927'},
        {'title': 'Cognitive Edge Computing: A Comprehensive Survey on Optimizing Large Models and AI Agents for Pervasive Deployment', 'arxiv_id': '2501.03265'},
        {'title': 'Edge AI: A Taxonomy, Systematic Review and Future Directions', 'arxiv_id': '2407.04053'},
    ],
    'edge-ai-security': [
        {'title': 'The Federation Strikes Back: A Survey of Federated Learning Privacy Attacks, Defenses, Applications, and Policy Landscape', 'arxiv_id': '2405.03636'},
        {'title': 'Towards Resilient Federated Learning in CyberEdge Networks: Recent Advances and Future Trends', 'arxiv_id': '2504.01240'},
        {'title': 'SoK: Towards Security and Safety of Edge AI', 'arxiv_id': '2410.05349'},
    ],
    'embedded-security': [
        {'title': 'Modern Hardware Security: A Review of Attacks and Countermeasures', 'arxiv_id': '2501.04394'},
        {'title': 'SoK: Where\'s the "up"?! A Comprehensive (bottom-up) Study on the Security of Arm Cortex-M Systems', 'arxiv_id': '2401.15289'},
    ],
}
TOPIC_RELEVANCE = {
    'edge-ai': re.compile(r'\b(edge ai|tinyml|on-device|mobile ai|edge computing)\b', re.I),
    'edge-ai-security': re.compile(r'\b(edge ai|federated learning|privacy|adversarial|cyberedge|edge security)\b', re.I),
    'embedded-security': re.compile(r'\b(embedded|firmware|hardware security|cortex-m|microcontroller)\b', re.I),
}


def run(cmd: list[str], *, cwd: Path | None = None, timeout: int = 600, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, timeout=timeout)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(cmd)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9\u4e00-\u9fff]+', '-', text)
    return text.strip('-') or 'paper'


def is_review_paper(paper: dict[str, Any]) -> bool:
    hay = ' '.join([
        paper.get('title', ''),
        paper.get('venue', ''),
    ])
    return bool(REVIEW_RE.search(hay))


def is_direct_pdf_url(url: str | None) -> bool:
    if not url:
        return False
    u = url.lower()
    return u.endswith('.pdf') or 'arxiv.org/pdf/' in u or 'pdf' in u.split('?')[0].rsplit('/', 1)[-1]


def is_topic_relevant(topic: str, paper: dict[str, Any]) -> bool:
    pattern = TOPIC_RELEVANCE.get(topic)
    if not pattern:
        return True
    hay = ' '.join([
        paper.get('title', ''),
        paper.get('abstract', ''),
        paper.get('venue', ''),
    ])
    return bool(pattern.search(hay))


def normalize_paper_identity(value: str | None) -> str:
    if not value:
        return ''
    return re.sub(r'\s+', ' ', str(value).strip().lower())


def paper_identity(paper: dict[str, Any]) -> str:
    return normalize_paper_identity(
        paper.get('arxiv_id')
        or paper.get('doi')
        or paper.get('paper_id')
        or paper.get('url')
        or paper.get('arxiv_url')
        or paper.get('title')
    )


def load_processed_ids() -> set[str]:
    if not PROCESSED_PAPERS_PATH.exists():
        return set()
    try:
        data = json.loads(PROCESSED_PAPERS_PATH.read_text(encoding='utf-8'))
        if isinstance(data, list):
            return {normalize_paper_identity(x) for x in data if normalize_paper_identity(x)}
        if isinstance(data, dict):
            return {normalize_paper_identity(x) for x in data.get('processed_papers', []) if normalize_paper_identity(x)}
    except Exception:
        return set()
    return set()


def save_processed_ids(processed_ids: set[str]) -> None:
    PROCESSED_PAPERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        'processed_papers': sorted(x for x in processed_ids if x),
        'updated_at': datetime.now(timezone(timedelta(hours=8))).isoformat(),
    }
    PROCESSED_PAPERS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def fallback_open_review_paper(topic: str, processed_ids: set[str]) -> dict[str, Any] | None:
    queries = REVIEW_FALLBACK_QUERIES.get(topic, [])
    ns = {'a': 'http://www.w3.org/2005/Atom'}
    for query in queries:
        url = (
            'https://export.arxiv.org/api/query?search_query=' +
            urllib.parse.quote(f'all:"{query}"') +
            '&max_results=8&sortBy=submittedDate&sortOrder=descending'
        )
        with urllib.request.urlopen(url, timeout=30) as resp:
            body = resp.read().decode('utf-8', errors='ignore')
        if not body.startswith('<?xml'):
            continue
        root = ET.fromstring(body)
        for entry in root.findall('a:entry', ns):
            title = (entry.findtext('a:title', default='', namespaces=ns) or '').replace('\n', ' ').strip()
            arxiv_url = (entry.findtext('a:id', default='', namespaces=ns) or '').strip()
            arxiv_id = arxiv_url.split('/abs/')[-1].split('v')[0] if arxiv_url else ''
            if not title or not arxiv_id:
                continue
            if not REVIEW_RE.search(title):
                continue
            if arxiv_id in processed_ids:
                continue
            authors = [a.findtext('a:name', default='', namespaces=ns).strip() for a in entry.findall('a:author', ns)]
            published = (entry.findtext('a:published', default='', namespaces=ns) or '')[:10]
            summary = (entry.findtext('a:summary', default='', namespaces=ns) or '').strip()
            return {
                'paper_id': None,
                'arxiv_id': arxiv_id,
                'doi': None,
                'title': title,
                'authors': [a for a in authors if a],
                'published': published,
                'abstract': summary,
                'categories': [],
                'pdf_url': f'https://arxiv.org/pdf/{arxiv_id}.pdf',
                'arxiv_url': f'https://arxiv.org/abs/{arxiv_id}',
                'source': 'arxiv-fallback-review',
                'venue': 'arXiv',
                'citations': 0,
                'url': f'https://arxiv.org/abs/{arxiv_id}',
                'access': 'open',
                'topic': topic,
                'credibility_score': 50.0,
            }
        time.sleep(1)
    return None


def curated_review_fallback(topic: str, processed_ids: set[str]) -> dict[str, Any] | None:
    for item in CURATED_REVIEW_FALLBACKS.get(topic, []):
        arxiv_id = item['arxiv_id']
        if arxiv_id in processed_ids:
            continue
        return {
            'paper_id': None,
            'arxiv_id': arxiv_id,
            'doi': None,
            'title': item['title'],
            'authors': [],
            'published': '',
            'abstract': '',
            'categories': [],
            'pdf_url': f'https://arxiv.org/pdf/{arxiv_id}.pdf',
            'arxiv_url': f'https://arxiv.org/abs/{arxiv_id}',
            'source': 'curated-review-fallback',
            'venue': 'arXiv',
            'citations': 0,
            'url': f'https://arxiv.org/abs/{arxiv_id}',
            'access': 'open',
            'topic': topic,
            'credibility_score': 45.0,
        }
    return None


def extract_json_object(text: str) -> dict[str, Any]:
    text = (text or '').strip()
    start = text.find('{')
    end = text.rfind('}')
    if start < 0 or end < start:
        raise ValueError(f'No JSON object found in: {text[:500]}')
    return json.loads(text[start:end + 1])


def heuristic_value_score(paper: dict[str, Any], mode: str) -> float:
    score = float(paper.get('credibility_score') or 0)
    title = (paper.get('title') or '').lower()
    abstract = (paper.get('abstract') or '').lower()
    hay = f'{title} {abstract}'
    if mode == 'review':
        if REVIEW_RE.search(title):
            score += 20
        for needle in ['survey', 'review', 'overview', 'systematic', 'taxonomy', 'benchmark']:
            if needle in hay:
                score += 4
    for needle in ['deployment', 'efficient', 'resource-constrained', 'tinyml', 'edge', 'on-device', 'federated']:
        if needle in hay:
            score += 2
    if paper.get('source') in {'dblp-open', 'arxiv'}:
        score += 3
    if paper.get('citations', 0) >= 20:
        score += 3
    return round(score, 2)


def llm_rank_topic_candidates(topic: str, mode: str, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    shortlist = []
    for idx, paper in enumerate(candidates[:5]):
        shortlist.append({
            'index': idx,
            'title': paper.get('title', ''),
            'published': paper.get('published', ''),
            'venue': paper.get('venue', ''),
            'source': paper.get('source', ''),
            'citations': paper.get('citations', 0),
            'credibility_score': paper.get('credibility_score', 0),
            'heuristic_value_score': heuristic_value_score(paper, mode),
            'abstract': (paper.get('abstract', '') or '')[:900],
        })
    prompt = (
        'You are selecting one paper candidate for the edge-ai-papers website. '\
        'Goal: choose the single best candidate for credibility, reader value, and usefulness as a notebook/report/video article. '\
        'Prefer strong review/survey/overview papers when mode=review. '\
        'Do not pick based only on novelty; credibility and substance matter more.\n\n'
        f'Topic: {topic}\n'
        f'Mode: {mode}\n\n'
        'Return JSON only with this exact schema: '\
        '{"selected_index": <int>, "reason": "<short reason>", "confidence": <0-100>}\n\n'
        f'Candidates:\n{json.dumps(shortlist, ensure_ascii=False, indent=2)}'
    )
    try:
        res = run(['hermes', 'chat', '-Q', '--source', 'tool', '--max-turns', '1', '-q', prompt], timeout=240)
        parsed = extract_json_object(res.stdout)
        idx = parsed.get('selected_index')
        if not isinstance(idx, int) or idx < 0 or idx >= len(shortlist):
            raise ValueError(f'Invalid selected_index from LLM: {parsed}')
        return parsed
    except Exception as exc:
        print(f'LLM ranking failed for topic {topic}: {exc}', file=sys.stderr)
        return None


def choose_best_paper(topic: str, mode: str, papers: list[dict[str, Any]]) -> dict[str, Any]:
    ranked = sorted(
        papers,
        key=lambda p: (
            heuristic_value_score(p, mode),
            float(p.get('credibility_score') or 0),
            int(p.get('citations') or 0),
            p.get('published', ''),
        ),
        reverse=True,
    )
    llm_choice = llm_rank_topic_candidates(topic, mode, ranked)
    if llm_choice:
        chosen = dict(ranked[llm_choice['selected_index']])
        chosen['_selection'] = {
            'method': 'hybrid_llm',
            'reason': llm_choice.get('reason', ''),
            'confidence': llm_choice.get('confidence'),
        }
        return chosen
    chosen = dict(ranked[0])
    chosen['_selection'] = {'method': 'heuristic_fallback'}
    return chosen


def select_papers(mode: str, topics: list[str], workspace: Path, max_per_search: int = 40, candidates_per_topic: int = 8) -> list[dict[str, Any]]:
    selected = []
    processed_ids = load_processed_ids()
    selected_ids = set(processed_ids)
    for topic in topics:
        out = workspace / f'{topic}-candidates.json'
        cmd = [
            sys.executable,
            str(DISCOVERY_SCRIPT),
            '--topics', topic,
            '--papers-per-topic', str(candidates_per_topic),
            '--max-per-search', str(max_per_search),
            '--mode', mode,
            '--output', str(out),
        ]
        discovery_failed = False
        try:
            run(cmd, timeout=900)
        except RuntimeError as exc:
            discovery_failed = True
            print(f'Paper discovery failed for topic {topic}: {exc}', file=sys.stderr)
        if out.exists():
            data = json.loads(out.read_text(encoding='utf-8'))
        else:
            data = {'papers': [], 'metadata': {'discovery_failed': discovery_failed}}
        papers = data.get('papers', [])
        papers = [p for p in papers if is_direct_pdf_url(p.get('pdf_url')) and is_topic_relevant(topic, p)]
        papers = [p for p in papers if paper_identity(p) and paper_identity(p) not in selected_ids]
        if not papers and mode == 'review':
            fallback = fallback_open_review_paper(topic, selected_ids)
            if fallback:
                papers = [fallback]
        if not papers and mode == 'review':
            curated = curated_review_fallback(topic, selected_ids)
            if curated:
                papers = [curated]
        if not papers:
            raise RuntimeError(f'No unused {mode} paper with pdf_url found for topic {topic}')
        chosen = choose_best_paper(topic, mode, papers)
        selected.append(chosen)
        selected_ids.add(paper_identity(chosen))
    return selected


def download_pdf(url: str, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    run(['curl', '-L', '--fail', '-o', str(out_path), url], timeout=300)
    return out_path


def parse_json_stdout(stdout: str) -> dict[str, Any]:
    text = stdout.strip()
    start = text.find('{')
    if start < 0:
        raise ValueError(f'No JSON object in output: {stdout[:500]}')
    return json.loads(text[start:])


def create_notebook_and_upload(pdf_path: Path, profile: str) -> dict[str, Any]:
    res = run(['node', str(NOTEBOOK_UPLOAD_SCRIPT), '--profile', profile, '--pdf', str(pdf_path), '--hold', '0'], timeout=600)
    data = parse_json_stdout(res.stdout)
    return data['state']


def generate_report(notebook_url: str, source_label: str, paper_title: str, profile: str) -> None:
    report_label = 'Briefing Doc' if is_review_paper({'title': paper_title}) else 'Create Your Own'
    run([
        'node', str(REPO_ROOT / 'scripts' / 'notebooklm_generate_report_min.js'),
        '--headless',
        '--profile', profile,
        '--url', notebook_url,
        '--source-label', source_label,
        '--report-label', report_label,
    ], timeout=600)


def generate_video(notebook_url: str, source_label: str, paper_title: str, profile: str) -> None:
    run([
        'node', str(NOTEBOOK_VIDEO_SCRIPT),
        '--profile', profile,
        '--url', notebook_url,
        '--source-label', source_label,
        '--paper-title', paper_title,
        '--mode', 'auto',
        '--hold', '0',
    ], timeout=600)


def export_report_markdown(notebook_url: str, title_hint: str, out_path: Path, profile: str, source_label: str = '') -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        'node', str(NOTEBOOK_EXPORT_SCRIPT),
        '--profile', profile,
        '--url', notebook_url,
        '--output', str(out_path),
    ]
    if title_hint:
        cmd += ['--title-hint', title_hint]
    if source_label:
        cmd += ['--source-label', source_label]
    run(cmd, timeout=600)
    return out_path


def wait_and_download_video(notebook_url: str, out_dir: Path, profile: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    run(['node', str(NOTEBOOK_WAIT_VIDEO_SCRIPT), '--profile', profile, '--url', notebook_url, '--timeout-sec', '1200', '--poll-sec', '20'], timeout=1500)
    res = run(['bash', str(NOTEBOOK_DOWNLOAD_VIDEO_SCRIPT), '--profile', profile, '--url', notebook_url, '--out-dir', str(out_dir)], timeout=1200)
    m = re.search(r'Saved video to (.+\\.mp4)', res.stdout + '\n' + res.stderr)
    if not m:
        mp4s = sorted(out_dir.glob('*.mp4'))
        if not mp4s:
            raise RuntimeError(f'Could not determine downloaded video path\n{res.stdout}\n{res.stderr}')
        return mp4s[-1]
    return Path(m.group(1).strip())


def delete_notebook(notebook_url: str, title_hint: str, profile: str) -> dict[str, Any]:
    cmd = [
        'node', str(NOTEBOOK_DELETE_SCRIPT),
        '--profile', profile,
        '--url', notebook_url,
        '--headless',
    ]
    if title_hint:
        cmd += ['--title-hint', title_hint]
    res = run(cmd, timeout=600)
    return json.loads(res.stdout)


def _safe_unlink(path: Path, workspace_root: Path) -> bool:
    try:
        resolved = path.resolve()
        workspace_resolved = workspace_root.resolve()
    except FileNotFoundError:
        return False
    if workspace_resolved not in resolved.parents and resolved != workspace_resolved:
        raise RuntimeError(f'Refusing to delete path outside workspace: {resolved}')
    if resolved.exists() and resolved.is_file():
        resolved.unlink()
        return True
    return False


def cleanup_local_artifacts(paper: dict[str, Any], workspace_root: Path) -> dict[str, Any]:
    removed: list[str] = []
    missing: list[str] = []
    errors: list[str] = []

    targets: list[Path] = []
    markdown_source = paper.get('markdown_source')
    if markdown_source:
        md_path = Path(markdown_source)
        targets.append(md_path)
        targets.append(md_path.parent / 'report.md')

    video_file = paper.get('video_file')
    if video_file:
        video_path = Path(video_file)
        targets.append(video_path)
        if video_path.parent.name == 'video':
            targets.extend(sorted(video_path.parent.glob('*')))

    seen = set()
    unique_targets: list[Path] = []
    for target in targets:
        key = str(target)
        if key not in seen:
            seen.add(key)
            unique_targets.append(target)

    for target in unique_targets:
        try:
            if _safe_unlink(target, workspace_root):
                removed.append(str(target))
            else:
                missing.append(str(target))
        except Exception as exc:
            errors.append(f'{target}: {exc}')

    candidate_dirs = []
    if markdown_source:
        candidate_dirs.append(Path(markdown_source).parent)
    if video_file:
        candidate_dirs.append(Path(video_file).parent)
    for directory in candidate_dirs:
        try:
            resolved = directory.resolve()
            workspace_resolved = workspace_root.resolve()
            if workspace_resolved not in resolved.parents and resolved != workspace_resolved:
                raise RuntimeError(f'Refusing to touch directory outside workspace: {resolved}')
            if resolved.exists() and resolved.is_dir() and not any(resolved.iterdir()):
                resolved.rmdir()
        except FileNotFoundError:
            continue
        except Exception as exc:
            errors.append(f'{directory}: {exc}')

    return {
        'paper_id': paper.get('id'),
        'removed': removed,
        'missing': missing,
        'errors': errors,
    }


def post_publish_cleanup(manifest_data: dict[str, Any], workspace_root: Path) -> dict[str, Any]:
    notebook_results = []
    local_results = []
    errors = []
    for paper in manifest_data.get('papers', []):
        notebook_url = paper.get('notebook_url')
        profile = paper.get('profile_used')
        title = paper.get('title', '')
        if notebook_url and profile:
            try:
                notebook_results.append({
                    'paper_id': paper.get('id'),
                    'deleted': True,
                    'result': delete_notebook(notebook_url, title, profile),
                })
            except Exception as exc:
                notebook_results.append({
                    'paper_id': paper.get('id'),
                    'deleted': False,
                    'error': str(exc),
                })
                errors.append(f"delete notebook failed for {paper.get('id')}: {exc}")
        else:
            notebook_results.append({
                'paper_id': paper.get('id'),
                'deleted': False,
                'skipped': True,
                'reason': 'missing notebook_url or profile_used',
            })

        local_result = cleanup_local_artifacts(paper, workspace_root)
        local_results.append(local_result)
        if local_result['errors']:
            errors.extend([f"local cleanup failed for {paper.get('id')}: {msg}" for msg in local_result['errors']])

    return {
        'performed': True,
        'notebooks': notebook_results,
        'local_artifacts': local_results,
        'errors': errors,
    }


def normalize_exported_markdown(src: Path, paper: dict[str, Any], youtube_url: str | None = None) -> str:
    text = src.read_text(encoding='utf-8')
    lines = text.splitlines()
    if lines and lines[0].strip() == '---':
        end = None
        for i in range(1, len(lines)):
            if lines[i].strip() == '---':
                end = i
                break
        if end is not None:
            lines = lines[end + 1:]
    while lines and not lines[0].strip():
        lines.pop(0)
    cleaned = []
    skip_next_separator = False
    title_line = None
    for line in lines:
        s = line.strip()
        if title_line is None and s.startswith('# '):
            title_line = s
        if s.startswith('导出时间:') or s.startswith('Exported:'):
            skip_next_separator = True
            continue
        if skip_next_separator and s == '---':
            skip_next_separator = False
            continue
        cleaned.append(line)
    body = '\n'.join(cleaned).strip() + '\n'
    body = body.replace('\\--------------------------------------------------------------------------------', '---')
    kind = 'Review Paper' if is_review_paper(paper) else 'General Paper'
    wrapper = [
        f"## {paper['title']}",
        '',
        f"**類別：** {TOPIC_TO_CATEGORY.get(paper['topic'], paper['topic'])}（{kind}）  ",
        f"**來源：** {paper.get('source', '')}  ",
        f"**發表年份：** {(paper.get('published', '') or '')[:4]}  ",
        f"**作者：** {', '.join(paper.get('authors', [])[:6]) or '未整理（待補）'}  ",
        f"**連結：** {paper.get('pdf_url') or paper.get('url') or paper.get('arxiv_url') or ''}",
        '',
        '### NotebookLM 報告（Markdown Export）',
        '',
        body.rstrip(),
    ]
    if youtube_url:
        wrapper += ['', '### 影片報告', f'- YouTube：{youtube_url}']
    return '\n'.join(wrapper).rstrip() + '\n'


def write_wrapped_markdown(export_md: Path, out_path: Path, paper: dict[str, Any]) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(normalize_exported_markdown(export_md, paper), encoding='utf-8')
    return out_path


def build_manifest(papers: list[dict[str, Any]], work_dir: Path, mode: str, run_date: str) -> Path:
    manifest = {
        'date': run_date,
        'paperType': 'review' if mode == 'review' else 'general',
        'generatedAt': datetime.now(timezone(timedelta(hours=8))).isoformat(),
        'papers': papers,
    }
    path = work_dir / 'manifest.json'
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return path


def parse_profiles_arg(profiles_arg: str) -> list[str]:
    profiles = [p.strip() for p in profiles_arg.split(',') if p.strip()]
    return profiles or DEFAULT_NOTEBOOK_PROFILES


def is_video_limit_error(exc: Exception) -> bool:
    text = str(exc)
    needles = [
        'Video overview daily limit reached',
        '影片摘要使用次數已達每日上限',
        'daily limit',
        'try again later',
        'Could not open video artifact',
    ]
    t = text.lower()
    return any(n.lower() in t for n in needles)


def process_one_paper(idx: int, paper: dict[str, Any], mode: str, work_dir: Path, profiles: list[str], profile_locks: dict[str, Lock], start_profile_index: int = 0, skip_youtube: bool = False) -> dict[str, Any]:
    last_exc = None
    ordered_profiles = profiles[start_profile_index:] + profiles[:start_profile_index]
    for attempt, profile in enumerate(ordered_profiles, start=1):
        lock = profile_locks[profile]
        with lock:
            try:
                topic = paper['topic']
                category = TOPIC_TO_CATEGORY.get(topic, topic)
                paper_dir = work_dir / f'paper-{idx}'
                if paper_dir.exists():
                    shutil.rmtree(paper_dir)
                paper_dir.mkdir(parents=True, exist_ok=True)
                pdf_path = download_pdf(paper['pdf_url'], paper_dir / f'paper-{idx}.pdf')
                notebook = create_notebook_and_upload(pdf_path, profile)
                notebook_url = notebook['url']
                source_label = pdf_path.name

                generate_report(notebook_url, source_label, paper['title'], profile)
                export_md = export_report_markdown(notebook_url, '', paper_dir / 'report.md', profile, source_label)
                wrapped_md = write_wrapped_markdown(export_md, paper_dir / 'report_wrapped.md', paper)

                video_path = None
                video_status = 'skipped' if skip_youtube else 'pending'
                video_error = None
                youtube_url = None
                if not skip_youtube:
                    try:
                        generate_video(notebook_url, source_label, paper['title'], profile)
                        video_path = wait_and_download_video(notebook_url, paper_dir / 'video', profile)
                        video_status = 'ok'
                    except Exception as exc:
                        if is_video_limit_error(exc):
                            if attempt < len(ordered_profiles):
                                last_exc = exc
                                continue
                            video_status = 'skipped_daily_limit'
                            video_error = f'All profiles hit video daily limit; skipped video for this paper. Last error: {exc}'
                        else:
                            video_status = 'failed'
                            video_error = str(exc)

                result = {
                    'id': f'paper-{idx}',
                    'category': category,
                    'title': paper['title'],
                    'slug': f"paper-{idx}-{slugify(category)}-{slugify(paper['title'])[:80]}",
                    'link': paper.get('pdf_url') or paper.get('url') or '',
                    'type': 'REVIEW PAPER' if mode == 'review' else 'GENERAL PAPER',
                    'tags': [category, 'Review Paper' if mode == 'review' else 'General Paper'],
                    'markdown_source': str(wrapped_md),
                    'video_file': str(video_path) if video_path else '',
                    'source': paper.get('source', ''),
                    'year': (paper.get('published', '') or '')[:4],
                    'authors': ', '.join(paper.get('authors', [])[:6]),
                    'notebook_url': notebook_url,
                    'privacy_status': 'unlisted',
                    'profile_used': profile,
                    'video_status': video_status,
                }
                if video_error:
                    result['video_error'] = video_error
                if youtube_url:
                    result['youtube_url'] = youtube_url
                return result
            except Exception as exc:
                last_exc = exc
                if attempt < len(ordered_profiles):
                    continue
    raise RuntimeError(f'Failed to process paper-{idx} across profiles: {last_exc}')


def process_papers_parallel(selected: list[dict[str, Any]], mode: str, work_dir: Path, profiles: list[str], max_parallel: int, skip_youtube: bool) -> list[dict[str, Any]]:
    max_workers = max(1, min(max_parallel, len(profiles), len(selected)))
    profile_locks = {profile: Lock() for profile in profiles}
    results: dict[int, dict[str, Any]] = {}
    futures = {}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for idx, paper in enumerate(selected, start=1):
            start_profile_index = (idx - 1) % len(profiles)
            fut = ex.submit(process_one_paper, idx, paper, mode, work_dir, profiles, profile_locks, start_profile_index, skip_youtube)
            futures[fut] = idx
        for fut in as_completed(futures):
            idx = futures[fut]
            results[idx] = fut.result()
    return [results[i] for i in sorted(results)]


def git_commit_push(repo: Path, run_date: str, push: bool = True):
    run(['git', 'add', f'reports/{run_date}', 'reports/index.json'], cwd=repo, timeout=120)
    status = run(['git', 'status', '--short'], cwd=repo, timeout=120).stdout.strip()
    if not status:
        return {'committed': False, 'pushed': False}
    run(['git', 'commit', '-m', f'feat: add {run_date} automated review paper batch'], cwd=repo, timeout=300)
    if push:
        run(['git', 'push', 'origin', 'main'], cwd=repo, timeout=300)
    return {'committed': True, 'pushed': push}


def main() -> int:
    parser = argparse.ArgumentParser(description='Run end-to-end NotebookLM paper pipeline')
    parser.add_argument('--mode', default='review', choices=['review', 'general'])
    parser.add_argument('--topics', default=','.join(TOPIC_ORDER))
    parser.add_argument('--run-date', default=datetime.now(timezone(timedelta(hours=8))).date().isoformat())
    parser.add_argument('--workspace', default='')
    parser.add_argument('--profiles', default=','.join(DEFAULT_NOTEBOOK_PROFILES))
    parser.add_argument('--max-parallel', type=int, default=3)
    parser.add_argument('--discover-only', action='store_true')
    parser.add_argument('--skip-youtube', action='store_true')
    parser.add_argument('--skip-push', action='store_true')
    args = parser.parse_args()

    topics = [t.strip() for t in args.topics.split(',') if t.strip()]
    profiles = parse_profiles_arg(args.profiles)
    work_dir = Path(args.workspace) if args.workspace else (Path('/tmp') / f'edge-ai-pipeline-{args.run_date}')
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    selected = select_papers(args.mode, topics, work_dir)
    if args.discover_only:
        print(json.dumps({'mode': args.mode, 'run_date': args.run_date, 'selected': selected}, ensure_ascii=False, indent=2))
        return 0

    manifest_papers = process_papers_parallel(
        selected=selected,
        mode=args.mode,
        work_dir=work_dir,
        profiles=profiles,
        max_parallel=args.max_parallel,
        skip_youtube=args.skip_youtube,
    )

    manifest_path = build_manifest(manifest_papers, work_dir, args.mode, args.run_date)

    if not args.skip_youtube:
        run([sys.executable, str(YOUTUBE_UPLOAD_SCRIPT), '--manifest', str(manifest_path), '--write-back', '--privacy-status', 'unlisted'], cwd=REPO_ROOT, timeout=1800)

    manifest_data = json.loads(manifest_path.read_text(encoding='utf-8'))

    run([sys.executable, str(PUBLISH_SCRIPT), str(manifest_path)], cwd=REPO_ROOT, timeout=600)
    git_result = git_commit_push(REPO_ROOT, args.run_date, push=not args.skip_push)
    processed_update = {'updated': False, 'reason': 'processed paper registry updates only after a successful git push'}
    if git_result.get('pushed'):
        processed_ids = load_processed_ids()
        new_ids = {paper_identity(p) for p in selected if paper_identity(p)}
        processed_ids.update(new_ids)
        save_processed_ids(processed_ids)
        processed_update = {
            'updated': True,
            'count_added': len(new_ids),
            'processed_registry': str(PROCESSED_PAPERS_PATH),
            'added_ids': sorted(new_ids),
        }
    cleanup_result = {'performed': False, 'reason': 'cleanup requires a successful git push'}
    if git_result.get('pushed'):
        cleanup_result = post_publish_cleanup(manifest_data, work_dir)

    summary = {
        'ok': True,
        'mode': args.mode,
        'run_date': args.run_date,
        'workspace': str(work_dir),
        'manifest': str(manifest_path),
        'papers': manifest_data['papers'],
        'git': git_result,
        'processed_registry': processed_update,
        'cleanup': cleanup_result,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
