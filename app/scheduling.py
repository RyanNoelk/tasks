"""Scheduling helpers for recurring task templates.

Schedules are stored as RFC 5545 RRULE strings + a DTSTART date. We use
``dateutil.rrule`` to parse and evaluate occurrences. UI input is mediated by a
small set of presets; we map presets <-> RRULE in this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from dateutil.rrule import DAILY, MONTHLY, WEEKLY, rrulestr


WEEKDAY_CODES: tuple[str, ...] = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")
WEEKDAY_SHORT: tuple[str, ...] = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
WEEKDAY_PLURAL: tuple[str, ...] = (
    "Mondays",
    "Tuesdays",
    "Wednesdays",
    "Thursdays",
    "Fridays",
    "Saturdays",
    "Sundays",
)
WEEK_ORDINAL_LABEL: dict[int, str] = {
    1: "First",
    2: "Second",
    3: "Third",
    4: "Fourth",
    -1: "Last",
}


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _build_rule(rrule_str: str, dtstart: date):
    return rrulestr(rrule_str, dtstart=datetime.combine(dtstart, time.min))


def is_scheduled(template, on_date: date) -> bool:
    """Return True if `template` is scheduled to occur on `on_date`."""
    if on_date < template.schedule_dtstart:
        return False
    rule = _build_rule(template.schedule_rrule, template.schedule_dtstart)
    start = datetime.combine(on_date, time.min)
    end = start + timedelta(days=1)
    return bool(rule.between(start, end, inc=True))


# ── Format ────────────────────────────────────────────────


def format_frequency(template) -> str:
    rule = _build_rule(template.schedule_rrule, template.schedule_dtstart)
    freq = rule._freq
    interval = rule._interval or 1

    if freq == DAILY:
        return "Daily" if interval == 1 else f"Every {interval} days"

    if freq == WEEKLY:
        days = sorted(rule._byweekday) if rule._byweekday else []
        if interval == 1:
            if days == [0, 1, 2, 3, 4]:
                return "Weekdays"
            if days == [5, 6]:
                return "Weekends"
            if not days:
                return "Weekly"
            if len(days) == 1:
                return WEEKDAY_PLURAL[days[0]]
            return ", ".join(WEEKDAY_SHORT[d] for d in days)
        # interval > 1
        if not days:
            return f"Every {interval} weeks"
        day_str = ", ".join(WEEKDAY_SHORT[d] for d in days)
        if interval == 2:
            return f"Every other week on {day_str}"
        return f"Every {interval} weeks on {day_str}"

    if freq == MONTHLY:
        if rule._bymonthday:
            md = rule._bymonthday[0]
            if md == -1:
                return "Monthly on the last day"
            return f"Monthly on the {_ordinal(md)}"
        if rule._bynweekday:
            wd, n = rule._bynweekday[0]
            label = WEEK_ORDINAL_LABEL.get(n, str(n))
            return f"{label} {WEEKDAY_SHORT[wd]} of the month"

    return template.schedule_rrule


# ── Parse form ────────────────────────────────────────────


def _days_to_codes(days: list[str] | None) -> list[str]:
    if not days:
        return []
    out = []
    for raw in days:
        try:
            i = int(raw)
        except (TypeError, ValueError):
            continue
        if 0 <= i <= 6:
            out.append(WEEKDAY_CODES[i])
    return out


def _parse_iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("anchor_date must be YYYY-MM-DD") from exc


def parse_schedule_form(
    *,
    preset: str,
    days: list[str] | None = None,
    interval: int | str | None = None,
    anchor_date: str | None = None,
    day_of_month: int | str | None = None,
    last_day: bool = False,
    which_week: int | str | None = None,
    which_weekday: int | str | None = None,
    today: date | None = None,
) -> tuple[str, date]:
    """Translate UI preset + fields into (rrule_string, dtstart).

    Raises ``ValueError`` on any invalid combination; route layer maps to 400.
    """
    today = today or date.today()

    if preset == "daily":
        return "FREQ=DAILY", today

    if preset == "weekdays":
        return "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR", today

    if preset == "weekends":
        return "FREQ=WEEKLY;BYDAY=SA,SU", today

    if preset == "custom_weekly":
        codes = _days_to_codes(days)
        if not codes:
            raise ValueError("pick at least one day")
        return f"FREQ=WEEKLY;BYDAY={','.join(codes)}", today

    if preset == "every_n_weeks":
        codes = _days_to_codes(days)
        if not codes:
            raise ValueError("pick at least one day")
        try:
            n = int(interval) if interval is not None else 2
        except (TypeError, ValueError) as exc:
            raise ValueError("interval must be an integer") from exc
        if n < 1:
            raise ValueError("interval must be >= 1")
        anchor = _parse_iso_date(anchor_date) if anchor_date else today
        return f"FREQ=WEEKLY;INTERVAL={n};BYDAY={','.join(codes)}", anchor

    if preset == "monthly_day":
        if last_day:
            return "FREQ=MONTHLY;BYMONTHDAY=-1", today
        try:
            d = int(day_of_month) if day_of_month is not None else 0
        except (TypeError, ValueError) as exc:
            raise ValueError("day_of_month must be an integer") from exc
        if not 1 <= d <= 31:
            raise ValueError("day_of_month must be 1..31")
        return f"FREQ=MONTHLY;BYMONTHDAY={d}", today

    if preset == "monthly_nth_weekday":
        try:
            wk = int(which_week) if which_week is not None else 0
        except (TypeError, ValueError) as exc:
            raise ValueError("which_week must be an integer") from exc
        try:
            wd = int(which_weekday) if which_weekday is not None else -1
        except (TypeError, ValueError) as exc:
            raise ValueError("which_weekday must be an integer") from exc
        if wk not in (1, 2, 3, 4, -1):
            raise ValueError("which_week must be 1..4 or -1 (last)")
        if not 0 <= wd <= 6:
            raise ValueError("which_weekday must be 0..6")
        return f"FREQ=MONTHLY;BYDAY={wk}{WEEKDAY_CODES[wd]}", today

    raise ValueError(f"unknown preset: {preset}")


# ── Reverse: prefill form from an existing template ──────


@dataclass
class FormState:
    preset: str = "daily"
    days: list[int] = field(default_factory=list)
    interval: int = 2
    anchor_date: date | None = None
    day_of_month: int = 1
    last_day: bool = False
    which_week: int = 1
    which_weekday: int = 0


def derive_form_state(template) -> FormState:
    rule = _build_rule(template.schedule_rrule, template.schedule_dtstart)
    state = FormState(anchor_date=template.schedule_dtstart)
    freq = rule._freq
    interval = rule._interval or 1

    if freq == DAILY:
        state.preset = "daily"
        return state

    if freq == WEEKLY:
        days = sorted(rule._byweekday) if rule._byweekday else []
        state.days = list(days)
        if interval == 1:
            if days == [0, 1, 2, 3, 4]:
                state.preset = "weekdays"
            elif days == [5, 6]:
                state.preset = "weekends"
            else:
                state.preset = "custom_weekly"
        else:
            state.preset = "every_n_weeks"
            state.interval = interval
        return state

    if freq == MONTHLY:
        if rule._bymonthday:
            md = rule._bymonthday[0]
            state.preset = "monthly_day"
            if md == -1:
                state.last_day = True
                state.day_of_month = 1
            else:
                state.day_of_month = md
            return state
        if rule._bynweekday:
            wd, n = rule._bynweekday[0]
            state.preset = "monthly_nth_weekday"
            state.which_week = n
            state.which_weekday = wd
            return state

    return state
