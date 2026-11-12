"""Annual historical climate: one variable and one year, by window or on another grid.

Files live at ``<climate_root>/raw/historical/<variable>/<year>_era5.nc``: one global lon/lat
grid per file (0.1 degree in the real data), one data variable, one year. Only the cells that
cover the area asked for are read.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import xarray as xr
from affine import Affine
from idd_spatial_analysis.constants import WGS84
from idd_spatial_analysis.frame import BlockGrid
from idd_spatial_analysis.raster import reproject_to_grid

from idd_human_suitability import constants as c
from idd_human_suitability.paths import root

if TYPE_CHECKING:
    from idd_spatial_analysis.frame import Bounds
    from idd_spatial_analysis.raster.io import Raster
    from numpy.typing import NDArray

_ENGINE = "h5netcdf"
_PAD_CELLS = 1
_MIN_AXIS_CELLS = 2


def climate_file(variable: str, year: int, *, climate_root: Path | None = None) -> Path:
    """The historical file of ``variable`` for ``year``.

    ``climate_root`` overrides the root from ``paths.yaml``. Raises ``FileNotFoundError`` when
    there is no such file, which is also what a year outside the historical record gives.
    """
    base = climate_root if climate_root is not None else root(c.CLIMATE_ROOT_KEY)
    path = Path(base) / c.CLIMATE_HISTORICAL_FILE.format(variable=variable, year=year)
    if not path.exists():
        msg = f"no historical climate file for {variable!r} in {year}: {path}"
        raise FileNotFoundError(msg)
    return path


def _axis(values: NDArray[np.float64], name: str, path: Path, *, descending: bool) -> float:
    """The constant step of a coordinate axis, positive; raises unless it is regular."""
    if values.size < _MIN_AXIS_CELLS:
        msg = f"{path}: {name} has fewer than {_MIN_AXIS_CELLS} cells"
        raise ValueError(msg)
    steps = np.diff(values)
    step = float(steps[0])
    if not np.allclose(steps, step) or step == 0 or (step < 0) != descending:
        direction = "north to south" if descending else "west to east"
        msg = f"{path}: {name} is not a regular axis running {direction}"
        raise ValueError(msg)
    return abs(step)


def _file_grid(dataset: xr.Dataset, path: Path) -> BlockGrid:
    """The lon/lat grid of a climate file, from its cell-centre coordinates."""
    lat = np.asarray(dataset[c.CLIMATE_LATITUDE_DIM].to_numpy(), dtype=np.float64)
    lon = np.asarray(dataset[c.CLIMATE_LONGITUDE_DIM].to_numpy(), dtype=np.float64)
    lat_step = _axis(lat, c.CLIMATE_LATITUDE_DIM, path, descending=True)
    lon_step = _axis(lon, c.CLIMATE_LONGITUDE_DIM, path, descending=False)
    transform = Affine(
        lon_step, 0.0, float(lon[0]) - lon_step / 2, 0.0, -lat_step, float(lat[0]) + lat_step / 2
    )
    return BlockGrid(crs=WGS84, transform=transform, height=int(lat.size), width=int(lon.size))


def climate_window(
    variable: str, year: int, bounds: Bounds, *, climate_root: Path | None = None
) -> Raster:
    """``variable`` in ``year`` for the climate cells covering lon/lat ``bounds``, with their grid.

    ``bounds`` are ``(left, bottom, right, top)`` in degrees. The window is one cell wider on
    every side than the cells the bounds touch, clipped to the file, so that a later regrid
    never runs out of source at the edge. Values are float32, in the file's own units. Raises
    ``ValueError`` when the bounds miss the file's grid, when the file's axes are not regular
    (latitude north to south, longitude west to east) or when the file holds another year.
    """
    path = climate_file(variable, year, climate_root=climate_root)
    with xr.open_dataset(path, engine=_ENGINE) as dataset:
        years = [int(value) for value in dataset[c.CLIMATE_YEAR_DIM].to_numpy()]
        if years != [year]:
            msg = f"{path} holds year(s) {years}, expected [{year}]"
            raise ValueError(msg)
        full_grid = _file_grid(dataset, path)
        window = full_grid.window(bounds, pad=_PAD_CELLS)
        rows = slice(int(window.row_off), int(window.row_off + window.height))
        cols = slice(int(window.col_off), int(window.col_off + window.width))
        selection = dataset[c.CLIMATE_VALUE_VARIABLE].isel(
            {
                c.CLIMATE_YEAR_DIM: 0,
                c.CLIMATE_LATITUDE_DIM: rows,
                c.CLIMATE_LONGITUDE_DIM: cols,
            }
        )
        array = np.asarray(selection.to_numpy(), dtype=np.float32)
    return array, full_grid.sub(window)


def climate_on_grid(
    variable: str, year: int, grid: BlockGrid, *, climate_root: Path | None = None
) -> NDArray[np.float32]:
    """``variable`` in ``year`` on ``grid``: each pixel takes the climate cell its centre is in.

    ``grid`` may be in any CRS; it is usually much finer than the climate grid, so many pixels
    share one value. Nothing is interpolated. Pixels outside the climate file are NaN. On the
    100 m equal-area grid of one country this gave exactly the values of the sibling's
    ``NearestIndexMap`` lookup for every pixel (checked 2026-11-11) at a fifth of the time.
    """
    window, window_grid = climate_window(
        variable, year, grid.lonlat_bounds(), climate_root=climate_root
    )
    on_grid = reproject_to_grid(window, window_grid, grid, resampling="nearest")
    return np.asarray(on_grid, dtype=np.float32)
