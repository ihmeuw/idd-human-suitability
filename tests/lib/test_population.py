from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pytest
from idd_spatial_analysis.constants import WGS84, WORLD_CYLINDRICAL_EQUAL_AREA
from pyproj import Transformer

from idd_human_suitability.lib.population import population_file, population_window
from tests.lib.conftest import POPULATION_VERSION, RESOLUTION

if TYPE_CHECKING:
    from pathlib import Path


def test_population_file_follows_the_layout(population_root: Path) -> None:
    path = population_file(
        2020, resolution=RESOLUTION, version=POPULATION_VERSION, population_root=population_root
    )
    assert path == population_root / POPULATION_VERSION / "world_cylindrical_100" / "2020q1.tif"


@pytest.mark.parametrize(
    ("year", "resolution", "version"),
    [(1999, RESOLUTION, POPULATION_VERSION), (2020, 1000, POPULATION_VERSION), (2020, 100, "nope")],
)
def test_population_file_missing_raises(
    population_root: Path, year: int, resolution: int, version: str
) -> None:
    with pytest.raises(FileNotFoundError, match="no population raster"):
        population_file(
            year, resolution=resolution, version=version, population_root=population_root
        )


def test_population_window_in_the_rasters_crs_returns_exactly_those_pixels(
    population_root: Path,
) -> None:
    array, grid = population_window(
        (500.0, 500.0, 1000.0, 1500.0),
        2020,
        resolution=RESOLUTION,
        version=POPULATION_VERSION,
        bounds_crs=WORLD_CYLINDRICAL_EQUAL_AREA,
        population_root=population_root,
    )
    rows, cols = np.indices((20, 20))
    expected = (rows * 100 + cols)[5:15, 5:10].astype("float32")
    np.testing.assert_array_equal(array, expected)
    assert array.dtype == np.float32
    assert grid.bounds == (500.0, 500.0, 1000.0, 1500.0)
    assert grid.resolution == (100.0, 100.0)


def test_population_window_takes_lonlat_bounds_by_default(population_root: Path) -> None:
    to_lonlat = Transformer.from_crs(WORLD_CYLINDRICAL_EQUAL_AREA, WGS84, always_xy=True)
    left, bottom = to_lonlat.transform(500.0, 500.0)
    right, top = to_lonlat.transform(1000.0, 1500.0)
    array, grid = population_window(
        (left, bottom, right, top),
        2020,
        resolution=RESOLUTION,
        version=POPULATION_VERSION,
        population_root=population_root,
    )
    assert array.shape == (10, 5)
    assert array[0, 0] == 505.0
    np.testing.assert_allclose(grid.bounds, (500.0, 500.0, 1000.0, 1500.0), atol=1e-6)


def test_population_window_is_clipped_to_the_raster(population_root: Path) -> None:
    array, grid = population_window(
        (-5000.0, -5000.0, 300.0, 300.0),
        2020,
        resolution=RESOLUTION,
        version=POPULATION_VERSION,
        bounds_crs=WORLD_CYLINDRICAL_EQUAL_AREA,
        population_root=population_root,
    )
    assert array.shape == (3, 3)
    assert grid.bounds == (0.0, 0.0, 300.0, 300.0)


def test_population_window_outside_the_raster_raises(population_root: Path) -> None:
    with pytest.raises(ValueError, match="do not overlap"):
        population_window(
            (50_000.0, 50_000.0, 60_000.0, 60_000.0),
            2020,
            resolution=RESOLUTION,
            version=POPULATION_VERSION,
            bounds_crs=WORLD_CYLINDRICAL_EQUAL_AREA,
            population_root=population_root,
        )
