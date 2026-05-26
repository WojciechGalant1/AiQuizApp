from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import httpx
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .quiz_view import QuizView
from .results_view import ResultsView
from .upload_view import UploadView
from .history_view import HistoryView
from .preview_view import PreviewView

API_BASE = "http://127.0.0.1:8000"


# ---------------------------------------------------------------------------
# Worker wątek – generowanie quizu (żeby nie blokować GUI)
# ---------------------------------------------------------------------------

class GenerateWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, file_path: str, num_questions: int) -> None:
        super().__init__()
        self._file_path = file_path
        self._num_questions = num_questions

    def run(self) -> None:
        try:
            with open(self._file_path, "rb") as f:
                files = {"file": (Path(self._file_path).name, f)}
                data = {"num_questions": str(self._num_questions)}
                resp = httpx.post(
                    f"{API_BASE}/generate-quiz",
                    files=files,
                    data=data,
                    timeout=120.0,
                )
            if resp.status_code != 200:
                try:
                    detail = resp.json().get("detail", resp.text)
                except Exception:
                    detail = resp.text or f"HTTP {resp.status_code}"
                self.error.emit(f"Błąd serwera: {detail}")
                return
            self.finished.emit(resp.json())
        except httpx.ConnectError:
            self.error.emit(
                "Nie można połączyć się z serwerem.\n"
                "Upewnij się, że backend działa (uvicorn)."
            )
        except Exception as exc:
            self.error.emit(f"Błąd: {exc}")


# ---------------------------------------------------------------------------
# Worker wątek – sprawdzanie odpowiedzi przez backend
# ---------------------------------------------------------------------------

class CheckAnswersWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, quiz_id: int, answers: list[dict]) -> None:
        super().__init__()
        self._quiz_id = quiz_id
        self._answers = answers

    def run(self) -> None:
        try:
            payload = {
                "quiz_id": self._quiz_id,
                "answers": self._answers,
            }
            resp = httpx.post(
                f"{API_BASE}/check-answers",
                json=payload,
                timeout=30.0,
            )
            if resp.status_code != 200:
                try:
                    detail = resp.json().get("detail", resp.text)
                except Exception:
                    detail = resp.text or f"HTTP {resp.status_code}"
                self.error.emit(f"Błąd serwera: {detail}")
                return
            self.finished.emit(resp.json())
        except httpx.ConnectError:
            self.error.emit(
                "Nie można połączyć się z serwerem.\n"
                "Upewnij się, że backend działa (uvicorn)."
            )
        except Exception as exc:
            self.error.emit(f"Błąd: {exc}")


# ---------------------------------------------------------------------------
# Worker wątek – pobieranie historii
# ---------------------------------------------------------------------------

class FetchHistoryWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def run(self) -> None:
        try:
            resp = httpx.get(f"{API_BASE}/quizzes", timeout=10.0)
            if resp.status_code != 200:
                self.error.emit(f"Błąd: HTTP {resp.status_code}")
                return
            self.finished.emit(resp.json())
        except Exception as exc:
            self.error.emit(f"Błąd połączenia: {exc}")


# ---------------------------------------------------------------------------
# Worker wątek – pobieranie konkretnego quizu z historii
# ---------------------------------------------------------------------------

class FetchQuizWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, quiz_id: int) -> None:
        super().__init__()
        self._quiz_id = quiz_id

    def run(self) -> None:
        try:
            resp = httpx.get(f"{API_BASE}/quizzes/{self._quiz_id}", timeout=10.0)
            if resp.status_code != 200:
                self.error.emit(f"Błąd: HTTP {resp.status_code}")
                return
            self.finished.emit(resp.json())
        except Exception as exc:
            self.error.emit(f"Błąd połączenia: {exc}")


# ---------------------------------------------------------------------------
# Worker wątek – usuwanie quizu z historii
# ---------------------------------------------------------------------------

class DeleteQuizWorker(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, quiz_id: int) -> None:
        super().__init__()
        self._quiz_id = quiz_id

    def run(self) -> None:
        try:
            resp = httpx.delete(f"{API_BASE}/quizzes/{self._quiz_id}", timeout=10.0)
            if resp.status_code != 200:
                self.error.emit(f"Błąd: HTTP {resp.status_code}")
                return
            self.finished.emit()
        except Exception as exc:
            self.error.emit(f"Błąd połączenia: {exc}")


# ---------------------------------------------------------------------------
# Główne okno
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AI Quiz Generator")
        self.setMinimumSize(700, 550)
        self.resize(800, 620)

        self._current_questions: list[dict] = []
        self._current_title: str = ""
        self._current_quiz_id: int = -1

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        self._upload_view = UploadView()
        self._quiz_view = QuizView()
        self._results_view = ResultsView()
        self._history_view = HistoryView()
        self._preview_view = PreviewView()

        self._loading_widget = self._build_loading_widget()

        self._stack.addWidget(self._upload_view)     # 0
        self._stack.addWidget(self._loading_widget)  # 1
        self._stack.addWidget(self._quiz_view)       # 2
        self._stack.addWidget(self._results_view)    # 3
        self._stack.addWidget(self._history_view)    # 4
        self._stack.addWidget(self._preview_view)    # 5

        self._upload_view.quiz_requested.connect(self._on_generate)
        self._upload_view.history_requested.connect(self._on_history_requested)
        self._quiz_view.quiz_finished.connect(self._on_quiz_finished)
        self._results_view.back_to_home.connect(self._go_home)
        self._history_view.back_requested.connect(self._go_home)
        self._history_view.refresh_requested.connect(self._on_history_requested)
        self._history_view.quiz_selected.connect(self._on_history_quiz_selected)
        self._history_view.preview_requested.connect(self._on_preview_requested)
        self._history_view.delete_requested.connect(self._on_delete_requested)
        self._preview_view.back_requested.connect(self._go_history)

        self._fetch_intent = "solve"  # track what to do with fetched quiz

        self._apply_global_style()

    def _build_loading_widget(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._loading_label = QLabel("Generowanie quizu...\nTo może potrwać kilkanaście sekund.")
        self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._loading_label.setStyleSheet("font-size: 16px; color: #64748b;")
        layout.addWidget(self._loading_label)
        return w

    def _apply_global_style(self) -> None:
        self.setStyleSheet(
            "QMainWindow { background: #ffffff; }"
            "QWidget { font-family: 'Segoe UI', Arial, sans-serif; }"
        )

    # -- flow --

    def _on_generate(self, file_path: str, num_questions: int) -> None:
        self._loading_label.setText("Generowanie quizu...\nTo może potrwać kilkanaście sekund.")
        self._stack.setCurrentIndex(1)
        self._worker = GenerateWorker(file_path, num_questions)
        self._worker.finished.connect(self._on_quiz_ready)
        self._worker.error.connect(self._on_generate_error)
        self._worker.start()

    def _on_quiz_ready(self, data: dict) -> None:
        self._current_title = data.get("title", "Quiz")
        self._current_questions = data.get("questions", [])
        self._current_quiz_id = data.get("quiz_id", -1)
        self._quiz_view.load_quiz(self._current_title, self._current_questions)
        self._stack.setCurrentIndex(2)

    def _on_generate_error(self, msg: str) -> None:
        self._stack.setCurrentIndex(0)
        QMessageBox.critical(self, "Błąd", msg)

    def _on_quiz_finished(self, answers: list) -> None:
        self._loading_label.setText("Sprawdzanie odpowiedzi...")
        self._stack.setCurrentIndex(1)
        self._check_worker = CheckAnswersWorker(self._current_quiz_id, answers)
        self._check_worker.finished.connect(self._on_answers_checked)
        self._check_worker.error.connect(self._on_check_error)
        self._check_worker.start()

    def _on_answers_checked(self, data: dict) -> None:
        self._results_view.show_results(
            data["score"], data["total"], data["details"]
        )
        self._stack.setCurrentIndex(3)

    def _on_check_error(self, msg: str) -> None:
        self._stack.setCurrentIndex(2)  # wróć do quizu
        QMessageBox.critical(self, "Błąd sprawdzania odpowiedzi", msg)

    def _go_home(self) -> None:
        self._stack.setCurrentIndex(0)

    def _go_history(self) -> None:
        self._stack.setCurrentIndex(4)

    def _on_history_requested(self) -> None:
        self._loading_label.setText("Pobieranie historii quizów...")
        self._stack.setCurrentIndex(1)
        self._history_worker = FetchHistoryWorker()
        self._history_worker.finished.connect(self._on_history_ready)
        self._history_worker.error.connect(self._on_history_error)
        self._history_worker.start()

    def _on_history_ready(self, quizzes: list) -> None:
        self._history_view.show_quizzes(quizzes)
        self._stack.setCurrentIndex(4)

    def _on_history_error(self, msg: str) -> None:
        self._stack.setCurrentIndex(0)
        QMessageBox.critical(self, "Błąd historii", msg)

    def _on_history_quiz_selected(self, quiz_id: int) -> None:
        self._fetch_intent = "solve"
        self._start_quiz_fetch(quiz_id, "Pobieranie quizu do rozwiązania...")

    def _on_preview_requested(self, quiz_id: int) -> None:
        self._fetch_intent = "preview"
        self._start_quiz_fetch(quiz_id, "Pobieranie pytań do podglądu...")

    def _start_quiz_fetch(self, quiz_id: int, loading_msg: str) -> None:
        self._loading_label.setText(loading_msg)
        self._stack.setCurrentIndex(1)
        self._fetch_quiz_worker = FetchQuizWorker(quiz_id)
        self._fetch_quiz_worker.finished.connect(self._on_fetched_quiz_ready)
        self._fetch_quiz_worker.error.connect(self._on_fetch_quiz_error)
        self._fetch_quiz_worker.start()

    def _on_fetched_quiz_ready(self, data: dict) -> None:
        self._current_title = data.get("title", "Quiz z historii")
        self._current_questions = data.get("questions", [])
        self._current_quiz_id = data.get("id", -1)
        
        if self._fetch_intent == "preview":
            self._preview_view.load_preview(self._current_title, self._current_questions)
            self._stack.setCurrentIndex(5)
        else:
            self._quiz_view.load_quiz(self._current_title, self._current_questions)
            self._stack.setCurrentIndex(2)

    def _on_fetch_quiz_error(self, msg: str) -> None:
        self._stack.setCurrentIndex(4)
        QMessageBox.critical(self, "Błąd quizu", msg)

    def _on_delete_requested(self, quiz_id: int) -> None:
        self._loading_label.setText("Usuwanie quizu...")
        self._stack.setCurrentIndex(1)
        self._delete_worker = DeleteQuizWorker(quiz_id)
        self._delete_worker.finished.connect(self._on_delete_finished)
        self._delete_worker.error.connect(self._on_delete_error)
        self._delete_worker.start()

    def _on_delete_finished(self) -> None:
        # Po usunięciu po prostu odświeżamy historię
        self._on_history_requested()

    def _on_delete_error(self, msg: str) -> None:
        self._stack.setCurrentIndex(4)
        QMessageBox.critical(self, "Błąd usuwania", msg)


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
