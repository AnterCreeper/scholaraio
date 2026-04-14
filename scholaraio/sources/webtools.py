"""HTTP connector helpers for external web search/extraction services."""

from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_DEFAULT_WEBSEARCH_URL = "http://127.0.0.1:8765"
_DEFAULT_WEBEXTRACT_URL = "http://127.0.0.1:8766"


def _resolve_base_url(explicit: str | None, env_name: str, default: str) -> str:
    return (explicit or os.environ.get(env_name) or default).rstrip("/")


def _resolve_api_key(env_name: str) -> str:
    return os.environ.get(env_name, "").strip()


def _headers(api_key: str) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _load_json_response(req: Request, *, timeout: int, error_prefix: str):
    try:
        with urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            raise RuntimeError(f"{error_prefix} (HTTP {exc.code}): {body}") from exc
        raise RuntimeError(f"{error_prefix}: {data.get('error', body)}") from exc
    except URLError as exc:
        raise RuntimeError(f"无法连接到服务: {exc.reason}") from exc

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"解析响应失败: {exc}") from exc


def check_websearch_health(base_url: str | None = None) -> dict:
    """Check whether the external web search service is healthy."""
    base = _resolve_base_url(base_url, "WEBSEARCH_URL", _DEFAULT_WEBSEARCH_URL)
    req = Request(f"{base}/health", method="GET")
    return _load_json_response(req, timeout=5, error_prefix="搜索服务健康检查失败")


def check_webextract_health(base_url: str | None = None) -> dict:
    """Check whether the external web extraction service is healthy."""
    base = _resolve_base_url(base_url, "WEBEXTRACT_URL", _DEFAULT_WEBEXTRACT_URL)
    req = Request(f"{base}/health", method="GET")
    return _load_json_response(req, timeout=5, error_prefix="提取服务健康检查失败")


def websearch(query: str, count: int = 10, base_url: str | None = None) -> list[dict]:
    """Run a web search request against the configured external service."""
    base = _resolve_base_url(base_url, "WEBSEARCH_URL", _DEFAULT_WEBSEARCH_URL)
    api_key = _resolve_api_key("WEBSEARCH_API_KEY")
    payload = json.dumps({"query": query, "count": count}).encode("utf-8")
    req = Request(f"{base}/search", data=payload, headers=_headers(api_key), method="POST")
    return _load_json_response(req, timeout=30, error_prefix="搜索失败")


def webextract(url: str, pdf: bool | None = None, base_url: str | None = None) -> dict:
    """Extract rendered page content from a URL via the external extractor service."""
    base = _resolve_base_url(base_url, "WEBEXTRACT_URL", _DEFAULT_WEBEXTRACT_URL)
    api_key = _resolve_api_key("WEBEXTRACT_API_KEY")
    body: dict[str, object] = {"url": url}
    if pdf is not None:
        body["pdf"] = pdf
    req = Request(
        f"{base}/extract",
        data=json.dumps(body).encode("utf-8"),
        headers=_headers(api_key),
        method="POST",
    )
    return _load_json_response(req, timeout=60, error_prefix="提取失败")


def webextract_batch(urls: list[str], base_url: str | None = None) -> list[dict]:
    """Extract multiple URLs through the Open WebUI-compatible batch endpoint."""
    base = _resolve_base_url(base_url, "WEBEXTRACT_URL", _DEFAULT_WEBEXTRACT_URL)
    api_key = _resolve_api_key("WEBEXTRACT_API_KEY")
    req = Request(
        base,
        data=json.dumps({"urls": urls}).encode("utf-8"),
        headers=_headers(api_key),
        method="POST",
    )
    return _load_json_response(req, timeout=120, error_prefix="批量提取失败")
