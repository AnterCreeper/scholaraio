"""Shared CLI output formatting helpers."""

from __future__ import annotations

from typing import Any

from scholaraio.core.log import ui as _default_ui


def _ui(message: str = "") -> None:
    try:
        from scholaraio.interfaces.cli import compat as cli_mod
    except ImportError:
        _default_ui(message)
        return
    cli_mod.ui(message)


def _print_search_result(idx: int, r: dict[str, Any], extra: str = "") -> None:
    authors = r.get("authors") or ""
    author_display = authors.split(",")[0].strip() + (" et al." if "," in authors else "")
    cite = r.get("citation_count") or ""
    cite_suffix = f"  [被引: {cite}]" if cite else ""
    extra_suffix = f"  ({extra})" if extra else ""
    # Prefer dir_name for display, fall back to paper_id (UUID)
    display_id = r.get("dir_name") or r["paper_id"]
    _ui(f"[{idx}] {display_id}{extra_suffix}")
    _ui(f"     {author_display} | {r.get('year', '?')} | {r.get('journal', '?')}{cite_suffix}")
    _ui(f"     {r['title']}")
    _ui()


def _print_search_next_steps(include_ws_add: bool = True) -> None:
    _ui("下一步：可以运行 `scholaraio show <paper-id> --layer 2/3/4` 查看摘要、结论或全文。")
    if include_ws_add:
        _ui("也可以运行 `scholaraio ws add <工作区名> <paper-id>` 把感兴趣的论文加入工作区。")


def _format_match_tag(match: str) -> str:
    mapping = {
        "both": "关键词+语义",
        "fts": "关键词",
        "vec": "语义",
    }
    return mapping.get(match, match)


def _format_citations(cc: Any) -> str:
    if not cc:
        return ""
    if isinstance(cc, (int, float, str)):
        return str(cc)
    if not isinstance(cc, dict):
        return ""
    parts = []
    for src in ("semantic_scholar", "openalex", "crossref"):
        if src in cc:
            label = {"semantic_scholar": "S2", "openalex": "OA", "crossref": "CR"}[src]
            parts.append(f"{label}:{cc[src]}")
    return " | ".join(parts)
