from types import SimpleNamespace

import pytest

from assistant.commands import parse_duration, registry
from assistant.storage import NoteStore, ReminderStore, TaskStore
from assistant.scheduler import ReminderScheduler


class FakeLLM:
    def __init__(self):
        self.cleared = False

    def clear_history(self):
        self.cleared = True


@pytest.fixture
def ctx(tmp_path):
    scheduler = ReminderScheduler(ReminderStore(tmp_path / "rem.json"), announce=lambda _: None)
    yield SimpleNamespace(
        settings=None,
        tasks=TaskStore(tmp_path / "tasks.json"),
        notes=NoteStore(tmp_path / "notes.json"),
        llm=FakeLLM(),
        scheduler=scheduler,
    )
    scheduler.stop()


@pytest.mark.parametrize(
    ("text", "seconds"),
    [
        ("10", 600),
        ("45m", 2700),
        ("1h", 3600),
        ("1h30m", 5400),
        ("1h 30m", 5400),
    ],
)
def test_parse_duration_valid(text, seconds):
    assert parse_duration(text) == seconds


@pytest.mark.parametrize("text", ["", "abc", "0", "h", "-5"])
def test_parse_duration_invalid(text):
    assert parse_duration(text) is None


def test_non_command_returns_none(ctx):
    assert registry.dispatch(ctx, "what is photosynthesis?") is None


def test_help_and_exit(ctx):
    assert "task" in registry.dispatch(ctx, "help").text
    assert registry.dispatch(ctx, "exit").should_exit is True


def test_task_lifecycle(ctx):
    assert "Added task 1" in registry.dispatch(ctx, "task add write intro").text
    assert "write intro" in registry.dispatch(ctx, "task list").text
    assert "done" in registry.dispatch(ctx, "task done 1").text
    assert "No open tasks" in registry.dispatch(ctx, "task list").text
    assert "No task with id 9" in registry.dispatch(ctx, "task done 9").text


def test_notes(ctx):
    registry.dispatch(ctx, "note add cite at least 5 sources")
    assert "5 sources" in registry.dispatch(ctx, "note list").text


def test_remind_validation(ctx):
    assert "Usage" in registry.dispatch(ctx, "remind soon do a thing").text
    assert "I'll remind you" in registry.dispatch(ctx, "remind 1h submit draft").text


def test_clear_history(ctx):
    registry.dispatch(ctx, "clear")
    assert ctx.llm.cleared is True
