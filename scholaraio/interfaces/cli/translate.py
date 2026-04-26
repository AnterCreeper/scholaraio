"""Translate CLI command handler."""

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


def _resolve_paper(paper_id: str, cfg):
    from scholaraio.interfaces.cli import compat as cli_mod

    return cli_mod._resolve_paper(paper_id, cfg)


def cmd_translate(args: argparse.Namespace, cfg) -> None:
    from scholaraio.services.translate import batch_translate, translate_paper

    ui = _ui
    papers_dir = cfg.papers_dir
    target_lang = (args.lang or cfg.translate.target_lang).lower().strip()

    try:
        from scholaraio.services.translate import validate_lang

        validate_lang(target_lang)
    except ValueError:
        ui(f"错误: 无效的语言代码 '{target_lang}'（应为 2-5 个小写字母，如 zh、en、ja）")
        sys.exit(1)

    if args.paper_id:
        paper_d = _resolve_paper(args.paper_id, cfg)
        tr = translate_paper(
            paper_d,
            cfg,
            target_lang=target_lang,
            force=args.force,
            portable=args.portable,
            progress_callback=ui,
        )
        if tr.ok:
            ui(f"翻译完成: {tr.path}")
            if tr.portable_path:
                ui(f"可移植导出: {tr.portable_path}")
        else:
            from scholaraio.services.translate import (
                SKIP_ALL_CHUNKS_FAILED,
                SKIP_ALREADY_EXISTS,
                SKIP_EMPTY,
                SKIP_NO_MD,
                SKIP_SAME_LANG,
            )

            _skip_messages = {
                SKIP_NO_MD: "跳过: 该论文目录下无 paper.md 文件",
                SKIP_EMPTY: "跳过: paper.md 内容为空",
                SKIP_SAME_LANG: f"跳过: 论文已是目标语言 ({target_lang})",
                SKIP_ALREADY_EXISTS: "跳过: 翻译已存在（使用 --force 强制重新翻译）",
            }
            if tr.partial and tr.path:
                ui(
                    f"翻译中断：已完成 {tr.completed_chunks}/{tr.total_chunks} 块，"
                    f"当前结果已写入 {tr.path}，可稍后继续续翻"
                )
                sys.exit(1)
            if tr.skip_reason == SKIP_ALL_CHUNKS_FAILED:
                ui("翻译失败: 所有分块都翻译失败，未写出目标文件")
                sys.exit(1)
            ui(_skip_messages.get(tr.skip_reason, "跳过"))
    elif args.all:
        ui(f"批量翻译 → {target_lang}")
        stats = batch_translate(papers_dir, cfg, target_lang=target_lang, force=args.force, portable=args.portable)
        ui(f"完成: {stats['translated']} 已翻译 | {stats['skipped']} 跳过 | {stats['failed']} 失败")
    else:
        ui("请指定 <paper-id> 或 --all")
        sys.exit(1)
