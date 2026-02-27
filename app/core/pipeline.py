"""
FreeYourHand - AI 處理流水線
串接 AudioRecorder → WhisperEngine → GeminiClient → ClipboardManager
使用 QThread 避免阻塞 UI。
"""

import os
from enum import Enum, auto
from PyQt6.QtCore import QObject, QThread, pyqtSignal

from app.core.audio_recorder import AudioRecorder
from app.core.whisper_engine import WhisperEngine
from app.core.gemini_client import GeminiClient
from app.core.clipboard import ClipboardManager
from app.utils.logger import get_logger

logger = get_logger("pipeline")


class PipelineState(Enum):
    IDLE = auto()
    RECORDING = auto()
    TRANSCRIBING = auto()
    POLISHING = auto()
    PASTING = auto()
    DONE = auto()
    ERROR = auto()


class ProcessingWorker(QObject):
    """在背景線程中執行辨識 + 校對 + 貼上的 Worker。"""

    state_changed = pyqtSignal(object)     # PipelineState
    result_ready = pyqtSignal(str)         # final text
    error_occurred = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, audio_path: str, translate: bool,
                 whisper: WhisperEngine, gemini: GeminiClient,
                 clipboard: ClipboardManager):
        super().__init__()
        self.audio_path = audio_path
        self.translate = translate
        self.whisper = whisper
        self.gemini = gemini
        self.clipboard = clipboard

    def run(self):
        """執行完整處理流程。"""
        try:
            # Step 1: Transcribe
            self.state_changed.emit(PipelineState.TRANSCRIBING)
            logger.info("Pipeline: transcribing...")

            transcript = self.whisper.transcribe(self.audio_path)

            # Clean up temp audio file
            self.whisper.cleanup_temp_file(self.audio_path)

            if not transcript:
                self.error_occurred.emit("No speech detected")
                self.state_changed.emit(PipelineState.ERROR)
                self.finished.emit()
                return

            # Step 2: Polish with Gemini
            self.state_changed.emit(PipelineState.POLISHING)
            logger.info("Pipeline: polishing...")

            result = self.gemini.polish(transcript, translate=self.translate)

            if not result:
                # Fallback to raw transcript
                result = transcript
                logger.warning("Polish failed, using raw transcript")

            # Step 3: Copy & Paste
            self.state_changed.emit(PipelineState.PASTING)
            logger.info("Pipeline: pasting...")

            self.clipboard.copy_and_paste(result)

            # Done
            self.state_changed.emit(PipelineState.DONE)
            self.result_ready.emit(result)
            logger.info(f"Pipeline complete: {result[:60]}...")

        except Exception as e:
            error_msg = f"Pipeline error: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            self.state_changed.emit(PipelineState.ERROR)

        finally:
            self.finished.emit()


class Pipeline(QObject):
    """
    主流水線控制器。
    管理錄音 → 辨識 → 校對 → 貼上的完整流程。
    """

    state_changed = pyqtSignal(object)      # PipelineState
    rms_level = pyqtSignal(float)            # for waveform animation
    result_ready = pyqtSignal(str)           # final text
    error_occurred = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Components
        self.recorder = AudioRecorder()
        self.whisper = WhisperEngine()
        self.gemini = GeminiClient()
        self.clipboard = ClipboardManager()

        # State
        self._state = PipelineState.IDLE
        self._translate_mode = False
        self._worker: ProcessingWorker | None = None
        self._thread: QThread | None = None

        # Wire recorder signals
        self.recorder.rms_level.connect(self.rms_level.emit)
        self.recorder.error_occurred.connect(self._on_error)

    @property
    def state(self) -> PipelineState:
        return self._state

    def start_recording(self, translate: bool = False):
        """使用者按下快捷鍵 → 開始錄音。"""
        if self._state != PipelineState.IDLE:
            logger.warning(f"Cannot start recording in state {self._state}")
            return

        self._translate_mode = translate
        self._set_state(PipelineState.RECORDING)
        self.recorder.start()

    def stop_recording(self, translate: bool = False):
        """使用者放開快捷鍵 → 停止錄音，啟動處理。"""
        if self._state != PipelineState.RECORDING:
            logger.warning(f"Cannot stop recording in state {self._state}")
            return

        # Use translate if Shift was pressed at any point during recording
        if translate:
            self._translate_mode = True
            logger.info("Translate mode activated (Shift was pressed during recording)")

        audio_path = self.recorder.stop()

        if not audio_path:
            self._set_state(PipelineState.IDLE)
            return

        # Start processing in background thread
        self._start_processing(audio_path, self._translate_mode)

    def cancel(self):
        """取消當前操作。"""
        if self._state == PipelineState.RECORDING:
            self.recorder.stop()
        # Note: can't easily cancel running inference, just reset state
        self._set_state(PipelineState.IDLE)
        logger.info("Pipeline cancelled")

    def _start_processing(self, audio_path: str, translate: bool):
        """在背景線程啟動辨識 + 校對 + 貼上。"""
        self._thread = QThread()
        self._worker = ProcessingWorker(
            audio_path, translate,
            self.whisper, self.gemini, self.clipboard,
        )
        self._worker.moveToThread(self._thread)

        # Connect signals
        self._thread.started.connect(self._worker.run)
        self._worker.state_changed.connect(self._set_state)
        self._worker.result_ready.connect(self.result_ready.emit)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.finished.connect(self._on_processing_done)

        self._thread.start()

    def _on_processing_done(self):
        """處理完成後清理線程。"""
        if self._thread:
            self._thread.quit()
            self._thread.wait()
            self._thread = None
            self._worker = None

        # Auto-return to IDLE after a short display of DONE
        if self._state == PipelineState.DONE:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(1500, lambda: self._set_state(PipelineState.IDLE))

    def _set_state(self, state: PipelineState):
        """更新流水線狀態。"""
        old_state = self._state
        self._state = state
        logger.debug(f"Pipeline state: {old_state.name} → {state.name}")
        self.state_changed.emit(state)

    def _on_error(self, message: str):
        """處理錯誤。"""
        self.error_occurred.emit(message)
        # Auto-return to IDLE after error display
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(3000, lambda: self._set_state(PipelineState.IDLE))
