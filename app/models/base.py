from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy mapping registry; no shared domain attributes or behavior."""
