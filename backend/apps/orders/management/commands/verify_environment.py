"""Exercise real HTTP views in a rolled-back transaction, preserving operator MFA and demo data."""

import base64
import getpass
import json
import time
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.test import Client

from apps.access.services import cipher
from apps.catalog.models import Option, Product
from apps.identity.mfa import totp
from apps.orders.demo import credential_path, reference, validate_destination


def expect(response, status, label):
    if response.status_code != status:
        raise CommandError(
            f"{label}: expected HTTP {status}, received {response.status_code}; body withheld."
        )
    return (
        response.json()
        if status != 204 and response.get("Content-Type", "").startswith("application/json")
        else None
    )


def post(client, path, body, status=200, *, method="post"):
    csrf = expect(client.get("/api/v1/csrf/"), 200, "CSRF bootstrap")["csrf_token"]
    return expect(
        getattr(client, method)(path, body, content_type="application/json", HTTP_X_CSRFTOKEN=csrf),
        status,
        path.split("/")[3],
    )


def complete_mfa(client, challenge, *, realm="staff"):
    if not challenge.get("mfa_required"):
        raise CommandError("Privileged login did not require MFA.")
    if challenge["enrollment_required"]:
        encoded = parse_qs(urlsplit(challenge["provisioning_uri"]).query)["secret"][0]
        raw = base64.b32decode(encoded + "=" * (-len(encoded) % 8))
        code = totp(raw).generate(int(time.time())).decode()
    else:
        code = getpass.getpass(
            "Existing MFA: current code or unused recovery code (verification rolls back): "
        )
    post(client, f"/api/v1/{realm}/mfa/challenge/", {"code": code})


class Command(BaseCommand):
    help = "Verify local authentication/MFA, admission, ordering, receipts and isolation; all DB writes roll back."

    def add_arguments(self, parser):
        parser.add_argument("--env", choices=("dev", "qa"), required=True)

    def handle(self, *args, **options):
        env = options["env"]
        validate_destination(env)
        path = credential_path(env)
        if not path.is_file():
            raise CommandError("Seed the selected environment first.")
        accounts = json.loads(cipher().decrypt(path.read_bytes()))
        with transaction.atomic():
            try:
                self.verify(env, accounts)
            finally:
                transaction.set_rollback(True)
        self.stdout.write(
            "PASS: HTTP views, CSRF, password/MFA, PIN, QR/NFC URL, admission, menu, order/edit/status, calls, receipts, closure/history/reuse, tenant/unit authorization and logout. All writes rolled back. Live proxy/WS/browser checks are separate."
        )

    def verify(self, env, accounts):
        origin = settings.PUBLIC_APP_ORIGIN

        def client():
            return Client(
                enforce_csrf_checks=True,
                HTTP_HOST="127.0.0.1",
                HTTP_ORIGIN=origin,
                REMOTE_ADDR="127.0.0.1",
            )

        owner, waiter, other, limited, customer = [client() for _ in range(5)]
        company = f"{env}-tapserve-demo"
        login = {
            "company": company,
            "unit": "centro",
            "username": f"{env}-owner-a",
            "password": accounts["owner-a"]["password"],
        }
        expect(
            owner.post("/api/v1/staff/password-login/", login, content_type="application/json"),
            403,
            "CSRF enforcement",
        )
        challenge = post(owner, "/api/v1/staff/password-login/", login)
        expect(owner.get("/api/v1/staff/me/"), 401, "Partial login has no authorization")
        complete_mfa(owner, challenge)
        expect(owner.get("/api/v1/staff/me/"), 200, "Owner MFA")
        strong_other = None
        for key, scope, unit in (
            ("owner-b", f"{env}-horizonte-demo", "principal"),
            ("admin", company, "centro"),
            ("manager", company, "centro"),
            ("manager-shopping", company, "shopping"),
            ("manager-horizonte", f"{env}-horizonte-demo", "principal"),
        ):
            administrator = client()
            challenge = post(
                administrator,
                "/api/v1/staff/password-login/",
                {
                    "company": scope,
                    "unit": unit,
                    "username": f"{env}-{key}",
                    "password": accounts[key]["password"],
                },
            )
            complete_mfa(administrator, challenge)
            expect(administrator.get("/api/v1/staff/me/"), 200, "Administrative account/MFA")
            if key == "owner-b":
                strong_other = administrator
        platform = client()
        challenge = post(
            platform,
            "/api/v1/platform/login/",
            {"username": f"{env}-platform", "password": accounts["platform"]["password"]},
        )
        expect(platform.get("/api/v1/platform/companies/"), 401, "Partial platform login")
        complete_mfa(platform, challenge, realm="platform")
        expect(platform.get("/api/v1/platform/companies/"), 200, "Platform operator/MFA")
        expect(platform.get("/api/v1/staff/me/"), 401, "Separate platform realm")
        for who, scope, unit, key, login_code in (
            (waiter, company, "centro", "a-centro:waiter", "demo-waiter"),
            (other, f"{env}-horizonte-demo", "principal", "b-principal:waiter", "demo-waiter"),
            (limited, company, "centro", "a-centro:limited", "demo-limited"),
        ):
            post(
                who,
                "/api/v1/staff/login/",
                {
                    "company": scope,
                    "unit": unit,
                    "login_code": login_code,
                    "pin": accounts[key]["pin"],
                },
            )
        point = post(
            owner,
            "/api/v1/admin/service-points/",
            {
                "idempotency_key": str(uuid4()),
                "type": "OTHER",
                "name": "Verificação transacional " + uuid4().hex[:8],
                "nfc_enabled": True,
                "qr_enabled": True,
            },
            201,
        )
        identifier = point["id"]
        point_path = f"/api/v1/admin/service-points/{identifier}/"
        expect(other.get(point_path), 403, "Waiter cannot manage another tenant")
        expect(limited.get("/api/v1/staff/tables/"), 403, "Reduced permissions")
        link = expect(owner.get(point_path + "url/"), 200, "QR/NFC URL")["url"]
        expect(owner.get(point_path + "qr/"), 200, "QR generation")
        if strong_other is None:
            raise CommandError("The second company's owner was not verified.")
        expect(
            strong_other.get(point_path + "url/"), 404, "Other company owner has no point access"
        )
        token = link.rsplit("/", 1)[1]
        request = post(customer, "/api/v1/public/access/", {"public_token": token}, 202)
        admission = request["admission_id"]
        expect(customer.get("/api/v1/public/menu/"), 401, "Pending admission privacy")
        expect(
            other.get(f"/api/v1/staff/sessions/{uuid4()}/settlement/"),
            404,
            "Unknown tenant session",
        )
        post(
            waiter,
            f"/api/v1/staff/admissions/{admission}/decision/",
            {"idempotency_key": str(uuid4()), "status": "APPROVED"},
        )
        post(customer, f"/api/v1/public/admissions/{admission}/claim/", {})
        expect(customer.get("/api/v1/public/menu/"), 200, "Menu")
        unit_id = expect(owner.get("/api/v1/staff/me/"), 200, "Owner scope")["unit_id"]
        product = Product.objects.get(pk=reference(env, f"{unit_id}/Hambúrguer Clássico"))
        choices = list(
            Option.objects.filter(group__product=product, name="Ao ponto").values_list(
                "id", flat=True
            )
        )

        def order(browser):
            return post(
                browser,
                "/api/v1/public/orders/",
                {
                    "idempotency_key": str(uuid4()),
                    "items": [
                        {
                            "product_id": str(product.id),
                            "quantity": 1,
                            "option_ids": [str(value) for value in choices],
                            "participant_name": "Verificação Demo",
                        }
                    ],
                },
                201,
            )["batch"]

        batch = order(customer)
        session_id = batch["session_id"]
        session_path = f"/api/v1/staff/sessions/{session_id}/"
        expect(other.get(session_path + "settlement/"), 404, "Tenant isolation")
        # A same-company employee assigned only to another unit is equally denied.
        foreign_unit = client()
        post(
            foreign_unit,
            "/api/v1/staff/login/",
            {
                "company": company,
                "unit": "shopping",
                "login_code": "demo-waiter",
                "pin": accounts["a-shopping:waiter"]["pin"],
            },
        )
        expect(foreign_unit.get(session_path + "settlement/"), 404, "Unit isolation")
        item = batch["items"][0]
        kitchen = client()
        post(
            kitchen,
            "/api/v1/staff/login/",
            {
                "company": company,
                "unit": "centro",
                "login_code": "demo-kitchen",
                "pin": accounts["a-centro:kitchen"]["pin"],
            },
        )
        expect(kitchen.get("/api/v1/staff/production/items/"), 200, "KDS own sector")
        expect(kitchen.get("/api/v1/staff/tables/"), 403, "KDS cannot view all tables")
        post(
            kitchen,
            f"/api/v1/staff/items/{item['id']}/status/",
            {"idempotency_key": str(uuid4()), "expected_status": "NEW", "status": "DELIVERING"},
            403,
        )
        post(
            customer,
            f"/api/v1/public/items/{item['id']}/",
            {
                "idempotency_key": str(uuid4()),
                "expected_version": item["version"],
                "quantity": 1,
                "option_ids": [str(value) for value in choices],
                "notes": "Verificação sem persistência.",
            },
            method="patch",
        )
        call = post(
            customer,
            "/api/v1/public/service-requests/",
            {"idempotency_key": str(uuid4()), "kind": "ATTENDANT"},
            201,
        )
        previous = "OPEN"
        for state in ("ASSIGNED", "RESOLVED"):
            post(
                waiter,
                f"/api/v1/staff/service-requests/{call['id']}/status/",
                {"idempotency_key": str(uuid4()), "expected_status": previous, "status": state},
            )
            previous = state
        previous = "NEW"
        for state in ("ACCEPTED", "PREPARING", "READY", "DELIVERING", "DELIVERED"):
            post(
                owner,
                f"/api/v1/staff/items/{item['id']}/status/",
                {"idempotency_key": str(uuid4()), "expected_status": previous, "status": state},
            )
            previous = state
        post(
            customer,
            "/api/v1/public/service-requests/",
            {"idempotency_key": str(uuid4()), "kind": "CHECK"},
            201,
        )
        from decimal import Decimal

        for partial in (True, False):
            total = expect(owner.get(session_path + "settlement/"), 200, "Settlement query")
            amount = Decimal(total["remaining"])
            if partial:
                amount = (amount / 2).quantize(Decimal("0.01"))
            post(
                owner,
                session_path + "external-receipts/",
                {
                    "idempotency_key": str(uuid4()),
                    "expected_version": total["version"],
                    "point_id": identifier,
                    "amount": str(amount),
                    "method": "CARD",
                    "reason": "Verificação fictícia; será revertida pela transação.",
                },
            )
        total = expect(owner.get(session_path + "settlement/"), 200, "Full receipt")
        if Decimal(total["remaining"]) != 0:
            raise CommandError("Full declared receipt left an unexpected balance.")
        post(
            owner,
            session_path + "close/",
            {
                "idempotency_key": str(uuid4()),
                "expected_version": total["version"],
                "reason": "Verificação transacional.",
            },
        )
        expect(customer.get("/api/v1/public/context/"), 401, "Closed device revoked")
        history = expect(owner.get(f"/api/v1/staff/tables/{identifier}/history/"), 200, "History")
        if history["count"] != 1:
            raise CommandError("Closure history missing.")
        newcomer = client()
        request = post(newcomer, "/api/v1/public/access/", {"public_token": token}, 202)
        post(
            waiter,
            f"/api/v1/staff/admissions/{request['admission_id']}/decision/",
            {"idempotency_key": str(uuid4()), "status": "APPROVED"},
        )
        post(newcomer, f"/api/v1/public/admissions/{request['admission_id']}/claim/", {})
        if order(newcomer)["session_id"] == session_id:
            raise CommandError("New occupation reused the closed session.")
        post(owner, "/api/v1/staff/logout/", {}, 204)
        expect(owner.get("/api/v1/staff/me/"), 401, "Logout")
