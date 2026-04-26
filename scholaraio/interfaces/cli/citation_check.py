"""Citation-check CLI command handler."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


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


def _resolve_ws_paper_ids(args: argparse.Namespace, cfg) -> set[str] | None:
    from scholaraio.interfaces.cli import compat as cli_mod

    return cli_mod._resolve_ws_paper_ids(args, cfg)


def cmd_citation_check(args: argparse.Namespace, cfg) -> None:
    from scholaraio.services.citation_check import check_citations, extract_citations

    if args.file:
        p = Path(args.file)
        if not p.exists():
            _log_error("文件不存在：%s", p)
            sys.exit(1)
        text = p.read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()

    if not text.strip():
        _ui("输入文本为空。")
        return

    citations = extract_citations(text)
    if not citations:
        _ui("未在文本中发现引用。")
        return

    _ui(f"提取到 {len(citations)} 条引用，正在验证…\n")

    try:
        paper_ids = _resolve_ws_paper_ids(args, cfg)
    except ValueError as e:
        _ui(str(e))
        return

    results = check_citations(
        citations,
        cfg.index_db,
        paper_ids=paper_ids,
    )

    counts = {"VERIFIED": 0, "NOT_IN_LIBRARY": 0, "AMBIGUOUS": 0}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1

    status_labels = {
        "VERIFIED": "已验证",
        "NOT_IN_LIBRARY": "库中未找到",
        "AMBIGUOUS": "候选不唯一",
    }

    for r in results:
        status_icon = {"VERIFIED": "✓", "NOT_IN_LIBRARY": "✗", "AMBIGUOUS": "?"}.get(r["status"], " ")
        status_text = status_labels.get(r["status"], r["status"])
        _ui(f"  [{status_icon}] {status_text:8s}  {r['raw']}  ({r['author']}, {r['year']})")
        if r["matches"]:
            for m in r["matches"][:3]:
                display_id = m.get("dir_name") or m.get("paper_id", "?")
                _ui(f"       → {display_id}")
                _ui(f"         {m.get('title', '?')}")

    _ui()
    _ui(
        f"验证结果：已验证 {counts['VERIFIED']} / "
        f"候选不唯一 {counts['AMBIGUOUS']} / "
        f"库中未找到 {counts['NOT_IN_LIBRARY']}"
    )
