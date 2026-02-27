"""
FreeYourHand - Gemini API 校對模組
精確還原使用者語音內容，或翻譯為英文。
"""

from PyQt6.QtCore import QObject, pyqtSignal

from app.utils.logger import get_logger
from app.utils.config import Config

logger = get_logger("gemini")


class GeminiClient(QObject):
    """
    Gemini API 客戶端。
    - 精確還原模式：修正同音字、加標點、去贅詞
    - 翻譯模式：精確翻譯為英文
    """

    polish_done = pyqtSignal(str)        # polished text
    polish_error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._config = Config()
        self._client = None

    def _ensure_client(self):
        """確保 API 客戶端已初始化。"""
        api_key = self._config.gemini_api_key
        if not api_key:
            raise ValueError("Gemini API Key is not set. Please configure it in Settings.")

        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=api_key)
            logger.info("Gemini client initialized")

    def polish(self, transcript: str, translate: bool = False) -> str | None:
        """
        校對或翻譯語音辨識逐字稿。

        Args:
            transcript: 原始辨識文字
            translate: True=翻譯為英文, False=精確還原

        Returns:
            處理後的文字，或 None（失敗時）
        """
        if not transcript or not transcript.strip():
            logger.warning("Empty transcript, skipping polish")
            return transcript

        try:
            self._ensure_client()
        except ValueError as e:
            logger.error(str(e))
            self.polish_error.emit(str(e))
            return None

        # Choose prompt template
        if translate:
            prompt = self._config.prompt_translate.format(transcript=transcript)
            mode_str = "translate"
        else:
            prompt = self._config.prompt_restore.format(transcript=transcript)
            mode_str = "restore"

        logger.info(f"Polishing ({mode_str}): {transcript[:60]}...")

        try:
            model = self._config.gemini_model
            response = self._client.models.generate_content(
                model=model,
                contents=prompt,
            )

            result = response.text.strip()

            if result:
                logger.info(f"Polish result ({len(result)} chars): {result[:80]}...")
                self.polish_done.emit(result)
                return result
            else:
                logger.warning("Empty polish result")
                return transcript

        except Exception as e:
            error_msg = f"Gemini API error: {e}"
            logger.error(error_msg)
            self.polish_error.emit(error_msg)
            # Fallback: return raw transcript
            return transcript

    def test_connection(self) -> tuple[bool, str]:
        """
        測試 Gemini API 連線。
        回傳 (success, message) 元組。
        """
        try:
            self._ensure_client()
            model = self._config.gemini_model
            response = self._client.models.generate_content(
                model=model,
                contents="Hello, please respond with 'OK'.",
            )
            if response.text:
                return True, f"Connection successful (model: {model})"
            return False, "Empty response from API"
        except Exception as e:
            return False, f"Connection failed: {e}"

    def list_models(self) -> list[str]:
        """
        從 API 動態取得可用的 Gemini 模型列表。
        只回傳支援 generateContent 的模型。
        """
        try:
            self._ensure_client()
            models = []
            for model in self._client.models.list():
                name = model.name
                # Only include models that support generateContent
                methods = getattr(model, 'supported_actions', None) or \
                          getattr(model, 'supported_generation_methods', None) or []
                # The model name from API is like "models/gemini-2.0-flash"
                # Strip the "models/" prefix for display
                display_name = name.replace("models/", "") if name.startswith("models/") else name
                # Filter for gemini models only
                if "gemini" in display_name.lower():
                    models.append(display_name)
            logger.info(f"Found {len(models)} Gemini models")
            return sorted(models)
        except Exception as e:
            logger.warning(f"Failed to list models: {e}")
            return []

    def reset_client(self):
        """重置客戶端（用於 API Key 變更後）。"""
        self._client = None
        logger.info("Gemini client reset")
