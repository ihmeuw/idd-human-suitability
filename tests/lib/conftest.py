"""Small synthetic inputs laid out the way the real roots are.

Geography: admin units are lon/lat boxes just north-east of (0, 0); rasters are 100 m
equal-area grids whose origin is the equal-area image of (0, 0), so the two overlap.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import rasterio
from affine import Affine
from idd_spatial_analysis.constants import WGS84, WORLD_CYLINDRICAL_EQUAL_AREA
from shapely.geometry import box

from idd_human_suitability import constants as c

if TYPE_CHECKING:
    from pathlib import Path

RELEASE = "2024_01_01"
HIERARCHY = "gbd_2023"
POPULATION_VERSION = "2026_01_01"
SOURCE = "source_a"
RESOLUTION = 100
TILE_PIXELS = 10
BLOCK_WEST = "B-0000X-0000Y"
BLOCK_EAST = "B-0001X-0000Y"


def write_tif(path: Path, array: np.ndarray, transform: Affine) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=array.shape[0],
        width=array.shape[1],
        count=1,
        dtype="float32",
        crs=WORLD_CYLINDRICAL_EQUAL_AREA,
        transform=transform,
        nodata=float("nan"),
    ) as dst:
        dst.write(array.astype("float32"), 1)


@pytest.fixture
def shapefile_root(tmp_path: Path) -> Path:
    """An admin shapefile root holding one release with simplified admin-0 and admin-2 files."""
    release_dir = tmp_path / "admin_shapefiles" / RELEASE
    release_dir.mkdir(parents=True)
    admin0 = gpd.GeoDataFrame(
        {
            "ADM0_CODE": [1, 2, 3, 4],
            "ADM0_NAME": ["Alpha", "Beta", "Gamma", "Isle"],
            "loc_id": [101, 102, 103, 999],
            "geo_id": [1.0, 2.0, 3.0, 4.0],
        },
        geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1), box(5, 5, 6, 6), box(10, 10, 11, 11)],
        crs=WGS84,
    )
    admin0.to_file(release_dir / "lbd_standard_admin_0_simplified.shp")
    admin2 = gpd.GeoDataFrame(
        {
            "ADM2_CODE": [11, 12, 21],
            "ADM2_NAME": ["Alpha West", "Alpha East", "Beta All"],
            "ADM1_CODE": [10, 10, 20],
            "ADM1_NAME": ["Alpha One", "Alpha One", "Beta One"],
            "ADM0_CODE": [1, 1, 2],
            "ADM0_NAME": ["Alpha", "Alpha", "Beta"],
            "loc_id": [1001, 1002, 2001],
        },
        geometry=[box(0, 0, 0.5, 1), box(0.5, 0, 1, 1), box(1, 0, 2, 1)],
        crs=WGS84,
    )
    admin2.to_file(release_dir / "lbd_standard_admin_2_simplified.shp")
    return tmp_path / "admin_shapefiles"


def hierarchy_frame() -> pd.DataFrame:
    """A GBD-style hierarchy: two regions; Alpha and Beta share one, Gamma is in the other."""
    return pd.DataFrame(
        {
            "location_id": [1, 10, 20, 30, 101, 102, 103, 500],
            "parent_id": [1, 1, 10, 10, 20, 20, 30, 101],
            "level": [0, 1, 2, 2, 3, 3, 3, 4],
            "location_name": [
                "Global",
                "Super",
                "Region One",
                "Region Two",
                "Alpha",
                "Beta",
                "Gamma",
                "Alpha Province",
            ],
            "ihme_loc_id": ["G", "S1", "R1", "R2", "ALP", "BET", "GAM", "ALP_500"],
            "region_id": [np.nan, np.nan, 20.0, 30.0, 20.0, 20.0, 30.0, 20.0],
            "region_name": [
                None,
                None,
                "Region One",
                "Region Two",
                "Region One",
                "Region One",
                "Region Two",
                "Region One",
            ],
            "location_set_id": [35] * 8,
        }
    )


@pytest.fixture
def raking_root(tmp_path: Path) -> Path:
    """A raking root holding one GBD hierarchy file."""
    base = tmp_path / "raking"
    path = base / c.HIERARCHY_FILE.format(hierarchy=HIERARCHY)
    path.parent.mkdir(parents=True)
    hierarchy_frame().to_parquet(path)
    return base


@pytest.fixture
def population_root(tmp_path: Path) -> Path:
    """A population root with one version and one 20 x 20 pixel year at 100 m.

    Pixel values are ``row * 100 + col``, so any window can be checked against its position.
    """
    base = tmp_path / "population"
    rows, cols = np.indices((20, 20))
    path = base / c.POPULATION_FILE.format(
        version=POPULATION_VERSION,
        crs=c.POPULATION_CRS_EQUAL_AREA,
        resolution=RESOLUTION,
        year=2020,
    )
    write_tif(path, (rows * 100 + cols).astype("float32"), Affine(100, 0, 0, 0, -100, 2000))
    return base


def tile_values(block_key: str, band: str) -> np.ndarray:
    """The pixel values of one synthetic tile: distinct per block and band."""
    rows, cols = np.indices((TILE_PIXELS, TILE_PIXELS))
    offset = (1000 if block_key == BLOCK_EAST else 0) + (5000 if band == "height" else 0)
    return (offset + rows * 10 + cols).astype("float32")


@pytest.fixture
def tiles_root(tmp_path: Path) -> Path:
    """A building tiles root: two side-by-side 1 km blocks, one source, three periods.

    ``2020q2`` and ``2020q3`` have ``density`` and ``height`` for both blocks; ``2021q1`` has
    ``height`` for the west block only. A folder that is not a period sits beside them.
    """
    base = tmp_path / "tiles"
    size = TILE_PIXELS * RESOLUTION
    index = gpd.GeoDataFrame(
        {"block_key": [BLOCK_WEST, BLOCK_EAST], "tile_key": ["T-0000", "T-0001"]},
        geometry=[box(0, 0, size, size), box(size, 0, 2 * size, size)],
        crs=WORLD_CYLINDRICAL_EQUAL_AREA,
    )
    index_path = base / c.TILE_INDEX_FILE.format(resolution=RESOLUTION)
    index_path.parent.mkdir(parents=True)
    index.to_parquet(index_path)
    transforms = {
        BLOCK_WEST: Affine(RESOLUTION, 0, 0, 0, -RESOLUTION, size),
        BLOCK_EAST: Affine(RESOLUTION, 0, size, 0, -RESOLUTION, size),
    }
    wanted = {
        "2020q2": {"density": [BLOCK_WEST, BLOCK_EAST], "height": [BLOCK_WEST, BLOCK_EAST]},
        "2020q3": {"density": [BLOCK_WEST, BLOCK_EAST], "height": [BLOCK_WEST, BLOCK_EAST]},
        "2021q1": {"density": [BLOCK_WEST, BLOCK_EAST], "height": [BLOCK_WEST]},
    }
    for period, bands in wanted.items():
        for band, blocks in bands.items():
            for block_key in blocks:
                path = base / c.BUILDING_TILE_FILE.format(
                    resolution=RESOLUTION,
                    source=SOURCE,
                    period=period,
                    block_key=block_key,
                    band=band,
                )
                write_tif(path, tile_values(block_key, band), transforms[block_key])
    (base / c.BUILDING_SOURCE_DIR.format(resolution=RESOLUTION, source=SOURCE) / "notes").mkdir()
    return base


@pytest.fixture
def income_root(tmp_path: Path) -> Path:
    """An admin-2 income root holding a small GDP per capita table."""
    base = tmp_path / "income"
    base.mkdir()
    rows = [
        "year_id,location_id,pop_masking_flag,zero_pop_masking_flag,country_ISO3,scenario,gdppc_mean",
        "2020,1002,0,1,ALP,reference,250.5",
        "2020,1001,0,0,ALP,reference,100.25",
        "2020,1001,0,0,ALP,better,110.0",
        "2020,1002,0,0,ALP,better,275.0",
        "2021,1001,0,0,ALP,reference,105.0",
        "2021,1002,0,0,ALP,reference,260.0",
        "2020,2001,1,0,BET,reference,999.0",
        "2020,3001,0,0,DUP,reference,1.0",
        "2020,3001,0,0,DUP,reference,2.0",
    ]
    (base / c.ADMIN2_GDPPC_FILENAME).write_text("\n".join(rows) + "\n")
    return base
