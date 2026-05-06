from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routes import pages, tasks, templates

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Daily Tasks")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.include_router(pages.router)
app.include_router(tasks.router)
app.include_router(templates.router)
