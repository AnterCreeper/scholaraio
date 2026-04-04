"""Regression tests for ingest pipeline edge cases."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from scholaraio.ingest.metadata._api import query_semantic_scholar
from scholaraio.ingest.metadata._models import PaperMetadata
from scholaraio.ingest.pipeline import (
    InboxCtx,
    StepResult,
    _collect_existing_ids,
    step_dedup,
    step_extract,
    step_office_convert,
    step_translate,
)
from scholaraio.translate import SKIP_ALL_CHUNKS_FAILED, TranslateResult


class _DummyResponse:
    status_code = 404
    headers: dict[str, str]

    def __init__(self) -> None:
        self.headers = {}

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {}


def test_query_semantic_scholar_encodes_old_style_arxiv_id(monkeypatch):
    seen: dict[str, str] = {}

    def fake_get(url: str, timeout: int):
        seen["url"] = url
        return _DummyResponse()

    monkeypatch.setattr("scholaraio.ingest.metadata._api.SESSION.get", fake_get)

    query_semantic_scholar(arxiv_id="hep-th/9901001")

    assert seen["url"] == (
        "https://api.semanticscholar.org/graph/v1/paper/"
        "arXiv%3Ahep-th%2F9901001?fields="
        "title,abstract,citationCount,year,externalIds,authors,venue,"
        "publicationTypes,references.externalIds"
    )


def test_query_semantic_scholar_encodes_doi_path_segment(monkeypatch):
    seen: dict[str, str] = {}

    def fake_get(url: str, timeout: int):
        seen["url"] = url
        return _DummyResponse()

    monkeypatch.setattr("scholaraio.ingest.metadata._api.SESSION.get", fake_get)

    query_semantic_scholar(doi="10.1017/S0022112094000431")

    assert seen["url"] == (
        "https://api.semanticscholar.org/graph/v1/paper/"
        "DOI%3A10.1017%2FS0022112094000431?fields="
        "title,abstract,citationCount,year,externalIds,authors,venue,"
        "publicationTypes,references.externalIds"
    )


def test_collect_existing_ids_includes_arxiv_ids(tmp_path: Path):
    papers_dir = tmp_path / "papers"
    paper_dir = papers_dir / "Imamura-1999-String-Junctions"
    paper_dir.mkdir(parents=True)
    (paper_dir / "meta.json").write_text(
        json.dumps(
            {
                "title": "String Junctions and Their Duals in Heterotic String Theory",
                "doi": "",
                "ids": {"arxiv": "hep-th/9901001v3"},
            }
        ),
        encoding="utf-8",
    )

    dois, pub_nums, arxiv_ids = _collect_existing_ids(papers_dir)

    assert dois == {}
    assert pub_nums == {}
    assert arxiv_ids["hep-th/9901001"] == paper_dir / "meta.json"


def test_step_dedup_rejects_duplicate_arxiv_only_preprint(tmp_path: Path, monkeypatch):
    existing_json = tmp_path / "papers" / "Imamura-1999-String-Junctions" / "meta.json"
    existing_json.parent.mkdir(parents=True)
    existing_json.write_text("{}", encoding="utf-8")

    monkeypatch.setattr("scholaraio.ingest.metadata.enrich_metadata", lambda meta: meta)
    monkeypatch.setattr("scholaraio.ingest.pipeline._detect_patent", lambda ctx: False)
    monkeypatch.setattr("scholaraio.ingest.pipeline._detect_thesis", lambda ctx: False)
    monkeypatch.setattr("scholaraio.ingest.pipeline._detect_book", lambda ctx: False)

    moved: dict[str, object] = {}

    def fake_move_to_pending(ctx, *, issue="no_doi", message="", extra=None):
        moved["issue"] = issue
        moved["extra"] = extra or {}

    monkeypatch.setattr("scholaraio.ingest.pipeline._move_to_pending", fake_move_to_pending)

    ctx = InboxCtx(
        pdf_path=None,
        inbox_dir=tmp_path / "inbox",
        papers_dir=tmp_path / "papers",
        existing_dois={},
        existing_pub_nums={},
        cfg=SimpleNamespace(_root=tmp_path),
        opts={"no_api": False, "dry_run": False},
        pending_dir=tmp_path / "pending",
        md_path=None,
        meta=PaperMetadata(
            title="String Junctions and Their Duals in Heterotic String Theory",
            arxiv_id="hep-th/9901001v1",
        ),
    )
    ctx.existing_arxiv_ids = {"hep-th/9901001": existing_json}

    result = step_dedup(ctx)

    assert result == StepResult.FAIL
    assert ctx.status == "duplicate"
    assert moved["issue"] == "duplicate"
    assert moved["extra"] == {
        "duplicate_of": "Imamura-1999-String-Junctions",
        "arxiv_id": "hep-th/9901001",
    }


def test_step_office_convert_reports_scholaraio_office_extra(tmp_path: Path, monkeypatch):
    office_path = tmp_path / "report.docx"
    office_path.write_text("dummy", encoding="utf-8")

    errors: list[str] = []
    monkeypatch.setattr(
        "scholaraio.ingest.pipeline._log.error", lambda msg, *args: errors.append(msg % args if args else msg)
    )

    import builtins

    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "markitdown":
            raise ModuleNotFoundError("No module named 'markitdown'", name="markitdown")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    ctx = InboxCtx(
        pdf_path=None,
        inbox_dir=tmp_path,
        papers_dir=tmp_path / "papers",
        existing_dois={},
        cfg=SimpleNamespace(_root=tmp_path),
        opts={"office_path": office_path, "dry_run": False},
    )

    result = step_office_convert(ctx)

    assert result == StepResult.FAIL
    assert ctx.status == "failed"
    assert any("pip install scholaraio[office]" in msg for msg in errors)


def test_step_extract_labels_arxiv_id_as_generic_id(tmp_path: Path, monkeypatch):
    md_path = tmp_path / "paper.md"
    md_path.write_text("# test", encoding="utf-8")

    messages: list[str] = []

    class DummyExtractor:
        def extract(self, _path: Path) -> PaperMetadata:
            return PaperMetadata(
                title="String Junctions and Their Duals in Heterotic String Theory",
                first_author_lastname="Imamura",
                year=1999,
                arxiv_id="hep-th/9901001",
            )

    monkeypatch.setattr("scholaraio.ingest.pipeline.ui", lambda msg="": messages.append(msg))
    monkeypatch.setattr("scholaraio.ingest.extractor.get_extractor", lambda cfg: DummyExtractor())

    ctx = InboxCtx(
        pdf_path=None,
        inbox_dir=tmp_path,
        papers_dir=tmp_path / "papers",
        existing_dois={},
        cfg=SimpleNamespace(_root=tmp_path),
        opts={"dry_run": False},
        md_path=md_path,
    )

    result = step_extract(ctx)

    assert result == StepResult.OK
    assert any("ID: arXiv:hep-th/9901001" in msg for msg in messages)
    assert all("DOI: arXiv:" not in msg for msg in messages)


def test_step_translate_treats_all_chunks_failed_as_failure(tmp_path: Path, monkeypatch):
    paper_dir = tmp_path / "papers" / "Smith-2023-Test"
    paper_dir.mkdir(parents=True)
    json_path = paper_dir / "meta.json"
    json_path.write_text("{}", encoding="utf-8")
    (paper_dir / "paper.md").write_text("Original text", encoding="utf-8")

    messages: list[str] = []
    monkeypatch.setattr("scholaraio.ingest.pipeline.ui", lambda msg="": messages.append(msg))
    monkeypatch.setattr(
        "scholaraio.translate.translate_paper",
        lambda *args, **kwargs: TranslateResult(skip_reason=SKIP_ALL_CHUNKS_FAILED, total_chunks=3),
    )

    cfg = SimpleNamespace(
        translate=SimpleNamespace(target_lang="zh", chunk_size=1000, concurrency=1),
        llm=SimpleNamespace(model="test-model"),
    )

    result = step_translate(json_path, cfg, {"force": False})

    assert result == StepResult.FAIL
    assert any("全部分块翻译失败" in msg for msg in messages)
