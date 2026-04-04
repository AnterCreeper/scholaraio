from __future__ import annotations

from pathlib import Path

from scholaraio.config import Config
from scholaraio.ingest.mineru import ConvertResult
from scholaraio.ingest.pipeline import InboxCtx, StepResult, batch_convert_pdfs, step_mineru


def test_step_mineru_falls_back_without_cloud_key(tmp_path, monkeypatch):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")

    cfg = Config()
    monkeypatch.setattr(cfg, "resolved_mineru_api_key", lambda: "")

    ctx = InboxCtx(
        pdf_path=pdf,
        inbox_dir=tmp_path,
        papers_dir=tmp_path / "papers",
        existing_dois={},
        cfg=cfg,
        opts={},
    )

    import scholaraio.ingest.mineru as mineru
    import scholaraio.ingest.pdf_fallback as pdf_fallback

    monkeypatch.setattr(mineru, "check_server", lambda *_: False)
    monkeypatch.setattr(mineru, "_get_pdf_page_count", lambda *_: 1)
    monkeypatch.setattr(
        mineru,
        "convert_pdf",
        lambda *_: ConvertResult(pdf_path=pdf, success=False, error="should not be called"),
    )

    calls: list[tuple[Path, Path]] = []

    def _fallback(pdf_path: Path, md_path: Path, parser_order=None, auto_detect=True):
        calls.append((pdf_path, md_path))
        md_path.write_text("fallback ok\n", encoding="utf-8")
        return True, "pymupdf", None

    monkeypatch.setattr(pdf_fallback, "convert_pdf_with_fallback", _fallback)

    result = step_mineru(ctx)

    assert result == StepResult.OK
    assert calls == [(pdf, tmp_path / "paper.md")]
    assert ctx.md_path == tmp_path / "paper.md"
    assert ctx.md_path.read_text(encoding="utf-8") == "fallback ok\n"


def test_step_mineru_skips_page_count_when_mineru_unreachable_and_no_cloud_key(tmp_path, monkeypatch):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")

    cfg = Config()
    monkeypatch.setattr(cfg, "resolved_mineru_api_key", lambda: "")

    ctx = InboxCtx(
        pdf_path=pdf,
        inbox_dir=tmp_path,
        papers_dir=tmp_path / "papers",
        existing_dois={},
        cfg=cfg,
        opts={},
    )

    import scholaraio.ingest.mineru as mineru
    import scholaraio.ingest.pdf_fallback as pdf_fallback

    def _page_count(*_args, **_kwargs):
        raise AssertionError("page count should not be queried when MinerU is unreachable without cloud key")

    monkeypatch.setattr(mineru, "check_server", lambda *_: False)
    monkeypatch.setattr(mineru, "_get_pdf_page_count", _page_count)
    monkeypatch.setattr(
        pdf_fallback,
        "convert_pdf_with_fallback",
        lambda _pdf, md_path, **_kwargs: (
            md_path.write_text("fallback ok\n", encoding="utf-8"),
            True,
            "pymupdf",
            None,
        )[1:],
    )

    result = step_mineru(ctx)

    assert result == StepResult.OK
    assert ctx.md_path == tmp_path / "paper.md"


def test_batch_convert_pdfs_falls_back_without_cloud_key(tmp_path, monkeypatch):
    paper_dir = tmp_path / "papers" / "Smith-2023-Test"
    paper_dir.mkdir(parents=True)
    (paper_dir / "meta.json").write_text("{}", encoding="utf-8")
    pdf = paper_dir / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")

    cfg = Config()
    cfg._root = tmp_path
    cfg.paths.papers_dir = "papers"
    monkeypatch.setattr(cfg, "resolved_mineru_api_key", lambda: "")

    import scholaraio.ingest.mineru as mineru
    import scholaraio.ingest.pdf_fallback as pdf_fallback
    import scholaraio.ingest.pipeline as pipeline

    monkeypatch.setattr(mineru, "check_server", lambda *_: False)
    monkeypatch.setattr(pipeline, "_batch_postprocess", lambda *_args, **_kwargs: None)

    calls: list[tuple[Path, Path]] = []

    def _fallback(pdf_path: Path, md_path: Path, parser_order=None, auto_detect=True):
        calls.append((pdf_path, md_path))
        md_path.write_text("fallback batch ok\n", encoding="utf-8")
        return True, "docling", None

    monkeypatch.setattr(pdf_fallback, "convert_pdf_with_fallback", _fallback)

    stats = batch_convert_pdfs(cfg, enrich=False)

    assert stats == {"converted": 1, "failed": 0, "skipped": 0}
    assert calls == [(pdf, paper_dir / "paper.md")]
    assert (paper_dir / "paper.md").read_text(encoding="utf-8") == "fallback batch ok\n"


def test_batch_convert_pdfs_fallback_cleans_noncanonical_source_pdf(tmp_path, monkeypatch):
    paper_dir = tmp_path / "papers" / "Smith-2023-Test"
    paper_dir.mkdir(parents=True)
    (paper_dir / "meta.json").write_text("{}", encoding="utf-8")
    pdf = paper_dir / "source.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")

    cfg = Config()
    cfg._root = tmp_path
    cfg.paths.papers_dir = "papers"
    monkeypatch.setattr(cfg, "resolved_mineru_api_key", lambda: "")

    import scholaraio.ingest.mineru as mineru
    import scholaraio.ingest.pdf_fallback as pdf_fallback
    import scholaraio.ingest.pipeline as pipeline

    monkeypatch.setattr(mineru, "check_server", lambda *_: False)
    monkeypatch.setattr(pipeline, "_batch_postprocess", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        pdf_fallback,
        "convert_pdf_with_fallback",
        lambda _pdf, md_path, **_kwargs: (
            md_path.write_text("fallback batch ok\n", encoding="utf-8"),
            True,
            "docling",
            None,
        )[1:],
    )

    stats = batch_convert_pdfs(cfg, enrich=False)

    assert stats == {"converted": 1, "failed": 0, "skipped": 0}
    assert (paper_dir / "paper.md").read_text(encoding="utf-8") == "fallback batch ok\n"
    assert not pdf.exists()


def test_step_mineru_prefers_docling_when_configured(tmp_path, monkeypatch):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")

    cfg = Config()
    cfg.ingest.pdf_preferred_parser = "docling"

    ctx = InboxCtx(
        pdf_path=pdf,
        inbox_dir=tmp_path,
        papers_dir=tmp_path / "papers",
        existing_dois={},
        cfg=cfg,
        opts={},
    )

    import scholaraio.ingest.mineru as mineru
    import scholaraio.ingest.pdf_fallback as pdf_fallback

    mineru_calls: list[Path] = []
    fallback_calls: list[tuple[Path, Path, list[str] | None]] = []

    monkeypatch.setattr(mineru, "check_server", lambda *_: True)
    monkeypatch.setattr(mineru, "_get_pdf_page_count", lambda *_: 1)
    monkeypatch.setattr(
        mineru,
        "convert_pdf",
        lambda pdf_path, *_args, **_kwargs: (
            mineru_calls.append(pdf_path),
            ConvertResult(pdf_path=pdf_path, success=False, error="should not be called"),
        )[1],
    )

    def _fallback(pdf_path: Path, md_path: Path, parser_order=None, auto_detect=True):
        fallback_calls.append((pdf_path, md_path, list(parser_order) if parser_order is not None else None))
        md_path.write_text("docling preferred\n", encoding="utf-8")
        return True, "docling", None

    monkeypatch.setattr(pdf_fallback, "convert_pdf_with_fallback", _fallback)

    result = step_mineru(ctx)

    assert result == StepResult.OK
    assert mineru_calls == []
    assert len(fallback_calls) == 1
    assert fallback_calls[0][:2] == (pdf, tmp_path / "paper.md")
    assert fallback_calls[0][2] is not None
    assert fallback_calls[0][2][0] == "docling"
    assert ctx.md_path == tmp_path / "paper.md"


def test_step_mineru_skips_page_count_when_preferred_parser_bypasses_mineru(tmp_path, monkeypatch):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")

    cfg = Config()
    cfg.ingest.pdf_preferred_parser = "docling"

    ctx = InboxCtx(
        pdf_path=pdf,
        inbox_dir=tmp_path,
        papers_dir=tmp_path / "papers",
        existing_dois={},
        cfg=cfg,
        opts={},
    )

    import scholaraio.ingest.mineru as mineru
    import scholaraio.ingest.pdf_fallback as pdf_fallback

    def _page_count(*_args, **_kwargs):
        raise AssertionError("page count should not be queried for fallback-only parsers")

    monkeypatch.setattr(mineru, "_get_pdf_page_count", _page_count)
    monkeypatch.setattr(mineru, "check_server", lambda *_: True)
    monkeypatch.setattr(
        pdf_fallback,
        "convert_pdf_with_fallback",
        lambda _pdf, md_path, **_kwargs: (
            md_path.write_text("docling preferred\n", encoding="utf-8"),
            True,
            "docling",
            None,
        )[1:],
    )

    result = step_mineru(ctx)

    assert result == StepResult.OK
    assert ctx.md_path == tmp_path / "paper.md"
