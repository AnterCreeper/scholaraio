---
name: export
description: Export papers from the knowledge base to standard citation formats (BibTeX, RIS, Markdown reference list) or export any Markdown content as a Word DOCX file. Supports exporting all papers, specific papers, or filtered by year/journal. Use when the user needs citation files, wants to import into Zotero/Endnote/Mendeley, needs a reference list for writing, or wants to share a document as Word.
---

# 导出论文与文档

将本地论文库导出为标准引用格式，或将任意 Markdown 内容转换为 Word 文件。

## 支持的导出格式

| 格式 | 命令 | 用途 |
|------|------|------|
| BibTeX `.bib` | `export bibtex` | LaTeX 写作引用 |
| RIS `.ris` | `export ris` | Zotero / Endnote / Mendeley 导入 |
| Markdown 文献列表 | `export markdown` | 直接粘贴到文档、综述草稿 |
| Word DOCX | `export docx` | 分享给同事、导师，任意 Markdown 内容 |

---

## BibTeX 导出

```bash
# 导出全部论文到屏幕
scholaraio export bibtex --all

# 导出全部论文到文件
scholaraio export bibtex --all -o workspace/library.bib

# 导出指定论文
scholaraio export bibtex "Smith-2023-Turbulence" "Doe-2024-DNS"

# 按年份筛选导出
scholaraio export bibtex --all --year 2020-2024 -o workspace/recent.bib

# 按期刊筛选导出
scholaraio export bibtex --all --journal "Fluid Mechanics" -o workspace/jfm.bib
```

## RIS 导出（Zotero / Endnote / Mendeley）

```bash
# 导出全部论文
scholaraio export ris --all -o workspace/library.ris

# 导出指定论文
scholaraio export ris "Smith-2023-Turbulence" "Doe-2024-DNS" -o workspace/refs.ris

# 按年份筛选
scholaraio export ris --all --year 2022-2024 -o workspace/recent.ris
```

导出后可直接在 Zotero 中：File → Import → 选择 .ris 文件

## Markdown 文献列表导出

```bash
# 导出全部论文（有序列表，APA 风格）
scholaraio export markdown --all

# 导出到文件
scholaraio export markdown --all -o workspace/references.md

# 无序列表
scholaraio export markdown --all --bullet

# 按年份筛选
scholaraio export markdown --all --year 2020-2024 -o workspace/recent_refs.md
```

示例输出：
```
1. Smith, J., & Zhang, L. (2023). Deep Learning for Fluid Dynamics. *Nature*, *10*(2), 100-110. https://doi.org/10.1038/xxx
2. Doe, A. et al. (2024). Turbulence Modeling with Transformers. *JFM*, *820*, 1-30. https://doi.org/10.1017/xxx
```

## DOCX 导出（任意 Markdown → Word）

```bash
# 将 Markdown 文件导出为 Word
scholaraio export docx --input workspace/literature_review.md --output workspace/review.docx

# 添加文档标题
scholaraio export docx --input workspace/report.md --output workspace/report.docx --title "研究报告"

# 从 stdin 读取（配合 Claude 生成内容直接导出）
echo "# 标题\n内容..." | scholaraio export docx --output workspace/doc.docx
```

支持的 Markdown 元素：标题（H1-H9）、段落、**粗体**、*斜体*、列表、表格、代码块、引用块

**依赖**：需安装 `pip install python-docx`

---

## 示例

用户说："把我所有论文导出成 BibTeX"
→ 执行 `export bibtex --all`

用户说："导出成 RIS，我要导入 Zotero"
→ 执行 `export ris --all -o workspace/library.ris`

用户说："给我一份 Markdown 格式的参考文献列表"
→ 执行 `export markdown --all`

用户说："把这篇文献综述导出成 Word 文件"
→ 执行 `export docx --input workspace/review.md --output workspace/review.docx`

用户说："我写了一份报告，帮我转成 Word"
→ 执行 `export docx --input <文件路径> --output workspace/report.docx`

用户说："导出 DNS 相关的论文引用"
→ 先用 `usearch "DNS"` 搜索，从结果中提取目录名，再 `export bibtex <dir1> <dir2> ...`
