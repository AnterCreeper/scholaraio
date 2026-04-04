<div align="center">

<!-- TODO: 有 logo 后替换 -->
<!-- <img src="docs/assets/logo.png" width="200" alt="ScholarAIO Logo"> -->

# ScholarAIO

**Scholar All-In-One — 为 AI agent 打造的科研知识基础设施。**

[English](README.md) | [中文](README_CN.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Claude Code Skills](https://img.shields.io/badge/Claude_Code_Skills-26-purple.svg)](.claude/skills/)

</div>

---

你的 coding agent 已经能读代码、写代码、跑实验。ScholarAIO 给它加上一个结构化的论文知识库——于是同一个 agent，既能帮你写代码，也能检索文献、交叉验证结果、复现论文方法、起草文稿。一个终端，一个 agent，完成科研全流程。

<!-- TODO: 加 demo GIF -->
<!-- <div align="center">
  <img src="docs/assets/demo.gif" width="700" alt="ScholarAIO Demo">
</div> -->

## 从这里开始

| 如果你想... | 推荐做法 |
|-------------|----------|
| 直接体验 ScholarAIO 或参与开发 | 直接用 agent 打开这个仓库 |
| 在 Claude Code 的任意项目里使用 ScholarAIO | 安装 Claude Code 插件 |
| 在 Codex / OpenClaw 中复用 ScholarAIO skills | 注册到 `~/.agents/skills/` |

详细说明见：[`docs/getting-started/agent-setup.md`](docs/getting-started/agent-setup.md)

## 在本仓库内使用

如果你想获得最完整的体验，这是最好的路径：仓库内置的 agent 指令、skills、CLI 和完整代码上下文都会直接可用。

```bash
# 1. 克隆并安装
git clone https://github.com/ZimoLiao/scholaraio.git
cd scholaraio
pip install -e ".[full]"

# 2. 配置本地环境
scholaraio setup

# 3. 在仓库根目录启动你的 agent
claude
```

直接打开仓库时：

- Claude Code 会读取 `CLAUDE.md` 和 `.claude/skills/`
- Codex / OpenClaw 会读取 `AGENTS.md` 和 `.agents/skills/`
- Cline 会读取 `.clinerules`
- Cursor 会读取 `.cursorrules`
- Windsurf 会读取 `.windsurfrules`
- GitHub Copilot 会读取 `.github/copilot-instructions.md`

你也可以直接使用 CLI，例如 `scholaraio search "你的主题"`。

## 在任意项目中启用 ScholarAIO

### Claude Code 插件

如果你想在任意项目里启用 ScholarAIO，Claude Code 插件是最干净的路径：

请在 Claude Code 会话中输入以下斜杠命令，不要在系统终端里运行：

```text
/plugin marketplace add ZimoLiao/scholaraio
/plugin install scholaraio@scholaraio-marketplace
```

安装后，在任意项目中新开 Claude Code 会话，即可用 `/scholaraio:search`、`/scholaraio:show` 这类命名空间 skill。

### Codex / OpenClaw skills 注册

如果你想在仓库外也让 Codex 风格 agent 发现 ScholarAIO，推荐像其他 skills 包那样做一次全局注册：

```bash
git clone https://github.com/ZimoLiao/scholaraio.git ~/.codex/scholaraio
cd ~/.codex/scholaraio
pip install -e ".[full]"
scholaraio setup
mkdir -p ~/.agents/skills
ln -s ~/.codex/scholaraio/.claude/skills ~/.agents/skills/scholaraio
```

然后明确配置发现路径，避免在其他项目目录里误创建 `data/` 和 `workspace/`：

```bash
# 方案 A：让 ScholarAIO 数据继续放在克隆仓库目录下
export SCHOLARAIO_CONFIG="$HOME/.codex/scholaraio/config.yaml"

# 方案 B：把配置放到全局默认位置
mkdir -p ~/.scholaraio
cp ~/.codex/scholaraio/config.yaml ~/.scholaraio/config.yaml
```

如果不做这一步，在其他项目目录里运行 `scholaraio` 时，程序可能回退到当前项目下的默认配置并在那里创建 `data/` 和 `workspace/`。创建符号链接后重启 agent，这样 ScholarAIO skills 才会被全局发现；如果你还想让 agent 同时读取仓库自带的完整项目指令，仍然建议直接打开本仓库。

完整 agent 对照表见 [`docs/getting-started/agent-setup.md`](docs/getting-started/agent-setup.md)。

## 核心功能

|  | 功能 | 说明 |
|--|------|------|
| **PDF 解析** | 深度结构提取 | 优先使用 [MinerU](https://github.com/opendatalab/MinerU) 或 [Docling](https://github.com/docling-project/docling) 输出结构化 Markdown；若两者都不可用，ScholarAIO 会回退到 PyMuPDF 文本提取。使用 MinerU 时，超长 PDF（>100 页）会自动切分再合并 |
| **不只是论文** | 各种文档都能入 | 期刊论文、学位论文、专利、技术报告、标准、讲义——四种 inbox 分类入库，各有针对性的元数据处理 |
| **融合检索** | 关键词 + 语义 | FTS5 + Qwen3 嵌入 + FAISS → RRF 排序融合 |
| **主题发现** | 自动聚类 | BERTopic + 6 种交互式 HTML 可视化——同时支持主库和 explore 数据集 |
| **文献探索** | 多维度发现 | OpenAlex 9 维过滤（期刊、概念、作者、机构、关键词、来源类型、年份、引用量、文献类型）→ 向量化 → 聚类 → 检索 |
| **引用图谱** | 参考文献与影响力 | 正向/反向引用、共同引用分析 |
| **分层阅读** | 按需加载 | L1 元数据 → L2 摘要 → L3 结论 → L4 全文 |
| **多源导入** | 带上你的文献库 | Endnote XML/RIS、Zotero（API + SQLite，支持 collection → workspace 映射）、PDF、Markdown——更多来源持续接入 |
| **工作区** | 按项目组织 | 论文子集管理，支持范围内检索和 BibTeX 导出 |
| **多格式导出** | BibTeX / RIS / Markdown / DOCX | 导出整个库或工作区——直接用于 Zotero、Endnote、投稿或分享 |
| **持久化笔记** | 跨会话记忆 | Agent 的分析结果按论文保存（`notes.md`），再次访问时复用已有发现，无需重读全文——省 token、不重复劳动 |
| **研究洞察** | 阅读行为分析 | 搜索热词、高频阅读论文、阅读趋势、语义近邻推荐——发现你可能忽略的文献 |
| **绘图与可视化** | 出版级图表 | Mermaid（流程图、时序图、ER 图、甘特图、思维导图）+ Inkscape 矢量图形——输出 PNG/SVG/PDF |
| **学术写作** | AI 辅助撰写 | 文献综述、论文章节、引用验证、审稿回复、研究空白分析——每条引用可追溯至你自己的文献库 |

## 不只是论文管理

ScholarAIO 把 PDF 解析成干净的 Markdown，LaTeX 公式准确，图片附件完整。这意味着你的 coding agent 不只能"读"论文，还能：

- **复现方法** — 读算法描述，写出实现，直接运行
- **验证结论** — 从图表中提取数据，独立计算，交叉核对
- **推导公式** — 接着论文的推导继续展开，用数值计算验证边界条件
- **可视化结果** — 把论文数据和你自己的实验结果画在一起对比

知识库是基础设施，agent 在此之上能做什么，取决于你的想象力。

## 兼容你的 Agent

ScholarAIO 的设计目标是 **agent 无关**，但不同 agent 的安装入口并不一样。有些更适合直接打开仓库，有些更适合走插件。

| Agent / IDE | 直接打开本仓库 | 在其他项目中复用 |
|-------------|---------------|------------------|
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | `CLAUDE.md` + `.claude/skills/` | Claude 插件市场 |
| [Codex](https://openai.com/codex) / OpenClaw | `AGENTS.md` + `.agents/skills/` | 注册到 `~/.agents/skills/` |
| [Cline](https://github.com/cline/cline) | `.clinerules` + `.claude/skills/` | CLI + skills |
| [Cursor](https://cursor.sh) | `.cursorrules` | CLI + skills |
| [Windsurf](https://codeium.com/windsurf) | `.windsurfrules` | CLI + skills |
| [GitHub Copilot](https://github.com/features/copilot) | `.github/copilot-instructions.md` | CLI + skills |

Skills 遵循开放的 [AgentSkills.io](https://agentskills.io) 标准，`.agents/skills/` 是 `.claude/skills/` 的符号链接，方便跨 agent 发现。

**从现有工具迁移？** 支持从 Endnote（XML/RIS）和 Zotero（Web API 或本地 SQLite）直接导入——PDF、元数据、引用关系一并迁入。更多导入源持续开发中。

## 工作流程

```
PDF → MinerU → 结构化 Markdown（图表 + LaTeX 公式保留）
                    ↓
          元数据提取（正则 + LLM 交叉验证）
          API 补全（Crossref / Semantic Scholar / OpenAlex）
                    ↓
          DOI 去重 → data/papers/<Author-Year-Title>/
                    ↓
      ┌─────────────┼─────────────┐
   FTS5 索引      FAISS 向量     BERTopic
   （关键词）     （语义）       （聚类）
      └─────────────┼─────────────┘
                    ↓
        你的 agent（Claude Code / Cursor / CLI / ...）
```

## 配置说明

主配置：`config.yaml`（进 git）。敏感信息：`config.local.yaml`（不进 git）。

| Key | 用途 | 获取方式 |
|-----|------|---------|
| LLM API key | 元数据提取、内容富化、学术讨论 | 在 `config.local.yaml` 中设置 `llm.api_key`，或使用环境变量：`SCHOLARAIO_LLM_API_KEY`（通用）、`DEEPSEEK_API_KEY`、`OPENAI_API_KEY`、`ANTHROPIC_API_KEY`、`GOOGLE_API_KEY` / `GEMINI_API_KEY`。默认后端：[DeepSeek](https://platform.deepseek.com/)；同时支持 Claude、Gemini、Ollama 及任意 OpenAI 兼容 API |
| `MINERU_API_KEY` | MinerU 云端 PDF 解析 | [mineru.net](https://mineru.net/apiManage/token) 免费申请，也可[本地部署](https://github.com/opendatalab/MinerU) |

> **均为可选。** 没有 LLM key：降级为纯正则提取。没有 MinerU 云端/本地能力时，ScholarAIO 仍可回退到 Docling 或 PyMuPDF 解析 PDF；也可以直接将 `.md` 放入 `data/inbox/`。

嵌入模型（Qwen3-Embedding-0.6B，约 1.2 GB）首次使用时自动下载。默认从 ModelScope 下载（国内无需代理），海外用户设置 `embed.source: huggingface`。

完整配置参考 → [`config.yaml`](config.yaml)

## 三种使用方式

| 模式 | 适用场景 | 命令 |
|------|---------|------|
| **Agent**（推荐） | 完整科研工作流——对话式交互 | 项目目录下运行 `claude` 或你喜欢的 agent |
| **CLI** | 脚本、快速查询 | `scholaraio --help` |

<details>
<summary><strong>CLI 命令一览</strong></summary>

**检索与阅读**
```
scholaraio search QUERY       关键词检索（FTS5）
scholaraio vsearch QUERY      语义向量检索
scholaraio usearch QUERY      融合检索（关键词 + 语义）
scholaraio search-author NAME 按作者搜索
scholaraio top-cited          按引用量排序
scholaraio show PAPER         查看论文内容（L1-L4）
```

**入库与富化**
```
scholaraio pipeline PRESET    运行入库流水线（full|ingest|enrich|reindex）
scholaraio index              构建 FTS5 检索索引
scholaraio embed              生成语义向量
scholaraio enrich-toc         提取目录结构
scholaraio enrich-l3          提取结论段
scholaraio backfill-abstract  补全缺失摘要
scholaraio refetch            重新查询引用量
```

**引用图谱**
```
scholaraio refs PAPER         查看参考文献
scholaraio citing PAPER       查看被引论文
scholaraio shared-refs A B    共同参考文献分析
```

**探索与主题**
```
scholaraio explore fetch ...  文献探索（OpenAlex 多维过滤）
scholaraio explore search ... 探索库内检索
scholaraio topics             BERTopic 主题建模
```

**导入与导出**
```
scholaraio import-endnote     从 Endnote 导入
scholaraio import-zotero      从 Zotero 导入
scholaraio attach-pdf         为已有论文补充 PDF
scholaraio export bibtex      导出 BibTeX
scholaraio ws init NAME       创建工作区
scholaraio ws add NAME PAPER  添加论文到工作区
scholaraio ws search NAME Q   工作区内检索
```

**维护**
```
scholaraio audit              数据质量审计
scholaraio repair             修复元数据
scholaraio rename             标准化目录名
scholaraio migrate-dirs       迁移旧版目录结构
scholaraio setup              环境配置向导（默认进入向导，`check` 只做诊断）
scholaraio metrics            查看 LLM 用量统计
```

</details>

## 项目结构

```
scholaraio/          # Python 包——CLI、所有核心模块
  ingest/            #   PDF 解析 + 元数据提取流水线
  sources/           #   数据源适配（local / Endnote / Zotero）

.claude/skills/      # 26 个 agent skills（AgentSkills.io 格式）
.agents/skills/      # ↑ 符号链接，方便跨 agent 发现
data/papers/         # 你的论文库（不进 git）
data/inbox/          # 放入 PDF 即可入库
```

完整模块参考 → [`CLAUDE.md`](CLAUDE.md) 或 [`AGENTS.md`](AGENTS.md)

## 引用

如果 ScholarAIO 对你的研究有帮助，欢迎引用：

```bibtex
@software{scholaraio,
  author = {Liao, Zi-Mo},
  title = {ScholarAIO: AI-Native Research Terminal},
  year = {2026},
  url = {https://github.com/ZimoLiao/scholaraio},
  license = {MIT}
}
```

## 许可证

[MIT](LICENSE) © 2026 Zi-Mo Liao
