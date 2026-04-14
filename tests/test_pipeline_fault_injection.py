"""Fault-injection tests for the ingest pipeline.

Covers every inbox step with injected failures, verifies state transitions,
ensures no file loss, and confirms idempotent recovery.
"""

from __future__ import annotations

import json
import shutil
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from scholaraio import cli
from scholaraio.config import Config
from scholaraio.ingest.pipeline import (
    STEPS,
    InboxCtx,
    StepResult,
    _cleanup_assets,
    _cleanup_inbox,
    _collect_existing_ids,
    _move_to_pending,
    _process_inbox,
    run_pipeline,
    step_dedup,
    step_extract,
    step_extract_doc,
    step_ingest,
    step_mineru,
    step_office_convert,
    step_validate_pdf,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def cfg(tmp_path: Path) -> Config:
    """Minimal Config rooted in tmp_path."""
    return Config(_root=tmp_path)


@pytest.fixture()
def inbox_dir(cfg: Config) -> Path:
    d = cfg._root / "data" / "inbox"
    d.mkdir(parents=True)
    return d


@pytest.fixture()
def papers_dir(cfg: Config) -> Path:
    d = cfg.papers_dir
    d.mkdir(parents=True)
    return d


@pytest.fixture()
def pending_dir(cfg: Config) -> Path:
    d = cfg._root / "data" / "pending"
    d.mkdir(parents=True)
    return d


@pytest.fixture()
def make_pdf(inbox_dir: Path):
    """Factory for PDF files in inbox."""
    def _make(name: str = "test.pdf", content: bytes = b"%PDF-1.4") -> Path:
        p = inbox_dir / name
        p.write_bytes(content)
        return p
    return _make


@pytest.fixture()
def make_md(inbox_dir: Path):
    """Factory for markdown files in inbox."""
    def _make(name: str = "test.md", content: str = "# Title\n") -> Path:
        p = inbox_dir / name
        p.write_text(content, encoding="utf-8")
        return p
    return _make


@pytest.fixture()
def make_ctx(cfg: Config, inbox_dir: Path, papers_dir: Path, pending_dir: Path):
    """Factory for InboxCtx."""
    def _build(
        *,
        pdf: Path | None = None,
        md: Path | None = None,
        meta=None,
        opts=None,
        existing_dois=None,
        is_thesis: bool = False,
        is_patent: bool = False,
        existing_pub_nums=None,
    ) -> InboxCtx:
        return InboxCtx(
            pdf_path=pdf,
            inbox_dir=inbox_dir,
            papers_dir=papers_dir,
            pending_dir=pending_dir,
            existing_dois=existing_dois or {},
            existing_pub_nums=existing_pub_nums or {},
            cfg=cfg,
            opts=opts or {},
            md_path=md,
            meta=meta,
            is_thesis=is_thesis,
            is_patent=is_patent,
        )
    return _build


@pytest.fixture()
def mock_meta_factory():
    """Factory for PaperMetadata instances."""
    from scholaraio.ingest.metadata import PaperMetadata

    def _build(**kwargs):
        defaults = {
            "title": "Test Paper",
            "authors": ["Alice Smith"],
            "first_author": "Alice Smith",
            "first_author_lastname": "Smith",
            "year": 2024,
            "doi": "",
            "journal": "Test Journal",
            "abstract": "An abstract.",
            "paper_type": "journal-article",
        }
        defaults.update(kwargs)
        return PaperMetadata(**defaults)
    return _build


@pytest.fixture(autouse=True)
def silence_ui(monkeypatch):
    """Suppress UI output in tests."""
    monkeypatch.setattr("scholaraio.ingest.pipeline.ui", lambda *a, **k: None)


# ---------------------------------------------------------------------------
# Office convert
# ---------------------------------------------------------------------------


class TestStepOfficeConvert:
    def test_skip_when_no_office_path(self, make_ctx):
        tmp = Path("/tmp")
        ctx = make_ctx(md=tmp)
        ctx.inbox_dir = tmp
        assert step_office_convert(ctx) == StepResult.OK

    def test_skip_when_md_already_exists(self, make_ctx, inbox_dir: Path):
        md = inbox_dir / "doc.md"
        md.write_text("x", encoding="utf-8")
        ctx = make_ctx(md=md, opts={"office_path": inbox_dir / "doc.docx"})
        assert step_office_convert(ctx) == StepResult.OK
        assert ctx.md_path == md

    def test_fail_on_import_error(self, make_ctx, inbox_dir: Path, monkeypatch):
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "markitdown" or name.startswith("markitdown."):
                raise ImportError("no markitdown")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", fake_import)
        ctx = make_ctx(opts={"office_path": inbox_dir / "doc.docx"})
        assert step_office_convert(ctx) == StepResult.FAIL
        assert ctx.status == "failed"


# ---------------------------------------------------------------------------
# Validate PDF
# ---------------------------------------------------------------------------


class TestStepValidatePdf:
    def test_skip_when_no_pdf(self, make_ctx):
        ctx = make_ctx(md=Path("/tmp/x.md"))
        assert step_validate_pdf(ctx) == StepResult.OK

    def test_fail_on_invalid_pdf(self, make_ctx, inbox_dir: Path, monkeypatch):
        monkeypatch.setattr(
            "scholaraio.ingest.mineru.validate_pdf",
            lambda p: (False, "not a pdf"),
        )
        pdf = inbox_dir / "bad.pdf"
        pdf.write_text("not pdf", encoding="utf-8")
        ctx = make_ctx(pdf=pdf)
        assert step_validate_pdf(ctx) == StepResult.FAIL
        assert ctx.status == "failed"

    def test_ok_on_valid_pdf(self, make_ctx, inbox_dir: Path, monkeypatch):
        monkeypatch.setattr(
            "scholaraio.ingest.mineru.validate_pdf",
            lambda p: (True, ""),
        )
        pdf = inbox_dir / "good.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        ctx = make_ctx(pdf=pdf)
        assert step_validate_pdf(ctx) == StepResult.OK


# ---------------------------------------------------------------------------
# MinerU
# ---------------------------------------------------------------------------


class TestStepMineru:
    def test_skip_md_only(self, make_ctx, tmp_path: Path):
        md = tmp_path / "x.md"
        md.write_text("x", encoding="utf-8")
        ctx = make_ctx(md=md)
        assert step_mineru(ctx) == StepResult.OK

    def test_skip_existing_md(self, make_ctx, inbox_dir: Path):
        pdf = inbox_dir / "paper.pdf"
        pdf.write_bytes(b"%PDF")
        md = inbox_dir / "paper.md"
        md.write_text("x", encoding="utf-8")
        ctx = make_ctx(pdf=pdf, md=md)
        assert step_mineru(ctx) == StepResult.OK
        assert ctx.md_path == md

    def test_fail_when_no_server_and_no_api_key(self, make_ctx, inbox_dir: Path, monkeypatch):
        monkeypatch.setattr("scholaraio.ingest.mineru.check_server", lambda url: False)
        monkeypatch.setattr("scholaraio.ingest.mineru._get_pdf_page_count", lambda p: 1)
        pdf = inbox_dir / "paper.pdf"
        pdf.write_bytes(b"%PDF")
        ctx = make_ctx(pdf=pdf)
        assert step_mineru(ctx) == StepResult.FAIL
        assert ctx.status == "failed"

    def test_success_local_server(self, make_ctx, inbox_dir: Path, monkeypatch):
        pdf = inbox_dir / "paper.pdf"
        pdf.write_bytes(b"%PDF")
        md = inbox_dir / "paper.md"

        class Result:
            success = True
            md_path = md
            error = ""

        monkeypatch.setattr("scholaraio.ingest.mineru.check_server", lambda url: True)
        monkeypatch.setattr("scholaraio.ingest.mineru._get_pdf_page_count", lambda p: 1)
        monkeypatch.setattr("scholaraio.ingest.mineru.convert_pdf", lambda p, opts: Result())
        ctx = make_ctx(pdf=pdf)
        assert step_mineru(ctx) == StepResult.OK
        assert ctx.md_path == md

    def test_fail_on_conversion_error(self, make_ctx, inbox_dir: Path, monkeypatch):
        pdf = inbox_dir / "paper.pdf"
        pdf.write_bytes(b"%PDF")

        class Result:
            success = False
            md_path = None
            error = "conversion failed"

        monkeypatch.setattr("scholaraio.ingest.mineru.check_server", lambda url: True)
        monkeypatch.setattr("scholaraio.ingest.mineru._get_pdf_page_count", lambda p: 1)
        monkeypatch.setattr("scholaraio.ingest.mineru.convert_pdf", lambda p, opts: Result())
        ctx = make_ctx(pdf=pdf)
        assert step_mineru(ctx) == StepResult.FAIL
        assert ctx.status == "failed"


# ---------------------------------------------------------------------------
# Extract
# ---------------------------------------------------------------------------


class TestStepExtract:
    def test_fail_when_no_md(self, make_ctx):
        ctx = make_ctx()
        assert step_extract(ctx) == StepResult.FAIL
        assert ctx.status == "failed"

    def test_success(self, make_ctx, inbox_dir: Path, mock_meta_factory, monkeypatch):
        md = inbox_dir / "paper.md"
        md.write_text("# Title\n", encoding="utf-8")
        meta = mock_meta_factory(title="Real Title", doi="10.1234/x")

        def fake_extractor(md_path):
            return meta

        monkeypatch.setattr(
            "scholaraio.ingest.extractor.get_extractor",
            lambda cfg: SimpleNamespace(extract=fake_extractor),
        )
        ctx = make_ctx(md=md)
        assert step_extract(ctx) == StepResult.OK
        assert ctx.meta == meta


# ---------------------------------------------------------------------------
# Extract Doc
# ---------------------------------------------------------------------------


class TestStepExtractDoc:
    def test_fail_when_no_md(self, make_ctx):
        ctx = make_ctx()
        assert step_extract_doc(ctx) == StepResult.FAIL

    def test_success(self, make_ctx, inbox_dir: Path, mock_meta_factory, monkeypatch):
        md = inbox_dir / "doc.md"
        md.write_text("# Doc\n", encoding="utf-8")
        meta = mock_meta_factory(title="Doc Title", paper_type="document")

        monkeypatch.setattr(
            "scholaraio.ingest.metadata._doc_extract.extract_document_metadata",
            lambda md_path, cfg: meta,
        )
        ctx = make_ctx(md=md)
        assert step_extract_doc(ctx) == StepResult.OK
        assert ctx.meta.paper_type == "document"

    def test_fail_when_no_title(self, make_ctx, inbox_dir: Path, monkeypatch):
        md = inbox_dir / "doc.md"
        md.write_text("x", encoding="utf-8")
        meta = MagicMock()
        meta.title = ""
        monkeypatch.setattr(
            "scholaraio.ingest.metadata._doc_extract.extract_document_metadata",
            lambda md_path, cfg: meta,
        )
        ctx = make_ctx(md=md)
        assert step_extract_doc(ctx) == StepResult.FAIL
        assert ctx.status == "failed"


# ---------------------------------------------------------------------------
# Dedup
# ---------------------------------------------------------------------------


class TestStepDedup:
    def test_fail_when_no_meta(self, make_ctx):
        ctx = make_ctx()
        assert step_dedup(ctx) == StepResult.FAIL
        assert ctx.status == "failed"

    def test_thesis_skips_dedup(self, make_ctx, mock_meta_factory):
        meta = mock_meta_factory()
        ctx = make_ctx(meta=meta, is_thesis=True)
        assert step_dedup(ctx) == StepResult.OK
        assert ctx.meta.paper_type == "thesis"

    def test_duplicate_doi_moves_to_pending(self, make_ctx, mock_meta_factory, pending_dir: Path, monkeypatch):
        monkeypatch.setattr("scholaraio.ingest.metadata.enrich_metadata", lambda meta: meta)
        meta = mock_meta_factory(doi="10.1234/x")
        existing_json = Path("/fake/meta.json")
        ctx = make_ctx(meta=meta, existing_dois={"10.1234/x": existing_json})
        assert step_dedup(ctx) == StepResult.FAIL
        assert ctx.status == "duplicate"
        # pending directory should be created
        assert any(pending_dir.iterdir())

    def test_no_doi_becomes_pending(self, make_ctx, mock_meta_factory, inbox_dir: Path, monkeypatch):
        monkeypatch.setattr("scholaraio.ingest.metadata.enrich_metadata", lambda meta: meta)
        meta = mock_meta_factory(doi="")
        md = inbox_dir / "paper.md"
        md.write_text("x", encoding="utf-8")
        ctx = make_ctx(meta=meta, md=md)
        monkeypatch.setattr("scholaraio.ingest.pipeline._detect_patent", lambda c: False)
        monkeypatch.setattr("scholaraio.ingest.pipeline._detect_thesis", lambda c: False)
        monkeypatch.setattr("scholaraio.ingest.pipeline._detect_book", lambda c: False)
        assert step_dedup(ctx) == StepResult.FAIL
        assert ctx.status == "needs_review"

    def test_no_doi_thesis_detected(self, make_ctx, mock_meta_factory, inbox_dir: Path, monkeypatch):
        monkeypatch.setattr("scholaraio.ingest.metadata.enrich_metadata", lambda meta: meta)
        meta = mock_meta_factory(doi="")
        md = inbox_dir / "paper.md"
        md.write_text("x", encoding="utf-8")
        ctx = make_ctx(meta=meta, md=md)
        monkeypatch.setattr("scholaraio.ingest.pipeline._detect_patent", lambda c: False)
        monkeypatch.setattr("scholaraio.ingest.pipeline._detect_thesis", lambda c: True)
        assert step_dedup(ctx) == StepResult.OK
        assert ctx.meta.paper_type == "thesis"

    def test_patent_no_pub_num_pending(self, make_ctx, mock_meta_factory):
        meta = mock_meta_factory(publication_number="", paper_type="patent")
        ctx = make_ctx(meta=meta, is_patent=True)
        assert step_dedup(ctx) == StepResult.FAIL
        assert ctx.status == "needs_review"

    def test_patent_duplicate(self, make_ctx, mock_meta_factory):
        meta = mock_meta_factory(publication_number="CN123456789A", paper_type="patent")
        existing = Path("/fake/meta.json")
        ctx = make_ctx(meta=meta, is_patent=True, existing_pub_nums={"CN123456789A": existing})
        assert step_dedup(ctx) == StepResult.FAIL
        assert ctx.status == "duplicate"

    def test_duplicate_with_missing_md_restores_md(
        self, make_ctx, mock_meta_factory, papers_dir: Path, inbox_dir: Path, monkeypatch
    ):
        """When duplicate DOI exists but its MD is missing, restore from current entry."""
        monkeypatch.setattr("scholaraio.ingest.metadata.enrich_metadata", lambda meta: meta)
        # Setup existing paper directory with meta.json but no paper.md
        existing_dir = papers_dir / "Smith-2024-Old"
        existing_dir.mkdir()
        existing_json = existing_dir / "meta.json"
        existing_json.write_text(json.dumps({"doi": "10.1234/x"}), encoding="utf-8")

        pdf = inbox_dir / "new.pdf"
        pdf.write_bytes(b"%PDF")
        md = inbox_dir / "new.md"
        md.write_text("markdown", encoding="utf-8")
        meta = mock_meta_factory(doi="10.1234/x")
        ctx = make_ctx(meta=meta, pdf=pdf, md=md, existing_dois={"10.1234/x": existing_json})

        monkeypatch.setattr(
            "scholaraio.ingest.pipeline._repair_abstract",
            lambda json_path, md_path, cfg: None,
        )

        assert step_dedup(ctx) == StepResult.FAIL
        assert ctx.status == "duplicate"
        # The md should have been moved to the existing directory
        assert (existing_dir / "paper.md").exists()
        assert not md.exists()


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------


class TestStepIngest:
    def test_fail_when_no_meta(self, make_ctx):
        ctx = make_ctx()
        assert step_ingest(ctx) == StepResult.FAIL
        assert ctx.status == "failed"

    def test_fail_when_no_title_and_no_abstract(self, make_ctx, mock_meta_factory):
        meta = mock_meta_factory(title="", abstract="")
        ctx = make_ctx(meta=meta)
        assert step_ingest(ctx) == StepResult.FAIL
        assert ctx.status == "failed"

    def test_success_moves_files(self, make_ctx, mock_meta_factory, inbox_dir: Path, papers_dir: Path):
        meta = mock_meta_factory(doi="10.1234/ingest")
        md = inbox_dir / "paper.md"
        md.write_text("# Paper\n", encoding="utf-8")
        pdf = inbox_dir / "paper.pdf"
        pdf.write_bytes(b"%PDF")
        ctx = make_ctx(meta=meta, md=md, pdf=pdf, existing_dois={})

        assert step_ingest(ctx) == StepResult.OK
        assert ctx.status == "ingested"
        assert ctx.ingested_json is not None
        assert ctx.ingested_json.exists()
        assert not md.exists()  # moved out of inbox
        assert not pdf.exists()  # cleaned up

    def test_abstract_backfill(self, make_ctx, mock_meta_factory, inbox_dir: Path, monkeypatch):
        meta = mock_meta_factory(abstract="")
        md = inbox_dir / "paper.md"
        md.write_text("# Paper\nAbstract: hello world", encoding="utf-8")
        ctx = make_ctx(meta=meta, md=md)
        monkeypatch.setattr(
            "scholaraio.ingest.metadata.extract_abstract_from_md",
            lambda md_path, cfg: "backfilled abstract",
        )
        step_ingest(ctx)
        assert ctx.meta.abstract == "backfilled abstract"

    def test_collision_avoidance(self, make_ctx, mock_meta_factory, inbox_dir: Path, papers_dir: Path):
        meta = mock_meta_factory()
        md = inbox_dir / "paper.md"
        md.write_text("x", encoding="utf-8")
        # Pre-create directory to force suffix; actual stem uses hyphens
        (papers_dir / "Smith-2024-Test-Paper").mkdir()
        ctx = make_ctx(meta=meta, md=md)
        step_ingest(ctx)
        assert ctx.ingested_json.parent.name.startswith("Smith-2024-Test-Paper-")


# ---------------------------------------------------------------------------
# Idempotency / Recovery via _process_inbox
# ---------------------------------------------------------------------------


class TestProcessInboxRecovery:
    def test_mineru_failure_keeps_pdf_for_retry(self, cfg: Config, inbox_dir: Path, papers_dir: Path, pending_dir: Path, monkeypatch):
        pdf = inbox_dir / "paper.pdf"
        pdf.write_bytes(b"%PDF")
        monkeypatch.setattr("scholaraio.ingest.mineru.validate_pdf", lambda p: (True, ""))
        monkeypatch.setattr("scholaraio.ingest.mineru.check_server", lambda url: True)
        monkeypatch.setattr("scholaraio.ingest.mineru._get_pdf_page_count", lambda p: 1)

        class FailResult:
            success = False
            md_path = None
            error = "mineru down"

        monkeypatch.setattr("scholaraio.ingest.mineru.convert_pdf", lambda p, opts: FailResult())
        ingested = []
        _process_inbox(
            inbox_dir, papers_dir, pending_dir, {},
            ["validate_pdf", "mineru", "extract", "dedup", "ingest"],
            cfg, {}, False, ingested,
        )
        assert pdf.exists()  # PDF should remain in inbox for retry
        assert not ingested

    def test_extract_failure_then_retry_success(
        self, cfg: Config, inbox_dir: Path, papers_dir: Path, pending_dir: Path, mock_meta_factory, monkeypatch
    ):
        pdf = inbox_dir / "paper.pdf"
        pdf.write_bytes(b"%PDF")
        md = inbox_dir / "paper.md"
        md.write_text("# Title\n", encoding="utf-8")

        monkeypatch.setattr("scholaraio.ingest.mineru.validate_pdf", lambda p: (True, ""))
        monkeypatch.setattr("scholaraio.ingest.mineru.check_server", lambda url: True)
        monkeypatch.setattr("scholaraio.ingest.mineru._get_pdf_page_count", lambda p: 1)
        out_md = inbox_dir / "paper.md"

        class OkResult:
            success = True
            md_path = out_md
            error = ""

        monkeypatch.setattr("scholaraio.ingest.mineru.convert_pdf", lambda p, opts: OkResult())

        # Monkeypatch step_extract to return FAIL on first call, real behavior on second
        real_step_extract = step_extract
        extract_calls = []

        def flaky_step_extract(ctx):
            extract_calls.append(1)
            if len(extract_calls) == 1:
                ctx.status = "failed"
                return StepResult.FAIL
            ctx.meta = mock_meta_factory(doi="10.1234/retry", title="Retry Paper")
            return StepResult.OK

        monkeypatch.setattr(STEPS["extract"], "fn", flaky_step_extract, raising=False)
        monkeypatch.setattr(
            "scholaraio.ingest.metadata.enrich_metadata",
            lambda meta: meta,
        )

        ingested = []
        _process_inbox(
            inbox_dir, papers_dir, pending_dir, {},
            ["validate_pdf", "mineru", "extract", "dedup", "ingest"],
            cfg, {}, False, ingested,
        )
        assert not ingested  # first run failed
        assert md.exists()  # md still in inbox

        # Second run: extract succeeds
        _process_inbox(
            inbox_dir, papers_dir, pending_dir, {},
            ["validate_pdf", "mineru", "extract", "dedup", "ingest"],
            cfg, {}, False, ingested,
        )
        assert len(ingested) == 1
        assert ingested[0].exists()

    def test_dedup_no_doi_then_retry_with_manual_doi(
        self, cfg: Config, inbox_dir: Path, papers_dir: Path, pending_dir: Path, mock_meta_factory, monkeypatch
    ):
        """Simulate user adding DOI to pending, then re-running pipeline."""
        md = inbox_dir / "paper.md"
        md.write_text("# Title\n", encoding="utf-8")

        monkeypatch.setattr(
            "scholaraio.ingest.extractor.get_extractor",
            lambda cfg: SimpleNamespace(
                extract=lambda md_path: mock_meta_factory(doi="", title="Manual DOI Paper")
            ),
        )
        monkeypatch.setattr(
            "scholaraio.ingest.metadata.enrich_metadata",
            lambda meta: meta,
        )
        monkeypatch.setattr("scholaraio.ingest.pipeline._detect_patent", lambda c: False)
        monkeypatch.setattr("scholaraio.ingest.pipeline._detect_thesis", lambda c: False)
        monkeypatch.setattr("scholaraio.ingest.pipeline._detect_book", lambda c: False)

        ingested = []
        _process_inbox(
            inbox_dir, papers_dir, pending_dir, {},
            ["extract", "dedup", "ingest"],
            cfg, {}, False, ingested,
        )
        assert not ingested
        # Should be in pending
        pending_dirs = list(pending_dir.iterdir())
        assert len(pending_dirs) == 1
        assert not md.exists()  # moved to pending

        # User fixes: move back to inbox with DOI in metadata
        fixed_md = inbox_dir / "paper.md"
        shutil.copy(str(pending_dirs[0] / "paper.md"), str(fixed_md))

        # Update extractor to return DOI
        monkeypatch.setattr(
            "scholaraio.ingest.extractor.get_extractor",
            lambda cfg: SimpleNamespace(
                extract=lambda md_path: mock_meta_factory(doi="10.1234/fixed", title="Manual DOI Paper")
            ),
        )
        ingested2 = []
        _process_inbox(
            inbox_dir, papers_dir, pending_dir, {},
            ["extract", "dedup", "ingest"],
            cfg, {}, False, ingested2,
        )
        assert len(ingested2) == 1

    def test_duplicate_not_ingested_again(self, cfg: Config, inbox_dir: Path, papers_dir: Path, pending_dir: Path, mock_meta_factory, monkeypatch):
        """Re-running pipeline on duplicate should not create a second paper entry."""
        # Pre-ingest one paper (with paper.md so it goes to pending as duplicate)
        existing_dir = papers_dir / "Smith-2024-Test"
        existing_dir.mkdir()
        (existing_dir / "meta.json").write_text(
            json.dumps({"doi": "10.1234/dup"}), encoding="utf-8"
        )
        (existing_dir / "paper.md").write_text("existing", encoding="utf-8")

        md = inbox_dir / "paper.md"
        md.write_text("x", encoding="utf-8")
        monkeypatch.setattr(
            "scholaraio.ingest.extractor.get_extractor",
            lambda cfg: SimpleNamespace(
                extract=lambda md_path: mock_meta_factory(doi="10.1234/dup")
            ),
        )
        monkeypatch.setattr(
            "scholaraio.ingest.metadata.enrich_metadata",
            lambda meta: meta,
        )

        ingested = []
        _process_inbox(
            inbox_dir, papers_dir, pending_dir, {"10.1234/dup": existing_dir / "meta.json"},
            ["extract", "dedup", "ingest"],
            cfg, {}, False, ingested,
        )
        assert not ingested
        assert len(list(pending_dir.iterdir())) == 1  # moved to pending


# ---------------------------------------------------------------------------
# Document inbox recovery
# ---------------------------------------------------------------------------


class TestDocumentInboxRecovery:
    def test_doc_pipeline_ingests_without_dedup(
        self, cfg: Config, inbox_dir: Path, papers_dir: Path, pending_dir: Path, mock_meta_factory, monkeypatch
    ):
        md = inbox_dir / "report.md"
        md.write_text("# Report\n", encoding="utf-8")
        meta = mock_meta_factory(title="Report", paper_type="document")

        monkeypatch.setattr(
            "scholaraio.ingest.metadata._doc_extract.extract_document_metadata",
            lambda md_path, cfg: meta,
        )
        ingested = []
        _process_inbox(
            inbox_dir, papers_dir, pending_dir, {},
            ["office_convert", "validate_pdf", "mineru", "extract_doc", "ingest"],
            cfg, {}, False, ingested,
            existing_pub_nums={},
        )
        assert len(ingested) == 1
        assert (ingested[0].parent / "paper.md").exists()

    def test_doc_extract_failure_keeps_md(self, cfg: Config, inbox_dir: Path, papers_dir: Path, pending_dir: Path, monkeypatch):
        md = inbox_dir / "report.md"
        md.write_text("x", encoding="utf-8")
        monkeypatch.setattr(
            "scholaraio.ingest.metadata._doc_extract.extract_document_metadata",
            lambda md_path, cfg: (_ for _ in ()).throw(RuntimeError("doc extract failed")),
        )
        ingested = []
        _process_inbox(
            inbox_dir, papers_dir, pending_dir, {},
            ["office_convert", "validate_pdf", "mineru", "extract_doc", "ingest"],
            cfg, {}, False, ingested,
        )
        assert not ingested
        assert md.exists()  # still in inbox for retry


# ---------------------------------------------------------------------------
# run_pipeline integration with fault injection
# ---------------------------------------------------------------------------


class TestRunPipelineIntegration:
    def test_full_pipeline_with_mineru_failure_then_recovery(
        self, cfg: Config, inbox_dir: Path, papers_dir: Path, mock_meta_factory, monkeypatch
    ):
        pdf = inbox_dir / "paper.pdf"
        pdf.write_bytes(b"%PDF")
        out_md = inbox_dir / "paper.md"

        class FailResult:
            success = False
            md_path = None
            error = "mineru down"

        class OkResult:
            success = True
            md_path = out_md
            error = ""

        results = [FailResult(), OkResult()]
        result_iter = iter(results)

        def mock_convert(p, opts):
            r = next(result_iter)
            if r.success:
                out_md.write_text("# Run Paper\n", encoding="utf-8")
            return r

        monkeypatch.setattr("scholaraio.ingest.mineru.validate_pdf", lambda p: (True, ""))
        monkeypatch.setattr("scholaraio.ingest.mineru.check_server", lambda url: True)
        monkeypatch.setattr("scholaraio.ingest.mineru._get_pdf_page_count", lambda p: 1)
        monkeypatch.setattr("scholaraio.ingest.mineru.convert_pdf", mock_convert)
        monkeypatch.setattr(
            "scholaraio.ingest.extractor.get_extractor",
            lambda cfg: SimpleNamespace(
                extract=lambda md_path: mock_meta_factory(doi="10.1234/run", title="Run Paper")
            ),
        )
        monkeypatch.setattr(
            "scholaraio.ingest.metadata.enrich_metadata",
            lambda meta: meta,
        )

        # First run fails at mineru
        run_pipeline(["validate_pdf", "mineru", "extract", "dedup", "ingest"], cfg, {})
        assert pdf.exists()
        assert not list(papers_dir.iterdir())

        # Second run succeeds
        run_pipeline(["validate_pdf", "mineru", "extract", "dedup", "ingest"], cfg, {})
        assert not pdf.exists()
        assert any(papers_dir.iterdir())

    def test_run_pipeline_skips_papers_scope_when_nothing_ingested(
        self, cfg: Config, inbox_dir: Path, papers_dir: Path, monkeypatch
    ):
        md = inbox_dir / "paper.md"
        md.write_text("x", encoding="utf-8")

        def failing_step_extract(ctx):
            ctx.status = "failed"
            return StepResult.FAIL

        monkeypatch.setattr(STEPS["extract"], "fn", failing_step_extract, raising=False)
        monkeypatch.setattr(
            "scholaraio.ingest.metadata.enrich_metadata",
            lambda meta: meta,
        )
        # If papers scope were to run on empty ingested_jsons when inbox steps present,
        # it would skip. We just verify no crash.
        run_pipeline(["extract", "dedup", "ingest", "toc", "l3", "embed", "index"], cfg, {})


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


class TestCollectExistingIds:
    def test_collects_dois_and_pub_nums(self, papers_dir: Path):
        d = papers_dir / "Paper1"
        d.mkdir()
        (d / "meta.json").write_text(
            json.dumps({
                "doi": "10.1234/a",
                "ids": {"patent_publication_number": "CN111111111A"},
            }),
            encoding="utf-8",
        )
        dois, pub_nums = _collect_existing_ids(papers_dir)
        assert dois == {"10.1234/a": d / "meta.json"}
        assert pub_nums == {"CN111111111A": d / "meta.json"}

    def test_empty_dir(self, papers_dir: Path):
        dois, pub_nums = _collect_existing_ids(papers_dir)
        assert dois == {}
        assert pub_nums == {}


class TestCleanupInbox:
    def test_deletes_files(self, tmp_path: Path):
        pdf = tmp_path / "a.pdf"
        pdf.write_bytes(b"x")
        md = tmp_path / "a.md"
        md.write_text("x", encoding="utf-8")
        _cleanup_inbox(pdf, md, dry_run=False)
        assert not pdf.exists()
        assert not md.exists()

    def test_dry_run_preserves_files(self, tmp_path: Path):
        pdf = tmp_path / "a.pdf"
        pdf.write_bytes(b"x")
        md = tmp_path / "a.md"
        md.write_text("x", encoding="utf-8")
        _cleanup_inbox(pdf, md, dry_run=True)
        assert pdf.exists()
        assert md.exists()


class TestCleanupAssets:
    def test_removes_mineru_artifacts(self, tmp_path: Path):
        images = tmp_path / "test_mineru_images"
        images.mkdir()
        layout = tmp_path / "test_layout.json"
        layout.write_text("{}", encoding="utf-8")
        _cleanup_assets(tmp_path, "test", "test")
        assert not images.exists()
        assert not layout.exists()


class TestMoveToPending:
    def test_moves_md_and_pdf(self, cfg: Config, inbox_dir: Path, pending_dir: Path, make_ctx):
        md = inbox_dir / "paper.md"
        md.write_text("x", encoding="utf-8")
        pdf = inbox_dir / "paper.pdf"
        pdf.write_bytes(b"%PDF")
        ctx = make_ctx(md=md, pdf=pdf)
        _move_to_pending(ctx, issue="no_doi")
        assert not md.exists()
        assert not pdf.exists()
        pending_subdirs = list(pending_dir.iterdir())
        assert len(pending_subdirs) == 1
        assert (pending_subdirs[0] / "paper.md").exists()
        assert (pending_subdirs[0] / "paper.pdf").exists()
        assert (pending_subdirs[0] / "pending.json").exists()
