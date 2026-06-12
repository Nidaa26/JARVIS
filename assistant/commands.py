


"""Local command handling.

Commands (tasks, notes, reminders, etc.) are executed entirely locally —
no API/model call is made — which keeps them instant and free. Anything
that is not a recognised command falls through to the LLM.


"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:  # avoid an import cycle at runtime
    from .app import AppContext

_DURATION_RE = re.compile(r"^(?:(\d+)\s*h)?\s*(?:(\d+)\s*m?)?$", re.IGNORECASE)


def parse_duration(text: str) -> Optional[float]:
    """Parse '10', '45m', '1h', '1h30m' → seconds. None if unparseable."""
    match = _DURATION_RE.match(text.strip())
    if not match or not (match.group(1) or match.group(2)):
        return None
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    total = hours * 3600 + minutes * 60
    return float(total) if total > 0 else None


@dataclass
class CommandResult:
    text: str
    should_exit: bool = False


Handler = Callable[["AppContext", str], CommandResult]


class CommandRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, Handler] = {}
        self._help: list[tuple[str, str]] = []

    def register(self, names: list[str], usage: str) -> Callable[[Handler], Handler]:
        def decorator(fn: Handler) -> Handler:
            for name in names:
                self._handlers[name] = fn
            self._help.append((usage, fn.__doc__ or ""))
            return fn

        return decorator

    def dispatch(self, ctx: "AppContext", raw: str) -> Optional[CommandResult]:
        """Execute ``raw`` if its first word is a command; else None."""
        raw = raw.strip()
        if not raw:
            return CommandResult("")
        word, _, rest = raw.partition(" ")
        handler = self._handlers.get(word.lower())
        if handler is None:
            return None
        return handler(ctx, rest.strip())

    def help_text(self) -> str:
        lines = ["Available commands (everything else goes to the AI):"]
        lines += [f"  {usage:<28} {doc}" for usage, doc in sorted(self._help)]
        return "\n".join(lines)


registry = CommandRegistry()


@registry.register(["help", "?"], "help")
def _help(ctx: "AppContext", args: str) -> CommandResult:
    """Show this help."""
    return CommandResult(registry.help_text())


@registry.register(["exit", "quit", "bye", "goodbye"], "exit")
def _exit(ctx: "AppContext", args: str) -> CommandResult:
    """Quit the assistant."""
    return CommandResult("Goodbye!", should_exit=True)


@registry.register(["time"], "time")
def _time(ctx: "AppContext", args: str) -> CommandResult:
    """Say the current date and time."""
    return CommandResult(datetime.now().strftime("It is %H:%M on %A, %B %d."))


@registry.register(["task", "tasks", "todo"], "task add|list|done|remove ...")
def _task(ctx: "AppContext", args: str) -> CommandResult:
    """Manage the shared task list."""
    action, _, rest = args.partition(" ")
    action = action.lower()
    rest = rest.strip()

    if action == "add" and rest:
        task = ctx.tasks.add_task(rest)
        return CommandResult(f"Added task {task['id']}: {task['title']}")
    if action in ("list", ""):
        pending = ctx.tasks.pending()
        if not pending:
            return CommandResult("No open tasks. Nice!")
        lines = [f"  {t['id']}. {t['title']}" for t in pending]
        return CommandResult("Open tasks:\n" + "\n".join(lines))
    if action in ("done", "complete") and rest.isdigit():
        task = ctx.tasks.complete(int(rest))
        if task:
            return CommandResult(f"Marked task {task['id']} done: {task['title']}")
        return CommandResult(f"No task with id {rest}.")
    if action in ("remove", "delete", "rm") and rest.isdigit():
        if ctx.tasks.remove(int(rest)):
            return CommandResult(f"Removed task {rest}.")
        return CommandResult(f"No task with id {rest}.")
    return CommandResult("Usage: task add <title> | task list | task done <id> | task remove <id>")


@registry.register(["note", "notes"], "note add <text> | note list")
def _note(ctx: "AppContext", args: str) -> CommandResult:
    """Keep quick project notes."""
    action, _, rest = args.partition(" ")
    action = action.lower()
    rest = rest.strip()

    if action == "add" and rest:
        note = ctx.notes.add_note(rest)
        return CommandResult(f"Noted ({note['id']}).")
    if action in ("list", ""):
        notes = ctx.notes.all()
        if not notes:
            return CommandResult("No notes yet.")
        lines = [f"  {n['id']}. {n['text']}" for n in notes]
        return CommandResult("Notes:\n" + "\n".join(lines))
    return CommandResult("Usage: note add <text> | note list")


@registry.register(["remind", "reminder"], "remind <10|45m|1h30m> <text>")
def _remind(ctx: "AppContext", args: str) -> CommandResult:
    """Set a reminder (duration in minutes by default)."""
    when, _, message = args.partition(" ")
    seconds = parse_duration(when)
    message = message.strip()
    if seconds is None or not message:
        return CommandResult("Usage: remind <minutes, e.g. 10, 45m or 1h30m> <message>")
    due = ctx.scheduler.schedule(message, seconds)
    due_str = datetime.fromtimestamp(due).strftime("%H:%M")
    return CommandResult(f"Okay — I'll remind you at {due_str}: {message}")


@registry.register(["clear", "reset"], "clear")
def _clear(ctx: "AppContext", args: str) -> CommandResult:
    """Forget the current AI conversation."""
    ctx.llm.clear_history()
    return CommandResult("Conversation history cleared.")
