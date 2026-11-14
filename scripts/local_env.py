"""Operate the two local profiles; never fall back to legacy credentials or databases."""

import argparse
import getpass
import json
import os
import re
import secrets
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / "backend/.venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
PROFILES = {"dev": ("development", 8004, 5177), "qa": ("qa", 8003, 5176)}


def read_env(path):
    from environ import Env

    class LocalReader(Env):
        ENVIRON = {}

    LocalReader.read_env(path, overwrite=True, parse_comments=False)
    return LocalReader.ENVIRON


def clean_environment():
    return {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("POSTGRES_", "PG", "DJANGO_", "TAPSERVE_", "VITE_"))
    }


def load(profile, *, credentials=True):
    if profile not in PROFILES:
        raise ValueError("Select dev or qa")
    mode, api, frontend = PROFILES[profile]
    path = ROOT / "backend" / f".env.{mode}.local"
    if not path.is_file():
        raise ValueError("Run scripts/local_env.py init first")
    config = read_env(path)
    expected = {
        "TAPSERVE_ENV": profile,
        "DJANGO_SETTINGS_MODULE": f"config.settings.{profile}",
        "POSTGRES_DB": f"tapserve_{profile}",
        "POSTGRES_USER": f"tapserve_{profile}_user",
        "BACKEND_PORT": str(api),
        "FRONTEND_PORT": str(frontend),
        "PUBLIC_APP_ORIGIN": f"http://127.0.0.1:{frontend}",
    }
    if any(config.get(key) != value for key, value in expected.items()):
        raise ValueError("Local environment/database/role/ports mismatch")
    if config.get("POSTGRES_HOST") not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Only the identified local PostgreSQL instance is permitted")
    if (
        not config.get("POSTGRES_PORT", "").isdigit()
        or not 1024 <= int(config["POSTGRES_PORT"]) <= 65535
    ):
        raise ValueError("Invalid PostgreSQL port")
    if credentials and not config.get("POSTGRES_PASSWORD"):
        raise ValueError(f"Fill POSTGRES_PASSWORD in backend/.env.{mode}.local; value withheld")
    public = read_env(ROOT / "frontend" / f".env.{mode}.local")
    if public != {
        "VITE_TAPSERVE_ENV": profile,
        "VITE_BACKEND_URL": f"http://127.0.0.1:{api}",
        "VITE_FRONTEND_PORT": str(frontend),
    }:
        raise ValueError("Frontend/backend configuration mismatch; no fallback permitted")
    if len(config.get("DJANGO_SECRET_KEY", "")) < 50 or not config.get("TAPSERVE_TOKEN_KEYS"):
        raise ValueError("Missing independent Django/token secrets")
    from cryptography.fernet import Fernet

    Fernet(config["TAPSERVE_TOKEN_KEYS"].encode())
    other_mode = PROFILES["qa" if profile == "dev" else "dev"][0]
    other_path = ROOT / "backend" / f".env.{other_mode}.local"
    if other_path.is_file():
        other = read_env(other_path)
        for key in ("POSTGRES_PASSWORD", "DJANGO_SECRET_KEY", "TAPSERVE_TOKEN_KEYS"):
            if config.get(key) and config[key] == other.get(key):
                raise ValueError(f"DEV and QA must have independent {key}; values withheld")
    directory = ROOT / ".local/environments" / profile
    for name in ("media", "tmp", "logs"):
        (directory / name).mkdir(parents=True, exist_ok=True)
    return {**clean_environment(), **config, "TAPSERVE_LOAD_ENV": "1", "PYTHONIOENCODING": "utf-8"}


def initialize():
    from cryptography.fernet import Fernet

    for profile, (mode, api, frontend) in PROFILES.items():
        backend = ROOT / "backend" / f".env.{mode}.local"
        if not backend.exists():
            values = {
                "TAPSERVE_ENV": profile,
                "DJANGO_SETTINGS_MODULE": f"config.settings.{profile}",
                "DJANGO_DEBUG": "True" if profile == "dev" else "False",
                "DJANGO_SECRET_KEY": secrets.token_urlsafe(64),
                "TAPSERVE_TOKEN_KEYS": Fernet.generate_key().decode(),
                "POSTGRES_DB": f"tapserve_{profile}",
                "POSTGRES_USER": f"tapserve_{profile}_user",
                "POSTGRES_PASSWORD": "",
                "POSTGRES_HOST": "127.0.0.1",
                "POSTGRES_PORT": "5432",
                "BACKEND_PORT": str(api),
                "FRONTEND_PORT": str(frontend),
                "DJANGO_ALLOWED_HOSTS": "localhost,127.0.0.1,[::1]",
                "CSRF_TRUSTED_ORIGINS": f"http://127.0.0.1:{frontend},http://localhost:{frontend}",
                "CORS_ALLOWED_ORIGINS": "",
                "PUBLIC_APP_ORIGIN": f"http://127.0.0.1:{frontend}",
                "STAFF_PIN_NETWORKS": "127.0.0.1/32,::1/128",
                "TRUSTED_PROXY_NETWORKS": "",
            }
            with backend.open("x", encoding="utf-8") as output:
                output.write(
                    "# Local only. Fill the existing role password manually; never commit this file.\n"
                )
                output.write("\n".join(f"{key}={value}" for key, value in values.items()) + "\n")
        path = ROOT / "frontend" / f".env.{mode}.local"
        if not path.exists():
            with path.open("x", encoding="utf-8") as output:
                output.write(
                    f"VITE_TAPSERVE_ENV={profile}\nVITE_BACKEND_URL=http://127.0.0.1:{api}\nVITE_FRONTEND_PORT={frontend}\n"
                )
        load(profile, credentials=False)
        print(profile.upper(), "local env files ready; existing files and credentials preserved")


def parameters(config, *, database=None, user=None, password=None):
    return dict(
        host=config["POSTGRES_HOST"],
        port=config["POSTGRES_PORT"],
        dbname=database or config["POSTGRES_DB"],
        user=user or config["POSTGRES_USER"],
        password=password if password is not None else config["POSTGRES_PASSWORD"],
        connect_timeout=5,
    )


def check_database(config, *, harden=False):
    import psycopg
    from psycopg import sql

    profile = config["TAPSERVE_ENV"]
    own, other = config["POSTGRES_DB"], f"tapserve_{'qa' if profile == 'dev' else 'dev'}"
    with psycopg.connect(**parameters(config)) as connection:
        identity = connection.execute(
            "SELECT current_database(),current_user,inet_server_port()"
        ).fetchone()
        if identity != (own, config["POSTGRES_USER"], int(config["POSTGRES_PORT"])):
            raise ValueError("Connected PostgreSQL identity mismatch")
        role = connection.execute(
            "SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls,rolcanlogin FROM pg_roles WHERE rolname=current_user"
        ).fetchone()
        memberships = connection.execute(
            "SELECT roleid FROM pg_auth_members WHERE member=current_user::regrole"
        ).fetchall()
        if role != (False, False, False, False, False, True) or memberships:
            raise ValueError(
                "Application role is privileged or inherits memberships; administrator must review"
            )
        owner = connection.execute(
            "SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=current_database()"
        ).fetchone()[0]
        if owner != config["POSTGRES_USER"]:
            raise ValueError("Unexpected database owner; do not migrate")
        foreign = connection.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tableowner!=current_user"
        ).fetchall()
        if foreign:
            raise ValueError("Tables owned by another role; administrator must review")
        if harden:
            # PostgreSQL 17 ddl-priv: PUBLIC gets CONNECT/TEMP and function EXECUTE by default.
            connection.execute(
                sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC, {}").format(
                    sql.Identifier(own), sql.Identifier(other + "_user")
                )
            )
            for objects in (
                "SCHEMA public",
                "ALL TABLES IN SCHEMA public",
                "ALL SEQUENCES IN SCHEMA public",
                "ALL FUNCTIONS IN SCHEMA public",
            ):
                connection.execute(
                    sql.SQL("REVOKE ALL ON " + objects + " FROM PUBLIC, {}").format(
                        sql.Identifier(other + "_user")
                    )
                )
            connection.execute("ALTER DEFAULT PRIVILEGES REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC")
            connection.execute(
                "ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM PUBLIC"
            )
            connection.execute(
                "ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM PUBLIC"
            )
        allowed = connection.execute(
            "SELECT has_database_privilege(%s,%s,'CONNECT'),has_database_privilege(%s,%s,'CONNECT')",
            (
                config["POSTGRES_USER"],
                own,
                "tapserve_qa_user" if profile == "dev" else "tapserve_dev_user",
                own,
            ),
        ).fetchone()
        if allowed != (True, False):
            raise ValueError(
                "Cross-environment CONNECT remains granted; run harden in both profiles"
            )
        print(profile.upper(), "PostgreSQL identity, owner and least privilege OK")
    if harden:
        print(
            profile.upper(),
            "own database permissions hardened; check both profiles after hardening the pair",
        )
        return
    with psycopg.connect(**parameters(config)) as connection:
        if connection.execute(
            "SELECT has_database_privilege(current_user,%s,'CONNECT')", (other,)
        ).fetchone()[0]:
            raise ValueError(
                "Own role can still CONNECT to the other environment; harden the pair first"
            )
    try:
        with psycopg.connect(**parameters(config, database=other)):
            raise ValueError("Cross-environment connection unexpectedly accepted")
    except psycopg.OperationalError:
        # libpq connect errors lack SQLSTATE: reconfirm the working credentials and denied ACL.
        with psycopg.connect(**parameters(config)) as connection:
            if connection.execute(
                "SELECT has_database_privilege(current_user,%s,'CONNECT')", (other,)
            ).fetchone()[0]:
                raise ValueError("Cross-environment ACL changed during verification") from None
        print(
            profile.upper(),
            "cross CONNECT ACL denied; cross connection failed; own connection reconfirmed",
        )


def run_backend(config, *arguments):
    # Fixed Python executable and argument arrays; env secrets never enter argv.
    return subprocess.call(
        [str(PYTHON), "-B", "manage.py", *arguments], cwd=ROOT / "backend", env=config
    )  # noqa: S603


def create_test_database(config):
    import psycopg
    from cryptography.fernet import Fernet
    from psycopg import sql

    admin = input("Local PostgreSQL administrator role: ").strip()
    if not admin:
        raise ValueError("An explicit administrator role is required")
    password = getpass.getpass("Administrator password (not saved): ")
    identifier = uuid.uuid4().hex
    database, role = "tapserve_test_" + identifier, "tapserve_test_user_" + identifier
    role_password = secrets.token_urlsafe(36)
    values = {
        "POSTGRES_HOST": config["POSTGRES_HOST"],
        "POSTGRES_PORT": config["POSTGRES_PORT"],
        "POSTGRES_DB": database,
        "POSTGRES_USER": role,
        "POSTGRES_PASSWORD": role_password,
        "DJANGO_SECRET_KEY": secrets.token_urlsafe(64),
        "TAPSERVE_TOKEN_KEYS": Fernet.generate_key().decode(),
        "DJANGO_SETTINGS_MODULE": "config.settings.test",
        "TAPSERVE_LOAD_ENV": "0",
    }
    directory = ROOT / ".local/environments/tests" / identifier
    directory.mkdir(parents=True)
    with (directory / ".env").open("x", encoding="utf-8") as output:
        output.write("\n".join(f"{key}={value}" for key, value in values.items()) + "\n")
    print(
        "Exclusive disposable manifest saved before provisioning:", directory / ".env", flush=True
    )
    with psycopg.connect(
        **parameters(config, database="postgres", user=admin, password=password), autocommit=True
    ) as connection:
        verifier = connection.pgconn.encrypt_password(
            role_password.encode(), role.encode(), b"scram-sha-256"
        ).decode()
        connection.execute(
            sql.SQL(
                "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS PASSWORD {}"
            ).format(sql.Identifier(role), sql.Literal(verifier))
        )
        connection.execute(
            sql.SQL("CREATE DATABASE {} OWNER {} TEMPLATE template0").format(
                sql.Identifier(database), sql.Identifier(role)
            )
        )
        connection.execute(
            sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(sql.Identifier(database))
        )
    print("Disposable test database provisioned. Manifest:", directory / ".env")


def test_environment(path):
    path = path.resolve()
    identifier = path.parent.name
    if (
        not re.fullmatch(r"[a-f0-9]{32}", identifier)
        or path != ROOT / ".local/environments/tests" / identifier / ".env"
    ):
        raise ValueError("Tests require an explicitly provisioned disposable database manifest")
    values = read_env(path)
    expected = {
        "POSTGRES_DB": "tapserve_test_" + identifier,
        "POSTGRES_USER": "tapserve_test_user_" + identifier,
        "TAPSERVE_LOAD_ENV": "0",
        "DJANGO_SETTINGS_MODULE": "config.settings.test",
    }
    if any(values.get(key) != value for key, value in expected.items()) or values.get(
        "POSTGRES_HOST"
    ) not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Unsafe test database/role/host/settings")
    return {**clean_environment(), **values, "PYTHONIOENCODING": "utf-8"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "init",
            "check",
            "harden",
            "migrate",
            "seed",
            "dry-run",
            "start",
            "credentials",
            "create-test-db",
            "test",
            "verify",
            "smoke",
        ),
    )
    parser.add_argument("--env", choices=PROFILES)
    parser.add_argument("--lab", type=Path)
    args = parser.parse_args()
    if args.action == "init":
        initialize()
        return
    if args.action == "smoke":
        from local_smoke import smoke

        smoke()
        return
    if args.action == "test":
        if args.lab is None:
            parser.error("--lab must identify the disposable database manifest")
        env = test_environment(args.lab)
        temporary = args.lab.resolve().parent / "runs" / uuid.uuid4().hex
        temporary.parent.mkdir(exist_ok=True)
        raise SystemExit(
            subprocess.call(
                [
                    str(PYTHON),
                    "-B",
                    "-m",
                    "pytest",
                    "-p",
                    "no:cacheprovider",
                    "--tb=short",
                    "-q",
                    "--basetemp",
                    str(temporary),
                ],
                cwd=ROOT / "backend",
                env=env,
            )
        )  # noqa: S603
    if not args.env:
        parser.error("--env dev or --env qa is required")
    config = load(args.env, credentials=args.action != "create-test-db")
    if args.action == "create-test-db":
        create_test_database(config)
    elif args.action == "credentials":
        if not sys.stdout.isatty():
            raise ValueError(
                "Credentials can only be opened deliberately in an operator terminal, without redirection"
            )
        from cryptography.fernet import Fernet

        path = ROOT / ".local/environments" / args.env / "demo-credentials.enc"
        payload = Fernet(config["TAPSERVE_TOKEN_KEYS"].encode()).decrypt(path.read_bytes())
        getpass.getpass(
            "Secrets will appear only in this terminal. Enter to continue; do not record/share: "
        )
        print(json.dumps(json.loads(payload), ensure_ascii=False, indent=2))
    elif args.action == "start":
        raise SystemExit(
            subprocess.call(
                [str(PYTHON), str(ROOT / "scripts/dev.py"), "--env", args.env], env=config
            )
        )  # noqa: S603
    else:
        check_database(config, harden=args.action == "harden")
        if args.action == "migrate":
            raise SystemExit(run_backend(config, "migrate", "--noinput"))
        if args.action in {"seed", "dry-run"}:
            raise SystemExit(
                run_backend(
                    config,
                    "seed_environment",
                    "--env",
                    args.env,
                    *(["--dry-run"] if args.action == "dry-run" else []),
                )
            )
        if args.action == "check":
            for command in (
                ("check",),
                ("migrate", "--check"),
                ("makemigrations", "--check", "--dry-run"),
            ):
                code = run_backend(config, *command)
                if code:
                    raise SystemExit(code)
        if args.action == "verify":
            raise SystemExit(run_backend(config, "verify_environment", "--env", args.env))


if __name__ == "__main__":
    if Path(sys.prefix).resolve() != PYTHON.parents[1].resolve():
        raise SystemExit(
            subprocess.call([str(PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])
        )  # noqa: S603
    try:
        main()
    except Exception as error:
        # libpq/SQL diagnostics may contain connection strings; never echo them.
        if isinstance(error, ValueError):
            raise SystemExit(str(error)) from None
        raise SystemExit(
            f"Local operation failed ({type(error).__name__}); secret details withheld"
        ) from None
