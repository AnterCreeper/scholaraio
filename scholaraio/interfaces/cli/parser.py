"""CLI parser construction."""

from __future__ import annotations

import argparse

from scholaraio.interfaces.cli.arguments import _add_filter_args, _add_result_limit_arg


def _build_parser() -> argparse.ArgumentParser:
    from scholaraio.interfaces.cli import compat as cli_mod

    cmd_index = cli_mod.cmd_index
    cmd_search = cli_mod.cmd_search
    cmd_search_author = cli_mod.cmd_search_author
    cmd_show = cli_mod.cmd_show
    cmd_embed = cli_mod.cmd_embed
    cmd_vsearch = cli_mod.cmd_vsearch
    cmd_usearch = cli_mod.cmd_usearch
    cmd_citation_check = cli_mod.cmd_citation_check
    cmd_enrich_toc = cli_mod.cmd_enrich_toc
    cmd_enrich_l3 = cli_mod.cmd_enrich_l3
    cmd_pipeline = cli_mod.cmd_pipeline
    cmd_refetch = cli_mod.cmd_refetch
    cmd_top_cited = cli_mod.cmd_top_cited
    cmd_refs = cli_mod.cmd_refs
    cmd_citing = cli_mod.cmd_citing
    cmd_shared_refs = cli_mod.cmd_shared_refs
    cmd_topics = cli_mod.cmd_topics
    cmd_backfill_abstract = cli_mod.cmd_backfill_abstract
    cmd_rename = cli_mod.cmd_rename
    cmd_audit = cli_mod.cmd_audit
    cmd_repair = cli_mod.cmd_repair
    cmd_explore = cli_mod.cmd_explore
    cmd_ws = cli_mod.cmd_ws
    cmd_export = cli_mod.cmd_export
    cmd_diagram = cli_mod.cmd_diagram
    cmd_document = cli_mod.cmd_document
    cmd_fsearch = cli_mod.cmd_fsearch
    cmd_import_endnote = cli_mod.cmd_import_endnote
    cmd_import_zotero = cli_mod.cmd_import_zotero
    cmd_attach_pdf = cli_mod.cmd_attach_pdf
    cmd_ingest_link = cli_mod.cmd_ingest_link
    cmd_arxiv_search = cli_mod.cmd_arxiv_search
    cmd_arxiv_fetch = cli_mod.cmd_arxiv_fetch
    cmd_patent_search = cli_mod.cmd_patent_search
    cmd_patent_fetch = cli_mod.cmd_patent_fetch
    cmd_proceedings = cli_mod.cmd_proceedings
    cmd_toolref = cli_mod.cmd_toolref
    cmd_style = cli_mod.cmd_style
    cmd_setup = cli_mod.cmd_setup
    cmd_insights = cli_mod.cmd_insights
    cmd_migrate = cli_mod.cmd_migrate
    cmd_translate = cli_mod.cmd_translate
    cmd_websearch = cli_mod.cmd_websearch
    cmd_webextract = cli_mod.cmd_webextract
    cmd_backup = cli_mod.cmd_backup
    cmd_metrics = cli_mod.cmd_metrics

    parser = argparse.ArgumentParser(
        prog="scholaraio",
        description="面向 AI coding agent 的研究终端",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- index ---
    p_index = sub.add_parser("index", help="构建 FTS5 检索索引")
    p_index.set_defaults(func=cmd_index)
    p_index.add_argument("--rebuild", action="store_true", help="清空后重建")

    # --- search ---
    p_search = sub.add_parser("search", help="关键词检索")
    p_search.set_defaults(func=cmd_search)
    p_search.add_argument("query", nargs="+", help="检索词")
    _add_result_limit_arg(p_search, "最多返回 N 条（默认读 config search.top_k）")
    _add_filter_args(p_search)

    # --- search-author ---
    p_sa = sub.add_parser("search-author", help="按作者名搜索")
    p_sa.set_defaults(func=cmd_search_author)
    p_sa.add_argument("query", nargs="+", help="作者名（模糊匹配）")
    _add_result_limit_arg(p_sa, "最多返回 N 条（默认读 config search.top_k）")
    _add_filter_args(p_sa)

    # --- show ---
    p_show = sub.add_parser("show", help="查看论文内容")
    p_show.set_defaults(func=cmd_show)
    p_show.add_argument("paper_id", help="论文 ID（目录名 / UUID / DOI）")
    p_show.add_argument(
        "--layer",
        type=int,
        default=2,
        choices=[1, 2, 3, 4],
        help="加载层级：1=元数据, 2=摘要, 3=结论, 4=全文（默认 2）",
    )
    p_show.add_argument("--lang", type=str, default=None, help="加载翻译版本（如 zh），仅 L4 生效")
    p_show.add_argument(
        "--append-notes",
        type=str,
        default=None,
        metavar="TEXT",
        help="向论文笔记 notes.md 追加内容（T2 层，跨会话复用）",
    )

    # --- embed ---
    p_embed = sub.add_parser("embed", help="生成语义向量写入 index.db")
    p_embed.set_defaults(func=cmd_embed)
    p_embed.add_argument("--rebuild", action="store_true", help="清空后重建")

    # --- vsearch ---
    p_vsearch = sub.add_parser("vsearch", help="语义向量检索")
    p_vsearch.set_defaults(func=cmd_vsearch)
    p_vsearch.add_argument("query", nargs="+", help="检索词")
    _add_result_limit_arg(p_vsearch, "最多返回 N 条（默认读 config embed.top_k）")
    _add_filter_args(p_vsearch)

    # --- usearch (unified) ---
    p_usearch = sub.add_parser("usearch", help="融合检索（关键词 + 语义向量）")
    p_usearch.set_defaults(func=cmd_usearch)
    p_usearch.add_argument("query", nargs="+", help="检索词")
    _add_result_limit_arg(p_usearch, "最多返回 N 条（默认读 config search.top_k）")
    _add_filter_args(p_usearch)

    # --- enrich-toc ---
    p_toc = sub.add_parser("enrich-toc", help="LLM 过滤标题噪声，提取论文 TOC 写入 JSON")
    p_toc.set_defaults(func=cmd_enrich_toc)
    p_toc.add_argument("paper_id", nargs="?", help="论文 ID（省略则需 --all）")
    p_toc.add_argument("--all", action="store_true", help="处理 papers_dir 中所有论文")
    p_toc.add_argument("--force", action="store_true", help="强制重新提取")
    p_toc.add_argument("--inspect", action="store_true", help="展示过滤过程")

    # --- pipeline ---
    p_pipe = sub.add_parser("pipeline", help="组合步骤流水线（可任意组装）")
    p_pipe.set_defaults(func=cmd_pipeline)
    p_pipe.add_argument(
        "preset",
        nargs="?",
        help="预设名称：full | ingest | enrich | reindex",
    )
    p_pipe.add_argument("--steps", help="自定义步骤序列（逗号分隔），如 toc,l3,index")
    p_pipe.add_argument("--list", dest="list_steps", action="store_true", help="列出所有步骤和预设")
    p_pipe.add_argument("--dry-run", action="store_true", help="预览，不写文件")
    p_pipe.add_argument("--no-api", action="store_true", help="离线模式，跳过外部 API")
    p_pipe.add_argument("--force", action="store_true", help="强制重新处理（toc/l3）")
    p_pipe.add_argument("--inspect", action="store_true", help="展示处理详情")
    p_pipe.add_argument("--max-retries", type=int, default=2, help="l3 最大重试次数（默认 2）")
    p_pipe.add_argument("--rebuild", action="store_true", help="重建索引（index 步骤）")
    p_pipe.add_argument("--inbox", help="inbox 目录（默认配置值；fresh 实例为 data/spool/inbox）")
    p_pipe.add_argument("--papers", help="papers 目录（默认配置值）")

    # --- refetch ---
    p_refetch = sub.add_parser("refetch", help="重新查询 API 补全引用量、references 等字段")
    p_refetch.set_defaults(func=cmd_refetch)
    p_refetch.add_argument("paper_id", nargs="?", help="论文 ID（目录名 / UUID / DOI；省略则需 --all）")
    p_refetch.add_argument("--all", action="store_true", help="补查所有缺失引用量的论文")
    p_refetch.add_argument("--force", action="store_true", help="强制重新查询（包括已有引用量的论文）")
    p_refetch.add_argument(
        "--references-only",
        "--refs-only",
        action="store_true",
        help="仅补 references 为空的 DOI 论文；单篇模式下只更新 references",
    )
    p_refetch.add_argument("--jobs", "-j", type=int, default=5, help="并发数（默认 5）")

    # --- top-cited ---
    p_tc = sub.add_parser("top-cited", help="按引用量排序查看论文")
    p_tc.set_defaults(func=cmd_top_cited)
    _add_result_limit_arg(p_tc, "最多返回 N 条（默认读 config search.top_k）")
    _add_filter_args(p_tc)

    # --- refs ---
    p_refs = sub.add_parser("refs", help="查看论文的参考文献列表")
    p_refs.set_defaults(func=cmd_refs)
    p_refs.add_argument("paper_id", help="论文 ID（目录名 / UUID / DOI）")
    p_refs.add_argument("--ws", type=str, default=None, help="限定工作区范围")

    # --- citing ---
    p_citing = sub.add_parser("citing", help="查看哪些本地论文引用了此论文")
    p_citing.set_defaults(func=cmd_citing)
    p_citing.add_argument("paper_id", help="论文 ID（目录名 / UUID / DOI）")
    p_citing.add_argument("--ws", type=str, default=None, help="限定工作区范围")

    # --- shared-refs ---
    p_sr = sub.add_parser("shared-refs", help="共同参考文献分析")
    p_sr.set_defaults(func=cmd_shared_refs)
    p_sr.add_argument("paper_ids", nargs="+", help="论文 ID（至少 2 个）")
    p_sr.add_argument("--min", type=int, default=None, help="最少共引次数（默认 2）")
    p_sr.add_argument("--ws", type=str, default=None, help="限定工作区范围")

    # --- topics ---
    p_topics = sub.add_parser("topics", help="BERTopic 主题建模与探索")
    p_topics.set_defaults(func=cmd_topics)
    p_topics.add_argument("--build", action="store_true", help="构建主题模型")
    p_topics.add_argument("--rebuild", action="store_true", help="清空旧模型目录后重建主题模型")
    p_topics.add_argument("--reduce", type=int, default=None, metavar="N", help="快速合并主题到 N 个（不重新聚类）")
    p_topics.add_argument(
        "--merge", type=str, default=None, metavar="IDS", help="手动合并主题，格式: 1,6,14+3,5（用+分隔组）"
    )
    p_topics.add_argument("--topic", type=int, default=None, metavar="ID", help="查看指定主题的论文（-1 查看 outlier）")
    _add_result_limit_arg(p_topics, "返回条数")
    p_topics.add_argument("--min-topic-size", type=int, default=None, help="最小聚类大小（覆盖 config）")
    p_topics.add_argument("--nr-topics", type=int, default=None, help="目标主题数（覆盖 config，0=auto, -1=不合并）")
    p_topics.add_argument("--viz", action="store_true", help="生成 HTML 可视化图表（6 张）")

    # --- backfill-abstract ---
    p_bf = sub.add_parser("backfill-abstract", help="补全缺失的 abstract（支持 DOI 官方抓取）")
    p_bf.set_defaults(func=cmd_backfill_abstract)
    p_bf.add_argument("--dry-run", action="store_true", help="预览，不写文件")
    p_bf.add_argument("--doi-fetch", action="store_true", help="从出版商网页抓取官方 abstract（覆盖现有）")

    # --- rename ---
    p_rename = sub.add_parser("rename", help="根据 JSON 元数据重命名论文文件")
    p_rename.set_defaults(func=cmd_rename)
    p_rename.add_argument("paper_id", nargs="?", help="论文 ID（省略则需 --all）")
    p_rename.add_argument("--all", action="store_true", help="重命名所有文件名不正确的论文")
    p_rename.add_argument("--dry-run", action="store_true", help="预览，不实际重命名")

    # --- audit ---
    p_audit = sub.add_parser("audit", help="审计已入库论文的数据质量")
    p_audit.set_defaults(func=cmd_audit)
    p_audit.add_argument("--severity", choices=["error", "warning", "info"], help="只显示指定严重级别的问题")

    # --- repair ---
    p_repair = sub.add_parser("repair", help="修复论文元数据（手动指定 title/DOI，跳过 MD 解析）")
    p_repair.set_defaults(func=cmd_repair)
    p_repair.add_argument("paper_id", help="论文 ID（目录名 / UUID / DOI）")
    p_repair.add_argument("--title", required=True, help="正确的论文标题")
    p_repair.add_argument("--doi", default="", help="已知 DOI（加速 API 查询）")
    p_repair.add_argument("--author", default="", help="一作全名")
    p_repair.add_argument("--year", type=int, default=None, help="发表年份")
    p_repair.add_argument("--no-api", action="store_true", help="跳过 API 查询，仅用提供的信息")
    p_repair.add_argument("--dry-run", action="store_true", help="预览，不实际修改")

    # --- explore ---
    p_explore = sub.add_parser("explore", help="多维文献探索（OpenAlex 拉取 + 嵌入 + 聚类）")
    p_explore.set_defaults(func=cmd_explore)
    p_explore_sub = p_explore.add_subparsers(dest="explore_action", required=True)

    p_ef = p_explore_sub.add_parser("fetch", help="从 OpenAlex 拉取论文（多维度 filter）")
    p_ef.add_argument("--issn", default=None, help="期刊 ISSN（如 0022-1120）")
    p_ef.add_argument("--concept", default=None, help="OpenAlex concept ID（如 C62520636）")
    p_ef.add_argument("--topic-id", default=None, help="OpenAlex topic ID")
    p_ef.add_argument("--author", default=None, help="OpenAlex author ID")
    p_ef.add_argument("--institution", default=None, help="OpenAlex institution ID")
    p_ef.add_argument("--keyword", default=None, help="标题/摘要关键词搜索")
    p_ef.add_argument("--source-type", default=None, help="来源类型（journal/conference/repository）")
    p_ef.add_argument("--oa-type", default=None, help="论文类型（article/review 等）")
    p_ef.add_argument("--min-citations", type=int, default=None, help="最小引用量")
    p_ef.add_argument("--name", help="探索库名称（默认从 filter 推导）")
    p_ef.add_argument("--year-range", help="年份过滤（如 2020-2025）")
    p_ef.add_argument("--incremental", action="store_true", help="增量更新（追加新论文）")
    p_ef.add_argument("--limit", type=int, default=None, help="最多拉取的论文数量上限（不设则无限）")

    p_ee = p_explore_sub.add_parser("embed", help="为探索库生成语义向量")
    p_ee.add_argument("--name", required=True, help="探索库名称")
    p_ee.add_argument("--rebuild", action="store_true", help="清空后重建")

    p_et = p_explore_sub.add_parser("topics", help="探索库主题建模")
    p_et.add_argument("--name", required=True, help="探索库名称")
    p_et.add_argument("--build", action="store_true", help="构建主题模型")
    p_et.add_argument("--rebuild", action="store_true", help="重建主题模型")
    p_et.add_argument("--topic", type=int, default=None, help="查看指定主题的论文")
    _add_result_limit_arg(p_et, "返回条数")
    p_et.add_argument("--min-topic-size", type=int, default=None, help="最小聚类大小（默认 30）")
    p_et.add_argument("--nr-topics", type=int, default=None, help="目标主题数（默认自然聚类）")

    p_es = p_explore_sub.add_parser("search", help="探索库搜索（语义/关键词/融合）")
    p_es.add_argument("--name", required=True, help="探索库名称")
    p_es.add_argument("query", nargs="+", help="查询文本")
    _add_result_limit_arg(p_es, "返回条数")
    p_es.add_argument(
        "--mode", choices=["semantic", "keyword", "unified"], default="semantic", help="搜索模式（默认 semantic）"
    )

    p_ev = p_explore_sub.add_parser("viz", help="生成全部可视化（HTML）")
    p_ev.add_argument("--name", required=True, help="探索库名称")

    p_el = p_explore_sub.add_parser("list", help="列出所有探索库")

    p_ei = p_explore_sub.add_parser("info", help="查看探索库信息")
    p_ei.add_argument("--name", default=None, help="探索库名称（省略列出全部）")

    # --- export ---
    p_export = sub.add_parser("export", help="导出论文或文档（BibTeX / RIS / Markdown / DOCX）")
    p_export.set_defaults(func=cmd_export)
    p_export_sub = p_export.add_subparsers(dest="export_action", required=True)

    p_eb = p_export_sub.add_parser("bibtex", help="导出 BibTeX 格式（LaTeX 引用）")
    p_eb.add_argument("paper_ids", nargs="*", help="论文目录名（可多个）")
    p_eb.add_argument("--all", action="store_true", help="导出全部论文")
    p_eb.add_argument("--year", type=str, default=None, help="年份过滤：2023 / 2020-2024")
    p_eb.add_argument("--journal", type=str, default=None, help="期刊名过滤（模糊匹配）")
    p_eb.add_argument("-o", "--output", type=str, default=None, help="输出文件路径（省略则输出到屏幕）")

    p_er = p_export_sub.add_parser("ris", help="导出 RIS 格式（Zotero / Endnote / Mendeley 导入）")
    p_er.add_argument("paper_ids", nargs="*", help="论文目录名（可多个）")
    p_er.add_argument("--all", action="store_true", help="导出全部论文")
    p_er.add_argument("--year", type=str, default=None, help="年份过滤：2023 / 2020-2024")
    p_er.add_argument("--journal", type=str, default=None, help="期刊名过滤（模糊匹配）")
    p_er.add_argument("-o", "--output", type=str, default=None, help="输出文件路径（省略则输出到屏幕）")

    p_em = p_export_sub.add_parser("markdown", help="导出 Markdown 文献列表（可直接粘贴到文档）")
    p_em.add_argument("paper_ids", nargs="*", help="论文目录名（可多个）")
    p_em.add_argument("--all", action="store_true", help="导出全部论文")
    p_em.add_argument("--year", type=str, default=None, help="年份过滤：2023 / 2020-2024")
    p_em.add_argument("--journal", type=str, default=None, help="期刊名过滤（模糊匹配）")
    p_em.add_argument("--bullet", action="store_true", help="使用无序列表（默认有序）")
    p_em.add_argument(
        "--style",
        type=str,
        default="apa",
        help="引用格式：apa（默认）/ vancouver / chicago-author-date / mla / <自定义>",
    )
    p_em.add_argument("-o", "--output", type=str, default=None, help="输出文件路径（省略则输出到屏幕）")

    p_ed = p_export_sub.add_parser("docx", help="将 Markdown 文本导出为 Word DOCX 文件")
    p_ed.add_argument("--input", "-i", type=str, default=None, help="输入 Markdown 文件路径（省略则从 stdin 读取）")
    p_ed.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="输出 .docx 文件路径（默认读 workspace_docx_output_path，即 <workspace>/_system/output/output.docx）",
    )
    p_ed.add_argument("--title", type=str, default=None, help="文档标题（可选，插入为一级标题）")

    # --- ws (workspace) ---
    p_ws = sub.add_parser("ws", help="工作区论文子集管理")
    p_ws.set_defaults(func=cmd_ws)
    p_ws_sub = p_ws.add_subparsers(dest="ws_action", required=True)

    p_ws_init = p_ws_sub.add_parser("init", help="初始化工作区")
    p_ws_init.add_argument("name", help="工作区名称（workspace/ 下的子目录名）")

    p_ws_add = p_ws_sub.add_parser("add", help="添加论文到工作区")
    p_ws_add.add_argument("name", help="工作区名称")
    p_ws_add.add_argument("paper_refs", nargs="*", help="论文引用（UUID / 目录名 / DOI）")
    p_ws_add_batch = p_ws_add.add_mutually_exclusive_group()
    p_ws_add_batch.add_argument("--search", dest="add_search", type=str, default=None, help="按搜索结果批量添加")
    p_ws_add_batch.add_argument("--topic", dest="add_topic", type=int, default=None, help="按主题 ID 批量添加")
    p_ws_add_batch.add_argument("--all", dest="add_all", action="store_true", default=False, help="添加全库论文")
    _add_result_limit_arg(p_ws_add, "限制 --search 返回条数")
    _add_filter_args(p_ws_add)

    p_ws_rm = p_ws_sub.add_parser("remove", help="从工作区移除论文")
    p_ws_rm.add_argument("name", help="工作区名称")
    p_ws_rm.add_argument("paper_refs", nargs="+", help="论文引用（UUID / 目录名 / DOI）")

    p_ws_list = p_ws_sub.add_parser("list", help="列出所有工作区")

    p_ws_show = p_ws_sub.add_parser("show", help="查看工作区中的论文")
    p_ws_show.add_argument("name", help="工作区名称")

    p_ws_search = p_ws_sub.add_parser("search", help="在工作区内搜索")
    p_ws_search.add_argument("name", help="工作区名称")
    p_ws_search.add_argument("query", nargs="+", help="查询文本")
    _add_result_limit_arg(p_ws_search, "返回条数")
    p_ws_search.add_argument(
        "--mode", choices=["unified", "keyword", "semantic"], default="unified", help="搜索模式（默认 unified）"
    )
    _add_filter_args(p_ws_search)

    p_ws_rename = p_ws_sub.add_parser("rename", help="重命名工作区")
    p_ws_rename.add_argument("old_name", help="当前工作区名称")
    p_ws_rename.add_argument("new_name", help="新工作区名称")

    p_ws_export = p_ws_sub.add_parser("export", help="导出工作区论文 BibTeX")
    p_ws_export.add_argument("name", help="工作区名称")
    p_ws_export.add_argument("-o", "--output", type=str, default=None, help="输出文件路径")
    _add_filter_args(p_ws_export)

    # --- import-endnote ---
    p_ie = sub.add_parser("import-endnote", help="从 Endnote XML/RIS 导入论文元数据")
    p_ie.set_defaults(func=cmd_import_endnote)
    p_ie.add_argument("files", nargs="+", help="Endnote 导出文件（.xml 或 .ris）")
    p_ie.add_argument("--no-api", action="store_true", help="跳过 API 查询，仅用文件中的元数据")
    p_ie.add_argument("--dry-run", action="store_true", help="预览，不实际导入")
    p_ie.add_argument("--no-convert", action="store_true", help="跳过 PDF → paper.md 转换（默认自动转换）")

    # --- import-zotero ---
    p_iz = sub.add_parser("import-zotero", help="从 Zotero 导入论文元数据和 PDF")
    p_iz.set_defaults(func=cmd_import_zotero)
    p_iz.add_argument("--local", metavar="SQLITE_PATH", help="使用本地 zotero.sqlite")
    p_iz.add_argument("--api-key", help="Zotero API key")
    p_iz.add_argument("--library-id", help="Zotero library ID")
    p_iz.add_argument("--library-type", choices=["user", "group"], help="Library 类型（默认 user）")
    p_iz.add_argument("--collection", metavar="KEY", help="仅导入指定 collection")
    p_iz.add_argument("--item-type", nargs="+", help="限定 item 类型（如 journalArticle conferencePaper）")
    p_iz.add_argument("--list-collections", action="store_true", help="列出所有 collections 后退出")
    p_iz.add_argument("--no-pdf", action="store_true", help="跳过 PDF 下载/复制")
    p_iz.add_argument("--no-api", action="store_true", help="跳过学术 API 查询")
    p_iz.add_argument("--dry-run", action="store_true", help="预览，不实际导入")
    p_iz.add_argument("--no-convert", action="store_true", help="跳过 PDF → paper.md 转换")
    p_iz.add_argument("--import-collections", action="store_true", help="将 Zotero collections 创建为工作区")

    # --- attach-pdf ---
    p_ap = sub.add_parser("attach-pdf", help="为已入库论文补充 PDF 并生成 paper.md")
    p_ap.set_defaults(func=cmd_attach_pdf)
    p_ap.add_argument("paper_id", help="论文 ID（目录名 / UUID / DOI）")
    p_ap.add_argument("pdf_path", help="PDF 文件路径")
    p_ap.add_argument("--dry-run", action="store_true", help="预览将要执行的操作，不实际运行")

    # --- citation-check ---
    p_cc = sub.add_parser("citation-check", help="验证文本中的引用是否在本地知识库中")
    p_cc.set_defaults(func=cmd_citation_check)
    p_cc.add_argument("file", nargs="?", default=None, help="待检查的文件路径（省略则从 stdin 读取）")
    p_cc.add_argument("--ws", type=str, default=None, help="在指定工作区范围内验证")

    # --- migrate ---
    p_migrate = sub.add_parser(
        "migrate",
        help="迁移控制面板（status / plan / run / verify / cleanup / finalize / upgrade / recover）",
    )
    p_migrate.set_defaults(func=cmd_migrate)
    p_migrate_sub = p_migrate.add_subparsers(dest="migrate_action", required=True)

    p_migrate_status = p_migrate_sub.add_parser("status", help="查看 instance metadata 和 migration.lock 状态")
    p_migrate_status.set_defaults(func=cmd_migrate)

    p_migrate_plan = p_migrate_sub.add_parser("plan", help="生成非执行型 migration plan 并写入 journal")
    p_migrate_plan.add_argument("--migration-id", default=None, help="指定 journal ID；默认自动生成")
    p_migrate_plan.set_defaults(func=cmd_migrate)

    p_migrate_recover = p_migrate_sub.add_parser("recover", help="显式恢复迁移控制状态")
    p_migrate_recover.add_argument("--clear-lock", action="store_true", help="显式清除 migration.lock")
    p_migrate_recover.set_defaults(func=cmd_migrate)

    p_migrate_verify = p_migrate_sub.add_parser("verify", help="刷新 verify.json 并执行最小控制面验证")
    p_migrate_verify.add_argument("--migration-id", default=None, help="指定 journal ID；默认使用最新一个")
    p_migrate_verify.set_defaults(func=cmd_migrate)

    p_migrate_cleanup = p_migrate_sub.add_parser("cleanup", help="在 verify 通过后执行安全 cleanup 评估")
    p_migrate_cleanup.add_argument("--migration-id", default=None, help="指定 journal ID；默认使用最新一个")
    p_migrate_cleanup.add_argument(
        "--confirm", action="store_true", help="显式确认 cleanup 执行；当前阶段默认不会删除数据"
    )
    p_migrate_cleanup.set_defaults(func=cmd_migrate)

    p_migrate_finalize = p_migrate_sub.add_parser(
        "finalize",
        help="按固化规则完成迁移收口（workspace 索引迁移 + cleanup + verify）",
    )
    p_migrate_finalize.add_argument("--migration-id", default=None, help="指定 journal ID；默认自动生成")
    p_migrate_finalize.add_argument("--confirm", action="store_true", help="确认执行最终收口流程")
    p_migrate_finalize.set_defaults(func=cmd_migrate)

    p_migrate_upgrade = p_migrate_sub.add_parser(
        "upgrade",
        help="一键执行受支持旧布局到当前 fresh layout 的迁移、验证和收口",
    )
    p_migrate_upgrade.add_argument("--migration-id", default=None, help="指定 journal ID；默认自动生成")
    p_migrate_upgrade.add_argument("--confirm", action="store_true", help="确认执行完整迁移升级流程")
    p_migrate_upgrade.set_defaults(func=cmd_migrate)

    p_migrate_run = p_migrate_sub.add_parser("run", help="执行受支持的显式 migration store")
    p_migrate_run.add_argument(
        "--store",
        required=True,
        choices=["citation_styles", "toolref", "explore", "proceedings", "spool", "papers", "workspace"],
        help="本次执行的 store",
    )
    p_migrate_run.add_argument("--migration-id", default=None, help="指定 journal ID；默认自动生成")
    p_migrate_run.add_argument("--confirm", action="store_true", help="确认执行会写入目标目录的数据复制")
    p_migrate_run.set_defaults(func=cmd_migrate)

    # --- setup ---
    p_setup = sub.add_parser(
        "setup",
        help="环境检测与安装向导",
        description="默认进入交互式安装向导；使用 `check` 子命令仅做环境诊断。",
    )
    p_setup.set_defaults(func=cmd_setup)
    p_setup_sub = p_setup.add_subparsers(dest="setup_action")
    p_setup_check = p_setup_sub.add_parser("check", help="检查环境状态")
    p_setup_check.add_argument("--lang", choices=["en", "zh"], default="zh", help="输出语言（zh 或 en，默认 zh）")

    # --- backup ---
    p_backup = sub.add_parser("backup", help="rsync 增量备份", description="rsync 增量备份")
    p_backup.set_defaults(func=cmd_backup)
    p_backup_sub = p_backup.add_subparsers(dest="backup_action", required=True)

    p_backup_list = p_backup_sub.add_parser("list", help="列出已配置的备份目标")
    del p_backup_list  # no extra args needed

    p_backup_run = p_backup_sub.add_parser("run", help="执行指定备份目标")
    p_backup_run.add_argument("target", help="备份目标名称（来自 config backup.targets）")
    p_backup_run.add_argument("--dry-run", action="store_true", help="预演模式，只展示 rsync 计划而不实际传输")

    # --- fsearch ---
    p_fsearch = sub.add_parser("fsearch", help="联邦搜索：同时搜索主库、proceedings、explore 库和 arXiv")
    p_fsearch.set_defaults(func=cmd_fsearch)
    p_fsearch.add_argument("query", nargs="+", help="检索词")
    p_fsearch.add_argument(
        "--scope",
        type=str,
        default="main",
        help="搜索范围（逗号分隔）：main / proceedings / explore:NAME / explore:* / arxiv（默认 main）",
    )
    _add_result_limit_arg(p_fsearch, "每个来源最多返回 N 条（默认 10）")

    # --- proceedings ---
    p_proc = sub.add_parser("proceedings", help="论文集辅助命令（apply-split 等）")
    p_proc.set_defaults(func=cmd_proceedings)
    p_proc_sub = p_proc.add_subparsers(dest="proceedings_action", required=True)

    p_proc_apply = p_proc_sub.add_parser("apply-split", help="对已准备好的 proceedings 应用 split_plan.json")
    p_proc_apply.add_argument("proceeding_dir", help="proceedings 目录路径")
    p_proc_apply.add_argument("split_plan", help="split_plan.json 路径")

    p_proc_clean_candidates = p_proc_sub.add_parser(
        "build-clean-candidates", help="为已拆分的 proceedings 生成 clean_candidates.json"
    )
    p_proc_clean_candidates.add_argument("proceeding_dir", help="proceedings 目录路径")

    p_proc_apply_clean = p_proc_sub.add_parser("apply-clean", help="对已拆分的 proceedings 应用 clean_plan.json")
    p_proc_apply_clean.add_argument("proceeding_dir", help="proceedings 目录路径")
    p_proc_apply_clean.add_argument("clean_plan", help="clean_plan.json 路径")

    # --- arxiv ---
    p_arxiv = sub.add_parser("arxiv", help="arXiv 检索与拉取工具")
    p_arxiv_sub = p_arxiv.add_subparsers(dest="arxiv_action", required=True)

    p_arxiv_search = p_arxiv_sub.add_parser("search", help="搜索 arXiv 预印本")
    p_arxiv_search.set_defaults(func=cmd_arxiv_search)
    p_arxiv_search.add_argument("query", nargs="*", help="检索词（可省略，配合 --category 使用）")
    _add_result_limit_arg(p_arxiv_search, "最多返回 N 条（默认 10）")
    p_arxiv_search.add_argument("--category", type=str, default="", help="arXiv 分类，如 physics.flu-dyn")
    p_arxiv_search.add_argument(
        "--sort", choices=["relevance", "recent"], default="relevance", help="排序方式（默认 relevance）"
    )

    p_arxiv_fetch = p_arxiv_sub.add_parser("fetch", help="下载 arXiv PDF，可选直接入库")
    p_arxiv_fetch.set_defaults(func=cmd_arxiv_fetch)
    p_arxiv_fetch.add_argument("arxiv_ref", help="arXiv ID、arXiv:ID、abs URL 或 pdf URL")
    p_arxiv_fetch.add_argument("--ingest", action="store_true", help="下载后直接走 ingest pipeline 入库")
    p_arxiv_fetch.add_argument("--force", action="store_true", help="覆盖已有同名 PDF 或强制 pipeline 处理")
    p_arxiv_fetch.add_argument("--dry-run", action="store_true", help="预览将要执行的操作")

    # --- websearch ---
    p_web = sub.add_parser("websearch", help="实时网页搜索 (Bing via GUILessBingSearch)")
    p_web.set_defaults(func=cmd_websearch)
    p_web.add_argument("query", nargs="+", help="搜索查询词")
    p_web.add_argument("--count", type=int, default=10, help="返回结果数量（默认 10）")

    # --- webextract ---
    p_wext = sub.add_parser("webextract", help="网页内容提取 (qt-web-extractor)")
    p_wext.set_defaults(func=cmd_webextract)
    p_wext.add_argument("url", help="要提取的网页 URL")
    p_wext.add_argument("--pdf", action="store_true", help="目标为 PDF 文件")
    p_wext.add_argument("--full", action="store_true", help="输出完整提取结果，不截断")
    p_wext.add_argument("--max-chars", type=int, default=4000, help="预览模式最大输出字符数（默认 4000）")

    # --- ingest-link ---
    p_ingest_link = sub.add_parser("ingest-link", help="抓取渲染后的网页/在线 PDF，并按文档流程直接入库")
    p_ingest_link.set_defaults(func=cmd_ingest_link)
    p_ingest_link.add_argument("urls", nargs="+", help="一个或多个网页/在线 PDF URL")
    p_ingest_link.add_argument("--dry-run", action="store_true", help="预览将要执行的操作")
    p_ingest_link.add_argument("--force", action="store_true", help="强制重新处理生成的文档")
    p_ingest_link.add_argument("--pdf", action="store_true", help="仅在自动识别不稳时，提示 webextract 按 PDF 模式抓取")
    p_ingest_link.add_argument("--no-index", action="store_true", help="仅入库，不执行 embed/index")
    p_ingest_link.add_argument("--json", action="store_true", help="输出抓取结果摘要 JSON")

    # --- patent-fetch ---
    p_patent_fetch = sub.add_parser(
        "patent-fetch",
        help="下载专利 PDF 到 <patent inbox>",
        description="下载专利 PDF 到 <patent inbox>",
    )
    p_patent_fetch.set_defaults(func=cmd_patent_fetch)
    p_patent_fetch.add_argument(
        "id_or_url",
        help="专利公开号（如 US20240176406A1）或专利页面 URL",
    )

    # --- patent-search ---
    p_patent = sub.add_parser(
        "patent-search",
        help="USPTO 专利搜索（PPUBS，无需 API Key）",
        description="USPTO 专利搜索（PPUBS，无需 API Key）；如启用 --fetch，下载到 <patent inbox>",
    )
    p_patent.set_defaults(func=cmd_patent_search)
    p_patent.add_argument("query", nargs="*", help='搜索查询词（PPUBS 字段语法如 ("keyword").title.）')
    p_patent.add_argument(
        "--application", "-a", type=str, default=None, help="按申请号查询详情（如 17123456），需配合 --source odp 使用"
    )
    p_patent.add_argument("--count", "-c", type=int, default=10, help="返回结果数量（默认 10）")
    p_patent.add_argument("--offset", "-o", type=int, default=0, help="分页偏移（默认 0）")
    p_patent.add_argument(
        "--source",
        type=str,
        choices=["ppubs", "odp"],
        default="ppubs",
        help="搜索源：ppubs（默认，无需 API Key）或 odp（需要 API Key）",
    )
    p_patent.add_argument(
        "--fetch", "-f", action="store_true", help="搜索后自动下载所有结果中的专利 PDF 到 <patent inbox>"
    )

    # --- insights ---
    p_insights = sub.add_parser("insights", help="研究行为分析：搜索热词、最常阅读论文等")
    p_insights.set_defaults(func=cmd_insights)
    p_insights.add_argument("--days", type=int, default=30, help="分析最近 N 天的数据（默认 30）")

    # --- metrics ---
    p_metrics = sub.add_parser("metrics", help="查看 LLM token 用量和调用统计")
    p_metrics.set_defaults(func=cmd_metrics)
    p_metrics.add_argument("--last", type=int, default=20, help="最近 N 条记录")
    p_metrics.add_argument("--category", default="llm", help="事件类别（llm/api/step，默认 llm）")
    p_metrics.add_argument("--since", default=None, help="起始时间（ISO 格式，如 2026-03-01）")
    p_metrics.add_argument("--summary", action="store_true", help="仅显示汇总统计")

    # --- style ---
    p_style = sub.add_parser("style", help="引用格式管理（列出 / 查看自定义格式）")
    p_style.set_defaults(func=cmd_style)
    p_style_sub = p_style.add_subparsers(dest="style_sub", required=True)

    p_style_list = p_style_sub.add_parser("list", help="列出所有可用引用格式")
    del p_style_list  # no extra args needed

    p_style_show = p_style_sub.add_parser("show", help="查看引用格式的格式化函数代码")
    p_style_show.add_argument("name", help="格式名称，如 jcp / apa / vancouver")

    # --- document ---
    p_doc = sub.add_parser("document", help="Office 文档工具（inspect 等）")
    p_doc.set_defaults(func=cmd_document)
    p_doc_sub = p_doc.add_subparsers(dest="doc_action", required=True)

    p_doc_inspect = p_doc_sub.add_parser("inspect", help="检查 Office 文档结构（DOCX / PPTX / XLSX）")
    p_doc_inspect.add_argument("file", help="文件路径")
    p_doc_inspect.add_argument(
        "--format",
        choices=["docx", "pptx", "xlsx"],
        default=None,
        help="文件格式（默认从扩展名推断）",
    )

    # --- diagram ---
    p_diagram = sub.add_parser("diagram", help="论文 → 可编辑科研图表（DOT/SVG / drawio XML / Mermaid）")
    p_diagram.set_defaults(func=cmd_diagram)
    p_diagram.add_argument("paper_id", nargs="?", help="论文 ID（目录名 / UUID / DOI）；与 --from-ir 二选一")
    p_diagram.add_argument(
        "--type",
        choices=["model_arch", "tech_route", "exp_setup"],
        default="model_arch",
        help="图表类型（默认 model_arch）",
    )
    p_diagram.add_argument(
        "--format",
        choices=["svg", "drawio", "dot", "mermaid"],
        default="svg",
        help="输出格式（默认 svg）",
    )
    p_diagram.add_argument(
        "--dump-ir",
        action="store_true",
        help="仅提取并保存 IR（JSON），不渲染",
    )
    p_diagram.add_argument(
        "--from-ir",
        type=str,
        default=None,
        help="从已有的 IR JSON 文件直接渲染（与 paper_id / --from-text 三选一）",
    )
    p_diagram.add_argument(
        "--from-text",
        type=str,
        default=None,
        help="从文字描述直接生成图表（与 paper_id / --from-ir 三选一）",
    )
    p_diagram.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="输出目录（默认读 workspace_figures_dir，即 <workspace>/_system/figures/）",
    )
    p_diagram.add_argument(
        "--critic",
        action="store_true",
        help="启用 Critic-Agent 闭环迭代自审（参考 PaperVizAgent 的 Critic-Visualizer loop）",
    )
    p_diagram.add_argument(
        "--critic-rounds",
        type=int,
        default=3,
        help="Critic 最大迭代轮次（默认 3，仅 --critic 时生效）",
    )

    # --- enrich-l3 ---
    p_l3 = sub.add_parser("enrich-l3", help="LLM 提取结论段写入 JSON")
    p_l3.set_defaults(func=cmd_enrich_l3)
    p_l3.add_argument("paper_id", nargs="?", help="论文 ID（省略则需 --all）")
    p_l3.add_argument("--all", action="store_true", help="处理 papers_dir 中所有论文")
    p_l3.add_argument("--force", action="store_true", help="强制重新提取（覆盖已有结果）")
    p_l3.add_argument("--inspect", action="store_true", help="展示提取过程详情")
    p_l3.add_argument("--max-retries", type=int, default=2, help="最大重试次数（默认 2）")

    # --- toolref ---
    p_tr = sub.add_parser("toolref", help="科学计算工具文档查阅（fetch/show/search/list/use）")
    p_tr.set_defaults(func=cmd_toolref)
    p_tr_sub = p_tr.add_subparsers(dest="toolref_action", required=True)

    p_trf = p_tr_sub.add_parser("fetch", help="拉取工具文档（git clone → 提取 → 索引）")
    p_trf.add_argument("tool", help="工具名（qe/lammps/gromacs/openfoam/bioinformatics）")
    p_trf.add_argument("--version", default=None, help="版本号（如 7.5, 22Jul2025_update3）")
    p_trf.add_argument("--force", action="store_true", help="强制重新拉取并覆盖本地缓存")

    p_trs = p_tr_sub.add_parser("show", help="查看指定命令/参数的文档")
    p_trs.add_argument("tool", help="工具名")
    p_trs.add_argument("path", nargs="+", help="查找路径（如 pw ecutwfc）")

    p_trq = p_tr_sub.add_parser("search", help="全文搜索工具文档")
    p_trq.add_argument("tool", help="工具名")
    p_trq.add_argument("query", nargs="+", help="搜索关键词")
    _add_result_limit_arg(p_trq, "返回条数（默认 20）")
    p_trq.add_argument("--program", default=None, help="按程序过滤（如 pw.x）")
    p_trq.add_argument("--section", default=None, help="按 namelist/section 过滤（如 SYSTEM）")

    p_trl = p_tr_sub.add_parser("list", help="列出已有工具文档及版本")
    p_trl.add_argument("tool", nargs="?", default=None, help="工具名（省略列出全部）")

    p_tru = p_tr_sub.add_parser("use", help="切换工具文档的当前活跃版本")
    p_tru.add_argument("tool", help="工具名")
    p_tru.add_argument("version", help="目标版本号")

    # --- translate ---
    p_trans = sub.add_parser("translate", help="翻译论文 Markdown 到目标语言")
    p_trans.set_defaults(func=cmd_translate)
    p_trans.add_argument("paper_id", nargs="?", help="论文 ID（省略则需 --all）")
    p_trans.add_argument("--all", action="store_true", help="批量翻译所有论文")
    p_trans.add_argument("--lang", type=str, default=None, help="目标语言（默认读 config translate.target_lang）")
    p_trans.add_argument("--force", action="store_true", help="强制重新翻译（覆盖已有翻译）")
    p_trans.add_argument(
        "--portable",
        action="store_true",
        help="额外导出可移植翻译包（默认读 translation_bundle_root，即 workspace/_system/translation-bundles/；复制 images/）",
    )

    return parser
