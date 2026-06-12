"""Thread-safe JSON persistence for tasks, notes, and reminders.

Writes are atomic (temp file + ``os.replace``) so a crash mid-write can
never corrupt the data file. All mutation happens under a re-entrant
lock, which makes the stores safe to share with the background
reminder scheduler thread.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


class JsonStore:
    """A small dict-of-records store backed by a single JSON file."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._lock = threading.RLock()
        self._data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        try:
            with self._path.open(encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                return data
            log.warning("Ignoring malformed store file %s (not a JSON object)", self._path)
        except FileNotFoundError:
            pass
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("Could not read %s (%s); starting empty", self._path, exc)
        return {"items": [], "next_id": 1}

    def _save_locked(self) -> None:
        """Atomically persist current state. Caller must hold the lock."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=self._path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, ensure_ascii=False, indent=2)
            os.replace(tmp_name, self._path)
        except OSError:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    # -- generic record API -------------------------------------------------

    def add(self, record: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            record = {**record, "id": self._data["next_id"], "created_at": time.time()}
            self._data["next_id"] += 1
            self._data["items"].append(record)
            self._save_locked()
            return record

    def all(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(item) for item in self._data["items"]]

    def update(self, item_id: int, **fields: Any) -> dict[str, Any] | None:
        with self._lock:
            for item in self._data["items"]:
                if item["id"] == item_id:
                    item.update(fields)
                    self._save_locked()
                    return dict(item)
            return None

    def remove(self, item_id: int) -> bool:
        with self._lock:
            before = len(self._data["items"])
            self._data["items"] = [i for i in self._data["items"] if i["id"] != item_id]
            if len(self._data["items"]) != before:
                self._save_locked()
                return True
            return False


class TaskStore(JsonStore):
    def add_task(self, title: str) -> dict[str, Any]:
        return self.add({"title": title, "done": False})

    def complete(self, task_id: int) -> dict[str, Any] | None:
        return self.update(task_id, done=True)

    def pending(self) -> list[dict[str, Any]]:
        return [t for t in self.all() if not t["done"]]


class NoteStore(JsonStore):
    def add_note(self, text: str) -> dict[str, Any]:
        return self.add({"text": text})


class ReminderStore(JsonStore):
    def add_reminder(self, message: str, due_at: float) -> dict[str, Any]:
        return self.add({"message": message, "due_at": due_at, "fired": False})

    def pending(self) -> list[dict[str, Any]]:
        return [r for r in self.all() if not r["fired"]]

    def mark_fired(self, reminder_id: int) -> None:
        self.update(reminder_id, fired=True)
