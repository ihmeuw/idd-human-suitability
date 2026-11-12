"""Layers that share one grid as one object: a Dataset per grid, and a table with a row per pixel.

Every loader in ``lib`` returns arrays on a ``BlockGrid``. When several of them are on the same
grid, pixel ``(row, col)`` is the same place in each, and they can be held together.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd
import xarray as xr

if TYPE_CHECKING:
    from collections.abc import Mapping

    from idd_spatial_analysis.frame import BlockGrid
    from numpy.typing import NDArray

Y_DIM = "y"
X_DIM = "x"
CRS_ATTR = "crs"
TRANSFORM_ATTR = "transform"
_NO_ZONE = 0
_AFFINE_COEFFICIENTS = 6


def stack_layers(layers: Mapping[str, NDArray[Any]], grid: BlockGrid) -> xr.Dataset:
    """One Dataset on dimensions ``(y, x)`` with one variable per layer.

    ``layers`` maps a variable name to a 2-D array on ``grid``; every array must have the
    grid's shape. The arrays are wrapped, not copied, and keep their dtypes. The ``y`` and
    ``x`` coordinates are the pixel centres in the grid's CRS (``y`` runs north to south, as
    the rows do). The CRS string and the six affine coefficients of the grid are stored in the
    Dataset's attributes under ``crs`` and ``transform``. Raises ``ValueError`` for no layers,
    a layer of another shape, or a layer named ``x`` or ``y``.
    """
    if not layers:
        msg = "layers is empty"
        raise ValueError(msg)
    data_vars: dict[str, tuple[tuple[str, str], NDArray[Any]]] = {}
    for name, array in layers.items():
        if name in {Y_DIM, X_DIM}:
            msg = f"a layer cannot be named {name!r}: that is a coordinate"
            raise ValueError(msg)
        values = np.asarray(array)
        if values.shape != grid.shape:
            msg = f"layer {name!r} has shape {values.shape}, the grid has {grid.shape}"
            raise ValueError(msg)
        data_vars[name] = ((Y_DIM, X_DIM), values)
    xs, ys = grid.pixel_centers()
    coefficients = [float(value) for value in tuple(grid.transform)[:_AFFINE_COEFFICIENTS]]
    return xr.Dataset(
        data_vars,
        coords={Y_DIM: ys, X_DIM: xs},
        attrs={CRS_ATTR: str(grid.crs), TRANSFORM_ATTR: coefficients},
    )


def pixels_to_table(pixels_ds: xr.Dataset, *, zone_variable: str | None = None) -> pd.DataFrame:
    """One row per pixel: ``y``, ``x`` (the pixel centre) and every variable of the Dataset.

    Rows are in raster order, top row first and left to right. Variables keep their dtypes.
    With ``zone_variable``, the name of an integer variable holding a zone id per pixel with
    ``0`` for no zone, only the pixels inside a zone are kept; that is how a country's own
    pixels are taken out of its bounding box. Raises ``KeyError`` when ``zone_variable`` is
    not in the Dataset, ``TypeError`` when it is not an integer variable, and ``ValueError``
    when no pixel is in a zone or a variable is not on ``(y, x)``.
    """
    off_grid = [
        str(name) for name, var in pixels_ds.data_vars.items() if var.dims != (Y_DIM, X_DIM)
    ]
    if off_grid:
        msg = f"variables not on ({Y_DIM}, {X_DIM}): {off_grid}"
        raise ValueError(msg)
    height, width = int(pixels_ds.sizes[Y_DIM]), int(pixels_ds.sizes[X_DIM])
    keep: NDArray[np.intp] | None = None
    if zone_variable is not None:
        if zone_variable not in pixels_ds.data_vars:
            msg = f"the Dataset has no variable {zone_variable!r}"
            raise KeyError(msg)
        zone = pixels_ds[zone_variable].to_numpy()
        if zone.dtype.kind not in "iu":
            msg = f"{zone_variable!r} must hold integer zone ids, got {zone.dtype}"
            raise TypeError(msg)
        keep = np.flatnonzero(zone.ravel() != _NO_ZONE)
        if keep.size == 0:
            msg = f"no pixel is in a zone of {zone_variable!r}"
            raise ValueError(msg)
    if keep is None:
        rows = np.repeat(np.arange(height), width)
        cols = np.tile(np.arange(width), height)
    else:
        rows, cols = np.divmod(keep, width)
    columns: dict[str, NDArray[Any]] = {
        Y_DIM: np.asarray(pixels_ds[Y_DIM].to_numpy(), dtype=np.float64)[rows],
        X_DIM: np.asarray(pixels_ds[X_DIM].to_numpy(), dtype=np.float64)[cols],
    }
    for name, var in pixels_ds.data_vars.items():
        flat = var.to_numpy().ravel()
        columns[str(name)] = flat if keep is None else flat[keep]
    return pd.DataFrame(columns)
