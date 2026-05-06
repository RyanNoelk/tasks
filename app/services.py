from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import OneOffTask, TaskCompletion, TaskTemplate


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


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


# ── One-off tasks ────────────────────────────────────────


@dataclass
class OneOffPage:
    items: list[OneOffTask]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        if self.total == 0:
            return 1
        return (self.total + self.page_size - 1) // self.page_size

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages


def _paginate_one_offs(
    session: Session,
    base_filter,
    order_by,
    *,
    q: str | None,
    page: int,
    page_size: int,
) -> OneOffPage:
    page = max(1, page)
    page_size = max(1, min(200, page_size))

    where = [base_filter]
    if q:
        where.append(OneOffTask.name.ilike(f"%{q.strip()}%"))

    total = session.scalar(
        select(func.count(OneOffTask.id)).where(*where)
    ) or 0

    stmt = (
        select(OneOffTask)
        .where(*where)
        .order_by(*order_by)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list(session.scalars(stmt))
    return OneOffPage(items=items, total=total, page=page, page_size=page_size)


def list_pending_one_offs(
    session: Session,
    *,
    q: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> OneOffPage:
    return _paginate_one_offs(
        session,
        OneOffTask.completed_at.is_(None),
        (OneOffTask.created_at, OneOffTask.id),
        q=q,
        page=page,
        page_size=page_size,
    )


def list_completed_one_offs(
    session: Session,
    *,
    q: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> OneOffPage:
    return _paginate_one_offs(
        session,
        OneOffTask.completed_at.is_not(None),
        (OneOffTask.completed_at.desc(), OneOffTask.id.desc()),
        q=q,
        page=page,
        page_size=page_size,
    )


def create_one_off(session: Session, name: str) -> OneOffTask:
    task = OneOffTask(name=name.strip())
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def complete_one_off(session: Session, task_id: int) -> OneOffTask | None:
    task = session.get(OneOffTask, task_id)
    if task is None:
        return None
    task.completed_at = _utcnow()
    session.commit()
    session.refresh(task)
    return task


def restore_one_off(session: Session, task_id: int) -> OneOffTask | None:
    task = session.get(OneOffTask, task_id)
    if task is None:
        return None
    task.completed_at = None
    session.commit()
    session.refresh(task)
    return task


def delete_one_off(session: Session, task_id: int) -> bool:
    task = session.get(OneOffTask, task_id)
    if task is None:
        return False
    session.delete(task)
    session.commit()
    return True
