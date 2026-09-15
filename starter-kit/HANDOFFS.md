# Handoff Receipts — durable close-out proof

The cumulative, append-only record of **each session's close-out handoff**, distilled into a
machine-checkable block. It is the durable answer to *"was close-out actually performed, and what
did the session hand its successor?"* — the part of close-out that otherwise lives only in the
transient `SESSION_NOTES.md` (overwritten every session) or the spoken report (which leaves no file
at all).

One `handoff` block per **session** (not per commit), newest on top. The canonical-only
`bin/check-handoff` (copy it into your `bin/` if you want the structural check) asserts each block is
present and structurally complete; the next session's Phase 0 reconcile greps this file for a missing
or still-`pending` receipt and backfills it — that reconcile, not the checker, is the dependable
backstop, so the discipline needs no tooling. Together — a write-step at close-out **and** a
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

**Naming the acting model (optional).** No new key — `REQUIRED_KEYS` is unchanged, and the fenced
block below stays exactly as documented. When a one-line summary is useful, especially for a
single-tier session where it saves a reader a cross-reference into `CHANGELOG.md`'s per-action
**Model:** bullet (see that file's format section), name the model in this receipt's free-text
prose area — the Format section below documents that area as *"the durable proxy for the Phase 3G
spoken report."* This formalizes what a capability-tiered session already does organically when it
states which tier built which layer and which tier reviewed it; this fork's own first receipt
(root `HANDOFFS.md`, session S1) is the worked precedent. `CHANGELOG.md`'s **Model:** bullet
remains the structured, per-action record; this is a convenience pointer for the session-level
view, not a second schema — and it is fine for both to name the same model on a single-tier
session, since they answer different questions ("what happened, action by action" vs. "which model
ran this session"). A canonical-only `bin/model-report` (copy it into your `bin/` if you want it,
same as `bin/check-handoff`) reads this free-text convention back alongside `CHANGELOG.md`'s
**Model:** bullets and git's `Co-Authored-By` trailers, keeping all three visually separate.

## Format — a fenced `handoff` block

````
```handoff
session: S<N>
date: YYYY-MM-DD
status: <pending | complete>
self_score: <1-10>
predecessor_score: <1-10>
active_task: <current state>
what_was_done: <what you did, including a commit sha — or the literal `pending`>
next_steps: <specific and actionable; never "pick next from backlog">
key_files: <each entry carries a path:line token, e.g. SessionManager.java:245>
gotchas: <traps the next session should watch for>
runtime_smoke: <a run result, or "n/a — docs-only", or "impossible: <reason>">
changelog_ref: <PR #N, a short-sha, or CHANGELOG.md "<its ### heading>" — never a bare line number, which decays once the ledger is trimmed>
commit: <short-sha — or the literal `pending`>
```
<free-text prose: the durable proxy for the Phase 3G spoken report, plus the +/- self-score breakdown>

Write clean `key: value` lines — no inline `#` comments (a `#` is a literal value character,
as in `changelog_ref: PR #52`). The keys are the six Phase 3D Minimum Handoff Requirements (the sixth
*is* `self_score`) plus `predecessor_score` (the Phase 3A evaluation) and a little metadata. `status`
is `pending` at the Phase 1B claim and `complete` at
close-out; a third value, `reconciled`, is written *only* by a later session's Phase 0 reconcile
when it reconstructs a receipt a crashed session never completed — you never write it yourself.
````

`self_score` and `predecessor_score` are distinct keys so one can never stand in for the other; omit
`predecessor_score` on Session 1 (there is no predecessor to score). `commit: pending` and
`what_was_done: pending` are legal at write time (the receipt ships in the very commit whose sha it
would name); no future session is assigned to fill either in later, so `pending` is a legitimate
resting value for both, not a promise a later session owes.

**A receipt's identity is `session` + `date`, not `session` alone.** `S<N>` is a per-sequence
counter, and one ledger may legitimately merge more than one sequence — a fork and its upstream each
running their own, so two distinct sessions share an `S<N>` by construction. Keep `S<N>` unique
within a sequence if you can (never renumber an already-written receipt to do it — a visible gap
that closes on merge is the lesser defect), but do not treat a repeated id across sequences as
corruption. `bin/check-handoff --all` keys on the pair for this reason.

## Size, and when to archive

This file gains a receipt every session and Phase 0 reads it every session, so it carries the same
size discipline as `CHANGELOG.md`: **two caps, two distinct failure modes, fire if either fires,
stop only when both stop conditions hold.**

| Cap | Protects against | Form | Fire when | Cut until |
|---|---|---|---|---|
| **Lines** — ~2,000, a **proxy** for the agent `Read` cap (the cap itself is denominated in **tokens**, not lines) | **measures an unread tail** — it does not, on its own, establish a remedy. A read past the cap returns only the prefix that fits, and says so: a `PARTIAL view` banner names the delivered span and the true length, and an explicit over-cap line range errors outright. **Announced, not silent.** **Whether archiving the tail REMEDIES this is an open question, not a settled benefit.** Truncation is ordered top-down and this file is newest-on-top, so the records a cut removes are ones a whole-file read was not delivering anyway: the delivered prefix is the same before and after, and what changes is that the reader stops being warned. Raised as BL-52. **Re-measure rather than trusting this row** — the reproduction is `docs/planning/read-cap-premise-correction-plan.md` Appendix A in the framework repo | a **rate** | headroom < **15** receipts | headroom > **30** |
| **Bytes** — a per-file budget, default **65,536 B** (64 KB) | **context tax**: every session pays for the whole file, every time | a **level with hysteresis** | `size > budget` | `size ≤ ½ × budget` |

**Run this rather than estimating it:**

```sh
python3 methodology_trim.py --file HANDOFFS.md --check
```

`--check` evaluates both conditions and never writes. `--write` performs the trim, refuses unless it
can prove the split lossless, and **neither commits nor stages** — it leaves this file modified and
the new shard *untracked*, and leaves the commit to you (`git add HANDOFFS.md docs/archive/`).

An archive is a **shard**: a new frozen file, same format, same newest-on-top order.

- **Path: `docs/archive/HANDOFFS-through-<CUT-KEY>.md`.** Both halves are load-bearing — the
  directory keeps the shard from shadowing this file, and the `HANDOFFS-` prefix is what the
  trigger's own glob looks for. A shard named otherwise is silently invisible to it.
- **This file keeps one short pointer** naming each shard, the span it covers and how many receipts
  it holds — with the command that recomputes those counts, never a hand-maintained number.
- **The shard back-links here and states only facts about itself.** It must not restate a
  forward-looking rule: a shard is frozen, so a rule copied into one cannot be corrected when the
  live rule moves.
- **After a split, anything that enumerates receipts must span both** — `HANDOFFS.md
  docs/archive/HANDOFFS-*.md` — or it silently counts a shrunken population.

If a `CHANGELOG.md` sits beside this file, its own **Size, and when to archive** section carries the
reasoning both files share: why the line cap must be a rate, why the byte cap cannot be one, and how
to choose the budget. Everything needed to *act* is here.

What is specific to *this* file, and gets receipts wrong if assumed:

- **A record is a `handoff` block *plus the prose beneath it*, not the fence alone.** The self-score
  and predecessor-score paragraphs sit outside the fence and belong to the receipt above them. A
  fence-only cut severs every receipt from its own scoring.
- **Archive oldest-first by position, never by sorting on `session:`.** Two independent `S<N>`
  sequences can share one ledger — a fork and its upstream each running their own counter — and
  their numbers collide. The record's identity is **session + date**.
- **A trim leaves the newest-receipt check alone and moves what the older-receipt checks see.**
  Phase 0 reconcile is frontier-based and a structural checker applies the full schema to the newest
  receipt only, so neither is disturbed. Its other passes are not so confined — an answer-slot rule
  reads every receipt below the newest, and a locator-form rule reads every receipt in the file. So
  after a trim, **run the checker against each shard as well**, and recompute any "all N older
  receipts" count from the files rather than carrying it forward.
- **Never trim to zero receipts.** An empty receipt ledger is indistinguishable from a broken one.
- **A shard freezes, with one exception this file needs:** a `commit:` answer slot may still be
  reconciled inside an archived receipt, because that field was always going to be filled by a later
  session. Nothing else in a shard is rewritten.

## Three files, three questions, one shared key

- **`SESSION_NOTES.md`** — the *transient scratchpad*: rich working notes, overwritten every session.
- **`HANDOFFS.md`** (this file) — the *durable receipt*: the distilled, machine-checkable proof that
  the handoff was written. Nothing is ever deleted; once the file outgrows a session's read, the
  oldest receipts move to a frozen shard (see **Size, and when to archive** above).
- **`CHANGELOG.md`** — the *cumulative action ledger*: *"what was done here, ever?"*, append-only.

The shared key across all three is the commit sha (`changelog_ref` / `commit` here). This file
**distills** the handoff; it does not copy the scratchpad. The belongs-here test: *would the next
session need this block to continue the work without re-reading the whole repo?*

---

<!-- Receipts go below, newest on top. Delete the seed-sentinel line above when you add the first one. -->
