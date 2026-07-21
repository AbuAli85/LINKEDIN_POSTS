"""Shared atomic JSON read/write helpers.

A crash mid-write (or two cron jobs writing the same tracker/schedule file at
once) can otherwise leave it truncated or unreadable, and a corrupt file can
then crash the next run that tries to load it. Every module that persists
shared state (trackers, schedules, status/booking files) should go through
these instead of raw json.dump()/write_text()/json.load().
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def write_json(path: Path | str, data: Any, indent: int = 2) -> None:
    """Write JSON atomically: write to a temp file in the same directory, then
    os.replace() it over the target so readers only ever see the old file or
    the fully-written new one, never a partial write.
    """
    path = Path(path)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def load_json(path: Path | str, default: Any = None) -> Any:
    """Read JSON, returning `default` (and printing a warning) on a missing or
    corrupt file instead of crashing the caller.
    """
    path = Path(path)
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
        print(f"WARNING: {path} is missing or corrupt ({exc}) — using default.")
        return default
