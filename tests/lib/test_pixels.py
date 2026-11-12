from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pytest
from idd_spatial_analysis.constants import WORLD_CYLINDRICAL_EQUAL_AREA
from idd_spatial_analysis.frame import BlockGrid, grid_from_bounds

from idd_human_suitability.lib.pixels import pixels_to_table, stack_layers

if TYPE_CHECKING:
    import xarray as xr

PEOPLE = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], dtype=np.float32)
ZONE = np.array([[0, 7, 7], [3, 0, 3]], dtype=np.int32)


@pytest.fixture
def grid() -> BlockGrid:
    """Two rows by three columns of 100 m pixels with its lower-left corner at the origin."""
    return grid_from_bounds((0.0, 0.0, 300.0, 200.0), 100, WORLD_CYLINDRICAL_EQUAL_AREA)


@pytest.fixture
def pixels_ds(grid: BlockGrid) -> xr.Dataset:
    return stack_layers({"people": PEOPLE, "zone": ZONE}, grid)


def test_stack_layers_puts_each_layer_on_y_x_with_pixel_centre_coordinates(
    pixels_ds: xr.Dataset,
) -> None:
    assert dict(pixels_ds.sizes) == {"y": 2, "x": 3}
    assert list(pixels_ds.data_vars) == ["people", "zone"]
    np.testing.assert_array_equal(pixels_ds["x"].to_numpy(), [50.0, 150.0, 250.0])
    np.testing.assert_array_equal(pixels_ds["y"].to_numpy(), [150.0, 50.0])
    np.testing.assert_array_equal(pixels_ds["people"].to_numpy(), PEOPLE)
    np.testing.assert_array_equal(pixels_ds["zone"].to_numpy(), ZONE)
    assert pixels_ds["people"].dims == ("y", "x")


def test_stack_layers_keeps_dtypes_and_does_not_copy(pixels_ds: xr.Dataset) -> None:
    assert pixels_ds["people"].dtype == np.float32
    assert pixels_ds["zone"].dtype == np.int32
    assert np.shares_memory(pixels_ds["people"].to_numpy(), PEOPLE)


def test_stack_layers_records_the_grid_in_the_attributes(
    pixels_ds: xr.Dataset, grid: BlockGrid
) -> None:
    assert pixels_ds.attrs["crs"] == grid.crs
    assert pixels_ds.attrs["transform"] == [100.0, 0.0, 0.0, 0.0, -100.0, 200.0]


def test_stack_layers_value_at_a_coordinate_is_the_pixel_there(pixels_ds: xr.Dataset) -> None:
    assert float(pixels_ds["people"].sel(x=250.0, y=50.0)) == 6.0
    assert int(pixels_ds["zone"].sel(x=150.0, y=150.0)) == 7


def test_stack_layers_single_pixel_grid() -> None:
    one = grid_from_bounds((0.0, 0.0, 100.0, 100.0), 100, WORLD_CYLINDRICAL_EQUAL_AREA)
    single_ds = stack_layers({"people": np.array([[9.0]], dtype=np.float32)}, one)
    assert dict(single_ds.sizes) == {"y": 1, "x": 1}
    assert float(single_ds["people"].to_numpy()[0, 0]) == 9.0


def test_stack_layers_bad_inputs_raise(grid: BlockGrid) -> None:
    with pytest.raises(ValueError, match="layers is empty"):
        stack_layers({}, grid)
    with pytest.raises(
        ValueError, match=r"layer 'small' has shape \(2, 2\), the grid has \(2, 3\)"
    ):
        stack_layers({"people": PEOPLE, "small": np.zeros((2, 2))}, grid)
    with pytest.raises(ValueError, match="cannot be named 'x'"):
        stack_layers({"x": PEOPLE}, grid)


def test_pixels_to_table_has_one_row_per_pixel_in_raster_order(pixels_ds: xr.Dataset) -> None:
    table = pixels_to_table(pixels_ds)
    assert list(table.columns) == ["y", "x", "people", "zone"]
    assert table["y"].tolist() == [150.0, 150.0, 150.0, 50.0, 50.0, 50.0]
    assert table["x"].tolist() == [50.0, 150.0, 250.0, 50.0, 150.0, 250.0]
    assert table["people"].tolist() == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    assert table["zone"].tolist() == [0, 7, 7, 3, 0, 3]
    assert table.dtypes.astype(str).to_dict() == {
        "y": "float64",
        "x": "float64",
        "people": "float32",
        "zone": "int32",
    }


def test_pixels_to_table_keeps_only_pixels_in_a_zone(pixels_ds: xr.Dataset) -> None:
    table = pixels_to_table(pixels_ds, zone_variable="zone")
    assert table["zone"].tolist() == [7, 7, 3, 3]
    assert table["people"].tolist() == [2.0, 3.0, 4.0, 6.0]
    assert table["y"].tolist() == [150.0, 150.0, 50.0, 50.0]
    assert table["x"].tolist() == [150.0, 250.0, 50.0, 250.0]
    assert list(table.index) == [0, 1, 2, 3]
    assert table["people"].dtype == np.float32


def test_pixels_to_table_totals_match_the_arrays(pixels_ds: xr.Dataset) -> None:
    table = pixels_to_table(pixels_ds, zone_variable="zone")
    assert float(table["people"].sum()) == float(PEOPLE[ZONE > 0].sum())
    assert table.groupby("zone")["people"].sum().to_dict() == {3: 10.0, 7: 5.0}


def test_pixels_to_table_keeps_nan_values(grid: BlockGrid) -> None:
    people = PEOPLE.copy()
    people[0, 1] = np.nan
    table = pixels_to_table(
        stack_layers({"people": people, "zone": ZONE}, grid), zone_variable="zone"
    )
    assert np.isnan(table["people"].iloc[0])
    assert len(table) == 4


def test_pixels_to_table_zone_variable_errors(pixels_ds: xr.Dataset, grid: BlockGrid) -> None:
    with pytest.raises(KeyError, match="no variable 'nope'"):
        pixels_to_table(pixels_ds, zone_variable="nope")
    with pytest.raises(TypeError, match="'people' must hold integer zone ids"):
        pixels_to_table(pixels_ds, zone_variable="people")
    empty_ds = stack_layers({"people": PEOPLE, "zone": np.zeros_like(ZONE)}, grid)
    with pytest.raises(ValueError, match="no pixel is in a zone"):
        pixels_to_table(empty_ds, zone_variable="zone")


def test_pixels_to_table_variable_off_the_grid_raises(pixels_ds: xr.Dataset) -> None:
    with_extra = pixels_ds.assign(profile=("x", np.array([1.0, 2.0, 3.0])))
    with pytest.raises(ValueError, match=r"variables not on \(y, x\): \['profile'\]"):
        pixels_to_table(with_extra)
