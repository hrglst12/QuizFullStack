from datetime import datetime, timedelta, timezone
from secrets import compare_digest
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from app.config import settings
from app.schemas import Token

router = APIRouter(prefix="/api/admin", tags=["admin"])
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/admin/login")


@router.post("/login")
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    valid = compare_digest(form.username.encode(), settings.admin_username.encode()) & compare_digest(
        form.password.encode(), settings.admin_password.encode()
    )
    if not valid:
        raise HTTPException(401, "Incorrect username or password")
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.token_minutes)
    return Token(access_token=jwt.encode({"sub": form.username, "exp": expires}, settings.secret_key, "HS256"))


def require_admin(token: Annotated[str, Depends(oauth2)]) -> None:
    try:
        jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token", headers={"WWW-Authenticate": "Bearer"})
