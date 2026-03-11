---
name: import
description: Import papers from external reference managers (Endnote XML/RIS, Zotero Web API or local SQLite). Handles PDF matching, MinerU conversion, metadata enrichment, and index updates. Use when the user wants to import their existing library from Zotero, Endnote, or attach a PDF to an existing paper.
---

# 导入外部文献管理工具数据

## Endnote 导入

支持 Endnote 导出的 XML 和 RIS 格式文件。

```bash
# 完整导入：元数据 + PDF 匹配 + MinerU 转换 + embed + index
scholaraio import-endnote <file.xml>

# 多文件导入
scholaraio import-endnote file1.xml file2.ris

# 仅导入元数据和 PDF，跳过 MinerU 转换
scholaraio import-endnote <file.xml> --no-convert

# 预览模式
scholaraio import-endnote <file.xml> --dry-run

# 离线模式
scholaraio import-endnote <file.xml> --no-api
```

### PDF 自动匹配

对 Endnote XML 文件，自动解析 `internal-pdf://` 链接，从 `<library>.Data/PDF/` 目录匹配 PDF：
- 多个 PDF 时自动排除 SI/补充材料
- 默认通过 MinerU 转换为 paper.md

## Zotero 导入

支持 Web API 和本地 SQLite 两种模式。

### Web API 模式

```bash
# 列出 collections
scholaraio import-zotero --api-key KEY --library-id ID --list-collections

# 完整导入
scholaraio import-zotero --api-key KEY --library-id ID

# 仅导入指定 collection
scholaraio import-zotero --api-key KEY --library-id ID --collection COLLECTION_KEY

# 导入后将 collections 创建为工作区
scholaraio import-zotero --api-key KEY --library-id ID --import-collections
```

### 本地 SQLite 模式

```bash
scholaraio import-zotero --local /path/to/zotero.sqlite
```

### 配置文件（可选）

在 `config.local.yaml` 中配置 Zotero 凭据：

```yaml
zotero:
  api_key: "your-zotero-api-key"
  library_id: "your-library-id"
```

## 补充 PDF

```bash
scholaraio attach-pdf <paper-id> <path/to/paper.pdf>
```

自动调用 MinerU 转换 PDF → markdown，补全缺失的 abstract，增量更新 embed + index。
