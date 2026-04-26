"""Workspace CLI command handler."""

from __future__ import annotations

import argparse
import logging
import sqlite3
from pathlib import Path


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


def _workspace_root(cfg) -> Path:
    from scholaraio.interfaces.cli import compat as cli_mod

    return cli_mod._workspace_root(cfg)


def _resolve_top(args: argparse.Namespace, default: int) -> int:
    from scholaraio.interfaces.cli import compat as cli_mod

    return cli_mod._resolve_top(args, default)


def _format_match_tag(match: str) -> str:
    from scholaraio.interfaces.cli import compat as cli_mod

    return cli_mod._format_match_tag(match)


def _print_search_result(idx: int, result: dict, extra: str = "") -> None:
    from scholaraio.interfaces.cli import compat as cli_mod

    cli_mod._print_search_result(idx, result, extra=extra)


def _print_search_next_steps(*, include_ws_add: bool = True) -> None:
    from scholaraio.interfaces.cli import compat as cli_mod

    cli_mod._print_search_next_steps(include_ws_add=include_ws_add)


def _read_manifest_safe(ws_dir: Path) -> dict | None:
    from scholaraio.projects import workspace as workspace_mod

    try:
        return workspace_mod.read_manifest(ws_dir)
    except RuntimeError as exc:
        _ui(str(exc))
        return None


def _manifest_summary_lines(manifest: dict | None) -> list[str]:
    if not manifest:
        return []
    if manifest.get("schema_version") != 1:
        return []
    lines: list[str] = []
    description = manifest.get("description")
    if isinstance(description, str) and description:
        lines.append(f"    描述: {description}")
    tags = manifest.get("tags")
    if isinstance(tags, list) and tags:
        lines.append(f"    标签: {', '.join(str(tag) for tag in tags)}")
    return lines


def _manifest_detail_lines(manifest: dict | None) -> list[str]:
    if not manifest:
        return []
    if manifest.get("schema_version") != 1:
        return []
    lines: list[str] = []
    name = manifest.get("name")
    if isinstance(name, str) and name:
        lines.append(f"  名称: {name}")
    description = manifest.get("description")
    if isinstance(description, str) and description:
        lines.append(f"  描述: {description}")
    tags = manifest.get("tags")
    if isinstance(tags, list) and tags:
        lines.append(f"  标签: {', '.join(str(tag) for tag in tags)}")
    outputs = manifest.get("outputs")
    if isinstance(outputs, dict):
        default_dir = outputs.get("default_dir")
        if isinstance(default_dir, str) and default_dir:
            lines.append(f"  默认输出目录: {default_dir}")
    mounts = manifest.get("mounts")
    if isinstance(mounts, dict):
        for bucket in ("explore", "toolref"):
            values = mounts.get(bucket)
            if isinstance(values, list) and values:
                lines.append(f"  {bucket} 挂载: {', '.join(str(value) for value in values)}")
    return lines


def cmd_ws(args: argparse.Namespace, cfg) -> None:
    from scholaraio.projects import workspace as workspace_mod

    ws_root = _workspace_root(cfg)
    action = args.ws_action

    # Validate workspace-name style arguments in CLI layer to prevent path traversal.
    names_to_check: list[str] = []
    if action in {"init", "add", "remove", "show", "search", "export"}:
        names_to_check.append(args.name)
    elif action == "rename":
        names_to_check.extend([args.old_name, args.new_name])

    for name in names_to_check:
        if not workspace_mod.validate_workspace_name(name):
            _ui(f"非法工作区名称: {name}")
            return

    if action == "init":
        ws_dir = ws_root / args.name
        workspace_mod.create(ws_dir)
        _ui(f"工作区已创建: {ws_dir}")

    elif action == "add":
        ws_dir = ws_root / args.name
        if not workspace_mod.has_paper_index(ws_dir):
            workspace_mod.create(ws_dir)

        # Resolve paper_refs from batch flags or positional args
        paper_refs = args.paper_refs or []
        if args.add_all:
            index_db_path = Path(cfg.index_db)
            if not index_db_path.exists():
                _ui("索引数据库不存在，可能尚未初始化。")
                _ui("请先运行: scholaraio index")
                return

            try:
                with sqlite3.connect(cfg.index_db) as conn:
                    conn.row_factory = sqlite3.Row
                    rows = conn.execute("SELECT id, dir_name FROM papers_registry").fetchall()
            except sqlite3.OperationalError as e:
                _log_debug("索引数据库查询失败: %s", e)
                _ui("索引数据库结构不完整或尚未初始化。")
                _ui("请先运行: scholaraio index")
                return

            resolved = [{"id": r["id"], "dir_name": r["dir_name"]} for r in rows]
            if not resolved:
                _ui("主库中没有论文")
                return
            added = workspace_mod.add(ws_dir, [], cfg.index_db, resolved=resolved)
            _ui(f"已添加 {len(added)} 篇论文到 {args.name}")
            for entry in added:
                _ui(f"  + {entry['dir_name']}")
            return
        elif args.add_topic is not None:
            from scholaraio.services.topics import get_topic_papers, load_model

            try:
                model = load_model(cfg.topics_model_dir)
            except (FileNotFoundError, ImportError) as e:
                _ui(f"无法加载主题模型: {e}")
                _ui("请先运行: scholaraio topics --build")
                return
            papers = get_topic_papers(model, args.add_topic)
            if not papers:
                _ui(f"主题 {args.add_topic} 中没有论文")
                return
            paper_refs = [p["paper_id"] for p in papers]
            _ui(f"主题 {args.add_topic}: 找到 {len(paper_refs)} 篇论文")
        elif args.add_search is not None:
            from scholaraio.services.index import unified_search

            results = unified_search(
                args.add_search,
                cfg.index_db,
                top_k=_resolve_top(args, cfg.search.top_k),
                cfg=cfg,
                year=getattr(args, "year", None),
                journal=getattr(args, "journal", None),
                paper_type=getattr(args, "paper_type", None),
            )
            if not results:
                _ui(f'未找到 "{args.add_search}" 的结果')
                return
            paper_refs = [r["paper_id"] for r in results]
            _ui(f'搜索 "{args.add_search}": 找到 {len(paper_refs)} 篇论文')

        if not paper_refs:
            _ui("未指定论文引用")
            return

        added = workspace_mod.add(ws_dir, paper_refs, cfg.index_db)
        _ui(f"已添加 {len(added)} 篇论文到 {args.name}")
        for entry in added:
            _ui(f"  + {entry['dir_name']}")

    elif action == "remove":
        ws_dir = ws_root / args.name
        removed = workspace_mod.remove(ws_dir, args.paper_refs, cfg.index_db)
        _ui(f"已移除 {len(removed)} 篇论文")
        for entry in removed:
            _ui(f"  - {entry['dir_name']}")

    elif action == "list":
        names = workspace_mod.list_workspaces(ws_root)
        if not names:
            _ui("没有工作区")
            return
        for name in names:
            ws_dir = ws_root / name
            ids = workspace_mod.read_paper_ids(ws_dir)
            _ui(f"  {name}（{len(ids)} 篇论文）")
            for line in _manifest_summary_lines(_read_manifest_safe(ws_dir)):
                _ui(line)

    elif action == "show":
        ws_dir = ws_root / args.name
        papers = workspace_mod.show(ws_dir, cfg.index_db)
        _ui(f"工作区 {args.name}: {len(papers)} 篇论文")
        for line in _manifest_detail_lines(_read_manifest_safe(ws_dir)):
            _ui(line)
        for i, p in enumerate(papers, 1):
            _ui(f"  {i:3d}. {p['dir_name']}")

    elif action == "search":
        ws_dir = ws_root / args.name
        pids = workspace_mod.read_paper_ids(ws_dir)
        if not pids:
            _ui("工作区为空")
            return
        query = " ".join(args.query)
        mode = getattr(args, "mode", "unified")
        top_k = _resolve_top(args, cfg.search.top_k)

        if mode == "keyword":
            from scholaraio.services.index import search as kw_search

            results = kw_search(
                query,
                cfg.index_db,
                top_k=top_k,
                cfg=cfg,
                year=args.year,
                journal=args.journal,
                paper_type=args.paper_type,
                paper_ids=pids,
            )
        elif mode == "semantic":
            from scholaraio.services.vectors import vsearch

            results = vsearch(
                query,
                cfg.index_db,
                top_k=top_k,
                cfg=cfg,
                year=args.year,
                journal=args.journal,
                paper_type=args.paper_type,
                paper_ids=pids,
            )
        else:
            from scholaraio.services.index import unified_search

            results = unified_search(
                query,
                cfg.index_db,
                top_k=top_k,
                cfg=cfg,
                year=args.year,
                journal=args.journal,
                paper_type=args.paper_type,
                paper_ids=pids,
            )

        if not results:
            _ui(f'工作区 {args.name} 中未找到 "{query}" 的结果')
            return
        _ui(f"工作区 {args.name} 中找到 {len(results)} 篇:\n")
        for i, r in enumerate(results, 1):
            match = r.get("match")
            extra = _format_match_tag(match) if match else ""
            _print_search_result(i, r, extra=extra)
        _print_search_next_steps(include_ws_add=False)

    elif action == "export":
        ws_dir = ws_root / args.name
        dir_names = workspace_mod.read_dir_names(ws_dir, cfg.index_db)
        if not dir_names:
            _ui("工作区为空")
            return
        from scholaraio.services.export import export_bibtex

        bib = export_bibtex(
            cfg.papers_dir,
            paper_ids=list(dir_names),
            year=args.year,
            journal=args.journal,
            paper_type=args.paper_type,
        )
        if not bib:
            _ui("未找到匹配的论文")
            return
        if args.output:
            out = Path(args.output)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(bib, encoding="utf-8")
            _ui(f"已导出到 {out}（{bib.count('@')} 篇）")
        else:
            print(bib)

    elif action == "rename":
        try:
            workspace_mod.rename(ws_root, args.old_name, args.new_name)
        except (ValueError, FileNotFoundError, FileExistsError) as e:
            _ui(str(e))
            return
        _ui(f"工作区已重命名: {args.old_name} → {args.new_name}")
