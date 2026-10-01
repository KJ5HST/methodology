# CHANGELOG.md — archive: 2026-06-25 → 2026-09-26

Retired records from [`CHANGELOG.md`](../../CHANGELOG.md), moved here so the live ledger stays small enough to read
in one pass. Same format, same newest-on-top order — this is the same ledger, continued.

Holds **96 record(s), 2026-06-25 → 2026-09-26**. Cut key: `2026-09-30`. Counts here are computed from the file
itself, never carried forward. This shard is frozen: it states no forward-looking rule,
because the live file owns those and a copy of one was wrong a day after it was written.

---

### 2026-09-26 · [ad hoc] The prose update route gets the three rules that stop it overwriting an adopter's ledgers

- **Why:** `starter-kit/BOOTSTRAP.md` §Without `bin/sync` was one sentence — *"It will fetch the latest
  starter-kit files and overlay them"* — and it named no exception. An agent following it literally overlays
  `CHANGELOG.md` and `HANDOFFS.md`, which are seeds: the adopter's action ledger and every close-out receipt
  are replaced with empty templates. A six-adopter acceptance test found this and rated it critical. The
  `bin/sync` route has never had the defect; only the prose route does, and the prose route is the one the
  instruction in that section tells people to use.
- **What is added:** three numbered rules given with the instruction. **(1)** a two-row table splitting the
  distribution into tracked files that are overlaid and adopter-owned files that are never overwritten, with
  the consequence of getting it wrong stated in the sentence after it. **(2)** the hand reconcile the seeds
  need afterwards, pointing at the *Updating an existing project from an earlier methodology version*
  paragraph in §Setup with `bin/sync` rather than restating it, so the two cannot drift apart. **(3)** verify
  with `bin/status` and what its five verdicts mean.
- **The table is derived from `bin/_manifest.py`, not written from memory:** its `DISTRIBUTION` list is what
  classes six files as seeds — `CHANGELOG.md`, `HANDOFFS.md`, `SESSION_NOTES.md`, `ROADMAP.md`,
  `.context-budget.json`, `.quality-gates.json` — and every other entry as tracked.
- **Rule 3's five verdicts are the ones `bin/status` actually prints:** `missing`, `current`,
  `N versions behind`, `locally modified`, and `present (stale format)` — read from the source, not inferred
  from the documentation.
- **Measured:** `bash bin/tests.sh` reports **139 passed, 0 failed** on this branch, unchanged from the commit
  it starts from; `bin/check-links` resolves 107 links; `quality_ratchet.py --run` reports **10/10 pass**. The
  change is prose in one file and no gate moves.

### 2026-09-26 · [ad hoc] The suite's ratchet floor rises to what this branch measures

- **Why:** this branch adds 49 assertions to `bin/tests.sh`, and `.quality-gates.json` still floored
  `tests-sh-passed` at the count from before them. The ratchet therefore protected none of the new tests — a later
  change that silently removed all 49 would still have passed the gate.
- **Measured, not assumed:** `bash bin/tests.sh` reports **139 passed, 0 failed** in a clone of the commit this
  branch starts from and **188 passed, 0 failed** in a clone of its tip. Diffing the two runs' `PASS:` lines names
  49 assertions present only on the branch and **none** of the base's missing from it. The floor becomes 188.
- **Tightening only, and the guard is live:** `quality_ratchet.py --precommit` accepts the change (exit 0) and
  refuses the same line lowered by one (exit 2, *"gate 'tests-sh-passed': floor lowered 139 -> 138"*), so the check
  was exercised on this tree rather than assumed to work. `--run` reports 10/10 pass with the new floor met exactly.
- **A later merge cannot invalidate it:** the gate is a minimum, and every other change in flight adds tests rather
  than removing them. Where another one raises this same line to a lower number, a minimum resolves to the larger.

### 2026-09-22 · [ad hoc] The documents say what the update route now does, and stop requiring the `gh` CLI

- **Why:** two earlier changes on this branch made `--source=github` clone the repository and made `bin/sync`'s
  refusal name a source that has no history to compare against. The prose still described the route as it behaved
  before: it required the `gh` CLI, and it told readers to *prefer* `--source=local` because only a local checkout
  carried the history that recognizes a file as merely behind. Both statements are now false.
- **The `gh` CLI is no longer required, and four documents said it was:** `README.md`'s Option A, the sync block in
  `starter-kit/BOOTSTRAP.md`, and the `--source=github` lines in `docs/tutorials/T1_setup.md` and
  `docs/tutorials/T8_keeping_current.md` now say *needs git and network*. Both `--source` help strings say what
  `github` does — it clones the repository for the run.
- **Either source now carries the history:** `BOOTSTRAP.md`'s *Updating an existing project* paragraph no longer
  prefers `--source=local`. It says both sources carry the history that recognizes a file as merely behind, keeps the
  sentence about a shallow clone or a downloaded tarball, and points that sentence at the refusal that now names it
  rather than reporting it against the reader's files.
- **`README.md`'s Quick Start note** keeps its wording and gains one clause: where to run `bin/sync` from, and that
  either source recognizes an unedited file that is merely behind, so it is updated rather than refused.
- **`BOOTSTRAP.md` troubleshooting** gains the second cause a reader can now meet — a shallow or history-less source —
  beside the *locally modified* entry that was the only one there.
- **Scope:** prose and two help strings only; no behaviour changes. `bin/check-links` OK, 107 links.

### 2026-09-22 · [ad hoc] `bin/sync`: a source without its history is named as the refusal's cause, not the project's files

- **The defect:** `bin/sync` refuses a tracked file that matches neither the canonical version nor any version in
  the source's history, and says it has *local modifications*. That is earned only when the history is complete. From
  a shallow clone or a downloaded tree it said the same of files that were merely behind: a project installed from
  `008d656` and never edited had 9 files refused as local modifications, exit 2, by `bin/sync --source=local
  --dry-run` from a depth-1 clone of this branch and from a `git archive` of it. `starter-kit/BOOTSTRAP.md` already
  says a shallow clone or a tarball loses that history; the refusal did not.
- **The fix:** before refusing, `bin/sync` asks its source what history it has. No `.git`: the refusal says the source
  has no git history and prints the `git clone` command. `git rev-parse --is-shallow-repository` true: it says the
  checkout is shallow and how many commits it holds, and prints `git -C <source> fetch --unshallow`. In both, the
  header says the files *differ from the canonical version*, the `CLAUDE.md` paragraph (which presumes an edit) is
  left out, and the exit stays 2. A source with its full history prints exactly the text it did.
- **The `--source=github` hint:** it printed *"To inspect the drift first:"* over no lines, because its commands would
  have named the clone, which is removed when the run ends. It now prints a clone of the source pinned to the commit
  the run read (`git clone <url> methodology-<sha> && git -C methodology-<sha> checkout -q <sha>`) and one `diff` per
  file against it.
- **Tests, written red first:** Test 29 takes Test 26's fixture three ways — a depth-1 and a depth-2 clone over
  `file://`, and a `git archive` of it — with a project holding the fixture's oldest version, merely behind. Each
  source exits 2, names its cause (with the commit count, 1 and 3), writes nothing, and never says *local
  modifications*; the shallow refusal prints the `fetch --unshallow` command and the tarball's the clone command. For
  `--source=github` the test runs the printed hint after the run, from an empty directory: the clone succeeds and
  `diff` exits 1 on the edit. The control: a full-history source upgrades the same file. Test 7 now also asserts
  that a full-history source still says *local modifications*. On the unfixed script 9 of the 55 checks in Tests 7
  and 26–29 fail, all of them new; the controls pass.
- **Mutants, run:** thirteen — each cause's detection disabled, the cause ignored, each header's wording swapped, the
  github hint's diff aimed at the removed clone, its pin wrong, the hint given the local form or dropped, the
  `fetch --unshallow` path dropped, the commit count hard-coded, its plural forced, and the clone command dropped.
  All thirteen fail at least one check; unmutated, 55 / 0.
- **Live (one run each):** from the `008d656` project, the depth-1 clone and the tarball each refused its 9 files
  with its own cause, exit 2. Against `https://github.com/KJ5HST/methodology.git`, a project with one edited file:
  exit 2 with the full-history text, and the printed hint, run by hand, cloned `6b29d3d` and `diff` showed the edit.
- **Not changed here:** `bin/status` from a history-less source still reads a merely-behind file as *locally
  modified*; the `--help` text and the documents.

### 2026-09-21 · [ad hoc] `bin/sync` and `bin/status`: `--source=github` clones the repository, so a file that is merely behind is recognized

- **The defect:** `--source=github` read each distributed file's contents through the GitHub API and nothing else,
  then classified the project's copy against an empty history. A file that was merely behind matched no known
  version, so `bin/sync` refused it as a *local modification* (exit 2) and `bin/status` read it as *locally
  modified*: the one case an update exists for. On a project installed from `008d656` and never edited, updated
  toward `6b29d3d`, `bin/sync --source=github --dry-run` refused 9 files, exit 2, in 12.3 s (one run). The history
  walk for this source was deferred when the full distribution was added (issue #32), with `--source=local` kept as
  the supported update path.
- **The fix:** `--source=github` makes a full clone of `https://github.com/KJ5HST/methodology.git` into a temporary
  directory, or of `METHODOLOGY_SOURCE_URL` when it is set (anything `git clone` accepts), and runs exactly the
  `--source=local` code over the clone: the same reads, the same full-history walk, the same `git describe`. The
  directory is removed when the run ends, dry run or not. Both scripts, one mechanism. The `gh` calls are gone, so a
  public repository needs neither the GitHub CLI nor authentication; a private mirror uses git's own credentials.
- **What a user sees change:** the source line names the URL cloned (`source:  github (https://…)`), and `version:`
  is the clone's `git describe` (`v3.7-68-g6b29d3d`) rather than `github:<sha>`. A distributed file the source lacks
  (this checkout's manifest is ahead of it) is listed with every other such file before anything is written, exit 1,
  in both scripts; `bin/sync` used to stop at the first one with a `gh auth login` hint.
- **Tests, written red first:** Test 27 serves Test 26's fixture (both merge-hiding shapes) as a `file://` bare
  repository through `METHODOLOGY_SOURCE_URL`, and checks every version the way Test 26 does, through
  `--source=github`: 6 status rows and 5 sync outcomes, a real local edit still refused, plus the source and
  version lines, a dry run that writes nothing, and no temporary clone left behind. Test 28 removes one distributed
  file from the fixture: both scripts name it, exit 1, and nothing is written. On the unfixed scripts the two tests
  fail 16 of their 20 checks; the 4 that pass are the controls. Test 26's fixture moved into a function the two
  share, with its assertions unchanged. Test 9's guard is now the URL's reachability (`git ls-remote`, 30 s timeout)
  instead of `gh auth status`.
- **Mutants, run:** nine — a `--depth 1` clone in each script, the inventory skipped in each, the URL override
  ignored, the temporary clone left behind by each, and the github route given no history in each. Tests 26–28
  fail on all nine and pass unmutated (31 / 0). The two `--depth 1` mutants passed until the fixture was served as
  `file://` rather than a plain path: git ignores `--depth` when it clones a plain path.
- **Live, against this repository (one run):** the same project from `008d656`: `bin/sync --source=github --dry-run`
  exit 0, 10 files would be written, `version: v3.7-68-g6b29d3d`, 1.6 s; `bin/status --source=github` 9 rows
  *N versions behind*, 0 *locally modified*, 1.9 s.
- **Not changed here:** the refusal text for a source that has no history of its own (a shallow clone, a downloaded
  tarball), the *"To inspect the drift first:"* header this route prints over no lines, the `--help` text, and the
  documents that describe the route.

### 2026-09-21 · [ad hoc] `bin/status` and `bin/sync`: the history walks look up blobs in one batched call

- **Why:** the full-history walk the entry below adds visits more than twice the commits the default walk did, and
  both tools ran one `git ls-tree` subprocess per commit. Against six adopter projects, `bin/status` went from 3.0 s
  to 10.1 s and one project's `bin/sync --dry-run` from 2.9 s to 7.5 s.
- **The change:** one `git cat-file --batch-check` per walk, fed `<commit>:<path>` lines: `bin/status`'s new
  `blobs_at()`, used by `history_walk()`, and `bin/sync`'s `local_history_blobs()`. A separate commit from the fix, so
  it can be judged, or dropped, on its own.
- **Behaviour-neutral:** on the fork where it was first measured, `bin/status` output over the six projects was
  byte-identical to the fix's (174 rows), and `bin/sync --dry-run` output identical apart from the `version:` line,
  with the same exit codes. Run time after: `bin/status` 4.0 s, that `bin/sync --dry-run` 2.3 s. Test 26 unchanged.

### 2026-09-21 · [ad hoc] `bin/status` and `bin/sync`: a version a merge hid from git's default walk is recognized again

- **The defect:** both tools listed a file's past versions with a plain `git log -- <path>`, which follows only a
  merge's TREESAME parent. A version on the side a merge did not keep was never visited, so an unmodified copy of it
  read *locally modified* and `bin/sync` refused it (exit 2).
- **The fix:** `bin/sync`'s `local_history_blobs()` walks with `--full-history`; it only asks whether a version is
  known. `bin/status` walks twice, sharing a commit → blob cache: the first-parent line (`--first-parent`) and the
  full history. *N versions behind* counts the distinct versions newer than the project's along the first-parent
  line, and falls back to the full walk for a version that only ever existed on a merged branch.
- **Test 26, written red first:** a methodology repository with both hiding shapes on one tracked file (a merge that
  takes a side branch's content, and one that keeps main's), at fixed commit dates. It proves the shapes (the walks
  visit 4 / 8 / 4 commits), then pins 6 status rows and 3 sync outcomes, including a real local edit that must still
  be refused.
- **Provenance:** made and measured first on a fork of this repository, where running the fixed tools against six
  adopter projects turned 8 misread files from *locally modified* into *N versions behind* and left the 3 genuine
  local edits refused. Carried here with the test renumbered and three comments reworded; the logic is unchanged.

### 2026-09-21 · [ad hoc] `.quality-gates.json`: the same two floors tightened again, to what this branch now measures

- **Action:** `tests-sh-passed` 141 → 142 and `context-budget-unit-tests` 129 → 140. These are the values
  `python3 starter-kit/quality_ratchet.py --run` measures after the two `context_budget.py` changes recorded
  between this entry and the first tightening below, which add 11 unit tests and 1 `bin/tests.sh` row. No other
  floor moves: every other gate measures exactly its threshold. This is a separate commit from the first
  tightening, so either can be dropped alone.
- **Measured** in a fresh clone of the branch before this commit: `10/10 pass · 0 fail · 0 unmeasured`, with
  `tests-sh-passed` 142 and `context-budget-unit-tests` 140.

### 2026-09-21 · [ad hoc] `context_budget.py`: a row over a ceiling stays `over` when a structure pattern also fails

- **Action:** `measure_file()` in `starter-kit/context_budget.py` gave a row the status of whichever check wrote
  last. A ceiling check (bytes, lines, line length, tokens) sets `over`; a structure pattern that matched fewer
  records than its `expect_min` then set `instrument-failed` unconditionally, overwriting it. `render()` ranks
  `instrument-failed` just below `over`, so the headline read `INSTRUMENT-FAILED`, the row read
  `instrument-failed`, and when the growth run fired the advisory said *"Nothing is over a ceiling yet"* directly
  above the finding that said the ceiling was exceeded. That write was the only one in `measure_file()` that could
  lower a status. It now leaves an `over` row as it is, so a check can raise a row's status and never lower it.
  Both findings still print, and the exit code is 2 either way. This is the case the growth-run entry two below
  lists under *Not changed here*.
- **A comment corrected:** the comment above `main()`'s exit said the tool's ordering *"already ranks"* an
  instrument failure *"above `over`"*; `render()`'s ranking puts it just below. The comment now says what the code
  does: a config defect exits 2 exactly as `over` does.
- **Tests, RED first against the unchanged tool** (blob `f75482c2`): 4 in a new `TestStatusPrecedence` class in
  `tools/test_context_budget.py`. (1) The real `main()` → `render()` path under `--status`, on a file over its byte
  ceiling that also fails a pattern, with the growth run fired: the headline reads `OVER`, both findings print,
  the advisory gives the over-state sentence, and the exit is 2. (2) `--status --json` reports that row as `over`.
  (3) A control: a row that only fails its pattern still reads `instrument-failed`. (4) Raising still works: a
  row past its warn line that fails its pattern reads `instrument-failed`. Tests (1) and (2) fail on the old tool;
  (3) and (4) pass on it by design, and the mutants below are what they catch.
- **Mutants, run rather than predicted,** after the fixed tool passed the same harness: the guard removed, so the
  last writer wins again (tests 1 and 2); the guard made to never set the status (tests 3 and 4); raising from
  `warn` blocked (test 4 alone); raising from `ok` blocked (test 3 alone). `--selftest` catches the two that stop
  a pattern-only row reading `instrument-failed`, and neither of the others.
- **Counts:** `tools/test_context_budget.py` 136 → 140 tests, `--selftest` 52 checks unchanged, `bin/tests.sh`
  142 passed, 0 failed (unchanged: no shell row added). No gate threshold changes in this commit.

### 2026-09-21 · [ad hoc] `context_budget.py`: `--check` is a second name for `--status`, and a refused argument is told what it most likely meant

- **Action:** the refusal added below (exit 3 and the usage text) said what was wrong and not what to do instead.
  Searched in this repository and seven adopter projects, the arguments typed after this tool's name that it
  did not define were two: `--status`, which now exists, and `--check`. `--check` is the ledger trimmer's name for its report-only run
  (`methodology_trim.py --check`: *"evaluate the trigger and report; never writes"*), and one adopter project's
  session notes tell the next session to *"Re-measure (`python3 context_budget.py --check`) before writing
  more"*. Now:
  - `--check`, with or without `--json`, is accepted and is the same run as `--status`: the same ledger, the
    same exit code, and no history row. The usage text gains a `--check` line.
  - Every other refused argument gets a line of its own, `unknown argument: <arg>`, followed by what it most
    likely meant, taken from what the sibling tools use the same flag for:
    - `--force` (the trimmer's and the dashboard's override): *"there is deliberately no --force: to permit
      growth, raise that file's ceiling in .context-budget.json"*;
    - `--dry-run` (the dashboard's preview): *"did you mean --status? It measures and writes nothing"*;
    - `--run` and `--write` (the ratchet's and the trimmer's real run): *"run with no argument to measure and
      record"*;
    - a misspelling of an accepted argument: *"did you mean <nearest>?"*, from `difflib.get_close_matches`
      with a cutoff of 0.75;
    - anything else: nothing more.
  - Unchanged: exit 3, nothing read or written, and the usage text after the refusal.
- **The cutoff was measured, not chosen.** At `difflib`'s default of 0.6, `--version` is offered `--json`, which
  is not what anyone typing it meant; at 0.75 it is offered nothing. Both cutoffs send `--stauts`, `status`,
  `--jsn`, `--selftset`, `--calibrat`, `--precomit`, `--chek` and `--hlep` to the intended argument, and neither
  offers anything for `--zzz`, `--verbose` or `-v`. The one loss at 0.75: `install` is no longer offered
  `install-hook`.
- **Where the hint table lives.** It names `--force`, so it sits below the selftest, which refuses that string
  anywhere above its own definition, and hints are looked up by key rather than by testing the argument list for
  a flag, the form `bin/tests.sh` and the unit tests grep for.
- **Tests, RED first against the unchanged tool** (blob `dd4803bf`): 7 new in `TestCommandLine` in
  `tools/test_context_budget.py`, and its frozen accepted set gains `--check`. Six fail on the old tool: the
  `--check` test, the `--force`, preview, misspelling and one-line-each hint tests, and the frozen set. Two pass on
  it by design, because the old tool never suggested anything: `--zzz` and `--version` are offered nothing. The
  mutants below are what those two catch. One row in `bin/tests.sh`: `--check` on the seed config exits as
  `--status` does and writes nothing. It fails on the old tool (exit 3 against 1).
- **Mutants, run rather than predicted,** after the fixed tool passed the same harness: `--check` dropped from
  the write guard (the `--check` test and the shell row); the hint table emptied (the `--force`, preview and
  one-line-each tests); the cutoff at 0.6 (the `--version` test); the suggestion printed unconditionally (the
  `--zzz`, `--version` and one-line-each tests); the hint table moved above the selftest (`--selftest` exits 2 on
  *"--force is not offered"*). `--selftest` catches only the last.
- **Counts:** `tools/test_context_budget.py` 129 → 136 tests, `--selftest` 52 checks unchanged, `bin/tests.sh`
  141 → 142 passed, 0 failed. `VERSION` stays 1.3.0, which this pull request already sets. No gate threshold
  changes in this commit.

### 2026-09-21 · [ad hoc] `.quality-gates.json`: two floors tightened to what this branch measures

- **Action:** `tests-sh-passed` 139 → 141 and `context-budget-unit-tests` 118 → 129. These are the values
  `python3 starter-kit/quality_ratchet.py --run` measures after the two `context_budget.py` changes below,
  which add 11 unit tests and 2 `bin/tests.sh` rows. The manifest says the next tightening is owed whenever a
  measured value rises, and a tightening passes the pre-commit ratchet without approval. No other floor
  moves: every other gate measures exactly its threshold.
- **Measured** in a fresh clone of the branch before this commit: `10/10 pass · 0 fail · 0 unmeasured`, with
  `tests-sh-passed` 141 and `context-budget-unit-tests` 129.

### 2026-09-21 · [ad hoc] `context_budget.py`: the growth-run advisory no longer says nothing is over a ceiling when something is

- **Action:** when the growth run fires, `render()` in `starter-kit/context_budget.py` prints an advisory
  whose second sentence was a literal: *"Nothing is over a ceiling yet — that is the point. Ceilings fire
  late."* It printed in every such run, including runs whose headline read `context budget OVER` above
  a table with rows marked `over`. The sentence is now chosen by `worst`, the variable the headline
  prints, so the two cannot disagree. When nothing is over, the sentence is unchanged, word for word.
  When something is, it reads *"A ceiling has fired as well — see the rows marked over."* No other output
  changes.
- **Tests, RED first against the unchanged tool** (blob `131158cb`): 3 in a new `TestGrowthRunAdvisory`
  class in `tools/test_context_budget.py`. (1) A matrix over every status `render()` ranks (`ok`,
  `unmeasured`, `warn`, `instrument-failed`, `over`), with and without the growth run. It calls
  `render()` in process, checks each cell's headline and advisory first, and asserts the advisory never
  says *"Nothing is over a ceiling"* when the headline says `OVER`. (2) The presence control: every
  status below `over` still prints the original sentence, so deleting it would not pass (1). (3) The
  real `main()` → `render()` path on a project over its resident total, with a growth-run limit of 2 and a
  seeded history. Tests (1) and (3) fail on the old tool, and (2) passes on it by design.
- **Mutants, run rather than predicted,** after the fixed tool passed the same harness: the literal
  restored (tests 1 and 3 fail); the sentence deleted in both states (all 3); the condition inverted (all
  3); the condition widened to `instrument-failed` (test 2). `--selftest` catches none of them, since it
  does not cover the advisory.
- **Not changed here:** a row can be over a ceiling and still read `instrument-failed`. `measure_file()`
  gives a row the status of whichever check wrote last, so a failed structure pattern overwrites a byte
  ceiling's `over`. The headline then reads `INSTRUMENT-FAILED`, and the advisory keeps the original
  sentence above a finding that says the ceiling was exceeded. That is a status-precedence question in
  `measure_file()`, not in the advisory.
- **Counts:** `tools/test_context_budget.py` 126 → 129 tests, `--selftest` 52 checks unchanged, `bin/tests.sh`
  141 passed, 0 failed (unchanged: no shell row added). No gate threshold changes in this commit.

### 2026-09-21 · [ad hoc] `context_budget.py --status` now exists and writes nothing; an unknown argument is refused

- **Action:** `starter-kit/context_budget.py` had no `--status` command and ignored any argument it did
  not recognise, so `--status`, `--check`, `--force` and a typo each ran the default measurement. That run
  appends a row to `.context-budget-history.jsonl` whenever a size changed. `--status` is nonetheless
  cited as a verification step in this repository's own ledgers, and the PR #82 review thread named its
  write as what stands in the way of a `context-budget` gate. Now:
  - `--status`, with or without `--json`, is the default run without its one write: the same ledger, the
    same exit code, and no history row.
  - An argument outside a fixed list (`install-hook`, `--precommit`, `--calibrate`, `--selftest`, `--json`,
    `--status`; `-h`/`--help` still win) exits **3**, the tool's documented usage code. It prints
    `unknown argument: …` and the usage text, and reads and writes nothing. The usage text's *"There is
    deliberately no --force"* is now observable: `--force` is refused rather than silently measured.
  - `VERSION` 1.2.0 → 1.3.0. The usage text gains a `--status` line, and the default's *"append one
    history line"* now says *"when a size changed"*, which is what `append_history` does.
- **Where the list lives, and a guard that narrowed on the way.** The list sits above `def selftest`
  because the selftest's escape-hatch check (the string `--force` must not appear in the source above
  that function) is the only existing guard that can read it; `main()` is below it. While the list was
  being written, a comment above it named that function's definition. The check splits the source on the
  first mention, so it moved up, and `--force` added to the list then passed the selftest. A new test
  pins the split point to the function itself.
- **Tests, RED first against the unchanged tool** (blob `b1111d92`): 8 in a new `TestCommandLine` class in
  `tools/test_context_budget.py`. Six fail on the old tool. Two are controls that pass on it by design: the
  default run still writes, and `--help` still wins over an unknown argument. Two rows in `bin/tests.sh`'s
  budget block, in a `mktemp` project with the seed config: `--status` leaves `git status --porcelain
  --ignored` empty, and `--zzz` exits 3 and changes nothing. The same project's default run comes last, as
  the presence control: the fixture does get written to. Both rows fail on the old tool.
- **Mutants, run rather than predicted:** the append made unconditional again (3 unit tests and 1 row
  fail); the rejection removed (2 and 1); `--force` added to the list (3 unit tests, and the selftest,
  which now sees it); a comment naming the selftest's definition above the list, plus `--force` (3 unit
  tests; the selftest does not see it). The two `"--force" in args` greps, in `bin/tests.sh` and
  `tools/test_context_budget.py`, catch neither `--force` mutant, since they match that expression only.
- **Counts:** `tools/test_context_budget.py` 118 → 126 tests, `--selftest` 52 checks unchanged, `bin/tests.sh`
  139 → 141 passed, 0 failed. No gate threshold changes in this commit.

### 2026-09-20 · [ad hoc] The ledger gate stopped running after any stopped rebase — the marker git leaves behind, dropped

- **Action:** `.githooks/pre-commit` skipped replayed commits by testing five markers under the git
  dir. One of them, `REBASE_HEAD`, is **left behind by git** when a rebase that *stopped* — a
  conflict, or `-i` parked at `edit` — runs to completion. From that moment the hook exited 0 on
  every commit in that clone. The marker loop runs **before** both gates the hook chains, so the
  casualty was not only the failure-mode-#27 ledger gate but `quality_ratchet.py --precommit`,
  whose whole job is refusing a loosened threshold. Both then read green because neither ran.
- **The shape was chosen from a measurement, not from plausibility.** Every operation in the marker
  list was run to completion on git 2.50.1 and its markers observed at each stage. Two facts decided
  it: `REBASE_HEAD` is the **only** marker that survives its operation (the other four are removed
  when the operation ends or is aborted, so none needs the same treatment), and it is **redundant** —
  every rebase in progress carries `rebase-merge` or `rebase-apply` alongside it, so dropping it
  costs no in-progress coverage. A third measured fact explains how it goes unnoticed: a **clean**
  rebase leaks nothing, so only a stopped rebase arms the trap.
- **A hook is the one gate nothing else watches, and it fails open** — its failure mode is silence,
  not red. So the fix ships with `.githooks/pre-commit --selftest` (10 checks, on the
  `.githooks/commit-msg --selftest` precedent) and a `pre-commit-selftest` gate in
  `.quality-gates.json`, modelled on the existing `commit-msg-selftest` entry. Adding a gate always
  passes the ratchet; no threshold moved.
- **Evidence:** RED-first — the same ten checks against the unfixed marker list go red on exactly
  one, green on the other nine, so the test isolates the defect rather than being vacuously red;
  0 red after the fix. The selftest builds each probe repo with `git init --template=`, so a user's
  `init.templateDir` cannot install *its* hooks into the probe and answer for the hook under test,
  and it asserts each fixture actually built (a probe against a repo that failed to build answers
  about nothing, in green). `bin/tests.sh` unchanged at 139 passed / 0 failed;
  `quality_ratchet.py --run` 11/11 with the new gate.

### 2026-09-16 · [ad hoc] Parallel-sessions plan — making fan-out to concurrent writing sessions clean, not just safe

- **Action:** planning session S24 on branch `docs/parallel-sessions-plan`. The operator asked whether the
  quality-ratchet work (PR #82) made multi-agent fan-out workable; the Phase 0 answer was *safe but not
  clean* — `ITERATIVE_METHODOLOGY.md` §Mechanical Gates binds every actor's output, but two writing
  sessions still collide on `CHANGELOG.md`/`HANDOFFS.md` (prepend-only, one anchor, co-staging hook forces
  every commit onto them — S21 hit it with two sequences), on serial `S<N>` identity, on the absent
  merge-session receipt (the open "11 reconciled receipts" ruling), and on Test 9's `--source=github`
  coupling to `main`. Deliverable: `docs/planning/parallel-sessions-plan.md` + a PR for review, nothing
  implemented (S13's shape). Results appended at close-out.
- **The plan, committed:** `docs/planning/parallel-sessions-plan.md` — 468 lines; §1 decomposes the operator's
  own records into six mechanisms (two-writers-in-one-tree, the return-content fan-out that worked, the S21
  double-ledger conflict, the undischargeable "11 receipts", Test 9's `main` coupling, the worktree-blind
  calibrate); §3 the finding (*one closer per tree*; two shapes by who closes out); §4 fifteen decisions D1–D15
  plus an alternatives table (changelog fragments considered and deferred); §6 six phases, one per session;
  §7 six honest ceilings; §8 twelve operator decisions; §9 the evidence commands, all re-run before commit.
- **PR opened (non-commit action):** [PR #83](https://github.com/KJ5HST/methodology/pull/83) from
  `docs/parallel-sessions-plan` at `903d724`, read back from the API (OPEN, +492/−0, 3 files); its body carries
  the summary and asks the operator to answer §8 there — that answer is the plan's Phase 0. **Not merged.**
- **Gate run at `903d724`:** `quality_ratchet: 8/10 pass · 2 fail · 0 unmeasured · results bcbd7f39383a ·
  manifest 97a7aab85b9a`. The two fails are one **environmental** failure — `tests-sh-passed` 138 /
  `tests-sh-failed` 1 from `tools/test_context_budget.py` `TestFitGateEndToEnd::test_an_admitting_floor_prints_the_constant`:
  this machine now holds exactly 4 transcripts for this path (calibrate()'s fit minimum; this session's is the
  4th), so the fit runs on 4 points and is refused for a negative slope (R² 0.049), a refusal the test's `setUp`
  does not skip on (it skips only on "not enough" — S16's fix for the sibling case S19 reported). Tool and test
  are byte-identical to `main @ 6b29d3d`; not loosened; the one-file fix is the next session's first small task.
- Session S24: claim `3c244aa` + plan `903d724` + the close-out commit (receipt complete, cites the run). Every
  commit ran the ledger co-staging hook clean — no `--no-verify`.

### 2026-09-16 · [ad hoc] PR #82 merged — post-merge verification on main and the first tightening

- **Action:** the operator merged [PR #82](https://github.com/KJ5HST/methodology/pull/82) (quality ratchet,
  plan #81 Phases 1–4 + the review-response fixes) at merge commit `64f23bf` (2026-09-16T18:05:47Z; parents
  `0fd003a` + `5c9d3b4`). Session S23 verifies `main` and takes the tightening the S22 receipt records as
  owed: `tests-sh-failed` 1 → 0 and `tests-sh-passed` 138 → 139, Test 9 turning green on `main`. Local
  `feat/quality-ratchet` deleted (merged; the remote branch was already gone). Results appended at close-out.
- **Verified on `main` at `64f23bf`:** `bin/tests.sh` **139/0** — Test 9 green for the first time since the
  branch was cut; dashboard unit 226 OK, budget 118 OK (2 skipped), trimmer 123 OK (2 skipped), ratchet 45
  OK, `check-links` OK, `check-learnings` OK, `check-handoff --all` OK, twins byte-identical at 2.11.1,
  `context_budget.py --status` exit 0, `quality_ratchet.py --selftest` OK (22), `commit-msg --selftest` OK.
- **The first tightening, discharged:** `tests-sh-failed` `max 1 → 0`, `tests-sh-passed` `min 138 → 139`;
  the hook's verdict on the staged edit exit 0 (two tightenings). `--run` at the tightened manifest:
  **10/10 pass · 0 fail · 0 unmeasured · results `6542e640a956` · manifest `97a7aab85b9a`** (2 m 50 s).
  `_first_tightening_owed` in the manifest now records the discharge and the standing rule: raise floors
  when a measurement rises, never lower them.
- Session S23: claim `b4c04af` + tightening `fb81c4b` + the close-out commit (receipt complete, cites the run).
  The ledger hook refused the first close-out attempt — `CHANGELOG.md` was not co-staged — as designed.

### 2026-09-16 · [ad hoc] PR #82 review-response fixes — the six corrections and the review's accepted findings, one checkpoint per fix

- **Action:** the fix set the maintainer's confirmation comment promised, built on `feat/quality-ratchet`
  after merging `main` (`b2aea23`, ledger union). Operator-directed bundling across subsystems (the S8
  shape), one independently verified checkpoint commit per fix. Session S22: merge `b2aea23`, claim `563a6e2`,
  seven checkpoints `b742344`..`b5dda4e`, the close-out commit. PR head `b5dda4e` + close-out; NOT merged.
- Merge `b2aea23`: `origin/main` (S21) into the branch; `CHANGELOG.md` and `HANDOFFS.md` resolved as a union.
- **F1 — the deletion hole** (review 2a + 4, bullets 1 and 4): `quality_ratchet.py` 1.0.0 → 1.1.0. `find_root`
  falls back to the git toplevel, so `--precommit` can judge a commit that removes the manifest instead of
  exiting 3 "refuses to invent thresholds" (the exit that, in the hook `install-hook` writes, refused every
  later commit). The comparison base is now the **newest parseable committed manifest that declares a
  gate** — not HEAD's copy — so removing the manifest is refused as the loosest loosening, re-adding it
  lower after a bypassed removal is still refused against the removed version, and a corrupted or emptied
  HEAD copy is skipped; a branch that removed its manifest and left it removed is not locked. The
  empty-gates rule was found by the test, not the review: the first cut used "newest parseable" and a
  bypassed `{"gates": []}` became a base that let a lower re-declaration through. `install-hook` writes
  the path of the copy that is running (`starter-kit/quality_ratchet.py` here, root for adopters).
  `.githooks/pre-commit` fires when the worktree OR HEAD has a manifest. Tests: unit 33 → 43 (8 RED
  first, 2 controls), selftest 17 → 22, `bin/tests.sh` +4 through real git (one RED on the old tool: the
  lockout) — and the pre-existing `git checkout -- manifest` in that block restored the worktree from a
  still-staged refused edit; now `checkout HEAD --`.
- **F1b** — the F1 base note fired on every ordinary commit ("HEAD has none") because `git log -- manifest`
  names the newest commit that *touched* the file, not HEAD; seen in the F1 checkpoint's own hook output.
  The note now prints only when HEAD's copy is absent, unparseable, or empty. Unit 43 → 44 (RED first).
- **F2 — the dashboard** (review 2a fix 3 + O1, §4 bullets 2–3): `DASHBOARD_VERSION` 2.11.0 → 2.11.1, both
  twins. The history walk runs whenever the manifest *has* a history, not only when the worktree has the
  file — the early return made the deleted-and-never-re-added state report nothing; it now reports
  `manifest deleted in <sha>` with every gate that went with it. A deleted or unparseable version is
  recorded as an empty gate list (flagged), never skipped. Each version is compared to the nearest OLDER
  version that declared a gate — the base `quality_ratchet.py` now uses — so 80 → (deleted) → 1 reads
  as `floor lowered 80 → 1`, not "added". A direction flip is a loosening in its own right; a changed
  `command`/`extract` is a separate LOW advisory, as the bypass message promised. The +2 for a passing
  gate *named* coverage is dropped (`echo 100` earned it, from a gitignored file). Unit 222 → 226 (6 RED
  first, incl. the version pin); fleet delta 0 by construction — no sibling repo has a manifest history.
- **F3 — `tests-sh-failed` at `max 1`** (review 2b): declared now at the branch's measured value (Test 9 by
  construction), so a second failure is caught today; tightens to 0 in the first commit after merge.
  Manifest 9 → 10 gates (the ratchet's own verdict on the staged edit: "1 gate(s) added"). Because two
  gates now read one `bash bin/tests.sh`, `run_gates` memoizes identical commands within a run — the
  suite runs once, two numbers are read from it; a `--run` that took the suite twice is one nobody
  cites (unit 44 → 45, RED first).
- **F4 — the docs** (review 2c, §5, and the unraised merge/rebase skip): `SESSION_RUNNER.md` Phase 0 step 6
  gains the gate-citation check — the newest complete receipt's `quality_ratchet:` line against the results
  file, or a re-run — **paid for by reduction**: the step's HANDOFFS clause no longer restates the note eight
  lines below it, and step 5 loses an aside; measured by the doubled-file Read **18,897.5 → 18,865.5 tokens**
  (53,328 → 53,252 B), 34.5 under the 18,900 ceiling. `SAFEGUARDS.md` ratchet row: removing the manifest is
  refused; merge/rebase commits skip the hook and the dashboard's history read is the catch (16,765 → 17,024
  B, 6,029.7 tokens, 70 under 6,100; the pair 24,894.5 = 99.58 % of the cap). `ITERATIVE_METHODOLOGY.md`
  §Mechanical Gates states the enforcement point beside the "every actor" claim (opt-in hook, on-record
  bypass, merge skip; CI is what makes "every" literal). `BOOTSTRAP.md` Step 10: the manifest itself is
  ratcheted; the two limits stated plainly.
- **F5 — the budget config** (review §3 + O2): both read-set densities re-measured on the blobs they now
  describe — runner **2.8248 → 2.8227** on `2a3e410d` (53,252 B, 18,865.5 tokens), SAFEGUARDS **2.8191 →
  2.8234** on `933816b4` (17,024 B, 6,029.7) — each entry naming its blob and the rule: re-measure when
  `git rev-parse HEAD:<path>` changes; `measured_bytes` at 25 % drift is not a substitute. `CLAUDE.md`
  gains a **token ceiling, 23,483 at its measured 2.519 B/token** (blob `1244e95b`), the byte pin kept as
  the coarse backstop — the S20 reduction was −15 B and **+62 tokens**, which a byte pin cannot see. The
  tool now reports 23,482 / 18,865 / 6,029 against 23,483 / 18,900 / 6,100, within one token of the
  measurements. Not built: a `measured_blob` key the tool checks itself (follow-up).
- **F6 — tightened to measured** (the ratchet doing its job): `tests-sh-passed` 134 → 138, `dashboard-unit-tests`
  222 → 226, `ratchet-unit-tests` 33 → 45 — three tightenings, no approval needed, the hook's verdict on the
  staged edit exit 0. `--run`: **10/10 pass · 0 fail · 0 unmeasured · results `efccbc7f2195` · manifest
  `08423c179055`**, 2 m 46 s with `bin/tests.sh` executed once for its two gates.
- **Non-commit actions:** branch pushed at `b5dda4e`; PR #82 body replaced — rmsharp's §1 rewording as the
  description (facts updated: base = newest committed manifest with gates, ten gates, 2.11.1, the two
  limits), the decisions in plain words, a "Review findings and what changed" section (read back: 9,876
  chars). **Learning #16** appended (1,137 B; 15 rows, `#14` reserved). `git merge-tree --write-tree
  --name-only origin/main feat/quality-ratchet` **exit 0 at this close-out** — clean, by exit code (S21's
  lesson). Not built, recorded: `measured_blob` self-check in the budget tool; the `context-budget` gate
  (history-file decision first); CI.

### 2026-09-16 · [ad hoc] Posted the maintainer's confirmation of the PR #82 review to the PR (non-commit action)

- **Action:** one maintainer comment on [PR #82](https://github.com/KJ5HST/methodology/pull/82) answering
  rmsharp's review comment of 2026-09-16: the review **reproduces** (its own repro script 7/7 sections, the
  four token figures by the doubled-file Read, the `--run` hash `74c773523dab` on a third tree; the §1
  rewording accurate on every checkable claim) — with six corrections from the internal check (oversight
  venue, 2026-09-16): fix 1 alone *refuses* a `git rm` via `find_root`'s exit 3, so `find_root` is the
  prerequisite; the dashboard fix never runs while the manifest stays deleted; "one new test offsets one
  failure" is false at the unit-suite level (one `tests.sh` check each); the receipt-vs-results comparison is
  specified in `starter-kit/HANDOFFS.md` §Citing the gate run, absent only from the runner's Phase 0
  procedure; the stale-density finding applies to `SAFEGUARDS.md` too; the proposed `context-budget` gate
  writes an un-ignored history file. Two items the review did not raise: merge/rebase commits skip the
  ratchet; an unparseable HEAD manifest is the delete/re-add hole with one `--no-verify`. Fixes are the
  next session's work, in the corrected order. Session S21: claim `07d166e` + the close-out commit.
  Comment: <https://github.com/KJ5HST/methodology/pull/82#issuecomment-5701463025> (read back via the API).
  S21's ledger prepends conflict with the branch's S20 prepends in this file and `HANDOFFS.md` (`git merge-tree`
  exit 1; clean against `8b4dc2c`) — resolve as a union on the PR branch before merge, the S15 precedent.

### 2026-09-15 · [ad hoc] Quality ratchet — the plan's Phases 1–4 built as one pre-declared vertical slice (PR opened, not merged)

- **Action:** implement [`docs/planning/quality-ratchet-plan.md`](../../docs/planning/quality-ratchet-plan.md)
  (PR #81, the plan; D1–D10) through its four buildable layers on branch `feat/quality-ratchet`, one
  checkpoint commit per layer with the full matrix at each boundary, and open a PR for review. Phases 5
  (adopter dogfood) and 6 (release) are separate sessions by the plan's own text. Session S20. **Checkpoints:**
  claim `5cd300e` · P0 `008d656` · P1 `628d218` · P2a `9d34485` · P2b `727d9ff` · P2c `d433739` · P3 `cca7941` ·
  P4a `bae6b05` · P4b `58babe6` · P4c `04044f1` · self-review `b4226d3` + `d24fb2c` · close-out (this commit).
  **Gate run cited in the receipt:** `quality_ratchet: 9/9 pass · results 74c773523dab · manifest 2424c429b2c6`.
  **§8 decisions** taken at the plan's recommendations (1 yes; 2 gitignored; 3 amend #17; 4 empty seed; 5 separate
  file; 7 separate plan) and listed in the PR body for the operator to reverse. **PR opened:**
  [#82](https://github.com/KJ5HST/methodology/pull/82) (a non-commit action; the branch pushed as `e13958d`).
- **P0 — preconditions (checkpoint 1).** `tools/test_context_budget.py`: `TestFitGateEndToEnd` skipped only
  when NO transcript existed, but `calibrate()` refuses to fit below 4 usable sessions — on this machine (2
  transcripts for the repo path) both tests ran and failed against *"not enough to fit"*, so `bin/tests.sh`
  read 115/1 on `main` (S19 gotcha 1); the class now asks the tool (a probe at an impossible floor) and skips
  on its "not enough". New `TestThisRepoReadSetPartition` (**G1** of the #80 re-review): the repo's own
  `.context-budget.json` per-file token ceilings in a whole-read class must sum to ≤ `read_cap_tokens` —
  RED first at 27,800 with the 22,000 mutant, OK at 25,000. And the read-set partition is **re-split
  19,200 + 5,800 → 18,900 + 6,100**: `SAFEGUARDS.md` was pinned at its exact size (5,800/5,800), which would
  have refused the one Blast Radius row D3 adds; 300 tokens move from the runner's margin. `--status` OK,
  `config_defects []`, budget suite 116 → **118** OK.
- **P1 — prose (checkpoint 2).** **D3** `starter-kit/SAFEGUARDS.md` Blast Radius gains one row: *never loosen a
  declared quality threshold to make a change pass — loosening requires plan mode approval; tightening never
  does*. **D4** `ITERATIVE_METHODOLOGY.md` gains §**Mechanical Gates Bind Every Actor** beside §Matching
  Reasoning Effort to Stakes — enforce on the artifact, not the actor; four consequences (never re-done by
  judgment or waived by tier; judgment reserved for what no gate expresses, before and after implementation;
  checks never pass by default or timeout; thresholds only tighten); cites the capability-tiered paragraph
  rather than duplicating it; states the ceiling (a floor without a faithfulness check measures effort).
  No principle, phase, or gate added — "9 principles / 6 phases / 12 quality gates" claims re-grepped, true.
  **D5** `starter-kit/SESSION_RUNNER.md` Phase 3C gains the mechanical branch: *a mechanical learning is a
  gate, not a row* (Learning #12 generalized from "test" to "gate"; the decay term FM #28 names).
  **D8** FM #17 gains one clause (loosening a threshold is erosion in mechanical form; `--no-verify` is a
  recorded bypass, not an exemption) and Degradation Detection gains one row — **FMs 1–28 byte-unchanged,
  count stays 28** (28 table rows re-counted). **Learning #15** appended to `starter-kit/FRAMEWORK_LEARNINGS.md`
  (1,331 B, under the 1,500 B row budget; `#14` stays reserved, callout reworded to "rows continue from
  #15"). **Cost, measured:** the Phase 0 pair is 70,066 B; doubled-file Read reports 49,643 → **24,822
  tokens, 99.3 % of the read cap** (the tool estimates 18,868 + 5,946 = 24,814 — within 8 tokens of the
  measurement); the runner sits 32 tokens under its 18,900 ceiling, so the next runner growth must be paid
  for by a reduction. `bin/check-links` 105 OK; `bin/check-learnings` OK (14 rows, contiguous with #14
  reserved); `bin/tests.sh` 116/0; dashboard unit 211 OK.
- **P2a — the tool (checkpoint 3).** New `starter-kit/quality_ratchet.py` (**D2**; 494 lines, stdlib only, no
  `--force`): `--precommit` refuses a staged `.quality-gates.json` whose thresholds are looser than `HEAD`'s
  (a `min` lowered, a `max` raised, a gate removed, a direction flipped); tightening and adding always pass;
  a changed `command`/`extract` warns (the ratchet holds thresholds, not commands). `--run` executes each
  declared gate (regex `extract` → the number; no `extract` → the exit code), writes a results file
  (`.quality-gates-results.json`, hash-stamped, time-independent hash) and prints a **citable summary line**
  (`quality_ratchet: N/M pass · F fail · U unmeasured · results <sha12> · manifest <sha12>`); a gate with
  no command is **unmeasured, never pass** (exit 1). `--status`, `--selftest` (17 checks, each observed
  failing and passing, incl. the installed hook refusing a loosening through real `git commit`),
  `install-hook` (honours `core.hooksPath`; prints the chain line for a foreign hook). New
  `starter-kit/quality-gates.json` seed (**§8.4 empty**, with the schema and one valid `_example`). New
  canonical-only `tools/test_quality_ratchet.py` — **33 tests** (pure ratchet arithmetic; config defects;
  measurement incl. the index-not-worktree rule and a 127 exit for a missing command; results/status;
  precommit through git; stdlib/no-force/selftest/seed invariants).
- **P2b — distribution (checkpoint 4).** `bin/_manifest.py` **27 → 29** rows (`quality_ratchet.py` TRACKED,
  `.quality-gates.json` SEED). Adding the rows with nothing else changed turned **6 guard tests RED** — the
  F2-generalized installed-file test (by name, and end to end for both files), the checklist
  scored-or-exempt invariant, and the exclusion-matches-manifest cross-reference — exactly the guards
  v3.6/v3.7/#80 built for this moment. Both scanner twins gain the two names in
  `FRAMEWORK_INSTALLED_SOURCE` (in manifest order — the cross-reference is order-sensitive) with their own
  `_FRAMEWORK_FILE_SIGNATURES` entries (the tool's `VERSION` regex + 4 signatures; the seed's `_example`
  keys), so a 494-LOC install cannot flip a document project to `code` (PR #71's lesson, measured by the
  real-file test); `CHECKLIST_EXEMPT` records why neither is scored. Twins byte-identical; 211 OK;
  `bin/sync` into a scratch tree installs both, `bin/status` reports `tracked current` / `seed present`;
  `bin/tests.sh` 115/1 — **Test 9 by construction** (`--source=github` reads `main`, which lacks the new
  starter-kit file until merge; the #80 shape).
- **P2c — install path and shell checks (checkpoint 5).** `bin/tests.sh` **116 → 128** checks: the unit suite
  wired in beside the budget suite, plus a `quality_ratchet.py` block that syncs a scratch adopter tree,
  declares one gate, installs the hook, and proves through real `git commit` that a loosened threshold is
  refused, `--no-verify` bypasses it, a tightening passes, removing the gate is refused, and a re-sync
  leaves the adopter's manifest alone — **RED first**: with `compare()` neutralized, the loosening
  committed. `starter-kit/BOOTSTRAP.md` Step 10 retitled *(Optional) → (Recommended)* and gains the
  ratchet paragraph (start where you are; chain after the ledger hook with one line; the results file and
  the receipt citation) plus a tool-agnostic per-stack table (Python/Node/Rust/JVM/Docs — the methodology
  ships the ratchet, not the ruler). `.gitignore` gains `.quality-gates-results.json` (**§8.2**: gitignored
  by default, with the reason). `bin/check-links` 105 → **107** (both new adopter-layout links resolve).
- **P3 — dashboard (checkpoint 6), `DASHBOARD_VERSION` 2.10.7 → 2.11.0, both twins byte-identical.** New
  `collect_gate_metrics` (**D6**): reads `.quality-gates.json` (declared count), the results file where it
  exists (pass/fail/unmeasured, a `manifest`-hash staleness check, a passing gate named *coverage*), and a
  **git-only** loosening history (`git log -- .quality-gates.json`, capped at 50, each pair diffed for a
  lowered floor / raised ceiling / removed gate — the scanner never executes a project command, and a test
  proves it with a `touch`-marker gate). Advisory risks: *N declared, never run here* (medium); *results
  predate the manifest* (low); *K of N measured outside their threshold: names* (high); *unmeasured (no
  command)* (low); *threshold `x` floor lowered a → b in `sha` (date) (+k earlier) — thresholds only tighten*
  (medium). `score_health`: a **measured** passing coverage gate earns +2 on top of configured coverage's
  +2, cap unchanged — the first number, not file-existence, the scanner scores; doc-only repos keep their
  render slot. Card: a *Quality Gates* row beside *Coverage Config*. **Silence is deliberate**: no manifest,
  and the **empty seed** every synced adopter receives, produce no risk. 11 new tests
  (`TestQualityGateSignals`), **RED first against the 2.10.7 scanner: 11 ran, 2 failures + 7 errors**; unit
  suite **211 → 222** OK. **Fleet delta: 27 repos re-scanned under 2.10.7 and 2.11.0 — 0 changed class,
  score, or risk set** (none has a manifest). `bin/tests.sh` 127/1 (Test 9 by construction).
- **P4a — workstreams and the honesty citation (checkpoint 7).** `workstreams/DEVELOPMENT_WORKSTREAM.md`: Step 4's
  "what's the current standard?" now has its answer (the declared floors/ceilings in `.quality-gates.json`;
  measure and declare at the current value where none exist) and *Code Health Metrics* is generated by
  `quality_ratchet.py --run`, not hand-filled. `workstreams/AUDIT_WORKSTREAM.md`: anti-pattern **#10 "Findings
  that stay prose"** (list was 1–9) — a mechanical-invariant finding becomes a declared gate. **D9**:
  `starter-kit/HANDOFFS.md` documents the gate-run citation (the `quality_ratchet: N/M pass · …` summary line
  in `runtime_smoke`) and the Phase 0 comparison of the cited counts against the results file, with the
  v3.3-style ceiling (structure at lint, counts at reconcile, truth of nothing a gate does not express);
  `bin/check-handoff` gains the lint — when a manifest beside the ledger declares ≥ 1 gate, the **newest**
  complete receipt must carry the token (newest-only, so receipts written before the manifest are not
  re-judged and `--all` stays green on history). Observed in a scratch ledger: silent with no manifest and
  with the empty seed; FAIL with one gate and no citation (both modes); OK once cited.
- **P4b — this repo dogfoods the ratchet (checkpoint 8).** Root `.quality-gates.json` declares **9 gates at
  their current measured values** — `tests-sh-passed ≥ 134`, the four unit-suite counts (dashboard ≥ 222,
  budget ≥ 118, trimmer ≥ 123, ratchet ≥ 33), and five exit-code gates (`check-links`, `check-learnings`,
  `check-handoff --all --allow-pending`, `commit-msg --selftest`) — with `tests-sh-failed ≤ 0` recorded as the
  **first tightening owed after merge** (Test 9 is red by construction on the branch, and a gate declared
  red teaches bypass). First `--run`: **9/9 pass**. `.githooks/pre-commit` chains `--precommit` before the
  ledger gate — **observed live in this repo**: a staged floor 127 → 100 was refused with the bypass cost
  printed, then reverted. `bin/tests.sh` 128 → **135** checks: the manifest parses with no defects and
  declares gates; the hook chains the ratchet; the D9 lint observed silent (no manifest; empty seed),
  failing (one gate, no citation — both modes) and passing (cited).
- **P4c — completeness sweep (checkpoint 9; Learning #10).** Every site that enumerates the distributed corpus
  now names the ratchet — and, found by the same sweep, the two tools that v3.7/#80 shipped **without ever
  reaching these lists**: `README.md` (§Option A/B copy lists, the repo tree — `starter-kit/` gains
  `methodology_trim.py`, `context_budget.py` + `context-budget.json`, `quality_ratchet.py` +
  `quality-gates.json`; `tools/` gains the three canonical-only unit suites), `CLAUDE.md` (starter-kit and
  tools tables), `docs/tutorials/T1_setup.md` (the expected-result file list and the seeds), and
  `HOW_TO_USE.md`'s Phase 3C line (the mechanical branch). No count claim moved. `bin/check-links` 107 OK.
- **Self-review (checkpoints 10–11), before the PR.** (a) The gate run is now a named close-out step everywhere
  close-out is enumerated (Learning #8): `SESSION_RUNNER.md` 3E (one line — `--run` is the smoke test's
  mechanical half; cite its summary line), `ITERATIVE_METHODOLOGY.md` Phase 6 step 8 (c), `HOW_TO_USE.md` 3E.
  (b) Learning #15's *"26 of 28 failure modes bind by text alone"* put in the past tense — this ratchet is
  what changes it. (c) **Two budget consequences, paid by reduction, not by a raised ceiling** (the rule this
  PR adds): the P4c table rows had pushed `CLAUDE.md` **984 B over its arrival-size pin** (59,168 B — the F3
  class flagged on #80); six existing rows/bullets were tightened and it reads **59,153 B, 15 under**;
  the runner's two new lines were shaved so it sits at 18,878 / 18,900 tokens. Measured pair after the
  trims: doubled Read **49,683 → 24,842 tokens** (99.4 % of the cap; tool estimate 24,824, within 18).
  `context_budget.py --status` OK, exit 0. (The ledger hook refused the CLAUDE.md commit until this line was
  co-staged — the fast path working as designed.)

### 2026-09-15 · [ad hoc] Merged PR #80 — the read-set budgets series (#76–#79)

- **Action:** merge [PR #80](https://github.com/KJ5HST/methodology/pull/80) (rmsharp) at head `aa36fd8` into
  `main` with a merge commit, the repo's convention. Preceded by the internal review of 2026-09-14 (F1–F6,
  posted as one comment by S18) and the internal re-review of 2026-09-15 of the four answering commits
  (`5c9f0f3`/`d4e1570` F1 (a), `3774076` F2, `aa36fd8` F3), which returned **merge** with one new
  non-blocking finding (G1: the read-set token partition is prose-only since the byte class ceiling left).
  Session S19. **Merge commit `4d9e271`** (parents `e5e2661` + `aa36fd8`), read back from the API.
- **Verified on the merged `main`:** `bin/tests.sh` 115 / 1 — Test 9 now **passes** (main has the three new files);
  the one failure is `tools/test_context_budget.py` `TestFitGateEndToEnd`, **environmental** (this machine has exactly
  2 transcripts for the repo path: enough for the test to run, too few for `calibrate()` to fit; the test file and tool
  are identical at `aa36fd8` and here, and a worktree path skips it) — fix queued as the next session's first step.
  Dashboard unit 211 OK; trim unit 123 OK; `check-links` OK; `check-learnings` OK (13 rows); `commit-msg --selftest`
  OK; twins byte-identical at `DASHBOARD_VERSION` 2.10.7; `context_budget.py --status` OK, exit 0. Adopters now
  receive 27 manifest rows on their next `bin/sync` (24 → 27; corpus 659,755 → 839,383 B).
- **Deferred to the next Orient by design:** 11 `status: reconciled` receipts for #80's non-merge commits, the
  one-time ledger reorder S15's below-`main` placement made necessary, and the v3.8 release PR.

### 2026-09-15 · [ad hoc] Posted the PR #80 review findings to the PR (non-commit action)

- **Action:** one maintainer comment on [PR #80](https://github.com/KJ5HST/methodology/pull/80) carrying the
  six findings of the 2026-09-14 review (internal, oversight venue): **F1** the Learnings payload —
  `starter-kit/FRAMEWORK_LEARNINGS.md` ships 46 rows (13 canonical + the fork's #15–#47) while the PR body says
  rows #1–#13; **F2** the `methodology_trim.py` doc-only exclusion is unguarded at the predicate level (RED-shown);
  **F3** the shipped root `.context-budget.json` reports the PR's own headline OVER; **F4–F6** optional
  (two limits on one file; a docstring describing the fork; the `--source=github` wording). Reproduction
  commands included; nothing merged, nothing changed on the branch. Session S18: claim `75405be` + the
  close-out commit. Comment: <https://github.com/KJ5HST/methodology/pull/80#issuecomment-5674670153> (read back via the API).

### 2026-09-14 · [ad hoc] Housekeeping — merged branches and stray refs deleted (non-commit actions)

- **Deleted, all verified merged into `main` by `git branch --merged` first:** local `docs/quality-ratchet-plan`,
  `feat/context-budget`, `feature/protocols-as-first-class-upstream`, `fix/issue-32-phase2-link-reconciliation`,
  `fix/issue-32-phase3-sync-coverage`, `fix/issue-32-phase4-status-per-file`, `fix/issue-36-check-links-no-mutate`;
  remote `origin/docs/quality-ratchet-plan` (#81), `origin/fix/issue-67-stale-version-remedy` (#73),
  `origin/release/v3.7` (#74); the stray `refs/remotes/pr/63` (merged long ago). Also the local tracking copy
  of `read-set-budgets` created in S15 — `origin/read-set-budgets` is PR #80's head and is untouched.
- **Kept, deliberately:** `docs/operator-gated-review-plan` (3 unpushed commits; reserves Learning #14) and
  `experimental/pocock-audit` (17 unmerged commits, 2026-05-02) — both are the maintainer's to decide.
- **Not done:** no history rewrite. The S16 truncated commits (`356556f`, `ad7bd37`, `ed9ab7e`) stay in
  `main`'s history with the repair `ed98444` on top; removing them would force-push a public branch with a
  fork downstream and is not a housekeeping call. Session S17: claim `b3c9e9d` + the close-out commit; the
  ref list above is the post-deletion read-back (`git branch -a`: 3 local, 2 remote; #80 OPEN/MERGEABLE).

### 2026-09-14 · [ad hoc] Shipped `.githooks/commit-msg` — the disclosure gate (FM #16's honesty counterpart)

- **Change:** new `.githooks/commit-msg` (canonical-only, like the ledger hook beside it — `.githooks/`
  is in no `bin/_manifest.py` row) + a short "Disclosure Hook" paragraph in `starter-kit/SAFEGUARDS.md`
  (distributed). When `AI_AGENT`, `CLAUDECODE`, or `CLAUDE_CODE_SESSION_ID` is in the environment — or
  `METHODOLOGY_REQUIRE_COAUTHOR=1` — the commit message must carry a well-formed
  `Co-Authored-By: <name> <email>` trailer outside comment lines; otherwise the hook is silent, so a
  human committing by hand is never asked to disclose an agent that was not there. `--no-verify`
  bypasses once; `METHODOLOGY_REQUIRE_COAUTHOR=0` disables. Built-in `--selftest` (7 checks).
  Session S16: claim `356556f`, hook + SAFEGUARDS `ad7bd37`, plus the close-out commit completing this entry.
  SAFEGUARDS.md grows by the one paragraph; the Phase 0 pair PR #80 measures stays under its cap
  (checked at close-out against the branch's own figure).
- **What the trailer is, and is not:** the agent never takes credit. The human is the author of every
  commit and owns it. The trailer is *disclosure* — so that no reader of the history is misled about
  how the work was produced. Disclosure was an instruction every session had to remember on every
  commit — an actor-side rule, the class the quality-ratchet plan (§3) says does not scale; under a
  harness this makes forgetting it impossible. The first draft of this entry framed the trailer as
  the agent's credit; the maintainer corrected it before anything was pushed.
- **Deferred, deliberately:** wiring `--selftest` into `bin/tests.sh` and the `BOOTSTRAP.md` Step 10
  mention wait for PR #80, which edits both files (S15 just un-conflicted it).
- **Incident, same session:** the script that reframed this entry sliced the file to the next `---`
  line — which is not the next entry boundary but a separator 316 lines down — and **deleted the ten
  entries between here and 2026-08-10** (S15, S14, S13, the v3.7 release, issue #67, and five more) in
  the amended claim `356556f`, carried by `ad7bd37` and `ed9ab7e`, all pushed. Found by the S15
  merge-tree check re-conflicting where it should not have; restored from `f8fc3ca` by the commit
  after `ed9ab7e` — `diff` against `f8fc3ca` shows 0 lines removed, 21 added (this entry), 41 headings,
  55 source tags. The co-staging hook cannot see this: it checks that the ledger was *touched*, not
  that it did not shrink. A ledger-count ratchet (staged `### ` headings ≥ HEAD's) is the mechanical
  fix and is proposed, not shipped, in the S16 receipt.

### 2026-09-14 · [ad hoc] Resolved the CHANGELOG.md conflict S13/S14 created for PR #80

- **Change:** `main` merged into the PR #80 head branch `read-set-budgets` (which lives in this repo) with
  the one conflicting file, `CHANGELOG.md`, resolved as a union in ledger order — today's S13–S15 entries
  on top, #80's four entries (2026-09-02..04) below them, everything else common. No other file conflicted
  (`git merge-tree --write-tree --name-only origin/main origin/read-set-budgets` → `CHANGELOG.md` only).
  Session S15: claim `8fdc50f` (main) → resolution merge `b82dcff` (pushed to `origin/read-set-budgets`)
  → close-out commit on main. Union verified: 57 source-tagged entries = the branch's 54 + today's 3.
  `git merge-tree` empty after the push and again after the close-out prepend.
- **Why:** #80 was MERGEABLE/CLEAN at `512c2ed` this morning; S13/S14's ledger and receipt commits
  prepended at the same anchor #80 prepends at, so the first session to record anything on `main` after
  #80 opened made it conflict — S13 should have computed that before merging PR #81 (Learning #13) and did
  not. Ordering #80's entries below today's, rather than above, is what stops the next `main` prepend
  from re-conflicting: the two hunks are no longer adjacent.

### 2026-09-14 · [ad hoc] Redacted the quality-ratchet plan to its published source only

- **Change:** `docs/planning/quality-ratchet-plan.md` — every statement derived from the maintainer's
  private correspondence with the article's author removed (the S13 version had paraphrased it, never
  quoted it). The article <https://campusiq.com/blogs/everybody-ships> is now the plan's only source for
  CampusIQ's practice. 15 edits, 425 → 410 lines; residue grep for correspondence-derived phrasing: 0 hits.
  Session S14, committed directly on `main` (the S12 close-out precedent): `4a5aab0` (claim), `762e7bc`
  (redaction), plus the close-out commit completing this entry and the S14 receipt. PR #81's body was
  edited to match. Hook ran clean on every commit.
- **Why:** the maintainer was no longer sure the exchange was not in confidence. Removing it from the live
  record is cheap and reversible; publishing it is neither. Git history (`993aa89`, PR #81) retains the
  S13 text — stated in the receipt, not hidden.

### 2026-09-14 · [ad hoc] Published the quality-ratchet plan — what the methodology should take from CampusIQ's Forseti layer

- **Change:** new `docs/planning/quality-ratchet-plan.md` (canonical-only planning record; not in
  `bin/_manifest.py`, so adopters receive nothing via `bin/sync`). No framework file changed; nothing
  implemented. Session S13; branch `docs/quality-ratchet-plan` → [PR #81](https://github.com/KJ5HST/methodology/pull/81)
  → merge `db121ce` (2026-09-14). Commits: `f62699a` (claim), `993aa89` (plan), `db121ce` (merge), plus the
  close-out commit completing this entry and the S13 receipt. All three session commits ran the ledger
  co-staging hook clean — no `--no-verify` (the first session since S8 to do so; the entry was written
  at claim and completed here).
- **Source:** Aaron Benz, *"Everybody Ships: How CampusIQ Built an AI-Native Company"*,
  <https://campusiq.com/blogs/everybody-ships> — quoted verbatim; the maintainer's correspondence with
  the author is paraphrased as personal communication, never quoted.
- **The finding the plan records:** CampusIQ enforces quality on the *artifact* — the same 130+ checks
  for every actor, thresholds that only tighten, checks that never pass by default — while this
  methodology enforces it on the *actor*: 10 of its 12 quality gates are self-certifications and 26 of
  28 failure modes bind by text alone (only #27 → `.githooks/pre-commit` and #28 → `context_budget.py`
  have a distributed mechanical gate). Self-certification multiplies under N agents rather than scaling;
  a stronger reviewer changes the judge, not the class of gate. Corpus grep for any code-quality
  threshold: 0 hits; the one ratchet that exists (`starter-kit/context_budget.py:504`) guards document size.
- **What it proposes** (D1–D10, six one-session phases): ship the ratchet, not the ruler —
  `.quality-gates.json` SEED + `quality_ratchet.py` TRACKED (refuses a commit that loosens a declared
  threshold), a `SAFEGUARDS.md` hard rule, a flight-manual section generalizing the capability-tiered
  clause from elective to universal, Phase 3C routing "a mechanical learning is a gate, not a row",
  advisory dashboard scoring of gate outcomes, receipt citation of the gate run. Not adopted: two-day
  default approval, PR-throughput floors, coverage floors without a faithfulness check. No new FM.
- **Blocked on:** PR #80 (relocates the Learnings table every prose phase touches). Nothing executes
  until #80 is decided.
- **Verification:** 425 lines; 26 `file:line` anchors on `main @ 512c2ed` re-checked by script (26/26);
  leak check for private-correspondence phrasing, internal-only paths, project names and brand names: 0 hits;
  `bin/check-links` OK (83/21), `bin/check-handoff --allow-pending` OK.

### 2026-09-18 · [BL-72] `bin/check-handoff` skips a fenced block with an info string, instead of the newest receipt behind it

- **Defect:** `scan()` recognised two fence openers, a bare backtick run (a wrapper) and a `handoff` fence. A fence
  with any other info string, such as the `sh` block in the seed's *Size, and when to archive* section, was read as
  prose, so its closing fence opened a wrapper that ran to the next bare fence: the closing fence of the newest
  receipt. That receipt was never parsed. The checker validated the one below it and exited 0, and `--all` counted
  one receipt fewer. Every adopter ledger that keeps the seed's section above its receipts was affected.
- **Fix:** such a fence is now skipped whole, to a bare closer at least as long (CommonMark), as a wrapper already
  was. An info string may not contain a backtick, so a prose line that starts with inline code quoting a fence
  opens nothing. Unlike a wrapper's, the block's lines stay visible to the orphan check, so a receipt under a
  misspelled tag is reported field by field, at its own lines. An unclosed one is reported like an unclosed
  wrapper. A `handoff` fence is read as before.
- **Tests:** ten assertions in `bin/tests.sh` Test 22, after block isolation. Six fail on the previous checker, and
  each of six mutants of the fix fails at least one. The seed fixtures read the seed itself, and fail loudly if it
  loses its sentinel comment or its info-string fence, rather than passing on a fixture that tests nothing.
- **Placed** above the previous entry, below `upstream/main`'s.
- **Commit:** this commit, on `bl57/changelog-rules`

### 2026-09-17 · [BL-57] Four wording fixes: the thin seed, the flight manual's index row, a moved note, two test references

- **Change:**
  - `starter-kit/CHANGELOG.md` — *"Old entries are archived"* becomes *may be archived* (archiving is optional), and
    *"size and archiving"* becomes *reading and archiving* (the rules name no size).
  - `ITERATIVE_METHODOLOGY.md:575` — the §Reference Apparatus row, the same *reading and archiving*.
  - `FRAMEWORK_APPARATUS.md` — the note under the entry format kept a clause about the seed's freshness check, which
    no longer applies where the note now lives; it says only that the tokens are illustrative.
  - `bin/tests.sh` Test 20 (b2) — two references to `BOOTSTRAP.md:85`, which this branch moved to `:87`, cite the
    paragraph by name instead.
- **Why:** each was found by the same independent review. No rule changes; no marker changes, so no seed reads stale
  because of this.
- **Placed** above the previous entry, below `upstream/main`'s.
- **Commit:** this commit, on `bl57/changelog-rules`

### 2026-09-17 · [BL-57] *Placement* covers the trimmer's first month heading and a merged branch's entries

- **Change:** two sentences in `FRAMEWORK_APPARATUS.md` §The Action Ledger, *Placement*. A ledger with no month
  headings starts them at its next new month **or at its first trim**, whose entry `methodology_trim.py` files under
  the current month's heading (`insert_ledger_entry`). A merged branch's entries keep their branch order as one block
  rather than being re-sorted by date.
- **Why:** the rule as written contradicted the trimmer, which adds the current month's heading on its first trim;
  and it said nothing about a merged branch, whose newer entries sit below older-dated ones on `main` today (PR #80's
  did, and this branch's will). Found by the same independent review.
- **Placed** above the previous entry, below `upstream/main`'s — the case the second sentence describes.
- **Commit:** this commit, on `bl57/changelog-rules`

### 2026-09-17 · [BL-57] The `HANDOFFS.md` seed says its archive rule is its own, not the ledger's optional one

- **Change:** `starter-kit/HANDOFFS.md`'s pointer to *Reading and archiving* adds one sentence: that subsection makes
  archiving optional for `CHANGELOG.md`, and this file keeps its own rule — archive when the trimmer's trigger fires.
- **Why:** the seed states that rule and then sends the reader to a subsection that concludes *"Archiving is
  optional"*, which read as a contradiction. The two rules differ on purpose; this branch changes the ledger's and
  leaves `HANDOFFS.md`'s as it was. Found by the same independent review.
- **Placed** above the previous entry, below `upstream/main`'s.
- **Commit:** this commit, on `bl57/changelog-rules`

### 2026-09-17 · [BL-57] The `CHANGELOG.md` migration route keeps the lines a trimmer wrote above the first entry

- **Change:** `bin/status`'s route for a stale `CHANGELOG.md`, and `starter-kit/BOOTSTRAP.md`'s *Updating an existing
  project* paragraph, said to replace **everything** above the first entry with the seed's header. They now say to
  replace the rules text or old header, keeping any archive-pointer block and month heading a trimmer wrote there.
  The `HANDOFFS.md` route in both says to replace any older copy of the size section, and the paragraph names the
  `handoffs-format: 2` line as what makes a copy current (the previous entry's marker).
- **Why:** `methodology_trim.py` writes its shard pointer block and the topmost `## YYYY-MM` heading into that
  zone (`:310`, `:1191`), so the old route, followed literally, deleted them; one adopter's migration nearly did. The
  `HANDOFFS.md` route already kept them; the `CHANGELOG.md` one did not. Found by the same independent review.
- **Test:** Test 20 (g) — the route assertion follows the new wording, and two new assertions require the keep
  clause in the note and in the paragraph it cites. Neither text carried it at the previous commit.
- **Placed** above the previous entry, below `upstream/main`'s.
- **Commit:** this commit, on `bl57/changelog-rules`

### 2026-09-17 · [BL-57] The `HANDOFFS.md` seed gets a versioned format marker; its section heading could not tell an old seed from a new one

- **Change:** `starter-kit/HANDOFFS.md` opens its *Size, and when to archive* section with `handoffs-format: 2`, a line
  the seed asks adopters to keep; `bin/_manifest.py` keys `HANDOFFS.md` on it, as `CHANGELOG.md` keys on
  `ledger-format: 2`; `bin/status`'s route names the section, which carries the marker, and says to replace any older
  copy of it.
- **Why:** the heading arrived in the seed that shipped with the trimmer (`56997af`), over the size premise this
  branch removes (a 65,536 B byte row priced as a *context tax*). Keyed on the heading, that seed read current: a
  marker present in the earlier format can never flag it. Two of six real adopters carry exactly that text and read
  current. Found by an independent review of this branch before the pull request.
- **Test:** `bin/tests.sh` Test 20 (g) gains the shipped-marker check and a fixture with the heading, the old premise
  and no marker. Run against the heading key, that fixture read `present`; against the marker, `present (stale format)`.
  A freshly synced project reads `present` for both seeds, with no note.
- **Placed** above the previous entry, below `upstream/main`'s.
- **Commit:** this commit, on `bl57/changelog-rules`

### 2026-09-17 · [BL-57] Two code comments stop citing a plan item that exists only in the contributor's fork

- **Change:** `bin/status:112` and `bin/tests.sh:323` each ended a sentence with *"(BL-57 item (22))"*, a pointer into
  a planning document on `rmsharp/methodology` that this repository does not have. Both sentences already state the
  reason in full, so the citation is dropped and nothing replaces it. Comments only; no behaviour changes.
- **Placed** above the density entry, below `upstream/main`'s.
- **Commit:** this commit, on `bl57/changelog-rules`

### 2026-09-17 · [BL-57] The three read-set densities re-measured on the blobs this branch ships

- **Change:** `.context-budget.json` — `bytes_per_token` and `measured_bytes` for `CLAUDE.md`,
  `starter-kit/SESSION_RUNNER.md` and `starter-kit/SAFEGUARDS.md`, and each entry's note: which blob was measured,
  and which blob id to watch for the next re-measure. The config's own rule is to re-measure when a file's blob
  changes; this branch changed all three, and the densities still named `1244e95b`, `2a3e410d` and `933816b4`.
- **Measured** by the doubled-file method (seven copies for `SAFEGUARDS.md`), each run reproducing the previous
  measurement exactly as a control: `CLAUDE.md` `dd416ea` 46,953 doubled → 23,476.5 tokens, 2.5182 B/token (control
  46,965); the runner `4811f02` 37,717 → 18,858.5, 2.8225 (control 37,731); `SAFEGUARDS.md` `ed49b97` 42,586 over seven
  → 6,083.7, 2.8155 (control 42,208).
- **Every ceiling holds:** 6.5 tokens under `CLAUDE.md`'s 23,483, 41.5 under the runner's 18,900, 16.3 under
  `SAFEGUARDS.md`'s 6,100; the pair is 24,942.2 of the 25,000-token read cap (99.77%). No ceiling changed.
- **Correction:** the `[BL-63]` entry below gave `SAFEGUARDS.md` as *"about 6,067 tokens"*, an estimate at the old
  density. It measures 6,083.7. Left at 2.8234, the tool counted 6,066, 18 tokens under.
- **Placed** above the `[BL-63]` entry, below `upstream/main`'s.
- **Commit:** this commit, on `bl57/changelog-rules`

### 2026-09-17 · [BL-63] `BOOTSTRAP.md` says how to commit a `bin/sync` run, and `SAFEGUARDS.md`'s five-file cap names it

- **Change:**
  - `starter-kit/BOOTSTRAP.md`, *Setup with `bin/sync`* — a new *Committing a sync* paragraph after *Drift safety*:
    in committed mode, one `bin/sync` run is one commit, holding exactly the files it wrote (which `--dry-run` lists
    first) plus that commit's `CHANGELOG.md` entry; the adopter's own edits afterwards go in their own commits under
    the cap. It gives the reasons: every file is a byte-for-byte copy of a canonical one, one `git revert` undoes the
    run, and a split can leave operating files citing tools that have not arrived yet.
  - `starter-kit/SAFEGUARDS.md`, the five-file cap row — one sentence, *"A committed-mode `bin/sync` run is one
    commit, whatever its file count"*, linking `BOOTSTRAP.md`. Without it the new paragraph would contradict a file
    that says it wins over other guidance and lists the cap under *No Exceptions*.
- **Why:** `bin/sync` copies the whole distributed corpus and does not commit, and no distributed document said how
  its result is committed, so every committed-mode sync that updates more than five files broke the cap or left the
  adopter to invent a split. Measured in one adopter's syncs: 15 and 21 files; dry runs in three others: 14–16.
- **Size:** `SAFEGUARDS.md` 17,024 → 17,129 B, about 6,067 tokens at its recorded 2.8234 B/token against its 6,100
  `max_tokens`; the read-set pair's partition (18,900 + 6,100) is unchanged. `BOOTSTRAP.md` +584 B; it has no budget.
- **Separable:** this commit touches nothing else, so it can be dropped from the pull request on its own.
- **Placed** above the previous `[BL-62]` entry, below `upstream/main`'s.
- **Commit:** this commit, on `bl57/changelog-rules`

### 2026-09-17 · [BL-62] The read-cap partition test sums only the files read together, not every whole-read class

- **Change:**
  - `tools/test_context_budget.py` — `TestThisRepoReadSetPartition` summed the `max_tokens` of every class in
    `WHOLE_READ_CLASSES` (resident, read-mandated, read-set) against the one 25,000-token Read. Only the read-set
    pair, the Phase 0 mandatory read, is read in one Read; a read-mandated or resident file is read whole but on its
    own. So a config declaring two read-mandated ledgers at 25,000 tokens each, two full Reads, failed the test as
    50,000 > 25,000. The check moves into `token_partition(cfg)`, which sums only `READ_TOGETHER_CLASSES`
    (`("read-set",)`); the repo test and its presence control run on it unchanged in meaning, and the renamed
    `test_the_read_set_token_ceilings_partition_the_read_cap` replaces
    `test_whole_read_class_token_ceilings_partition_the_read_cap`. New `TestTokenPartitionRule`, four tests on
    fixture configs: separately-read files do not share the cap; a read-set pair past the cap is still refused;
    one within it passes; one at exactly the cap fits.
  - `.context-budget.json` — the read-set note said the test fails any edit whose ceilings *"in a whole-read
    class"* exceed the cap. It now says *"in the read-set class"*.
- **Why:** the fork hit it with its own config (two read-mandated ledgers at 25,000 each) and had to drop the two
  declarations to pass. Canonical-only: the test file is not distributed, so no adopter runs it.
- **Checked:** test-first. With the check extracted but the old every-class rule kept, two of the new tests failed
  (50,000 > 25,000); with the rule restricted, the file runs 122 tests, 0 failures, 2 skipped (118 and the same
  2 skips before). Five mutants each fail it: the old every-class rule (2 failures), no class summed (4), `>`
  becoming `>=` at the cap (2), a pair skipped (4), `checked` never counted (4).
- **Placed** above the previous `[BL-57]` entry, below `upstream/main`'s.
- **Commit:** this commit, on `bl57/changelog-rules`

### 2026-09-17 · [BL-57] `methodology_trim.py` links its design doc's public copy, and stops citing a hook flag no hook has

- **Change:** `starter-kit/methodology_trim.py`, comments only.
  - The module docstring said the design doc (`docs/planning/ledger-trimmer-design.md`) *"has not been published
    to a public remote"*, so it gave no URL. The doc is public in the `rmsharp/methodology` fork, so the docstring
    now links it at the commit that last changed it (`979dc73`), where the link cannot drift. The file's section
    citations (*design §2*, *§4*, *§5*, *P2* and the rest) now resolve through that link.
  - The *defaults* paragraph said the tool never runs `git mv` because *"`--no-renames` in the FM #27 pre-commit
    hook"* would let a rename-shaped trim pass. This repository's hook has no `--no-renames`, and never did. The
    paragraph now keeps the rule and says what the tool does instead: it writes a new shard and edits the live
    ledger in place, so the ledger keeps its path and its history.
- **Why:** item F5 of the PR #80 review, open since #80 merged. A distributed comment that cites a missing document
  and a flag that does not exist sends the next maintainer of the tool looking for both.
- **Checked:** the module still parses; `grep -c 'no-renames\|not been published'` on the file reads 0; the link
  resolves on GitHub (74,109 B, blob `09c99c14`, the blob the fork's `main` holds). No test reads the docstring.
- **Placed** above the previous `[BL-57]` entry, below `upstream/main`'s.
- **Commit:** this commit, on `bl57/changelog-rules`

### 2026-09-17 · [BL-57] `bin/status`'s stale-seed note gives each seed its own migration route, and the `BOOTSTRAP.md` paragraph it cites gives the `HANDOFFS.md` one too

- **Change:**
  - `bin/status` — the note beneath the table told an adopter holding either stale seed to *"replace the text
    above the first entry (or receipt) with the current starter-kit seed's"*. It now gives each flagged file
    its own route: for `CHANGELOG.md`, replace the text above the first entry with the seed's header; for
    `HANDOFFS.md`, bring across the seed's `## Size, and when to archive` section, above the first receipt,
    and keep the rest of the front matter. The routes sit in `MIGRATION_ROUTES`, beside `STALE_SEED`; the
    `HANDOFFS.md` one names the section from `bin/_manifest.py`'s marker, and a file with no route gets the
    general rule.
  - `starter-kit/BOOTSTRAP.md:85` — the paragraph the note cites named only the `CHANGELOG.md` formats and
    route. It now also names a `HANDOFFS.md` without the size section, and gives that file's route.
  - `bin/tests.sh` Test 20 (g) — eight assertions: a route appears only for a flagged file; a stale
    `HANDOFFS.md` is flagged and gets its own route and no *replace*; two stale seeds get both routes; the
    cited paragraph gives the `HANDOFFS.md` route.
- **Why:** BL-57 item (22). The `HANDOFFS.md` seed differs from an older copy by one section, the one the
  marker keys on. Replacing the front matter instead deletes whatever an adopter's trimmer wrote there, an
  archive pointer and a count sentence among them.
- **Checked:** Test 20 was run alone before the fix: 5 failures, among them *"the note tells a stale
  HANDOFFS.md to replace its front matter"*; 24 passed, 0 failed after. Two mutants fail it: routes printed
  for files that are not flagged (2 failures), and no `HANDOFFS.md` route (1).
- **Placed** above the previous `[BL-57]` entry, below `upstream/main`'s.
- **Commit:** this commit, on `bl57/changelog-rules`

### 2026-09-16 · [BL-57] This ledger's front matter points to §The Action Ledger for its rules, its audit and its month headings

- **Change, in this file's front matter only** (the maintainer's own file — the PR body will say it can
  be dropped, and that dropping it leaves the pointer false):
  - `:11`–`:13` — the rules *"live in [`FRAMEWORK_APPARATUS.md` §The Action Ledger]"*; the seed *"points
    there"*. It said the rules and the seed both *"live in `starter-kit/CHANGELOG.md`"*, which P1 made
    false when it moved the rules out of the seed.
  - `:15`–`:17` — the source-tag paragraph cites *"the audit in §The Action Ledger — anchored to the entry
    heading, and reading any archived shards"*, where it published the unanchored one-file
    `grep -E '\[(issue #|BL-|ad hoc)' CHANGELOG.md`. On this commit that form matches **94** lines
    against **68** entries: it also counts the tag definitions and every in-prose mention of a tag.
  - `:22`, `:24` — `[BL-<N>]` becomes `[BL-<id>]` in the tag definitions, the item P3 recorded as left
    for P4. What `[BL-<N>]` remains on this tree is history: entry bodies here, `CLAUDE.md:123` (v3.1)
    and `README.md:365` (*What's New*).
  - `:36`–`:37` — *"Promote to `## YYYY-MM` sections as it grows"* becomes *"Month headings start at this
    ledger's next new month, and nothing below is retrofitted"*. This ledger has none today, so the
    first one opens at the first entry dated in October.
- **Why:** BL-57 D8 (i), in one commit as the plan requires; C10, C13 and P3's finding (4).
- **Checked:** the audit gives **68** in `zsh` and in `bash` on this commit, equal to the file's `^### `
  count — this tree has no shards. `FRAMEWORK_APPARATUS.md:338` is `## The Action Ledger`, the link's
  target.
- **Placed** above the previous `[BL-57]` entry.
- **Commit:** this commit, on `bl57/changelog-rules`

### 2026-09-16 · [BL-57] `CHANGELOG.md` is described as the action ledger, not as completed-work history — and `CLAUDE.md` is back under its token ceiling

- **Change:** *"Completed work history"* becomes the action ledger at `starter-kit/BOOTSTRAP.md:23`, `:107`,
  `:131`, `README.md:96`, `:114`, `:200` and `CLAUDE.md:51`. Two instructions that framed an entry as
  something written when work *completes* now say to record each action, and to remove a finished
  backlog item from `BACKLOG.md`: `starter-kit/BOOTSTRAP.md:139` and the matching sentence in
  `README.md:96`. The migration step at `starter-kit/BOOTSTRAP.md:145` moves completed items in *as
  entries, newest on top*, where it said *"into reverse-chronological sections"*.
- **Also:** `CLAUDE.md:21`, the *Reference apparatus* row, now reads *"its tables, tests, scoring scales
  and ledger rules; distributed"*. It pays back the 4 tokens the merge `52ad407` carried over
  `CLAUDE.md`'s `max_tokens` 23,483 — P1's *"and the `CHANGELOG.md` rules"* was 9 B shorter and 4
  tokens longer than the wording it replaced.
- **Why:** BL-57 C11. The seed's ledger records every action, including releases, PRs and declines, and
  an instruction keyed to *completing work* misses all three.
- **What *"completed work"* still says, and why it stays:** `README.md:530` is the v2.1 *What's New* entry
  (history); `CLAUDE.md:128` is the v3.6 release narrative quoting a dashboard label; `starter-kit/BOOTSTRAP.md:134`
  says that open work, completed work and plans belong in separate files, which is the backlog split
  and still true. `grep -ni 'completed work history'` over the three files finds only `README.md:530`.
- **Size, in tokens:** `CLAUDE.md` reads **46,953** doubled (23,476.5 tokens) against **≤ 46,965**
  (`upstream/main`'s blob `1244e95b`, whose recorded figure reproduced in the same run): 6 under
  `upstream/main`, 10 under the merge. Bytes: `CLAUDE.md` −25, `README.md` +13, `BOOTSTRAP.md` +81; the
  last two carry no budget row. The runner is untouched by this commit.
- **Placed** above the previous `[BL-57]` entry.
- **Commit:** this commit, on `bl57/changelog-rules`

### 2026-09-16 · [BL-57] A newest-on-top ledger is prepended to, not appended to; the claim commit's entry says *(in progress)*

- **Change:** seven instructions that said *"append … newest on top"* now say *prepend*: the runner's
  Phase 3F (`starter-kit/SESSION_RUNNER.md:281`), failure mode #27's countermeasure (`:332`) and its
  Degradation row (`:360`); `ITERATIVE_METHODOLOGY.md:294`, Phase 6 step 8; `HOW_TO_USE.md:767` and
  `:804`; and the ledger hook's refusal text (`.githooks/pre-commit:70`). The runner's Phase 1B stub
  (`:88`) and the flight manual's Phase 1B step 1 (`ITERATIVE_METHODOLOGY.md:169`) now say the claim
  commit's ledger entry reads *(in progress)* and close-out records the rest, where they said the
  session's actions are recorded at Phase 3F — which a claim commit's own entry contradicts.
- **Why:** BL-57 C3 and C7. §The Action Ledger already said *prepend*; these seven sites were the other
  side of that disagreement. *Append-only*, meaning never edited, is a different claim and stays.
- **Size, in tokens, against the criterion restated before this phase's first edit:** the runner reads
  **37,717** doubled (18,858.5 tokens) against **≤ 37,731** (`upstream/main`'s blob `2a3e410d`) — 7 tokens
  more than P4's start at the merge, 7 under the criterion; the 36,955 control reproduced in the same
  run. Bytes: runner +9, `ITERATIVE_METHODOLOGY.md` +45, `HOW_TO_USE.md` +2, the hook +1. The flight
  manual's +45 misses the plan's *"byte-neutral wording"*; it has no budget row — `.context-budget.json`
  lists it under `_deliberate_exclusions`.
- **Checked:** `grep -nE '[Aa]ppends? (a|one) dated|Append the owed entry'` over the runner,
  `ITERATIVE_METHODOLOGY.md`, `HOW_TO_USE.md` and the hook exits 1 — no matches. No test or tool pins
  the changed text (`git grep` over `bin`, `tools` and the starter-kit scripts).
- **Placed** above the previous `[BL-57]` entry.
- **Commit:** this commit, on `bl57/changelog-rules`

### 2026-09-16 · [BL-57] §The Action Ledger states when an entry is written and where it goes: one per commit, never edited, under the topmost month

- **Change:** `FRAMEWORK_APPARATUS.md` §The Action Ledger replaces its closing paragraph — *"Work
  committed but not finished … Promote to `## YYYY-MM` sections as the list grows"* — with two rules,
  and its opening sentence stops saying entries are written *"At close-out"*, which a claim commit's
  entry contradicts. Each rule, as it now reads on this commit:
  - `:439` — *"**Lifecycle — one entry per commit, never edited.** The commit is the unit the ledger
    co-staging hook checks, so each commit carries its own entry, and each non-commit action gets one
    of its own."*
  - `:442` — *"A claim commit carries an *(in progress)* entry, and close-out adds its own entry rather
    than rewriting the claim's."* Work committed but unfinished is marked the same way.
  - `:446` — *"A committed entry is never edited. A correction is a new entry that names what was
    wrong. The one exception is removing content that must not be published … and that removal is
    recorded by an entry of its own."*
  - `:449` — *"A Phase 0 backfill is the one entry that may span several commits."*
  - `:451` — *"The Phase 1B `CHANGELOG: pending` marker lives in `SESSION_NOTES.md`. A project that
    keeps no `SESSION_NOTES.md` relies on its `status: pending` `HANDOFFS.md` receipt instead."*
  - `:454` — *"**Placement — prepend under the topmost `## YYYY-MM`.** … When the month changes, open
    the new month's heading above the last one: group by month, not by release. A ledger that has no
    month headings starts them at its next new month, and nothing already written is retrofitted.
    Entries stay at `###`, the level the tools key on."* — `_DATED_ENTRY_RE`
    (`starter-kit/methodology_dashboard.py:211`) and the trimmer's `record_start`
    (`starter-kit/methodology_trim.py:307`) both anchor on `^###`.
- **Also:** `HOW_TO_USE.md:748` gives the apparatus as *"~535 lines"* — 534 after this change; it said
  515, which P2 had already made stale at 501.
- **Why:** BL-57 C7, C8 and C13, as the operator decided at Q4 A (one entry per commit, never edited).
  The rules had one sentence on a claim's entry (*"mark it `(in progress)`"*) and none on editing,
  and the month rule said *"promote … as the list grows"*, which names no point at which to start —
  this ledger holds 65 entries and no month heading.
- **Placed** above the previous `[BL-57]` entry, below `upstream/main`'s block, after the merge `52ad407`.
- **Commit:** this commit, on `bl57/changelog-rules`

### 2026-09-16 · [BL-57] Correction: §The Action Ledger attributed a measurement to a ledger that does not record it

- **What was wrong:** the entry above, and the text it describes, said the unanchored audit *"returned
  78 against 64 actions"* **"on this framework's own ledger."** The measurement is real, but it was
  taken on the project whose ledger was split at v3.6, not on this repository's — whose root
  `CHANGELOG.md` carries no such record. A reader of this tree could not check the claim, and merged
  upstream it would attribute the count to a ledger where the comparison was never run.
- **Change:** the sentence now states the failure first and the number as what it is —
  *"an unanchored pattern … can report more actions than the ledger holds; the project this was
  measured on counted 78 where 64 had happened."* The mechanism is checkable anywhere; the figure no
  longer claims a home it does not have.
- **Why:** an unverifiable number in a distributed file is the thing §The Action Ledger's own advice
  warns against — it is right when written and unfalsifiable afterwards. Caught by grepping this
  tree for the figure's provenance before close-out, not by any gate.
- **Placed** above the previous entry.
- **Commit:** this commit, on `bl57/changelog-rules`

### 2026-09-16 · [BL-57] The `HANDOFFS.md` seed enumerates its shards with `git ls-files`, not a bare glob

- **Change:** `starter-kit/HANDOFFS.md`'s rule that anything counting receipts must span the live
  file and its shards published that span as the bare glob `HANDOFFS.md docs/archive/HANDOFFS-*.md`.
  It now reads `HANDOFFS.md $(git ls-files 'docs/archive/HANDOFFS-*.md')`, with the reason stated:
  zsh aborts a command whose glob matches nothing, so before the first split the bare form counts
  nothing at all — the same reason the ledger's audit is written that way. 10,417 → 10,676 B.
- **Why:** C10. The bullet was outside P2's lines and was carried to P3 with the audit it matches.
- **Reproduced in a throwaway repository with one entry and no shard:** the bare form prints `0`
  under zsh (with `no matches found` on stderr, exit 1) and `1` under bash (with a `cat` error on
  stderr, exit 0); the `git ls-files` form prints `1` and exits 0 under both. The failure the fix
  removes is not an error the caller sees — it is **two shells returning two different counts**.
- **Placed** above the previous entry.
- **Commit:** this commit, on `bl57/changelog-rules`

### 2026-09-16 · [BL-57] The runner cites the ledger rules instead of restating their audit; three files adopt `[BL-<id>]`

- **Change:** `starter-kit/SESSION_RUNNER.md:39` (Phase 0, the backfill step) drops the inline
  `grep -E '\[(issue #|BL-|ad hoc)' CHANGELOG.md` for a link to
  [§The Action Ledger](../../docs/methodology/FRAMEWORK_APPARATUS.md#the-action-ledger), so the audit is
  published in exactly one place. `:278` (Phase 3F) and `:329` (failure mode #27) change
  `[BL-<N>]` to `[BL-<id>]`, as do `ITERATIVE_METHODOLOGY.md:294` and `.githooks/pre-commit:57`.
  After this commit `grep -F '[BL-<N>]'` over the runner, the flight manual, `HOW_TO_USE.md`, the
  hook, §The Action Ledger and both seeds finds nothing.
- **Why:** C6 and C10, the distributed half of BL-57's P3. One rule, one home, one audit.
- **Two duplicate clauses paid for the link.** The step already showed `[ad hoc]` in its own entry
  template, so *"default `[ad hoc]`"* was removed; and the note's closing paragraph already says the
  backfill *"does not become this session's deliverable"*, so the step's weaker *"separate from this
  session's later deliverable"* was removed. **The runner ends smaller than it started: 52,195 →
  52,163 B, and 18,477.5 → 18,463.5 tokens.**
- **The two units disagreed about the link, which is why the size rule is now stated in tokens.**
  Adding the cross-reference and the two id changes alone measured **+36 B but only +9 tokens** — a
  path tokenizes at about 4 B/token where this file averages 2.8248 — so a byte rule overstates what
  a cross-reference costs and understates what cut prose saves. Tokens are the unit the read cap and
  the file's own ceiling are written in.
- **Placed** above the previous entry.
- **Commit:** this commit, on `bl57/changelog-rules`

### 2026-09-16 · [BL-57] §The Action Ledger: a source tag admits any backlog id, and the audit reads the archived shards

- **Change:** `FRAMEWORK_APPARATUS.md` §The Action Ledger states the vocabulary as `[issue #<N>]`,
  `[BL-<id>]` and `[ad hoc]` — `<id>` being whatever id the project's backlog gives the item, not a
  number. The audit moves out of the vocabulary sentence into its own paragraph and becomes
  `cat CHANGELOG.md $(git ls-files 'docs/archive/CHANGELOG-*.md') | grep -cE '^### …'`. Three
  properties of that command are stated in place, because each fixes a way the old one-line form
  gave a wrong number rather than an error: **`git ls-files`, not a bare glob** — zsh aborts a
  command whose glob matches nothing, so in a project that has never trimmed the bare form returns
  no count at all; **anchored to the entry heading** — unanchored it also matches the vocabulary's
  own definitions and every mention of a tag in prose, which on this repository's ledger returned
  78 against 64 actions; and **`BL-[^]]+`, not `BL-[0-9]+`** — it counts whatever id the backlog
  uses. A closing sentence says entries written before a project adopted the vocabulary stay as
  written and are not counted, so the shortfall is expected rather than a defect to repair.
- **Why:** C6 and C10, the source-tag half of BL-57's P3. The rules live in one place now, so the
  audit published beside them is the one every project runs.
- **Measured, not asserted.** The two shells disagree on the bare-glob form in a repository with no
  shard: zsh prints `0`, bash prints `1`. Across the six adopter repositories, widening
  `BL-[0-9]+` to `BL-[^]]+` moves the count 96 → 262, 599 → 784 and 236 → 247 in three of them —
  **362 logged actions the numeric-only pattern could not see** — and leaves the other three
  unchanged. One of those adopters tags with `BL-OPS-ADMIN-PW-RECOVERY-001`.
- **Placed** above the previous entry.
- **Commit:** this commit, on `bl57/changelog-rules`

### 2026-09-15 · [BL-57] The `HANDOFFS.md` seed names no size — archive when the trimmer's trigger fires; the trimmer's budget comment drops *"context-tax"*

- **Change:** `starter-kit/HANDOFFS.md` §Size, and when to archive keeps its heading, which `bin/status`
  keys on (D9), and replaces what follows it: the premise that Phase 0 reads the file every session, and
  the two-cap table with its 65,536 B default and its citations of BL-52 and a fork-only plan, give way
  to the reads the protocol makes and one rule — *"Archive it when the trimmer's trigger fires. The tool
  states the trigger, and this file names no size of its own."* The pointer to §The Action Ledger names
  *Reading and archiving* and what it holds, and the *three files* list says receipts move *"when the
  file is archived"*, not *"once the file outgrows a session's read"*. `starter-kit/methodology_trim.py:186`:
  *"the per-file context-tax budget"* → *"the per-file byte budget"* — a comment; the module's AST is
  identical to `b82dcff`'s. 11,505 → 10,417 B.
- **Why:** steps 2 and 3 of BL-57's P2 (C1, C2, C12, C14). This file's own archive rule otherwise stands
  (D7); whether *optional* extends to it is the operator's call.
- **Placed** above the previous entry.
- **Commit:** this commit, on `bl57/changelog-rules`

### 2026-09-15 · [BL-57] §The Action Ledger: the ledger is never read whole, and archiving is optional — the two-cap size rule goes

- **Change:** `FRAMEWORK_APPARATUS.md`'s *Size, and when to archive* becomes *Reading and archiving*,
  on the operator's Q2 A. Each rule, at its line in this commit: `:428` *"The protocol never asks a
  session to read this file whole"*, then its three partial reads — Phase 0 reconcile from `git log`
  (`:430`), close-out at the top (`:432`), a lookup by `grep` or `git log --grep` (`:433`); `:436`–`:438`,
  past the trimmer's `READ_REFUSE_BYTES`, read the top with an offset and a limit; `:440` *"Archiving is
  optional"*; `:442` *"The tool's trigger is the only statement of when — these rules name no size"*;
  `:476` conservation, *"the live file and its shards together never lose an entry"*, so a count spans
  both and never the live file alone, or a count ratchet refuses every trim (C9); `:486`, kept, a trim
  *"does not belong in Phase 0"*. The two-cap table goes — its 65,536 B default (C2), its *"every session
  pays"* premise (C1), its citations of BL-52 and a planning document this repository does not hold
  (C12) — with the rate-versus-level argument, which describes a line cap the trimmer no longer has. The
  shard convention stays; its enumeration becomes `cat CHANGELOG.md $(git ls-files
  'docs/archive/CHANGELOG-*.md')`, equal in bash, zsh and a Python count with no shard (55) and with
  eleven (526). The *three files* paragraph (`:498`) no longer says the ledger splits *"once it outgrows
  a session's read"*, and the file's intro (`:13`) and the section's opening (`:342`) no longer call the
  moved text verbatim. 28,022 → 25,983 B.
- **Why:** step 1 of BL-57's P2 (C1, C2, C9, C12, and C4's half in this file). The protocol reads only
  parts of the ledger, so its size costs no session a read; the trimmer stays, for a project that wants
  a smaller live file.
- **Placed** above BL-57's P1 entries, below `main`'s.
- **Commit:** this commit, on `bl57/changelog-rules`

### 2026-09-15 · [BL-57] The documents that describe `FRAMEWORK_APPARATUS.md` name its seventh section

- **Change:** `HOW_TO_USE.md`'s layer table (the apparatus row gains *write a ledger entry*; ~330 → ~515
  lines), `CLAUDE.md`'s Document Hierarchy row, and `ITERATIVE_METHODOLOGY.md` §Reference Apparatus, whose
  table listed the six sections that moved there and now lists §The Action Ledger as well. Wording only.
  The `CLAUDE.md` row is 9 B shorter than before: `.context-budget.json` pins that file's ceiling at its
  size (59,168 B), so it names the rules and drops *"Extracted so the manual fits one read"*, which the
  apparatus's own intro already says.
- **Why:** step 4 of BL-57's P1 — the file gained a section in step 2, and three documents that describe
  it did not know. The plan named the first two; the third is the same kind of index, found by grepping
  for the set-size claim (*"Six sections moved there"*).
- **Placed** above #80's entries, below `main`'s.
- **Commit:** this commit, on `bl57/changelog-rules`

### 2026-09-15 · [BL-57] `bin/status` keys the `CHANGELOG.md` seed on `ledger-format: 2`, and its migration advice stops rewriting entries

- **Change:** `bin/_manifest.py`'s `SEED_FORMAT_MARKERS` key `CHANGELOG.md` on `ledger-format: 2`, the
  seed's pointer line, instead of its title, and `HANDOFFS.md` on its `Size, and when to archive` heading
  instead of its title; the comment states why a title can never fire. `bin/status`'s migration note and
  `BOOTSTRAP.md`'s *Updating an existing project* paragraph now say: replace the text above the first
  entry with the current seed's, leave every entry as written, and reseed only a file with no history.
  `bin/tests.sh` Test 20: the in-use fixture carries the marker line, and a new case (b2) holds the frozen
  pre-ledger-format-2 seed, which must read *present (stale format)*.
- **Why:** step 3 of BL-57's P1. A title never changed across formats, so keying on it reported every old
  seed as current; and the old advice — *"reconcile its header and per-entry format"* — told adopters to
  rewrite committed entries.
- **Verified:** (b2) fails against the title-keyed marker (116 passed / 2 failed) and passes with this
  commit (117 / 1; the other failure is Test 9 throughout). On copies of six adopters, `bin/status` reads
  every `CHANGELOG.md` *present (stale format)*, with the new advice beneath, and its six `HANDOFFS.md`
  verdicts equal fork `main`'s, which already keys on that heading.
- **Placed** above #80's entries, below `main`'s.
- **Commit:** this commit, on `bl57/changelog-rules`

### 2026-09-15 · [BL-57] The `CHANGELOG.md` rules move to `FRAMEWORK_APPARATUS.md` §The Action Ledger; the seed becomes a pointer with a format marker

- **Change:** the seed's three rule sections — *How to add an entry*, *Size, and when to archive* and
  *CHANGELOG.md vs SESSION_NOTES.md* — move verbatim, one heading level down, into a seventh section of
  `FRAMEWORK_APPARATUS.md` (15,493 → 28,022 B), whose intro now says so. `starter-kit/CHANGELOG.md` keeps
  its title, purpose paragraph, sentinel and footer, and gains a linked pointer carrying
  `ledger-format: 2` (12,893 → 1,335 B). `starter-kit/HANDOFFS.md`'s cross-reference points at the new
  home, and `methodology_trim.py`'s fence-tracking comment says where the fenced examples live now
  (comment only: its AST is unchanged). No rule changes.
- **Why:** step 2 of BL-57's P1. `bin/sync` writes a seed once and never again, so rules kept in a seed
  froze at each project's seeding; in a synced file a correction reaches every project.
- **Verified:** each moved section occurs byte for byte in the home (the plan's §9.3 check); the trimmer
  reports `NO_RECORDS` on the new seed; `bin/sync` into an empty directory seeds it; `bin/check-links`
  resolves the two new links (105 → 107).
- **Placed** above #80's entries, below `main`'s.
- **Commit:** this commit, on `bl57/changelog-rules`

### 2026-09-15 · [BL-57] The trimmer's fence-awareness controls read a frozen copy of today's seed, so they survive the seed shrinking

- **Change:** `tools/test_methodology_trim.py` and a new `tools/fixtures/seed-CHANGELOG-ledger-format-1.md`,
  both canonical-only; nothing distributed changes. Three controls asserted that the live
  `starter-kit/CHANGELOG.md` holds record-shaped example lines inside fences. They now read the fixture —
  the seed exactly as it ships today, git blob `47bc8485`, which a new test asserts — while the live seed
  must still hold no records. The dated-prose test's `.replace()` anchor, `## How to add an entry`,
  becomes the `---` line, asserted to occur exactly once before the replace; a docstring cites the
  sentinel by its token, not by line number. Green with either seed.
- **Why:** step 1 of BL-57's P1. The seed's rules text moves to `FRAMEWORK_APPARATUS.md` next, and every
  adopter seeded before then keeps the fenced examples, so the controls stay meaningful on the copy.
- **Placed** above #80's entries, below `main`'s.
- **Commit:** this commit, on `bl57/changelog-rules`

### 2026-09-15 · [ad hoc] PR #80 review F3: the root `.context-budget.json` holds the Phase 0 pair to the read cap in tokens at its measured density, and drops the two ledgers it could only report as over

- **Change:** `.context-budget.json` only — this repository's own config, which `bin/_manifest.py` does not
  distribute (adopters receive the seed, `starter-kit/context-budget.json`, unchanged).
  `starter-kit/SESSION_RUNNER.md` and `starter-kit/SAFEGUARDS.md` trade their byte ceilings for token
  ceilings at densities measured by the doubled-file method — 19,200 + 5,800 tokens, which partition the
  25,000-token read cap — and the `read-set` class keeps its total as a measurement but declares no byte
  ceiling, because `class_ceiling()` can only take a typed byte total or derive one at the 2.27 B/token
  floor. `CHANGELOG.md` and `HANDOFFS.md` leave `files[]` for `_deliberate_exclusions`, with the reason
  and the command that recovers their entries.
- **Why:** F3 of the review ([comment](https://github.com/KJ5HST/methodology/pull/80#issuecomment-5674670153)):
  `context_budget.py --status` printed OVER at the head — for the pair the headline says fits, and for
  both ledgers — and wired as a gate it would have refused every ledger append. The operator chose the
  review's answer (i) for the pair, and for the ledgers a fourth: a ledger is read in part, and in a
  whole-read class `token_ceiling()` clamps every file to the 25,000-token cap, so answer (ii) left both
  ledgers over and its pin refused the next append (measured).
- **Measured on both trees** — this branch, and its merge into `main` at `9fa3141`: `--status` exits
  **0 (OK)** on each, where it exited 2. `--precommit`: a 300 B append to either ledger passes; the
  runner passes +100 B and is refused at +2,100 B (19,220 tokens against 19,200); `SAFEGUARDS.md` is
  pinned at its size in the merge; a shrink passes. The merged pair is 68,548 B and 24,278 tokens,
  967 B more than this branch's 67,581 B — `main`'s own S16 paragraph in `SAFEGUARDS.md`.
- **Placed** with this PR's own entries, above F2's, below `main`'s.
- **Commit:** this commit, on `read-set-budgets` (PR #80)

### 2026-09-15 · [ad hoc] PR #80 review F2: the doc-only exclusion is tested for every non-markdown file `bin/sync` installs, from its real `starter-kit/` source

- **Change:** `tools/test_methodology_dashboard.py` only — canonical-only, so adopters receive nothing,
  and neither scanner twin changes. `test_a_synced_repo_with_context_budget_installed_is_still_doc_only`
  is generalized in place as `test_a_synced_repo_with_each_installed_source_file_is_still_doc_only`.
  Every non-markdown dest in `bin/_manifest.py`'s `DISTRIBUTION` (today `methodology_dashboard.py`,
  `methodology_trim.py`, `context_budget.py`, `.context-budget.json`) is written from its real
  `starter-kit/` source into the Quarto doc-only fixture, one at a time and then all together, and must
  leave `source_loc` 0, `doc_only` true and no "No test infrastructure" risk; each must also pass
  `is_framework_installed` directly. The names come from the manifest, not `FRAMEWORK_INSTALLED_SOURCE`,
  so a file the manifest installs and the scanner does not list fails here by name; a last assertion
  checks the test covered exactly the scanner's list. Still 211 tests — the names are subtests.
- **Why:** F2 of the review ([comment](https://github.com/KJ5HST/methodology/pull/80#issuecomment-5674670153)):
  with `methodology_trim.py`'s `version_re` and four signatures neutralized in both twins, the suite
  stayed OK (211) while a synced doc-only fixture read `code` with the false HIGH.
- **RED first.** Six mutants, each planted in both twins of a clone, the old and the new suite run
  against each; controls 211 OK on both sides, the clone verified clean after every mutant:
  - M1, the review's mutant: old **OK (211)**; new FAILS — `2181 != 0` source LOC, alone and all together.
  - M2, the same neutralization of `context_budget.py`: old fails 2; new fails 3.
  - M3, the same of `methodology_dashboard.py`: old and new fail the same 12. **Not this test:** the
    neutralized strings sit in the scanner's own signature table, so the real file still matches itself;
    the stand-in fixtures catch it. The docstring says so.
  - M4, `.context-budget.json`'s signatures neutralized: old **OK (211)**; new FAILS on the direct
    predicate call — the file is `config`, so end to end it cannot fail.
  - M5, `methodology_trim.py` dropped from the tuple and the table: old fails 1; new fails 4, this test
    by name.
  - M6, the one `collect_all` call site skipping `methodology_trim.py`, predicate untouched: old **OK
    (211)**; new FAILS end to end.
- **Placed** with this PR's own entries, above F1's, below `main`'s.
- **Commit:** this commit, on `read-set-budgets` (PR #80)

### 2026-09-15 · [ad hoc] PR #80 review F1 (a), step 2: `FRAMEWORK_LEARNINGS.md` ships rows 1–13 and the reserved `#14`, as this PR's description says

- **Change:** rows #15–#47 — 33 learnings from the contributor's fork, 32 of them citing fork sessions —
  leave the distributed `starter-kit/FRAMEWORK_LEARNINGS.md` (56,673 → 13,983 B). Rows 1–13 are
  byte-identical to what this PR carried. The `#14` callout stays, reworded because no row 15 exists now:
  the next row appended is `#15`, and its two sentences about fork sessions S34 and S35 are gone.
  `bin/check-learnings`' comment quoting the old callout follows it. The fork keeps its rows in its own
  copy; any of them can come upstream later, one PR at a time.
- **Why:** F1 of the review ([comment](https://github.com/KJ5HST/methodology/pull/80#issuecomment-5674670153)),
  option (a), the reviewer's default, taken by the contributor: the canonical numbered set grows one row
  at a time, and this PR's description says 13 rows.
- **Placed** above step 1, with this PR's own entries.
- **Verified:** `bin/check-learnings` exit 0 — *"13 Learning row(s), contiguous 1..13; all citations
  resolve"*; a `Learning #20` planted in `starter-kit/SAFEGUARDS.md` is caught (exit 1, *"cites Learning
  #20, which does not exist"*) and the restored tree passes. `bin/check-links` OK (105 links, 23 files);
  `tools/test_methodology_dashboard.py` 211 OK; `context_budget.py --status` reports the file `ok` at
  13,983 of 73,728 B.
- **Commit:** this commit, on `read-set-budgets` (PR #80)

### 2026-09-15 · [ad hoc] PR #80 review F1 (a), step 1: citations of Learnings past #13 now state their rule, before the table keeps only rows 1–13

- **Change:** comments and two docstrings, in three files; no behaviour changes. The review of this PR
  ([comment](https://github.com/KJ5HST/methodology/pull/80#issuecomment-5674670153), F1) asks that
  `starter-kit/FRAMEWORK_LEARNINGS.md` ship rows 1–13 plus the reserved `#14` rather than 46 rows. Before
  that cut, every citation it would leave dangling is rewritten to state the rule instead of a number:
  `starter-kit/context_budget.py:77` and `:378` (Learning #34) and `:409` (*"learning #22 / #26a"* — this
  table has no `#26a`, and its #22 is about backlog deletion, so the pair cites another numbering);
  `tools/test_context_budget.py:489`, `:546`, `:563` (#34); `tools/test_methodology_trim.py:1244` (#16)
  and `:2063` (#43).
- **Why:** `bin/check-learnings` sweeps only the Markdown files of the distributed corpus
  (`distributed_md_files`), so the two `context_budget.py` citations — a file every adopter receives —
  would have dangled with the check green. Repaired first, so no commit carries a dangling citation. The
  `Learning #N` mentions past 13 that remain are history (the #28/#29/#30/#34 that never existed, in
  `CLAUDE.md`, `README.md` and `bin/check-learnings:36`), a planted test value (`bin/tests.sh`, #4242),
  and a dated audit citing another project's numbering (`docs/audits/2026-05-02-mattpocock-skills-evaluation.md`).
- **Placed** with this PR's own entries, below `main`'s, for the reason the conflict-resolution entry at
  the top of this ledger gives: an entry prepended at the top re-conflicts with the next `main` prepend.
- **Verified:** `starter-kit/context_budget.py` and `tools/test_methodology_trim.py` parse to an AST
  identical to `b82dcff`'s; `tools/test_context_budget.py` differs in exactly the two docstrings.
  `tools/test_context_budget.py` 116 tests OK, `tools/test_methodology_trim.py` 123 OK,
  `context_budget.py --selftest` exit 0, `bin/check-learnings` exit 0.
- **Commit:** this commit, on `read-set-budgets` (PR #80)

### 2026-09-03 · [ad hoc] The context-budget gate ships — ceilings in tokens, class totals, and the repairs beneath them

- **Change:** `starter-kit/context_budget.py` `1.0.0` → `1.2.0` (29,549 → 73,040 B), shipped as the
  end state of nine fork commits (seven that went through the fork's own review rounds, plus two
  comment-only rewords made for this port) rather than a replay — the tests arrive as one file, and
  every intermediate state of the tool before its reviewed end state fails them. Ceilings may now be declared in **tokens** (`max_tokens`, against `read_cap_tokens`
  25,000 — the number in the Read tool's own refusal message); a whole-read file with only `max_bytes`
  gets a ceiling derived at the 2.27 B/token floor and clamped at the cap; **class totals**
  (`resident`, `read-set`) are summed and gated in the bare run and in `--precommit`;
  `config_defects()` reports a declared `max_tokens` above the cap and a typed class total that
  disagrees with its derivation; `calibrate()` walks first-parent history, compares timezone-aware
  stamps and refuses a fit below R² 0.50 instead of printing noise; the index is sized with
  `git cat-file -s` (the old path was 1 B short on LF, more on CRLF, and raised on non-UTF-8 content);
  the ledger row names the ceiling that fired in its own unit and reports bytes, not lines, when
  nothing fired. Exit codes are unchanged (`0/1/2/3`), and so is the refusal to run at a root with no
  `.context-budget.json` (exit 3).
- **What it buys.** [#76](https://github.com/KJ5HST/methodology/pull/76) and
  [#78](https://github.com/KJ5HST/methodology/pull/78) shed bytes; this one **refuses growth**. On this branch the Phase 0
  mandatory pair is 52,195 + 15,386 = **67,581 B against the 56,750 B one-read cap — over by
  10,831 B, exactly what [#76](https://github.com/KJ5HST/methodology/pull/76)'s table left.** Nothing here shrinks it. Once a root config declares
  the pair, `--precommit` refuses any commit that grows either file and passes any that shrinks one.
- **The tests travel with the tool.** `tools/test_context_budget.py` — 116 tests, canonical-only
  (not in `bin/_manifest.py`, like the trimmer's), every git fixture a scratch repository — plus one
  `bin/tests.sh` row wiring it, immediately after the trimmer's. Until that row `calibrate()`'s
  arithmetic had no test anywhere: the existing `== Test: context_budget.py ==` block covers
  install-hook, sync distribution and the selftest gates, all of which stay green while the fit
  returns noise. Two tests fit this repository's own session transcripts against `CLAUDE.md` and
  **skip**, by design, on a machine without them.
- **The seed follows the tool.** `starter-kit/context-budget.json` gains `read_cap_tokens`, a
  `max_tokens` on each of its two whole-read entries and a note on the on-demand entry saying why it
  gets none (+6 lines) — documentation of keys the new tool reads. It is a seed-once file: no
  adopter's existing config changes on sync.
- **Scanner:** untouched. Both dashboard twins already list `context_budget.py` and
  `.context-budget.json` as framework-installed files and score neither.
- **Verification:** clean clone of `cea3068`, measured at the branch head with the root config in
  place. `python3 tools/test_context_budget.py` — 116 run, OK, 2 skipped; `--selftest` 52 PASS /
  0 FAIL; `bin/tests.sh` **115 passed / 1 failed** against **114 / 1** on the untouched base — one
  row added, zero status flips; the failure on both is Test 9 (`bin/sync --source=github` reads
  `main`, where three manifest sources are absent until this branch merges). `bin/check-links`,
  `bin/check-learnings`, `bin/check-handoff` and `bin/check-handoff --all` each 0.
- **Provenance:** ported from `rmsharp/methodology` `main` — the tool byte-identical (blob
  `d91677b5`), the test module differing in six lines: four where a fork-relative identifier became
  the date of the change, two where a reference to the fork's numbered `bin/tests.sh` block became a
  description of this tree's. The fork's own root config, its measurement history, its dashboard
  series and its ledgers are **deliberately excluded**.
- **This repository declares its own budget** — a root `.context-budget.json`, in a second commit so
  the policy file is reviewable apart from the code. It **pins** `CLAUDE.md` at its arrival size
  (59,168 B: growth refused, shrink passes), **derives** the `read-set` total from the read cap at run
  time (25,000 tok × 2.27 B/tok = 56,750 B) and splits it 41,364 / 15,386 across `SESSION_RUNNER.md`
  / `SAFEGUARDS.md`, so all 10,831 B of debt sits on the file the series wants shrunk, and
  **declares** the two ledgers Phase 0 reads at 65,536 B and 25,000 tokens each and
  `FRAMEWORK_LEARNINGS.md` at 73,728 B — the derivation `bin/check-learnings` already cites this
  file for. Every number's `_` key says how it was derived; five values are marked PROPOSAL, and the
  calibration constants are the seed's (`--calibrate` proposes and writes nothing). Day one: the bare
  run exits 2 with six findings — `SESSION_RUNNER.md` and the pair over by 10,831 B, both ledgers over
  in bytes and in tokens — none of them new. This file is also what turns the wired `bin/tests.sh`
  row green: without a root config the tool exits 3 and the unit module's selftest test fails. The
  gate is **not wired** into `.githooks/pre-commit`: run `--precommit` by hand, and never
  `install-hook` at this root (the config's `_` key says why). Run by hand, this PR's own two commits
  fail it — exit 3 on the first (no config yet), exit 2 on this one (this bullet grows a ledger
  already over its ceiling). `.gitignore` gains the comments explaining why neither measurement history
  (the dashboard's, this tool's) is ignored; this tool's appears on the first bare run and is yours to
  track or not.

### 2026-09-02 · [ad hoc] The flight manual sheds its apparatus into a read-on-demand sibling

- **Change:** the six contiguous apparatus sections of `ITERATIVE_METHODOLOGY.md` — Knowledge
  Accumulation System, Honest Accounting Framework, Scope Validation System, Verification
  Hierarchy, Session Document Template, Performance Tracking — move **verbatim** into a new
  distributed sibling, `FRAMEWORK_APPARATUS.md` → `docs/methodology/FRAMEWORK_APPARATUS.md`,
  `TRACKED`. The manual keeps a *Reference Apparatus* stub naming all six and linking the file.
  **Nothing was deleted.** The apparatus is reference, not theory — you open it to fill in a
  session document, validate a scope or score a claim, not to understand why the phases exist.
- **What it buys.** `ITERATIVE_METHODOLOGY.md` **68,240 → 55,976 B (−12,264, −18.0%)**, landing
  **774 B under the 56,750 B one-read cap** it had been over. The sibling is **15,493 B** and is
  read on demand. Manifest **26 → 27** rows.
- **The extraction was the easy half; reachability was not.** The move updated every place that
  *names* the six sections and, at first, no place that *invokes* what is in them — those
  sections used to be reached by scrolling, so no link-based proof can see their loss.
  `bin/check-links` strips the `#fragment` and validates existence only, so it stays green either
  way. Nine pointers were therefore added where none existed (Principles 4–7, Phase 2 step 8,
  Phase 6 steps 5–6 and its gate, and the self-referencing *Across the Full Series* heading, whose
  bare parenthetical became a link); four more sites already pointed at these sections in prose and
  were converted in place. `ITERATIVE_METHODOLOGY.md` now carries **14** references to the sibling —
  **13 pointer sites** plus the stub's own link — and the stub enumerates all thirteen.
- **The manual-copy path is documented, not just the tool path.** `README.md`'s Option B and
  `starter-kit/BOOTSTRAP.md`'s Step 1 both enumerate the framework files by hand. Left alone they
  would have told an adopter to copy a `docs/methodology/` **missing the file those 14 links point
  at** — an install broken in a way `bin/check-links` structurally cannot report, because it builds
  its simulated tree from `bin/_manifest.py`, which was correct. Fixed at `README.md` (both the
  Option A sentence and the Option B list), `starter-kit/BOOTSTRAP.md` (the tree diagram, the sync
  sentence and the manual-copy step) and `docs/tutorials/T1_setup.md`.
- **The documents that describe the corpus now describe this one.** `CLAUDE.md` gains a Reference
  apparatus row and its layer count is corrected; `HOW_TO_USE.md`'s layer table gains a row and its
  `ITERATIVE_METHODOLOGY.md` length is re-derived (**~880 → ~580 lines**, sibling ~330).
- **Scanner:** `docs/methodology/FRAMEWORK_APPARATUS.md` joins `FRAMEWORK_DISTINCTIVE_DOCS` in both
  `methodology_dashboard.py` twins, so a synced project is still classified by a name only this
  framework installs. The twins remain byte-identical. The installed-markdown counts in the
  surrounding comments were **re-derived from `bin/_manifest.py` on this tree** (27 rows / 23
  markdown / 19 tracked-markdown) rather than carried over from the branch this was ported from.

### 2026-08-28 · [ad hoc] The Learnings table leaves the every-session read for a read-on-demand sibling

- **Change:** the `## Learnings (added by sessions)` table moves out of
  `starter-kit/SESSION_RUNNER.md` into a new distributed sibling,
  `starter-kit/FRAMEWORK_LEARNINGS.md` → adopter root `FRAMEWORK_LEARNINGS.md`, `TRACKED`.
  `SESSION_RUNNER.md` keeps a one-paragraph pointer; Phase 3C's two routing bullets now name the
  sibling. The learnings are **reference, not procedure** — a session needs them when a learning
  applies, not to run a session.
- **What it buys, measured on both files rather than argued.** The Phase 0 mandatory read
  (`SESSION_RUNNER.md` + `SAFEGUARDS.md`) goes **80,526 B → 67,581 B (−12,945, −16.1%)**.
  `SESSION_RUNNER.md` alone: **65,140 → 52,195 B**. `SAFEGUARDS.md` is untouched. Against the
  56,750 B one-read floor the pair is **over by 23,776 B before and 10,831 B after — a 54.4%
  cut with no content deleted.** The sibling is 56,673 B and is read on demand.
- **Nothing is lost — the rows move, and then some.** The 13 rows that lived here arrive as rows
  **#1–#13** of a 46-row table; rows #1–#11 are byte-identical, and **#12 and #13 arrive compacted**
  (2,401 → 1,451 B and 1,573 → 1,447 B) under the 1,500 B per-row budget the new file publishes.
  Compaction is *said shorter without saying less*: every mechanism, figure and citation is kept,
  and each compacted row was read back by an independent reader asked only what was lost.
- **`#14` is deliberately absent and must stay absent.** It is reserved by
  `docs/operator-gated-review-plan`'s D3; the table numbers **1..47 with 14 reserved**. Renumbering
  would break every `Learning #N` citation, which is what "append only, never renumber" exists to
  prevent. `bin/check-learnings` now parses the file's own prose for reserved numbers, so the gap
  is not reported as a missing row.
- **Tooling follows the table, because the file publishes rules that must be true.**
  `bin/check-learnings` locates the table by its header row rather than by a `## Learnings` heading
  (portable across both layouts), honours the reserved gap, and enforces the **1,500 B row budget
  the new file's front matter names it for** — held against every row, not only the row being
  written. `bin/tests.sh` Test 23 retargets to the new file and now asserts on each mutation's
  **specific finding text** rather than the exit code, which is a union over every check and would
  otherwise be satisfied by the new budget arm.
- **Scanner:** `FRAMEWORK_LEARNINGS.md` joins `FRAMEWORK_AMBIGUOUS_DOCS` (the ambiguous root-name
  set grows 6 → 7, a behaviour change, so `DASHBOARD_VERSION` 2.10.6 → 2.10.7 on both byte-identical
  twins) and gains a `CHECKLIST_EXEMPT` entry rather than a `METHODOLOGY_ITEMS` row —
  `METHODOLOGY_MAX` is a derived denominator, so scoring it would move every already-compliant
  adopter's percentage for a change they did not make. That exemption was driven **RED** first: with
  it removed, `test_every_distributed_adopter_root_file_is_scored_or_exempt` fails on exactly
  `['FRAMEWORK_LEARNINGS.md']`.
- **Every count claim is derived from the manifest and asserted, not carried over.** The
  originating commit's count edits were computed against a 22-row `DISTRIBUTION`; this one is 24, so
  its "+1" arithmetic lands two short here. Parsing `bin/_manifest.py` gives **total 25, markdown
  dests 22, TRACKED markdown 18, TRACKED markdown at the adopter root 7, `workstreams/` sources 9**,
  and all **eight** count claims across four files were re-checked against that derivation — 8
  correct, 0 wrong. Three needed correcting: the `FRAMEWORK_ITEMS` comment (*"9 of the 22"* → **25**),
  `docs/tutorials/T8_keeping_current.md` (*"all 23 distributed files"* → **25**), and
  `tools/test_methodology_dashboard.py` (*"21 installed markdown files"* → **22**). **Two of the
  three units of the first two corrections are pre-existing drift** from `df6a991`, which added the
  context-budget rows without updating the prose — not this change.
- **Referents a reader of this tree cannot resolve, disclosed because no check covers them.** Seven
  backticked artifacts named inside the rows do not exist here (`.context-budget.json`,
  `methodology_trim.py`, `docs/planning/BACKLOG.md`, `docs/audits/…`, `.verify.sh`, two `BACKLOG.md`
  paths), across 10 of the 46 rows; and **32 of 46 rows cite session numbers S35–S119** from the
  canonical fork's sequence, which runs separately from this repo's and **collides with it**. None is
  a broken hyperlink — they are prose code spans, which is exactly why `bin/check-links` is green and
  correctly so: it strips inline code, so its green says nothing about them. **They are left as-is
  deliberately, and a clarifying note in the front matter is affordable rather than blocked** — the
  earlier reading of the budget was wrong on both counts and is corrected here. This file's class is
  `on-demand`, ceiling **73,728 B**; at 56,673 B it has **17,055 B of headroom**, so a ~400 B note
  costs nothing it does not have. The **56,750 B** figure is the `read-set` *class total* — the
  Phase 0 mandatory pair — and was never this file's ceiling. Nor does a note threaten anything about
  `bin/sync`: `read_local` reads a **working tree** (`bin/sync:52`) and `read_github` reads
  `KJ5HST/methodology`; neither consults a local ref, the two sources already differ on several
  tracked files in every measured adopter, and nothing compares them. The note is **deferred to a
  follow-up, not declined on cost** — per-row provenance is content, and this change is an extraction.
- **Verification:** `bin/check-learnings` **0** (*46 rows, contiguous 1..46, all citations resolve,
  0 over 1,500 B*); `tools/test_methodology_dashboard.py` **211 passed**; twins byte-identical.
  `bin/tests.sh` row-for-row against a pristine control — see the PR body for the table.
- **Provenance:** ported from `rmsharp/methodology` `ed22ace` (the extraction) plus the compaction
  and checker repairs that followed it. The fork's own ledgers, `docs/planning/`, and the two
  unrelated `SESSION_RUNNER.md` changes it also carries (issue #75's *name the surface* additions
  and the Phase 3F `Model:` bullet) are **deliberately excluded**.


### 2026-08-12 · [ad hoc] Released v3.7 — the artifacts Phase 0 mandates reading now have ceilings

- **Change:** release narration commit on `release/v3.7` — `README.md` §What's New in v3.7 (folding
  in the stale "Since v3.6 (unreleased)" section), `CLAUDE.md` §Versioning entry, and the
  "Current version" line 3.6 → 3.7. Cite-don't-restate: the full narrative lives in
  [`CLAUDE.md` §Versioning "v3.7"](../../CLAUDE.md#versioning); this entry is the action record.
- **Scope:** 38 commits and 13 ledger entries since `v3.6` (`d7a482a`). **Minor**, not patch,
  because the framework gained a failure mode (**#28**, count 27 → 28 — the first since v3.1) and a
  new distributed tool (`starter-kit/context_budget.py`, TRACKED, with a SEED config). **Not major**
  because no principle, phase, gate, or workstream changed. Learnings 12 → 13; `DASHBOARD_VERSION`
  2.10.2 → 2.10.6 across four separate fixes; `bin/tests.sh` 84 → 114; unit suite 197 → 211.
- **The "unreleased" README section was stale and is why this was worth catching.** It still ended
  *"the failure-mode count stays 27"* — written before PR #66 appended FM #28, and true when
  written. A section that describes itself as pending release is exactly the text nobody re-reads;
  it is Learning #7's cross-reference problem applied to the release notes themselves.
- **Tag and Release — recorded after the action, not predicted before it.** Annotated tag `v3.7`
  (tag object `0138e095`) cut at **`dcb6fc6`**, the PR [#74](https://github.com/KJ5HST/methodology/pull/74)
  merge commit, plus GitHub Release *"v3.7 — The artifacts Phase 0 mandates reading now have
  ceilings"*, published 2026-08-12T04:50:42Z, not a draft and not a prerelease:
  <https://github.com/KJ5HST/methodology/releases/tag/v3.7>. Written into this entry only once each
  fact existed and had been read back — a tag SHA asserted in advance is exactly the forward-looking
  claim Learning #13 says to compute rather than predict.
- **Unlike v3.6, this release has a narration commit of its own** (`2bddc3e`), so the tag+publish
  step is recorded here against a real commit rather than reconstructed four days late. That was
  v3.6's failure: a release is the non-commit action failure mode #27 names, and the one class
  Phase 0 reconcile-on-read cannot catch by design — reconcile diffs `git log` against the ledger
  frontier, and a tag plus a Release move neither.
- **Commit/PR:** narration `2bddc3e` → merge `dcb6fc6` (PR #74); this ledger completion rides the
  S12 close-out commit.
- **Session:** S12 · **Verified:** tag confirmed annotated (`git cat-file -t` → `tag`) and pointing
  at `dcb6fc6`; present on `origin`; Release confirmed published, non-draft, non-prerelease.

### 2026-08-12 · [issue #67] The stale-copy warning now names a remedy proportionate to the finding, and bare `--dry-run` no longer writes

- **Change:** `tools/methodology_dashboard.py` (+ `starter-kit/` twin, kept byte-identical) and
  `tools/test_methodology_dashboard.py`. `DASHBOARD_VERSION` 2.10.5 → 2.10.6. Closes
  [issue #67](https://github.com/KJ5HST/methodology/issues/67).
- **Defect 1 — a disproportionate remedy.** `check_stale_version()` answered "this one copy is
  old" with `Re-sync: python3 <canonical> --sync`. But `--sync` is scoped from the **canonical's
  own location**, not the working directory, so it rewrites every discovered sibling — measured at
  26 files across 25 repos, including 7 creates in repos that do not gitignore the path and 1
  where the file is git-tracked. An adopter following a one-line instruction verbatim dirtied
  eight unrelated repositories. The warning now leads with the safe per-project action
  (`cp <canonical> <this copy>`) and offers the portfolio path only as `--sync --dry-run`, with
  its scope stated. **Why it matters beyond tidiness:** a remedy nobody can safely run is one
  mechanism behind an *ignored* warning — in one adopter this line rode ~28 consecutive handoffs
  unacted-on. The measurement was never missing; the actionable remedy was.
- **Defect 2 — a flag named `--dry-run` that writes.** It was consulted only inside the `--sync`
  branch, so bare `--dry-run` fell through to a full scan and wrote `dashboard.html` *and*
  appended to `dashboard_history.jsonl`. It is now an error (exit 2) that writes nothing.
  Refusing rather than silently no-opping is deliberate: a silent no-op leaves the caller unable
  to distinguish "nothing to do" from "flag ignored" — the same unreadable-signal class as
  defect 1.
- **Tests:** new `TestCliRemedyProportionality` (3 cases, unit suite 208 → 211). Both defect
  tests were driven RED against the pre-fix scanner and the failing run read, not assumed;
  the third is a presence control (a plain run must still write `dashboard.html`), without which
  a scanner that refused *every* invocation would pass and look fixed.
- **Scope deliberately not taken:** the issue also suggests `--sync-self` and a `--yes` gate on
  `--sync`. Both change the CLI contract rather than fix a defect, so they are left for a
  separate deliverable; the `cp` line already gives the per-project remedy with no new surface.
- **Distribution:** the scanner is `bin/_manifest.py`-TRACKED, so adopters receive both fixes via
  `bin/sync`.

### 2026-08-11 · [ad hoc] `methodology_dashboard.py`'s `LANG_MAP`/`DOC_EXTS` now recognize R, Quarto, and R Markdown

- **Change:** `tools/methodology_dashboard.py` (+ `starter-kit/` twin, kept byte-identical) and
  `tools/test_methodology_dashboard.py`.
- **The defect:** `.r` was already in `SOURCE_EXTS` (R source always counted toward Source LOC),
  but had no `LANG_MAP` entry, so it never got its own "Code by Language" row. `.qmd` (Quarto) and
  `.rmd` (R Markdown) were in neither `SOURCE_EXTS` nor `DOC_EXTS`, so either extension outside a
  `docs/` path fell through `categorize_file`'s whole ladder to `"other"` — not source, not docs,
  not even LOC-counted (LOC is skipped entirely for `"other"`). Found scanning a real R package:
  603 `.r` files / 77,773 LOC counted as Source but invisible in "Code by Language".
- **Fix:** `"r": "R"` added to `LANG_MAP`; `.qmd`/`.rmd` added to `DOC_EXTS`.
- **A real, not just cosmetic, classification consequence — found on review, pinned here.**
  Quarto's `.qmd` was already a render-toolchain marker (`detect_doc_only`'s fallback arm), so a
  Quarto repo was already `doc_only` before this fix; what changed for Quarto is only its
  *reported* metrics (a Quarto book previously showed zero documentation and its files as
  uncounted `"other"`). Bare `.Rmd` has no toolchain marker at all (`_bookdown.yml` is one; a
  plain analysis project has neither that nor `*.qmd`), so adding `.rmd` to `DOC_EXTS` is what
  newly clears the corpus disjunction for that class: a real R-Markdown analysis repo (no
  toolchain marker, a small `.R` helper alongside several `.Rmd` files) flips `doc_only`
  `False → True` and its `"No test infrastructure"` risk softens from `HIGH` to a doc-only
  advisory. Believed correct — an R-Markdown analysis project is exactly the population BL-5/v3.2
  exists to score fairly, and the has-tests gate still protects a real R package with a `tests/`
  dir — verified directly against the pre-fix scanner (the identical fixture there reads
  `doc_only=False` with the `HIGH` risk) and pinned with a new end-to-end regression test,
  `test_rmd_analysis_repo_flips_doc_only_and_softens_the_test_risk`, so a future `DOC_EXTS` edit
  cannot silently un-flip the population without a test noticing.
- **Also fixed:** the existing Quarto fixture's own render-toolchain-arm isolation. Adding
  `.qmd`/`.rmd` to `DOC_EXTS` meant the pre-existing Quarto test could now clear the corpus
  disjunction on doc-LOC alone, silently narrowing what it proved (Layer 7's specific
  toolchain-arm-in-isolation guarantee). A `QUARTO_MINIMAL` fixture + a dedicated isolation test
  restore that proof; the stale in-code comment claiming a pure-Quarto repo's `.qmd` was "never
  counted as docs" is corrected to match.
- **Verified:** `python3 -m unittest tools/test_methodology_dashboard.py` 204/204 (198 prior + 6
  from the original fix + 1 classification-regression test), the 2 failures on this base
  (`test_every_distributed_adopter_root_file_is_scored_or_exempt`,
  `test_exclusion_list_matches_the_manifest`) are pre-existing and unrelated (fixed by a sibling
  PR, not this one). `DASHBOARD_VERSION` 2.10.2 → 2.10.5 (2.10.3/2.10.4 independently claimed by
  two sibling PRs open the same day). Twins confirmed byte-identical.
- **Distribution:** `starter-kit/methodology_dashboard.py` is `bin/_manifest.py`-TRACKED, so
  adopters receive the fix via `bin/sync`; `tools/` and `tools/test_methodology_dashboard.py` are
  canonical-only.
### 2026-08-11 · [BL-31] Dashboard's framework-installed exclusion never learned about the context-budget gate PR #66 itself shipped

- **Origin:** fork backlog item BL-31 (`docs/planning/BACKLOG.md`, fork `main` only — not yet pushed
  to `origin` as of this entry, so no link is given rather than cite one that would not resolve),
  found re-verifying PR #66's own review-comment fixes after merge. `bin/_manifest.py` gained two
  new non-markdown dests in this PR (`context_budget.py`, TRACKED; `.context-budget.json`, SEED),
  but `tools/methodology_dashboard.py`'s `FRAMEWORK_INSTALLED_SOURCE` tuple and
  `tools/test_methodology_dashboard.py`'s `CHECKLIST_EXEMPT` test fixture — both purpose-built to
  stay in sync with this manifest — were never extended to match. Reproduced before the fix, not
  inferred: a `git worktree` at the merge commit (`a2a7275`) run against
  `python3 -m unittest tools/test_methodology_dashboard.py` gave 2 failures, both in tests that
  predate this PR (last touched at `bec4095`) and exist specifically to catch this class of drift.
- **Effect the drift had:** any adopter running `bin/sync` post-merge would have `context_budget.py`
  misattributed to their own source LOC — the exact miscount `FRAMEWORK_INSTALLED_SOURCE` exists to
  prevent for `methodology_dashboard.py` itself — and both new root files would read as neither
  scored nor exempt on the compliance checklist.
- **First fix (listing the names) did not actually work — found on review, not shipped as-is.**
  Adding `context_budget.py` and `.context-budget.json` to `FRAMEWORK_INSTALLED_SOURCE` satisfies
  the name-list agreement test, but `is_framework_installed()` then verified EVERY listed name
  against `methodology_dashboard.py`'s own content signatures (`DASHBOARD_VERSION`,
  `METHODOLOGY_ITEMS`, etc.) — which `context_budget.py` never carries — so the content check
  silently rejected it and the exclusion never fired. Reproduced directly:
  `is_framework_installed(Path("context_budget.py"), ...)` returned `False` even with the name
  listed; a real bin/sync-shaped synced doc repo still flipped `doc_only` `True -> False`.
- **Real fix:** content verification is now PER FILE. `_FRAMEWORK_FILE_SIGNATURES` gives each name
  in `FRAMEWORK_INSTALLED_SOURCE` its own version pattern and signature set —
  `context_budget.py`'s own `VERSION`/`CONFIG_NAME`/`HISTORY_NAME` markers, `.context-budget.json`'s
  own distinctive keys (though that entry is structurally unreachable today: `is_framework_installed`
  is only called for `category == "source"`, and a `.json` extension is always `"config"` — given a
  signature anyway so the completeness test below needs no special case). A new canonical test
  asserts every `FRAMEWORK_INSTALLED_SOURCE` name has a matching signature entry, so a future
  addition to the tuple cannot repeat this exact gap silently. A new behavior test reproduces the
  bug end-to-end with the REAL shipped `context_budget.py` content (not a synthetic stand-in) and
  asserts a synced doc-only repo stays `doc_only` — RED-confirmed against the name-only fix before
  landing this one. `CHECKLIST_EXEMPT` (a `tools/test_methodology_dashboard.py` test fixture, not
  scanner source) gains both names, with the same reasoning already on record for
  `methodology_dashboard.py` — their presence proves a pre-commit hook was installed, not that the
  session-operating discipline the checklist measures was followed. `DASHBOARD_VERSION` 2.10.2 →
  2.10.3.
- **Verified:** `python3 -m unittest tools/test_methodology_dashboard.py` 200/200 (197 prior + 3
  new; RED-confirmed against the pre-per-file-signature code first); `bash bin/tests.sh` 114/114;
  `python3 bin/check-links` OK (83 links / 21 files); twins confirmed
  byte-identical.
### 2026-08-10 · [ad hoc] Two defects in the HANDOFFS.md receipt spec: an unassigned reconcile promise, an unoffered locator form

- **Change:** `starter-kit/HANDOFFS.md`'s fenced receipt-format spec, two independent fixes in one
  pass since both sit in the same few lines.
- **(1) The spec promised a reconcile no procedure ever assigns.** It said `commit: pending` and
  `what_was_done: pending` are legal at write time because "the next session reconciles them to
  real shas" — but `SESSION_RUNNER.md` Phase 0 step 6 only reconciles a *missing or still-
  `status: pending`* receipt, never a `status: complete` receipt whose `commit:` field alone is
  `pending`. No procedure anywhere performs the promise as written. Reworded to state `pending` as
  a legitimate resting value for both fields, not a duty nobody is assigned to discharge.
- **(2) `changelog_ref`'s spec offered two locator forms neither of which receipts actually use.**
  The placeholder named `PR #N` or a short-sha; in practice, entries locate a `CHANGELOG.md`
  action by its quoted `### ` heading instead — all 8 live receipts in this repo's own
  `HANDOFFS.md` already use that form, and none use `PR #N` or a bare sha, without the spec ever
  blessing it. Added the quoted-heading form as a third explicit option and noted that a bare line
  number is not a durable locator once a ledger is ever trimmed or archived.
- **Distribution:** `HANDOFFS.md` is `bin/_manifest.py`-SEED (copied once, then adopter-owned), so
  new adopters receive the corrected spec; existing adopters' own copies are unaffected until they
  choose to re-seed.
### 2026-08-10 · [ad hoc] Documented and pinned the doc-only detection thresholds

- **Change:** `tools/methodology_dashboard.py` (+ `starter-kit/` twin, kept byte-identical) and
  `tools/test_methodology_dashboard.py`.
- **The defect:** `DOC_ONLY_SOURCE_LOC_MAX`, `DOC_ONLY_DOC_LOC_MIN` and `DOC_ONLY_DOC_FILES_MIN`
  are round numbers with no recorded derivation, and nothing asserted their values directly —
  `test_source_cap_boundary` exercises `DOC_ONLY_SOURCE_LOC_MAX` only indirectly, via hardcoded
  200/201 boundary literals, so that coverage would silently vanish if that fixture were ever
  rewritten to derive its boundary from the constant instead. `DOC_ONLY_SOURCE_LOC_MAX` in
  particular decides which of two scoring regimes a repo gets (a real 148-LOC repo the cap alone
  misclassified is documented near `FRAMEWORK_INSTALLED_DOCS`, ~100 lines below), so an accidental
  drift here is a user-visible verdict change, not cosmetic.
- **Fix:** added a comment recording that all three are deliberate, stated heuristics — not
  derived from a measured corpus of adopter repos — and a direct regression test
  (`test_doc_only_thresholds_are_pinned_not_left_to_drift`) asserting all three current values, so
  a future edit to any of them is a visible, deliberate decision.
- **Verified:** `python3 tools/test_methodology_dashboard.py` 198/198 (197 prior + this one).
  `DASHBOARD_VERSION` 2.10.2 → 2.10.4 in both twins (2.10.3 was skipped: #71 claimed it
  independently for an unrelated fix, and the constant's own "bump on any change" rule means two
  distinct changes cannot ship under one version); `test_dashboard_version` and
  `test_twins_byte_identical` updated/re-confirmed.
- **Distribution:** `starter-kit/methodology_dashboard.py` is `bin/_manifest.py`-TRACKED, so
  adopters receive the documented, pinned thresholds via `bin/sync`; `tools/` and
  `tools/test_methodology_dashboard.py` are canonical-only.

### 2026-08-10 · [ad hoc] Re-grounded the /caveman row's remaining unsupported claim

- **Change:** `starter-kit/RECOMMENDED_SKILLS.md`'s `/caveman` row.
- **The defect:** `15ccb38` (the "Discharged the three documentation follow-ons" entry below)
  removed a dangling `Learning #34` citation from this row but kept the claim it was
  attributing — "the methodology's own handoff length discipline" — which has no referent
  anywhere in this distributed corpus, and runs opposite to `SESSION_RUNNER.md`'s own failure
  mode #15 (the *thin* handoff is the failure, not the long one) and its Minimum Handoff
  Requirements, which gate on content, not length.
- **Fix:** re-grounded the row on those two verified, reachable sources instead — no length rule
  is stated because none exists to state.
- **Distribution:** `RECOMMENDED_SKILLS.md` is `bin/_manifest.py`-TRACKED, so adopters receive the
  fix via `bin/sync`.

### 2026-08-10 · [ad hoc] Resolved both review findings on [PR #66](https://github.com/KJ5HST/methodology/pull/66) — in the PR, not a follow-up

- **Origin:** rmsharp reviewed PR #66 and filed two findings, each reproduced against real repo
  state rather than theorised, with inline suggestions and an offer to take them to a follow-up PR.
  Fixed here instead, because finding 1 is a defect in code *this PR introduces* — shipping it
  would mean the failure-mode-#28 release note describes a gate that silently does nothing on the
  adopters most likely to want it. The v3.6 precedent is explicit: Layer 7 ran before Layer 6 so no
  release shipped with a known live defect in its own subsystem.
- **Finding 1 — `install_hook()` ignored `core.hooksPath`** (`starter-kit/context_budget.py`).
  It always wrote `<git-dir>/hooks/pre-commit` and printed "installed". `core.hooksPath` redirects
  git away from that directory entirely, and **this methodology's own `BOOTSTRAP.md` Step 10 tells
  adopters to set it** (`.githooks`) to enable the v3.1 ledger co-staging gate — so the population
  following our own setup instructions got a silent no-op with a success message. Reproduced end to
  end before the fix: a commit growing `CLAUDE.md` to 40,000 B against a 28,000 B ceiling was
  *created* rather than refused; after, the same commit is refused and `git rev-list --count`
  confirms none was created. A relative value now resolves against the worktree top level (what git
  itself does when running the hook), an absolute value is used as given, and the pre-existing
  "a hook is already here and is not ours" branch now fires correctly on a repo whose `.githooks/`
  already holds the ledger hook — reporting and refusing to clobber instead of shadowing it.
- **Finding 2 — receipt identity is `session` + `date`, not `session` alone** (`bin/check-handoff`).
  `validate_ledger()` asserted an invariant the format in `starter-kit/HANDOFFS.md` never states.
  `S<N>` is a per-sequence counter and one ledger may merge more than one sequence — a fork and its
  upstream each running their own — so two distinct sessions share an `S<N>` by construction;
  rmsharp reproduced four false positives on a real ledger. **The argument is not the false positive
  itself but what one does to a gate:** this very PR's thesis is that the dashboard printed
  `Large files detected` at every Phase 0 and 15+ sessions read past it. A checker that fires on a
  structurally valid file trains that same blindness on the checker we most need believed. Coverage
  lost is narrow — a block copied and not edited duplicates *both* keys and is still caught — and
  the cross-branch collision it appeared to guard was never guarded, since the checker sees one tree
  and could only ever fire after the merge landed. Code and spec now agree rather than the code
  being stricter: `starter-kit/HANDOFFS.md` states the rule, including that keeping `S<N>` unique
  within a sequence must never mean renumbering an already-written receipt.
- **Verification:** suite **107 → 112**. Both fixes were driven **RED first and observed failing**
  (Learning #12): 2 of the 4 new `install-hook` assertions fail against the unpatched tool (the
  other 2 are deliberate presence controls that must pass either way), and finding 2's new negative
  assertion fails with exactly the reported error, `duplicate session id 'S8'`, before passing. The
  duplicate-identity mutation was also strengthened to copy the S8 header wholesale, so it cannot
  quietly degrade into a session-only collision if a date later changes. The 2 remaining suite
  failures are pre-existing and reproduce on `main` with this branch's changes stashed
  (`tools/test_methodology_dashboard.py`, untouched here; and the GitHub-source dry-run, which needs
  network). `bin/check-links` OK (83 links / 21 files); live ledger green under `--all`.
- **Learning #10 caught one thing the diff could not:** `README.md`'s unreleased #65 bullet still
  claimed "unique session ids". Dated `CHANGELOG.md` entries describing what #65 shipped are left
  verbatim per the v2.7.1 frozen-record precedent; the unreleased What's New bullet describes
  current behaviour and was corrected.
- **Not recorded as a Learning row by design.** The candidate — *a checker's invariant must not be
  stricter than the format it validates; the adopter who trips it is the one who finds out* — is
  real, but `#14` is reserved by `docs/operator-gated-review-plan`'s decision D3. Appending it here
  would create exactly the collision D3 exists to prevent. It is carried in the S10 receipt instead,
  to be appended at the first free number after that branch merges.
- **Commits:** `eacb516` (1B claim) · `14bd88a` (finding 1) · `63e1dcf` (finding 2).

---

### 2026-08-08 · [ad hoc] Failure mode #28 and `context_budget.py` — the artifacts Phase 0 mandates reading now have ceilings

- **Change:** the methodology tells every session to *write* a durable record (Phase 3C a learning,
  Phase 3D a handoff, Phase 3A an evaluation of its predecessor) and no phase ever tells one to
  *reduce* one. That is a compounding term with no decay term, and past a threshold the artifacts
  Phase 0 orders a session to read stop being readable. Adds **failure mode #28, "Unbounded mandatory
  read"**, four Degradation Detection rows, and `starter-kit/context_budget.py` — a stdlib-only
  checker with a declarative per-project config, distributed `TRACKED` with a `SEED` config, plus a
  pre-commit gate. Suite **99 → 107**.
- **Evidence — measured on adopter project ResortApp across 51 raw session transcripts, not
  theorised.** Opening context (tokens present before the first word of the task) rose from
  **45,931 to 103,241 over 38 consecutive sessions and never once decreased**, reversed only when a
  human hand-extracted 156 KB out of `CLAUDE.md`; it regrew 7.6% in the next 43 hours, half of that
  from learnings-index rows **this methodology instructs sessions to append**. `SESSION_NOTES.md`
  reached **26,097 lines / 4,089,558 B ≈ 1.02M tokens** — larger than the window Phase 0 step 2
  mandates reading it into. The measured median session read **180 lines, 0.72% of it.**
- **Why a gate and not a report.** `methodology_dashboard.py` already printed
  `Large files detected (SESSION_NOTES.md: 26,039 lines)` at every Phase 0 by protocol mandate — the
  single risk flag in that project's `dashboard.html` — and **15+ consecutive sessions read past
  it.** The signal was never missing; nothing gated on it. So `--precommit` refuses a commit that
  grows a budgeted file past its ceiling, prints five ranked remedies with "raise the ceiling"
  deliberately last, and states what `--no-verify` costs. All three branches were observed: growth
  refused, shrink-while-over permitted, growth-again refused, then end-to-end through the installed
  hook with `git rev-list --count HEAD` proving no commit was created.
- **Two findings worth naming separately.** (1) Throughput is the wrong tell — source output on that
  project *peaked* on the two days its documents were largest, with zero compactions and 428K of a
  1M window used. What degrades is task selection, not volume. (2) Size hides the **refutation**, not
  the false claim: the claim that cost one session its entire deliverable sat in `CLAUDE.md`, which
  *is* read in full, while the evidence against it sat 503 lines past anything anyone reads.
- **Also:** `bin/tests.sh` gains 10 cases, including the tool's own 13-gate `--selftest` (every gate
  observed failing as well as passing), that re-sync never clobbers an adopter-owned config, and that
  the tool ships no `--force`. Failure-mode count assertions updated 27 → 28 across `CLAUDE.md`,
  `README.md` and four tutorials (Learning #7); the historical release note naming #27 is left alone.
  Pre-existing and unrelated: two `bin/tests.sh` failures on this branch also fail on `main`
  (`tools/test_methodology_dashboard.py` is byte-identical to `main` and fails there; the GitHub
  dry-run needs network).

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
  the full narrative lives in [`CLAUDE.md` §Versioning "v3.6"](../../CLAUDE.md#versioning).
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
  [`CLAUDE.md` §Versioning "v3.6"](../../CLAUDE.md#versioning).
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
  [`CLAUDE.md` §Versioning "v3.5"](../../CLAUDE.md#versioning).
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
  the full narrative lives in [`CLAUDE.md` §Versioning "v3.4"](../../CLAUDE.md#versioning).
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
  lives in [`CLAUDE.md` §Versioning "v3.3"](../../CLAUDE.md#versioning).
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
  [`CLAUDE.md` §Versioning "v3.2"](../../CLAUDE.md#versioning).
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
- **Commit/PR:** this commit (release narration) · [PR #46](https://github.com/KJ5HST/methodology/pull/46). → full narrative: [`CLAUDE.md` §Versioning "v3.1"](../../CLAUDE.md#versioning).
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
- **Commit/PR:** annotated tag `v3.0.1` at `aa822f6` (the PR #44 merge). → full narrative: [`CLAUDE.md` §Versioning "v3.0.1"](../../CLAUDE.md#versioning).
- **Session:** S6 (backfill) · **Verified:** `reuse lint` 53/53; live REUSE badge scanned compliant.

### 2026-07-06 · [ad hoc] PR #44 merged — REUSE.toml + LICENSES/MIT.txt + README badges
- **Change:** added `REUSE.toml` (single bulk `path = "**"` MIT annotation), `LICENSES/MIT.txt`, and
  two README badges (static `License: MIT` + live REUSE-compliance); no existing framework file gained an inline SPDX header.
- **Commit/PR:** PR #44 (content `7b5238a`, merged `aa822f6`).
- **Session:** S6 (backfill) · **Verified:** `reuse lint` 53/53 files, 0 problems.

### 2026-06-25 · [issue #43] Released v3.0 — relicensed under the MIT License
- **Change:** the bespoke source-available `LICENSE` was replaced with verbatim standard MIT text;
  use/copy/modify/distribute/**sell** with attribution retained is now permitted (the prior no-resale restriction dropped).
- **Commit/PR:** relicense `49a103a`, release `5525f30`, annotated tag `v3.0`. Issue: <https://github.com/KJ5HST/methodology/issues/43>. → full narrative: [`CLAUDE.md` §Versioning "v3.0"](../../CLAUDE.md#versioning).
- **Session:** S6 (backfill) · **Verified:** n/a — relicense + lockstep README/CLAUDE.md updates.

