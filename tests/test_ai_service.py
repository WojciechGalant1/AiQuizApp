from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from groq import RateLimitError, AuthenticationError, APIError

from backend.ai_service import (
    _call_with_retry,
    _build_prompt,
    generate_questions,
    split_text,
)
from tests.conftest import SAMPLE_QUESTIONS


# ---------------------------------------------------------------------------
# split_text
# ---------------------------------------------------------------------------

class TestSplitText:
    def test_short_text_single_chunk(self):
        text = "word " * 100
        chunks = split_text(text, chunk_size=200, overlap=50)
        assert len(chunks) == 1

    def test_long_text_multiple_chunks(self):
        text = "word " * 500
        chunks = split_text(text, chunk_size=200, overlap=50)
        assert len(chunks) > 1

    def test_overlap_creates_shared_words(self):
        text = " ".join(f"w{i}" for i in range(300))
        chunks = split_text(text, chunk_size=200, overlap=50)
        first_end_words = set(chunks[0].split()[-50:])
        second_start_words = set(chunks[1].split()[:50])
        assert len(first_end_words & second_start_words) == 50

    def test_empty_text(self):
        assert split_text("") == []


# ---------------------------------------------------------------------------
# _build_prompt
# ---------------------------------------------------------------------------

class TestBuildPrompt:
    def test_contains_chunk_text(self):
        prompt = _build_prompt("Testowy tekst o Pythonie", 3)
        assert "Testowy tekst o Pythonie" in prompt

    def test_contains_num_questions(self):
        prompt = _build_prompt("chunk", 7)
        assert "7" in prompt


# ---------------------------------------------------------------------------
# _call_with_retry
# ---------------------------------------------------------------------------

def _make_mock_response(content: str) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


class TestCallWithRetry:
    def test_successful_call(self):
        client = MagicMock()
        client.chat.completions.create.return_value = _make_mock_response("hello")
        result = _call_with_retry(client, "prompt")
        assert result == "hello"

    def test_auth_error_raises_runtime(self):
        client = MagicMock()
        err = AuthenticationError(
            message="bad key",
            response=MagicMock(status_code=401),
            body=None,
        )
        client.chat.completions.create.side_effect = err
        with pytest.raises(RuntimeError, match="Nieprawidłowy klucz"):
            _call_with_retry(client, "prompt")

    @patch("backend.ai_service.time.sleep")
    def test_rate_limit_retries_then_raises(self, mock_sleep):
        client = MagicMock()
        err = RateLimitError(
            message="rate limited",
            response=MagicMock(status_code=429),
            body=None,
        )
        client.chat.completions.create.side_effect = err
        with pytest.raises(RuntimeError, match="Przekroczono limit"):
            _call_with_retry(client, "prompt")
        assert mock_sleep.call_count > 0

    @patch("backend.ai_service.time.sleep")
    def test_rate_limit_recovers(self, mock_sleep):
        client = MagicMock()
        err = RateLimitError(
            message="rate limited",
            response=MagicMock(status_code=429),
            body=None,
        )
        client.chat.completions.create.side_effect = [
            err,
            _make_mock_response("ok"),
        ]
        result = _call_with_retry(client, "prompt")
        assert result == "ok"


# ---------------------------------------------------------------------------
# generate_questions
# ---------------------------------------------------------------------------

def _mock_ai_response(questions: list[dict]) -> str:
    return json.dumps(questions, ensure_ascii=False)


class TestGenerateQuestions:
    @patch("backend.ai_service._get_client")
    @patch("backend.ai_service._call_with_retry")
    def test_returns_valid_questions(self, mock_call, mock_client):
        mock_client.return_value = MagicMock()
        mock_call.return_value = _mock_ai_response(SAMPLE_QUESTIONS)

        result = generate_questions("Tekst o programowaniu", num_questions=2)
        assert len(result) == 2
        assert result[0]["question"] == SAMPLE_QUESTIONS[0]["question"]

    @patch("backend.ai_service._get_client")
    @patch("backend.ai_service._call_with_retry")
    def test_filters_invalid_questions(self, mock_call, mock_client):
        mock_client.return_value = MagicMock()
        valid = SAMPLE_QUESTIONS[0]
        invalid = {"question": "Bad", "answers": []}  # missing 'correct'
        mock_call.return_value = _mock_ai_response([valid, invalid])

        result = generate_questions("Tekst", num_questions=5)
        assert len(result) == 1
        assert result[0]["question"] == valid["question"]

    @patch("backend.ai_service._get_client")
    @patch("backend.ai_service._call_with_retry")
    def test_handles_invalid_json(self, mock_call, mock_client):
        mock_client.return_value = MagicMock()
        mock_call.return_value = "not valid json {{{}"

        result = generate_questions("Tekst", num_questions=3)
        assert result == []

    @patch("backend.ai_service._get_client")
    @patch("backend.ai_service._call_with_retry")
    def test_strips_markdown_fences(self, mock_call, mock_client):
        mock_client.return_value = MagicMock()
        raw = "```json\n" + _mock_ai_response(SAMPLE_QUESTIONS) + "\n```"
        mock_call.return_value = raw

        result = generate_questions("Tekst", num_questions=2)
        assert len(result) == 2

    @patch("backend.ai_service._get_client")
    @patch("backend.ai_service._call_with_retry")
    def test_limits_to_num_questions(self, mock_call, mock_client):
        mock_client.return_value = MagicMock()
        many_qs = SAMPLE_QUESTIONS * 5
        mock_call.return_value = _mock_ai_response(many_qs)

        result = generate_questions("Tekst", num_questions=3)
        assert len(result) == 3

    @patch("backend.ai_service._get_client")
    def test_missing_api_key_raises(self, mock_client):
        from backend.ai_service import _get_client
        _get_client.cache_clear()
        mock_client.side_effect = RuntimeError("Brak klucza")
        with pytest.raises(RuntimeError, match="Brak klucza"):
            generate_questions("Tekst", num_questions=1)
