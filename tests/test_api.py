from __future__ import annotations

import io
import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from tests.conftest import SAMPLE_QUESTIONS


@pytest.fixture()
def client(in_memory_db):
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# POST /generate-quiz
# ---------------------------------------------------------------------------

class TestGenerateQuiz:
    @patch("backend.main.generate_questions")
    def test_success(self, mock_gen, client):
        mock_gen.return_value = SAMPLE_QUESTIONS
        file = io.BytesIO(b"Testowy tekst o programowaniu w Pythonie")
        resp = client.post(
            "/generate-quiz",
            files={"file": ("test.txt", file, "text/plain")},
            data={"num_questions": "2"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Quiz: test.txt"
        assert len(data["questions"]) == 2
        assert data["quiz_id"] > 0

    def test_unsupported_format(self, client):
        file = io.BytesIO(b"content")
        resp = client.post(
            "/generate-quiz",
            files={"file": ("doc.docx", file, "application/octet-stream")},
        )
        assert resp.status_code == 400

    @patch("backend.main.generate_questions")
    def test_empty_text(self, mock_gen, client):
        file = io.BytesIO(b"   ")
        resp = client.post(
            "/generate-quiz",
            files={"file": ("empty.txt", file, "text/plain")},
        )
        assert resp.status_code == 400

    @patch("backend.main.generate_questions")
    def test_ai_runtime_error(self, mock_gen, client):
        mock_gen.side_effect = RuntimeError("API down")
        file = io.BytesIO(b"Real content here")
        resp = client.post(
            "/generate-quiz",
            files={"file": ("test.txt", file, "text/plain")},
        )
        assert resp.status_code == 502

    @patch("backend.main.generate_questions")
    def test_ai_returns_empty(self, mock_gen, client):
        mock_gen.return_value = []
        file = io.BytesIO(b"Some real content")
        resp = client.post(
            "/generate-quiz",
            files={"file": ("test.txt", file, "text/plain")},
        )
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# POST /check-answers
# ---------------------------------------------------------------------------

class TestCheckAnswers:
    @patch("backend.main.generate_questions")
    def test_all_correct(self, mock_gen, client):
        mock_gen.return_value = SAMPLE_QUESTIONS
        file = io.BytesIO(b"Tekst o programowaniu")
        gen_resp = client.post(
            "/generate-quiz",
            files={"file": ("test.txt", file, "text/plain")},
            data={"num_questions": "2"},
        )
        quiz_id = gen_resp.json()["quiz_id"]

        resp = client.post("/check-answers", json={
            "quiz_id": quiz_id,
            "answers": [
                {"question_index": 0, "selected": "A"},
                {"question_index": 1, "selected": "B"},
            ],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["score"] == 2
        assert data["total"] == 2
        assert data["percent"] == 100.0

    @patch("backend.main.generate_questions")
    def test_partial_score(self, mock_gen, client):
        mock_gen.return_value = SAMPLE_QUESTIONS
        file = io.BytesIO(b"Content")
        gen_resp = client.post(
            "/generate-quiz",
            files={"file": ("test.txt", file, "text/plain")},
            data={"num_questions": "2"},
        )
        quiz_id = gen_resp.json()["quiz_id"]

        resp = client.post("/check-answers", json={
            "quiz_id": quiz_id,
            "answers": [
                {"question_index": 0, "selected": "A"},
                {"question_index": 1, "selected": "C"},
            ],
        })
        data = resp.json()
        assert data["score"] == 1
        assert data["total"] == 2

    def test_quiz_not_found(self, client):
        resp = client.post("/check-answers", json={
            "quiz_id": 9999,
            "answers": [{"question_index": 0, "selected": "A"}],
        })
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /quizzes
# ---------------------------------------------------------------------------

class TestListQuizzes:
    def test_empty_list(self, client):
        resp = client.get("/quizzes")
        assert resp.status_code == 200
        assert resp.json() == []

    @patch("backend.main.generate_questions")
    def test_lists_created_quizzes(self, mock_gen, client):
        mock_gen.return_value = SAMPLE_QUESTIONS
        file = io.BytesIO(b"Content")
        client.post(
            "/generate-quiz",
            files={"file": ("test.txt", file, "text/plain")},
        )
        resp = client.get("/quizzes")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "Quiz: test.txt"


# ---------------------------------------------------------------------------
# GET /quizzes/{quiz_id}
# ---------------------------------------------------------------------------

class TestGetQuizDetail:
    @patch("backend.main.generate_questions")
    def test_existing(self, mock_gen, client):
        mock_gen.return_value = SAMPLE_QUESTIONS
        file = io.BytesIO(b"Content")
        gen_resp = client.post(
            "/generate-quiz",
            files={"file": ("test.txt", file, "text/plain")},
        )
        quiz_id = gen_resp.json()["quiz_id"]

        resp = client.get(f"/quizzes/{quiz_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == quiz_id
        assert len(data["questions"]) == 2

    def test_not_found(self, client):
        resp = client.get("/quizzes/9999")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /quizzes/{quiz_id}
# ---------------------------------------------------------------------------

class TestDeleteQuiz:
    @patch("backend.main.generate_questions")
    def test_delete_existing(self, mock_gen, client):
        mock_gen.return_value = SAMPLE_QUESTIONS
        file = io.BytesIO(b"Content")
        gen_resp = client.post(
            "/generate-quiz",
            files={"file": ("test.txt", file, "text/plain")},
        )
        quiz_id = gen_resp.json()["quiz_id"]

        resp = client.delete(f"/quizzes/{quiz_id}")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

        resp = client.get(f"/quizzes/{quiz_id}")
        assert resp.status_code == 404

    def test_delete_not_found(self, client):
        resp = client.delete("/quizzes/9999")
        assert resp.status_code == 404
