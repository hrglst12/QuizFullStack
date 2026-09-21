from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


Username = Annotated[Text, Field(max_length=50)]
Password = Annotated[str, Field(min_length=8, max_length=128)]


class UserCreate(BaseModel):
    username: Username
    password: Password


class UserUpdate(BaseModel):
    username: Username
    password: Password | None = None  # omitted = keep the current password


class UserOut(ORM):
    """Never includes the password hash."""

    id: int
    username: str
    created_at: datetime


class CategoryIn(BaseModel):
    name: Text = Field(max_length=100)


class CategoryOut(ORM, CategoryIn):
    id: int
    question_count: int


class QuestionIn(BaseModel):
    category_id: int
    text: Text
    options: list[Text] = Field(min_length=2, max_length=6)
    answer_index: int = Field(ge=0)

    @model_validator(mode="after")
    def answer_in_options(self):
        if self.answer_index >= len(self.options):
            raise ValueError("answer_index must point to one of the options")
        return self


class QuestionOut(ORM, QuestionIn):
    id: int


class QuestionPublic(ORM):
    """A question as shown to players: the correct answer is left out."""

    id: int
    category_id: int
    text: str
    options: list[str]


class AnswerIn(BaseModel):
    choice: int


class AnswerOut(BaseModel):
    correct: bool
    answer_index: int


class QuestionAnswer(AnswerIn):
    question_id: int


class ScoreIn(BaseModel):
    """A finished game: the server grades the answers itself instead of trusting a client-side score."""

    player_name: Text = Field(max_length=50)
    answers: list[QuestionAnswer] = Field(min_length=1, max_length=50)


class ScoreOut(ORM):
    id: int
    player_name: str
    score: int
    total: int
    created_at: datetime
