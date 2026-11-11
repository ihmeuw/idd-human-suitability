"""Relative path fragments, ``paths.yaml`` key names, column names and enums.

No absolute path lives here. Absolute roots come from the gitignored ``paths.yaml`` through
``idd_human_suitability.paths``; this module names the keys and the fragments below them.
"""

from __future__ import annotations

from typing import Final

# Keys of paths.yaml
OUTPUT_ROOT_KEY: Final = "project_output_root"
"""Root of this project's output node."""

# Top-level folders of the output node: <project_output_root>/<folder>
REFERENCES_DIR: Final = "00-references"
RAW_DATA_DIR: Final = "01-raw_data"
PROCESSED_DATA_DIR: Final = "02-processed_data"
OUTPUT_DIR: Final = "03-output"

# Literature: <project_output_root>/<REFERENCES_DIR>/<LITERATURE_DIR>/
LITERATURE_DIR: Final = "habitability_refs"
LITERATURE_REVIEW_FILENAME: Final = (
    "Habitability & the Human Niche — Literature Review and Data Landscape.md"
)
LITERATURE_TEXT_DIR: Final = "txt"
"""Plain-text extractions of the papers; filenames match the review's reference list."""
LITERATURE_PDF_DIR: Final = "pdf"
