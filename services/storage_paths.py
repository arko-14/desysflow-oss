"""Shared helpers for local DesysFlow storage paths."""

from __future__ import annotations

import os
from pathlib import Path

VISIBLE_STORAGE_ROOT = "desysflow"
LEGACY_STORAGE_ROOTS = (".desysflow", ".desflow")
CHAT_DB_NAME = "desysflow_chat.db"
SESSION_DB_NAME = "desysflow_session.db"
LEGACY_CHAT_DB_NAMES = (".desysflow_chat.db",)
LEGACY_SESSION_DB_NAMES = (".desysflow_session.db",)


def normalize_storage_root_path(path: Path) -> Path:
    """Map legacy hidden storage roots to the visible default root name."""
    if path.name in LEGACY_STORAGE_ROOTS:
        return path.with_name(VISIBLE_STORAGE_ROOT)
    return path


def storage_root_candidates(path: Path) -> list[Path]:
    """Return the preferred root followed by legacy-compatible fallbacks."""
    normalized = normalize_storage_root_path(path)
    candidates = [normalized]
    for legacy_name in LEGACY_STORAGE_ROOTS:
        legacy_path = normalized.with_name(legacy_name)
        if legacy_path not in candidates:
            candidates.append(legacy_path)
    return candidates


def resolve_storage_root_path(raw_root: str | None = None, *, base: Path | None = None) -> Path:
    """Resolve the preferred storage root path without creating it."""
    raw = (raw_root if raw_root is not None else os.getenv("DESYSFLOW_STORAGE_ROOT", "")).strip()
    if raw:
        return normalize_storage_root_path(Path(raw).expanduser())
    anchor = base or Path.cwd()
    return anchor / VISIBLE_STORAGE_ROOT


def _migrate_legacy_storage_root(target: Path) -> Path:
    """Move a legacy hidden root into the visible default root when possible."""
    if target.exists():
        return target

    for legacy_path in storage_root_candidates(target)[1:]:
        if not legacy_path.exists():
            continue
        try:
            legacy_path.rename(target)
            return target
        except OSError:
            return legacy_path
    return target


def _resolve_storage_file(root: Path, preferred_name: str, legacy_names: tuple[str, ...]) -> Path:
    """Prefer visible filenames while reusing or migrating legacy hidden files."""
    target = root / preferred_name
    if target.exists():
        return target

    for legacy_name in legacy_names:
        legacy_path = root / legacy_name
        if not legacy_path.exists():
            continue
        try:
            legacy_path.rename(target)
            return target
        except OSError:
            return legacy_path
    return target


def get_storage_root() -> Path:
    """Return the local storage root and ensure it exists."""
    root = _migrate_legacy_storage_root(resolve_storage_root_path())
    root.mkdir(parents=True, exist_ok=True)
    return root


def default_chat_db_path() -> str:
    return str(_resolve_storage_file(get_storage_root(), CHAT_DB_NAME, LEGACY_CHAT_DB_NAMES))


def default_session_db_path() -> str:
    return str(_resolve_storage_file(get_storage_root(), SESSION_DB_NAME, LEGACY_SESSION_DB_NAMES))
