from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError

from app import auth, models  # noqa: F401  (models must be imported to register tables)
from app.db import Base, engine
from app.routers import admin, public


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Quiz API", lifespan=lifespan)


@app.exception_handler(IntegrityError)
async def conflict(_, __):
    return JSONResponse({"detail": "Conflicts with existing data"}, status_code=409)


app.include_router(public.router)
app.include_router(auth.router)
app.include_router(admin.router)
# Web UI: / is the quiz, /admin/ is the dashboard. Mounted last so /api/* wins.
app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True))
