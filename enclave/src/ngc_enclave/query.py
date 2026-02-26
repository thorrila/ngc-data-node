from pathlib import Path
from typing import Any

import duckdb


def query_variants(
    parquet_path: str | Path,
    chrom: str | None = None,
    pos_min: int | None = None,
    pos_max: int | None = None,
) -> list[dict[str, Any]]:
    """Query the Parquet file using DuckDB. Filters are all optional."""
    path = str(parquet_path)

    # Build WHERE clause dynamically from whichever filters were provided
    conditions = []
    if chrom:
        conditions.append(f"chrom = '{chrom}'")
    if pos_min is not None:
        conditions.append(f"pos >= {pos_min}")
    if pos_max is not None:
        conditions.append(f"pos <= {pos_max}")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # DuckDB reads Parquet directly — no database server needed
    sql = f"SELECT * FROM read_parquet('{path}') {where_clause}"
    result = duckdb.query(sql).fetchall()
    columns = [desc[0] for desc in duckdb.query(sql).description]

    # Convert list of tuples → list of dicts (JSON-serialisable)
    return [dict(zip(columns, row)) for row in result]
