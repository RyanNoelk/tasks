from datetime import datetime, timezone
from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.scheduling import format_frequency
from app.time import local_zone, today as today_local

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _format_local_hm(dt: datetime | None) -> str:
    """Format a datetime as 'HH:MM' in the configured local zone.

    Treats naive datetimes as UTC since stored timestamps may come back
    without tzinfo from SQLite. This is a server-side fallback; the page's
    JS (`tasksFormatTimes`) converts <time datetime="..."> elements to the
    user's browser locale on render.
    """
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(local_zone()).strftime("%-I:%M %p")


def _to_iso_utc(dt: datetime | None) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


templates.env.filters["local_hm"] = _format_local_hm
templates.env.filters["iso_utc"] = _to_iso_utc
templates.env.filters["frequency"] = format_frequency
templates.env.globals["today"] = today_local
