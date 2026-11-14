"""Operator-owned disposable PG17 lab. Never starts postgres directly or changes ACLs.

prepare proves start/query/stop/restart/NOTIFY and leaves the new lab stopped.
verify runs the original critical tests three times, then full backend gates, and stops.
"""
import argparse
import base64
import json
import os
import re
import secrets
import socket
import subprocess
import sys
import uuid
from pathlib import Path

import psycopg
from psycopg import sql
from qa_windows_probe import probe

ROOT = Path(__file__).resolve().parents[1]
PG = Path("C:/Program Files/PostgreSQL/17/bin")
MATRIX = ROOT / "docs/auditoria-v2/evidencias/fase2/notify_matrix.py"


def validate_layout(path, config):
    path = Path(path).resolve()
    identifier = config["id"]
    if not re.fullmatch(r"[a-f0-9]{32}", identifier):
        raise ValueError("Invalid laboratory identifier")
    directory = ROOT / ".local" / ("fase2b-pg-" + identifier)
    if path != directory / "lab.json" or directory.resolve() != directory:
        raise ValueError("Only the exclusively created Fase 2B directory is permitted")
    if config["database"] != "tapserve_lab_" + identifier or config["user"] != "qa_" + identifier:
        raise ValueError("Database and user must belong to this laboratory")
    if type(config["port"]) is not int or not 1024 <= config["port"] <= 65535 or config["port"] in (5432, 64817):
        raise ValueError("Refuse existing/invalid server ports")
    expected = dict(POSTGRES_HOST="127.0.0.1", POSTGRES_PORT=str(config["port"]),
        POSTGRES_DB=config["database"], POSTGRES_USER=config["user"], TAPSERVE_LOAD_ENV="0",
        DJANGO_SETTINGS_MODULE="config.settings.test", TAPSERVE_NOTIFY_LAB=config["database"])
    if any(config["env"].get(key) != value for key, value in expected.items()):
        raise ValueError("Application environment must use this synthetic database only")
    allowed = {*expected, "DJANGO_SECRET_KEY", "TAPSERVE_TOKEN_KEYS", "POSTGRES_PASSWORD", "PYTHONDONTWRITEBYTECODE"}
    if set(config["env"]) - allowed:
        raise ValueError("Unexpected laboratory environment option")
    return directory


def environment(config):
    env = {key: value for key, value in os.environ.items()
        if not key.startswith(("PG", "POSTGRES_", "TAPSERVE_", "DJANGO_"))}
    env.update(config["env"])
    env["PATH"] = str(PG) + os.pathsep + env["PATH"]
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def parameters(config, database="postgres"):
    return dict(host="127.0.0.1", port=config["port"], user=config["user"],
        password=config["env"]["POSTGRES_PASSWORD"], dbname=database, connect_timeout=5)


def run(command, directory, name, *, env=None, cwd=ROOT):
    with (directory / name).open("x", encoding="utf-8") as log:
        # Fixed executable/argument arrays; no shell or credentials in command lines.
        process = subprocess.Popen(  # noqa: S603 - fixed caller-owned executable/argument arrays.
            command, cwd=cwd, env=env, stdout=log,
            stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            code = process.wait()
        except BaseException:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
            raise
    print(name, "exit", code, flush=True)
    if code:
        raise RuntimeError("Command failed; inspect " + str(directory / name))


def save(path, config):
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")


def check_identity(directory, config):
    data = directory / "pgdata"
    pidfile = data / "postmaster.pid"
    if (data / "PG_VERSION").read_text().strip() != "17":
        raise ValueError("Refuse another PostgreSQL version")
    lines = pidfile.read_text().splitlines()
    if int(lines[3]) != config["port"] or Path(lines[1]).resolve() != data:
        raise ValueError("Postmaster identity does not match the laboratory")
    with psycopg.connect(**parameters(config), autocommit=True) as connection:
        row = connection.execute("SELECT current_setting('data_directory'), inet_server_port(), current_user, system_identifier FROM pg_control_system()").fetchone()
        if Path(row[0]).resolve() != data or row[1] != config["port"] or row[2] != config["user"]:
            raise ValueError("Live server identity mismatch")
        if config.get("system_identifier") not in (None, row[3]):
            raise ValueError("Cluster identity changed; do not signal it")
        config["system_identifier"] = row[3]
        config["pid"] = int(lines[0])


def start(directory, config):
    if (directory / "pgdata/postmaster.pid").exists():
        raise ValueError("Server already has a PID file; inspect status before starting")
    sequence = uuid.uuid4().hex
    config["state"] = "starting"
    save(directory / "lab.json", config)
    run([str(PG / "pg_ctl.exe"), "-D", str(directory / "pgdata"), "-l",
        str(directory / "postgres.log"), "-o", f"-h 127.0.0.1 -p {config['port']}", "-w", "start"],
        directory, "start-" + sequence + ".txt")
    check_identity(directory, config)
    config["state"] = "running"
    save(directory / "lab.json", config)


def stop(directory, config):
    check_identity(directory, config)
    run([str(PG / "pg_ctl.exe"), "-D", str(directory / "pgdata"), "-m", "fast", "-w", "stop"],
        directory, "stop-" + uuid.uuid4().hex + ".txt")
    with socket.socket() as connection:
        if (directory / "pgdata/postmaster.pid").exists() or connection.connect_ex(("127.0.0.1", config["port"])) == 0:
            raise RuntimeError("Shutdown was not independently confirmed")
    config["state"] = "stopped"
    save(directory / "lab.json", config)


def notify(directory, config):
    run([sys.executable, "-B", str(MATRIX), "--from-env"], directory,
        "notify-" + uuid.uuid4().hex + ".txt", env=environment(config))


def prepare(capability):
    identifier = uuid.uuid4().hex
    directory = ROOT / ".local" / ("fase2b-pg-" + identifier)
    directory.mkdir()
    with socket.socket() as connection:
        connection.bind(("127.0.0.1", 0))
        port = connection.getsockname()[1]
    password = secrets.token_urlsafe(36)
    config = dict(id=identifier, port=port, user="qa_" + identifier,
        database="tapserve_lab_" + identifier, state="initializing",
        owner_sid=capability["windows"]["user_sid"])
    config["env"] = dict(TAPSERVE_LOAD_ENV="0", DJANGO_SETTINGS_MODULE="config.settings.test",
        DJANGO_SECRET_KEY=secrets.token_urlsafe(64),
        TAPSERVE_TOKEN_KEYS=base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
        POSTGRES_HOST="127.0.0.1", POSTGRES_PORT=str(port), POSTGRES_USER=config["user"],
        POSTGRES_PASSWORD=password, POSTGRES_DB=config["database"],
        TAPSERVE_NOTIFY_LAB=config["database"], PYTHONDONTWRITEBYTECODE="1")
    path = directory / "lab.json"
    validate_layout(path, config)
    save(path, config)
    password_file = directory / "init-password"
    with password_file.open("x", encoding="utf-8") as output:
        output.write(password)
    try:
        run([str(PG / "initdb.exe"), "-D", str(directory / "pgdata"), "-U", config["user"],
            "--auth=scram-sha-256", "--pwfile", str(password_file), "--encoding=UTF8", "--locale=C"],
            directory, "initdb.txt")
    finally:
        password_file.unlink()
    try:
        start(directory, config)
        stop(directory, config)
        start(directory, config)
        with psycopg.connect(**parameters(config), autocommit=True) as connection:
            connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(config["database"])))
        notify(directory, config)
        config["basic_validation_passed"] = True
        save(path, config)
    finally:
        if (directory / "pgdata/postmaster.pid").exists():
            stop(directory, config)
    print("Validated, stopped laboratory:", path, flush=True)


def verify(directory, config):
    if not config.get("basic_validation_passed"):
        raise ValueError("Independent lifecycle and notification gates must pass first")
    if (directory / "pgdata/postmaster.pid").exists():
        raise ValueError("Verification requires a stopped lab; do not interrupt an existing run")
    env = environment(config)
    try:
        start(directory, config)
        notify(directory, config)
        critical = ["tests/test_distributed_realtime.py", "tests/test_realtime.py",
            "tests/test_service_requests.py::test_free_point_notifications_do_not_leak_to_other_free_point_or_rollback",
            "tests/test_realtime_lifecycle.py",
            "tests/test_settlement.py::test_closing_session_disconnects_existing_customer_websocket"]
        for index in range(1, 4):
            name = "critical-" + str(index) + "-" + uuid.uuid4().hex
            run([sys.executable, "-B", "-m", "pytest", "-p", "no:cacheprovider", "--tb=short",
                "-q", "--junitxml=" + str(directory / (name + ".xml")), *critical],
                directory, name + ".txt", env=env, cwd=ROOT / "backend")
        name = "full-" + uuid.uuid4().hex
        run([sys.executable, "-B", "-m", "pytest", "-p", "no:cacheprovider", "--tb=short",
            "-q", "--junitxml=" + str(directory / (name + ".xml"))],
            directory, name + ".txt", env=env, cwd=ROOT / "backend")
        for command in (["-m", "ruff", "check", "."], ["-m", "mypy", "apps", "common", "config"],
            ["-m", "pip", "check"], ["manage.py", "check"],
            ["manage.py", "makemigrations", "--check", "--dry-run"],
            [str(ROOT / "scripts/extract_architecture.py")]):
            run([sys.executable, "-B", *command], directory, "quality-" + uuid.uuid4().hex + ".txt",
                env=env, cwd=ROOT / "backend")
    finally:
        if (directory / "pgdata/postmaster.pid").exists():
            stop(directory, config)


def self_check():
    identifier = "a" * 32
    good = dict(id=identifier, user="qa_" + identifier, database="tapserve_lab_" + identifier, port=55432)
    good["env"] = dict(POSTGRES_HOST="127.0.0.1", POSTGRES_PORT="55432", POSTGRES_USER=good["user"],
        POSTGRES_DB=good["database"], TAPSERVE_LOAD_ENV="0", DJANGO_SETTINGS_MODULE="config.settings.test",
        TAPSERVE_NOTIFY_LAB=good["database"])
    path = ROOT / ".local" / ("fase2b-pg-" + identifier) / "lab.json"
    assert validate_layout(path, good) == path.parent  # noqa: S101 - executable guard self-check.
    for bad_path, bad in [(ROOT / "lab.json", good), (path, {**good, "port": 5432}),
        (path, {**good, "port": 64817}), (path, {**good, "database": "tapserve"}),
        (path, {**good, "id": "../other"}),
        (path, {**good, "env": {**good["env"], "POSTGRES_HOST": "production.invalid"}}),
        (path, {**good, "env": {**good["env"], "TAPSERVE_LOAD_ENV": "1"}})]:
        try:
            validate_layout(bad_path, bad)
        except ValueError:
            continue
        raise AssertionError("Unsafe laboratory configuration accepted")
    print("PASS: layout/port/database guards; no cluster created or contacted")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "start", "stop", "verify", "self-check"))
    parser.add_argument("--lab", type=Path)
    args = parser.parse_args()
    if args.action == "self-check":
        self_check()
        return
    capability = probe()
    if not capability["lab_gate_passed"]:
        raise SystemExit("BLOCKED: own named pipes/lifecycle fail in this context; no PG process started")
    if not all((PG / name).is_file() for name in ("initdb.exe", "pg_ctl.exe", "psql.exe")) or not MATRIX.is_file():
        parser.error("Installed PG17 clients and the preserved notification matrix are required")
    if any(os.environ.get(key) for key in ("PGSERVICE", "PGSERVICEFILE", "PGHOSTADDR", "PGOPTIONS")):
        parser.error("Alternative libpq routing/options must be absent in this isolated terminal")
    for name in ("initdb.exe", "pg_ctl.exe"):
        version = subprocess.run(  # noqa: S603 - fixed installed client and --version.
            [str(PG / name), "--version"], capture_output=True, text=True, check=True).stdout
        if not re.search(r"\(PostgreSQL\) 17\.", version):
            parser.error("Only installed PostgreSQL 17 clients are supported")
    if args.action == "prepare":
        prepare(capability)
    else:
        if args.lab is None:
            parser.error("--lab must name the exact new laboratory manifest")
        config = json.loads(args.lab.read_text(encoding="utf-8"))
        directory = validate_layout(args.lab, config)
        if config.get("owner_sid") != capability["windows"]["user_sid"]:
            parser.error("Control requires the Windows owner that created this laboratory")
        lock = directory / "controller.lock"
        with lock.open("x", encoding="utf-8") as handle:
            handle.write(str(os.getpid()))
        try:
            {"start": start, "stop": stop, "verify": verify}[args.action](directory, config)
        finally:
            lock.unlink()


if __name__ == "__main__":
    main()
