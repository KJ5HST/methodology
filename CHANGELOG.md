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

### 2026-07-08 · [ad hoc] bin/status flags stale-format adopter seeds (BL-6 item 2)
- **Change:** `bin/status` now surfaces a SEED file whose *format* predates the current methodology —
  advisory-only — as `present (stale format)`, with a one-line migration note beneath the table, so an
  adopter upgrading from a pre-v3.1 methodology can **discover** that its seeded `CHANGELOG.md` still
  carries the old (pre-action-ledger) shape instead of the lag being silent. Mechanism: a new generic
  `_manifest.SEED_FORMAT_MARKERS` dict (dest → marker), with `CHANGELOG.md` keyed on the ledger
  **title** `"Authoritative Action Ledger"` — a lifetime-stable token that append-only entries never
  remove — deliberately **not** the `METHODOLOGY-SEED-SENTINEL` (which the adopter deletes on its first
  real entry, so keying on it would mis-flag an *in-use* current-format ledger). `SESSION_NOTES.md` /
  `ROADMAP.md` are intentionally omitted (rewritten wholesale each session → no stable marker; add an
  entry only when a seed gains a lifetime-stable one). Detection is **advisory only**: `bin/sync` still
  never auto-overwrites an adopter-owned seed, the status string is never reclassified as drift, and the
  exit code is unchanged. Docs updated in lockstep: `starter-kit/BOOTSTRAP.md`'s update-existing-project
  note and the `docs/tutorials/T8_keeping_current.md` SEED-state model now name the third state.
- **Commit/PR:** `346ac01` (feature + Test 20: `bin/_manifest.py` + `bin/status` + `bin/tests.sh`) ·
  this commit (docs: `starter-kit/BOOTSTRAP.md` note + `docs/tutorials/T8_keeping_current.md` third
  state) — branch `feat/status-stale-seed-advisory` (from `upstream/main`). The `[BL-6]`-item-2
  backlog closure + the item-3 hook-distribution decision land on fork `main` at merge (this
  upstream-based branch carries no `docs/planning/`). Design + fixes hardened by a 6-lens adversarial
  review + default-to-refuted verify (`wf_52a1df0d-068`): **5 findings confirmed → all fixed** (an
  in-use-ledger test-coverage gap that let a sentinel-keyed regression pass, a vacuous disposition
  assertion masked by the note line, a multi-project note undercount, and a `T8` doc-code mismatch).
- **Session:** BL-6 item 2 · **Verified:** `bin/tests.sh` **68/68** (new **Test 20**, 14 assertions;
  54 → 68); manual stale / current / absent cases; the marker survives an in-use ledger (root
  `CHANGELOG.md` carries the title, no sentinel); a sentinel-keyed regression now makes Test 20 **fail**
  — proving constraint #2 (no false positive on a current-format seed) is locked in by a test.

### 2026-07-08 · [ad hoc] Dashboard: fair scoring for document-only / research repos (DASHBOARD_VERSION 2.8.0)
- **Change:** `methodology_dashboard.py` (both byte-identical twins, `tools/` + `starter-kit/`) now
  detects a **document-only / research** repo and reshapes scoring so it is no longer falsely
  penalized for having nothing to unit-test. Detection is marker-override → source-loc cap (200) →
  corpus-disjunction: an explicit bidirectional **`.methodology-profile`** marker (`doc-only` |
  `code`) wins; otherwise a repo with negligible source but a real doc corpus **or** a render
  toolchain (the latter catches pure-LaTeX/Quarto repos whose `.tex`/`.qmd` aren't counted as docs)
  is doc-only. When doc-only, the 2nd health slot (dict key `testing`, stable for JSON/portfolio)
  is filled by a new **Render/Verification** score — an *honest static proxy* (the scanner cannot
  execute a render; it scores render/verification *configuration*: toolchain configs, the v2.5
  `pdffonts`/`fc-list`/`kpsewhich` render-dependency check, docs-render/link-check CI, and
  Research-Documentation verification artifacts). The code-centric **No test infrastructure** /
  thin-coverage risks are suppressed for doc-only repos and replaced with render/verification
  advisories; the **Large files** risk is fixed (unconditionally) to fire only on a *source* file,
  so a 2500-line `.md`/`.tex` chapter no longer trips it; the doc-to-source ratio display shows
  `n/a (doc-only)` / Doc LOC instead of a misleading `0.000`. Two BL-5 polish items ride along:
  `.gitignore` now covers `starter-kit/__pycache__/`, and **Signal F** (unmigrated `- [x]` BACKLOG
  done-marks) is gated on methodology adoption so it can't fire on a non-adopter sibling. Adds
  `tools/test_methodology_dashboard.py` — the **first functional scoring tests** (23 cases, stdlib
  `unittest`, canonical-only) — wired into `bin/tests.sh` (51 → 54 suite checks). Advisory tool,
  **no hard gate**. Resolves fork backlog **BL-5** (the `[BL-5]` BACKLOG removal lands on fork
  `main` at merge, since this upstream-based branch carries no `docs/planning/`). Designated
  framework **v3.2** (minor) — annotated tag + GitHub Release at the PR #50 merge commit;
  `DASHBOARD_VERSION` bumps **2.7.0 → 2.8.0**. → full narrative:
  [`CLAUDE.md` §Versioning "v3.2"](CLAUDE.md#versioning).
- **Commit/PR:** `b2efd76` (dashboard logic, both twins) · `536837f` (tests + `.gitignore` +
  `bin/tests.sh` wiring + ledger) · `bad258c` (review-hardening fixes) · this commit (v3.2 release
  narration — `CLAUDE.md` §Versioning + `README.md` What's New) — branch
  `feat/dashboard-doc-only-scoring` (from `upstream/main`) → [PR #50](https://github.com/KJ5HST/methodology/pull/50).
  Design pressure-tested by a judge panel + adversarial synthesis (`wf_7174281b-754`); the
  implementation was then hardened by a 4-dimension adversarial review + default-to-refuted verify (`wf_7c95bb29-131`).
- **Session:** BL-5 dashboard doc-only scoring · **Verified:** 29/29 dashboard unit tests + 54/54
  `bin/tests.sh`; twins byte-identical + both `DASHBOARD_VERSION` 2.8.0; real runs — this mixed
  repo stays code-scored (Testing kept; Large-files still trips on the 2465-line `.py`), a
  synthetic doc-only tree detects doc-only, fills the slot with Render/Verify, and drops the false
  no-test-infra + big-`.md` risks; no `starter-kit/__pycache__` generated. The review found **6
  real defects** — a BOM-prefixed `.methodology-profile` override silently dropped; the large-file
  check inspecting only `largest[0]` (a non-source #1 masking a real large source file below it);
  `fmt_ratio` mislabeling a zero-source *code* repo `(doc-only)`; the footnote printing a false
  `source_loc ≤ 200` on a marker-forced repo; a tautological cap test; an untested render-dependency
  advisory — **all fixed and regression-tested**.

### 2026-07-08 · [ad hoc] sample-project/.gitignore ignores demo.json (Tutorial 2/3 smoke-test store)
- **Change:** `docs/tutorials/sample-project/.gitignore` now ignores **`demo.json`** — the `--file demo.json`
  store that the Tutorial 2 (and Tutorial 3) Phase 3E runtime smoke test writes. The ignore list previously
  covered only `todos.json`/`__pycache__/`/`.pytest_cache/`, and T2's 3F stages four named files, so a
  learner replaying T2 was left with `demo.json` **untracked** after close-out — undercutting the clean-tree
  discipline the tutorial teaches. `demo.json` is the only non-ignored artifact the tutorials generate
  (verified: sole `--file` store; the default `todos.json` is already ignored). Resolves fork backlog BL-6
  follow-up 1c. Canonical-only tutorial asset — **no version event**.
- **Commit/PR:** this commit — branch `docs/sample-gitignore-demo-json` → upstream PR.
- **Session:** BL-6 follow-up 1c · **Verified:** 51/51 `bin/tests.sh`; grep-confirmed `demo.json` is the complete untracked-artifact set (T2/T3 `--file` sweep); co-staged through `.githooks/pre-commit`.

### 2026-07-08 · [ad hoc] HOW_TO_USE close-out gains Phase 3E smoke test (re-lettered 3E→3F, 3F→3G); T1 commits the seeded ledger
- **Change:** two v3.1 close-out fidelity fixes to the teaching docs (fork backlog BL-6 follow-ups 1a + 1b).
  **1a** — `HOW_TO_USE.md` §Phase 3 Close Out gained the missing **3E: Runtime smoke test** step and
  re-lettered the trailing two to match canonical `SESSION_RUNNER.md` (Commit **3E→3F**, Report and STOP
  **3F→3G**); the FM #27 ledger recording stays in the re-lettered **3F Commit**, and the failure-mode
  table now cites the close-out letters (FM #24 → Phase 3E, FM #27 → Phase 3F). **1b** —
  `docs/tutorials/T1_setup.md` Step 6 now explicitly commits the setup (`git add -A && git commit`) so the
  Step-1-seeded `CHANGELOG.md`/`ROADMAP.md` are tracked before the first session; Step 5 now gitignores the
  generated `dashboard.html` (so `git add -A` stays clean and Tutorial 2's clean-tree premise holds), and
  `T2_worked_transcript.md`'s seed citation is reconciled to **[T1 Step 1]**. Docs-lag correction — **no version event**.
- **Commit/PR:** this commit — branch `docs/closeout-3e-smoke-and-t1-commit` → upstream PR.
- **Session:** BL-6 follow-ups 1a/1b · **Verified:** 6-lens adversarial review → 6 findings fixed (2 majors: the T1↔T2 `git commit -am` contradiction and `git add -A` sweeping in `dashboard.html`); 2 focused re-verifies returned CONSISTENT + CLEAN; 51/51 `bin/tests.sh`; co-staged through `.githooks/pre-commit`.

### 2026-07-08 · [ad hoc] HOW_TO_USE + T2 tutorials: sync close-out docs to the v3.1 FM #27 ledger
- **Change:** `HOW_TO_USE.md` (a distributed file) and the `docs/tutorials/T2_*` pair predated failure
  mode #27 and still taught a pre-ledger close-out. Now current: `HOW_TO_USE.md` FM count **23 → 27**
  (two sites) with compressed rows **24–27** added, and the `CHANGELOG.md` action-ledger recording folded
  into the 3E close-out step (cited as Failure Mode #27); `T2_first_session.md` + `T2_worked_transcript.md`
  show the Phase 3F ledger entry, the paired `BACKLOG.md` removal for a `[BL-N]` item, and explicit
  `git add` staging (so a freshly-seeded, still-untracked ledger is not silently dropped by `git commit -am`).
  Resolves the pedagogical-refresh half of fork backlog BL-6. Deliberately out of scope, tracked as a
  BL-6 follow-up: `HOW_TO_USE.md`'s close-out enumeration still lacks the Phase 3E runtime smoke-test step
  and its 3E/3F lettering lags canonical.
- **Commit/PR:** this commit — branch `docs/how-to-use-fm27-ledger` → upstream PR (docs-lag correction, no version event).
- **Session:** BL-6 item 1 · **Verified:** 6-lens adversarial review (4 fidelity findings fixed); 51/51 `bin/tests.sh`; co-staged through `.githooks/pre-commit`.

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
