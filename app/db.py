from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    with SessionLocal() as db:
        yield db


DB = Annotated[Session, Depends(get_db)]


def get_or_404(db: Session, model: type[Base], id: int):
    if (obj := db.get(model, id)) is None:
        raise HTTPException(404, f"{model.__name__} not found")
    return obj
