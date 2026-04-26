"""Index CLI command handler."""

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


def cmd_index(args: argparse.Namespace, cfg) -> None:
    from scholaraio.services.index import build_index

    papers_dir = cfg.papers_dir
    db_path = cfg.index_db

    if not papers_dir.exists():
        _log_error("论文目录不存在: %s", papers_dir)
        sys.exit(1)

    action = "重建索引" if args.rebuild else "构建索引"
    _ui(f"{action}: {papers_dir} -> {db_path}")
    count = build_index(papers_dir, db_path, rebuild=args.rebuild)
    _ui(f"完成：已索引 {count} 篇论文。")
    _ui("下一步：运行 `scholaraio search <关键词>` 或 `scholaraio usearch <关键词>` 开始检索。")
