# Tutorial 5: Cautionary Use

> **Objective:** Read the methodology's guardrails the way they're meant to be read — the gates, the 27 failure modes, "1 and done," the vertical-slice gates, and the Plan-Mode exit trap as a reference the procedure enforces *for* you — and judge the one case where the right move is not to use the methodology at all.
> **Prerequisites:** [Tutorial 2: Your First Session, End-to-End](T2_first_session.md) — you need a session you've actually run, because its near-misses are this tutorial's raw material. New here? Start at the [series index](README.md).
> **Time:** ~20 minutes
> **What you'll produce:** A near-miss you catch on purpose — you deliberately push a session toward a gate, watch the gate hold, and record the catch — plus a written "use it / don't use it" verdict for one real task.
> **Track:** Pick one and stick with it for this pass —
> **A** (your own repo): probe the gates on a real backlog item; your [Tutorial 2](T2_first_session.md) run is the reference.
> **B** ([sample project](sample-project/)): probe them on the next backlog item, **F2 — `todo rm <id>`**, the item your Tutorial 2 handoff pointed at.

## Why this matters

The earlier tutorials had you *avoid* the near-misses. This one has you *provoke* them — because the guardrails are the actual product, and you only trust a guardrail you've felt hold. The deepest cautionary fact in the framework is that the discipline is perishable: 14 consecutive clean sessions can collapse within hours once steps start getting shaved off. Knowing the gates by name is how you notice the shaving before it cascades. The case is documented, not asserted:

- [Protocol Erosion](../../ITERATIVE_METHODOLOGY.md#protocol-erosion) — how a working methodology degrades, and why "this step doesn't apply to my session" is the erosion itself.
- [When to Use This Methodology](../../ITERATIVE_METHODOLOGY.md#when-to-use-this-methodology) — the explicit *do-not-use* list, so you don't burn the overhead on a one-off.
- [Evidence](../../README.md#evidence) — what holding the line actually changed.

This tutorial does not restate the gates, the 27 failure modes, or the vertical-slice gates — those live in the [cockpit checklist](../../starter-kit/SESSION_RUNNER.md) and the [flight manual](../../ITERATIVE_METHODOLOGY.md), one source of truth. It makes you *use* them as a reference and *test* that they hold.

## Before you start

You need a completed Tutorial 2 run. Re-open two things: the [worked transcript's near-misses](T2_worked_transcript.md#near-misses-this-session-caught-these-feed-tutorial-5) (the three catches), and your own `SESSION_NOTES.md` handoff from that session — the one that named **F2** as next and flagged **B1** (empty-text validation) as a known, deliberately-untouched item.

```sh
# Track B, from your sandbox copy of the sample project:
python -m pytest                 # expect: 12 passed  (F1 shipped in Tutorial 2)
grep -nE "F2|B1" BACKLOG.md      # both are still open work
```

**Checkpoint:** You can name the three near-misses from your own run, and you can see that F2 and B1 are still open. You are about to start a *fresh* session and deliberately steer it at a gate.

## Steps

The first step is reading; the rest is provoking a real session and watching the procedure refuse to break. Don't skip ahead — Step 1 gives you the names you'll point at in Steps 2–4.

### 1. Map your own near-misses to their failure modes — consult, don't memorize

Open the [Known Failure Modes](../../starter-kit/SESSION_RUNNER.md#known-failure-modes) table and the [12 quality gates](../../ITERATIVE_METHODOLOGY.md#quality-gates-summary). For each of the three near-misses your Tutorial 2 session caught, find the row that names it and the countermeasure that stopped it.

**Expected result:** Three clean mappings — "the backlog says F1, I'll just start" → **[FM #1](../../starter-kit/SESSION_RUNNER.md#known-failure-modes)** (Phase 0 stop); "I'll fix B1 while I'm in there" → **[FM #2](../../starter-kit/SESSION_RUNNER.md#known-failure-modes) / [#8](../../starter-kit/SESSION_RUNNER.md#known-failure-modes)** ("1 and done"); "the plan's obvious, I'll just code" → the **Present gate** ([Quality Gate #6](../../ITERATIVE_METHODOLOGY.md#quality-gates-summary)).
**Checkpoint:** You can point at the exact row for each. Notice what you did *not* have to do: memorize all 26. The list is a reference you consult; the gates enforce the behavior whether or not you can recite it.

### 2. Provoke Phase 0 — hand over a task during orientation

Start a brand-new session against the project. While the agent is still orienting — before it has reported state and stopped — interrupt with a task: *"Implement F2 — `todo rm <id>`."* You are deliberately doing the thing Tutorial 2 told you not to: handing work in mid-orient.

**Expected result:** The session does **not** drop orientation and start coding. It finishes all of Phase 0, reports state, and waits — a task in the prompt does not complete Phase 0.
**Checkpoint:** The gate held: you pushed and it still stopped for you. Write that down in `SESSION_NOTES.md` ("Caught: task-in-prompt during orient; Phase 0 held"). That recorded catch is **[FM #9](../../starter-kit/SESSION_RUNNER.md#known-failure-modes)**'s countermeasure working. (If it *did* start editing, the protocol isn't loaded — re-check [Tutorial 1 Step 2/6](T1_setup.md).)

### 3. Provoke the scope boundary — "while you're in there, also fix B1"

Now approve F2 the normal way, and at the plan/Present beat add the tempting rider: *"and while you're in `todo.py`, just fix the empty-text bug B1 too."* B1 is right next to your change and trivial. Watch what a session on the procedure does with a second deliverable smuggled in.

**Expected result:** It declines to bundle — B1 is named as out of scope and routed to its own session, exactly as your Tutorial 2 plan deferred it. One intent ships; the other is handed off.
**Checkpoint:** Scope held against a direct request to break it. That's "1 and done" — **[FM #2](../../starter-kit/SESSION_RUNNER.md#known-failure-modes)** crossed with **[FM #8](../../starter-kit/SESSION_RUNNER.md#known-failure-modes)** (redesign-during-implementation). Record this catch too. (Two small things in one session is still two deliverables.)

### 4. Recognize the two traps you can't easily stage

Some gates you won't trip in a tutorial, but you must recognize them on sight:

- **The Plan-Mode exit trap.** When a multi-phase plan arrives under Plan Mode's auto-preamble *"Implement the following plan,"* that wording is **not** a go-ahead to code — it is the [Plan-Mode exit trap](../../starter-kit/SESSION_RUNNER.md#phase-1-receive-task) (**[FM #19](../../starter-kit/SESSION_RUNNER.md#known-failure-modes)** plan-mode bypass, **[FM #18](../../starter-kit/SESSION_RUNNER.md#known-failure-modes)** planning-to-implementation bleed). Recognize it; planning and implementation are separate sessions.
- **The vertical-slice masquerade.** "1 and done" has exactly one sanctioned way to ship more than one layer: a *verified vertical slice* — **one capability** end to end under the four mandatory gates defined in [§Vertical Slice Sessions](../../starter-kit/SESSION_RUNNER.md#vertical-slice-sessions). It is never a license to bundle two capabilities. Bundling F2 **and** B1 and calling it "a slice" is **[FM #26](../../starter-kit/SESSION_RUNNER.md#known-failure-modes)**. The test: does one prior-session plan-mode contract enumerate exactly this layer set, all of the *same* capability?

**Expected result:** You can state, in one sentence each, why "Implement the following plan" doesn't mean start coding, and why F2+B1 is not a slice.
**Checkpoint:** You can tell a legitimate slice (data + service + client + tests of *one* capability, four gates met) from a mega-session wearing the slice costume (two capabilities, or a plan plus its code).

### 5. Make the "don't use it" call

Take one real task you actually have and run it through the [When to Use](../../ITERATIVE_METHODOLOGY.md#when-to-use-this-methodology) test. Is it repeated work where quality compounds and a stakeholder approves the output — or a genuine one-off where the overhead exceeds the work? Write a one-line verdict.

**Expected result:** A written call — e.g., *"One-off config tweak, no repetition, no stakeholder → skip the methodology, just do it"* or *"First of ~6 similar migrations → use it; Session 1's overhead pays off by Session 3."*
**Checkpoint:** You produced a use/don't-use decision grounded in the actual criteria, not a reflex to always run the full protocol. Running all six phases on a trivial one-off is its own failure — see [HOW_TO_USE.md "The methodology feels too heavy for this task"](../../HOW_TO_USE.md#the-methodology-feels-too-heavy-for-this-task).

## Common mistakes

Cite the failure mode by number; link the list, don't paste it.
(Full list: [Known Failure Modes](../../starter-kit/SESSION_RUNNER.md#known-failure-modes).)

- **Trying to memorize the 27 failure modes.** They are a reference you consult at the moment of temptation, not a quiz. Operating from a half-remembered gist is itself **FM #3 (skim documents)** — the countermeasure is to open the table and read the row, the way you did in Step 1.
- **"This step doesn't apply to my session."** The single most important cautionary line in the framework: that thought *is* the erosion. This is **FM #17 (protocol erosion)** — every step exists because a session failed without it, and the vertical-slice allowance *adds* a gate, it never removes one. When you catch yourself shaving a step, see [Degradation Detection](../../starter-kit/SESSION_RUNNER.md#degradation-detection).
- **Calling a two-capability bundle "a vertical slice."** Pre-declaring a contract for *one* capability's layers is the slice; reaching for the slice vocabulary to ship F2 and B1 together is **FM #26 (mega-session masquerading as a vertical slice)**. One capability, one prior contract, exactly that layer set — or split it.

## You produced

Two near-misses you caught on purpose — recorded in `SESSION_NOTES.md` as gates that held when you deliberately pushed on them (task-in-prompt during orient; a second deliverable smuggled into the Present beat) — and a written use/don't-use verdict for one real task. You now read the failure-mode list and the gates the way they're meant to be read: as a reference the procedure enforces for you, not a thing to recite. And you know the one task profile where the disciplined move is to *not* use the methodology at all.

## Next

You've now installed the framework, run one real session, and stress-tested the gates. Next in the track:

→ **[Tutorial 3: The Compounding Loop](T3_compounding_loop.md)** — run the handoff-and-scoring loop across sessions and watch session N+1 beat session N. (See the [curriculum](README.md#curriculum) for the full track.) And take the use/don't-use judgment from Step 5 to a real project — the methodology earns its keep on the work you'd otherwise repeat without learning from.
