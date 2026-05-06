from datetime import date as date_cls, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app import services
from app.db import get_session
from app.time import today as today_local
from app.templating import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def index(request: Request, session: Session = Depends(get_session)) -> HTMLResponse:
    on_date = today_local()
    items = services.checklist_for(session, on_date, include_inactive=False)
    return templates.TemplateResponse(
        request,
        "index.html",
        {"items": items, "on_date": on_date, "is_today": True},
    )


@router.get("/manage", response_class=HTMLResponse)
def manage(request: Request, session: Session = Depends(get_session)) -> HTMLResponse:
    rows = services.list_all_templates(session)
    return templates.TemplateResponse(request, "manage.html", {"rows": rows})


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


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
