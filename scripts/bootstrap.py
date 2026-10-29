"""Install locked dependencies and generate a secret only for a new local env file."""

import base64
import os
import secrets
import shutil
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def configure_local_tokens() -> None:
    destination = ROOT / "backend/.env"
    if destination.exists() and not any(
        line.strip().startswith("TAPSERVE_TOKEN_KEYS=")
        for line in destination.read_text(encoding="utf-8-sig").splitlines()
    ):
        with destination.open("a", encoding="utf-8") as local_env:
            local_env.write(
                "\nTAPSERVE_TOKEN_KEYS="
                + base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
                + "\n"
            )


def main() -> None:
    if sys.version_info[:2] != (3, 12):
        raise SystemExit("Use Python 3.12 (local reference 3.12.10).")
    environment = ROOT / "backend/.venv"
    if not environment.exists():
        venv.create(environment, with_pip=True)
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if npm is None:
        raise SystemExit("Node/npm missing. Node 22.12+ or compatible 24 is required.")
    subprocess.run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "-r",
            str(ROOT / "backend/requirements.lock"),
        ],
        check=True,
    )
    subprocess.run([npm, "ci"], cwd=ROOT / "frontend", check=True)
    destination = ROOT / "backend/.env"
    if not destination.exists():
        content = (ROOT / ".env.example").read_text(encoding="utf-8")
        content = content.replace(
            "<generate-random-secret-with-bootstrap>", secrets.token_urlsafe(64)
        )
        destination.write_text(content, encoding="utf-8")
        if os.name != "nt":
            destination.chmod(0o600)
        print("Configure PostgreSQL credentials in backend/.env; generated secret is not printed.")
    print("Existing local configuration preserved. Run migrations, then python scripts/dev.py.")
    configure_local_tokens()


if __name__ == "__main__":
    main()
