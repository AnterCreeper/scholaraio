---
name: skill-harness
description: ScholarAIO skill 系统的 harness 规范。定义 CLI 设计原则、skill 编写规则、自动化校验标准，确保一致性不依赖个人记忆。
version: 1.0.0
---

# ScholarAIO Skill Harness 规范

> **核心原则：在 CLI 层统一异常，而不是让 skill 去记忆特例。**

当发现 CLI 参数在不同命令间不一致时（如此前的 `--top` vs `--limit`），**优先修改 CLI 增加别名/统一参数名**，而不是让所有 skill 迁就历史遗留的命名。Skill 只应使用“规范名”（canonical name）。

---

## 1. CLI 边界统一原则（Canonical CLI）

### 1.1 分页/数量限制
- **规范名**：`--limit N`
- 所有涉及返回条数的命令必须支持 `--limit`
- 历史别名 `--top` 可保留作为向后兼容，但 skill 文档中**只允许写 `--limit`**
- 已统一命令清单：`search`, `usearch`, `vsearch`, `search-author`, `top-cited`, `topics`, `explore topics`, `explore search`, `ws search`, `ws add`, `fsearch`

### 1.2 工作区指定
- **规范名**：`--ws <名称>`
- 不存在 `-w` 等缩写别名，保持单一明确

### 1.3 输出格式
- **规范名**：`--format <fmt>`
- 常见值：`svg`, `drawio`, `mermaid`, `md`, `tex`, `pdf`

### 1.4 过滤参数
- 年份：`--year YYYY` 或 `--year START-END`
- 期刊：`--journal <名称>`
- 类型：`--type <类型>`

### 1.5 当 CLI 出现历史不一致时
1. 选择最直观、最通用的名称作为规范名（通常参考 explore fetch 或行业惯例）
2. 在 CLI argparse 中为其他命令增加同名参数（或别名）
3. 保留旧参数作为别名，避免破坏现有用户脚本
4. **绝不**在 skill 中写“注意：此命令用 `--top` 而彼命令用 `--limit`”之类的兼容提示

---

## 2. Skill 编写规范

### 2.1 Frontmatter 必填字段
```yaml
---
name: <skill-id>
description: <一句话说明>
version: <semver>
author: ZimoLiao/scholaraio
license: MIT
tags: [<标签>]
tier: core | writing | visualization | utility
destructive: true | false
---
```

- `tier` 分类：
  - `core` — 知识库核心操作（search, show, ingest, index...）
  - `writing` — 学术写作辅助（literature-review, paper-writing...）
  - `visualization` — 图表/文档生成（draw, diagram, document...）
  - `utility` — 工具/运维（setup, backup, websearch...）
- `destructive: true` 当且仅当 skill 的执行逻辑中包含以下任意一种：
  - 删除/覆盖文件或元数据（`rm`, `git push`, `rename --all` 无 `--dry-run` 直接执行）
  - 修改数据库/JSON 且无法自动回滚
  - 影响共享状态（推送到远程仓库）

### 2.2 禁止硬编码绝对路径
- ❌ 禁止：`/root/.claude/projects/...`
- ✅ 正确：`docs/xxx.md`（随仓库版本控制）或“项目记忆中的 `xxx.md`”（模糊引用，由运行时环境解析）

### 2.3 Subagent 提示词必须引用模板
- 所有用于 subagent 的复杂提示词必须提取到 `.claude/skills/_templates/`
- skill 内只允许写：**"启动 subagent 并使用 `_templates/xxx.md` 模板"**
- 禁止在 skill 中内联超过 3 行的 subagent 提示词

现有模板：
- `critic-reading.md`
- `comparison-table.md`
- `rebuttal-draft.md`

### 2.4 破坏性操作必须显式确认
- 如果 `destructive: true`，skill 文档中必须包含：
  1. 一步明确的确认提示（如"执行前**必须获得用户确认**"）
  2. 推荐的前置检查/备份（如 `/audit` 或 `/backup`）

### 2.5 CLI 示例必须使用规范名
- skill 中所有代码块示例必须使用 canonical flag
- 不允许出现历史别名（如 `--top`）

---

## 3. 自动化校验（Validation）

### 3.1 校验脚本
运行以下命令自动扫描常见违规：

```bash
python .claude/skills/_templates/validate_skills.py
```

检查项：
1. **硬编码绝对路径**：扫描 `/root/.claude/`、`/home/`、`/tmp/` 等绝对路径
2. **非规范 CLI 参数**：扫描 `--top` 等已废弃别名
3. **缺失 frontmatter 字段**：`tier`、`destructive` 是否齐全
4. **破坏性操作无确认**：`destructive: true` 但文档中缺少 "确认" / "备份" 关键字
5. **无效 CLI 组合**：扫描已知的无效参数组合（如 `diagram --from-text ... --critic`）

### 3.2 集成到开发流程
- 在新增/修改 skill 后，必须运行校验脚本
- 校验未通过不得合入

---

## 4. 决策记录（Decision Log）

| 日期 | 问题 | 决策 | 理由 |
|------|------|------|------|
| 2026-04-15 | `--top` vs `--limit` 不一致 | 统一规范名为 `--limit`，CLI 保留 `--top` 作为别名 | `--limit` 更直观，与 `explore fetch --limit` 及 API 惯例一致 |
| 2026-04-15 | subagent 提示词质量参差 | 提取为 `_templates/` 共享模板 | 避免 copy-paste 退化，统一质量控制 |
| 2026-04-15 | 破坏性操作无标识 | frontmatter 新增 `destructive` 字段 | 为主 agent 自动推荐前置检查提供元数据 |
| 2026-04-15 | 硬编码绝对路径 | 禁止在 skill 中写机器相关路径 | 确保 skill 在不同环境（本地/插件/其他机器）可移植 |

---

## 5. 附录：Canonical Flag 速查表

| 概念 | 规范名 | 已废弃别名 |
|------|--------|------------|
| 返回数量 | `--limit N` | `--top N` |
| 工作区 | `--ws NAME` | — |
| 输出格式 | `--format FMT` | — |
| 年份过滤 | `--year YYYY` / `--year START-END` | — |
| 强制/去重 | `--force` | — |
| 重建索引 | `--rebuild` | — |
| Critic 模式 | `--critic` | — |
| 从文字生成 | `--from-text "..."` | — |
| 从 IR 生成 | `--from-ir PATH` | — |
