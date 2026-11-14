"""Live loopback HTTP/proxy/cookie/WebSocket checks; only login/logout and socket leases persist."""

import asyncio
import json
import re
from http.cookiejar import CookieJar
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

from cryptography.fernet import Fernet
from local_env import ROOT, load


def request(
    opener, origin, path, *, body=None, method=None, csrf=None, expected=200, header_origin=None
):
    if not re.fullmatch(
        r"http://127\.0\.0\.1:(5176|5177|8003|8004)", origin
    ) or not path.startswith("/"):
        raise ValueError("Live smoke only accepts the configured loopback ports")
    headers = {"Origin": header_origin or origin}
    if csrf:
        headers["X-CSRFToken"] = csrf
    if body is not None:
        headers["Content-Type"] = "application/json"
    message = Request(  # noqa: S310 - exact loopback allowlist above.
        origin + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers=headers,
        method=method,
    )
    try:
        response = opener.open(message, timeout=10)  # noqa: S310 - load() fixes loopback origins.
    except HTTPError as error:
        response = error
    with response:
        if response.status != expected:
            raise ValueError(
                f"Live {path} expected HTTP {expected}, received {response.status}; details withheld"
            )
        data = response.read(2 * 1024 * 1024)
        return (
            json.loads(data) if response.headers.get_content_type() == "application/json" else data
        )


async def websocket(origin, cookie):
    # Autobahn is already a Daphne dependency; no extra websocket client package is needed.
    from autobahn.asyncio.websocket import WebSocketClientFactory, WebSocketClientProtocol

    loop = asyncio.get_running_loop()
    received = loop.create_future()

    class Probe(WebSocketClientProtocol):
        def onMessage(self, payload, isBinary):
            if received.done():
                return
            try:
                value = json.loads(payload)
                if isBinary or value != {
                    "type": "refresh",
                    "event_id": None,
                    "kind": "SNAPSHOT_REQUIRED",
                }:
                    raise ValueError("Live WebSocket did not deliver its scoped initial snapshot")
                received.set_result(True)
            except (ValueError, UnicodeDecodeError) as error:
                received.set_exception(error)
            self.sendClose()

        def onClose(self, wasClean, code, reason):
            if not received.done():
                received.set_exception(
                    ValueError(f"Live WebSocket closed before snapshot (code {code})")
                )

    factory = WebSocketClientFactory(
        origin.replace("http:", "ws:") + "/ws/v1/staff/", origin=origin, headers={"Cookie": cookie}
    )
    factory.protocol = Probe
    transport, _ = await loop.create_connection(factory, "127.0.0.1", int(origin.rsplit(":", 1)[1]))
    try:
        await asyncio.wait_for(received, timeout=12)
    finally:
        transport.close()


def smoke():
    profiles = {env: load(env) for env in ("dev", "qa")}
    jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar))
    logged_in = []
    try:
        for env, config in profiles.items():
            origin = config["PUBLIC_APP_ORIGIN"]
            page = request(opener, origin, "/staff/login")
            if b'id="root"' not in page:
                raise ValueError("Live frontend HTML did not contain its application root")
            expected = {"status": "ok", "database": "ok"}
            for target in (origin, f"http://127.0.0.1:{config['BACKEND_PORT']}"):
                if request(opener, target, "/api/v1/health/") != expected:
                    raise ValueError("Live PostgreSQL/proxy health failed")
            vault = ROOT / ".local/environments" / env / "demo-credentials.enc"
            accounts = json.loads(
                Fernet(config["TAPSERVE_TOKEN_KEYS"].encode()).decrypt(vault.read_bytes())
            )
            csrf = request(opener, origin, "/api/v1/csrf/")["csrf_token"]
            request(
                opener,
                origin,
                "/api/v1/staff/login/",
                body={
                    "company": f"{env}-tapserve-demo",
                    "unit": "centro",
                    "login_code": "demo-waiter",
                    "pin": accounts["a-centro:waiter"]["pin"],
                },
                csrf=csrf,
            )
            logged_in.append(origin)
            other = profiles["qa" if env == "dev" else "dev"]["PUBLIC_APP_ORIGIN"]
            if len(logged_in) == 1:
                request(opener, other, "/api/v1/staff/me/", expected=401)
            csrf = request(opener, origin, "/api/v1/csrf/")["csrf_token"]
            request(
                opener,
                origin,
                "/api/v1/staff/logout/",
                body={},
                csrf=csrf,
                header_origin=other,
                expected=403,
            )
            request(opener, origin, "/api/v1/staff/me/")
            message = Request(origin + "/ws/v1/staff/")  # noqa: S310 - origin validated by load().
            jar.add_cookie_header(message)
            cookie = message.get_header("Cookie", "")
            if "tapserve-" + env + "-session=" not in cookie:
                raise ValueError("Expected environment-scoped session cookie missing")
            asyncio.run(websocket(origin, cookie))
            print(
                env.upper(),
                "PASS: live frontend, direct/proxied API/PG, PIN, distinct cookies, cross-origin CSRF and proxied WebSocket snapshot",
            )
        # Both cookies coexist in the same browser-like jar, and each realm remains independently authenticated.
        for origin in logged_in:
            request(opener, origin, "/api/v1/staff/me/")
    finally:
        for index, origin in enumerate(logged_in):
            csrf = request(opener, origin, "/api/v1/csrf/")["csrf_token"]
            request(opener, origin, "/api/v1/staff/logout/", body={}, csrf=csrf, expected=204)
            request(opener, origin, "/api/v1/staff/me/", expected=401)
            for remaining in logged_in[index + 1:]:
                request(opener, remaining, "/api/v1/staff/me/")
