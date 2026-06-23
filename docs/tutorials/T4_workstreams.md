# Tutorial 4: Choosing & Adapting a Workstream

> **Objective:** Match the task in front of you to the right workstream — Design, Architecture, Development, Audit, or Research-Documentation — and, when none of them fits, spin up a custom one from the template instead of forcing a bad fit.
> **Prerequisites:** [Tutorial 3: The Compounding Loop](T3_compounding_loop.md) — you've now run two sessions (Tutorial 2 shipped F1, Tutorial 3 shipped F2), and both were *the same kind of work* without you ever naming it. This tutorial names it. New here? Start at the [series index](README.md).
> **Time:** ~25 minutes
> **What you'll produce:** A recorded **workstream selection** for a real task (the choice, plus the two or three things it changes about Phase 2 and Phase 3), and a new `*_WORKSTREAM.md` file you create from the template for a task no shipped workstream covered.
> **Track:** Pick one and stick with it for this pass —
> **A** (your own repo): name the workstream your last two real sessions were in, then choose one consciously for your next task.
> **B** ([sample project](sample-project/)): run an *Audit* session on the todo CLI you've been building, then draft a custom *Release* workstream for it.

## Why this matters

For two sessions you've been running the **Development workstream** — implementing features — and you never had to say so, because Development is the unstated default. That works right up until the task in front of you *isn't* feature work: an audit, a design pass, a release. Reach for the only lens you've used and an audit quietly turns into "while I'm here, let me just fix it," and a design session ships untested code. The workstream is the methodology's domain-specific lens: the *same* 9 principles, 6 phases, and 12 gates, with only Phase 2, Phase 3, scope validation, verification, and the reference tables specialized to the work. Choosing the right one — or building one when none fits — is a skill, not a default.

- [Adapting to Your Domain](../../ITERATIVE_METHODOLOGY.md#adapting-to-your-domain) — workstreams are domain-specific adaptations; the phases and gates don't change, only the five things listed there.
- [`HOW_TO_USE.md` §Workstreams](../../HOW_TO_USE.md#workstreams) — "the workstream is where knowledge compounds." Session 1 invents the patterns; Session 5 applies them automatically.
- [Workstreams (README)](../../README.md#workstreams) — the five shipped lenses and what each is best for, at a glance.

This tutorial does not restate the phases, the workstream catalog, or the failure-mode list — they live in the [flight manual](../../ITERATIVE_METHODOLOGY.md), the [README](../../README.md#workstreams), and the [cockpit checklist](../../starter-kit/SESSION_RUNNER.md). It makes you *make the selection decision once*, feel a workstream change the work, and *build one* when the catalog runs out.

## Before you start

You need the project from the earlier tutorials, with two Development sessions behind it. Track B: the sample todo CLI where Tutorial 2 shipped F1 and Tutorial 3 shipped F2.

```sh
# Track B, from your sandbox copy of the sample project:
python -m pytest        # expect: green (16 passed if you built F2 in Tutorial 3)
ls docs/methodology/workstreams/   # the shipped workstreams, installed by bin/sync in Tutorial 1
```

**Checkpoint:** Tests are green, and you can see the shipped workstream files — `DESIGN_`, `ARCHITECTURE_`, `DEVELOPMENT_`, `AUDIT_`, `RESEARCH_DOCUMENTATION_`, and the blank `TEMPLATE_WORKSTREAM.md` — under `docs/methodology/workstreams/`. (Tutorial 1's `bin/sync` put them there; they're the catalog you're about to choose from.)

## Steps

Each step is one action. Steps 1–3 are the *choosing* skill; Step 4 is the *adapting* skill; Step 5 makes the choice persist. Don't skip ahead.

### 1. Name the workstream you've already been using

Open [`DEVELOPMENT_WORKSTREAM.md`](../../workstreams/DEVELOPMENT_WORKSTREAM.md#when-to-use) and read its **When to Use**: *"implementing a series of related features … running a bug fix campaign … any development work where the same type of task repeats with variation."* That is exactly what Tutorial 2 and Tutorial 3 were. You were in the Development workstream the whole time — it's just the default you never had to declare.

**Expected result:** You can point at the Development workstream's *When to Use* and see your last two sessions described in it.
**Checkpoint:** You know the word **workstream**, that you've been operating in Development, and that [four other lenses](../../README.md#workstreams) exist for work that isn't feature implementation.

### 2. Match a new task to a workstream — read the *When to Use*, don't default

A new priority arrives: **before sharing the todo CLI more widely, review it for correctness and edge-case bugs.** Nothing new ships — so this is *not* Development. At [Phase 1](../../starter-kit/SESSION_RUNNER.md#phase-1-receive-task), the session runner asks "which workstream governs this work?" Answer it by reading each lens's *When to Use* and matching, instead of reaching for the one you know:

| Lens | *When to Use* says… | Fit? |
|------|---------------------|:----:|
| Design | UI layouts, visual hierarchy | no |
| Architecture | systems, APIs, data models | no |
| Development | *implement* features / run a bug-fix campaign | no — you're *finding*, not fixing |
| **Audit** | *"auditing a codebase for a specific class of issue (security, performance, **correctness**, style)"* | **yes** |
| Research-Documentation | cited papers, regulatory analyses | no |

→ **Audit workstream.** Record the choice and its one-line rationale (the *When to Use* clause it matched) in your session notes or `CONTEXT.md`.

**Expected result:** A written selection — *"This session → Audit workstream, because the task is finding a class of issue (correctness), not implementing."*
**Checkpoint:** You chose by matching the task to a workstream's [*When to Use*](../../workstreams/AUDIT_WORKSTREAM.md#when-to-use), not by defaulting to Development. Reaching for Development on every task — and then "just fixing" what you find — is **FM #12 (workstream transfer amnesia)**; you just avoided it by choosing deliberately.

### 3. Run the session in that lens — same gates, different Phase 2 and Phase 3

The workstream changes nothing about the gates; it changes the *domain work inside them*. For Audit versus the Development you ran in Tutorial 2:

- **Phase 2** is *define audit criteria + inventory scope* (a criteria table and a coverage list), not *study requirements + read the code you'll modify*.
- **Phase 3** produces an [**audit report**](../../workstreams/AUDIT_WORKSTREAM.md#the-audit-report) — severity, location, evidence, recommendation — **not code.**
- **Verification** is *coverage* ("examined N of M") plus every finding carrying evidence, not "tests still green / no regression."
- The default **reasoning tier** shifts too: an audit mutates nothing, but a *missed* finding is costly, so scale depth to the cost of a miss ([Matching Reasoning Effort to Stakes](../../ITERATIVE_METHODOLOGY.md#matching-reasoning-effort-to-stakes)).

Do the small real version: write a two-row criteria table and a scope list for `todo.py`, read it against them, and you'll surface the project's known rough edges as *findings* — **B1** (`add` accepts empty/whitespace text) and **B2** (no confirmation before overwriting the data file), each with a `file:line` and a recommendation. The discipline that makes this an Audit and not a Development session: **you file them; you do not fix them.** Fixing is a separate Development session that the audit *recommends* — patching B1 inline here is the very scope creep [Tutorial 5](T5_cautionary.md) warned about, and the Development reflex **FM #12** predicts you'll feel.

```markdown
### Finding #1: `add` accepts empty text  — Severity: Moderate — todo.py:44
Evidence: `add_todo("")` creates a blank task; no validation (see NOTE in todo.py).
Recommendation: reject empty/whitespace in a *future Development session* (own test).
```

**Expected result:** A short findings report (B1, B2) with locations and recommendations — and **zero code changed**; the suite is still green because an audit doesn't touch code.
**Checkpoint:** Your deliverable is a *report*, not a diff. You found the bugs the workstream's way — surfaced with evidence and handed off — instead of the Development way of patching them on sight.

### 4. When none fits: spin up a custom workstream from the template

A different task is coming: **cut a tagged `v0.1` release** of the todo CLI — update the changelog, bump the version, tag it, smoke-test the packaged artifact. Walk the catalog again: not Design, not Architecture, not Audit, not Research-Documentation — and not Development either (you're not implementing a feature or running a bug campaign). None fits. [Phase 1](../../starter-kit/SESSION_RUNNER.md#phase-1-receive-task) names this case directly — *"if no workstream document exists for the task type, follow the master framework"* — and when the work is the kind you'll repeat, the methodology's move is to build the missing lens first rather than force the task into a workstream it doesn't belong to.

The methodology's stance is *adapt, don't force*. Follow [`HOW_TO_USE.md` §Creating a Custom Workstream](../../HOW_TO_USE.md#creating-a-custom-workstream): copy the [blank template](../../workstreams/TEMPLATE_WORKSTREAM.md), fill the sections that earn their place, and delete the optional ones it marks as deletable.

```sh
# in your installed project (adopter layout):
cp docs/methodology/workstreams/TEMPLATE_WORKSTREAM.md \
   docs/methodology/workstreams/RELEASE_WORKSTREAM.md
# fill: When to Use + Phase 2 (Research) + Phase 3 (Create); delete the optional sections you don't need
```

Filled in, the bones look like this — a thin lens, not a fork of the framework:

```markdown
# Release Workstream
## When to Use
- Cutting a tagged, versioned release of a tool or library
- Publishing a packaged artifact (wheel, binary, image) from a known-good commit
## Phase 2: Research (Release-Specific)
- Inventory what ships: changelog entries since the last tag, version string, artifacts
- Verify the build equivalent is green at the exact commit being tagged
## Phase 3: Create (Release-Specific)
- The deliverable is the release checklist: version bumped, CHANGELOG updated,
  tag created, packaged artifact smoke-tested from a clean checkout
```

**Expected result:** A real `RELEASE_WORKSTREAM.md` with at least *When to Use* + Phase 2 + Phase 3 filled, that a future session could pick up and run.
**Checkpoint:** The file exists and reads like the shipped workstreams — same shape, your domain — and it specializes Phase 2/3 only; it does **not** rewrite the phases or gates ([Adapting to Your Domain](../../ITERATIVE_METHODOLOGY.md#adapting-to-your-domain) lists the five things a workstream may change, and the gates aren't among them). It lives beside the shipped lenses in `docs/methodology/workstreams/`; because it isn't in the [distribution manifest](../../bin/_manifest.py), `bin/sync` will never overwrite it — it's yours.

### 5. Record the workstream — and notice you've found a campaign

The selection is only real if it persists. Note the active workstream in your handoff (the [Tutorial 3](T3_compounding_loop.md) discipline) so the next session inherits the choice instead of re-deciding. Then look at what the audit actually recommended: fix B1, fix B2, and run the [7-dimension audit](../../workstreams/AUDIT_WORKSTREAM.md) across the whole CLI. That is more than one session's work — which is precisely the signal [Phase 1's campaign check](../../starter-kit/SESSION_RUNNER.md#phase-1-receive-task) exists to catch.

**Expected result:** Your handoff names the active workstream and flags whether the remaining work is a single session or a [multi-session campaign](../../ITERATIVE_METHODOLOGY.md#multi-session-campaigns).
**Checkpoint:** A future session can read which workstream is active without re-deciding, and you've spotted that the audit's full recommendation is a campaign — exactly where the next tutorial picks up.

## Common mistakes

Cite the failure mode by number; link the list, don't paste it.
(Full list: [Known Failure Modes](../../starter-kit/SESSION_RUNNER.md#known-failure-modes).)

- **Carrying one workstream's reflexes into another.** You ran two Development sessions, switch to an Audit, and "just fix" B1 the moment you see it — the Development habit fires in the wrong lens. That's **FM #12 (workstream transfer amnesia)**, and the act of fixing mid-audit is also **FM #8 (redesign during implementation)** and **FM #2 (keep going)**. The countermeasure: when you switch workstreams, consciously re-read the new lens's Phase 2–3 and [re-apply the close-out checklist](../../starter-kit/SESSION_RUNNER.md#phase-3-close-out) — discipline doesn't auto-transfer.
- **Forcing a poor-fit task into the nearest lens.** Jamming the release into Development because it's familiar produces a session with the wrong Phase 2 and the wrong verification. The methodology's answer is to [adapt the template](../../HOW_TO_USE.md#creating-a-custom-workstream), not to mislabel the work.
- **Building a custom workstream that re-forks the framework.** A new workstream specializes Phase 2, Phase 3, scope validation, verification, and the reference tables — *only* those ([Adapting to Your Domain](../../ITERATIVE_METHODOLOGY.md#adapting-to-your-domain)). If your `*_WORKSTREAM.md` rewrites the phases, renumbers the gates, or invents its own close-out, it has stopped being a lens and become a fork that will drift from canonical.

## You produced

A recorded workstream selection — the Audit lens chosen by matching the task to its *When to Use*, with the rationale on disk — and a short audit report that *found* the CLI's rough edges instead of patching them. And a real custom `RELEASE_WORKSTREAM.md`, built from the template for work the catalog didn't cover, that specializes only Phase 2 and Phase 3 and leaves the gates untouched. You can now answer the Phase 1 question — *which workstream governs this work?* — for any task, and build the answer when it doesn't exist yet. The audit's full recommendation turned out to be bigger than one session, which is the thread the next tutorial pulls.

## Next

→ **[Tutorial 6: Multi-Session Campaigns](T6_campaigns.md)** — carry one deliverable, like the repo-wide hardening your audit just recommended, across many sessions without losing the thread. For now, do it for real: name the workstream your *own* last session was in, and the next time a task doesn't fit, draft the lens before you start instead of forcing the work into Development.
