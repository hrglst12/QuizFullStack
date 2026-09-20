from sqlalchemy import JSON, ForeignKey, String, Text, func, select
from sqlalchemy.orm import Mapped, column_property, mapped_column

from app.db import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(Text)
    options: Mapped[list[str]] = mapped_column(JSON)
    answer_index: Mapped[int]


Category.question_count = column_property(
    select(func.count(Question.id)).where(Question.category_id == Category.id).scalar_subquery()
)
