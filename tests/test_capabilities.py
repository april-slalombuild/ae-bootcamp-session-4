import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.app import create_app


def test_capabilities_endpoint_returns_seeded_capabilities(tmp_path):
    app = create_app(tmp_path / "capabilities.sqlite")
    client = TestClient(app)

    response = client.get("/capabilities")

    assert response.status_code == 200
    capabilities = response.json()
    assert "Cloud Architecture" in capabilities
    assert capabilities["Cloud Architecture"]["consultants"] == [
        "alice.smith@slalom.com",
        "bob.johnson@slalom.com",
    ]


def test_registration_persists_across_app_instances(tmp_path):
    db_path = tmp_path / "capabilities.sqlite"
    consultant_email = "persistent.consultant@slalom.com"

    first_app = create_app(db_path)
    first_client = TestClient(first_app)
    register_response = first_client.post(
        "/capabilities/Cloud%20Architecture/register",
        params={"email": consultant_email},
    )

    assert register_response.status_code == 200

    second_app = create_app(db_path)
    second_client = TestClient(second_app)
    capabilities_response = second_client.get("/capabilities")

    assert capabilities_response.status_code == 200
    capabilities = capabilities_response.json()
    assert consultant_email in capabilities["Cloud Architecture"]["consultants"]