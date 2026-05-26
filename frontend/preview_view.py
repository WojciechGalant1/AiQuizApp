from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class PreviewView(QWidget):
    """Widok podglądu pytań wygenerowanego quizu bez konieczności jego rozwiązywania."""

    back_requested = pyqtSignal()

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

        self._title_lbl = QLabel("Podgląd quizu")
        self._title_lbl.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #1e293b; border: none;"
        )
        header_layout.addWidget(self._title_lbl)
        header_layout.addStretch()

        btn_back = QPushButton("← Powrót do historii")
        btn_back.setStyleSheet(
            "QPushButton { font-size: 13px; padding: 7px 16px; margin-left: 8px; "
            "background: #2563eb; color: white; border: none; border-radius: 6px; }"
            "QPushButton:hover { background: #1d4ed8; }"
        )
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.clicked.connect(self.back_requested.emit)
        header_layout.addWidget(btn_back)

        outer.addWidget(header)

        # --- Zawartość ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: #ffffff; }")
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setSpacing(16)
        self._content_layout.setContentsMargins(20, 20, 20, 20)
        scroll.setWidget(self._content)
        outer.addWidget(scroll)

    def load_preview(self, title: str, questions: list[dict]) -> None:
        self._title_lbl.setText(f"👁️ Podgląd: {title}")

        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, q in enumerate(questions, start=1):
            card = QWidget()
            card.setStyleSheet(
                "QWidget { background: #f0fdf4; border: 1px solid #bbf7d0; "
                "border-radius: 8px; padding: 16px; }"
            )
            card_layout = QVBoxLayout(card)

            # Pytanie
            q_label = QLabel(f"{i}. {q['question']}")
            q_label.setWordWrap(True)
            q_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #1e293b;")
            card_layout.addWidget(q_label)

            # Opcje
            options_widget = QWidget()
            options_layout = QVBoxLayout(options_widget)
            options_layout.setContentsMargins(10, 8, 0, 8)
            options_layout.setSpacing(4)
            for ans in q.get("answers", []):
                ans_lbl = QLabel(ans)
                ans_lbl.setWordWrap(True)
                ans_lbl.setStyleSheet("font-size: 13px; color: #475569;")
                options_layout.addWidget(ans_lbl)
            
            card_layout.addWidget(options_widget)

            # Poprawna odpowiedź i wyjaśnienie
            correct_box = QWidget()
            correct_box.setStyleSheet(
                "QWidget { background: #dcfce7; border-radius: 6px; padding: 10px; }"
            )
            correct_layout = QVBoxLayout(correct_box)
            correct_layout.setContentsMargins(12, 10, 12, 10)

            correct_lbl = QLabel(f"Poprawna odpowiedź: {q.get('correct', '?')}")
            correct_lbl.setStyleSheet("font-size: 14px; font-weight: 600; color: #166534; border: none;")
            correct_layout.addWidget(correct_lbl)

            if q.get("explanation"):
                expl_lbl = QLabel(f"Wyjaśnienie: {q['explanation']}")
                expl_lbl.setWordWrap(True)
                expl_lbl.setStyleSheet("font-size: 13px; color: #14532d; font-style: italic; border: none;")
                correct_layout.addWidget(expl_lbl)

            card_layout.addWidget(correct_box)

            self._content_layout.addWidget(card)

        self._content_layout.addStretch()
