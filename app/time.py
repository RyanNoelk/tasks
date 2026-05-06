import os
from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def local_zone() -> ZoneInfo:
    name = os.environ.get("TZ", "UTC")
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


_local_zone = local_zone  # backward compat


def today() -> date:
    return datetime.now(local_zone()).date()
