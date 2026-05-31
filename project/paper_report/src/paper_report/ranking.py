from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from datetime import date
from typing import Iterable

from .models import Paper, RankedPaper, ResearchProfile

_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_+-]*")
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "into", "is", "it", "of", "on",
    "or", "that", "the", "their", "this", "through", "to", "use", "using", "with", "we", "our", "via", "paper",
    "study", "system", "systems", "model", "models", "method", "methods", "approach", "benchmark",
}

SYNONYMS = {
    "coordination": ["coordinate", "coordinated", "coordinating", "collaboration", "collaborative"],
    "agent": ["agents", "autonomous", "tool-using", "tool", "multi-agent", "multiagent", "assistant", "assistants", "controller", "controllers"],
    "workspace": ["workspaces", "shared", "memory", "store", "stores"],
    "file": ["files", "file-based", "filesystem"],
    "log": ["logs", "append-only", "events", "event"],
    "lock": ["locks", "locking", "mutex"],
    "broker": ["brokers", "event-broker", "mediates", "mediated"],
    "planning": ["planner", "planners", "plans", "decomposes", "decompose", "goals", "long-horizon", "multi-step"],
    "reasoning": ["reason", "reflects", "reflection", "self-improvement", "evaluation", "evaluates"],
    "tool": ["tools", "apis", "api", "invocation", "calls", "external"],
    "security": ["secure", "safety", "harden", "hardens", "robustness", "threat", "threats", "tampering", "malicious", "attack", "attacks", "safe"],
    "privacy": ["confidential", "leakage", "secret", "secrets", "encrypted", "privacy-preserving"],
    "permission": ["permissions", "capability", "capabilities", "least-privilege", "sandbox", "sandboxing", "confines", "isolated", "isolation"],
    "exfiltration": ["exfiltrate", "exfiltrating", "leak", "leaks", "leakage"],
    "edge": ["on-device", "device", "devices", "iot", "mobile", "nodes", "node", "edge-deployed"],
    "embedded": ["microcontroller", "microcontrollers", "firmware", "interrupt", "flash", "sensor", "sensors", "cyber-physical", "resource-constrained"],
    "realtime": ["real-time", "timing", "bounded-latency", "latency", "scheduling"],
}


def tokenize(text: str) -> list[str]:
    raw = [t.lower().replace("-", "") for t in _TOKEN_RE.findall(text or "")]
    tokens = [t for t in raw if len(t) > 1 and t not in STOPWORDS]
    expanded: list[str] = []
    for token in tokens:
        expanded.append(token)
        for canonical, variants in SYNONYMS.items():
            if token == canonical or token in {v.replace("-", "") for v in variants}:
                expanded.append(canonical)
                break
    return expanded


def phrase_present(phrase: str, text: str) -> bool:
    compact_text = re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()
    compact_phrase = re.sub(r"[^a-z0-9]+", " ", phrase.lower()).strip()
    return bool(compact_phrase and compact_phrase in compact_text)


def hashed_embedding(text: str, dimensions: int = 512) -> list[float]:
    """Return a small local semantic-ish vector.

    This is intentionally not a plain keyword counter: tokens are expanded through
    the domain synonym map, bigrams are included, and exact phrase matches are only
    one weak feature later in the scoring pipeline. The vector uses positive hash
    buckets rather than signed random projection so short paper abstracts do not
    cancel their own evidence.
    """
    counts = Counter(tokenize(text))
    tokens = list(counts.keys())
    for a, b in zip(tokens, tokens[1:]):
        counts[f"{a}_{b}"] += 0.5
    vec = [0.0] * dimensions
    for token, count in counts.items():
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        idx = int.from_bytes(digest[:4], "big") % dimensions
        vec[idx] += 1.0 + math.log1p(count)
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return vec
    return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    return max(0.0, sum(x * y for x, y in zip(a, b)))


def seed_texts(profile: ResearchProfile) -> list[str]:
    texts: list[str] = []
    for seed in profile.positive_seed_papers:
        if isinstance(seed, dict):
            texts.append(" ".join(str(seed.get(k, "")) for k in ("title", "abstract", "summary")))
        elif isinstance(seed, str) and not seed.startswith("seed_paper_id_"):
            texts.append(seed)
    return [t for t in texts if t.strip()]


def positive_keyword_score(profile: ResearchProfile, paper_text: str) -> float:
    if not profile.positive_keywords:
        return 0.0
    hits = sum(1 for kw in profile.positive_keywords if phrase_present(kw, paper_text))
    return min(1.0, hits / max(1, min(4, len(profile.positive_keywords))))


def negative_keyword_penalty(profile: ResearchProfile, paper_text: str) -> float:
    hits = sum(1 for kw in profile.negative_keywords if phrase_present(kw, paper_text))
    return min(0.75, hits * 0.30)


def negated_domain_evidence_penalty(paper_text: str) -> float:
    """Penalize abstracts that mention domain concepts only to say they are absent.

    Example: "without tool use, planning, memory, or autonomous workflows" should
    not be treated as strong semantic evidence for an agentic-AI profile.
    """
    compact = re.sub(r"[^a-z0-9+-]+", " ", (paper_text or "").lower())
    concept = r"tool|api|planning|planner|memory|autonomous|workflow|security|privacy|firmware|microcontroller|edge|iot|embedded|real-time|sensor"
    patterns = [
        rf"\bwithout\b[^.%;]{{0,90}}\b({concept})\b",
        rf"\b(no|lacks?|lack of|not)\b[^.%;]{{0,60}}\b({concept})\b",
    ]
    hits = sum(len(re.findall(pattern, compact)) for pattern in patterns)
    return min(0.45, hits * 0.20)


def full_text_score(paper: Paper) -> float:
    if paper.pdf_url:
        return 1.0
    if paper.open_access and paper.url:
        return 0.7
    if paper.doi or paper.url:
        return 0.3
    return 0.0


def recency_score(paper: Paper, today: date | None = None) -> float:
    if paper.time_window == "recent_0_to_4_months":
        return 1.0
    if paper.time_window == "fallback_4_to_12_months":
        return 0.7
    if paper.time_window == "fallback_13_to_36_months":
        return 0.4
    if paper.time_window == "fallback_36_to_60_months":
        return 0.2
    if not today:
        today = date.today()
    published = paper.parsed_date()
    if not published:
        return 0.2
    days = (today - published).days
    if days <= 31 * 4:
        return 1.0
    if days <= 366:
        return 0.7
    if days <= 366 * 2:
        return 0.4
    return 0.2


def citation_signal(paper: Paper) -> float:
    total = max(0, paper.citation_count) + 2 * max(0, paper.influential_citation_count)
    return min(1.0, math.log1p(total) / math.log1p(100))


def code_or_project_signal(paper: Paper) -> float:
    text = " ".join([paper.title, paper.abstract, paper.url, paper.pdf_url] + [str(v) for v in paper.extra.values()]).lower()
    if any(token in text for token in ("github.com", " code ", "source code", "dataset", "project page", "repository")):
        return 1.0
    return 0.0


def semantic_relevance(profile: ResearchProfile, paper: Paper) -> tuple[float, float, float, float, float]:
    paper_text = f"{paper.title}\n{paper.abstract}"
    profile_sim = cosine(hashed_embedding(paper_text), hashed_embedding(profile.description))
    seed_sims = [cosine(hashed_embedding(paper_text), hashed_embedding(seed)) for seed in seed_texts(profile)]
    seed_sim = max(seed_sims) if seed_sims else profile_sim
    keyword_score = positive_keyword_score(profile, paper_text)
    penalty = negative_keyword_penalty(profile, paper_text) + negated_domain_evidence_penalty(paper_text)
    penalty = min(0.85, penalty)
    combined = (0.70 * profile_sim) + (0.25 * seed_sim) + (0.05 * keyword_score)
    # Local vectors are conservative compared with model embeddings; scale them into
    # the configured 0.0-1.0 threshold range. Exact positive keywords are deliberately
    # weak here: they help candidate recall, but should not dominate final selection.
    relevance = max(0.0, min(1.0, combined * 2.65 - penalty))
    if penalty:
        # Negative profile evidence means the paper is likely from a nearby but wrong
        # field (e.g. robot swarm / traffic control). Do not let keyword stuffing or
        # citation count push it above a clean semantic match.
        relevance = min(relevance, max(0.0, 0.50 - penalty * 0.25))
    return relevance, profile_sim, seed_sim, keyword_score, penalty


def rank_papers(profile: ResearchProfile, papers: Iterable[Paper], today: date | None = None) -> list[RankedPaper]:
    ranked: list[RankedPaper] = []
    for paper in papers:
        sem, profile_sim, seed_sim, kw_score, neg_penalty = semantic_relevance(profile, paper)
        rec = recency_score(paper, today=today)
        full = full_text_score(paper)
        cite = citation_signal(paper)
        code_signal = code_or_project_signal(paper)
        final = (0.45 * sem) + (0.20 * rec) + (0.15 * full) + (0.10 * cite) + (0.10 * code_signal)
        ranked.append(
            RankedPaper(
                paper=paper,
                semantic_relevance=round(sem, 4),
                profile_similarity=round(profile_sim, 4),
                seed_similarity=round(seed_sim, 4),
                positive_keyword_score=round(kw_score, 4),
                negative_keyword_penalty=round(neg_penalty, 4),
                recency_score=round(rec, 4),
                full_text_score=round(full, 4),
                citation_signal=round(cite, 4),
                code_or_project_signal=round(code_signal, 4),
                final_score=round(final, 4),
            )
        )
    return sorted(ranked, key=lambda p: (p.final_score, p.semantic_relevance, p.full_text_score), reverse=True)
