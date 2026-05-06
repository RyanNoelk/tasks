from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import TaskCompletion, TaskTemplate


@dataclass
class ChecklistItem:
    template_id: int
    name: str
    completed: bool
    date: date


def list_active_templates(session: Session) -> list[TaskTemplate]:
    stmt = (
        select(TaskTemplate)
        .where(TaskTemplate.active.is_(True))
        .order_by(TaskTemplate.position, TaskTemplate.id)
    )
    return list(session.scalars(stmt))


def list_all_templates(session: Session) -> list[TaskTemplate]:
    stmt = select(TaskTemplate).order_by(TaskTemplate.position, TaskTemplate.id)
    return list(session.scalars(stmt))


def get_template(session: Session, template_id: int) -> TaskTemplate | None:
    return session.get(TaskTemplate, template_id)


def create_template(session: Session, name: str) -> TaskTemplate:
    max_pos = session.scalar(select(func.coalesce(func.max(TaskTemplate.position), -1))) or -1
    tmpl = TaskTemplate(name=name.strip(), position=max_pos + 1, active=True)
    session.add(tmpl)
    session.commit()
    session.refresh(tmpl)
    return tmpl


def update_template(
    session: Session,
    template_id: int,
    *,
    name: str | None = None,
    position: int | None = None,
) -> TaskTemplate | None:
    tmpl = session.get(TaskTemplate, template_id)
    if tmpl is None:
        return None
    if name is not None:
        tmpl.name = name.strip()
    if position is not None:
        tmpl.position = position
    session.commit()
    session.refresh(tmpl)
    return tmpl


def soft_delete_template(session: Session, template_id: int) -> bool:
    tmpl = session.get(TaskTemplate, template_id)
    if tmpl is None:
        return False
    tmpl.active = False
    session.commit()
    return True


def checklist_for(session: Session, on_date: date, *, include_inactive: bool = False) -> list[ChecklistItem]:
    """Return joined view of templates and whether each was completed on `on_date`.

    For today's view, filter to active templates only. For history, include inactive
    templates that have a completion row for that date so old data still renders.
    """
    completed_ids_stmt = select(TaskCompletion.template_id).where(TaskCompletion.date == on_date)
    completed_ids: set[int] = set(session.scalars(completed_ids_stmt))

    if include_inactive:
        stmt = (
            select(TaskTemplate)
            .where((TaskTemplate.active.is_(True)) | (TaskTemplate.id.in_(completed_ids)))
            .order_by(TaskTemplate.position, TaskTemplate.id)
        )
    else:
        stmt = (
            select(TaskTemplate)
            .where(TaskTemplate.active.is_(True))
            .order_by(TaskTemplate.position, TaskTemplate.id)
        )
    templates = list(session.scalars(stmt))

    return [
        ChecklistItem(
            template_id=t.id,
            name=t.name,
            completed=t.id in completed_ids,
            date=on_date,
        )
        for t in templates
    ]


def toggle_completion(session: Session, template_id: int, on_date: date) -> ChecklistItem | None:
    """Insert or delete a completion row. Return the resulting state or None if template missing."""
    tmpl = session.get(TaskTemplate, template_id)
    if tmpl is None:
        return None

    existing = session.scalar(
        select(TaskCompletion).where(
            TaskCompletion.template_id == template_id,
            TaskCompletion.date == on_date,
        )
    )
    if existing is None:
        session.add(TaskCompletion(template_id=template_id, date=on_date))
        session.commit()
        completed = True
    else:
        session.delete(existing)
        session.commit()
        completed = False

    return ChecklistItem(template_id=tmpl.id, name=tmpl.name, completed=completed, date=on_date)
