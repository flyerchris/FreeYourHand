"""
FreeYourHand - mlx-whisper 語音辨識引擎
支援多模型選擇與自動下載，Apple Silicon 最佳化。
"""

import os
import threading
from PyQt6.QtCore import QObject, pyqtSignal

from app.constants import WHISPER_MODELS, DEFAULT_WHISPER_MODEL
from app.utils.logger import get_logger
from app.utils.config import Config

logger = get_logger("whisper")


class WhisperEngine(QObject):
    """
    MLX Whisper 語音辨識引擎。
    可個別選擇模型進行語音轉文字。
    """

    transcription_done = pyqtSignal(str)    # transcribed text
    transcription_error = pyqtSignal(str)
    model_loading = pyqtSignal(str)         # model name being loaded
    model_ready = pyqtSignal(str)           # model name ready

    def __init__(self, parent=None):
        super().__init__(parent)
        self._config = Config()
        self._current_model = None

    def get_model_id(self, model_name: str | None = None) -> str:
        """取得模型的 HuggingFace ID。"""
        name = model_name or self._config.whisper_model
        return WHISPER_MODELS.get(name, WHISPER_MODELS[DEFAULT_WHISPER_MODEL])

    def transcribe(self, audio_path: str, language: str | None = None) -> str | None:
        """
        執行語音辨識（同步）。
        回傳辨識文字或 None。
        """
        model_name = self._config.whisper_model
        model_id = self.get_model_id(model_name)

        logger.info(f"Transcribing with model: {model_name} ({model_id})")
        self.model_loading.emit(model_name)

        try:
            import mlx_whisper

            # Log audio file info
            file_size = os.path.getsize(audio_path)
            logger.info(f"Audio file: {audio_path} ({file_size} bytes)")

            result = mlx_whisper.transcribe(
                audio_path,
                path_or_hf_repo=model_id,
                language=language,
            )

            # Log raw result for debugging
            text = result.get("text", "").strip()
            detected_lang = result.get("language", "unknown")
            segments = result.get("segments", [])
            logger.info(f"Whisper raw: language={detected_lang}, segments={len(segments)}, text_len={len(text)}")
            if segments:
                logger.debug(f"First segment: {segments[0]}")

            self.model_ready.emit(model_name)

            if text:
                logger.info(f"Transcription result ({len(text)} chars): {text[:80]}...")
                self.transcription_done.emit(text)
                return text
            else:
                logger.warning("Empty transcription result — Whisper returned no text")
                return None

        except Exception as e:
            error_msg = f"Transcription failed: {e}"
            logger.error(error_msg)
            self.transcription_error.emit(error_msg)
            return None

    def is_model_cached(self, model_name: str | None = None) -> bool:
        """檢查模型是否已下載到快取。"""
        try:
            from huggingface_hub import scan_cache_dir
            model_id = self.get_model_id(model_name)
            cache_info = scan_cache_dir()
            for repo in cache_info.repos:
                if repo.repo_id == model_id:
                    return True
            return False
        except Exception:
            return False

    def get_available_models(self) -> list[dict]:
        """取得可用模型列表及其快取狀態。"""
        models = []
        for name, model_id in WHISPER_MODELS.items():
            models.append({
                "name": name,
                "model_id": model_id,
                "cached": self.is_model_cached(name),
                "active": name == self._config.whisper_model,
            })
        return models

    def cleanup_temp_file(self, path: str):
        """清理暫存音訊檔案。"""
        try:
            if path and os.path.exists(path):
                os.unlink(path)
                logger.debug(f"Cleaned up temp file: {path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp file: {e}")
