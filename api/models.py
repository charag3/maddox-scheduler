import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Integer, Text, Enum as SAEnum, ForeignKey, TIMESTAMP as _TS
from sqlalchemy.dialects.postgresql import UUID

TIMESTAMPTZ = _TS(timezone=True)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


class TaskStatus(str, enum.Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"
    paused = "paused"


PROJECTS = [
    "Chimney Chimp",
    "Skill Builders ABA",
    "Bespo Watches",
    "Ekho Engine",
    "SomaAgentBot",
    "Fire-Hire",
    "Maalob",
    "Arganika Tree",
    "KDM Tecnologías",
    "Revolver Garage",
    "Umbra Performance",
    "web-raiz",
    "Soma Space Ops",
    "Phil's Painting",
    "Polished",
    "Personal",
]

PROJECT_COLORS = {
    "Chimney Chimp": "#f97316",
    "Skill Builders ABA": "#8b5cf6",
    "Bespo Watches": "#0ea5e9",
    "Ekho Engine": "#06b6d4",
    "SomaAgentBot": "#10b981",
    "Fire-Hire": "#ef4444",
    "Maalob": "#84cc16",
    "Arganika Tree": "#22c55e",
    "KDM Tecnologías": "#3b82f6",
    "Revolver Garage": "#f59e0b",
    "Umbra Performance": "#6366f1",
    "web-raiz": "#ec4899",
    "Soma Space Ops": "#14b8a6",
    "Phil's Painting": "#a78bfa",
    "Polished": "#fb923c",
    "Personal": "#94a3b8",
}


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String, nullable=False)
    project: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[TaskStatus] = mapped_column(SAEnum(TaskStatus, name="task_status", create_type=False), default=TaskStatus.todo)
    priority: Mapped[int] = mapped_column(Integer, default=3)
    scheduled_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)
    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actual_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, default=datetime.utcnow, onupdate=datetime.utcnow)

    work_logs: Mapped[list["WorkLog"]] = relationship("WorkLog", back_populates="task", cascade="all, delete-orphan")


class WorkLog(Base):
    __tablename__ = "work_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"))
    started_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    task: Mapped["Task"] = relationship("Task", back_populates="work_logs")
