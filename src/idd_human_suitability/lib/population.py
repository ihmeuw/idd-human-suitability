"""The gridded population results: one global raster per year, read by window.

The 100 m files are virtual mosaics of the population model's tiles, so reading a window
touches only the tiles under it; nothing here ever reads a whole file.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from idd_spatial_analysis.constants import WGS84
from idd_spatial_analysis.raster import read_window

from idd_human_suitability import constants as c
from idd_human_suitability.paths import root

if TYPE_CHECKING:
    from idd_spatial_analysis.frame import Bounds
    from idd_spatial_analysis.raster.io import Raster


def population_file(
    year: int, *, resolution: int, version: str, population_root: Path | None = None
) -> Path:
    """The equal-area population raster of ``year``: ``<root>/<version>/world_cylindrical_<resolution>/<year>q1.tif``.

    ``resolution`` is in metres (100 or 1000 exist). ``version`` is a dated release or
    ``current``. ``population_root`` overrides the root from ``paths.yaml``. Raises
    ``FileNotFoundError`` when the file does not exist.
    """
    base = population_root if population_root is not None else root(c.POPULATION_ROOT_KEY)
    path = Path(base) / c.POPULATION_FILE.format(
        version=version, crs=c.POPULATION_CRS_EQUAL_AREA, resolution=resolution, year=year
    )
    if not path.exists():
        msg = f"no population raster for year {year} at {resolution} m in {version!r}: {path}"
        raise FileNotFoundError(msg)
    return path


def population_window(  # noqa: PLR0913  (keyword-only read options)
    bounds: Bounds,
    year: int,
    *,
    resolution: int,
    version: str,
    bounds_crs: str = WGS84,
    population_root: Path | None = None,
) -> Raster:
    """People per pixel inside ``bounds`` for ``year``, with the grid of exactly those pixels.

    ``bounds`` are ``(left, bottom, right, top)`` in ``bounds_crs``, lon/lat by default; the
    result is on the population raster's own equal-area grid, float32 with NaN where the
    model has no value. The window is the bounding box, so it includes pixels of neighbouring
    countries.
    """
    path = population_file(
        year, resolution=resolution, version=version, population_root=population_root
    )
    array, grid = read_window(path, bounds, bounds_crs=bounds_crs)
    return array, grid
