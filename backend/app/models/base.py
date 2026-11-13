from datetime import datetime, timezone
from typing import ClassVar


def utcnow() -> datetime:
    """Naive UTC datetime (what pymongo returns on reads)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class SerializeMixin:
    # Keep explicit nulls in API output (used by Profile, where null means "not filled in yet").
    KEEP_NULLS: ClassVar[bool] = False
    # Fields never sent to clients.
    HIDDEN: ClassVar[frozenset] = frozenset()
