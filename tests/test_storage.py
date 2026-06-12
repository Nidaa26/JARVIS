import json

from assistant.storage import JsonStore, NoteStore, ReminderStore, TaskStore


def test_add_and_roundtrip(tmp_path):
    path = tmp_path / "store.json"
    store = JsonStore(path)
    record = store.add({"title": "hello"})
    assert record["id"] == 1
    assert "created_at" in record

    # A fresh instance must read back the persisted data.
    reloaded = JsonStore(path)
    assert reloaded.all()[0]["title"] == "hello"
    assert reloaded.add({"title": "second"})["id"] == 2


def test_update_and_remove(tmp_path):
    store = JsonStore(tmp_path / "s.json")
    rec = store.add({"x": 1})
    assert store.update(rec["id"], x=2)["x"] == 2
    assert store.update(999, x=3) is None
    assert store.remove(rec["id"]) is True
    assert store.remove(rec["id"]) is False
    assert store.all() == []


def test_corrupt_file_recovers(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not valid json", encoding="utf-8")
    store = JsonStore(path)
    assert store.all() == []
    store.add({"ok": True})
    assert json.loads(path.read_text(encoding="utf-8"))["items"][0]["ok"] is True


def test_task_store(tmp_path):
    tasks = TaskStore(tmp_path / "tasks.json")
    t1 = tasks.add_task("write report")
    tasks.add_task("make slides")
    assert len(tasks.pending()) == 2
    tasks.complete(t1["id"])
    pending = tasks.pending()
    assert len(pending) == 1 and pending[0]["title"] == "make slides"


def test_note_and_reminder_stores(tmp_path):
    notes = NoteStore(tmp_path / "notes.json")
    notes.add_note("remember the rubric")
    assert notes.all()[0]["text"] == "remember the rubric"

    reminders = ReminderStore(tmp_path / "rem.json")
    rec = reminders.add_reminder("stand-up", due_at=123.0)
    assert reminders.pending() != []
    reminders.mark_fired(rec["id"])
    assert reminders.pending() == []
