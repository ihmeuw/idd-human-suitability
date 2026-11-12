from __future__ import annotations

from typing import TYPE_CHECKING

import geopandas as gpd
import numpy as np
import pytest
from idd_spatial_analysis.constants import WGS84, WORLD_CYLINDRICAL_EQUAL_AREA
from idd_spatial_analysis.frame import grid_from_bounds
from shapely.geometry import box

from idd_human_suitability.lib.buildings import (
    available_bands,
    available_periods,
    blocks_for,
    building_raster,
    closest_period,
)
from tests.lib.conftest import BLOCK_EAST, BLOCK_WEST, RESOLUTION, SOURCE, tile_values

if TYPE_CHECKING:
    from pathlib import Path

FIVE_YEARLY = [f"{year}q1" for year in range(1975, 2030, 5)]
QUARTERLY = ["2020q2", "2020q3", "2020q4", "2021q1", "2021q2"]
BOTH = [BLOCK_WEST, BLOCK_EAST]


def test_available_periods_in_time_order_ignoring_other_folders(tiles_root: Path) -> None:
    assert available_periods(SOURCE, RESOLUTION, tiles_root=tiles_root) == [
        "2020q2",
        "2020q3",
        "2021q1",
    ]


def test_available_periods_unknown_source_raises(tiles_root: Path) -> None:
    with pytest.raises(FileNotFoundError, match="no building tiles for source 'nope'"):
        available_periods("nope", RESOLUTION, tiles_root=tiles_root)


def test_available_periods_folder_without_periods_raises(tiles_root: Path) -> None:
    (tiles_root / "100m" / "empty_source" / "readme").mkdir(parents=True)
    with pytest.raises(ValueError, match="holds no <year>q<quarter> folder"):
        available_periods("empty_source", RESOLUTION, tiles_root=tiles_root)


@pytest.mark.parametrize(
    ("year", "periods", "expected"),
    [
        (2020, QUARTERLY, "2020q2"),
        (2021, QUARTERLY, "2021q1"),
        (2030, QUARTERLY, "2021q2"),
        (1990, QUARTERLY, "2020q2"),
        (2020, FIVE_YEARLY, "2020q1"),
        (2022, FIVE_YEARLY, "2020q1"),
        (2023, FIVE_YEARLY, "2025q1"),
        (2022, ["2023q1", "2021q1"], "2021q1"),
        (2020, ["2019q4", "2020q2"], "2019q4"),
        (2020, ["2020q3"], "2020q3"),
    ],
)
def test_closest_period(year: int, periods: list[str], expected: str) -> None:
    assert closest_period(year, periods) == expected


def test_closest_period_empty_raises() -> None:
    with pytest.raises(ValueError, match="no periods"):
        closest_period(2020, [])


@pytest.mark.parametrize("period", ["2020", "2020q5", "q1", "2020Q1"])
def test_closest_period_malformed_period_raises(period: str) -> None:
    with pytest.raises(ValueError, match="not of the form"):
        closest_period(2020, [period])


@pytest.mark.parametrize(
    ("polygon", "expected"),
    [
        (box(0.001, 0.001, 0.004, 0.004), [BLOCK_WEST]),
        (box(0.011, 0.001, 0.015, 0.004), [BLOCK_EAST]),
        (box(0.001, 0.001, 0.015, 0.004), BOTH),
    ],
)
def test_blocks_for_lonlat_polygons(tiles_root: Path, polygon: object, expected: list[str]) -> None:
    polygons = gpd.GeoDataFrame(geometry=[polygon], crs=WGS84)
    assert blocks_for(polygons, RESOLUTION, tiles_root=tiles_root) == expected


def test_blocks_for_polygon_outside_every_block_raises(tiles_root: Path) -> None:
    polygons = gpd.GeoDataFrame(geometry=[box(20, 20, 21, 21)], crs=WGS84)
    with pytest.raises(ValueError, match="no block intersects"):
        blocks_for(polygons, RESOLUTION, tiles_root=tiles_root)


def test_blocks_for_missing_tile_index_raises(tiles_root: Path) -> None:
    polygons = gpd.GeoDataFrame(geometry=[box(0.001, 0.001, 0.004, 0.004)], crs=WGS84)
    with pytest.raises(FileNotFoundError, match="no tile index at 40 m"):
        blocks_for(polygons, 40, tiles_root=tiles_root)


@pytest.mark.parametrize(
    ("period", "blocks", "expected"),
    [
        ("2020q2", BOTH, ["density", "height"]),
        ("2021q1", BOTH, ["density"]),
        ("2021q1", [BLOCK_WEST], ["density", "height"]),
    ],
)
def test_available_bands_keeps_bands_present_for_every_block(
    tiles_root: Path, period: str, blocks: list[str], expected: list[str]
) -> None:
    assert (
        available_bands(SOURCE, period, blocks, resolution=RESOLUTION, tiles_root=tiles_root)
        == expected
    )


def test_available_bands_unknown_block_has_none(tiles_root: Path) -> None:
    assert (
        available_bands(
            SOURCE, "2020q2", ["B-0099X-0099Y"], resolution=RESOLUTION, tiles_root=tiles_root
        )
        == []
    )


def test_available_bands_bad_inputs_raise(tiles_root: Path) -> None:
    with pytest.raises(ValueError, match="blocks is empty"):
        available_bands(SOURCE, "2020q2", [], resolution=RESOLUTION, tiles_root=tiles_root)
    with pytest.raises(FileNotFoundError, match="2030q1"):
        available_bands(SOURCE, "2030q1", BOTH, resolution=RESOLUTION, tiles_root=tiles_root)


def test_building_raster_mosaics_the_blocks_onto_the_grid(tiles_root: Path) -> None:
    grid = grid_from_bounds((500.0, 200.0, 1500.0, 800.0), RESOLUTION, WORLD_CYLINDRICAL_EQUAL_AREA)
    array = building_raster(
        SOURCE, "2020q2", "density", BOTH, grid, resolution=RESOLUTION, tiles_root=tiles_root
    )
    side_by_side = np.hstack(
        [tile_values(BLOCK_WEST, "density"), tile_values(BLOCK_EAST, "density")]
    )
    np.testing.assert_array_equal(array, side_by_side[2:8, 5:15])
    assert array.dtype == np.float32
    assert array.shape == grid.shape


def test_building_raster_reads_the_requested_band(tiles_root: Path) -> None:
    grid = grid_from_bounds((0.0, 0.0, 1000.0, 1000.0), RESOLUTION, WORLD_CYLINDRICAL_EQUAL_AREA)
    array = building_raster(
        SOURCE, "2020q3", "height", [BLOCK_WEST], grid, resolution=RESOLUTION, tiles_root=tiles_root
    )
    np.testing.assert_array_equal(array, tile_values(BLOCK_WEST, "height"))


def test_building_raster_missing_tile_names_the_block(tiles_root: Path) -> None:
    grid = grid_from_bounds((500.0, 200.0, 1500.0, 800.0), RESOLUTION, WORLD_CYLINDRICAL_EQUAL_AREA)
    with pytest.raises(
        FileNotFoundError, match=rf"2021q1 height: no tile for blocks \['{BLOCK_EAST}'\]"
    ):
        building_raster(
            SOURCE, "2021q1", "height", BOTH, grid, resolution=RESOLUTION, tiles_root=tiles_root
        )


def test_building_raster_grid_off_the_tile_lattice_raises(tiles_root: Path) -> None:
    shifted = grid_from_bounds(
        (550.0, 200.0, 1550.0, 800.0), RESOLUTION, WORLD_CYLINDRICAL_EQUAL_AREA
    )
    with pytest.raises(ValueError, match="differs from the requested grid"):
        building_raster(
            SOURCE, "2020q2", "density", BOTH, shifted, resolution=RESOLUTION, tiles_root=tiles_root
        )


def test_building_raster_empty_blocks_raises(tiles_root: Path) -> None:
    grid = grid_from_bounds((0.0, 0.0, 1000.0, 1000.0), RESOLUTION, WORLD_CYLINDRICAL_EQUAL_AREA)
    with pytest.raises(ValueError, match="blocks is empty"):
        building_raster(
            SOURCE, "2020q2", "density", [], grid, resolution=RESOLUTION, tiles_root=tiles_root
        )
