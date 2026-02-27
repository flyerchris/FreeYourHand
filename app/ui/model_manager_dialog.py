"""
FreeYourHand - 模型下載管理 UI
列出可用 Whisper 模型，顯示下載進度，管理快取。
支援下載、刪除已下載模型、開啟快取資料夾。
"""

import os
import shutil
import subprocess
from pathlib import Path
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QWidget,
    QPushButton, QProgressBar, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox,
)

from app.constants import WHISPER_MODELS
from app.core.whisper_engine import WhisperEngine
from app.utils.logger import get_logger

logger = get_logger("model_manager")


class ModelDownloadWorker(QThread):
    """背景下載 Worker。"""
    progress = pyqtSignal(str)
    finished_ok = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, model_id: str):
        super().__init__()
        self.model_id = model_id

    def run(self):
        try:
            self.progress.emit(f"Downloading {self.model_id}...")
            from huggingface_hub import snapshot_download
            snapshot_download(repo_id=self.model_id)
            self.finished_ok.emit(self.model_id)
        except Exception as e:
            self.error.emit(str(e))


DARK_STYLE = """
QDialog { background-color: #1a1a2e; color: #e0e0e0; }
QTableWidget {
    background-color: #16162a; color: #e0e0e0;
    border: 1px solid #2d2d4a; border-radius: 6px;
    gridline-color: #2d2d4a;
}
QTableWidget::item { padding: 4px; }
QTableWidget::item:selected { background-color: #00a0cc; }
QHeaderView::section {
    background-color: #1e1e3a; color: #8888aa;
    padding: 8px; border: none; font-weight: bold;
}
QPushButton {
    height: 14px;
    background-color: #2a2a50; color: #e0e0e0;
    border: 1px solid #3a3a5e; border-radius: 6px;
    padding: 2px 12px; font-size: 12px;
}
QPushButton:hover { background-color: #3a3a60; border-color: #00d2ff; }
QPushButton#download { background-color: #00a0cc; color: white; border: none; }
QPushButton#download:hover { background-color: #00b8e6; }
QPushButton#delete { background-color: #cc3333; color: white; border: none; }
QPushButton#delete:hover { background-color: #e04040; }
QPushButton:disabled { background-color: #1a1a2e; color: #555; }
QProgressBar {
    background-color: #222244; border: 1px solid #3a3a5e;
    border-radius: 4px; text-align: center; color: #e0e0e0;
}
QProgressBar::chunk { background-color: #00d2ff; border-radius: 3px; }
QLabel { color: #b0b0d0; }
"""


class ModelManagerDialog(QDialog):
    """模型管理對話框。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._engine = WhisperEngine()
        self._worker: ModelDownloadWorker | None = None

        self.setWindowTitle("Whisper Model Manager")
        self.setMinimumSize(600, 420)
        self.setStyleSheet(DARK_STYLE)

        self._setup_ui()
        self._refresh_models()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("🎙  Whisper 模型管理")
        title.setFont(QFont("SF Pro Display", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #ffffff;")
        header.addWidget(title)

        header.addStretch()

        btn_open_folder = QPushButton("📂  Open Cache Folder")
        btn_open_folder.clicked.connect(self._open_cache_folder)
        header.addWidget(btn_open_folder)

        layout.addLayout(header)

        # Model table — 4 columns
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Model", "Size", "Status", "Action"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(3, 120)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(32)
        layout.addWidget(self._table)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)  # Indeterminate
        self._progress.hide()
        layout.addWidget(self._progress)

        # Status label
        self._status = QLabel("")
        self._status.setStyleSheet("font-size: 11px; color: #666688;")
        layout.addWidget(self._status)

        # Close button
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)

    def _get_cache_path(self, model_id: str) -> str:
        """取得模型的 HuggingFace 快取路徑。"""
        folder_name = f"models--{model_id.replace('/', '--')}"
        return str(Path.home() / ".cache" / "huggingface" / "hub" / folder_name)

    def _get_cache_size(self, cache_path: str) -> float:
        """計算快取資料夾大小（MB），只算 blobs 避免 symlink 重複計算。"""
        blobs_path = os.path.join(cache_path, "blobs")
        if not os.path.exists(blobs_path):
            return 0.0
        total = 0
        for dirpath, _, filenames in os.walk(blobs_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    total += os.path.getsize(fp)
        return total / 1024 / 1024

    def _refresh_models(self):
        """刷新模型列表。"""
        models = self._engine.get_available_models()
        self._table.setRowCount(len(models))

        total_cached_mb = 0.0

        for i, model in enumerate(models):
            cache_path = self._get_cache_path(model["model_id"])
            size_mb = self._get_cache_size(cache_path)
            if model["cached"]:
                total_cached_mb += size_mb

            # Name
            name_item = QTableWidgetItem(model["name"])
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if model["active"]:
                name_item.setFont(QFont("", -1, QFont.Weight.Bold))
                name_item.setText(f"✦ {model['name']}")
            self._table.setItem(i, 0, name_item)

            # Size
            if model["cached"]:
                size_text = f"{size_mb:.0f} MB"
            else:
                size_text = "—"
            size_item = QTableWidgetItem(size_text)
            size_item.setFlags(size_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(i, 1, size_item)

            # Status
            status = "✅ Downloaded" if model["cached"] else "⬇ Not downloaded"
            status_item = QTableWidgetItem(status)
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(i, 2, status_item)

            # Action buttons
            if model["cached"]:
                btn = QPushButton("Delete")
                btn.setObjectName("delete")
                btn.clicked.connect(
                    lambda _, n=model["name"], mid=model["model_id"]: self._delete_model(n, mid)
                )
                self._table.setCellWidget(i, 3, btn)
            else:
                btn = QPushButton("Download")
                btn.setObjectName("download")
                btn.clicked.connect(lambda _, m=model["model_id"]: self._download_model(m))
                self._table.setCellWidget(i, 3, btn)

        self._status.setText(f"Total cache: {total_cached_mb:.0f} MB")

    def _download_model(self, model_id: str):
        """開始下載模型。"""
        if self._worker and self._worker.isRunning():
            QMessageBox.warning(self, "Warning", "A download is already in progress.")
            return

        self._progress.show()
        self._status.setText(f"Downloading {model_id}...")

        self._worker = ModelDownloadWorker(model_id)
        self._worker.finished_ok.connect(self._on_download_done)
        self._worker.error.connect(self._on_download_error)
        self._worker.start()

    def _delete_model(self, model_name: str, model_id: str):
        """刪除已下載的模型。"""
        cache_path = self._get_cache_path(model_id)
        size_mb = self._get_cache_size(cache_path)

        reply = QMessageBox.question(
            self, "Delete Model",
            f"確定要刪除 '{model_name}' 嗎？\n\n"
            f"大小：{size_mb:.0f} MB\n"
            f"路徑：{cache_path}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                shutil.rmtree(cache_path)
                self._status.setText(f"✅ '{model_name}' deleted ({size_mb:.0f} MB freed)")
                self._refresh_models()
                logger.info(f"Deleted model: {model_name} ({size_mb:.0f} MB)")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete: {e}")

    def _open_cache_folder(self):
        """在 Finder 中開啟 HuggingFace 快取資料夾。"""
        cache_dir = str(Path.home() / ".cache" / "huggingface" / "hub")
        if os.path.exists(cache_dir):
            subprocess.run(["open", cache_dir])
        else:
            QMessageBox.information(self, "Info", "Cache folder not found.")

    def _on_download_done(self, model_id: str):
        self._progress.hide()
        self._status.setText(f"✅ {model_id} downloaded successfully!")
        self._refresh_models()
        logger.info(f"Model downloaded: {model_id}")

    def _on_download_error(self, error: str):
        self._progress.hide()
        self._status.setText(f"❌ Download failed: {error}")
        logger.error(f"Model download failed: {error}")
