"""Proceedings detection and writeout helpers."""

from __future__ import annotations

import json
import re
from pathlib import Path

from scholaraio.index import build_proceedings_index
from scholaraio.papers import generate_uuid

_TITLE_KEYWORDS = (
    "proceedings of",
    "conference proceedings",
    "symposium proceedings",
    "workshop proceedings",
)

_TOC_PATTERNS = (
    "table of contents",
    "contents",
)

_DOI_RE = re.compile(r"10\.\d{4,}/[^\s)]+", re.IGNORECASE)
_PAPER_SPLIT_RE = re.compile(r"^##\s*Paper:\s*(.+)$", re.MULTILINE)


def looks_like_proceedings_text(text: str) -> bool:
    lowered = text.lower()
    if any(keyword in lowered for keyword in _TITLE_KEYWORDS):
        return True
    if any(marker in lowered for marker in _TOC_PATTERNS) and len(set(_DOI_RE.findall(text))) >= 2:
        return True
    return len(set(_DOI_RE.findall(text))) >= 3


def detect_proceedings_from_md(md_path: Path, *, force: bool = False) -> tuple[bool, str]:
    """Detect whether a markdown file appears to represent a proceedings volume."""
    if force:
        return True, "manual_inbox"

    text = md_path.read_text(encoding="utf-8", errors="replace")
    lowered = text.lower()

    if any(keyword in lowered for keyword in _TITLE_KEYWORDS):
        return True, "title_keyword"
    if any(marker in lowered for marker in _TOC_PATTERNS):
        return True, "table_of_contents"
    if len(set(_DOI_RE.findall(text))) >= 3:
        return True, "multi_doi"
    return False, ""


def _slugify(text: str) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff\s-]", "", text, flags=re.UNICODE)
    cleaned = re.sub(r"\s+", "-", cleaned.strip())
    return cleaned[:80].strip("-") or "untitled"


def _split_proceedings_markdown(text: str) -> list[dict]:
    matches = list(_PAPER_SPLIT_RE.finditer(text))
    papers: list[dict] = []
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        chunk = text[start:end].strip()
        lines = [line.strip() for line in chunk.splitlines() if line.strip()]
        title = match.group(1).strip()
        author = lines[1] if len(lines) > 1 else ""
        doi_match = _DOI_RE.search(chunk)
        papers.append(
            {
                "title": title,
                "authors": [author] if author else [],
                "doi": doi_match.group(0) if doi_match else "",
                "abstract": "\n".join(lines[3:]).strip() if len(lines) > 3 else "",
                "paper_type": "conference-paper",
                "markdown": f"# {title}\n\n" + "\n".join(lines[1:]).strip(),
            }
        )
    return papers


def ingest_proceedings_markdown(proceedings_root: Path, md_path: Path, *, source_name: str = "") -> Path:
    """Write a proceedings volume and its child papers under data/proceedings."""
    text = md_path.read_text(encoding="utf-8", errors="replace")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = lines[0].lstrip("# ").strip() if lines else md_path.stem
    child_papers = _split_proceedings_markdown(text)

    proceeding_dir = proceedings_root / _slugify(title)
    suffix = 2
    while proceeding_dir.exists():
        proceeding_dir = proceedings_root / f"{_slugify(title)}-{suffix}"
        suffix += 1
    (proceeding_dir / "papers").mkdir(parents=True)

    proceeding_meta = {
        "id": generate_uuid(),
        "title": title,
        "source_file": source_name or md_path.name,
        "child_paper_count": len(child_papers),
    }
    (proceeding_dir / "meta.json").write_text(json.dumps(proceeding_meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (proceeding_dir / "proceeding.md").write_text(text, encoding="utf-8")

    for paper in child_papers:
        paper_dir = proceeding_dir / "papers" / _slugify(paper["title"])
        paper_dir.mkdir(parents=True, exist_ok=True)
        paper_meta = {
            "id": generate_uuid(),
            "title": paper["title"],
            "authors": paper["authors"],
            "year": "",
            "journal": "",
            "doi": paper["doi"],
            "abstract": paper["abstract"],
            "paper_type": paper["paper_type"],
            "proceeding_id": proceeding_meta["id"],
            "proceeding_title": proceeding_meta["title"],
            "proceeding_dir": proceeding_dir.name,
        }
        (paper_dir / "meta.json").write_text(json.dumps(paper_meta, ensure_ascii=False, indent=2), encoding="utf-8")
        (paper_dir / "paper.md").write_text(paper["markdown"], encoding="utf-8")

    build_proceedings_index(proceedings_root, proceedings_root / "proceedings.db", rebuild=True)
    return proceeding_dir
