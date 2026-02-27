"""
FreeYourHand - Mac 選單列圖示（System Tray）
提供右鍵選單：Settings / Models / Log / About / Quit。
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QFont, QPen
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication, QMessageBox

from app.constants import APP_NAME, APP_VERSION
from app.utils.logger import get_logger

logger = get_logger("tray")


def _create_tray_icon_pixmap() -> QPixmap:
    """生成選單列圖示（程式碼繪製的麥克風圖示）。"""
    size = 22
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Microphone body
    pen = QPen(QColor(0, 0, 0), 2)
    painter.setPen(pen)
    painter.setBrush(QColor(0, 0, 0))

    # Mic head (rounded rect)
    painter.drawRoundedRect(7, 3, 8, 10, 3, 3)

    # Mic arc
    painter.setBrush(QColor(0, 0, 0, 0))
    pen.setWidthF(1.5)
    painter.setPen(pen)
    painter.drawArc(4, 6, 14, 12, 0, -180 * 16)

    # Stand
    painter.drawLine(11, 18, 11, 20)
    painter.drawLine(7, 20, 15, 20)

    painter.end()
    return pixmap


class TrayIcon(QSystemTrayIcon):
    """Mac 選單列系統圖示。"""

    def __init__(self, app_controller, parent=None):
        super().__init__(parent)
        self._controller = app_controller

        # Set icon
        pixmap = _create_tray_icon_pixmap()
        self.setIcon(QIcon(pixmap))
        self.setToolTip(f"{APP_NAME} v{APP_VERSION}")

        # Build menu
        self._menu = QMenu()
        self._build_menu()
        self.setContextMenu(self._menu)

        # Show
        self.show()
        logger.info("System tray icon created")

    def _build_menu(self):
        """建構右鍵選單。"""
        # Status indicator
        self._status_action = QAction("● Ready", self._menu)
        self._status_action.setEnabled(False)
        self._menu.addAction(self._status_action)
        self._menu.addSeparator()

        # Settings
        settings_action = QAction("⚙  Settings...", self._menu)
        settings_action.triggered.connect(self._controller.show_settings)
        self._menu.addAction(settings_action)

        # Model Manager
        models_action = QAction("🎙  Models...", self._menu)
        models_action.triggered.connect(self._controller.show_model_manager)
        self._menu.addAction(models_action)

        # Log Viewer
        log_action = QAction("📋  Log...", self._menu)
        log_action.triggered.connect(self._controller.show_log_viewer)
        self._menu.addAction(log_action)

        self._menu.addSeparator()

        # About
        about_action = QAction(f"About {APP_NAME}", self._menu)
        about_action.triggered.connect(self._show_about)
        self._menu.addAction(about_action)

        # Quit
        quit_action = QAction("Quit", self._menu)
        quit_action.triggered.connect(self._controller.quit_app)
        self._menu.addAction(quit_action)

    def update_status(self, text: str):
        """更新選單中的狀態文字。"""
        self._status_action.setText(f"● {text}")

    def _show_about(self):
        """顯示 About 對話框。"""
        QMessageBox.about(
            None,
            f"About {APP_NAME}",
            f"<h3>{APP_NAME}</h3>"
            f"<p>Version {APP_VERSION}</p>"
            f"<p>Mac 語音輸入潤稿工具</p>"
            f"<p>結合 MLX Whisper 語音辨識與 Gemini AI 校對，<br>"
            f"實現精確的語音輸入體驗。</p>"
        )
