"""
FreeYourHand - 全局快捷鍵監聽模組
偵測 Right Option 長按 / 釋放，以及 Shift 修飾鍵。
"""

import threading
import time
from pynput import keyboard
from PyQt6.QtCore import QObject, pyqtSignal

from app.utils.logger import get_logger
from app.utils.config import Config

logger = get_logger("hotkey")


class HotkeyListener(QObject):
    """
    全局快捷鍵監聽器。
    - 長按 Right Option → 開始錄音
    - 放開 Right Option → 停止錄音
    - 同時按住 Shift → 翻譯模式
    """

    key_pressed = pyqtSignal(bool)   # True = translate mode (shift held)
    key_released = pyqtSignal(bool)  # True = translate mode (shift was pressed during recording)
    listener_error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._listener: keyboard.Listener | None = None
        self._hotkey_pressed = False
        self._shift_pressed = False
        self._shift_during_recording = False  # Shift pressed at any point during recording
        self._config = Config()
        self._running = False

    def start(self):
        """啟動全局鍵盤監聽。"""
        if self._running:
            return

        self._running = True
        try:
            self._listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
            )
            self._listener.daemon = True
            self._listener.start()
            logger.info("Hotkey listener started")
        except Exception as e:
            error_msg = f"Failed to start hotkey listener: {e}"
            logger.error(error_msg)
            self.listener_error.emit(error_msg)

    def stop(self):
        """停止全局鍵盤監聽。"""
        self._running = False
        if self._listener:
            self._listener.stop()
            self._listener = None
            logger.info("Hotkey listener stopped")

    def _get_key_name(self, key) -> str:
        """取得按鍵名稱字串。"""
        if isinstance(key, keyboard.Key):
            return key.name
        elif hasattr(key, 'vk'):
            return f"vk_{key.vk}"
        return str(key)

    def _is_hotkey(self, key) -> bool:
        """判斷是否為設定的觸發鍵。"""
        hotkey = self._config.hotkey
        # Handle Key.alt_r
        if hotkey == "Key.alt_r":
            return (isinstance(key, keyboard.Key) and key == keyboard.Key.alt_r)
        # Handle Key.alt_gr (some keyboards)
        if hotkey == "Key.alt_gr":
            return (isinstance(key, keyboard.Key) and key == keyboard.Key.alt_gr)
        # Handle custom key string
        key_name = self._get_key_name(key)
        return key_name == hotkey.replace("Key.", "")

    def _is_shift(self, key) -> bool:
        """判斷是否為 Shift 鍵。"""
        if isinstance(key, keyboard.Key):
            return key in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r)
        return False

    def _on_press(self, key):
        """按鍵按下事件。"""
        if not self._running:
            return False

        # Track shift state
        if self._is_shift(key):
            self._shift_pressed = True
            # If hotkey is already held, mark translate mode
            if self._hotkey_pressed:
                self._shift_during_recording = True
                logger.debug("Shift pressed during recording → translate mode")

        # Hotkey pressed
        if self._is_hotkey(key) and not self._hotkey_pressed:
            self._hotkey_pressed = True
            self._shift_during_recording = self._shift_pressed
            translate_mode = self._shift_pressed
            logger.debug(f"Hotkey pressed (translate={translate_mode})")
            self.key_pressed.emit(translate_mode)

    def _on_release(self, key):
        """按鍵釋放事件。"""
        if not self._running:
            return False

        # Track shift state
        if self._is_shift(key):
            self._shift_pressed = False

        # Hotkey released
        if self._is_hotkey(key) and self._hotkey_pressed:
            self._hotkey_pressed = False
            translate = self._shift_during_recording
            self._shift_during_recording = False
            logger.debug(f"Hotkey released (translate={translate})")
            self.key_released.emit(translate)
