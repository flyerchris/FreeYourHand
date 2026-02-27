"""
FreeYourHand - 聲紋動畫 Widget
自繪多條能量柱，根據 RMS 值動態變化，漸層色彩（青 → 紫）。
"""

import random
import math
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QPen
from PyQt6.QtWidgets import QWidget

from app.constants import (
    WAVEFORM_BAR_COUNT,
    WAVEFORM_BAR_WIDTH,
    WAVEFORM_BAR_GAP,
    WAVEFORM_FPS,
    WAVEFORM_MIN_HEIGHT,
    WAVEFORM_MAX_HEIGHT,
    WAVEFORM_SMOOTHING,
    COLOR_WAVEFORM_START,
    COLOR_WAVEFORM_END,
)


class WaveformWidget(QWidget):
    """
    即時聲紋動畫 Widget。
    多條柱狀圖隨 RMS 值動態跳動，60fps 重新渲染。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(WAVEFORM_MAX_HEIGHT + 10)

        # Bar states
        self._bar_count = WAVEFORM_BAR_COUNT
        self._target_heights = [WAVEFORM_MIN_HEIGHT] * self._bar_count
        self._current_heights = [WAVEFORM_MIN_HEIGHT] * self._bar_count
        self._bar_offsets = [random.uniform(0, math.pi * 2) for _ in range(self._bar_count)]

        # Animation
        self._rms = 0.0
        self._active = False
        self._tick = 0

        # Timer for 60fps rendering
        self._timer = QTimer(self)
        self._timer.setInterval(1000 // WAVEFORM_FPS)
        self._timer.timeout.connect(self._animate)

    def start(self):
        """開始動畫。"""
        self._active = True
        self._tick = 0
        self._timer.start()

    def stop(self):
        """停止動畫並歸零。"""
        self._active = False
        self._rms = 0.0
        self._timer.stop()
        # Animate down to zero
        self._target_heights = [WAVEFORM_MIN_HEIGHT] * self._bar_count
        self.update()

    def set_rms(self, rms: float):
        """設定當前 RMS 值（0.0 ~ 1.0）。"""
        self._rms = max(0.0, min(1.0, rms))

    def _animate(self):
        """每幀更新柱狀圖高度。"""
        self._tick += 1
        t = self._tick / WAVEFORM_FPS

        for i in range(self._bar_count):
            # Each bar has its own phase offset for organic movement
            phase = self._bar_offsets[i]

            # Combine RMS with sinusoidal movement
            wave = math.sin(t * 4.0 + phase) * 0.3 + 0.7
            jitter = random.uniform(0.85, 1.15)

            target = WAVEFORM_MIN_HEIGHT + (
                self._rms * WAVEFORM_MAX_HEIGHT * wave * jitter
            )
            target = max(WAVEFORM_MIN_HEIGHT, min(WAVEFORM_MAX_HEIGHT, target))
            self._target_heights[i] = target

            # Smooth interpolation
            self._current_heights[i] += (
                (self._target_heights[i] - self._current_heights[i]) * WAVEFORM_SMOOTHING
            )

        self.update()

    def paintEvent(self, event):
        """繪製聲紋柱狀圖。"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Calculate total width of all bars
        total_bar_width = (
            self._bar_count * WAVEFORM_BAR_WIDTH
            + (self._bar_count - 1) * WAVEFORM_BAR_GAP
        )
        start_x = (w - total_bar_width) / 2

        # Color gradient across bars
        c_start = QColor(*COLOR_WAVEFORM_START)
        c_end = QColor(*COLOR_WAVEFORM_END)

        for i in range(self._bar_count):
            # Interpolate color
            t = i / max(1, self._bar_count - 1)
            color = QColor(
                int(c_start.red() + (c_end.red() - c_start.red()) * t),
                int(c_start.green() + (c_end.green() - c_start.green()) * t),
                int(c_start.blue() + (c_end.blue() - c_start.blue()) * t),
                200,
            )

            bar_h = self._current_heights[i]
            x = start_x + i * (WAVEFORM_BAR_WIDTH + WAVEFORM_BAR_GAP)
            y = (h - bar_h) / 2  # Center vertically

            # Draw rounded bar
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            radius = WAVEFORM_BAR_WIDTH / 2
            painter.drawRoundedRect(
                QRectF(x, y, WAVEFORM_BAR_WIDTH, bar_h),
                radius, radius,
            )

        painter.end()
