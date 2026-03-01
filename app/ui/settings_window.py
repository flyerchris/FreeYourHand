"""
FreeYourHand - 設定視窗
Tab 式設定介面：General / AI / Advanced
深色主題，現代感 UI。
"""

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QLineEdit, QPushButton, QComboBox, QTextEdit,
    QGroupBox, QFormLayout, QSpinBox, QMessageBox, QSizePolicy,
)
import subprocess
import shutil

from app.constants import WHISPER_MODELS
from app.utils.config import Config
from app.utils.logger import get_logger

logger = get_logger("settings")

# ── Dark Theme Stylesheet ─────────────────────────────────
DARK_STYLE = """
QDialog {
    background-color: #1a1a2e;
    color: #e0e0e0;
}
QTabWidget::pane {
    border: 1px solid #2d2d4a;
    border-radius: 8px;
    background-color: #16162a;
    top: -1px;
}
QTabBar::tab {
    background-color: #1e1e3a;
    color: #8888aa;
    padding: 10px 24px;
    margin-right: 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-size: 13px;
    font-weight: 500;
}
QTabBar::tab:selected {
    background-color: #16162a;
    color: #00d2ff;
    border-bottom: 2px solid #00d2ff;
}
QTabBar::tab:hover:!selected {
    background-color: #242448;
    color: #bbbbdd;
}
QGroupBox {
    font-size: 14px;
    font-weight: bold;
    color: #c0c0e0;
    border: 1px solid #2d2d4a;
    border-radius: 8px;
    margin-top: 16px;
    padding: 16px 12px 12px 12px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
QLabel {
    color: #b0b0d0;
    font-size: 13px;
}
QLineEdit, QComboBox, QSpinBox {
    background-color: #222244;
    color: #e0e0e0;
    border: 1px solid #3a3a5e;
    border-radius: 6px;
    padding: 3px 12px;
    min-height: 15px;
    font-size: 13px;
    selection-background-color: #00d2ff;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #00d2ff;
}
QTextEdit {
    background-color: #222244;
    color: #e0e0e0;
    border: 1px solid #3a3a5e;
    border-radius: 6px;
    padding: 8px;
    font-size: 12px;
    font-family: "SF Mono", "Menlo", monospace;
}
QTextEdit:focus {
    border: 1px solid #00d2ff;
}
QPushButton {
    background-color: #2a2a50;
    color: #e0e0e0;
    border: 1px solid #3a3a5e;
    border-radius: 6px;
    padding: 3px 24px;
    min-height: 15px;
    font-size: 13px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #3a3a60;
    border-color: #00d2ff;
}
QPushButton:pressed {
    background-color: #1a1a3a;
}
QPushButton#primary {
    background-color: #00a0cc;
    color: white;
    border: none;
}
QPushButton#primary:hover {
    background-color: #00b8e6;
}
QPushButton#danger {
    background-color: #cc3333;
    color: white;
    border: none;
}
QPushButton#danger:hover {
    background-color: #e04040;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox::down-arrow {
    width: 0;
    height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #8888aa;
}
QComboBox QAbstractItemView {
    background-color: #222244;
    color: #e0e0e0;
    border: 1px solid #3a3a5e;
    selection-background-color: #00d2ff;
}
"""


class SettingsWindow(QDialog):
    """設定視窗 — Tab 式介面。"""

    def __init__(self, gemini_client=None, parent=None):
        super().__init__(parent)
        self._config = Config()
        self._gemini_client = gemini_client

        self.setWindowTitle("FreeYourHand Settings")
        self.setMinimumSize(580, 520)
        self.setStyleSheet(DARK_STYLE)

        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Title
        title = QLabel("⚙  設定")
        title.setFont(QFont("SF Pro Display", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #ffffff; margin-bottom: 4px;")
        layout.addWidget(title)

        # Tab widget
        tabs = QTabWidget()
        tabs.addTab(self._create_general_tab(), "General")
        tabs.addTab(self._create_api_tab(), "API")
        tabs.addTab(self._create_ai_tab(), "AI")
        tabs.addTab(self._create_advanced_tab(), "Advanced")
        layout.addWidget(tabs)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_save = QPushButton("Save")
        btn_save.setObjectName("primary")
        btn_save.clicked.connect(self._save_settings)
        btn_layout.addWidget(btn_save)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)

    # ── General Tab ───────────────────────────────────────

    def _create_general_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Hotkey group
        group = QGroupBox("快捷鍵")
        form = QFormLayout(group)

        self._hotkey_edit = QLineEdit()
        self._hotkey_edit.setPlaceholderText("e.g. Key.alt_r")
        self._hotkey_edit.setReadOnly(True)
        self._hotkey_edit.setToolTip("Click and press a key to set")

        form.addRow("觸發鍵：", self._hotkey_edit)

        hint = QLabel(
            "預設為右側 Option 鍵 (⌥)。長按開始錄音，放開結束。\n"
            "錄音時按 Shift → 翻譯為英文。\n"
            "隨時按 ESC → 取消當前操作。"
        )
        hint.setStyleSheet("color: #666688; font-size: 11px;")
        hint.setWordWrap(True)
        form.addRow(hint)

        layout.addWidget(group)
        layout.addStretch()
        return widget

    # ── AI Tab ────────────────────────────────────────────

    # ── API Tab ────────────────────────────────────────────

    def _create_api_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Gemini group
        gemini_group = QGroupBox("Gemini API")
        gemini_form = QFormLayout(gemini_group)

        self._api_key_edit = QLineEdit()
        self._api_key_edit.setPlaceholderText("Enter your Gemini API Key")
        self._api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        gemini_form.addRow("API Key：", self._api_key_edit)

        # Test connection button
        self._btn_test = QPushButton("Test Connection")
        self._btn_test.clicked.connect(self._test_connection)
        gemini_form.addRow("", self._btn_test)

        # Gemini model selection
        self._gemini_model_combo = QComboBox()
        self._gemini_model_combo.setPlaceholderText("Enter API Key and click Fetch Models")
        gemini_form.addRow("Gemini Model：", self._gemini_model_combo)

        # Fetch models button
        self._btn_fetch = QPushButton("Fetch Models")
        self._btn_fetch.clicked.connect(self._fetch_gemini_models)
        gemini_form.addRow("", self._btn_fetch)

        layout.addWidget(gemini_group)
        layout.addStretch()
        return widget

    # ── AI Tab ─────────────────────────────────────────────

    def _create_ai_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Whisper group
        whisper_group = QGroupBox("Whisper 模型")
        whisper_form = QFormLayout(whisper_group)

        self._whisper_combo = QComboBox()
        for name in WHISPER_MODELS:
            self._whisper_combo.addItem(name)
        whisper_form.addRow("模型：", self._whisper_combo)

        layout.addWidget(whisper_group)

        # Custom restore prompt group
        prompt_group = QGroupBox("自定義校對指令 (中文模式)")
        prompt_layout = QVBoxLayout(prompt_group)

        self._prompt_edit = QTextEdit()
        self._prompt_edit.setMinimumHeight(100)
        self._prompt_edit.setPlaceholderText("留空使用預設 Prompt")
        prompt_layout.addWidget(self._prompt_edit)

        btn_reset_prompt = QPushButton("Reset to Default")
        btn_reset_prompt.clicked.connect(self._reset_prompt)
        prompt_layout.addWidget(btn_reset_prompt, alignment=Qt.AlignmentFlag.AlignRight)

        layout.addWidget(prompt_group)

        # Custom translate prompt group
        translate_group = QGroupBox("自定義翻譯指令 (Shift 翻譯模式)")
        translate_layout = QVBoxLayout(translate_group)

        self._translate_prompt_edit = QTextEdit()
        self._translate_prompt_edit.setMinimumHeight(100)
        self._translate_prompt_edit.setPlaceholderText("留空使用預設翻譯 Prompt")
        translate_layout.addWidget(self._translate_prompt_edit)

        btn_reset_translate = QPushButton("Reset to Default")
        btn_reset_translate.clicked.connect(self._reset_translate_prompt)
        translate_layout.addWidget(btn_reset_translate, alignment=Qt.AlignmentFlag.AlignRight)

        layout.addWidget(translate_group)
        return widget

    # ── Advanced Tab ──────────────────────────────────────

    def _create_advanced_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Logging group
        log_group = QGroupBox("日誌設定")
        log_form = QFormLayout(log_group)

        self._log_level_combo = QComboBox()
        self._log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        log_form.addRow("日誌層級：", self._log_level_combo)

        layout.addWidget(log_group)
        layout.addStretch()
        return widget

    # ── Load / Save ───────────────────────────────────────

    def _load_settings(self):
        """從 Config 載入設定到 UI。"""
        self._hotkey_edit.setText(self._config.hotkey)
        self._api_key_edit.setText(self._config.gemini_api_key)
        self._prompt_edit.setPlainText(self._config.prompt_restore)
        self._translate_prompt_edit.setPlainText(self._config.prompt_translate)

        # Whisper model
        idx = self._whisper_combo.findText(self._config.whisper_model)
        if idx >= 0:
            self._whisper_combo.setCurrentIndex(idx)

        # Gemini model — load persisted model list first
        saved_models = self._config.gemini_model_list
        if saved_models:
            self._gemini_model_combo.clear()
            self._gemini_model_combo.addItems(saved_models)
        saved_model = self._config.gemini_model
        if saved_model:
            idx = self._gemini_model_combo.findText(saved_model)
            if idx >= 0:
                self._gemini_model_combo.setCurrentIndex(idx)
            else:
                # Model not in list, add it and select it
                self._gemini_model_combo.addItem(saved_model)
                self._gemini_model_combo.setCurrentIndex(self._gemini_model_combo.count() - 1)

        # Log level
        idx = self._log_level_combo.findText(self._config.log_level)
        if idx >= 0:
            self._log_level_combo.setCurrentIndex(idx)

    def _save_settings(self):
        """將 UI 設定儲存到 Config。"""
        self._config.set_gemini_api_key(self._api_key_edit.text().strip())
        self._config.set_whisper_model(self._whisper_combo.currentText())
        self._config.set_gemini_model(self._gemini_model_combo.currentText())
        self._config.set_log_level(self._log_level_combo.currentText())

        prompt = self._prompt_edit.toPlainText().strip()
        if prompt:
            self._config.set_prompt_restore(prompt)

        translate_prompt = self._translate_prompt_edit.toPlainText().strip()
        if translate_prompt:
            self._config.set_prompt_translate(translate_prompt)

        # Reset Gemini client if API key changed
        if self._gemini_client:
            self._gemini_client.reset_client()

        logger.info("Settings saved")
        self.accept()

    def _test_connection(self):
        """測試 Gemini API 連線（使用下方選取的模型）。"""
        key = self._api_key_edit.text().strip()
        if not key:
            QMessageBox.warning(self, "Warning", "Please enter an API Key first.")
            return

        selected_model = self._gemini_model_combo.currentText().strip()
        if not selected_model:
            QMessageBox.warning(self, "Warning", "Please select or enter a Gemini model first.")
            return

        # Temporarily set key and model for testing
        self._config.set_gemini_api_key(key)
        self._config.set_gemini_model(selected_model)

        if self._gemini_client:
            self._gemini_client.reset_client()
            success, msg = self._gemini_client.test_connection()
            if success:
                QMessageBox.information(self, "Success", msg)
            else:
                QMessageBox.critical(self, "Error", msg)
        else:
            QMessageBox.information(self, "Info", "Gemini client not available for testing.")

    def _reset_prompt(self):
        """重設校對 Prompt 為預設值。"""
        from app.constants import PROMPT_PRECISE_RESTORE
        self._prompt_edit.setPlainText(PROMPT_PRECISE_RESTORE)

    def _reset_translate_prompt(self):
        """重設翻譯 Prompt 為預設值。"""
        from app.constants import PROMPT_TRANSLATE
        self._translate_prompt_edit.setPlainText(PROMPT_TRANSLATE)

    def _fetch_gemini_models(self):
        """從 API 動態取得可用的 Gemini 模型列表，並持久化。"""
        key = self._api_key_edit.text().strip()
        if not key:
            QMessageBox.warning(self, "Warning", "Please enter an API Key first.")
            return

        # Temporarily set key
        self._config.set_gemini_api_key(key)

        if self._gemini_client:
            self._gemini_client.reset_client()
            models = self._gemini_client.list_models()
            if models:
                current = self._gemini_model_combo.currentText()
                self._gemini_model_combo.clear()
                self._gemini_model_combo.addItems(models)
                # Persist model list
                self._config.set_gemini_model_list(models)
                # Restore previous selection if it exists
                idx = self._gemini_model_combo.findText(current)
                if idx >= 0:
                    self._gemini_model_combo.setCurrentIndex(idx)
                QMessageBox.information(
                    self, "Success",
                    f"Found {len(models)} models."
                )
            else:
                QMessageBox.warning(
                    self, "Warning",
                    "No models found. Please check your API Key."
                )
        else:
            QMessageBox.information(
                self, "Info",
                "Gemini client not available. Save settings and reopen."
            )
