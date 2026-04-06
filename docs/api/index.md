# API Reference

::: scholaraio.index
    options:
      members:
        - build_index
        - build_proceedings_index
        - search
        - search_proceedings

::: scholaraio.loader
    options:
      members:
        - load_l1
        - load_l2
        - load_l3
        - load_l4
        - load_notes
        - append_notes
        - enrich_toc
        - enrich_l3

::: scholaraio.export
    options:
      members:
        - meta_to_bibtex
        - export_bibtex

::: scholaraio.audit
    options:
      members:
        - Issue
        - audit_papers

::: scholaraio.workspace
    options:
      members:
        - create
        - add
        - remove
        - list_workspaces
        - read_paper_ids

::: scholaraio.papers
    options:
      members:
        - paper_dir
        - meta_path
        - md_path
        - iter_paper_dirs

::: scholaraio.proceedings
    options:
      members:
        - proceedings_db_path
        - iter_proceedings_dirs
        - iter_proceedings_papers

::: scholaraio.translate
    options:
      members:
        - translate_paper
        - batch_translate
        - detect_language
