# [Domain/Scope] [Campaign Name] Protocol

A multi-session campaign template for [describe the campaign-scale deliverable]. This protocol extends [`PARENT_WORKSTREAM.md`](PARENT_WORKSTREAM.md) — its [parent-workstream phase or primitive] is the per-session primitive this protocol scales into a [paper-wide / repository-wide / system-wide] discipline.

[Optional: any modes the protocol supports — e.g., creation/audit/maintenance — and a one-line description of each. Delete this paragraph if the protocol has only one mode.]

This is a **protocol**, not a workstream. It does not replace [parent workstream]; it prescribes a campaign structure for a specific deliverable: [name the campaign deliverable].

---

## Relationship to Other Documents

| Document | Role |
|----------|------|
| [`ITERATIVE_METHODOLOGY.md`](../ITERATIVE_METHODOLOGY.md) | Master framework — 9 principles, 6 phases, 12 quality gates. This protocol obeys all of them. See §Protocols and Multi-Session Campaigns. |
| [`PARENT_WORKSTREAM.md`](PARENT_WORKSTREAM.md) | Parent workstream. Defines the per-session primitives this protocol scales. |
| [`../starter-kit/SESSION_RUNNER.md`](../starter-kit/SESSION_RUNNER.md) | Operational checklist — every session in the campaign runs against it. |

[Add additional rows for sibling workstreams the protocol borrows session patterns from — e.g., `AUDIT_WORKSTREAM.md` for review-mode sessions.]

---

## When to Use

[State trigger conditions. Be specific — this is the "should I use this protocol?" gate. If multiple modes exist (creation/audit), provide trigger conditions per mode.]

### Triggers

[State the umbrella condition that makes this protocol applicable, AND any of:]
- [Specific trigger 1]
- [Specific trigger 2]
- [Specific trigger 3]

### When NOT to use

- [Case where the cost outweighs the value]
- [Case where a simpler tool fits — single session, sample-based audit, etc.]
- [Case where the deliverable is out of scope for this protocol]

---

## Why This Is a Campaign, Not a Mode

A single session attempting this campaign's full scope will fail in one of three ways:

1. **Context exhaustion.** [How holding the corpus, inputs, and per-unit ledger degrades reasoning quality long before raw token limits hit.]
2. **"1 and done" violation.** [Why this deliverable is hundreds of micro-deliverables fused into one artifact, and the second half receives less rigor than the first.]
3. **No resumability.** [Why a crashed mid-session leaves the next session unable to recover without checkpoint files.]

This protocol decomposes the work into a planning session, N execution sessions, and a consolidation session — each obeying the methodology's session-scope rules and producing a checkpoint deliverable.

---

## Campaign Structure

```
Session 1: Campaign Planning
    └─ Produces: CAMPAIGN.md ([what's in it])

Sessions 2..N+1: Per-Unit Execution (one per scoped unit)
                   └─ Produces: units/<unit>.md ([what's in it])

Session N+2: Consolidation
                   └─ Produces: REPORT.md ([what's in it])
```

[Describe typical campaign size. Where do per-unit splits happen? What governs N? Provide concrete numbers if possible.]

All campaign artifacts live under `[campaign-directory]/`:

```
[campaign-directory]/
├── CAMPAIGN.md                    # Planning session output
├── units/
│   ├── unit-1.md                  # Per-unit deliverables
│   └── ...
└── REPORT.md                       # Consolidation session output
```

---

## Session 1: Campaign Planning

A planning session per [`ITERATIVE_METHODOLOGY.md` §Session Types](../ITERATIVE_METHODOLOGY.md#planningpreparation-sessions). Heavy Phase 2; produces a Phase 3 design that subsequent sessions execute mechanically.

### Steps

1. [Step] — [what to produce / verify]
2. [Step] — [what to produce / verify]
3. **Choose the scoping unit.** Default: [default split]. Split smaller when [criterion]. Never split below [floor].
4. **Define the deliverable contract** (see Deliverable Contracts below). Lock the schema before execution begins; schema drift across units forces consolidation rework.
5. **Allocate sub-agent strategy.** [Decisions per unit: parent-only, parent-with-read-only-sub-agents, parallel sub-agents. See Sub-Agent Dispatch Pattern below.]
6. **Set exit criteria.** Per-unit completion thresholds and campaign-level halt conditions.
7. **Write `CAMPAIGN.md`** as the session's Phase 3 deliverable. Stakeholder approves before any execution session begins.

### Gate (Phase 4 in this session)

Stakeholder approval of `CAMPAIGN.md` is the second-highest-leverage gate in the protocol (after the per-execution-session implement gate). A bad plan multiplies cost across N sessions.

---

## Sessions 2..N+1: Per-Unit Execution

[Describe the per-session shape. Specify session type per `ITERATIVE_METHODOLOGY.md` §Session Types — implementation (all 6 phases) or review/audit (Phases 1-4 + 6, skip 5).]

### Common steps

1. **Pre-Flight.** Read `CAMPAIGN.md`. Read prior unit deliverables. Verify [domain-specific state] matches planning-session inventory.
2. **Phase 1.5 (Claim the Session).** Stub names the unit in progress. A ghost session here is detectable because the stub names exactly which unit was being worked on.
3. **Research.** [What to extract for this unit, with no exceptions.]
4. **[Mode-specific work]** (see below).
5. **Present.** Surface the unit deliverable to the stakeholder. Highlight: [protocol-specific items — e.g., blocked rows, calibration adjustments, patterns visible at unit scope].
6. **Phase 6 close-out.** Standard. Handoff records: [protocol-specific items].

### Mode-specific steps

[If the protocol supports multiple modes, describe each separately under sub-headings.]

### Critical disciplines

- **Evidence is non-negotiable.** [Define what "evidence" means in this protocol's deliverables — a quoted passage, a verified measurement, a reproducible test result.]
- **Append-only within a session.** Rows are not deleted. A row whose status changes during the session gets a `superseded` mark and a new row.
- [Other domain-specific disciplines.]

---

## Session N+2: Consolidation

A review/audit session whose deliverable is the campaign-wide report.

### Steps

1. **Pre-Flight.** Read `CAMPAIGN.md` and every unit deliverable. Verify completeness — no unit has unresolved [protocol-specific status] rows. If any do, this session halts and flags them as a follow-on execution session.
2. **Research.** Aggregate across units. Identify cross-unit patterns: [examples].
3. **Create the report.** [Use the structure below.] The consolidation session does **not** re-do per-unit work — its job is merging, pattern-finding, and remediation/integration planning.
4. **Present.** Stakeholder approves the report. Open items become input to follow-on sessions.
5. **Phase 6 close-out.** Standard.

### `REPORT.md` structure

```markdown
## Coverage
[What was covered, with statistics.]

## [Mode-specific findings/results structure]

## Cross-Unit Patterns
[What was visible at the campaign scale that wasn't visible per unit.]

## Open Items / Remediation Plan
[Prioritized punch list for follow-on sessions.]
```

---

## Sub-Agent Dispatch Pattern

[If applicable. Many protocols benefit from sub-agent fan-out at per-unit scale. Describe the pattern, when to fan out, and calibration rules. See `RESEARCH_EXHAUSTIVE_VERIFICATION_PROTOCOL.md` for a worked example.]

---

## Deliverable Contracts

### Per-unit schema

```markdown
| # | [Field 1] | [Field 2] | [Field 3] | [Status/Verdict] | [Evidence] |
|---|-----------|-----------|-----------|------------------|------------|
```

**[Status / Verdict] vocabulary:**

| Value | Meaning |
|-------|---------|
| [value] | [meaning] |

The vocabulary is **locked at planning time**. Schema drift across units forces consolidation rework.

---

## Calibration and Exit Criteria

### Baseline expectations

[If the protocol has empirical baselines from prior runs, document them with bands and recommended actions.]

| Observed [metric] | Interpretation | Action |
|--|--|--|
| [band] | [interpretation] | [action] |

### Stop conditions

The campaign **halts** (not pauses — halts) when:
- [Stop condition 1]
- [Stop condition 2]
- A systemic finding emerges that invalidates the campaign premise.
- Stakeholder direction changes.

A halted campaign produces a partial `REPORT.md` covering completed units. Do not synthesize coverage you did not produce.

---

## Resumability

Each unit deliverable is a checkpoint. After every execution session, commit the unit file before close-out:

```
[campaign-directory]/units/<unit>.md
```

A crashed mid-unit session is recovered by the next session reading the unit file from the last committed state and resuming from the first row marked [pending-status]. The Phase 1.5 stub records which unit is in progress, so a ghost session is detectable.

**Unit deliverables are append-only within a session.** Never delete a row; mark it `superseded` and add a new row. The history of changed statuses is itself a signal — for calibration, scope drift, and the consolidation session's pattern detection.

---

## Anti-Patterns

[Numbered list. Same discipline as workstream anti-patterns: every entry exists because a real session made that exact mistake. Do not add hypothetical entries until evidence accumulates.]

1. **One-session attempt.** Trying to run the entire campaign in a single session. Context degrades; the second half is less reliable than the first. Use the campaign decomposition.
2. **Skipping the planning session.** Jumping to per-unit execution without a `CAMPAIGN.md`. Schema drift across units forces consolidation rework that exceeds the planning-session cost.
3. **Evidence-free rows.** Marking a row complete without the required evidence. The unit deliverable becomes an assertion list, not a [verified / drafted / audited] record.
4. **Cross-unit consolidation creep.** Doing per-unit work in the consolidation session because "I notice a problem in this unit while merging." Stop, log it as a follow-on, return to merging.
5. **Sub-agent calibration drift.** Dispatching sub-agents without explicit vocabulary calibration. Different sub-agents will produce different rates of [protocol-specific verdicts] for identical evidence.
6. [Domain-specific anti-pattern from real sessions in this protocol.]

---

## Verification Checklist

### Per execution session, before close-out

- [ ] Every [unit-scope claim/item] has a row in the [map/grid]
- [ ] Every row has a [status/verdict] drawn from the locked vocabulary
- [ ] Every row has the required evidence
- [ ] No row is in a transient/pending state
- [ ] Unit deliverable is committed
- [ ] Handoff records sub-agent strategy and calibration adjustments

### Per campaign, before close-out (consolidation session)

- [ ] Every unit listed in `CAMPAIGN.md` has a corresponding deliverable
- [ ] No unit deliverable contains pending or open rows
- [ ] Statistics tables sum correctly to total counts
- [ ] Every finding cites at least one unit deliverable row as evidence
- [ ] Cross-unit patterns are surfaced explicitly, not buried in per-finding remediation
- [ ] Remediation plan is ordered by priority and dependency, not by unit order
- [ ] Estimate-to-actual ratio is recorded for future-campaign calibration

---

## Example Campaign Outline

```
Campaign: [Name]
Mode: [creation/audit/etc.]
Trigger: [What kicked off this campaign]

Session 1 (Planning):
    Inventory: [what was inventoried]
    Estimate: [N units, M items per unit]
    Decomposition: [per-unit split]
    Sub-agent strategy: [chosen pattern]
    CAMPAIGN.md committed.

Sessions 2..N+1 (Execution, one per unit):
    Session 2 (unit-1): [results, calibration, anomalies]
    ...

Session N+2 (Consolidation):
    Aggregate: [totals, ratios]
    Cross-unit patterns: [what emerged]
    Findings/Open items: [count, priorities]
    Recommendation: [follow-on session count]
    REPORT.md committed.

Total: [N] sessions over [duration].
```
