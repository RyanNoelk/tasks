from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from app import services
from app.db import get_session
from app.scheduling import derive_form_state, parse_schedule_form
from app.templating import templates

router = APIRouter(prefix="/templates")


def _parse_schedule(
    *,
    preset: str,
    days: list[str],
    interval: int | None,
    anchor_date: str | None,
    day_of_month: int | None,
    last_day: bool,
    which_week: int | None,
    which_weekday: int | None,
) -> tuple[str, object]:
    try:
        return parse_schedule_form(
            preset=preset,
            days=days,
            interval=interval,
            anchor_date=anchor_date,
            day_of_month=day_of_month,
            last_day=last_day,
            which_week=which_week,
            which_weekday=which_weekday,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("", response_class=HTMLResponse)
def create(
    request: Request,
    name: str = Form(...),
    preset: str = Form("daily"),
    days: list[str] = Form(default_factory=list),
    interval: int | None = Form(default=None),
    anchor_date: str | None = Form(default=None),
    day_of_month: int | None = Form(default=None),
    last_day: bool = Form(default=False),
    which_week: int | None = Form(default=None),
    which_weekday: int | None = Form(default=None),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    name = name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="name required")
    rrule, dtstart = _parse_schedule(
        preset=preset,
        days=days,
        interval=interval,
        anchor_date=anchor_date,
        day_of_month=day_of_month,
        last_day=last_day,
        which_week=which_week,
        which_weekday=which_weekday,
    )
    tmpl = services.create_template(session, name, rrule=rrule, dtstart=dtstart)
    return templates.TemplateResponse(
        request,
        "partials/template_row.html",
        {"row": tmpl},
    )


@router.get("/{template_id}/edit", response_class=HTMLResponse)
def edit_form(
    request: Request,
    template_id: int,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    tmpl = services.get_template(session, template_id)
    if tmpl is None:
        raise HTTPException(status_code=404, detail="template not found")
    return templates.TemplateResponse(
        request,
        "partials/template_edit_row.html",
        {"row": tmpl, "state": derive_form_state(tmpl)},
    )


@router.get("/{template_id}/cancel-edit", response_class=HTMLResponse)
def cancel_edit(
    request: Request,
    template_id: int,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    tmpl = services.get_template(session, template_id)
    if tmpl is None:
        raise HTTPException(status_code=404, detail="template not found")
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
    preset: str | None = Form(default=None),
    days: list[str] = Form(default_factory=list),
    interval: int | None = Form(default=None),
    anchor_date: str | None = Form(default=None),
    day_of_month: int | None = Form(default=None),
    last_day: bool = Form(default=False),
    which_week: int | None = Form(default=None),
    which_weekday: int | None = Form(default=None),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    rrule = None
    dtstart = None
    if preset is not None:
        rrule, dtstart = _parse_schedule(
            preset=preset,
            days=days,
            interval=interval,
            anchor_date=anchor_date,
            day_of_month=day_of_month,
            last_day=last_day,
            which_week=which_week,
            which_weekday=which_weekday,
        )

    tmpl = services.update_template(
        session,
        template_id,
        name=name,
        position=position,
        rrule=rrule,
        dtstart=dtstart,
    )
    if tmpl is None:
        raise HTTPException(status_code=404, detail="template not found")
    return templates.TemplateResponse(
        request,
        "partials/template_row.html",
        {"row": tmpl},
    )


@router.delete("/{template_id}", response_model=None)
def delete(
    template_id: int,
    session: Session = Depends(get_session),
):
    ok = services.soft_delete_template(session, template_id)
    if not ok:
        raise HTTPException(status_code=404, detail="template not found")
    # Refresh so the row moves to the Archived tab and counts update.
    return Response(status_code=204, headers={"HX-Refresh": "true"})
