# Tutorial 2: Your First Session, End-to-End

> **Objective:** Run one complete methodology session — all six phases, one deliverable — so you have felt the loop the framework is built around, especially Phase 0 Orient and the Present gate.
> **Prerequisites:** [Tutorial 1: Setup & First Bootstrap](T1_setup.md) (the framework must be installed). You need a terminal, `git`, and Python 3. New here? Start at the [series index](README.md).
> **Time:** ~30 minutes
> **What you'll produce:** One shipped, tested feature (Track B: `todo done <id>`) reached through all six phases, plus a `SESSION_NOTES.md` handoff a *next* session could act on without re-discovery.
> **Track:** Pick one and stick with it for this pass —
> **A** (your own repo): take one real backlog item through the six phases; the [worked transcript](T2_worked_transcript.md) is your reference for "what a good run looks like."
> **B** ([sample project](sample-project/)): build backlog item **F1 — `todo done <id>`** by replaying the [worked transcript](T2_worked_transcript.md) step-for-step in your sandbox.

## Why this matters

Tutorial 1 installed the operating procedure; this is where you *run* it and feel why each phase earns its place. Two phases do the heavy lifting and are the ones every newcomer is tempted to skip: **Phase 0 (Orient)** — read before you touch anything — and the **Present gate** — show the plan and stop until it's approved. By the end you'll have taken one real deliverable from a clean tree to a verified commit without either skip. The payoff is documented, not promised:

- [The Self-Improvement Loop](../../ITERATIVE_METHODOLOGY.md#the-self-improvement-loop) — the compounding you start feeling the moment this session writes a handoff the next one reads.
- [When to Use This Methodology](../../ITERATIVE_METHODOLOGY.md#when-to-use-this-methodology) — and when a session like this is overkill.
- [Evidence](../../README.md#evidence) — what running sessions this way actually changed.

The six phases themselves are defined in the [flight manual](../../ITERATIVE_METHODOLOGY.md#the-6-phases) and operated by the [cockpit checklist](../../starter-kit/SESSION_RUNNER.md); this tutorial doesn't restate them — it makes you run one. For another angle on the same first run, see [`HOW_TO_USE.md` §Running Your First Session](../../HOW_TO_USE.md#running-your-first-session).

## Before you start

You need the bootstrapped project from Tutorial 1 — the one with `SESSION_RUNNER.md`, `SAFEGUARDS.md`, `SESSION_NOTES.md`, the task-tracking files, and a `CLAUDE.md` whose first section is the SESSION PROTOCOL block. Confirm the build equivalent is green before you change anything:

```sh
# Track B, from inside your sandbox copy of the sample project:
python -m pytest        # expect: 7 passed
```

Read the [worked transcript](T2_worked_transcript.md) once now, start to finish. It's short, and it's the artifact every checkpoint below maps to — Track B learners will reproduce its tool output almost line for line.

**Checkpoint:** Your tree is clean (`git status`), tests are green, and `CLAUDE.md` opens with the SESSION PROTOCOL heading. You're about to start a *fresh* session — not the one that did setup.

## Steps

Each step is one phase of the session, in order. The whole point is that you can't reorder them: orientation gates the task, the plan gates the code, the close-out gates the next session. Don't skip ahead.

### 1. Start a fresh session and let it orient — do NOT give a task yet

Open a brand-new session against the bootstrapped project (this is the "fresh session" Tutorial 1 Step 6 set you up for). The agent has just read `CLAUDE.md`, so its first act is **Phase 0: Orient** — read `SAFEGUARDS.md`, read `SESSION_NOTES.md`, check the backlog, run `git status` and the dashboard, check for ghost sessions, **report, and wait.**

Your only job here is to let it finish orienting without handing it work.

**Expected result:** The agent reports current state and stops — clean tree, "Session 1, no prior session," backlog top item is F1, baseline `7 passed` — then asks for a task.
**Checkpoint:** You received an orientation report and a request for direction. Nothing has changed on disk. (If the agent started editing files, it skipped Phase 0 — [FM #1](../../starter-kit/SESSION_RUNNER.md#known-failure-modes).)

### 2. Give exactly one task — and watch it claim the session

Now hand over **one** deliverable:

- **Track B:** *"Implement F1 — `todo done <id>`."*
- **Track A:** name one small, vertical, testable item from your own backlog. One. Not two "while we're here."

The agent restates the deliverable, then — before any code — writes a **claim stub** to `SESSION_NOTES.md` (Phase 1B). That stub is what guarantees even a crashed session leaves a trace.

**Expected result:** The agent echoes back one deliverable and one workstream, then writes the IN-PROGRESS stub.
**Checkpoint:** `SESSION_NOTES.md` now contains a "What Session 1 Did … Status: Session claimed" stub. (See the transcript's [Phase 1B](T2_worked_transcript.md#1b--claim-the-session).)

### 3. Let it research and produce a plan — before any code

This is **Phase 2: Execute**, and its first move is *not* typing code. The agent reads the actual implementation it's about to change, states the expected vs. current behavior and the acceptance criteria, and challenges scope. For the sample, reading `add_todo` surfaces the empty-text bug **B1** — and the correct move is to *defer* it, not fix it. The output of this step is an **implementation plan** (what changes, what's explicitly out of scope, the test plan).

**Expected result:** A written plan: `mark_done` + `cmd_done` + a `done` subparser, five tests written first, and B1 named as out of scope.
**Checkpoint:** You can see a plan with an explicit **"What I'm NOT changing"** boundary. B1 is listed there, not in the change set. (Fixing B1 here would be scope creep — [FM #2](../../starter-kit/SESSION_RUNNER.md#known-failure-modes)/[#8](../../starter-kit/SESSION_RUNNER.md#known-failure-modes).)

### 4. The Present gate — approve before a line of code

The agent presents the plan and **stops**. This feels unnatural — the plan is small and obvious — and stopping anyway is exactly the discipline. Read the plan. If it's right, approve it; if not, send it back to revise. **No implementation happens until you say go.**

**Expected result:** The agent waits for your explicit approval and does not edit code until it has it.
**Checkpoint:** You gave an explicit "approved" (or requested changes) *before* any file changed. This is the highest-ROI gate in the methodology — a flawed plan caught here costs zero implementation effort. (Coding through this gate is the [Present-gate skip](../../ITERATIVE_METHODOLOGY.md#the-6-phases).)

### 5. Implement test-first — red, then green

With approval, the agent implements in the **test-first** order: write the failing tests, run them to confirm they fail *for the right reason* (red), then make the change and re-run the **full** suite (green).

```sh
# Track B — you'll see, in order:
python -m pytest test_done.py -q   # red: 5 failed  (done is an invalid choice)
# …agent applies the change to todo.py…
python -m pytest -q                # green: 12 passed  (7 original + 5 new)
```

**Expected result:** Five new tests fail before the change and pass after; the original seven never break.
**Checkpoint:** Red showed `5 failed`; green shows `12 passed`. A regression in the original 7 would mean stop and re-research — not patch forward. (A test that passes *before* the feature exists is testing nothing — [test-last](../../workstreams/DEVELOPMENT_WORKSTREAM.md#common-anti-patterns-development) is anti-pattern #3.)

### 6. Close out — hand off, runtime-verify, commit, and STOP

**Phase 3** is automatic; the agent does it without being asked, in order: record any project learning (3C), write the handoff (3D), then — because this deliverable changes runtime behavior — actually run the app to confirm the feature is live (3E; "tests pass" is not enough for a runtime change), and finally record the action in the `CHANGELOG.md` ledger and commit one atomic change with that entry co-staged (3F), then stop.

```sh
# Track B runtime smoke test — the feature is active, not just compiled:
python3 todo.py --file demo.json add "write the report"
python3 todo.py --file demo.json done 1     # -> done #1: write the report
python3 todo.py --file demo.json list        # -> 1 [x] write the report
```

**Expected result:** A full handoff written to `SESSION_NOTES.md` (what was done + commit, what's next, key files with line numbers, gotchas, a self-assessment score), a runtime smoke test, one `CHANGELOG.md` ledger entry (with F1 struck from `BACKLOG.md`), one commit, and a stop.
**Checkpoint:** `SESSION_NOTES.md` holds a handoff that names the next item (F2) and the key files; `git log` shows one feature commit; `CHANGELOG.md` gained one dated entry for F1 and `BACKLOG.md` no longer lists it; the agent did **not** start F2 or fix B1. That stop is "1 and done" — [FM #2](../../starter-kit/SESSION_RUNNER.md#known-failure-modes).

## Common mistakes

Cite the failure mode by number; link the list, don't paste it.
(Full list: [Known Failure Modes](../../starter-kit/SESSION_RUNNER.md#known-failure-modes).)

- **Giving the task during orientation.** You hand over F1 while the agent is still reporting state, so Phase 0 never closes with a real stop. Let it finish and wait — orientation exists for *you*, to confirm shared state before work begins. This is **FM #9 (task-in-prompt bypass)**; the countermeasure is Step 1 — let the report land before you direct.
- **Approving by silence at the Present gate.** Skimming the plan and saying nothing is not approval — and the agent must not code without it. Read it; the whole value of the gate is the cheap catch. Coding before approval is **FM #2 (keep going)** crossed with skipping the gate; the countermeasure is Step 4's explicit go-ahead.
- **"While I'm in there, I'll fix B1."** The empty-text bug is right next to your change and tempting. Fixing it makes this two deliverables. That's **FM #2 (keep going)** / **FM #8 (redesign during implementation)**; the countermeasure is the "What I'm NOT changing" boundary in Step 3 and "1 and done."

## You produced

One real deliverable taken end-to-end: a tested, runtime-verified `todo done <id>` (Track B) or your own first feature (Track A), plus a `SESSION_NOTES.md` handoff written to be *scored* by the next session. You ran Phase 0 to a real stop, held the Present gate, kept scope to one item, and closed out cleanly — the whole loop, once, for real. The deferred B1 bug and the three near-misses you just resisted (self-assigning during orient, coding before approval, fixing B1 inline) are exactly the material Tutorial 5 turns into cautionary cases.

## Next

→ **[Tutorial 5: Cautionary Use](T5_cautionary.md)** — the gates, the 27 failure modes, "1 and done," the vertical-slice gates, and the Plan-Mode exit trap, built on the near-misses from *this* session — and when the methodology is too heavy to bother.
