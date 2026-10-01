# Changelog — Authoritative Action Ledger

The cumulative, append-only record of **actions taken in this repository** — across backlog
items, repository issues, and ad-hoc work. It is the authoritative answer to *"what was done
here, ever?"*, distinct from the release narrative in [`CLAUDE.md` §Versioning](CLAUDE.md#versioning).

This repository dogfoods its own methodology: every session records its actions here at
close-out (`starter-kit/SESSION_RUNNER.md` Phase 3F), and Phase 0 reconciles the ledger against
`git log` and backfills anything a crashed or out-of-band session missed. Taking an action — any
commit, or any non-commit action (release, tag, PR, upstream issue close, access grant, grooming
decision) — and not recording it is failure mode #27. The rules for this file live in
[`FRAMEWORK_APPARATUS.md` §The Action Ledger](FRAMEWORK_APPARATUS.md#the-action-ledger); the reusable
seed, [`starter-kit/CHANGELOG.md`](starter-kit/CHANGELOG.md), points there.

**Source tag — exactly one per entry**, so the audit in §The Action Ledger — anchored to the entry
heading, and reading any archived shards — enumerates every logged action and proves all three
sources landed:

- `[issue #<N>]` — a repository issue. Issues live in `KJ5HST/methodology`; the fork
  `rmsharp/methodology` has Issues disabled, so entries — authored from either side — cite an
  **absolute URL**, never a bare `#<N>`, and resolve identically from both.
- `[BL-<id>]` — a backlog item, removed from the backlog in the same commit. That backlog is
  [`docs/planning/BACKLOG.md`](https://github.com/rmsharp/methodology/blob/main/docs/planning/BACKLOG.md)
  on fork `main` only — **this repo has no `docs/planning/BACKLOG.md`** — so a `[BL-<id>]` entry here
  records work whose origin lives in the fork.
- `[ad hoc]` — work with no backlog or issue origin: releases, tag/branch ops, PR opens, upstream
  issue closes, access grants, and decline/wontfix/grooming decisions.

**Boundary vs. `CLAUDE.md` §Versioning — so the two ledgers cannot diverge.** §Versioning owns
*released-version semantics* (one narrated entry per shipped version); `README.md` §What's New is
its public restatement. This ledger is the *per-action operational timeline*, including
non-release work (housekeeping, doc-only PRs, adopter coordination, backlog grooming) that
otherwise has no home but raw `git log`. Where the two overlap — a release — this ledger carries a
**one-line pointer** into §Versioning, never a re-narration (cite, don't restate).

Reverse-chronological, newest on top; prepend-only. Month headings (`## YYYY-MM`) start at this
ledger's next new month, and nothing below is retrofitted (§The Action Ledger, *Placement*).

**Archived 96 record(s), 2026-06-25 → 2026-09-26** into [`docs/archive/CHANGELOG-through-2026-09-30.md`](docs/archive/CHANGELOG-through-2026-09-30.md) — same format, same order, frozen.
Losslessness is proved by [`docs/archive/CHANGELOG-through-2026-09-30.md.verify.sh`](docs/archive/CHANGELOG-through-2026-09-30.md.verify.sh), which re-derives L1/L2/L3 from git; run it rather
than trusting this sentence. Written by `methodology_trim.py` v1.5.0.

---

## 2026-10

### 2026-10-01 · [ad hoc] Phase 2, checkpoint 3 — the tutorials say 29 failure modes

- **Action:** S31. `docs/tutorials/README.md`, `T2_first_session.md`, `T5_cautionary.md` (three places) and
  `TUTORIAL_TEMPLATE.md`: "28 failure modes" → 29, following FM #29's append. Canonical-only files.

### 2026-10-01 · [ad hoc] Phase 2, checkpoint 2 — sequence tags and the merge rule in the `HANDOFFS.md` seed; Learning #17; the count is 29

- **Action:** S31. `starter-kit/HANDOFFS.md`: a *Concurrent sequences* paragraph — each repository's `main` keeps bare
  `S<N>`, other branches tag `S<N>-<seq>` (rmsharp's wording); the keep-both `git merge-file --union --diff3` recipe;
  a merge is one action with one receipt that scores the merged line's last receipt and owes no per-commit
  `reconciled` receipt. `starter-kit/FRAMEWORK_LEARNINGS.md`: Learning #17 (*many hands, one closer; one writer per
  tree*) — `bin/check-learnings` OK, 16 rows (#14 reserved). Live failure-mode counts 28 → 29: `CLAUDE.md` (the
  count and *#29 in v4.1*), `README.md` (the feature list). Release narration and Learning #15's historical "26 of 28"
  left as written. The tutorials' four claims follow in the next commit (the 5-file cap).

### 2026-10-01 · [ad hoc] Phase 2, checkpoint 1 — §Parallel Actors, FM #29 *Shared-state interference*, the one-writer rule

- **Action:** S31. `ITERATIVE_METHODOLOGY.md`: new `## Parallel Actors` (Shape A's contract = slice gates a–d + (e) one
  closer, (f) disjoint write scopes, (g) serial integration; Shape B's identity, ledger merge, one-receipt merge and
  cross-line scoring; the capability-tier elaboration moved from the runner; an honest ceiling), a Principle 9
  paragraph (*many hands, one closer*), a Phase 1 step-4 `--merges` clause, a Mechanical Gates pointer.
  `starter-kit/SESSION_RUNNER.md`: FM #29 appended (1–28 byte-unchanged) + its Degradation row, the step-6 `--merges`
  line, the merge-is-one-action sentence, the one-writer pointer, a task-map row — paid by reduction (capability-tiered
  paragraph compressed to its gate statement, reconcile and session-notes paragraphs tightened): 53,229 → 52,839 B.
  `starter-kit/SAFEGUARDS.md`: the one-writer Blast Radius row, paid by reduction: 17,129 → 16,965 B. **Measured, not
  estimated:** an intermediate draft the density estimate called in-ceiling read 25,034.5 tokens as a pair — over the
  25,000 read cap; the shipped pair reads 24,844.5 (HEAD's was 24,942.5), runner 18,799.5 / 18,900 and SAFEGUARDS
  6,046.4 / 6,100 by doubled reads, densities recorded in `.context-budget.json`. Flight manual 20,533.5 → 22,772.5
  tokens (one read).

### 2026-10-01 · [ad hoc] Parallel-sessions plan Phase 2 — the prose: Parallel Actors, one writer per tree, FM #29 (in progress)

- **Action:** session S31 claimed on `main`: Phase 2 of `docs/planning/parallel-sessions-plan.md` per §8A — the flight
  manual's `## Parallel Actors` (the a–g contract) and Principle 9 paragraph, the runner's pointers, D6 and FM #29
  *Shared-state interference* (paid by reduction), the SAFEGUARDS one-writer row, the `HANDOFFS.md` identity and
  merge paragraphs, Learning #17, and every live count claim. Budgets measured before writing: flight manual 20,534
  tokens (one-read cap 25,000), runner 42 tokens of headroom, SAFEGUARDS 17.

### 2026-10-01 · [ad hoc] S30 close-out — Phase 1 of the parallel-sessions plan done

- **Action:** closes the S30 claim entry (*Parallel-sessions plan Phase 1 — ledger merge mechanics (in progress)*).
  Gate run at `5ea14d1` (the tightened manifest): `quality_ratchet: 12/12 pass · 0 fail · 0 unmeasured · results
  f5b44d3e26a1 · manifest 312cd7c405c8`.

### 2026-10-01 · [ad hoc] Ratchet: `tests-sh-passed` 215 → 237 after Phase 1

- **Action:** S30. Measured at `e4aa45f`: `quality_ratchet: 12/12 pass · 0 fail · 0 unmeasured · results b1e984497caa ·
  manifest 12c131faffed` — `bin/tests.sh` 237/0 (Tests 30 and 31 add 22). Tightening only.

### 2026-10-01 · [ad hoc] Phase 1 Layer B — `bin/check-ledger`, and `check-handoff` stops passing a fused receipt

- **Action:** S30. New canonical-only `bin/check-ledger` (CHANGELOG.md counterpart of `check-handoff`): no conflict
  marker, every `###` heading `YYYY-MM-DD · ` + exactly one source tag right after the date (tags in inline code
  ignored), no duplicate heading, no orphaned text, no seed sentinel once entries exist; date order and union's lost
  blank line deliberately accepted. Declared as a gate, `check-ledger --all` max 0 (an addition). **`bin/check-handoff`
  fix:** `parse_block` kept the last value of a repeated key, so two receipts fused by a union merge passed `--all` as
  one clean receipt — found by Layer A's RED control, contradicting the assumption in rmsharp's #83 review that the
  checker would catch it; a repeated key is now a finding. `bin/tests.sh`: Test 30 gains that assertion (RED against
  the old checker), Test 31 has 14 fixtures; three `check-ledger` mutants each killed, a fourth exposed a footer branch
  that could never change an outcome — removed. Both checkers clean on this repo (28 receipts; live ledger + shard).

### 2026-10-01 · [ad hoc] Measured: GitHub's merge does not apply `merge=union` — probe PR #90, closed unmerged

- **Action (non-commit, then this commit):** S30, the plan's Phase 1 verification item. Two scratch branches off `main`
  (`scratch/union-base`, `scratch/union-head`), each prepending one `CHANGELOG.md` entry at the same anchor, merge
  clean locally under the new `.gitattributes`; [PR #90](https://github.com/KJ5HST/methodology/pull/90) between them
  read **CONFLICTING** (`mergeStateStatus` DIRTY). So GitHub's server-side merge ignores the driver; the documented
  path is the plan's fallback — merge locally, where the driver applies, then push. PR #90 closed unmerged, both
  branches deleted (local and remote). The seed and this repo's `.gitattributes` now say so in their comment.

### 2026-10-01 · [ad hoc] Phase 1 Layer A, checkpoint 2 — the dashboard accounts for the new `.gitattributes` seed (2.11.2)

- **Action:** S30. Adding a distributed file tripped three of the dashboard's structural tests, as Learning #12
  intends: every adopter-root dest must be scored or exempt, and the installed-file tuple must match the manifest.
  `.gitattributes` joins `FRAMEWORK_INSTALLED_SOURCE` with its own signature set, `CONFIG_FILES` (name-matched — a
  dotfile's `Path.suffix` is empty), and the test's `CHECKLIST_EXEMPT` with its reason (merge configuration says
  nothing about session discipline; the advisory is deferred, plan §8A item 11). `DASHBOARD_VERSION` 2.11.1 → 2.11.2,
  both twins byte-identical; unit suite 226 OK. **Found, not changed:** `.gitignore` / `.editorconfig` / `.eslintrc`
  / `.prettierrc` in `CONFIG_EXTS` can never match for the same reason — fixing it would re-categorize every
  scanned repo's dotfiles, a separate change.

### 2026-10-01 · [ad hoc] Phase 1 Layer A — the `.gitattributes` seed merges `CHANGELOG.md` by union; `HANDOFFS.md` stays visible

- **Action:** S30. New `starter-kit/gitattributes` (SEED → `.gitattributes`; `bin/_manifest.py` 29 → 30) and this
  repo's own `.gitattributes`: `merge=union` for `CHANGELOG.md`, `dashboard_history.jsonl`,
  `.context-budget-history.jsonl` — not `HANDOFFS.md`, whose keep-both recipe the seed carries in a comment.
  `bin/tests.sh` Test 30 (7 checks): a two-branch merge conflicts in `HANDOFFS.md` only, `CHANGELOG.md` auto-merges
  whole, the recipe yields three whole receipts; a RED control shows union fusing two receipts into one block at
  exit 0; the real trimmer against a prepend merges clean with nothing archived returning; sync installs the seed and
  never overwrites an adopter's copy. RED: with no seed in the starter-kit, 5 of the 7 fail. **Found:** the fused
  block passes `bin/check-handoff --all` (`parse_block` keeps the last of a repeated key) — fixed in Layer B.

### 2026-10-01 · [ad hoc] Parallel-sessions plan Phase 1 — ledger merge mechanics (in progress)

- **Action:** session S30 claimed on `main`: Phase 1 of `docs/planning/parallel-sessions-plan.md` as §8A amends it.
  Layer A: `.gitattributes` + `starter-kit/gitattributes` seed (three `merge=union` lines, not `HANDOFFS.md`),
  `bin/_manifest.py` 29 → 30, two-branch merge and trim-against-prepend tests, RED first. Layer B: `bin/check-ledger`
  and its gate. In-phase: whether GitHub's merge honours `merge=union`, measured on a scratch PR.

### 2026-10-01 · [ad hoc] S29 close-out — the never-edited gate receipt completed

- **Action:** closes the S29 claim entry (*The ledger gate refuses an edit to a committed entry (in progress)*). Gate
  run at `106f22b`: `quality_ratchet: 11/11 pass · 0 fail · 0 unmeasured · results 30d2a763be2b · manifest
  58b9c63d75da` (`pre-commit-selftest` now runs 17 checks).

### 2026-10-01 · [ad hoc] `.githooks/pre-commit` refuses an edit to a committed `CHANGELOG.md` entry

- **Action:** S29. With the ledger co-staged, the hook now compares the staged ledger with HEAD's entry by entry (a
  `###` heading to the next `#`/`##`/`###` heading or `---` rule, outside fences, trailing blanks ignored) and refuses
  a committed entry whose heading or body changed, or one that disappeared — unless the commit stages a
  `docs/archive/` shard (a trim). Needs python3; skipped without it. `--selftest` 10 → 17 checks, two mutants of
  the check each killed by it. **RED first by replay** of real commits on their parents: under the old hook S26's
  `746c17a` and `d1c1154` passed; under the new one both are refused and the trim `e010fdf`, the release docs, the
  backfill and every S26–S29 claim and close-out pass. Sweep of all 119 ledger-touching commits since v3.7: 71 pass
  (every rmsharp #84–#88 commit among them), 48 refused — each an append to an existing entry under the pre-#84
  practice, three spot-checked by diff. `FRAMEWORK_APPARATUS.md` *Lifecycle* names the hook.

### 2026-10-01 · [ad hoc] The ledger gate refuses an edit to a committed entry (in progress)

- **Action:** session S29 claimed on `main`. `FRAMEWORK_APPARATUS.md` §The Action Ledger, *Lifecycle*, says a committed
  entry is never edited, and nothing enforces it: S26 broke it twice (`746c17a`, `d1c1154`) with every gate green.
  Deliverable: `.githooks/pre-commit` refuses a staged `CHANGELOG.md` that changes or drops a committed entry, except
  a drop that stages an archive shard (the trimmer's commit); RED first by replaying those two commits; selftest cases.
  Also in this commit: S28's receipt cited the archive pointer at `CHANGELOG.md:36`; it is at `:39` — corrected there.

### 2026-10-01 · [ad hoc] S28 close-out — housekeeping done; branches deleted, PR #83 notified, oversight scanner refreshed

- **Action:** closes the S28 claim entry (*Housekeeping … (in progress)*). Non-commit actions this session: merged
  branches `fix/context-budget-fit-skip` and `docs/parallel-sessions-plan` deleted locally and on GitHub, and the stale
  remote `read-set-budgets` (PR #80, merged) deleted — each verified an ancestor of `main` first; a notice of the
  §8A decisions posted on [PR #83](https://github.com/KJ5HST/methodology/pull/83#issuecomment-5942319472), asking
  rmsharp's view on D8 before Phase 3 changes his Test 28; the oversight root's `methodology_dashboard.py` copied
  2.6.1 → 2.11.1 (recorded in the oversight `CHANGELOG.md`). Left for the operator, untouched: two local-only
  unmerged branches, `docs/operator-gated-review-plan` (a 2026-07-31 DRAFT plan awaiting ratification) and
  `experimental/pocock-audit` (17 commits, May). Gate run at `3e857aa`: `quality_ratchet: 11/11 pass · 0 fail ·
  0 unmeasured · results 30d2a763be2b · manifest 58b9c63d75da`.

### 2026-10-01 · [ad hoc] `CLAUDE.md` density re-measured; `.context-budget-history.jsonl` ruled tracked

- **Action:** S28. `.context-budget.json`: `CLAUDE.md` `bytes_per_token` 2.5182 → **2.5687** and `measured_bytes`
  59,119 → 45,842 — the doubled-file read reports 35,693 tokens, so 17,846.5 for the file (the S26 archive moved it
  31% off the old measurement); `max_tokens` 23,483 unchanged (a pin). The tracked-or-ignored ruling open since S23 is
  settled as **tracked**, matching the fork and the reason `.gitignore` already gives (the growth-run trigger reads the
  series, which survives a clone only if committed); its first row is committed here.

### 2026-10-01 · [ad hoc] Ledger trim: `CHANGELOG.md` → `docs/archive/CHANGELOG-through-2026-09-30.md` (96 record(s), 229,112 B → 17,036 B)

**Written by:** `methodology_trim.py` v1.5.0 — a tool action, not a session's judgment.
Moved the oldest **96** record(s) (2026-06-25 → 2026-09-26) out of [`CHANGELOG.md`](CHANGELOG.md) into
[`docs/archive/CHANGELOG-through-2026-09-30.md`](docs/archive/CHANGELOG-through-2026-09-30.md). Losslessness is asserted by L1 (records-zone concatenation), L2 (zone
pinning) and L3 (record partition), and is **re-derivable** — run [`docs/archive/CHANGELOG-through-2026-09-30.md.verify.sh`](docs/archive/CHANGELOG-through-2026-09-30.md.verify.sh)
rather than trusting a digest printed here. Live file 229,112 B → 17,036 B (−92.6%).

### 2026-10-01 · [ad hoc] Backfilled: PR #77 merged 2026-09-03 — the ledger trimmer shipped (`56997af`, merge `907a696`)

- **Action (backfill, not S28's):** [PR #77](https://github.com/KJ5HST/methodology/pull/77) (rmsharp, *Ship the ledger
  trimmer, with tests that run outside this fork* — read-set budgets, 2 of 4) merged at `907a696` on
  2026-09-03T01:38Z: one commit, `56997af` — `starter-kit/methodology_trim.py` and `tools/test_methodology_trim.py`,
  the `bin/_manifest.py` row, the trimmer's seed sections in `starter-kit/CHANGELOG.md` and `starter-kit/HANDOFFS.md`,
  dashboard twins and tests (9 files, +4,691/−6). Neither commit touched this root ledger, so the reconcile gap
  lost sight of it once a later commit edited the ledger (failure mode #27). Found by rmsharp's PR #83 review;
  verified in S27 (`docs/planning/parallel-sessions-plan.md` §8A, row 5). The release that carried it is v3.8.

### 2026-10-01 · [ad hoc] Housekeeping: the items S26 and S27 left open (in progress)

- **Action:** session S28 claimed on `main`. Operator: "Do not leave anything unfinished." This session covers the
  small open items: the PR #77 backfill, the due `CHANGELOG.md` trim, the `CLAUDE.md` density re-measure, the
  `.context-budget-history.jsonl` ruling, merged-branch cleanup, the PR #83 notice, and the oversight dashboard
  refresh. The larger items follow as their own sessions.

### 2026-10-01 · [ad hoc] S27 close-out — the decision receipt completed

- **Action:** S27's `HANDOFFS.md` receipt goes `status: pending` → `complete`; this entry closes the S27 claim entry
  (*Parallel-sessions plan: the twelve §8 decisions (in progress)*). Gate run at `5bab033`: `quality_ratchet: 11/11
  pass · 0 fail · 0 unmeasured · results 30d2a763be2b · manifest 58b9c63d75da`. Not done here, recorded as next
  steps: the PR #77 backfill and the due `CHANGELOG.md` trim found while deciding.

### 2026-10-01 · [ad hoc] Parallel-sessions plan ratified with amendments — §8A records the twelve decisions

- **Action:** S27, under the operator's delegation. `docs/planning/parallel-sessions-plan.md` gains §8A (decision
  table, phase amendments, §9A commands) and its Status moves from DRAFT to ratified-with-amendments. Main
  amendment, measured: `HANDOFFS.md` leaves `merge=union` (rmsharp's objection reproduced — two receipts fuse
  under the default and `zdiff3` styles, merge exit 0; whole only under `diff3`); `CHANGELOG.md` keeps it (trim
  against prepend merges clean at `--cut 1`/`--cut 3`, and the trimmer accepts the result). Also: D5 and FM #29
  wording per rmsharp (FM #29 named *Shared-state interference*); D6 gains a merged-PR ledger check (PR #77's
  `56997af` has no entry here — verified); D8 kept as a requirement and adapted to #87's clone; D11 deferred past
  Phase 5; D12 superseded — the plan ships as v4.1. Nothing implemented.

### 2026-10-01 · [ad hoc] Parallel-sessions plan: the twelve §8 decisions (in progress)

- **Action:** session S27 claimed on `main`. The operator delegated the plan's open decisions ("you do it", answering
  S26's next step (a)). Deliverable: the twelve §8 answers recorded in `docs/planning/parallel-sessions-plan.md`, each
  against rmsharp's PR #83 review and against what has changed since 2026-09-16 (v3.8 and v4.0 shipped; #87 rewrote
  `--source=github`); the claims that can be computed are measured, not assumed. Nothing in the plan is implemented.

### 2026-10-01 · [ad hoc] S26 close-out — the v4.0 receipt completed

- **Action:** S26's `HANDOFFS.md` receipt goes `status: pending` → `complete`. This entry closes the S26 claim entry
  below (*v4.0 — the open pull requests merged and released*), whose `CHANGELOG: pending` line it supersedes; that
  entry is not edited again (see the correction entry below). Gate run cited in the receipt: the one at the tag.

### 2026-10-01 · [ad hoc] v4.0 tagged and released

- **Action (non-commit):** annotated tag `v4.0` at `2f911c9` (tag object `64e5811`), pushed with `main`
  (`746c17a..2f911c9`); [GitHub Release v4.0](https://github.com/KJ5HST/methodology/releases/tag/v4.0) published
  2026-10-01T20:55:11Z, read back as Latest. Gate run at the tagged commit: `quality_ratchet: 11/11 pass · 0 fail ·
  0 unmeasured · results 30d2a763be2b · manifest 58b9c63d75da`. The release: [`CLAUDE.md` §Versioning](CLAUDE.md#versioning)
  v4.0 (pointer, not re-narrated).

### 2026-10-01 · [ad hoc] Correction: the S26 claim entry was edited by two later commits

- **What was wrong:** after PR #84's merge (`99377b3`) made *a committed entry is never edited* a rule of this ledger
  (`FRAMEWORK_APPARATUS.md` §The Action Ledger, *Lifecycle*), S26 kept the older one-entry-per-session habit and
  appended bullets to its own claim entry in `746c17a` (the merges and the tightening) and `d1c1154` (the §Versioning
  archive). Those bullets are accurate and stay; editing them back out would be a third edit. From `2f911c9` on, each
  commit and non-commit action has its own entry.

### 2026-10-01 · [ad hoc] Recorded: v3.8 tagged and released by rmsharp on 2026-09-30

- **Action (non-commit, not S26's):** rmsharp tagged `v3.8` at `6b29d3d` and published its GitHub Release
  (2026-09-30T23:01:13Z) with the README and §Versioning entries deferred; no ledger held it (failure mode #27 —
  reconcile-on-read cannot see a non-commit action). Found at S25's Orient; the deferred docs landed in `2f911c9`.

### 2026-10-01 · [ad hoc] v4.0 release documentation — `CLAUDE.md` §Versioning and `README.md` What's New for v3.8 and v4.0

- **Action:** S26. `CLAUDE.md` *Current version* v3.7 → v4.0; §Versioning gains the v3.8 entry (rmsharp tagged and
  released v3.8 on 2026-09-30 with its docs deferred) and the v4.0 entry; `README.md` What's New gains both, and its
  repository tree a `docs/versioning-archive.md` row. `CLAUDE.md` 40,771 → 45,842 B under its unchanged 59,168 B
  ceiling; `bin/check-links` OK; a sweep for `Current version`, `v3.7`/`v3.8`/`v4.0` and the old gate and test counts
  outside the ledgers found no other stale claim. The release itself: [`CLAUDE.md` §Versioning](CLAUDE.md#versioning)
  v4.0 (pointer, not re-narrated). This opens the ledger's first month heading, per *Placement*; the September entries
  below are not retrofitted.

### 2026-10-01 · [ad hoc] v4.0 — the open pull requests merged and released

- **Action:** session S26 on `main`. Operator: "Merge them and release 4.0." Merge #89 → #88 → #87 → #86 → #85 →
  #84 → #83 onto `main` locally, newest ledger entries first (the order S25's corrected receipt records), each
  `CHANGELOG.md` conflict resolved keep-both with `main`'s side on top; full suite and gate run on the merged tree;
  push; then the v4.0 release docs (README What's New, `CLAUDE.md` §Versioning — which also owes the undocumented
  v3.8), tag and GitHub Release. `CHANGELOG: pending` — results appended at close-out.
- **Seven merges** (claim `1befe64`), first-parent: [#89](https://github.com/KJ5HST/methodology/pull/89) `19f8d4f` →
  [#88](https://github.com/KJ5HST/methodology/pull/88) `19566b6` → [#87](https://github.com/KJ5HST/methodology/pull/87)
  `af8a693` → [#86](https://github.com/KJ5HST/methodology/pull/86) `a4eeef3` →
  [#85](https://github.com/KJ5HST/methodology/pull/85) `a9946c6` → [#84](https://github.com/KJ5HST/methodology/pull/84)
  `99377b3` → [#83](https://github.com/KJ5HST/methodology/pull/83) `d7768cb`. Ledgers merged keep-both with
  `git merge-file --union --diff3` — diff3 keeps git from refining the shared fence lines out of two prepended
  `HANDOFFS.md` receipts, the fusion rmsharp's #83 review demonstrated; `bin/check-handoff --all` after every merge
  (receipts S26 → S25 → S24 → S23). Two non-ledger conflicts: `.quality-gates.json` at #86 (two `min` floors →
  the larger of each) and `starter-kit/BOOTSTRAP.md` at #84 (#87's head + #84's tail, the resolution #87's body
  documents). #84's own entries keep their branch order below, per its new *Placement* rule.
- **Gate run on the merged tree (`d7768cb`):** `quality_ratchet: 11/11 pass · 0 fail · 0 unmeasured · results
  219197070a3b · manifest 21dd9f1c1d67` — `bin/tests.sh` 215/0. **Tightening owed and taken:** `tests-sh-passed`
  188 → 215, `context-budget-unit-tests` 140 → 145, `trimmer-unit-tests` 123 → 124 — `746c17a`; pushed
  `6b29d3d..746c17a`, and GitHub read back all seven PRs as MERGED.
- **Room for the release entries (operator's choice of three):** `CLAUDE.md` stood at 59,119 B under its pinned
  59,168 B resident ceiling. The v1.0–v2.9 §Versioning entries (17 entries, 18,537 B) moved **verbatim** to new
  `docs/versioning-archive.md` (canonical-only, not distributed), with a one-line pointer in their place — the
  archive body compared byte-equal to the span at `746c17a`. `CLAUDE.md` → 40,771 B; the ceiling is unchanged.

### 2026-10-01 · [ad hoc] Fit-gate end-to-end test skips, never fails, when the data refuse the fit

- **Action:** session S25 on branch `fix/context-budget-fit-skip` (from `main` at `6b29d3d`). S24's
  next step (a0): `tools/test_context_budget.py` `TestFitGateEndToEnd.setUp` skips only on calibrate()'s
  "not enough" refusal, but calibrate() has further refusals that depend on the machine's transcripts, not
  on the floor under test — a non-positive slope or an undefined R² (refused at every floor), and no
  variation in the regressor ("cannot fit") — so on such a machine the two tests FAIL instead of skipping
  (S24 measured it: 4 transcripts, slope −3.57, `bin/tests.sh` 138/1, `--run` 8/10). One file, RED first.
  Claimed at `1a36282`; results below.
- **The fix (one file, `tools/test_context_budget.py`):** `setUp` now skips on both stops calibrate() names
  ("not enough", "cannot fit"), then probes the admitting floor 0.0 and skips when the refusal there does not
  cite the floor — the data decided it, not the gate under test. A refusal that *does* cite the floor at 0.0 is
  not skipped: no defined R² is below 0.0, so it would mean calibrate() applied the wrong floor. New unit test
  `test_only_the_floor_refusal_names_the_floor` pins that word as the discriminator (118 → 119 tests).
  **RED first** — the natural failure no longer reproduces here (a 5th transcript turned the slope positive),
  so it was reproduced with a fixture `HOME` whose synthetic transcripts give each shape, tool and test
  unmodified: negative slope and flat response FAILED the presence control, no regressor variation FAILED
  both tests; after the fix all three skip, naming the cause, while a positive and a low-R² fixture still run
  and pass. Three mutant `calibrate()`s (ignores its floor, prints nothing, always refuses) are still caught —
  failed, never skipped — on both admitting fixtures and on this machine's real transcripts.
- **Gate run at `229f08d`:** `quality_ratchet: 10/10 pass · 0 fail · 0 unmeasured · results a3b034f8cabf ·
  manifest 97a7aab85b9a` — `bin/tests.sh` 139/0 again on this machine. **Tightening owed and taken:**
  `context-budget-unit-tests` 118 → 119 (the new pin test), per the manifest's standing rule — `02677ea`;
  re-run at the tightened manifest: `quality_ratchet: 10/10 pass · 0 fail · 0 unmeasured · results f5d8c427f056 ·
  manifest b2e7f7752273`.
- **PR opened (non-commit action):** [PR #89](https://github.com/KJ5HST/methodology/pull/89) from
  `fix/context-budget-fit-skip` at `02677ea`, read back from the API (OPEN, +60/−4, 4 files). **Not merged.**
- **Observed, not acted on:** every open PR (#83–#88) and this branch share base `6b29d3d`; `git merge-tree`
  shows each pair conflicting on the `CHANGELOG.md` top anchor except #84 (clean against all but #87, on
  `starter-kit/BOOTSTRAP.md`), plus #86×#87 on `.quality-gates.json` and this branch×#83 on `HANDOFFS.md`.
  The v3.8 tag and GitHub Release (rmsharp, 2026-09-30, at `6b29d3d`) are not yet in this ledger — the
  release-docs session records them. The operator's "clean everything up so we can merge and version" is
  sequenced in the S25 receipt's next steps, not started here.
- **Correction — merge order:** the receipt's first draft put #84 first; the operator proposed 88 → 87 → 84
  and a scratch-clone simulation of both orders backed it — same final tree except `CHANGELOG.md` order, where
  only newest-entries-first keeps a keep-both resolution newest-on-top (84-first put #88's 09-26 entry below
  #87's 09-21 ones); `bin/tests.sh` on the 88 → 87 → 84 tree 212/0. Receipt `next_steps` (b) corrected in place.

---

**Release history before v3.0 (v1.0 – v2.9):** not re-narrated here — see [`CLAUDE.md` §Versioning](CLAUDE.md#versioning)
for the per-version narrative and `README.md` §What's New for the public restatement. This ledger is
prepend-only from v3.0 forward (decision D5: an authoritative ledger needs no hole at its recent edge,
and duplicating §Versioning would violate cite-don't-restate).
