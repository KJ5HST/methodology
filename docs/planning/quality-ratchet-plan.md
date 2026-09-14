# Quality-Ratchet Plan — what the methodology should take from CampusIQ's Forseti layer, and what it should not

**Date:** 2026-09-14 (methodology session S13; recomposed from a planning session earlier the same day)
**Status:** DRAFT — a planning-session deliverable awaiting maintainer ratification. Nothing here is implemented.
**Workstream:** Planning (`starter-kit/SESSION_RUNNER.md` §Planning Sessions) — the plan is the deliverable.
**Source under study:** Aaron Benz, *"Everybody Ships: How CampusIQ Built an AI-Native Company"*,
<https://campusiq.com/blogs/everybody-ships> (announced on LinkedIn:
<https://www.linkedin.com/posts/aaron-benz_everybody-ships-how-campusiq-built-an-ai-native-activity-7503578276444119041-yPZM>).
**Trigger:** the maintainer's question, on reading the article, of how a methodology derived from individual
high-performance disciplines (competitive pistol coaching, flight training) — which has not transferred to
teams of agents — could keep quality and honesty high *and measurable* while scaling to many actors. The
article is the material here; nothing below rests on any other account of CampusIQ's practice.
**Evidence discipline:** every claim about the methodology carries a `file:line` on `main @ 512c2ed`
(post-v3.7) or the command that produced it (§9); every claim about CampusIQ is a verbatim quote from the
article, which is the sole source.
**Sequencing constraint:** PR #80 (`read-set-budgets`, open since 2026-09-10) relocates the Learnings table
and the flight manual's apparatus. Anchors are given for both states; **no phase of this plan executes until
#80 is merged or declined** (§4 D10, §6 Phase 0).

---

## 0. The answer in one paragraph

**CampusIQ scales quality by enforcing it on the artifact; the methodology enforces it on the actor.**
At CampusIQ every change — from any of 4 engineers, 17 non-engineers, or an agent — passes *the same*
130+ mechanical checks, with thresholds that only tighten, and a human decides ship/no-ship on three
questions. The methodology's 12 quality gates, 28 failure modes and 13 learnings are all answered by the
session's own judgment and recorded by the session's own hand. That is why it is excellent for one
disciplined agent and has not transferred to N: **a self-certified gate does not scale, it multiplies**,
and a stronger adversarial reviewer is one more self-certifying actor, not a measurement. The methodology
has already discovered this principle *once* — v3.7's "why a gate and not a report" (`CLAUDE.md`
§Versioning, v3.7), Learning #12, the ledger co-staging hook, and `context_budget.py`'s ratchet — but
applied it only to its own **records** and its own **context size**, never to the **code** it governs.
The plan below closes that gap without shipping a linter: the methodology should ship the *ratchet*,
not the *ruler*.

---

## 1. Source

Aaron Benz, *"Everybody Ships: How CampusIQ Built an AI-Native Company"*, campusiq.com
(<https://campusiq.com/blogs/everybody-ships>; team figures stated as of 2026-06-04). Facts and verbatim
quotes used below:

- 21 people, **4 engineers** (CEO excluded); the experiment ran ~16 months from early 2025.
- "Second Brain": 11 departmental "lobes", 565 skills, 47 tools; named services **Bifrost** (credentials),
  **Mimir/CASS** (memory/context), **Huginn** (execution), **Heimdall** (telemetry), **Forseti** (quality).
- Quality: *"More than 130 checks run before work gets through, with the same engineering gates in place
  for everyone."*
- The gate: *"The robots can do the work and run the technical checks, but a person still decides whether
  something should ship. Every change comes back to three things: what changed, why it changed, and what
  the risk is. If no one responds within two days, human approval can pass by default. The automated
  checks never do."*
- Coverage: *"Our coverage floor is now 90%, which means some of the work we were comfortable shipping a
  year ago wouldn't make it through today."*
- Failure mode 1, "The Slop Will Bury Us": *"AI can produce a lot of work very quickly, including work
  that looks finished when it isn't. At this volume, there's no way a person can catch everything by
  simply paying closer attention. So every change goes through the same gates, with automated builds and
  testing, mandatory human review, more than 130 automated checks, and sandboxed runs for agents. We have
  data showing quality holds as volume grows. We just haven't published it yet."*
- Failure mode 2, "The Demo Becomes the Product": *"building something quickly and deciding it belongs in
  production are two different things. That second decision still belongs to a person."*
- Heimdall: *"Usage and telemetry that show us who's getting value from the system, where people are
  getting stuck, and where they might need help."*
- Throughput: *"79.3 PRs / Average per developer per week, against a 75 PR floor."* Q2 2026: 4,106 PRs
  merged; median 2.4 h open→merge; 88% within 24 h; ~$29 token cost per PR. Q1 2025 → Q1 2026: 371 →
  6,163 merged PRs. Median change 447 lines; 5.9% of merges trivial. Non-engineers: 1,026 PRs in 12 months.
- Adoption: a ~2-month lag between the first adopter and the rest of the team; "the valley" (early win,
  then a plateau when the tool's limits and the learning curve coincide).

**Unverified claim to carry:** *"We have data showing quality holds as volume grows. We just haven't
published it yet."* Nothing below rests on that data; §6 Phase 5 has the methodology measure its own.

---

## 2. The CampusIQ model, decomposed, against the methodology as it stands

Ten mechanisms. For each: the nearest thing the methodology already has, with evidence, and a status.
"Present-for-records" means the mechanism exists but is applied only to the methodology's own artifacts
(ledger, receipts, context size), never to the code the methodology governs.

| # | CampusIQ mechanism (source) | Nearest existing element in the methodology (evidence on `main @ 512c2ed`) | Status |
|---|---|---|---|
| 1 | **Same gates for every actor** — *"the same engineering gates in place for everyone"* (article) | Capability-tiered review, `starter-kit/SESSION_RUNNER.md:177`: *"delegate a layer to a lighter/faster tier only when its correctness rests on an objective, checkable gate … the gate proves correctness, not the tier's judgment"*; Learning #11 (`:383`). But it is **elective**, scoped to pre-declared vertical slices, and keeps *review itself* on the strongest tier. | Partial — the principle exists as an exception, not a rule |
| 2 | **Enforce via CI; checks never pass by default** (article) | Two shipped gates, both for records: `.githooks/pre-commit` (67 lines; refuses a commit without `CHANGELOG.md` co-staged, FM #27) and `starter-kit/context_budget.py --precommit` (`:504–535`). Code checks are `BOOTSTRAP.md` **Step 10 "(Optional)"** (`:310`): *"The methodology works without hooks"*; *"what matters is that some check runs before the commit, not which one"* (`:318`). | Present-for-records; optional and threshold-free for code |
| 3 | **A numeric quality threshold, published** — *"Our coverage floor is now 90%"* (article) | `grep -rn -i 'cyclomatic\|coverage floor\|LOC cap' --include='*.md' --include='*.py' .` → **0 hits** as a rule for governed code. The only numeric caps are the scanner's doc-only heuristic (`tools/methodology_dashboard.py:260`, `DOC_ONLY_SOURCE_LOC_MAX = 200`) and context-budget ceilings. `workstreams/DEVELOPMENT_WORKSTREAM.md:217` has a hand-filled "Code Health Metrics — File / Test Coverage / Complexity" table template; `:105` asks *"What's the current standard? (Test coverage target …)"* as a question with no answer. | **Absent** |
| 4 | **Ratchet** — *"some of the work we were comfortable shipping a year ago wouldn't make it through today"* (article): the floor has moved up, not down | `context_budget.py:504` — *"Relative rule: refuse only when the staged file is over ceiling AND larger than HEAD. A commit that reduces an over-budget file must never be blocked, or the tool prevents its own remedy."* `growth_run` (`:249`) *"survives someone raising a ceiling to silence a warning."* "Raise the ceiling" is deliberately the **last** remedy (`:275`). The nearest general rule is `starter-kit/SAFEGUARDS.md:53`, *"'Refactoring' always requires plan mode approval"* — nothing says the same of loosening a threshold. | Present for **one** dimension (document size); absent as a rule |
| 5 | **A check set that grows** — *"more than 130 checks"* (article); the question for the methodology is what a wrong answer becomes: a new check, or a new instruction | Learning #12 (`SESSION_RUNNER.md:384`): *"When an invariant is mechanical, encode it as a test — a review-time grep is a human step that silently stops happening."* But the failure-mode catalogue is the opposite pattern: 28 wrong answers turned into **instructions**. Distributed mechanical enforcement exists for **2 of 28** (#27 → the hook; #28 → `context_budget.py`); `bin/check-handoff` structurally checks the receipt (the artifact of #6/#14/#15) but is canonical-only; the other 23 bind by text alone. | Partial — stated as a Learning, practised for 2/28 |
| 6 | **Measure quality over time** — Heimdall telemetry; a coverage floor with a number; *"data showing quality holds as volume grows"* (article) | `methodology_dashboard.py` scores `test_to_source_ratio` (`:2055`) and **coverage-config presence** (`collect_coverage_config`, `:1679`; `:2067`) — never a coverage number, complexity, or lint result; `README.md:310`: *"presence is still not use."* The Performance Comparison Table (`ITERATIVE_METHODOLOGY.md`; moving to `FRAMEWORK_APPARATUS.md` §Performance Tracking on #80) is **self-reported**. | Partial — proxies for presence, self-reported for quality |
| 7 | **Human decides ship/no-ship on what / why / risk** (article) | Gate 6 "Stakeholder Approval" sits **before** implementation (`ITERATIVE_METHODOLOGY.md:421–436`); there is no symmetric acceptance gate after it. The receipt (`starter-kit/HANDOFFS.md` spec) has no `risk` field. | Partial — pre-work only |
| 8 | **Two-day default approval for humans** (article) | No equivalent. FM #17 (protocol erosion) and FM #24 (build-passes-ship-it) describe why the methodology would refuse it. | **Do not adopt** (§4 D7) |
| 9 | **Sandboxed runs for agents** (article) | `starter-kit/SAFEGUARDS.md` Blast Radius rules (`:42–53`) are textual; `/git-guardrails-claude-code` is a *recommended* mechanical form (`starter-kit/RECOMMENDED_SKILLS.md:27`). | Partial — textual |
| 10 | **565 skills with no published evaluation mechanism**, and a **PR-throughput floor** (article) | No eval system on either side — nothing to learn yet. Throughput: v3.7's own finding is *"throughput is the wrong tell … what degrades is task selection, not volume"*; an adopter of this methodology ran green on velocity for thirteen sessions while nothing reached a user. | Evals: not yet. Throughput floor: **do not adopt** |

**Read across the table:** every row where the methodology is "present" is a row about the methodology's
*own* artifacts. Rows 3–6 — the ones about the *governed code* — are absent or self-reported. That is the
whole finding, stated as an inventory.

---

## 3. The finding — why the methodology has not scaled to N agents

### 3A. All twelve gates are questions the actor asks itself

`ITERATIVE_METHODOLOGY.md:421–436` lists the 12 quality gates. Read the "Question It Answers" column:
*"Have I read everything I need…?"*, *"Have I run the code and verified it works…?"*, *"Did I break
anything…?"*, *"Have I scored the previous session's handoff…?"* Ten of twelve are first-person
self-certifications. The two with a mechanical component — Gate 1 (ledger reconcile) and Gate 2 (the
1B stub) — are, again, about the record. Gate 8 "Runtime Verification" and Gate 9 "Cross-Artifact
Verification" are the two that *could* be properties of the artifact, and both are answered by the session
saying so; `bin/check-handoff` verifies that the `runtime_smoke` field is present and non-placeholder,
*"never semantic quality"* (v3.3 narrative).

With one disciplined agent, self-certification plus bidirectional handoff scoring works — the v3.x
release history is the proof. With N agents, each self-certified gate becomes N self-certifications, and
the handoff-scoring loop that keeps one agent honest has no cross-agent form. **A stronger adversarial
reviewer does not change the class of the gate** — it moves the judgment to a better judge. It is still
judgment, still unmeasured, and the methodology's own text already says so: capability-tiered review is
*"additional evidence, not a substitute, for gate (c)'s build/test matrix"* (`SESSION_RUNNER.md:177`).
That is the precise, non-mystical reason the maintainer's experiment with a stronger model tier running
adversarial reviews did not measure up to single-agent sessions: it raised the ceiling on judgment
without adding a single measurement.

### 3B. CampusIQ's gates are properties of the artifact, and that is what transfers

A check that the build passes, that coverage is at or above a floor, that a lint rule holds, is true or
false of the *change* regardless of who or what produced it. It cannot be argued
with, it costs the same at N = 1 and N = 40, and it runs without consuming any actor's context or
discipline. **The gate set is the only part of a methodology that transfers to N actors unchanged.** The
methodology already knows this in one place — *"the gate proves correctness, not the tier's judgment"* —
and confines it to an elective clause for vertical slices.

### 3C. The methodology has already measured that instructions lose to gates

v3.7's narrative (`CLAUDE.md` §Versioning): *"`methodology_dashboard.py` already printed `Large files
detected` at every Phase 0 by protocol mandate and 15+ consecutive sessions read past it — the signal was
never missing, nothing gated on it."* And FM #28: the artifacts a session must read grow monotonically
because every phase tells a session to *write* and none tells it to *reduce*. The consequence for this
plan is structural, not stylistic: **an instruction is paid for on every session; a gate is paid for only
when it fires.** Each failure mode that can be converted into a check removes a mandatory-read line —
which is exactly the pressure PR #80 is relieving by hand today. That is a plausible mechanism for why a
check set of this kind works on agents at all: a fast, specific, unarguable failure signal outperforms a
long description of what to avoid.

### 3D. Honesty, made measurable

The question that started this was how to keep *honesty* high and measurable while scaling. Under a
mechanical gate the answer splits cleanly:

- For every property a gate expresses, honesty **stops being load-bearing**. A check is not persuaded.
  FM #16 ("False credit / fabrication") cannot occur about coverage if the number comes from the tool.
- For every property no gate expresses — *why* it changed, what the *risk* is, whether it should ship —
  honesty remains load-bearing, and that is exactly the residue CampusIQ keeps a human on.
- Honesty therefore becomes **countable**: the rate at which a session's durable claims (receipt fields,
  ledger entries) are contradicted by the gate artifact. Today `runtime_smoke` is free text and the
  checker validates shape, not truth. If the receipt must *cite* the gate run (a hash, a CI URL, a
  results file) and Phase 0 reconcile compares the claim to the artifact, a false claim is a detectable
  event, in the same class as an unrecorded commit. Ceiling, stated plainly: a session can still be
  dishonest about ungated things; the point is to shrink that set and count the rest.

### 3E. Where CampusIQ's model needs the methodology (the learning runs both ways)

- **Coverage floors are gameable by the actors they gate.** An agent that must clear a floor will write
  tests that assert nothing. The published list has no faithfulness guard; the methodology has the concept
  (FM #24; "faithful verification" in the vertical-slice gates; and a maintainer review session on
  2026-08-01 that mutation-tested a green suite three ways and found it blind to the file under review —
  *mutation-test the suite before citing it as coverage*). Any adopted coverage floor must ship beside a
  faithfulness check (mutation score, assertion density, or a mutation spot-check at review) or it becomes
  FM #24 at scale.
- **The two-day default approval is FM #17 with a timer.** It is a throughput valve that trades review
  coverage for flow. Not adopted.
- **A PR-count floor is the metric the methodology has evidence against** (§2 row 10). Not adopted.
- **"130 checks" is a count, not a target.** Learning #12's phrasing is better: encode each *invariant*;
  the count follows.
- **The demo-becomes-the-product decision** ("that second decision still belongs to a person") is Gate 6
  after the fact. A maintainer assessment of an adopter's delivery failure (2026-07-19) independently
  asked for exactly this acceptance gate; that remains a separate plan (§8, decision 7).

---

## 4. Design decisions (proposed — each is the maintainer's to ratify or reverse)

**D1 — Ship the ratchet, not the ruler.** *Methodology recommends; methodology does not reimplement*
(9 sites corpus-wide). The methodology ships **no** linter, complexity tool or coverage runner. It ships
(a) a declared, machine-readable gate manifest per project, (b) a small stdlib checker that refuses any
commit which *loosens* a declared threshold — the same relative rule `context_budget.py:504` already
implements for one dimension — and (c) prose that makes "same gates for every actor" a rule rather than
an exception. Which tools produce the numbers is the project's choice, listed tool-agnostically in
`BOOTSTRAP.md` Step 10 exactly as the pre-commit paragraph already lists hook runners.

**D2 — One new SEED + one new TRACKED file, on the `context_budget` precedent.**
`starter-kit/quality-gates.json` (SEED → adopter root `.quality-gates.json`; adopter-owned, never
clobbered) and `starter-kit/quality_ratchet.py` (TRACKED → adopter root). The manifest declares, per gate:
`name`, `direction` (`min`|`max`), `threshold`, and optionally `command` + `extract` (a regex that pulls
the measured number from the command's output). Two modes: `--precommit` (refuse a staged manifest whose
thresholds are looser than `HEAD`'s; a commit that *tightens* always passes; a commit that *adds* a gate
always passes) and `--run` (execute declared commands, extract, compare, print a table, write a results
file). Single-purpose, ≤ ~400 lines, `--selftest`, no dependencies — the shape of the hook the methodology
already ships.

**D3 — The ratchet is a SAFEGUARDS hard rule.** Add one row to the Blast Radius table
(`starter-kit/SAFEGUARDS.md:46–53`): **"Never loosen a declared quality threshold to make a change pass —
loosening requires plan-mode approval"**, with the why: *a threshold that can be lowered under pressure is
a suggestion; the ratchet is what makes "wouldn't make it through today" true a year later.* Parallel in form to
`:53` ("Refactoring always requires plan mode approval"). Tightening needs no approval.

**D4 — "Same gates for every actor" becomes a principle-level statement, not a slice-only clause.**
Amend `ITERATIVE_METHODOLOGY.md` with a short section beside §Matching Reasoning Effort to Stakes (`:389`)
— working title **§Mechanical Gates Bind Every Actor** — stating: (i) verification a gate expresses is
never re-done by judgment and never waived by tier, agent, or human; (ii) judgment is reserved for what no
gate expresses — what changed, why, and the risk — and that decision belongs to the stakeholder *after*
implementation as well as before; (iii) automated checks never pass by default or by timeout; (iv)
thresholds only tighten (D3). Cross-reference the existing capability-tiered paragraph rather than
duplicating it. **No principle is renumbered; no phase or gate is added** — the same class of change as
v2.9's reasoning-tier section.

**D5 — "A wrong answer becomes a check" becomes a close-out routing rule.** Phase 3C already routes learnings
(adopter → `CLAUDE.md` Adaptations; canonical → the table). Add the mechanical branch: *if the learning
is a mechanical invariant, it is a gate — declare it in `.quality-gates.json` (or a test) and write the
row as a one-line pointer to the gate.* This is Learning #12 generalized from "test" to "gate", and it is
the decay term FM #28 says the methodology lacks: a gate does not grow the mandatory read. After #80,
new rows must fit `ROW_BUDGET_BYTES = 1500` (`bin/check-learnings:106` on that branch).

**D6 — The dashboard measures gate outcomes, advisory as always.** If `.quality-gates.json` exists, read
it; if a results file exists, read that. New advisory risks: *"N declared gates, never run here"*,
*"threshold `<name>` loosened since `<sha>`"* (derivable from `git log -p -- .quality-gates.json`,
git-only, no project command executed by the scanner), *"measured `<name>` below declared floor"*.
The testing dimension may award points for **measured** coverage over **configured** coverage — the
first time the scanner scores a number rather than a file's existence. The dashboard remains *"advisory —
never a hard gate"*; the gate is the pre-commit/CI check, where it belongs.

**D7 — Not adopted, and recorded so the question is not re-opened by the next session:** the two-day
default human approval; a PR-throughput floor; "130 checks" as a target; any coverage floor without a
faithfulness check beside it (§3E); shipping a specific linter/complexity tool.

**D8 — No new failure mode.** Gate erosion — loosening a threshold to pass — is FM #17 (protocol erosion)
in mechanical form. Amend FM #17 with one clause (precedent: its v2.7 anti-erosion clause) and add one
Degradation-Detection row (*"a declared threshold was loosened in the same commit that needed it"*).
FMs 1–28 stay byte-unchanged and the count stays 28. This is a judgment call worth contesting; the
argument for FM #29 is that "threshold loosening" will be the single most common way agents defeat the
ratchet and may deserve its own name.

**D9 — Honesty becomes a receipt citation.** `runtime_smoke` and `what_was_done` may cite a gate run
(results-file hash, CI run URL, or the `--run` table's summary line). `bin/check-handoff` gains a lint
that the citation resolves when a manifest exists in the repo; Phase 0 reconcile compares the newest
receipt's claim to the newest results. Ceiling stated in the docs, as v3.3 did: structure, not truth,
for anything no gate expresses.

**D10 — Sequencing.** Nothing lands before PR #80 is decided. #80 moves the Learnings table to
`starter-kit/FRAMEWORK_LEARNINGS.md` and the apparatus (including Performance Tracking) to
`FRAMEWORK_APPARATUS.md`, and grows `bin/_manifest.py` 24 → 27 rows; every prose phase below touches one
of those anchors. Executing this plan against `main` today would guarantee a conflict with a PR the
maintainer has not yet reviewed.

---

## 5. Target state (after all phases)

An adopter's root after `bin/sync`:

```
.quality-gates.json        # SEED — adopter-owned; declares gates + thresholds (+ optional commands)
quality_ratchet.py         # TRACKED — --precommit (ratchet), --run (measure), --status, --selftest
.githooks/pre-commit       # unchanged ledger gate; BOOTSTRAP shows chaining the ratchet after it
SAFEGUARDS.md              # + one Blast Radius row (D3)
SESSION_RUNNER.md          # FM #17 clause; Degradation row; Phase 3C mechanical-branch routing (D5, D8)
docs/methodology/ITERATIVE_METHODOLOGY.md   # + §Mechanical Gates Bind Every Actor (D4)
```

Canonical repo: the same files under `starter-kit/`, `bin/_manifest.py` +2 rows, `bin/tests.sh` +N
checks, dashboard twins byte-identical at a bumped `DASHBOARD_VERSION`, and — because this repo
dogfoods — its own `.quality-gates.json` declaring the gates it already has (`bin/tests.sh` green,
`check-links`, `check-learnings`, `check-handoff --all`, unit suite count ≥ 211, `ROW_BUDGET_BYTES`).

---

## 6. Phased plan — one phase per session, each with a STOP

Every phase: Orient (Phase 0) → claim (1B) → one deliverable → full close-out with receipt and ledger
entry (FM #27). Verification commands are the ones `main` already runs; new ones are named where added.

### Phase 0 — Precondition (not a session of this plan): decide PR #80
Review and merge or decline #80. **DONE:** `gh pr view 80 --json state` is `MERGED` or `CLOSED`.
Everything below assumes merged; if declined, the Learnings anchor stays `starter-kit/SESSION_RUNNER.md:367–388`
and the row-budget constraint in D5 is dropped.

### Phase 1 — Prose: principle, hard rule, FM #17 clause, degradation row, Learning row (one session)
Files (≤ 5): `ITERATIVE_METHODOLOGY.md` (new §, beside `:389`), `starter-kit/SAFEGUARDS.md` (`:46–53`
table row), `starter-kit/SESSION_RUNNER.md` (FM #17 row `:319`; Degradation table `:334–366`; Phase 3C
routing `:217–234`), `starter-kit/FRAMEWORK_LEARNINGS.md` (a new Learning row — take the next free number
that `bin/check-learnings` accepts; other in-flight work may have reserved #14), `HOW_TO_USE.md` if it
enumerates SAFEGUARDS rules (grep first — Learning #7/#10 sweep).
**DONE:** the four changes exist, every cross-reference resolves, no count claim is stale.
**Verify:** `bash bin/tests.sh` (all green, count unchanged or +N stated), `bin/check-links`,
`bin/check-learnings`, `grep -c 'does not reimplement'` unchanged, `grep -n 'count stays 28'` across
README/CLAUDE unchanged (no FM added), Learning #7/#10 whole-corpus sweep for "12 quality gates" /
"9 principles" (must still be true — nothing was added to either set).
**STOP.** Separate session.

### Phase 2 — Tool: `quality_ratchet.py` + `quality-gates.json` seed + manifest + BOOTSTRAP Step 10 (one session, possibly a pre-declared 2-layer vertical slice)
Layer A: the checker with `--precommit`, `--selftest`, `--status`; manifest rows (+2, 27 → 29 after #80);
`bin/tests.sh` checks: sync distributes it, seed is not clobbered, a loosened threshold is REFUSED, a
tightened one passes, an added gate passes (RED-first). Layer B: `--run` with `command`/`extract`,
writing a results file (default gitignored — see §8 decision 2); `BOOTSTRAP.md` Step 10 retitled from
"(Optional)" to "(Recommended)" with the ratchet chained after the ledger hook and a tool-agnostic table
(Python: `coverage report --fail-under`, `radon cc`, `ruff`; Node: `c8`/`nyc`, `eslint complexity`;
Rust: `cargo llvm-cov`, `clippy`; JVM: JaCoCo, PMD). If declared as a slice: gate (a) contract names both
layers; checkpoint commit after A.
**DONE:** `python3 starter-kit/quality_ratchet.py --selftest` green; `bin/tests.sh` +≥5 checks green;
`bin/sync` into a scratch adopter tree installs both files; a loosened threshold cannot be committed there
without `--no-verify`.
**Verify:** the commands above plus `bin/check-links` (BOOTSTRAP edits) and `bin/status` over a scratch tree.
**STOP.**

### Phase 3 — Dashboard: score gate outcomes, advisory (one session)
`tools/methodology_dashboard.py` + `starter-kit/` twin: read `.quality-gates.json`; git-only loosening
detection; advisory risks (D6); measured-coverage points in `score_health` (`:2029`); `DASHBOARD_VERSION`
bump; unit tests in `tools/test_methodology_dashboard.py` (RED-first for: manifest absent → silent;
manifest present + no results → "never run" advisory; loosening in history → risk; measured ≥ floor → points).
**DONE:** unit suite 211 → 211+N green; `cmp starter-kit/methodology_dashboard.py tools/methodology_dashboard.py`
byte-identical; `bin/tests.sh` version-equality check green; the maintainer's live portfolio re-scanned and
the delta reported (expect: 0 repos change class; only repos with a manifest gain risks/points).
**STOP.**

### Phase 4 — Workstreams + honesty citation (one session)
`workstreams/DEVELOPMENT_WORKSTREAM.md:217` Code Health Metrics → "generated by `quality_ratchet.py --run`,
not hand-filled"; `:105` gets its answer ("the declared floor in `.quality-gates.json`");
`workstreams/AUDIT_WORKSTREAM.md` gains "every finding that is a mechanical invariant becomes a declared
gate" beside anti-pattern #9; `starter-kit/HANDOFFS.md` receipt spec documents the gate-run citation form;
`bin/check-handoff` lint for a resolvable citation when a manifest exists (D9).
**DONE / Verify:** `bin/check-handoff --all` green on this repo's receipts (the newest must cite this
repo's own gate run); `bin/check-links`; `bin/tests.sh`; Learning #10 whole-corpus sweep for every
enumeration of close-out steps (`HOW_TO_USE.md`, tutorials T2/T5, campaign checklists — Learning #8).
**STOP.**

### Phase 5 — Dogfood and measure on one adopter before releasing (one session to set up; N sessions to observe)
Pick one active adopter with a real test suite. Declare 3–5 gates at *current* measured values (the
ratchet starts where you are; CampusIQ's floor moved from "comfortable a year ago" to 90%, it did not
start there). Record, per session, three counts the methodology has never had: gate failures caught
before commit, loosening attempts refused, receipt claims contradicted by the results file. **DONE:** five
sessions of counts in that project's `SESSION_NOTES.md`, summarized in its ledger. This is the evidence
the release narrative cites — the methodology's own "quality holds as volume grows", published.
**STOP** after setup; observation rides on ordinary sessions.

### Phase 6 — Release (one session)
Minor version (v3.8 if nothing else ships first): a new distributed tool + a principle-level section +
a SAFEGUARDS hard rule; no phase, gate, principle count or FM count change (FM count stays 28 under D8).
Follow the v3.7 release procedure: narration commit → PR → merge → annotated tag → `gh release` → ledger
entry completed from real command output, never before the tag exists.
**STOP.**

---

## 7. Two questions this plan would put to CampusIQ

Recorded so that a later session can ask them rather than re-derive them:

1. **How is the coverage floor guarded against vacuous tests?** A floor an agent must clear is a floor an
   agent can clear with assertions that assert nothing. Is there a mutation score, an assertion-density
   check, or a review-time mutation spot-check beside the floor?
2. **What makes the check set grow past 130?** When a defect is found in review, does it become a new
   Forseti check, a test, or an eval case — and who files it, the reviewer or the agent that produced it?
   The answer decides whether the check set grows by review or by self-report, which is the same
   distinction §3 turns on.

---

## 8. Open decisions for the maintainer (answer before Phase 1)

1. **Ratify the framing** in §0/§3 — enforce on the artifact, not the actor — as the principle-level change
   (D4), or keep it at the SAFEGUARDS/tool level only (D2/D3) with no flight-manual section.
2. **Results file: committed or gitignored?** Committed = durable, reconcilable, dashboard-readable from
   any clone, but churns on every run. Gitignored = quiet, but only the machine that ran it can score it.
   Recommendation: gitignored by default, with the receipt citing the summary line (D9), and revisit after
   Phase 5's counts.
3. **FM #29 or FM #17 amendment** (D8). Recommendation: amend #17; promote to #29 only if Phase 5 shows
   loosening attempts are frequent.
4. **Where the seed's initial thresholds come from.** Empty manifest (adopter declares from measurement —
   recommended, mirrors Phase 5) vs. a default copied from the article (a 90% coverage
   floor) — the latter would be false at install for most existing adopters and would immediately fail
   every pre-commit, which teaches bypass.
5. **Manifest name and schema owner** — `.quality-gates.json` on the `.context-budget.json` precedent, or
   fold gates into `.context-budget.json` (one file, two concerns — not recommended: the hook the
   methodology ships is *"narrow and single-purpose"* by design).
6. **Whether to put §7's questions to the source now** or after Phase 5 produces numbers.
7. **Scope guard:** this plan deliberately does **not** touch delivery/acceptance (the post-implementation
   "should it ship" gate) beyond noting that CampusIQ's "a person still decides" is the same gap. Confirm
   that stays a separate plan.

---

## 9. Commands that produced the evidence (re-runnable by the executor)

```sh
cd methodology                                   # main @ 512c2ed
grep -rn -i 'cyclomatic\|coverage floor\|coverage threshold\|LOC cap\|ratchet' --include='*.md' --include='*.py' .   # 0 hits as a code rule
grep -rn -i 'never a hard gate\|advisory only\|nothing gates' --include='*.md' --include='*.py' .                 # dashboard = advisory
grep -n 'def precommit' -A 12 starter-kit/context_budget.py    # the one existing ratchet (:504)
sed -n '421,436p' ITERATIVE_METHODOLOGY.md                      # 12 gates — read the question column
sed -n '297,333p' starter-kit/SESSION_RUNNER.md | grep -c '^| [0-9]'  # 28 FMs (two-table trap: count THIS range only)
grep -n -o 'FM #[0-9]*\|failure mode #[0-9]*' .githooks/pre-commit tools/methodology_dashboard.py | sort | uniq -c   # only #27 is cited by a check
sed -n '310,319p' starter-kit/BOOTSTRAP.md                      # Step 10 "(Optional)"; "some check … not which one"
grep -n 'test_to_source_ratio\|collect_coverage_config' tools/methodology_dashboard.py   # presence, never a number
grep -n 'Code Health Metrics' -A 2 workstreams/DEVELOPMENT_WORKSTREAM.md                 # hand-filled table (:217)
python3 -c "import sys; sys.path.insert(0,'bin'); import _manifest as m; print(len(m.DISTRIBUTION))"   # 24 (27 on #80)
git show origin/read-set-budgets:bin/check-learnings | grep -n ROW_BUDGET_BYTES              # 1500 on #80
gh pr view 80 --json mergeable,mergeStateStatus,commits,changedFiles,additions,deletions     # MERGEABLE/CLEAN, 11 commits, 28 files
```

Primary and sole source: <https://campusiq.com/blogs/everybody-ships> (fetched 2026-09-14).
