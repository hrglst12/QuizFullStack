from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from app.auth import hash_password, require_admin
from app.db import DB, get_or_404
from app.models import User
from app.schemas import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/api/admin/users", tags=["users"], dependencies=[Depends(require_admin)])


@router.get("")
def list_users(db: DB) -> list[UserOut]:
    return db.scalars(select(User).order_by(User.id)).all()


@router.post("", status_code=201)
def create_user(body: UserCreate, db: DB) -> UserOut:
    user = User(username=body.username, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    return user


@router.get("/{user_id}")
def get_user(user_id: int, db: DB) -> UserOut:
    return get_or_404(db, User, user_id)


@router.put("/{user_id}")
def update_user(user_id: int, body: UserUpdate, db: DB) -> UserOut:
    user = get_or_404(db, User, user_id)
    user.username = body.username
    if body.password is not None:
        user.password_hash = hash_password(body.password)
    db.commit()
    return user


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, db: DB) -> None:
    user = get_or_404(db, User, user_id)
    if db.scalar(select(func.count(User.id))) <= 1:
        raise HTTPException(409, "Son kullanıcı silinemez, kimse giriş yapamaz hale gelir")
    db.delete(user)
    db.commit()
