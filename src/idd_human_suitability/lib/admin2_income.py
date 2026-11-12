"""The admin-2 income forecast tables: one country, year and scenario at a time.

The files are large CSVs (hundreds of MB) covering every admin-2 unit, year and scenario. They
are scanned with a filter and explicit column types, so only the rows asked for reach memory.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds
from idd_spatial_analysis.constants import LOCATION_ID_COLUMN

from idd_human_suitability import constants as c
from idd_human_suitability.paths import root

_GDPPC_SCHEMA = pa.schema(
    [
        (c.YEAR_ID_COLUMN, pa.int16()),
        (LOCATION_ID_COLUMN, pa.int32()),
        (c.POP_MASKING_FLAG_COLUMN, pa.int8()),
        (c.ZERO_POP_MASKING_FLAG_COLUMN, pa.int8()),
        (c.ISO3_COLUMN, pa.string()),
        (c.SCENARIO_COLUMN, pa.string()),
        (c.GDPPC_COLUMN, pa.float64()),
    ]
)


def load_admin2_gdppc(
    iso3: str, year: int, scenario: str, *, income_root: Path | None = None
) -> pd.DataFrame:
    """GDP per capita of every admin-2 unit of one country in one year under one scenario.

    One row per unit, sorted by ``location_id`` (int32, the shapefiles' ``loc_id``), with
    ``gdppc_mean`` (float64, 2010 PPP dollars as the file name states) and the two masking
    flags as booleans. Raises ``ValueError`` when the filter matches no row or a unit appears
    twice.
    """
    base = income_root if income_root is not None else root(c.ADMIN2_INCOME_ROOT_KEY)
    path = Path(base) / c.ADMIN2_GDPPC_FILENAME
    if not path.exists():
        msg = f"admin-2 GDP per capita table not found: {path}"
        raise FileNotFoundError(msg)
    dataset = ds.dataset(path, format="csv", schema=_GDPPC_SCHEMA)
    wanted = (
        (ds.field(c.ISO3_COLUMN) == iso3)
        & (ds.field(c.YEAR_ID_COLUMN) == year)
        & (ds.field(c.SCENARIO_COLUMN) == scenario)
    )
    columns = [
        LOCATION_ID_COLUMN,
        c.GDPPC_COLUMN,
        c.POP_MASKING_FLAG_COLUMN,
        c.ZERO_POP_MASKING_FLAG_COLUMN,
    ]
    table = dataset.to_table(filter=wanted, columns=columns)
    if table.num_rows == 0:
        msg = f"{path.name}: no rows for country {iso3!r}, year {year}, scenario {scenario!r}"
        raise ValueError(msg)
    frame = pd.DataFrame(
        {
            LOCATION_ID_COLUMN: table.column(LOCATION_ID_COLUMN).to_numpy().astype("int32"),
            c.GDPPC_COLUMN: table.column(c.GDPPC_COLUMN).to_numpy().astype("float64"),
            c.POP_MASKING_FLAG_COLUMN: table.column(c.POP_MASKING_FLAG_COLUMN)
            .to_numpy()
            .astype(bool),
            c.ZERO_POP_MASKING_FLAG_COLUMN: table.column(c.ZERO_POP_MASKING_FLAG_COLUMN)
            .to_numpy()
            .astype(bool),
        }
    )
    duplicated = frame.loc[frame[LOCATION_ID_COLUMN].duplicated(), LOCATION_ID_COLUMN]
    if not duplicated.empty:
        msg = f"{path.name}: units appear more than once: {sorted(set(duplicated.tolist()))[:10]}"
        raise ValueError(msg)
    return frame.sort_values(LOCATION_ID_COLUMN).reset_index(drop=True)
