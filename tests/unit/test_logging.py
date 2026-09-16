import logging

from app.core.logging import RedactingFormatter


def test_redacting_formatter_hides_sensitive_data() -> None:
    formatter = RedactingFormatter("%(message)s")

    # Phone numbers
    record = logging.LogRecord(
        "test", logging.INFO, "", 0, "Called +12345678900", (), None
    )
    assert formatter.format(record) == "Called [REDACTED_PHONE]"

    # Message body/content (JSON-like)
    record2 = logging.LogRecord(
        "test",
        logging.INFO,
        "",
        0,
        'Payload: {"content": "Hello World"}',
        (),
        None,
    )
    assert formatter.format(record2) == 'Payload: {"content": [REDACTED]}'

    # Credentials
    record3 = logging.LogRecord(
        "test", logging.INFO, "", 0, "token=secret123, status=ok", (), None
    )
    assert formatter.format(record3) == "token= [REDACTED], status=ok"
