"""Tests for scholaraio.publish_site.generator."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from scholaraio.publish_site.generator import (
    build_source_zips,
    generate_site,
    link_or_copy_pdfs,
    load_papers,
    slugify,
)


class TestSlugify:
    def test_lowercases_and_replaces_special_chars(self):
        assert slugify("Hello World!") == "hello-world"

    def test_strips_leading_trailing_dashes(self):
        assert slugify("--Test--") == "test"

    def test_preserves_alphanum_and_hyphens(self):
        assert slugify("a-b-123") == "a-b-123"


class TestLoadPapers:
    def test_loads_metadata_sorted_reverse(self, tmp_path: Path):
        published = tmp_path / "published"
        p1 = published / "2024-01-01-Paper-One"
        p2 = published / "2024-02-01-Paper-Two"
        p1.mkdir(parents=True)
        p2.mkdir(parents=True)

        (p1 / "metadata.json").write_text(
            json.dumps({"title": "One", "date": "2024-01-01"}), encoding="utf-8"
        )
        (p2 / "metadata.json").write_text(
            json.dumps({"title": "Two", "date": "2024-02-01"}), encoding="utf-8"
        )

        papers = load_papers(published)
        assert len(papers) == 2
        # Sorted reverse by folder name
        assert papers[0]["title"] == "Two"
        assert papers[1]["title"] == "One"
        assert papers[0]["_slug"] == "2024-02-01-paper-two"

    def test_skips_non_directories(self, tmp_path: Path):
        published = tmp_path / "published"
        published.mkdir()
        (published / "not-a-dir.txt").write_text("x")
        assert load_papers(published) == []

    def test_skips_missing_metadata(self, tmp_path: Path):
        published = tmp_path / "published"
        (published / "empty-dir").mkdir(parents=True)
        assert load_papers(published) == []


class TestBuildSourceZips:
    def test_creates_zip_with_tex_images_misc_meta(self, tmp_path: Path):
        published = tmp_path / "published"
        src = published / "2024-01-01-Test"
        src.mkdir(parents=True)

        (src / "main.tex").write_text("\\documentclass{article}", encoding="utf-8")
        (src / "images").mkdir()
        (src / "images" / "fig.png").write_bytes(b"png")
        (src / "misc").mkdir()
        (src / "misc" / "notes.txt").write_text("notes", encoding="utf-8")

        meta = {
            "title": "Test",
            "date": "2024-01-01",
            "tex_files": ["main.tex"],
            "images_dir": "images",
            "misc_dir": "misc",
            "_source_dir": "2024-01-01-Test",
            "_slug": "2024-01-01-test",
        }
        (src / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")

        build_source_zips([meta], published)

        zip_path = src / "2024-01-01-test-source.zip"
        assert zip_path.exists()

        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            assert "main.tex" in names
            assert "images/fig.png" in names
            assert "misc/notes.txt" in names
            assert "metadata.json" in names

        assert meta["_source_zip_url"] == "assets/papers/2024-01-01-test/2024-01-01-test-source.zip"


class TestLinkOrCopyPdfs:
    def test_copy_mode_copies_pdf_and_zip(self, tmp_path: Path):
        published = tmp_path / "published"
        out = tmp_path / "site"
        src = published / "2024-01-01-Test"
        src.mkdir(parents=True)
        (src / "paper.pdf").write_bytes(b"pdf")
        (src / "2024-01-01-test-source.zip").write_bytes(b"zip")

        meta = {
            "title": "Test",
            "pdf_filename": "paper.pdf",
            "_source_dir": "2024-01-01-Test",
            "_slug": "2024-01-01-test",
        }

        link_or_copy_pdfs([meta], published, out, copy_assets=True)

        assets = out / "assets" / "papers" / "2024-01-01-test"
        assert (assets / "paper.pdf").read_bytes() == b"pdf"
        assert (assets / "2024-01-01-test-source.zip").read_bytes() == b"zip"
        assert meta["_pdf_url"] == "assets/papers/2024-01-01-test/paper.pdf"

    def test_symlink_mode_creates_symlink(self, tmp_path: Path):
        published = tmp_path / "published"
        out = tmp_path / "site"
        src = published / "2024-01-01-Test"
        src.mkdir(parents=True)
        (src / "paper.pdf").write_bytes(b"pdf")

        meta = {
            "title": "Test",
            "pdf_filename": "paper.pdf",
            "_source_dir": "2024-01-01-Test",
            "_slug": "2024-01-01-test",
        }

        link_or_copy_pdfs([meta], published, out, copy_assets=False)

        assets = out / "assets" / "papers" / "2024-01-01-test"
        assert assets.is_symlink()
        assert (assets / "paper.pdf").read_bytes() == b"pdf"

    def test_missing_pdf_sets_empty_url(self, tmp_path: Path):
        published = tmp_path / "published"
        out = tmp_path / "site"
        src = published / "2024-01-01-Test"
        src.mkdir(parents=True)

        meta = {
            "title": "Test",
            "pdf_filename": "missing.pdf",
            "_source_dir": "2024-01-01-Test",
            "_slug": "2024-01-01-test",
        }

        link_or_copy_pdfs([meta], published, out, copy_assets=True)
        assert meta["_pdf_url"] == ""


class TestGenerateSite:
    def test_generates_all_files_copy_mode(self, tmp_path: Path):
        published = tmp_path / "published"
        out = tmp_path / "site"
        src = published / "2024-01-01-Test"
        src.mkdir(parents=True)
        (src / "paper.pdf").write_bytes(b"pdf")

        meta = {
            "title": "Test Paper",
            "date": "2024-01-01",
            "keywords": ["AI"],
            "subject": "CS",
            "pdf_filename": "paper.pdf",
            "tex_files": ["main.tex"],
            "authors": ["A. Author"],
            "note": "Note",
        }
        (src / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")
        (src / "main.tex").write_text("x", encoding="utf-8")

        generate_site(published, out, copy_assets=True)

        assert (out / "index.html").exists()
        assert (out / "css" / "style.css").exists()
        assert (out / "js" / "main.js").exists()
        assert (out / "README.md").exists()

        html = (out / "index.html").read_text(encoding="utf-8")
        assert "Test Paper" in html
        assert "AI" in html
        assert "CS" in html

    def test_no_pprints_message_when_empty(self, tmp_path: Path, capsys):
        published = tmp_path / "published"
        published.mkdir()
        out = tmp_path / "site"

        generate_site(published, out, copy_assets=True)

        captured = capsys.readouterr()
        assert "No papers found." in captured.out or "No papers found." in captured.err
