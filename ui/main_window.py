"""
Main window: dark theme, drag-and-drop, progress, status, Open Output Folder.
"""

import sys
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.audio_utils import check_ffmpeg_available
from core.pipeline import DEMUCS_MODELS, QUALITY_PROFILES
from core.worker import StemWorker


# Dark theme palette
BG_DARK = "#1a1b26"
BG_CARD = "#24283b"
BG_HOVER = "#2d3142"
ACCENT = "#7aa2f7"
ACCENT_HOVER = "#89b4fa"
TEXT = "#c0caf5"
TEXT_DIM = "#565f89"
SUCCESS = "#9ece6a"
ERROR_COLOR = "#f7768e"


class DropZone(QFrame):
    """Drag-and-drop area for video files."""

    video_dropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setObjectName("dropZone")
        self.setMinimumHeight(160)
        self._label = QLabel("Drop video here\nor click to browse")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.addWidget(self._label)
        self.setStyleSheet(f"""
            QFrame#dropZone {{
                background: {BG_CARD};
                border: 2px dashed {TEXT_DIM};
                border-radius: 12px;
            }}
            QFrame#dropZone:hover {{
                border-color: {ACCENT};
                background: {BG_HOVER};
            }}
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and self._is_video(urls[0].toLocalFile()):
                event.acceptProposedAction()
                self.setStyleSheet(f"""
                    QFrame#dropZone {{
                        background: {BG_HOVER};
                        border: 2px dashed {ACCENT};
                        border-radius: 12px;
                    }}
                """)

    def dragLeaveEvent(self, e):
        self.setStyleSheet(f"""
            QFrame#dropZone {{
                background: {BG_CARD};
                border: 2px dashed {TEXT_DIM};
                border-radius: 12px;
            }}
        """)

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet(f"""
            QFrame#dropZone {{
                background: {BG_CARD};
                border: 2px dashed {TEXT_DIM};
                border-radius: 12px;
            }}
        """)
        if event.mimeData().hasUrls():
            path = event.mimeData().urls()[0].toLocalFile()
            if self._is_video(path):
                self.video_dropped.emit(path)

    @staticmethod
    def _is_video(path: str) -> bool:
        p = Path(path).suffix.lower()
        return p in (".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v")

    def set_text(self, text: str):
        self._label.setText(text)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._worker: StemWorker | None = None
        self._output_dir: str | None = None
        self.setWindowTitle("AudioStem-Pro — Extract background music")
        self.setMinimumSize(520, 420)
        self.resize(560, 460)
        self._build_ui()
        self._apply_styles()
        self._check_ffmpeg()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(20)
        layout.setContentsMargins(28, 28, 28, 28)

        title = QLabel("AudioStem-Pro")
        title.setObjectName("title")
        layout.addWidget(title)

        subtitle = QLabel("Extract background music from video (vocals removed)")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)
        byline = QLabel('by <a href="https://aiautomationflows.com/">Eduarth Schmidt</a>')
        byline.setObjectName("subtitle")
        byline.setOpenExternalLinks(True)
        byline.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(byline)

        opts_layout = QFormLayout()
        self._model_combo = QComboBox()
        for model_id, label in DEMUCS_MODELS:
            self._model_combo.addItem(label, model_id)
        self._model_combo.setObjectName("combo")
        opts_layout.addRow("Model:", self._model_combo)
        self._quality_combo = QComboBox()
        for shifts, label in QUALITY_PROFILES:
            self._quality_combo.addItem(label, shifts)
        self._quality_combo.setObjectName("combo")
        opts_layout.addRow("Quality:", self._quality_combo)
        layout.addLayout(opts_layout)

        self._drop_zone = DropZone(self)
        self._drop_zone.video_dropped.connect(self.on_video_selected)
        layout.addWidget(self._drop_zone)

        self._select_btn = QPushButton("Select Video")
        self._select_btn.setObjectName("primaryButton")
        self._select_btn.clicked.connect(self._on_select_clicked)
        layout.addWidget(self._select_btn)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        self._status = QLabel("Ready")
        self._status.setObjectName("statusLabel")
        layout.addWidget(self._status)

        self._open_folder_btn = QPushButton("Open Output Folder")
        self._open_folder_btn.setObjectName("secondaryButton")
        self._open_folder_btn.setVisible(False)
        self._open_folder_btn.clicked.connect(self._on_open_folder)
        layout.addWidget(self._open_folder_btn)

        layout.addStretch(1)

    def _apply_styles(self):
        self.setStyleSheet(f"""
            QMainWindow {{
                background: {BG_DARK};
            }}
            QWidget {{
                background: {BG_DARK};
                color: {TEXT};
            }}
            QLabel#title {{
                font-size: 24px;
                font-weight: bold;
                color: {TEXT};
            }}
            QLabel#subtitle {{
                color: {TEXT_DIM};
                font-size: 13px;
            }}
            QLabel#statusLabel {{
                color: {TEXT_DIM};
                font-size: 12px;
            }}
            QPushButton#primaryButton {{
                background: {ACCENT};
                color: {BG_DARK};
                border: none;
                border-radius: 8px;
                padding: 14px 24px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton#primaryButton:hover {{
                background: {ACCENT_HOVER};
            }}
            QPushButton#primaryButton:disabled {{
                background: {TEXT_DIM};
                color: {TEXT};
            }}
            QPushButton#secondaryButton {{
                background: {BG_CARD};
                color: {ACCENT};
                border: 1px solid {ACCENT};
                border-radius: 8px;
                padding: 12px 20px;
                font-size: 13px;
            }}
            QPushButton#secondaryButton:hover {{
                background: {BG_HOVER};
            }}
            QProgressBar {{
                border: none;
                border-radius: 6px;
                background: {BG_CARD};
                text-align: center;
                color: {TEXT};
            }}
            QProgressBar::chunk {{
                background: {ACCENT};
                border-radius: 6px;
            }}
            QComboBox#combo {{
                background: {BG_CARD};
                color: {TEXT};
                border: 1px solid {TEXT_DIM};
                border-radius: 6px;
                padding: 6px 10px;
                min-width: 200px;
            }}
            QComboBox#combo:hover {{
                border-color: {ACCENT};
            }}
        """)

    def _check_ffmpeg(self):
        ok, msg = check_ffmpeg_available()
        if not ok:
            QMessageBox.warning(self, "FFmpeg not found", msg)

    def _on_select_clicked(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video",
            "",
            "Video (*.mp4 *.mov *.avi *.mkv *.webm *.m4v);;All (*.*)",
        )
        if path:
            self.on_video_selected(path)

    def on_video_selected(self, path: str):
        if self._worker and self._worker.isRunning():
            return
        path = Path(path).resolve()
        if not path.exists():
            QMessageBox.warning(self, "File not found", f"File does not exist:\n{path}")
            return
        self._output_dir = None
        self._open_folder_btn.setVisible(False)
        self._progress.setVisible(True)
        self._progress.setValue(0)
        self._status.setText("Starting…")
        self._drop_zone.set_text(path.name)
        self._select_btn.setEnabled(False)

        model_name = self._model_combo.currentData()
        shifts = self._quality_combo.currentData()
        self._worker = StemWorker(str(path), model_name=model_name, shifts=shifts)
        self._worker.status.connect(self._on_status)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_ok.connect(self._on_finished_ok)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _on_status(self, text: str):
        self._status.setText(text)

    def _on_progress(self, value: int):
        self._progress.setValue(value)

    def _on_finished_ok(self, output_dir: str):
        self._output_dir = output_dir
        self._status.setText("Done")
        self._progress.setValue(100)
        self._open_folder_btn.setVisible(True)

    def _on_error(self, message: str):
        QMessageBox.critical(self, "Error", message)
        self._status.setText("Error")
        self._progress.setValue(0)

    def _on_worker_finished(self):
        self._select_btn.setEnabled(True)
        self._worker = None

    def _on_open_folder(self):
        if not self._output_dir or not Path(self._output_dir).exists():
            QMessageBox.warning(self, "Folder not found", "Output folder is no longer available.")
            return
        if sys.platform == "darwin":
            import subprocess
            subprocess.run(["open", self._output_dir], check=False)
        elif sys.platform == "win32":
            import subprocess
            subprocess.run(["explorer", self._output_dir], check=False)
        else:
            import subprocess
            subprocess.run(["xdg-open", self._output_dir], check=False)
