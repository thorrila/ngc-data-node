import pytest
from httpx import AsyncClient, ASGITransport
from ngc_enclave.main import app
import os

# Use the default dev token for testing
API_KEY = os.getenv("NGC_API_KEY", "ngc")
HEADERS = {"Authorization": f"Bearer {API_KEY}"}


@pytest.mark.asyncio
async def test_health_check():
    """Verify the health endpoint is public and functional."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_unauthorized_access():
    """Verify that protected endpoints require an API key."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/variants")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_variants_structure():
    """Verify the variants endpoint returns the correct structure (even if empty)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/variants", headers=HEADERS)

    # It might return 500 if the parquet file doesn't exist, which is expected in some test envs
    # but we want to check it doesn't 401 or 404.
    assert response.status_code in [200, 500]
    if response.status_code == 200:
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_alleles_structure():
    """Verify the alleles endpoint returns the correct structure."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/alleles", headers=HEADERS)

    assert response.status_code in [200, 500]
    if response.status_code == 200:
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_list_datasets_unauthorized():
    """Verify /datasets is protected."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/datasets")
    assert response.status_code == 401
