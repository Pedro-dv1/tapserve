import runpy
from pathlib import Path

import pytest


@pytest.mark.parametrize("fault", ["duplicate", "missing-file", "missing-symbol", "outside"])
def test_current_requirements_validation_rejects_broken_evidence(tmp_path, fault):
    root = Path(__file__).resolve().parents[2]
    validate = runpy.run_path(str(root / "scripts/extract_architecture.py"))[
        "validate_traceability"
    ]
    (tmp_path / "docs").mkdir()
    (tmp_path / "app.py").write_text("def checked(): pass\n", encoding="utf-8")
    reference = {
        "missing-file": "missing.py",
        "missing-symbol": "app.py::absent",
        "outside": "../outside.py",
        "duplicate": "app.py::checked",
    }[fault]
    row = f"| TS-001 | Concrete behavior | `app.py` | `{reference}` | Implementado |\n"
    (tmp_path / "docs/REQUIREMENTS_TRACEABILITY.md").write_text(
        row * (2 if fault == "duplicate" else 1), encoding="utf-8"
    )
    with pytest.raises(ValueError):
        validate(tmp_path)
