from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base, QuizRecord

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "quizzes.db"

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)

SessionLocal = sessionmaker(bind=engine)


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(engine)


def get_session() -> Session:
    return SessionLocal()


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------

def save_quiz(title: str, source_filename: str, questions: list[dict]) -> int:
    with get_session() as session:
        record = QuizRecord(
            title=title,
            source_filename=source_filename,
            questions_json=json.dumps(questions, ensure_ascii=False),
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record.id


def update_score(quiz_id: int, score: float, total: int) -> None:
    with get_session() as session:
        record = session.get(QuizRecord, quiz_id)
        if record:
            record.score = score
            record.total = total
            session.commit()


def get_quiz(quiz_id: int) -> QuizRecord | None:
    with get_session() as session:
        return session.get(QuizRecord, quiz_id)


def get_all_quizzes() -> list[QuizRecord]:
    with get_session() as session:
        return list(session.query(QuizRecord).order_by(QuizRecord.created_at.desc()).all())
