"""Rendered web-link ingest CLI command handler."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from scholaraio.core.log import redirect_console_ui


def _ui(msg: str = "") -> None:
    try:
        from scholaraio.interfaces.cli import compat as cli_mod
    except ImportError:
        from scholaraio.core.log import ui as log_ui

        log_ui(msg)
        return
    cli_mod.ui(msg)


def _sleep(seconds: float) -> None:
    try:
        from scholaraio.interfaces.cli import compat as cli_mod
    except ImportError:
        import time as time_mod

        time_mod.sleep(seconds)
        return
    cli_mod.time.sleep(seconds)


def _slugify_ingest_link_title(title: str, fallback_url: str, index: int) -> str:
    raw = (title or "").strip() or _fallback_ingest_link_title(fallback_url, index)
    slug = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
    slug = slug[:240].strip("-")
    return slug or f"link-{index:02d}"


def _fallback_ingest_link_title(source_url: str, index: int) -> str:
    parsed = urlparse(source_url)
    return Path(parsed.path).stem or parsed.netloc or f"link-{index:02d}"


def _render_ingest_link_markdown(title: str, source_url: str, body: str) -> str:
    parts = [
        f"# {title}",
        "",
        f"Source URL: {source_url}",
        "",
    ]
    body_text = (body or "").strip()
    if body_text:
        parts.append(body_text)
    return "\n".join(parts).rstrip() + "\n"


def _webextract_for_ingest_link(
    url: str,
    *,
    pdf: bool | None,
    extractor,
    max_attempts: int = 3,
    backoff_base: float = 1.0,
) -> dict:
    last_result: dict | None = None
    last_error = ""
    last_source_url = url

    for attempt in range(1, max_attempts + 1):
        try:
            result = extractor(url, pdf=pdf)
        except Exception as exc:
            last_result = None
            last_error = str(exc)
            last_source_url = url
        else:
            result = result or {}
            source_url = (result.get("url") or url).strip()
            error = (result.get("error") or "").strip()
            text = result.get("text") or ""
            last_result = result
            last_error = error
            last_source_url = source_url
            if not error or text.strip():
                if attempt > 1:
                    _ui(f"链接提取重试后成功: {source_url} (第 {attempt} 次)")
                return result

        if attempt >= max_attempts:
            break
        wait = backoff_base * float(2 ** (attempt - 1))
        _ui(f"链接提取失败，准备重试: {last_source_url} ({last_error})，{wait:.1f}s 后重试")
        _sleep(wait)

    if last_result is not None:
        return last_result
    return {
        "url": last_source_url,
        "title": "",
        "text": "",
        "html": "",
        "error": last_error or "unknown extraction error",
    }


def cmd_ingest_link(args: argparse.Namespace, cfg) -> None:
    from scholaraio.providers import webtools
    from scholaraio.services.ingest.pipeline import run_pipeline

    urls = [u.strip() for u in args.urls if u.strip()]
    if not urls:
        _ui("请至少提供一个 URL")
        return

    if args.dry_run:
        _ui(f"[dry-run] 将抓取 {len(urls)} 个链接并直接入库")
        for url in urls:
            _ui(f"  - {url}")
        return

    step_names = ["extract_doc", "ingest"]
    if not args.no_index:
        step_names.extend(["embed", "index"])

    summaries: list[dict[str, str]] = []
    output_mode = redirect_console_ui(sys.stderr) if args.json else nullcontext()

    def extract_for_ingest(url: str, *, pdf: bool | None = None) -> dict:
        return webtools.extract_web(url, pdf=pdf, cfg=cfg)

    try:
        with output_mode, tempfile.TemporaryDirectory(prefix="scholaraio_link_") as tmpdir:
            _ui(f"开始直接入库链接: {len(urls)} 个")
            tmp_root = Path(tmpdir)
            inbox_dir = tmp_root / "inbox"
            inbox_dir.mkdir(parents=True, exist_ok=True)
            doc_inbox_dir = Path(tmpdir) / "inbox-doc"
            doc_inbox_dir.mkdir(parents=True, exist_ok=True)

            for idx, url in enumerate(urls, start=1):
                pdf_mode = True if args.pdf else None
                result = _webextract_for_ingest_link(url, pdf=pdf_mode, extractor=extract_for_ingest)
                source_url = (result.get("url") or url).strip()
                error = (result.get("error") or "").strip()
                text = result.get("text") or ""
                if error and not text.strip():
                    _ui(f"链接提取失败，已跳过: {source_url} ({error})")
                    continue
                if error:
                    _ui(f"链接提取有警告，继续入库: {source_url} ({error})")

                title = (result.get("title") or "").strip() or _fallback_ingest_link_title(source_url, idx)
                slug = _slugify_ingest_link_title(title, source_url, idx)
                md_name = f"{idx:02d}-{slug}.md"
                md_path = doc_inbox_dir / md_name
                sidecar_path = md_path.with_suffix(".json")

                md_text = _render_ingest_link_markdown(title, source_url, text)
                md_path.write_text(md_text, encoding="utf-8")

                sidecar = {
                    "title": title,
                    "source_file": md_name,
                    "source_url": source_url,
                    "source_type": "web",
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                    "extraction_method": "qt-web-extractor",
                }
                sidecar_path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

                summaries.append(
                    {
                        "url": source_url,
                        "title": title,
                        "markdown_file": md_name,
                    }
                )
                _ui(f"已抓取: {title[:80]}")

            if not summaries:
                _ui("没有可入库的链接内容")
                return

            run_pipeline(
                step_names,
                cfg,
                {
                    "inbox_dir": inbox_dir,
                    "doc_inbox_dir": doc_inbox_dir,
                    "force": args.force,
                    "include_aux_inboxes": False,
                },
            )
    except Exception as e:
        _ui(f"链接抓取或入库失败: {e}")
        return

    if args.json:
        sys.stdout.write(json.dumps(summaries, ensure_ascii=False, indent=2) + "\n")
