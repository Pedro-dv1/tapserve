"""Validate the current versioned requirements; no missing legacy DOCX is assumed."""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate_traceability(root: Path = ROOT) -> list[str]:
    document = root / "docs" / "REQUIREMENTS_TRACEABILITY.md"
    rows = [
        line.split("|")[1:-1]
        for line in document.read_text(encoding="utf-8").splitlines()
        if re.match(r"^\| TS-\d{3} \|", line)
    ]
    if not rows:
        raise ValueError("The current requirements inventory is empty")
    identifiers = []
    for row in rows:
        if len(row) != 5 or any(not cell.strip() for cell in row):
            raise ValueError(
                "Each requirement needs ID, behavior, implementation, tests and status"
            )
        identifier, _, implementation, tests, _ = [cell.strip() for cell in row]
        if identifier in identifiers:
            raise ValueError("Duplicate requirement: " + identifier)
        identifiers.append(identifier)
        for cell in (implementation, tests):
            references = re.findall(r"`([^`]+)`", cell)
            if not references:
                raise ValueError("A requirement has no evidence paths: " + identifier)
            for reference in references:
                relative, _, symbol = reference.partition("::")
                path = (root / relative).resolve()
                if not path.is_relative_to(root.resolve()) or not path.is_file():
                    raise ValueError(
                        "Missing or out-of-tree requirement evidence: " + reference
                    )
                if symbol:
                    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
                    if not any(
                        isinstance(
                            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                        )
                        and node.name == symbol
                        for node in ast.walk(tree)
                    ):
                        raise ValueError(
                            "Missing requirement test/symbol: " + reference
                        )
    return identifiers


if __name__ == "__main__":
    print(
        f"Validated {len(validate_traceability())} current requirements and their evidence paths."
    )
