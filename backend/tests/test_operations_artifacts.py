import json
import runpy
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "field,value",
    [
        ("PGHOST", "192.168.1.1"),
        ("PGHOST", "database.example"),
        ("PGDATABASE", "tapserve"),
        ("PGPORT", "5432;bad"),
        ("PGSERVICE", "production"),
        ("TAPSERVE_BACKUP_LAB", ""),
    ],
)
def test_lab_restore_rejects_non_disposable_or_nonlocal_configuration(field, value):
    validate = runpy.run_path(str(ROOT / "deploy/lab_backup.py"))["database_arguments"]
    environment = {
        "PGHOST": "127.0.0.1",
        "PGPORT": "55432",
        "PGUSER": "lab_user",
        "PGDATABASE": "tapserve_lab_" + "a" * 32,
        "TAPSERVE_BACKUP_LAB": "tapserve_lab_" + "a" * 32,
    }
    environment[field] = value
    with pytest.raises(ValueError):
        validate(environment)


def test_lab_backup_never_overwrites_existing_archive(tmp_path):
    runner = runpy.run_path(str(ROOT / "deploy/lab_backup.py"))["main"]
    name = "tapserve_lab_" + "a" * 32
    environment = {
        "PGHOST": "127.0.0.1",
        "PGPORT": "55432",
        "PGUSER": "lab_user",
        "PGDATABASE": name,
        "TAPSERVE_BACKUP_LAB": name,
    }
    archive = tmp_path / "synthetic.dump"
    archive.write_bytes(b"original synthetic archive")
    with patch.dict("os.environ", environment, clear=True), patch("subprocess.run") as execute:
        with pytest.raises(SystemExit) as error:
            runner(["backup", str(archive), "--confirm-database", name])
    assert error.value.code == 1
    execute.assert_not_called()
    assert archive.read_bytes() == b"original synthetic archive"


def test_production_examples_preserve_transport_and_token_log_boundaries():
    proxy = (ROOT / "deploy/nginx.conf.example").read_text(encoding="utf-8")
    service = (ROOT / "deploy/tapserve@.service").read_text(encoding="utf-8")
    policy = json.loads((ROOT / "deploy/s3-policy.json.example").read_text(encoding="utf-8"))
    assert "proxy_ssl_verify on;" in proxy
    assert "connect-src 'self' wss://tapserve.example;" in proxy
    assert "proxy_pass https://tapserve_asgi;" in proxy
    assert "X-TapServe-Client-IP $remote_addr" in proxy
    assert "proxy_next_upstream off;" in proxy
    assert "ssl:port=%i:interface=127.0.0.1" in service
    assert "--websocket-max-message-size 256" in service
    assert "--access-log /dev/null" in service
    assert "--proxy-headers" not in service
    format_definition = proxy.split("log_format tapserve_safe", 1)[1].split(";", 1)[0]
    assert not any(
        value in format_definition
        for value in ("$uri", "$request_uri", "$request ", "$http_cookie", "$http_referer")
    )
    assert all("*" != statement["Resource"] for statement in policy["Statement"])
