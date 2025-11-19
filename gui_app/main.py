from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

if __package__:
    from .backend import Backend
else:  # Allow running as `python gui_app/main.py`
    import pathlib

    sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
    from gui_app.backend import Backend


def run() -> int:
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Material")
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()

    def _log_warnings(errors):
        for error in errors:
            print(error.toString(), file=sys.stderr)

    engine.warnings.connect(_log_warnings)

    backend = Backend()
    engine.rootContext().setContextProperty("backend", backend)

    qml_file = Path(__file__).resolve().parent / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))

    if not engine.rootObjects():
        print("No se pudo cargar la interfaz QML.", file=sys.stderr)
        return -1
    return app.exec()


if __name__ == "__main__":
    sys.exit(run())
