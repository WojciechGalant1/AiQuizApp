from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

MAX_FILE_SIZE_MB = 10
MAX_PDF_PAGES = 50


class UploadView(QWidget):
    quiz_requested = pyqtSignal(str, int)  # (file_path, num_questions)
    history_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._file_path: str = ""
        self._init_ui()

    def _init_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # --- Pasek górny (Header) ---
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 20, 20, 0)
        header_layout.addStretch()

        btn_history = QPushButton("📋  Historia quizów")
        btn_history.setStyleSheet(
            "QPushButton { font-size: 13px; font-weight: 600; padding: 8px 16px; "
            "background: #f8fafc; color: #475569; border: 1px solid #e2e8f0; border-radius: 6px; }"
            "QPushButton:hover { background: #f1f5f9; color: #0f172a; border-color: #cbd5e1; }"
        )
        btn_history.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_history.clicked.connect(self.history_requested.emit)
        header_layout.addWidget(btn_history)
        
        outer_layout.addWidget(header)

        # --- Główna zawartość (wyśrodkowana) ---
        content_container = QWidget()
        layout = QVBoxLayout(content_container)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(24)
        
        outer_layout.addWidget(content_container, stretch=1)

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
        if not path:
            return

        p = Path(path)
        file_size = p.stat().st_size
        max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
        if file_size > max_bytes:
            size_mb = file_size / 1024 / 1024
            QMessageBox.warning(
                self,
                "Plik za duży",
                f"Wybrany plik ma {size_mb:.1f} MB.\n"
                f"Maksymalny rozmiar to {MAX_FILE_SIZE_MB} MB.",
            )
            return

        page_info = ""
        if p.suffix.lower() == ".pdf":
            try:
                import pdfplumber
                with pdfplumber.open(path) as pdf:
                    num_pages = len(pdf.pages)
                if num_pages > MAX_PDF_PAGES:
                    QMessageBox.warning(
                        self,
                        "Za dużo stron",
                        f"Wybrany PDF ma {num_pages} stron.\n"
                        f"Maksymalna liczba stron to {MAX_PDF_PAGES}.",
                    )
                    return
                page_info = f", {num_pages} str."
            except Exception:
                pass

        self._file_path = path
        short = p.name
        size_kb = file_size / 1024
        size_info = f"{size_kb:.0f} KB" if size_kb < 1024 else f"{size_kb / 1024:.1f} MB"
        self._file_label.setText(f"Wybrany plik: {short}  ({size_info}{page_info})")
        self._file_label.setStyleSheet(
            "font-size: 13px; color: #1e293b; padding: 16px; "
            "border: 2px solid #2563eb; border-radius: 8px; "
            "background: #eff6ff;"
        )
        self._btn_generate.setEnabled(True)

    def _on_generate(self) -> None:
        if self._file_path:
            self.quiz_requested.emit(self._file_path, self._spin.value())
