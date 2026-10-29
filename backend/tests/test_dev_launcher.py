import importlib.util
import sys
from pathlib import Path

import pytest


@pytest.fixture
def launcher():
    path = Path(__file__).resolve().parents[2] / "scripts" / "dev.py"
    spec = importlib.util.spec_from_file_location("tapserve_dev", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "address",
    [
        "0.0.0.0",  # noqa: S104
        "127.0.0.1",
        "8.8.8.8",
        "::1",
        "invalid",
        "192.168.100.7,8.8.8.8",
        "192.168.103.104,",
    ],
)  # noqa: S104
def test_lan_launcher_rejects_non_private_or_unspecified_advertised_addresses(
    monkeypatch, address, launcher
):
    monkeypatch.setattr(sys, "argv", ["dev.py", "--lan-ip", address])
    with pytest.raises(SystemExit) as error:
        launcher.main()
    assert error.value.code == 2


def test_lan_launcher_preserves_both_origins_and_uses_first_for_qr(monkeypatch, launcher):
    from io import StringIO
    from unittest.mock import MagicMock

    monkeypatch.setattr(sys, "argv", ["dev.py", "--lan-ip", "192.168.103.104,192.168.100.7"])
    monkeypatch.setattr(launcher.shutil, "which", lambda name: "node")
    monkeypatch.setattr(Path, "exists", lambda path: True)
    monkeypatch.setattr(Path, "mkdir", lambda *args, **kwargs: None)
    monkeypatch.setattr(Path, "open", lambda *args, **kwargs: StringIO())
    probe = MagicMock()
    probe.__enter__.return_value = probe
    probe.connect_ex.return_value = 1
    monkeypatch.setattr(launcher.socket, "socket", lambda: probe)
    captured = {}

    def inspect_launch(command, **options):
        captured.update(options["env"])
        assert command[command.index("-b") + 1] == "0.0.0.0"  # noqa: S104
        raise RuntimeError("launch inspected")

    monkeypatch.setattr(launcher.subprocess, "Popen", inspect_launch)
    with pytest.raises(RuntimeError, match="launch inspected"):
        launcher.main()
    assert captured["PUBLIC_APP_ORIGIN"] == "http://192.168.103.104:5173"
    assert {"192.168.100.7", "192.168.103.104"} <= set(captured["DJANGO_ALLOWED_HOSTS"].split(","))
    assert {"http://192.168.100.7:5173", "http://192.168.103.104:5173"} <= set(
        captured["CSRF_TRUSTED_ORIGINS"].split(",")
    )
    assert captured["VITE_BACKEND_URL"] == "http://127.0.0.1:8000"
