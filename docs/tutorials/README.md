# Tutorials

A hands-on, progressive learning track for the Iterative Session Methodology. The other
docs *define* the framework — this one makes you *do* it, one thing at a time, against a real
project, with a checkpoint after each step.

> **Status:** The **core trio is published** — [T1: Setup & First Bootstrap](T1_setup.md),
> [T2: Your First Session, End-to-End](T2_first_session.md) (with a
> [worked transcript](T2_worked_transcript.md) of a real session against the sample project), and
> [T5: Cautionary Use](T5_cautionary.md). The [tutorial template](TUTORIAL_TEMPLATE.md) and
> [sample project](sample-project/) are in place. The curriculum below shows what's done and what's coming.

## Why bother?

You can read the [9 principles, 6 phases, and 12 gates](../../ITERATIVE_METHODOLOGY.md) and still
not know how to *run* a session. These tutorials close that gap: you install the framework, run
one real session end to end, and see where the guardrails catch you. The payoff — fewer wrecked
sessions, and session N+1 reliably better than session N — is documented, not promised:

- [The Problem](../../README.md#the-problem) and [Evidence](../../README.md#evidence) — why the methodology exists and what it changed.
- [When to Use This Methodology](../../ITERATIVE_METHODOLOGY.md#when-to-use-this-methodology) — and when not to.
- [The Self-Improvement Loop](../../ITERATIVE_METHODOLOGY.md#the-self-improvement-loop) — the compounding payoff these tutorials let you feel firsthand.

## How the series works

- **One objective per tutorial** — mirrors the methodology's "1 deliverable per session." Each
  tutorial does exactly one thing.
- **Progressive** — T1 → T2 → T5 build on each other; every tutorial names its predecessor.
- **You produce a real artifact** — an installed framework, a saved session doc, a feature you
  shipped, a near-miss you caught. Not read-along.
- **Cite, don't restate** — tutorials link into [`BOOTSTRAP.md`](../../starter-kit/BOOTSTRAP.md),
  [`SESSION_RUNNER.md`](../../starter-kit/SESSION_RUNNER.md), and
  [`ITERATIVE_METHODOLOGY.md`](../../ITERATIVE_METHODOLOGY.md) at the right beat. One source of
  truth; the tutorials never fork the principles, phases, or failure-mode list.
- **Dogfooded** — each tutorial is itself authored as a methodology session.

## Two ways to practice — pick one per pass

Choose a single track for a given run (do one, then the other if you like — not both at once):

- **Track A — your own repo.** Apply each step to a project you actually care about. The sample
  run is your reference for "what a good run looks like."
- **Track B — the bundled sample.** Use the [sample project](sample-project/) (a tiny todo CLI
  with a real test suite and a [backlog](sample-project/BACKLOG.md)) and follow the steps
  step-for-step in a throwaway sandbox.

One running example threads the core trio: T1 installs the framework onto the sample project, T2
runs the first session (building one todo-CLI feature), and T5 uses that same session's
near-misses as its cautionary cases.

## Curriculum

The **core trio (T1 · T2 · T5)** is the first cut; the rest is a roadmap.

| # | Tutorial | You'll be able to… | In first cut? |
|---|----------|--------------------|:-------------:|
| [T1](T1_setup.md) | Setup & First Bootstrap | Install the framework into a project: root files, `CLAUDE.md` protocol block, task tracking, dashboard | ✅ **published** |
| [T2](T2_first_session.md) | Your First Session, End-to-End | Run one full 6-phase pass to one deliverable — with Phase 0 Orient and the Present gate front and center | ✅ **published** |
| [T5](T5_cautionary.md) | Cautionary Use | Read the gates, the 26 failure modes, "1 and done", the vertical-slice gates, and the Plan-Mode exit trap — and know when the methodology is too heavy | ✅ **published** |
| T3 | The Compounding Loop | Run the handoff + scoring loop and watch session N+1 improve | roadmap |
| T4 | Choosing & Adapting a Workstream | Pick the right workstream; spin up a custom one | roadmap |
| T6 | Multi-Session Campaigns | Carry one deliverable across many sessions | roadmap |
| T7 | Portfolio & Dashboard Ops | Run across many projects; read the health dashboard | roadmap |
| T8 | Keeping Adopters Current | Use `bin/sync` / `bin/status` to stay in step with the canonical repo | roadmap |

## Writing a tutorial

Start from [`TUTORIAL_TEMPLATE.md`](TUTORIAL_TEMPLATE.md) — it encodes the shared anatomy
(front-matter, "You do X → Expected result" steps with checkpoints, FM-by-number callouts, the
"Why this matters" hook, and the successor pointer).
