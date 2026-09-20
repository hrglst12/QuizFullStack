from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.db import DB, get_or_404
from app.models import Category, Question
from app.schemas import CategoryIn, CategoryOut, QuestionIn, QuestionOut

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.post("/categories", status_code=201)
def create_category(body: CategoryIn, db: DB) -> CategoryOut:
    category = Category(**body.model_dump())
    db.add(category)
    db.commit()
    return category


@router.put("/categories/{category_id}")
def update_category(category_id: int, body: CategoryIn, db: DB) -> CategoryOut:
    category = get_or_404(db, Category, category_id)
    category.name = body.name
    db.commit()
    return category


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(category_id: int, db: DB) -> None:
    db.delete(get_or_404(db, Category, category_id))
    db.commit()


@router.get("/questions")
def list_questions(db: DB, category_id: int | None = None) -> list[QuestionOut]:
    stmt = select(Question).order_by(Question.id.desc())
    if category_id:
        stmt = stmt.where(Question.category_id == category_id)
    return db.scalars(stmt).all()


def save_question(db: Session, question: Question, body: QuestionIn) -> Question:
    get_or_404(db, Category, body.category_id)
    for field, value in body.model_dump().items():
        setattr(question, field, value)
    db.add(question)
    db.commit()
    return question


@router.post("/questions", status_code=201)
def create_question(body: QuestionIn, db: DB) -> QuestionOut:
    return save_question(db, Question(), body)


@router.put("/questions/{question_id}")
def update_question(question_id: int, body: QuestionIn, db: DB) -> QuestionOut:
    return save_question(db, get_or_404(db, Question, question_id), body)


@router.delete("/questions/{question_id}", status_code=204)
def delete_question(question_id: int, db: DB) -> None:
    db.delete(get_or_404(db, Question, question_id))
    db.commit()
