from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from app.db import DB, get_or_404
from app.models import Category, Question, Score
from app.schemas import AnswerIn, AnswerOut, CategoryOut, QuestionPublic, ScoreIn, ScoreOut

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


@router.post("/categories/{category_id}/scores", status_code=201)
def submit_score(category_id: int, body: ScoreIn, db: DB) -> ScoreOut:
    get_or_404(db, Category, category_id)
    ids = [a.question_id for a in body.answers]
    if len(set(ids)) != len(ids):
        raise HTTPException(422, "Aynı soru birden fazla kez cevaplanamaz")
    stmt = select(Question.id, Question.answer_index).where(Question.category_id == category_id, Question.id.in_(ids))
    correct = dict(db.execute(stmt).all())
    if len(correct) != len(ids):
        raise HTTPException(422, "Cevaplar bu kategoriye ait olmayan veya var olmayan sorular içeriyor")
    entry = Score(
        category_id=category_id,
        player_name=body.player_name,
        score=sum(correct[a.question_id] == a.choice for a in body.answers),
        total=len(ids),
    )
    db.add(entry)
    db.commit()
    return entry


@router.get("/categories/{category_id}/scores")
def leaderboard(category_id: int, db: DB, limit: int = Query(10, ge=1, le=100)) -> list[ScoreOut]:
    get_or_404(db, Category, category_id)
    ratio = Score.score * 1.0 / Score.total  # compare by percentage: a category's question count can change over time
    stmt = (
        select(Score)
        .where(Score.category_id == category_id)
        .order_by(ratio.desc(), Score.total.desc(), Score.created_at, Score.id)
        .limit(limit)
    )
    return db.scalars(stmt).all()
