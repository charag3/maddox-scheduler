import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from ..database import get_db
from ..models import Task, TaskStatus
from ..schemas import TaskCreate, TaskUpdate, TaskOut

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

LOAD_LOGS = selectinload(Task.work_logs)


async def get_task_or_404(task_id: uuid.UUID, db: AsyncSession) -> Task:
    q = select(Task).options(LOAD_LOGS).where(Task.id == task_id)
    result = await db.execute(q)
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(404, "Task not found")
    return task


@router.get("", response_model=list[TaskOut])
async def list_tasks(
    project: Optional[str] = None,
    status: Optional[TaskStatus] = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(Task).options(LOAD_LOGS).order_by(Task.priority.desc(), Task.scheduled_at.asc().nullslast())
    if project:
        q = q.where(Task.project == project)
    if status:
        q = q.where(Task.status == status)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("", response_model=TaskOut, status_code=201)
async def create_task(body: TaskCreate, db: AsyncSession = Depends(get_db)):
    task = Task(**body.model_dump())
    db.add(task)
    await db.commit()
    return await get_task_or_404(task.id, db)


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(task_id: uuid.UUID, body: TaskUpdate, db: AsyncSession = Depends(get_db)):
    task = await get_task_or_404(task_id, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    await db.commit()
    return await get_task_or_404(task_id, db)


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    task = await get_task_or_404(task_id, db)
    await db.delete(task)
    await db.commit()


@router.post("/{task_id}/start", response_model=TaskOut)
async def start_task(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    task = await get_task_or_404(task_id, db)
    task.started_at = datetime.now(timezone.utc)
    task.status = TaskStatus.in_progress
    await db.commit()
    return await get_task_or_404(task_id, db)


@router.post("/{task_id}/done", response_model=TaskOut)
async def complete_task(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    task = await get_task_or_404(task_id, db)
    now = datetime.now(timezone.utc)
    task.completed_at = now
    task.status = TaskStatus.done
    if task.started_at:
        delta = now - task.started_at
        task.actual_minutes = int(delta.total_seconds() / 60)
    await db.commit()
    return await get_task_or_404(task_id, db)
