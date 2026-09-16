class PersistenceFailure(RuntimeError):
    """A database transaction could not be completed."""


class MessageIdentityConflict(ValueError):
    """A provider identifier was reused with different immutable message data."""
