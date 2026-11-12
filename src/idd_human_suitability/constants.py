"""Relative path fragments, ``paths.yaml`` key names, column names and enums.

No absolute path lives here. Absolute roots come from the gitignored ``paths.yaml`` through
``idd_human_suitability.paths``; this module names the keys and the fragments below them.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Mapping

# Keys of paths.yaml. Every key is documented in paths.yaml.example.
OUTPUT_ROOT_KEY: Final = "project_output_root"
"""Root of this project's output node."""
INTERMEDIATE_ROOT_KEY: Final = "intermediate_root"
"""Root for the large intermediate files, which do not go on the output node."""
ADMIN_SHAPEFILE_ROOT_KEY: Final = "admin_shapefile_root"
"""Admin boundary shapefiles: ``<root>/<release>/``, one dated folder per release."""
CLIMATE_ROOT_KEY: Final = "climate_root"
"""Annual climate grids, historical and by scenario."""
BUILDING_TILES_ROOT_KEY: Final = "building_tiles_root"
"""Building tiles and their tile index, by resolution."""
POPULATION_ROOT_KEY: Final = "population_root"
"""Gridded population results, by version, CRS and resolution."""
RAKING_ROOT_KEY: Final = "raking_root"
"""Location hierarchies and raking shapes; the layout below it belongs to
``idd_spatial_analysis.boundaries`` (``load_hierarchy``, ``load_raking_shapes``)."""
OVERTURE_WATER_ROOT_KEY: Final = "overture_water_root"
"""Water polygons, one GeoParquet file per water class."""
ADMIN2_INCOME_ROOT_KEY: Final = "admin2_income_root"
"""Admin-2 income and consumption forecast tables."""

# Releases and versions in use. Each is a folder or file name component, which is why it is
# named here and nowhere else; a notebook's parameter cell reads them from here. They stay
# until Bobby changes them (set 2026-11-11).
ADMIN_RELEASE: Final = "2024_07_29"
"""Admin shapefile release: ``<admin_shapefile_root>/<release>/``."""
GBD_HIERARCHY: Final = "gbd_2023"
"""The GBD hierarchy that says which region a country is in."""
BUILDING_SOURCES: Final[Mapping[str, str]] = MappingProxyType(
    {"ghsl": "ghsl_r2023a", "microsoft": "microsoft_v8"}
)
"""Building type as a person names it -> its folder under ``<building_tiles_root>/<res>m/``."""

# Location hierarchies: <raking_root>/<fragment>. idd_spatial_analysis.boundaries.load_hierarchy
# reads the same files but returns only the id columns; the names, ISO3 codes and regions
# need the file itself.
HIERARCHY_FILE: Final = "gbd-inputs/hierarchy_{hierarchy}.parquet"
GBD_COUNTRY_LEVEL: Final = 3
"""``level`` of a country in a GBD hierarchy (0 global, 1 super-region, 2 region)."""
LOCATION_NAME_COLUMN: Final = "location_name"
IHME_LOC_ID_COLUMN: Final = "ihme_loc_id"
"""ISO3 code for a country row."""
REGION_ID_COLUMN: Final = "region_id"
REGION_NAME_COLUMN: Final = "region_name"

# Climate: <climate_root>/<fragment>. Both layouts were confirmed on disk on 2026-11-11
# (historical years as four digits, draws as three zero-padded digits).
CLIMATE_HISTORICAL_FILE: Final = "raw/historical/{variable}/{year}_era5.nc"
CLIMATE_SCENARIO_FILE: Final = "{scenario}/{variable}/{draw}.nc"
# Inside a climate file: one data variable on (year, latitude, longitude), one year per file.
CLIMATE_VALUE_VARIABLE: Final = "value"
CLIMATE_YEAR_DIM: Final = "year"
CLIMATE_LATITUDE_DIM: Final = "latitude"
CLIMATE_LONGITUDE_DIM: Final = "longitude"
# Climate variables in use (folder names under raw/historical/), set by Bobby 2026-11-11.
CLIMATE_MEAN_TEMPERATURE: Final = "mean_temperature"
"""Annual mean temperature. Values are on a degree Celsius scale (2020: -52 to 34); the file
states no unit."""
CLIMATE_TOTAL_PRECIPITATION: Final = "total_precipitation"
"""Annual total precipitation. Values are on a millimetre-per-year scale (2020: 0 to 28,340)
although the file's ``units`` attribute says ``m``."""

# Building tiles: <building_tiles_root>/<fragment>. The tile file layout was confirmed on
# disk on 2026-11-11 for one source and period at 100 m.
TILE_INDEX_FILE: Final = "{resolution}m/tile_index.parquet"
BUILDING_SOURCE_DIR: Final = "{resolution}m/{source}"
"""Holds one folder per period, named ``<year>q<quarter>``."""
BUILDING_PERIOD_DIR: Final = BUILDING_SOURCE_DIR + "/{period}"
BUILDING_TILE_FILE: Final = BUILDING_PERIOD_DIR + "/{block_key}_{band}.tif"

# Population: <population_root>/<fragment>. Confirmed on disk on 2026-11-11: one file per
# year, always named <year>q1.tif. The 100 m files are virtual mosaics of the model's tiles,
# so a window read touches only the tiles it covers.
POPULATION_FILE: Final = "{version}/{crs}_{resolution}/{year}q1.tif"
POPULATION_VERSION: Final = "2026_05_16"
"""The population release this project uses until Bobby changes it (set 2026-11-11, when the
``current`` link on disk pointed at it). Dated on purpose: ``current`` moves."""
POPULATION_CRS_EQUAL_AREA: Final = "world_cylindrical"
"""Folder label of the equal-area grids (metres; resolutions 100 and 1000)."""
POPULATION_CRS_WGS84: Final = "wgs84"
"""Folder label of the lon/lat grids (degrees; resolutions 0p1 and 0p01)."""

# Overture water: <overture_water_root>/<fragment>
OVERTURE_WATER_FILE: Final = "{water_class}.parquet"

# Admin-2 income and consumption forecasts: <admin2_income_root>/<filename>
ADMIN2_LDIPC_FILENAME: Final = "LSAEadmin2_ldipc_mean_forecasts_scenarios_2010PPP.csv"
ADMIN2_GDPPC_FILENAME: Final = "LSAEadmin2_gdppc_mean_forecasts_scenarios_2010PPP.csv"
ADMIN2_MEDIAN_CONSUMPTION_FILENAME: Final = (
    "LSAEadmin2_median_consumppc_forecasts_scenarios_2021PPP_fixQAT.csv"
)
ADMIN2_CONSUMPTION_DISTRIBUTION_FILENAME: Final = (
    "admin2_consumppc_distribution_estimates_scenarios_fixQAT.csv"
)
# Columns of the admin-2 income tables
YEAR_ID_COLUMN: Final = "year_id"
ISO3_COLUMN: Final = "country_ISO3"
SCENARIO_COLUMN: Final = "scenario"
GDPPC_COLUMN: Final = "gdppc_mean"
POP_MASKING_FLAG_COLUMN: Final = "pop_masking_flag"
ZERO_POP_MASKING_FLAG_COLUMN: Final = "zero_pop_masking_flag"

# Top-level folders of the output node: <project_output_root>/<folder>
REFERENCES_DIR: Final = "00-references"
RAW_DATA_DIR: Final = "01-raw_data"
PROCESSED_DATA_DIR: Final = "02-processed_data"
OUTPUT_DIR: Final = "03-output"

# Literature: <project_output_root>/<REFERENCES_DIR>/<LITERATURE_DIR>/
LITERATURE_DIR: Final = "habitability_refs"
LITERATURE_REVIEW_FILENAME: Final = (
    "Habitability & the Human Niche — Literature Review and Data Landscape.md"
)
LITERATURE_TEXT_DIR: Final = "txt"
"""Plain-text extractions of the papers; filenames match the review's reference list."""
LITERATURE_PDF_DIR: Final = "pdf"
