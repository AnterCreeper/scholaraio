from __future__ import annotations

import json

from scholaraio.toolref import (
    _build_bioinformatics_manifest,
    _build_openfoam_manifest,
    _clean_manifest_text,
    _has_local_docs,
    _normalize_search_query,
    _normalize_program_filter,
    _pick_manifest_synopsis,
    _parse_manifest_html,
    toolref_fetch,
    toolref_list,
    toolref_show,
)


def test_normalize_program_filter_for_qe():
    assert _normalize_program_filter("qe", "pw") == "pw.x"
    assert _normalize_program_filter("qe", "ph.x") == "ph.x"


def test_normalize_program_filter_for_non_qe():
    assert _normalize_program_filter("openfoam", "simpleFoam") == "simplefoam"
    assert _normalize_program_filter("bioinformatics", "samtools") == "samtools"


def test_normalize_search_query_rewrites_punctuation_runs():
    assert _normalize_search_query("k-point/convergence") == "k point convergence"
    assert _normalize_search_query("  spike__rbd ") == "spike rbd"


def test_build_openfoam_manifest_uses_requested_version():
    manifest = _build_openfoam_manifest("2312")
    assert manifest
    assert all("page_name" in item for item in manifest)
    assert any("/2312/" in item["url"] for item in manifest if "doc.openfoam.com" in item["url"])


def test_build_bioinformatics_manifest_contains_multiple_subtools():
    manifest = _build_bioinformatics_manifest("2026-03-curated")
    programs = {item["program"] for item in manifest}
    assert {"blastn", "minimap2", "samtools", "bcftools", "mafft", "iqtree", "esmfold"} <= programs


def test_parse_manifest_html_extracts_main_text(tmp_path):
    html_path = tmp_path / "page.html"
    meta_path = tmp_path / "page.json"

    html_path.write_text(
        """
        <html>
          <body>
            <main>
              <h1>simpleFoam</h1>
              <p>Steady-state incompressible solver.</p>
              <pre><code>simpleFoam -case motorBike</code></pre>
            </main>
          </body>
        </html>
        """,
        encoding="utf-8",
    )
    meta_path.write_text(
        json.dumps(
            {
                "program": "simpleFoam",
                "section": "solver",
                "page_name": "openfoam/simpleFoam",
                "title": "simpleFoam",
            }
        ),
        encoding="utf-8",
    )

    records = _parse_manifest_html(html_path)

    assert len(records) == 1
    record = records[0]
    assert record["page_name"] == "openfoam/simpleFoam"
    assert "Steady-state incompressible solver." in record["content"]
    assert "simpleFoam -case motorBike" in record["content"]


def test_has_local_docs_for_manifest_html(tmp_path, monkeypatch):
    from scholaraio import toolref as mod

    monkeypatch.setattr(mod, "_DEFAULT_TOOLREF_DIR", tmp_path)
    pages_dir = tmp_path / "openfoam" / "2312" / "pages"
    pages_dir.mkdir(parents=True)
    assert not _has_local_docs("openfoam", "2312")

    (pages_dir / "001-openfoam-simpleFoam.html").write_text("<html></html>", encoding="utf-8")
    (pages_dir / "001-openfoam-simpleFoam.json").write_text("{}", encoding="utf-8")
    assert not _has_local_docs("openfoam", "2312")

    manifest = _build_openfoam_manifest("2312")
    for idx, item in enumerate(manifest, start=1):
        (pages_dir / f"{idx:03d}-{item['page_name'].replace('/', '-')}.html").write_text("<html></html>", encoding="utf-8")
        (pages_dir / f"{idx:03d}-{item['page_name'].replace('/', '-')}.json").write_text("{}", encoding="utf-8")
    assert _has_local_docs("openfoam", "2312")


def test_clean_manifest_text_removes_common_navigation_and_footer():
    raw = """
Top
Toggle navigation
simpleFoam
- solvers
Overview
Steady-state incompressible solver.
Search results
Found a content problem with this page?
"""
    cleaned = _clean_manifest_text(raw, "simpleFoam", "simpleFoam")
    assert "Toggle navigation" not in cleaned
    assert "Search results" not in cleaned
    assert "Steady-state incompressible solver." in cleaned


def test_pick_manifest_synopsis_skips_generic_lines():
    lines = ["simpleFoam", "- solvers", "Overview", "Steady-state incompressible solver."]
    assert _pick_manifest_synopsis(lines, "simpleFoam") == "Steady-state incompressible solver."


def test_clean_manifest_text_anchors_blast_manual():
    raw = """
Bookshelf
Toggle navigation
BLAST® Command Line Applications User Manual
This manual documents the BLAST command line applications.
Search results
"""
    cleaned = _clean_manifest_text(raw, "BLAST+ user manual", "blastn")
    assert cleaned.startswith("BLAST")
    assert "Bookshelf" not in cleaned


def test_parse_manifest_html_uses_dictionary_synopsis(tmp_path):
    html_path = tmp_path / "page.html"
    meta_path = tmp_path / "page.json"
    html_path.write_text(
        """
        <html><body><main><h1>fvSchemes</h1><pre><code>FoamFile {}</code></pre></main></body></html>
        """,
        encoding="utf-8",
    )
    meta_path.write_text(
        json.dumps(
            {
                "program": "fvSchemes",
                "section": "dictionary",
                "page_name": "openfoam/fvSchemes",
                "title": "fvSchemes",
            }
        ),
        encoding="utf-8",
    )

    record = _parse_manifest_html(html_path)[0]
    assert record["synopsis"] == "fvSchemes dictionary"


def test_toolref_fetch_manifest_force_rebuilds_pages(tmp_path, monkeypatch):
    from scholaraio import toolref as mod

    class FakeResponse:
        def __init__(self, text: str):
            self.text = text

        def raise_for_status(self):
            return None

    class FakeSession:
        def __init__(self):
            self.headers = {}

        def get(self, url, timeout=60):
            return FakeResponse(f"<html><body><main><h1>{url}</h1></main></body></html>")

    monkeypatch.setattr(mod, "_DEFAULT_TOOLREF_DIR", tmp_path)
    monkeypatch.setattr(mod.requests, "Session", FakeSession)
    monkeypatch.setattr(
        mod,
        "_build_manifest",
        lambda tool, version: [
            {
                "program": "simpleFoam",
                "section": "solver",
                "page_name": "openfoam/simpleFoam",
                "title": "simpleFoam",
                "url": "https://example.org/simpleFoam",
            }
        ],
    )

    count = toolref_fetch("openfoam", version="2312", cfg=None)
    assert count == 1

    extra = tmp_path / "openfoam" / "2312" / "pages" / "stale.html"
    extra.write_text("stale", encoding="utf-8")

    count = toolref_fetch("openfoam", version="2312", force=True, cfg=None)
    assert count == 1
    assert not extra.exists()


def test_toolref_list_reads_manifest_meta(tmp_path, monkeypatch):
    from scholaraio import toolref as mod

    monkeypatch.setattr(mod, "_DEFAULT_TOOLREF_DIR", tmp_path)
    vdir = tmp_path / "openfoam" / "2312"
    vdir.mkdir(parents=True)
    (vdir / "meta.json").write_text(
        json.dumps(
            {
                "tool": "openfoam",
                "version": "2312",
                "source_type": "manifest",
                "expected_pages": 11,
                "failed_pages": 2,
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "openfoam" / "current").symlink_to(vdir, target_is_directory=True)

    entries = toolref_list("openfoam", cfg=None)
    assert len(entries) == 1
    assert entries[0]["source_type"] == "manifest"
    assert entries[0]["expected_pages"] == 11
    assert entries[0]["failed_pages"] == 2


def test_toolref_fetch_manifest_force_keeps_more_complete_cache(tmp_path, monkeypatch):
    from scholaraio import toolref as mod

    class FakeResponse:
        def __init__(self, text: str):
            self.text = text

        def raise_for_status(self):
            return None

    class FakeSession:
        def __init__(self):
            self.headers = {}

        def get(self, url, timeout=60):
            if "view" in url:
                raise mod.requests.RequestException("boom")
            return FakeResponse(f"<html><body><main><h1>{url}</h1></main></body></html>")

    monkeypatch.setattr(mod, "_DEFAULT_TOOLREF_DIR", tmp_path)
    monkeypatch.setattr(
        mod,
        "_build_manifest",
        lambda tool, version: [
            {
                "program": "samtools",
                "section": "alignment",
                "page_name": "samtools/sort",
                "title": "samtools sort",
                "url": "https://example.org/sort",
            },
            {
                "program": "samtools",
                "section": "alignment",
                "page_name": "samtools/view",
                "title": "samtools view",
                "url": "https://example.org/view",
            },
        ],
    )

    vdir = tmp_path / "bioinformatics" / "2026-03-curated"
    pages_dir = vdir / "pages"
    pages_dir.mkdir(parents=True)
    for idx, (name, page_name) in enumerate(
        [("samtools-sort", "samtools/sort"), ("samtools-view", "samtools/view")],
        start=1,
    ):
        (pages_dir / f"{idx:03d}-{name}.html").write_text("<html></html>", encoding="utf-8")
        (pages_dir / f"{idx:03d}-{name}.json").write_text(
            json.dumps({"page_name": page_name}),
            encoding="utf-8",
        )
    (vdir / "meta.json").write_text(
        json.dumps(
            {
                "tool": "bioinformatics",
                "version": "2026-03-curated",
                "source_type": "manifest",
                "fetched_pages": 2,
                "expected_pages": 2,
                "failed_pages": 0,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(mod.requests, "Session", FakeSession)
    monkeypatch.setattr(mod, "_index_tool", lambda tool, version, cfg=None: mod._manifest_page_count(vdir))
    monkeypatch.setattr(mod, "_set_current", lambda tool, version, cfg=None: None)

    count = toolref_fetch("bioinformatics", version="2026-03-curated", force=True, cfg=None)
    assert count == 2
    assert (pages_dir / "002-samtools-view.html").exists()
    meta = json.loads((vdir / "meta.json").read_text(encoding="utf-8"))
    assert meta["fetched_pages"] == 2
    assert meta["failed_pages"] == 0
    assert meta["last_fetch_failed_page_names"] == ["samtools/view"]


def test_toolref_show_falls_back_to_program_manual_page(tmp_path, monkeypatch):
    from scholaraio import toolref as mod
    import sqlite3

    monkeypatch.setattr(mod, "_DEFAULT_TOOLREF_DIR", tmp_path)
    tdir = tmp_path / "bioinformatics"
    vdir = tdir / "2026-03-curated"
    vdir.mkdir(parents=True)
    (tdir / "current").symlink_to(vdir, target_is_directory=True)

    db = tdir / "toolref.db"
    conn = sqlite3.connect(db)
    conn.executescript(mod._PAGES_SCHEMA)
    conn.execute(
        """INSERT INTO toolref_pages
           (tool, version, program, section, page_name, title, synopsis, content)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "bioinformatics",
            "2026-03-curated",
            "minimap2",
            "alignment",
            "minimap2/manual",
            "minimap2 manual",
            "manual page",
            "manual content",
        ),
    )
    conn.execute(
        """INSERT INTO toolref_pages
           (tool, version, program, section, page_name, title, synopsis, content)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "bioinformatics",
            "2026-03-curated",
            "minimap2",
            "alignment",
            "minimap2/options",
            "minimap2 options",
            "options page",
            "options content",
        ),
    )
    conn.commit()
    conn.close()

    rows = toolref_show("bioinformatics", "minimap2", cfg=None)
    assert rows
    assert rows[0]["page_name"] == "minimap2/manual"
