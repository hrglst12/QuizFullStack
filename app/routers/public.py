from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.db import DB, get_or_404
from app.models import Category, Question
from app.schemas import AnswerIn, AnswerOut, CategoryOut, QuestionPublic

router = APIRouter(prefix="/api", tags=["quiz"])


@router.get("/categories")
def list_categories(db: DB) -> list[CategoryOut]:
    return db.scalars(select(Category).order_by(Category.name)).all()


@router.get("/categories/{category_id}/questions")
def quiz_questions(category_id: int, db: DB, limit: int = Query(10, ge=1, le=50)) -> list[QuestionPublic]:
    get_or_404(db, Category, category_id)
    stmt = select(Question).where(Question.category_id == category_id).order_by(func.random()).limit(limit)
    return db.scalars(stmt).all()


@router.post("/questions/{question_id}/answer")
def check_answer(question_id: int, body: AnswerIn, db: DB) -> AnswerOut:
    question = get_or_404(db, Question, question_id)
    return AnswerOut(correct=body.choice == question.answer_index, answer_index=question.answer_index)
