from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from scholaraio.ingest.mineru import (
    ConvertOptions,
    ConvertResult,
    _convert_long_pdf_cloud,
    _plan_cloud_chunking,
    _resolve_cloud_model_version,
    convert_pdf_cloud,
    convert_pdfs_cloud_batch,
)


def test_convert_long_pdf_cloud_preserves_cloud_model_version(tmp_path, monkeypatch):
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    chunk_pdf = tmp_path / "chunk-1.pdf"
    chunk_pdf.write_bytes(b"%PDF-1.4")

    captured: dict[str, str] = {}

    monkeypatch.setattr(
        "scholaraio.ingest.mineru._split_pdf",
        lambda _pdf_path, chunk_size, output_dir: [chunk_pdf],
    )

    def fake_convert_pdfs_cloud_batch(
        pdf_paths: list[Path],
        opts: ConvertOptions,
        *,
        api_key: str,
        cloud_url: str,
        batch_size: int = 20,
    ) -> list[ConvertResult]:
        captured["cloud_model_version"] = opts.cloud_model_version
        return [ConvertResult(pdf_path=pdf_paths[0], md_path=output_dir / "chunk-1.md", success=True)]

    output_dir = tmp_path / "out"
    output_dir.mkdir()

    def fake_merge_chunk_results(chunk_results, original_pdf_path, out_dir):
        assert chunk_results[0].success is True
        assert original_pdf_path == pdf_path
        return ConvertResult(pdf_path=original_pdf_path, md_path=out_dir / "paper.md", success=True)

    monkeypatch.setattr("scholaraio.ingest.mineru.convert_pdfs_cloud_batch", fake_convert_pdfs_cloud_batch)
    monkeypatch.setattr("scholaraio.ingest.mineru._merge_chunk_results", fake_merge_chunk_results)

    opts = ConvertOptions(
        output_dir=output_dir,
        backend="pipeline",
        cloud_model_version="MinerU-HTML",
        lang="en",
    )

    result = _convert_long_pdf_cloud(
        pdf_path,
        opts,
        api_key="test-key",
        cloud_url="https://mineru.example/api",
    )

    assert result.success is True
    assert captured["cloud_model_version"] == "MinerU-HTML"


def test_resolve_cloud_model_version_falls_back_to_backend_when_unset():
    opts = ConvertOptions(backend="vlm-auto-engine", cloud_model_version="")
    assert _resolve_cloud_model_version(opts) == "vlm"


def test_resolve_cloud_model_version_uses_backend_mapping_by_default():
    opts = ConvertOptions(backend="vlm-auto-engine")
    assert _resolve_cloud_model_version(opts) == "vlm"


def test_convert_pdf_cloud_invokes_mineru_open_api_extract_with_token_and_flags(tmp_path, monkeypatch):
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    output_dir = tmp_path / "out"

    captured: dict[str, object] = {}

    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/mineru-open-api" if name == "mineru-open-api" else None)

    def fake_run(cmd, *, capture_output, text, cwd, env, timeout, check):
        captured["cmd"] = cmd
        captured["cwd"] = cwd
        captured["env_token"] = env.get("MINERU_TOKEN")
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "paper.md").write_text("# ok\n", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="saved")

    monkeypatch.setattr(subprocess, "run", fake_run)

    opts = ConvertOptions(
        output_dir=output_dir,
        cloud_model_version="vlm",
        lang="en",
        parse_method="ocr",
        formula_enable=False,
        table_enable=True,
        poll_timeout=321,
    )

    result = convert_pdf_cloud(
        pdf_path,
        opts,
        api_key="test-key",
        cloud_url="https://mineru.net/api/v4",
    )

    assert result.success is True
    assert result.md_path == output_dir / "paper.md"
    assert result.md_path.read_text(encoding="utf-8") == "# ok\n"
    assert captured["env_token"] == "test-key"
    assert captured["cwd"] == str(tmp_path)
    assert captured["cmd"] == [
        "/usr/bin/mineru-open-api",
        "extract",
        str(pdf_path),
        "-o",
        str(output_dir),
        "--language",
        "en",
        "--model",
        "vlm",
        "--ocr",
        "--formula=false",
        "--table=true",
        "--timeout",
        "321",
    ]


def test_convert_pdf_cloud_omits_pdf_only_flags_for_html_model_and_passes_custom_base_url(tmp_path, monkeypatch):
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    output_dir = tmp_path / "out"

    captured: dict[str, object] = {}

    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/mineru-open-api" if name == "mineru-open-api" else None)

    def fake_run(cmd, *, capture_output, text, cwd, env, timeout, check):
        captured["cmd"] = cmd
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "paper.md").write_text("# html\n", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = convert_pdf_cloud(
        pdf_path,
        ConvertOptions(
            output_dir=output_dir,
            cloud_model_version="MinerU-HTML",
            lang="en",
            parse_method="ocr",
            formula_enable=False,
            table_enable=False,
        ),
        api_key="test-key",
        cloud_url="https://private-mineru.example/api",
    )

    assert result.success is True
    assert captured["cmd"] == [
        "/usr/bin/mineru-open-api",
        "extract",
        str(pdf_path),
        "-o",
        str(output_dir),
        "--language",
        "en",
        "--model",
        "html",
        "--timeout",
        "900",
        "--base-url",
        "https://private-mineru.example/api",
    ]


def test_convert_pdf_cloud_returns_actionable_error_when_cli_missing(tmp_path, monkeypatch):
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    monkeypatch.setattr(shutil, "which", lambda name: None)

    result = convert_pdf_cloud(
        pdf_path,
        ConvertOptions(output_dir=tmp_path / "out"),
        api_key="test-key",
        cloud_url="https://mineru.net/api/v4",
    )

    assert result.success is False
    assert "mineru-open-api" in (result.error or "")
    assert "pip install" in (result.error or "")


def test_convert_pdf_cloud_surfaces_cli_failure_details(tmp_path, monkeypatch):
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/mineru-open-api" if name == "mineru-open-api" else None)

    def fake_run(cmd, *, capture_output, text, cwd, env, timeout, check):
        return subprocess.CompletedProcess(cmd, 6, stdout="", stderr="timed out")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = convert_pdf_cloud(
        pdf_path,
        ConvertOptions(output_dir=tmp_path / "out"),
        api_key="test-key",
        cloud_url="https://mineru.net/api/v4",
    )

    assert result.success is False
    assert "exit code 6" in (result.error or "")
    assert "timed out" in (result.error or "")


def test_convert_pdfs_cloud_batch_splits_into_chunks(tmp_path, monkeypatch):
    pdf_paths: list[Path] = []
    for idx in range(3):
        pdf_path = tmp_path / f"paper-{idx}.pdf"
        pdf_path.write_bytes(b"%PDF-1.4")
        pdf_paths.append(pdf_path)

    calls: list[list[str]] = []

    def fake_convert_chunk_cloud(
        chunk: list[Path],
        opts: ConvertOptions,
        *,
        api_key: str,
        cloud_url: str,
    ) -> list[ConvertResult]:
        calls.append([path.name for path in chunk])
        return [ConvertResult(pdf_path=path, md_path=tmp_path / f"{path.stem}.md", success=True) for path in chunk]

    monkeypatch.setattr("scholaraio.ingest.mineru._convert_chunk_cloud", fake_convert_chunk_cloud)

    results = convert_pdfs_cloud_batch(
        pdf_paths,
        ConvertOptions(output_dir=tmp_path / "out"),
        api_key="test-key",
        cloud_url="https://mineru.example/api",
        batch_size=2,
    )

    assert calls == [["paper-0.pdf", "paper-1.pdf"], ["paper-2.pdf"]]
    assert len(results) == 3
    assert all(result.success for result in results)


def test_plan_cloud_chunking_uses_600_page_limit_when_only_page_count_exceeds(tmp_path, monkeypatch):
    pdf_path = tmp_path / "long.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr("scholaraio.ingest.mineru._get_pdf_page_count", lambda _path: 601)

    should_chunk, chunk_size, reason = _plan_cloud_chunking(pdf_path)

    assert should_chunk is True
    assert chunk_size == 600
    assert "601 pages" in reason


def test_plan_cloud_chunking_uses_size_limit_when_file_is_too_large(tmp_path, monkeypatch):
    pdf_path = tmp_path / "big.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr("scholaraio.ingest.mineru._get_pdf_page_count", lambda _path: 400)
    monkeypatch.setattr("scholaraio.ingest.mineru._get_pdf_size_bytes", lambda _path: 250 * 1024 * 1024)

    should_chunk, chunk_size, reason = _plan_cloud_chunking(pdf_path)

    assert should_chunk is True
    assert chunk_size == 320
    assert "250.0 MB" in reason


def test_plan_cloud_chunking_uses_safe_fallback_chunk_size_when_page_count_unknown(tmp_path, monkeypatch):
    pdf_path = tmp_path / "unknown.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr("scholaraio.ingest.mineru._get_pdf_page_count", lambda _path: -1)
    monkeypatch.setattr("scholaraio.ingest.mineru._get_pdf_size_bytes", lambda _path: 250 * 1024 * 1024)

    should_chunk, chunk_size, reason = _plan_cloud_chunking(pdf_path)

    assert should_chunk is True
    assert chunk_size == 100
    assert "250.0 MB" in reason
