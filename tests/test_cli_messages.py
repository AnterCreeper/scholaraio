"""Regression tests for localized CLI/setup messaging."""

from __future__ import annotations

from argparse import Namespace
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
        (paper_dir / "notes.md").write_text(
            "## 2026-03-26 | test | analysis\n- Key finding\n", encoding="utf-8"
        )

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


class TestArxivCommands:
    def test_arxiv_fetch_downloads_to_inbox_without_ingest(self, tmp_path, monkeypatch):
        messages: list[str] = []
        monkeypatch.setattr(cli, "ui", messages.append)

        downloaded = tmp_path / "data" / "inbox" / "2603.25200.pdf"

        def fake_download(arxiv_ref, dest_dir, *, overwrite=False):
            dest_dir.mkdir(parents=True, exist_ok=True)
            downloaded.write_bytes(b"%PDF")
            return downloaded

        monkeypatch.setattr("scholaraio.sources.arxiv.download_arxiv_pdf", fake_download)

        cfg = SimpleNamespace(_root=tmp_path, papers_dir=tmp_path / "data" / "papers")
        args = Namespace(arxiv_ref="2603.25200", ingest=False, force=False, dry_run=False)

        cli.cmd_arxiv_fetch(args, cfg)

        assert downloaded.exists()
        assert any("已下载到 inbox" in m for m in messages)

    def test_arxiv_fetch_ingest_uses_temp_inbox_pipeline(self, tmp_path, monkeypatch):
        messages: list[str] = []
        monkeypatch.setattr(cli, "ui", messages.append)

        def fake_download(arxiv_ref, dest_dir, *, overwrite=False):
            dest_dir.mkdir(parents=True, exist_ok=True)
            out = dest_dir / "2603.25200.pdf"
            out.write_bytes(b"%PDF")
            return out

        seen: dict[str, object] = {}

        def fake_run_pipeline(step_names, cfg, opts):
            seen["steps"] = step_names
            seen["inbox_dir"] = opts["inbox_dir"]

        monkeypatch.setattr("scholaraio.sources.arxiv.download_arxiv_pdf", fake_download)
        monkeypatch.setattr("scholaraio.ingest.pipeline.run_pipeline", fake_run_pipeline)

        cfg = SimpleNamespace(_root=tmp_path, papers_dir=tmp_path / "data" / "papers")
        args = Namespace(arxiv_ref="2603.25200", ingest=True, force=False, dry_run=False)

        cli.cmd_arxiv_fetch(args, cfg)

        assert seen["steps"] == ["mineru", "extract", "dedup", "ingest", "embed", "index"]
        assert any("开始直接入库" in m for m in messages)

    def test_arxiv_fetch_reports_download_failure(self, tmp_path, monkeypatch):
        messages: list[str] = []
        monkeypatch.setattr(cli, "ui", messages.append)
        monkeypatch.setattr(
            "scholaraio.sources.arxiv.download_arxiv_pdf", lambda *args, **kwargs: (_ for _ in ()).throw(TimeoutError("timeout"))
        )

        cfg = SimpleNamespace(_root=tmp_path, papers_dir=tmp_path / "data" / "papers")
        args = Namespace(arxiv_ref="2603.25200", ingest=False, force=False, dry_run=False)

        cli.cmd_arxiv_fetch(args, cfg)

        assert any("arXiv 下载失败" in m for m in messages)
