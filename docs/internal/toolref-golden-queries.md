# Toolref Golden Queries

> Internal regression checklist for `scholaraio toolref`.
>
> Purpose:
> - protect high-frequency QE and LAMMPS lookups from ranking regressions
> - provide a concrete "production-ready enough" bar for future toolref changes
> - serve as a manual spot-check list after parser, indexing, or version-refresh work

## Scope

This checklist is intentionally narrow.

It does not try to prove full documentation completeness.
It protects the most important user-facing paths:

- `toolref show` exact lookup quality
- `toolref search` top-result quality
- alias resolution for command families
- reindex stability after `toolref fetch`

Current priority tools:

- Quantum ESPRESSO (`qe`)
- LAMMPS (`lammps`)
- Bioinformatics (`bioinformatics`)

## How To Use

Rebuild the active index first:

```bash
python -m scholaraio.cli toolref fetch qe --version 7.5
python -m scholaraio.cli toolref fetch lammps --version stable_2Aug2023_update3
python -m scholaraio.cli toolref fetch bioinformatics --version 2026-03-curated
```

Then run the queries below and compare the first result or direct target.

Pass rule:

- `show`: the expected page should be the direct match shown first
- `search`: the expected page should appear at rank 1 unless noted otherwise
- content should be specific enough to answer the query without immediately falling back to raw upstream docs

## QE Golden Queries

### Exact parameter lookup

```bash
python -m scholaraio.cli toolref show qe pw conv_thr
```

Expected:

- page: `pw.x/ELECTRONS/conv_thr`
- content explains SCF convergence threshold

```bash
python -m scholaraio.cli toolref show qe ph tr2_ph
```

Expected:

- page: `ph.x/INPUTPH/tr2_ph`

```bash
python -m scholaraio.cli toolref show qe pw ecutwfc
```

Expected:

- page: `pw.x/SYSTEM/ecutwfc`

### Search ranking

```bash
python -m scholaraio.cli toolref search qe conv_thr
```

Expected:

- rank 1: `pw.x/ELECTRONS/conv_thr`

```bash
python -m scholaraio.cli toolref search qe startingpot
```

Expected:

- `pw.x/ELECTRONS/startingpot` appears in the top block

### Program filter normalization

```bash
python -m scholaraio.cli toolref search qe ecutwfc --program pw
```

Expected:

- `pw` is normalized to `pw.x`
- top result belongs to `pw.x`

## LAMMPS Golden Queries

### Alias-driven command entry

```bash
python -m scholaraio.cli toolref show lammps fix_npt
```

Expected:

- page: `lammps/fix_nh`
- content clearly states aliases covering `fix nvt`, `fix npt`, `fix nph`

```bash
python -m scholaraio.cli toolref show lammps pair style eam
```

Expected:

- page: `lammps/pair_eam`
- content includes EAM family aliases such as `eam/alloy`

### Search ranking

```bash
python -m scholaraio.cli toolref search lammps fix npt
```

Expected:

- rank 1: `lammps/fix_nh`
- `fix_npt_asphere` and related variants may appear below, but should not outrank the main command page

```bash
python -m scholaraio.cli toolref search lammps pair style eam
```

Expected:

- rank 1: `lammps/pair_eam`

```bash
python -m scholaraio.cli toolref search lammps npt thermostat barostat
```

Expected:

- `lammps/fix_nh` should appear in the top block
- `Howto_barostat` may appear, but should not be the only useful result

## Reindex Sanity Checks

After any parser or ranking change, confirm:

```bash
python -m scholaraio.cli toolref list qe
python -m scholaraio.cli toolref list lammps
```

Expected:

- active QE version remains indexed
- active LAMMPS version remains indexed
- no fetch/reindex crash

Current observed healthy state after the latest parser/ranking fix:

- QE `7.5`: `1214` indexed pages
- LAMMPS `stable_2Aug2023_update3`: `980` indexed pages

## Bioinformatics Golden Queries

### Toolchain routing

```bash
python -m scholaraio.cli toolref search bioinformatics "read mapping nanopore"
```

Expected:

- rank 1: `minimap2/manual`

```bash
python -m scholaraio.cli toolref search bioinformatics "variant calling vcf"
```

Expected:

- top block contains `bcftools/mpileup` and `bcftools/call`

```bash
python -m scholaraio.cli toolref search bioinformatics "ultrafast bootstrap"
```

Expected:

- rank 1: `iqtree/ultrafast-bootstrap`

```bash
python -m scholaraio.cli toolref search bioinformatics "protein structure folding"
```

Expected:

- rank 1: `esmfold/huggingface-doc`

### Reindex sanity

```bash
python -m scholaraio.cli toolref list bioinformatics
```

Expected:

- active version remains `2026-03-curated`
- indexed page count remains complete after refresh

Current observed healthy state after the latest manifest/routing fix:

- Bioinformatics `2026-03-curated`: `12` indexed pages

## Non-Goals

This checklist does not currently validate:

- semantic/vector search
- every QE package beyond the most common command families
- every LAMMPS accelerator or package-specific variant
- documentation wording fidelity against upstream line-by-line source

If one of those becomes product-critical, add a new section instead of overloading this checklist.
