from __future__ import annotations

from pathlib import Path

import requests

from scholaraio.ingest.mineru import (
    ConvertOptions,
    ConvertResult,
    _convert_long_pdf_cloud,
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
        cloud_url="https://mineru.example",
    )

    assert result.success is True
    assert captured["cloud_model_version"] == "MinerU-HTML"


def test_resolve_cloud_model_version_falls_back_to_backend_when_unset():
    opts = ConvertOptions(backend="vlm-auto-engine", cloud_model_version="")
    assert _resolve_cloud_model_version(opts) == "vlm"


def test_resolve_cloud_model_version_uses_backend_mapping_by_default():
    opts = ConvertOptions(backend="vlm-auto-engine")
    assert _resolve_cloud_model_version(opts) == "vlm"


def test_convert_pdf_cloud_sends_official_cloud_payload_shape(tmp_path, monkeypatch):
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    captured: dict[str, object] = {}

    class DummyResponse:
        def __init__(self, payload: dict, status_code: int = 200):
            self._payload = payload
            self.status_code = status_code
            self.text = ""

        def json(self):
            return self._payload

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        return DummyResponse({"code": 0, "data": {"batch_id": "b1", "file_urls": ["https://upload.example/file.pdf"]}})

    def fake_put(url, data=None, timeout=None):
        return DummyResponse({}, status_code=200)

    def fake_get(url, headers=None, timeout=None):
        return DummyResponse(
            {
                "code": 0,
                "data": {
                    "extract_result": [
                        {
                            "data_id": "paper",
                            "file_name": "paper.pdf",
                            "state": "done",
                            "full_md_url": "https://download.example/full.md",
                        }
                    ]
                },
            }
        )

    def fake_download(item, out_dir, download_retries=3):
        return "# ok"

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(requests, "put", fake_put)
    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr("scholaraio.ingest.mineru._download_cloud_result", fake_download)
    monkeypatch.setattr("scholaraio.ingest.mineru.time.sleep", lambda _x: None)

    opts = ConvertOptions(
        output_dir=tmp_path / "out",
        cloud_model_version="vlm",
        lang="en",
        parse_method="ocr",
        formula_enable=False,
        table_enable=True,
    )

    result = convert_pdf_cloud(
        pdf_path,
        opts,
        api_key="test-key",
        cloud_url="https://mineru.example/api/v4",
    )

    assert result.success is True
    payload = captured["json"]
    assert payload == {
        "files": [{"name": "paper.pdf", "data_id": "paper", "is_ocr": True}],
        "model_version": "vlm",
        "enable_formula": False,
        "enable_table": True,
        "language": "en",
    }


def test_convert_pdfs_cloud_batch_sends_is_ocr_per_file(tmp_path, monkeypatch):
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    captured: dict[str, object] = {}

    class DummyResponse:
        def __init__(self, payload: dict, status_code: int = 200):
            self._payload = payload
            self.status_code = status_code
            self.text = ""

        def json(self):
            return self._payload

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        return DummyResponse({"code": 0, "data": {"batch_id": "b1", "file_urls": ["https://upload.example/file.pdf"]}})

    def fake_put(url, data=None, timeout=None):
        return DummyResponse({}, status_code=200)

    def fake_get(url, headers=None, timeout=None):
        return DummyResponse(
            {
                "code": 0,
                "data": {
                    "extract_result": [
                        {
                            "data_id": "paper",
                            "file_name": "paper.pdf",
                            "state": "done",
                            "full_md_url": "https://download.example/full.md",
                        }
                    ]
                },
            }
        )

    def fake_download(item, out_dir, download_retries=3):
        return "# ok"

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(requests, "put", fake_put)
    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr("scholaraio.ingest.mineru._download_cloud_result", fake_download)
    monkeypatch.setattr("scholaraio.ingest.mineru.time.sleep", lambda _x: None)

    opts = ConvertOptions(
        output_dir=tmp_path / "out",
        cloud_model_version="pipeline",
        lang="ch",
        parse_method="ocr",
    )

    results = convert_pdfs_cloud_batch(
        [pdf_path],
        opts,
        api_key="test-key",
        cloud_url="https://mineru.example/api/v4",
    )

    assert len(results) == 1
    assert results[0].success is True
    payload = captured["json"]
    assert payload == {
        "files": [{"name": "paper.pdf", "data_id": "paper", "is_ocr": True}],
        "model_version": "pipeline",
        "enable_formula": True,
        "enable_table": True,
        "language": "ch",
    }


def test_convert_pdfs_cloud_batch_retries_upload_timeout_then_succeeds(tmp_path, monkeypatch):
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    put_calls = {"count": 0}

    class DummyResponse:
        def __init__(self, payload: dict, status_code: int = 200):
            self._payload = payload
            self.status_code = status_code
            self.text = ""

        def json(self):
            return self._payload

    def fake_post(url, headers=None, json=None, timeout=None):
        return DummyResponse({"code": 0, "data": {"batch_id": "b1", "file_urls": ["https://upload.example/file.pdf"]}})

    def fake_put(url, data=None, timeout=None):
        put_calls["count"] += 1
        if put_calls["count"] < 3:
            raise requests.ConnectTimeout("connect timeout")
        return DummyResponse({}, status_code=200)

    def fake_get(url, headers=None, timeout=None):
        return DummyResponse(
            {
                "code": 0,
                "data": {"extract_result": [{"data_id": "paper", "state": "done", "md_url": "https://download"}]},
            }
        )

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(requests, "put", fake_put)
    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(
        "scholaraio.ingest.mineru._download_cloud_result", lambda item, out_dir, download_retries=3: "# ok"
    )
    monkeypatch.setattr("scholaraio.ingest.mineru.time.sleep", lambda _x: None)

    results = convert_pdfs_cloud_batch(
        [pdf_path],
        ConvertOptions(output_dir=tmp_path / "out", upload_retries=3),
        api_key="test-key",
        cloud_url="https://mineru.example/api/v4",
    )

    assert results[0].success is True
    assert put_calls["count"] == 3


def test_download_cloud_result_retries_md_url(tmp_path, monkeypatch):
    calls = {"count": 0}

    class DummyResponse:
        def __init__(self, text: str = "", status_code: int = 200):
            self.text = text
            self.status_code = status_code
            self.content = b""

    def fake_get(url, timeout=None, proxies=None):
        calls["count"] += 1
        if calls["count"] < 3:
            raise requests.ConnectTimeout("connect timeout")
        return DummyResponse("# recovered", status_code=200)

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr("scholaraio.ingest.mineru.time.sleep", lambda _x: None)

    from scholaraio.ingest.mineru import _download_cloud_result

    md = _download_cloud_result({"md_url": "https://download.example/full.md"}, tmp_path, download_retries=3)

    assert md == "# recovered"
    assert calls["count"] == 3


def test_convert_pdfs_cloud_batch_uses_configured_upload_workers(tmp_path, monkeypatch):
    pdf_paths = []
    for idx in range(2):
        pdf_path = tmp_path / f"paper-{idx}.pdf"
        pdf_path.write_bytes(b"%PDF-1.4")
        pdf_paths.append(pdf_path)

    captured = {"max_workers": None}

    class DummyResponse:
        def __init__(self, payload: dict, status_code: int = 200):
            self._payload = payload
            self.status_code = status_code
            self.text = ""

        def json(self):
            return self._payload

    class DummyPool:
        def __init__(self, max_workers):
            captured["max_workers"] = max_workers

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def map(self, func, iterable):
            return [func(item) for item in iterable]

    def fake_post(url, headers=None, json=None, timeout=None):
        return DummyResponse(
            {
                "code": 0,
                "data": {
                    "batch_id": "b1",
                    "file_urls": ["https://upload.example/file-0.pdf", "https://upload.example/file-1.pdf"],
                },
            }
        )

    def fake_put(url, data=None, timeout=None):
        return DummyResponse({}, status_code=200)

    def fake_get(url, headers=None, timeout=None):
        return DummyResponse(
            {
                "code": 0,
                "data": {
                    "extract_result": [
                        {"data_id": "paper-0", "state": "done", "md_url": "https://download/0"},
                        {"data_id": "paper-1", "state": "done", "md_url": "https://download/1"},
                    ]
                },
            }
        )

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(requests, "put", fake_put)
    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(
        "scholaraio.ingest.mineru._download_cloud_result", lambda item, out_dir, download_retries=3: "# ok"
    )
    monkeypatch.setattr("scholaraio.ingest.mineru.time.sleep", lambda _x: None)
    monkeypatch.setattr("concurrent.futures.ThreadPoolExecutor", DummyPool)

    results = convert_pdfs_cloud_batch(
        pdf_paths,
        ConvertOptions(output_dir=tmp_path / "out", upload_workers=3),
        api_key="test-key",
        cloud_url="https://mineru.example/api/v4",
    )

    assert len(results) == 2
    assert all(result.success for result in results)
    assert captured["max_workers"] == 3


def test_convert_pdf_cloud_omits_pdf_only_flags_for_html_model(tmp_path, monkeypatch):
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    captured: dict[str, object] = {}

    class DummyResponse:
        def __init__(self, payload: dict, status_code: int = 200):
            self._payload = payload
            self.status_code = status_code
            self.text = ""

        def json(self):
            return self._payload

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["json"] = json
        return DummyResponse({"code": 0, "data": {"batch_id": "b1", "file_urls": ["https://upload.example/file.pdf"]}})

    def fake_put(url, data=None, timeout=None):
        return DummyResponse({}, status_code=200)

    def fake_get(url, headers=None, timeout=None):
        return DummyResponse(
            {
                "code": 0,
                "data": {
                    "extract_result": [
                        {
                            "data_id": "paper",
                            "file_name": "paper.pdf",
                            "state": "done",
                            "full_md_url": "https://download.example/full.md",
                        }
                    ]
                },
            }
        )

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(requests, "put", fake_put)
    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(
        "scholaraio.ingest.mineru._download_cloud_result",
        lambda item, out_dir, download_retries=3: "# ok",
    )
    monkeypatch.setattr("scholaraio.ingest.mineru.time.sleep", lambda _x: None)

    opts = ConvertOptions(
        output_dir=tmp_path / "out",
        cloud_model_version="MinerU-HTML",
        lang="en",
        parse_method="ocr",
        formula_enable=False,
        table_enable=False,
    )

    result = convert_pdf_cloud(
        pdf_path,
        opts,
        api_key="test-key",
        cloud_url="https://mineru.example/api/v4",
    )

    assert result.success is True
    assert captured["json"] == {
        "files": [{"name": "paper.pdf", "data_id": "paper"}],
        "model_version": "MinerU-HTML",
    }
