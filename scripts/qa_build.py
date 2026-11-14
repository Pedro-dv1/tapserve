"""Build through the official command only after Node IPC passes; preserve old dist.

Checks local references, maps, known secret patterns/values, hashes and HTTP SPA fallback.
Does not certify a browser, API/WS proxy, CSP or TLS; those require the complete QA lab.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import threading
import uuid
from functools import partial
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit
from urllib.request import urlopen

from check_secrets import findings

ROOT = Path(__file__).resolve().parents[1]


def reference_file(root, source, reference):
    parsed = urlsplit(reference)
    if parsed.scheme or parsed.netloc or reference.startswith("#"):
        return None
    target = (root / unquote(parsed.path.lstrip("/")) if reference.startswith("/")
        else source.parent / unquote(parsed.path)).resolve()
    if not target.is_relative_to(root.resolve()) or not target.is_file():
        raise ValueError("Missing or outside-bundle asset referenced by " + source.name)
    return target


class EntryAssets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "script" and values.get("src"):
            self.references.append(values["src"])
        if tag == "link" and values.get("href"):
            self.references.append(values["href"])


def inspect_bundle(root):
    entry = root / "index.html"
    parser = EntryAssets()
    parser.feed(entry.read_text(encoding="utf-8"))
    if not parser.references or not any(value.endswith(".js") for value in parser.references):
        raise ValueError("The generated entry must reference JavaScript")
    for reference in parser.references:
        reference_file(root, entry, reference)
    manifest = []
    for file in sorted(root.rglob("*")):
        if file.is_symlink() or not file.resolve().is_relative_to(root.resolve()):
            raise ValueError("Unexpected bundle symlink")
        if not file.is_file():
            continue
        data = file.read_bytes()
        if file.suffix == ".map":
            raise ValueError("Unexpected source map")
        if file.suffix in (".js", ".css", ".html", ".json"):
            content = data.decode("utf-8")
            if "sourceMappingURL=" in content:
                raise ValueError("Unexpected source map reference")
            for key, value in os.environ.items():
                if len(value) >= 16 and re.search(r"SECRET|PASSWORD|TOKEN_KEYS|PRIVATE_KEY", key) and value in content:
                    raise ValueError("Environment secret found in bundle (value withheld): " + key)
            references = (re.findall(r'''(?:\bfrom\s*|\bimport\s*\(\s*)["']([^"']+)["']''', content)
                if file.suffix == ".js" else re.findall(r'''url\(\s*["']?([^\s)'";]+)''', content)
                if file.suffix == ".css" else [])
            for reference in references:
                reference_file(root, file, reference)
        manifest.append(dict(path=file.relative_to(root).as_posix(), size=len(data),
            sha256=hashlib.sha256(data).hexdigest()))
    if list(findings(root)):
        raise ValueError("Known secret pattern found; inspect privately, do not publish bundle")
    return manifest


class SpaHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Synthetic smoke only; no request URLs/cookies go to logs.

    def do_GET(self):
        path = urlsplit(self.path).path
        if path.startswith(("/api/", "/ws/")):
            self.send_error(404)
            return
        if not Path(self.translate_path(path)).is_file():
            self.path = "/index.html"
        super().do_GET()


def smoke(root, manifest):
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SpaHandler, directory=str(root)))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    origin = "http://127.0.0.1:" + str(server.server_port)
    try:
        for path in ("/", "/staff/login", "/staff/operation"):
            with urlopen(origin + path, timeout=5) as response:  # noqa: S310 - generated literal loopback origin.
                if response.status != 200 or response.headers.get_content_type() != "text/html" or response.read() != (root / "index.html").read_bytes():
                    raise ValueError("SPA fallback smoke failed")
        for item in manifest:
            if item["path"].endswith((".js", ".css")):
                with urlopen(origin + "/" + item["path"], timeout=5) as response:  # noqa: S310
                    types = {".js": ("text/javascript", "application/javascript"), ".css": ("text/css",)}
                    if response.headers.get_content_type() not in types[Path(item["path"]).suffix]:
                        raise ValueError("Unexpected JavaScript/CSS MIME type")
                    if hashlib.sha256(response.read()).hexdigest() != item["sha256"]:
                        raise ValueError("Served asset differs from generated bundle")
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
    if worker.is_alive():
        raise RuntimeError("Owned smoke server did not stop")


def self_check():
    root = ROOT / ".local" / ("fase2b-bundle-selfcheck-" + uuid.uuid4().hex)
    root.mkdir()
    (root / "index.html").write_text('<script type="module" src="/entry.js"></script>')
    (root / "entry.js").write_text("console.log('synthetic');")
    manifest = inspect_bundle(root)
    smoke(root, manifest)
    for bad in ("missing.js", "../../outside.js"):
        try:
            reference_file(root, root / "entry.js", bad)
        except ValueError:
            continue
        raise AssertionError("Unsafe/missing reference accepted")
    (root / "unexpected.map").write_text("synthetic")
    try:
        inspect_bundle(root)
    except ValueError:
        pass
    else:
        raise AssertionError("Source map accepted")
    print("PASS: synthetic references, map rejection, HTTP fallback/assets and server shutdown; no Vite build")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        self_check()
        return
    run = ROOT / ".local" / ("fase2b-build-" + uuid.uuid4().hex)
    run.mkdir()
    node = shutil.which("node")
    powershell = shutil.which("powershell.exe")
    if node is None or powershell is None or shutil.which("npm.cmd") is None:
        parser.error("Installed Node/npm/PowerShell are required; this command installs nothing")
    result = subprocess.run(  # noqa: S603 - fixed Node probe; output path generated in workspace.
        [node, str(ROOT / "scripts/qa_node_probe.mjs"), "--output", str(run / "node.json")], check=False)
    if result.returncode:
        raise SystemExit("BLOCKED: Node IPC preflight failed; official build and dist were not touched: " + str(run))
    if any(file.name != ".env.example" for file in (ROOT / "frontend").glob(".env*")):
        parser.error("Review frontend .env files privately before creating a public bundle")
    if any(key.startswith("VITE_") and re.search(r"SECRET|PASSWORD|TOKEN|KEY", key) for key in os.environ):
        parser.error("Unexpected sensitive public variable; values withheld")
    dist = ROOT / "frontend/dist"
    backup = run / "previous-dist"
    if dist.is_symlink() or dist.resolve() != ROOT / "frontend/dist" or not backup.resolve().is_relative_to(ROOT / ".local"):
        raise ValueError("Refuse an unexpected generated output path")
    if dist.exists():
        shutil.move(str(dist), str(backup))
    with (run / "build.txt").open("x", encoding="utf-8") as log:
        result = subprocess.run(  # noqa: S603 - literal official command; no interpolated shell data.
            [powershell, "-NoProfile", "-Command", "& npm.cmd --prefix frontend run build; exit $LASTEXITCODE"],
            cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=False)
    (run / "exit-code.json").write_text(json.dumps(dict(build_exit_code=result.returncode)))
    if result.returncode:
        raise SystemExit("Build failed; previous dist retained separately: " + str(run))
    manifest = inspect_bundle(dist)
    smoke(dist, manifest)
    (run / "assets.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("PASS official build, fresh assets/maps/limited secrets/hash/HTTP smoke:", run)
    print("Browser execution, API/WS proxy, CSP and TLS still require the complete laboratory.")


if __name__ == "__main__":
    main()
