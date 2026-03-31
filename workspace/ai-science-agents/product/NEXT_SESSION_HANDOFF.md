# Next Session Handoff

> Updated: 2026-03-31
>
> Purpose:
> - record what has been completed in the current `v1.3.0-scientific-skills` push
> - make the next Codex session resumable without rereading the whole branch

## What Was Completed

### 1. `toolref` hardening for mature tools

The following tools were pushed to a much more production-ready state:

- Quantum ESPRESSO
- LAMMPS
- GROMACS
- OpenFOAM
- Bioinformatics

Key outcomes:

- QE `show/search` now prefers exact program + parameter hits
- LAMMPS now resolves common natural aliases correctly:
  - `fix npt -> fix_nh`
  - `pair style eam -> pair_eam`
- GROMACS `mdp-options.rst` parsing was upgraded so important parameter pages are no longer skeletal:
  - `pcoupl`
  - `tcoupl`
  - `constraints`
- GROMACS natural-language search now maps better to parameter pages:
  - `Parrinello Rahman -> pcoupl`
  - `v-rescale thermostat -> tcoupl`
  - `nose-hoover thermostat -> tcoupl`
  - `constraints h-bonds -> constraints`
- OpenFOAM manifest coverage was expanded and actually pulled locally:
  - `simpleFoam`
  - `yPlus`
  - `wallShearStress`
  - `residuals`
- OpenFOAM manifest refresh logic was hardened so failed pages can be restored from existing cache instead of silently dropping previously fetched pages

Current local OpenFOAM state:

- `python -m scholaraio.cli toolref list openfoam`
- result: `2312 (current) — 16 页 [16/16 已索引]`

Current local Bioinformatics state:

- `python -m scholaraio.cli toolref list bioinformatics`
- result: `2026-03-curated (current) — 12 页 [12/12 已索引]`

Bioinformatics upgrades completed in this pass:

- added a fetch fallback path for manifest pages, so a primary upstream URL can fail without losing the page if a secondary official page still works
- `minimap2/manual` now has a GitHub README fallback
- added higher-value entry pages for:
  - `bcftools/call`
  - `bcftools/mpileup`
  - `iqtree/ultrafast-bootstrap`
- improved natural-language routing so these queries now hit useful targets:
  - `read mapping nanopore -> minimap2/manual`
  - `ultrafast bootstrap -> iqtree/ultrafast-bootstrap`
  - `variant calling vcf -> bcftools/mpileup`, `bcftools/call`
  - `protein structure folding -> esmfold/huggingface-doc`

### 2. Scientific skill architecture was clarified

The project now has a clearer split between:

- tool-specific scientific skills
- `toolref`
- runtime fallback behavior

New artifacts:

- `docs/internal/scientific-cli-skill-spec.md`
- `.claude/skills/scientific-runtime/SKILL.md`

`scientific-tool-onboarding` was updated to point to those two as the default standard.

### 3. Existing scientific skills were upgraded toward `toolref-first`

Updated skills:

- `quantum-espresso`
- `lammps`
- `gromacs`
- `openfoam`
- `bioinformatics`

They now more explicitly say:

- the agent should use `toolref` first
- the user should not be asked to maintain `toolref`
- coverage gaps are maintenance issues, not user obligations

## Verification Already Run

These passed in the current session:

- `python -m pytest tests/test_toolref.py -q`
- `python -m pytest tests/test_toolref.py tests/test_cli_messages.py -q`

Also manually validated:

- `toolref list/show/search` flows for QE
- `toolref list/show/search` flows for LAMMPS
- `toolref list/show/search` flows for GROMACS
- `toolref list/show/search` flows for OpenFOAM
- `toolref list/show/search` flows for Bioinformatics

## What Is Still Not Done

### 1. Scientific runtime protocol is documented, but not yet fully propagated

We now have:

- a spec
- a runtime skill
- onboarding references

But not every future scientific skill will automatically inherit this unless we keep enforcing it during onboarding and review.

### 2. Launch readiness still depends on demo execution, not only docs/toolref quality

The code/documentation/tooling side has moved forward, but launch-prep still needs real execution evidence:

- run logs
- validation tables
- final assets
- frozen numbers

## Recommended Next Step

Shift from toolref hardening back to **launch execution artifacts**.

Why:

- the five main scientific toolrefs are now in a usable release state
- the remaining release risk is no longer mostly docs routing, but real demo evidence and final assets
- launch-prep still needs frozen logs, plots, and validation notes

## First Commands For The Next Session

Start here:

```bash
git status --short
python -m scholaraio.cli toolref list qe
python -m scholaraio.cli toolref list lammps
python -m scholaraio.cli toolref list gromacs
python -m scholaraio.cli toolref list openfoam
python -m scholaraio.cli toolref list bioinformatics
python -m pytest tests/test_toolref.py tests/test_cli_messages.py -q
```

Then inspect:

- `workspace/ai-science-agents/launch-prep/STATUS_BOARD.md`
- `workspace/ai-science-agents/launch-prep/ROADMAP.md`
- `workspace/ai-science-agents/product/DEMO_SPECS.md`

## Next Session Goal

Use the now-stable scientific toolrefs to unblock launch materials:

- run or verify the highest-priority demos
- freeze run logs, validation numbers, and final notes
- update release-facing docs and assets with real evidence
