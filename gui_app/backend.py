from __future__ import annotations

import json
import os
import subprocess
import threading
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QUrl, Signal, Slot

import portable_packager
import trace_xml_to_config


class _SignalWriter:
    """Redirects stdout/stderr to the GUI log signal."""

    def __init__(self, emitter: "Backend") -> None:
        self._emitter = emitter
        self._buffer = ""

    def write(self, text: str) -> int:
        if not text:
            return 0
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            clean = line.strip()
            if clean:
                self._emitter.logMessage.emit(clean)
        return len(text)

    def flush(self) -> None:
        if self._buffer.strip():
            self._emitter.logMessage.emit(self._buffer.strip())
        self._buffer = ""


@dataclass
class _JobParams:
    xml_path: Optional[str] = None
    output_path: Optional[str] = None
    app_name: Optional[str] = None
    config_path: Optional[str] = None
    dry_run: bool = False


class Backend(QObject):
    """Bridge between QML and the Python logic."""

    logMessage = Signal(str, arguments=["message"])
    operationStarted = Signal(str, arguments=["description"])
    operationFinished = Signal(str, arguments=["description"])
    operationFailed = Signal(str, arguments=["error"])

    def __init__(self) -> None:
        super().__init__()
        self._lock = threading.Lock()

    # -------------------------- Public slots for QML ----------------------- #
    @Slot(str, str, str)
    def convertXml(self, xml_path: str, output_path: str, app_name: str) -> None:
        params = _JobParams(xml_path=xml_path, output_path=output_path, app_name=app_name or None)
        self._start_thread(self._convert_worker, params, "Convirtiendo XML...")

    @Slot(str, str, bool)
    def generatePackage(self, config_path: str, output_dir: str, dry_run: bool) -> None:
        params = _JobParams(config_path=config_path, output_path=output_dir, dry_run=dry_run)
        self._start_thread(self._package_worker, params, "Generando paquete portable...")

    @Slot(str, result=str)
    def urlToLocalPath(self, url: str) -> str:
        qurl = QUrl(url)
        return qurl.toLocalFile() if qurl.isValid() else url

    @Slot(str)
    def openPath(self, path: str) -> None:
        if not path:
            return
        expanded = self._resolve_path(path, create=False)
        if os.name == "nt":
            if expanded.is_dir():
                subprocess.Popen(["explorer", str(expanded)])
            else:
                subprocess.Popen(["explorer", f"/select,{expanded}"])
        else:
            subprocess.Popen(["xdg-open", str(expanded)])

    @Slot(str, result=bool)
    def pathExists(self, path: str) -> bool:
        if not path:
            return False
        return self._resolve_path(path, create=False).exists()

    # ------------------------------ Workers -------------------------------- #
    def _convert_worker(self, params: _JobParams) -> None:
        try:
            xml_path = self._resolve_path(params.xml_path)
            output_path = self._resolve_path(params.output_path, must_exist_parent=True)
            self.logMessage.emit(f"Procesando XML: {xml_path}")
            config = trace_xml_to_config.build_config(xml_path, params.app_name)
            with output_path.open("w", encoding="utf-8") as handle:
                json.dump(config, handle, indent=2, ensure_ascii=False)
            self.operationFinished.emit(f"Configuración guardada en {output_path}")
        except Exception as exc:  # pragma: no cover - GUI feedback
            self._handle_error("Error al convertir XML", exc)

    def _package_worker(self, params: _JobParams) -> None:
        from contextlib import redirect_stdout, redirect_stderr

        writer = _SignalWriter(self)
        try:
            config_path = self._resolve_path(params.config_path)
            output_dir = self._resolve_path(params.output_path, create=True)
            with redirect_stdout(writer), redirect_stderr(writer):
                portable_packager.main(config_path, output_dir, dry_run=params.dry_run)
            writer.flush()
            if params.dry_run:
                self.operationFinished.emit("Dry-run completado (no se copiaron archivos).")
            else:
                self.operationFinished.emit(f"Paquete generado en {output_dir}")
        except Exception as exc:  # pragma: no cover - GUI feedback
            self._handle_error("Error al generar paquete", exc)
        finally:
            writer.flush()

    # -------------------------- Utilities ---------------------------------- #
    def _start_thread(self, target, params: _JobParams, description: str) -> None:
        self.operationStarted.emit(description)
        thread = threading.Thread(target=target, args=(params,), daemon=True)
        thread.start()

    def _resolve_path(self, raw: Optional[str], create: bool = False, must_exist_parent: bool = False) -> Path:
        if not raw:
            raise ValueError("Debes especificar una ruta válida.")
        path = Path(raw).expanduser()
        if create:
            path.mkdir(parents=True, exist_ok=True)
        if must_exist_parent and not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
        return path.resolve()

    def _handle_error(self, prefix: str, exc: Exception) -> None:
        message = f"{prefix}: {exc}"
        self.logMessage.emit(traceback.format_exc())
        self.operationFailed.emit(message)
