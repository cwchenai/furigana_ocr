"""Application bootstrapper."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .config import AppConfig
from .services.pipeline import ProcessingPipeline
from .ui.main_window import MainWindow


def main() -> int:
    """Entry point used by both console scripts and ``python -m``."""

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    config = AppConfig()
    pipeline = ProcessingPipeline(config)
    window = MainWindow(config, pipeline)
    window.show()

    return app.exec()


if __name__ == "__main__":  # pragma: no cover - manual invocation only
    raise SystemExit(main())
