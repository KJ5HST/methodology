# Inherited-Codebase Familiarization Protocol

A multi-session campaign template for taking over an unfamiliar codebase — typically from a departing owner, an acquired team, an open-source project under new maintenance, or a subsystem the current team has neglected. This protocol extends [`AUDIT_WORKSTREAM.md`](AUDIT_WORKSTREAM.md) — its define-criteria → inventory-scope → examine-systematically → report-with-evidence pattern is the per-module primitive this protocol scales into a repository-wide discipline.

The protocol is explicitly **bidirectional in evidence sources**:

- **Interview mode** — the prior owner is still available for questions. Question rounds are scheduled at planning time; per-unit deliverables include a clearly-labeled "interview-derived" evidence column; owner-bias is the dominant failure mode.
- **Archaeology mode** — the prior owner is gone. Evidence comes from git log/blame, commit messages, merged PRs, the issue tracker, runtime tracing, and the code itself; documentation and comments are explicitly downgraded as evidence (often stale). Documentation-trust is the dominant failure mode.

Both modes share the same campaign shape (planning → per-module work → consolidation). They share the same per-unit schema, the same exit criteria, and the same consolidation deliverable. They differ only in which evidence sources count, what the planning session must arrange, and which anti-patterns dominate.

This is a **protocol**, not a workstream. It does not replace the Audit workstream; it prescribes a campaign structure for a specific deliverable: a complete, evidence-backed familiarization record sufficient to assume named operational responsibility for the codebase.

---

## Relationship to Other Documents

| Document | Role |
|----------|------|
| [`ITERATIVE_METHODOLOGY.md`](../ITERATIVE_METHODOLOGY.md) | Master framework — 9 principles, 6 phases, 12 quality gates. This protocol obeys all of them. See §Protocols and Multi-Session Campaigns. |
| [`AUDIT_WORKSTREAM.md`](AUDIT_WORKSTREAM.md) | Parent workstream. Defines audit-criteria definition, scope inventory, evidence-bearing findings, and the review-session pattern (Phases 1-4 + 6, skip 5). |
| [`DEVELOPMENT_WORKSTREAM.md`](DEVELOPMENT_WORKSTREAM.md) | Sibling workstream. The consolidation session's prioritized backlog feeds into Development sessions; the per-unit dependency analysis informs blast-radius estimates for those sessions. |
| [`../starter-kit/SESSION_RUNNER.md`](../starter-kit/SESSION_RUNNER.md) | Operational checklist — every session in the campaign runs against it. |

---

## When to Use

### Triggers (both modes)

Use this protocol when ownership of a codebase is transferring, AND any of:

- The codebase is large enough that one session cannot produce a complete familiarization record without quality degradation in the second half (typically >6 modules, >10K LOC, or non-trivial cross-module coupling)
- The new owner will be on the hook for production behavior — oncall rotation, security response, regulatory sign-off — and "I don't know that subsystem yet" is not an acceptable answer
- A migration, modernization, or rewrite decision depends on knowing what the existing system actually does (not what its documentation claims)
- Multiple engineers will share ownership and need a common, evidence-backed mental model to coordinate
- An audit, security review, or major refactor is planned and current familiarity is insufficient to scope it honestly

### Interview-mode triggers

The trigger conditions above apply, AND the prior owner (or a knowledgeable proxy) is available for scheduled question rounds before they leave or rotate off. Interview mode requires a question-round budget at planning time — without it, "interview mode" degrades to "ad-hoc questions" and the calibration discipline collapses.

### Archaeology-mode triggers

The trigger conditions above apply, AND no prior owner is available. The codebase must speak for itself. Sessions rely on git log, blame, merged PRs, issue-tracker history, and runtime observation; documentation is consulted but not trusted.

### When NOT to use

- **One-off contribution to an unfamiliar codebase.** A bug fix or feature in someone else's code does not require campaign-scale familiarization — read the affected module, fix, ship. The Development workstream's Phase 2 (Read the Code) is sufficient.
- **Codebases the team already owns and operates.** If the team is already on call for it, the familiarization debt this protocol amortizes is already paid; running this protocol produces a documentation artifact, not a familiarity gain.
- **Prototypes or short-lived code.** Familiarization is an investment; it pays off over months of ownership. For code with a known sunset date inside the campaign window, sample-based audit fits.
- **Time pressure overrides completeness.** When a production incident is in progress, a focused investigation per the Audit workstream is right; campaign-scale familiarization is wrong. Run the protocol after the incident, not during it.

### Mode selection and mode mixing

Mode is usually unambiguous from context: is the prior owner reachable on a schedule, or not? When the prior owner is reachable but unreliable (occasional answers, no scheduled rounds), choose archaeology mode and treat owner answers as one more evidence source — not as the campaign's calibration anchor.

Mixing evidence sources within a unit is allowed and often necessary (an interview answer cross-checked against git history is stronger than either alone), but every row must label its evidence source. The deliverable contract enforces this: a row whose evidence is only "owner said so" without any code-level corroboration is flagged at consolidation as a residual unknown, not as familiarity.

---

## Why This Is a Campaign, Not a Mode

A single session that attempts to familiarize with a non-trivial inherited codebase will fail in one of three ways:

1. **Context exhaustion.** Even on a 1M-token model, holding a multi-module codebase, the cross-module coupling graph, the git history, and a per-module ledger degrades reasoning quality on later modules long before raw token limits hit. Modules read in the last quarter of the session receive measurably less rigor than those in the first quarter — and inherited-codebase work is exactly the setting where superficial reading produces confidently wrong mental models.
2. **"1 and done" violation.** [Principle 9](../ITERATIVE_METHODOLOGY.md#9-session-scope-bounding) bounds every session to one deliverable. A 12-module familiarization is not one deliverable; it is dozens of micro-deliverables (one per module, plus their cross-cuts) fused into a single artifact, and the second half receives less rigor than the first. Worse, the cross-module patterns the campaign exists to surface require uniform per-module depth — and uniform depth across many modules in one session is exactly what context exhaustion prevents.
3. **No resumability.** A session that crashes mid-run leaves the next session unable to determine which modules were studied, at what depth, against what criteria. Without checkpoint files and a locked deliverable schema, the entire run must restart — and the next session, lacking a record of the first session's interpretive judgments, often produces inconsistent depth across modules even if it does resume.

This protocol decomposes the work into a planning session, N execution sessions (one per scoped unit), and a consolidation session — each obeying the methodology's session-scope rules and producing a checkpoint deliverable.

---

## Campaign Structure

```
Session 1: Campaign Planning
    └─ Produces: CAMPAIGN.md (mode, module map, scoping, deliverable contract,
                              question rounds [interview], owner responsibility,
                              exit criteria)

Sessions 2..N+1: Per-Unit Execution (one per scoped unit)
    Both modes: read code → enumerate API surface → trace data flow →
                catalog gotchas → answer "what would I check before changing X"
                Interview mode: schedule and conduct interview round; reconcile
                                interview answers with code-level evidence.
                Archaeology mode: git archaeology — log, blame, PR thread reading;
                                  runtime tracing if available.
                   └─ Produces: units/<unit>.md (familiarization record)

Session N+2: Consolidation
    └─ Produces: REPORT.md (cross-module architecture, risk map,
                            prioritized backlog, residual unknowns)
```

A typical campaign for a 6-module subsystem is 8 sessions (1 + 6 + 1). A 12-module monorepo is typically 14 sessions (1 + 12 + 1). Per-module splits are standard when a single module exceeds ~3K LOC, when call-graph fan-out crosses a threshold the planning session sets, or when one module hosts multiple independent responsibilities.

All campaign artifacts live under `familiarization/`:

```
familiarization/
├── CAMPAIGN.md                     # Planning session output
├── units/
│   ├── auth.md                     # Per-module deliverables
│   ├── billing.md
│   └── ...
├── interviews/                      # Interview mode only
│   ├── round-1-pre-execution.md
│   ├── round-2-mid-campaign.md
│   └── round-3-final.md
└── REPORT.md                        # Consolidation session output
```

---

## Session 1: Campaign Planning

A planning session per [Iterative Methodology §Session Types](../ITERATIVE_METHODOLOGY.md#planningpreparation-sessions). Heavy Phase 2; produces a Phase 3 design that subsequent sessions execute mechanically.

### Common steps (both modes)

1. **Define the operational responsibility.** What will the new owner be on the hook for after the campaign closes — oncall, feature work, security response, code review approval, all of the above? "Familiar enough" is defined relative to this responsibility. A campaign that produces familiarity sufficient for code review but not for oncall has succeeded only if oncall was not in scope. Lock the responsibility in `CAMPAIGN.md`.
2. **Inventory modules.** Enumerate the codebase's modules, packages, services, or directories — whatever the unit of organization is in this codebase. For each: LOC, file count, public API surface size (rough estimate), last-touched date, owner-of-record (if known). The inventory is the audit-scope inventory from `AUDIT_WORKSTREAM.md` Phase 2 Step 2.
3. **Choose the scoping unit.** Default: one execution session per module (or top-level package). Split per-component when a module exceeds ~3K LOC OR hosts multiple independent responsibilities OR has fan-out exceeding the planning session's threshold (default 20 inbound call sites from outside the module). Never split below file/class — sub-file splits fragment the local mental model and produce per-unit deliverables that cannot be cleanly merged.
4. **Choose the scoping basis when modules don't reflect reality.** In legacy code, nominal module boundaries may not match real coupling boundaries. If a planning-time read of imports/calls shows that "module A" and "module B" are inseparable in practice, scope by coupling cluster instead of by module. Document the decision and the evidence in `CAMPAIGN.md`.
5. **Define the deliverable contract** (see Deliverable Contracts). Lock the schema before execution begins; schema drift across units produces unit deliverables the consolidation session cannot cleanly merge into a portfolio view.
6. **Allocate sub-agent strategy.** For each unit, decide: parent-only, parent-with-read-only-sub-agents (recommended — sub-agents can absorb large source files without polluting parent context), or parallel sub-agents per call-graph cluster. See Sub-Agent Dispatch Pattern.
7. **Set exit criteria.** Per-unit completion thresholds (the falsifiable predicates listed under Calibration and Exit Criteria) and campaign-level halt conditions. Lock the predicates so units cannot be marked complete by softening the bar mid-campaign.
8. **Write `CAMPAIGN.md`** as the session's Phase 3 deliverable. Stakeholder approves before any execution session begins.

### Interview-mode specifics

- **Schedule question rounds.** Default: three rounds — one before execution starts (orientation, system overview, "what are you most worried we'll miss"), one mid-campaign after ~half of execution sessions complete (targeted gap-fill against accumulated unknowns), one near campaign end (cross-module pattern reconciliation, gotcha confirmation, succession-plan questions). Each round has a budget (typical: 60-90 minutes); over-running breaks the schedule and risks the prior owner becoming unavailable mid-campaign.
- **Pre-stage round-1 questions.** Don't ask the departing owner to "tell me about the system." Ask questions whose answers will steer the module ordering and the gotcha-priors for the first execution session. The planning session writes round-1's question list as part of `CAMPAIGN.md`.
- **Lock an answer-recording protocol.** Every interview answer goes into `interviews/round-N-*.md` with a date, the question verbatim, the answer summarized, and a follow-up flag for items that require code-level corroboration.

### Archaeology-mode specifics

- **Identify auxiliary evidence sources.** Beyond the code: which issue tracker, which PR review tool, which runbook repo, which monitoring/tracing system. The planning session inventories what's accessible. Sources that are inaccessible (deactivated logins, deleted Slack history) become campaign-level constraints and may justify scope reduction.
- **Calibrate documentation skepticism.** Archaeology mode treats READMEs, in-code comments, and design docs as hypotheses, not facts. Spot-check 5 doc claims against current code during planning. The hit rate informs how aggressively per-unit sessions must verify documentation against implementation.
- **Identify load-bearing institutional knowledge.** Some things are not in the code or the git history (why a service runs in this region, why a flag is gated by user-id parity, why a cron runs at exactly 3:17 AM). Mark these at planning time as expected residual unknowns; the consolidation session's REPORT will include them as "items to escalate to whoever can answer," not as familiarization gaps.

### Gate (Phase 4 in this session)

Stakeholder approval of `CAMPAIGN.md` is the **second-highest-leverage gate in the protocol** (after the per-execution-session implement gate). A bad scoping decision multiplies cost across N sessions; a vague exit criterion lets every unit be marked "done" at a different bar.

---

## Sessions 2..N+1: Per-Unit Execution

Each execution session is bounded to one scoped unit. Familiarization sessions are review/audit sessions per [Iterative Methodology §Session Types](../ITERATIVE_METHODOLOGY.md#reviewaudit-sessions) — Phases 1-4 + 6, skip Phase 5. The deliverable is an analysis document, not modified code.

### Common steps (both modes)

1. **Pre-Flight.** Read `CAMPAIGN.md`. Read prior unit deliverables. Verify the inventoried files for this unit still exist at the recorded paths (a rebase, merge, or upstream pull between sessions can move things; the planning inventory is the source of truth for what *was* in scope, the current state is the source of truth for what *is*).
2. **Phase 1.5 (Claim the Session).** Write the stub naming the unit in progress. A ghost session here is detectable because the stub names exactly which module was being studied.
3. **Research — read the implementation.** For this unit only:
   - Enumerate the public API surface — every exported function, class, endpoint, message handler, scheduled job, or other externally-callable entry point. For each: file:line, signature, one-line purpose statement.
   - Trace data flow for each entry point — input source(s), transformation steps with file:line at each hop, persistent or shared state touched, outputs. Stop at module boundaries; cross-module flow is consolidation-session work.
   - Inventory owned state — every persistent store, in-memory cache, global variable, or module-level singleton this unit writes to. For each: writer list (file:line), reader list (file:line), invariants the unit relies on.
   - Catalog gotchas — surprising behavior, implicit assumptions, undocumented constraints, known-fragile areas. Each row gets file:line evidence and a severity. A unit with zero gotchas after several hours of reading gets an explicit "no gotchas surfaced in N hours of reading by [agent]" annotation, not an empty section.
4. **Mode-specific evidence gathering** (see below).
5. **Answer the falsifiable predicates** (see Exit Criteria). For each predicate, record the answer with file:line evidence. A predicate that cannot be answered with evidence stays open and blocks unit close-out — it does not get a softened bar.
6. **Present.** Surface the unit deliverable to the stakeholder. Highlight: gotchas of severity ≥ moderate, residual unknowns (predicates not closeable), interview/archaeology evidence conflicts, and patterns that may generalize beyond this unit (flag for consolidation, do not generalize within the unit).
7. **Phase 6 close-out.** Standard. Handoff records: sub-agent strategy used, calibration adjustments, residual-unknown count, which checkpoints were committed, and any cross-unit hypotheses to verify in subsequent sessions.

### Interview-mode steps

1. **Pre-interview unit reading.** Before any interview round that targets this unit, complete steps 3 (read the implementation) above. Interviewing the departing owner before reading the code wastes the interview budget on questions the code already answers.
2. **Targeted question list.** Generate the unit's interview questions from gaps surfaced during reading: contradictions between code and comments, behavior whose intent isn't obvious, named constants whose values are surprising, error paths that look defensive against an unstated risk. Questions whose answers are obvious from the code do not belong on the list.
3. **Conduct the interview round** at the time scheduled by `CAMPAIGN.md`. Record verbatim answers to `interviews/round-N-*.md`.
4. **Reconcile interview answers with code-level evidence.** Each answer either confirms the code-level reading (raise the corresponding row to verified), contradicts it (flag — investigate which is right; the resolution is itself a finding), or fills a gap that the code alone could not answer (record with `evidence: interview-round-N` so consolidation can identify uncorroborated owner claims).
5. **Owner-bias check.** At least once per session, deliberately read a piece of the unit cold — without filtering through what the owner said. Compare the cold reading against the interview-anchored reading. Differences are the owner's blind spots; they are exactly what the new owner will inherit if not surfaced.

### Archaeology-mode steps

1. **Git archaeology.** For the unit's high-traffic files, read the commit log (most recent N=20 typical) and skim blame on hot regions. Surprising commits — large rewrites, hot-fix patterns, revert chains, single-author churn — become research questions.
2. **PR / issue tracker reading.** For the same files, find the merged PRs that touched them and read the discussion. PR comments often record context that did not survive to the code or the docs.
3. **Runtime observation if accessible.** If staging or production traces are available, run the unit's entry points and observe. A 60-second trace often surfaces conditional paths a static read missed.
4. **Documentation skepticism.** Treat in-repo docs, comments, and READMEs as hypotheses. For each doc claim that maps to a fact a per-unit deliverable row will assert, verify against current code. Stale doc claims become a finding for consolidation; they do not become rows in the unit deliverable on the strength of the doc alone.
5. **Residual unknown discipline.** Some things will not be answerable from code, history, or runtime alone. Mark these as residual unknowns with the type of evidence that would resolve them ("requires production-incident review," "requires asking [team]"). Do not pretend to know.

### Critical disciplines (both modes)

- **Evidence is non-negotiable.** A row without file:line evidence (or, for owner-derived rows in interview mode, an explicit `evidence: interview-round-N` annotation) is not a familiarization row. It is a guess. The consolidation session will reject it.
- **Reading is not understanding.** A predicate-list answered with file:line citations but without a coherent end-to-end trace is reading-coverage, not comprehension. The "what would I check before changing X" predicate exists specifically to force the agent to demonstrate that the citations have been integrated into a working mental model.
- **Append-only within a session.** Rows are not deleted. A row whose status changes during the session (e.g., a gotcha later confirmed false by interview) gets a `superseded` mark and a new row. The history of changed entries is itself a calibration signal.
- **No cross-unit generalization.** Patterns that look system-wide from inside one unit are mythical-architecture inferences (see Anti-Patterns). Flag them for consolidation; do not assert them as unit-level findings.

---

## Session N+2: Consolidation

A review/audit session whose deliverable is the campaign-wide familiarization report.

### Steps

1. **Pre-Flight.** Read `CAMPAIGN.md` and every unit deliverable. Verify completeness — every unit listed in `CAMPAIGN.md` has a corresponding deliverable; no unit deliverable contains unanswered exit-criteria predicates. If any do, this session halts and flags them as a follow-on execution session.
2. **Research — aggregate across units.** Identify cross-module patterns: shared idioms, repeated gotchas, conventions present in some modules and absent in others, modules whose API surfaces overlap or conflict, services whose ownership of a data structure is disputed by multiple units' "owned state" sections.
3. **Build the cross-module architecture.** A single page or diagram showing the modules, their primary call directions, and the data structures that cross module boundaries. This is a *result* of the per-unit work, not an *input* to it; building it during execution risks the mythical-architecture anti-pattern.
4. **Build the risk map.** For each known fragility, cross-module coupling, residual unknown, or unowned-state finding from the units, record severity and the specific work that would close it.
5. **Build the prioritized backlog.** Using the risk map, generate a session backlog ordered by priority. Items become input to follow-on Development workstream sessions; the backlog is one of the protocol's primary deliverables back into normal session flow.
6. **Present.** Stakeholder approves the report. The named operational responsibility from `CAMPAIGN.md` is the gate: if the stakeholder cannot in good faith confirm "I would now take the named responsibility on this codebase," the consolidation session has surfaced familiarization gaps that justify a follow-on campaign or deeper execution sessions on specific modules.
7. **Phase 6 close-out.** Standard. Recommendation typically opens a follow-on Development session series against the prioritized backlog.

### `REPORT.md` structure

```markdown
## Coverage
- Modules in scope: [list]
- Sessions executed: X of Y planned (with reason for any deviations)
- LOC covered: N (approximate)
- Estimate-to-actual ratio for unit count and session length: [calibration signal]
- Operational responsibility this campaign was sized for: [from CAMPAIGN.md]

## Cross-Module Architecture
- Module map (diagram or structured list)
- Primary call directions
- Cross-module data structures (with owning module, reader modules, invariants)
- Shared services / clients / SDKs

## Cross-Module Patterns
- Idioms and conventions that hold across all modules
- Conventions present in some modules and absent in others (with module list)
- Repeated gotchas (same surprise surfaced in N units — system-level finding, not per-module)
- Patterns that one unit speculated but consolidation did not confirm (these go in residual unknowns, not in this section)

## Risk Map
| # | Risk | Severity | Affected Modules | Evidence (unit row IDs) | Closing Action |
|---|------|----------|-------------------|-------------------------|-----------------|

## Residual Unknowns
| # | Unknown | Type of Evidence Needed | Suggested Resolver |
|---|---------|--------------------------|---------------------|

## Prioritized Backlog
For follow-on Development sessions:
| Priority | Item | Affected Module | Closes Risk # | Estimated Sessions |

## Operational-Responsibility Sign-Off
- Stakeholder confirmation that the named responsibility is now assumable, OR
- Specific gaps and the follow-on work needed to close them.
```

---

## Sub-Agent Dispatch Pattern

The parent agent's context is the campaign's bottleneck. Sub-agents protect it.

### Recommended pattern

For each unit:

1. **Parent** chooses the unit's reading order (typically: package init → public API → its callees, breadth-first). Populates the unit deliverable's skeleton with the API surface enumeration before any deep reading.
2. **Sub-agent** receives a single entry point or a single call-graph cluster + the relevant source files. Returns: the data-flow trace, the owned-state writes/reads observed, and any gotchas surfaced. The sub-agent never sees the full repository — its context is bounded to the cluster it was assigned.
3. **Parent** writes results into the unit deliverable, runs the cross-cluster integration (since gotchas often surface only when multiple sub-agent reports are read together), and answers the exit-criteria predicates from the consolidated unit-level view.

**Why this works:** sub-agent context holds a few source files and one entry point. It can read deeply without polluting the parent's context with the full source. The parent retains the strategic view across the unit.

### When to fan out

Parallel sub-agents (one per call-graph cluster) are appropriate when:
- The unit's public API has more than ~10 entry points
- Entry points are largely independent (cross-entry-point shared state is the integration-step concern, not the per-entry-point concern)
- Sub-agent permission asymmetry permits read-only — the unit deliverable is written by the parent, so sub-agents do not need write access

### Calibration

Different sub-agents apply different rigor unless given explicit calibration. Include in every sub-agent prompt:

- The locked unit-deliverable schema (so its return matches what the parent will paste into rows)
- An example row for each schema field
- The evidence requirement (file:line for every assertion; no narrative claims without file:line)
- The "no cross-unit generalization" rule — sub-agents working a single cluster especially tend to over-generalize from local patterns

---

## Deliverable Contracts

### Per-unit familiarization record schema

```markdown
# Unit: <module name>

## Purpose
[1-2 sentence statement of what this module is responsible for, derived from
 reading not from documentation. If documentation states a different purpose,
 record the discrepancy in Gotchas.]

## Public API Surface
| # | Symbol | File:Line | Signature | One-Line Purpose | Evidence |
|---|--------|-----------|-----------|-------------------|----------|

## Data Flow (per entry point)
For each entry point in the API surface table:
- Entry point: [symbol]
- Input source(s): [where called from, with file:line]
- Transformation steps: [file:line at each hop]
- State touched: [reference rows in Owned State]
- Output: [where it goes]

## Owned State
| # | State | Type | File:Line of Definition | Writers (file:line) | Readers (file:line) | Invariants | Evidence |
|---|-------|------|-------------------------|----------------------|----------------------|------------|----------|

## Gotchas
| # | Gotcha | File:Line | Severity | Why It's Surprising | Evidence Source |
|---|--------|-----------|----------|----------------------|------------------|

## Open Questions Ledger
| # | Question | Tried | Answer | Evidence Source | Status |
|---|----------|-------|--------|------------------|--------|

## Risk Markers
- Test coverage (rough): [%] [evidence]
- Last-touch recency on hot files: [date range]
- Known fragile regions: [list with file:line]
- External dependencies: [list]

## Exit-Criteria Predicates (must all close)
- [ ] Public API entry points listed with file:line
- [ ] Each entry point has an end-to-end data-flow trace with file:line at each hop
- [ ] Each owned-state row has writer list and reader list with file:line
- [ ] Gotcha catalog has at least one row OR explicit "no gotchas surfaced in N hours of reading" annotation
- [ ] "What would I check before changing X" answered for the top 3 entry points by call-site count
- [ ] Any documentation-vs-code discrepancies are recorded as gotchas, not silently resolved
- [ ] (Interview mode) At least one cold-read owner-bias check completed
- [ ] (Archaeology mode) Spot-checked N=5 doc claims against current code; results recorded
```

**Evidence-source vocabulary:**

| Value | Meaning |
|-------|---------|
| `code:<file:line>` | Direct code-level evidence; the strongest |
| `git:<commit-or-pr>` | Git history evidence — log, blame, or PR thread |
| `runtime:<trace-id-or-description>` | Runtime observation evidence |
| `interview-round-N` | Interview mode only; owner answer in the named round |
| `doc:<path>` | Documentation evidence; downgrade in archaeology mode unless corroborated |
| `superseded` | Row was replaced by another within the session |

A row with only `interview-round-N` evidence (no `code:` corroboration) is acceptable but flagged at consolidation as an uncorroborated owner claim. A row with only `doc:` evidence is not acceptable in archaeology mode and is flagged at unit-close in interview mode.

The vocabulary is **locked at planning time**. Schema drift across units forces consolidation rework.

---

## Calibration and Exit Criteria

### Per-unit completion — the falsifiable predicates

A unit is complete when, and only when, the eight exit-criteria predicates in the unit-deliverable schema all close with evidence. The bar is deliberately falsifiable: each predicate either has its required evidence or it does not. "Familiar enough" is subjective; closing the predicates is not.

The hardest predicate is "what would I check before changing X" for the top 3 entry points. It is the predicate most prone to being soft-closed (a generic "I'd check the tests and the callers" answer is not a close). A valid answer names specific files, specific invariants, and specific runtime concerns the change would interact with — and is grounded in this unit's actual code, not in generic engineering advice.

### Campaign-level exit

The campaign closes when:

1. Every unit listed in `CAMPAIGN.md` has a complete unit deliverable.
2. The consolidation session's `REPORT.md` is approved.
3. **The named operational responsibility test passes:** the stakeholder confirms in writing that they would now take on the operational responsibility defined in `CAMPAIGN.md` Step 1. If they cannot, the campaign has surfaced gaps — those become a follow-on campaign or deeper execution sessions, not a softened sign-off.

### Baseline calibration (early data)

This protocol is new; the baselines below are starting estimates. The consolidation session records actual ratios; subsequent campaigns refine the bands.

| Observed | Interpretation | Action |
|----------|----------------|--------|
| Per-unit session runs <1 hour | Either the module is smaller than estimated, or the read is shallow | Spot-check the predicate answers against a fresh sub-agent for second opinions |
| Per-unit session runs >4 hours | Either the module is larger than estimated, or the agent is rabbit-holing | Halt mid-unit; checkpoint what's complete; replan the unit's split |
| Residual-unknown count >20% of API surface for a unit | Unit is under-investigated or has large institutional-knowledge dependency | Schedule a targeted second-pass session, or escalate the unknowns to whoever can answer |
| (Interview mode) Owner-bias check shows >2 contradictions per session | Owner's mental model materially diverges from the code in this unit | Increase cold-read time; flag as a consolidation cross-unit signal |

### Stop conditions

The campaign halts (not pauses — halts) when:

- A single unit cannot reach exit predicates after two execution sessions on it. This is a signal that the planning-session scoping was wrong, not that more time is needed.
- The cross-module architecture being inferred during consolidation contradicts the planning-session inventory in a load-bearing way (modules thought independent are entangled; nominal owners are not the actual owners). The campaign restarts at planning, not at execution.
- (Interview mode) The departing owner becomes unavailable before the question rounds are complete. Mode degrades to archaeology — pause, rescope under the new mode, resume.
- A systemic finding emerges that invalidates the campaign premise (codebase is being deprecated; ownership is changing again; the responsibility being prepared for is being reorganized away).
- Stakeholder direction changes.

A halted campaign produces a partial `REPORT.md` covering completed units. Do not synthesize coverage you did not produce.

---

## Resumability

Each unit deliverable is a checkpoint. After every execution session, commit the unit file before close-out:

```
familiarization/units/<unit>.md
```

A crashed mid-unit session is recovered by the next session reading the unit file from the last committed state and resuming from the first unanswered exit-criteria predicate. The Phase 1.5 stub records which unit is in progress, so a ghost session is detectable.

**Unit deliverables are append-only within a session.** Never delete a row; mark it `superseded` and add a new row. The history of changed rows is itself a signal — for calibration, for owner-bias detection in interview mode, and for the consolidation session's pattern detection.

In interview mode, `interviews/round-N-*.md` is a separate checkpoint stream. A crash mid-interview-round is recovered by reading the partial round file; a crash post-interview-pre-reconciliation is recovered by reading the round file alongside the unit deliverable's `Open Questions Ledger`.

---

## Anti-Patterns

### Shared (both modes)

1. **One-session attempt.** Trying to familiarize across the whole codebase in a single session. Context degrades; the second half of modules is read more shallowly than the first; cross-module patterns surfaced from a fatigued read are unreliable. Use the campaign decomposition.
2. **Skipping the planning session.** Jumping into module-by-module reading without a `CAMPAIGN.md`. Schema drift across units forces consolidation rework that exceeds the planning-session cost; exit criteria drift across units lets each unit close at its own bar; named operational responsibility goes undefined and the campaign can never honestly close.
3. **Mythical-architecture inference.** Generalizing system-wide patterns from a single well-understood module. The other N-1 modules may not follow the same conventions — and inherited codebases especially tend to have multiple concurrent conventions reflecting different past owners. Flag suspected patterns for consolidation; do not assert them as unit-level findings.
4. **Module-rabbit-holing.** Spending 3-4× estimate on the first module because it's interesting or unfamiliar; later modules get rushed; the consolidation surfaces the imbalance as inconsistent depth. The per-unit calibration band exists to detect this; honor it by halting and replanning, not by accepting it.
5. **Documentation trust.** Treating READMEs and in-code comments as ground truth. Code is the source of truth in inherited codebases; documentation describes past intentions and decays with every change that doesn't update it. Documentation evidence requires code-level corroboration before it becomes a unit-deliverable row.
6. **Reading-coverage as comprehension.** Filing file:line citations for every predicate without integrating them into a coherent mental model. The "what would I check before changing X" predicate is the diagnostic; if its answers are generic, the predicate has not actually been closed.
7. **Test-suite-as-spec.** Treating the test suite as the contract. Tests cover what the prior author thought might break, not what does break in production; in inherited codebases the tests are often the *least* reliable evidence of intended behavior because they freeze early misunderstandings.
8. **Evidence-free rows.** A row with no `code:` / `git:` / `runtime:` / `interview-round-N` / `doc:` source. Familiarization records full of unsourced assertions are confidence theatre; the consolidation session will reject them.
9. **Sub-agent calibration drift.** Dispatching sub-agents without explicit schema and evidence-requirement calibration. Different sub-agents will produce different rigor on identical clusters; cross-cluster integration becomes impossible if their outputs are incomparable.
10. **Cross-unit consolidation creep.** Doing per-unit work in the consolidation session because "I notice we missed something while merging." Stop, log it as a follow-on execution, return to merging.

### Interview-mode-specific

11. **Owner-bias anchoring.** Treating the departing owner's mental model as ground truth. The owner's blind spots are precisely what the new owner inherits if not surfaced — and they are invisible from inside the owner's mental model. The cold-read check is the structural defense; skipping it defeats the mode's only safeguard against this failure.
12. **Interview-without-reading.** Conducting an interview round before the unit's code has been read. The interview budget is spent on questions the code already answers; the questions that the code *can't* answer go unasked. Read first, interview second.
13. **Owner-derived rows without code corroboration.** Marking a row complete on the strength of an interview answer alone, without a `code:<file:line>` citation. A claim that the owner cannot point at in the code is institutional knowledge — record it as a residual unknown for consolidation, not as a familiarization row.

### Archaeology-mode-specific

14. **Documentation-as-evidence.** Same shape as anti-pattern #5 but more dangerous in archaeology mode, because there is no owner to correct stale docs. A doc claim with no code-level corroboration is not evidence; it is a hypothesis. In archaeology mode the spot-check rate of doc-vs-code agreement is itself a finding.
15. **Git-archaeology rabbit-holing.** Reading the entire history of a hot file because each commit is interesting. The protocol's "most recent N=20 commits + skim blame" rule exists because diminishing returns on history reading are sharp. Honor the bound.
16. **Residual-unknown denial.** Refusing to mark items as residual unknowns because "I should be able to figure this out from the code." Some load-bearing facts about an inherited system are not in the code, the history, or any accessible runtime trace — they are in the heads of people who are gone. Marking them as residual unknowns, with the type of evidence that would resolve them, is the honest accounting; pretending to know is not.

---

## Verification Checklist

### Per execution session, before close-out

- [ ] Every entry point in the unit's API surface has a row with file:line, signature, and one-line purpose
- [ ] Every entry point has an end-to-end data-flow trace with file:line at each hop
- [ ] Every owned-state row has explicit writer list and reader list with file:line
- [ ] Every gotcha row has file:line evidence and a severity
- [ ] Every row has an evidence-source value drawn from the locked vocabulary
- [ ] No row's only evidence is `doc:` (archaeology mode) or `interview-round-N` without follow-up action (interview mode)
- [ ] All eight exit-criteria predicates close with evidence
- [ ] (Interview mode) Cold-read owner-bias check completed and recorded
- [ ] (Archaeology mode) Doc spot-check completed; results recorded
- [ ] Unit deliverable is committed to `familiarization/units/<unit>.md`
- [ ] Handoff records sub-agent strategy, calibration adjustments, residual-unknown count, and any cross-unit hypotheses to verify in subsequent sessions

### Per campaign, before close-out (consolidation session)

- [ ] Every unit listed in `CAMPAIGN.md` has a corresponding deliverable
- [ ] No unit deliverable contains unanswered exit-criteria predicates
- [ ] Cross-module architecture diagram exists and is grounded in unit deliverables (no module-level claims without unit-row provenance)
- [ ] Risk-map rows each cite at least one unit-deliverable row as evidence
- [ ] Residual-unknowns table is non-empty OR has explicit "no residual unknowns" annotation with stakeholder confirmation
- [ ] Prioritized backlog is ordered by priority and dependency, not by module order
- [ ] Estimate-to-actual ratios are recorded for future-campaign calibration (unit count, session length, residual-unknown rate)
- [ ] Operational-responsibility sign-off is captured — either the responsibility is assumable, or the gaps blocking that are listed with closing actions

---

## Example Campaign Outlines

### Archaeology campaign: 6-module subsystem inherited from a reorg'd team

```
Campaign: Billing subsystem familiarization (post-reorg)
Mode: archaeology
Trigger: Prior team disbanded; new team assumes oncall in 6 weeks; pre-oncall
         familiarization required.
Operational responsibility: oncall + bug-fix authority on the 6 billing modules.

Session 1 (Planning):
    Inventory: 6 modules (auth-bridge, invoice-render, ledger-sync, payment-gateway,
              statement-export, webhook-dispatch). 24K LOC total. invoice-render
              and ledger-sync nominally separate but planning-time import-graph read
              shows they share a non-trivial cache; scoped as one unit.
    Estimate: 5 execution sessions (5 scoped units after merging the two coupled modules).
              ~3 hours per unit.
    Decomposition: one execution session per scoped unit.
    Sub-agent strategy: parent + read-only sub-agents per call-graph cluster
                        (payment-gateway and webhook-dispatch have ≥10 entry points).
    Doc spot-check at planning: 5 README claims spot-checked; 2 stale (40% miss rate).
                                Calibration: aggressive doc skepticism in execution.
    Residual-unknown candidates pre-identified: cron timing on statement-export,
                                                payment-gateway region affinity.
    CAMPAIGN.md committed.

Sessions 2-6 (Execution, one per scoped unit):
    Session 2 (auth-bridge): 8 entry points. All 8 traced. 3 gotchas
                              (one critical: token refresh races with concurrent calls;
                              evidenced at file:line). Exit predicates closed.
    Session 3 (invoice-render + ledger-sync): 14 entry points combined; the shared
                              cache was the integration concern. 5 gotchas; 2 cross-
                              module data-structure invariants surfaced (recorded for
                              consolidation). Exit predicates closed; one residual
                              unknown (cache-eviction policy not derivable from code).
    Session 4 (payment-gateway): 11 entry points; sub-agents fanned out per region
                              client. 2 critical gotchas (PCI logging discipline, idempotency
                              key re-use under retry). Exit predicates closed.
    Session 5 (statement-export): 4 entry points. 1 residual unknown (cron timing —
                              expected from planning). Exit predicates closed.
    Session 6 (webhook-dispatch): 12 entry points; sub-agent fan-out. 4 gotchas.
                              Documentation showed 6 webhooks; code has 9 (3 stale-doc
                              findings recorded). Exit predicates closed.

Session 7 (Consolidation):
    Aggregate: 49 entry points across 5 units; 15 gotchas; 4 residual unknowns.
    Cross-module patterns: 3 (idempotency-key idiom in 2 of 5 units only, retry-policy
                            convention varies by unit, logging-discipline gap in
                            webhook-dispatch and payment-gateway).
    Risk map: 11 risks; 3 critical (token refresh race, PCI logging, webhook idempotency).
    Residual unknowns: 4 (escalated to former tech-lead via async).
    Prioritized backlog: 8 items for follow-on Development sessions (estimated 12-15
                         sessions over ~6 weeks, fitting the oncall-readiness window).
    Operational-responsibility sign-off: 3 of 4 residual unknowns gate-blocking;
                                         oncall assumable after their resolution + the
                                         3 critical risks closed.
    REPORT.md committed.

Total: 7 sessions over ~3 weeks at ~2 sessions/week.
```

### Interview campaign: 4-module service before the lead engineer departs

```
Campaign: Recommendation-service familiarization (pre-departure)
Mode: interview
Trigger: Lead engineer leaving in 4 weeks; service is opaque to remaining team;
         feature work and oncall both transferring.
Operational responsibility: feature work + oncall + code-review approval on the
                            4 recommendation-service modules.

Session 1 (Planning):
    Inventory: 4 modules (candidate-gen, ranker, exposure-budget, eval-loop). ~18K LOC.
    Estimate: 4 execution sessions, ~2.5 hours per unit; departing engineer has
              ~10 hours of question-round budget total.
    Decomposition: one execution session per module.
    Question rounds scheduled: round 1 (orientation, day -28), round 2 (mid-campaign
                               targeted, day -14), round 3 (cross-module reconciliation,
                               day -3).
    Round-1 questions pre-staged: 18 questions covering system overview, "what worries
                                  you we'll miss," ownership history, recent incidents.
    Sub-agent strategy: parent + read-only sub-agents per cluster.
    CAMPAIGN.md committed.

Round 1 interview conducted (90 min):
    18 questions answered. 4 follow-ups queued for round 2 (require code-level
    corroboration after execution sessions surface the relevant rows).
    Round-1 file committed.

Sessions 2-5 (Execution, one per module):
    Session 2 (candidate-gen): 9 entry points. Owner-bias check: cold read found an
                                error path the owner hadn't mentioned in round 1
                                (recorded; flagged for round-2 follow-up). 3 gotchas.
    Session 3 (ranker): 12 entry points; sub-agent fan-out by feature family. 5 gotchas;
                        2 owner-derived rows lack code corroboration (will resolve in
                        round 2 or downgrade to residual unknown).
    Session 4 (exposure-budget): 6 entry points. 2 gotchas.
    Session 5 (eval-loop): 8 entry points. 3 gotchas; one critical (eval-loop
                            silently masks ranker regressions under specific traffic shapes;
                            file:line evidence; round-2 follow-up to confirm intended).

Round 2 interview conducted (75 min):
    12 follow-ups asked (4 from round 1 + 8 from sessions). 10 resolved (5 raised
    rows to verified, 3 contradicted code reads — investigated in subsequent
    consolidation work, 2 filled gaps the code couldn't answer). 2 deferred to round 3.
    Round-2 file committed.

Round 3 interview conducted (60 min):
    Cross-module reconciliation focus + remaining 2 deferred follow-ups + succession-
    plan questions ("what would you check first if X went wrong"). All resolved.
    Round-3 file committed.

Session 6 (Consolidation):
    Aggregate: 35 entry points across 4 units; 13 gotchas; 1 residual unknown
               (one piece of institutional knowledge about a partner-team contract;
               escalated to that team).
    Owner-corroboration analysis: of 35 entry-point rows, 33 have code-level evidence;
                                  2 are interview-only (flagged in REPORT as
                                  uncorroborated owner claims).
    Cross-module patterns: 4 (consistent feature-store idiom across 3 of 4 modules;
                              eval-loop is the outlier, which is a finding).
    Risk map: 7 risks; 2 critical.
    Prioritized backlog: 6 items for follow-on Development sessions.
    Operational-responsibility sign-off: yes, with the 2 critical risks closed in
                                          the next 2 weeks (3 follow-on sessions).
    REPORT.md committed.

Total: 6 sessions + 3 interview rounds over ~4 weeks. Departing engineer left
       on schedule; campaign closed before their last day.
```
