# Tutorial 3: The Compounding Loop

> **Objective:** Run the handoff-and-scoring loop across two sessions — *score* your predecessor's handoff and *write* one you know will be scored — and feel why session N+1 starts faster than session N when the handoff is good.
> **Prerequisites:** [Tutorial 2: Your First Session, End-to-End](T2_first_session.md) — you need the **Session 1 handoff** it produced (the one that named **F2** as next and scored itself 9/10); that handoff is the raw material this tutorial scores. Ideally you've also read [Tutorial 5: Cautionary Use](T5_cautionary.md). New here? Start at the [series index](README.md).
> **Time:** ~25 minutes
> **What you'll produce:** Backlog item **F2 — `todo rm <id>`** shipped as *Session 2*, plus the **scored handoff chain** on disk — a 1–10 evaluation of Session 1's handoff (with evidence) and Session 2's own handoff to Session 3, written to be scored in turn.
> **Track:** Pick one and stick with it for this pass —
> **A** (your own repo): run your *second* real session, scoring the handoff your Tutorial 2 session left; that run is your reference.
> **B** ([sample project](sample-project/)): run Session 2 on the sample, building **F2 — `todo rm <id>`**, the item your Tutorial 2 handoff pointed at.

## Why this matters

Tutorial 2 had you run one session well. But one good session is just a good session — the methodology's actual payoff is **compounding**, and compounding lives entirely in the seam *between* sessions. The mechanism is small and bidirectional: each session opens by scoring its predecessor's handoff, and closes by writing a handoff it knows will be scored. That two-sided pressure is what turns a sequence of isolated sessions into a chain where each one starts ahead of the last. It is not theory — it is the single change the framework credits with its longest clean streak:

- [Principle 8: Handoff Accountability](../../ITERATIVE_METHODOLOGY.md#8-handoff-accountability) — "the primary mechanism that makes sessions compound."
- [The Self-Improvement Loop](../../ITERATIVE_METHODOLOGY.md#the-self-improvement-loop) and its [between-sessions detail](../../ITERATIVE_METHODOLOGY.md#between-sessions-the-handoff-accountability-loop) — the outgoing/incoming loop, end to end.
- [`HOW_TO_USE.md` §What the Session Runner Contains](../../HOW_TO_USE.md#what-the-session-runner-contains) — the evidence: the handoff loop "added around Session 34 … correlated with 14 consecutive clean deliveries."

This tutorial does not restate Principle 8 or the close-out steps — they live in the [flight manual](../../ITERATIVE_METHODOLOGY.md) and the [cockpit checklist](../../starter-kit/SESSION_RUNNER.md#phase-3-close-out), one source of truth. It makes you *run both sides of the loop once* and watch the head start arrive.

## Before you start

You need your **completed Tutorial 2 run** — the project where Session 1 shipped F1 and left a handoff. Track B: that means F1 is in (12 tests green) and your `SESSION_NOTES.md` holds the Session 1 handoff that named **F2** as next, listed the key files with line numbers, and flagged the gotcha *"core stays I/O-free."* If you're picking up cold, re-read that handoff in the [worked transcript](T2_worked_transcript.md#3d--handoff-notes) — it is exactly what Session 2 will score.

```sh
# Track B, from your sandbox copy of the sample project:
python -m pytest                       # expect: 12 passed  (F1 shipped in Tutorial 2)
sed -n '/What Session 1 Did/,/Self-assessment/p' SESSION_NOTES.md   # the handoff you'll score
```

**Checkpoint:** Tests are green at 12, and you can see Session 1's handoff in `SESSION_NOTES.md` — it names F2, the key files, and the I/O-free gotcha. You're about to start a *fresh* session (Session 2) against that handoff.

## Steps

Each step is one move of the loop. The first and last steps — orienting *from* the handoff and writing the *next* one — are the whole point; the build in the middle is Tutorial 2's lesson, run again, faster. Don't skip ahead.

### 1. Open Session 2 and orient — read the handoff, don't re-discover

Start a brand-new session. Phase 0 runs as always — but this time there *is* a predecessor, so the orientation reads Session 1's handoff in `SESSION_NOTES.md` and absorbs it: F1 is done, the next item is **F2**, the relevant code is at `todo.py:57`/`:103`/`:127`, and the standing gotcha is *core stays I/O-free*.

**Expected result:** The orientation report says, in effect, *"Session 2. Predecessor shipped F1 and handed off F2 with key files and one gotcha; baseline 12 passed."* — and then stops for a task, exactly as in Tutorial 2.
**Checkpoint:** The agent oriented *from the handoff* — it already knows what's next and where the code lives, without re-reading the whole codebase. **That head start is the compounding.** (Had Session 1 written *"Done. Pick next from backlog,"* you'd be re-discovering all of it right now — that's [FM #15](../../starter-kit/SESSION_RUNNER.md#known-failure-modes).)

### 2. Give the one task the handoff teed up — and watch it go faster

Hand over **F2 — `todo rm <id>`** (Track A: the item *your* Tutorial 2 handoff named). The session claims itself (Phase 1B stub) and runs the same six phases you learned in Tutorial 2 — but Research is shorter, because the handoff already told it the shape: reuse the **I/O-free-core / I/O-shell split** (a pure `remove_todo` + a `cmd_rm` shell + one `rm` subparser), and settle the open question the handoff flagged (ids are *not* renumbered after a delete — next id stays `max(remaining)+1`, consistent with `test_add_reuses_max_id_plus_one_after_gaps`).

```sh
# Track B — the build runs as in Tutorial 2 (test-first, full suite each time); counts are illustrative:
python -m pytest test_rm.py -q   # red:  4 failed  (rm is an invalid choice, remove_todo missing)
# …agent applies remove_todo + cmd_rm + the rm subparser to todo.py…
python -m pytest -q              # green: 16 passed (12 prior + 4 new) — no regression
python3 todo.py --file demo.json rm 1   # runtime smoke test: -> removed #1: …
```

**Expected result:** A plan that *cites the predecessor's gotcha as an input* and reuses the F1 pattern instead of re-deriving it; F2 shipped test-first, the original 12 tests still green, runtime-verified.
**Checkpoint:** You can point at where Session 2 stood on Session 1's shoulders — the core/shell split came from the handoff, not from fresh analysis. (The full phase-by-phase mechanics are Tutorial 2's lesson and its [worked transcript](T2_worked_transcript.md); here you're watching them cost less.)

### 3. Close out — Phase 3A FIRST: score Session 1's handoff (1–10)

Now the close-out, and its *first* step is the one Session 1 had to skip (it had no predecessor): **[3A — Evaluate the Previous Session's Handoff](../../starter-kit/SESSION_RUNNER.md#3a-evaluate-the-previous-sessions-handoff).** Score Session 1's handoff against the [six minimum requirements](../../starter-kit/SESSION_RUNNER.md#minimum-handoff-requirements-all-mandatory) — did it give key files with line numbers? gotchas? a specific, actionable next step? — and write the verdict to `SESSION_NOTES.md` under a **"Session 1 Handoff Evaluation (by Session 2)"** heading, with *specific evidence*, not a vibe.

```markdown
### Session 1 Handoff Evaluation (by Session 2)
**Score: 9/10.** What helped: named F2 as the exact next item; key files with line
numbers (todo.py:57/103/127) meant zero re-discovery; the "core stays I/O-free"
gotcha pre-decided F2's structure. What was missing: no note on the id-reuse policy
decision (I had to make the call this session). ROI: saved ~one research cycle.
```

**Expected result:** A written 1–10 score with concrete "what helped / what was missing" evidence — the predecessor can see precisely why.
**Checkpoint:** `SESSION_NOTES.md` now holds a *numbered* evaluation of Session 1 with specifics, written *before* you self-assess. Skipping this — "my self-assessment is enough" — is [FM #10 (skip handoff evaluation)](../../starter-kit/SESSION_RUNNER.md#known-failure-modes); the evaluation *is* the compounding mechanism, which is why [3A comes first](../../starter-kit/SESSION_RUNNER.md#phase-3-close-out).

### 4. Write Session 2's handoff — knowing Session 3 will score it

Now you're on the *other* side of the loop. Write Session 2's handoff to all [six minimum requirements](../../starter-kit/SESSION_RUNNER.md#3d-write-handoff-notes): current state, what was done + commit, **F3 (`undo`) as the specific next item**, key files with the new line numbers, the id-reuse decision as a gotcha, and a self-assessment score. Write the notes you'd want to *receive* — the ones you just gave Session 1 a 9 for. Write it both to `SESSION_NOTES.md` and as a durable ` ```handoff ` receipt in [`HANDOFFS.md`](../../starter-kit/HANDOFFS.md): the receipt carries `predecessor_score: 9` — the score you just handed Session 1 — next to your own `self_score`, so *both* halves of the loop are machine-checkable, not just prose.

**Expected result:** A full handoff that names F3, the key files (`remove_todo`/`cmd_rm` and their lines), the id-reuse gotcha, and a self-score — meeting every minimum requirement.
**Checkpoint:** Re-read your handoff against the score you just handed out. A handoff like *"Done. Pick next from backlog"* would earn the ≤4/10 you'd refuse to write — that's [FM #15 (minimal handoff)](../../starter-kit/SESSION_RUNNER.md#known-failure-modes). You wrote one that would earn a 9.

### 5. Confirm both sides of the loop are on disk

The loop is real only if it's *written down*. Check that this session left both halves: the evaluation it owed its predecessor, and the handoff it owes its successor.

```sh
grep -n "Handoff Evaluation (by Session 2)" SESSION_NOTES.md   # incoming: you -> Session 1
grep -n "What's next.*F3"                  SESSION_NOTES.md     # outgoing: you -> Session 3
grep -n "predecessor_score: 9"             HANDOFFS.md          # the receipt: durable, machine-checkable
```

**Expected result:** Both lines are present; F2 is shipped, tested, and runtime-verified; the session stopped at one deliverable.
**Checkpoint:** `SESSION_NOTES.md` carries an *incoming* evaluation and an *outgoing* handoff. The yardstick you held Session 1 to is the one Session 3 will hold to you — that bidirectional pressure ([Principle 8](../../ITERATIVE_METHODOLOGY.md#8-handoff-accountability)) is what makes the chain improve instead of drift.

## Common mistakes

Cite the failure mode by number; link the list, don't paste it.
(Full list: [Known Failure Modes](../../starter-kit/SESSION_RUNNER.md#known-failure-modes).)

- **Skipping the predecessor evaluation.** Self-assessing feels like enough, and scoring the last session feels like extra work — so 3A gets dropped. This is **FM #10 (skip handoff evaluation)**; the countermeasure is that [3A runs *first* in close-out](../../starter-kit/SESSION_RUNNER.md#phase-3-close-out) — the evaluation is the compounding mechanism, not paperwork after it.
- **Writing a handoff you'd score ≤4.** *"Done. Pick next from backlog"* is technically a handoff and functionally useless — the next session starts blind. That's **FM #15 (minimal handoff)**; the countermeasure is the [six minimum requirements](../../starter-kit/SESSION_RUNNER.md#minimum-handoff-requirements-all-mandatory). Write notes that would earn a 9 or 10.
- **Scoring without evidence.** "Looked fine, 9/10" gives your predecessor nothing to act on, and the feedback loop quietly stops improving anything — see [`HOW_TO_USE.md` "The self-improvement loop isn't improving anything."](../../HOW_TO_USE.md#the-self-improvement-loop-isnt-improving-anything). The score creates accountability; the *specific evidence* creates the improvement. (And inflated scores that hide drift are how a 9/10 chain slides toward 1/10 — [protocol erosion, FM #17](../../starter-kit/SESSION_RUNNER.md#known-failure-modes); watch the trend in [Degradation Detection](../../starter-kit/SESSION_RUNNER.md#degradation-detection).)

## You produced

Session 2, complete: **F2 — `todo rm <id>`** shipped and runtime-verified, *and* a scored handoff chain on disk — a 1–10 evaluation of Session 1's handoff with concrete evidence, and Session 2's own handoff to Session 3 written to the six minimum requirements. You have now run **both sides of the loop**: you graded the session before you and set up the session after you, against the same yardstick. The point was never this one feature — it's that the score is a ratchet. Session 3 inherits a better starting line because you wrote it one, exactly as Session 1 wrote one for you.

## Next

→ **[Tutorial 4: Choosing & Adapting a Workstream](T4_workstreams.md)** — pick the right workstream for the work in front of you, and spin up a custom one when none fits. For now, run a real *Session 2* on a project you actually return to: the loop only compounds on work you repeat, and you only trust the ratchet once you've felt your own past handoff give you a head start.
