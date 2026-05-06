import os
from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _local_zone() -> ZoneInfo:
    name = os.environ.get("TZ", "UTC")
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def today() -> date:
    return datetime.now(_local_zone()).date()
