# Paper Ingestion

## Quick Ingest

Place PDFs in `data/inbox/` and run the pipeline:

```bash
scholaraio pipeline ingest
```

This will:

1. Convert PDFs to Markdown (via MinerU)
2. Extract metadata (regex + LLM)
3. Query APIs for completeness (Crossref, Semantic Scholar, OpenAlex)
4. Deduplicate by DOI
5. Move to `data/papers/` and update indexes

## Five Inboxes

| Inbox | Path | Behavior |
|-------|------|----------|
| Papers | `data/inbox/` | Standard pipeline with DOI dedup |
| Proceedings | `data/inbox-proceedings/` | Two-stage proceedings pipeline; first ingest creates `data/proceedings/<Volume>/` with `proceeding.md` + `split_candidates.json` and marks `split_status=pending_review` |
| Theses | `data/inbox-thesis/` | Skips DOI check, marks as thesis |
| Patents | `data/inbox-patent/` | Extracts publication number and deduplicates as patent |
| Documents | `data/inbox-doc/` | Skips DOI check, LLM-generated title/abstract |

Proceedings are also auto-detected conservatively from the regular `data/inbox/` path. When that happens, ScholarAIO routes the volume into `data/proceedings/` for review instead of `data/papers/`. Child papers are written under `data/proceedings/<Volume>/papers/` only after you review the split and run `scholaraio proceedings apply-split`.

## Proceedings Search

Proceedings child papers are not included in default main-library search. Use federated search when you want them:

```bash
scholaraio fsearch granular damping --scope proceedings
```

## Skip MinerU

Already have Markdown? Place `.md` files directly in the inbox — MinerU conversion is skipped.

## Pending Papers

Papers without DOI (that aren't theses) go to `data/pending/` for manual review. Add a DOI and re-run the pipeline to complete ingestion.

## External Import

```bash
# From Endnote
scholaraio import-endnote library.xml

# From Zotero
scholaraio import-zotero --api-key KEY --library-id ID
```
