---
name: publish
version: 1.1.0
description: 将最终经用户审计的文章归档到 published/ 目录，并生成可部署的 GitHub Pages 站点
tier: utility
destructive: true
---

# 文章发布归档

当用户明确表示文章已完成并经过审计，需要生成最终归档包时，执行本流程。

## 架构分离原则

为了支持 ScholarAIO 上游化，发布流程拆分为三层：

1. **`scholaraio/` 上游仓库**：只包含站点**生成器代码**（`scholaraio/publish_site/`）
2. **`published/` 用户私有数据**：已归档的论文（PDF、TeX 源、插图、ZIP）
3. **用户独立的 GitHub Pages 仓库**（如 `AnterCreeper/generated-report`）：实际部署的静态站点

```
scholaraio/                    ← 上游仓库
├── scholaraio/publish_site/   ← 站点生成器
└── published/                 ← 用户私有论文（.gitignore）

generated-report/              ← 用户独立仓库（GitHub Pages 源）
├── index.html
├── css/
├── js/
└── assets/papers/
```

## 归档结构

在 `published/` 目录下创建子文件夹，命名规则为：
```
published/<YYYY-MM-DD>-<文章标题简写>/
```

文件夹内必须包含：
- **TeX 源文件**：主 `.tex` 以及所有通过 `\input{}` 引入的副 `.tex` 文件
- **images/** 插图文件夹：论文中引用的外部图片（即使为纯 TikZ 插图，也应创建空 `images` 文件夹或放置说明文件）
- **misc/** 杂项文件夹（可选）：补充材料，如 `.bib` 参考文献库、大纲、demo 脚本、Inkscape SVG 辅助文件、数据集说明等
- **最终 PDF**：编译生成的 PDF 文件
- **metadata.json**：记录该成果的元数据

## metadata.json 字段规范

```json
{
  "title": "文章完整标题",
  "date": "YYYY-MM-DD",
  "keywords": ["关键词1", "关键词2", "..."],
  "subject": "主题/领域",
  "pdf_filename": "xxx.pdf",
  "tex_files": ["main.tex", "chapter-xxx.tex"],
  "images_dir": "images",
  "misc_dir": "misc",
  "authors": ["作者", "Claude (AI Assistant)"],
  "note": "Final audited deliverable archived."
}
```

## 执行步骤

1. 确认当前 workspace 下已存在最终编译成功的 PDF 和对应的 `.tex` 源文件。
2. **（强烈推荐）在归档前执行备份**：运行 `/backup` 或 `scholaraio backup` 确保数据安全，尤其当这是重要交付物时。
3. 计算归档文件夹名称：`published/<YYYY-MM-DD>-<文章标题>/`。标题中的空格可保留或替换为连字符/下划线，中文标题直接保留。**注意：文件夹名请勿包含中文冒号（：）、英文冒号（:）、问号（?）、星号（*）、尖括号（<>）等特殊字符**，以免影响文件系统和 Git 的兼容性。
4. 创建目录结构：
   ```bash
   mkdir -p "published/<YYYY-MM-DD>-<标题>/images"
   mkdir -p "published/<YYYY-MM-DD>-<标题>/misc"
   ```
5. 复制所有相关文件：
   - 主 tex + 副 tex
   - 最终 PDF
   - **插图过滤复制**：扫描 `.tex` 源文件中所有 `\includegraphics{}` 引用的图片路径，仅将这些被引用的图片复制到 `images/` 子目录；未被引用的图片不复制，但保留在源 workspace 中不删除
   - **杂项文件**：将 `.bib`、大纲、demo 脚本、SVG 辅助文件等补充材料复制到 `misc/` 子目录
6. 写入 `metadata.json`，字段严格按规范填写。
7. 向用户报告归档路径和文件清单。

## 生成展示站点

站点生成器已经上游化到 `scholaraio publish-site` CLI 命令，不再依赖 `published-site/generate.py`。

### 配置默认输出目录

可在 `config.yaml` 中设置默认站点输出目录，省去每次传入 `--out-dir`：

```yaml
publish:
  site_output_dir: "~/generated-report"
```

### 默认行为：自包含复制模式

```bash
scholaraio publish-site
```

默认会将所有 PDF 和 source ZIP **复制**到输出目录的 `assets/papers/` 下，生成一个自包含的站点，可直接推送到 GitHub Pages。

### 本地开发模式（符号链接，不复制大文件）

如需节省磁盘空间，可显式使用符号链接模式：

```bash
scholaraio publish-site --symlink
```

### 部署到 GitHub Pages

1. 确保 `generated-report` 是一个独立的 Git 仓库（用于 GitHub Pages）
2. 用 `--copy-assets` 生成站点到该目录
3. commit 并 push：

```bash
cd ~/generated-report
git add .
git commit -m "Update site with new paper: <标题>"
# 执行前请确认：git push origin main
```

### 生成器行为

`scholaraio publish-site` 会：
1. 扫描 `published/*/metadata.json` 读取最新元数据
2. 重新生成 `index.html`、`css/style.css`、`js/main.js`
3. 为每篇论文在 `published/<dir>/` 下打包 source ZIP（包含 `.tex`、插图、`misc`、`metadata.json`）
4. 根据 `--copy-assets` / `--symlink` 模式处理 `assets/papers/`

## 注意事项

- 仅应在用户明确同意“已完成/通过审计”后执行归档，避免将草稿状态混入 published。
- 若存在多版本迭代，每次归档应使用新的日期前缀，保留历史版本。
- 不删除源 workspace 中的原始文件，published 为独立的最终交付副本。
- **每次归档后务必运行 `scholaraio publish-site` 更新展示站点**，否则新论文不会出现在 GitHub Pages 上。
- `published-site/` 目录已从主仓库移除并加入 `.gitignore`，它现在属于用户独立管理的 GitHub Pages 仓库。
