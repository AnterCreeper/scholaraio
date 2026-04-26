"""Attach-PDF CLI command handler."""

from __future__ import annotations

import argparse
import shutil
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


def _resolve_paper(paper_id: str, cfg) -> Path:
    from scholaraio.interfaces.cli import compat as cli_mod

    return cli_mod._resolve_paper(paper_id, cfg)


def _batch_convert_pdfs(cfg, *, enrich: bool = False) -> None:
    """Convert all unprocessed PDFs in papers_dir to paper.md via MinerU."""
    from scholaraio.services.ingest.pipeline import batch_convert_pdfs

    batch_convert_pdfs(cfg, enrich=enrich)


def cmd_attach_pdf(args: argparse.Namespace, cfg) -> None:
    paper_d = _resolve_paper(args.paper_id, cfg)
    pdf_path = Path(args.pdf_path)

    if not pdf_path.exists():
        _ui(f"错误：PDF 文件不存在: {pdf_path}")
        sys.exit(1)

    existing_md = paper_d / "paper.md"
    dry_run = getattr(args, "dry_run", False)

    if dry_run:
        _ui(f"[dry-run] 论文目录: {paper_d}")
        _ui(f"[dry-run] PDF 来源: {pdf_path}")
        _ui(f"[dry-run] 目标 paper.md: {paper_d / 'paper.md'}")
        if existing_md.exists():
            _ui("[dry-run] 警告：已有 paper.md，实际运行时将被覆盖")
        _ui("[dry-run] 将执行: MinerU 转换 → 摘要补全 → 重新嵌入 → 重建索引")
        _ui("[dry-run] 如确认无误，去掉 --dry-run 参数再运行")
        return

    if existing_md.exists():
        _ui(f"警告：{paper_d.name} 已有 paper.md，将被覆盖")

    # Copy PDF to paper directory.
    dest_pdf = paper_d / pdf_path.name
    shutil.copy2(str(pdf_path), str(dest_pdf))
    _ui(f"已复制 PDF: {dest_pdf.name}")

    # Convert PDF -> markdown via MinerU.
    from scholaraio.providers.mineru import (
        ConvertOptions,
        _convert_long_pdf,
        _convert_long_pdf_cloud,
        _get_pdf_page_count,
        _plan_cloud_chunking,
        check_server,
        convert_pdf,
        is_pdf_validation_error,
        validate_pdf_for_mineru,
    )
    from scholaraio.providers.pdf_fallback import (
        convert_pdf_with_fallback,
        preferred_parser_order,
        prefers_fallback_parser,
    )

    mineru_opts = ConvertOptions(
        api_url=cfg.ingest.mineru_endpoint,
        output_dir=paper_d,
        backend=cfg.ingest.mineru_backend_local,
        cloud_model_version=cfg.ingest.mineru_model_version_cloud,
        lang=cfg.ingest.mineru_lang,
        parse_method=cfg.ingest.mineru_parse_method,
        formula_enable=cfg.ingest.mineru_enable_formula,
        table_enable=cfg.ingest.mineru_enable_table,
        poll_timeout=cfg.ingest.mineru_poll_timeout,
    )

    result = None
    preferred_done = False
    fallback_auto_detect = getattr(cfg.ingest, "pdf_fallback_auto_detect", True)
    fallback_order = preferred_parser_order(
        getattr(cfg.ingest, "pdf_preferred_parser", "mineru"),
        getattr(cfg.ingest, "pdf_fallback_order", None),
        auto_detect=fallback_auto_detect,
    )
    local_chunk_limit = getattr(cfg.ingest, "chunk_page_limit", 100)

    def _ensure_valid_for_mineru() -> None:
        validation = validate_pdf_for_mineru(dest_pdf)
        if not validation.ok:
            _ui(f"PDF 校验失败: {validation.error or 'PDF validation failed'}")
            sys.exit(1)

    if prefers_fallback_parser(getattr(cfg.ingest, "pdf_preferred_parser", "mineru")):
        ok, parser_name, fallback_err = convert_pdf_with_fallback(
            dest_pdf,
            existing_md,
            parser_order=fallback_order,
            auto_detect=fallback_auto_detect,
        )
        if not ok:
            _ui(f"首选解析器失败: {fallback_err}")
            sys.exit(1)
        _ui(f"已按配置优先使用 {parser_name} 生成 paper.md")
        preferred_done = True
    elif check_server(cfg.ingest.mineru_endpoint):
        _ensure_valid_for_mineru()
        page_count = _get_pdf_page_count(dest_pdf)
        if page_count > local_chunk_limit:
            _ui(f"检测到长 PDF（{page_count} 页，超过 {local_chunk_limit} 页限制），正在分片处理...")
            result = _convert_long_pdf(dest_pdf, mineru_opts, chunk_size=local_chunk_limit)
        else:
            result = convert_pdf(dest_pdf, mineru_opts)
    else:
        api_key = cfg.resolved_mineru_api_key()
        if not api_key:
            _ui("MinerU 不可达且无 MinerU token，改用 fallback 解析器")
        else:
            from scholaraio.providers.mineru import convert_pdf_cloud

            _ensure_valid_for_mineru()
            should_chunk, chunk_size, reason = _plan_cloud_chunking(
                dest_pdf,
                default_chunk_size=local_chunk_limit,
            )
            if should_chunk:
                _ui(f"检测到云端需分片 PDF（{reason}），正在分片处理...")
                try:
                    result = _convert_long_pdf_cloud(
                        dest_pdf,
                        mineru_opts,
                        api_key=api_key,
                        cloud_url=cfg.ingest.mineru_cloud_url,
                        chunk_size=chunk_size,
                    )
                except ImportError as exc:
                    result = None
                    _ui(f"云端分片依赖缺失，尝试 fallback：{exc}。可安装 scholaraio[pdf]")
                except Exception as exc:
                    result = None
                    _ui(f"云端分片失败，尝试 fallback：{exc}")
            else:
                result = convert_pdf_cloud(
                    dest_pdf,
                    mineru_opts,
                    api_key=api_key,
                    cloud_url=cfg.ingest.mineru_cloud_url,
                )

    if not preferred_done and (result is None or not result.success):
        err = result.error if result is not None else "MinerU unavailable"
        if is_pdf_validation_error(result):
            _ui(f"PDF 校验失败: {err}")
            sys.exit(1)
        _ui(f"MinerU 转换失败，尝试 fallback: {err}")
        ok, parser_name, fallback_err = convert_pdf_with_fallback(
            dest_pdf,
            existing_md,
            parser_order=fallback_order,
            auto_detect=fallback_auto_detect,
        )
        if not ok:
            _ui(f"fallback 解析失败: {fallback_err}")
            sys.exit(1)
        _ui(f"已降级使用 {parser_name} 生成 paper.md")
    elif result is not None:
        # Move/rename output to paper.md.
        if result.md_path and result.md_path != existing_md:
            md_src = result.md_path
            md_src_parent = md_src.parent
            if existing_md.exists():
                existing_md.unlink()
            shutil.move(str(md_src), str(existing_md))
            for images_src in [md_src.parent / "images", md_src.parent / f"{md_src.stem}_images"]:
                if images_src.is_dir():
                    target = paper_d / "images"
                    if images_src == target:
                        break
                    if target.exists():
                        shutil.rmtree(target)
                    shutil.move(str(images_src), str(target))
                    break
            if md_src_parent != paper_d and md_src_parent.is_dir() and not any(md_src_parent.iterdir()):
                md_src_parent.rmdir()

    # Clean up MinerU artifacts (keep images/).
    for pattern in ["*_layout.json", "*_content_list.json", "*_origin.pdf"]:
        for f in paper_d.glob(pattern):
            f.unlink(missing_ok=True)
    # Rename MinerU images dir if needed.
    for img_dir in paper_d.glob("*_images"):
        if img_dir.name != "images" and img_dir.is_dir():
            target = paper_d / "images"
            if target.exists():
                shutil.rmtree(target)
            img_dir.rename(target)

    # Clean up the copied PDF (we only need the markdown).
    if dest_pdf.exists() and dest_pdf.name != "paper.pdf":
        dest_pdf.unlink()

    _ui(f"paper.md 已生成: {paper_d.name}/")

    # Backfill abstract if missing.
    from scholaraio.stores.papers import read_meta, write_meta

    data = read_meta(paper_d)
    if not data.get("abstract"):
        from scholaraio.services.ingest_metadata import extract_abstract_from_md

        abstract = extract_abstract_from_md(existing_md, cfg)
        if abstract:
            data["abstract"] = abstract
            write_meta(paper_d, data)
            _ui(f"abstract 已补全 ({len(abstract)} chars)")

    # Incremental re-embed + re-index.
    from scholaraio.services.ingest.pipeline import step_embed, step_index

    step_embed(cfg.papers_dir, cfg, {"dry_run": False, "rebuild": False})
    step_index(cfg.papers_dir, cfg, {"dry_run": False, "rebuild": False})
