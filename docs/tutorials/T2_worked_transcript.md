<!--
WORKED TRANSCRIPT — the recorded first session that Tutorial 2 is built around.
This is a real run against the sample project (docs/tutorials/sample-project/),
building backlog item F1 (`todo done <id>`) end to end through the six phases.

Maintenance note (staleness): the *methodology* steps below are load-bearing and
must stay faithful to starter-kit/SESSION_RUNNER.md. The *tool output* (test counts,
diffs, CLI lines) is illustrative and was captured from an actual run; it may age.
**Re-record this transcript if the SESSION_RUNNER phase structure changes** (new phase,
renumbered close-out step, changed gate). Treat the sample project as a maintained
deliverable, not fire-and-forget.
-->

# Worked Transcript — Tutorial 2's First Session

This is the verbatim shape of one real methodology session: building **F1 — `todo done <id>`** on the [sample project](sample-project/), from orientation to close-out, through all six phases. [Tutorial 2](T2_first_session.md) walks you through running it yourself; this file is what "a good run looks like."

- **Track B** learners (bundled sample): replay these steps in your sandbox — your tool output should match within a line or two.
- **Track A** learners (your own repo): read this as the reference while you take *your own* first backlog item through the same six phases.

> **The session is `Session 1`.** Tutorial 1 *installed* the framework; it deliberately ran no feature work (T1 Step 6). So this is the project's first real session — which is why Phase 3A (evaluate the predecessor) is skipped below: there is no predecessor yet.

The operating procedure is [`SESSION_RUNNER.md`](../../starter-kit/SESSION_RUNNER.md); its phases wrap the [six phases](../../ITERATIVE_METHODOLOGY.md#the-6-phases) of the flight manual. The task — *"Implement F1"* — maps to the [Development workstream](../../workstreams/DEVELOPMENT_WORKSTREAM.md). Nothing below is restated from those docs; the transcript *shows the procedure being followed* and links to it.

---

## Phase 0 — Orient *(change nothing, read only)*

The agent read `CLAUDE.md` when the session began; its first act is to orient, **not** to start coding. It works through the Phase 0 checklist:

1. Read `SAFEGUARDS.md` in full — blast-radius limit (≤5 files/commit), the build-equivalent rule, the one-deliverable rule.
2. Read `SESSION_NOTES.md` → **ACTIVE TASK: none.** This is Session 1.
3. No GitHub repo, so read `BACKLOG.md`. Top item is **F1 — `todo done <id>`**.
4. Workspace state:

```text
$ git status
On branch main
nothing to commit, working tree clean

$ git log --oneline -1
a1b2c3d start: sample todo CLI (+ methodology framework, Tutorial 1)
```

5. Ran `python3 methodology_dashboard.py` → dashboard refreshed; methodology-compliance score is non-zero (T1 installed the files).
6. **Ghost-session check:** `SESSION_NOTES.md` documents no sessions; `git log` shows only the setup commit. No undocumented work. Clean.
7. **Build equivalent, baseline** — the gate before any change is green tests:

```text
$ python -m pytest -q
.......                                                    [100%]
7 passed in 0.01s
```

**Orientation report to the operator:** *On `main`, clean tree. Session 1 — no prior session. Backlog top item is F1 (`todo done <id>`). Baseline: 7 tests pass. Dashboard healthy. Awaiting a task.*

→ **STOP.** Phase 0 ends by waiting for the operator. The agent does **not** assume "the backlog says F1, so I'll start." (That assumption is [FM #1](../../starter-kit/SESSION_RUNNER.md#known-failure-modes).)

---

## Phase 1 — Receive Task

Operator: **"Implement F1 — `todo done <id>`."**

The agent states its understanding back:

> *I'm going to implement one deliverable — the `todo done <id>` command — following the Development workstream. I'll close out when that's done.*

### 1B — Claim the Session

**Mandatory, before any technical work.** A stub is written to `SESSION_NOTES.md` **first**, so even a crash leaves a trace:

```markdown
### What Session 1 Did
**Deliverable:** Implement F1 — `todo done <id>` (IN PROGRESS)
**Started:** (timestamp)
**Status:** Session claimed. Work beginning.
```

---

## Phase 2 — Execute

The agent reads the [Development workstream](../../workstreams/DEVELOPMENT_WORKSTREAM.md) and follows its phases, respecting the hard gates.

### Research

- **Expected behavior:** `todo done <id>` marks the task with that id complete and persists it. **Current behavior:** there is no such command (`add`, `list` only).
- **Read the code that will change** (not the description — the implementation): `todo.py`. The data model *already* carries a `done` flag (`add_todo` sets `"done": False`; `render` prints `[x]` when true). So the gap is a *command*, not a data-model change — `mark_done` core + a `cmd_done` shell + one parser entry.
- **Acceptance criteria:** marking an existing id sets `done=True` and saves; an unknown id is a clean non-zero error, not a crash; the existing 7 tests stay green.
- **Edge cases:** unknown id; already-done id (should be idempotent).
- **Scope challenge.** Reading `add_todo` surfaces **B1** (the NOTE in the code: empty text is accepted without validation). It is tempting to "just fix that while I'm here." → **Caught: that is a second deliverable.** B1 gets its own session with its own test. F1 only. *(This near-miss is one of Tutorial 5's cautionary cases.)*

### Create — the implementation plan *(design before code)*

```markdown
## What I'm changing
- todo.py: add `mark_done(todos, todo_id)` — pure core, no I/O, returns the
  todo or None. Idempotent.
- todo.py: add `cmd_done(args)` — load → mark_done → save; unknown id → stderr + exit 1.
- todo.py: register the `done` subparser with one positional `id` (type=int).

## What I'm NOT changing (scope boundary)
- add_todo validation (B1) — separate session.
- render / load_todos / save_todos — already support the `done` flag.

## Test plan (test-first)
- mark_done sets the flag and returns the todo; leaves others untouched.
- mark_done on an already-done task is idempotent.
- mark_done unknown id → None, list unchanged.
- main(["done","1"]) persists done=True and exits 0.
- main(["done","42"]) on a missing id exits 1.

## Verification
1. The 5 new tests fail before the change (red), pass after (green).
2. The original 7 tests still pass (no regression).
3. Manual CLI run: add → done → list shows [x]; unknown id errors cleanly.
```

### Present — **the gate** *(STOP and get approval)*

The agent presents the plan above and **stops**. No code yet.

> *Here is the plan for F1: a `mark_done` core function, a `cmd_done` shell, one parser entry, five tests written first. B1 (empty-text validation) is explicitly out of scope. Approve before I implement?*

Operator: **"Approved."**

→ This is the highest-ROI gate in the methodology: a flawed plan caught here costs zero implementation effort. The agent did **not** start coding when the plan felt obvious — implementing before this approval would be skipping the [Present gate](../../ITERATIVE_METHODOLOGY.md#the-6-phases).

### Implement — test-first *(red → green)*

**Red.** The five tests go in `test_done.py` *before* the implementation, and are run to prove they fail for the right reason:

```text
$ python -m pytest test_done.py -q
...
todo: error: argument command: invalid choice: 'done' (choose from 'add', 'list')
...
5 failed in 0.25s
```

Red confirmed: `mark_done` does not exist and `done` is not a subcommand. (A test that passes before you write the feature is testing nothing.)

**Green.** The plan's three edits to `todo.py`, applied verbatim:

```diff
+def mark_done(todos: list[dict], todo_id: int) -> dict | None:
+    """Mark the todo with `todo_id` complete and return it; None if no such id."""
+    for t in todos:
+        if t["id"] == todo_id:
+            t["done"] = True
+            return t
+    return None
@@
+def cmd_done(args: argparse.Namespace) -> int:
+    store = _store_path(args)
+    todos = load_todos(store)
+    todo = mark_done(todos, args.id)
+    if todo is None:
+        print(f"no todo with id {args.id}", file=sys.stderr)
+        return 1
+    save_todos(store, todos)
+    print(f"done #{todo['id']}: {todo['text']}")
+    return 0
@@
+    p_done = sub.add_parser("done", help="mark a todo complete")
+    p_done.add_argument("id", type=int, help="the id of the todo to complete")
+    p_done.set_defaults(func=cmd_done)
```

Re-run the **full** build equivalent (not just the new file — watch for regressions):

```text
$ python -m pytest -q
............                                               [100%]
12 passed in 0.02s
```

7 original + 5 new = 12. No regression.

---

## Phase 3 — Close Out *(automatic; do not ask "shall I continue?")*

### 3A — Evaluate the predecessor's handoff

**Skipped — this is Session 1.** There is no previous handoff to score. (From Session 2 on, this step comes first and scores the prior session 1–10.)

### 3B — Self-assess

Research before code: yes. Read the implementation, not just the backlog line: yes — that is what revealed the `done` flag already existed and kept the change to ~30 lines. Stakeholder corrections: 0. Scope held (B1 deferred): yes.

### 3C — Document Learnings

The sample project is an *adopter* (it copied `SESSION_RUNNER.md`), so any project learning is recorded in its `CLAUDE.md` → Project-Specific Methodology Adaptations — **not** in the synced files. One worth keeping: *the core stays I/O-free — `cmd_done` persists, `mark_done` must not*, so the next `done`-style command follows the same split. Nothing framework-level to record this session.

### 3D — Handoff notes

`SESSION_NOTES.md` stub is overwritten with the full handoff:

```markdown
### What Session 1 Did
**Deliverable:** F1 — `todo done <id>` (DONE)
**What was done:** mark_done() + cmd_done() + `done` subparser in todo.py; 5 tests
  in test_done.py. Commit (hash). 12/12 tests green; CLI smoke-tested.
**What's next:** F2 — `todo rm <id>` (BACKLOG). Decide id-reuse policy after delete
  (see test_add_reuses_max_id_plus_one_after_gaps in test_todo.py).
**Key files:** todo.py:57 mark_done (core), todo.py:103 cmd_done (shell),
  todo.py:127 done subparser. test_done.py (all F1 tests).
**Gotchas:** core stays I/O-free — cmd_done persists, mark_done must not.
  B1 (empty-text validation) is a KNOWN open item, deliberately NOT touched this session.
**Self-assessment:** 0 corrections; scope held; runtime-verified. 9/10.
```

### 3E — Runtime smoke test

The deliverable changes runtime behavior (a new subcommand and dispatch), so "tests pass" is necessary but not sufficient — the app is actually run:

```text
$ python3 todo.py --file demo.json add "write the report"
added #1: write the report
$ python3 todo.py --file demo.json done 1
done #1: write the report
$ python3 todo.py --file demo.json list
  1 [x] write the report
$ python3 todo.py --file demo.json done 99
no todo with id 99            # exit status 1
```

The feature is *active*, not just compiled. (Skipping this is [FM #24, build-passes-ship-it](../../starter-kit/SESSION_RUNNER.md#known-failure-modes).)

### 3F — Record the ledger, then commit *(one action, one commit)*

F1 came from the backlog, so its close-out does two paired things in the **same commit**: prepend a dated, source-tagged line to the project's `CHANGELOG.md` action ledger (setup seeded one — [T1 Step 3](T1_setup.md)) **and** strike F1 from `BACKLOG.md` (a `[BL-N]` entry clears its item). Stage both **explicitly** — a freshly-seeded ledger may still be untracked, and `git commit -am` skips untracked files, so it would silently drop the entry — the very [FM #27, unrecorded action](../../starter-kit/SESSION_RUNNER.md#known-failure-modes) this step prevents:

```text
# prepended to CHANGELOG.md (newest on top):
### 2026-06-22 · [BL-F1] todo done <id> — mark a task complete
- **Commit:** (hash) · **Session:** S1 · **Verified:** 12/12 tests green; CLI smoke-tested (done + invalid id → exit 1)

# F1 struck from BACKLOG.md in the same commit

$ git add CHANGELOG.md BACKLOG.md todo.py test_done.py
$ git commit -m "feat(todo): add `done <id>` to mark a task complete (F1)"
```

### 3G — Report and STOP

Deliverable summarized, self-assessment given, next session pointed at F2.

→ **The session is over.** The agent does **not** continue to F2, and does **not** fix B1. "1 and done." ([FM #2](../../starter-kit/SESSION_RUNNER.md#known-failure-modes) is the urge to keep going.)

---

## Near-misses this session caught *(these feed Tutorial 5)*

1. **"The backlog says F1 — I'll just start."** Caught at the end of Phase 0: orientation ends by *waiting for the operator*, not by self-assigning. → FM #1.
2. **"While I'm in `add_todo`, I'll fix the empty-text bug (B1)."** Caught in Research / scope-challenge: that is a second deliverable. → FM #2 / FM #8, "1 and done."
3. **"The plan is obvious — I'll skip straight to coding."** Caught at the Present gate: no implementation before explicit approval.

## What this session produced

One shipped, tested, runtime-verified feature — `todo done <id>` — reached through all six phases with zero stakeholder corrections, the B1 scope-creep temptation deferred to its own session, and a handoff a Session 2 could act on without re-discovery. That is the unit the methodology optimizes: **one deliverable, done well, set up to compound.**

→ Back to **[Tutorial 2: Your First Session, End-to-End](T2_first_session.md)** to run it yourself.
