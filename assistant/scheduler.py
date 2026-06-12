

from __future__ import annotations

import heapq
import logging
import threading
import time
from typing import Callable

from .storage import ReminderStore

log = logging.getLogger(__name__)

AnnounceFn = Callable[[str], None]


class ReminderScheduler:
    def __init__(self, store: ReminderStore, announce: AnnounceFn) -> None:
        self._store = store
        self._announce = announce
        self._heap: list[tuple[float, int, str]] = []  # (due_at, id, message)
        self._cond = threading.Condition()
        self._stopped = False
        self._thread = threading.Thread(target=self._run, name="reminders", daemon=True)

    def start(self) -> None:
        now = time.time()
        for rem in self._store.pending():
            if rem["due_at"] <= now:
                self._announce(f"Missed reminder (while you were away): {rem['message']}")
                self._store.mark_fired(rem["id"])
            else:
                heapq.heappush(self._heap, (rem["due_at"], rem["id"], rem["message"]))
        self._thread.start()

    def schedule(self, message: str, delay_seconds: float) -> float:
        """Schedule a reminder; returns its due timestamp."""
        due_at = time.time() + max(0.0, delay_seconds)
        record = self._store.add_reminder(message, due_at)
        with self._cond:
            heapq.heappush(self._heap, (due_at, record["id"], message))
            self._cond.notify()
        return due_at

  
    def stop(self) -> None:
        with self._cond:
            self._stopped = True
            self._cond.notify()
        if self._thread.is_alive():
            self._thread.join(timeout=2)

    def _run(self) -> None:
        while True:
            with self._cond:
                while not self._stopped and not self._heap:
                    self._cond.wait()
                if self._stopped:
                    return
                due_at, rem_id, message = self._heap[0]
                wait = due_at - time.time()
                if wait > 0:
                    self._cond.wait(timeout=wait)
                    continue  # re-check: heap head may have changed
                heapq.heappop(self._heap)
            # Fire outside the lock so a slow announce can't block scheduling.
            try:
                self._announce(f"Reminder: {message}")
            except Exception:  # noqa: BLE001 — announcer must never kill the thread
                log.exception("Reminder announcement failed")
            self._store.mark_fired(rem_id)
