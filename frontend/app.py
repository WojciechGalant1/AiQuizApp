from __future__ import annotations

import sys
from enum import IntEnum
from typing import Any, Callable

import httpx
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from . import api
from .history_view import HistoryView
from .preview_view import PreviewView
from .quiz_view import QuizView
from .results_view import ResultsView
from .upload_view import UploadView


# ---------------------------------------------------------------------------
# Generyczny worker – uruchamia dowolne wywołanie API w osobnym wątku
# ---------------------------------------------------------------------------


class HttpWorker(QThread):
    """Wywołuje funkcję synchroniczną w wątku i emituje wynik lub błąd."""

    result_ready = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self) -> None:
        try:
            result = self._fn(*self._args, **self._kwargs)
            self.result_ready.emit(result)
        except httpx.ConnectError:
            self.error.emit(
                "Nie można połączyć się z serwerem.\n"
                "Upewnij się, że backend działa (uvicorn)."
            )
        except Exception as exc:
            self.error.emit(str(exc))


# ---------------------------------------------------------------------------
# Główne okno
# ---------------------------------------------------------------------------


class Page(IntEnum):
    UPLOAD = 0
    LOADING = 1
    QUIZ = 2
    RESULTS = 3
    HISTORY = 4
    PREVIEW = 5


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AI Quiz Generator")
        self.setMinimumSize(700, 550)
        self.resize(800, 620)

        self._current_questions: list[dict] = []
        self._current_title: str = ""
        self._current_quiz_id: int = -1
        self._active_worker: QThread | None = None

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        self._upload_view = UploadView()
        self._quiz_view = QuizView()
        self._results_view = ResultsView()
        self._history_view = HistoryView()
        self._preview_view = PreviewView()

        self._stack.addWidget(self._upload_view)              # Page.UPLOAD
        self._stack.addWidget(self._build_loading_widget())   # Page.LOADING
        self._stack.addWidget(self._quiz_view)                # Page.QUIZ
        self._stack.addWidget(self._results_view)             # Page.RESULTS
        self._stack.addWidget(self._history_view)             # Page.HISTORY
        self._stack.addWidget(self._preview_view)             # Page.PREVIEW

        self._upload_view.quiz_requested.connect(self._on_generate)
        self._upload_view.history_requested.connect(self._on_history_requested)
        self._quiz_view.quiz_finished.connect(self._on_quiz_finished)
        self._results_view.back_to_home.connect(
            lambda: self._stack.setCurrentIndex(Page.UPLOAD)
        )
        self._history_view.back_requested.connect(
            lambda: self._stack.setCurrentIndex(Page.UPLOAD)
        )
        self._history_view.refresh_requested.connect(self._on_history_requested)
        self._history_view.quiz_selected.connect(self._on_history_quiz_selected)
        self._history_view.preview_requested.connect(self._on_preview_requested)
        self._history_view.delete_requested.connect(self._on_delete_requested)
        self._preview_view.back_requested.connect(
            lambda: self._stack.setCurrentIndex(Page.HISTORY)
        )

        self._apply_global_style()

    def _build_loading_widget(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)

        self._loading_label = QLabel(
            "Generowanie quizu...\nTo może potrwać kilkanaście sekund."
        )
        self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._loading_label.setStyleSheet("font-size: 16px; color: #64748b;")
        layout.addWidget(self._loading_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedWidth(320)
        self._progress_bar.setFixedHeight(6)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setStyleSheet(
            "QProgressBar { background: #e2e8f0; border: none; border-radius: 3px; }"
            "QProgressBar::chunk { background: #2563eb; border-radius: 3px; }"
        )
        layout.addWidget(self._progress_bar, alignment=Qt.AlignmentFlag.AlignCenter)

        return w

    def _apply_global_style(self) -> None:
        self.setStyleSheet(
            "QMainWindow { background: #ffffff; }"
            "QWidget { font-family: 'Segoe UI', Arial, sans-serif; }"
        )

    # ------------------------------------------------------------------
    # Cykl życia workera i postępu
    # ------------------------------------------------------------------

    def _stop_active_worker(self) -> None:
        w = self._active_worker
        if w is not None and w.isRunning():
            w.quit()
            w.wait(5000)
        self._active_worker = None

    def closeEvent(self, event: QCloseEvent) -> None:
        self._stop_active_worker()
        super().closeEvent(event)

    def _stop_progress(self) -> None:
        self._progress_bar.setRange(0, 1)
        self._progress_bar.setValue(0)

    # ------------------------------------------------------------------
    # Generyczny runner operacji w tle
    # ------------------------------------------------------------------

    def _run_operation(
        self,
        fn: Callable[..., Any],
        *args: Any,
        loading_msg: str,
        on_success: Callable[..., None],
        error_title: str,
        error_fallback: Page,
    ) -> None:
        """Pokazuje ekran ładowania i uruchamia ``fn(*args)`` w wątku.

        Po sukcesie wynik trafia do ``on_success``, po błędzie zostaje
        wyświetlone okno z ``error_title`` i nastąpi powrót na ``error_fallback``."""
        self._stop_active_worker()
        self._loading_label.setText(loading_msg)
        self._stack.setCurrentIndex(Page.LOADING)
        self._progress_bar.setRange(0, 0)

        worker = HttpWorker(fn, *args)
        worker.result_ready.connect(on_success)
        worker.error.connect(
            lambda msg, t=error_title, p=error_fallback: self._handle_error(t, msg, p)
        )
        self._active_worker = worker
        worker.start()

    def _handle_error(self, title: str, msg: str, fallback: Page) -> None:
        self._stop_progress()
        self._stack.setCurrentIndex(fallback)
        QMessageBox.critical(self, title, msg)

    # ------------------------------------------------------------------
    # Generowanie nowego quizu
    # ------------------------------------------------------------------

    def _on_generate(self, file_path: str, num_questions: int) -> None:
        self._run_operation(
            api.generate_quiz, file_path, num_questions,
            loading_msg="Generowanie quizu...\nTo może potrwać kilkanaście sekund.",
            on_success=self._on_quiz_ready,
            error_title="Błąd",
            error_fallback=Page.UPLOAD,
        )

    def _on_quiz_ready(self, data: dict) -> None:
        self._stop_progress()
        self._current_title = data.get("title", "Quiz")
        self._current_questions = data.get("questions", [])
        self._current_quiz_id = data.get("quiz_id", -1)
        self._quiz_view.load_quiz(self._current_title, self._current_questions)
        self._stack.setCurrentIndex(Page.QUIZ)

    # ------------------------------------------------------------------
    # Sprawdzanie odpowiedzi
    # ------------------------------------------------------------------

    def _on_quiz_finished(self, answers: list) -> None:
        self._run_operation(
            api.check_answers, self._current_quiz_id, answers,
            loading_msg="Sprawdzanie odpowiedzi...",
            on_success=self._on_answers_checked,
            error_title="Błąd sprawdzania odpowiedzi",
            error_fallback=Page.QUIZ,
        )

    def _on_answers_checked(self, data: dict) -> None:
        self._stop_progress()
        self._results_view.show_results(
            data["score"], data["total"], data["details"]
        )
        self._stack.setCurrentIndex(Page.RESULTS)

    # ------------------------------------------------------------------
    # Historia
    # ------------------------------------------------------------------

    def _on_history_requested(self) -> None:
        self._run_operation(
            api.fetch_history,
            loading_msg="Pobieranie historii quizów...",
            on_success=self._on_history_ready,
            error_title="Błąd historii",
            error_fallback=Page.UPLOAD,
        )

    def _on_history_ready(self, quizzes: list) -> None:
        self._stop_progress()
        self._history_view.show_quizzes(quizzes)
        self._stack.setCurrentIndex(Page.HISTORY)

    # ------------------------------------------------------------------
    # Pobieranie quizu z historii – rozwiązywanie lub podgląd
    # ------------------------------------------------------------------

    def _on_history_quiz_selected(self, quiz_id: int) -> None:
        self._fetch_quiz_from_history(
            quiz_id,
            loading_msg="Pobieranie quizu do rozwiązania...",
            on_success=self._show_solve_quiz,
        )

    def _on_preview_requested(self, quiz_id: int) -> None:
        self._fetch_quiz_from_history(
            quiz_id,
            loading_msg="Pobieranie pytań do podglądu...",
            on_success=self._show_preview_quiz,
        )

    def _fetch_quiz_from_history(
        self,
        quiz_id: int,
        loading_msg: str,
        on_success: Callable[[dict], None],
    ) -> None:
        self._run_operation(
            api.fetch_quiz, quiz_id,
            loading_msg=loading_msg,
            on_success=on_success,
            error_title="Błąd quizu",
            error_fallback=Page.HISTORY,
        )

    def _apply_quiz_data(self, data: dict) -> None:
        self._current_title = data.get("title", "Quiz z historii")
        self._current_questions = data.get("questions", [])
        self._current_quiz_id = data.get("id", -1)

    def _show_solve_quiz(self, data: dict) -> None:
        self._stop_progress()
        self._apply_quiz_data(data)
        self._quiz_view.load_quiz(self._current_title, self._current_questions)
        self._stack.setCurrentIndex(Page.QUIZ)

    def _show_preview_quiz(self, data: dict) -> None:
        self._stop_progress()
        self._apply_quiz_data(data)
        self._preview_view.load_preview(self._current_title, self._current_questions)
        self._stack.setCurrentIndex(Page.PREVIEW)

    # ------------------------------------------------------------------
    # Usuwanie quizu z historii
    # ------------------------------------------------------------------

    def _on_delete_requested(self, quiz_id: int) -> None:
        self._run_operation(
            api.delete_quiz, quiz_id,
            loading_msg="Usuwanie quizu...",
            on_success=self._on_delete_finished,
            error_title="Błąd usuwania",
            error_fallback=Page.HISTORY,
        )

    def _on_delete_finished(self, _result: Any = None) -> None:
        self._on_history_requested()


def main() -> None:
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
