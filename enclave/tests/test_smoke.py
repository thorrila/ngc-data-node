from fastapi.testclient import TestClient

from ngc_enclave.main import app

client = TestClient(app)


def test_health_returns_ok():
    """Health endpoint should always return 200 with status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
