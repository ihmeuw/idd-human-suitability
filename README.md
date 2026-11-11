# idd-human-suitability

Code to build and analyze global, gridded, time-varying habitability metrics
(climate-niche and HDI-style), 1950 to 2100.

## Layout

```
src/idd_human_suitability/
  constants.py     relative path fragments, paths.yaml key names, column names
  paths.py         reads paths.yaml (the only file with absolute paths)
  lib/             shared functions used across pipeline stages
  NN_<name>/       one subfolder per pipeline stage (added as stages exist)
tests/             mirrors the source tree; tests/qc/ holds pipeline QC checks
notebooks/
  vignettes/       committed walkthroughs; they only call functions from the package
  scratch/         exploration
scripts/           job-submission entry points
config/            generated YAML config (ignored by git)
```

## Setup

Requirements: Python 3.12 and [uv](https://docs.astral.sh/uv/) 0.12 or later.

```bash
uv venv --python 3.12
uv sync
.venv/bin/pre-commit install
.venv/bin/python -m ipykernel install --user --name idd-human-suitability \
    --display-name "idd-human-suitability (.venv)"
cp paths.yaml.example paths.yaml    # then edit the values for your machine
```

Code runs through `.venv/bin/python`; there is no environment to activate.

Three dependencies are sibling repositories under `ihmeuw`, installed from
GitHub over SSH and pinned to their `main` branch:

| Package | Used for | Visibility |
|---|---|---|
| [idd-spatial-analysis](https://github.com/ihmeuw/idd-spatial-analysis) | raster windows and mosaics, regridding, admin boundaries, zonal statistics | public |
| [idd-figures](https://github.com/ihmeuw/idd-figures) | figure templates and shared plotting functions | public |
| [idd-tools](https://github.com/ihmeuw/idd-tools) | output versioning, atomic IO, job orchestration | private |

`uv sync` therefore needs a GitHub SSH key, and read access to `idd-tools`.

Cluster job orchestration uses jobmon, which is an optional extra served only
by IHME's internal package index. Inside the IHME network:

```bash
uv sync --extra jobmon
```

Everything that does not submit cluster jobs works without it.

Generic spatial, figure and job-orchestration code is imported from these
packages and is not reimplemented here. This repository holds what is specific
to the project.

## Paths

No absolute path is committed. Every absolute root lives in `paths.yaml`,
which git ignores; `paths.yaml.example` is the template and documents each
key. Code builds a path as a root from `paths.yaml` joined to a relative
fragment from `constants.py`.

The output root (`project_output_root`) holds four top-level folders, to be
created on a new machine:

```
00-references/
01-raw_data/
02-processed_data/
03-output/
```

Most input data, and the large intermediate files, live outside this root.
Each such location is a separate key in `paths.yaml`.

## Tests and checks

```bash
.venv/bin/python -m pytest tests/ --ignore=tests/qc
.venv/bin/ruff check src/ tests/
.venv/bin/mypy src/
```

`tests/qc/` holds pipeline-level checks that need the real data and are run
after a stage completes, not as part of the unit tests.
