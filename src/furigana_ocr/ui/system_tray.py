"""System tray integration for the Furigana OCR application."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon


class SystemTrayController(QObject):
    """Creates the system tray icon and exposes high level signals."""

    start_requested = Signal()
    stop_requested = Signal()
    exit_requested = Signal()
    show_requested = Signal()

    def __init__(self, icon: QIcon | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._tray = QSystemTrayIcon(icon or QIcon.fromTheme("applications-education"), self)
        self._menu = QMenu()
        self._start_action = QAction("開始", self)
        self._stop_action = QAction("停止", self)
        self._stop_action.setEnabled(False)
        self._exit_action = QAction("結束", self)

        self._start_action.triggered.connect(self.start_requested)
        self._stop_action.triggered.connect(self.stop_requested)
        self._exit_action.triggered.connect(self.exit_requested)

        self._menu.addAction(self._start_action)
        self._menu.addAction(self._stop_action)
        self._menu.addSeparator()
        self._menu.addAction(self._exit_action)
        self._tray.setContextMenu(self._menu)
        self._tray.activated.connect(self._on_activated)

    def show(self) -> None:
        self._tray.show()

    def hide(self) -> None:
        self._tray.hide()

    def set_running(self, running: bool) -> None:
        self._start_action.setEnabled(not running)
        self._stop_action.setEnabled(running)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.Trigger:
            self.show_requested.emit()
        elif reason == QSystemTrayIcon.Context:
            # Context menu will show automatically; nothing extra required.
            pass

    def show_message(self, title: str, message: str, msecs: int = 3000) -> None:
        self._tray.showMessage(title, message, self._tray.icon(), msecs)


__all__ = ["SystemTrayController"]
