from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase


# ---------------------------------------------------------------------------
# SQLAlchemy ORM
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


class QuizRecord(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(256), nullable=False)
    source_filename = Column(String(256), nullable=False)
    questions_json = Column(Text, nullable=False)
    score = Column(Float, nullable=True)
    total = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Pydantic schemas – API request / response
# ---------------------------------------------------------------------------

class QuestionSchema(BaseModel):
    question: str
    answers: list[str]
    correct: str
    explanation: str = ""


class GenerateQuizRequest(BaseModel):
    filename: str
    text: str
    num_questions: int = Field(default=5, ge=1, le=20)


class GenerateQuizResponse(BaseModel):
    quiz_id: int
    title: str
    questions: list[QuestionSchema]


class AnswerItem(BaseModel):
    question_index: int
    selected: str


class CheckAnswersRequest(BaseModel):
    quiz_id: int
    answers: list[AnswerItem]


class CheckAnswersResponse(BaseModel):
    score: int
    total: int
    percent: float
    details: list[dict]


class QuizHistoryItem(BaseModel):
    id: int
    title: str
    source_filename: str
    score: Optional[float]
    total: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}
