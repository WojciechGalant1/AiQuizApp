from __future__ import annotations

import json

from backend.db import (
    delete_quiz,
    get_all_quizzes,
    get_quiz,
    save_quiz,
    update_score,
)
from tests.conftest import SAMPLE_QUESTIONS


class TestSaveQuiz:
    def test_returns_positive_id(self, in_memory_db):
        qid = save_quiz("Quiz 1", "doc.txt", SAMPLE_QUESTIONS)
        assert isinstance(qid, int)
        assert qid > 0

    def test_persists_data(self, in_memory_db):
        qid = save_quiz("Quiz 1", "doc.txt", SAMPLE_QUESTIONS)
        record = get_quiz(qid)
        assert record is not None
        assert record.title == "Quiz 1"
        assert record.source_filename == "doc.txt"
        assert json.loads(record.questions_json) == SAMPLE_QUESTIONS

    def test_multiple_saves_increment_id(self, in_memory_db):
        id1 = save_quiz("Q1", "a.txt", SAMPLE_QUESTIONS)
        id2 = save_quiz("Q2", "b.txt", SAMPLE_QUESTIONS)
        assert id2 > id1


class TestGetQuiz:
    def test_existing_quiz(self, seeded_db):
        record = get_quiz(seeded_db)
        assert record is not None
        assert record.id == seeded_db
        assert record.title == "Test Quiz"

    def test_nonexistent_quiz(self, in_memory_db):
        assert get_quiz(9999) is None


class TestUpdateScore:
    def test_updates_score(self, seeded_db):
        update_score(seeded_db, 1.0, 2)
        record = get_quiz(seeded_db)
        assert record is not None
        assert record.score == 1.0
        assert record.total == 2

    def test_nonexistent_quiz_no_error(self, in_memory_db):
        update_score(9999, 5.0, 10)


class TestGetAllQuizzes:
    def test_empty_db(self, in_memory_db):
        assert get_all_quizzes() == []

    def test_returns_all(self, in_memory_db):
        save_quiz("Q1", "a.txt", SAMPLE_QUESTIONS)
        save_quiz("Q2", "b.txt", SAMPLE_QUESTIONS)
        quizzes = get_all_quizzes()
        assert len(quizzes) == 2

    def test_ordered_by_date_desc(self, in_memory_db):
        save_quiz("First", "a.txt", SAMPLE_QUESTIONS)
        save_quiz("Second", "b.txt", SAMPLE_QUESTIONS)
        quizzes = get_all_quizzes()
        assert quizzes[0].title == "Second"
        assert quizzes[1].title == "First"


class TestDeleteQuiz:
    def test_delete_existing(self, seeded_db):
        assert delete_quiz(seeded_db) is True
        assert get_quiz(seeded_db) is None

    def test_delete_nonexistent(self, in_memory_db):
        assert delete_quiz(9999) is False

    def test_delete_does_not_affect_others(self, in_memory_db):
        id1 = save_quiz("Q1", "a.txt", SAMPLE_QUESTIONS)
        id2 = save_quiz("Q2", "b.txt", SAMPLE_QUESTIONS)
        delete_quiz(id1)
        assert get_quiz(id2) is not None
