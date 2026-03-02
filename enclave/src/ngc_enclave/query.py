from typing import Any

import duckdb
from cachetools import TTLCache, cached

# Caches are shared across the module. TTL of 60 seconds ensures data freshness.
variant_cache = TTLCache(maxsize=128, ttl=60)
allele_cache = TTLCache(maxsize=128, ttl=60)


@cached(cache=variant_cache)
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

    # DuckDB reads Parquet directly — results are transferred via Arrow for speed
    sql = f"SELECT * FROM read_parquet('{path}') {where_clause}"
    return duckdb.query(sql).arrow().to_pylist()


@cached(cache=allele_cache)
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

    return duckdb.query(sql).arrow().to_pylist()
