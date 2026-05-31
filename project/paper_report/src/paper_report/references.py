from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from .models import Paper, RankedPaper
from .report_generation import ranked_paper_from_dict
from .semantic_scholar import PAPER_API, semantic_scholar_headers

REFERENCE_FIELDS = "contexts,intents,isInfluential,citedPaper.paperId,citedPaper.title,citedPaper.authors,citedPaper.year,citedPaper.url,citedPaper.externalIds"


@dataclass(slots=True)
class ReferenceItem:
    title: str
    authors: list[str] = field(default_factory=list)
    year: str = ""
    url: str = ""
    paper_id: str = ""
    doi: str = ""
    arxiv_id: str = ""
    contexts: list[str] = field(default_factory=list)
    intents: list[str] = field(default_factory=list)
    is_influential: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class PaperReferences:
    citing_paper_title: str
    citing_paper_url: str = ""
    citing_paper_id: str = ""
    references: list[ReferenceItem] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "citing_paper_title": self.citing_paper_title,
            "citing_paper_url": self.citing_paper_url,
            "citing_paper_id": self.citing_paper_id,
            "references": [item.to_dict() for item in self.references],
            "error": self.error,
        }


def load_selected_ranked_papers(selection_json_path: str | Path) -> list[RankedPaper]:
    data = json.loads(Path(selection_json_path).read_text(encoding="utf-8"))
    return [ranked_paper_from_dict(item) for item in data.get("selected_papers", [])]


def semantic_scholar_identifier(paper: Paper) -> str:
    if paper.semantic_scholar_id:
        return paper.semantic_scholar_id
    if paper.doi:
        return f"DOI:{paper.doi}"
    if paper.arxiv_id:
        return f"arXiv:{paper.arxiv_id.split('v')[0]}"
    return ""


def _authors(raw: list[dict[str, Any]] | None) -> list[str]:
    return [item.get("name", "") for item in raw or [] if item.get("name")]


def _reference_from_s2(item: dict[str, Any]) -> ReferenceItem | None:
    cited = item.get("citedPaper") or {}
    title = cited.get("title") or ""
    if not title:
        return None
    external = cited.get("externalIds") or {}
    return ReferenceItem(
        title=title,
        authors=_authors(cited.get("authors")),
        year=str(cited.get("year") or ""),
        url=cited.get("url") or "",
        paper_id=cited.get("paperId") or "",
        doi=external.get("DOI") or external.get("doi") or "",
        arxiv_id=external.get("ArXiv") or external.get("arXiv") or external.get("ARXIV") or "",
        contexts=[str(context) for context in item.get("contexts") or [] if context],
        intents=[str(intent) for intent in item.get("intents") or [] if intent],
        is_influential=bool(item.get("isInfluential")),
    )


def fetch_references_for_paper(
    paper: Paper,
    *,
    limit: int = 50,
    session: requests.Session | None = None,
    sleep_seconds: float = 1.0,
) -> PaperReferences:
    identifier = semantic_scholar_identifier(paper)
    result = PaperReferences(
        citing_paper_title=paper.title,
        citing_paper_url=paper.url or paper.pdf_url,
        citing_paper_id=identifier,
    )
    if not identifier:
        result.error = "No Semantic Scholar / DOI / arXiv identifier available for reference lookup"
        return result
    http = session or requests.Session()
    try:
        response = http.get(
            f"{PAPER_API}/{identifier}/references",
            params={"fields": REFERENCE_FIELDS, "limit": limit},
            headers=semantic_scholar_headers(),
            timeout=30,
        )
        if response.status_code == 404:
            result.error = "Semantic Scholar references endpoint returned 404"
            return result
        response.raise_for_status()
        data = response.json()
        refs: list[ReferenceItem] = []
        for item in data.get("data") or []:
            ref = _reference_from_s2(item)
            if ref:
                refs.append(ref)
        result.references = refs
    except requests.RequestException as exc:
        result.error = str(exc)
    if sleep_seconds:
        time.sleep(sleep_seconds)
    return result


def record_references(
    selection_json_path: str | Path,
    output_dir: str | Path,
    *,
    limit_per_paper: int = 50,
    session: requests.Session | None = None,
    sleep_seconds: float = 1.0,
) -> tuple[Path, Path]:
    papers = load_selected_ranked_papers(selection_json_path)
    records = [
        fetch_references_for_paper(item.paper, limit=limit_per_paper, session=session, sleep_seconds=sleep_seconds) for item in papers
    ]
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "selected_paper_references.json"
    md_path = out / "selected_paper_references.md"
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_selection_json": str(selection_json_path),
        "papers": [record.to_dict() for record in records],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_references_markdown(payload), encoding="utf-8")
    return json_path, md_path


def render_references_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Selected Paper References",
        "",
        f"Generated at: {payload.get('generated_at', '')}",
        "",
        "此檔案在刪除本地報告 / 影片前產生，用來記錄本次選中 papers 引用過哪些 reference。",
        "",
    ]
    for paper in payload.get("papers") or []:
        lines.append(f"## Citing paper: {paper.get('citing_paper_title') or 'Untitled'}")
        if paper.get("citing_paper_url"):
            lines.append(f"- Citing paper URL: {paper['citing_paper_url']}")
        if paper.get("error"):
            lines.append(f"- Reference lookup note: {paper['error']}")
        refs = paper.get("references") or []
        if not refs:
            lines.extend(["", "No references recorded.", ""])
            continue
        lines.append("")
        for idx, ref in enumerate(refs, start=1):
            authors = ", ".join(ref.get("authors") or []) or "Unknown authors"
            url = ref.get("url") or (f"https://doi.org/{ref.get('doi')}" if ref.get("doi") else "")
            lines.append(f"{idx}. **{ref.get('title', 'Untitled')}** ({ref.get('year') or 'n.d.'})")
            lines.append(f"   - Authors: {authors}")
            if url:
                lines.append(f"   - URL: {url}")
            if ref.get("doi"):
                lines.append(f"   - DOI: {ref['doi']}")
            if ref.get("arxiv_id"):
                lines.append(f"   - arXiv: {ref['arxiv_id']}")
            if ref.get("contexts"):
                lines.append(f"   - Cited context: {ref['contexts'][0]}")
        lines.append("")
    return "\n".join(lines)
