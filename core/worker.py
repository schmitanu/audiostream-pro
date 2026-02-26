"""
Background worker (QThread) for the desktop app.
Delegates to the shared pipeline and bridges progress to Qt signals.
"""

from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from .pipeline import run_pipeline


class StemWorker(QThread):
    """Worker thread: runs pipeline and emits status/progress/finished/error."""

    status = pyqtSignal(str)
    progress = pyqtSignal(int)
    finished_ok = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(
        self,
        video_path: str,
        output_dir: str | None = None,
        model_name: str = "htdemucs",
        shifts: int = 1,
        parent=None,
    ):
        super().__init__(parent)
        self._video_path = Path(video_path).resolve()
        self._output_dir = Path(output_dir).resolve() if output_dir else None
        self._model_name = model_name
        self._shifts = shifts

    def run(self):
        def on_progress(status: str, progress: int):
            self.status.emit(status)
            self.progress.emit(progress)

        try:
            out_path = run_pipeline(
                self._video_path,
                output_dir=self._output_dir,
                progress_callback=on_progress,
                model_name=self._model_name,
                shifts=self._shifts,
            )
            self.finished_ok.emit(str(out_path.parent))
        except Exception as e:
            self.error.emit(str(e))
            self.progress.emit(0)
