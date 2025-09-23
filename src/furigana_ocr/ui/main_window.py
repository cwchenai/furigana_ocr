"""Main application window and orchestration logic."""

from __future__ import annotations

import traceback
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, QThread, QTimer, Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from ..config import AppConfig
from ..core.models import Region, TokenAnnotation
from ..services.pipeline import ProcessingPipeline
from .overlay import OverlayState, OverlayWindow
from .region_selector import RegionSelector
from .system_tray import SystemTrayController


class _PipelineWorker(QObject):
    finished = Signal(list)
    failed = Signal(object)

    def __init__(self, pipeline: ProcessingPipeline, region: Region) -> None:
        super().__init__()
        self._pipeline = pipeline
        self._region = region

    def run(self) -> None:
        try:
            annotations = self._pipeline.process_region(self._region)
        except Exception as exc:  # pragma: no cover - defensive
            self.failed.emit(exc)
        else:
            self.finished.emit(annotations)


class MainWindow(QMainWindow):
    """Primary window managing user interaction and scheduling."""

    def __init__(self, config: AppConfig, pipeline: ProcessingPipeline) -> None:
        super().__init__()
        self.config = config
        self.pipeline = pipeline

        self._status_bar = QStatusBar(self)
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("尚未啟動")

        self._start_button = QPushButton("開始")
        self._trigger_button = QPushButton("強制觸發")
        self._trigger_button.setEnabled(False)
        self._end_button = QPushButton("結束")

        self._engine_selector = QComboBox()
        self._engine_selector.addItem("Tesseract", "tesseract")
        self._engine_selector.addItem("PaddleOCR", "paddle")
        current_engine = self.config.capture.engine.lower()
        index = self._engine_selector.findData(current_engine)
        if index >= 0:
            self._engine_selector.setCurrentIndex(index)
        else:
            self._engine_selector.setCurrentIndex(0)
            self.config.capture.engine = str(self._engine_selector.currentData())

        self._frequency_input = QDoubleSpinBox()
        self._frequency_input.setRange(0.5, 60.0)
        self._frequency_input.setSingleStep(0.5)
        self._frequency_input.setSuffix(" 秒")
        self._frequency_input.setValue(self.config.capture.frequency_ms / 1000.0)

        self._build_layout()

        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.VeryCoarseTimer)
        self._timer.timeout.connect(lambda: self._trigger_processing(True))

        self._overlay = OverlayWindow(self.config.overlay)
        self._region_selector = RegionSelector()
        self._region_selector.region_selected.connect(self._on_region_selected)
        self._region_selector.selection_cancelled.connect(self._on_region_selection_cancelled)

        self._tray = SystemTrayController(self.windowIcon(), self)
        self._tray.start_requested.connect(self._on_start_clicked)
        self._tray.stop_requested.connect(self._on_stop_clicked)
        self._tray.exit_requested.connect(self._exit_application)
        self._tray.show_requested.connect(self._restore_from_tray)
        self._tray.show()
        self._tray.set_running(False)

        self._start_button.clicked.connect(self._on_start_clicked)
        self._trigger_button.clicked.connect(self._on_force_trigger)
        self._end_button.clicked.connect(self._exit_application)
        self._frequency_input.valueChanged.connect(self._on_frequency_changed)
        self._engine_selector.currentIndexChanged.connect(self._on_engine_changed)

        self.capture_region: Optional[Region] = None
        self._running = False
        self._is_processing = False
        self._worker_threads: List[QThread] = []
        self._worker_context: Dict[_PipelineWorker, Tuple[Optional[QThread], bool]] = {}
        self._exiting = False

        self.setWindowTitle("Furigana OCR Overlay")
        self.resize(380, 200)

    def _build_layout(self) -> None:
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        engine_layout = QHBoxLayout()
        engine_layout.addWidget(QLabel("OCR 引擎:"))
        engine_layout.addWidget(self._engine_selector)
        layout.addLayout(engine_layout)

        frequency_layout = QHBoxLayout()
        frequency_layout.addWidget(QLabel("更新頻率:"))
        frequency_layout.addWidget(self._frequency_input)
        layout.addLayout(frequency_layout)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self._start_button)
        button_layout.addWidget(self._trigger_button)
        button_layout.addWidget(self._end_button)
        layout.addLayout(button_layout)

        layout.addStretch()
        layout.addWidget(QLabel("狀態: 如需開始請先選擇範圍"))

        self.setCentralWidget(central)

    def _on_frequency_changed(self, value: float) -> None:
        interval = int(value * 1000)
        self.config.capture.frequency_ms = interval
        if self._timer.isActive():
            self._timer.start(interval)

    def _on_engine_changed(self, index: int) -> None:
        engine = self._engine_selector.itemData(index)
        if not engine:
            return
        engine_name = str(engine)
        self.config.capture.engine = engine_name
        self.pipeline.set_ocr_engine(engine_name)
        if self._running and not self._is_processing:
            self._trigger_processing(True)
        self._status_bar.showMessage(f"已切換至 {self._engine_selector.currentText()} 引擎")

    def _on_start_clicked(self) -> None:
        if self._running:
            self._stop_pipeline()
        else:
            self._initiate_region_selection()

    def _on_stop_clicked(self) -> None:
        if self._running:
            self._stop_pipeline()

    def _initiate_region_selection(self) -> None:
        self._status_bar.showMessage("請拖曳選擇擷取區域，右鍵取消")
        self._region_selector.start()

    def _on_region_selection_cancelled(self) -> None:
        self._status_bar.showMessage("已取消選取")

    def _on_region_selected(self, region: Region) -> None:
        self.capture_region = region
        self._status_bar.showMessage("已選擇範圍，準備開始")
        self._start_pipeline()

    def _start_pipeline(self) -> None:
        if self.capture_region is None:
            QMessageBox.warning(self, "尚未選擇區域", "請先框選要擷取的畫面範圍。")
            return
        self._running = True
        self._start_button.setText("停止")
        self._trigger_button.setEnabled(True)
        self._tray.set_running(True)
        self._status_bar.showMessage("執行中…")
        self._trigger_processing(False)
        self._timer.start(self.config.capture.frequency_ms)

    def _stop_pipeline(self) -> None:
        self._timer.stop()
        self._running = False
        self._start_button.setText("開始")
        self._trigger_button.setEnabled(False)
        self._tray.set_running(False)
        self._overlay.clear()
        self._status_bar.showMessage("已停止")

    def _trigger_processing(self, reset_timer: bool) -> None:
        if not self._running or self.capture_region is None:
            return
        if self._is_processing:
            return
        self._is_processing = True
        self._status_bar.showMessage("辨識中…")
        if reset_timer:
            self._timer.stop()
        worker = _PipelineWorker(self.pipeline, self.capture_region)
        thread = QThread(self)
        worker.moveToThread(thread)
        worker.finished.connect(self._on_processing_finished)
        worker.failed.connect(self._on_processing_failed)
        thread.started.connect(worker.run)
        thread.start()
        self._worker_threads.append(thread)
        self._worker_context[worker] = (thread, reset_timer)

    def _on_processing_finished(self, annotations: List[TokenAnnotation]) -> None:
        sender = self.sender()
        if not isinstance(sender, _PipelineWorker):
            return

        thread, reset_timer = self._worker_context.pop(sender, (sender.thread(), False))

        if thread is not None:
            if thread.isRunning():
                thread.quit()
                thread.wait(100)
            if thread in self._worker_threads:
                self._worker_threads.remove(thread)
            thread.deleteLater()

        sender.deleteLater()

        if self._running:
            self._overlay.update_state(OverlayState(region=self.capture_region or (0, 0, 0, 0), annotations=annotations))
            if reset_timer:
                self._timer.start(self.config.capture.frequency_ms)
            self._status_bar.showMessage("已更新詞彙資訊")
        else:
            self._overlay.clear()
        self._is_processing = False

    def _on_processing_failed(self, exc: Exception) -> None:
        sender = self.sender()
        if isinstance(sender, _PipelineWorker):
            thread, _ = self._worker_context.pop(sender, (sender.thread(), False))

            if thread is not None:
                if thread.isRunning():
                    thread.quit()
                    thread.wait(100)
                if thread in self._worker_threads:
                    self._worker_threads.remove(thread)
                thread.deleteLater()

            sender.deleteLater()
        self._is_processing = False
        if self._running:
            self._timer.start(self.config.capture.frequency_ms)
        self._status_bar.showMessage("辨識失敗，將重試；詳情請查看日誌。")
        traceback.print_exception(type(exc), exc, exc.__traceback__)
        QMessageBox.critical(self, "處理失敗", str(exc))

    def _on_force_trigger(self) -> None:
        if self._running:
            self._trigger_processing(True)

    def _exit_application(self) -> None:
        self._exiting = True
        self._timer.stop()
        self._tray.hide()
        self._overlay.close()
        try:
            self.pipeline.capture.close()
        except Exception:
            pass
        QApplication.quit()

    def _restore_from_tray(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event: QCloseEvent) -> None:  # type: ignore[override]
        if not self._exiting:
            self._exit_application()
            event.accept()
        super().closeEvent(event)


__all__ = ["MainWindow"]
