import functools
from typing import Any

import duckdb


@functools.lru_cache(maxsize=128)
def query_variants(
    parquet_path: str,
    chrom: str | None = None,
    pos_min: int | None = None,
    pos_max: int | None = None,
) -> list[dict[str, Any]]:
    """Query the Parquet file using DuckDB. Results are cached to handle high concurrency."""
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


@functools.lru_cache(maxsize=128)
def query_allele_frequencies(
    parquet_path: str,
    chrom: str | None = None,
    pos_min: int | None = None,
    pos_max: int | None = None,
) -> list[dict[str, Any]]:
    """Calculate allele frequencies using DuckDB aggregation."""
    path = str(parquet_path)

    conditions = []
    if chrom:
        conditions.append(f"chrom = '{chrom}'")
    if pos_min is not None:
        conditions.append(f"pos >= {pos_min}")
    if pos_max is not None:
        conditions.append(f"pos <= {pos_max}")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # Group by the unique variant signature and count occurrences
    sql = f"""
        SELECT
            chrom, pos, reference, alt,
            count(*) as allele_count,
            round(count(*) * 1.0 / (SELECT count(*) FROM read_parquet('{path}') {where_clause}), 4) as frequency
        FROM read_parquet('{path}')
        {where_clause}
        GROUP BY chrom, pos, reference, alt
        ORDER BY allele_count DESC
        LIMIT 100
    """

    result = duckdb.query(sql).fetchall()
    columns = [desc[0] for desc in duckdb.query(sql).description]

    return [dict(zip(columns, row)) for row in result]
