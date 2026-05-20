import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db
from ..models import WorkLog, Task
from ..schemas import WorkLogCreate, WorkLogOut

router = APIRouter(prefix="/api/work-logs", tags=["work_logs"])


@router.get("", response_model=list[WorkLogOut])
async def list_work_logs(
    task_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(WorkLog).order_by(WorkLog.started_at.desc())
    if task_id:
        q = q.where(WorkLog.task_id == task_id)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("", response_model=WorkLogOut, status_code=201)
async def create_work_log(body: WorkLogCreate, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, body.task_id)
    if not task:
        raise HTTPException(404, "Task not found")

    log = WorkLog(**body.model_dump())
    if not log.started_at:
        log.started_at = datetime.now(timezone.utc)

    if log.ended_at and log.started_at:
        delta = log.ended_at - log.started_at
        log.duration_minutes = int(delta.total_seconds() / 60)

    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log
