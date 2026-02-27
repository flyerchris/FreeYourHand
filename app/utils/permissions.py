"""
FreeYourHand - 系統權限檢查模組
檢查麥克風權限與輔助使用權限（macOS）。
"""

import subprocess
import sys
from app.utils.logger import get_logger

logger = get_logger("permissions")


def check_microphone_permission() -> bool:
    """
    檢查麥克風權限。
    嘗試開啟音訊裝置，若失敗則代表未授權。
    """
    try:
        import pyaudio
        pa = pyaudio.PyAudio()
        # Try to open a stream to test permission
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1024,
        )
        stream.close()
        pa.terminate()
        logger.info("Microphone permission: granted")
        return True
    except Exception as e:
        logger.warning(f"Microphone permission: denied ({e})")
        return False


def check_accessibility_permission() -> bool:
    """
    檢查輔助使用（Accessibility）權限。
    使用 pyobjc 的 AXIsProcessTrusted 來判斷。
    """
    try:
        from ApplicationServices import AXIsProcessTrusted
        trusted = AXIsProcessTrusted()
        if trusted:
            logger.info("Accessibility permission: granted")
        else:
            logger.warning("Accessibility permission: denied")
        return bool(trusted)
    except ImportError:
        logger.warning("pyobjc not available, skipping accessibility check")
        return False
    except Exception as e:
        logger.warning(f"Accessibility check error: {e}")
        return False


def request_accessibility_permission():
    """
    引導使用者開啟輔助使用權限設定頁面。
    """
    try:
        subprocess.run([
            "open",
            "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
        ], check=True)
        logger.info("Opened Accessibility settings page")
    except Exception as e:
        logger.error(f"Failed to open Accessibility settings: {e}")


def request_microphone_permission():
    """
    引導使用者開啟麥克風權限設定頁面。
    """
    try:
        subprocess.run([
            "open",
            "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone"
        ], check=True)
        logger.info("Opened Microphone settings page")
    except Exception as e:
        logger.error(f"Failed to open Microphone settings: {e}")


def check_all_permissions() -> dict:
    """
    檢查所有必要權限並回傳狀態。
    """
    return {
        "microphone": check_microphone_permission(),
        "accessibility": check_accessibility_permission(),
    }
