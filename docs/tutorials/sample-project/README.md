# Sample Project — a tiny todo CLI

This is the **practice substrate** for the methodology tutorials. It is intentionally small,
plain, and throwaway: a stdlib-only Python todo-list CLI with a real test suite and a short
[backlog](BACKLOG.md). You will run real methodology sessions against it.

It ships **without** any methodology files (no `SESSION_RUNNER.md`, no `CLAUDE.md`, no
`BACKLOG.md`-as-task-tracker). Installing the framework onto this project is exactly what you
do in **Tutorial 1** — see [`../README.md`](../README.md) for the series index.

## Try it

```sh
cd docs/tutorials/sample-project

python3 todo.py add "write the report"
python3 todo.py add "submit the report"
python3 todo.py list
```

State is stored in `todos.json` in the current directory (override with `--file PATH` or the
`TODO_STORE` env var). `todos.json` is throwaway — delete it any time.

## The build equivalent (run this after every change)

```sh
python -m pytest        # the runner the tutorials document
python -m unittest      # stdlib fallback — zero dependencies
```

Both should report all tests passing. In methodology terms this is your *build equivalent*:
green tests are the gate, not "it ran once on my machine."

## What's deliberately missing

The CLI has `add` and `list` but **no way to mark a task done** — even though each task already
carries a `done` flag. Wiring up `todo done <id>` is the first feature you build, end-to-end, in
Tutorial 2. The [backlog](BACKLOG.md) lists the rest, including a couple of rough edges that
Tutorial 5 uses as cautionary cases. Don't fix everything at once — that's the whole point.
