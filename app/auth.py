from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pwdlib import PasswordHash
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.db import DB, SessionLocal
from app.models import User
from app.schemas import Token

router = APIRouter(prefix="/api/admin", tags=["admin"])
# Swagger UI's Authorize dialog offers both: log in with a username and password (oauth2), or paste a token you already
# have (bearer). Either way the client just sends "Authorization: Bearer <token>", so at runtime one is enough.
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/admin/login", auto_error=False)
pasted_token = HTTPBearer(
    auto_error=False,
    bearerFormat="JWT",
    description="POST /api/admin/login cevabındaki access_token değerini yapıştır (başına Bearer yazma).",
)

passwords = PasswordHash.recommended()  # argon2id
# Verified against when the username doesn't exist, so a failed login takes as long either way.
_DUMMY_HASH = passwords.hash("not-a-real-password")


def hash_password(password: str) -> str:
    return passwords.hash(password)


def ensure_admin() -> None:
    """The first user comes from .env; once any user exists the database is the source of truth."""
    with SessionLocal() as db:
        if db.scalar(select(func.count(User.id))):
            return
        db.add(User(username=settings.admin_username, password_hash=hash_password(settings.admin_password)))
        try:
            db.commit()
        except IntegrityError:  # another process created it first
            db.rollback()


@router.post("/login")
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DB) -> Token:
    user = db.scalar(select(User).where(User.username == form.username))
    password_ok = passwords.verify(form.password, user.password_hash if user else _DUMMY_HASH)
    if user is None or not password_ok:
        raise HTTPException(401, "Kullanıcı adı veya şifre hatalı")
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.token_minutes)
    return Token(access_token=jwt.encode({"sub": str(user.id), "exp": expires}, settings.secret_key, "HS256"))


def require_admin(
    oauth2_token: Annotated[str | None, Depends(oauth2)],
    bearer: Annotated[HTTPAuthorizationCredentials | None, Depends(pasted_token)],
    db: DB,
) -> User:
    invalid = HTTPException(401, "Geçersiz veya süresi dolmuş token", headers={"WWW-Authenticate": "Bearer"})
    token = oauth2_token or (bearer.credentials if bearer else None)
    if token is None:
        raise invalid
    try:
        user_id = int(jwt.decode(token, settings.secret_key, algorithms=["HS256"])["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise invalid
    # Looked up on every request so deleting a user cuts off their existing tokens immediately.
    if (user := db.get(User, user_id)) is None:
        raise invalid
    return user
