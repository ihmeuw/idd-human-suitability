from __future__ import annotations

from typing import TYPE_CHECKING, Any

import cartopy.crs as ccrs
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pytest
from idd_spatial_analysis.constants import WGS84, WORLD_CYLINDRICAL_EQUAL_AREA
from idd_spatial_analysis.frame import BlockGrid, bbox_in_crs, grid_from_bounds
from matplotlib.figure import Figure
from shapely.geometry import box

from idd_human_suitability.lib.figures.maps import MAP_AXES_NAME, raster_map_with_admin_lines

if TYPE_CHECKING:
    from collections.abc import Iterator

ADMIN2_BOUNDS = (0.2, 0.1, 0.8, 0.9)
THIN, BOLD = 0.3, 2.5
OPTIONS: dict[str, Any] = {
    "bins": [0, 1, 2, 3],
    "display_resolution": 0.05,
    "resampling": "average",
    "legend_title": "units",
    "admin2_linewidth": THIN,
    "admin0_linewidth": BOLD,
}


@pytest.fixture
def grid() -> BlockGrid:
    bounds = bbox_in_crs((0.0, 0.0, 1.0, 1.0), WGS84, WORLD_CYLINDRICAL_EQUAL_AREA)
    return grid_from_bounds(bounds, 1000, WORLD_CYLINDRICAL_EQUAL_AREA)


@pytest.fixture
def admin2_gdf() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {"loc_id": [1, 2]}, geometry=[box(0.2, 0.1, 0.5, 0.9), box(0.5, 0.1, 0.8, 0.9)], crs=WGS84
    )


@pytest.fixture
def admin0_gdf() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {"ADM0_NAME": ["Here", "Far"]},
        geometry=[box(0.0, 0.0, 1.0, 1.0), box(40.0, 40.0, 41.0, 41.0)],
        crs=WGS84,
    )


@pytest.fixture(autouse=True)
def _close_figures() -> Iterator[None]:
    yield
    plt.close("all")


def _map_axes(fig: Any) -> Any:
    """The map axes; idd-figures attaches ``axes_by_name`` to the figures it builds."""
    return fig.axes_by_name[MAP_AXES_NAME]


def _linewidths(fig: Figure) -> list[float]:
    axes = _map_axes(fig)
    return [float(width) for coll in axes.collections for width in coll.get_linewidths()]


def test_extent_is_the_admin2_bounding_box(
    grid: BlockGrid, admin0_gdf: gpd.GeoDataFrame, admin2_gdf: gpd.GeoDataFrame
) -> None:
    array = np.full(grid.shape, 2.5, dtype=np.float32)
    fig = raster_map_with_admin_lines(
        array, grid, admin0_gdf=admin0_gdf, admin2_gdf=admin2_gdf, **OPTIONS
    )
    assert isinstance(fig, Figure)
    lon_min, lon_max, lat_min, lat_max = _map_axes(fig).get_extent(crs=ccrs.PlateCarree())
    np.testing.assert_allclose((lon_min, lat_min, lon_max, lat_max), ADMIN2_BOUNDS, atol=1e-6)


def test_raster_is_drawn_on_the_display_grid_with_its_values(
    grid: BlockGrid, admin0_gdf: gpd.GeoDataFrame, admin2_gdf: gpd.GeoDataFrame
) -> None:
    array = np.full(grid.shape, 2.5, dtype=np.float32)
    fig = raster_map_with_admin_lines(
        array, grid, admin0_gdf=admin0_gdf, admin2_gdf=admin2_gdf, **OPTIONS
    )
    images = _map_axes(fig).images
    assert len(images) == 1
    drawn = np.asarray(images[0].get_array(), dtype="float64")
    assert drawn.shape == (16, 12)
    np.testing.assert_allclose(drawn, 2.5)
    left, right, bottom, top = images[0].get_extent()
    np.testing.assert_allclose((left, bottom, right, top), ADMIN2_BOUNDS, atol=1e-6)


def test_sum_resampling_adds_up_the_source_pixels(
    grid: BlockGrid, admin0_gdf: gpd.GeoDataFrame, admin2_gdf: gpd.GeoDataFrame
) -> None:
    array = np.ones(grid.shape, dtype=np.float32)
    options = {**OPTIONS, "resampling": "sum", "bins": [0, 10, 50, 100]}
    fig = raster_map_with_admin_lines(
        array, grid, admin0_gdf=admin0_gdf, admin2_gdf=admin2_gdf, **options
    )
    drawn = np.asarray(_map_axes(fig).images[0].get_array(), dtype="float64")
    # a 0.05 degree cell near the equator covers about 5.57 km x 5.56 km of 1 km pixels
    np.testing.assert_allclose(np.nanmean(drawn), 0.05 * 0.05 * 111.32 * 111.31, rtol=0.03)


def test_admin2_lines_are_thin_and_admin0_lines_are_bold(
    grid: BlockGrid, admin0_gdf: gpd.GeoDataFrame, admin2_gdf: gpd.GeoDataFrame
) -> None:
    array = np.zeros(grid.shape, dtype=np.float32)
    fig = raster_map_with_admin_lines(
        array, grid, admin0_gdf=admin0_gdf, admin2_gdf=admin2_gdf, **OPTIONS
    )
    assert sorted(set(_linewidths(fig))) == [THIN, BOLD]


def test_admin0_units_outside_the_extent_draw_nothing(
    grid: BlockGrid, admin2_gdf: gpd.GeoDataFrame
) -> None:
    far = gpd.GeoDataFrame(
        {"ADM0_NAME": ["Far"]}, geometry=[box(40.0, 40.0, 41.0, 41.0)], crs=WGS84
    )
    array = np.zeros(grid.shape, dtype=np.float32)
    fig = raster_map_with_admin_lines(array, grid, admin0_gdf=far, admin2_gdf=admin2_gdf, **OPTIONS)
    assert set(_linewidths(fig)) == {THIN}


def test_polygons_in_another_crs_are_brought_to_lonlat(
    grid: BlockGrid, admin0_gdf: gpd.GeoDataFrame, admin2_gdf: gpd.GeoDataFrame
) -> None:
    array = np.zeros(grid.shape, dtype=np.float32)
    fig = raster_map_with_admin_lines(
        array,
        grid,
        admin0_gdf=admin0_gdf.to_crs(WORLD_CYLINDRICAL_EQUAL_AREA),
        admin2_gdf=admin2_gdf.to_crs(WORLD_CYLINDRICAL_EQUAL_AREA),
        **OPTIONS,
    )
    lon_min, lon_max, lat_min, lat_max = _map_axes(fig).get_extent(crs=ccrs.PlateCarree())
    np.testing.assert_allclose((lon_min, lat_min, lon_max, lat_max), ADMIN2_BOUNDS, atol=1e-6)


def test_legend_has_one_swatch_label_per_bin(
    grid: BlockGrid, admin0_gdf: gpd.GeoDataFrame, admin2_gdf: gpd.GeoDataFrame
) -> None:
    array = np.zeros(grid.shape, dtype=np.float32)
    fig = raster_map_with_admin_lines(
        array, grid, admin0_gdf=admin0_gdf, admin2_gdf=admin2_gdf, title="A title", **OPTIONS
    )
    texts = {text.get_text() for axes in fig.axes for text in axes.texts}
    assert {"0\u20131", "1\u20132", "2\u20133", "units", "A title"} <= texts


@pytest.mark.parametrize("which", ["admin0_gdf", "admin2_gdf"])
def test_polygons_without_crs_or_rows_raise(
    grid: BlockGrid, admin0_gdf: gpd.GeoDataFrame, admin2_gdf: gpd.GeoDataFrame, which: str
) -> None:
    array = np.zeros(grid.shape, dtype=np.float32)
    good = {"admin0_gdf": admin0_gdf, "admin2_gdf": admin2_gdf}
    no_crs = {**good, which: good[which].set_crs(None, allow_override=True)}
    with pytest.raises(ValueError, match=f"{which} carries no CRS"):
        raster_map_with_admin_lines(array, grid, **no_crs, **OPTIONS)
    empty = {**good, which: good[which].iloc[0:0]}
    with pytest.raises(ValueError, match=f"{which} is empty"):
        raster_map_with_admin_lines(array, grid, **empty, **OPTIONS)


def test_array_not_matching_the_grid_raises(
    grid: BlockGrid, admin0_gdf: gpd.GeoDataFrame, admin2_gdf: gpd.GeoDataFrame
) -> None:
    with pytest.raises(ValueError, match="does not end with the grid shape"):
        raster_map_with_admin_lines(
            np.zeros((3, 3), dtype=np.float32),
            grid,
            admin0_gdf=admin0_gdf,
            admin2_gdf=admin2_gdf,
            **OPTIONS,
        )
