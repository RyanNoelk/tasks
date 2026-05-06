from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from app import services
from app.db import get_session
from app.templating import templates

router = APIRouter(prefix="/one-offs")


@router.post("", response_class=HTMLResponse)
def create(
    request: Request,
    name: str = Form(...),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    name = name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="name required")
    task = services.create_one_off(session, name)
    return templates.TemplateResponse(
        request,
        "partials/one_off_row.html",
        {"task": task, "view": "today"},
    )


@router.post("/{task_id}/complete", response_class=HTMLResponse)
def complete(
    request: Request,
    task_id: int,
    session: Session = Depends(get_session),
) -> Response:
    task = services.complete_one_off(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    # Empty body + outerHTML swap removes the row from Today.
    return Response(status_code=200)


@router.post("/{task_id}/restore", response_class=HTMLResponse)
def restore(
    request: Request,
    task_id: int,
    session: Session = Depends(get_session),
) -> Response:
    task = services.restore_one_off(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    # Removed from history list once restored.
    return Response(status_code=200)


@router.delete("/{task_id}")
def delete(task_id: int, session: Session = Depends(get_session)) -> Response:
    ok = services.delete_one_off(session, task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="task not found")
    return Response(status_code=200)
