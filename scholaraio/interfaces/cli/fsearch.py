"""Federated search CLI command handler."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any


def _ui(msg: str = "") -> None:
    try:
        from scholaraio.interfaces.cli import compat as cli_mod
    except ImportError:
        from scholaraio.core.log import ui as log_ui

        log_ui(msg)
        return
    cli_mod.ui(msg)


def _resolve_top(args: argparse.Namespace, default: int) -> int:
    from scholaraio.interfaces.cli import compat as cli_mod

    return cli_mod._resolve_top(args, default)


def _print_search_result(idx: int, result: dict, extra: str = "") -> None:
    from scholaraio.interfaces.cli import compat as cli_mod

    cli_mod._print_search_result(idx, result, extra=extra)


def _format_match_tag(match: str) -> str:
    from scholaraio.interfaces.cli import compat as cli_mod

    return cli_mod._format_match_tag(match)


def _search_arxiv(query: str, top_k: int) -> list[dict]:
    """Call arXiv Atom API, return simplified paper dicts."""
    from scholaraio.providers.arxiv import search_arxiv

    return search_arxiv(query, top_k)


def _query_dois_for_set(cfg, doi_set: list[str]) -> set[str]:
    """Return the subset of doi_set that exists in the main library."""
    import sqlite3

    if not doi_set or not Path(cfg.index_db).exists():
        return set()
    try:
        normalized = [d.lower() for d in doi_set]
        placeholders = ",".join("?" * len(normalized))
        with sqlite3.connect(str(cfg.index_db)) as conn:
            rows = conn.execute(
                f"SELECT doi FROM papers_registry WHERE LOWER(doi) IN ({placeholders})",
                normalized,
            ).fetchall()
        return {r[0].lower() for r in rows}
    except Exception:
        return set()


def _query_arxiv_ids_for_set(cfg, arxiv_id_set: list[str]) -> set[str]:
    """Return the subset of normalized arXiv IDs that exists in the main library."""
    from scholaraio.providers.arxiv import normalize_arxiv_ref
    from scholaraio.stores.papers import iter_paper_dirs, read_meta

    if not arxiv_id_set or not Path(cfg.papers_dir).exists():
        return set()

    wanted: set[str] = set()
    for arxiv_id in arxiv_id_set:
        normalized = normalize_arxiv_ref(arxiv_id)
        if normalized:
            wanted.add(normalized)
    if not wanted:
        return set()

    found: set[str] = set()
    try:
        for paper_dir in iter_paper_dirs(Path(cfg.papers_dir)):
            try:
                meta = read_meta(paper_dir)
            except Exception:
                continue
            arxiv_id = meta.get("arxiv_id") or (meta.get("ids") or {}).get("arxiv", "")
            normalized = normalize_arxiv_ref(arxiv_id)
            if normalized and normalized in wanted:
                found.add(normalized)
    except Exception:
        return set()
    return found


def _search_arxiv_from_cli(query: str, top_k: int) -> list[dict]:
    from scholaraio.interfaces.cli import compat as cli_mod

    return cli_mod._search_arxiv(query, top_k)


def _query_dois_for_set_from_cli(cfg, doi_set: list[str]) -> set[str]:
    from scholaraio.interfaces.cli import compat as cli_mod

    return cli_mod._query_dois_for_set(cfg, doi_set)


def _query_arxiv_ids_for_set_from_cli(cfg, arxiv_id_set: list[str]) -> set[str]:
    from scholaraio.interfaces.cli import compat as cli_mod

    return cli_mod._query_arxiv_ids_for_set(cfg, arxiv_id_set)


def cmd_fsearch(args: argparse.Namespace, cfg) -> None:
    query = " ".join(args.query)
    top_k = _resolve_top(args, 10)
    scope_str = args.scope or "main"
    scopes = [s.strip() for s in scope_str.split(",") if s.strip()] or ["main"]

    _ui(f'联邦搜索: "{query}"  scope={scope_str}\n')

    for scope in scopes:
        if scope == "main":
            _ui("── [主库] ──")
            results: list[dict[str, Any]] = []
            diagnostics: Any = {"vector_degraded": False}
            if not cfg.index_db.exists():
                _ui("  主库索引不存在，请先运行 scholaraio index")
            else:
                from scholaraio.services.index import unified_search

                try:
                    results, diagnostics = unified_search(
                        query,
                        cfg.index_db,
                        top_k=top_k,
                        cfg=cfg,
                        return_diagnostics=True,
                    )
                except Exception as e:
                    _ui(f"  主库搜索失败：{e}")
            if not results:
                _ui("  无结果")
            else:
                if diagnostics.get("vector_degraded"):
                    _ui("  提示：向量检索不可用，已降级为关键词检索。")
                for i, r in enumerate(results, 1):
                    score = r.get("score", 0.0)
                    _print_search_result(i, r, extra=f"{_format_match_tag(r.get('match', '?'))} {score:.3f}")
            _ui()

        elif scope.startswith("explore:"):
            explore_name = scope[len("explore:") :]
            from scholaraio.stores.explore import validate_explore_name

            if explore_name != "*" and not validate_explore_name(explore_name):
                _ui(f"  无效的 explore 库名 '{explore_name}'：不能为空，且不能包含路径分隔符或 '..'")
                _ui()
                continue
            if explore_name == "*":
                from scholaraio.stores.explore import list_explore_libs

                names = list_explore_libs(cfg)
                if not names:
                    _ui("── [explore: *] ──")
                    _ui("  暂无 explore 库，请先运行 scholaraio explore fetch --name <名称>")
                    _ui()
            else:
                names = [explore_name]

            for name in names:
                _ui(f"── [explore: {name}] ──")
                from scholaraio.stores.explore import explore_db_path, explore_unified_search

                db = explore_db_path(name, cfg)
                if not db.exists():
                    _ui(f"  explore 库 {name} 不存在或未建索引（explore.db 缺失）")
                    _ui()
                    continue
                try:
                    results = explore_unified_search(name, query, top_k=top_k, cfg=cfg)
                except Exception as e:
                    _ui(f"  搜索失败: {e}")
                    _ui()
                    continue
                if not results:
                    _ui("  无结果")
                else:
                    for i, r in enumerate(results, 1):
                        authors = r.get("authors", [])
                        first = authors[0] if authors else "?"
                        score = r.get("score", 0.0)
                        _ui(f"  [{i}] [{r.get('year', '?')}] {r.get('title', '')}")
                        _ui(f"       {first} | 分数: {score:.3f}")
                        _ui()

        elif scope == "arxiv":
            _ui("── [arXiv] ──")
            arxiv_results = _search_arxiv_from_cli(query, top_k)
            if not arxiv_results:
                _ui("  arXiv 不可用或无结果")
            else:
                arxiv_dois = [r["doi"].lower() for r in arxiv_results if r.get("doi")]
                arxiv_ids = [r.get("arxiv_id", "") for r in arxiv_results if r.get("arxiv_id")]
                in_lib_dois = _query_dois_for_set_from_cli(cfg, arxiv_dois)
                in_lib_arxiv_ids = _query_arxiv_ids_for_set_from_cli(cfg, arxiv_ids)
                for i, r in enumerate(arxiv_results, 1):
                    from scholaraio.providers.arxiv import normalize_arxiv_ref

                    authors = r.get("authors", [])
                    first = (authors[0] if authors else "?") + (" et al." if len(authors) > 1 else "")
                    doi = r.get("doi", "")
                    arxiv_id = r.get("arxiv_id", "")
                    normalized_arxiv_id = normalize_arxiv_ref(arxiv_id)
                    in_lib = bool(
                        (doi and doi.lower() in in_lib_dois)
                        or (normalized_arxiv_id and normalized_arxiv_id in in_lib_arxiv_ids)
                    )
                    status = "  [已入库]" if in_lib else ""
                    _ui(f"  [{i}] [{r.get('year', '?')}] {r.get('title', '')}{status}")
                    _ui(f"       {first} | arxiv:{arxiv_id}" + (f" | doi:{doi}" if doi else ""))
                    _ui()

        elif scope == "proceedings":
            _ui("── [论文集] ──")
            from scholaraio.services.index import search_proceedings

            db = cfg.proceedings_dir / "proceedings.db"
            if not db.exists():
                _ui("  proceedings 索引不存在，请先导入论文集")
                results = []
            else:
                try:
                    results = search_proceedings(query, db, top_k=top_k)
                except Exception as e:
                    _ui(f"  proceedings 搜索失败：{e}")
                    results = []
            if not results:
                _ui("  无结果")
            else:
                for i, r in enumerate(results, 1):
                    extra = f"proceedings:{r.get('proceeding_title', r.get('proceeding_dir', '?'))}"
                    _print_search_result(i, r, extra=extra)
            _ui()

        else:
            _ui(f"  未知 scope: {scope}，支持: main / proceedings / explore:NAME / explore:* / arxiv")
