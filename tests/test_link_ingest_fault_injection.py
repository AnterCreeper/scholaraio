"""Fault-injection tests for link_ingest module and CLI cmd_ingest_link.

Covers webextract failures, LLM failures, image download failures,
malformed data, filesystem errors, and CLI edge cases.
"""

from __future__ import annotations

import json
import sys
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from scholaraio import cli
from scholaraio.config import Config
from scholaraio.link_ingest import (
    _parse_llm_json,
    check_webextract_health,
    compute_content_hash,
    download_all_images,
    download_image,
    extract_images_from_html,
    extract_structure_with_llm,
    extract_with_webextract,
    find_existing_entry,
    ingest_url,
    list_entries,
    merge_images_into_content,
    parse_url,
    remove_entry,
    sanitize_filename,
)


class _MockHttpResp:
    """Mock urllib response that supports the context manager protocol."""

    def __init__(self, data: bytes):
        self._data = data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self):
        return self._data


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def papers_dir(tmp_path: Path) -> Path:
    d = tmp_path / "papers"
    d.mkdir()
    return d


@pytest.fixture()
def llm_cfg() -> dict:
    return {
        "backend": "openai-compat",
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com",
        "api_key": "fake-key",
        "timeout": 30,
        "timeout_toc": 120,
    }


@pytest.fixture()
def capture_ui(monkeypatch):
    messages: list[str] = []
    monkeypatch.setattr(cli, "ui", messages.append)
    return messages


@pytest.fixture()
def cli_cfg(tmp_path: Path):
    return SimpleNamespace(
        papers_dir=tmp_path / "papers",
        index_db=tmp_path / "index.db",
        llm=SimpleNamespace(
            backend="openai-compat",
            model="deepseek-chat",
            base_url="https://api.deepseek.com",
            api_key="fake-key",
            timeout=30,
            timeout_toc=120,
        ),
    )


# ---------------------------------------------------------------------------
# check_webextract_health
# ---------------------------------------------------------------------------


class TestCheckWebextractHealth:
    def test_returns_true_when_ok(self, monkeypatch):
        monkeypatch.setattr(
            "scholaraio.link_ingest.urllib.request.urlopen",
            lambda req, timeout=None: _MockHttpResp(b'{"status": "ok"}'),
        )
        assert check_webextract_health() is True

    def test_returns_false_on_network_error(self, monkeypatch):
        def boom(*a, **k):
            raise OSError("connection refused")

        monkeypatch.setattr("scholaraio.link_ingest.urllib.request.urlopen", boom)
        assert check_webextract_health() is False

    def test_returns_false_on_bad_json(self, monkeypatch):
        monkeypatch.setattr(
            "scholaraio.link_ingest.urllib.request.urlopen",
            lambda req, timeout=None: _MockHttpResp(b"not json"),
        )
        assert check_webextract_health() is False

    def test_returns_false_on_non_ok_status(self, monkeypatch):
        monkeypatch.setattr(
            "scholaraio.link_ingest.urllib.request.urlopen",
            lambda req, timeout=None: _MockHttpResp(b'{"status": "degraded"}'),
        )
        assert check_webextract_health() is False


# ---------------------------------------------------------------------------
# extract_with_webextract
# ---------------------------------------------------------------------------


class TestExtractWithWebextract:
    def test_success(self, monkeypatch):
        monkeypatch.setattr(
            "scholaraio.link_ingest.urllib.request.urlopen",
            lambda req, timeout=None: _MockHttpResp(b'{"title": "Test", "text": "hello"}'),
        )
        result = extract_with_webextract("http://example.com")
        assert result["title"] == "Test"

    def test_raises_on_network_error(self, monkeypatch):
        def boom(*a, **k):
            raise OSError("timeout")

        monkeypatch.setattr("scholaraio.link_ingest.urllib.request.urlopen", boom)
        with pytest.raises(OSError, match="timeout"):
            extract_with_webextract("http://example.com")

    def test_raises_on_bad_json(self, monkeypatch):
        monkeypatch.setattr(
            "scholaraio.link_ingest.urllib.request.urlopen",
            lambda req, timeout=None: _MockHttpResp(b"not json"),
        )
        with pytest.raises(json.JSONDecodeError):
            extract_with_webextract("http://example.com")


# ---------------------------------------------------------------------------
# find_existing_entry
# ---------------------------------------------------------------------------


class TestFindExistingEntry:
    def test_found_via_link_metadata(self, papers_dir: Path):
        d = papers_dir / "example-com-2024-test"
        d.mkdir()
        (d / "link_metadata.json").write_text(
            json.dumps({"source_url": "http://example.com/page"}), encoding="utf-8"
        )
        assert find_existing_entry("http://example.com/page", papers_dir) == d

    def test_found_via_meta_json(self, papers_dir: Path):
        d = papers_dir / "example-com-2024-test"
        d.mkdir()
        (d / "meta.json").write_text(
            json.dumps({"source_url": "http://example.com/page2"}), encoding="utf-8"
        )
        assert find_existing_entry("http://example.com/page2", papers_dir) == d

    def test_not_found(self, papers_dir: Path):
        assert find_existing_entry("http://example.com/missing", papers_dir) is None

    def test_malformed_json_ignored(self, papers_dir: Path):
        d = papers_dir / "example-com-2024-bad"
        d.mkdir()
        (d / "link_metadata.json").write_text("not json", encoding="utf-8")
        (d / "meta.json").write_text("also bad", encoding="utf-8")
        assert find_existing_entry("http://example.com/anything", papers_dir) is None


# ---------------------------------------------------------------------------
# ingest_url fault injection
# ---------------------------------------------------------------------------


class TestIngestUrlFaultInjection:
    def test_returns_exists_when_already_ingested(self, papers_dir: Path, llm_cfg: dict):
        d = papers_dir / "example-com-2024-test"
        d.mkdir()
        (d / "link_metadata.json").write_text(
            json.dumps({"source_url": "http://example.com/exists"}), encoding="utf-8"
        )
        result = ingest_url("http://example.com/exists", llm_cfg, papers_dir)
        assert result["status"] == "exists"

    def test_webextract_error_returns_error(self, papers_dir: Path, llm_cfg: dict, monkeypatch):
        def boom(*a, **k):
            raise OSError("webextract down")

        monkeypatch.setattr("scholaraio.link_ingest.extract_with_webextract", boom)
        result = ingest_url("http://example.com/fail", llm_cfg, papers_dir)
        assert result["status"] == "error"
        assert "webextract down" in result["error"]

    def test_partial_error_with_short_content_returns_error(self, papers_dir: Path, llm_cfg: dict, monkeypatch):
        def fake_extract(url, **kw):
            return {"title": "T", "text": "short", "error": "blocked"}

        monkeypatch.setattr("scholaraio.link_ingest.extract_with_webextract", fake_extract)
        result = ingest_url("http://example.com/partial", llm_cfg, papers_dir)
        assert result["status"] == "error"
        assert "blocked" in result["error"]

    def test_partial_error_with_long_content_succeeds(self, papers_dir: Path, llm_cfg: dict, monkeypatch):
        long_content = "word " * 100

        def fake_extract(url, **kw):
            return {"title": "T", "text": long_content, "error": "some warning"}

        monkeypatch.setattr("scholaraio.link_ingest.extract_with_webextract", fake_extract)
        monkeypatch.setattr(
            "scholaraio.link_ingest.extract_structure_with_llm",
            lambda content, cfg: {"abstract": "", "structure_tree": [], "sections_summary": {}},
        )
        result = ingest_url("http://example.com/partial_ok", llm_cfg, papers_dir)
        assert result["status"] == "success"
        assert result["dir"].exists()

    def test_empty_content_returns_error(self, papers_dir: Path, llm_cfg: dict, monkeypatch):
        def fake_extract(url, **kw):
            return {"title": "T", "text": "   "}

        monkeypatch.setattr("scholaraio.link_ingest.extract_with_webextract", fake_extract)
        result = ingest_url("http://example.com/empty", llm_cfg, papers_dir)
        assert result["status"] == "error"
        assert "Empty content" in result["error"]

    def test_ingest_success_with_images_and_structure(self, papers_dir: Path, llm_cfg: dict, monkeypatch):
        content = "# Hello\n\n![alt](http://example.com/img.png)"

        def fake_extract(url, **kw):
            return {"title": "Test Page", "text": content, "html": "<img src='img.png'>"}

        monkeypatch.setattr("scholaraio.link_ingest.extract_with_webextract", fake_extract)
        monkeypatch.setattr(
            "scholaraio.link_ingest.extract_structure_with_llm",
            lambda content, cfg: {
                "abstract": "abs",
                "structure_tree": [{"level": 1, "title": "Hello", "anchor": "hello"}],
                "sections_summary": {"hello": "summary"},
            },
        )
        # Mock image download to avoid network
        monkeypatch.setattr(
            "scholaraio.link_ingest.download_image",
            lambda img_url, base_url, images_dir: (True, "img.png"),
        )

        result = ingest_url("http://example.com/ok", llm_cfg, papers_dir)
        assert result["status"] == "success"
        entry_dir = result["dir"]
        assert (entry_dir / "paper.md").exists()
        assert (entry_dir / "meta.json").exists()
        assert (entry_dir / "link_metadata.json").exists()

        meta = json.loads((entry_dir / "meta.json").read_text(encoding="utf-8"))
        assert meta["paper_type"] == "webdocument"
        assert meta["structure_tree"][0]["title"] == "Hello"

    def test_force_reingest_overwrites_existing(self, papers_dir: Path, llm_cfg: dict, monkeypatch):
        d = papers_dir / "example-com-2024-old"
        d.mkdir()
        old_meta = {"id": "preserve-me", "source_url": "http://example.com/force"}
        (d / "meta.json").write_text(json.dumps(old_meta), encoding="utf-8")
        (d / "link_metadata.json").write_text(
            json.dumps({"source_url": "http://example.com/force"}), encoding="utf-8"
        )

        def fake_extract(url, **kw):
            return {"title": "New Title", "text": "new content"}

        monkeypatch.setattr("scholaraio.link_ingest.extract_with_webextract", fake_extract)
        monkeypatch.setattr(
            "scholaraio.link_ingest.extract_structure_with_llm",
            lambda content, cfg: {"abstract": "", "structure_tree": [], "sections_summary": {}},
        )

        result = ingest_url("http://example.com/force", llm_cfg, papers_dir, force=True)
        assert result["status"] == "success"
        assert result["dir"] == d

        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        assert meta["title"] == "New Title"
        assert meta["id"] == "preserve-me"  # UUID preserved

    def test_directory_collision_avoidance(self, papers_dir: Path, llm_cfg: dict, monkeypatch):
        from datetime import datetime
        # Pre-create a directory that would collide (match ingest_url naming)
        expected_name = f"example.com-{datetime.now().year}-Title"
        (papers_dir / expected_name).mkdir()

        def fake_extract(url, **kw):
            return {"title": "Title", "text": "content"}

        monkeypatch.setattr("scholaraio.link_ingest.extract_with_webextract", fake_extract)
        monkeypatch.setattr(
            "scholaraio.link_ingest.extract_structure_with_llm",
            lambda content, cfg: {"abstract": "", "structure_tree": [], "sections_summary": {}},
        )

        result = ingest_url("http://example.com/title", llm_cfg, papers_dir)
        assert result["status"] == "success"
        assert result["dir"].name == f"{expected_name}-2"

    def test_old_meta_missing_preserve_new_uuid(self, papers_dir: Path, llm_cfg: dict, monkeypatch):
        d = papers_dir / "example-com-2024-old"
        d.mkdir()
        (d / "link_metadata.json").write_text(
            json.dumps({"source_url": "http://example.com/old"}), encoding="utf-8"
        )
        # meta.json missing entirely

        def fake_extract(url, **kw):
            return {"title": "Old", "text": "content"}

        monkeypatch.setattr("scholaraio.link_ingest.extract_with_webextract", fake_extract)
        monkeypatch.setattr(
            "scholaraio.link_ingest.extract_structure_with_llm",
            lambda content, cfg: {"abstract": "", "structure_tree": [], "sections_summary": {}},
        )

        result = ingest_url("http://example.com/old", llm_cfg, papers_dir, force=True)
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        # Since old meta doesn't exist, new UUID is generated
        assert "id" in meta
        assert len(meta["id"]) == 36  # uuid format


# ---------------------------------------------------------------------------
# download_image
# ---------------------------------------------------------------------------


class TestDownloadImage:
    def test_success(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(
            "scholaraio.link_ingest.urllib.request.urlopen",
            lambda req, timeout=None: _MockHttpResp(b"fake-image-data"),
        )
        images_dir = tmp_path / "images"
        images_dir.mkdir()
        success, filename = download_image("http://example.com/img.png", "http://example.com/", images_dir)
        assert success is True
        assert filename == "img.png"
        assert (images_dir / "img.png").read_bytes() == b"fake-image-data"

    def test_network_failure(self, tmp_path: Path, monkeypatch):
        def boom(*a, **k):
            raise OSError("download failed")

        monkeypatch.setattr("scholaraio.link_ingest.urllib.request.urlopen", boom)
        images_dir = tmp_path / "images"
        images_dir.mkdir()
        success, error = download_image("http://example.com/img.png", "http://example.com/", images_dir)
        assert success is False
        assert "download failed" in error

    def test_collision_avoidance(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(
            "scholaraio.link_ingest.urllib.request.urlopen",
            lambda req, timeout=None: _MockHttpResp(b"data"),
        )
        images_dir = tmp_path / "images"
        images_dir.mkdir()
        (images_dir / "img.png").write_bytes(b"old")

        success, filename = download_image("http://example.com/img.png", "http://example.com/", images_dir)
        assert filename == "img_1.png"
        assert (images_dir / "img_1.png").exists()

    def test_no_path_in_url(self, tmp_path: Path):
        images_dir = tmp_path / "images"
        images_dir.mkdir()
        success, error = download_image("http://example.com", "http://example.com/", images_dir)
        assert success is False
        assert "No path" in error


# ---------------------------------------------------------------------------
# download_all_images
# ---------------------------------------------------------------------------


class TestDownloadAllImages:
    def test_downloads_markdown_images(self, tmp_path: Path, monkeypatch):
        content = "![a](http://x.com/1.png) ![b](http://x.com/2.png)"
        entry_dir = tmp_path / "entry"
        entry_dir.mkdir()

        calls = []

        def fake_download(img_url, base_url, images_dir):
            calls.append(img_url)
            return True, "local.png"

        monkeypatch.setattr("scholaraio.link_ingest.download_image", fake_download)
        new_content, info = download_all_images(content, "http://x.com/", entry_dir)

        assert len(calls) == 2
        assert "images/local.png" in new_content
        assert info[0]["status"] == "downloaded"

    def test_skips_data_uris(self, tmp_path: Path, monkeypatch):
        content = "![a](data:image/png;base64,abc)"
        entry_dir = tmp_path / "entry"
        entry_dir.mkdir()

        monkeypatch.setattr(
            "scholaraio.link_ingest.download_image",
            lambda *a, **k: (True, "x.png"),
        )
        new_content, info = download_all_images(content, "http://x.com/", entry_dir)
        assert info[0]["status"] == "skipped"
        assert "data URI" in info[0]["reason"]

    def test_html_img_tags_also_extracted(self, tmp_path: Path, monkeypatch):
        content = '<img src="http://x.com/h.png" alt="html img">'
        entry_dir = tmp_path / "entry"
        entry_dir.mkdir()

        calls = []

        def fake_download(img_url, base_url, images_dir):
            calls.append(img_url)
            return True, "h.png"

        monkeypatch.setattr("scholaraio.link_ingest.download_image", fake_download)
        new_content, info = download_all_images(content, "http://x.com/", entry_dir)

        assert len(calls) == 1
        assert info[0]["status"] == "downloaded"

    def test_partial_failure_keeps_original(self, tmp_path: Path, monkeypatch):
        content = "![a](http://x.com/1.png)"
        entry_dir = tmp_path / "entry"
        entry_dir.mkdir()

        monkeypatch.setattr(
            "scholaraio.link_ingest.download_image",
            lambda *a, **k: (False, "timeout"),
        )
        new_content, info = download_all_images(content, "http://x.com/", entry_dir)
        assert "![a](http://x.com/1.png)" in new_content
        assert info[0]["status"] == "failed"
        assert "timeout" in info[0]["error"]


# ---------------------------------------------------------------------------
# extract_structure_with_llm
# ---------------------------------------------------------------------------


class TestExtractStructureWithLlm:
    def test_returns_structure_on_success(self, llm_cfg: dict, monkeypatch):
        class FakeResult:
            content = '{"abstract": "abs", "structure_tree": [{"level": 1, "title": "T"}]}'

        monkeypatch.setattr("scholaraio.metrics.call_llm", lambda *a, **k: FakeResult())
        result = extract_structure_with_llm("content", llm_cfg)
        assert result["abstract"] == "abs"
        assert result["structure_tree"][0]["title"] == "T"

    def test_returns_empty_when_no_api_key(self, llm_cfg: dict):
        cfg_no_key = {**llm_cfg, "api_key": ""}
        result = extract_structure_with_llm("content", cfg_no_key)
        assert result == {"structure_tree": [], "sections_summary": {}, "abstract": ""}

    def test_returns_empty_on_llm_exception(self, llm_cfg: dict, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("llm down")

        monkeypatch.setattr("scholaraio.metrics.call_llm", boom)
        result = extract_structure_with_llm("content", llm_cfg)
        assert result == {"structure_tree": [], "sections_summary": {}, "abstract": ""}


# ---------------------------------------------------------------------------
# _parse_llm_json
# ---------------------------------------------------------------------------


class TestParseLlmJson:
    def test_plain_json(self):
        assert _parse_llm_json('{"a": 1}') == {"a": 1}

    def test_code_fence_json(self):
        text = "```json\n{\"a\": 1}\n```"
        assert _parse_llm_json(text) == {"a": 1}

    def test_fallback_on_malformed(self):
        assert _parse_llm_json("not json") == {"structure_tree": [], "sections_summary": {}, "abstract": ""}

    def test_extracts_json_from_text(self):
        text = "Here is the result:\n```json\n{\"abstract\": \"x\"}\n```\nHope that helps!"
        assert _parse_llm_json(text) == {"abstract": "x"}


# ---------------------------------------------------------------------------
# list_entries
# ---------------------------------------------------------------------------


class TestListEntries:
    def test_lists_valid_entries(self, papers_dir: Path):
        d = papers_dir / "example-com-2024-test"
        d.mkdir()
        (d / "meta.json").write_text(
            json.dumps({
                "title": "Test",
                "source_url": "http://example.com",
                "paper_type": "webdocument"
            }),
            encoding="utf-8",
        )
        entries = list_entries(papers_dir)
        assert len(entries) == 1
        assert entries[0]["title"] == "Test"

    def test_skips_malformed_meta(self, papers_dir: Path):
        d = papers_dir / "example-com-2024-bad"
        d.mkdir()
        (d / "meta.json").write_text("bad json", encoding="utf-8")
        entries = list_entries(papers_dir)
        assert entries == []

    def test_empty_directory(self, papers_dir: Path):
        assert list_entries(papers_dir) == []


# ---------------------------------------------------------------------------
# remove_entry
# ---------------------------------------------------------------------------


class TestRemoveEntry:
    def test_removes_existing(self, papers_dir: Path):
        d = papers_dir / "example-com-2024-test"
        d.mkdir()
        (d / "link_metadata.json").write_text(
            json.dumps({"source_url": "http://example.com/rm"}), encoding="utf-8"
        )
        assert remove_entry("http://example.com/rm", papers_dir) is True
        assert not d.exists()

    def test_returns_false_when_not_found(self, papers_dir: Path):
        assert remove_entry("http://example.com/missing", papers_dir) is False


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


class TestUtilityFunctions:
    def test_compute_content_hash(self):
        h1 = compute_content_hash("hello")
        h2 = compute_content_hash("hello")
        h3 = compute_content_hash("world")
        assert h1 == h2
        assert h1 != h3
        assert len(h1) == 16

    def test_sanitize_filename(self):
        assert sanitize_filename("a/b<c>d|e?f*g") == "a_b_c_d_e_f_g"
        assert sanitize_filename("  hello world  ") == "hello_world"

    def test_parse_url(self):
        assert parse_url("https://www.example.com/path/to/page") == ("example.com", "path-to-page")
        assert parse_url("http://unknown") == ("unknown", "")

    def test_extract_images_from_html(self):
        html = '<img src="a.png" alt="A"><IMG src="b.png">'
        images = extract_images_from_html(html)
        assert len(images) == 2
        assert images[0] == ("A", "a.png")
        assert images[1] == ("image", "b.png")

    def test_merge_images_into_content(self):
        content = "# Title"
        html = '<img src="i.png" alt="img">'
        result = merge_images_into_content(content, html, "http://example.com/")
        assert "## 图片引用" in result
        # merge_images_into_content uses raw img src from HTML (no urljoin)
        assert "![img](i.png)" in result


# ---------------------------------------------------------------------------
# CLI cmd_ingest_link
# ---------------------------------------------------------------------------


class TestCliIngestLink:
    def test_exits_when_webextract_unavailable(self, capture_ui, cli_cfg, monkeypatch):
        monkeypatch.setattr("scholaraio.link_ingest.check_webextract_health", lambda: False)
        monkeypatch.setattr(sys, "exit", MagicMock(side_effect=SystemExit(1)))

        args = Namespace(urls=["http://example.com"], file=None, list=False, remove=None, force=False, no_index=False)
        with pytest.raises(SystemExit):
            cli.cmd_ingest_link(args, cli_cfg)
        assert any("webextract 服务不可用" in m for m in capture_ui)

    def test_list_entries(self, capture_ui, cli_cfg, monkeypatch):
        monkeypatch.setattr("scholaraio.link_ingest.check_webextract_health", lambda: True)
        monkeypatch.setattr(
            "scholaraio.link_ingest.list_entries",
            lambda p: [
                {"title": "Entry 1", "url": "http://a.com", "paper_type": "webdocument", "dir": Path("/x/1")}
            ],
        )

        args = Namespace(urls=[], file=None, list=True, remove=None, force=False, no_index=False)
        cli.cmd_ingest_link(args, cli_cfg)
        assert any("Entry 1" in m for m in capture_ui)

    def test_list_empty(self, capture_ui, cli_cfg, monkeypatch):
        monkeypatch.setattr("scholaraio.link_ingest.check_webextract_health", lambda: True)
        monkeypatch.setattr("scholaraio.link_ingest.list_entries", lambda p: [])

        args = Namespace(urls=[], file=None, list=True, remove=None, force=False, no_index=False)
        cli.cmd_ingest_link(args, cli_cfg)
        assert any("无已入库条目" in m for m in capture_ui)

    def test_remove_existing(self, capture_ui, cli_cfg, monkeypatch):
        monkeypatch.setattr("scholaraio.link_ingest.check_webextract_health", lambda: True)
        monkeypatch.setattr("scholaraio.link_ingest.remove_entry", lambda url, p: True)

        args = Namespace(urls=[], file=None, list=False, remove="http://a.com", force=False, no_index=False)
        cli.cmd_ingest_link(args, cli_cfg)
        assert any("已删除" in m for m in capture_ui)

    def test_remove_missing_exits(self, capture_ui, cli_cfg, monkeypatch):
        monkeypatch.setattr("scholaraio.link_ingest.check_webextract_health", lambda: True)
        monkeypatch.setattr("scholaraio.link_ingest.remove_entry", lambda url, p: False)
        monkeypatch.setattr(sys, "exit", MagicMock(side_effect=SystemExit(1)))

        args = Namespace(urls=[], file=None, list=False, remove="http://a.com", force=False, no_index=False)
        with pytest.raises(SystemExit):
            cli.cmd_ingest_link(args, cli_cfg)

    def test_file_not_found_exits(self, capture_ui, cli_cfg, monkeypatch):
        monkeypatch.setattr("scholaraio.link_ingest.check_webextract_health", lambda: True)
        monkeypatch.setattr(sys, "exit", MagicMock(side_effect=SystemExit(1)))

        args = Namespace(urls=[], file="/nonexistent.txt", list=False, remove=None, force=False, no_index=False)
        with pytest.raises(SystemExit):
            cli.cmd_ingest_link(args, cli_cfg)
        assert any("文件不存在" in m for m in capture_ui)

    def test_file_ingestion(self, capture_ui, cli_cfg, monkeypatch, tmp_path: Path):
        monkeypatch.setattr("scholaraio.link_ingest.check_webextract_health", lambda: True)
        monkeypatch.setattr(
            "scholaraio.link_ingest.ingest_url",
            lambda url, cfg, papers_dir, force=False: {
                "status": "success", "dir": tmp_path / "x", "url": url, "title": "T"
            },
        )

        url_file = tmp_path / "urls.txt"
        url_file.write_text("http://a.com\nhttp://b.com\n", encoding="utf-8")

        args = Namespace(urls=[], file=str(url_file), list=False, remove=None, force=False, no_index=True)
        cli.cmd_ingest_link(args, cli_cfg)
        assert any("2/2 成功" in m for m in capture_ui)

    def test_url_error_reported(self, capture_ui, cli_cfg, monkeypatch):
        monkeypatch.setattr("scholaraio.link_ingest.check_webextract_health", lambda: True)
        monkeypatch.setattr(
            "scholaraio.link_ingest.ingest_url",
            lambda url, cfg, papers_dir, force=False: {
                "status": "error", "error": "timeout", "url": url
            },
        )

        args = Namespace(urls=["http://fail.com"], file=None, list=False, remove=None, force=False, no_index=True)
        cli.cmd_ingest_link(args, cli_cfg)
        assert any("timeout" in m for m in capture_ui)
        assert any("0/1 成功" in m for m in capture_ui)

    def test_exists_counts_as_success(self, capture_ui, cli_cfg, monkeypatch):
        monkeypatch.setattr("scholaraio.link_ingest.check_webextract_health", lambda: True)
        monkeypatch.setattr(
            "scholaraio.link_ingest.ingest_url",
            lambda url, cfg, papers_dir, force=False: {
                "status": "exists", "dir": Path("/x"), "url": url
            },
        )

        args = Namespace(urls=["http://exists.com"], file=None, list=False, remove=None, force=False, no_index=True)
        cli.cmd_ingest_link(args, cli_cfg)
        assert any("1/1 成功" in m for m in capture_ui)

    def test_index_update_on_success(self, capture_ui, cli_cfg, monkeypatch):
        monkeypatch.setattr("scholaraio.link_ingest.check_webextract_health", lambda: True)
        monkeypatch.setattr(
            "scholaraio.link_ingest.ingest_url",
            lambda url, cfg, papers_dir, force=False: {
                "status": "success", "dir": Path("/x"), "url": url, "title": "T"
            },
        )
        monkeypatch.setattr("scholaraio.vectors.build_vectors", lambda **kw: 1)
        monkeypatch.setattr("scholaraio.index.build_index", lambda **kw: 1)

        args = Namespace(urls=["http://ok.com"], file=None, list=False, remove=None, force=False, no_index=False)
        cli.cmd_ingest_link(args, cli_cfg)
        assert any("索引更新完成" in m for m in capture_ui)

    def test_index_update_failure_reported(self, capture_ui, cli_cfg, monkeypatch):
        monkeypatch.setattr("scholaraio.link_ingest.check_webextract_health", lambda: True)
        monkeypatch.setattr(
            "scholaraio.link_ingest.ingest_url",
            lambda url, cfg, papers_dir, force=False: {
                "status": "success", "dir": Path("/x"), "url": url, "title": "T"
            },
        )

        def boom(**kw):
            raise RuntimeError("index crashed")

        monkeypatch.setattr("scholaraio.vectors.build_vectors", boom)

        args = Namespace(urls=["http://ok.com"], file=None, list=False, remove=None, force=False, no_index=False)
        cli.cmd_ingest_link(args, cli_cfg)
        assert any("索引更新失败" in m for m in capture_ui)

    def test_no_index_skips_indexing(self, capture_ui, cli_cfg, monkeypatch):
        monkeypatch.setattr("scholaraio.link_ingest.check_webextract_health", lambda: True)
        monkeypatch.setattr(
            "scholaraio.link_ingest.ingest_url",
            lambda url, cfg, papers_dir, force=False: {
                "status": "success", "dir": Path("/x"), "url": url, "title": "T"
            },
        )
        # If build_vectors were called unexpectedly, this would be an error since we didn't mock it
        # But we can't easily assert it wasn't called without a spy.
        # Instead, we just verify no indexing-related output appears.

        args = Namespace(urls=["http://ok.com"], file=None, list=False, remove=None, force=False, no_index=True)
        cli.cmd_ingest_link(args, cli_cfg)
        assert not any("索引" in m for m in capture_ui)

    def test_no_urls_exits(self, capture_ui, cli_cfg, monkeypatch):
        monkeypatch.setattr("scholaraio.link_ingest.check_webextract_health", lambda: True)
        monkeypatch.setattr(sys, "exit", MagicMock(side_effect=SystemExit(1)))

        args = Namespace(urls=[], file=None, list=False, remove=None, force=False, no_index=False)
        with pytest.raises(SystemExit):
            cli.cmd_ingest_link(args, cli_cfg)
        assert any("请提供至少一个 URL" in m for m in capture_ui)
