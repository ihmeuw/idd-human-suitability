"""Building tiles: which periods and bands exist, and one band mosaicked onto a grid.

Tiles live at ``<building_tiles_root>/<resolution>m/<source>/<period>/<block>_<band>.tif``,
with periods named ``<year>q<quarter>``. The tile index, the block lookup and the mosaic are
``idd_spatial_analysis``; this module knows only the layout.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from idd_spatial_analysis.crs import crs_equal
from idd_spatial_analysis.frame import blocks_intersecting, load_tile_index
from idd_spatial_analysis.raster import mosaic

from idd_human_suitability import constants as c
from idd_human_suitability.paths import root

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    import geopandas as gpd
    from idd_spatial_analysis.frame import BlockGrid
    from numpy.typing import NDArray

_PERIOD = re.compile(r"^(\d{4})q([1-4])$")
_QUARTERS = 4
_TILE_SUFFIX = ".tif"


def _tiles_root(tiles_root: Path | None) -> Path:
    return Path(tiles_root) if tiles_root is not None else root(c.BUILDING_TILES_ROOT_KEY)


def _quarter_index(period: str) -> int:
    """Quarters since year 0, so periods compare and subtract as integers."""
    match = _PERIOD.match(period)
    if match is None:
        msg = f"period {period!r} is not of the form <year>q<quarter>"
        raise ValueError(msg)
    return int(match.group(1)) * _QUARTERS + int(match.group(2)) - 1


def available_periods(source: str, resolution: int, *, tiles_root: Path | None = None) -> list[str]:
    """Periods that have a folder for ``source`` at ``resolution`` metres, in time order.

    Raises ``FileNotFoundError`` when the source has no folder at that resolution and
    ``ValueError`` when the folder holds no period.
    """
    folder = _tiles_root(tiles_root) / c.BUILDING_SOURCE_DIR.format(
        resolution=resolution, source=source
    )
    if not folder.is_dir():
        msg = f"no building tiles for source {source!r} at {resolution} m: {folder}"
        raise FileNotFoundError(msg)
    periods = [
        entry.name for entry in folder.iterdir() if entry.is_dir() and _PERIOD.match(entry.name)
    ]
    if not periods:
        msg = f"{folder} holds no <year>q<quarter> folder"
        raise ValueError(msg)
    return sorted(periods, key=_quarter_index)


def closest_period(year: int, periods: Iterable[str]) -> str:
    """The period nearest in time to the first quarter of ``year``.

    The reference point is ``<year>q1`` because that is when the population rasters are dated.
    When two periods are equally near, the earlier one is returned.
    """
    candidates = sorted(set(periods), key=_quarter_index)
    if not candidates:
        msg = "no periods to choose from"
        raise ValueError(msg)
    target = year * _QUARTERS
    return min(candidates, key=lambda period: abs(_quarter_index(period) - target))


def blocks_for(
    polygons_gdf: gpd.GeoDataFrame, resolution: int, *, tiles_root: Path | None = None
) -> list[str]:
    """Keys of the tile blocks at ``resolution`` metres that touch any of the polygons, sorted."""
    index_path = _tiles_root(tiles_root) / c.TILE_INDEX_FILE.format(resolution=resolution)
    if not index_path.exists():
        msg = f"no tile index at {resolution} m: {index_path}"
        raise FileNotFoundError(msg)
    tiles = load_tile_index(index_path)
    return [str(key) for key in blocks_intersecting(tiles, polygons_gdf)]


def _tile_path(  # noqa: PLR0913  (one argument per part of the file name)
    source: str, period: str, block_key: str, band: str, *, resolution: int, tiles_root: Path | None
) -> Path:
    return _tiles_root(tiles_root) / c.BUILDING_TILE_FILE.format(
        resolution=resolution, source=source, period=period, block_key=block_key, band=band
    )


def available_bands(
    source: str,
    period: str,
    blocks: Sequence[str],
    *,
    resolution: int,
    tiles_root: Path | None = None,
) -> list[str]:
    """Bands that have a tile for every one of ``blocks`` in ``period``, sorted.

    A band missing for some block is left out: mosaicking it would leave an unexplained hole.
    Raises ``ValueError`` when ``blocks`` is empty and ``FileNotFoundError`` when the period
    folder does not exist.
    """
    if not blocks:
        msg = "blocks is empty"
        raise ValueError(msg)
    folder = _tiles_root(tiles_root) / c.BUILDING_PERIOD_DIR.format(
        resolution=resolution, source=source, period=period
    )
    if not folder.is_dir():
        msg = f"no tiles for {source!r} in {period!r} at {resolution} m: {folder}"
        raise FileNotFoundError(msg)
    per_block: list[set[str]] = []
    for block_key in blocks:
        prefix = f"{block_key}_"
        per_block.append(
            {
                entry.name[len(prefix) : -len(_TILE_SUFFIX)]
                for entry in folder.glob(f"{prefix}*{_TILE_SUFFIX}")
            }
        )
    return sorted(set.intersection(*per_block))


def building_raster(  # noqa: PLR0913  (keyword-only read options)
    source: str,
    period: str,
    band: str,
    blocks: Sequence[str],
    grid: BlockGrid,
    *,
    resolution: int,
    tiles_root: Path | None = None,
) -> NDArray[np.float32]:
    """One band of ``source`` in ``period`` on ``grid``, mosaicked from the tiles of ``blocks``.

    ``grid`` must lie on the tiles' lattice (same CRS, resolution and pixel edges), which is
    the case for a window of the population raster at the same resolution. Raises
    ``FileNotFoundError`` naming the blocks without a tile, and ``ValueError`` when the mosaic
    does not come back on ``grid`` exactly: a silently shifted raster would misalign every
    later overlay.
    """
    if not blocks:
        msg = "blocks is empty"
        raise ValueError(msg)
    paths = [
        _tile_path(source, period, key, band, resolution=resolution, tiles_root=tiles_root)
        for key in blocks
    ]
    missing = [key for key, path in zip(blocks, paths, strict=True) if not path.exists()]
    if missing:
        msg = f"{source} {period} {band}: no tile for blocks {missing}"
        raise FileNotFoundError(msg)
    array, out_grid = mosaic(paths, grid.bounds)
    same_lattice = (
        crs_equal(out_grid.crs, grid.crs)
        and out_grid.shape == grid.shape
        and np.allclose(np.array(out_grid.transform[:6]), np.array(grid.transform[:6]))
    )
    if not same_lattice:
        msg = (
            f"{source} {period} {band}: mosaic grid {out_grid.shape} {out_grid.bounds} "
            f"differs from the requested grid {grid.shape} {grid.bounds}"
        )
        raise ValueError(msg)
    return np.asarray(array, dtype=np.float32)
