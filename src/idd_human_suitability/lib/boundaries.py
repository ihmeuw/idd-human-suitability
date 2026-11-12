"""Countries, the GBD region each belongs to, and their admin polygons.

Polygons come from one pinned admin shapefile release through
``idd_spatial_analysis.boundaries.load_admin``. Regions come from a GBD location hierarchy:
the shapefiles carry no grouping above the country, and their ``loc_id`` is the hierarchy's
``location_id``.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
from idd_spatial_analysis.boundaries import AdminRelease, load_admin
from idd_spatial_analysis.constants import (
    ADM_NAME_COLUMN,
    LEVEL_COLUMN,
    LOC_ID_COLUMN,
    LOCATION_ID_COLUMN,
    PARENT_ID_COLUMN,
)
from idd_spatial_analysis.tables import require_columns

from idd_human_suitability import constants as c
from idd_human_suitability.paths import root

if TYPE_CHECKING:
    import geopandas as gpd

_ADM0_NAME = ADM_NAME_COLUMN.format(level=0)
_ID_DTYPE = "int32"
_NULLABLE_ID_DTYPE = "Int32"
_ADMIN2_LEVEL = 2
_HIERARCHY_COLUMNS = (
    LOCATION_ID_COLUMN,
    PARENT_ID_COLUMN,
    LEVEL_COLUMN,
    c.LOCATION_NAME_COLUMN,
    c.IHME_LOC_ID_COLUMN,
    c.REGION_ID_COLUMN,
    c.REGION_NAME_COLUMN,
)


@dataclass(frozen=True)
class Country:
    """One country as the shapefiles and the GBD hierarchy identify it."""

    name: str
    adm0_code: int
    location_id: int
    iso3: str
    region_id: int
    region_name: str


def admin_release(
    release: str, *, simplified: bool = True, shapefile_root: Path | None = None
) -> AdminRelease:
    """The shapefile release ``<admin_shapefile_root>/<release>``.

    ``simplified`` selects the generalised geometry. ``shapefile_root`` overrides the root from
    ``paths.yaml``. Raises ``FileNotFoundError`` when the release folder does not exist, so a
    mistyped release fails here and not at the first read.
    """
    base = shapefile_root if shapefile_root is not None else root(c.ADMIN_SHAPEFILE_ROOT_KEY)
    out = AdminRelease(Path(base), release, simplified=simplified)
    if not out.directory.is_dir():
        msg = f"admin shapefile release {release!r} not found under {base}"
        raise FileNotFoundError(msg)
    return out


def load_gbd_hierarchy(hierarchy: str, *, raking_root: Path | None = None) -> pd.DataFrame:
    """Every location of one GBD hierarchy with its name, ISO3 code and region.

    Columns: ``location_id``, ``parent_id``, ``level`` (int32), ``location_name``,
    ``ihme_loc_id`` (strings), ``region_id`` (nullable Int32, null above the region level) and
    ``region_name``. ``hierarchy`` is the file's name part, for example ``gbd_2023``.
    """
    base = raking_root if raking_root is not None else root(c.RAKING_ROOT_KEY)
    path = Path(base) / c.HIERARCHY_FILE.format(hierarchy=hierarchy)
    if not path.exists():
        msg = f"hierarchy {hierarchy!r} not found: {path}"
        raise FileNotFoundError(msg)
    columns = list(_HIERARCHY_COLUMNS)
    table = pd.read_parquet(path, columns=columns)
    require_columns(table, columns, f"hierarchy {hierarchy}")
    typed = {
        LOCATION_ID_COLUMN: table[LOCATION_ID_COLUMN].astype(_ID_DTYPE),
        PARENT_ID_COLUMN: table[PARENT_ID_COLUMN].astype(_ID_DTYPE),
        LEVEL_COLUMN: table[LEVEL_COLUMN].astype(_ID_DTYPE),
        c.LOCATION_NAME_COLUMN: table[c.LOCATION_NAME_COLUMN].astype("string"),
        c.IHME_LOC_ID_COLUMN: table[c.IHME_LOC_ID_COLUMN].astype("string"),
        c.REGION_ID_COLUMN: table[c.REGION_ID_COLUMN].astype(_NULLABLE_ID_DTYPE),
        c.REGION_NAME_COLUMN: table[c.REGION_NAME_COLUMN].astype("string"),
    }
    return pd.DataFrame(typed).reset_index(drop=True)


def find_country(name: str, admin0_gdf: gpd.GeoDataFrame, hierarchy_df: pd.DataFrame) -> Country:
    """The country called ``name`` in the admin-0 table, with its ISO3 code and GBD region.

    ``admin0_gdf`` is ``load_admin(release, 0, columns=["loc_id"])``. The name is matched
    against ``ADM0_NAME`` ignoring case and surrounding spaces. Raises ``ValueError`` when the
    name matches no unit (the message offers the closest names) or more than one, and when the
    unit is not a country of the hierarchy, which means it has no region there.
    """
    require_columns(admin0_gdf, [_ADM0_NAME, "ADM0_CODE", LOC_ID_COLUMN], "admin0 table")
    wanted = name.strip().casefold()
    names = admin0_gdf[_ADM0_NAME].astype(str)
    hits = admin0_gdf.loc[names.str.strip().str.casefold() == wanted]
    if hits.empty:
        close = difflib.get_close_matches(name.strip(), sorted(set(names)), n=5, cutoff=0.6)
        msg = f"no admin-0 unit is named {name!r}; closest names: {close}"
        raise ValueError(msg)
    if len(hits) > 1:
        msg = f"{len(hits)} admin-0 units are named {name!r}"
        raise ValueError(msg)
    row = hits.iloc[0]
    if pd.isna(row[LOC_ID_COLUMN]):
        msg = f"admin-0 unit {row[_ADM0_NAME]!r} has no loc_id"
        raise ValueError(msg)
    location_id = int(row[LOC_ID_COLUMN])
    in_hierarchy = hierarchy_df.loc[
        (hierarchy_df[LOCATION_ID_COLUMN] == location_id)
        & (hierarchy_df[LEVEL_COLUMN] == c.GBD_COUNTRY_LEVEL)
    ]
    if in_hierarchy.empty or pd.isna(in_hierarchy.iloc[0][c.REGION_ID_COLUMN]):
        msg = (
            f"{row[_ADM0_NAME]!r} (location_id {location_id}) is not a country of the "
            "hierarchy, so it has no region"
        )
        raise ValueError(msg)
    location = in_hierarchy.iloc[0]
    return Country(
        name=str(row[_ADM0_NAME]),
        adm0_code=int(row["ADM0_CODE"]),
        location_id=location_id,
        iso3=str(location[c.IHME_LOC_ID_COLUMN]),
        region_id=int(location[c.REGION_ID_COLUMN]),
        region_name=str(location[c.REGION_NAME_COLUMN]),
    )


def region_admin0(
    country: Country, admin0_gdf: gpd.GeoDataFrame, hierarchy_df: pd.DataFrame
) -> gpd.GeoDataFrame:
    """Admin-0 polygons of every country in ``country``'s GBD region, ``country`` included.

    Raises ``ValueError`` when a country of the region has no polygon in ``admin0_gdf``: a
    region drawn with a member missing would look complete and not be.
    """
    members = hierarchy_df.loc[
        (hierarchy_df[c.REGION_ID_COLUMN] == country.region_id)
        & (hierarchy_df[LEVEL_COLUMN] == c.GBD_COUNTRY_LEVEL)
    ]
    member_ids = {int(value) for value in members[LOCATION_ID_COLUMN]}
    present = admin0_gdf.loc[admin0_gdf[LOC_ID_COLUMN].isin(sorted(member_ids))]
    missing = member_ids - {int(value) for value in present[LOC_ID_COLUMN]}
    if missing:
        names = members.loc[
            members[LOCATION_ID_COLUMN].isin(sorted(missing)), c.LOCATION_NAME_COLUMN
        ]
        msg = f"region {country.region_name!r}: no admin-0 polygon for {sorted(map(str, names))}"
        raise ValueError(msg)
    return present.reset_index(drop=True)


def country_admin2(country: Country, release: AdminRelease) -> gpd.GeoDataFrame:
    """Admin-2 polygons of ``country`` with ``loc_id``, the id the admin-2 tables join on."""
    return load_admin(
        release, _ADMIN2_LEVEL, countries=[country.adm0_code], columns=[LOC_ID_COLUMN]
    )
