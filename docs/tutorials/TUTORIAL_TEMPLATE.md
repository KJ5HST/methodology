<!--
TUTORIAL TEMPLATE — copy this file to docs/tutorials/T<N>_<slug>.md and fill it in.

This is the one shared shape for every tutorial in the series (parallel to
workstreams/TEMPLATE_WORKSTREAM.md). It encodes the series' rules so individual
tutorials stay consistent:

  • Cite, don't restate. Link into BOOTSTRAP / SESSION_RUNNER / ITERATIVE_METHODOLOGY
    at the right beat. One source of truth — never copy the 9 principles, 6 phases,
    or the 26 failure modes into a tutorial; they drift the moment you do.
  • One objective per tutorial (mirrors "1 deliverable per session").
  • The learner *produces* something — every tutorial ends with a real artifact.
  • State the predecessor; point to the successor.

Delete this comment block and replace every [bracketed] placeholder before publishing.
Relative-link note: tutorials live at docs/tutorials/, so repo-root docs are two levels
up — e.g. ../../ITERATIVE_METHODOLOGY.md, ../../starter-kit/SESSION_RUNNER.md.
-->

# Tutorial [N]: [Title]

> **Objective:** [The single thing the learner will be able to do by the end. One sentence.]
> **Prerequisites:** [Tutorial N-1] ([link]); [any tools/accounts]. New here? Start at the [series index](README.md).
> **Time:** [~N minutes]
> **What you'll produce:** [The concrete artifact the learner walks away with — an installed framework, a saved session doc, a merged feature, a caught near-miss.]
> **Track:** Pick one and stick with it for this pass —
> **A** (your own repo): apply each step to a project you care about; the sample run is your reference.
> **B** ([sample project](sample-project/)): clone/use the bundled todo CLI and follow along step-for-step.

## Why this matters

[2–3 sentences of payoff, then LINK the canonical case — do not restate it. Pull from:
[The Problem](../../README.md#the-problem) · [Evidence](../../README.md#evidence) ·
[When to Use This Methodology](../../ITERATIVE_METHODOLOGY.md#when-to-use-this-methodology) ·
[The Self-Improvement Loop](../../ITERATIVE_METHODOLOGY.md#the-self-improvement-loop).]

## Before you start

[Anything that must be true first: prior tutorial completed, tools installed, repo cloned.
Give the one command or check that confirms readiness.]

**Checkpoint:** [What the learner should see that proves they're ready to begin.]

## Steps

Each step is one action and its expected result. Don't skip ahead — later steps assume the
checkpoints passed.

### 1. [You do X]

[Exact instruction — the command to run or the edit to make.]

**Expected result:** [What happens.]
**Checkpoint:** [What the learner should now see / have. Be concrete enough to self-verify.]

### 2. [You do Y]

[…]

**Expected result:** […]
**Checkpoint:** […]

<!-- Add as many numbered steps as the one objective needs. Keep each to a single action. -->

## Common mistakes

Cite the failure mode by number; link the list, don't paste it.
(Full list: [Known Failure Modes](../../starter-kit/SESSION_RUNNER.md#known-failure-modes).)

- **[Mistake the learner is likely to make here]** — [one line]. This is **FM #[n]**; the
  countermeasure is [the gate/step that prevents it].
- **[Another]** — [one line]. See **FM #[n]**.

## You produced

[Restate the artifact from the front-matter, now in the past tense, so the learner sees they
made something real. If it's part of the running example threaded through the series, say how
the next tutorial builds on it.]

## Next

→ **[Tutorial N+1: Title](T[N+1]_[slug].md)** — [one line on what it adds].
