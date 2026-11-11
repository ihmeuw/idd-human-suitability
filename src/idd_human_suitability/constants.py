"""Relative path fragments, ``paths.yaml`` key names, column names and enums.

No absolute path lives here. Absolute roots come from the gitignored ``paths.yaml`` through
``idd_human_suitability.paths``; this module names the keys and the fragments below them.
"""

from __future__ import annotations

from typing import Final

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
OVERTURE_WATER_ROOT_KEY: Final = "overture_water_root"
"""Water polygons, one GeoParquet file per water class."""
ADMIN2_INCOME_ROOT_KEY: Final = "admin2_income_root"
"""Admin-2 income and consumption forecast tables."""

# Climate: <climate_root>/<fragment>. Both layouts were confirmed on disk on 2026-11-11
# (historical years as four digits, draws as three zero-padded digits).
CLIMATE_HISTORICAL_FILE: Final = "raw/historical/{variable}/{year}_era5.nc"
CLIMATE_SCENARIO_FILE: Final = "{scenario}/{variable}/{draw}.nc"

# Building tiles: <building_tiles_root>/<fragment>. The tile file layout was confirmed on
# disk on 2026-11-11 for one source and period at 100 m.
TILE_INDEX_FILE: Final = "{resolution}m/tile_index.parquet"
BUILDING_TILE_FILE: Final = "{resolution}m/{source}/{period}/{block_key}_{band}.tif"

# Population: <population_root>/<fragment>. Confirmed on disk on 2026-11-11: one file per
# year, named <year>q1.tif. ``version`` is a dated release or POPULATION_CURRENT_VERSION, a
# link that moves when a new release is promoted. The 100 m files are virtual mosaics of the
# model's tiles, so a window read touches only the tiles it covers.
POPULATION_FILE: Final = "{version}/{crs}_{resolution}/{year}q1.tif"
POPULATION_CURRENT_VERSION: Final = "current"
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
