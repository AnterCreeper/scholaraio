"""Tests for the ingest-link CLI command."""

from __future__ import annotations

import json
from argparse import Namespace
from types import SimpleNamespace

from scholaraio import cli


class TestIngestLinkCommand:
    def test_ingest_link_dry_run_reports_urls(self, tmp_path, monkeypatch):
        messages: list[str] = []
        monkeypatch.setattr(cli, "ui", messages.append)

        called = {"extract": 0, "pipeline": 0}
        monkeypatch.setattr(
            "scholaraio.sources.webtools.webextract",
            lambda *args, **kwargs: called.__setitem__("extract", called["extract"] + 1),
        )
        monkeypatch.setattr(
            "scholaraio.ingest.pipeline.run_pipeline",
            lambda *args, **kwargs: called.__setitem__("pipeline", called["pipeline"] + 1),
        )

        cfg = SimpleNamespace(_root=tmp_path, papers_dir=tmp_path / "data" / "papers")
        args = Namespace(
            urls=["https://example.com/a", "https://example.com/b"],
            dry_run=True,
            force=False,
            pdf=False,
            no_index=False,
            json=False,
        )

        cli.cmd_ingest_link(args, cfg)

        assert called == {"extract": 0, "pipeline": 0}
        assert any("[dry-run]" in m and "2 个链接" in m for m in messages)

    def test_ingest_link_uses_temp_doc_inbox_pipeline(self, tmp_path, monkeypatch):
        messages: list[str] = []
        monkeypatch.setattr(cli, "ui", messages.append)

        def fake_extract(url, *, pdf=None, base_url=None):
            assert pdf is False
            return {
                "url": url,
                "title": "Example Page",
                "text": "## Intro\n\nHello from the web.",
                "html": "<html></html>",
                "error": "",
            }

        seen: dict[str, object] = {}

        def fake_run_pipeline(step_names, cfg, opts):
            seen["steps"] = step_names
            seen["doc_inbox_dir"] = opts["doc_inbox_dir"]
            seen["opts"] = opts
            inbox = opts["doc_inbox_dir"]
            md_files = sorted(inbox.glob("*.md"))
            json_files = sorted(inbox.glob("*.json"))
            seen["md_text"] = md_files[0].read_text(encoding="utf-8")
            seen["sidecar"] = json.loads(json_files[0].read_text(encoding="utf-8"))

        monkeypatch.setattr("scholaraio.sources.webtools.webextract", fake_extract)
        monkeypatch.setattr("scholaraio.ingest.pipeline.run_pipeline", fake_run_pipeline)

        cfg = SimpleNamespace(_root=tmp_path, papers_dir=tmp_path / "data" / "papers")
        args = Namespace(
            urls=["https://example.com/article"],
            dry_run=False,
            force=True,
            pdf=False,
            no_index=False,
            json=False,
        )

        cli.cmd_ingest_link(args, cfg)

        assert seen["steps"] == ["extract_doc", "ingest", "embed", "index"]
        assert seen["doc_inbox_dir"] != cfg._root / "data" / "inbox-doc"
        assert seen["opts"]["include_aux_inboxes"] is False
        assert seen["opts"]["force"] is True
        assert "# Example Page" in seen["md_text"]
        assert "Source URL: https://example.com/article" in seen["md_text"]
        assert seen["sidecar"]["source_url"] == "https://example.com/article"
        assert seen["sidecar"]["source_type"] == "web"
        assert seen["sidecar"]["extraction_method"] == "qt-web-extractor"
        assert any("开始直接入库链接" in m for m in messages)

    def test_ingest_link_no_index_skips_global_steps(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "scholaraio.sources.webtools.webextract",
            lambda url, *, pdf=None, base_url=None: {
                "url": url,
                "title": "Example Page",
                "text": "Body",
                "html": "",
                "error": "",
            },
        )

        seen: dict[str, object] = {}

        def fake_run_pipeline(step_names, cfg, opts):
            seen["steps"] = step_names

        monkeypatch.setattr("scholaraio.ingest.pipeline.run_pipeline", fake_run_pipeline)

        cfg = SimpleNamespace(_root=tmp_path, papers_dir=tmp_path / "data" / "papers")
        args = Namespace(
            urls=["https://example.com/article"],
            dry_run=False,
            force=False,
            pdf=False,
            no_index=True,
            json=False,
        )

        cli.cmd_ingest_link(args, cfg)

        assert seen["steps"] == ["extract_doc", "ingest"]

    def test_ingest_link_json_outputs_extracted_summary(self, tmp_path, monkeypatch):
        messages: list[str] = []
        monkeypatch.setattr(cli, "ui", messages.append)
        monkeypatch.setattr(
            "scholaraio.sources.webtools.webextract",
            lambda url, *, pdf=None, base_url=None: {
                "url": url,
                "title": "Example Page",
                "text": "Body",
                "html": "",
                "error": "",
            },
        )
        monkeypatch.setattr("scholaraio.ingest.pipeline.run_pipeline", lambda *args, **kwargs: None)

        cfg = SimpleNamespace(_root=tmp_path, papers_dir=tmp_path / "data" / "papers")
        args = Namespace(
            urls=["https://example.com/article"],
            dry_run=False,
            force=False,
            pdf=False,
            no_index=False,
            json=True,
        )

        cli.cmd_ingest_link(args, cfg)

        payload = json.loads(messages[-1])
        assert payload == [
            {
                "url": "https://example.com/article",
                "title": "Example Page",
                "markdown_file": "01-example-page.md",
            }
        ]
