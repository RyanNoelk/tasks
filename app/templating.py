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
    without tzinfo from SQLite.
    """
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(local_zone()).strftime("%-I:%M %p")


templates.env.filters["local_hm"] = _format_local_hm
templates.env.filters["frequency"] = format_frequency
templates.env.globals["today"] = today_local
