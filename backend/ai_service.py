from __future__ import annotations

import functools
import json
import logging
import os
import textwrap
import time
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq, RateLimitError, AuthenticationError, APIError
from pydantic import ValidationError

from paths import get_env_path
from .models import QuestionSchema

load_dotenv(get_env_path())

log = logging.getLogger(__name__)

CHUNK_SIZE = 1500
OVERLAP = 150
MAX_RETRIES = 5
BASE_DELAY = 10  # seconds
MODEL_NAME = "llama-3.3-70b-versatile"

@functools.lru_cache(maxsize=1)
def _get_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "Brak klucza GROQ_API_KEY. "
            "Ustaw go w pliku .env obok requirements.txt.\n"
            "Klucz uzyskasz za darmo: https://console.groq.com/keys"
        )
    return Groq(api_key=api_key)


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def split_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        start = end - overlap
    return chunks


# ---------------------------------------------------------------------------
# Wywołanie API z retry + exponential backoff
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = textwrap.dedent("""\
    Jesteś ekspertem od tworzenia quizów edukacyjnych.
    Tworzysz pytania jednokrotnego wyboru na podstawie podanego tekstu.
    Odpowiadasz WYŁĄCZNIE poprawnym JSON-em (bez markdown, bez ```json).
""")


def _is_request_too_large(exc: RateLimitError | APIError) -> bool:
    """413 / 'Request too large' — ponawianie nie pomoże."""
    status = getattr(getattr(exc, "response", None), "status_code", 0)
    if status == 413:
        return True
    body = getattr(exc, "body", None) or {}
    err = body.get("error", {}) if isinstance(body, dict) else {}
    msg = err.get("message", "") if isinstance(err, dict) else str(err)
    return "request too large" in msg.lower()


def _call_with_retry(client: Groq, prompt: str) -> str:
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                temperature=0.7,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
            return (response.choices[0].message.content or "").strip()
        except RateLimitError as exc:
            if _is_request_too_large(exc):
                raise RuntimeError(
                    "Tekst w jednym fragmencie jest zbyt długi dla modelu AI.\n"
                    "Spróbuj wgrać krótszy dokument."
                )
            if attempt < MAX_RETRIES - 1:
                delay = BASE_DELAY * (2 ** attempt)
                log.info("Rate limit – ponawiam za %ds (próba %d/%d)", delay, attempt + 2, MAX_RETRIES)
                time.sleep(delay)
                continue
            raise RuntimeError(
                f"Przekroczono limit API Groq po {MAX_RETRIES} próbach.\n"
                "Odczekaj minutę i spróbuj ponownie."
            )
        except AuthenticationError:
            raise RuntimeError(
                "Nieprawidłowy klucz Groq API. Sprawdź plik .env.\n"
                "Klucz uzyskasz: https://console.groq.com/keys"
            )
        except APIError as exc:
            if _is_request_too_large(exc):
                raise RuntimeError(
                    "Tekst w jednym fragmencie jest zbyt długi dla modelu AI.\n"
                    "Spróbuj wgrać krótszy dokument."
                )
            raise RuntimeError(f"Błąd API Groq: {exc.message}")

    return ""


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

def _build_prompt(chunk: str, num_questions: int) -> str:
    return textwrap.dedent(f"""\
        Na podstawie poniższego tekstu wygeneruj {num_questions} pytań testowych.

        Zasady:
        - pytania jednokrotnego wyboru
        - 4 odpowiedzi oznaczone A, B, C, D
        - tylko jedna poprawna
        - dodaj krótkie wyjaśnienie do każdego pytania
        - odpowiedz WYŁĄCZNIE jako tablica JSON w formacie:
        [
          {{
            "question": "treść pytania",
            "answers": ["A) ...", "B) ...", "C) ...", "D) ..."],
            "correct": "A",
            "explanation": "krótkie wyjaśnienie"
          }}
        ]

        TEKST:
        {chunk}
    """)


# ---------------------------------------------------------------------------
# Generowanie quizu
# ---------------------------------------------------------------------------

def generate_questions(text: str, num_questions: int = 5) -> list[dict]:
    """Generuje pytania quizowe z tekstu. Dzieli tekst na chunki jeśli potrzeba."""
    client = _get_client()
    chunks = split_text(text)

    if len(chunks) == 1:
        q_per_chunk = [num_questions]
    else:
        base = num_questions // len(chunks)
        remainder = num_questions % len(chunks)
        q_per_chunk = [base + (1 if i < remainder else 0) for i in range(len(chunks))]

    all_questions: list[dict] = []

    for i, (chunk, n) in enumerate(zip(chunks, q_per_chunk)):
        if n == 0:
            continue

        if i > 0:
            time.sleep(4)

        raw = _call_with_retry(client, _build_prompt(chunk, n))
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            questions = json.loads(raw)
        except json.JSONDecodeError:
            log.warning("AI zwróciło niepoprawny JSON dla chunk %d – pomijam", i)
            continue

        for raw_q in questions:
            try:
                QuestionSchema(**raw_q)
                all_questions.append(raw_q)
            except (ValidationError, TypeError):
                log.warning("Pomijam niepoprawne pytanie z chunk %d: %s", i, raw_q)

    return all_questions[:num_questions]
