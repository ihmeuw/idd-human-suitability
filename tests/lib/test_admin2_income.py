from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from idd_human_suitability.lib.admin2_income import load_admin2_gdppc

if TYPE_CHECKING:
    from pathlib import Path


def test_load_admin2_gdppc_returns_one_country_year_scenario(income_root: Path) -> None:
    frame = load_admin2_gdppc("ALP", 2020, "reference", income_root=income_root)
    assert list(frame.columns) == [
        "location_id",
        "gdppc_mean",
        "pop_masking_flag",
        "zero_pop_masking_flag",
    ]
    assert frame["location_id"].tolist() == [1001, 1002]
    assert frame["gdppc_mean"].tolist() == [100.25, 250.5]
    assert frame["pop_masking_flag"].tolist() == [False, False]
    assert frame["zero_pop_masking_flag"].tolist() == [False, True]
    assert frame.dtypes.astype(str).to_dict() == {
        "location_id": "int32",
        "gdppc_mean": "float64",
        "pop_masking_flag": "bool",
        "zero_pop_masking_flag": "bool",
    }
    assert list(frame.index) == [0, 1]


@pytest.mark.parametrize(
    ("iso3", "year", "scenario", "expected"),
    [
        ("ALP", 2020, "better", [110.0, 275.0]),
        ("ALP", 2021, "reference", [105.0, 260.0]),
        ("BET", 2020, "reference", [999.0]),
    ],
)
def test_load_admin2_gdppc_filters_on_all_three(
    income_root: Path, iso3: str, year: int, scenario: str, expected: list[float]
) -> None:
    frame = load_admin2_gdppc(iso3, year, scenario, income_root=income_root)
    assert frame["gdppc_mean"].tolist() == expected


@pytest.mark.parametrize(
    ("iso3", "year", "scenario"),
    [("ZZZ", 2020, "reference"), ("ALP", 1990, "reference"), ("ALP", 2020, "worse")],
)
def test_load_admin2_gdppc_no_rows_raises(
    income_root: Path, iso3: str, year: int, scenario: str
) -> None:
    with pytest.raises(ValueError, match="no rows for country"):
        load_admin2_gdppc(iso3, year, scenario, income_root=income_root)


def test_load_admin2_gdppc_repeated_unit_raises(income_root: Path) -> None:
    with pytest.raises(ValueError, match=r"appear more than once: \[3001\]"):
        load_admin2_gdppc("DUP", 2020, "reference", income_root=income_root)


def test_load_admin2_gdppc_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="GDP per capita table not found"):
        load_admin2_gdppc("ALP", 2020, "reference", income_root=tmp_path)
