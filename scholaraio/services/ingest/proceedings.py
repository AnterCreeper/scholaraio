"""Proceedings routing helpers for ingest."""

from __future__ import annotations

from scholaraio.core.log import ui
from scholaraio.services.ingest.cleanup import cleanup_inbox
from scholaraio.services.ingest.paths import proceedings_dir
from scholaraio.services.ingest.types import InboxCtx


def ingest_proceedings_ctx(ctx: InboxCtx, *, force: bool) -> bool:
    """Route a markdown entry into the proceedings library."""
    from scholaraio.services.ingest.proceedings_volume import ingest_proceedings_markdown

    if not ctx.md_path or not ctx.md_path.exists():
        return False

    dry_run = bool(ctx.opts.get("dry_run", False))
    proceedings_root = proceedings_dir(ctx.cfg)
    source_name = ctx.pdf_path.name if ctx.pdf_path else ctx.md_path.name
    if dry_run:
        ctx.status = "skipped"
        ui(f"检测为论文集；dry-run 模式下跳过写入 {proceedings_root}。")
        ui("预览模式不会生成 proceeding.md 和 split_candidates.json。")
        ui("退出 dry-run 后重新执行，可生成待审阅的论文集拆分文件。")
        return True

    ingest_proceedings_markdown(proceedings_root, ctx.md_path, source_name=source_name)
    cleanup_inbox(ctx.pdf_path, ctx.md_path, dry_run=dry_run)
    ctx.status = "ingested"
    ui("检测为论文集，已生成 proceeding.md 和 split_candidates.json。")
    ui("等待 agent 审阅 split_candidates.json 并生成 split_plan.json，然后再执行后续拆分入库。")
    return True
