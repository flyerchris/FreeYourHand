"""
FreeYourHand - 全局日誌系統
支援 Console + 檔案輸出，並推送日誌至 UI LogViewer。
"""

import logging
import os
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal

from app.constants import APP_NAME, LOG_FILE_NAME, LOG_MAX_LINES


class LogSignalEmitter(QObject):
    """Qt Signal 發射器，用於將日誌推送至 UI。"""
    log_message = pyqtSignal(str, str, str)  # level, timestamp, message


class QtLogHandler(logging.Handler):
    """自訂 Handler，將日誌透過 Qt Signal 推送至 UI。"""

    def __init__(self, emitter: LogSignalEmitter):
        super().__init__()
        self.emitter = emitter

    def emit(self, record: logging.LogRecord):
        try:
            timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
            self.emitter.log_message.emit(
                record.levelname, timestamp, self.format(record)
            )
        except Exception:
            self.handleError(record)


# ── Singleton logger instance ─────────────────────────────

_log_emitter = LogSignalEmitter()
_logger: logging.Logger | None = None


def get_log_emitter() -> LogSignalEmitter:
    """取得日誌 Signal 發射器，供 LogViewer 連接。"""
    return _log_emitter


def setup_logger(log_dir: str | None = None, level: int = logging.DEBUG) -> logging.Logger:
    """初始化全局日誌系統。"""
    global _logger

    if _logger is not None:
        return _logger

    logger = logging.getLogger(APP_NAME)
    logger.setLevel(level)
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, LOG_FILE_NAME)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Qt Signal handler (for UI)
    qt_handler = QtLogHandler(_log_emitter)
    qt_handler.setLevel(logging.DEBUG)
    qt_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(qt_handler)

    _logger = logger
    logger.info("Logger initialized")
    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """取得子日誌器。"""
    base = APP_NAME
    if name:
        return logging.getLogger(f"{base}.{name}")
    return logging.getLogger(base)
