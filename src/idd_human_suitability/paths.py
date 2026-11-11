"""Absolute roots from the gitignored ``paths.yaml``.

``paths.yaml`` is the only file in the repo that holds absolute paths. Everything else builds
paths as ``root(key) / <fragment from constants>``. Loading is a function, not top-level code,
so importing the package never requires ``paths.yaml``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_PATHS_FILE = Path(__file__).resolve().parents[2] / "paths.yaml"
_WRITE_KEY = "write"


class PathsFileMissingError(FileNotFoundError):
    """``paths.yaml`` is absent; the message says what to do."""


def load_paths(paths_file: Path | None = None) -> dict[str, Any]:
    """Read ``paths.yaml`` and return its mapping with every root as a ``Path``.

    A root left blank (``~`` in YAML) comes back as ``None``. ``write`` comes back as a list of
    key names (empty when absent or blank); pipeline code ignores it.
    """
    file = paths_file if paths_file is not None else _PATHS_FILE
    if not file.exists():
        msg = f"{file} missing. Run: cp paths.yaml.example paths.yaml; then edit."
        raise PathsFileMissingError(msg)
    with file.open() as handle:
        data: dict[str, Any] = yaml.safe_load(handle) or {}
    resolved: dict[str, Any] = {
        key: (Path(value) if key != _WRITE_KEY and isinstance(value, str) else value)
        for key, value in data.items()
    }
    write = resolved.get(_WRITE_KEY)
    if write is None:
        write = []
    if not isinstance(write, list) or not all(isinstance(key, str) for key in write):
        msg = f"{file}: write must be a list of key names, got {write!r}"
        raise TypeError(msg)
    resolved[_WRITE_KEY] = write
    return resolved


def root(key: str, paths_file: Path | None = None) -> Path:
    """The absolute root stored under ``key`` in ``paths.yaml``.

    Raises ``KeyError`` when the key is absent or blank, naming the file to edit, so a missing
    root fails where it is asked for and not later as a path that does not exist.
    """
    paths = load_paths(paths_file)
    value = paths.get(key)
    if key == _WRITE_KEY or not isinstance(value, Path):
        file = paths_file if paths_file is not None else _PATHS_FILE
        msg = f"{file} has no root under {key!r}; see paths.yaml.example"
        raise KeyError(msg)
    return value
