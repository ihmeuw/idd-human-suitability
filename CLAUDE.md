# idd-human-suitability — repo rules

## Purpose

Code to build and analyze global, gridded, time-varying habitability metrics
(climate-niche and HDI-style), 1950 to 2100.

## Environment scheme: venv-only (declared 2026-11-11)

This repo runs the **pure-uv scheme**: a project `.venv` at the repo root,
uv-managed interpreter, uv-managed dependencies. One scheme per repo, never
mixed.

- **Expected:** `./.venv` exists and is the only environment for this repo.
  Its interpreter is a uv-managed standalone CPython (`uv python install`),
  never a conda python. All code runs via `.venv/bin/python` — by absolute
  path in Slurm/jobmon task commands, no activation required.
- **Forbidden:** conda hosting of any kind for this repo — no conda env named
  after the repo, no `environment.yml`, no `UV_PROJECT_ENVIRONMENT=$CONDA_PREFIX`
  idiom.
- **Session start:** there is no env to activate. Use `.venv/bin/python`
  directly.
- **Sync idiom:** `uv sync --inexact --extra jobmon` day-to-day; plain
  `uv sync --extra jobmon` (exact) for clean rebuilds, vetted first with
  `uv sync --dry-run --extra jobmon`. Without `--extra jobmon` an exact sync
  removes the jobmon client.
- **jobmon:** orchestrators are submitted from the .venv, and worker command
  templates invoke `.venv/bin/python` by absolute path.
- Interpreter downloads are deliberate only: the user-level uv policy is
  `python-downloads = "manual"` — a plain `uv venv`/`uv sync` must never
  trigger a CPython download.

## Repo universe: import, do not reimplement

This repo is one of the idd-* repos. Generic work belongs to the sibling
packages; this repo imports it.

| Need | Sibling | Import |
|---|---|---|
| Spatial loading and operations: raster windows and mosaics, regridding, admin boundaries, zone masks, zonal statistics | `idd-spatial-analysis` | `idd_spatial_analysis` |
| Figures: templates, painters, layouts, palettes | `idd-figures` | `idd_figures` |
| Jobmon orchestration, output versioning (`idd-versions`), atomic IO | `idd-tools` | `idd_tools` |

- Before writing a function, check whether a sibling already has it. If it
  does, import it from the sibling directly. No wrapper modules that re-export.
- `src/idd_human_suitability/lib/` holds only what is specific to this
  project: which files, which variables, which region, and how they combine.
- A helper written here that turns out to be general-purpose is flagged for
  extraction to the sibling that should own it. Do not extract mid-session and
  do not edit a sibling from a session in this repo.
- Siblings are declared in `pyproject.toml` as git sources pinned to `main`
  (through `/consume-idd-repo`). They are installed at base. An extra of a
  sibling (`idd-figures[maps]`, `idd-spatial-analysis[rasterra]`, …) is
  requested when code here first uses the part that needs it, not before.
- Jobmon is this repo's own `jobmon` extra (`idd-tools[jobmon]`), declared
  exactly as idd-travel-time declares it: the extra, the `ihme` index block
  and the `jobmon_installer_ihme` source pin. The cluster env is synced with
  `--extra jobmon`; CI syncs without it, because a GitHub runner cannot reach
  the IHME index. `idd_tools.jobmon` needs the extra; `idd_tools.versions`
  does not.
- Third-party packages are added to `dependencies` when code here first
  imports them, with Bobby's approval, floors only.

## Layout

- `src/idd_human_suitability/constants.py`: relative path fragments,
  `paths.yaml` key names, column names, enums. No absolute paths.
- `src/idd_human_suitability/paths.py`: `load_paths()` / `root(key)`, the only
  readers of `paths.yaml`.
- `src/idd_human_suitability/lib/`: shared functions used across stages.
- `src/idd_human_suitability/NN_<name>/`: one subfolder per pipeline stage,
  added when a stage exists. A stage reads the previous stage's output node
  and does not import from another stage.
- `tests/`: mirrors the source tree; every directory is a package. Stage tests
  go in `tests/stage_NN_<name>/`, QC checks in `tests/qc/`.
- `notebooks/vignettes/`: committed walkthroughs. `notebooks/scratch/`:
  exploration.
- `scripts/`: job-submission entry points. `config/`: generated YAML, ignored.

## Paths

This repo is public. No absolute filesystem path is committed in any file.
Absolute roots live only in the gitignored `paths.yaml`; `paths.yaml.example`
is the committed template. Code builds every path as
`root(<key from constants>) / <fragment from constants>`. A path or a
`paths.yaml` key typed anywhere other than `constants.py` is a defect.
`paths.yaml` changes only when Bobby says so.

Outputs: the project output node is the `project_output_root` key. Its
top-level folders are `00-references`, `01-raw_data`, `02-processed_data` and
`03-output` (names in `constants.py`).

Most data does not live on the node (Bobby, 2026-11-11):

- **Inputs:** there are many, and most are not under `01-raw_data`. Each
  input location is its own root key in `paths.yaml`, read-only.
- **Big intermediates:** only some processed data is written to
  `02-processed_data`. The large intermediate files go to more than one other
  root. Each is its own key in `paths.yaml`, and a session writes there only
  when that key is in the file's `write:` list.

Never assume a dataset sits under the node: look up its root key.

Stage folders in the repo (`src/idd_human_suitability/NN_<name>/`) are a
different matter: none is created until there is a clear pipeline (Bobby,
2026-11-11).

## Notebooks

Notebooks only call repo functions. A notebook in `notebooks/vignettes/`
defines no function of its own: a function needed there is written in `lib/`
with a unit test first, then imported.

## Literature: `00-references` on the output node

The literature review and the full-text paper extractions are not kept in
this repo. They live under `<project_output_root>/00-references`
(`REFERENCES_DIR` in `constants.py`) and are added by Bobby. Consult them when
designing an analysis.

- Each source in the review carries a tag: **(R)** read in full, **(A)**
  abstract only, **(N)** not opened.
- Never upgrade a tag without reading the text.
- When a number is needed, take it from the paper text, not from memory, and
  cite the paper and the table or figure.
