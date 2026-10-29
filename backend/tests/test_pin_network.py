import pytest
from django.test import Client, RequestFactory, override_settings
from rest_framework.exceptions import PermissionDenied

from common.network import client_address
from tests.test_identity import post_with_csrf


def test_forwarded_client_address_requires_explicit_proxy_trust():
    factory = RequestFactory()
    request = factory.get(
        "/",
        REMOTE_ADDR="198.51.100.10",
        HTTP_X_TAPSERVE_CLIENT_IP="127.0.0.1",
        HTTP_X_FORWARDED_FOR="127.0.0.1",
    )
    assert client_address(request) == "198.51.100.10"
    with override_settings(TRUSTED_PROXY_NETWORKS=["198.51.100.10/32"]):
        assert client_address(request) == "127.0.0.1"
        for value in ("", "bad", "127.0.0.1,198.51.100.10"):
            request.META["HTTP_X_TAPSERVE_CLIENT_IP"] = value
            with pytest.raises(PermissionDenied):
                client_address(request)


def test_pin_is_denied_outside_allowed_network_and_forged_headers_do_not_bypass(identity_data):
    client = Client(
        enforce_csrf_checks=True,
        REMOTE_ADDR="198.51.100.10",
        HTTP_X_TAPSERVE_CLIENT_IP="127.0.0.1",
        HTTP_X_FORWARDED_FOR="127.0.0.1",
    )
    assert (
        post_with_csrf(
            client,
            "/api/v1/staff/login/",
            {"company": "company-a", "unit": "unit-a", "login_code": "waiter", "pin": "123456"},
        ).status_code
        == 403
    )
    assert (
        post_with_csrf(
            client,
            "/api/v1/staff/password-login/",
            {
                "company": "company-a",
                "unit": "unit-a",
                "username": "owner",
                "password": identity_data[-1],
            },
        ).status_code
        == 200
    )
