"""Launch both local surfaces after checking ports; Ctrl+C stops only our children."""

import argparse
import os
import shutil
import socket
import subprocess
import time
from ipaddress import IPv4Address
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", choices=("dev", "qa"), help="Use the isolated local profile")
    parser.add_argument("--api-port", type=int, default=8000)
    parser.add_argument("--frontend-port", type=int, default=5173)
    parser.add_argument(
        "--lan-ip",
        default=os.environ.get("TAPSERVE_LAN_IP"),
        help="Comma-separated private IPv4 addresses; first is used for QR links. Binds both servers to 0.0.0.0.",
    )
    args = parser.parse_args()
    profile_environment = None
    if args.env:
        from local_env import PROFILES, check_database, load

        if args.lan_ip or args.api_port != 8000 or args.frontend_port != 5173:
            parser.error("Named profiles use fixed loopback ports; edit the reviewed configuration instead")
        profile_environment = load(args.env)
        check_database(profile_environment)
        _, args.api_port, args.frontend_port = PROFILES[args.env]
    if (
        not all(1024 <= port <= 65535 for port in (args.api_port, args.frontend_port))
        or args.api_port == args.frontend_port
    ):
        parser.error("Use two distinct ports from 1024 to 65535.")
    lan_ips = (
        list(dict.fromkeys(value.strip() for value in args.lan_ip.split(",")))
        if args.lan_ip
        else []
    )
    for lan_ip in lan_ips:
        try:
            address = IPv4Address(lan_ip)
            if (
                not address.is_private
                or address.is_loopback
                or address.is_unspecified
                or address.is_multicast
                or address.is_reserved
            ):
                raise ValueError("Use the computer's private LAN address.")
        except ValueError as error:
            parser.error(str(error))
    origin = f"http://{lan_ips[0] if lan_ips else '127.0.0.1'}:{args.frontend_port}"
    hosts = ["localhost", "127.0.0.1", "[::1]", *lan_ips]
    origins = [
        f"http://127.0.0.1:{args.frontend_port}",
        f"http://localhost:{args.frontend_port}",
        *(f"http://{address}:{args.frontend_port}" for address in lan_ips),
    ]
    # All-interface binding is an explicit LAN opt-in for the DEV profile only.
    bind = "0.0.0.0" if args.lan_ip else "127.0.0.1"  # noqa: S104
    environment = {
        **(profile_environment or os.environ),
        "DJANGO_SETTINGS_MODULE": f"config.settings.{args.env or 'dev'}",
        "DJANGO_ALLOWED_HOSTS": ",".join(hosts),
        "PUBLIC_APP_ORIGIN": origin,
        "CSRF_TRUSTED_ORIGINS": ",".join(dict.fromkeys(origins)),
        "VITE_BACKEND_URL": f"http://127.0.0.1:{args.api_port}",
        "VITE_TAPSERVE_ENV": args.env or "",
        "VITE_FRONTEND_PORT": str(args.frontend_port),
    }
    python = (
        ROOT / "backend" / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    )
    node = shutil.which("node")
    if not python.exists() or node is None or not (ROOT / "frontend/node_modules").exists():
        raise SystemExit("Run the README installation steps first.")
    for port in (args.api_port, args.frontend_port):
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                raise SystemExit(f"Port {port} is occupied; existing processes were not changed.")
    processes: list[subprocess.Popen] = []
    log_directory = ROOT / ".local"
    if args.env:
        log_directory = log_directory / "environments" / args.env / "logs"
    log_directory.mkdir(exist_ok=True)
    log_files = []
    options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    try:
        for name, command, directory in (
            (
                "api",
                [
                    str(python),
                    "-m",
                    "daphne",
                    "-b",
                    bind,
                    "-p",
                    str(args.api_port),
                    "-v",
                    "0",
                    "--websocket-max-message-size",
                    "256",
                    "--websocket-max-frame-size",
                    "256",
                    "config.asgi:application",
                ],
                ROOT / "backend",
            ),
            (
                "frontend",
                [
                    node,
                    "node_modules/vite/bin/vite.js",
                    "--configLoader",
                    "native",
                    *(["--mode", "development" if args.env == "dev" else "qa"] if args.env else []),
                    "--host",
                    bind,
                    "--port",
                    str(args.frontend_port),
                    "--strictPort",
                ],
                ROOT / "frontend",
            ),
        ):
            log = (log_directory / f"{name}-{args.env or 'dev'}.log").open("a", encoding="utf-8")
            log_files.append(log)
            processes.append(
                subprocess.Popen(
                    command,
                    cwd=directory,
                    env=(environment if name == "api" else {
                        key: value for key, value in environment.items()
                        if not key.startswith(("POSTGRES_", "PG", "DJANGO_", "TAPSERVE_"))
                    }),
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    **options,
                )
            )
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline and all(process.poll() is None for process in processes):
            try:
                # Fixed loopback URL; no user-supplied URL or credentials.
                with urlopen(
                    f"http://127.0.0.1:{args.frontend_port}/api/v1/health/", timeout=2
                ) as response:  # noqa: S310
                    if (
                        response.status == 200
                        and response.read() == b'{"status":"ok","database":"ok"}'
                    ):
                        with urlopen(
                            f"http://127.0.0.1:{args.frontend_port}/src/main.tsx", timeout=3
                        ) as module:  # noqa: S310 - fixed loopback URL.
                            if module.status != 200:
                                continue
                        break
            except (URLError, TimeoutError):
                pass
            time.sleep(0.5)
        else:
            raise SystemExit(f"{args.env or 'DEV'} health failed. Inspect logs in {log_directory}.")
        print(
            f"{(args.env or 'dev').upper()}: {origin} | API http://127.0.0.1:{args.api_port}/api/v1/health/ | PostgreSQL and proxy health OK; no Redis/Docker",
            flush=True,
        )
        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
        raise SystemExit(
            f"A local server exited. Inspect logs in {log_directory}; no fallback was enabled."
        )
    except KeyboardInterrupt:
        print(f"Stopping TapServe {(args.env or 'dev').upper()} processes.")
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        for log in log_files:
            log.close()


if __name__ == "__main__":
    main()
