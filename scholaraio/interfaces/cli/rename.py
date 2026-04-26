"""Rename CLI command handler."""

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


def _log_debug(msg: str, *args) -> None:
    try:
        from scholaraio.interfaces.cli import compat as cli_mod
    except ImportError:
        logging.getLogger(__name__).debug(msg, *args)
        return
    cli_mod._log.debug(msg, *args)


def cmd_rename(args: argparse.Namespace, cfg) -> None:
    from scholaraio.services.ingest_metadata import rename_paper
    from scholaraio.stores.papers import iter_paper_dirs

    papers_dir = cfg.papers_dir

    if args.all:
        targets = sorted(d / "meta.json" for d in iter_paper_dirs(papers_dir))
    elif args.paper_id:
        targets = [papers_dir / args.paper_id / "meta.json"]
    else:
        _log_error("请指定 <paper-id> 或 --all")
        sys.exit(1)

    renamed = skip = fail = 0
    for json_path in targets:
        if not json_path.exists():
            _log_error("未找到论文: %s", json_path.parent.name)
            fail += 1
            continue

        new_path = rename_paper(json_path, dry_run=args.dry_run)
        if new_path:
            action = "预览" if args.dry_run else "重命名"
            _ui(f"{action}: {json_path.parent.name} -> {new_path.parent.name}")
            renamed += 1
        else:
            skip += 1

    _ui(f"\n完成: {renamed} 已重命名 | {skip} 未变化 | {fail} 失败")
    if renamed and not args.dry_run:
        _log_debug("consider rebuilding index: scholaraio index --rebuild")
