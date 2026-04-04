# Proceedings Ingest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add proceedings-aware ingestion with a dedicated inbox, conservative auto-detection from the regular inbox, separate proceedings storage, and explicit `fsearch` support for a `proceedings` scope.

**Architecture:** Extend the ingest pipeline with a new proceedings path parallel to thesis and document handling. Store proceedings volumes and child papers under `data/proceedings/`, keep them out of the main paper registry, and add opt-in federated retrieval through `fsearch`. Start with keyword search support for proceedings and conservative heuristic segmentation so the first release closes the workflow without destabilizing existing paper ingest.

**Tech Stack:** Python 3.10+, argparse CLI, SQLite FTS5, existing ScholarAIO ingest/index infrastructure, pytest.

---

## File Map

- Create: `scholaraio/proceedings.py`
- Create: `scholaraio/ingest/proceedings.py`
- Create: `tests/test_proceedings.py`
- Modify: `scholaraio/config.py`
- Modify: `scholaraio/ingest/pipeline.py`
- Modify: `scholaraio/cli.py`
- Modify: `scholaraio/index.py`
- Modify: `README.md`
- Modify: `docs/guide/ingestion.md`

## Task 1: Add proceedings directories to configuration

**Files:**
- Modify: `scholaraio/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

Add a test next to the existing ensured-directory coverage that asserts `ensure_dirs()` creates:

```python
assert (tmp_path / "data" / "inbox-proceedings").exists()
assert (tmp_path / "data" / "proceedings").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n scholaraio python -m pytest tests/test_config.py -k ensure_dirs -v`
Expected: FAIL because the new proceedings directories are not created yet.

- [ ] **Step 3: Write minimal implementation**

Update the list of ensured directories in `scholaraio/config.py` so both new paths are created alongside the existing inboxes and data roots.

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n scholaraio python -m pytest tests/test_config.py -k ensure_dirs -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git -C /home/lzmo/repos/personal/scholaraio-issue-46 add scholaraio/config.py tests/test_config.py
git -C /home/lzmo/repos/personal/scholaraio-issue-46 commit -m "Add proceedings directories to config"
```

## Task 2: Add proceedings storage helpers and keyword index builder

**Files:**
- Create: `scholaraio/proceedings.py`
- Modify: `scholaraio/index.py`
- Test: `tests/test_proceedings.py`

- [ ] **Step 1: Write the failing test**

Add tests that create a fake proceedings volume with two child papers and assert:

```python
papers = list(iter_proceedings_papers(proceedings_root))
assert len(papers) == 2
assert {p["proceeding_title"] for p in papers} == {"Example Proceedings"}
```

Add a keyword-index test that builds a proceedings index and confirms a query returns only proceedings child rows.

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n scholaraio python -m pytest tests/test_proceedings.py -v`
Expected: FAIL because the helper module and proceedings index functions do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Implement focused helpers in `scholaraio/proceedings.py`:

- proceedings root/path resolution
- proceeding and child-paper metadata loading
- iteration over child papers

Add minimal proceedings keyword indexing to `scholaraio/index.py` or a small proceedings-specific helper section:

- create `proceedings_fts`
- store child-paper rows with proceeding metadata
- expose a `search_proceedings(...)` function returning the same basic result shape `cmd_fsearch` can normalize

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n scholaraio python -m pytest tests/test_proceedings.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git -C /home/lzmo/repos/personal/scholaraio-issue-46 add scholaraio/proceedings.py scholaraio/index.py tests/test_proceedings.py
git -C /home/lzmo/repos/personal/scholaraio-issue-46 commit -m "Add proceedings storage and keyword index helpers"
```

## Task 3: Add proceedings detection helpers

**Files:**
- Create: `scholaraio/ingest/proceedings.py`
- Modify: `scholaraio/ingest/pipeline.py`
- Test: `tests/test_proceedings.py`

- [ ] **Step 1: Write the failing test**

Add tests for:

- manual proceedings inbox forces proceedings mode
- regular inbox markdown with proceedings cues is classified as proceedings
- ordinary single-paper markdown is not classified as proceedings

Use compact fixtures that include patterns like `Proceedings of`, repeated DOI/title blocks, and TOC-like headings.

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n scholaraio python -m pytest tests/test_proceedings.py -k detect -v`
Expected: FAIL because no proceedings detection entry point exists yet.

- [ ] **Step 3: Write minimal implementation**

Implement `scholaraio/ingest/proceedings.py` with conservative helpers:

- `looks_like_proceedings_text(...)`
- `detect_proceedings_from_md(...)`
- optional LLM-assisted detection wrapper that safely falls back to heuristics when no key is available

Wire `scholaraio/ingest/pipeline.py` to call these helpers at the right point, parallel to thesis detection but without changing current thesis behavior.

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n scholaraio python -m pytest tests/test_proceedings.py -k detect -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git -C /home/lzmo/repos/personal/scholaraio-issue-46 add scholaraio/ingest/proceedings.py scholaraio/ingest/pipeline.py tests/test_proceedings.py
git -C /home/lzmo/repos/personal/scholaraio-issue-46 commit -m "Add proceedings detection helpers"
```

## Task 4: Add proceedings ingest writeout

**Files:**
- Create: `scholaraio/ingest/proceedings.py`
- Modify: `scholaraio/ingest/pipeline.py`
- Test: `tests/test_proceedings.py`

- [ ] **Step 1: Write the failing test**

Add a pipeline-level test that seeds a proceedings markdown fixture, runs the proceedings path, and asserts:

```python
assert (tmp_path / "data" / "proceedings").exists()
assert proceeding_meta["child_paper_count"] == 2
assert child_meta["proceeding_title"] == proceeding_meta["title"]
```

The first fixture can use heuristic chunk boundaries instead of a real 1000-page PDF.

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n scholaraio python -m pytest tests/test_proceedings.py -k ingest -v`
Expected: FAIL because no proceedings writer or pipeline path exists yet.

- [ ] **Step 3: Write minimal implementation**

Add proceedings pipeline helpers that:

- create a proceeding directory under `data/proceedings/`
- persist volume-level `meta.json`
- segment markdown into child paper chunks
- write each child paper into `papers/<Paper-Dir>/meta.json` and `paper.md`
- build or refresh the proceedings keyword index after successful ingest

Keep segmentation heuristic and deterministic in V1.

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n scholaraio python -m pytest tests/test_proceedings.py -k ingest -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git -C /home/lzmo/repos/personal/scholaraio-issue-46 add scholaraio/ingest/proceedings.py scholaraio/ingest/pipeline.py tests/test_proceedings.py
git -C /home/lzmo/repos/personal/scholaraio-issue-46 commit -m "Add proceedings ingest pipeline"
```

## Task 5: Process dedicated proceedings inbox and auto-route from main inbox

**Files:**
- Modify: `scholaraio/ingest/pipeline.py`
- Test: `tests/test_proceedings.py`

- [ ] **Step 1: Write the failing test**

Add tests that:

- files placed in `data/inbox-proceedings/` go directly to proceedings ingest
- files placed in `data/inbox/` and detected as proceedings are routed away from `data/papers/`
- ordinary papers in `data/inbox/` still go to `data/papers/`

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n scholaraio python -m pytest tests/test_proceedings.py -k route -v`
Expected: FAIL because the inbox routing logic does not yet support proceedings.

- [ ] **Step 3: Write minimal implementation**

Extend the inbox phase in `scholaraio/ingest/pipeline.py`:

- scan `data/inbox-proceedings/`
- process it with proceedings-specific steps
- add conservative auto-routing for regular inbox entries that detect as proceedings
- keep thesis/document inbox ordering explicit and unchanged for existing behavior

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n scholaraio python -m pytest tests/test_proceedings.py -k route -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git -C /home/lzmo/repos/personal/scholaraio-issue-46 add scholaraio/ingest/pipeline.py tests/test_proceedings.py
git -C /home/lzmo/repos/personal/scholaraio-issue-46 commit -m "Route proceedings through dedicated inbox flow"
```

## Task 6: Add `proceedings` scope to federated search

**Files:**
- Modify: `scholaraio/cli.py`
- Modify: `scholaraio/index.py`
- Test: `tests/test_cli_messages.py`
- Test: `tests/test_proceedings.py`

- [ ] **Step 1: Write the failing test**

Add tests that:

- `fsearch --scope proceedings` returns proceedings child papers
- `fsearch --scope main` does not return proceedings child papers
- the unknown-scope help text mentions `proceedings`
- results label proceedings origin clearly

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n scholaraio python -m pytest tests/test_proceedings.py tests/test_cli_messages.py -k fsearch -v`
Expected: FAIL because `cmd_fsearch` does not recognize the new scope.

- [ ] **Step 3: Write minimal implementation**

Update `cmd_fsearch` and parser help in `scholaraio/cli.py`:

- recognize `proceedings`
- query proceedings keyword search
- normalize result rows with source labels such as `proceedings:<volume>`
- keep current `main`, `explore:*`, and `arxiv` behavior unchanged

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n scholaraio python -m pytest tests/test_proceedings.py tests/test_cli_messages.py -k fsearch -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git -C /home/lzmo/repos/personal/scholaraio-issue-46 add scholaraio/cli.py scholaraio/index.py tests/test_proceedings.py tests/test_cli_messages.py
git -C /home/lzmo/repos/personal/scholaraio-issue-46 commit -m "Add proceedings scope to federated search"
```

## Task 7: Update user-facing docs

**Files:**
- Modify: `README.md`
- Modify: `docs/guide/ingestion.md`

- [ ] **Step 1: Write the failing doc expectation**

Add a short checklist in your working notes for the docs update:

- new `data/inbox-proceedings/`
- new `data/proceedings/`
- proceedings are excluded from default search
- `fsearch --scope proceedings` includes them

- [ ] **Step 2: Run a grep check to verify the docs are missing it**

Run: `rg -n "inbox-proceedings|data/proceedings|scope proceedings" README.md docs/guide/ingestion.md`
Expected: no matches for the new behavior.

- [ ] **Step 3: Write minimal implementation**

Document the new inbox, storage tree, and federated search scope without over-promising segmentation accuracy.

- [ ] **Step 4: Run the grep check to verify it passes**

Run: `rg -n "inbox-proceedings|data/proceedings|scope proceedings" README.md docs/guide/ingestion.md`
Expected: matches for all new concepts.

- [ ] **Step 5: Commit**

```bash
git -C /home/lzmo/repos/personal/scholaraio-issue-46 add README.md docs/guide/ingestion.md
git -C /home/lzmo/repos/personal/scholaraio-issue-46 commit -m "Document proceedings ingest workflow"
```

## Task 8: Final verification

**Files:**
- Verify: `tests/test_config.py`
- Verify: `tests/test_proceedings.py`
- Verify: `tests/test_cli_messages.py`
- Verify: touched production files

- [ ] **Step 1: Run focused tests**

Run:

```bash
conda run -n scholaraio python -m pytest tests/test_config.py tests/test_proceedings.py tests/test_cli_messages.py -v
```

Expected: PASS.

- [ ] **Step 2: Run the full suite**

Run:

```bash
conda run -n scholaraio python -m pytest
```

Expected: PASS with no new failures.

- [ ] **Step 3: Inspect git diff**

Run:

```bash
git -C /home/lzmo/repos/personal/scholaraio-issue-46 status --short
git -C /home/lzmo/repos/personal/scholaraio-issue-46 diff --stat HEAD~1..HEAD
```

Expected: only intended files are modified.

- [ ] **Step 4: Commit any remaining cleanup**

```bash
git -C /home/lzmo/repos/personal/scholaraio-issue-46 add <remaining-files>
git -C /home/lzmo/repos/personal/scholaraio-issue-46 commit -m "Finish proceedings ingest feature"
```
