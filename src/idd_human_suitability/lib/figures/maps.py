"""Maps built on idd-figures: a raster with admin lines on top.

Everything drawn goes through ``idd_figures`` (``map_panel`` for the layout, raster, legend
and the thin line layer; ``disputed_boundary_painter`` for the bold one). idd-figures has no
call that draws two line layers of different weights above a raster, so the bold layer uses
its clipped-line painter with a solid style. A general "extra boundary layers" argument on
``map_panel`` would replace that; it is a request for idd-figures, not something to add here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from idd_figures.lib.bins import map_bin_labels
from idd_figures.lib.colors import binned_colormap
from idd_figures.lib.layouts.maps import map_panel
from idd_figures.lib.painters.maps import disputed_boundary_painter
from idd_spatial_analysis.constants import WGS84
from idd_spatial_analysis.crs import crs_equal
from idd_spatial_analysis.frame import grid_from_bounds
from idd_spatial_analysis.raster import reproject_to_grid

if TYPE_CHECKING:
    from collections.abc import Sequence

    import geopandas as gpd
    from idd_spatial_analysis.frame import BlockGrid
    from matplotlib.figure import Figure
    from numpy.typing import NDArray

MAP_AXES_NAME = "map"
"""Name of the map axes in the returned figure: ``fig.axes_by_name[MAP_AXES_NAME]``."""


def _lonlat(polygons_gdf: gpd.GeoDataFrame, name: str) -> gpd.GeoDataFrame:
    if polygons_gdf.crs is None:
        msg = f"{name} carries no CRS"
        raise ValueError(msg)
    if polygons_gdf.empty:
        msg = f"{name} is empty"
        raise ValueError(msg)
    if crs_equal(polygons_gdf.crs, WGS84):
        return polygons_gdf
    return polygons_gdf.to_crs(WGS84)


def raster_map_with_admin_lines(  # noqa: PLR0913  (keyword-only figure options)
    array: NDArray[Any],
    grid: BlockGrid,
    *,
    admin0_gdf: gpd.GeoDataFrame,
    admin2_gdf: gpd.GeoDataFrame,
    bins: Sequence[float],
    display_resolution: float,
    resampling: str,
    legend_title: str,
    title: str | None = None,
    base_cmap: str = "YlOrRd",
    admin2_linewidth: float = 0.2,
    admin0_linewidth: float = 1.4,
    line_color: str = "black",
    fig_width: float = 10.0,
) -> Figure:
    """A binned map of ``array`` with admin-2 lines (thin) and admin-0 lines (bold) on top.

    The map extent is the lon/lat bounding box of ``admin2_gdf``. ``array`` on ``grid`` (any
    CRS) is first put on a lon/lat grid of ``display_resolution`` degrees covering that box,
    using the rasterio method ``resampling`` (``average`` keeps the array's own units as a
    mean over each display cell; ``sum`` adds them up). ``bins`` are the bin edges in the
    array's units after resampling; values beyond the last edge take the last colour, and NaN
    pixels are left blank. Both line layers are clipped to the extent by the painters or the
    axes. Returns the figure; the caller shows or saves it.
    """
    admin2_lonlat = _lonlat(admin2_gdf, "admin2_gdf")
    admin0_lonlat = _lonlat(admin0_gdf, "admin0_gdf")
    edges = [float(edge) for edge in bins]
    lon_min, lat_min, lon_max, lat_max = (float(value) for value in admin2_lonlat.total_bounds)
    extent = [lon_min, lon_max, lat_min, lat_max]
    display_grid = grid_from_bounds((lon_min, lat_min, lon_max, lat_max), display_resolution, WGS84)
    display = reproject_to_grid(array, grid, display_grid, resampling=resampling)
    left, bottom, right, top = display_grid.bounds
    cmap, norm, colors = binned_colormap(edges, base_cmap=base_cmap)
    # idd-figures attaches axes_by_name to the figure it returns; matplotlib's Figure type
    # does not know it, so the panel stays untyped until it is handed back.
    panel = map_panel(
        extent=extent,
        raster=display,
        raster_extent=[left, right, bottom, top],
        cmap=cmap,
        norm=norm,
        colors=colors,
        bin_labels=map_bin_labels(edges),
        boundary_gdf=admin2_lonlat,
        boundary_style={"color": line_color, "linewidth": admin2_linewidth},
        ocean=False,
        title=title,
        legend_title=legend_title,
        fig_width=fig_width,
    )
    disputed_boundary_painter(
        panel.axes_by_name[MAP_AXES_NAME],
        admin0_lonlat,
        extent=extent,
        color=line_color,
        linewidth=admin0_linewidth,
        linestyle="-",
        zorder=4,
    )
    fig: Figure = panel
    return fig
