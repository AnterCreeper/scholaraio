"""Export CLI command handlers."""

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


def _workspace_root(cfg) -> Path:
    from scholaraio.interfaces.cli import compat as cli_mod

    return cli_mod._workspace_root(cfg)


def _default_docx_output_path(cfg) -> Path:
    from scholaraio.interfaces.cli import compat as cli_mod

    return cli_mod._default_docx_output_path(cfg)


def cmd_export(args: argparse.Namespace, cfg) -> None:
    action = args.export_action
    if action == "bibtex":
        _cmd_export_bibtex(args, cfg)
    elif action == "ris":
        _cmd_export_ris(args, cfg)
    elif action == "markdown":
        _cmd_export_markdown(args, cfg)
    elif action == "docx":
        _cmd_export_docx(args, cfg)
    else:
        _log_error("未知导出操作: %s", action)
        sys.exit(1)


def _cmd_export_ris(args: argparse.Namespace, cfg) -> None:
    from scholaraio.services.export import export_ris

    paper_ids = args.paper_ids if args.paper_ids else None
    if not paper_ids and not args.all:
        _log_error("请指定论文 ID 或 --all")
        sys.exit(1)

    ris = export_ris(
        cfg.papers_dir,
        paper_ids=paper_ids,
        year=args.year,
        journal=args.journal,
    )

    if not ris:
        _ui("未找到匹配的论文")
        return

    if args.output:
        out = Path(args.output)
        out.write_text(ris, encoding="utf-8")
        count = ris.count("TY  -")
        _ui(f"已导出到 {out}（{count} 篇）")
    else:
        print(ris)


def _cmd_export_markdown(args: argparse.Namespace, cfg) -> None:
    from scholaraio.services.export import export_markdown_refs

    paper_ids = args.paper_ids if args.paper_ids else None
    if not paper_ids and not args.all:
        _log_error("请指定论文 ID 或 --all")
        sys.exit(1)

    style = getattr(args, "style", "apa") or "apa"

    try:
        md = export_markdown_refs(
            cfg.papers_dir,
            cfg=cfg,
            paper_ids=paper_ids,
            year=args.year,
            journal=args.journal,
            numbered=not args.bullet,
            style=style,
        )
    except (FileNotFoundError, ValueError, AttributeError, ImportError) as e:
        _log_error("%s", e)
        sys.exit(1)

    if not md:
        _ui("未找到匹配的论文")
        return

    if args.output:
        out = Path(args.output)
        out.write_text(md, encoding="utf-8")
        count = md.count("\n")
        _ui(f"已导出到 {out}（{count} 条引用，{style} 格式）")
    else:
        print(md)


def _cmd_export_docx(args: argparse.Namespace, cfg) -> None:
    from scholaraio.services.export import export_docx

    if args.input:
        input_path = Path(args.input)
        if not input_path.exists():
            _log_error("输入文件不存在: %s", args.input)
            sys.exit(1)
        content = input_path.read_text(encoding="utf-8")
    elif not sys.stdin.isatty():
        content = sys.stdin.read()
    else:
        _log_error("请通过 --input 指定 Markdown 文件，或通过 stdin 传入内容")
        sys.exit(1)

    output = Path(args.output) if args.output else _default_docx_output_path(cfg)

    try:
        export_docx(content, output, title=args.title or None)
        _ui(f"已导出到 {output}")
    except ImportError as e:
        _log_error("%s", e)
        sys.exit(1)


def _cmd_export_bibtex(args: argparse.Namespace, cfg) -> None:
    from scholaraio.services.export import export_bibtex

    paper_ids = args.paper_ids if args.paper_ids else None
    if not paper_ids and not args.all:
        _log_error("请指定论文 ID 或 --all")
        sys.exit(1)

    bib = export_bibtex(
        cfg.papers_dir,
        paper_ids=paper_ids,
        year=args.year,
        journal=args.journal,
    )

    if not bib:
        _ui("未找到匹配的论文")
        return

    if args.output:
        out = Path(args.output)
        out.write_text(bib, encoding="utf-8")
        _ui(f"已导出到 {out}（{bib.count('@')} 篇）")
    else:
        print(bib)
