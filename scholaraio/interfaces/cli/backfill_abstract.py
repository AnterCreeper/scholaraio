"""Abstract backfill CLI command handler."""

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


def _log_debug(msg: str, *args) -> None:
    try:
        from scholaraio.interfaces.cli import compat as cli_mod
    except ImportError:
        logging.getLogger(__name__).debug(msg, *args)
        return
    cli_mod._log.debug(msg, *args)


def _log_error(msg: str, *args) -> None:
    try:
        from scholaraio.interfaces.cli import compat as cli_mod
    except ImportError:
        logging.getLogger(__name__).error(msg, *args)
        return
    cli_mod._log.error(msg, *args)


def cmd_backfill_abstract(args: argparse.Namespace, cfg) -> None:
    from scholaraio.services.ingest_metadata import backfill_abstracts

    papers_dir = cfg.papers_dir
    if not papers_dir.exists():
        _log_error("论文目录不存在: %s", papers_dir)
        sys.exit(1)

    action = "预览补全" if args.dry_run else "补全摘要"
    doi_fetch = getattr(args, "doi_fetch", False)
    source = "DOI 官方来源" if doi_fetch else "本地 .md + LLM 回退"
    _ui(f"{action}摘要（{source}）...\n")
    stats = backfill_abstracts(papers_dir, dry_run=args.dry_run, doi_fetch=doi_fetch, cfg=cfg)
    parts = [f"{stats['filled']} 已补全", f"{stats['skipped']} 跳过", f"{stats['failed']} 失败"]
    if stats.get("updated"):
        parts.insert(1, f"{stats['updated']} 已更新为官方摘要")
    _ui(f"\n完成: {' | '.join(parts)}")
    if stats["filled"] and not args.dry_run:
        _log_debug("consider rebuilding vector index: scholaraio embed --rebuild")
