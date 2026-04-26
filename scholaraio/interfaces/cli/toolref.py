"""Tool reference CLI command handler."""

from __future__ import annotations

import argparse
import logging
import sys


def _ui(msg: str = "") -> None:
    try:
        from scholaraio.interfaces.cli import compat as cli_mod
    except ImportError:
        from scholaraio.core.log import ui as log_ui

        log_ui(msg)
        return
    cli_mod.ui(msg)


def _log_error(msg: str, *args) -> None:
    try:
        from scholaraio.interfaces.cli import compat as cli_mod
    except ImportError:
        logging.getLogger(__name__).error(msg, *args)
        return
    cli_mod._log.error(msg, *args)


def _resolve_result_limit(args: argparse.Namespace, default: int) -> int:
    from scholaraio.interfaces.cli import compat as cli_mod

    return cli_mod._resolve_result_limit(args, default)


def cmd_toolref(args: argparse.Namespace, cfg) -> None:
    from scholaraio.stores.toolref import (
        TOOL_REGISTRY,
        toolref_fetch,
        toolref_list,
        toolref_search,
        toolref_show,
        toolref_use,
    )

    try:
        action = args.toolref_action

        if action == "fetch":
            count = toolref_fetch(args.tool, version=args.version, force=args.force, cfg=cfg)
            if count == 0:
                _ui("未索引任何页面。请检查版本号或文档源。")

        elif action == "show":
            results = toolref_show(args.tool, *args.path, cfg=cfg)
            if not results:
                _ui(f"未找到匹配：{args.tool} {' '.join(args.path)}")
                _ui(f"尝试搜索：scholaraio toolref search {args.tool} {' '.join(args.path)}")
                return
            for r in results:
                _ui(f"\n{'=' * 60}")
                _ui(r["page_name"])
                if r.get("section"):
                    _ui(f"   段落：{r['section']}  |  程序：{r.get('program', '')}")
                if r.get("synopsis"):
                    _ui(f"   {r['synopsis']}")
                _ui(f"{'─' * 60}")
                _ui(r.get("content", "(无内容)"))

        elif action == "search":
            query = " ".join(args.query)
            results = toolref_search(
                args.tool,
                query,
                top_k=_resolve_result_limit(args, 20),
                program=args.program,
                section=args.section,
                cfg=cfg,
            )
            if not results:
                _ui(f"无结果：{query}")
                return
            _ui(f"找到 {len(results)} 条结果：\n")
            for i, r in enumerate(results, 1):
                synopsis = r.get("synopsis", "")[:80]
                _ui(f"  {i:2d}. [{r['page_name']}] {synopsis}")

        elif action == "list":
            entries = toolref_list(args.tool, cfg=cfg)
            if not entries:
                tools = ", ".join(TOOL_REGISTRY.keys())
                _ui(f"无已拉取文档。支持的工具：{tools}")
                _ui("使用 `scholaraio toolref fetch <tool> --version <ver>` 拉取")
                return
            current_tool = ""
            for e in entries:
                if e["tool"] != current_tool:
                    current_tool = e["tool"]
                    _ui(f"\n{e['display_name']}:")
                marker = " (current)" if e["is_current"] else ""
                completeness = ""
                unit = "页" if e.get("source_type") == "manifest" else "条"
                if e.get("source_type") == "manifest" and e.get("expected_pages"):
                    completeness = f" [{e['page_count']}/{e['expected_pages']} 已索引"
                    failed_pages = e.get("failed_pages")
                    if failed_pages:
                        completeness += f", {failed_pages} 失败"
                    completeness += "]"
                _ui(f"  {e['version']}{marker} — {e['page_count']} {unit}{completeness}")

        elif action == "use":
            toolref_use(args.tool, args.version, cfg=cfg)
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        _log_error("%s", e)
        sys.exit(1)
