from __future__ import annotations

import json
from pathlib import Path

from scholaraio.ingest.proceedings import (
    detect_proceedings_from_md,
    ingest_proceedings_markdown,
    looks_like_proceedings_text,
)
from scholaraio.index import build_proceedings_index, search_proceedings
from scholaraio.proceedings import iter_proceedings_papers


def _write_proceedings_fixture(root: Path) -> Path:
    proceedings_root = root / "proceedings"
    proceedings_dir = proceedings_root / "Zheng-2024-IUTAM"
    papers_dir = proceedings_dir / "papers"
    papers_dir.mkdir(parents=True)

    (proceedings_dir / "meta.json").write_text(
        json.dumps(
            {
                "id": "proc-1",
                "title": "Example Proceedings",
                "year": 2024,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    paper_a = papers_dir / "Alpha-2024-Waves"
    paper_a.mkdir()
    (paper_a / "meta.json").write_text(
        json.dumps(
            {
                "id": "proc-paper-1",
                "title": "Wave propagation in porous media",
                "authors": ["Alice Zheng"],
                "year": 2024,
                "doi": "10.1000/example.1",
                "abstract": "Wave propagation in porous media with granular damping.",
                "paper_type": "conference-paper",
                "proceeding_title": "Example Proceedings",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (paper_a / "paper.md").write_text("# Wave propagation in porous media", encoding="utf-8")

    paper_b = papers_dir / "Beta-2024-Shocks"
    paper_b.mkdir()
    (paper_b / "meta.json").write_text(
        json.dumps(
            {
                "id": "proc-paper-2",
                "title": "Shock response of cellular materials",
                "authors": ["Bo Li"],
                "year": 2024,
                "doi": "10.1000/example.2",
                "abstract": "Shock response and granular collapse under impact.",
                "paper_type": "conference-paper",
                "proceeding_title": "Example Proceedings",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (paper_b / "paper.md").write_text("# Shock response of cellular materials", encoding="utf-8")

    return proceedings_root


def test_iter_proceedings_papers_yields_child_rows(tmp_path: Path):
    proceedings_root = _write_proceedings_fixture(tmp_path)

    papers = list(iter_proceedings_papers(proceedings_root))

    assert len(papers) == 2
    assert {p["proceeding_title"] for p in papers} == {"Example Proceedings"}
    assert {p["paper_id"] for p in papers} == {"proc-paper-1", "proc-paper-2"}


def test_build_and_search_proceedings_index_returns_matching_child_rows(tmp_path: Path):
    proceedings_root = _write_proceedings_fixture(tmp_path)
    db_path = tmp_path / "proceedings.db"

    count = build_proceedings_index(proceedings_root, db_path, rebuild=True)
    results = search_proceedings("granular", db_path, top_k=10)

    assert count == 2
    assert len(results) == 2
    assert {r["proceeding_title"] for r in results} == {"Example Proceedings"}
    assert {r["paper_id"] for r in results} == {"proc-paper-1", "proc-paper-2"}


def test_detect_proceedings_manual_mode_forces_true(tmp_path: Path):
    md_path = tmp_path / "volume.md"
    md_path.write_text("A perfectly ordinary paper body.", encoding="utf-8")

    detected, reason = detect_proceedings_from_md(md_path, force=True)

    assert detected is True
    assert reason == "manual_inbox"


def test_detect_proceedings_from_regular_inbox_cues(tmp_path: Path):
    md_path = tmp_path / "volume.md"
    md_path.write_text(
        "# Proceedings of the IUTAM Symposium on Granular Flow\n\n"
        "## Table of Contents\n\n"
        "1. Wave propagation in porous media\n"
        "2. Shock response of cellular materials\n\n"
        "10.1000/example.1\n"
        "10.1000/example.2\n",
        encoding="utf-8",
    )

    detected, reason = detect_proceedings_from_md(md_path)

    assert detected is True
    assert reason in {"title_keyword", "table_of_contents", "multi_doi"}


def test_detect_proceedings_rejects_regular_single_paper(tmp_path: Path):
    md_path = tmp_path / "paper.md"
    md_path.write_text(
        "# Boundary layer instability in compressible flow\n\n"
        "Alice Smith, Bob Wang\n\n"
        "10.1000/example.single\n\n"
        "This paper studies a single wave packet in compressible flow.\n",
        encoding="utf-8",
    )

    detected, reason = detect_proceedings_from_md(md_path)

    assert detected is False
    assert reason == ""
    assert looks_like_proceedings_text(md_path.read_text(encoding="utf-8")) is False


def test_ingest_proceedings_markdown_writes_volume_and_child_papers(tmp_path: Path):
    proceedings_root = tmp_path / "data" / "proceedings"
    proceedings_root.mkdir(parents=True)
    md_path = tmp_path / "volume.md"
    md_path.write_text(
        "# Proceedings of the IUTAM Symposium on Granular Flow\n\n"
        "## Paper: Wave propagation in porous media\n"
        "Alice Zheng\n"
        "10.1000/example.1\n"
        "Wave propagation in porous media with granular damping.\n\n"
        "## Paper: Shock response of cellular materials\n"
        "Bo Li\n"
        "10.1000/example.2\n"
        "Shock response and collapse under granular impact.\n",
        encoding="utf-8",
    )

    proceeding_dir = ingest_proceedings_markdown(
        proceedings_root,
        md_path,
        source_name="Zheng-2024-Proceedings of the IUTAM Symposium.pdf",
    )

    meta = json.loads((proceeding_dir / "meta.json").read_text(encoding="utf-8"))
    child_dirs = sorted((proceeding_dir / "papers").iterdir())
    child_meta = json.loads((child_dirs[0] / "meta.json").read_text(encoding="utf-8"))

    assert proceeding_dir.exists()
    assert meta["child_paper_count"] == 2
    assert child_meta["proceeding_title"] == meta["title"]
    assert len(child_dirs) == 2
