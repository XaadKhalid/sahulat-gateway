import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_configuration_reads_prefixed_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SAHULAT_HEALTH_REQUESTS_PER_SECOND", "25")
    assert Settings().health_requests_per_second == 25


@pytest.mark.parametrize("value", ["0", "-1", "1001", "invalid"])
def test_invalid_limit_fails_configuration(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("SAHULAT_HEALTH_REQUESTS_PER_SECOND", value)
    with pytest.raises(ValidationError):
        Settings()
