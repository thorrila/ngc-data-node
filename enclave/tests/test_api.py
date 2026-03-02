import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from ngc_enclave.db import get_db
from ngc_enclave.main import app, verify_api_key

# Ensure API key is set for testing
os.environ["NGC_API_KEY"] = "ngc"
VALID_API_KEY = "ngc"
HEADERS = {"Authorization": f"Bearer {VALID_API_KEY}"}


@pytest.mark.asyncio
async def test_health_check():
    """Test that the health check endpoint returns 200 OK."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_missing_api_key():
    """Test that requests without an API key are rejected."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/variants")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing Authorization Header"


@pytest.mark.asyncio
async def test_invalid_api_key():
    """Test that requests with an invalid API key are rejected."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/variants", headers={"Authorization": "Bearer wrong-token"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid API Key"


@pytest.mark.asyncio
@patch("ngc_enclave.main.query_variants")
@patch("ngc_enclave.main.log_request", new_callable=AsyncMock)
async def test_get_variants_success(mock_log, mock_query):
    """Test that /variants returns data and logs the request successfully."""
    # Mock DuckDB response
    mock_query.return_value = [{"chrom": "chr1", "pos": 1000, "reference": "A", "alt": "T"}]

    app.dependency_overrides[verify_api_key] = lambda: VALID_API_KEY
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/variants?chr=chr1&pos_min=1000&pos_max=2000", headers=HEADERS)

        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["chrom"] == "chr1"

        # Ensure DuckDB was called with correct parameters
        mock_query.assert_called_once()
        kwargs = mock_query.call_args.kwargs
        assert kwargs.get("chrom") == "chr1"
        assert kwargs.get("pos_min") == 1000
        assert kwargs.get("pos_max") == 2000

        # Ensure auditing logged 200 OK
        mock_log.assert_called_once()
        assert mock_log.call_args.args[3] == 200  # HTTP status code parameter
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
@patch("ngc_enclave.main.query_allele_frequencies")
@patch("ngc_enclave.main.log_request", new_callable=AsyncMock)
async def test_get_alleles_success(mock_log, mock_query):
    """Test that /alleles returns aggregated data."""
    mock_query.return_value = [{"chrom": "chr1", "pos": 1000, "allele_count": 5, "frequency": 0.25}]

    app.dependency_overrides[verify_api_key] = lambda: VALID_API_KEY
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/alleles?chr=chr1", headers=HEADERS)

        assert response.status_code == 200
        assert response.json()[0]["frequency"] == 0.25
        mock_query.assert_called_once()
        mock_log.assert_called_once()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
@patch("ngc_enclave.main.get_db")
@patch("ngc_enclave.main.log_request", new_callable=AsyncMock)
async def test_list_datasets_success(mock_log, mock_get_db):
    """Test the /datasets endpoint with database mocking."""
    # Mocking SQLAlchemy async session
    mock_session = AsyncMock()

    class MockRow:
        def __init__(self, data):
            self._mapping = data

    mock_result = MagicMock()
    mock_result.fetchall.return_value = [MockRow({"id": 1, "filename": "test.vcf", "ingested_at": "2025-01-01"})]
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[verify_api_key] = lambda: VALID_API_KEY
    app.dependency_overrides[get_db] = lambda: mock_session

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/datasets", headers=HEADERS)
            assert response.status_code == 200
            assert response.json()[0]["filename"] == "test.vcf"
    finally:
        app.dependency_overrides.clear()
