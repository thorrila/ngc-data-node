"""Tests for query.py — exercises real DuckDB against a real Parquet fixture."""

import os
from unittest.mock import patch

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from httpx import ASGITransport, AsyncClient

os.environ["NGC_API_KEY"] = "ngc"
HEADERS = {"Authorization": "Bearer ngc"}


@pytest.fixture(scope="module")
def parquet_path(tmp_path_factory):
    path = str(tmp_path_factory.mktemp("data") / "test.parquet")
    pq.write_table(
        pa.table(
            {
                "chrom": ["1", "1", "1", "2", "2", "X"],
                "pos": pa.array([100, 200, 300, 100, 200, 100], type=pa.int64()),
                "id": [".", "rs1", ".", ".", "rs2", "."],
                "reference": ["A", "C", "G", "T", "A", "C"],
                "alt": ["T", "G", "A", "C", "T", "G"],
                "sample_id_hash": ["abc"] * 6,
            }
        ),
        path,
    )
    return path


def clear():
    from ngc_enclave.query import allele_cache, variant_cache

    variant_cache.clear()
    allele_cache.clear()


# --- Filters ---


def test_no_filter_returns_all(parquet_path):
    from ngc_enclave.query import query_variants

    clear()
    assert len(query_variants(parquet_path)) == 6


def test_chrom_filter(parquet_path):
    from ngc_enclave.query import query_variants

    clear()
    results = query_variants(parquet_path, chrom="1")
    assert len(results) == 3 and all(r["chrom"] == "1" for r in results)


def test_pos_range_filter(parquet_path):
    from ngc_enclave.query import query_variants

    clear()
    results = query_variants(parquet_path, pos_min=150, pos_max=250)
    assert all(150 <= r["pos"] <= 250 for r in results)


def test_no_match_returns_empty(parquet_path):
    from ngc_enclave.query import query_variants

    clear()
    assert query_variants(parquet_path, chrom="MT") == []


def test_allele_frequencies(parquet_path):
    from ngc_enclave.query import query_allele_frequencies

    clear()
    results = query_allele_frequencies(parquet_path)
    assert all("frequency" in r and 0.0 <= r["frequency"] <= 1.0 for r in results)


# --- Security ---


def test_sql_injection_is_safe(parquet_path):
    from ngc_enclave.query import query_variants

    clear()
    assert query_variants(parquet_path, chrom="1'; DROP TABLE x; --") == []


# --- Limit enforcement (API layer) ---


@pytest.mark.asyncio
@patch("ngc_enclave.main.query_variants", return_value=[])
@patch("ngc_enclave.main.log_request", return_value=None)
async def test_default_limit_is_1000(mock_log, mock_q):
    from ngc_enclave.main import app, verify_api_key

    app.dependency_overrides[verify_api_key] = lambda: "ngc"
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.get("/variants", headers=HEADERS)
        assert mock_q.call_args.kwargs["limit"] == 1000
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
@patch("ngc_enclave.main.query_variants", return_value=[])
@patch("ngc_enclave.main.log_request", return_value=None)
async def test_limit_capped_at_5000(mock_log, mock_q):
    from ngc_enclave.main import app, verify_api_key

    app.dependency_overrides[verify_api_key] = lambda: "ngc"
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.get("/variants?limit=99999", headers=HEADERS)
        assert mock_q.call_args.kwargs["limit"] == 5000
    finally:
        app.dependency_overrides.clear()


# --- Cache ---


def test_cache_hit_calls_duckdb_once(parquet_path):
    from ngc_enclave.query import query_variants

    clear()
    count = 0
    orig = __import__("duckdb").connect

    def counting(*a, **kw):
        nonlocal count
        count += 1
        return orig(*a, **kw)

    with patch("duckdb.connect", side_effect=counting):
        query_variants(parquet_path, chrom="2")
        query_variants(parquet_path, chrom="2")  # cache hit
    assert count == 1, f"Expected 1 DuckDB call, got {count}"


def test_different_args_miss_cache(parquet_path):
    from ngc_enclave.query import query_variants

    clear()
    count = 0
    orig = __import__("duckdb").connect

    def counting(*a, **kw):
        nonlocal count
        count += 1
        return orig(*a, **kw)

    with patch("duckdb.connect", side_effect=counting):
        query_variants(parquet_path, chrom="1")
        query_variants(parquet_path, chrom="2")  # different args → cache miss
    assert count == 2, f"Expected 2 DuckDB calls, got {count}"
