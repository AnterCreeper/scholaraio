from __future__ import annotations

import json
from pathlib import Path

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
