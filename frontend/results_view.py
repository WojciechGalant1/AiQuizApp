from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)


class ResultsView(QWidget):
    """Widok wyników quizu z detalami i wyjaśnieniami."""

    back_to_home = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        outer = QVBoxLayout(self)

        self._score_label = QLabel()
        self._score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._score_label.setStyleSheet(
            "font-size: 26px; font-weight: bold; padding: 16px;"
        )
        outer.addWidget(self._score_label)

        self._percent_label = QLabel()
        self._percent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._percent_label.setStyleSheet("font-size: 16px; color: #64748b;")
        outer.addWidget(self._percent_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setSpacing(12)
        scroll.setWidget(self._content)
        outer.addWidget(scroll)

        btn_row = QHBoxLayout()
        btn_home = QPushButton("Nowy quiz")
        btn_home.setStyleSheet(
            "QPushButton { font-size: 14px; font-weight: bold; padding: 10px 28px; "
            "background: #2563eb; color: white; border: none; border-radius: 6px; }"
            "QPushButton:hover { background: #1d4ed8; }"
        )
        btn_home.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_home.clicked.connect(self.back_to_home.emit)
        btn_row.addStretch()
        btn_row.addWidget(btn_home)
        btn_row.addStretch()
        outer.addLayout(btn_row)

    def show_results(self, score: int, total: int, details: list[dict]) -> None:
        percent = round((score / total) * 100, 1) if total else 0

        if percent >= 80:
            color = "#16a34a"
            emoji = "Swietnie!"
        elif percent >= 50:
            color = "#ca8a04"
            emoji = "Nieźle!"
        else:
            color = "#dc2626"
            emoji = "Spróbuj ponownie"

        self._score_label.setText(f"{emoji}  {score} / {total}")
        self._score_label.setStyleSheet(
            f"font-size: 28px; font-weight: bold; color: {color}; padding: 16px;"
        )
        self._percent_label.setText(f"{percent}% poprawnych odpowiedzi")

        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for d in details:
            card = QWidget()
            if d["is_correct"]:
                border_color = "#16a34a"
                bg = "#f0fdf4"
                icon = "+"
            else:
                border_color = "#dc2626"
                bg = "#fef2f2"
                icon = "x"

            card.setStyleSheet(
                f"QWidget {{ background: {bg}; border: 1px solid {border_color}; "
                f"border-radius: 8px; padding: 12px; }}"
            )
            cl = QVBoxLayout(card)

            header = QLabel(f"[{icon}]  {d['question']}")
            header.setWordWrap(True)
            header.setStyleSheet("font-size: 13px; font-weight: 600;")
            cl.addWidget(header)

            ans_text = (
                f"Twoja: {d['selected']}  |  Poprawna: {d['correct']}"
                if not d["is_correct"]
                else f"Poprawna: {d['correct']}"
            )
            ans_label = QLabel(ans_text)
            ans_label.setStyleSheet("font-size: 12px; color: #475569;")
            cl.addWidget(ans_label)

            if d.get("explanation"):
                expl = QLabel(f"Wyjaśnienie: {d['explanation']}")
                expl.setWordWrap(True)
                expl.setStyleSheet("font-size: 12px; color: #64748b; font-style: italic;")
                cl.addWidget(expl)

            self._content_layout.addWidget(card)

        self._content_layout.addStretch()
