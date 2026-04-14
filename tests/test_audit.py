"""Contract tests for the audit module.

Verifies: audit detects known data quality issues and returns structured reports.
Does NOT test: specific rule implementations or diagnostic messages.
"""

from __future__ import annotations

import json

from scholaraio.audit import Issue, audit_papers, list_scrub_suspects


class TestAuditDetection:
    """Audit contract: reports issues as structured Issue objects."""

    def test_clean_papers_produce_no_errors(self, tmp_papers):
        issues = audit_papers(tmp_papers)
        errors = [i for i in issues if i.severity == "error"]
        # Well-formed test data should have no errors
        assert len(errors) == 0

    def test_missing_doi_reported_for_non_thesis(self, tmp_papers):
        """Paper B is thesis (no DOI ok), but a journal-article without DOI should warn."""
        # Create a journal article without DOI
        d = tmp_papers / "NoDoi-2023-Test"
        d.mkdir()
        (d / "meta.json").write_text(
            json.dumps(
                {
                    "id": "cccc-3333",
                    "title": "Test Paper",
                    "authors": ["Author"],
                    "year": 2023,
                    "doi": "",
                    "paper_type": "journal-article",
                }
            ),
        )
        (d / "paper.md").write_text("# Test Paper\n\nSome content here for testing.")

        issues = audit_papers(tmp_papers)
        doi_issues = [i for i in issues if "doi" in i.rule.lower() or "doi" in i.message.lower()]
        assert len(doi_issues) >= 1

    def test_issue_has_required_fields(self, tmp_papers):
        # Create a problematic paper to guarantee at least one issue
        d = tmp_papers / "Bad-0000-Empty"
        d.mkdir()
        (d / "meta.json").write_text(json.dumps({"id": "bad"}))
        (d / "paper.md").write_text("")

        issues = audit_papers(tmp_papers)
        assert len(issues) > 0
        for issue in issues:
            assert isinstance(issue, Issue)
            assert issue.paper_id
            assert issue.severity in ("error", "warning", "info")
            assert issue.rule
            assert issue.message


class TestScrubSuspects:
    """Scrub suspect detection should flag obvious metadata problems conservatively."""

    def test_flags_placeholder_title(self, tmp_path):
        d = tmp_path / "Unknown-2024-Introduction"
        d.mkdir()
        (d / "meta.json").write_text(
            json.dumps(
                {
                    "id": "placeholder-title",
                    "title": "Introduction",
                    "authors": ["Alice Example"],
                    "first_author_lastname": "Example",
                    "year": 2024,
                }
            )
        )

        issues = list_scrub_suspects(tmp_path)

        assert any(i.paper_id == d.name and i.rule == "placeholder_title" for i in issues)

    def test_flags_garbled_title(self, tmp_path):
        d = tmp_path / "Example-2024-Trainium"
        d.mkdir()
        (d / "meta.json").write_text(
            json.dumps(
                {
                    "id": "garbled-title",
                    "title": "Trainium�/� Architecture",
                    "authors": ["Alice Example"],
                    "first_author_lastname": "Example",
                    "year": 2024,
                }
            )
        )

        issues = list_scrub_suspects(tmp_path)

        assert any(i.paper_id == d.name and i.rule == "garbled_title" for i in issues)

    def test_flags_unknown_author(self, tmp_path):
        d = tmp_path / "Unknown-2024-Network"
        d.mkdir()
        (d / "meta.json").write_text(
            json.dumps(
                {
                    "id": "unknown-author",
                    "title": "Network Scheduling for Training",
                    "authors": ["Unknown"],
                    "first_author_lastname": "Unknown",
                    "year": 2024,
                }
            )
        )

        issues = list_scrub_suspects(tmp_path)

        assert any(i.paper_id == d.name and i.rule == "suspicious_author" for i in issues)

    def test_flags_scalar_author_metadata_without_crashing(self, tmp_path):
        d = tmp_path / "Malformed-2024-Network"
        d.mkdir()
        (d / "meta.json").write_text(
            json.dumps(
                {
                    "id": "scalar-author",
                    "title": "Network Scheduling for Training",
                    "authors": 123,
                    "first_author_lastname": "",
                    "year": 2024,
                }
            )
        )

        issues = list_scrub_suspects(tmp_path)

        assert any(i.paper_id == d.name and i.rule == "suspicious_author" for i in issues)

    def test_flags_missing_year(self, tmp_path):
        d = tmp_path / "Contributor-XXXX-Distributed-Systems"
        d.mkdir()
        (d / "meta.json").write_text(
            json.dumps(
                {
                    "id": "missing-year",
                    "title": "Distributed Systems for Large-Scale Training",
                    "authors": ["Alice Example"],
                    "first_author_lastname": "Example",
                    "year": None,
                }
            )
        )

        issues = list_scrub_suspects(tmp_path)

        assert any(i.paper_id == d.name and i.rule == "suspicious_year" for i in issues)

    def test_skips_healthy_record(self, tmp_papers):
        issues = list_scrub_suspects(tmp_papers)

        assert all(i.paper_id != "Smith-2023-Turbulence" for i in issues)

    def test_includes_dirs_without_meta_json_when_paper_md_exists(self, tmp_path):
        d = tmp_path / "Broken-2024-OnlyMarkdown"
        d.mkdir()
        (d / "paper.md").write_text("# Broken metadata\n\nOnly markdown remains.", encoding="utf-8")

        issues = list_scrub_suspects(tmp_path)

        assert any(i.paper_id == d.name and i.rule == "invalid_metadata" for i in issues)
