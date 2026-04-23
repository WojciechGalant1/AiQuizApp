from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class UploadView(QWidget):
    quiz_requested = pyqtSignal(str, int)  # (file_path, num_questions)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._file_path: str = ""
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        title = QLabel("AI Quiz Generator")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #2563eb;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Wgraj dokument i wygeneruj quiz za pomocą AI")
        subtitle.setStyleSheet("font-size: 14px; color: #64748b;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(20)

        self._file_label = QLabel("Nie wybrano pliku")
        self._file_label.setStyleSheet(
            "font-size: 13px; color: #94a3b8; padding: 16px; "
            "border: 2px dashed #cbd5e1; border-radius: 8px; "
            "background: #f8fafc;"
        )
        self._file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._file_label.setMinimumHeight(80)
        layout.addWidget(self._file_label)

        btn_browse = QPushButton("Wybierz plik (.txt / .pdf)")
        btn_browse.setStyleSheet(
            "QPushButton { font-size: 14px; padding: 10px 24px; "
            "background: #2563eb; color: white; border: none; border-radius: 6px; }"
            "QPushButton:hover { background: #1d4ed8; }"
        )
        btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_browse.clicked.connect(self._browse_file)
        layout.addWidget(btn_browse, alignment=Qt.AlignmentFlag.AlignCenter)

        q_row = QHBoxLayout()
        q_label = QLabel("Liczba pytań:")
        q_label.setStyleSheet("font-size: 13px;")
        self._spin = QSpinBox()
        self._spin.setRange(1, 20)
        self._spin.setValue(5)
        self._spin.setStyleSheet("font-size: 13px; padding: 4px 8px;")
        q_row.addStretch()
        q_row.addWidget(q_label)
        q_row.addWidget(self._spin)
        q_row.addStretch()
        layout.addLayout(q_row)

        self._btn_generate = QPushButton("Generuj quiz")
        self._btn_generate.setEnabled(False)
        self._btn_generate.setStyleSheet(
            "QPushButton { font-size: 15px; font-weight: bold; padding: 12px 32px; "
            "background: #16a34a; color: white; border: none; border-radius: 6px; }"
            "QPushButton:hover { background: #15803d; }"
            "QPushButton:disabled { background: #94a3b8; }"
        )
        self._btn_generate.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_generate.clicked.connect(self._on_generate)
        layout.addWidget(self._btn_generate, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()

    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Wybierz dokument", "", "Dokumenty (*.txt *.pdf)"
        )
        if path:
            self._file_path = path
            short = path.split("/")[-1] if "/" in path else path.split("\\")[-1]
            self._file_label.setText(f"Wybrany plik: {short}")
            self._file_label.setStyleSheet(
                "font-size: 13px; color: #1e293b; padding: 16px; "
                "border: 2px solid #2563eb; border-radius: 8px; "
                "background: #eff6ff;"
            )
            self._btn_generate.setEnabled(True)

    def _on_generate(self) -> None:
        if self._file_path:
            self.quiz_requested.emit(self._file_path, self._spin.value())
