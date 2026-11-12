"""Zone values onto a raster: each pixel takes the value of the zone it belongs to.

The zone mask comes from ``idd_spatial_analysis.raster.rasterize_zones``. The lookup here is
general and is a candidate for that package.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    import pandas as pd
    from numpy.typing import NDArray

_NO_ZONE = 0
_DENSE_LOOKUP_MAX_ID = 50_000_000
"""Largest zone id for which a dense id -> value table is built (200 MB of float32)."""


def zone_values_to_raster(zone_mask: NDArray[Any], values: pd.Series) -> NDArray[np.float32]:
    """A float32 raster holding, at each pixel, the value of the pixel's zone.

    ``zone_mask`` holds an integer zone id per pixel with ``0`` for no zone, as
    ``rasterize_zones`` returns it. ``values`` is indexed by zone id. Pixels outside every
    zone are NaN. Raises ``ValueError`` when a zone present in the mask has no value, when a
    zone id repeats in ``values`` or when ``values`` carries the id ``0``: a join that lost
    units must not produce a raster with quiet holes. Zones with a value that never appear in
    the mask are fine (too small to hold a pixel centre, or outside the grid).
    """
    mask = np.asarray(zone_mask)
    if mask.dtype.kind not in "iu":
        msg = f"zone_mask must hold integers, got {mask.dtype}"
        raise TypeError(msg)
    ids = np.asarray(values.index.to_numpy(), dtype=np.int64)
    numbers = np.asarray(values.to_numpy(), dtype=np.float32)
    if ids.size == 0:
        msg = "values is empty"
        raise ValueError(msg)
    if np.unique(ids).size != ids.size:
        msg = "values has repeated zone ids"
        raise ValueError(msg)
    if (ids <= _NO_ZONE).any():
        msg = f"zone ids must be positive ({_NO_ZONE} means no zone)"
        raise ValueError(msg)
    present = np.unique(mask)
    present = present[present != _NO_ZONE]
    missing = np.setdiff1d(present, ids)
    if missing.size:
        msg = f"{missing.size} zone(s) in the mask have no value, e.g. {missing[:10].tolist()}"
        raise ValueError(msg)
    largest = int(ids.max())
    if largest <= _DENSE_LOOKUP_MAX_ID:
        lookup = np.full(largest + 1, np.nan, dtype=np.float32)
        lookup[ids] = numbers
        return np.asarray(lookup[mask], dtype=np.float32)
    order = np.argsort(ids)
    sorted_ids, sorted_numbers = ids[order], numbers[order]
    out = np.full(mask.shape, np.nan, dtype=np.float32)
    inside = mask != _NO_ZONE
    out[inside] = sorted_numbers[np.searchsorted(sorted_ids, mask[inside])]
    return out
