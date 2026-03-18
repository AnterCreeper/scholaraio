---
name: show
description: View paper content at different detail levels. L1 (metadata), L2 (abstract), L3 (conclusion), L4 (full text). Use when the user wants to read a paper, see its abstract, conclusion, or full content.
version: 1.0.0
author: ZimoLiao/scholaraio
license: MIT
tags: ["academic", "papers", "reading", "content"]
---
# 查看论文内容

按分层结构查看指定论文的内容。支持 L1（元数据）、L2（摘要）、L3（结论）、L4（全文）四个层次。

## 执行逻辑

1. 解析用户输入，提取：
   - **paper-id**：论文标识符（目录名 / UUID / DOI 均可）
   - **layer**：查看层次（1-4），默认 `--layer 2`（输出包含 L1 元数据 + L2 摘要）

2. 如果用户不确定论文 ID，先用 `/search` 帮用户找到目标论文。

3. 执行查看命令：

```bash
scholaraio show "<paper-id>" --layer <N>
```

4. 将内容格式化后展示给用户。对于 L4 全文，如果内容过长，先展示摘要并询问用户是否需要完整内容。

## 层次说明

| 层 | 内容 | 说明 |
|----|------|------|
| L1 | 元数据 | title, authors, year, journal, doi |
| L2 | 摘要 | abstract |
| L3 | 结论 | conclusion（需先运行 enrich-l3） |
| L4 | 全文 | 完整 markdown |

## 示例

用户说："看一下 Smith-2023-TransformerSurvey 这篇的摘要"
→ 执行 `show "Smith-2023-TransformerSurvey" --layer 2`

用户说："给我看 Zhang-2024-LLM 的全文"
→ 执行 `show "Zhang-2024-LLM" --layer 4`

用户说："这篇论文的结论是什么"（上下文中已有论文 ID）
→ 执行 `show "<paper-id>" --layer 3`
