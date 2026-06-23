# Tutorial 6: Multi-Session Campaigns

> **Objective:** Recognize when a deliverable is too big for one session even after correct decomposition, and carry it across many sessions using the **planning → execution → consolidation** sequence — with a checkpoint deliverable at every boundary — without losing the thread.
> **Prerequisites:** [Tutorial 4: Choosing & Adapting a Workstream](T4_workstreams.md) — its Audit session ended by recommending *fix B1, fix B2, and run the 7-dimension audit across the whole CLI*, and noticed that recommendation is "more than one session's work." That recommendation is the campaign this tutorial runs. New here? Start at the [series index](README.md).
> **Time:** ~30 minutes (this is the heaviest concept in the series — it coordinates *across* sessions, not within one).
> **What you'll produce:** A real `CAMPAIGN.md` (the planning-session output), one execution-session **unit deliverable** committed as a checkpoint, and a partial `REPORT.md` (the consolidation output) — the three campaign session types, run once each in miniature — plus the recognition skill: the three-part test that tells you a campaign is the right tool *before* you stand one up.
> **Track:** Pick one and stick with it for this pass —
> **A** (your own repo): take a deliverable you've already discovered is too big for one session — a repo-wide audit, a hardening pass, an inherited-codebase familiarization — and run its planning session for real.
> **B** ([sample project](sample-project/)): run the **repository-wide hardening audit** of the todo CLI that Tutorial 4's audit recommended.

## Why this matters

Every tutorial so far lived *inside* one session — Phase 0 to close-out, one deliverable, stop. But some deliverables don't fit one session even when you decompose them correctly: paper-wide claim verification across hundreds of citations, security hardening across dozens of endpoints, familiarization with an inherited 40-module codebase. The six phases bound a single session and [Principle 9](../../ITERATIVE_METHODOLOGY.md#9-session-scope-bounding) bounds what one session may *produce*; coordinating many sessions toward a single deliverable operates at a different scale entirely. Forcing that work into one session is not heroic — it is the failure the campaign layer exists to prevent: the second half gets less rigor than the first, there's no resumability when it crashes, and "1 and done" is violated by a deliverable that was secretly dozens of micro-deliverables fused together.

- [§Multi-Session Campaigns](../../ITERATIVE_METHODOLOGY.md#multi-session-campaigns) — what a campaign is, and the crucial distinction: a campaign is **not** a workstream (workstreams adapt the phases to a domain; campaigns sequence sessions toward one deliverable *within* a workstream).
- [When to write or invoke a campaign](../../ITERATIVE_METHODOLOGY.md#when-to-write-or-invoke-a-campaign) — the three-part test, and just as important, when **not** to reach for one.
- [Phase 1's multi-session campaign check](../../starter-kit/SESSION_RUNNER.md#phase-1-receive-task) — the gate that catches campaign-shaped work at the start of a session, which is exactly what Tutorial 4 tripped.

This tutorial does not restate the campaign template, the session sequence, or the anti-pattern list — they live in [§Multi-Session Campaigns](../../ITERATIVE_METHODOLOGY.md#multi-session-campaigns), the [blank template](../../workstreams/TEMPLATE_CAMPAIGN.md), and the realized [`INHERITED_CODEBASE_FAMILIARIZATION_CAMPAIGN.md`](../../workstreams/INHERITED_CODEBASE_FAMILIARIZATION_CAMPAIGN.md). It makes you *run the three session types once* on a deliberately small deliverable, so you feel the session boundaries that keep a long campaign from collapsing into one mega-session.

> **A note on scale — read this before you start.** The todo CLI is tiny; a real hardening audit of it would fit in one or two sessions, and the three-part test below would tell you **not** to stand up a campaign for it. We use it anyway, the same way the whole series uses a toy: to rehearse the *structure* safely. So this tutorial **telescopes** what must, in real life, be **separate sessions** — you'll walk planning, one execution unit, and consolidation in a single sitting to see the whole arc. The lesson is precisely that they are separate sessions; Step 4 is where that boundary becomes the point.

## Before you start

You need the project from Tutorial 4, with the audit's findings on disk. Track B: the sample todo CLI where Tutorials 2–3 shipped F1 and F2 and Tutorial 4 ran an audit that filed **B1** (`add` accepts empty/whitespace text) and **B2** (no confirmation before overwriting the data file) without fixing them.

```sh
# Track B, from your sandbox copy of the sample project:
python -m pytest        # expect: 16 passed  (F1 + F2 shipped; the Tutorial 4 audit changed no code)
ls docs/methodology/workstreams/   # the catalog, incl. *_CAMPAIGN.md templates installed by bin/sync in Tutorial 1
```

**Checkpoint:** Tests are green at 16, your Tutorial 4 audit report (B1, B2 with `file:line` and recommendations) is on disk, and you can see the campaign templates — `TEMPLATE_CAMPAIGN.md`, `INHERITED_CODEBASE_FAMILIARIZATION_CAMPAIGN.md`, `RESEARCH_EXHAUSTIVE_VERIFICATION_CAMPAIGN.md` — beside the workstreams. (Tutorial 1's `bin/sync` put them there; they're the templates you're about to use.)

## Steps

Each step is one move of the campaign. Steps 1–2 are the *recognition and planning* skill, Step 3 is one *execution* unit, Step 4 is the boundary that keeps the campaign honest, and Step 5 *consolidates*. Don't skip ahead.

### 1. Apply the three-part test — is this actually a campaign?

Tutorial 4 ended by noticing the audit recommended more than one session's work. "A lot to do" is not the trigger, though — the trigger is a specific three-part test. Open [When to write or invoke a campaign](../../ITERATIVE_METHODOLOGY.md#when-to-write-or-invoke-a-campaign) and check that **all three** hold:

| # | The condition | Does the hardening audit meet it? |
|---|---------------|-----------------------------------|
| 1 | Can't be produced in one session even under correct decomposition | On a real codebase, yes — a 7-dimension sweep plus per-finding evidence across many files is dozens of micro-deliverables. *On this toy, honestly no* — which is the teaching point. |
| 2 | The shape is, or will be, repeatable | Yes — "audit every dimension, file findings with evidence, consolidate into a prioritized backlog" recurs on every codebase you inherit or harden. |
| 3 | Cross-session coordination (shared schema, checkpoint deliverables, calibration) is load-bearing for quality | Yes — without a locked finding schema, units don't merge; without checkpoints, a crash restarts the run. |

The same section names when **not** to: the work fits in one session, the deliverable is genuinely one-off, or the right artifact is a *new workstream* (which was Tutorial 4's lesson — don't confuse the two). For the toy, condition 1 fails, so the honest answer on a real project this size is "not a campaign." We proceed anyway *as a rehearsal*, with that flag raised — manufacturing campaign ceremony for one-session work is its own waste, the inverse of the mistake this tutorial mostly guards against.

**Expected result:** A written verdict — *"All three conditions hold at real scale (1 only because the toy is small); shape is the Audit-extending hardening campaign; proceeding as a structural rehearsal."*
**Checkpoint:** You can name which of the three conditions hold and which is borderline, and you didn't reach for a campaign merely because "there's a lot to do." Recognition first, ceremony second.

### 2. Run the planning session — produce `CAMPAIGN.md` (no findings yet, no fixes)

Session 1 of any campaign is a **planning session** ([§Session Types](../../ITERATIVE_METHODOLOGY.md#session-types) — heavy Phase 2, and its Phase 3 deliverable is *the plan itself*, not work product). The campaign extends the Audit workstream, exactly as the realized [`INHERITED_CODEBASE_FAMILIARIZATION_CAMPAIGN.md`](../../workstreams/INHERITED_CODEBASE_FAMILIARIZATION_CAMPAIGN.md) does — its per-module audit primitive is what this campaign scales repository-wide. Copy the [blank template](../../workstreams/TEMPLATE_CAMPAIGN.md) and fill the load-bearing decisions:

- **Choose the scoping unit.** One execution session per **audit dimension** — for code, the [Audit workstream's *When to Use*](../../workstreams/AUDIT_WORKSTREAM.md#when-to-use) frames these as *classes of issue* (*"security, performance, correctness, style"* — the same clause Tutorial 4 matched). Here the campaign picks its own — *correctness · input-validation · data-safety · error-handling* — the axis that splits cleanly and merges cleanly for this CLI.
- **Lock the deliverable contract.** One per-finding schema, used by every unit, fixed *now*: `| # | dimension | location | severity | evidence | recommendation |`, with a closed status vocabulary. Schema drift across units is what forces consolidation rework.
- **Set exit criteria.** A unit is done when its dimension is examined across every function in `todo.py` and every finding carries evidence; the campaign halts (not pauses — halts) on a systemic finding or a stakeholder direction change.

```sh
# in your installed project (adopter layout):
mkdir -p docs/hardening-campaign/units
cp docs/methodology/workstreams/TEMPLATE_CAMPAIGN.md docs/hardening-campaign/CAMPAIGN.md
# fill: mode, the dimension list as the unit map, the locked per-finding schema, exit criteria
```

The bones of a filled `CAMPAIGN.md` — a thin coordination contract, not a fork of the framework:

```markdown
# Todo-CLI Hardening Campaign  (extends AUDIT_WORKSTREAM.md)
Unit map (one execution session each): correctness · input-validation · data-safety · error-handling
Per-finding schema (LOCKED): | # | dimension | location | severity | evidence | recommendation |
Exit criteria: every dimension examined across all of todo.py; every finding has evidence.
Consolidation deliverable: REPORT.md — prioritized remediation backlog feeding Development sessions.
```

Then **stop and get approval.** Stakeholder sign-off on `CAMPAIGN.md` is the campaign's second-highest-leverage gate (after each execution session's own implement gate) — a bad plan multiplies its cost across every unit. Because planning a campaign is the decision every later session inherits, this session runs at your agent's **deepest reasoning tier** ([Matching Reasoning Effort to Stakes](../../ITERATIVE_METHODOLOGY.md#matching-reasoning-effort-to-stakes) — high compounding cost ⇒ reason hard up front).

**Expected result:** A real `CAMPAIGN.md` with the unit map, the locked schema, and exit criteria — and **zero code and zero findings produced**; planning sessions plan.
**Checkpoint:** The plan exists and reads like the realized campaign templates — it specializes the session *sequence*, not the phases or gates. No `todo.py` was touched, no finding was filed; that's the next session's job.

### 3. Run one execution session — one unit, committed as a checkpoint

Session 2 is the first **execution session**, and it runs the full Audit pattern on **exactly one unit**. Pick the *input-validation* dimension. Pre-Flight reads `CAMPAIGN.md` first; the [Phase 1B stub](../../starter-kit/SESSION_RUNNER.md#1b-claim-the-session-mandatory) names the unit in progress (`unit: input-validation`) so a crash is detectable. Examine every function in `todo.py` against that one dimension, and file findings into the locked schema — `B1` resurfaces here with evidence, alongside any sibling the dimension turns up. Write the unit deliverable and **commit it before close-out** — the unit file *is* the checkpoint ([Resumability](../../workstreams/TEMPLATE_CAMPAIGN.md#resumability)).

```markdown
<!-- docs/hardening-campaign/units/input-validation.md -->
| # | dimension        | location    | severity | evidence                                   | recommendation                     |
|---|------------------|-------------|----------|--------------------------------------------|------------------------------------|
| 1 | input-validation | todo.py:44  | moderate | `add_todo("")` creates a blank task (B1)   | reject empty/whitespace (own session) |
| 2 | input-validation | todo.py:75  | low      | `cmd_add` forwards `args.text` unchecked   | validate at the core, not the shell   |
```

```sh
python -m pytest                 # expect: still 16 passed — an audit unit changes no code
git add docs/hardening-campaign/units/input-validation.md && git commit -m "campaign(hardening): input-validation unit"
```

Note what this unit is and isn't: it **files** findings, it does **not fix** them — the same Audit-vs-Development discipline Tutorial 4 taught (you found B1; you didn't patch it). The actual fixes are follow-on *Development* sessions that the campaign's consolidation backlog will feed — they live **outside** the campaign, exactly as the inherited-codebase campaign's backlog [feeds Development sessions](../../workstreams/INHERITED_CODEBASE_FAMILIARIZATION_CAMPAIGN.md). And notice how much of the prior series is still live here: this is still a six-phase session (Tutorial 2), it still scores its predecessor and hands off the next unit (Tutorial 3), and it's still governed by a consciously chosen workstream (Tutorial 4).

**Expected result:** One committed `units/input-validation.md` with evidence-bearing rows in the locked schema; suite still green at 16; the handoff names **the next unit** (`data-safety`, which will pick up B2) as the specific next step.
**Checkpoint:** Your deliverable is one unit's findings, on disk and committed, in the schema the plan locked. A future session — or a recovery after a crash — can read `CAMPAIGN.md`, see which units have files, and resume from the first one that doesn't. That checkpoint-and-resume property is the whole reason this is a campaign and not one long session.

### 4. Stop at one unit — the per-unit boundary is the campaign's "1 and done"

You finished `input-validation` fast and you can feel it: *"data-safety is right there, let me just knock out B2 too, and maybe start error-handling."* That pull is the one-session attempt re-emerging *inside* the campaign — and it is the same failure the campaign existed to prevent, now wearing a "vertical slice" costume. Two different units bundled into one session is **FM #26 (mega-session masquerading as a vertical slice)**; the "just keep going" that drives it is **FM #2 (keep going)**. The campaign's per-unit boundary is "1 and done" at campaign scale: one unit per session, then close out. Resist it, and the campaign stays resumable and uniformly rigorous; ignore it, and the second unit gets the thin reasoning the campaign was designed to avoid.

**Expected result:** You closed out after one unit — `input-validation` only — even though the next unit looked cheap.
**Checkpoint:** Exactly one new unit file exists, and your handoff (not a second commit of work) is what carries `data-safety` forward. If you'd bundled two units, the [Degradation Detection](../../starter-kit/SESSION_RUNNER.md#degradation-detection) row "two unrelated capabilities in one session → FM #26" would be firing.

### 5. Consolidate — merge, find the cross-unit pattern, write the backlog

Skip ahead now to the campaign's **consolidation session** (Session N+2). In real life it runs only after every execution unit is done; here you'll write a *partial* one over your single unit, which is itself a discipline — *do not synthesize coverage you did not produce.* The consolidation session **does not re-do per-unit work**: it aggregates the unit files, surfaces patterns visible only at campaign scale, and writes a prioritized remediation backlog as `REPORT.md`. The pattern the toy actually exposes once you line the findings up: **B1** (core trusts un-validated text) and **B2** (core overwrites the store without confirmation) are the *same* underlying weakness — *the core trusts its inputs and its filesystem blindly* — a finding no single unit could see.

```markdown
<!-- docs/hardening-campaign/REPORT.md (partial — 1 of 4 units complete) -->
## Coverage
input-validation: complete (2 findings). data-safety / correctness / error-handling: pending.
## Cross-unit pattern
The core layer trusts its inputs and its filesystem without guarding either (B1, and B2 once data-safety runs).
## Remediation backlog (feeds Development sessions, ordered by severity)
1. Validate todo text at the core (B1) — own session, own test.
2. Confirm-before-overwrite for the store (B2) — own session.
```

The temptation here mirrors Step 4's: while merging you'll spot a fix and want to apply it. That's **consolidation creep** — log it in the backlog and keep merging; fixing during consolidation is per-unit work in the wrong session.

**Expected result:** A `REPORT.md` that states honest partial coverage, names the cross-unit pattern, and lists an ordered remediation backlog — and changes no code.
**Checkpoint:** You've now produced all three campaign deliverables — `CAMPAIGN.md`, one `units/*.md`, and a partial `REPORT.md` — and the report's backlog is the bridge back to ordinary Development sessions. The campaign is resumable from its first pending unit, and nothing was fixed inside it.

## Common mistakes

Cite the failure mode by number; link the list, don't paste it.
(Full list: [Known Failure Modes](../../starter-kit/SESSION_RUNNER.md#known-failure-modes); campaign-specific anti-patterns live in [`TEMPLATE_CAMPAIGN.md` §Anti-Patterns](../../workstreams/TEMPLATE_CAMPAIGN.md#anti-patterns).)

- **The one-session attempt.** Running the whole campaign — every dimension, all the findings — in a single session. The back half gets thinner reasoning than the front, and a crash restarts everything. This is the **one-session attempt** anti-pattern, and inside a session it surfaces as **FM #26 (mega-session)** and **FM #2 (keep going)**; the countermeasure is the per-unit boundary you held in Step 4.
- **Manufacturing a campaign for one-session work.** The inverse mistake — standing up `CAMPAIGN.md`, units, and a consolidation session for work that fits in one sitting. The [three-part test](../../ITERATIVE_METHODOLOGY.md#when-to-write-or-invoke-a-campaign) exists to stop both directions; if condition 1 fails, the right answer is a normal session (or, if the work is a new *kind* of task, the [custom workstream from Tutorial 4](T4_workstreams.md)), not campaign ceremony.
- **Skipping the planning session.** Jumping straight to filing findings without a locked schema in `CAMPAIGN.md`. Units written to different shapes don't merge, and the consolidation session pays for it in rework — the **skip-the-planning-session** anti-pattern. The countermeasure is Step 2's locked deliverable contract, approved before any unit runs.
- **Consolidation creep.** Doing per-unit work in the consolidation session because you noticed a problem while merging. Stop, log it as a backlog item, return to merging — the **cross-unit consolidation creep** anti-pattern from Step 5.

## You produced

A complete pass through a multi-session campaign in miniature: a real `CAMPAIGN.md` whose plan locks the unit map and the per-finding schema, one committed execution unit (`units/input-validation.md`) that filed evidence without fixing anything, and a partial `REPORT.md` that surfaced a cross-unit pattern and handed a prioritized backlog to ordinary Development sessions. More durably, you have the **recognition skill** — the three-part test that tells you, before you build any of it, whether the deliverable in front of you is genuinely campaign-shaped or just large. You ran the three session types, felt the per-unit boundary that keeps a long campaign uniformly rigorous and resumable, and saw how a campaign sequences sessions *toward* a deliverable that no single session could produce — while every session inside it still ran the same six phases, the same handoff loop, and the same gates you've practiced since Tutorial 2.

## Next

→ **[Tutorial 7: Portfolio & Dashboard Ops](T7_portfolio_dashboard.md)** — zoom out from one project to many: run the health dashboard across your whole portfolio and let the risk matrix decide where the next session goes. For now, do it for real on Track A: take a deliverable you already suspect is too big for one session, run *only* its planning session, and let the `CAMPAIGN.md` — not a heroic marathon — be where the work gets organized.
