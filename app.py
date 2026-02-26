"""
AudioStem-Pro — Desktop app to extract background music from video
by removing vocals using Demucs (htdemucs) and FFmpeg.

Author: Eduarth Schmidt
Run: python app.py
"""

__author__ = "Eduarth Schmidt"

import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("AudioStem-Pro")
    app.setApplicationDisplayName("AudioStem-Pro")
    font = QFont()
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
