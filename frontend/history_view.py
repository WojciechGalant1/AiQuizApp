from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class HistoryView(QWidget):
    """Widok historii wygenerowanych quizów z możliwością ponownego rozwiązania."""

    quiz_selected = pyqtSignal(int)   # emituje quiz_id wybranego quizu
    preview_requested = pyqtSignal(int) # emituje quiz_id do podglądu
    delete_requested = pyqtSignal(int) # emituje quiz_id do usunięcia
    back_requested = pyqtSignal()
    refresh_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setSpacing(0)
        outer.setContentsMargins(0, 0, 0, 0)

        # --- Nagłówek ---
        header = QWidget()
        header.setStyleSheet(
            "QWidget { background: #f8fafc; border-bottom: 1px solid #e2e8f0; }"
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 14, 20, 14)

        title_lbl = QLabel("Historia quizów")
        title_lbl.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #1e293b; border: none;"
        )
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()

        btn_refresh = QPushButton("↻  Odśwież")
        btn_refresh.setStyleSheet(
            "QPushButton { font-size: 13px; padding: 7px 16px; "
            "background: #e2e8f0; color: #475569; border: none; border-radius: 6px; }"
            "QPushButton:hover { background: #cbd5e1; }"
        )
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.clicked.connect(self.refresh_requested.emit)
        header_layout.addWidget(btn_refresh)

        btn_back = QPushButton("← Powrót")
        btn_back.setStyleSheet(
            "QPushButton { font-size: 13px; padding: 7px 16px; margin-left: 8px; "
            "background: #2563eb; color: white; border: none; border-radius: 6px; }"
            "QPushButton:hover { background: #1d4ed8; }"
        )
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.clicked.connect(self.back_requested.emit)
        header_layout.addWidget(btn_back)

        outer.addWidget(header)

        # --- Lista quizów (scroll) ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: #ffffff; }")
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setSpacing(10)
        self._content_layout.setContentsMargins(20, 16, 20, 16)
        scroll.setWidget(self._content)
        outer.addWidget(scroll)

    # ------------------------------------------------------------------
    # Publiczne API
    # ------------------------------------------------------------------

    def show_quizzes(self, quizzes: list[dict]) -> None:
        """Czyści listę i wypełnia ją kartami quizów."""
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not quizzes:
            empty = QLabel("Brak quizów w historii.\nWygeneruj swój pierwszy quiz!")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("font-size: 14px; color: #94a3b8; padding: 40px;")
            self._content_layout.addWidget(empty)
        else:
            for quiz in quizzes:
                self._content_layout.addWidget(self._build_card(quiz))

        self._content_layout.addStretch()

    # ------------------------------------------------------------------
    # Budowanie kart
    # ------------------------------------------------------------------

    def _build_card(self, q: dict) -> QWidget:
        card = QWidget()
        card.setStyleSheet(
            "QWidget { background: #f8fafc; border: 1px solid #e2e8f0; "
            "border-radius: 8px; }"
        )
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        # --- Lewa część: informacje ---
        info = QVBoxLayout()
        info.setSpacing(4)

        title_lbl = QLabel(q.get("title", "Quiz"))
        title_lbl.setStyleSheet(
            "font-size: 14px; font-weight: 600; color: #1e293b; border: none;"
        )
        info.addWidget(title_lbl)

        source_lbl = QLabel(f"📄  {q.get('source_filename', '')}")
        source_lbl.setStyleSheet("font-size: 12px; color: #64748b; border: none;")
        info.addWidget(source_lbl)

        created_raw = q.get("created_at", "")
        try:
            dt = datetime.fromisoformat(created_raw)
            date_str = dt.strftime("%d.%m.%Y  %H:%M")
        except Exception:
            date_str = created_raw or "—"
        date_lbl = QLabel(f"🕐  {date_str}")
        date_lbl.setStyleSheet("font-size: 12px; color: #94a3b8; border: none;")
        info.addWidget(date_lbl)

        layout.addLayout(info, stretch=1)

        # --- Prawa część: wynik + przycisk ---
        right = QVBoxLayout()
        right.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right.setSpacing(8)

        score = q.get("score")
        total = q.get("total")
        if score is not None and total:
            pct = round((score / total) * 100)
            color = (
                "#16a34a" if pct >= 80
                else "#ca8a04" if pct >= 50
                else "#dc2626"
            )
            score_lbl = QLabel(f"{int(score)} / {total}  ({pct}%)")
            score_lbl.setStyleSheet(
                f"font-size: 14px; font-weight: bold; color: {color}; border: none;"
            )
        else:
            score_lbl = QLabel("Nie rozwiązano")
            score_lbl.setStyleSheet(
                "font-size: 13px; color: #94a3b8; border: none;"
            )
        score_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right.addWidget(score_lbl)

        btn_solve = QPushButton("▶  Rozwiąż")
        btn_solve.setStyleSheet(
            "QPushButton { font-size: 13px; font-weight: bold; padding: 8px 18px; "
            "background: #16a34a; color: white; border: none; border-radius: 6px; }"
            "QPushButton:hover { background: #15803d; }"
        )
        btn_solve.setCursor(Qt.CursorShape.PointingHandCursor)
        quiz_id: int = q.get("id", -1)
        btn_solve.clicked.connect(lambda _, qid=quiz_id: self.quiz_selected.emit(qid))

        btn_preview = QPushButton("👁️ Podgląd")
        btn_preview.setStyleSheet(
            "QPushButton { font-size: 13px; font-weight: bold; padding: 8px 14px; "
            "background: #e2e8f0; color: #475569; border: none; border-radius: 6px; }"
            "QPushButton:hover { background: #cbd5e1; }"
        )
        btn_preview.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_preview.clicked.connect(lambda _, qid=quiz_id: self.preview_requested.emit(qid))

        btn_delete = QPushButton("🗑️")
        btn_delete.setToolTip("Usuń quiz")
        btn_delete.setStyleSheet(
            "QPushButton { font-size: 14px; padding: 7px 12px; "
            "background: #fee2e2; color: #dc2626; border: none; border-radius: 6px; }"
            "QPushButton:hover { background: #fecaca; }"
        )
        btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_delete.clicked.connect(lambda _, qid=quiz_id: self._confirm_delete(qid))

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addWidget(btn_solve)
        btn_row.addWidget(btn_preview)
        btn_row.addWidget(btn_delete)

        right.addLayout(btn_row)

        layout.addLayout(right)
        return card

    def _confirm_delete(self, quiz_id: int) -> None:
        ans = QMessageBox.question(
            self,
            "Potwierdzenie",
            "Czy na pewno chcesz usunąć ten quiz z historii?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if ans == QMessageBox.StandardButton.Yes:
            self.delete_requested.emit(quiz_id)
