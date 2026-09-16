import pytest


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SAHULAT_WEBHOOK_SECRET", "test-secret")
    monkeypatch.setenv("SAHULAT_WEBHOOK_VERIFY_TOKEN", "test-token")
    monkeypatch.setenv(
        "SAHULAT_DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test"
    )
