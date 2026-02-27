"""
FreeYourHand - 底部透明懸浮視窗
錄音時顯示聲紋動畫，處理中顯示旋轉動畫，完成後顯示結果。
"""

import math
from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve,
    QRectF, QPointF, pyqtProperty,
)
from PyQt6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush,
    QLinearGradient, QConicalGradient, QPainterPath,
)
from PyQt6.QtWidgets import QWidget, QApplication, QVBoxLayout, QLabel

from app.constants import (
    OVERLAY_HEIGHT, OVERLAY_MARGIN_BOTTOM, OVERLAY_BORDER_RADIUS,
    OVERLAY_OPACITY, COLOR_BG, COLOR_PROCESSING, COLOR_SUCCESS,
    COLOR_ERROR, COLOR_TEXT, COLOR_TEXT_DIM,
)
from app.core.pipeline import PipelineState
from app.ui.waveform_widget import WaveformWidget
from app.utils.logger import get_logger

logger = get_logger("overlay")


class OverlayWindow(QWidget):
    """
    底部透明懸浮窗。
    狀態：IDLE(隱藏) → RECORDING(聲紋) → PROCESSING(旋轉) → DONE(文字)
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Window flags: frameless, always on top, transparent, tool window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        # State
        self._state = PipelineState.IDLE
        self._status_text = ""
        self._spinner_angle = 0.0

        # Spinner animation timer
        self._spinner_timer = QTimer(self)
        self._spinner_timer.setInterval(16)  # ~60fps
        self._spinner_timer.timeout.connect(self._update_spinner)

        # Setup UI
        self._setup_ui()
        self._position_window()

        # Initially hidden
        self.hide()

        # macOS: ensure window never steals focus
        self._setup_macos_no_focus()

    def _setup_ui(self):
        """建構 UI 元件。"""
        self.setFixedHeight(OVERLAY_HEIGHT)

        # Main layout
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 10, 20, 10)

        # Waveform widget
        self._waveform = WaveformWidget(self)
        self._layout.addWidget(self._waveform)
        self._waveform.hide()

        # Status label (for processing / done / error)
        self._status_label = QLabel(self)
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setFont(QFont("SF Pro Display", 14, QFont.Weight.Medium))
        self._status_label.setStyleSheet(
            f"color: rgba({COLOR_TEXT[0]},{COLOR_TEXT[1]},{COLOR_TEXT[2]},{COLOR_TEXT[3]});"
            "background: transparent;"
        )
        self._layout.addWidget(self._status_label)
        self._status_label.hide()

    def _position_window(self):
        """將視窗置於螢幕底部中央。"""
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geom = screen.availableGeometry()
        width = min(500, int(geom.width() * 0.35))

        x = geom.x() + (geom.width() - width) // 2
        y = geom.y() + geom.height() - OVERLAY_HEIGHT - OVERLAY_MARGIN_BOTTOM

        self.setGeometry(x, y, width, OVERLAY_HEIGHT)

    def _setup_macos_no_focus(self):
        """macOS: 設定 NSWindow 層級，確保不搶焦點。"""
        try:
            from AppKit import NSApp, NSFloatingWindowLevel
            ns_view = self.winId().__int__()
            # Find the NSWindow for this widget
            for window in NSApp.windows():
                if window.contentView() and window.contentView().window() == window:
                    # Check if this is our window by matching geometry
                    pass
            # Alternative: use objc to get the NSWindow directly
            import ctypes
            import objc
            ns_window = objc.objc_object(c_void_p=ctypes.c_void_p(int(self.winId())))
            if hasattr(ns_window, 'window'):
                ns_win = ns_window.window()
                ns_win.setLevel_(NSFloatingWindowLevel)
                ns_win.setCollectionBehavior_(1 << 0)  # canJoinAllSpaces
                ns_win.setHidesOnDeactivate_(False)
                logger.debug("macOS NSWindow configured for no-focus overlay")
        except Exception as e:
            logger.debug(f"macOS NSWindow setup skipped: {e}")

    def _show_no_focus(self):
        """顯示視窗但不搶焦點。"""
        self.show()
        try:
            from AppKit import NSApp
            for window in NSApp.windows():
                frame = window.frame()
                # Match by position (our overlay is at screen bottom)
                if abs(frame.size.height - OVERLAY_HEIGHT) < 5:
                    window.orderFrontRegardless()
                    break
        except Exception:
            self.raise_()

    def set_state(self, state: PipelineState):
        """更新顯示狀態。"""
        old = self._state
        self._state = state

        if state == PipelineState.IDLE:
            self._hide_all()
            self._spinner_timer.stop()
            self.hide()

        elif state == PipelineState.RECORDING:
            self._show_no_focus()
            self._status_label.hide()
            self._waveform.show()
            self._waveform.start()
            self._spinner_timer.stop()

        elif state in (PipelineState.TRANSCRIBING, PipelineState.POLISHING):
            self._waveform.stop()
            self._waveform.hide()
            label = "辨識中..." if state == PipelineState.TRANSCRIBING else "校對中..."
            self._status_text = label
            self._status_label.setText(f"  {label}")
            self._status_label.show()
            self._spinner_timer.start()
            self._show_no_focus()

        elif state == PipelineState.PASTING:
            self._spinner_timer.stop()
            self._status_text = "貼上中..."
            self._status_label.setText("✦  貼上中...")
            self._status_label.show()

        elif state == PipelineState.DONE:
            self._spinner_timer.stop()
            self._status_label.setText("✓  完成")
            self._status_label.setStyleSheet(
                f"color: rgba({COLOR_SUCCESS[0]},{COLOR_SUCCESS[1]},{COLOR_SUCCESS[2]},230);"
                "background: transparent; font-weight: bold;"
            )
            self._status_label.show()

        elif state == PipelineState.ERROR:
            self._spinner_timer.stop()
            self._status_label.setText("✗  發生錯誤")
            self._status_label.setStyleSheet(
                f"color: rgba({COLOR_ERROR[0]},{COLOR_ERROR[1]},{COLOR_ERROR[2]},230);"
                "background: transparent; font-weight: bold;"
            )
            self._status_label.show()

        self.update()

    def set_rms(self, rms: float):
        """更新 RMS 值至聲紋動畫。"""
        self._waveform.set_rms(rms)

    def _hide_all(self):
        """隱藏所有子元件。"""
        self._waveform.stop()
        self._waveform.hide()
        self._status_label.hide()
        # Reset label style
        self._status_label.setStyleSheet(
            f"color: rgba({COLOR_TEXT[0]},{COLOR_TEXT[1]},{COLOR_TEXT[2]},{COLOR_TEXT[3]});"
            "background: transparent;"
        )

    def _update_spinner(self):
        """更新旋轉角度。"""
        self._spinner_angle = (self._spinner_angle + 5) % 360
        self.update()

    # ── Custom painting ───────────────────────────────────

    def paintEvent(self, event):
        """繪製半透明圓角背景與旋轉動畫。"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw rounded rect background
        path = QPainterPath()
        rect = QRectF(0, 0, self.width(), self.height())
        path.addRoundedRect(rect, OVERLAY_BORDER_RADIUS, OVERLAY_BORDER_RADIUS)

        # Semi-transparent dark background with subtle gradient
        grad = QLinearGradient(0, 0, self.width(), 0)
        grad.setColorAt(0.0, QColor(COLOR_BG[0], COLOR_BG[1], COLOR_BG[2], COLOR_BG[3]))
        grad.setColorAt(1.0, QColor(
            COLOR_BG[0] + 10, COLOR_BG[1] + 5, COLOR_BG[2] + 20, COLOR_BG[3]
        ))
        painter.fillPath(path, QBrush(grad))

        # Subtle border
        painter.setPen(QPen(QColor(255, 255, 255, 30), 1))
        painter.drawPath(path)

        # Draw spinner if in processing state
        if self._state in (PipelineState.TRANSCRIBING, PipelineState.POLISHING):
            self._draw_spinner(painter)

        painter.end()

    def _draw_spinner(self, painter: QPainter):
        """繪製旋轉中的載入動畫。"""
        cx = 30  # spinner center x
        cy = self.height() / 2
        radius = 12

        # Conical gradient for spinner effect
        gradient = QConicalGradient(QPointF(cx, cy), -self._spinner_angle)
        color = QColor(*COLOR_PROCESSING)
        gradient.setColorAt(0.0, color)
        gradient.setColorAt(0.7, QColor(color.red(), color.green(), color.blue(), 40))
        gradient.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 0))

        pen = QPen(QBrush(gradient), 3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(
            QRectF(cx - radius, cy - radius, radius * 2, radius * 2),
            int(self._spinner_angle * 16),
            270 * 16,
        )
