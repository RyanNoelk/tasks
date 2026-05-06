from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app import services
from app.db import get_session
from app.templating import templates

router = APIRouter(prefix="/templates")


@router.post("", response_class=HTMLResponse)
def create(
    request: Request,
    name: str = Form(...),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    name = name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="name required")
    tmpl = services.create_template(session, name)
    return templates.TemplateResponse(
        request,
        "partials/template_row.html",
        {"row": tmpl},
    )


@router.patch("/{template_id}", response_class=HTMLResponse)
def update(
    request: Request,
    template_id: int,
    name: str | None = Form(default=None),
    position: int | None = Form(default=None),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    tmpl = services.update_template(session, template_id, name=name, position=position)
    if tmpl is None:
        raise HTTPException(status_code=404, detail="template not found")
    return templates.TemplateResponse(
        request,
        "partials/template_row.html",
        {"row": tmpl},
    )


@router.delete("/{template_id}", response_class=HTMLResponse)
def delete(
    request: Request,
    template_id: int,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    ok = services.soft_delete_template(session, template_id)
    if not ok:
        raise HTTPException(status_code=404, detail="template not found")
    tmpl = services.get_template(session, template_id)
    return templates.TemplateResponse(
        request,
        "partials/template_row.html",
        {"row": tmpl},
    )
