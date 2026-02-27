"""
FreeYourHand - 日誌查看器
即時顯示日誌串流，支援按 Level 過濾。
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QTextCharFormat
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QPushButton, QComboBox, QSizePolicy,
)

from app.utils.logger import get_log_emitter, get_logger
from app.constants import LOG_MAX_LINES

logger = get_logger("log_viewer")

# Level colors
LEVEL_COLORS = {
    "DEBUG":    "#666688",
    "INFO":     "#00d2ff",
    "WARNING":  "#ffb432",
    "ERROR":    "#ef4444",
    "CRITICAL": "#ff0040",
}

DARK_STYLE = """
QDialog { background-color: #1a1a2e; color: #e0e0e0; }
QTextEdit {
    background-color: #0e0e1a; color: #c0c0d8;
    border: 1px solid #2d2d4a; border-radius: 6px;
    font-family: "SF Mono", "Menlo", "Consolas", monospace;
    font-size: 12px; padding: 8px;
}
QComboBox {
    background-color: #222244; color: #e0e0e0;
    border: 1px solid #3a3a5e; border-radius: 6px;
    padding: 6px 12px; font-size: 12px;
}
QComboBox QAbstractItemView {
    background-color: #222244; color: #e0e0e0;
    border: 1px solid #3a3a5e;
}
QPushButton {
    background-color: #2a2a50; color: #e0e0e0;
    border: 1px solid #3a3a5e; border-radius: 6px;
    padding: 6px 16px; font-size: 12px;
}
QPushButton:hover { background-color: #3a3a60; border-color: #00d2ff; }
QLabel { color: #b0b0d0; }
"""


class LogViewer(QDialog):
    """即時日誌查看器。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FreeYourHand Log")
        self.setMinimumSize(650, 420)
        self.setStyleSheet(DARK_STYLE)

        self._min_level = "DEBUG"
        self._line_count = 0
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Header
        header = QHBoxLayout()
        title = QLabel("📋  Log")
        title.setFont(QFont("SF Pro Display", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #ffffff;")
        header.addWidget(title)

        header.addStretch()

        # Level filter
        header.addWidget(QLabel("Filter:"))
        self._level_combo = QComboBox()
        self._level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self._level_combo.currentTextChanged.connect(self._on_filter_changed)
        header.addWidget(self._level_combo)

        # Clear button
        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(self._clear)
        header.addWidget(btn_clear)

        layout.addLayout(header)

        # Log display
        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self._text)

        # Status bar
        self._status = QLabel("0 lines")
        self._status.setStyleSheet("font-size: 11px; color: #444466;")
        layout.addWidget(self._status)

    def _connect_signals(self):
        """連接日誌 Signal。"""
        emitter = get_log_emitter()
        emitter.log_message.connect(self._on_log_message)

    def _on_log_message(self, level: str, timestamp: str, message: str):
        """接收新日誌訊息。"""
        # Filter by level
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if levels.index(level) < levels.index(self._min_level):
            return

        # Apply color
        color = LEVEL_COLORS.get(level, "#c0c0d8")
        html = (
            f'<span style="color: #444466;">{timestamp}</span> '
            f'<span style="color: {color}; font-weight: bold;">[{level}]</span> '
            f'<span style="color: #c0c0d8;">{message}</span>'
        )

        self._text.append(html)
        self._line_count += 1

        # Auto-scroll to bottom
        scrollbar = self._text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        # Truncate if too many lines
        if self._line_count > LOG_MAX_LINES:
            cursor = self._text.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.KeepAnchor, 100)
            cursor.removeSelectedText()
            self._line_count -= 100

        self._status.setText(f"{self._line_count} lines")

    def _on_filter_changed(self, level: str):
        self._min_level = level

    def _clear(self):
        self._text.clear()
        self._line_count = 0
        self._status.setText("0 lines")
