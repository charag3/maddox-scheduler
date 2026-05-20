import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from .models import TaskStatus


class WorkLogBase(BaseModel):
    task_id: uuid.UUID
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None


class WorkLogCreate(WorkLogBase):
    pass


class WorkLogOut(WorkLogBase):
    id: uuid.UUID
    started_at: datetime

    model_config = {"from_attributes": True}


class TaskBase(BaseModel):
    title: str
    project: str
    status: TaskStatus = TaskStatus.todo
    priority: int = 3
    scheduled_at: Optional[datetime] = None
    estimated_minutes: Optional[int] = None
    notes: Optional[str] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    project: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[int] = None
    scheduled_at: Optional[datetime] = None
    estimated_minutes: Optional[int] = None
    notes: Optional[str] = None


class TaskOut(TaskBase):
    id: uuid.UUID
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    actual_minutes: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    work_logs: list[WorkLogOut] = []

    model_config = {"from_attributes": True}
