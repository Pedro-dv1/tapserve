import pytest
from django.test import Client, override_settings


@pytest.mark.django_db
@pytest.mark.parametrize("debug", [True, False])
def test_api_404_is_json_without_masking_auth_or_valid_endpoints(debug):
    client = Client()
    with override_settings(DEBUG=debug):
        response = client.get("/api/v1/no-such-endpoint/")
        assert response.status_code == 404
        assert response["Content-Type"].startswith("application/json")
        assert response.json()["error"]["code"] == "not_found"
        assert client.get("/api/v1/public/context/").status_code == 401
        assert client.get("/api/v1/admin/unit-logo/").status_code == 401
        assert client.get("/api/v1/health/").status_code == 200
        # Preserve Django's existing canonical trailing-slash redirects.
        response = client.get("/api/v1/health")
        assert response.status_code == 301
        assert response["Location"] == "/api/v1/health/"
