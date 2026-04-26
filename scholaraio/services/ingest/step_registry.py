"""Ingest pipeline step registry and presets."""

from __future__ import annotations

from scholaraio.services.ingest import inbox_steps, steps
from scholaraio.services.ingest.types import StepDef

STEPS: dict[str, StepDef] = {
    "office_convert": StepDef(
        fn=inbox_steps.step_office_convert,
        scope="inbox",
        desc="Office 文档（DOCX/XLSX/PPTX）→ Markdown（MarkItDown）",
    ),
    "mineru": StepDef(fn=inbox_steps.step_mineru, scope="inbox", desc="PDF → Markdown（MinerU）"),
    "extract": StepDef(fn=inbox_steps.step_extract, scope="inbox", desc="Markdown → 元数据提取"),
    "extract_doc": StepDef(fn=inbox_steps.step_extract_doc, scope="inbox", desc="文档 → LLM 元数据提取"),
    "dedup": StepDef(fn=inbox_steps.step_dedup, scope="inbox", desc="API 查询 + DOI 去重"),
    "ingest": StepDef(fn=inbox_steps.step_ingest, scope="inbox", desc="写入 configured papers library"),
    "toc": StepDef(fn=steps.step_toc, scope="papers", desc="LLM 提取 TOC 写入 JSON"),
    "l3": StepDef(fn=steps.step_l3, scope="papers", desc="LLM 提取结论写入 JSON"),
    "translate": StepDef(fn=steps.step_translate, scope="papers", desc="翻译论文 Markdown 到目标语言"),
    "refetch": StepDef(fn=steps.step_refetch, scope="papers", desc="重新查询 API 补全引用量等字段"),
    "embed": StepDef(fn=steps.step_embed, scope="global", desc="生成语义向量写入 index.db"),
    "index": StepDef(fn=steps.step_index, scope="global", desc="更新 SQLite FTS5 索引"),
}

# Document inbox uses a different step sequence (no DOI dedup).
# office_convert runs before mineru; for PDF entries it is a no-op (office_path not set).
DOC_INBOX_STEPS = ["office_convert", "mineru", "extract_doc", "ingest"]

# Office formats scanned in any inbox when office_convert is in the step list.
# Regular inbox presets don't include office_convert, so Office files there are ignored.
OFFICE_EXTENSIONS = (".docx", ".xlsx", ".pptx")

PRESETS: dict[str, list[str]] = {
    "full": ["mineru", "extract", "dedup", "ingest", "toc", "l3", "embed", "index"],
    "ingest": ["mineru", "extract", "dedup", "ingest", "embed", "index"],
    "enrich": ["toc", "l3", "embed", "index"],
    "reindex": ["embed", "index"],
}
