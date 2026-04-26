"""Web search and extraction CLI command handlers."""

from __future__ import annotations

import argparse
import sys


def _ui(msg: str = "") -> None:
    try:
        from scholaraio.interfaces.cli import compat as cli_mod
    except ImportError:
        from scholaraio.core.log import ui as log_ui

        log_ui(msg)
        return
    cli_mod.ui(msg)


def cmd_websearch(args: argparse.Namespace, cfg) -> None:
    """实时网页搜索 (Bing via GUILessBingSearch)."""
    from scholaraio.providers import webtools

    query = " ".join(args.query)
    count = args.count

    try:
        results = webtools.search_and_display(query, count=count, cfg=cfg)
    except webtools.ServiceUnavailableError as e:
        _ui(f"错误: {e}")
        _ui("提示: 请确保 GUILessBingSearch 服务已启动")
        _ui("  安装: https://github.com/wszqkzqk/GUILessBingSearch")
        _ui("  启动: python guiless_bing_search.py")
        sys.exit(1)
    except webtools.WebSearchError as e:
        _ui(f"搜索失败: {e}")
        sys.exit(1)

    if not results:
        return


def _terminal_preview(text: str, *, max_chars: int) -> tuple[str, bool]:
    body = (text or "").strip()
    if not body:
        return "", False
    if max_chars < 1 or len(body) <= max_chars:
        return body, False
    return body[:max_chars].rstrip(), True


def cmd_webextract(args: argparse.Namespace, cfg) -> None:
    """网页内容提取 (qt-web-extractor)."""
    from scholaraio.providers import webtools

    url = args.url
    pdf = args.pdf
    full = getattr(args, "full", False)
    max_chars = max(1, int(getattr(args, "max_chars", 4000) or 4000))

    try:
        result = webtools.extract_web(url, pdf=pdf, cfg=cfg)
    except webtools.WebExtractServiceUnavailableError as e:
        _ui(f"错误: {e}")
        _ui("提示: 请确保 qt-web-extractor 服务已启动")
        sys.exit(1)
    except webtools.WebExtractError as e:
        _ui(f"提取失败: {e}")
        sys.exit(1)

    title = result.get("title", "")
    text = result.get("text") or ""
    text_body = text.strip()
    error = str(result.get("error") or "").strip()

    if error and not text_body:
        _ui(f"提取失败: {error}")
        sys.exit(1)

    if error:
        _ui(f"提取有警告: {error}")

    _ui(f"提取成功: {title or url}")
    if not text_body:
        return

    output_text, truncated = (text_body, False) if full else _terminal_preview(text_body, max_chars=max_chars)
    if output_text:
        print(output_text)
    if truncated:
        _ui(f"内容较长，已截断显示前 {len(output_text)} / {len(text_body)} 个字符；使用 --full 查看全文")
