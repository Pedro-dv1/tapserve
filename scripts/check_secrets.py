"""Limited source-pattern check; emit locations only, never suspected secret values."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {
    ".git",
    ".venv",
    ".local",
    "node_modules",
    "dist",
    "__pycache__",
    ".ruff_cache",
}
PATTERNS = {
    "private-key": re.compile(r"-{5}BEGIN [A-Z ]*PRIVATE KEY-{5}"),
    "aws-access-key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "github-token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "point-capability-url": re.compile(r"https?://[^\s\"']+/a/[A-Za-z0-9_-]{32,}"),
    "literal-secret": re.compile(
        r"(?i)(?:DJANGO_SECRET_KEY|TAPSERVE_TOKEN_KEYS|api_secret)[\"']?\s*[:=]\s*[\"']([A-Za-z0-9_+/=-]{40,})"
    ),
}


def findings(root: Path):
    for directory, children, files in root.walk(follow_symlinks=False):
        children[:] = [
            name
            for name in children
            if name not in EXCLUDED and not name.startswith("pytest-cache-files-")
        ]
        for name in files:
            path = directory / name
            if (
                path.is_symlink()
                or name == ".env"
                or path.suffix not in {".py", ".ts", ".tsx", ".js", ".json", ".yml", ".yaml", ".md"}
            ):
                continue
            if path.stat().st_size > 2 * 1024 * 1024:
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
                for category, pattern in PATTERNS.items():
                    if pattern.search(line):
                        yield path.relative_to(root), number, category


def main() -> None:
    samples = {
        "private-key": "-" * 5 + "BEGIN PRIVATE KEY" + "-" * 5,
        "aws-access-key": "AKIA" + "A" * 16,
        "github-token": "ghp_" + "a" * 36,
        "point-capability-url": "https://example.invalid/a/" + "a" * 43,
        "literal-secret": 'DJANGO_SECRET_KEY="' + "a" * 64 + '"',
    }
    for category, pattern in PATTERNS.items():
        assert pattern.search(samples[category])
        assert not pattern.search("DJANGO_SECRET_KEY=<provided-by-environment>")
    found = list(findings(ROOT))
    for path, line, category in found:
        print(f"{path}:{line}: {category}")
    print(f"Limited source-pattern scan: {len(found)} findings. No Git-history or entropy scan.")
    raise SystemExit(1 if found else 0)


if __name__ == "__main__":
    main()
