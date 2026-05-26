from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.models import Base, QuizRecord


SAMPLE_QUESTIONS = [
    {
        "question": "Co to jest Python?",
        "answers": ["A) Język programowania", "B) Wąż", "C) Gra", "D) System operacyjny"],
        "correct": "A",
        "explanation": "Python to język programowania.",
    },
    {
        "question": "Ile wynosi 2+2?",
        "answers": ["A) 3", "B) 4", "C) 5", "D) 6"],
        "correct": "B",
        "explanation": "2+2=4",
    },
]


@pytest.fixture()
def in_memory_db(monkeypatch):
    """Replaces the db module's engine/session with an in-memory SQLite DB."""
    import backend.db as db_mod

    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)

    monkeypatch.setattr(db_mod, "engine", engine)
    monkeypatch.setattr(db_mod, "SessionLocal", session_factory)

    return engine


@pytest.fixture()
def seeded_db(in_memory_db):
    """In-memory DB pre-loaded with one quiz record."""
    from backend.db import save_quiz, update_score

    quiz_id = save_quiz("Test Quiz", "test.txt", SAMPLE_QUESTIONS)
    return quiz_id
