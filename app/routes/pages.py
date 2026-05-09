from datetime import date as date_cls, timedelta

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app import services
from app.db import get_session
from app.scheduling import FormState
from app.time import today as today_local
from app.templating import templates

router = APIRouter()


def get_today(tz: str | None = Cookie(default=None)) -> date_cls:
    """Return user's local today, derived from the `tz` cookie set by the browser."""
    return today_local(tz)


@router.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    page: int = 1,
    session: Session = Depends(get_session),
    on_date: date_cls = Depends(get_today),
) -> HTMLResponse:
    items = services.checklist_for(session, on_date, include_inactive=False)
    one_offs = services.list_pending_one_offs(session, page=page)
    due_now = [t for t in one_offs.items if t.due_date and t.due_date <= on_date]
    later = [t for t in one_offs.items if not t.due_date or t.due_date > on_date]
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "items": items,
            "on_date": on_date,
            "is_today": True,
            "today": on_date,
            "one_offs": one_offs,
            "one_offs_due_now": due_now,
            "one_offs_later": later,
        },
    )


@router.get("/manage", response_class=HTMLResponse)
def manage(
    request: Request,
    session: Session = Depends(get_session),
    today_value: date_cls = Depends(get_today),
) -> HTMLResponse:
    active_rows = services.list_active_templates(session)
    archived_rows = services.list_archived_templates(session)
    return templates.TemplateResponse(
        request,
        "manage.html",
        {
            "active_rows": active_rows,
            "archived_rows": archived_rows,
            "form_state": FormState(anchor_date=today_value),
            "today": today_value,
        },
    )


@router.get("/history", response_class=HTMLResponse)
def history(
    request: Request,
    date: str | None = None,
    session: Session = Depends(get_session),
    today_value: date_cls = Depends(get_today),
) -> HTMLResponse:
    if date is None:
        on_date = today_value
    else:
        try:
            on_date = date_cls.fromisoformat(date)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="invalid date, expected YYYY-MM-DD") from exc

    items = services.checklist_for(session, on_date, include_inactive=True)
    prev_date = on_date - timedelta(days=1)
    next_date = on_date + timedelta(days=1) if on_date < today_value else None
    return templates.TemplateResponse(
        request,
        "history.html",
        {
            "items": items,
            "on_date": on_date,
            "is_today": on_date == today_value,
            "today": today_value,
            "prev_date": prev_date,
            "next_date": next_date,
        },
    )


@router.get("/one-offs/history", response_class=HTMLResponse)
def one_off_history(
    request: Request,
    q: str | None = None,
    page: int = 1,
    session: Session = Depends(get_session),
    today_value: date_cls = Depends(get_today),
) -> HTMLResponse:
    tasks = services.list_completed_one_offs(session, q=q, page=page)
    return templates.TemplateResponse(
        request,
        "one_off_history.html",
        {"tasks": tasks, "q": q or "", "today": today_value},
    )


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
