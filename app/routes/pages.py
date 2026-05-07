from datetime import date as date_cls, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app import services
from app.db import get_session
from app.scheduling import FormState
from app.time import today as today_local
from app.templating import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    page: int = 1,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    on_date = today_local()
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
            "one_offs": one_offs,
            "one_offs_due_now": due_now,
            "one_offs_later": later,
        },
    )


@router.get("/manage", response_class=HTMLResponse)
def manage(request: Request, session: Session = Depends(get_session)) -> HTMLResponse:
    rows = services.list_all_templates(session)
    return templates.TemplateResponse(
        request,
        "manage.html",
        {"rows": rows, "form_state": FormState(anchor_date=today_local())},
    )


@router.get("/history", response_class=HTMLResponse)
def history(
    request: Request,
    date: str | None = None,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    if date is None:
        on_date = today_local()
    else:
        try:
            on_date = date_cls.fromisoformat(date)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="invalid date, expected YYYY-MM-DD") from exc

    items = services.checklist_for(session, on_date, include_inactive=True)
    today = today_local()
    prev_date = on_date - timedelta(days=1)
    next_date = on_date + timedelta(days=1) if on_date < today else None
    return templates.TemplateResponse(
        request,
        "history.html",
        {
            "items": items,
            "on_date": on_date,
            "is_today": on_date == today,
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
) -> HTMLResponse:
    tasks = services.list_completed_one_offs(session, q=q, page=page)
    return templates.TemplateResponse(
        request,
        "one_off_history.html",
        {"tasks": tasks, "q": q or ""},
    )


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
