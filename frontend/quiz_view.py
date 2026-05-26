from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)


class QuizView(QWidget):
    """Widok rozwiązywania quizu - wyświetla pytania z odpowiedziami."""

    quiz_finished = pyqtSignal(list)  # list of {question_index, selected}

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._questions: list[dict] = []
        self._groups: list[QButtonGroup] = []
        self._init_ui()

    def _init_ui(self) -> None:
        outer = QVBoxLayout(self)

        self._title_label = QLabel("Quiz")
        self._title_label.setStyleSheet(
            "font-size: 22px; font-weight: bold; color: #1e293b; margin-bottom: 8px;"
        )
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(self._title_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setSpacing(16)
        scroll.setWidget(self._content)
        outer.addWidget(scroll)

        btn_row = QHBoxLayout()
        self._btn_submit = QPushButton("Sprawdź odpowiedzi")
        self._btn_submit.setStyleSheet(
            "QPushButton { font-size: 15px; font-weight: bold; padding: 12px 32px; "
            "background: #2563eb; color: white; border: none; border-radius: 6px; }"
            "QPushButton:hover { background: #1d4ed8; }"
        )
        self._btn_submit.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_submit.clicked.connect(self._submit)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_submit)
        btn_row.addStretch()
        outer.addLayout(btn_row)

    def load_quiz(self, title: str, questions: list[dict]) -> None:
        self._title_label.setText(title)
        self._questions = questions
        self._groups.clear()

        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, q in enumerate(questions, start=1):
            card = QWidget()
            card.setStyleSheet(
                "QWidget { background: #f8fafc; border: 1px solid #e2e8f0; "
                "border-radius: 8px; padding: 16px; }"
            )
            card_layout = QVBoxLayout(card)

            q_label = QLabel(f"{i}. {q['question']}")
            q_label.setWordWrap(True)
            q_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #1e293b;")
            card_layout.addWidget(q_label)

            group = QButtonGroup(card)
            for ans in q.get("answers", []):
                rb = QRadioButton(ans)
                rb.setStyleSheet("font-size: 13px; padding: 4px 0;")
                group.addButton(rb)
                card_layout.addWidget(rb)
            self._groups.append(group)

            self._content_layout.addWidget(card)

        self._content_layout.addStretch()

    def _submit(self) -> None:
        unanswered = [
            i + 1 for i, g in enumerate(self._groups) if g.checkedButton() is None
        ]
        if unanswered:
            QMessageBox.warning(
                self,
                "Brak odpowiedzi",
                f"Odpowiedz na pytania: {', '.join(map(str, unanswered))}",
            )
            return

        answers: list[dict] = []
        for i, g in enumerate(self._groups):
            selected_text = g.checkedButton().text()
            if ")" in selected_text:
                selected_letter = selected_text.split(")")[0].strip()
            elif selected_text:
                selected_letter = selected_text[0]
            else:
                selected_letter = ""
            answers.append({"question_index": i, "selected": selected_letter})

        self.quiz_finished.emit(answers)
