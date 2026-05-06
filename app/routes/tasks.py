from datetime import date as date_cls

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app import services
from app.db import get_session
from app.time import today as today_local
from app.templating import templates

router = APIRouter(prefix="/tasks")


@router.post("/{template_id}/toggle", response_class=HTMLResponse)
def toggle(
    request: Request,
    template_id: int,
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

    item = services.toggle_completion(session, template_id, on_date)
    if item is None:
        raise HTTPException(status_code=404, detail="template not found")

    return templates.TemplateResponse(
        request,
        "partials/task_row.html",
        {"item": item, "is_today": on_date == today_local()},
    )
