"""Proceedings CLI command handler."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _ui(msg: str = "") -> None:
    try:
        from scholaraio.interfaces.cli import compat as cli_mod
    except ImportError:
        from scholaraio.core.log import ui as log_ui

        log_ui(msg)
        return
    cli_mod.ui(msg)


def cmd_proceedings(args: argparse.Namespace, cfg) -> None:
    del cfg  # proceedings subcommands currently operate on explicit paths.

    if args.proceedings_action == "build-clean-candidates":
        from scholaraio.services.ingest.proceedings_volume import build_proceedings_clean_candidates

        proceeding_dir = Path(args.proceeding_dir).expanduser()
        if not proceeding_dir.exists():
            _ui(f"proceedings 目录不存在: {proceeding_dir}")
            return

        candidates_path = build_proceedings_clean_candidates(proceeding_dir)
        _ui(f"已生成 proceedings clean candidates: {candidates_path}")
        _ui("等待 agent 审阅 clean_candidates.json 并生成 clean_plan.json，然后再执行后续清洗。")
        return

    if args.proceedings_action == "apply-split":
        from scholaraio.services.ingest.proceedings_volume import apply_proceedings_split_plan

        proceeding_dir = Path(args.proceeding_dir).expanduser()
        split_plan = Path(args.split_plan).expanduser()

        if not proceeding_dir.exists():
            _ui(f"proceedings 目录不存在: {proceeding_dir}")
            return
        if not split_plan.exists():
            _ui(f"split plan 不存在: {split_plan}")
            return

        apply_proceedings_split_plan(proceeding_dir, split_plan)
        meta = json.loads((proceeding_dir / "meta.json").read_text(encoding="utf-8"))
        _ui(f"已应用 proceedings split plan: {proceeding_dir.name} ({meta.get('child_paper_count', 0)} 篇)")
        return

    if args.proceedings_action == "apply-clean":
        from scholaraio.services.ingest.proceedings_volume import apply_proceedings_clean_plan

        proceeding_dir = Path(args.proceeding_dir).expanduser()
        clean_plan = Path(args.clean_plan).expanduser()

        if not proceeding_dir.exists():
            _ui(f"proceedings 目录不存在: {proceeding_dir}")
            return
        if not clean_plan.exists():
            _ui(f"clean plan 不存在: {clean_plan}")
            return

        apply_proceedings_clean_plan(proceeding_dir, clean_plan)
        meta = json.loads((proceeding_dir / "meta.json").read_text(encoding="utf-8"))
        _ui(f"已应用 proceedings clean plan: {proceeding_dir.name} ({meta.get('child_paper_count', 0)} 篇)")
        return

    _ui(f"未知 proceedings 子命令: {args.proceedings_action}")
