import os
import subprocess
import sys


def test_import_does_not_load_runtime_configuration() -> None:
    result = subprocess.run(
        [sys.executable, "-c", "import app.main"],
        env={**os.environ, "SAHULAT_HEALTH_REQUESTS_PER_SECOND": "invalid"},
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr
