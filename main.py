"""
FreeYourHand - Mac 語音輸入潤稿工具
主入口：初始化應用、權限檢查、啟動服務。
"""

import sys
import os
import logging
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication, QMessageBox

from app.constants import APP_NAME, APP_VERSION
from app.utils.logger import setup_logger, get_logger
from app.utils.config import Config
from app.utils.permissions import (
    check_microphone_permission,
    check_accessibility_permission,
    request_microphone_permission,
    request_accessibility_permission,
)
from app.core.pipeline import Pipeline, PipelineState
from app.core.hotkey_listener import HotkeyListener
from app.ui.overlay_window import OverlayWindow
from app.ui.tray_icon import TrayIcon
from app.ui.settings_window import SettingsWindow
from app.ui.model_manager_dialog import ModelManagerDialog
from app.ui.log_viewer import LogViewer


class AppController:
    """
    應用主控制器。
    串接 Pipeline、HotkeyListener、OverlayWindow、TrayIcon 等各元件。
    """

    def __init__(self):
        self._config = Config()

        # Initialize logger
        log_dir = os.path.join(str(Path.home()), ".freeyourhand", "logs")
        log_level = getattr(logging, self._config.log_level, logging.DEBUG)
        setup_logger(log_dir=log_dir, level=log_level)
        self._logger = get_logger("app")
        self._logger.info(f"Starting {APP_NAME} v{APP_VERSION}")

        # Components
        self._pipeline = Pipeline()
        self._hotkey = HotkeyListener()
        self._overlay = OverlayWindow()

        # Dialogs (lazy-created)
        self._settings_dialog = None
        self._model_dialog = None
        self._log_dialog = None

        # Tray icon
        self._tray = TrayIcon(self)

        # Wire signals
        self._connect_signals()

    def _connect_signals(self):
        """連接各元件的 Signal。"""
        # Hotkey → Pipeline
        self._hotkey.key_pressed.connect(self._on_hotkey_pressed)
        self._hotkey.key_released.connect(self._on_hotkey_released)
        self._hotkey.cancel_pressed.connect(self._on_cancel)
        self._hotkey.listener_error.connect(self._on_error)

        # Pipeline → Overlay
        self._pipeline.state_changed.connect(self._overlay.set_state)
        self._pipeline.rms_level.connect(self._overlay.set_rms)
        self._pipeline.error_occurred.connect(self._on_error)

        # Pipeline → Tray
        self._pipeline.state_changed.connect(self._update_tray_status)
        self._pipeline.result_ready.connect(self._on_result)

    def start(self):
        """啟動應用服務。"""
        # Check permissions first
        if self._config.first_launch:
            self._first_launch_guide()
            self._config.mark_launched()

        # Start hotkey listener
        self._hotkey.start()
        self._tray.update_status("Ready")
        self._logger.info("Application started, listening for hotkey...")

    # ── Hotkey handlers ───────────────────────────────────

    def _on_hotkey_pressed(self, translate: bool):
        """快捷鍵按下 → 開始錄音。"""
        self._logger.info(f"Hotkey pressed (translate={translate})")
        self._pipeline.start_recording(translate=translate)

    def _on_hotkey_released(self, translate: bool):
        """快捷鍵放開 → 停止錄音，啟動處理。"""
        self._logger.info(f"Hotkey released (translate={translate})")
        self._pipeline.stop_recording(translate=translate)

    def _on_cancel(self):
        """ESC 鍵按下 → 取消當前操作。"""
        self._logger.info("ESC pressed, cancelling...")
        self._pipeline.cancel()

    # ── State handlers ────────────────────────────────────

    def _update_tray_status(self, state: PipelineState):
        """更新 Tray 狀態文字。"""
        status_map = {
            PipelineState.IDLE: "Ready",
            PipelineState.RECORDING: "🔴 Recording...",
            PipelineState.TRANSCRIBING: "⏳ Transcribing...",
            PipelineState.POLISHING: "✨ Polishing...",
            PipelineState.PASTING: "📋 Pasting...",
            PipelineState.DONE: "✅ Done",
            PipelineState.ERROR: "❌ Error",
        }
        self._tray.update_status(status_map.get(state, "Ready"))

    def _on_result(self, text: str):
        """處理結果。"""
        self._logger.info(f"Result: {text[:80]}...")

    def _on_error(self, message: str):
        """處理錯誤。"""
        self._logger.error(f"Error: {message}")

    # ── Dialog launchers ──────────────────────────────────

    def show_settings(self):
        """顯示設定視窗。"""
        if self._settings_dialog is None or not self._settings_dialog.isVisible():
            self._settings_dialog = SettingsWindow(
                gemini_client=self._pipeline.gemini
            )
        self._settings_dialog.show()
        self._settings_dialog.raise_()
        self._settings_dialog.activateWindow()

    def show_model_manager(self):
        """顯示模型管理器。"""
        if self._model_dialog is None or not self._model_dialog.isVisible():
            self._model_dialog = ModelManagerDialog()
        self._model_dialog.show()
        self._model_dialog.raise_()
        self._model_dialog.activateWindow()

    def show_log_viewer(self):
        """顯示日誌查看器。"""
        if self._log_dialog is None or not self._log_dialog.isVisible():
            self._log_dialog = LogViewer()
        self._log_dialog.show()
        self._log_dialog.raise_()
        self._log_dialog.activateWindow()

    def quit_app(self):
        """退出應用。"""
        self._logger.info("Quitting application")
        self._hotkey.stop()
        self._pipeline.cancel()
        QApplication.quit()

    # ── First Launch ──────────────────────────────────────

    def _first_launch_guide(self):
        """首次啟動引導。"""
        self._logger.info("First launch detected, checking permissions...")

        # Check microphone
        if not check_microphone_permission():
            reply = QMessageBox.question(
                None, "Microphone Permission",
                f"{APP_NAME} 需要麥克風權限才能進行語音輸入。\n\n"
                "是否開啟系統偏好設定來授予權限？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                request_microphone_permission()

        # Check accessibility
        if not check_accessibility_permission():
            reply = QMessageBox.question(
                None, "Accessibility Permission",
                f"{APP_NAME} 需要輔助使用權限才能自動貼上文字。\n\n"
                "是否開啟系統偏好設定來授予權限？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                request_accessibility_permission()

        # Check Gemini API Key
        if not self._config.gemini_api_key:
            QMessageBox.information(
                None, "Setup Gemini API",
                f"請從選單列的 Settings 中設定 Gemini API Key，\n"
                f"以啟用語音校對功能。"
            )


def main():
    """應用主入口。"""
    # High-DPI support
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setQuitOnLastWindowClosed(False)  # Keep running after closing dialogs

    # Create controller and start
    controller = AppController()

    # Delay start to let the event loop initialize
    QTimer.singleShot(100, controller.start)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
