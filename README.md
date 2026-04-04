<div align="center">

<!-- TODO: Replace with actual logo when available -->
<!-- <img src="docs/assets/logo.png" width="200" alt="ScholarAIO Logo"> -->

# ScholarAIO

**Scholar All-In-One — a knowledge infrastructure for AI agents.**

[English](README.md) | [中文](README_CN.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Claude Code Skills](https://img.shields.io/badge/Claude_Code_Skills-ScholarAIO-purple.svg)](.claude/skills/)

</div>

---

Your coding agent already reads code, writes code, and runs experiments. ScholarAIO gives it a structured knowledge base of your research papers — so the same agent that writes your code can also search your literature, cross-check results against published findings, reproduce methods from papers, and draft your manuscript. One terminal, one agent, the full research loop.

<!-- TODO: Add demo GIF here -->
<!-- <div align="center">
  <img src="docs/assets/demo.gif" width="700" alt="ScholarAIO Demo">
</div> -->

## Start Here

| If you want to... | Do this |
|-------------------|---------|
| Try ScholarAIO itself or contribute to the repo | Open this repository directly with your agent |
| Use ScholarAIO in Claude Code across many projects | Install the Claude Code plugin |
| Reuse ScholarAIO skills in Codex / OpenClaw | Register the skills through `~/.agents/skills/` |

Detailed setup guide: [`docs/getting-started/agent-setup.md`](docs/getting-started/agent-setup.md)

## Use Inside This Repository

This is the best path when you want the full ScholarAIO experience: bundled agent instructions, local skills, CLI, and the complete codebase context.

```bash
# 1. Clone and install
git clone https://github.com/ZimoLiao/scholaraio.git
cd scholaraio
pip install -e ".[full]"

# 2. Configure your local environment
scholaraio setup

# 3. Start your agent in the repo root
claude
```

When you open the repo directly:

- Claude Code reads `CLAUDE.md` and `.claude/skills/`
- Codex / OpenClaw read `AGENTS.md` and `.agents/skills/`
- Cline reads `.clinerules`
- Cursor reads `.cursorrules`
- Windsurf reads `.windsurfrules`
- GitHub Copilot reads `.github/copilot-instructions.md`

You can also use the CLI directly with `scholaraio search "your topic"`.

## Register ScholarAIO in Another Project

### Claude Code plugin

ScholarAIO ships as a Claude Code plugin, so this is the cleanest cross-project install path:

Run these commands inside a Claude Code session, not in your system shell:

```text
/plugin marketplace add ZimoLiao/scholaraio
/plugin install scholaraio@scholaraio-marketplace
```

After that, start a new Claude Code session in any project and use namespaced skills such as `/scholaraio:search` or `/scholaraio:show`.

### Codex / OpenClaw skills

If you want ScholarAIO available to Codex-style agents outside this repo, clone it once and symlink the skills into the global discovery directory:

```bash
git clone https://github.com/ZimoLiao/scholaraio.git ~/.codex/scholaraio
cd ~/.codex/scholaraio
pip install -e ".[full]"
scholaraio setup
mkdir -p ~/.agents/skills
ln -s ~/.codex/scholaraio/.claude/skills ~/.agents/skills/scholaraio
```

Then make config discovery explicit for cross-project use:

```bash
# Option A: keep ScholarAIO data rooted in the cloned repo
export SCHOLARAIO_CONFIG="$HOME/.codex/scholaraio/config.yaml"

# Option B: move/copy config to the global fallback location
mkdir -p ~/.scholaraio
cp ~/.codex/scholaraio/config.yaml ~/.scholaraio/config.yaml
```

Without one of those two options, running `scholaraio` from another project may fall back to defaults rooted in that current project and create `data/` plus `workspace/` there. Restart the agent after creating the symlink. This registers the ScholarAIO skill library globally. For the full bundled project instructions, opening this repository directly is still the better path.

## What It Does

|  | Feature | Details |
|--|---------|---------|
| **PDF Parsing** | Deep structure extraction | Prefer [MinerU](https://github.com/opendatalab/MinerU) or [Docling](https://github.com/docling-project/docling) for structured Markdown. If neither is available, ScholarAIO falls back to PyMuPDF text extraction. Long PDFs (>100 pp) are auto-split and merged when MinerU is used |
| **Not Just Papers** | Any document goes in | Journal articles, theses, patents, technical reports, standards, lecture notes — four inboxes with tailored metadata handling |
| **Hybrid Search** | Keyword + semantic fusion | Keyword + semantic embeddings → RRF ranking |
| **Topic Discovery** | Auto-clustering | BERTopic + 6 interactive HTML visualizations — works on both your library and explore datasets |
| **Literature Exploration** | Multi-dimensional discovery | OpenAlex with 9 filter dimensions (journal, concept, author, institution, keyword, source type, year, citations, work type) → embed → cluster → search |
| **Citation Graph** | References & impact | Forward/backward citations, shared references across your library |
| **Layered Reading** | Read at the depth you need | L1 metadata → L2 abstract → L3 conclusion → L4 full text |
| **Multi-Source Import** | Bring your existing library | Endnote XML/RIS, Zotero (API + SQLite, with collection → workspace mapping), PDF, Markdown — more sources planned |
| **Workspaces** | Organize for projects | Paper subsets with scoped search and BibTeX export |
| **Multi-Format Export** | BibTeX, RIS, Markdown, DOCX | Export your library or workspace in any format — ready for Zotero, Endnote, manuscript submission, or sharing |
| **Persistent Notes** | Cross-session memory | Agent analysis is saved per-paper (`notes.md`). Revisiting a paper reuses prior findings instead of re-reading the full text — saves tokens and avoids redundant work |
| **Research Insights** | Reading behavior analytics | Search hot keywords, most-read papers, reading trends, and semantic neighbor recommendations for papers you haven't read yet |
| **Federated Discovery** | Search across silos | Search your main library, explore silos, and arXiv in one command; pull arXiv PDFs directly into the ingest pipeline |
| **Scientific Tool Docs** | Runtime guidance for computational tools | `toolref` ingests official docs for Quantum ESPRESSO, LAMMPS, GROMACS, OpenFOAM, and curated bioinformatics tools so agents can answer parameter and workflow questions precisely |
| **Diagrams & Figures** | Publication-ready visuals | Mermaid (flowcharts, sequence diagrams, ER diagrams, Gantt charts, mind maps) and vector graphics via Inkscape — output PNG/SVG/PDF |
| **Academic Writing** | AI-assisted drafting | Literature review, paper sections, citation check, rebuttal, gap analysis — every claim traceable to your own library |

## Beyond Paper Management

ScholarAIO parses PDFs into clean Markdown with accurate LaTeX and figure attachments. This means your coding agent doesn't just *read* papers — it can:

- **Reproduce methods** — read an algorithm description, write the implementation, run it
- **Verify claims** — extract data from figures and tables, compute independently, cross-check
- **Explore formulas** — pick up where a derivation leaves off, test boundary cases numerically
- **Visualize results** — plot data from papers alongside your own experiments

The knowledge base is the foundation; what your agent builds on top of it is open-ended.

## Works With Your Agent

ScholarAIO is designed to be **agent-agnostic**, but not every agent exposes the same installation surface. Some work best by opening this repository directly; others are better through plugins.

| Agent / IDE | Open this repo directly | Reuse from another project |
|-------------|-------------------------|-----------------------------|
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | `CLAUDE.md` + `.claude/skills/` | Claude plugin marketplace |
| [Codex](https://openai.com/codex) / OpenClaw | `AGENTS.md` + `.agents/skills/` | Symlink skills into `~/.agents/skills/` |
| [Cline](https://github.com/cline/cline) | `.clinerules` + `.claude/skills/` | CLI + skills |
| [Cursor](https://cursor.sh) | `.cursorrules` | CLI + skills |
| [Windsurf](https://codeium.com/windsurf) | `.windsurfrules` | CLI + skills |
| [GitHub Copilot](https://github.com/features/copilot) | `.github/copilot-instructions.md` | CLI + skills |

Skills follow the open [AgentSkills.io](https://agentskills.io) standard, and `.agents/skills/` is a symlink to `.claude/skills/` for cross-agent discovery.

**Migrating from existing tools?** Import directly from Endnote (XML/RIS) and Zotero (Web API or local SQLite) — your PDFs, metadata, and references come along. More import sources are on the roadmap.

## How It Works

```
PDF → MinerU → Structured Markdown (figures + LaTeX intact)
                    ↓
          Metadata extraction (regex + LLM cross-validation)
          API enrichment (Crossref / Semantic Scholar / OpenAlex)
                    ↓
          DOI dedup → data/papers/<Author-Year-Title>/
                    ↓
      ┌─────────────┼─────────────┐
   FTS5 Index    FAISS Vectors   BERTopic
   (keyword)     (semantic)      (clustering)
      └─────────────┼─────────────┘
                    ↓
        Your agent (Claude Code / Cursor / CLI / ...)
```

## Configuration

Main config: `config.yaml` (tracked). Secrets: `config.local.yaml` (gitignored).

| Key | Purpose | Get it |
|-----|---------|--------|
| LLM API key | Metadata extraction, enrichment, academic discussion | Set `llm.api_key` in `config.local.yaml`, or use env vars: `SCHOLARAIO_LLM_API_KEY` (universal), `DEEPSEEK_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY` / `GEMINI_API_KEY`. Default backend: [DeepSeek](https://platform.deepseek.com/); also supports Claude, Gemini, Ollama, and any OpenAI-compatible API |
| `MINERU_API_KEY` | MinerU cloud PDF parsing | Free at [mineru.net](https://mineru.net/apiManage/token) or [self-host](https://github.com/opendatalab/MinerU) |

> **Both are optional.** Without LLM: regex-only extraction. Without MinerU cloud/local: ScholarAIO can still fall back to Docling or PyMuPDF for PDF parsing, or you can place `.md` files in `data/inbox/` directly.

Embedding model (Qwen3-Embedding-0.6B, ~1.2 GB) auto-downloads on first use. Default source: ModelScope (no proxy needed in China). International users: set `embed.source: huggingface` in config.
You can also override embedding source/model cache via environment variables: `SCHOLARAIO_EMBED_SOURCE`, `SCHOLARAIO_EMBED_CACHE_DIR`, `SCHOLARAIO_EMBED_MODEL`, and optional mirror `SCHOLARAIO_HF_ENDPOINT` (fallback to `HF_ENDPOINT`).

Optional web browsing integration: see [`docs/guide/webtools-integration.md`](docs/guide/webtools-integration.md) for using ScholarAIO together with [claude-webtools](https://github.com/AnterCreeper/claude-webtools).

Full config reference → [`config.yaml`](config.yaml)

## Two Ways to Use

| Mode | Best for | Command |
|------|----------|---------|
| **Agent** (recommended) | Full research workflow — conversational | `claude` / your preferred agent in project dir |
| **CLI** | Scripting, quick queries | `scholaraio --help` |

<details>
<summary><strong>CLI command reference</strong></summary>

**Search & Read**
```
scholaraio search QUERY       Keyword search
scholaraio vsearch QUERY      Semantic vector search
scholaraio usearch QUERY      Unified search (keyword + semantic fusion)
scholaraio fsearch QUERY      Federated search (main / proceedings / explore / arXiv)
scholaraio search-author NAME Search by author
scholaraio top-cited          Rank by citation count
scholaraio show PAPER         View paper content (L1-L4)
```

**Ingest & Enrich**
```
scholaraio pipeline PRESET    Run ingestion pipeline (full|ingest|enrich|reindex)
scholaraio index              Build keyword search index
scholaraio embed              Generate semantic vectors
scholaraio enrich-toc         Extract table of contents
scholaraio enrich-l3          Extract conclusions
scholaraio backfill-abstract  Backfill missing abstracts
scholaraio refetch            Re-fetch citation counts from APIs
scholaraio translate PAPER    Translate markdown to a target language
```

**Citation Graph**
```
scholaraio refs PAPER         View references
scholaraio citing PAPER       View citing papers
scholaraio shared-refs A B    Shared references between papers
```

**Explore & Topics**
```
scholaraio explore fetch ...  Literature exploration (OpenAlex multi-filter)
scholaraio explore search ... Search within an explore library
scholaraio topics             BERTopic topic modeling
```

**Import & Export**
```
scholaraio import-endnote     Import from Endnote
scholaraio import-zotero      Import from Zotero
scholaraio attach-pdf         Attach PDF to existing paper
scholaraio arxiv search ...   Search arXiv preprints
scholaraio arxiv fetch ID     Download arXiv PDF (optionally ingest)
scholaraio export bibtex      Export BibTeX
scholaraio ws init NAME       Create a workspace
scholaraio ws add NAME PAPER  Add papers to workspace
scholaraio ws search NAME Q   Search within workspace
```

**Scientific Runtime**
```
scholaraio toolref list       List indexed scientific tool docs
scholaraio toolref show ...   Show exact parameter or command docs
scholaraio toolref search ... Search scientific tool docs
scholaraio document inspect   Inspect DOCX / PPTX / XLSX structure
```

**Maintenance**
```
scholaraio audit              Data quality audit
scholaraio repair             Fix metadata
scholaraio rename             Standardize directory names
scholaraio migrate-dirs       Migrate legacy directory structure
scholaraio setup              Setup wizard
scholaraio metrics            View LLM usage stats
scholaraio insights [--days N] Reading behavior analytics
```

</details>

## Project Structure

```
scholaraio/          # Python package — CLI and all core modules
  ingest/            #   PDF parsing + metadata extraction pipeline
  sources/           #   Data source adapters (local / Endnote / Zotero)

.claude/skills/      # Agent skills (AgentSkills.io format)
.agents/skills/      # ↑ symlink for cross-agent discovery
data/papers/         # Your paper library (gitignored)
data/proceedings/    # Proceedings library (gitignored)
data/inbox/          # Drop PDFs here for ingestion
data/inbox-proceedings/ # Drop proceedings volumes here for dedicated ingest
```

Full module reference → [`CLAUDE.md`](CLAUDE.md) or [`AGENTS.md`](AGENTS.md)

## Citation

If you use ScholarAIO in your research, please cite:

```bibtex
@software{scholaraio,
  author = {Liao, Zi-Mo},
  title = {ScholarAIO: AI-Native Research Terminal},
  year = {2026},
  url = {https://github.com/ZimoLiao/scholaraio},
  license = {MIT}
}
```

## License

[MIT](LICENSE) © 2026 Zi-Mo Liao
