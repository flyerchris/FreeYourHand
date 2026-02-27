"""
FreeYourHand - 設定持久化模組
使用 QSettings 管理所有使用者偏好設定。
"""

from PyQt6.QtCore import QSettings, QObject, pyqtSignal
from app.constants import (
    APP_NAME,
    APP_ORG,
    DEFAULT_HOTKEY,
    DEFAULT_WHISPER_MODEL,
    DEFAULT_GEMINI_MODEL,
    PROMPT_PRECISE_RESTORE,
    PROMPT_TRANSLATE,
)


class Config(QObject):
    """Application configuration manager backed by QSettings."""

    config_changed = pyqtSignal(str, object)  # key, new_value

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self._settings = QSettings(APP_ORG, APP_NAME)
        self._initialized = True

    # ── Getters with defaults ─────────────────────────────

    @property
    def hotkey(self) -> str:
        return self._settings.value("hotkey", DEFAULT_HOTKEY, type=str)

    @property
    def whisper_model(self) -> str:
        return self._settings.value("whisper_model", DEFAULT_WHISPER_MODEL, type=str)

    @property
    def gemini_model(self) -> str:
        return self._settings.value("gemini_model", DEFAULT_GEMINI_MODEL, type=str)

    @property
    def gemini_api_key(self) -> str:
        return self._settings.value("gemini_api_key", "", type=str)

    @property
    def prompt_restore(self) -> str:
        return self._settings.value("prompt_restore", PROMPT_PRECISE_RESTORE, type=str)

    @property
    def prompt_translate(self) -> str:
        return self._settings.value("prompt_translate", PROMPT_TRANSLATE, type=str)

    @property
    def first_launch(self) -> bool:
        return self._settings.value("first_launch", True, type=bool)

    @property
    def log_level(self) -> str:
        return self._settings.value("log_level", "DEBUG", type=str)

    # ── Setters ───────────────────────────────────────────

    def set(self, key: str, value):
        """Set a config value and emit change signal."""
        self._settings.setValue(key, value)
        self._settings.sync()
        self.config_changed.emit(key, value)

    def set_hotkey(self, value: str):
        self.set("hotkey", value)

    def set_whisper_model(self, value: str):
        self.set("whisper_model", value)

    def set_gemini_api_key(self, value: str):
        self.set("gemini_api_key", value)

    def set_gemini_model(self, value: str):
        self.set("gemini_model", value)

    def set_prompt_restore(self, value: str):
        self.set("prompt_restore", value)

    def set_prompt_translate(self, value: str):
        self.set("prompt_translate", value)

    def mark_launched(self):
        self.set("first_launch", False)

    def set_log_level(self, value: str):
        self.set("log_level", value)

    # ── Utilities ─────────────────────────────────────────

    @property
    def gemini_model_list(self) -> list:
        """Previously fetched Gemini model list."""
        val = self._settings.value("gemini_model_list", [], type=list)
        return val if val else []

    def set_gemini_model_list(self, models: list):
        self.set("gemini_model_list", models)

    def reset_prompts(self):
        """Reset prompts to defaults."""
        self.set_prompt_restore(PROMPT_PRECISE_RESTORE)
        self.set_prompt_translate(PROMPT_TRANSLATE)

    def all_settings(self) -> dict:
        """Return all current settings as a dict for debugging."""
        return {
            "hotkey": self.hotkey,
            "whisper_model": self.whisper_model,
            "gemini_model": self.gemini_model,
            "gemini_api_key": "***" if self.gemini_api_key else "(not set)",
            "log_level": self.log_level,
            "first_launch": self.first_launch,
        }
