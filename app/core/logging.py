import logging
import re

# Simple E.164-ish matcher for test proof.
_PHONE_PATTERN = re.compile(r"\+?\d{10,15}")
# Simple regex to redact potential JSON-like message content and credentials
_CREDENTIAL_PATTERN = re.compile(
    r"(?i)('|\"|)(password|secret|token|content|body)('|\"|)\s*(:|=)\s*('|\"|)(.*?)('|\"|)(,|}|\]|\n|$)"
)


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        redacted = _PHONE_PATTERN.sub("[REDACTED_PHONE]", original)
        redacted = _CREDENTIAL_PATTERN.sub(r"\1\2\3\4 [REDACTED]\8", redacted)
        return redacted


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(RedactingFormatter("%(levelname)s: %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
