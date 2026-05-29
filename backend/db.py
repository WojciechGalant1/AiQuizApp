from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from paths import get_data_dir
from .models import Base, QuizRecord

log = logging.getLogger(__name__)

DB_PATH = get_data_dir() / "quizzes.db"

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


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
        try:
            record = QuizRecord(
                title=title,
                source_filename=source_filename,
                questions_json=json.dumps(questions, ensure_ascii=False),
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return record.id
        except SQLAlchemyError:
            session.rollback()
            log.exception("Błąd zapisu quizu '%s'", title)
            raise


def update_score(quiz_id: int, score: float, total: int) -> None:
    with get_session() as session:
        try:
            record = session.get(QuizRecord, quiz_id)
            if record:
                record.score = score
                record.total = total
                session.commit()
        except SQLAlchemyError:
            session.rollback()
            log.exception("Błąd aktualizacji wyniku quizu %d", quiz_id)
            raise


def get_quiz(quiz_id: int) -> QuizRecord | None:
    with get_session() as session:
        try:
            record = session.get(QuizRecord, quiz_id)
            if record:
                session.expunge(record)
            return record
        except SQLAlchemyError:
            log.exception("Błąd odczytu quizu %d", quiz_id)
            raise


def get_all_quizzes() -> list[QuizRecord]:
    with get_session() as session:
        try:
            records = list(session.query(QuizRecord).order_by(QuizRecord.created_at.desc()).all())
            session.expunge_all()
            return records
        except SQLAlchemyError:
            log.exception("Błąd pobierania listy quizów")
            raise


def delete_quiz(quiz_id: int) -> bool:
    with get_session() as session:
        try:
            record = session.get(QuizRecord, quiz_id)
            if record:
                session.delete(record)
                session.commit()
                return True
            return False
        except SQLAlchemyError:
            session.rollback()
            log.exception("Błąd usuwania quizu %d", quiz_id)
            raise
