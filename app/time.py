import os
from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _resolve_zone(name: str | None) -> ZoneInfo:
    """First valid zone wins: explicit name → TZ env → UTC."""
    for candidate in (name, os.environ.get("TZ")):
        if not candidate:
            continue
        try:
            return ZoneInfo(candidate)
        except (ZoneInfoNotFoundError, ValueError):
            continue
    return ZoneInfo("UTC")


def local_zone(tz_name: str | None = None) -> ZoneInfo:
    return _resolve_zone(tz_name)


# Backward-compat alias
_local_zone = local_zone


def today(tz_name: str | None = None) -> date:
    return datetime.now(_resolve_zone(tz_name)).date()
