from __future__ import annotations

from pathlib import Path

import pytest

from idd_human_suitability import paths
from idd_human_suitability.paths import PathsFileMissingError, load_paths, root


def _write(tmp_path: Path, text: str) -> Path:
    file = tmp_path / "paths.yaml"
    file.write_text(text)
    return file


def test_load_paths_returns_roots_as_paths_and_write_as_list(tmp_path: Path) -> None:
    file = _write(
        tmp_path,
        "project_output_root: /somewhere/out\nprior_results_root: ~\nwrite: [project_output_root]\n",
    )
    loaded = load_paths(file)
    assert loaded["project_output_root"] == Path("/somewhere/out")
    assert loaded["prior_results_root"] is None
    assert loaded["write"] == ["project_output_root"]


@pytest.mark.parametrize("text", ["project_output_root: /somewhere/out\n", "write: ~\n", ""])
def test_load_paths_write_defaults_to_empty_list(tmp_path: Path, text: str) -> None:
    assert load_paths(_write(tmp_path, text))["write"] == []


def test_load_paths_missing_file_says_what_to_do(tmp_path: Path) -> None:
    with pytest.raises(PathsFileMissingError, match=r"cp paths\.yaml\.example paths\.yaml"):
        load_paths(tmp_path / "paths.yaml")


@pytest.mark.parametrize("write", ["project_output_root", "[1, 2]", "{a: b}"])
def test_load_paths_rejects_write_that_is_not_a_list_of_names(tmp_path: Path, write: str) -> None:
    with pytest.raises(TypeError, match="write must be a list of key names"):
        load_paths(_write(tmp_path, f"write: {write}\n"))


def test_load_paths_default_file_is_at_the_repo_root() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    assert repo_root / "paths.yaml" == paths._PATHS_FILE  # noqa: SLF001
    assert (repo_root / "pyproject.toml").exists()


def test_root_returns_the_path_under_a_key(tmp_path: Path) -> None:
    file = _write(tmp_path, "project_output_root: /somewhere/out\n")
    assert root("project_output_root", file) == Path("/somewhere/out")


@pytest.mark.parametrize("key", ["absent_root", "blank_root", "write"])
def test_root_raises_for_absent_blank_or_write_key(tmp_path: Path, key: str) -> None:
    file = _write(tmp_path, "project_output_root: /somewhere/out\nblank_root: ~\nwrite: []\n")
    with pytest.raises(KeyError, match=key):
        root(key, file)
