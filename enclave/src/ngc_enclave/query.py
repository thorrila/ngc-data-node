import threading
from typing import Any

import duckdb
from cachetools import TTLCache, cached

# Caches are shared across the module. TTL of 60 seconds ensures data freshness.
variant_cache = TTLCache(maxsize=128, ttl=600)
variant_lock = threading.Lock()
allele_cache = TTLCache(maxsize=128, ttl=600)
allele_lock = threading.Lock()


def _run_query(sql: str, params: dict) -> tuple[list[str], list[tuple]]:
    """
    Execute a parameterized DuckDB query safely.

    - Fix 1 (SQL injection): user-supplied values are passed as parameters ($name),
      never interpolated into the SQL string directly.
    - Fix 2 (double-query): we execute once and read both .description and .fetchall()
      from the same cursor object.
    - Fix 3 (thread-safety): duckdb.connect() creates a new in-process connection for
      this call only. The global duckdb.query() shares a single connection across all
      threads, which causes "DuckDB Collision" errors under concurrent load.
    """
    with duckdb.connect() as con:
        cur = con.execute(sql, params)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
    return columns, rows


@cached(cache=variant_cache, lock=variant_lock)
def query_variants(
    parquet_path: str,
    chrom: str | None = None,
    pos_min: int | None = None,
    pos_max: int | None = None,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    """Query the Parquet file using DuckDB. Results are cached to handle high concurrency."""
    path = str(parquet_path)

    # Build a parameterised WHERE clause. Placeholders ($chrom etc.) are never
    # constructed from user input — only the *values* are passed separately.
    conditions = []
    params: dict[str, Any] = {}

    if chrom is not None:
        conditions.append("chrom = $chrom")
        params["chrom"] = chrom
    if pos_min is not None:
        conditions.append("pos >= $pos_min")
        params["pos_min"] = pos_min
    if pos_max is not None:
        conditions.append("pos <= $pos_max")
        params["pos_max"] = pos_max

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # DuckDB reads Parquet directly — no database server needed
    sql = f"SELECT * FROM read_parquet($path) {where_clause} LIMIT $limit"
    params["path"] = path
    params["limit"] = limit

    columns, rows = _run_query(sql, params)
    return [dict(zip(columns, row)) for row in rows]


@cached(cache=allele_cache, lock=allele_lock)
def query_allele_frequencies(
    parquet_path: str,
    chrom: str | None = None,
    pos_min: int | None = None,
    pos_max: int | None = None,
) -> list[dict[str, Any]]:
    """Calculate allele frequencies using DuckDB aggregation."""
    path = str(parquet_path)

    conditions = []
    params: dict[str, Any] = {}

    if chrom is not None:
        conditions.append("chrom = $chrom")
        params["chrom"] = chrom
    if pos_min is not None:
        conditions.append("pos >= $pos_min")
        params["pos_min"] = pos_min
    if pos_max is not None:
        conditions.append("pos <= $pos_max")
        params["pos_max"] = pos_max

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # Group by the unique variant signature and count occurrences.
    # $path is passed as a parameter so the path itself cannot be injected.
    sql = f"""
        SELECT
            chrom, pos, reference, alt,
            count(*) AS allele_count,
            round(
                count(*) * 1.0 /
                (SELECT count(*) FROM read_parquet($path) {where_clause}),
                4
            ) AS frequency
        FROM read_parquet($path)
        {where_clause}
        GROUP BY chrom, pos, reference, alt
        ORDER BY allele_count DESC
        LIMIT 100
    """
    params["path"] = path

    columns, rows = _run_query(sql, params)
    return [dict(zip(columns, row)) for row in rows]
