# Parallel-Sessions Plan — making fan-out to many agents clean, not just safe

**Date:** 2026-09-16 (methodology session S24)
**Status:** RATIFIED WITH AMENDMENTS on 2026-10-01 (session S27, under the operator's delegation) — **§8A records
the twelve decisions and overrides any text below that conflicts with it.** Nothing here is implemented.
**Workstream:** Planning (`starter-kit/SESSION_RUNNER.md` §Planning Sessions); document shape per
`workstreams/ARCHITECTURE_WORKSTREAM.md` §The Architecture Document. The plan is the deliverable.
**Trigger:** the operator's question at this session's Orient — *"Do the recent changes allow for fanning out with
multiple agents now? Prior to that, fanning out was very messy."* The Orient answer was **safe but not clean**:
the quality ratchet (PR #82) binds every actor's *output* to the same gates, but two actors *writing at once*
still collide on the ledgers, on session identity, on the missing merge receipt, and on one branch-coupled test.
**Evidence discipline:** every claim about the methodology carries a `file:line` on `main @ 6b29d3d` (the tree
this branch was cut from; the S24 claim commit `3c244aa` changed only `CHANGELOG.md` and `HANDOFFS.md`, whose
anchors are given at `6b29d3d`) or the command that produced it (§9). Claims about what went wrong in practice
cite this repository's own receipts and ledger, and one adopter project's session records by session number —
the project is deliberately unnamed here; the mechanics, not the project, are the evidence.
**Sequencing constraint:** `main` carries 68 unreleased commits since `v3.7` and the S23 receipt names the v3.8
release PR as *"the only thing between main and a release"*; §4 D12 proposes this plan lands **after** v3.8.

---

## 0. The answer in one paragraph

**The methodology's unit of accountability is the session, and every one of its coordination artifacts is
serial:** one `ACTIVE TASK`, one `S<N>` counter, two prepend-only ledgers with a single anchor, a hook that
forces every commit onto one of them, and a reconcile step that walks one line of history. That design is
why one disciplined agent compounds — and why N agents collide. The ratchet fixed the half that *scales*:
verification is now a property of the artifact, so a lighter or parallel agent's output is judged by the same
ten gates as anyone's (`ITERATIVE_METHODOLOGY.md:401`). It did not touch the half that *coordinates*. The
operator's own records show both failures precisely: six verify-agents mutating one working tree fabricated a
defect against clean code (adopter S163), and two session sequences prepending at the same anchor conflicted
in both ledgers on merge (this repo, S21). They also show what worked: a nine-unit writing fan-out that shipped
without eroding a gate because **the agents returned content and one integrator wrote and committed** (adopter
S13). The plan below generalizes that: **many hands, one closer per tree.** A session may fan out to any number
of workers, but exactly one actor writes to a tree, exactly one session closes out, and where two sessions must
run at once they run on two trees whose records merge without conflict. Four mechanical changes (a merge
driver for the append-only files, a structural ledger check, a branch-independent `--source=github`,
worktree-aware calibration), two rules of record (sequence-tagged session ids, a merge receipt rule), and one
contract in prose make that true — the contract makes it a session shape rather than an improvisation.

---

## 1. What "messy" was — the operator's own records, decomposed

| # | What happened | Where recorded | Mechanism |
|---|---|---|---|
| 1 | **Six adversarial-verify agents in ONE working tree contaminated each other.** Two lenses mutated production source to prove tests discriminating; one flipped a sanctioned silent write *while another lens's `cargo test --workspace` was in flight*; the victim saw a pin FAIL and was "one step from filing a HIGH" against clean work. A third left an untracked file behind. | Adopter records, S163 | Concurrent writers (edits **and** test runs) in one tree; each agent reads the others' half-states as defects. The operator's ruling that followed: a no-subagents rule with a standing **read-only** adversarial-verify exception — *"do every discriminating mutation yourself, serially, afterwards."* |
| 2 | **Worktree isolation failed and the fan-out recovered as "return-content agents + serial integration."** Nine worktree agents died in 70 ms (harness: *"not in a git repository and no WorktreeCreate hooks are configured"*); the session re-shaped them to return source without writing files or running the build, and one integrator wrote each unit, regenerated the shared index files, and committed in dependency order under the 5-file cap. Largest single-session deliverable of that project; no gate eroded; one real bug caught by the integrator reading the oracle, not by trusting an agent's implementation *or* its test. | Adopter records, S13 (2026-06-17) | The working shape: workers produce, one integrator commits; shared files (`mod.rs`/`lib.rs`) owned by the integrator; the integrator's build/test/lint matrix is the gate; agent-authored tests are unverified until the integrator has watched one discriminate. |
| 3 | **Two session sequences prepending at one anchor conflicted in both ledgers.** `git merge-tree --write-tree --name-only origin/main origin/feat/quality-ratchet` exited 1 with CONFLICTS in `CHANGELOG.md` **and** `HANDOFFS.md`: S21's two prepends (on `main`) and S20's (on the branch) sat at the same anchor above S19. Resolved by hand as a union, newest on top — after a first read had truncated the conflict list and briefly recorded the merge as clean. | `HANDOFFS.md` S21 receipt, `next_steps` (DERIVED clause); same shape recorded for PR #80 (S13/S14 → S15) | `starter-kit/CHANGELOG.md:17,91` and `starter-kit/HANDOFFS.md:9` are **prepend-only, newest on top**: every writer inserts at the same line. `.githooks/pre-commit:53` makes every content commit co-stage `CHANGELOG.md`, so every concurrent branch touches the hotspot. No merge driver: `git check-attr merge CHANGELOG.md HANDOFFS.md` → `unspecified` (§9). |
| 4 | **A merge left an obligation nobody could discharge.** S19 merged PR #80 and deferred *"11 `status: reconciled` receipts for #80's non-merge commits"* to the next Orient; five sessions later no such block has been written, and the S21–S23 receipts each carry the item forward as an operator ruling still owed. | `CHANGELOG.md:293` (at `6b29d3d`); `HANDOFFS.md` S21/S22/S23 `next_steps` | The reconcile rule (`starter-kit/SESSION_RUNNER.md:44`) says a commit *"in the undocumented set with no receipt at all"* is reconstructed `status: reconciled`, and never says what a **merge** owes. Read literally, every commit of a merged branch that ran no runner owes a receipt — an obligation that scales with the branch and that no session has ever met. |
| 5 | **One test couples every branch to GitHub's `main`.** `bin/tests.sh:118–121` (Test 9) runs `bin/sync --source=github --dry-run`; `bin/sync:78–90` fetches each manifest row from `gh api repos/{REPO}/contents/{src}` — the default branch — while the manifest it iterates is the **local branch's** `bin/_manifest.py`. Any branch that adds a distributed file is red until it merges. S22 declared `tests-sh-failed max 1` to tolerate it; S23 tightened to 0 after the merge. | `HANDOFFS.md` S22 (F3), S23 (`what_was_done`); `.quality-gates.json` | With one branch this is a nuisance. With N concurrent branches the `tests-sh-failed max 0` gate cannot be green on any branch that touches the manifest, and a gate that is red by construction is a gate people learn to read past — FM #17 in mechanical form, the exact erosion the ratchet exists to prevent. |
| 6 | **A tool assumes the main checkout's path.** `starter-kit/context_budget.py:867` derives the transcript directory from `Path(root).resolve()`; a linked `git worktree` has a different path, so `--calibrate` finds no transcripts there. Observed: *"a worktree path skips it"*. | `CHANGELOG.md:286–289` (at `6b29d3d`); `tools/test_context_budget.py:351` | Worktrees are the natural isolation unit for parallel actors; one distributed tool is blind in them (the others are not: `quality_ratchet.py:72–89` (`find_root`) uses `git rev-parse --show-toplevel`; the hooks run in linked worktrees because `core.hooksPath` is repository config). |

**Read across the table.** Rows 1–2 are about **one session with many hands**: the failure was two writers in
one tree, and the fix was one writer. Rows 3–6 are about **two sessions at once**: the failures are the serial
artifacts, and none of them has a fix yet. The ratchet is what makes the *output* of either shape trustworthy;
nothing yet makes the *coordination* of either shape clean.

## 2. What already exists, and its limits

| Element | Evidence (`main @ 6b29d3d`) | Bears on | Limit |
|---|---|---|---|
| **§Mechanical Gates Bind Every Actor** — *"A gate that is a question the actor asks itself does not scale under N agents — it multiplies."* | `ITERATIVE_METHODOLOGY.md:401–416` | Output of any actor | Says nothing about how N actors' *records* combine. |
| **Capability-tiered review** — delegate a layer only where an objective gate proves it; the strongest tier reviews before each checkpoint lands; *"reviewing everything at the end … is failure mode #26 wearing a division-of-labor costume."* | `starter-kit/SESSION_RUNNER.md:177`; `starter-kit/RECOMMENDED_SKILLS.md:75`; Learning #11 | Fan-out within a slice | Elective; scoped to vertical slices; silent on **write scopes** and on **who commits** — the two things S163 and S13 turned on. |
| **"Sub-agents emit confident-but-wrong claims. Apply adversarial refutation to your own agents' output."** | `starter-kit/SESSION_RUNNER.md:175` | Verification of worker output | Refutation of *claims*; nothing about a lens **mutating** the tree it shares. |
| **Sub-Agent Dispatch Pattern** — parent reads, sub-agent gets one claim + one source and returns a verdict, parent writes; calibration vocabulary in every prompt. | `workstreams/RESEARCH_EXHAUSTIVE_VERIFICATION_CAMPAIGN.md:268–296`; `workstreams/TEMPLATE_CAMPAIGN.md:156,225`; `RESEARCH_DOCUMENTATION_WORKSTREAM.md:121,237–241` | Read-only fan-out | Already the right pattern for research; it is written for one workstream and does not reach the runner. |
| **Receipt identity is `session` + `date`** — *"a ledger may legitimately merge more than one sequence."* `check-handoff --all` keys on the pair; `session:` is any string. | `starter-kit/HANDOFFS.md:82–87`; `bin/check-handoff:214–230` | Concurrent sequences | Anticipates merged sequences but gives no way to **tell them apart** while both are live; two same-day claims from one base both pick `S24` and collide at merge. |
| **Hooks skip merges** (`MERGE_HEAD` etc.) and run in every linked worktree. | `.githooks/pre-commit:21–27`; `core.hooksPath` | Merge commits; worktrees | A merge resolving a ledger conflict is never gated — correct — so a **wrong** resolution is caught only by a checker that reads the result. `HANDOFFS.md` has one (`check-handoff --all`); `CHANGELOG.md` has **none**. |
| **Reconcile-on-read** — frontier = newest ledger-touching commit; gap = `git log --no-merges <frontier>..HEAD`. | `starter-kit/SESSION_RUNNER.md:35–44`; `tools/methodology_dashboard.py:1386–1389` | Any history | Correct on a line and correct after a merge that advanced the frontier; **excludes merges** from the gap, so an out-of-band merge (the operator's merge button, PR #82) is an action only discipline records — S23 did; nothing made it. |
| **HOW_TO_USE §Multi-Agent Teams** — *"Each agent should follow its own copy of the session runner … the session documents are the coordination mechanism."* | `HOW_TO_USE.md:868–878` | Concurrent sessions | Four bullets; no mechanics for the ledger merge, identity, or the merge receipt it presupposes. |
| **Principle 9** — one deliverable; *"when a session has high-parallelism verification available"* the deliverable may be a slice. | `ITERATIVE_METHODOLOGY.md:122–132` | Fan-out | Names parallel *verification*; never parallel *construction*, and never who closes out. |

## 3. The finding — one closer per tree

**3A. Two shapes, distinguished by who closes out.** Everything the operator calls "fan-out" is one of these:

- **Shape A — one session, many hands.** One accountable session (the *lead*) runs Phase 0, the 1B claim, and
  all of Phase 3. Workers are not sessions: they run no phase, write no record, and their output enters the
  repository only through the lead's commits. This is adopter S13, the capability-tiered review clause, and
  Claude Code's `Agent` tool as it is actually used. Its failure mode is row 1: a worker that writes (or builds)
  in the lead's tree.
- **Shape B — many sessions, many closers.** Two or more independent sessions, each running the full runner on
  its own deliverable, on its own branch or worktree, at the same time; integration is a merge. This is
  HOW_TO_USE's §Multi-Agent Teams, the fork-and-upstream case (`rmsharp` and this repo), and every case where a
  human and an agent work the same repo in one afternoon. Its failure modes are rows 3–6: the serial artifacts.

**3B. The rule both shapes reduce to.** *A tree has one writer.* In Shape A the writer is the lead; workers
return content or own an isolated tree. In Shape B each session owns its branch — and git already enforces it
there: a second session pushing to the same branch is rejected as non-fast-forward. What git does *not* do is
merge the methodology's records cleanly, tell two live `S24`s apart, say what a merge owes, or keep a
`main`-coupled test green on a branch. Those are this plan's six changes.

**3C. Why the unit of accountability must not change.** The compounding mechanism is bidirectional handoff
scoring along a line (`ITERATIVE_METHODOLOGY.md:112–120,470–478`). A worker that writes its own receipt has no
successor to score it and no predecessor it read; a receipt nobody scores is furniture. So a worker is a
*layer*, not a session — the vertical-slice vocabulary already fits: pre-declared unit set (gate a), one unit per
checkpoint commit (gate b), the full matrix at each boundary (gate c), per-surface faithfulness (gate d). Fan-out
adds three constraints to that contract (§4 D3) and removes nothing. Shape B keeps the line intact *per
sequence* and defines what happens where two lines join (D5, D6, D13).

**3D. What is mechanical and what is not.** The ledger merge driver, the ledger check, the
`--source=github` fix, and the worktree slug are code — they bind every actor (Learning #15). The identity
form and the merge rule are conventions of record that a checker reads and the reconcile step performs. The
one-writer rule and the fan-out contract are instructions: no hook can see a second agent in a tree. Their
mechanical form is the *harness's* isolation (a worktree per worker), which the methodology recommends and does
not ship (`RECOMMENDED_SKILLS.md` convention), plus git's non-fast-forward rejection for Shape B. The plan says
so where each rule lands, rather than presenting an instruction as a gate.

---

## 4. Design decisions (proposed — each is the operator's to ratify or reverse)

**D1 — The session stays the unit of accountability; a session may have many hands but one closer.** No new
principle. Principle 9 gains one paragraph on the v2.7 precedent (it was *"extended"* for slices, not amended):
the deliverable may be built by many actors, closed out by one; "one closer" is the invariant that keeps the
handoff loop (Principle 8) intact under fan-out.

**D2 — "One writer per tree" becomes a SAFEGUARDS hard rule.** One row in the Blast Radius table
(`starter-kit/SAFEGUARDS.md:46–54`): *Never let two actors write to one working tree — workers return content
or own an isolated tree; verification lenses run read-only against a frozen, committed tree; discriminating
mutations are made serially by the one writer.* Test runs count as writes (they mutate build state and read
half-states). Budget: SAFEGUARDS has 71 tokens of headroom (§9); a row is ~70–90 — paid by reduction if it
does not fit. Mechanical form: harness isolation (recommended), git's push rejection (Shape B). Stated as such.

**D3 — The fan-out contract = the four slice gates + three more.** Written once, in the flight manual as a new
`## Parallel Actors` section beside §Multi-Session Campaigns (`ITERATIVE_METHODOLOGY.md:345`), which has **no
context ceiling** and is read on demand; the runner carries a pointer and the one-writer sentence (D10). The
three additional gates:

- **(e) One closer.** Exactly one session runs Phase 0, 1B and 3 for the whole fan-out. Workers run none of
  them and write none of `SESSION_NOTES.md`, `HANDOFFS.md`, `CHANGELOG.md`, `.quality-gates.json`, or any
  manifest. The lead's receipt and ledger entry cover every unit — one bullet per unit with its integration
  commit — and the lead's 3A/3B/3C are the only evaluation and learning records.
- **(f) Pre-declared units with disjoint write scopes.** The gate (a) contract enumerates the units and the
  files each owns. Shared and integration files — index/module files, lockfiles, generated tables, the
  records above — are owned by the lead and edited or regenerated only by it. A worker that needs a file
  outside its scope stops and returns the need; the lead re-scopes. (Adopter S13: *"agents must NOT touch
  shared `mod.rs`/`lib.rs` — the integrator regenerates."*)
- **(g) Serial integration, one unit per checkpoint.** The lead integrates in dependency order; each unit's
  integration is a checkpoint commit under the 5-file cap (gate b) with the full matrix (gate c); the lead
  reviews the unit's diff before its checkpoint lands (capability-tiered review, unchanged) and **re-derives
  load-bearing worker claims itself** — a worker-authored test is unverified until the lead has watched it
  discriminate (introduce the regression, see it fail, revert). "The integrator's build/test/lint is the
  gate" is a restatement of gate (c), not a new gate.

  Read-only fan-out — research passes, adversarial lenses — is unrestricted in count and unchanged in form
  (the campaign template's calibration rules apply); D2 governs its one hazard. Reasoning tier: the lead on
  the strongest available tier; workers per the capability-tiered rule (gate-proven units only); the tier
  assignment recorded in the same contract as the unit set. The lead's context is the ceiling (the campaign
  template's *"the parent agent's context is the campaign's bottleneck"*): units return content sized for
  integration, never transcripts (FM #28 applies to what the lead reads). Fan-out is not a license for a
  second capability (FM #26), a plan with its code (FM #18), or a skipped step (FM #17); the slice test
  applies to the whole.

**D4 — The append-only files merge by union.** A tracked `.gitattributes` in this repo, distributed as a SEED
(`starter-kit/gitattributes` → `.gitattributes`, `bin/_manifest.py` 29 → 30 rows), declaring `merge=union` for
`CHANGELOG.md`, `HANDOFFS.md`, `dashboard_history.jsonl`, and `.context-budget-history.jsonl` — the four files
whose every legitimate concurrent edit is an insertion. `union` is a **built-in** git driver (no per-clone
config, unlike `ours`), honored by `merge`, `rebase`, and `cherry-pick`. On the S21 shape — two contiguous
blocks inserted at one anchor — it keeps both whole (in practice ours above theirs; git's documentation promises
only that both survive and tells the user to verify the result), which is what S21 produced by hand.
Two consequences accepted on the record: (i) *order across sequences is not chronological* — the seed already
rules out re-sorting (*"prepend-only, so close-out never re-sorts,"* `starter-kit/CHANGELOG.md:91`); identity is
the date, the source tag, and the commit sha, not the position; this also **closes S19's "one-time ledger
reorder" item by ruling** (leave as merged). (ii) *union never asks* — a semantically wrong merge is silent —
so D4 ships with D4b: a canonical-only **`bin/check-ledger`** (the `CHANGELOG.md` counterpart of
`bin/check-handoff`): every `###` entry carries exactly one source tag, no two entries share (date, title),
no entry body is orphaned from a heading, and the seed sentinel is gone once entries exist; declared as an
eleventh gate (`check-ledger max 0` — an addition, which the ratchet passes). An adopter whose `.gitattributes`
already exists gets the four lines from `BOOTSTRAP.md` Step 10 and, if D11 is ratified, a LOW dashboard
advisory when `git check-attr merge CHANGELOG.md` is `unspecified`.

**D5 — Session identity under concurrency: a sequence tag.** Bare `S<N>` is reserved for the trunk sequence
(`main`); a session claimed on any other branch writes `session: S<N>-<seq>`, `<seq>` being the branch's
short name or the agent's name (`S24-ratchet`). Identity remains (`session`, `date`); `bin/check-handoff`
accepts any string today (`:214–230`), so the change is one paragraph in `starter-kit/HANDOFFS.md:82–87` and
the 1B stub in the runner. Two concurrent sessions on **one** branch are not a supported shape — that is D2's
failure, and git's push rejection is what catches it.

**D6 — A merge is one action with one receipt.** The session that merges a branch records the merge as an
action: one ledger entry and one receipt naming the merged range (`git log --oneline <base>..<tip>`) and its
sequence tag. The merged branch's commits are covered by their own receipts if that branch ran the runner
(Shape B) or by the merging session's entry if it did not (an external contribution). **No per-commit
`status: reconciled` receipt is ever owed for a merged branch** — this closes the "11 reconciled receipts"
ruling S19 left open, and the runner's reconcile note (`SESSION_RUNNER.md:44`) says so in one sentence. One
mechanical addition to Phase 0 step 6: list `git log --merges <frontier>..HEAD` beside the `--no-merges` gap —
an out-of-band merge (the operator's merge button) is a commit the gap computation currently excludes, so
today only discipline records it (S23 did). `status: reconciled` keeps its one meaning: a receipt for a
session that left commits and no receipt.

**D7 — In Shape A the lead writes; workers produce.** Default and recommended: workers write nothing to the
shared tree and commit nothing; the lead applies each unit (from returned content or `git -C <worktree> diff`)
and commits it with the ledger bullet co-staged, so every commit on the integration branch passes the hook
unchanged. Permitted alternative: workers commit in their own worktree as WIP (`--no-verify` is the bypass
`SAFEGUARDS.md:170` already allows for WIP) and the lead squashes those commits into its checkpoints; worker
commits never reach the integration branch as-is. **Not adopted:** a hook that recognizes a "worker" context and
waives the ledger gate — it is `--no-verify` with a nicer name, and it would teach adopters that the ledger
gate has exceptions.

**D8 — `--source=github` reads the manifest at the same ref as the content.** `bin/sync` in github mode fetches
`bin/_manifest.py` from GitHub (default ref `main`, optional `--ref <sha|branch>`) and iterates *that* manifest,
so the file list and the file contents are consistent at one ref. Test 9 is unchanged in form and becomes green
on every branch **correctly**: it now tests what an adopter running `--source=github` receives, which is what
`main` publishes. A branch's new distributed file is verified post-merge (S23's procedure). This also fixes a
latent adopter defect — a stale local checkout whose manifest names a file `main` has since removed 404s
today. Rejected alternative: making Test 9 skip on unpushed branches — a SKIP lowers `tests-sh-passed` below its
floor, so the fix would move the red from one gate to another.

**D9 — Worktree-aware calibration.** `context_budget.py --calibrate` derives the transcript slug from the main
worktree's path (`git rev-parse --path-format=absolute --git-common-dir`, git ≥ 2.31, else the relative form
resolved; parent of `.git`) so a linked worktree
finds the project's transcripts; unit test RED-first (a worktree path resolves to the main path). The other
tools are audited for the same assumption and recorded either way (the dashboard's `ROOT = Path(__file__).parent`
is by design; the ratchet's `find_root` is already correct).

**D10 — Runner text is paid by reduction.** `starter-kit/SESSION_RUNNER.md` has **35 tokens** of headroom under
its 18,900-token ceiling (§9). Everything this plan adds to it — the task-map row, the §Vertical Slice pointer
and one-writer sentence, the step-6 `--merges` line, the D6 sentence, and (if D14 is ratified) an FM row and a
Degradation row — is paid for by reduction in the same commit, measured by `context_budget.py --precommit`
**and** the doubled-file Read method (both, per S22's finding that a byte pin can move the other way in tokens).
Candidate reductions, sized: the capability-tiered review paragraph (`:177`, 1,701 B) compressed to its gate
statement with the elaboration moved into the new flight-manual section, cite-don't-restate (~900 B); the
receipt-reconcile paragraph (`:44`, 784 B) tightened once D6 gives it a rule to state instead of a case to
describe (~200 B). The executor measures; this plan only shows the budget closes.

**D11 — Dashboard: one LOW advisory, advisory as always.** When methodology is adopted (ledger + receipts
present) and `git check-attr merge CHANGELOG.md` is `unspecified`: *"ledgers have no merge driver — concurrent
sessions will conflict at the top anchor; see BOOTSTRAP Step 10."* Both twins, `DASHBOARD_VERSION` bump, unit
tests RED-first. Optional; a separate session if Phase 4's sweep is large.

**D12 — Sequencing: v3.8 first, this plan as v3.9.** The v3.8 release entry already owes a reduction in
`CLAUDE.md` (59,153 of 59,168 B; one token of headroom); folding a fan-out feature into it would enlarge the
entry it cannot afford. Phase 1 here is independent of the release and could land before it; nothing else
should.

**D13 — Handoff scoring under Shape B.** Phase 3A scores the newest receipt in **your own sequence** (the one
you branched from). A session that merges another sequence additionally scores that sequence's final receipt in
one line of its own receipt — the only feedback a concurrent line ever gets. Recommended; one sentence in 3A.

**D14 — A failure mode, or a row?** Recommended: append **FM #29 "Shared-tree mutation"** — *dispatch agents
that edit, build, or test in one working tree concurrently; each reads the others' half-states as defects*
(row 1 is the evidence; the operator's standing rule is the countermeasure) — plus its Degradation row (*"a
finding appeared while another agent's build was running in the same tree"*). FMs 1–28 byte-unchanged; the
count moves 28 → 29 with the Learning #7/#10 sweep of every live count claim (`CLAUDE.md:88`, `README.md:239`).
Alternative, on the quality-ratchet plan's D8 precedent: no new FM, a Degradation row only, promote if Phase 5
records a recurrence. The plan recommends the FM because the tendency is specific, observed, and its
countermeasure is a sentence; the operator decides.

**D15 — The manifest under Shape B.** A `.quality-gates.json` conflict is resolved by taking the **tighter**
threshold on every gate, then `--run`; the hook skips the merge by design and the dashboard's history walk
(`tools/methodology_dashboard.py:2074`, `_fold_history` — nearest older version with gates) flags a resolution that went the
other way. `SESSION_NOTES.md` is branch-local, merges by union if declared, and is rewritten by the integrating
session at 3D — it is overwritten every session by definition (`starter-kit/SESSION_NOTES.md:5`).

### Alternatives considered (honest trade-offs, per `ARCHITECTURE_WORKSTREAM.md` §The Architecture Document)

| Decision | Alternative | Pros | Cons | Why not (now) |
|---|---|---|---|---|
| D4 ledger merge | **Changelog fragments** — one file per action in `changelog.d/`, assembled into `CHANGELOG.md` at integration or release (the towncrier / changesets / reno pattern; the industry's standard answer to exactly this conflict) | Conflict-free by construction; no merge driver to honor; per-action files are trivially greppable | A new distributed tool (the assembler); the co-staging hook must accept a fragment; reconcile's frontier (`git log -1 -- CHANGELOG.md`), the dashboard's ledger-lag, `methodology_trim.py`, the seed, T2's transcript and FM #27's text all change; the single-file ledger the audit grep and Phase 0 read depend on becomes two places | Blast radius ~10 files across four tools for a conflict a built-in driver resolves. Revisit only if Phase 5 shows union merges producing defects the checkers miss. |
| D4 ledger merge | **Per-session receipt files** (`handoffs/S24.md`) with `HANDOFFS.md` as an index | Receipts never conflict | Same class of change as fragments for `check-handoff`, the seed, reconcile, and the dashboard's checklist item; and `CHANGELOG.md` still conflicts | The receipt is the smaller problem; union covers both files at once. |
| D4 ledger merge | **Leave it; resolve by hand** (the S21 procedure) | Nothing to build | Every concurrent branch costs one manual union per ledger; the resolution is unchecked (S21's first read was wrong) | This is the status quo the operator called messy. |
| D5 identity | **Claim-time nonce** (`session: S24-7f3a`) or the **claim commit's parent sha** | Collision-proof without coordination | Unreadable in a ledger humans scan; the parent sha is shared by every session cut from one base, so it does not distinguish them | A branch name already names the sequence; the tag is readable and free. |
| D7 worker commits | **A hook that waives the ledger gate in a worker context** (env var or marker file) | Workers commit normally in their worktrees | Indistinguishable from `--no-verify` in enforcement; teaches that the ledger gate has exceptions; a marker file is one `touch` from a bypass on the integration branch | Rejected outright (D7). |
| D8 Test 9 | **SKIP on unpushed branches** | Honest "cannot measure" | Lowers `tests-sh-passed` below its floor — moves the red from `failed` to `passed` | A gate that is red by construction on every branch is the defect, whichever gate carries it. |
| D8 Test 9 | **Declare `tests-sh-failed max 1` on branches** (the S22 shape) | No code change | A standing loosening; `max 1` cannot tell "Test 9 by construction" from "one real failure" | The exact erosion the ratchet exists to refuse. |
| D14 | **Amend FM #26 or FM #17** instead of a new FM | Count stays 28 | Neither row is about *where* agents write; the S163 shape would be a clause in a row about something else, which is how countermeasures get skimmed (FM #3) | Recommended FM #29; the operator decides. |

---

## 5. Target state (after all phases)

- **Shape A is a named session shape** with a seven-gate contract (a–g), one closer, one writer per tree, and
  the ratchet judging every integrated unit — the adopter-S13 pattern written down, and the S163 failure named.
- **Shape B merges clean by construction**: two concurrent sessions claim `S24-alpha` and `S24-beta`, each
  closes out on its own branch, the merge auto-resolves both ledgers, `check-ledger` and `check-handoff --all`
  verify the result, the merging session records the merge as one action, and no receipt is owed per commit.
- **No gate is red by construction anywhere**: Test 9 tests what `main` publishes; the manifest is honored at
  `max 0` on every branch.
- **Every distributed tool works in a linked worktree**, or its limit is recorded.
- Adopters receive: the `.gitattributes` seed, the flight-manual section, the runner pointer, the SAFEGUARDS
  row, the `HANDOFFS.md` sequence-tag paragraph, the `bin/sync` fix, the calibration fix, and (D11) the
  advisory — via `bin/sync`. Canonical-only: `bin/check-ledger`, the tests, this plan.
- **Honest ceiling, stated where the rules land:** the one-writer rule and the contract are instructions; their
  mechanical forms are the harness's isolation and git's push rejection. Union merge never reports a conflict,
  so a semantically wrong merge is caught only by the two structural checkers and the integrating session's
  read. Concurrent sessions on one branch remain unsupported, not prevented.

---

## 6. Phased plan — one phase per session, each with a STOP

**Amended by §8A** — Phases 0, 1, 2, 3, 4 and 6 carry changes listed there (*Phase amendments*). Read §8A before
executing any phase; where it and the text below disagree, §8A wins.

Every phase: Orient → claim (1B, with a sequence tag if not on `main` — dogfooding D5 from Phase 1 on) → one
deliverable → full close-out with receipt and ledger entry (FM #27). RED-first for every new check: watch the
old tree fail the new test before the fix. Verification commands are the ones `main` runs today; new ones are
named where added. Phases 1 and 3 are independent of each other and of the prose; 4 depends on 2; 5 on 1–4.

### Phase 0 — Preconditions (not a session of this plan)
Operator answers §8. v3.8 ships (D12) unless the operator folds this plan in. **DONE:** §8 answered in writing
(a PR comment on this plan's PR suffices); `git tag` shows `v3.8` or the fold-in is recorded.

### Phase 1 — Ledger merge mechanics: `.gitattributes` + seed + `check-ledger` + tests (one session; a pre-declared 2-layer slice at most)
**Layer A (≤5 files):** `.gitattributes` (new; the four `merge=union` lines), `starter-kit/gitattributes` (new
seed), `bin/_manifest.py` (+1 SEED row → `.gitattributes`), `bin/tests.sh` (+ Test: in a scratch repo, two
branches each prepend a ledger entry and a receipt from one base; `git merge` → exit 0, both entries and both
receipts present, `check-handoff --all` green; **RED first** without the attribute the same merge exits 1 with
both files conflicted). Also assert the seed installs via `bin/sync` into a scratch tree and is never
clobbered (`bin/status` reports `present`). Checkpoint commit.
**Layer B (≤5 files):** `bin/check-ledger` (new, python3 stdlib, canonical-only; `--file`, `--all`-equivalent
by default), `bin/tests.sh` (+ Tests: a clean ledger passes; a duplicated entry, a missing source tag, two source
tags, an orphaned body each FAIL — RED first against fixtures), `.quality-gates.json` (+ `check-ledger max 0`,
an addition the ratchet passes; `tests-sh-passed` tightened to measured after). Run `check-ledger` on this
repo's own `CHANGELOG.md` first and fix what it finds or record why not.
**Verification item, in-phase:** open a scratch PR whose branch conflicts with its base only in `CHANGELOG.md`
and observe whether GitHub's merge honors `merge=union`. Record the answer in the ledger entry either way. If
not honored, the S21 procedure — merge `main` into the branch locally, where the driver applies — is the
documented path, and the driver still makes that step conflict-free.
**DONE:** the two-branch merge test is green; `check-ledger` green on this repo; twins untouched; `bin/sync`
into a scratch tree installs the seed.
**Verify:** `bash bin/tests.sh` (139 → 139+N, count stated), `bin/check-links`, `python3
starter-kit/quality_ratchet.py --run` (11/11), `bin/status` over a scratch adopter tree.
**STOP.**

### Phase 2 — Prose: the contract, the hard rule, identity, the merge rule (one session)
Files (≤5 per commit; two commits if the FM is ratified): `ITERATIVE_METHODOLOGY.md` (new `## Parallel Actors`
beside `:345`; Principle 9 paragraph at `:122–132`; one pointer sentence in §Mechanical Gates `:401`; Phase 1
step 4 `:148` gains the `--merges` clause), `starter-kit/SESSION_RUNNER.md` (task-map row after `:69`; step 6
`:18` `--merges` line; `:44` D6 sentence; §Vertical Slice pointer + one-writer sentence at `:175`; FM #29 row
after `:333` and Degradation row after the last row of `:337–365` if D14 is ratified — **all paid by
reduction**, D10), `starter-kit/SAFEGUARDS.md` (D2 row in `:46–54`), `starter-kit/HANDOFFS.md` (D5 paragraph
at `:82–87`; D6 sentence in §How to write a receipt), `starter-kit/FRAMEWORK_LEARNINGS.md` (Learning #17:
*a session may have many hands but one closer; a tree has one writer* — the next free number
`bin/check-learnings` accepts; #14 stays reserved).
**DONE:** every cross-reference resolves; every live count claim is current (FM 28 → 29 if ratified; Learning
#17 appended — rows 15 → 16, #14 still reserved); `context_budget.py --precommit` exit 0 **and** the doubled-file Read of the runner + SAFEGUARDS
pair stays under 25,000 tokens; `bin/check-learnings` green; `bin/check-handoff --all` green.
**Verify:** `bash bin/tests.sh`, `bin/check-links`, `bin/check-learnings`, `grep -rn 'count stays 28\|documents
28 failure' README.md CLAUDE.md` (updated if D14), Learning #7/#10 sweep for *"12 quality gates"* / *"9
principles"* (both still true — nothing added to either set).
**STOP.**

### Phase 3 — Tools: manifest-at-ref for `--source=github`; worktree-aware `--calibrate` (one session)
`bin/sync` (`read_github` fetches `bin/_manifest.py` at the ref and iterates it; `--ref`; `methodology_version`
reports the ref's sha), `bin/tests.sh` (Test 9 unchanged in form; + a test that a branch whose local manifest
names a file absent from the ref is **green** — RED first against the old `sync`, reproduced on a scratch branch
that adds a manifest row), `starter-kit/context_budget.py` (`:867` slug from the common dir; version bump),
`tools/test_context_budget.py` (+ a linked-worktree case, RED first), `.quality-gates.json` (tighten the three
counts to measured after).
**DONE:** Test 9 green on a branch that adds a manifest row (the S22 red, reproduced then fixed);
`--calibrate` from a linked worktree finds the main checkout's transcripts.
**Verify:** `bash bin/tests.sh`, `python3 tools/test_context_budget.py`, `python3 starter-kit/context_budget.py
--selftest`, `quality_ratchet.py --run` at the tightened manifest.
**STOP.**

### Phase 4 — Docs sweep + dashboard advisory (one session; the sweep itself run as a Shape-A fan-out — see Phase 5)
`HOW_TO_USE.md:868–878` (§Multi-Agent Teams cites `## Parallel Actors` and states the two shapes);
`workstreams/TEMPLATE_CAMPAIGN.md:156,225` and `RESEARCH_EXHAUSTIVE_VERIFICATION_CAMPAIGN.md:282–288` (cite
the one-writer rule; cite-don't-restate); `starter-kit/RECOMMENDED_SKILLS.md:75` (the Claude Code mechanism:
`Agent` tool `isolation: "worktree"`; return-content when isolation is unavailable — the *"not in a git
repository"* harness quirk; brand names confined to this file, as the Reasoning Effort table already does);
`starter-kit/BOOTSTRAP.md` Step 10 (the four `.gitattributes` lines for adopters who already have the file);
`README.md` (repo tree; feature list; the count claim); `docs/tutorials/T5_cautionary.md` (one corollary: the
S163 shape, optional). D11 in both dashboard twins with unit tests if ratified. Learning #10 whole-corpus sweep
for every enumeration of *sub-agent*, *parallel*, *worktree*, and the `S<N>` id form.
**DONE / Verify:** `bin/check-links`; `bash bin/tests.sh`; `cmp` of the twins; `grep -rn 'sub-agent\|worktree'
--include='*.md' .` reviewed line by line against the new section.
**STOP.**

### Phase 5 — Dogfood both shapes and measure (one session for Shape B; Shape A's measurement is Phase 4's own session)
**Shape A (measured in Phase 4):** Phase 4's sweep is executed *as* a fan-out under the contract — one unit per
file, disjoint scopes, workers return content, the lead integrates one unit per checkpoint under the full matrix
— and its ledger entry records: units, worker claims re-derived, claims found wrong, integration time, lead
context consumed. If Phase 2's contract is not yet ratified when Phase 4 runs, Phase 4 runs single-tier and the
Shape A dogfood becomes Phase 5's second session on a later doc deliverable.
**Shape B (this phase):** two concurrent sessions in two linked worktrees of this repo, each on a doc-only deliverable
(e.g., two tutorials from the roadmap), claimed `S<N>-alpha` / `S<N>-beta`, each closed out; a third session
merges both. Record: merge exit codes for both ledgers (expect 0), `check-ledger` / `check-handoff --all`
results, whether GitHub honored the driver, receipts owed (expect: one, the merge's).
**DONE:** the counts are in the ledger entries. This is the evidence the release narrative cites — the
methodology's own *"fan-out holds"*, measured, not asserted.
**STOP.**

### Phase 6 — Release (one session)
Minor version (v3.9 under D12): a new flight-manual section, a SAFEGUARDS hard rule, a new SEED, one new
canonical tool, two distributed-tool fixes; the failure-mode count 28 → 29 if D14 is ratified, else unchanged.
Follow the v3.7/v3.8 release procedure: narration commit → PR → merge → annotated tag → `gh release` → ledger
entry completed from real command output, never before the tag exists. `CLAUDE.md` §Versioning entry paid
by reduction against its token pin.
**STOP.**

---

## 7. Honest ceilings — what this plan does not make true

1. **"One writer per tree" is an instruction.** No hook can observe a second agent. The mechanical forms are
   the harness's per-worker isolation (recommended, not shipped) and, for Shape B, git's non-fast-forward
   rejection. A session that fans mutating agents into one tree will still be able to; it will be doing
   something the runner names.
2. **Union merge never asks.** It resolves every ledger conflict silently. The structural checkers catch
   duplication and malformed entries; a merge that *loses* nothing but *orders* oddly is by design; a merge
   that produces two well-formed but semantically overlapping entries is caught only by the integrating
   session reading its own ledger — which Phase 0 already mandates.
3. **GitHub's merge behavior is an assumption until Phase 1 measures it.** The fallback (merge `main` into the
   branch locally first) is the procedure S21 already used; the driver makes that step conflict-free.
4. **Test 9 verified on `main` means a branch's new distributed file is unverified until merged.** That is
   the correct scope for a github-source test; the post-merge verification (S23's) is where the new file is
   checked, and the plan does not pretend otherwise.
5. **Shape B feedback is thin.** D13 gives a merged sequence one score from the merger; nothing scores a
   concurrent session's handoff the way a successor on the same line would. Concurrency trades some of
   Principle 8's compounding for throughput, and the plan says so rather than hiding it.
6. **Presence is still not use.** A `.gitattributes` seed installed is not a merge driver honored on every
   platform; a contract written is not a contract followed. Phase 5's counts are the only evidence that matters.

---

## 8. Open decisions for the operator (answer before Phase 1)

1. **Ratify the framing** (§3, D1): one closer per tree; the session stays the unit of accountability; workers
   are layers, not sessions.
2. **D2 as a SAFEGUARDS hard rule** (recommended) or as a sentence in the runner's §Vertical Slice only.
3. **D4 ordering ruling:** leave union-merged order as merged and close the S19 reorder item (recommended), or
   permit the integrating session to move whole entries by date at close-out (an edit to a prepend-only file).
4. **D5 identity form:** `S<N>-<seq>` (recommended) vs `<seq>/S<N>` vs a claim-time nonce. Bare `S<N>` stays
   the trunk's.
5. **D6:** ratify "a merge is one action with one receipt" and **drop the 11-receipts instruction** by ruling
   (recommended), or write the 11 `reconciled` blocks once and keep the literal rule.
6. **D7 default:** workers produce / lead commits (recommended) vs worker WIP commits squashed by the lead.
   Confirm the "worker context waives the hook" idea stays **not adopted**.
7. **D8:** manifest-at-ref (recommended) vs a `--ref` flag alone vs leaving Test 9 as is and declaring
   `tests-sh-failed max 1` on branches (the S22 shape — not recommended; it is a standing loosening).
8. **D12 sequencing:** v3.8 first, this plan as v3.9 (recommended), or fold Phase 1 into v3.8.
9. **D13:** the merger scores the merged sequence's last receipt (recommended) or Shape B receipts go unscored.
10. **D14:** FM #29 "Shared-tree mutation" (recommended) or a Degradation row only.
11. **D11:** the dashboard advisory — in Phase 4, or not at all.
12. **Scope guard:** this plan does **not** touch the vertical-slice gates (a)–(d), the 6 phases, the 12
    quality gates, the 9 principles, or any workstream's phase adaptations. It adds a section, a rule, a
    seed, a checker, and two tool fixes. Confirm that boundary.

---

## 8A. Decisions — ratified 2026-10-01 (S27)

**Who decided.** The operator delegated these twelve decisions on 2026-10-01 (*"you do it"*); session S27
(Claude, on `main` after v4.0) made them. Each weighs the plan's recommendation, rmsharp's review on PR #83
(2026-09-21), and what changed after the plan was written: v3.8 and v4.0 shipped, and #84–#87 merged. Where a
claim could be computed, S27 measured it (§9A). The operator may reverse any item.

| # | Decision | Ruling | Basis |
|---|---|---|---|
| 1 | Framing (§3, D1) | **Ratified as proposed.** One closer per tree; the session stays the unit of accountability; workers are layers, not sessions. | Plan §1 rows 1–2; rmsharp agrees. |
| 2 | D2 | **Ratified as a `SAFEGUARDS.md` hard rule**, paid by reduction in the same commit. | Headroom **measured at 17 tokens** (6,083 / 6,100), not the plan's 71; #84 used the rest, as rmsharp predicted. The row costs ~70–90 tokens, so nearly all of it is paid by cutting. |
| 3 | D4 ordering | **Ratified: leave union-merged order as merged**; S19's one-time reorder item is closed by this ruling. | Measured (§9A): `union` keeps ours above theirs, so the result is not chronological. *Prepend-only, never re-sorted* already governs. |
| 3′ | D4 scope (rmsharp's main change) | **Amended: `merge=union` for `CHANGELOG.md`, `dashboard_history.jsonl` and `.context-budget-history.jsonl` only. `HANDOFFS.md` gets no merge driver.** Its conflicts stay marked and are resolved keep-both with `git merge-file --union --diff3` on the three index stages, then `bin/check-handoff --all`. | Measured (§9A): two receipts prepended at one anchor merge into **one block with two `session:` lines** under the default conflict style and under `zdiff3`, with merge exit 0. Only `diff3` keeps them whole, and that is per-clone configuration the methodology cannot ship. GitHub's server-side merge is a further unknown. The `--diff3` recipe resolved two real receipt-on-receipt merges cleanly in S26 (#89 and #83 into `main`). The alternatives table's **per-session receipt files** reopens as the fallback if receipt conflicts prove frequent. |
| 4 | D5 identity | **Ratified with rmsharp's wording:** *each repository's `main` uses bare `S<N>`; `S<N>-<seq>` is for other branches in the same repository.* | A fork's `main` is a trunk too (rmsharp's fork: 200+ bare `S<N>`), and `starter-kit/HANDOFFS.md` already keeps fork and upstream numbering separate. |
| 5 | D6 | **Ratified: a merge is one action with one receipt; the 11-reconciled-receipts instruction is dropped.** **Addition:** after a merge, the merging session checks that every merged PR has a ledger entry, and backfills one if not. | rmsharp: the 11 are his PR #80 commits, already in his fork's ledger. The addition is **verified on this repo**: PR #77's `56997af` (2026-09-02) changed only the seed, and no entry in the root `CHANGELOG.md` mentions PR #77. Phase 0's frontier-based gap stopped seeing it once a later commit edited the ledger. |
| 6 | D7 | **Ratified: workers produce, the lead commits.** A hook that waives the ledger gate in a "worker context" stays **not adopted**. | — |
| 7 | D8 | **Ratified as a requirement:** Test 9 must not be red by construction on a branch that adds a distributed file. **Mechanism, adapted to #87:** the github route already clones, so Phase 3 makes it iterate the **clone's** `bin/_manifest.py` (list and contents at one ref), with an optional `--ref`. | #87 clones `main` but still imports the *local* manifest (`bin/sync:15`). A local row the clone lacks is now refused on purpose (`absent_sources`, Test 28), so Test 9 still fails on such a branch. Iterating the source's manifest also fixes a stale adopter checkout missing files `main` added. This changes #87's Test 28 premise, so Phase 3 settles the form with rmsharp first. rmsharp's rate-limit note no longer applies: #87 replaced the ~29 per-file API calls with one clone. |
| 8 | D12 | **Superseded.** v3.8 (2026-09-30) and v4.0 (2026-10-01) shipped without this plan, so it ships as **v4.1** (minor). | `git tag`; §Versioning. |
| 9 | D13 | **Ratified:** the merging session scores the merged sequence's last receipt in one line of its own receipt. | — |
| 10 | D14 | **Ratified: append FM #29 "Shared-state interference"** (the name broadened from "Shared-tree mutation"): *run concurrent actors that edit, build, test, or consume a rate-limited service against shared state — one working tree, one build directory, one quota — and each reads the others' side effects as defects.* Plus its Degradation row. FMs 1–28 byte-unchanged; count 28 → 29 with the Learning #7/#10 sweep. | Plan §1 row 1 (adopter S163). rmsharp saw the tendency twice more: a review agent writing into the distributed `starter-kit/CHANGELOG.md` in a shared tree, and two concurrent suites tripping GitHub's secondary rate limit while sharing no tree. *Shared state* covers all three; *shared tree* covers one. |
| 11 | D11 | **Deferred until after Phase 5**; removed from Phase 4. | rmsharp: a permanent LOW advisory on every single-sequence project is a report nothing acts on. Phase 5's counts decide whether it earns a place. |
| 12 | Scope guard | **Confirmed, with corrected wording:** this plan *adds none, removes none and renumbers none* of the 9 principles, 6 phases and 12 quality gates. *It amends Principle 9 by one paragraph and Phase 1 step 4 by one clause.* It does not touch the vertical-slice gates (a)–(d) or any workstream's phase adaptations. | rmsharp: the original wording said the plan does not touch the principles or phases, which D1 and D6 contradict. |

**Unchanged by §8:** D3, D9, D10 and D15 stand as written, with two notes:

- **D10:** the runner's headroom is measured at **42 tokens** (18,858 / 18,900).
- **D15:** observed once in practice. S26 resolved a `.quality-gates.json` conflict between #86 and #87 by taking each gate's tighter `min`.

**Phase amendments (these override §6):**

- **Phase 0** is done: §8 is answered here. The D12 clause is replaced by item 8.
- **Phase 1 Layer A:**
  - `.gitattributes` gets **three** `merge=union` lines, without `HANDOFFS.md`.
  - The two-branch test expects:
    - `CHANGELOG.md` to merge with exit 0 and both entries whole;
    - `HANDOFFS.md` to **conflict**, and the documented `git merge-file --union --diff3` recipe to resolve it with `check-handoff --all` green.
  - RED first: the same test with `HANDOFFS.md` under `union` must show the fused block.
  - Add the **trim-against-prepend** case for `CHANGELOG.md` under `union`, with the real trimmer at its smallest cuts (§9A: green at `--cut 1` and `--cut 3`). The trimmer refuses `--cut 0` (`CUT_OUT_OF_RANGE`: it must retain at least one record; exit 3).
- **Phase 1 Layer B:** `bin/check-ledger` accepts a `###` heading directly under the previous entry's last line, because `union` drops that blank line (measured). The trimmer already accepts such a ledger (§9A).
- **Phase 2:**
  - D5 and D14 use the wording above.
  - D6 carries the merged-PR check.
  - The scope sentence uses item 12's wording.
  - SAFEGUARDS has 17 tokens of headroom and the runner 42.
- **Phase 3:** D8 as adapted above, starting from #87's clone. Test 28's semantics change, so coordinate with rmsharp first. D9's slug line is now `starter-kit/context_budget.py:891`.
- **Phase 4:** D11 is dropped (item 11).
- **Phase 5:** concurrent suites no longer contend for GitHub API quota (#87 clones), but still share the network. Keep the rule: run suites one at a time.
- **Phase 6:** the release is **v4.1**.

**Found while deciding, not acted on here:**

- PR #77's `56997af` is an unrecorded action in this repo's ledger (failure mode #27). It needs a backfill entry.
- This repo's `CHANGELOG.md` is 226,217 B, past the trimmer's 196,608 B archive trigger, so a trim is due. `methodology_trim.py --cut 3` dry-runs green: L1–L3 OK, 101 of 104 records to `docs/archive/`.

### 9A. Commands that produced §8A's measurements (S27, `main` @ `934975a`)

```sh
# D4 (rmsharp's objection): two receipts prepended at one anchor, HANDOFFS.md merge=union, three conflict styles
#   scratch repo; base = one receipt; branches alpha/beta each prepend one; git -c merge.conflictStyle=<s> merge
#   merge:  rc 0, 2 ```handoff fences for 3 session: lines  -> FUSED
#   diff3:  rc 0, 3 fences / 3 sessions                     -> whole
#   zdiff3: rc 0, 2 fences / 3 sessions                     -> FUSED
# D4 (trim vs prepend): scratch clone of main; CHANGELOG.md merge=union via .git/info/attributes
python3 starter-kit/methodology_trim.py --file CHANGELOG.md --cut 1 --write   # branch A (also --cut 3)
#   branch B prepends one entry under "## 2026-10"; git merge -> rc 0; live entries = kept + 1; no archived record back
#   the merged ledger: methodology_trim.py --check rc 0; a dry-run re-trim reports L1_OK L2_OK L3_OK
#   one blank line lost between the two entries (a ### directly under the previous body)
# D2 / D10 headroom
python3 starter-kit/context_budget.py --status --json   # SAFEGUARDS 6083/6100 tokens; SESSION_RUNNER 18858/18900
# D8 after #87
sed -n '15p;97,128p' bin/sync                             # local manifest import; clone_source; absent_sources
# D6 addition
git show --stat --format= 56997af | grep CHANGELOG       # only starter-kit/CHANGELOG.md (the seed)
grep -n 'pull/77\|PR #77' CHANGELOG.md                   # no match
```

---

## 9. Commands that produced the evidence (re-runnable by the executor)

```sh
cd methodology                                                        # main @ 6b29d3d (branch docs/parallel-sessions-plan @ 3c244aa)
git check-attr merge CHANGELOG.md HANDOFFS.md                         # both: merge: unspecified (no .gitattributes exists)
ls .gitattributes                                                      # No such file or directory
sed -n '21,27p;50,55p' .githooks/pre-commit                            # merge/rebase skip; CHANGELOG.md co-staging rule
sed -n '9p;82,87p' starter-kit/HANDOFFS.md                             # one block per session, newest on top; identity = session + date
sed -n '17p;91p' starter-kit/CHANGELOG.md                              # newest on top; "prepend-only, so close-out never re-sorts"
sed -n '214,230p' bin/check-handoff                                    # identity pair; `session:` unconstrained
sed -n '18p;35,44p' starter-kit/SESSION_RUNNER.md                      # Phase 0 step 6; reconcile mechanics; the HANDOFFS clause
sed -n '1386,1389p' tools/methodology_dashboard.py                     # ledger-lag: rev-list --count --no-merges <frontier>..HEAD
sed -n '116,126p' bin/tests.sh; sed -n '78,90p' bin/sync               # Test 9; read_github fetches contents at the default branch
sed -n '867,868p' starter-kit/context_budget.py                        # transcript slug from Path(root).resolve()
sed -n '72,89p' starter-kit/quality_ratchet.py                         # find_root via git rev-parse --show-toplevel (worktree-correct)
sed -n '175p;177p' starter-kit/SESSION_RUNNER.md | wc -c               # 199 B; 1,701 B — the reduction candidates
python3 starter-kit/context_budget.py --json | python3 -c "import json,sys; [print(f['path'], f['tokens'], '/', f['max_tokens']) for f in json.load(sys.stdin)['files']]"
                                                                       # SESSION_RUNNER.md 18865/18900 (35 tokens headroom); SAFEGUARDS.md 6029/6100 (71)
rm -f .context-budget-history.jsonl                                    # the --json run writes it; not tracked here
python3 -c "import sys; sys.path.insert(0,'bin'); import _manifest as m; print(len(m.DISTRIBUTION))"   # 29
git show 6b29d3d:CHANGELOG.md | grep -n '11 `status: reconciled`'     # :293 — the 11 deferred receipts (S19)
grep -n 'CONFLICTS in CHANGELOG.md AND HANDOFFS.md' HANDOFFS.md        # the S21 DERIVED clause
python3 -c "import json; [print(g['name'], g['direction'], g['threshold']) for g in json.load(open('.quality-gates.json'))['gates']]"   # 10 gates; tests-sh-failed max 0
sed -n '868,878p' HOW_TO_USE.md                                        # §Multi-Agent Teams — four bullets, two sentences
sed -n '268,296p' workstreams/RESEARCH_EXHAUSTIVE_VERIFICATION_CAMPAIGN.md   # Sub-Agent Dispatch Pattern; When to fan out
git rev-list --count v3.7..HEAD                                        # 68 unreleased commits on main
```

Adopter evidence (rows 1–2 of §1) is in that project's `SESSION_NOTES.md` and `CLAUDE.md` under sessions S13
(2026-06-17) and S163; the operator holds the path. The mechanics quoted are the whole of what this plan uses.
