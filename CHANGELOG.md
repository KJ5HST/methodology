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

- `[issue #<N>]` — a repository issue. Issues live in `KJ5HST/methodology`; the fork
  `rmsharp/methodology` has Issues disabled, so entries — authored from either side — cite an
  **absolute URL**, never a bare `#<N>`, and resolve identically from both.
- `[BL-<N>]` — a backlog item, removed from the backlog in the same commit. That backlog is
  [`docs/planning/BACKLOG.md`](https://github.com/rmsharp/methodology/blob/main/docs/planning/BACKLOG.md)
  on fork `main` only — **this repo has no `docs/planning/BACKLOG.md`** — so a `[BL-<N>]` entry here
  records work whose origin lives in the fork.
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

### 2026-08-02 · [issue #65] The repo's own numbered sets now have structural tests

- **Change:** implements [issue #65](https://github.com/KJ5HST/methodology/issues/65) — Learning #12
  ("when an invariant is mechanical, encode it as a test") applied to the two records the framework's
  own guarantees rest on. Before this, a Learning row could be **renumbered** (which `CLAUDE.md`
  forbids outright), duplicated, malformed, or deleted, and an older `HANDOFFS.md` receipt destroyed
  outright, with `bin/tests.sh` still reporting green. Suite **84 → 99**.
- **New `bin/check-learnings`** — asserts the `starter-kit/SESSION_RUNNER.md` Learnings table is
  contiguous from 1 with no gaps or duplicates, every row exactly 4 columns, every row one physical
  line; then sweeps the **distributed corpus** (`bin/_manifest.py`, 21 markdown files) so every
  `Learning #N` citation resolves to a row that exists — the defect S8 fixed by hand the day before.
  The sweep deliberately **excludes** `docs/audits/`, `docs/planning/`, `README.md` and this ledger:
  those legitimately cite *other projects'* numbering or name bad numbers as the defect being
  described, so sweeping them would manufacture findings against correct prose.
- **`bin/check-handoff --all`** — the checker validated only the **newest** receipt, so a mangled
  older block reported green forever. `--all` validates every block and adds the ledger-level
  invariants: fences balance, no receipt body stranded outside a fence, `session:`/`date:` lead every
  block, session ids unique. The default stays newest-only for the close-out fast path.
- **`--allow-pending` now narrows to the newest block, and relaxes a pending stub to its four
  honest keys.** A Phase 1B claim is *by definition* incomplete, yet the checker demanded all 13 keys,
  so a correct stub reported red for a whole session (S5 documented this friction) and the
  whole-ledger mode was unusable as a live check. An **older** receipt left pending is still caught —
  that is a session that never closed out. The close-out gate is untouched: at Phase 3D `status` is
  `complete` and all 13 keys are demanded.
- **RED-first, and it earned its keep — two mutations were caught proving nothing.** Issue #65 makes
  the precondition non-negotiable, and it immediately paid: (1) the malformed-row mutation anchored on
  the bare string `"| 13 |"`, which matches a **different numbered table** earlier in
  `SESSION_RUNNER.md` — the file has more than one — so it mutated the wrong set and the checker was
  *correct* to pass; (2) a citation mutation replaced the literal `Learning #7`, which does not occur
  (the real text is the plural `Learnings #7/#8`), so it silently changed nothing. Both are now
  guarded: `mutate` **aborts if the edit is a no-op**, and each anchor is pinned to text unique to the
  set under test. The vacuity guard alone is *not sufficient* — defect (1) really did change the file,
  just the wrong part of it, and only running RED exposed that.
- **Known limit, stated rather than papered over:** the citation regex does not span a parenthetical
  (`Learnings #7 (…) and #8` yields only `#7`). That is an under-detection — the checker never invents
  a finding, so a form it cannot parse is simply unchecked, never falsely flagged.
- **Commit/PR:** this commit. **Canonical-only** — `bin/check-learnings` is deliberately **not** in
  `bin/_manifest.py` (same class as `check-handoff` and `check-links`), so `bin/sync` ships adopters
  nothing new; this guards *this* repo's corpus, which is also the honest limit.
- **Session:** S9 · **Verified:** `bin/tests.sh` **99 passed / 0 failed**; `bin/check-links` OK (83
  links / 21 files); `bin/check-learnings` OK (13 rows, all citations resolve); `bin/check-handoff`
  OK both default and `--all` (7 receipts, fences balanced, ids unique); dashboard twins still
  byte-identical; `bin/_manifest.py` unchanged. No Learnings row appended — **#14 is reserved** by the
  unpushed `docs/operator-gated-review-plan` branch's decision D3, and the new checker would now catch
  that collision.

### 2026-08-02 · [ad hoc] Removed the Codex `AGENTS.md`; corrected four cross-repo citations that described the fork as "this repo"

- **Change:** operator-directed cleanup preceding the issue #65 work, in two parts. Recorded as one
  entry because both parts share a root cause — **text written from one repository's vantage, landing
  in another's** — and neither has a backlog or issue origin.
- **(1) The Codex `AGENTS.md` is deleted — and its deletion leaves no commit.** An untracked 116-line
  `AGENTS.md` had sat at the repo root since 2026-07-22 across at least four sessions, named in no
  receipt, no ledger entry, and no `README`. It was a **mechanical find-and-replace of `CLAUDE.md`**
  (`Claude`→`Codex`, `CLAUDE.md`→`AGENTS.md`, `claude.ai/code`→`Codex.ai/code`), applied blind across a
  file that is mostly *dated release narration* — so it falsified records: its v2.7.1 entry claimed the
  cross-doc split v2.7.1 fixed was between "`SESSION_RUNNER.md`/`AGENTS.md`", and its v2.7.2 entry
  credited agent-level memory to "Codex's auto-memory" where the original names Claude Code's. It was
  frozen at **v3.5** while `CLAUDE.md` is at v3.6, so it was also drifting. **Deliberately not
  gitignored:** an ignored regeneration would stop being reported at Orient, which is worse than an
  untracked one that gets flagged every session. Because the file was never tracked, removing it
  produces **zero git diff** — a non-commit action, the exact class failure mode #27 names and Phase 0
  reconcile-on-read cannot catch by design. This line *is* the only durable record that it happened.
- **(2) Four citations described the fork as "this repo".** All four reached this repository through
  fork PRs and were true where they were written: **`CHANGELOG.md`'s own source-tag key** claimed
  *"Issues for this repo live in the upstream parent `KJ5HST/methodology` (this fork has Issues
  disabled)"* — but this repository **is** `KJ5HST/methodology`, with Issues enabled (verified:
  `has_issues=true` here, `false` on `rmsharp/methodology`), so the key misdescribed its own repo; and
  the `[BL-<N>]` key pointed at a `docs/planning/BACKLOG.md` that has never existed here. The
  absolute-URL convention is **kept unchanged** — retargeting it would strand every entry already
  written — only its stated *reason* is corrected. Three `CLAUDE.md` §Versioning citations (v3.1, v3.3,
  v3.6) and one `CHANGELOG.md` citation (v3.3) named fork-only plans by bare repo-relative path; each is
  now an absolute fork URL plus an explicit "not present in this repo", matching the convention the
  v3.1 and v3.6 entries already used. **Every URL was resolved against the API before being written**
  (Learning #13 — an unresolvable reference is the trap), which is also how the `[BL-<N>]` fix was
  corrected mid-edit: `BACKLOG.md` is **live** on fork `main`, not retired as this ledger's 2026-07-06
  entry alone would suggest — it was reopened 07-07 with BL-5, exactly as the 2026-07-07 entry records.
- **Left verbatim by design:** the dated record prose at `CHANGELOG.md` (the 2026-07-06/07 backlog
  entries) and the S3/S7 receipts in `HANDOFFS.md` already label their fork references *fork-only* and
  are frozen records — the v2.7.1 precedent and `README.md:387`. Receipts are never edited after the
  fact regardless.
- **Commit/PR:** `3b58abb` (1B claim) · this commit. Part (1) has no commit of its own, by nature.
- **Session:** S9 · **Verified:** `bin/tests.sh` 84/84, `bin/check-links` OK, and all five cited fork
  paths resolved via `gh api` (`operator-gated-review-plan.md` was checked too and is **404 — correctly
  cited nowhere**).

### 2026-08-01 · [ad hoc] Discharged the three documentation follow-ons from the Learning #13 cycle

- **Change:** three independent fixes, operator-directed in one run, as three checkpoint commits —
  `15ccb38` (citations) · `faf42fb` (Phase 3D) · `f85a324`'s successor for the README. **Recorded as
  bundling, not as a vertical slice:** three capabilities with no prior plan-mode contract does not pass
  the failure-mode-#26 slice test, and calling it one would be the failure mode wearing a costume.
- **(1) Five citations pointed at Learnings that do not exist.** `starter-kit/RECOMMENDED_SKILLS.md` and
  `workstreams/DEVELOPMENT_WORKSTREAM.md` cited Learnings **#28/#29/#30/#34** against a canonical table
  of 1–13, and one sent the reader to *"Learning #30 (in `ITERATIVE_METHODOLOGY.md` §Knowledge
  Accumulation)"* — a section holding no numbered learnings at all. **Root cause, traced not guessed:**
  all five descend from `docs/audits/2026-05-02-mattpocock-skills-evaluation.md`, which cites **rad-con's**
  project Learnings by that project's own numbering (`"Learning #30 (rad-con UDP issue batch, S357…)"`);
  v2.6 distilled the audit into the distributed corpus and the numbers came along without their referent.
  Each site now states the substance the number stood for, so the text stands alone in the single-repo
  install where these files actually land. The audit doc is deliberately untouched — dated record prose,
  canonical-only, and correct about rad-con (v2.7.1 precedent).
- **(2) Learning #13's writer-side duty now reaches Phase 3D.** The duty ("derive it or label it a
  guess") lived only in the Learnings table, so a session following the operative close-out checklist
  never met it — **Learning #8** exactly. Added as prose on requirements 3 and 5, the two that actually
  carry predictions. **Deliberately not a seventh row:** seven live count-claims depend on the
  requirements being six (`SESSION_RUNNER.md:254`/`:256`/`:258`, `HOW_TO_USE.md:764`/`:791`,
  `ITERATIVE_METHODOLOGY.md:293`/`:523`) and `bin/check-handoff` maps the six onto receipt fields, so a
  seventh would imply a seventh `REQUIRED_KEY` and invalidate every receipt already written. The
  paragraph adds no requirement; it constrains how two of the six are written, and says so.
- **(3) `README.md` §What's New no longer lags the shipped table.** Learning #13 shipped with no version
  event (operator decision), which would have left the public restatement describing the corpus through
  #12 while `bin/sync` distributed 13 — breaking a 6-for-6 pattern (#7–#12 each have a bullet). New
  **`### Since v3.6 (unreleased)`** section rather than an invented version number; it states that it
  folds into the next release's section when one is cut. Pattern is now 7-for-7.
- **Verified at each of the three boundaries, not once at the end:** `bin/tests.sh` 84/84 and
  `bin/check-links` OK after every checkpoint (82 → **83** links, the one added relative link resolving
  in adopter layout per the v2.8 convention). Post-fix sweeps: no `Learning #N` with N > 13 survives in
  `starter-kit/` or `workstreams/`; the requirements table is still exactly 6 rows; `REQUIRED_KEYS` still
  13; the Learnings table still 1–13; all seven count-claims re-checked and still true.
- **Distribution:** `SESSION_RUNNER.md`, `RECOMMENDED_SKILLS.md` and `DEVELOPMENT_WORKSTREAM.md` are
  `bin/_manifest.py`-**TRACKED**, so adopters receive (1) and (2) via `bin/sync`; `README.md` is
  canonical-only, so (3) is not distributed.
- **Session:** S8 · **No principle, phase, gate, or workstream change; the failure-mode count stays 27**,
  and the Learnings table is deliberately unchanged — **#14 is reserved** by the operator-gated-review
  plan's decision D3.

### 2026-08-01 · [ad hoc] Opened issue #65 — the repo's own numbered sets have no structural test

- **Action:** filed [issue #65](https://github.com/KJ5HST/methodology/issues/65). No code or doc change;
  this is the ledger record for a non-commit action (failure mode #27).
- **The gap:** the `starter-kit/SESSION_RUNNER.md` **Learnings table** and the `HANDOFFS.md` **receipt
  ledger** both enforce their structural invariants by human attention alone. Nothing in `bin/tests.sh`
  (84 checks) or `tools/test_methodology_dashboard.py` (197 tests) asserts anything about either. This
  is **Learning #12** pointed at the file Learning #12 lives in.
- **Mutation-proved against `main` at `a4e2b30`, not argued.** Learnings table: a malformed 3-column row
  14, a duplicate row number 12, and deleting row 11 outright each leave `bin/tests.sh` at **84 passed,
  0 failed** — including the renumbering case `CLAUDE.md` forbids outright. Receipt ledger: stripping an
  older receipt's fence, `session:` and `date:` drops the block count 4 → 3 and both `bin/check-handoff`
  and `bin/tests.sh` still report green, because the checker validates only the **newest** receipt.
- **Not hypothetical — it already happened here**, and the same corruption also breaks fence-matching for
  the block below it, so one defect silently damages two receipts. The issue deliberately **cites no SHA**
  for that incident: both the introducing and repairing commits live on an unpushed branch, and an
  unreachable reference is precisely the trap Learning #13 was just added to prevent. Every claim in the
  issue reproduces from a clean clone of `main` instead.
- **Scope proposed:** test-only, canonical-only — contiguous/unique/4-column/one-line for the Learnings
  table; balanced fences, mandatory `session:`+`date:`, unique session ids, and a `--all` mode for
  `bin/check-handoff` that keeps newest-only as the close-out fast path. Non-goals stated explicitly:
  structure never quality, no distributed-file change, failure-mode count stays **27**. Learning #12's
  RED-first precondition carried over verbatim.
- **Session:** S7 · **Verified:** all five mutations re-run against `main` in a throwaway worktree
  (since removed) rather than quoted from the earlier PR #63 re-review; issue confirmed OPEN.

### 2026-07-27 · [ad hoc] New `SESSION_RUNNER.md` Learning #13 — a forward-looking claim has to be computed, not re-read

- **Change:** one row appended to the `starter-kit/SESSION_RUNNER.md` Learnings table (table was
  **1–12**; appended, never renumbered — the diff on that file is a single added line with no
  deletions, so rows 1–12 are byte-unchanged). That file is `bin/_manifest.py`-**distributed**, so
  adopters receive the row via `bin/sync`. *A forward-looking claim cannot be checked by re-reading
  a file — it has to be computed.*
- **Why the existing rows did not cover it.** Learning #6 and FM #11 cover claims written *from
  memory*, and both prescribe the same repair: go re-read the file that confirms the claim. #7, #10
  and #12 cover cross-references that go stale in the *corpus*. Neither reaches the other half of a
  handoff — its predictions. A prediction describes a state that does not exist yet, so no file
  confirms it; the only honest check is to derive it from current state, or to say plainly that it
  is a guess.
- **The motivating case is in this repository's own history, and it refutes the tempting
  diagnosis.** The S3 receipt's `next_steps` tells the next session to *"expect one CHANGELOG union
  conflict, resolve newest-on-top."* The sync merge that followed met **seven** conflicting files.
  But the prediction had not gone stale — it was never true. Two commands show why:
  `git log -S 'expect one CHANGELOG union conflict' -- HANDOFFS.md` locates the sentence first
  entering the tree in `bec4095`, and `git show --stat bec4095` shows that same commit changing
  seven files. Every fact needed to get the prediction right was already in the author's own working
  tree at the moment it was typed. (The seven-conflict outcome was measured against the contributing
  fork's `main` at `ae6050d`, which is not reachable from this repository, so it is corroboration
  here — the two commands above carry the argument on their own.)
- **Why it earns a row rather than a gotcha:** a wrong prediction is worse than none, because it
  licenses the successor to resolve *quickly* rather than *carefully* — and a merge resolved on the
  belief that "only the ledger differs" discards work silently, with no failing check to catch it.
  The countermeasure is mechanical and non-mutating: `git merge-tree --write-tree --name-only`
  computes the conflicting paths without touching a working tree.
- **Cross-reference sweep (Learnings #7/#10).** `git grep -nE 'table (was|is|now) ?1[–-][0-9]+'`
  returns two live sites outside this entry — the v3.4 narration in this ledger and the matching
  v3.4 bullet in `CLAUDE.md` §Versioning — both dated release narration this repo leaves verbatim by
  design (the v2.7.1 precedent). The Learnings caption states no size. Nothing else needed updating.
- **Commit/PR:** [PR #63](https://github.com/KJ5HST/methodology/pull/63)
- **Session:** docs-only follow-on to the v3.6 ship · **Verified:** `bin/tests.sh` 84/84 ·
  `bin/check-links` OK (82 links / 21 files) · Learnings table parses as contiguous rows 1–13, every
  row 4-column, rows 1–12 byte-unchanged · brand-neutrality grep empty.

### 2026-07-27 · [ad hoc] Released v3.6 — dashboard signal integrity

- **Change:** annotated tag `v3.6` (`23098da`) cut at `d7a482a`, the PR #62 merge commit, plus GitHub
  Release *"v3.6 — Dashboard signal integrity"*, published 2026-07-27T06:02:04Z. Cite-don't-restate:
  the full narrative lives in [`CLAUDE.md` §Versioning "v3.6"](CLAUDE.md#versioning).
- **Unlike the v3.5/v3.4/v3.3 releases, this one had no release-narration commit of its own.** The
  version bump rode PR #62 itself — `CLAUDE.md`'s "Current version" line, the §Versioning entry, and
  `README.md` §What's New in v3.6 all landed inside that PR. So the release action reduced to *tag +
  publish*, leaving **no commit at all**.
- **Why this entry is four days late — it is the failure mode it records.** A release is precisely the
  non-commit action failure mode #27 names, and the one class Phase 0 reconcile-on-read **cannot**
  catch by design: reconcile diffs `git log` against the ledger frontier, and a tag plus a GitHub
  Release move neither. With no release commit to notice either, nothing in the machinery could have
  surfaced it. Two consecutive sessions' Orient reported the gap (S3's successor, then the PR #63
  re-review) and neither was scoped to fix it. Recorded 2026-08-01 by operator direction; dated to the
  action, not to the recording, so the timeline stays true.
- **Commit/PR:** no release commit exists (see above); this entry is the record. Tag `v3.6` → `d7a482a`
  (PR [#62](https://github.com/KJ5HST/methodology/pull/62)).
- **Session:** S5 · **Verified:** tag confirmed annotated and pointing at `d7a482a`; Release publish
  timestamp read from the API, not inferred; `bin/tests.sh` 84/84; `bin/check-links` OK (82 links / 21
  files).

### 2026-07-26 · [ad hoc] Dashboard signal-integrity campaign lands upstream — the scanner's signals now mean what they say (v3.6)
- **Change:** the portfolio health scanner's signals are reconciled with what they actually measure,
  closing upstream issues [#59](https://github.com/KJ5HST/methodology/issues/59),
  [#60](https://github.com/KJ5HST/methodology/issues/60) and
  [#61](https://github.com/KJ5HST/methodology/issues/61) plus five defects that were never filed.
  **One root cause, eight defects:** every one was *a proxy presented as a semantic finding* — a
  110-point weighted sum rendered as a percentage; `.exists()` at the repo root rendered as
  "adoption"; a checkbox regex rendered as "completed work not migrated"; any file whose name starts
  with `CHANGELOG` rendered as "has an action ledger"; and a signal that never executes rendered as
  "no finding". The motivating case was a **false GREEN on a real adopter**, which silenced the exact
  finding the operator needed. Seven layers, one per session: scale honesty (2.9.0), ledger identity
  (2.9.1), backlog shape with abstention (2.9.2), repo role (2.10.0, closes #59), a
  completeness-critic doc sweep, the installer no longer defeating doc-only detection (2.10.1),
  close-out, and — added after the pre-PR review — evidence-gating the ambiguous framework doc
  names (2.10.2). `DASHBOARD_VERSION` **2.8.0 → 2.10.2**, both twins byte-identical; the scanner
  grows **2,475 → 3,336** lines and its unit suite **29 → 197**. `bin/tests.sh` is unchanged at **84** —
  the campaign added no shell checks. Cite-don't-restate: the full narrative, the honest limits, and
  the one live defect that ships **disclosed rather than quietly fixed** (the seed-discount hole —
  not a regression: v3.5, 2.10.1 and 2.10.2 were run side by side and all three return the
  identical wrong result) live in
  [`CLAUDE.md` §Versioning "v3.6"](CLAUDE.md#versioning).
- **Commit/PR:** [PR #62](https://github.com/KJ5HST/methodology/pull/62) — `9e93588` (S3 claim) ·
  `7a7e9a2` (the 13-file port + three approved edits + this entry) · `eeb827f` (pre-PR review
  fixes) · `bec4095` (Layer 8) · this commit — branch `feat/dashboard-signal-integrity`,
  built from `upstream/main` because fork `main` carries fork-only `docs/planning/*` that must not
  ship here. **The per-layer development history is fork-`main`-only and is not reachable from this
  repo's history** — unlike the v3.1 campaign, whose per-session commits were branch commits that
  merged here. For archaeology those layer commits are `6b10f09` (L1) · `3838a13` (L2) · `9ebedda`
  (L3) · `abb3b29` (L4) · `baa1dd1`+`fc65013` (L5) · `ae9e5b7`+`ef71946`+`6f10460`+`f1cfdbc`+`d78cd41`
  (L7) · `307a7a8`+`79fb2b1`+`99ee81c`+`081d77c`+`cbde2a1`+`ae6050d` (L6, close-out and release
  narration), all on [`rmsharp/methodology@main`](https://github.com/rmsharp/methodology/commits/main).
  Ratified plan: [`docs/planning/dashboard-signal-integrity-plan.md`](https://github.com/rmsharp/methodology/blob/main/docs/planning/dashboard-signal-integrity-plan.md) (`bc2481d`, fork `main` only).
  Tagged `[ad hoc]` rather than `[issue #NN]` because the one-tag-per-entry rule admits a single
  source and this action spans three issues; the per-layer entries carrying the individual `[issue
  #59]`/`[issue #60]`/`[issue #61]` tags are on the fork's ledger. The annotated tag and GitHub
  Release for **v3.6** are cut at the merge commit, per the v3.2/v3.4/v3.5 pattern.
- **Session:** S3 · **Verified:** `tools/test_methodology_dashboard.py` **197/197 OK** · `bin/tests.sh`
  **84 passed / 0 failed** · `bin/check-links` OK (82 relative links across 21 distributed markdown
  files) · `diff -q` on the two dashboard twins identical · `py_compile` clean on all three Python
  files · `CLAUDE.md`'s starter-kit table asserted row-for-row against `ls starter-kit/` (11 of 11).

### 2026-07-08 · [ad hoc] Released v3.5 — capability-tiered review
- **Change:** version bumped **v3.4 → v3.5** (`CLAUDE.md` "Current version" line + a new §Versioning
  entry; `README.md` What's New) covering the capability-tiered review elective addition (BL-7, PR #57,
  already merged). Cite-don't-restate: the full narrative lives in
  [`CLAUDE.md` §Versioning "v3.5"](CLAUDE.md#versioning).
- **Commit/PR:** this commit (release narration) → merged; annotated tag `v3.5` + GitHub Release.
- **Session:** release · **Verified:** `bin/tests.sh` 84/84; `bin/check-links` clean.

### 2026-07-08 · [ad hoc] Capability-tiered review — elective vertical-slice addition (BL-7)
- **Change:** codifies the operator-observed pattern from the close-out-receipt slice's hybrid model
  split (session S1) as an elective addition to `starter-kit/SESSION_RUNNER.md` §Vertical Slice
  Sessions: **capability-tiered review** — a pre-declared slice's layers may be delegated to a
  lighter/faster capability tier only where an objective gate (test suite, exhaustive grep, mechanical
  spec) proves correctness, with the strongest tier reviewing every delegated layer's output before
  that layer's checkpoint commit lands; explicitly additional evidence for gates (c)/(d), never a
  substitute, and explicitly not a fifth gate — forecloses two FM #26 misreadings (treating review as
  proof on its own, batching review to the end instead of per boundary). Four files: **`starter-kit/SESSION_RUNNER.md`**
  the core paragraph + new **Learning #11**; **`ITERATIVE_METHODOLOGY.md`** a one-sentence routing
  pointer in §Matching Reasoning Effort to Stakes; **`starter-kit/RECOMMENDED_SKILLS.md`** an
  illustrative Claude-Code-specific addendum after §Reasoning Effort (brand names confined to this file
  only); **`docs/tutorials/T5_cautionary.md`** a corollary citing this repo's own close-out-receipt
  slice as the worked "doing it right" counter-example to FM #26. Preceded by an operator-approved
  3-candidate design panel (placement, naming, scope, and all three optional extras decided by the
  operator). **No new phase, gate, principle, workstream, or failure mode; failure-mode count stays 27.**
  All four touched files are `bin/_manifest.py`-distributed except the tutorial (canonical-only), so
  adopters receive the core/recommendation discipline via `bin/sync`.
- **Design verification:** drafted, then adversarially checked by a 4-lens review (guardrail fidelity,
  citation/numbering fact-check, voice & agent-independence, completeness-critic whole-corpus sweep) —
  all four lenses independently confirmed the same real defect (brand names "Sonnet-5/Opus-4.8" leaking
  into the new Learning #11's Source column in the brand-neutral core file) — fixed before commit; no
  other findings across links, anchors, FM/gate byte-stability, or corpus-wide staleness checks.
- **Commit/PR:** this commit — branch `feat/capability-tiered-review` (from `upstream/main`).
- **Session:** capability-tiered review (BL-7 design + implementation) · **Verified:** `bin/tests.sh`
  84/84; `bin/check-links` clean.

### 2026-07-08 · [ad hoc] Released v3.4 — completeness-critic review lens
- **Change:** version bumped **v3.3 → v3.4** (`CLAUDE.md` "Current version" line + a new §Versioning
  entry; `README.md` What's New) covering the completeness-critic lens (issue #55). Cite-don't-restate:
  the full narrative lives in [`CLAUDE.md` §Versioning "v3.4"](CLAUDE.md#versioning).
- **Commit/PR:** this commit (release narration) → merged; annotated tag `v3.4` + GitHub Release.
- **Session:** release · **Verified:** `bin/tests.sh` 84/84; `bin/check-links` clean.

### 2026-07-08 · [issue #55] Completeness-critic review lens — new Learning #10 + AUDIT_WORKSTREAM guidance
- **Change:** promotes **Learning #7** (cross-reference completeness at self-review) and **Learning #8**
  (close-out-gate checklist propagation) from authoring-time self-checks to an explicit **review-time
  lens**: when a change adds, renames, or removes a concept, artifact, file, step, or numbered-set
  member, a review/audit pass now owes a whole-corpus sweep (not just the diff) for enumerations,
  worked examples, indexes, and count-claims that now lag. Three files: **`SESSION_RUNNER.md`** new
  **Learning #10** (table was 1-9); **`AUDIT_WORKSTREAM.md`** new anti-pattern **#9** "Diff-scoped blind
  spot" (list was 1-8), a new Verification Checklist bullet, and a note that `/code-review`/`/review`/
  `/security-review` are diff-scoped by design so the sweep stays methodology-owned; **`ITERATIVE_METHODOLOGY.md`**
  one sentence added to §Review/Audit Sessions citing the new Learning + the operative checklist step.
  Motivated by the v3.3 doc-completeness gap (PR #54) that a clean 6-lens adversarial review missed —
  [KJ5HST/methodology#55](https://github.com/KJ5HST/methodology/issues/55). **No new phase, gate,
  principle, or workstream; failure-mode count stays 27.** All three touched files are
  `bin/_manifest.py`-distributed, so adopters receive this via `bin/sync`.
- **Design verification:** drafted, then adversarially checked by a 4-lens review (acceptance-criteria
  coverage, numbering/citation fact-check, a reflexive Learning-#7 self-check for other stale
  cross-references, and placement/precedent judgment) — 2 of 4 lenses clean, 2 raised real findings
  (a mis-anchored insertion point in `AUDIT_WORKSTREAM.md`'s Recommended Skills section; a citation
  missing the `starter-kit/` path prefix used elsewhere in the repo) — both fixed before commit.
- **Commit/PR:** this commit — branch `feat/completeness-critic-review-lens` (from `upstream/main`).
- **Session:** completeness-critic lens · **Verified:** `bin/tests.sh` 84/84; `bin/check-links` clean.

### 2026-07-08 · [ad hoc] v3.3 doc-completeness — propagate the receipt into HOW_TO_USE, README tree, tutorials
- **Change:** the v3.3 close-out receipt is now reflected in the *secondary* docs that describe or
  demonstrate close-out, closing the Learning #7 propagation gap the release surfaced (the operator
  asked "has documentation been fully updated?" — it had not). **`HOW_TO_USE.md`** §Phase 3 3D now names
  the durable `HANDOFFS.md` receipt (it is DISTRIBUTED — was inconsistent with the synced
  `SESSION_RUNNER.md`); **`README.md`** Repository-Structure tree lists `HANDOFFS.md` (starter-kit) +
  `check-handoff` (bin/); the **tutorials** `T2_worked_transcript.md` (a full ` ```handoff ` receipt in
  its Phase-3 close-out + the receipt joins the `git add`), `T2_first_session.md` (1B receipt stub + the
  3D/expected-result), and `T3_compounding_loop.md` (the receipt carries `predecessor_score`, making the
  compounding loop machine-checkable). Mirrors the v3.1→BL-6 downstream-completeness pattern; **no version
  event** (docs-lag). No principle/phase/gate/workstream/FM change.
- **Commit/PR:** `67581fd` (distributed: `HOW_TO_USE.md` + `README.md`) · this commit (tutorials:
  `T2_worked_transcript.md`, `T2_first_session.md`, `T3_compounding_loop.md`) — branch
  `docs/v3.3-doc-completeness` (from `upstream/main`).
- **Session:** doc-completeness follow-on · **Verified:** `bin/check-links` clean; a completeness sweep
  found no other tutorial demonstrating close-out without the receipt (T5 only references a prior handoff).

### 2026-07-08 · [ad hoc] Released v3.3 — durable close-out receipt
- **Change:** version bumped **v3.2 → v3.3** (`CLAUDE.md` "Current version" line + a new §Versioning
  entry; `README.md` What's New) and shipped as an **annotated tag `v3.3` + GitHub Release (Latest)**,
  covering the close-out-receipt slice (PR #52, merge `e5638af`). Cite-don't-restate: the full narrative
  lives in [`CLAUDE.md` §Versioning "v3.3"](CLAUDE.md#versioning).
- **Commit/PR:** this commit (release narration) → merged; annotated tag `v3.3` + GitHub Release.
- **Session:** release · **Verified:** post-merge `bin/tests.sh` green — Test 9's github-source 404
  clears now that `HANDOFFS.md` is on the default branch.

### 2026-07-08 · [ad hoc] Close-out receipt — durable machine-checkable handoff artifact (shipped in v3.3, PR #52)
- **Change:** implemented the ratified plan (fork `main`:
  [`docs/planning/close-out-receipt-durable-artifact-plan.md`](https://github.com/rmsharp/methodology/blob/main/docs/planning/close-out-receipt-durable-artifact-plan.md))
  as a pre-declared **vertical slice** —
  one capability, checkpoint commit + verification at each layer boundary. Fixes "agent had to be
  prompted for the close-out report." **P1:** new `starter-kit/HANDOFFS.md` SEED — a
  per-session `handoff`-block receipt ledger (twin of this action ledger) — added to `bin/_manifest.py`
  `DISTRIBUTION` (SEED) + `SEED_FORMAT_MARKERS` (`"Handoff Receipts"`); `sync` seeds it, `status`
  reports `present` / `present (stale format)`, `sync` never clobbers it. **P2:** `bin/check-handoff`
  (canonical-only, python3 stdlib) + `bin/tests.sh` Tests 21–22 — asserts a receipt's presence +
  structural completeness (fence-isolated block, integer scores, `path:line` in `key_files`, sha-or-
  `pending` in `what_was_done`) plus anti-pattern lints (rejects "pick next from backlog", "need to
  verify", bare placeholders), never semantic quality. **P3a:** protocol wiring — `SESSION_RUNNER.md`
  (1B receipt stub, 3D "write the six as a durable receipt", Planning checklist, slice-revert) +
  `ITERATIVE_METHODOLOGY.md` (Phase 1B, Phase 6 step 7, the Review/Planning/Debugging session types).
  **P3b:** the receipt item added to all three campaign checklists (per-session + consolidation) —
  Learning #8 fully discharged. **P4:** Phase 0 reconcile-on-read extended to backstop the receipt — a
  missing or still-`pending` receipt for a session that left commits is reconstructed `status:
  reconciled` at the next Orient, folded into the one write Phase 0 already permits (`SESSION_RUNNER.md`
  step 6 + mechanics note, `ITERATIVE_METHODOLOGY.md` Pre-Flight). **P5:** framing — strengthened
  **FM #6** to name the durable receipt (count stays 27, no new FM), a degradation-detection row
  (commits landed but receipt never completed → FM #6), **Learning #9** (a handoff is dependable only
  as a durable machine-checkable artifact: gate-on-write AND reconcile-on-read), and the
  SAFEGUARDS/BOOTSTRAP harness stop-hook **recommendation** (agent-specific, soft-remind, never shipped;
  `bin/check-handoff` noted canonical-only/copyable). **P6:** dogfood close-out — the canonical repo's
  own root `HANDOFFS.md` receives its first receipt (S1) for this very slice, and `bin/check-handoff`
  validates it green (first non-fixture run). Merged to `KJ5HST/main` as **PR #52** (merge `e5638af`);
  the version event (D4) resolved to a **v3.3** minor — see the release entry above.
- **Commit/PR:** `4f0bea7` (P1: artifact + manifest) · `1646773` (P2: checker + tests, built by
  Sonnet 5; Opus review accepted `status: reconciled` for P4's backfill and made the `HANDOFFS.md`
  template checker-safe — no inline `#` comments, since `#` is a literal value char as in `PR #52`) ·
  `f722a84` (P3a: SESSION_RUNNER + IM protocol wiring, Opus) · `afbbe7d` (P3b: 3 campaign
  checklists, Opus) · `5f13c99` (P4: Phase 0 receipt reconcile, built by Sonnet 5; Opus review
  verified the false-positive scoping — one receipt per session, not per commit — and documented the
  `reconciled` status in the seed) · `719a41d` (P5: framing — FM #6 + degradation row + Learning #9 +
  stop-hook recommendation, Opus) · this commit (P6: dogfood root receipt + final verification, Opus —
  P6's deliverable is the session's own handoff, so authored, not delegated) — branch
  `feat/close-out-receipt` (from `upstream/main`); model
  split hybrid — **P2 + P4 Sonnet 5; P1/P3/P5/P6 Opus 4.8**, Opus reviewing every Sonnet phase (P6
  moved to Opus because its deliverable is the session's own close-out handoff, not a delegable task).
- **Final review & fixes:** a 6-lens adversarial review (`wf_91880f5f-35c`, default-to-refute verify) —
  **12 raised → 7 confirmed → all fixed** across 3 checkpoint commits. **Fix A (checker, this commit):**
  `key_files`'s `path:line` regex now requires a **path-like** pre-colon token (`/` or `.`), so an
  incidental colon-digit in prose (`John 3:16`, `10:30`, `3:1`) no longer passes (C1); `what_was_done`'s
  sha-shape now requires a **hex letter**, so a bare 7+ digit decimal/timestamp no longer counts as a sha
  (C2); + a docstring caveat that an unwrapped example fence shadows the real receipt (C7). Regression
  tests added (**81 → 83**). **Fix B (synced docs):** the mandatory-procedure references to
  `bin/check-handoff` in `SESSION_RUNNER.md` §3D, `ITERATIVE_METHODOLOGY.md` Phase 6, and the
  `HANDOFFS.md` seed now carry the "canonical-only — copy it in; the dependable backstop is Phase 0
  reconcile" caveat the optional-hook subsections already had (C4/C5), and the receipt-to-requirements
  wording no longer double-counts `self_score` (C6: "the six requirements, the sixth being `self_score`,
  plus `predecessor_score`"). **Fix C (this commit):** `HANDOFFS.md` added to BOOTSTRAP's seed
  enumerations (repo tree, root-files table, both "seeded"/"seeded-once" sentences) — deliberately NOT
  the named three-file `BACKLOG`/`CHANGELOG`/`ROADMAP` task-tracking split (HANDOFFS is a close-out
  record, not part of that concept; "three" stays accurate); the campaign per-session checklists drop
  the bare `bin/check-handoff` mention (its caveated form stays in §3D). **All 7 confirmed findings fixed**
  (`28cecc8` A · `ac97722` B · this commit C). 5 findings were refuted (e.g. the missing `--range`
  mode — plan-optional; the last-wins duplicate-key parse — benign).
- **Session:** close-out-receipt slice · **Verified:** `bin/tests.sh` **83/84** (the 1 = github-source
  404 on the not-yet-pushed `HANDOFFS.md`, clears on merge); `bin/check-links` clean; block-isolation +
  per-field-defect + C1/C2-regression fixtures green; **`bin/check-handoff` green on the first real
  receipt** (root `HANDOFFS.md`, S1 — dogfood, first non-fixture run).

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
