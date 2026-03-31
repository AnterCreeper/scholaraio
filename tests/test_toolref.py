from __future__ import annotations

import json

from scholaraio.toolref import (
    _build_bioinformatics_manifest,
    _build_openfoam_manifest,
    _clean_manifest_text,
    _expand_search_query,
    _has_local_docs,
    _normalize_search_query,
    _normalize_program_filter,
    _parse_lammps_rst,
    _pick_manifest_synopsis,
    _parse_manifest_html,
    toolref_fetch,
    toolref_list,
    toolref_search,
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


def test_expand_search_query_adds_openfoam_aliases():
    expanded = _expand_search_query("openfoam", "drag coefficient")
    assert "forces" in expanded
    assert "forcecoeffs" in expanded


def test_expand_search_query_adds_more_openfoam_aliases():
    expanded = _expand_search_query("openfoam", "y plus")
    assert "yplus" in expanded
    expanded = _expand_search_query("openfoam", "wall shear stress")
    assert "wallshearstress" in expanded
    expanded = _expand_search_query("openfoam", "solver residuals")
    assert "residuals" in expanded


def test_expand_search_query_adds_bioinformatics_aliases():
    expanded = _expand_search_query("bioinformatics", "phylogenetic tree")
    assert "iqtree" in expanded
    expanded = _expand_search_query("bioinformatics", "read mapping nanopore")
    assert "minimap2" in expanded
    expanded = _expand_search_query("bioinformatics", "protein structure folding")
    assert "esmfold" in expanded


def test_expand_search_query_adds_qe_aliases():
    expanded = _expand_search_query("qe", "ecut rho")
    assert "ecutrho" in expanded


def test_expand_search_query_adds_lammps_and_bio_aliases():
    lammps_expanded = _expand_search_query("lammps", "phase transition pressure")
    assert "fix_nphug" in lammps_expanded
    bio_expanded = _expand_search_query("bioinformatics", "spike mutation")
    assert "bcftools" in bio_expanded


def test_build_openfoam_manifest_uses_requested_version():
    manifest = _build_openfoam_manifest("2312")
    assert manifest
    assert all("page_name" in item for item in manifest)
    assert any("/2312/" in item["url"] for item in manifest if "doc.openfoam.com" in item["url"])


def test_build_openfoam_manifest_includes_specific_mesh_and_post_pages():
    manifest = _build_openfoam_manifest("2312")
    pages = {item["page_name"]: item for item in manifest}

    assert pages["openfoam/blockMesh"]["url"].endswith("/2312/tools/pre-processing/mesh/generation/blockMesh/blockmesh/")
    assert pages["openfoam/forceCoeffs"]["url"].endswith(
        "/2312/tools/post-processing/function-objects/forces/forceCoeffs/"
    )
    assert pages["openfoam/Q"]["url"].endswith("/2312/tools/post-processing/function-objects/field/Q/")


def test_build_openfoam_manifest_includes_validation_and_wall_pages():
    manifest = _build_openfoam_manifest("2312")
    pages = {item["page_name"]: item for item in manifest}

    assert pages["openfoam/yPlus"]["url"].endswith("/2312/tools/post-processing/function-objects/field/yPlus/")
    assert pages["openfoam/wallShearStress"]["url"].endswith(
        "/2312/tools/post-processing/function-objects/field/wallShearStress/"
    )
    assert pages["openfoam/residuals"]["url"].endswith("/2312/tools/processing/numerics/solvers/residuals/")


def test_build_bioinformatics_manifest_contains_multiple_subtools():
    manifest = _build_bioinformatics_manifest("2026-03-curated")
    programs = {item["program"] for item in manifest}
    assert {"blastn", "minimap2", "samtools", "bcftools", "mafft", "iqtree", "esmfold"} <= programs


def test_build_bioinformatics_manifest_includes_high_value_entry_points():
    manifest = _build_bioinformatics_manifest("2026-03-curated")
    pages = {item["page_name"]: item for item in manifest}

    assert pages["minimap2/manual"]["url"] == "https://lh3.github.io/minimap2/minimap2.html"
    assert "fallback_urls" in pages["minimap2/manual"]
    assert "github.com/lh3/minimap2" in pages["minimap2/manual"]["fallback_urls"][0]
    assert pages["bcftools/call"]["url"].endswith("/bcftools.html#call")
    assert pages["bcftools/mpileup"]["url"].endswith("/bcftools.html#mpileup")
    assert pages["iqtree/ultrafast-bootstrap"]["url"].endswith("/Command-Reference#ultrafast-bootstrap")


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


def test_toolref_fetch_manifest_force_preserves_failed_pages_from_existing_cache(tmp_path, monkeypatch):
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
            if "simpleFoam" in url:
                raise mod.requests.RequestException("timeout")
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
            },
            {
                "program": "yPlus",
                "section": "post-processing",
                "page_name": "openfoam/yPlus",
                "title": "yPlus",
                "url": "https://example.org/yPlus",
            },
        ],
    )

    vdir = tmp_path / "openfoam" / "2312"
    pages_dir = vdir / "pages"
    pages_dir.mkdir(parents=True)
    (pages_dir / "001-openfoam-simpleFoam.html").write_text("<html><body>cached simpleFoam</body></html>", encoding="utf-8")
    (pages_dir / "001-openfoam-simpleFoam.json").write_text(
        json.dumps(
            {
                "program": "simpleFoam",
                "section": "solver",
                "page_name": "openfoam/simpleFoam",
                "title": "simpleFoam",
                "url": "https://example.org/simpleFoam",
            }
        ),
        encoding="utf-8",
    )
    (vdir / "meta.json").write_text(
        json.dumps(
            {
                "tool": "openfoam",
                "version": "2312",
                "source_type": "manifest",
                "fetched_pages": 1,
                "expected_pages": 1,
                "failed_pages": 0,
            }
        ),
        encoding="utf-8",
    )

    count = toolref_fetch("openfoam", version="2312", force=True, cfg=None)
    assert count == 2
    assert (pages_dir / "001-openfoam-simpleFoam.html").exists()
    assert (pages_dir / "002-openfoam-yPlus.html").exists()
    meta = json.loads((vdir / "meta.json").read_text(encoding="utf-8"))
    assert meta["fetched_pages"] == 2
    assert meta["failed_pages"] == 0
    assert meta["last_fetch_failed_page_names"] == ["openfoam/simpleFoam"]


def test_toolref_fetch_manifest_uses_fallback_urls(tmp_path, monkeypatch):
    from scholaraio import toolref as mod

    class FakeResponse:
        def __init__(self, text: str):
            self.text = text

        def raise_for_status(self):
            return None

    class FakeSession:
        def __init__(self):
            self.headers = {}
            self.calls = []

        def get(self, url, timeout=60):
            self.calls.append(url)
            if "primary" in url:
                raise mod.requests.RequestException("timeout")
            return FakeResponse("<html><body><main><h1>minimap2 manual</h1></main></body></html>")

    monkeypatch.setattr(mod, "_DEFAULT_TOOLREF_DIR", tmp_path)
    session = FakeSession()
    monkeypatch.setattr(mod.requests, "Session", lambda: session)
    monkeypatch.setattr(
        mod,
        "_build_manifest",
        lambda tool, version: [
            {
                "program": "minimap2",
                "section": "alignment",
                "page_name": "minimap2/manual",
                "title": "minimap2 manual",
                "url": "https://example.org/primary",
                "fallback_urls": ["https://example.org/fallback"],
            }
        ],
    )

    count = toolref_fetch("bioinformatics", version="2026-03-curated", force=True, cfg=None)

    assert count == 1
    assert session.calls == ["https://example.org/primary", "https://example.org/fallback"]


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


def test_parse_lammps_rst_surfaces_aliases_for_search(tmp_path):
    rst = tmp_path / "fix_nh.rst"
    rst.write_text(
        """
fix nvt command
================

.. index:: fix nvt
.. index:: fix npt
.. index:: fix nph

Syntax
""""""""

.. code-block:: LAMMPS

   fix ID group-ID style_name keyword value ...

Description
"""""""""""""

Thermostat and barostat.
""",
        encoding="utf-8",
    )

    parsed = _parse_lammps_rst(rst)[0]

    assert "Aliases: fix nvt, fix npt, fix nph" in parsed["synopsis"]
    assert "fix npt" in parsed["content"]


def test_toolref_show_qe_prefers_exact_program_title_match(tmp_path, monkeypatch):
    from scholaraio import toolref as mod
    import sqlite3

    monkeypatch.setattr(mod, "_DEFAULT_TOOLREF_DIR", tmp_path)
    tdir = tmp_path / "qe"
    vdir = tdir / "7.5"
    vdir.mkdir(parents=True)
    (tdir / "current").symlink_to(vdir, target_is_directory=True)

    db = tdir / "toolref.db"
    conn = sqlite3.connect(db)
    conn.executescript(mod._PAGES_SCHEMA)
    conn.execute(
        """INSERT INTO toolref_pages
           (tool, version, program, section, page_name, title, synopsis, content)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        ("qe", "7.5", "pw.x", "ELECTRONS", "pw.x/ELECTRONS/conv_thr", "conv_thr", "", "exact"),
    )
    conn.execute(
        """INSERT INTO toolref_pages
           (tool, version, program, section, page_name, title, synopsis, content)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        ("qe", "7.5", "pw.x", "CONTROL", "pw.x/CONTROL/forc_conv_thr", "forc_conv_thr", "", "other"),
    )
    conn.commit()
    conn.close()

    rows = toolref_show("qe", "pw", "conv_thr", cfg=None)
    assert rows
    assert rows[0]["page_name"] == "pw.x/ELECTRONS/conv_thr"


def test_toolref_show_lammps_resolves_alias_from_query(tmp_path, monkeypatch):
    from scholaraio import toolref as mod
    import sqlite3

    monkeypatch.setattr(mod, "_DEFAULT_TOOLREF_DIR", tmp_path)
    tdir = tmp_path / "lammps"
    vdir = tdir / "stable"
    vdir.mkdir(parents=True)
    (tdir / "current").symlink_to(vdir, target_is_directory=True)

    db = tdir / "toolref.db"
    conn = sqlite3.connect(db)
    conn.executescript(mod._PAGES_SCHEMA)
    conn.executescript(mod._FTS_SCHEMA)
    conn.executescript(mod._FTS_TRIGGERS)
    conn.execute(
        """INSERT INTO toolref_pages
           (tool, version, program, section, page_name, title, synopsis, content)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "lammps",
            "stable",
            "lammps",
            "fix",
            "lammps/fix_nh",
            "fix nvt command",
            "fix ID group-ID style_name keyword value ... | Aliases: fix nvt, fix npt, fix nph",
            "Alias keys: |fix nvt| |fix npt| |fix nph|\nAliases: fix nvt, fix npt, fix nph",
        ),
    )
    conn.execute(
        """INSERT INTO toolref_pages
           (tool, version, program, section, page_name, title, synopsis, content)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "lammps",
            "stable",
            "lammps",
            "fix",
            "lammps/fix_npt_asphere",
            "fix npt/asphere command",
            "fix ID group-ID npt/asphere keyword value ... | Aliases: fix npt/asphere",
            "Alias keys: |fix npt/asphere|",
        ),
    )
    conn.commit()
    conn.close()

    rows = toolref_show("lammps", "fix_npt", cfg=None)
    assert rows
    assert rows[0]["page_name"] == "lammps/fix_nh"


def test_toolref_search_lammps_boosts_exact_alias_match(tmp_path, monkeypatch):
    from scholaraio import toolref as mod
    import sqlite3

    monkeypatch.setattr(mod, "_DEFAULT_TOOLREF_DIR", tmp_path)
    tdir = tmp_path / "lammps"
    vdir = tdir / "stable"
    vdir.mkdir(parents=True)
    (tdir / "current").symlink_to(vdir, target_is_directory=True)

    db = tdir / "toolref.db"
    conn = sqlite3.connect(db)
    conn.executescript(mod._PAGES_SCHEMA)
    conn.executescript(mod._FTS_SCHEMA)
    conn.executescript(mod._FTS_TRIGGERS)
    conn.execute(
        """INSERT INTO toolref_pages
           (tool, version, program, section, page_name, title, synopsis, content)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "lammps",
            "stable",
            "lammps",
            "howto",
            "lammps/Howto_barostat",
            "Howto barostat",
            "barostat notes",
            "NPT barostat overview",
        ),
    )
    conn.execute(
        """INSERT INTO toolref_pages
           (tool, version, program, section, page_name, title, synopsis, content)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "lammps",
            "stable",
            "lammps",
            "fix",
            "lammps/fix_nh",
            "fix nvt command",
            "fix ID group-ID style_name keyword value ... | Aliases: fix nvt, fix npt, fix nph",
            "Aliases: fix nvt, fix npt, fix nph",
        ),
    )
    conn.commit()
    conn.close()

    rows = toolref_search("lammps", "fix npt", cfg=None)
    assert rows
    assert rows[0]["page_name"] == "lammps/fix_nh"


def test_parse_gromacs_mdp_block_keeps_option_descriptions(tmp_path):
    rst = tmp_path / "mdp-options.rst"
    rst.write_text(
        """
.. mdp:: pcoupl

   .. mdp-value:: no

      No pressure coupling.

   .. mdp-value:: Parrinello-Rahman

      Extended-ensemble pressure coupling.

.. mdp:: constraints

   Controls which bonds become rigid.

   .. mdp-value:: h-bonds

      Convert the bonds with H-atoms to constraints.
""",
        encoding="utf-8",
    )

    records = __import__("scholaraio.toolref", fromlist=["_parse_gromacs_rst"])._parse_gromacs_rst(rst)
    pcoupl = next(r for r in records if r["title"] == "pcoupl")
    constraints = next(r for r in records if r["title"] == "constraints")

    assert "Parrinello-Rahman" in pcoupl["synopsis"]
    assert "Extended-ensemble pressure coupling" in pcoupl["content"]
    assert "h-bonds" in constraints["synopsis"]
    assert "Convert the bonds with H-atoms to constraints." in constraints["content"]


def test_expand_search_query_adds_gromacs_aliases():
    expanded = _expand_search_query("gromacs", "Parrinello Rahman")
    assert "pcoupl" in expanded
    expanded = _expand_search_query("gromacs", "v-rescale thermostat")
    assert "tcoupl" in expanded
    expanded = _expand_search_query("gromacs", "constraints h-bonds")
    assert "constraints" in expanded


def test_toolref_search_gromacs_boosts_parameter_hits(tmp_path, monkeypatch):
    from scholaraio import toolref as mod
    import sqlite3

    monkeypatch.setattr(mod, "_DEFAULT_TOOLREF_DIR", tmp_path)
    tdir = tmp_path / "gromacs"
    vdir = tdir / "2024"
    vdir.mkdir(parents=True)
    (tdir / "current").symlink_to(vdir, target_is_directory=True)

    db = tdir / "toolref.db"
    conn = sqlite3.connect(db)
    conn.executescript(mod._PAGES_SCHEMA)
    conn.executescript(mod._FTS_SCHEMA)
    conn.executescript(mod._FTS_TRIGGERS)
    conn.execute(
        """INSERT INTO toolref_pages
           (tool, version, program, section, page_name, title, synopsis, content)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "gromacs",
            "2024",
            "gromacs",
            "mdp",
            "gromacs/mdp/pcoupl",
            "pcoupl",
            "MDP parameter | Options: no, Parrinello-Rahman",
            "pcoupl Parrinello-Rahman pressure coupling tau-p ref-p",
        ),
    )
    conn.execute(
        """INSERT INTO toolref_pages
           (tool, version, program, section, page_name, title, synopsis, content)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "gromacs",
            "2024",
            "gromacs",
            "general",
            "gromacs/general/physical_validation",
            "Physical validation",
            "General notes",
            "Parrinello Rahman mentioned in passing",
        ),
    )
    conn.commit()
    conn.close()

    rows = toolref_search("gromacs", "Parrinello Rahman", cfg=None)
    assert rows
    assert rows[0]["page_name"] == "gromacs/mdp/pcoupl"


def test_toolref_search_gromacs_v_rescale_maps_to_tcoupl(tmp_path, monkeypatch):
    from scholaraio import toolref as mod
    import sqlite3

    monkeypatch.setattr(mod, "_DEFAULT_TOOLREF_DIR", tmp_path)
    tdir = tmp_path / "gromacs"
    vdir = tdir / "2024"
    vdir.mkdir(parents=True)
    (tdir / "current").symlink_to(vdir, target_is_directory=True)

    db = tdir / "toolref.db"
    conn = sqlite3.connect(db)
    conn.executescript(mod._PAGES_SCHEMA)
    conn.executescript(mod._FTS_SCHEMA)
    conn.executescript(mod._FTS_TRIGGERS)
    conn.execute(
        """INSERT INTO toolref_pages
           (tool, version, program, section, page_name, title, synopsis, content)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "gromacs",
            "2024",
            "gromacs",
            "mdp",
            "gromacs/mdp/tcoupl",
            "tcoupl",
            "MDP parameter | Options: no, nose-hoover, v-rescale",
            "tcoupl v rescale thermostat temperature coupling tau t ref t",
        ),
    )
    conn.execute(
        """INSERT INTO toolref_pages
           (tool, version, program, section, page_name, title, synopsis, content)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "gromacs",
            "2024",
            "gromacs",
            "general",
            "gromacs/general/2020.4",
            "2020.4",
            "release notes",
            "v rescale mentioned in release notes",
        ),
    )
    conn.commit()
    conn.close()

    rows = toolref_search("gromacs", "v-rescale thermostat", cfg=None)
    assert rows
    assert rows[0]["page_name"] == "gromacs/mdp/tcoupl"


def test_toolref_search_openfoam_boosts_yplus_page(tmp_path, monkeypatch):
    from scholaraio import toolref as mod
    import sqlite3

    monkeypatch.setattr(mod, "_DEFAULT_TOOLREF_DIR", tmp_path)
    tdir = tmp_path / "openfoam"
    vdir = tdir / "2312"
    vdir.mkdir(parents=True)
    (tdir / "current").symlink_to(vdir, target_is_directory=True)

    db = tdir / "toolref.db"
    conn = sqlite3.connect(db)
    conn.executescript(mod._PAGES_SCHEMA)
    conn.executescript(mod._FTS_SCHEMA)
    conn.executescript(mod._FTS_TRIGGERS)
    conn.execute(
        """INSERT INTO toolref_pages
           (tool, version, program, section, page_name, title, synopsis, content)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "openfoam",
            "2312",
            "yPlus",
            "post-processing",
            "openfoam/yPlus",
            "yPlus",
            "wall distance non-dimensionalisation",
            "yPlus function object wall y plus boundary layer",
        ),
    )
    conn.execute(
        """INSERT INTO toolref_pages
           (tool, version, program, section, page_name, title, synopsis, content)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "openfoam",
            "2312",
            "functionObjects",
            "post-processing",
            "openfoam/functionObjects",
            "function objects",
            "overview",
            "post processing overview mentioning yPlus",
        ),
    )
    conn.commit()
    conn.close()

    rows = toolref_search("openfoam", "y plus", cfg=None)
    assert rows
    assert rows[0]["page_name"] == "openfoam/yPlus"
