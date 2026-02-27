"""
FreeYourHand - 剪貼簿與貼上模組
將處理後的文字寫入剪貼簿，並模擬 Cmd+V 貼至游標處。
"""

import subprocess
import time
from PyQt6.QtCore import QObject, pyqtSignal

from app.utils.logger import get_logger

logger = get_logger("clipboard")


class ClipboardManager(QObject):
    """
    剪貼簿管理器。
    - 寫入文字至剪貼簿
    - 模擬 Cmd+V 貼上至當前游標處
    """

    paste_done = pyqtSignal()
    paste_error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def copy_and_paste(self, text: str):
        """
        將文字寫入剪貼簿並模擬 Cmd+V 貼上。
        """
        if not text:
            logger.warning("Empty text, skipping copy & paste")
            return

        try:
            # Step 1: Write to clipboard using pbcopy (macOS native)
            self._copy_to_clipboard(text)

            # Step 2: Small delay to ensure clipboard is updated
            time.sleep(0.05)

            # Step 3: Simulate Cmd+V
            self._simulate_paste()

            logger.info(f"Pasted {len(text)} chars to cursor")
            self.paste_done.emit()

        except Exception as e:
            error_msg = f"Copy & paste failed: {e}"
            logger.error(error_msg)
            self.paste_error.emit(error_msg)

    def _copy_to_clipboard(self, text: str):
        """使用 pbcopy 寫入剪貼簿。"""
        process = subprocess.Popen(
            ["pbcopy"],
            stdin=subprocess.PIPE,
            env={"LANG": "en_US.UTF-8"},
        )
        process.communicate(text.encode("utf-8"))
        if process.returncode != 0:
            raise RuntimeError(f"pbcopy failed with code {process.returncode}")
        logger.debug("Text copied to clipboard")

    def _simulate_paste(self):
        """
        使用 osascript 模擬 Cmd+V 貼上。
        需要 Accessibility 權限。
        """
        script = '''
            tell application "System Events"
                key code 9 using command down
            end tell
        '''
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            raise RuntimeError(f"osascript Cmd+V failed: {result.stderr}")
        logger.debug("Cmd+V simulated")

    def copy_only(self, text: str):
        """只複製到剪貼簿，不自動貼上。"""
        try:
            self._copy_to_clipboard(text)
            logger.info(f"Copied {len(text)} chars to clipboard (no paste)")
        except Exception as e:
            logger.error(f"Copy failed: {e}")
            self.paste_error.emit(str(e))
