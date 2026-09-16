import os
import shutil
import subprocess
import sys
from pathlib import Path


def test_forbidden_import_breaks_architecture_check(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    shutil.copytree(
        root / "app", tmp_path / "app", ignore=shutil.ignore_patterns("*.pyc")
    )
    schema = tmp_path / "app" / "schemas" / "health.py"
    schema.write_text(schema.read_text(encoding="utf-8") + "\nimport app.api.health\n")
    executable = Path(sys.executable).parent / (
        "lint-imports.exe" if os.name == "nt" else "lint-imports"
    )
    assert executable.is_file()
    result = subprocess.run(
        [
            executable,
            "--config",
            str(root / "tests/architecture/.importlinter"),
            "--no-cache",
        ],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "BROKEN" in result.stdout
    assert "app.schemas.health" in result.stdout
