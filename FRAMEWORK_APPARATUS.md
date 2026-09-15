# Framework Apparatus

The operative apparatus of the [Iterative Session Methodology](ITERATIVE_METHODOLOGY.md) — the tables
you fill in, the tests you run, and the scales you score against. This file is **reference, read on
demand**: you open it while writing a session document, validating a scope, or scoring a claim, not to
understand the framework. The theory these sections implement — the 9 principles, the 6 phases, the 12
quality gates — stays in [`ITERATIVE_METHODOLOGY.md`](ITERATIVE_METHODOLOGY.md).

The six sections below were moved here **verbatim** from that file, which had grown past the size a
single read can hold. Nothing was rewritten, condensed, or dropped in the move; the only edit was to
turn one in-file cross-reference into a link back to `ITERATIVE_METHODOLOGY.md`.

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
