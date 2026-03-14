---
name: ingest
description: Ingest papers and documents from inbox into the knowledge base. Runs the pipeline to convert PDFs via MinerU (auto-splits long PDFs), Office files (DOCX/XLSX/PPTX) via MarkItDown, extract metadata, deduplicate by DOI, and build indexes. Supports three inboxes - regular papers, theses, and general documents. Use when the user has new papers or documents to process, wants to run the pipeline, or rebuild indexes.
---

# 入库文档

将 inbox 中的 PDF、Office 文档（DOCX/XLSX/PPTX）或 Markdown 文件处理入库。

## 支持的文件格式

| 格式 | 放入目录 | 处理方式 |
|------|----------|----------|
| `.pdf` | `data/inbox/` 或 `data/inbox-doc/` | MinerU 转 Markdown |
| `.docx` `.xlsx` `.pptx` | `data/inbox-doc/` | MarkItDown 转 Markdown |
| `.md` | 任意 inbox | 直接入库（跳过转换） |

## 执行逻辑

1. 根据用户意图选择预设：
   - **入库新文档**（默认）：使用 `ingest` 预设
   - **完整处理**：使用 `full` 预设（入库 + 内容富化 + 重建索引）
   - **仅重建索引**：使用 `reindex` 预设
   - **仅内容富化**：使用 `enrich` 预设

2. 执行流水线命令：

```bash
scholaraio pipeline <preset>
```

可用预设：`full` | `ingest` | `enrich` | `reindex`

3. pipeline 会依次处理三个 inbox 目录：
   - `data/inbox/` — 普通论文（有 DOI 才入库，无 DOI 且非 thesis 转 pending）
   - `data/inbox-thesis/` — 学位论文（跳过 DOI 去重，自动标记 thesis）
   - `data/inbox-doc/` — 非论文文档（技术报告、讲义、Word/Excel/PPT、标准文档等，跳过 DOI 去重，LLM 生成标题/摘要）

4. Office 文件处理流程（`data/inbox-doc/` 中的 DOCX/XLSX/PPTX）：
   - `step_office_convert`（MarkItDown）→ 转换为 `<stem>.md`
   - `step_extract_doc`（LLM 生成标题/摘要）
   - `step_ingest`（写入 `data/papers/`）
   - **依赖**：需安装 `pip install 'markitdown[docx,pptx,xlsx]'`

5. 无 DOI 论文的处理逻辑：
   - 来自 `data/inbox-thesis/` → 直接标记为 thesis 并入库
   - 来自 `data/inbox-doc/` → 标记为 document 类型，LLM 生成标题和摘要后入库
   - 来自 `data/inbox/` → LLM 分析判断是否 thesis
     - 是 thesis → 标记并入库
     - 不是 thesis → 转入 `data/pending/` 待人工确认

6. 超长 PDF（>100 页）自动切分为短 PDF 分段转换后合并。

## 示例

用户说："我放了几篇新论文到 inbox，帮我入库"
→ 执行 `pipeline ingest`

用户说："把新论文全部处理完，包括提取目录和结论"
→ 执行 `pipeline full`

用户说："我有几份技术报告放在 inbox-doc 里了"
→ 执行 `pipeline ingest`（pipeline 自动处理三个 inbox 目录）

用户说："我把一个 Word 文档放进 inbox-doc 了"
→ 执行 `pipeline ingest`（自动用 MarkItDown 转换 DOCX）

用户说："重新建索引"
→ 执行 `pipeline reindex`
