# Research Exhaustive Verification Protocol

A multi-session campaign template for guaranteeing that *every* numeric, dated, and attributed claim in a research-documentation deliverable is supported by a quoted passage from a verified primary source. This protocol extends [`RESEARCH_DOCUMENTATION_WORKSTREAM.md`](RESEARCH_DOCUMENTATION_WORKSTREAM.md) — its Phase 3 Claim-Source Map and Phase 6 Claim-Source Audit are the per-section primitives this protocol scales into a paper-wide or repository-wide discipline.

The protocol is explicitly **bidirectional**:

- **Creation mode** — used while writing or extending papers. The claim-source map *gates* drafting: a section is not written until every claim it will contain has a verified quoted passage on file.
- **Audit mode** — used to verify an existing repository whose prior work was done without this discipline. Per-claim verdict grids replace the workstream's Audit-Mode sampling.

Both modes share the same campaign shape (planning → per-unit work → consolidation) because both run into the same wall: a non-trivial paper or repository contains hundreds of claims, and verifying them in a single session degrades reasoning quality long before it exhausts raw context.

This is a **protocol**, not a workstream. It does not replace the Research Documentation workstream; it prescribes a campaign structure for a specific deliverable: a complete, primary-source-anchored claim record.

---

## Relationship to Other Documents

| Document | Role |
|----------|------|
| [`ITERATIVE_METHODOLOGY.md`](../ITERATIVE_METHODOLOGY.md) | Master framework — 9 principles, 6 phases, 12 quality gates. This protocol obeys all of them. |
| [`RESEARCH_DOCUMENTATION_WORKSTREAM.md`](RESEARCH_DOCUMENTATION_WORKSTREAM.md) | Parent workstream. Defines the Claim-Source Map (Phase 3), Claim-Source Audit (Phase 6), and standard sampling-based Audit Mode. |
| [`AUDIT_WORKSTREAM.md`](AUDIT_WORKSTREAM.md) | Sibling workstream. Audit-mode sessions in this protocol follow its review-session pattern (Phases 1-4 + 6, skip 5). |
| [`../starter-kit/SESSION_RUNNER.md`](../starter-kit/SESSION_RUNNER.md) | Operational checklist — every session in the campaign runs against it. |

---

## When to Use

### Creation-mode triggers

Use creation mode when the deliverable is a paper, paper series, or synthesis whose evaluation will turn on the strength of every citation, AND any of:

- The paper exceeds the claim density (~75 numeric/dated/attributed claims) that one session can produce-and-verify cleanly
- The deliverable is a synthesis pulling claims from multiple prior dimension papers (cross-paper claim consistency is a first-class concern)
- A regulatory submission, peer-reviewed publication, dissertation chapter, or expert-witness report is the target — venues where "most claims are verified" fails the standard
- Multiple sessions will contribute to one paper, and you need a shared claim ledger that survives across them

### Audit-mode triggers

Use audit mode when verifying an existing repository, AND any of:

- A prior sampling-based audit (per Audit Mode in `RESEARCH_DOCUMENTATION_WORKSTREAM.md`) returned an unsupported rate substantially above the ~22% baseline
- The repository was inherited and prior verification cannot be trusted
- A high-stakes downstream use is imminent (filing, publication, defense) and you need a complete record before signing off

### When NOT to use either mode

- Internal drafts, working documents, or pre-stakeholder-review iterations — exhaustive verification is overhead until the content stabilizes
- Time-to-deliver dominates over completeness — produce a sample-based result with explicit coverage caveats instead
- The deliverable's reader-trust is elastic (informal memos, hypothesis-formation drafts) — apply the workstream's standard per-section discipline and skip the campaign machinery

### Mode selection and mode mixing

Mode is usually unambiguous from context: are you writing or are you reviewing? When both apply (writing paper N while inherited papers 1..N-1 contain unverified claims that paper N will cite), **run the audit campaign first, then the creation campaign**. Do not interleave modes within a single campaign — the verdict vocabulary and the status vocabulary are different (see Deliverable Contracts), and mixing them produces unit deliverables that the consolidation session cannot cleanly merge.

---

## Why This Is a Campaign, Not a Mode

A single session that attempts exhaustive verification across a non-trivial paper or repository will fail in one of three ways:

1. **Context exhaustion.** Even on a 1M-token model, holding the corpus, the paper text, and a per-claim ledger degrades reasoning quality on later claims long before raw token limits hit. Earlier claims compete with later ones for attention; the ledger entries written in the last quarter of the session are measurably less reliable than those in the first quarter.
2. **"1 and done" violation.** [Principle 9](../ITERATIVE_METHODOLOGY.md#9-session-scope-bounding) bounds every session to one deliverable. A 500-claim verification is not one deliverable; it is hundreds of micro-deliverables fused into a single artifact, and the second half receives less rigor than the first.
3. **No resumability.** A session that crashes mid-run (context loss, timeout, ghost session) leaves the next session unable to determine which claims were verified. Without checkpoint files, the entire run must restart.

This protocol decomposes the work into a planning session, N execution sessions, and a consolidation session — each obeying the methodology's session-scope rules and producing a checkpoint deliverable.

---

## Campaign Structure

```
Session 1: Campaign Planning
    └─ Produces: CAMPAIGN.md (mode, decomposition, deliverable contracts, budget)

Sessions 2..N+1: Per-Unit Execution (one per scoped unit)
    Creation mode: build claim-source map → draft section → verify rendered output
                   └─ Produces: units/<unit>.md (claim-source map, status-tracked)
    Audit mode:    extract claims → verify against cited sources → grid with verdicts
                   └─ Produces: units/<unit>.md (verdict grid)

Session N+2: Consolidation
    Creation mode: cross-paper consistency, bibliography integrity, render verification
                   └─ Produces: REPORT.md (integration report + open items)
    Audit mode:    cross-unit pattern detection, severity-ordered findings, remediation plan
                   └─ Produces: REPORT.md (finding report + follow-on session list)
```

A creation campaign for a 4-paper synthesis series is typically 6 sessions (1 + 4 + 1). An audit campaign for a 5-paper inherited repository is typically 7 sessions (1 + 5 + 1). Per-section splits are standard when claim density exceeds ~75 per paper.

All campaign artifacts live under `verification/exhaustive/`:

```
verification/exhaustive/
├── CAMPAIGN.md                    # Planning session output
├── units/
│   ├── paper-1.md                 # Per-unit deliverables (map or grid by mode)
│   ├── paper-2.md
│   └── ...
└── REPORT.md                       # Consolidation session output
```

---

## Session 1: Campaign Planning

A planning session per [Iterative Methodology §Session Types](../ITERATIVE_METHODOLOGY.md#planningpreparation-sessions). Heavy Phase 2; produces a Phase 3 design that subsequent sessions execute mechanically.

### Common steps (both modes)

1. **Inventory the corpus.** Apply `RESEARCH_DOCUMENTATION_WORKSTREAM.md` Phase 2 Steps 2–5 (corpus inventory, pre-flag, retrieval, filename verification) before any claim work. Without a verified corpus, the campaign grades or builds against the wrong files.
2. **Estimate claim count per scoped unit.** Sample 10 claims per paper and extrapolate. Record the estimate; the consolidation session will compare actual to estimate as a calibration signal for future campaigns.
3. **Choose the scoping unit.** Default: one execution session per paper. Split per-section when estimated claims exceed ~75 per paper. Never split below the section level — sub-section splits fragment claim context and produce inconsistent maps or verdicts.
4. **Define the deliverable contract** (see Deliverable Contracts). Lock the schema before execution begins; schema drift across units forces consolidation rework.
5. **Allocate sub-agent strategy.** For each unit, decide: parent-only, parent-with-read-only-sub-agents (recommended), or parallel-sub-agents-per-section. See Sub-Agent Dispatch Pattern.
6. **Set exit criteria.** Per-unit completion thresholds and campaign-level halt conditions (a critical-finding count threshold for audit; a blocked-claim-count threshold for creation).
7. **Write `CAMPAIGN.md`** as the session's Phase 3 deliverable. Stakeholder approves before any execution session begins.

### Creation-mode specifics

- Identify which papers are being written or extended in this campaign (in scope) versus which exist as inherited context (out of scope, but provide claim-input). If inherited papers also need verification, run an audit campaign first.
- Identify the bibliography integration plan: single project-wide `.bib` file, or per-paper `.bib` files merging into a synthesis `.bib`. Citation key conflicts must be resolved at planning time.
- Identify which sections will be drafted vs. extended vs. left untouched. The claim-source map is built only for sections that will see new or modified content.
- Estimate the corpus retrieval gap: how many primary sources do you need that you don't yet have? Retrieve them during planning if possible, before execution sessions burn time on retrieval workarounds.

### Audit-mode specifics

- Identify which papers are in audit scope and which are excluded (and why — exclusions are findings).
- Identify the verdict vocabulary that will apply (see Deliverable Contracts). The default is verified / re-attribute / remove / source-missing / pending; tune for the specific repository if a category is missing.
- Set the severity-calibration threshold: at what re-attribute rate does the campaign halt for stakeholder review of audit calibration?

### Gate (Phase 4 in this session)

Stakeholder approval of `CAMPAIGN.md` is the **second-highest-leverage gate in the protocol** (after the per-execution-session implement gate). A bad plan multiplies cost across N sessions.

---

## Sessions 2..N+1: Per-Unit Execution

Each execution session is bounded to one scoped unit. The session type differs by mode:

- **Creation mode:** Standard implementation session per [Iterative Methodology §Phases](../ITERATIVE_METHODOLOGY.md#the-6-phases) — all 6 phases apply, since the deliverable includes drafted text (Phase 5 is mechanical writing of pre-verified content).
- **Audit mode:** Review/audit session per [Iterative Methodology §Session Types](../ITERATIVE_METHODOLOGY.md#reviewaudit-sessions) — Phases 1-4 + 6, skip Phase 5.

### Common steps (both modes)

1. **Pre-Flight.** Read `CAMPAIGN.md`. Read prior execution sessions' unit deliverables if any exist. Verify the corpus state for this unit's sources matches the planning-session inventory.
2. **Phase 1.5 (Claim the Session).** Write the stub naming the unit in progress. A ghost session here is detectable because the stub names exactly which unit was being worked on.
3. **Research.** For this unit only, build the claim list. Every numeric, dated, and attributed claim in the unit's scope gets a row, with no exceptions. (A claim you skip cannot be verified later without re-reading the source.)
4. **Mode-specific work** (see below).
5. **Present.** Surface the unit deliverable to the stakeholder. Highlight: blocked or re-attribute rows (these need attention before consolidation), patterns visible at unit scope, and any sub-agent calibration adjustments made mid-session.
6. **Phase 6 close-out.** Standard. Handoff records: sub-agent strategy used, calibration adjustments, claim-count estimate-vs-actual, which checkpoints were committed.

### Creation-mode steps (Phases 3-5)

1. **Build the claim-source map.** For each claim the section will contain, record:
   - The claim as it will be made (≤30 words)
   - The cited source (citation key + on-disk path)
   - The quoted passage from the source that supports the claim (≤40 words)
   - The status: `planned` (claim identified, source verified, ready to draft) / `pending-source-retrieval` (claim needed, source not yet on disk) / `blocked` (cannot be supported by any available primary; either re-frame or remove from the plan)
2. **Resolve all `pending-source-retrieval` and `blocked` rows before drafting.** Drafting against a half-built map produces text that the audit step in Phase 6 will then have to flag and rewrite — wasteful. Apply the WAF retrieval hierarchy (`RESEARCH_DOCUMENTATION_WORKSTREAM.md` Phase 2 Step 4); if a primary cannot be retrieved, decide at planning level whether to re-frame the claim or drop it. **Never draft against a `blocked` row.**
3. **Draft the section.** Write only against `planned` rows. Each drafted sentence that asserts a claim should map to one (or more) row in the map; each map row should map to at least one drafted sentence.
4. **Update map status to `drafted`** for each row as its corresponding sentence is written. Rows that ended up unused stay as `planned` and become candidates for the consolidation report (they may indicate a planning-vs-drafting scope mismatch).
5. **Render and verify** the section. Confirm citations resolve, cross-references resolve, and no `?@fig-x` artifacts remain. **The Phase 6 Claim-Source Audit from the parent workstream still runs at the section level** — exhaustive verification at planning time does not exempt the rendered output from a final correctness check.
6. **Commit the unit deliverable** (`verification/exhaustive/units/<unit>.md`) along with the drafted section and any updated bibliography entries.

### Audit-mode steps (Phases 3-4 + 6)

1. **Extract claims from the existing text.** For each claim in the unit's scope, populate the grid skeleton with: section/line, claim text (≤30 words), citation key.
2. **Verify each claim against its cited source.** For each row, dispatch verification (sub-agent or self). Record: verdict (verified / re-attribute / remove / source-missing / pending), quoted passage from the source (≤40 words) or explicit annotation `(source contains X, not Y)`, severity if failing, and recommendation.
3. **Resolve all `pending` rows before close-out.** A row left as `pending` is deferred work that the next session must redo. (See [`RESEARCH_DOCUMENTATION_WORKSTREAM.md`](RESEARCH_DOCUMENTATION_WORKSTREAM.md) §Phase 6 — "audit-failed claims may still be true." Do one round of primary-source retrieval before recommending `remove`.)
4. **Surface unit-scope patterns.** If the same secondary source produces three or more re-attribute rows in this unit, that is a finding for the consolidation session — note it in the unit's tail.
5. **Commit the unit deliverable** (`verification/exhaustive/units/<unit>.md`).

### Critical disciplines (both modes)

- **Evidence is non-negotiable.** A row without a quoted passage (or, for audit `re-attribute`/`source-missing` rows, an explicit `(source contains X, not Y)` annotation) is not a verified or audited row. It is an assertion. The consolidation session will reject it.
- **Verdict and status independence.** A claim being *true* does not make it `verified`; a verified `re-attribute` recommendation does not make it `verified`. The vocabularies grade source-claim correspondence, not factual reality. Most papers have a few claims that are true but unsupported by their cited source — those are exactly what this protocol exists to catch.
- **Append-only within a session.** Rows are not deleted. A row whose verdict or status changes during the session gets a `superseded` mark and a new row. The history is itself an audit signal.

---

## Session N+2: Consolidation

A review/audit session whose deliverable is the campaign-wide report.

### Common steps (both modes)

1. **Pre-Flight.** Read `CAMPAIGN.md` and every unit deliverable. Verify completeness — no unit has unresolved `pending` (audit) or `blocked`/`pending-source-retrieval` (creation) rows. If any do, this session halts and flags them as a follow-on execution session.
2. **Research.** Aggregate across units. Identify cross-unit patterns: same source cited differently in two papers, same numeric claim restated with conflicting numbers, citation-key collisions, sources that fail repeatedly.
3. **Create the report** using the mode-specific structure below. The consolidation session does **not** re-verify claims or draft new sections — its job is merging, pattern-finding, and remediation/integration planning. Re-verification is per-unit work; doing it here violates session scope.
4. **Present.** Stakeholder approves the report. For creation mode: the report's open items (unused planned rows, cross-paper inconsistencies, render warnings) become input to follow-on writing sessions. For audit mode: the remediation punch list becomes input to follow-on Research Documentation sessions.
5. **Phase 6 close-out.** Standard. Recommendation typically opens a follow-on session series.

### Creation-mode `REPORT.md` structure

```markdown
## Coverage
- Papers in scope: [list]
- Sections drafted: X of Y planned
- Total claims drafted-against-verified-map: N
- Unused planned rows: M (with sections — these may indicate scope drift)

## Map Statistics
| Status | Count | % |
|--------|-------|---|
| drafted | | |
| planned-unused | | |
| pending-source-retrieval (deferred) | | |
| blocked (deferred) | | |

## Cross-Paper Consistency
- Citation key consistency across papers: [pass/fail with specifics]
- Numeric claims appearing in multiple papers: [reconciliation table]
- Bibliography integrity: [single source-of-truth verified, conflicts resolved]

## Render Verification
- All papers render to all target formats: [pass/fail per paper per format]
- No missing citations across the series
- No broken cross-references across the series
- Adjacent (out-of-scope) papers still render

## Open Items
Prioritized list for follow-on writing sessions:
| Priority | Item | Affected Paper | Action |
```

### Audit-mode `REPORT.md` structure

```markdown
## Coverage
- Units audited: X of Y (with reason for any exclusions)
- Total claims verified: N
- Per-unit claim counts: [breakdown]
- Estimate-to-actual ratio: [calibration signal]

## Verdict Distribution
| Verdict | Count | % |
|---------|-------|---|
| verified | | |
| re-attribute | | |
| remove | | |
| source-missing | | |

## Findings (Severity-Ordered)
For each finding:
- Severity: critical / moderate / minor
- Anti-pattern: #N from `RESEARCH_DOCUMENTATION_WORKSTREAM.md`
- Affected claims: [unit deliverable row IDs]
- Cross-unit pattern: yes/no (if yes, describe)
- Remediation: specific action

## Structural Observations
- Cross-unit patterns (systemic vs. one-off)
- Sources that fail repeatedly (candidates for removal from corpus)
- Sections or papers that pass cleanly (reference implementations)

## Remediation Plan
Prioritized punch list for follow-on Research Documentation sessions:
| Priority | Affected Unit | Action | Estimated Sessions |
```

---

## Sub-Agent Dispatch Pattern

The parent agent's context is the campaign's bottleneck. Sub-agents protect it. The pattern below works for both modes.

### Recommended pattern

For each unit:

1. **Parent** reads the unit's text (creation: the planning notes for the section; audit: the existing section), extracts the claim list, populates the unit deliverable's skeleton (claim text + intended/cited source + section/line).
2. **Sub-agent** receives a single claim row + the relevant source file. Returns: the quoted passage, status/verdict, recommendation. The sub-agent never sees the full paper or the full corpus — its context is one claim and one source.
3. **Parent** writes the result into the unit deliverable, applies any required corpus updates with its own write permissions, and (in creation mode) drafts the corresponding sentence.

**Why this works:** sub-agent context holds at most one source PDF + one claim. It can use Level 4 (implementation reading) verification without polluting the parent's context with the source's full text. The parent retains the strategic view across the unit.

### When to fan out

Parallel sub-agents (one per claim or one per section) are appropriate when:
- Claim count per unit exceeds ~50
- Sub-agent permission asymmetry permits read-but-not-write (parent must apply edits anyway — see [`RESEARCH_DOCUMENTATION_WORKSTREAM.md`](RESEARCH_DOCUMENTATION_WORKSTREAM.md) §Sub-Agent Permission Asymmetry)
- Claims are independent (cross-claim consistency checks happen at the parent level)

### Verdict and status calibration

Different sub-agents apply different standards unless given explicit calibration. Include in every sub-agent prompt:

- The full vocabulary (verdict for audit, status for creation)
- An example of each value
- The "true but unsupported" framing — a claim being factually correct does not make it `verified` (audit) or eligible to be `drafted` against (creation); only quoted-passage support does
- The evidence requirement (≤40 words, exact text)

---

## Deliverable Contracts

### Per-unit creation map schema

```markdown
| # | Section | Claim (≤30 words) | Cited Source | Source on Disk? | Quoted Passage (≤40 words) | Status | Drafted Sentence Ref |
|---|---------|-------------------|--------------|-----------------|----------------------------|--------|---------------------|
| 1 | §2.1    | "Reserves grew 14% YoY in 2023"            | smith2024 | yes | "Total reserves increased to $4.2B from $3.7B…" | drafted | §2.1 ¶2 sentence 3 |
| 2 | §2.1    | "Solvency II ratio is 187%"                | wyman2024 | yes | (consultant report contains 192%, not 187%; primary EIOPA filing reports 187%) | pending-source-retrieval | (not drafted) |
| 3 | §3.4    | "Cytora processes 40K policies/day"        | cytora_landing | stub | (cytora_landing is a marketing page, not the cited statistic) | blocked | (will not draft) |
```

**Status vocabulary (creation):**
| Value | Meaning |
|-------|---------|
| `planned` | Claim identified, source verified, ready to draft |
| `drafted` | Sentence written; row is closed |
| `pending-source-retrieval` | Source needed but not yet on disk; deferred |
| `blocked` | No primary source supports this claim; do not draft |
| `superseded` | This row was replaced by another (history) |

### Per-unit audit grid schema

```markdown
| # | Section | Claim (≤30 words) | Cited Source | Verdict | Quoted Passage (≤40 words) | Severity if Failing | Recommendation |
|---|---------|-------------------|--------------|---------|------------------------------|---------------------|----------------|
| 1 | §2.1    | "Reserves grew 14% YoY in 2023"     | smith2024      | verified         | "Total reserves increased to $4.2B from $3.7B…" | — | — |
| 2 | §2.1    | "Solvency II ratio is 187%"         | wyman2024      | re-attribute     | (consultant report contains 192%, not 187%; primary EIOPA filing reports 187%) | moderate | Re-cite to EIOPA 2024 Q3 filing |
| 3 | §3.4    | "Cytora processes 40K policies/day" | cytora_landing | source-missing   | (cytora_landing is a marketing page, not the cited statistic) | critical | Retrieve primary; if not found, remove claim |
```

**Verdict vocabulary (audit):**
| Value | Meaning |
|-------|---------|
| `verified` | Source contains a passage that supports the claim as cited |
| `re-attribute` | Claim may be true, but cited source does not support it; another source does |
| `remove` | Claim is unsupported by any retrievable primary; recommend removal |
| `source-missing` | Cited source is absent, a stub, or unrelated; needs retrieval before verdict can finalize |
| `pending` | Verification not yet performed (in-progress; should be 0 at session close) |
| `superseded` | This row was replaced by another (history) |

**Severity vocabulary (audit findings, not per-row):**
| Value | Meaning |
|-------|---------|
| `critical` | Load-bearing claim is materially wrong, OR source is wholly absent in a load-bearing context, OR framing language asserts a constraint as a goal in a load-bearing section |
| `moderate` | Claim is re-attributable without weakening the argument; figure with no provenance; redundant restatement |
| `minor` | Search artifact; bibliography entry style inconsistency; claim is correct but cited to a less-authoritative source than is locally available |

---

## Calibration and Exit Criteria

### Audit-mode baseline

The Research Documentation workstream cites an empirical baseline of ~22% unsupported claims and ~12% needing re-attribution from one real-world session. Use these as **expected ranges**, not pass/fail thresholds:

| Observed re-attribute rate | Interpretation | Action |
|----------------------------|----------------|--------|
| <5% | Either the corpus is exceptionally clean, or the audit is too lenient | Spot-check 10 `verified` rows with a fresh sub-agent for second opinions |
| 5–25% | Within expected range | Proceed to consolidation |
| >35% | Either the corpus is exceptionally compromised, or the audit is too strict | Halt; review verdict-calibration with stakeholder before continuing |

### Creation-mode baseline

Creation mode's analogous signal is the `blocked` and `pending-source-retrieval` rate at planning time:

| Observed blocked + pending rate | Interpretation | Action |
|---------------------------------|----------------|--------|
| <10% | Healthy — most planned claims have available primaries | Proceed |
| 10–30% | Normal for a cross-domain synthesis | Resolve via retrieval before drafting; budget extra retrieval time |
| >30% | The paper plan rests heavily on sources you don't have | Halt; revisit scope with stakeholder before committing to drafting |

### Stop conditions

The campaign halts (not pauses — halts) when:

- **Audit:** critical-finding count exceeds the planning-session threshold (default: 10 per unit, 30 campaign-wide)
- **Creation:** `blocked` count for a single section exceeds 25% of its planned claims
- A systemic finding emerges that invalidates the campaign premise (corpus is the wrong version; paper plan rests on a misread of the domain)
- Stakeholder direction changes ("we're rewriting the framing"; "pause this audit, we're going to file early")

A halted campaign produces a partial `REPORT.md` covering completed units. Do not synthesize coverage you did not produce.

---

## Resumability

Each unit deliverable is a checkpoint. After every execution session, commit the unit file before close-out:

```
verification/exhaustive/units/<unit>.md
```

A crashed mid-unit session is recovered by the next session reading the unit file from the last committed state and resuming from the first row marked `pending` (audit) or `planned` (creation, undrafted). The Phase 1.5 stub records which unit is in progress, so a ghost session is detectable.

**Unit deliverables are append-only within a session.** Never delete a row; mark it `superseded` and add a new row. The history of changed verdicts or statuses is itself a signal — for audit calibration, for creation scope drift, and for the consolidation session's pattern detection.

---

## Anti-Patterns

### Shared (both modes)

1. **One-session attempt.** Trying to run the entire campaign in a single session. Context degrades; the second half is less reliable than the first. Use the campaign decomposition.
2. **Skipping the planning session.** Jumping to per-unit execution without a `CAMPAIGN.md`. Schema drift across units forces consolidation rework that exceeds the planning-session cost.
3. **Evidence-free rows.** Marking a row `verified` or `drafted` without a quoted passage. The unit deliverable becomes an assertion list, not an audit or a verified plan.
4. **Cross-unit consolidation creep.** Doing per-unit work in the consolidation session because "I notice a problem in this paper while merging." Stop, log it as a follow-on, return to merging.
5. **Sub-agent verdict/status drift.** Dispatching sub-agents without explicit calibration. Different sub-agents will produce different rates of `re-attribute` (audit) or `blocked` (creation) for identical evidence.
6. **Filename trust at execution time.** Trusting that `smith2024.pdf` is Smith 2024 because it was named that way. The planning session's corpus inventory is the source of truth for what each file contains.
7. **Estimate amnesia.** Failing to record planning-session estimates, so the consolidation session cannot compare estimate-to-actual. The ratio is a calibration signal for future campaigns.
8. **Mode mixing within one campaign.** Running audit on some units and creation on others within the same `CAMPAIGN.md`. The vocabularies don't merge cleanly. Run sequential campaigns instead.

### Creation-mode-specific

9. **Drafting against a half-built map.** Writing sentences before all rows in the section's map are `planned`. The Phase 6 Claim-Source Audit then has to flag and rewrite — wasted work. Resolve `pending-source-retrieval` and `blocked` rows first.
10. **Map-drift drafting.** Writing sentences that don't correspond to any row in the map (because they "obviously don't need a citation") and discovering at audit time that they did. If you write a numeric, dated, or attributed statement, it gets a row — even if the row's status is `(self-evident)` and the source is the project itself.
11. **Re-verification in consolidation.** Re-opening sources at consolidation time to second-guess unit-level verifications. Consolidation aggregates and patterns; if you don't trust per-unit work, the campaign has a structural problem to fix, not a per-row problem.
12. **Rendering only at the end.** Deferring render-verification until the consolidation session. A bibliography that broke in unit 3 produces silent failures in units 4-7. Render at every checkpoint.

### Audit-mode-specific

13. **Severity inflation in findings.** Marking every `re-attribute` as critical. Critical means the cited claim is materially wrong AND the claim is load-bearing for the paper's argument. Most re-attributions are moderate.
14. **Premature remediation.** Editing the papers during the audit campaign. The campaign produces an audit; remediation is a follow-on workstream. Mixing them violates session scope and contaminates the audit's verdicts (a verdict on an edited claim is not the same as a verdict on the original).
15. **Re-verifying in consolidation.** Same as creation #11 — consolidation aggregates; trust the per-unit work or fix the per-unit process.

---

## Verification Checklist

### Per execution session, before close-out (creation mode)

- [ ] Every claim the section will contain has a row in the map
- [ ] Every row has a status drawn from the locked vocabulary
- [ ] No row is `pending-source-retrieval` or `blocked` while its corresponding section has been drafted
- [ ] Every `drafted` row has a quoted passage in the source-passage column AND a sentence reference in the drafted-sentence column
- [ ] The drafted section renders cleanly to every target format
- [ ] Phase 6 Claim-Source Audit (per `RESEARCH_DOCUMENTATION_WORKSTREAM.md`) ran on the rendered output — exhaustive planning does not exempt the final correctness check
- [ ] Unit deliverable is committed to `verification/exhaustive/units/<unit>.md`
- [ ] Handoff records sub-agent strategy, calibration adjustments, and any rows that ended up unused

### Per execution session, before close-out (audit mode)

- [ ] Every claim in the unit's text appears as a row in the grid
- [ ] Every row has a verdict drawn from the locked vocabulary
- [ ] Every non-`verified` row has a quoted passage or explicit `(source contains X, not Y)` annotation
- [ ] Every `re-attribute` row has a specific replacement source recommendation
- [ ] No row is `pending`
- [ ] Unit deliverable is committed to `verification/exhaustive/units/<unit>.md`
- [ ] Handoff records sub-agent strategy and any calibration adjustments

### Per campaign, before close-out (consolidation session)

- [ ] Every unit listed in `CAMPAIGN.md` has a corresponding deliverable
- [ ] No unit deliverable contains `pending` (audit) or open `pending-source-retrieval`/`blocked` (creation) rows
- [ ] Statistics tables sum correctly to total claim counts
- [ ] Every finding (audit) or open item (creation) cites at least one unit deliverable row ID as evidence
- [ ] Cross-unit patterns are surfaced explicitly, not buried in per-finding remediation
- [ ] Remediation plan (audit) or open-items list (creation) is ordered by priority and dependency, not by paper order
- [ ] Estimate-to-actual ratio is recorded for future-campaign calibration

---

## Example Campaign Outlines

### Creation campaign: 4-paper synthesis series

```
Campaign: Solvency II Synthesis Series — Capital, Fairness, Resilience, Integration
Mode: creation
Trigger: Filing target in 8 weeks; series will be peer-reviewed before submission

Session 1 (Planning):
    Inventory: 4 papers in scope (3 dimension papers + 1 integration);
              corpus has 287 PDFs, 12 missing primary sources flagged.
    Estimate: 327 claims total (capital: 88, fairness: 71, resilience: 95,
             integration: 73). Integration paper inherits ~40% of its claims
             from the dimension papers — those rows will reference dimension-paper
             map rows rather than re-mapping.
    Decomposition: one execution session per paper. Integration paper depends
                   on the three dimension papers (must be sessions 2-4 before 5).
    Sub-agent strategy: parent + read-only sub-agents per claim.
    Retrieval: 8 of 12 missing sources retrieved during planning via WAF
              hierarchy; 4 deferred to in-session retrieval.
    CAMPAIGN.md committed.

Sessions 2-5 (Execution, one per paper):
    Session 2 (capital): 91 claims (estimate 88). 87 drafted, 2 pending → resolved
                         by EIOPA Q3 filing retrieval mid-session, drafted, 2
                         blocked (over-specific market-share figure with no
                         primary; re-framed to "leading European insurers" range
                         claim using sector report).
    Session 3 (fairness): 73 claims. 68 drafted, 3 blocked (fairness metric
                          definition disputed across sources; deferred to
                          stakeholder review), 2 pending-retrieval.
    Session 4 (resilience): 98 claims. 94 drafted, 4 pending-retrieval.
    Session 5 (integration): 69 claims (estimate 73). 38 inherited rows
                             (cross-referenced to dimension papers' maps);
                             31 new rows. All 69 drafted.

Session 6 (Consolidation):
    Aggregate: 331 claims drafted (estimate 327; +1.2% drift, acceptable).
    Status distribution: 318 drafted (96.1%), 8 pending-retrieval-deferred (2.4%),
                         5 blocked (1.5%).
    Cross-paper consistency: 7 numeric claims appear in 2+ papers; all consistent
                              after one round of reconciliation in session 5.
    Bibliography: single project .bib (155 entries); no key collisions.
    Render: all 4 papers render to PDF, HTML, DOCX cleanly. No missing citations.
            Capital paper required one cross-ref fix in §3.2.
    Open items: 5 blocked claims need stakeholder decision (re-frame or remove);
                8 pending-retrieval claims need one more retrieval round.
                Recommendation: 2 follow-on writing sessions (one to resolve
                blocked claims with stakeholder; one to integrate retrieved
                sources for pending claims).
    REPORT.md committed.

Total: 6 sessions over ~3 working weeks at 2 sessions/week.
```

### Audit campaign: 5-paper inherited repository

```
Campaign: Inherited Solvency II Repository — Full Verification
Mode: audit
Trigger: Pre-submission audit before regulatory comment-letter filing;
         repository inherited from prior consultant; unverified.

Session 1 (Planning):
    Inventory: 5 papers, 312 PDFs in corpus, 8 missing primary sources flagged.
    Estimate: 487 claims total (paper-1: 89, paper-2: 71, paper-3: 142,
             paper-4: 95, paper-5: 90).
    Decomposition: paper-1, paper-2, paper-4, paper-5 each one session;
                   paper-3 split into two sessions (intro+capital, fairness+resilience)
                   because >75 estimated claims.
    Sub-agent strategy: parent + read-only sub-agents per claim (paper-3 sections).
    CAMPAIGN.md committed.

Sessions 2-7 (Execution, one per scoped unit):
    Session 2 (paper-1): 91 actual claims. 78 verified, 9 re-attribute, 4
                         source-missing. 1 critical finding.
    Session 3 (paper-2): 73 claims. 64 verified, 7 re-attribute, 2 remove.
                         0 critical.
    Session 4 (paper-3a): 78 claims. 61 verified, 14 re-attribute, 3 source-missing.
                          2 critical.
    Session 5 (paper-3b): 67 claims. 55 verified, 9 re-attribute, 3 source-missing.
                          1 critical.
    Session 6 (paper-4): 98 claims. 87 verified, 8 re-attribute, 3 source-missing.
                         0 critical.
    Session 7 (paper-5): 92 claims. 80 verified, 10 re-attribute, 2 source-missing.
                         1 critical.

Session 8 (Consolidation):
    Aggregate: 499 claims (estimate 487; +2.5% drift, acceptable).
    Verdict distribution: 425 verified (85.2%), 57 re-attribute (11.4%),
                          2 remove (0.4%), 15 source-missing (3.0%).
    Re-attribute rate 11.4% — within expected range; calibration sound.
    5 critical findings. Cross-unit pattern: 4 of 5 critical findings cite the
    same consultant report instead of the underlying EIOPA opinion.
    Recommendation: repository-wide rule — never cite consultant summaries for
    regulatory facts when EIOPA primary is available.
    Remediation plan: 4 follow-on Research Documentation sessions to apply
    re-attributions and removals.
    REPORT.md committed.

Total: 8 sessions over ~2 working weeks at 1 session/day.
```
