from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


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
