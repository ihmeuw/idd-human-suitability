from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pytest
import xarray as xr
from idd_spatial_analysis.constants import WGS84, WORLD_CYLINDRICAL_EQUAL_AREA
from idd_spatial_analysis.frame import bbox_in_crs, grid_from_bounds
from pyproj import Transformer

from idd_human_suitability import constants as c
from idd_human_suitability.lib.climate import climate_file, climate_on_grid, climate_window

if TYPE_CHECKING:
    from pathlib import Path

STEP = 0.5
CELLS = 20
YEAR = 2020
TEMPERATURE = "mean_temperature"
PRECIPITATION = "total_precipitation"


def cell_values() -> np.ndarray:
    """``row * 100 + col`` for a 20 x 20 grid of half-degree cells centred on (0, 0)."""
    rows, cols = np.indices((CELLS, CELLS))
    return (rows * 100 + cols).astype("float64")


def write_climate(  # noqa: PLR0913  (one argument per part of a synthetic file)
    base: Path,
    variable: str,
    values: np.ndarray,
    *,
    year: int = YEAR,
    file_year: int | None = None,
    latitude: np.ndarray | None = None,
    longitude: np.ndarray | None = None,
) -> Path:
    centres = (np.arange(CELLS) + 0.5) * STEP - CELLS * STEP / 2
    lat = centres[::-1] if latitude is None else latitude
    lon = centres if longitude is None else longitude
    dataset = xr.Dataset(
        {c.CLIMATE_VALUE_VARIABLE: (("year", "latitude", "longitude"), values[np.newaxis])},
        coords={
            "year": [year if file_year is None else file_year],
            "latitude": lat,
            "longitude": lon,
        },
    )
    path = base / c.CLIMATE_HISTORICAL_FILE.format(variable=variable, year=year)
    path.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_netcdf(path, engine="h5netcdf")
    return path


@pytest.fixture
def climate_root(tmp_path: Path) -> Path:
    """A climate root with two variables for one year on a small half-degree grid."""
    base = tmp_path / "climate"
    write_climate(base, TEMPERATURE, cell_values())
    write_climate(base, PRECIPITATION, cell_values() + 0.5)
    return base


def test_climate_file_follows_the_layout(climate_root: Path) -> None:
    path = climate_file(TEMPERATURE, YEAR, climate_root=climate_root)
    assert path == climate_root / "raw" / "historical" / TEMPERATURE / "2020_era5.nc"


@pytest.mark.parametrize(("variable", "year"), [(TEMPERATURE, 1900), ("nope", YEAR)])
def test_climate_file_missing_raises(climate_root: Path, variable: str, year: int) -> None:
    with pytest.raises(FileNotFoundError, match="no historical climate file"):
        climate_file(variable, year, climate_root=climate_root)


def test_climate_window_returns_the_covering_cells_plus_one_on_each_side(
    climate_root: Path,
) -> None:
    array, grid = climate_window(TEMPERATURE, YEAR, (0.1, 0.1, 1.2, 0.9), climate_root=climate_root)
    np.testing.assert_array_equal(array, cell_values()[7:11, 9:14].astype("float32"))
    assert array.dtype == np.float32
    assert grid.crs == WGS84
    np.testing.assert_allclose(grid.bounds, (-0.5, -0.5, 2.0, 1.5))
    np.testing.assert_allclose(grid.resolution, (STEP, STEP))


def test_climate_window_reads_the_requested_variable(climate_root: Path) -> None:
    bounds = (0.1, 0.1, 1.2, 0.9)
    temperature, _ = climate_window(TEMPERATURE, YEAR, bounds, climate_root=climate_root)
    precipitation, _ = climate_window(PRECIPITATION, YEAR, bounds, climate_root=climate_root)
    np.testing.assert_array_equal(precipitation - temperature, 0.5)


def test_climate_window_is_clipped_at_the_edge_of_the_file(climate_root: Path) -> None:
    array, grid = climate_window(
        TEMPERATURE, YEAR, (-9.0, 4.2, -4.6, 9.0), climate_root=climate_root
    )
    np.testing.assert_array_equal(array, cell_values()[0:3, 0:2].astype("float32"))
    np.testing.assert_allclose(grid.bounds, (-5.0, 3.5, -4.0, 5.0))


def test_climate_window_single_cell_bounds(climate_root: Path) -> None:
    array, _ = climate_window(TEMPERATURE, YEAR, (0.1, 0.1, 0.2, 0.2), climate_root=climate_root)
    assert array.shape == (3, 3)
    assert array[1, 1] == cell_values()[9, 10]


def test_climate_window_bounds_off_the_file_raise(climate_root: Path) -> None:
    with pytest.raises(ValueError, match="do not overlap"):
        climate_window(TEMPERATURE, YEAR, (50.0, 50.0, 51.0, 51.0), climate_root=climate_root)


def test_climate_window_file_holding_another_year_raises(tmp_path: Path) -> None:
    write_climate(tmp_path, TEMPERATURE, cell_values(), file_year=1999)
    with pytest.raises(ValueError, match=r"holds year\(s\) \[1999\], expected \[2020\]"):
        climate_window(TEMPERATURE, YEAR, (0.1, 0.1, 1.2, 0.9), climate_root=tmp_path)


def test_climate_window_south_to_north_latitude_raises(tmp_path: Path) -> None:
    ascending = (np.arange(CELLS) + 0.5) * STEP - CELLS * STEP / 2
    write_climate(tmp_path, TEMPERATURE, cell_values(), latitude=ascending)
    with pytest.raises(ValueError, match="latitude is not a regular axis running north to south"):
        climate_window(TEMPERATURE, YEAR, (0.1, 0.1, 1.2, 0.9), climate_root=tmp_path)


def test_climate_window_irregular_longitude_raises(tmp_path: Path) -> None:
    uneven = np.cumsum(np.linspace(0.3, 0.7, CELLS)) - 5.0
    write_climate(tmp_path, TEMPERATURE, cell_values(), longitude=uneven)
    with pytest.raises(ValueError, match="longitude is not a regular axis running west to east"):
        climate_window(TEMPERATURE, YEAR, (0.1, 0.1, 1.2, 0.9), climate_root=tmp_path)


def test_climate_on_grid_gives_each_pixel_the_cell_its_centre_is_in(climate_root: Path) -> None:
    bounds = bbox_in_crs((0.05, 0.05, 1.4, 0.9), WGS84, WORLD_CYLINDRICAL_EQUAL_AREA)
    grid = grid_from_bounds(bounds, 1000, WORLD_CYLINDRICAL_EQUAL_AREA)
    on_grid = climate_on_grid(TEMPERATURE, YEAR, grid, climate_root=climate_root)

    xs, ys = grid.pixel_centers()
    to_lonlat = Transformer.from_crs(WORLD_CYLINDRICAL_EQUAL_AREA, WGS84, always_xy=True)
    lon, lat = to_lonlat.transform(*np.meshgrid(xs, ys))
    cell_row = np.floor((CELLS * STEP / 2 - lat) / STEP).astype(int)
    cell_col = np.floor((lon + CELLS * STEP / 2) / STEP).astype(int)
    expected = (cell_row * 100 + cell_col).astype("float32")

    assert on_grid.shape == grid.shape
    assert on_grid.dtype == np.float32
    np.testing.assert_array_equal(on_grid, expected)
    assert len(np.unique(on_grid)) == 6  # 3 cells east-west by 2 north-south under the grid


def test_climate_on_grid_lonlat_grid_finer_than_the_climate_cells(climate_root: Path) -> None:
    grid = grid_from_bounds((0.0, 0.0, 1.0, 1.0), 0.25, WGS84)
    on_grid = climate_on_grid(PRECIPITATION, YEAR, grid, climate_root=climate_root)
    block = cell_values()[8:10, 10:12].astype("float32") + 0.5
    np.testing.assert_array_equal(on_grid, np.kron(block, np.ones((2, 2), dtype="float32")))


def test_climate_on_grid_pixels_outside_the_file_are_nan(climate_root: Path) -> None:
    grid = grid_from_bounds((4.0, 4.0, 6.0, 5.0), 0.5, WGS84)
    on_grid = climate_on_grid(TEMPERATURE, YEAR, grid, climate_root=climate_root)
    assert not np.isnan(on_grid[:, :2]).any()
    assert np.isnan(on_grid[:, 2:]).all()
