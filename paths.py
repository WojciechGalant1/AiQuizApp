"""Ścieżki aplikacji — działają zarówno z kodu źródłowego, jak i ze spakowanego exe."""
from __future__ import annotations

import sys
from pathlib import Path


def get_app_root() -> Path:
    """Katalog roboczy: obok .exe (frozen) lub katalog quiz_app (dev)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def get_env_path() -> Path:
    return get_app_root() / ".env"


def get_data_dir() -> Path:
    return get_app_root() / "data"
