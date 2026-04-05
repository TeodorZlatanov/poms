from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return the current time as a timezone-aware UTC datetime.

    Used as the default factory for every timestamp column in the project so
    that values round-trip through PostgreSQL TIMESTAMPTZ columns with explicit
    UTC offset, and reach the frontend as ISO strings with a `+00:00` suffix.
    """
    return datetime.now(UTC)
