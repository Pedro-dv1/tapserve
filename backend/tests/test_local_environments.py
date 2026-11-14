"""No database access: fail closed before any connection or seed mutation."""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("local_env", ROOT / "scripts/local_env.py")
local_env = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local_env)


@pytest.fixture
def profiles(monkeypatch):
    # Ordinary inherited Windows permissions also work under Codex's restricted token.
    tmp_path = ROOT / ".local/environments" / ("config-test-" + uuid4().hex)
    tmp_path.mkdir(parents=True)
    (tmp_path / "backend").mkdir()
    (tmp_path / "frontend").mkdir()
    monkeypatch.setattr(local_env, "ROOT", tmp_path)
    local_env.initialize()
    return tmp_path


def test_env_initialization_preserves_existing_secrets_and_does_not_reuse_parent(
    profiles, monkeypatch
):
    paths = list(profiles.glob("backend/.env.*.local"))
    before = {path: path.read_bytes() for path in paths}
    monkeypatch.setenv("POSTGRES_DB", "do_not_touch")
    monkeypatch.setenv("POSTGRES_PASSWORD", "legacy-password-is-not-reused")
    local_env.initialize()
    assert before == {path: path.read_bytes() for path in paths}
    dev, qa = [local_env.load(profile, credentials=False) for profile in ("dev", "qa")]
    assert dev["POSTGRES_DB"] == "tapserve_dev" and qa["POSTGRES_DB"] == "tapserve_qa"
    assert dev["POSTGRES_PASSWORD"] == qa["POSTGRES_PASSWORD"] == ""
    for key in ("DJANGO_SECRET_KEY", "TAPSERVE_TOKEN_KEYS", "POSTGRES_USER"):
        assert dev[key] != qa[key]
    assert os.environ["POSTGRES_DB"] == "do_not_touch"
    with pytest.raises(ValueError, match="Fill POSTGRES_PASSWORD"):
        local_env.load("dev")


def test_mixed_frontend_or_database_is_rejected(profiles):
    path = profiles / "frontend/.env.qa.local"
    original = path.read_text()
    path.write_text(original.replace("8003", "8004"))
    with pytest.raises(ValueError, match="Frontend/backend"):
        local_env.load("qa", credentials=False)
    path.write_text(original)
    backend = profiles / "backend/.env.qa.local"
    backend.write_text(
        backend.read_text().replace("POSTGRES_DB=tapserve_qa", "POSTGRES_DB=tapserve_dev")
    )
    with pytest.raises(ValueError, match="database/role"):
        local_env.load("qa", credentials=False)


def test_equal_database_passwords_are_rejected_without_disclosing_them(profiles):
    for path in profiles.glob("backend/.env.*.local"):
        path.write_text(
            path.read_text().replace(
                "POSTGRES_PASSWORD=\n", "POSTGRES_PASSWORD=synthetic-test-password\n"
            )
        )
    with pytest.raises(ValueError, match="independent POSTGRES_PASSWORD") as caught:
        local_env.load("dev")
    assert "synthetic-test-password" not in str(caught.value)


def test_persistent_or_foreign_test_manifest_is_rejected(profiles):
    with pytest.raises(ValueError, match="disposable"):
        local_env.test_environment(profiles / "backend/.env.qa.local")
    identifier = "a" * 32
    directory = profiles / ".local/environments/tests" / identifier
    directory.mkdir(parents=True)
    path = directory / ".env"
    path.write_text(
        "POSTGRES_DB=tapserve_qa\nPOSTGRES_USER=tapserve_qa_user\nPOSTGRES_HOST=127.0.0.1\n"
    )
    with pytest.raises(ValueError, match="Unsafe"):
        local_env.test_environment(path)


def test_seed_refuses_nonlocal_settings_before_database_or_credential_access():
    with (
        patch("apps.orders.demo.credentials") as secrets,
        patch("apps.orders.demo.connection.cursor") as cursor,
    ):
        with pytest.raises(CommandError, match="explicit dev/qa"):
            call_command("seed_environment", env="qa")
    secrets.assert_not_called()
    cursor.assert_not_called()


def test_django_profiles_isolate_all_cookies_media_and_database_settings(profiles):
    code = """import json, django
django.setup()
from django.conf import settings as s
print(json.dumps({'cookies': [s.SESSION_COOKIE_NAME,s.CSRF_COOKIE_NAME,s.DEVICE_COOKIE_NAME,s.BROWSER_COOKIE_NAME], 'media': str(s.MEDIA_ROOT), 'db': s.DATABASES['default']['NAME'], 'debug': s.DEBUG}))
"""
    snapshots = []
    for profile in ("dev", "qa"):
        env = local_env.load(profile, credentials=False)
        env.update(TAPSERVE_LOAD_ENV="0", POSTGRES_PASSWORD="synthetic-config-only")
        result = subprocess.run(  # noqa: S603 - fixed interpreter/source; secrets only in environment.
            [sys.executable, "-B", "-c", code],
            cwd=ROOT / "backend",
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        snapshots.append(json.loads(result.stdout))
    dev, qa = snapshots
    assert not set(dev["cookies"]).intersection(qa["cookies"])
    assert dev["media"] != qa["media"]
    assert dev["db"] == "tapserve_dev" and qa["db"] == "tapserve_qa"
    assert dev["debug"] is True and qa["debug"] is False


def test_live_smoke_rejects_nonlocal_destinations_before_any_network_call():
    from unittest.mock import MagicMock

    smoke_spec = importlib.util.spec_from_file_location(
        "local_smoke", ROOT / "scripts/local_smoke.py"
    )
    smoke = importlib.util.module_from_spec(smoke_spec)
    with patch.dict(sys.modules, {"local_env": local_env}):
        smoke_spec.loader.exec_module(smoke)
    opener = MagicMock()
    with pytest.raises(ValueError, match="loopback"):
        smoke.request(opener, "https://external.invalid", "/api/v1/health/")
    opener.open.assert_not_called()
