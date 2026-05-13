from datetime import date as date_cls

from fastapi import APIRouter, Cookie, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from app import services
from app.db import get_session
from app.templating import templates
from app.time import today as today_local

router = APIRouter(prefix="/one-offs")


@router.post("", response_class=HTMLResponse, response_model=None)
def create(
    request: Request,
    name: str = Form(...),
    due_date: str | None = Form(default=None),
    session: Session = Depends(get_session),
    tz: str | None = Cookie(default=None),
):
    name = name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="name required")
    parsed_due: date_cls | None = None
    if due_date:
        try:
            parsed_due = date_cls.fromisoformat(due_date)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="invalid due_date") from exc
    task = services.create_one_off(session, name, due_date=parsed_due)
    # Any due date affects sort order (and bucket placement when due today/past).
    # Trigger a full HTMX refresh so server-side ORDER BY drives the layout.
    # Undated tasks already sort last; safe to inline-append via HTMX.
    if parsed_due is not None:
        return Response(status_code=204, headers={"HX-Refresh": "true"})
    return templates.TemplateResponse(
        request,
        "partials/one_off_row.html",
        {"task": task, "view": "today", "today": today_local(tz)},
    )


@router.post("/{task_id}/complete", response_model=None)
def complete(
    task_id: int,
    session: Session = Depends(get_session),
) -> Response:
    task = services.complete_one_off(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    # Full refresh so the row leaves Today, bucket re-sorts, and counts update.
    return Response(status_code=204, headers={"HX-Refresh": "true"})


@router.post("/{task_id}/restore", response_model=None)
def restore(
    task_id: int,
    session: Session = Depends(get_session),
) -> Response:
    task = services.restore_one_off(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return Response(status_code=204, headers={"HX-Refresh": "true"})


@router.delete("/{task_id}")
def delete(task_id: int, session: Session = Depends(get_session)) -> Response:
    ok = services.delete_one_off(session, task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="task not found")
    return Response(status_code=200)
