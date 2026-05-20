from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from ..database import get_db
from ..models import Task, TaskStatus
from ..schemas import TaskOut

router = APIRouter(prefix="/api/calendar", tags=["calendar"])

LOAD_LOGS = selectinload(Task.work_logs)


@router.get("/week", response_model=list[TaskOut])
async def week_tasks(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=now.weekday())
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)

    q = select(Task).options(LOAD_LOGS).where(
        Task.scheduled_at >= start,
        Task.scheduled_at < end,
    ).order_by(Task.scheduled_at.asc())

    result = await db.execute(q)
    return result.scalars().all()


@router.get("/today", response_model=list[TaskOut])
async def today_tasks(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    q = select(Task).options(LOAD_LOGS).where(
        Task.scheduled_at >= start,
        Task.scheduled_at < end,
    ).order_by(Task.priority.desc(), Task.scheduled_at.asc())

    result = await db.execute(q)
    return result.scalars().all()


@router.get("/zombies", response_model=list[TaskOut])
async def zombie_tasks(db: AsyncSession = Depends(get_db)):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)

    q = select(Task).options(LOAD_LOGS).where(
        Task.status.in_([TaskStatus.todo, TaskStatus.in_progress]),
        Task.updated_at < cutoff,
    ).order_by(Task.updated_at.asc())

    result = await db.execute(q)
    return result.scalars().all()
