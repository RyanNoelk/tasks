from datetime import date as date_cls

from fastapi import APIRouter, Cookie, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app import services
from app.db import get_session
from app.time import today as today_local

router = APIRouter(prefix="/tasks")


@router.post("/{template_id}/toggle", response_model=None)
def toggle(
    template_id: int,
    date: str | None = None,
    session: Session = Depends(get_session),
    tz: str | None = Cookie(default=None),
):
    today_value = today_local(tz)
    on_date = today_value
    if date is not None:
        try:
            on_date = date_cls.fromisoformat(date)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="invalid date, expected YYYY-MM-DD") from exc

    item = services.toggle_completion(session, template_id, on_date)
    if item is None:
        raise HTTPException(status_code=404, detail="template not found")

    # Full refresh so completed tasks reorder to bottom and times render in
    # the user's local TZ from the next render pass.
    return Response(status_code=204, headers={"HX-Refresh": "true"})
