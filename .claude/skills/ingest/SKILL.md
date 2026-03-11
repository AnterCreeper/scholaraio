---
name: ingest
description: Ingest papers from inbox into the knowledge base. Runs the pipeline to convert PDFs via MinerU, extract metadata, deduplicate by DOI, and build indexes. Use when the user has new papers to process, wants to run the pipeline, or rebuild indexes.
---

# 入库论文

将 inbox 中的 PDF 论文处理入库，或运行完整的处理流水线。

## 执行逻辑

1. 根据用户意图选择预设：
   - **入库新论文**（默认）：使用 `ingest` 预设
   - **完整处理**：使用 `full` 预设（入库 + 内容富化 + 重建索引）
   - **仅重建索引**：使用 `reindex` 预设
   - **仅内容富化**：使用 `enrich` 预设

2. 执行流水线命令：

```bash
scholaraio pipeline <preset>
```

可用预设：`full` | `ingest` | `enrich` | `reindex`

3. pipeline 会依次处理两个 inbox 目录：
   - `data/inbox/` — 普通论文（有 DOI 才入库，无 DOI 且非 thesis 转 pending）
   - `data/inbox-thesis/` — 学位论文（跳过 DOI 去重，自动标记 thesis）

4. 无 DOI 论文的处理逻辑：
   - 来自 `data/inbox-thesis/` → 直接标记为 thesis 并入库
   - 来自 `data/inbox/` → LLM 分析判断是否 thesis
     - 是 thesis → 标记并入库
     - 不是 thesis → 转入 `data/pending/` 待人工确认

5. 展示处理结果摘要。

## 示例

用户说："我放了几篇新论文到 inbox，帮我入库"
→ 执行 `pipeline ingest`

用户说："把新论文全部处理完，包括提取目录和结论"
→ 执行 `pipeline full`

用户说："重新建索引"
→ 执行 `pipeline reindex`
