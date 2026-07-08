# Handoff Receipts — durable close-out proof

The cumulative, append-only record of **each session's close-out handoff**, distilled into a
machine-checkable block. It is the durable answer to *"was close-out actually performed, and what
did the session hand its successor?"* — the part of close-out that otherwise lives only in the
transient `SESSION_NOTES.md` (overwritten every session) or the spoken report (which leaves no file
at all).

One `handoff` block per **session** (not per commit), newest on top. `bin/check-handoff` asserts each
block is present and structurally complete; the next session's Phase 0 reconcile greps this file for a
missing or still-`pending` receipt and backfills it. Together — a write-step at close-out **and** a
reconcile-on-read backstop — this makes a skipped handoff *detectable* rather than silent.

> **A green `bin/check-handoff` is not a good handoff.** The check verifies presence and structure,
> never semantic quality. Faithfulness is still scored 1–10 by the next session (Phase 3A). A
> well-formed but hollow receipt passes the check and is caught only by that human judgement.

<!-- METHODOLOGY-SEED-SENTINEL: fresh receipt ledger, no receipts yet. While this line is present AND
     there are no `session:` blocks below, this is a freshly-seeded file, not a stale or abandoned one.
     Delete this line when you add your first real receipt. -->

## How to write a receipt

**At Phase 1B (claim the session)** — write the stub block below with `status: pending`, filling what
you can, and commit it with your session-claim commit. This committed `pending` block is the crash
breadcrumb: if the session ends before close-out, the next session's Phase 0 reconcile sees it.

**At Phase 3D (close-out)** — overwrite that block in place to `status: complete` and fill every
field. The block must satisfy all six Minimum Handoff Requirements (`SESSION_RUNNER.md` §3D).

## Format — a fenced `handoff` block

````
```handoff
session: S<N>
date: YYYY-MM-DD
status: pending            # "pending" at Phase 1B; "complete" at Phase 3D close-out
self_score: <1-10>         # Phase 3D field 6 — this session's own score, with the +/- breakdown in the prose below
predecessor_score: <1-10>  # Phase 3A evaluation of the PREVIOUS session's handoff — omit only on Session 1
active_task: <current state — Phase 3D field 1>
what_was_done: <field 2 — include a commit sha, or the literal `pending`>
next_steps: <field 3 — specific and actionable; never "pick next from backlog">
key_files: <field 4 — each entry carries a path:line token, e.g. SessionManager.java:245>
gotchas: <field 5 — traps the next session should watch for>
runtime_smoke: <Phase 3E — a run result, or "n/a — docs-only", or "impossible: <reason>">
changelog_ref: <pointer into CHANGELOG.md — PR #N or short-sha>
commit: pending            # reconciled to a short-sha by the next session
```
<free-text prose: the durable proxy for the Phase 3G spoken report, plus the +/- self-score breakdown>
````

`self_score` and `predecessor_score` are distinct keys so one can never stand in for the other.
`commit: pending` and `what_was_done: pending` are legal at write time (the receipt ships in the very
commit whose sha it would name); the next session reconciles them to real shas.

## Three files, three questions, one shared key

- **`SESSION_NOTES.md`** — the *transient scratchpad*: rich working notes, overwritten every session.
- **`HANDOFFS.md`** (this file) — the *durable receipt*: the distilled, machine-checkable proof that
  the handoff was written, kept forever.
- **`CHANGELOG.md`** — the *cumulative action ledger*: *"what was done here, ever?"*, append-only.

The shared key across all three is the commit sha (`changelog_ref` / `commit` here). This file
**distills** the handoff; it does not copy the scratchpad. The belongs-here test: *would the next
session need this block to continue the work without re-reading the whole repo?*

---

<!-- Receipts go below, newest on top. Delete the seed-sentinel line above when you add the first one. -->
