"""Real loopback HTTP upload: cookies, CSRF, URL dispatch, body limit and image pipeline."""

import uuid
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.test.client import encode_multipart

from apps.catalog.models import ProductPhoto
from tests.test_identity import owner_client
from tests.test_remediation_access import noisy_image


@pytest.mark.django_db(transaction=True)
def test_gallery_upload_over_real_http_preserves_boundaries(
    identity_data, catalog_data, live_server, tmp_path
):
    admin = owner_client(identity_data)
    csrf = admin.get("/api/v1/csrf/").json()["csrf_token"]
    cookie = "; ".join(f"{name}={item.value}" for name, item in admin.cookies.items())
    assert live_server.url.startswith(("http://localhost:", "http://127.0.0.1:"))
    endpoint = live_server.url + f"/api/v1/admin/products/{catalog_data[3].id}/photos/"

    def send(body, *, authenticated=True, content_type="multipart/form-data; boundary=TapServeLab"):
        headers = {"Content-Type": content_type}
        if authenticated:
            headers.update({"Cookie": cookie, "X-CSRFToken": csrf})
        request = Request(endpoint, data=body, headers=headers, method="POST")  # noqa: S310 - pytest loopback.
        try:
            with urlopen(request, timeout=15) as response:  # noqa: S310 - live_server loopback only.
                return response.status
        except HTTPError as error:
            return error.code

    def multipart():
        return encode_multipart(
            "TapServeLab", {"idempotency_key": str(uuid.uuid4()), "image": noisy_image()}
        )

    with override_settings(MEDIA_ROOT=tmp_path):
        valid = multipart()
        assert len(valid) > 65536
        assert send(valid) == 201
        assert send(multipart(), authenticated=False) in {401, 403}
        assert send(b"invalid multipart", content_type="multipart/form-data") == 400
        malformed = encode_multipart(
            "TapServeLab", {"idempotency_key": str(uuid.uuid4()), "image": "invalid"}
        )
        assert send(malformed) == 400
        above_file_limit = encode_multipart(
            "TapServeLab",
            {
                "idempotency_key": str(uuid.uuid4()),
                "image": SimpleUploadedFile(
                    "synthetic-large.png",
                    b"x" * (settings.PRODUCT_IMAGE_MAX_BYTES + 1),
                    content_type="image/png",
                ),
            },
        )
        assert send(above_file_limit) == 400
        assert ProductPhoto.objects.count() == 1
