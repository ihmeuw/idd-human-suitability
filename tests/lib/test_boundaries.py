from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import pytest
from idd_spatial_analysis.boundaries import load_admin

from idd_human_suitability.lib.boundaries import (
    Country,
    admin_release,
    country_admin2,
    find_country,
    load_gbd_hierarchy,
    region_admin0,
)
from tests.lib.conftest import HIERARCHY, RELEASE, hierarchy_frame

if TYPE_CHECKING:
    from pathlib import Path

    import geopandas as gpd

ALPHA = Country(
    name="Alpha", adm0_code=1, location_id=101, iso3="ALP", region_id=20, region_name="Region One"
)


@pytest.fixture
def admin0_gdf(shapefile_root: Path) -> gpd.GeoDataFrame:
    return load_admin(admin_release(RELEASE, shapefile_root=shapefile_root), 0, columns=["loc_id"])


@pytest.fixture
def hierarchy_df(raking_root: Path) -> pd.DataFrame:
    return load_gbd_hierarchy(HIERARCHY, raking_root=raking_root)


def test_admin_release_points_at_the_release_folder(shapefile_root: Path) -> None:
    release = admin_release(RELEASE, shapefile_root=shapefile_root)
    assert release.directory == shapefile_root / RELEASE
    assert release.simplified is True
    assert release.require(2).name == "lbd_standard_admin_2_simplified.shp"


def test_admin_release_can_select_the_full_geometry(shapefile_root: Path) -> None:
    release = admin_release(RELEASE, simplified=False, shapefile_root=shapefile_root)
    assert release.path(0).name == "lbd_standard_admin_0.shp"


def test_admin_release_missing_release_raises(shapefile_root: Path) -> None:
    with pytest.raises(FileNotFoundError, match="1999_01_01"):
        admin_release("1999_01_01", shapefile_root=shapefile_root)


def test_load_gbd_hierarchy_columns_dtypes_and_values(hierarchy_df: pd.DataFrame) -> None:
    assert list(hierarchy_df.columns) == [
        "location_id",
        "parent_id",
        "level",
        "location_name",
        "ihme_loc_id",
        "region_id",
        "region_name",
    ]
    dtypes = hierarchy_df.dtypes.astype(str).to_dict()
    assert dtypes["location_id"] == dtypes["parent_id"] == dtypes["level"] == "int32"
    assert dtypes["region_id"] == "Int32"
    assert len(hierarchy_df) == len(hierarchy_frame())
    by_id = hierarchy_df.set_index("location_id")
    assert pd.isna(by_id.loc[1, "region_id"])
    assert by_id.loc[101, "region_id"] == 20
    assert by_id.loc[101, "ihme_loc_id"] == "ALP"
    assert by_id.loc[103, "region_name"] == "Region Two"


def test_load_gbd_hierarchy_missing_file_raises(raking_root: Path) -> None:
    with pytest.raises(FileNotFoundError, match="gbd_1900"):
        load_gbd_hierarchy("gbd_1900", raking_root=raking_root)


def test_load_gbd_hierarchy_missing_column_raises(tmp_path: Path) -> None:
    path = tmp_path / "gbd-inputs" / f"hierarchy_{HIERARCHY}.parquet"
    path.parent.mkdir()
    hierarchy_frame().drop(columns=["ihme_loc_id"]).to_parquet(path)
    with pytest.raises((KeyError, ValueError), match="ihme_loc_id"):
        load_gbd_hierarchy(HIERARCHY, raking_root=tmp_path)


@pytest.mark.parametrize("name", ["Alpha", "alpha", "  ALPHA "])
def test_find_country_matches_ignoring_case_and_spaces(
    admin0_gdf: gpd.GeoDataFrame, hierarchy_df: pd.DataFrame, name: str
) -> None:
    assert find_country(name, admin0_gdf, hierarchy_df) == ALPHA


def test_find_country_unknown_name_offers_close_names(
    admin0_gdf: gpd.GeoDataFrame, hierarchy_df: pd.DataFrame
) -> None:
    with pytest.raises(ValueError, match=r"no admin-0 unit is named 'Alpa'.*Alpha"):
        find_country("Alpa", admin0_gdf, hierarchy_df)


def test_find_country_unit_outside_the_hierarchy_has_no_region(
    admin0_gdf: gpd.GeoDataFrame, hierarchy_df: pd.DataFrame
) -> None:
    with pytest.raises(ValueError, match=r"'Isle'.*not a country of the hierarchy"):
        find_country("Isle", admin0_gdf, hierarchy_df)


def test_find_country_subnational_location_is_not_a_country(
    admin0_gdf: gpd.GeoDataFrame, hierarchy_df: pd.DataFrame
) -> None:
    relabelled = admin0_gdf.copy()
    relabelled.loc[relabelled["ADM0_NAME"] == "Isle", "loc_id"] = 500
    with pytest.raises(ValueError, match="not a country of the hierarchy"):
        find_country("Isle", relabelled, hierarchy_df)


def test_find_country_repeated_name_raises(
    admin0_gdf: gpd.GeoDataFrame, hierarchy_df: pd.DataFrame
) -> None:
    doubled = pd.concat([admin0_gdf, admin0_gdf.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="2 admin-0 units are named 'Alpha'"):
        find_country("Alpha", doubled, hierarchy_df)


def test_region_admin0_returns_every_country_of_the_region(
    admin0_gdf: gpd.GeoDataFrame, hierarchy_df: pd.DataFrame
) -> None:
    region = region_admin0(ALPHA, admin0_gdf, hierarchy_df)
    assert sorted(region["ADM0_NAME"]) == ["Alpha", "Beta"]
    assert region.crs == admin0_gdf.crs
    assert list(region.index) == [0, 1]


def test_region_admin0_single_country_region(
    admin0_gdf: gpd.GeoDataFrame, hierarchy_df: pd.DataFrame
) -> None:
    gamma = find_country("Gamma", admin0_gdf, hierarchy_df)
    assert list(region_admin0(gamma, admin0_gdf, hierarchy_df)["ADM0_NAME"]) == ["Gamma"]


def test_region_admin0_member_without_polygon_raises(
    admin0_gdf: gpd.GeoDataFrame, hierarchy_df: pd.DataFrame
) -> None:
    without_beta = admin0_gdf.loc[admin0_gdf["ADM0_NAME"] != "Beta"]
    with pytest.raises(ValueError, match=r"Region One.*no admin-0 polygon for \['Beta'\]"):
        region_admin0(ALPHA, without_beta, hierarchy_df)


def test_country_admin2_returns_the_countrys_units_with_loc_id(shapefile_root: Path) -> None:
    release = admin_release(RELEASE, shapefile_root=shapefile_root)
    admin2 = country_admin2(ALPHA, release)
    assert sorted(admin2["ADM2_NAME"]) == ["Alpha East", "Alpha West"]
    assert set(admin2["ADM0_CODE"]) == {1}
    assert sorted(admin2["loc_id"].tolist()) == [1001, 1002]
    assert str(admin2["loc_id"].dtype) == "Int32"
    assert tuple(admin2.total_bounds) == (0.0, 0.0, 1.0, 1.0)
