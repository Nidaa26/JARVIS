import threading
import time

from assistant.scheduler import ReminderScheduler
from assistant.storage import ReminderStore


def test_reminder_fires(tmp_path):
    fired = threading.Event()
    messages = []

    def announce(text):
        messages.append(text)
        fired.set()

    scheduler = ReminderScheduler(ReminderStore(tmp_path / "r.json"), announce)
    scheduler.start()
    try:
        scheduler.schedule("stretch", delay_seconds=0.05)
        assert fired.wait(timeout=2.0), "reminder did not fire in time"
        assert "stretch" in messages[0]
    finally:
        scheduler.stop()


def test_missed_reminder_announced_on_start(tmp_path):
    store = ReminderStore(tmp_path / "r.json")
    store.add_reminder("overdue thing", due_at=time.time() - 60)

    messages = []
    scheduler = ReminderScheduler(store, messages.append)
    scheduler.start()
    try:
        assert any("Missed reminder" in m for m in messages)
        assert store.pending() == []
    finally:
        scheduler.stop()


def test_earlier_reminder_preempts(tmp_path):
    order = []
    done = threading.Event()

    def announce(text):
        order.append(text)
        if len(order) == 2:
            done.set()

    scheduler = ReminderScheduler(ReminderStore(tmp_path / "r.json"), announce)
    scheduler.start()
    try:
        scheduler.schedule("later", delay_seconds=0.4)
        scheduler.schedule("sooner", delay_seconds=0.05)
        assert done.wait(timeout=2.0)
        assert "sooner" in order[0] and "later" in order[1]
    finally:
        scheduler.stop()


def test_stop_is_clean(tmp_path):
    scheduler = ReminderScheduler(ReminderStore(tmp_path / "r.json"), lambda _: None)
    scheduler.start()
    scheduler.stop()  # must not hang or raise
