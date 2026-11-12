from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from idd_human_suitability.lib import rasterize
from idd_human_suitability.lib.rasterize import zone_values_to_raster

MASK = np.array([[0, 7, 7], [3, 3, 0], [3, 7, 7]], dtype=np.int32)
VALUES = pd.Series({3: 1.5, 7: 20.0, 99: 5.0})
EXPECTED = np.array([[np.nan, 20.0, 20.0], [1.5, 1.5, np.nan], [1.5, 20.0, 20.0]], dtype=np.float32)


def test_each_pixel_takes_its_zones_value_and_no_zone_is_nan() -> None:
    out = zone_values_to_raster(MASK, VALUES)
    np.testing.assert_array_equal(out, EXPECTED)
    assert out.dtype == np.float32
    assert out.shape == MASK.shape


def test_sparse_lookup_gives_the_same_raster(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rasterize, "_DENSE_LOOKUP_MAX_ID", 5)
    np.testing.assert_array_equal(zone_values_to_raster(MASK, VALUES), EXPECTED)


def test_large_zone_ids_are_supported() -> None:
    big = 2_000_000_000
    mask = np.array([[0, big], [big, 0]], dtype=np.int64)
    out = zone_values_to_raster(mask, pd.Series({big: 4.25}))
    np.testing.assert_array_equal(out, np.array([[np.nan, 4.25], [4.25, np.nan]], dtype=np.float32))


def test_a_nan_value_stays_nan() -> None:
    out = zone_values_to_raster(MASK, pd.Series({3: np.nan, 7: 2.0}))
    assert np.isnan(out[1, 0])
    assert out[0, 1] == 2.0


def test_mask_without_any_zone_is_all_nan() -> None:
    out = zone_values_to_raster(np.zeros((2, 2), dtype=np.int32), VALUES)
    assert np.isnan(out).all()


def test_single_pixel_mask() -> None:
    out = zone_values_to_raster(np.array([[7]], dtype=np.int32), VALUES)
    np.testing.assert_array_equal(out, np.array([[20.0]], dtype=np.float32))


def test_zone_in_the_mask_without_a_value_raises() -> None:
    with pytest.raises(ValueError, match=r"1 zone\(s\) in the mask have no value, e\.g\. \[7\]"):
        zone_values_to_raster(MASK, pd.Series({3: 1.5}))


def test_repeated_zone_id_raises() -> None:
    values = pd.Series([1.0, 2.0, 3.0], index=[3, 7, 7])
    with pytest.raises(ValueError, match="repeated zone ids"):
        zone_values_to_raster(MASK, values)


@pytest.mark.parametrize("bad_id", [0, -4])
def test_non_positive_zone_id_raises(bad_id: int) -> None:
    with pytest.raises(ValueError, match="zone ids must be positive"):
        zone_values_to_raster(MASK, pd.Series({3: 1.5, 7: 2.0, bad_id: 9.0}))


def test_empty_values_raises() -> None:
    with pytest.raises(ValueError, match="values is empty"):
        zone_values_to_raster(MASK, pd.Series(dtype="float64"))


def test_float_mask_raises() -> None:
    with pytest.raises(TypeError, match="zone_mask must hold integers"):
        zone_values_to_raster(MASK.astype("float32"), VALUES)
