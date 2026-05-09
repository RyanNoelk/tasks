import os
from contextvars import ContextVar
from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


# Per-request override set by middleware from the browser's `tz` cookie.
_tz_var: ContextVar[str | None] = ContextVar("tz_name", default=None)


def set_request_tz(name: str | None) -> None:
    """Set the IANA timezone name for the current request context."""
    _tz_var.set(name)


def local_zone() -> ZoneInfo:
    """Return the active local zone.

    Resolution order: per-request cookie override → `TZ` env var → UTC.
    """
    candidates = (_tz_var.get(), os.environ.get("TZ"))
    for name in candidates:
        if not name:
            continue
        try:
            return ZoneInfo(name)
        except (ZoneInfoNotFoundError, ValueError):
            continue
    return ZoneInfo("UTC")


# Backward-compat alias
_local_zone = local_zone


def today() -> date:
    return datetime.now(local_zone()).date()
