from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from app.routes import one_off, pages, tasks, templates
from app.time import set_request_tz

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Daily Tasks")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.middleware("http")
async def tz_middleware(request: Request, call_next):
    """Pass the browser's IANA timezone (set by JS in `tz` cookie) into request context."""
    set_request_tz(request.cookies.get("tz"))
    return await call_next(request)


app.include_router(pages.router)
app.include_router(tasks.router)
app.include_router(templates.router)
app.include_router(one_off.router)
