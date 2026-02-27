"""
FreeYourHand - 麥克風錄音模組
使用 pyaudio 進行即時錄音，並計算 RMS 能量值供聲紋動畫使用。
"""

import os
import struct
import math
import tempfile
import wave
import threading
from PyQt6.QtCore import QObject, pyqtSignal

from app.constants import (
    AUDIO_SAMPLE_RATE,
    AUDIO_CHANNELS,
    AUDIO_CHUNK_SIZE,
    AUDIO_FORMAT_WIDTH,
)
from app.utils.logger import get_logger

logger = get_logger("audio")


class AudioRecorder(QObject):
    """
    麥克風錄音器。
    - 錄音時持續發射 RMS 能量值供 UI 動畫使用
    - 錄音完成後暫存為 WAV 檔案
    """

    # Signals
    rms_level = pyqtSignal(float)       # 0.0 ~ 1.0 normalized energy
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal(str) # file path of recorded WAV
    error_occurred = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pa = None
        self._stream = None
        self._frames: list[bytes] = []
        self._is_recording = False
        self._record_thread: threading.Thread | None = None

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    def start(self):
        """開始錄音（在背景線程中執行）。"""
        if self._is_recording:
            logger.warning("Already recording, ignoring start request")
            return

        self._frames = []
        self._is_recording = True
        self._record_thread = threading.Thread(target=self._record_loop, daemon=True)
        self._record_thread.start()
        self.recording_started.emit()
        logger.info("Recording started")

    def stop(self) -> str | None:
        """停止錄音並回傳 WAV 檔案路徑。"""
        if not self._is_recording:
            return None

        self._is_recording = False

        # Wait for recording thread to finish
        if self._record_thread and self._record_thread.is_alive():
            self._record_thread.join(timeout=2.0)

        frame_count = len(self._frames)
        duration = frame_count * AUDIO_CHUNK_SIZE / AUDIO_SAMPLE_RATE
        logger.info(f"Recording stopped: {frame_count} frames, {duration:.2f}s")

        if not self._frames:
            logger.warning("No audio frames recorded")
            return None

        if duration < 0.3:
            logger.warning(f"Recording too short ({duration:.2f}s), need at least 0.3s")
            return None

        # Save to temp WAV file
        try:
            wav_path = self._save_wav()
            file_size = os.path.getsize(wav_path)
            self.recording_stopped.emit(wav_path)
            logger.info(f"WAV saved: {wav_path} ({file_size} bytes, {duration:.1f}s)")
            return wav_path
        except Exception as e:
            error_msg = f"Failed to save recording: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return None

    def _record_loop(self):
        """錄音主迴圈（在背景線程中執行）。"""
        try:
            import pyaudio
            self._pa = pyaudio.PyAudio()
            self._stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=AUDIO_CHANNELS,
                rate=AUDIO_SAMPLE_RATE,
                input=True,
                frames_per_buffer=AUDIO_CHUNK_SIZE,
            )

            while self._is_recording:
                try:
                    data = self._stream.read(AUDIO_CHUNK_SIZE, exception_on_overflow=False)
                    self._frames.append(data)

                    # Calculate RMS and emit
                    rms = self._calculate_rms(data)
                    self.rms_level.emit(rms)
                except Exception as e:
                    if self._is_recording:
                        logger.error(f"Recording error: {e}")
                    break

        except Exception as e:
            error_msg = f"Failed to initialize recording: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
        finally:
            self._cleanup_stream()

    def _cleanup_stream(self):
        """清理音訊串流。"""
        try:
            if self._stream:
                self._stream.stop_stream()
                self._stream.close()
                self._stream = None
            if self._pa:
                self._pa.terminate()
                self._pa = None
        except Exception as e:
            logger.error(f"Stream cleanup error: {e}")

    def _calculate_rms(self, data: bytes) -> float:
        """計算音訊片段的 RMS 能量值（0.0 ~ 1.0）。"""
        try:
            count = len(data) // 2  # 16-bit samples
            shorts = struct.unpack(f"<{count}h", data)

            sum_squares = sum(s * s for s in shorts)
            rms = math.sqrt(sum_squares / count) if count > 0 else 0

            # Normalize to 0.0 ~ 1.0 (32768 = max for 16-bit)
            normalized = min(rms / 8000.0, 1.0)
            return normalized
        except Exception:
            return 0.0

    def _save_wav(self) -> str:
        """將錄音資料存為暫存 WAV 檔。"""
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_path = tmp.name
        tmp.close()

        with wave.open(tmp_path, "wb") as wf:
            wf.setnchannels(AUDIO_CHANNELS)
            wf.setsampwidth(AUDIO_FORMAT_WIDTH)
            wf.setframerate(AUDIO_SAMPLE_RATE)
            wf.writeframes(b"".join(self._frames))

        return tmp_path
