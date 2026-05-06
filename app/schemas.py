from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class TemplateUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    position: Optional[int] = None


class ChecklistRow(BaseModel):
    template_id: int
    name: str
    completed: bool
    date: date
