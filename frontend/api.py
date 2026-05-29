"""Klient HTTP do komunikacji z backendem FastAPI.

Każda funkcja zwraca sparsowany JSON lub rzuca ``RuntimeError``
z czytelnym komunikatem (parsowanym z odpowiedzi serwera)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

API_BASE = "http://127.0.0.1:8000"


def _parse(resp: httpx.Response) -> Any:
    if resp.status_code != 200:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text or f"HTTP {resp.status_code}"
        raise RuntimeError(f"Błąd serwera: {detail}")
    return resp.json()


def generate_quiz(file_path: str, num_questions: int) -> dict:
    with open(file_path, "rb") as f:
        files = {"file": (Path(file_path).name, f)}
        data = {"num_questions": str(num_questions)}
        resp = httpx.post(
            f"{API_BASE}/generate-quiz",
            files=files,
            data=data,
            timeout=120.0,
        )
    return _parse(resp)


def check_answers(quiz_id: int, answers: list[dict]) -> dict:
    payload = {"quiz_id": quiz_id, "answers": answers}
    resp = httpx.post(f"{API_BASE}/check-answers", json=payload, timeout=30.0)
    return _parse(resp)


def fetch_history() -> list[dict]:
    resp = httpx.get(f"{API_BASE}/quizzes", timeout=10.0)
    return _parse(resp)


def fetch_quiz(quiz_id: int) -> dict:
    resp = httpx.get(f"{API_BASE}/quizzes/{quiz_id}", timeout=10.0)
    return _parse(resp)


def delete_quiz(quiz_id: int) -> None:
    resp = httpx.delete(f"{API_BASE}/quizzes/{quiz_id}", timeout=10.0)
    _parse(resp)
