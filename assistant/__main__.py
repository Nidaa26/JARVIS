"""Command-line entry point: ``python -m assistant`` or the ``gpa`` script."""

from __future__ import annotations

import argparse
import os
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gpa",
        description="Group Project Assistant — voice/text AI helper for group projects.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--voice", action="store_true", help="enable voice input/output")
    mode.add_argument("--text", action="store_true", help="force text-only mode")
    parser.add_argument("--log-level", help="override LOG_LEVEL (DEBUG, INFO, ...)")
    args = parser.parse_args(argv)

    # CLI flags override environment configuration.
    if args.voice:
        os.environ["ASSISTANT_VOICE"] = "1"
    elif args.text:
        os.environ["ASSISTANT_VOICE"] = "0"
    if args.log_level:
        os.environ["LOG_LEVEL"] = args.log_level

    from .app import Assistant
    from .config import Settings

    return Assistant(Settings()).run()


if __name__ == "__main__":
    sys.exit(main())
