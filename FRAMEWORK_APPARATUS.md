# Framework Apparatus

The operative apparatus of the [Iterative Session Methodology](ITERATIVE_METHODOLOGY.md) — the tables
you fill in, the tests you run, and the scales you score against. This file is **reference, read on
demand**: you open it while writing a session document, validating a scope, or scoring a claim, not to
understand the framework. The theory these sections implement — the 9 principles, the 6 phases, the 12
quality gates — stays in [`ITERATIVE_METHODOLOGY.md`](ITERATIVE_METHODOLOGY.md).

The first six sections below were moved here **verbatim** from that file, which had grown past the
size a single read can hold. Nothing was rewritten, condensed, or dropped in the move; the only edit
was to turn one in-file cross-reference into a link back to `ITERATIVE_METHODOLOGY.md`. The seventh,
[§The Action Ledger](#the-action-ledger), holds the rules for a project's `CHANGELOG.md`, moved here
from the starter-kit seed so that `bin/sync` keeps them current.

---

## Knowledge Accumulation System

Knowledge compounds across sessions through four mechanisms. All four are required — they serve different purposes.

### 1. Reference Tables

Structured tables recording factual findings about components, tools, or materials. Each session adds rows; no session removes them (unless correcting an error).

**Format:**
| Item | Key Finding | Constraints | Verified? |
|------|-------------|-------------|-----------|

**Purpose:** Eliminates re-derivation. When a future session needs to know a component's behavior, the reference table provides the answer without re-reading the implementation.

**Rule:** Reference tables record FACTS (measured heights, observed behaviors, code-confirmed capabilities), not opinions. If a finding is uncertain, mark it explicitly.

### 2. Pattern Library

Named patterns with "Description" and "When to Use" columns. Each pattern is attributed to the session that discovered it.

**Format:**
| Pattern Name | Description | When to Use | Discovered |
|-------------|-------------|-------------|------------|

**Purpose:** Makes successful solutions reusable. A future session can apply "RX/TX thematic split" by name rather than re-inventing it.

**Rule:** Patterns are TOOLS, not mandates. A pattern that works for 8 of 10 sessions may fail for the other 2. Each session must evaluate whether a pattern applies to its specific context. Anti-pattern: "Force-fitting a proven pattern because it worked before."

### 3. Anti-Pattern List

Numbered list of mistakes with descriptions of what went wrong and why.

**Format:**
```
Anti-pattern #N: [Name] — [Description of the mistake, what caused it,
and what would have prevented it]. Discovered: Session X.
```

**Purpose:** Makes failures non-repeatable. A numbered anti-pattern is citable — "check for anti-pattern #29" is specific and actionable.

**Rule:** Every entry in the anti-pattern list exists because a real session made that exact mistake. Do not add hypothetical anti-patterns. Only actual failures earn a number.

### 4. Cross-Session Citations

Design documents explicitly reference previous sessions when reusing patterns or avoiding anti-patterns.

**Examples:**
- "Applying the RX/TX thematic split from Session 1..."
- "Session 4 predicted ritXit would apply to satellite; this session confirms it."
- "Unlike Session 7's dxCluster error, this domain's ecosystem IS the DX cluster network."

**Purpose:** Creates institutional memory. A citation trail lets anyone trace WHY a decision was made, all the way back to the session that established the precedent.

---

## Honest Accounting Framework

Honest accounting is the integrity mechanism of the methodology. It prevents the common failure mode of "everything went well" narratives that hide real problems.

### What Went Right (Per Session)

List 3-6 things that worked well, with EVIDENCE:
- What specifically happened?
- Why did it work?
- Is it a reusable pattern? If so, name it and add it to the pattern library.
- What would have happened without this?

### What Went Wrong (Per Session)

List 1-4 things that went wrong, with ROOT CAUSE ANALYSIS:
- What specifically happened?
- Why did it happen? (Not "I made a mistake" — what structural gap allowed the mistake?)
- What would have prevented it?
- Is it a new anti-pattern? If so, number it and add it to the anti-pattern list.
- What should the next session do differently?

**The standard for honesty:** Would a hostile reviewer agree with your assessment? If your "What Went Wrong" section says "nothing significant," ask whether that's true or whether you're avoiding accountability.

**Fabrication is the terminal failure mode.** Claiming credit for work you didn't do, attributing quotes the stakeholder didn't say, or describing capabilities that don't exist — these are not "inaccuracies," they are trust destruction. A session that honestly reports "I produced nothing" is infinitely more valuable than one that claims a deliverable it didn't produce. The former leaves the next session informed; the latter leaves it deceived.

**Evidence from practice:** In a 1100+ session series, two sessions fabricated claims (one attributed a quote the stakeholder never said, another claimed credit for a plan that was input, not output). Both were caught within the same session. Both damaged trust disproportionately to the effort they tried to save.

### Performance Comparison Table

Maintained across all sessions. Columns should include:

| Metric | Description |
|--------|-------------|
| Iterations to approval | How many times was the design revised before approval? Target: 1. |
| Stakeholder corrections | How many factual errors did the stakeholder catch? Target: 0. |
| Defects found in existing work | How many problems were found in the artifact's prior state? Higher is better (means more thorough audit). |
| Research depth | What was examined before creating? Quantify (e.g., "all 22 plugin directories"). |
| New patterns discovered | Named patterns added to the library this session. |
| Gaps identified | Deficiencies found that can't be fixed this session. |
| Prior recommendations applied | X of Y recommendations from the previous session. Target: Y of Y. |

### Trajectory Narrative

After updating the performance table, write a paragraph interpreting the trend:
- Is quality improving, stable, or regressing?
- What explains the trend?
- Are there leading indicators of future problems?
- What is the current quality standard? (e.g., "first-pass approval, 0 corrections, 12+ defects found")

---

## Scope Validation System

Scope validation asks "Am I solving the right problem?" before "Am I solving the problem right?" Three tools:

### The Splitting Test

When a work item encompasses multiple sub-items, evaluate each pair:

1. Does sub-item A have a **different primary tool/component** than sub-item B?
2. Does sub-item A have a **different tempo/pace** than sub-item B?
3. Does sub-item A have a **different user posture** than sub-item B?

If all three are true, the sub-items belong in separate scopes. If they share a primary tool, keep them together and handle differences through views/configurations.

**Signal phrases that indicate a split is needed:** "fundamentally different," "passive vs active," "different tempo," "set-and-forget vs interactive." If you write these phrases about sub-items within a single scope, stop and evaluate.

### Domain-Ecosystem Validation

Before including a tool or component, ask:

1. Does this domain have its own specialized tool ecosystem?
2. Does my tool set include a tool FROM that ecosystem?
3. Or am I substituting a generic equivalent?

**Four possible outcomes:**
| Outcome | Meaning | Action |
|---------|---------|--------|
| **Rejection** | Generic tool is domain-inappropriate | Exclude; document the gap |
| **Confirmation** | My tool IS the domain's native tool | Include with confidence |
| **Identity** | My tool set IS the ecosystem | Include; no external tools needed |
| **Complementary** | My tool partially covers the domain; integration exists for the full tool | Include honestly; document limitations |

### Role/Mode Classification

Before designing, classify the work item:

- **Personal operation:** The user manages their own work
- **Group management:** The user manages others' work

This classification changes which components are "star" components and how the interface is organized. A personal-operation design centers on the user's own actions; a group-management design centers on a roster/queue of others' items.

---

## Verification Hierarchy

Seven levels, from least reliable to most reliable. Use the highest level that's practical for each claim.

| Level | Method | Cost | What It Catches | What It Misses |
|-------|--------|------|-----------------|----------------|
| 1 | **Assumption** | Free | Nothing | Everything |
| 2 | **Name/Label** | Free | Gross miscategorization | Subtle mismatches |
| 3 | **Description/Manifest** | Low | Capability gaps | Behavioral constraints |
| 4 | **Implementation Reading** | Medium | Width constraints, actual sizes, variant behavior | Domain-inappropriate usage |
| 5 | **Comprehensive Reading** | Medium | Unexpected components, hidden capabilities | Domain knowledge gaps |
| 6 | **Domain Validation** | High | Wrong tool for the community | Implementation bugs |
| 7 | **Mechanical Verification** | Medium | False capability claims | Semantic errors |

**Rule:** Each level was added because a real session trusted a lower level and got burned. Level 4 was added after session 1 trusted names (level 2) and proposed the wrong component. Level 6 was added after session 7 trusted implementation reading (level 4) and proposed a domain-inappropriate tool. Level 7 was added after session 9 trusted an agent's summary and discovered 5 false capability claims.

**Mechanical verification example (Level 7):**
```
Step 1: grep for capability declaration (does it claim to support X?)
Step 2: grep for capability usage (does it actually implement X?)
Zero matches on Step 2 = zero support. No interpretation needed.
```

---

## Session Document Template

Every session produces a document following this structure. Copy this template and fill it in.

```markdown
# Session [N]: [Work Item Name]

## Previous Session Handoff Evaluation
- **Score (1-10):** [How well did Session N-1's handoff prepare you?]
- **What helped:** [Specific notes, file references, or warnings that saved time]
- **What was missing:** [What you had to figure out that should have been documented]
- **What was wrong:** [Any claims that turned out to be inaccurate]
- **ROI:** [Did reading the handoff save more time than it cost?]

## Pre-Flight Assessment
- Workspace state: [clean/dirty — if dirty, what and why]
- Prior session notes: [summary of what the last session did]
- Ghost session check: [any undocumented sessions detected? changes without notes?]
- Ledger reconcile: [CHANGELOG current with git log? undocumented commits backfilled? or "no CHANGELOG" opt-out recorded?]
- Artifact current state: [builds? passes? known issues?]
- Adjacent artifact check: [which ones checked, their status]

## Research Summary

### Domain/Requirements
- [Who is the user? What do they need? What's their workflow?]

### Component Inventory
| Component | Key Finding | Constraints | Verified? |
|-----------|-------------|-------------|-----------|

### Prior Work Review
- [Which previous sessions were read]
- [Patterns being reused from prior sessions]
- [Anti-patterns being watched for]

### Scope Validation
- [Splitting test results]
- [Domain-ecosystem validation results]
- [Role/mode classification]

## Design

### Approach
- [Overall solution description]
- [Key decisions and their rationale]

### Component Selection
| Component | Included/Excluded | Rationale |
|-----------|-------------------|-----------|

### Quantitative Analysis
- [Balance calculations, sizing estimates, performance projections — whatever is measurable]

### Gap Analysis
| Gap | Severity | Workaround | Future Fix |
|-----|----------|------------|------------|

## Implementation

### Change Set
| File | Action | Notes |
|------|--------|-------|
| (file) | Modify/Create/Delete | (what changes) |

### Files NOT Modified (Scope Boundary)
- [Explicit list of files that are adjacent but out of scope]

## Verification
- Artifact verification: [pass/fail, details]
- Adjacent artifact check: [which ones, status]

## Session Learnings

### What Went Right
1. [Specific success with evidence]
2. [Reusable pattern, if discovered]

### What Went Wrong
1. [Specific failure with root cause analysis]
2. [New anti-pattern, if discovered]

### Performance Metrics
| Metric | This Session | Trend |
|--------|-------------|-------|
| Iterations to approval | | |
| Stakeholder corrections | | |
| Defects found | | |
| Research depth | | |
| New patterns | | |
| Prior recommendations applied | X of Y | |

### Recommendations for Next Session
1. [Specific, actionable improvement]
2. [...]

### Patterns Added to Library
| Pattern | Description | When to Use |

### Anti-Patterns Added
| # | Name | Description |
```

---

## Performance Tracking

Maintain a performance comparison table across ALL sessions in the methodology prompt or a dedicated tracking file.

**Required columns:**

| Column | What It Measures | Target |
|--------|-----------------|--------|
| Session | Identifier | — |
| Iterations to approval | Creative rework cycles | 1 |
| Stakeholder corrections | Domain errors caught by stakeholder | 0 |
| Defects in existing work | Thoroughness of pre-work audit | Increasing trend |
| Research depth | Components/files examined | "All" (comprehensive) |
| New patterns discovered | Methodology growth | 2+ (early), 0+ (mature) |
| Prior recommendations applied | Accountability | 100% |
| Handoff quality score | How well the previous session set this one up (1-10) | 8+ |
| Handoff ROI | Did reading the handoff save more time than it cost? | Positive |

**Interpreting the table:**
- **Iterations > 1:** Research was incomplete. Tighten Phase 2.
- **Corrections > 0:** Domain knowledge gap. Add domain validation steps.
- **Defects decreasing:** Audit is getting lazy. Check audit methodology.
- **Recommendations < 100%:** Either the recommendations were impractical or the session skipped them. Investigate which.
- **Handoff score < 7:** The previous session's close-out was insufficient. Review what was missing and add it to the close-out checklist.
- **Handoff ROI negative:** The handoff described completed work that was actually incomplete, or contained incorrect claims. Tighten the "re-read before claiming" rule.

**Maturity indicators:**
- Sessions 1-3: Foundation — expect methodology changes, pattern discovery, some corrections
- Sessions 4-7: Expansion — patterns stabilize, new anti-patterns emerge from edge cases
- Sessions 8-15: Maturity — validations exceed discoveries, corrections near zero, methodology changes are rare
- Sessions 15-30: Refinement — handoff quality becomes the primary lever for improvement; phase execution is automatic
- Sessions 30+: Maintenance — patterns are stable; focus shifts to preventing regression, maintaining discipline across workstream changes, and accountability

**Erosion indicators (see [§Protocol Erosion](ITERATIVE_METHODOLOGY.md#protocol-erosion)):**
- Handoff scores declining across consecutive sessions
- Session note gaps (ghost sessions)
- Scores that were stable at 8+ dropping below 5
- Self-assessments getting shorter or less specific
- "Maturity" being used as justification for skipping steps

---

## The Action Ledger

The rules for a project's `CHANGELOG.md`, the authoritative action ledger. They live here, in a
file `bin/sync` keeps current, rather than in the starter-kit seed, which each project receives
once and never again — so a correction made here reaches every project. The subsections
below began as that seed's text, moved one heading level down; the seed now carries a
pointer to this section and its format marker. Inside them, *this file* and *this ledger* mean
your `CHANGELOG.md`.

### How to add an entry

Prepend one entry per action, **newest on top** — when and where are *Lifecycle* and *Placement*,
below. Key on a mechanical fact, not judgment: *did this session author or retain any commit, or take any non-commit action?* If
yes, an entry is owed — "too small to log" or "I'll batch it next time" **is** failure mode
#27, not an exception. The only exemption is a session whose diff is empty and that took no
action at all.

**Source tag — exactly one per entry, from this closed vocabulary:**

- `[issue #<N>]` — a repository issue. If issues live in another repo (e.g. an upstream parent
  of a fork), cite an absolute URL, not a bare `#<N>`.
- `[BL-<id>]` — a `BACKLOG.md` item, under whatever id that backlog gives it. Remove it from
  `BACKLOG.md` in the same commit.
- `[ad hoc]` — work with no backlog or issue origin (the source most prone to vanishing):
  releases, tag/branch ops, PR opens, upstream issue closes, access grants, and
  decline/wontfix/grooming decisions all land here.

**The audit** enumerates every logged action and proves all three sources landed. It counts the
archived shards as well as the live file, because a trim moves entries from one into the other,
and it gives the same number in `bash` and in `zsh`:

```
cat CHANGELOG.md $(git ls-files 'docs/archive/CHANGELOG-*.md') \
  | grep -cE '^### [0-9]{4}-[0-9]{2}-[0-9]{2} · \[(issue #[0-9]+|BL-[^]]+|ad hoc)\]'
```

Three details in that command are load-bearing. **`git ls-files`, not a bare glob** — zsh aborts
a command whose glob matches nothing, so `docs/archive/CHANGELOG-*.md` written directly would
return no count at all in the common case of a project that has never trimmed. **Anchored to the
entry heading** — an unanchored pattern also matches the vocabulary's own definitions and every
mention of a tag in prose, so it can report more actions than the ledger holds; the project this
was measured on counted 78 where 64 had happened. **`BL-[^]]+`, not `BL-[0-9]+`** — it counts whatever id the project's backlog uses.

Entries written before a project adopted this vocabulary stay as written; the audit does not
count them, and that gap is expected rather than a defect to repair.

**Format** — the `###` header line is the required, greppable unit; the detail bullets are
recommended, plus one further bullet, `Model`, that is optional even relative to the others:

```
### YYYY-MM-DD · [SOURCE] one-line outcome-focused summary
- **Change:** what is now true in the repo/product that was not before
- **Commit/PR:** `<short-sha>`  —or—  PR #<N> (merged `<sha>`)
- **Session:** S<N> · **Verified:** <build/test/render/runtime evidence, or "n/a — docs-only">
- **Model:** <acting model> (optional — omit the line entirely when not recorded)
```

*(The `[SOURCE]`, `[issue #<N>]`, `[BL-<id>]`, and `[ad hoc]` tokens above are illustrative.)*

**Model:** — self-reported, free text; omit the line when not recorded. Names which model
executed the action — an agent-independent key with a concrete value, the same pattern
`key_files` already uses for paths. Single-tier work names one model:

```
### 2026-01-15 · [ad hoc] Ship the export-retry fix
- **Change:** exports now retry once on a transient network error instead of failing immediately
- **Commit/PR:** `a1b2c3d`
- **Session:** S42 · **Verified:** unit suite green, manual retry reproduced and confirmed fixed
- **Model:** <model>
```

Capability-tiered work (one session whose layers are built or reviewed across different tiers) is
recorded *per entry*, not compressed into one line: each layer/checkpoint already gets its own
`CHANGELOG.md` entry, so each entry's **Model:** bullet states only its own role:

```
### 2026-01-16 · [ad hoc] Layer 3 — draft the parser (delegated layer)
- **Change:** the new input format parses without a follow-up fixup pass
- **Commit/PR:** `d4e5f6a`
- **Session:** S43 · **Verified:** unit tests for the new parser pass
- **Model:** <model A> (delegated; reviewed by <model B>)

### 2026-01-16 · [ad hoc] Layer 4 — review and land the parser (primary layer)
- **Change:** the delegated layer's diff is reviewed and the checkpoint committed
- **Commit/PR:** `b7c8d9e`
- **Session:** S43 · **Verified:** full suite green after review fixes
- **Model:** <model B> (primary)
```

`HANDOFFS.md`'s "How to write a receipt" section documents a complementary session-level
convention: naming the model once in a receipt's free-text prose, for a reader who wants one
session's answer without correlating multiple entries here. That convention adds no new
`HANDOFFS.md` schema key — it is not a second, competing structured field, and it is fine for both
files to name the same model for a single-tier session, since they answer different questions
("what happened, action by action" vs. "which model ran this session"). A canonical-only
`bin/model-report` (copy it into your `bin/` if you want it) reads this file's **Model:** bullets
back alongside `HANDOFFS.md`'s free-text mentions and git's `Co-Authored-By` trailers, keeping all
three visually separate — see that tool's own docstring for why trailers are corroboration-only,
never authoritative.

**Lifecycle — one entry per commit, never edited.** The commit is the unit the ledger co-staging
hook checks, so each commit carries its own entry, and each non-commit action gets one of its own.

- **A claim commit carries an *(in progress)* entry**, and close-out adds its own entry rather than
  rewriting the claim's. Work committed but not finished — an in-progress hand-off, a reverted
  slice — is marked `(in progress)` the same way, and a later session closes it out or records the
  revert as its own entry.
- **A committed entry is never edited.** A correction is a new entry that names what was wrong. The
  one exception is removing content that must not be published — a credential, personal data — and
  that removal is recorded by an entry of its own.
- **A Phase 0 backfill is the one entry that may span several commits**: it records history that no
  close-out reached.
- **The Phase 1B `CHANGELOG: pending` marker lives in `SESSION_NOTES.md`.** A project that keeps no
  `SESSION_NOTES.md` relies on its `status: pending` `HANDOFFS.md` receipt instead.

**Placement — prepend under the topmost `## YYYY-MM`.** Reverse-chronological and prepend-only, so
close-out never re-sorts. When the month changes, open the new month's heading above the last one:
group by month, **not** by release. A ledger that has no month headings starts them at its next new
month, or at its first trim, whose own entry `methodology_trim.py` files under the current month's
heading; nothing already written is retrofitted. A merged branch's entries keep the order they had on
the branch, as one block, rather than being re-sorted into the dates around them. Entries stay at
`###`, the level the tools key on.

### Reading and archiving

**The protocol never asks a session to read this file whole.** Its three reads are each partial:

- **Phase 0 reconcile** takes the frontier from git — `git log -1 --format=%H -- CHANGELOG.md` — and
  lists the commits after it with `git log`; a backfill it owes goes on at the top.
- **Close-out** reads the top and prepends the session's entries there.
- **A lookup** — when was X done, which entry records commit Y — is a `grep` or a `git log --grep`,
  not a read.

So the file's size costs no session a read, and it has no place in a read budget. Past the
harness's default-read refusal — the trimmer's `READ_REFUSE_BYTES`, beyond which a default read
returns no content at all, front matter included — read the top with an offset and a limit.

**Archiving is optional.** A project that wants a smaller live file moves its oldest entries to a
frozen shard with `methodology_trim.py`, which refuses to write unless it can prove the split
lossless. The tool's trigger is the only statement of *when* — these rules name no size:

```sh
python3 methodology_trim.py --file CHANGELOG.md --check
```

`--check` evaluates the trigger, reports whether it fires, and never writes. For a project that has
chosen not to archive, its report is information, not a fault. `--write` performs the trim; a dry
run is the default. **It neither commits nor stages** — it leaves the live file modified and the new
shard *untracked*, prints the rollback, and leaves the commit to you. Stage both yourself:
`git add CHANGELOG.md docs/archive/` — committing with `-a` alone would land the shortened ledger
while the shard, being untracked, never enters history at all. `--budget-bytes <N>` overrides the
tool's byte budget for a single run.

**Archiving again is not always the answer.** If the file has already given back everything the
last archive removed, another archive resets the *level* and not the *rate* — the tool measures
exactly that and **refuses to fire**; `--force` is how you overrule it deliberately. Before a file's
first archive there is no baseline to measure against, so it abstains rather than compute a zero.

#### The shard convention

An archive is a **shard** — a new frozen file, same format, same newest-on-top order.

- **Path: `docs/archive/<LIVE-BASENAME>-through-<CUT-KEY>.md`.** Both halves are load-bearing. The
  directory keeps a shard from shadowing the live file by sort order, and the `CHANGELOG-` prefix is
  what the trigger's own glob looks for when it hunts its baseline — a shard named otherwise is
  silently invisible to it, and the trigger then measures against the wrong boundary.
- **The live file keeps one short pointer** naming each shard and the span it covers. Every count
  stated in that pointer carries the command that recomputes it, because a hand-maintained count
  drifts on the next prepend.
- **The shard back-links to the live file and states only facts about itself** — its own span, its
  own count. It must **not** restate a forward-looking rule. A shard is frozen, so a rule copied
  into one is wrong the moment the live rule moves, and correcting it means editing a frozen
  record. Cite the live file; do not copy it.
- **Conservation: the live file and its shards together never lose an entry.** A trim moves entries
  and deletes none, so anything that counts or enumerates this ledger reads both, never the live file
  alone — `cat CHANGELOG.md $(git ls-files 'docs/archive/CHANGELOG-*.md')`, which runs the same in
  bash and zsh, shard or no shard. The live file's own count falls at every trim by design, so a guard
  that compared it across commits would refuse every trim.
- **Prefer a release frontier as the cut key**, because a shipped release is a boundary nothing can
  ever be written back into. A calendar date works too, but it is frozen only by convention; if you
  cut at one, say in the shard's own front matter that you departed and why.

**A trim is an action, not a side effect.** It earns its own commit and its own `[ad hoc]` entry
here — one ledger, one shard, one commit, one revert. It does **not** belong in Phase 0, which is
read-only apart from the reconcile backfill.

**Not everything that grows can be archived this way.** Archiving moves *history*. A file that grows
because someone keeps adding *procedure* has no past to move — extract a section to a sibling file
and leave a pointer instead. A backlog of open items is live state rather than history: that is a
grooming problem, and its completed items belong here, in this ledger, not in a frozen shard.

### CHANGELOG.md vs SESSION_NOTES.md — two files, two questions, one shared key

`SESSION_NOTES.md` is the **transient handoff** — *"what's next, what traps?"* — overwritten
every session. `CHANGELOG.md` is the **cumulative ledger** — *"what was done, ever?"* —
append-only, and never read whole (see above). Nothing is ever deleted: when a project archives,
the oldest entries move to a shard. The commit SHA is the only intended intersection. Close-out **distills** the
durable outcome into a ledger entry; it does not copy the handoff. The belongs-here test:
*would the operator, six months out, need this to know what the repo does or how it got there?*
