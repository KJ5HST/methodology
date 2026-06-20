# Sample Project — Backlog

This backlog exists to give the methodology tutorials something real to work on. It is
deliberately small and a little rough. Items are ordered so the **first feature is the one
Tutorial 2 builds end-to-end**.

> When you bootstrap the framework onto this project in Tutorial 1, this file becomes your
> `BACKLOG.md`. The methodology's "1 deliverable per session" rule means you pick **one**
> item, take it through all six phases, and stop.

## Features

| id | Feature | Notes |
|----|---------|-------|
| F1 | `todo done <id>` — mark a task complete | **Start here (Tutorial 2).** The data model already has a `done` flag; only the command is missing. Small, vertical, testable. |
| F2 | `todo rm <id>` — delete a task | Decide what happens to ids after a delete (see the `test_add_reuses_max_id_plus_one_after_gaps` test). |
| F3 | `todo done <id>` should be reversible (`undo`) | Roadmap. |
| F4 | Due dates (`--due`) and an overdue marker in `list` | Roadmap; bigger than one session — a candidate to split. |

## Known rough edges (good cautionary cases)

| id | Issue | Why it's here |
|----|-------|---------------|
| B1 | `add` accepts empty/whitespace text | `add_todo` does no validation (see the NOTE in `todo.py`). It is tempting to "just fix this real quick" while building F1 — doing so is scope creep, and **Tutorial 5** uses it as a worked example of the urge to break the "1 deliverable" rule. Fix it as its **own** session, with its own test. |
| B2 | No confirmation before overwriting `todos.json` | Latent data-loss risk; not urgent. |

## How to verify your work

This project's **build equivalent** is its test suite. After any change, both of these must stay green:

```sh
python -m pytest        # the documented runner
python -m unittest      # stdlib fallback, no dependencies
```

A new feature is not "done" until it has a test that fails before your change and passes after.
