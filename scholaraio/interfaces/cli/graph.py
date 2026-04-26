"""Citation graph CLI command handlers."""

from __future__ import annotations

import argparse


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


def _resolve_ws_paper_ids(args: argparse.Namespace, cfg) -> set[str] | None:
    from scholaraio.interfaces.cli import compat as cli_mod

    return cli_mod._resolve_ws_paper_ids(args, cfg)


def cmd_refs(args: argparse.Namespace, cfg) -> None:
    from scholaraio.services.index import get_references
    from scholaraio.stores.papers import read_meta

    paper_d = _resolve_paper(args.paper_id, cfg)
    meta = read_meta(paper_d)
    paper_uuid = meta.get("id", "")

    pids = _resolve_ws_paper_ids(args, cfg)
    refs = get_references(paper_uuid, cfg.index_db, paper_ids=pids)
    if not refs:
        _ui("该论文没有参考文献数据。请先运行 refetch 拉取 references。")
        return

    in_lib = [r for r in refs if r.get("target_id")]
    out_lib = [r for r in refs if not r.get("target_id")]

    scope = f"工作区 {args.ws}" if getattr(args, "ws", None) else "库内"
    _ui(f"参考文献共 {len(refs)} 篇（{scope} {len(in_lib)} 篇，库外 {len(out_lib)} 篇）\n")

    if in_lib:
        _ui("── 库内 ──")
        for i, r in enumerate(in_lib, 1):
            display = r.get("dir_name") or r["target_id"]
            year = r.get("year") or "?"
            author = r.get("first_author") or "?"
            _ui(f"[{i}] {display}")
            _ui(f"     {author} | {year} | {r.get('title', '?')}")
            _ui(f"     DOI: {r['target_doi']}")
            _ui()

    if out_lib:
        _ui("── 库外 ──")
        for i, r in enumerate(out_lib, 1):
            _ui(f"[{i}] DOI: {r['target_doi']}")
        _ui()


def cmd_citing(args: argparse.Namespace, cfg) -> None:
    from scholaraio.services.index import get_citing_papers
    from scholaraio.stores.papers import read_meta

    paper_d = _resolve_paper(args.paper_id, cfg)
    meta = read_meta(paper_d)
    paper_uuid = meta.get("id", "")

    pids = _resolve_ws_paper_ids(args, cfg)
    results = get_citing_papers(paper_uuid, cfg.index_db, paper_ids=pids)
    if not results:
        scope = f"工作区 {args.ws} 中" if getattr(args, "ws", None) else "本地"
        _ui(f"没有找到引用该论文的{scope}论文。")
        return

    scope = f"工作区 {args.ws}" if getattr(args, "ws", None) else "本地"
    _ui(f"共 {len(results)} 篇{scope}论文引用了此论文：\n")
    for i, r in enumerate(results, 1):
        display = r.get("dir_name") or r["source_id"]
        year = r.get("year") or "?"
        author = r.get("first_author") or "?"
        _ui(f"[{i}] {display}")
        _ui(f"     {author} | {year} | {r.get('title', '?')}")
        _ui()


def cmd_shared_refs(args: argparse.Namespace, cfg) -> None:
    from scholaraio.services.index import get_shared_references
    from scholaraio.stores.papers import read_meta

    paper_uuids = []
    for pid in args.paper_ids:
        paper_d = _resolve_paper(pid, cfg)
        meta = read_meta(paper_d)
        paper_uuids.append(meta.get("id", ""))

    min_shared = args.min if args.min is not None else 2
    pids = _resolve_ws_paper_ids(args, cfg)
    results = get_shared_references(paper_uuids, cfg.index_db, min_shared=min_shared, paper_ids=pids)
    if not results:
        _ui(f"没有找到被 ≥{min_shared} 篇论文共同引用的参考文献。")
        return

    _ui(f"共同参考文献（被 ≥{min_shared} 篇共引）：共 {len(results)} 篇\n")
    for i, r in enumerate(results, 1):
        count = r["shared_count"]
        if r.get("target_id"):
            display = r.get("dir_name") or r["target_id"]
            year = r.get("year") or "?"
            _ui(f"[{i}] [{count}x] {display}")
            _ui(f"     {r.get('title', '?')} | {year}")
            _ui(f"     DOI: {r['target_doi']}")
        else:
            _ui(f"[{i}] [{count}x] DOI: {r['target_doi']}")
        _ui()
