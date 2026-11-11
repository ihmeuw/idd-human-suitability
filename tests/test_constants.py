"""The path constants, ``paths.yaml.example`` and the no-absolute-path rule stay in step."""

from __future__ import annotations

from pathlib import Path

import yaml

from idd_human_suitability import constants

_EXAMPLE = Path(__file__).resolve().parents[1] / "paths.yaml.example"
_WRITE_KEY = "write"
_PLACEHOLDER_PREFIX = "/your/"


def _string_constants() -> dict[str, str]:
    return {
        name: value
        for name, value in vars(constants).items()
        if name.isupper() and isinstance(value, str)
    }


def _root_keys() -> set[str]:
    return {value for name, value in _string_constants().items() if name.endswith("_KEY")}


def _example() -> dict[str, object]:
    loaded: dict[str, object] = yaml.safe_load(_EXAMPLE.read_text())
    return loaded


def test_there_are_root_keys_to_check() -> None:
    assert "project_output_root" in _root_keys()


def test_every_root_key_is_documented_in_the_example() -> None:
    assert _root_keys() - set(_example()) == set()


def test_the_example_documents_no_key_the_code_does_not_name() -> None:
    assert set(_example()) - _root_keys() == {_WRITE_KEY}


def test_example_roots_are_placeholders_and_write_is_empty() -> None:
    example = _example()
    assert example[_WRITE_KEY] == []
    roots = {key: value for key, value in example.items() if key != _WRITE_KEY}
    not_placeholders = {
        key: value
        for key, value in roots.items()
        if not (isinstance(value, str) and value.startswith(_PLACEHOLDER_PREFIX))
    }
    assert not_placeholders == {}


def test_no_constant_is_an_absolute_or_home_path() -> None:
    offenders = {
        name: value
        for name, value in _string_constants().items()
        if value.startswith(("/", "~")) or ":\\" in value
    }
    assert offenders == {}
