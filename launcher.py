"""
Punkt wejścia dla pojedynczego pliku .exe.

Uruchamia backend FastAPI w podprocesie (--backend), potem okno PyQt6.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path
from urllib.request import urlopen

_APP_ROOT: Path | None = None
_LOG_PATH: Path | None = None
_QT_APP = None  # musi żyć przez cały main() — inaczej GC niszczy QApplication i splash


def _qt_deleted(obj: object | None) -> bool:
    if obj is None:
        return True
    try:
        from PyQt6 import sip

        return sip.isdeleted(obj)
    except Exception:
        return True


def _log(msg: str) -> None:
    line = f"{time.strftime('%H:%M:%S')} {msg}\n"
    if _LOG_PATH:
        try:
            with open(_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(line)
        except OSError:
            pass


def _bootstrap() -> Path:
    global _APP_ROOT, _LOG_PATH
    from paths import get_app_root, get_env_path

    _APP_ROOT = get_app_root()
    _LOG_PATH = _APP_ROOT / "AIQuizGenerator.log"
    os.chdir(_APP_ROOT)
    if str(_APP_ROOT) not in sys.path:
        sys.path.insert(0, str(_APP_ROOT))

    from dotenv import load_dotenv

    env_path = get_env_path()
    load_dotenv(env_path)

    _log(f"=== Start (frozen={getattr(sys, 'frozen', False)}) ===")
    _log(f"app_root={_APP_ROOT}")
    _log(f".env exists={env_path.is_file()} path={env_path}")
    _log(f"GROQ_API_KEY set={bool(os.getenv('GROQ_API_KEY', '').strip())}")
    _ensure_stdio()
    return _APP_ROOT


def _ensure_stdio() -> None:
    """Przy exe bez konsoli (PyInstaller --windowed) stdout/stderr są None — uvicorn tego wymaga."""
    log_target = _LOG_PATH or Path(os.devnull)
    if sys.stdout is None:
        sys.stdout = open(log_target, "a", encoding="utf-8", buffering=1)
    if sys.stderr is None:
        sys.stderr = open(log_target, "a", encoding="utf-8", buffering=1)


def _run_uvicorn() -> None:
    try:
        _ensure_stdio()
        if sys.platform == "win32":
            import asyncio
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        import uvicorn
        from backend.main import app

        _log("uvicorn: start")
        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=8000,
            log_level="warning",
            log_config=None,
        )
        server = uvicorn.Server(config)
        server.run()
    except Exception:
        _log("uvicorn: BŁĄD\n" + traceback.format_exc())
        raise


def _port_is_open(host: str = "127.0.0.1", port: int = 8000, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _api_responds() -> bool:
    try:
        with urlopen("http://127.0.0.1:8000/openapi.json", timeout=2) as resp:
            return resp.status == 200
    except OSError:
        return False


def _wait_for_api(timeout: int, qt_app=None) -> tuple[bool, str]:
    """Czeka aż port 8000 nasłuchuje (socket), opcjonalnie weryfikuje API."""
    for i in range(timeout):
        if qt_app is not None:
            qt_app.processEvents()
        if _port_is_open():
            if _api_responds():
                _log(f"API gotowe po {i + 1}s")
                return True, ""
            _log(f"port 8000 otwarty po {i + 1}s, czekam na openapi.json...")
        time.sleep(1)
    return False, f"Brak odpowiedzi API po {timeout}s (szczegóły: {_LOG_PATH})"


def _start_backend() -> subprocess.Popen | threading.Thread:
    """Frozen: osobny proces tego samego exe. Dev: wątek w tym procesie."""
    root = _APP_ROOT or Path.cwd()

    if getattr(sys, "frozen", False):
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        cmd = [sys.executable, "--backend"]
        _log(f"backend subprocess: {cmd}")
        return subprocess.Popen(
            cmd,
            cwd=str(root),
            creationflags=flags,
        )

    thread = threading.Thread(target=_run_uvicorn, daemon=True, name="uvicorn")
    thread.start()
    _log("backend thread started")
    return thread


def _stop_backend(backend: subprocess.Popen | threading.Thread) -> None:
    if isinstance(backend, subprocess.Popen):
        backend.terminate()
        try:
            backend.wait(timeout=5)
        except subprocess.TimeoutExpired:
            backend.kill()
    _log("backend zatrzymany")


def _show_error(message: str) -> None:
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox

        app = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.critical(None, "AI Quiz Generator", message)
    except Exception:
        print(message, file=sys.stderr)


def _show_startup_splash(app) -> object | None:
    """Wymaga zewnętrznego QApplication — nie tworzy go lokalnie (GC niszczyłby widgety)."""
    try:
        from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

        w = QWidget()
        w.setWindowTitle("AI Quiz Generator")
        layout = QVBoxLayout(w)
        label = QLabel(
            "Uruchamianie serwera…\n"
            "Pierwsze uruchomienie może potrwać do 2 minut."
        )
        label.setStyleSheet("font-size: 13px; padding: 24px;")
        layout.addWidget(label)
        w.setFixedSize(360, 120)
        w.show()
        app.processEvents()
        return w
    except Exception:
        return None


def main() -> None:
    global _QT_APP
    _bootstrap()
    timeout = 120 if getattr(sys, "frozen", False) else 45

    from PyQt6.QtWidgets import QApplication

    _QT_APP = QApplication.instance() or QApplication(sys.argv)
    splash = _show_startup_splash(_QT_APP)
    backend = _start_backend()

    try:
        ok, detail = _wait_for_api(timeout, qt_app=_QT_APP)
        if not ok:
            if isinstance(backend, subprocess.Popen):
                _log(f"subprocess returncode={backend.poll()}")
            _show_error(
                "Nie udało się uruchomić serwera API na porcie 8000.\n\n"
                f"{detail}\n\n"
                f"Katalog aplikacji: {_APP_ROOT}\n"
                f"Plik .env: {(_APP_ROOT / '.env').is_file()}\n"
                f"Klucz GROQ_API_KEY: {'tak' if os.getenv('GROQ_API_KEY') else 'nie'}"
            )
            sys.exit(1)

        if splash is not None and not _qt_deleted(splash):
            splash.close()

        from frontend.app import main as run_gui

        run_gui()
    finally:
        if isinstance(backend, subprocess.Popen):
            _stop_backend(backend)


if __name__ == "__main__":
    if "--backend" in sys.argv:
        _bootstrap()
        _run_uvicorn()
    else:
        main()
