import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .database import engine
from .models import Base
from .routes import tasks, work_logs, calendar
from .models import PROJECTS, PROJECT_COLORS


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)
    yield


app = FastAPI(title="Maddox Scheduler", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks.router)
app.include_router(work_logs.router)
app.include_router(calendar.router)


@app.get("/api/projects")
async def get_projects():
    return [{"name": p, "color": PROJECT_COLORS.get(p, "#94a3b8")} for p in PROJECTS]


static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def serve_calendar():
    return FileResponse(os.path.join(static_dir, "calendar.html"))
