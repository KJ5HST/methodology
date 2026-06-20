#!/usr/bin/env python3
"""todo — a deliberately tiny todo-list CLI, the methodology tutorials' sample project.

This is throwaway practice code. It exists so a learner can run a *real* methodology
session against it: it has a genuine build equivalent (`python -m pytest` / `python -m
unittest`), a believable backlog of features and bugs (see BACKLOG.md), and a couple of
rough edges that make good cautionary cases.

Design notes for the tutorials:
- The *core* (load/save/add/render) is kept free of I/O-on-import and free of `print`,
  so tests can call it directly without spawning a subprocess.
- `main()` is a thin argument-dispatch shell around the core.
- It is intentionally INCOMPLETE. The data model already carries a `done` flag, but there
  is no command to set it — wiring up `todo done <id>` is the first feature a learner
  builds in Tutorial 2. Do not "fix" that here; it is the worked example.

Stdlib only. No third-party dependencies. Python 3.8+.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

DEFAULT_STORE = "todos.json"


# --- core (pure-ish; no printing, easy to test) ------------------------------

def load_todos(store: Path) -> list[dict]:
    """Return the list of todos from `store`, or [] if it does not exist yet."""
    if not store.exists():
        return []
    return json.loads(store.read_text(encoding="utf-8"))


def save_todos(store: Path, todos: list[dict]) -> None:
    """Persist `todos` to `store` as pretty-printed JSON."""
    store.write_text(json.dumps(todos, indent=2) + "\n", encoding="utf-8")


def add_todo(todos: list[dict], text: str) -> dict:
    """Append a new todo with the next id and return it.

    NOTE (BACKLOG #B1): `text` is not validated — an empty string is accepted and
    produces a blank, un-actionable task. Catching the urge to "just quickly fix this
    inline" while doing something else is one of Tutorial 5's cautionary cases.
    """
    next_id = max((t["id"] for t in todos), default=0) + 1
    todo = {"id": next_id, "text": text, "done": False}
    todos.append(todo)
    return todo


def render(todos: list[dict]) -> str:
    """Return the human-readable listing (newline-joined; no trailing newline)."""
    if not todos:
        return "(no todos yet — add one with: todo add \"your task\")"
    lines = []
    for t in todos:
        box = "[x]" if t["done"] else "[ ]"
        lines.append(f"{t['id']:>3} {box} {t['text']}")
    return "\n".join(lines)


# --- cli shell ---------------------------------------------------------------

def _store_path(args: argparse.Namespace) -> Path:
    """Resolve the store path: --file flag wins, else $TODO_STORE, else ./todos.json."""
    return Path(args.file or os.environ.get("TODO_STORE", DEFAULT_STORE))


def cmd_add(args: argparse.Namespace) -> int:
    store = _store_path(args)
    todos = load_todos(store)
    todo = add_todo(todos, args.text)
    save_todos(store, todos)
    print(f"added #{todo['id']}: {todo['text']}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    store = _store_path(args)
    print(render(load_todos(store)))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="todo", description="A tiny todo list.")
    parser.add_argument("--file", help="path to the JSON store (default: ./todos.json)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="add a todo")
    p_add.add_argument("text", help="the task text")
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="list todos")
    p_list.set_defaults(func=cmd_list)

    # BACKLOG #F1: `done <id>` (mark complete) — the first feature built in Tutorial 2.
    # BACKLOG #F2: `rm <id>` (delete a todo).
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
