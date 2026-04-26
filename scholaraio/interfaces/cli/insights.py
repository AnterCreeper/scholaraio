"""Insights CLI command handler."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _workspace_root(cfg) -> Path:
    workspace_dir = getattr(cfg, "workspace_dir", None)
    if workspace_dir is not None:
        return Path(workspace_dir)
    return Path(getattr(cfg, "_root", Path.cwd())) / "workspace"


def _ui(msg: str = "") -> None:
    try:
        from scholaraio.interfaces.cli import compat as cli_mod
    except ImportError:
        from scholaraio.core.log import ui as log_ui

        log_ui(msg)
        return
    cli_mod.ui(msg)


def cmd_insights(args: argparse.Namespace, cfg) -> None:
    from scholaraio.services import insights
    from scholaraio.services.metrics import get_store

    ui = _ui
    store = get_store()
    if not store:
        ui("暂无足够数据（metrics 未初始化）")
        return

    days = args.days
    if days <= 0:
        ui("--days 必须为正整数")
        return
    since_dt = datetime.now(timezone.utc) - timedelta(days=days)
    since_iso = since_dt.isoformat()

    search_events = store.query(category="search", since=since_iso, limit=10000)
    read_events = store.query(category="read", since=since_iso, limit=10000)

    if not search_events and not read_events:
        ui(f"暂无足够数据（过去 {days} 天内无搜索或阅读记录）")
        return

    ui(f"=== 科研行为分析（过去 {days} 天）===\n")

    ui("【搜索热词前 10】")
    hot_keywords = insights.extract_hot_keywords(search_events, top_k=10)
    if hot_keywords:
        for word, cnt in hot_keywords:
            bar = "█" * min(cnt, 20)
            ui(f"  {word:<20s} {bar} ({cnt})")
    else:
        ui("  暂无搜索记录")
    ui()

    ui("【最常阅读论文前 10】")
    most_read = insights.aggregate_most_read_titles(read_events, cfg.papers_dir, top_k=10)
    if most_read:
        for rank, (title_key, cnt) in enumerate(most_read, 1):
            label = title_key[:60]
            ui(f"  {rank:2d}. [{cnt}次] {label}")
    else:
        ui("  暂无阅读记录")
    ui()

    ui("【阅读量趋势（按周）】")
    if read_events:
        week_counts = insights.build_weekly_read_trend(read_events)
        if week_counts:
            max_count = max(cnt for _, cnt in week_counts) or 1
            for week, cnt in week_counts:
                bar_len = round(cnt / max_count * 20)
                bar = "█" * bar_len
                ui(f"  {week}  {bar} {cnt}")
        else:
            ui("  暂无足够数据")
    else:
        ui("  暂无阅读记录")
    ui()

    ui("【推荐：你可能还没读过的邻近论文】")
    recent_since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    recent_reads = store.query(category="read", since=recent_since, limit=500)
    recent_paper_ids = insights.recent_unique_read_names(recent_reads, limit=5)

    if not recent_paper_ids:
        ui("  过去7天无阅读记录，无法推荐")
    else:
        try:
            recommendations = insights.recommend_unread_neighbors(store, cfg, recent_days=7, recent_limit=5, top_k=5)
            if recommendations:
                for rank, (_pid, label, score) in enumerate(recommendations, 1):
                    label = label[:60]
                    ui(f"  {rank}. {label}  (分数: {score:.3f})")
            else:
                ui("  未找到合适的邻近论文（可能向量索引未建立）")
        except ImportError:
            ui("  语义搜索不可用（需安装 embed 依赖）")
    ui()

    ui("【活跃工作区】")
    try:
        ws_root = _workspace_root(cfg)
        workspaces = insights.list_workspace_counts(ws_root)
        if workspaces:
            for ws_name, count in workspaces:
                ui(f"  {ws_name:<30s} {count} 篇论文")
        else:
            ui("  暂无工作区")
    except Exception:
        ui("  工作区信息不可用")
    ui()
