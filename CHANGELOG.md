# Changelog — Authoritative Action Ledger

The cumulative, append-only record of **actions taken in this repository** — across backlog
items, repository issues, and ad-hoc work. It is the authoritative answer to *"what was done
here, ever?"*, distinct from the release narrative in [`CLAUDE.md` §Versioning](CLAUDE.md#versioning).

This repository dogfoods its own methodology: every session records its actions here at
close-out (`starter-kit/SESSION_RUNNER.md` Phase 3F), and Phase 0 reconciles the ledger against
`git log` and backfills anything a crashed or out-of-band session missed. Taking an action — any
commit, or any non-commit action (release, tag, PR, upstream issue close, access grant, grooming
decision) — and not recording it is failure mode #27. The full close-out and reconcile rules, plus
the reusable seed, live in [`starter-kit/CHANGELOG.md`](starter-kit/CHANGELOG.md).

**Source tag — exactly one per entry**, so `grep -E '\[(issue #|BL-|ad hoc)' CHANGELOG.md`
enumerates every logged action and proves all three sources landed:

- `[issue #<N>]` — a repository issue. Issues for this repo live in the **upstream** parent
  `KJ5HST/methodology` (this fork has Issues disabled), so entries cite an **absolute URL**, never
  a bare `#<N>`.
- `[BL-<N>]` — a `docs/planning/BACKLOG.md` item, removed from the backlog in the same commit.
- `[ad hoc]` — work with no backlog or issue origin: releases, tag/branch ops, PR opens, upstream
  issue closes, access grants, and decline/wontfix/grooming decisions.

**Boundary vs. `CLAUDE.md` §Versioning — so the two ledgers cannot diverge.** §Versioning owns
*released-version semantics* (one narrated entry per shipped version); `README.md` §What's New is
its public restatement. This ledger is the *per-action operational timeline*, including
non-release work (housekeeping, doc-only PRs, adopter coordination, backlog grooming) that
otherwise has no home but raw `git log`. Where the two overlap — a release — this ledger carries a
**one-line pointer** into §Versioning, never a re-narration (cite, don't restate).

Reverse-chronological, newest on top; prepend-only. Promote to `## YYYY-MM` sections as it grows.

---

### 2026-07-07 · [ad hoc] BOOTSTRAP: add earlier-version→v3.1 adopter migration note (seed CHANGELOG not auto-updated)
- **Change:** a local v3.0→v3.1 adopter-migration trial (real `bin/sync` against a pristine v3.0 tree)
  confirmed the update path is sound — **8 tracked files upgrade with no `--force`**, drift guard intact —
  but surfaced that the recomposed action-ledger seed (`CHANGELOG.md`, `SESSION_NOTES.md`) does **not**
  reach existing adopters (seed = write-if-absent, never clobbered). `starter-kit/BOOTSTRAP.md` gains an
  "Updating an existing project from an earlier methodology version" note: prefer `--source=local` from a
  full checkout, and manually reconcile (or delete-and-reseed) an older `CHANGELOG.md` to pick up the
  action-ledger format. Remaining loose ends (HOW_TO_USE / tutorial refresh, optional adopter re-seed
  tooling, hook-distribution decision) tracked in fork backlog BL-6.
- **Commit/PR:** this commit — branch `feat/changelog-authoritative-ledger` (held; pre-`v3.1`).
- **Session:** adopter-migration trial · **Verified:** live migration (dry-run + real sync + byte-compare) + 51/51 `bin/tests.sh`; this commit co-staged the ledger through the shipped `.githooks/pre-commit` gate.

### 2026-07-07 · [ad hoc] v3.1 release narration — §Versioning + What's New; tag + Release at PR #46 merge
- **Change:** the CHANGELOG-ledger campaign (S2–S7) is designated **v3.1** — a minor bump (first new
  failure mode since v2.7). `CLAUDE.md` §Versioning gains the narrated v3.1 entry, `README.md` §What's
  New its public restatement; the annotated tag `v3.1` + GitHub Release are cut at the PR #46 merge commit.
- **Commit/PR:** this commit (release narration) · [PR #46](https://github.com/KJ5HST/methodology/pull/46). → full narrative: [`CLAUDE.md` §Versioning "v3.1"](CLAUDE.md#versioning).
- **Session:** S7 · **Verified:** 51/51 `bin/tests.sh`.

### 2026-07-07 · [ad hoc] Authoritative CHANGELOG ledger campaign — gate + reconcile + dashboard + hook (S2–S7 complete)
- **Change:** `CHANGELOG.md` is now a dependable cross-source action ledger, closed on two
  mechanisms rather than one: a write-time gate (FM #27, Phase 3F), a reconcile-on-read backstop
  (Phase 0), a recomposed seed template, a dashboard freshness monitor, this dogfooded root ledger,
  a `.githooks/pre-commit` co-staging gate (decision D1 — the mechanical enforcement where a repo
  has no root runner), and the ledger close-out step propagated into every session-type and campaign
  checklist (escape #8). The whole campaign S2–S7 is complete.
- **Commit/PR:** `2227aab` (S2, FM #27) · `4828929` (S3, Phase 0 reconcile) · `f25e0c4` (S4, seed) ·
  `89b8f60` (S5, dashboard) · `339dfb2` (S6, root ledger) · `d2184cc` (S7, checklists) · this commit
  (S7, hook + docs) — branch `feat/changelog-authoritative-ledger`.
  Ratified plan: [`docs/planning/changelog-authoritative-ledger-gate-plan.md`](https://github.com/rmsharp/methodology/blob/main/docs/planning/changelog-authoritative-ledger-gate-plan.md) (`1710e90`, fork `main` only).
- **Session:** S7 · **Verified:** 9/9 hook behavior tests (block / pass / absent-ledger / mid-merge / `--no-verify`) + 51/51 `bin/tests.sh`.

<!-- Entries below were backfilled at ledger creation (S6), covering everything v3.0-forward per decision D5.
     They were reconstructed from git history at ledger birth, not logged live at the time of the action. -->

### 2026-07-07 · [ad hoc] Operational backlog reopened with BL-5 after full retirement
- **Change:** `docs/planning/BACKLOG.md` was retired 2026-07-06 once BL-1/2/3/4 all closed, then
  reopened 2026-07-07 with BL-5 (make `methodology_dashboard.py` adapt scoring to document-only repos).
- **Commit/PR:** `ff5cee9` (retire) · `72dc914` (reopen with BL-5). *(fork `main`)*
- **Session:** S6 (backfill) · **Verified:** n/a — docs-only (planning).

### 2026-07-06 · [BL-4] Backlog item BL-4 closed — methodology housekeeping
- **Change:** planning docs archived and stale branches pruned; BL-4 removed from `docs/planning/BACKLOG.md`.
- **Commit/PR:** `69dad12`. *(fork `main`)*
- **Session:** S6 (backfill) · **Verified:** n/a — docs-only (planning).

### 2026-07-06 · [ad hoc] PR #45 merged — v3.0.1 added to the §Versioning ledger
- **Change:** `CLAUDE.md` §Versioning gained its v3.0.1 entry (the release itself had already shipped at the PR #44 merge).
- **Commit/PR:** PR #45 (content `3fee545`, merged `4df8ee6`).
- **Session:** S6 (backfill) · **Verified:** n/a — docs-only.

### 2026-07-06 · [ad hoc] Released v3.0.1 — REUSE-compliance metadata + README badges
- **Change:** the repo's already-MIT licensing was made machine-readable (REUSE Spec 3.3); a patch
  release was cut on top of v3.0 (not a re-point — v3.0 left untouched).
- **Commit/PR:** annotated tag `v3.0.1` at `aa822f6` (the PR #44 merge). → full narrative: [`CLAUDE.md` §Versioning "v3.0.1"](CLAUDE.md#versioning).
- **Session:** S6 (backfill) · **Verified:** `reuse lint` 53/53; live REUSE badge scanned compliant.

### 2026-07-06 · [ad hoc] PR #44 merged — REUSE.toml + LICENSES/MIT.txt + README badges
- **Change:** added `REUSE.toml` (single bulk `path = "**"` MIT annotation), `LICENSES/MIT.txt`, and
  two README badges (static `License: MIT` + live REUSE-compliance); no existing framework file gained an inline SPDX header.
- **Commit/PR:** PR #44 (content `7b5238a`, merged `aa822f6`).
- **Session:** S6 (backfill) · **Verified:** `reuse lint` 53/53 files, 0 problems.

### 2026-06-25 · [issue #43] Released v3.0 — relicensed under the MIT License
- **Change:** the bespoke source-available `LICENSE` was replaced with verbatim standard MIT text;
  use/copy/modify/distribute/**sell** with attribution retained is now permitted (the prior no-resale restriction dropped).
- **Commit/PR:** relicense `49a103a`, release `5525f30`, annotated tag `v3.0`. Issue: <https://github.com/KJ5HST/methodology/issues/43>. → full narrative: [`CLAUDE.md` §Versioning "v3.0"](CLAUDE.md#versioning).
- **Session:** S6 (backfill) · **Verified:** n/a — relicense + lockstep README/CLAUDE.md updates.

---

**Release history before v3.0 (v1.0 – v2.9):** not re-narrated here — see [`CLAUDE.md` §Versioning](CLAUDE.md#versioning)
for the per-version narrative and `README.md` §What's New for the public restatement. This ledger is
prepend-only from v3.0 forward (decision D5: an authoritative ledger needs no hole at its recent edge,
and duplicating §Versioning would violate cite-don't-restate).
