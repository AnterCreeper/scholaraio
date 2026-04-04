---
name: setup
description: Initialize and diagnose the ScholarAIO environment. Run interactive setup wizard (bilingual EN/ZH) to install dependencies, create config files, and configure API keys. Run status check to see what's installed and what's missing. Use when the user wants to set up, install, configure, or troubleshoot ScholarAIO.
version: 1.0.0
author: ZimoLiao/scholaraio
license: MIT
tags: ["setup", "configuration", "installation"]
---
# Setup / 环境配置

当用户需要配置、安装、初始化 ScholarAIO 时，按以下流程操作：

## 1. 诊断当前状态

```bash
scholaraio setup check --lang zh
```

阅读输出，了解哪些组件已就绪、哪些缺失。
如果用户明确是在让 agent 代为配置，而不是自己逐步操作：
- 默认先跑 `scholaraio setup check --lang zh`
- 优先利用检查输出中的错误说明和建议链接，直接继续下一步配置
- 只有在会影响后续决策时，才回头问用户一个关键问题
- 对失败项要用“现状 + 原因 + 建议动作”的方式转述，不要只说“没装”或“不可达”

## 2. 根据缺失项引导用户

### 依赖缺失
- 告诉用户缺少哪些依赖，解释每组依赖的用途：
  - `embed`: 语义向量检索（Qwen3 嵌入模型）
  - `topics`: BERTopic 主题建模
  - `import`: Endnote / Zotero 导入
  - `full`: 全部功能
- 运行 `pip install -e ".[full]"` 或按需安装

### config.yaml 缺失
- 运行 `scholaraio setup` 交互式向导自动创建
- 或者直接帮用户创建（默认配置即可）

### API key 未配置
- **LLM key**（DeepSeek / OpenAI）：问用户是否有。没有也能用，但元数据提取降级为纯正则、enrich 不可用
- **PDF 解析器选择**：先问用户想用 `MinerU` 还是 `Docling`
- 如果用户已经明确知道要用哪个解析器，**不要替用户改主意**，直接按用户选择继续配置
- 如果用户不知道选哪个：
  - 测试 `MinerU` 官方入口和 `https://huggingface.co` 是否可达
  - 若只有一个可达，就建议优先对应方案
  - 若两者都可达，默认建议优先 `MinerU`
  - 若两者都不可达，优先建议 `Docling` 本地部署
  - 推荐时要明确说明：这是建议，不是替用户做决定；如果用户已有偏好，以用户选择为准
- **MinerU key**：仅在用户选择 `MinerU` 云端方案时提示。要明确说明：`MinerU API key 是免费的，只需要注册并申请`
- 将密钥写入 `config.local.yaml`（不进 git）

### MinerU 高级字段约束
- 对用户暴露时，默认坚持“能不改就不改”，优先开箱即用
- `mineru_model_version_cloud`
  - ScholarAIO 当前是 PDF 解析场景，云端只建议 `pipeline` 或 `vlm`
  - 不要引导用户设置 `MinerU-HTML`；那是 HTML 解析专用，不是 PDF 默认路径
- `mineru_parse_method`
  - 对云端精准解析 API，不存在通用的 `parse_method` 请求字段
  - ScholarAIO 只在用户明确要求 `ocr` 时映射为官方 `file.is_ocr=true`
  - `auto` / `txt` 默认都按“不强制 OCR”处理，不要过度解释成不同云端模式
- `mineru_enable_formula` / `mineru_enable_table` / `mineru_lang`
  - 这些字段只对 `pipeline` / `vlm` 有效
  - 没有强需求时保留默认值
- `mineru_batch_size`
  - 官方 batch 上限是 200
  - 默认值保持保守即可，不要主动调大
- `mineru_backend_local`
  - 仅在用户明确要本地部署 MinerU 时才讨论
  - 对纯云端用户，不要把它当成需要配置的字段

### 部署引导
- **MinerU**
  - 若推荐 `MinerU`，继续问用户是否打算本地部署
  - 若打算本地部署，给出官方 Quick Start、Docker 部署、GitHub 链接，并提示本地模型/ModelScope 方案
  - 若不打算本地部署，明确告诉用户去申请免费 API key
- **Docling**
  - 给出官方安装文档、CLI 文档、GitHub 链接
  - 至少提供 `pip install docling`，以及 Linux CPU-only 场景的官方安装示例

### 能写成代码的优先写成代码
- `scholaraio setup` 里应尽量直接实现：
  - 网络可达性探测
  - 解析器推荐逻辑
  - MinerU 本地/云端分流提问
  - 官方部署入口链接打印
- 更偏 agent 行为规范的内容保留在本 skill，例如：
  - 什么时候主动帮用户做网络探测
  - 如何向用户解释“为什么推荐这个解析器”
  - 遇到两边都不通时的默认建议
  - 如何在用户已有明确偏好时停止“自动推荐”

### 沙盒 / 提权说明（对 Codex 等 agent 很重要）
- 如果 agent 运行在沙盒里，**不要把沙盒内的网络探测结果直接当成用户真实网络环境**
- 对 `MinerU cloud`、`Hugging Face`、以及 `localhost:8000` 这类连通性测试：
  - 优先在允许的情况下提权后再测
  - 如果不能提权，就必须明确告诉用户“这是沙盒视角结果，可能误判”
- 特别注意：
  - agent 沙盒里的 `localhost` 不一定等于用户宿主机的 `localhost`
  - agent 沙盒里的外网策略可能比用户宿主机更严格
- 如果用户愿意自己在宿主机验证，优先让用户运行：
  - `curl -I --max-time 10 http://localhost:8000`
  - `curl -I --max-time 10 https://mineru.net/apiManage/token`
  - `curl -I --max-time 10 https://huggingface.co`

### 目录不存在
- 运行 `scholaraio setup check` 后如果目录缺失，运行任意 scholaraio 命令会自动创建（`ensure_dirs()`）

## 3. 验证

配置完成后再次运行 `scholaraio setup check` 确认所有项目 [OK]。

## 注意

- 用户也可以直接运行 `scholaraio setup` 进入交互式向导（bilingual EN/ZH）
- `config.local.yaml` 存放敏感信息（API key），不进 git
- 嵌入模型（~1.2GB）会在首次 embed/vsearch 时自动下载，setup 不触发下载
