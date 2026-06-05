from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path

import pdfplumber
from contextlib import asynccontextmanager

log = logging.getLogger(__name__)
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

from .ai_service import generate_questions
from .db import delete_quiz, get_all_quizzes, get_quiz, init_db, save_quiz, update_score
from .models import (
    CheckAnswersRequest,
    CheckAnswersResponse,
    GenerateQuizResponse,
    QuestionSchema,
    QuizHistoryItem,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="AI Quiz Generator", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Limity
# ---------------------------------------------------------------------------

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_PDF_PAGES = 50
MAX_TEXT_LENGTH = 100_000  # znaków


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_text_from_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return path.read_text(encoding="utf-8")
    if suffix == ".pdf":
        text_parts: list[str] = []
        with pdfplumber.open(path) as pdf:
            if len(pdf.pages) > MAX_PDF_PAGES:
                raise ValueError(
                    f"Plik PDF ma {len(pdf.pages)} stron (limit: {MAX_PDF_PAGES}). "
                    "Skróć dokument i spróbuj ponownie."
                )
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)
    raise ValueError(f"Nieobsługiwany format pliku: {suffix}")


# ---------------------------------------------------------------------------
# Endpointy
# ---------------------------------------------------------------------------

@app.post("/generate-quiz", response_model=GenerateQuizResponse)
def generate_quiz(
    file: UploadFile = File(...),
    num_questions: int = Form(default=5),
):
    if not file.filename:
        raise HTTPException(400, "Brak nazwy pliku")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".txt", ".pdf"):
        raise HTTPException(400, "Obsługiwane formaty: .txt, .pdf")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = file.file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                400,
                f"Plik jest za duży ({len(content) / 1024 / 1024:.1f} MB). "
                f"Maksymalny rozmiar: {MAX_FILE_SIZE // 1024 // 1024} MB.",
            )
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        text = extract_text_from_file(tmp_path)
    except ValueError as exc:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(400, str(exc))
    finally:
        tmp_path.unlink(missing_ok=True)

    if not text.strip():
        raise HTTPException(400, "Nie udało się wyekstrahować tekstu z pliku")

    if len(text) > MAX_TEXT_LENGTH:
        raise HTTPException(
            400,
            f"Wyekstrahowany tekst jest zbyt długi ({len(text):,} znaków). "
            f"Limit: {MAX_TEXT_LENGTH:,} znaków. Skróć dokument i spróbuj ponownie.",
        )

    try:
        questions_raw = generate_questions(text, num_questions)
    except RuntimeError as exc:
        raise HTTPException(502, str(exc))
    except Exception as exc:
        raise HTTPException(500, f"Nieoczekiwany błąd AI: {exc}")

    if not questions_raw:
        raise HTTPException(500, "AI nie wygenerowało pytań – spróbuj ponownie")

    if len(questions_raw) < num_questions:
        log.warning(
            "AI wygenerowało %d/%d poprawnych pytań dla pliku '%s'",
            len(questions_raw), num_questions, file.filename,
        )

    questions = [QuestionSchema(**q) for q in questions_raw]
    title = f"Quiz: {file.filename}"

    quiz_id = save_quiz(
        title=title,
        source_filename=file.filename,
        questions=[q.model_dump() for q in questions],
    )

    return GenerateQuizResponse(
        quiz_id=quiz_id,
        title=title,
        questions=questions,
    )


@app.post("/check-answers", response_model=CheckAnswersResponse)
def check_answers(payload: CheckAnswersRequest):
    record = get_quiz(payload.quiz_id)
    if not record:
        raise HTTPException(404, "Quiz nie znaleziony")

    questions = json.loads(record.questions_json)
    details: list[dict] = []
    score = 0

    for answer in payload.answers:
        idx = answer.question_index
        if idx < 0 or idx >= len(questions):
            continue
        q = questions[idx]
        is_correct = answer.selected == q["correct"]
        if is_correct:
            score += 1
        details.append({
            "question_index": idx,
            "question": q["question"],
            "selected": answer.selected,
            "correct": q["correct"],
            "is_correct": is_correct,
            "explanation": q.get("explanation", ""),
        })

    total = len(questions)
    percent = round((score / total) * 100, 1) if total else 0.0

    update_score(payload.quiz_id, score, total)

    return CheckAnswersResponse(
        score=score,
        total=total,
        percent=percent,
        details=details,
    )


@app.get("/quizzes", response_model=list[QuizHistoryItem])
def list_quizzes():
    return get_all_quizzes()


@app.get("/quizzes/{quiz_id}")
def get_quiz_detail(quiz_id: int):
    record = get_quiz(quiz_id)
    if not record:
        raise HTTPException(404, "Quiz nie znaleziony")
    return {
        "id": record.id,
        "title": record.title,
        "source_filename": record.source_filename,
        "questions": json.loads(record.questions_json),
        "score": record.score,
        "total": record.total,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


@app.delete("/quizzes/{quiz_id}")
def delete_quiz_endpoint(quiz_id: int):
    success = delete_quiz(quiz_id)
    if not success:
        raise HTTPException(404, "Quiz nie znaleziony")
    return {"status": "ok"}
