import os

import pytest

# Set these at import time so module-level settings parsing works
os.environ["SAHULAT_WEBHOOK_SECRET"] = "test-secret"
os.environ["SAHULAT_WEBHOOK_VERIFY_TOKEN"] = "test-token"
os.environ["SAHULAT_DATABASE_URL"] = (
    "postgresql+asyncpg://user:pass@localhost:5432/test"
)
os.environ["SAHULAT_REDIS_URL"] = "redis://localhost:6379"


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    pass
