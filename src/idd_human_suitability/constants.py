"""Relative path fragments, ``paths.yaml`` key names, column names and enums.

No absolute path lives here. Absolute roots come from the gitignored ``paths.yaml`` through
``idd_human_suitability.paths``; this module names the keys and the fragments below them.
"""

from __future__ import annotations

from typing import Final

# Keys of paths.yaml
OUTPUT_ROOT_KEY: Final = "project_output_root"
"""Root of this project's output node."""
