"""Regression tests for localized CLI/setup messaging."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

from scholaraio import cli
from scholaraio.setup import _S


class TestSetupImportHints:
    def test_zh_import_hint_is_fully_localized(self):
        zh_hint = _S["import_hint"]["zh"]

        assert zh_hint.startswith("\n提示：")

    def test_zotero_examples_use_distinct_placeholders_and_optional_local_collection(self):
        en_hint = _S["import_hint"]["en"]
        zh_hint = _S["import_hint"]["zh"]

        assert "--api-key <API_KEY>" in en_hint
        assert "--collection <COLLECTION_KEY>" in en_hint
        assert "scholaraio import-zotero --local /path/to/zotero.sqlite\n" in en_hint
        assert "--api-key <API_KEY>" in zh_hint
        assert "--collection <COLLECTION_KEY>" in zh_hint
        assert "scholaraio import-zotero --local /path/to/zotero.sqlite\n" in zh_hint


class TestShowLayer4Headings:
    def test_translated_full_text_heading_uses_consistent_spacing(self, tmp_papers, monkeypatch):
        paper_dir = tmp_papers / "Smith-2023-Turbulence"
        (paper_dir / "paper_zh.md").write_text("中文全文。", encoding="utf-8")

        messages: list[str] = []
        monkeypatch.setattr(cli, "ui", messages.append)
        monkeypatch.setattr(cli, "_print_header", lambda _: None)

        cfg = SimpleNamespace(papers_dir=tmp_papers, index_db=tmp_papers / "index.db")
        args = Namespace(paper_id="Smith-2023-Turbulence", layer=4, lang="zh")

        cli.cmd_show(args, cfg)

        assert "\n--- 全文（zh） ---\n" in messages

    def test_missing_translation_heading_uses_consistent_spacing(self, tmp_papers, monkeypatch):
        messages: list[str] = []
        monkeypatch.setattr(cli, "ui", messages.append)
        monkeypatch.setattr(cli, "_print_header", lambda _: None)

        cfg = SimpleNamespace(papers_dir=tmp_papers, index_db=tmp_papers / "index.db")
        args = Namespace(paper_id="Smith-2023-Turbulence", layer=4, lang="fr")

        cli.cmd_show(args, cfg)

        assert "\n--- 全文（原文，paper_fr.md 不存在） ---\n" in messages


class TestShowNotesIntegration:
    def test_notes_displayed_after_header(self, tmp_papers, monkeypatch):
        paper_dir = tmp_papers / "Smith-2023-Turbulence"
        (paper_dir / "notes.md").write_text("## 2026-03-26 | test | analysis\n- Key finding\n", encoding="utf-8")

        messages: list[str] = []
        monkeypatch.setattr(cli, "ui", messages.append)
        monkeypatch.setattr(cli, "_print_header", lambda _: None)

        cfg = SimpleNamespace(papers_dir=tmp_papers, index_db=tmp_papers / "index.db")
        args = Namespace(paper_id="Smith-2023-Turbulence", layer=1)

        cli.cmd_show(args, cfg)

        assert "\n--- Agent 笔记 (notes.md) ---\n" in messages
        assert any("Key finding" in m for m in messages)
        assert "\n--- 笔记结束 ---\n" in messages

    def test_no_notes_section_when_file_missing(self, tmp_papers, monkeypatch):
        messages: list[str] = []
        monkeypatch.setattr(cli, "ui", messages.append)
        monkeypatch.setattr(cli, "_print_header", lambda _: None)

        cfg = SimpleNamespace(papers_dir=tmp_papers, index_db=tmp_papers / "index.db")
        args = Namespace(paper_id="Smith-2023-Turbulence", layer=1)

        cli.cmd_show(args, cfg)

        assert "\n--- Agent 笔记 (notes.md) ---\n" not in messages

    def test_append_notes_visible_in_same_show(self, tmp_papers, monkeypatch):
        messages: list[str] = []
        monkeypatch.setattr(cli, "ui", messages.append)
        monkeypatch.setattr(cli, "_print_header", lambda _: None)

        cfg = SimpleNamespace(papers_dir=tmp_papers, index_db=tmp_papers / "index.db")
        args = Namespace(
            paper_id="Smith-2023-Turbulence",
            layer=1,
            append_notes="## 2026-03-26 | test | review\n- Important note",
        )

        cli.cmd_show(args, cfg)

        assert any("已追加笔记到" in m for m in messages)
        assert "\n--- Agent 笔记 (notes.md) ---\n" in messages
        assert any("Important note" in m for m in messages)

    def test_append_notes_empty_ignored(self, tmp_papers, monkeypatch):
        messages: list[str] = []
        monkeypatch.setattr(cli, "ui", messages.append)
        monkeypatch.setattr(cli, "_print_header", lambda _: None)

        cfg = SimpleNamespace(papers_dir=tmp_papers, index_db=tmp_papers / "index.db")
        args = Namespace(paper_id="Smith-2023-Turbulence", layer=1, append_notes="   ")

        cli.cmd_show(args, cfg)

        assert any("内容为空" in m for m in messages)
        assert not (tmp_papers / "Smith-2023-Turbulence" / "notes.md").exists()


class TestSearchResultFormatting:
    def test_print_search_result_omits_empty_extra(self, monkeypatch):
        messages: list[str] = []

        def fake_ui(message: str = "") -> None:
            messages.append(message)

        monkeypatch.setattr(cli, "ui", fake_ui)

        cli._print_search_result(
            1,
            {
                "paper_id": "paper-1",
                "authors": "Smith, John, Doe, Jane",
                "year": 2023,
                "journal": "JFM",
                "citation_count": 5,
                "title": "Test Paper",
            },
            extra="",
        )

        assert messages
        assert "( [])" not in messages[0]


class TestAttachPdfFallback:
    def test_attach_pdf_falls_back_without_cloud_key(self, tmp_path, monkeypatch):
        paper_dir = tmp_path / "papers" / "Smith-2023-Test"
        paper_dir.mkdir(parents=True)
        (paper_dir / "meta.json").write_text("{}", encoding="utf-8")
        src_pdf = tmp_path / "input.pdf"
        src_pdf.write_bytes(b"%PDF-1.4\n")

        cfg = SimpleNamespace(
            ingest=SimpleNamespace(
                mineru_endpoint="http://localhost:8000",
                mineru_cloud_url="https://mineru.net/api/v4",
                mineru_backend_local="pipeline",
                mineru_model_version_cloud="v1",
                mineru_lang="en",
                mineru_parse_method="auto",
                mineru_enable_formula=True,
                mineru_enable_table=True,
                pdf_fallback_order=["auto"],
                pdf_fallback_auto_detect=True,
            ),
            papers_dir=tmp_path / "papers",
        )
        cfg.resolved_mineru_api_key = lambda: ""

        monkeypatch.setattr(cli, "_resolve_paper", lambda *_: paper_dir)
        monkeypatch.setattr(cli, "ui", lambda *_args, **_kwargs: None)

        import scholaraio.ingest.mineru as mineru
        import scholaraio.ingest.pdf_fallback as pdf_fallback

        monkeypatch.setattr(mineru, "check_server", lambda *_: False)

        calls: list[tuple[Path, Path]] = []

        def _fallback(pdf_path, md_path, parser_order=None, auto_detect=True):
            calls.append((pdf_path, md_path))
            md_path.write_text("fallback attach ok\n", encoding="utf-8")
            return True, "docling", None

        monkeypatch.setattr(pdf_fallback, "convert_pdf_with_fallback", _fallback)
        monkeypatch.setattr("scholaraio.papers.read_meta", lambda *_: {"abstract": "exists"})
        monkeypatch.setattr("scholaraio.ingest.pipeline.step_embed", lambda *_: None)
        monkeypatch.setattr("scholaraio.ingest.pipeline.step_index", lambda *_: None)

        args = Namespace(paper_id="paper-1", pdf_path=str(src_pdf), dry_run=False)
        cli.cmd_attach_pdf(args, cfg)

        assert calls == [(paper_dir / "input.pdf", paper_dir / "paper.md")]
        assert (paper_dir / "paper.md").read_text(encoding="utf-8") == "fallback attach ok\n"
        assert not (paper_dir / "input.pdf").exists()

    def test_attach_pdf_prefers_configured_fallback_without_result_object(self, tmp_path, monkeypatch):
        paper_dir = tmp_path / "papers" / "Smith-2023-Test"
        paper_dir.mkdir(parents=True)
        (paper_dir / "meta.json").write_text("{}", encoding="utf-8")
        src_pdf = tmp_path / "input.pdf"
        src_pdf.write_bytes(b"%PDF-1.4\n")

        cfg = SimpleNamespace(
            ingest=SimpleNamespace(
                mineru_endpoint="http://localhost:8000",
                mineru_cloud_url="https://mineru.net/api/v4",
                mineru_backend_local="pipeline",
                mineru_model_version_cloud="v1",
                mineru_lang="en",
                mineru_parse_method="auto",
                mineru_enable_formula=True,
                mineru_enable_table=True,
                pdf_preferred_parser="docling",
                pdf_fallback_order=["auto"],
                pdf_fallback_auto_detect=True,
            ),
            papers_dir=tmp_path / "papers",
        )
        cfg.resolved_mineru_api_key = lambda: ""

        monkeypatch.setattr(cli, "_resolve_paper", lambda *_: paper_dir)
        monkeypatch.setattr(cli, "ui", lambda *_args, **_kwargs: None)

        import scholaraio.ingest.pdf_fallback as pdf_fallback

        calls: list[tuple[Path, Path]] = []

        def _fallback(pdf_path, md_path, parser_order=None, auto_detect=True):
            calls.append((pdf_path, md_path))
            md_path.write_text("preferred attach ok\n", encoding="utf-8")
            return True, "docling", None

        monkeypatch.setattr(pdf_fallback, "convert_pdf_with_fallback", _fallback)
        monkeypatch.setattr("scholaraio.papers.read_meta", lambda *_: {"abstract": "exists"})
        monkeypatch.setattr("scholaraio.ingest.pipeline.step_embed", lambda *_: None)
        monkeypatch.setattr("scholaraio.ingest.pipeline.step_index", lambda *_: None)

        args = Namespace(paper_id="paper-1", pdf_path=str(src_pdf), dry_run=False)
        cli.cmd_attach_pdf(args, cfg)

        assert calls == [(paper_dir / "input.pdf", paper_dir / "paper.md")]
        assert (paper_dir / "paper.md").read_text(encoding="utf-8") == "preferred attach ok\n"
        assert not (paper_dir / "input.pdf").exists()


class TestSetupMetricsFallback:
    def test_setup_check_skips_metrics_init_failure(self, monkeypatch):
        messages: list[str] = []

        monkeypatch.setattr(
            cli,
            "load_config",
            lambda: SimpleNamespace(
                ensure_dirs=lambda: None,
                metrics_db_path="/tmp/metrics.db",
                ingest=SimpleNamespace(contact_email=""),
                resolved_s2_api_key=lambda: "",
            ),
        )
        monkeypatch.setattr(cli, "ui", messages.append)
        monkeypatch.setattr("scholaraio.log.setup", lambda cfg: "session-1")

        def _boom(*_args, **_kwargs):
            raise RuntimeError("database is locked")

        monkeypatch.setattr("scholaraio.metrics.init", _boom)
        monkeypatch.setattr("scholaraio.ingest.metadata._models.configure_session", lambda *_: None)
        monkeypatch.setattr("scholaraio.ingest.metadata._models.configure_s2_session", lambda *_: None)
        monkeypatch.setattr(cli, "cmd_setup", lambda args, cfg: print("SETUP_OK"))
        monkeypatch.setattr("sys.argv", ["scholaraio", "setup", "check", "--lang", "zh"])

        cli.main()

        assert any("metrics 初始化失败，已跳过" in msg for msg in messages)
