# Audit Workstream

Adaptation of the [Iterative Session Methodology](../ITERATIVE_METHODOLOGY.md) for code audits, system reviews, security assessments, and quality evaluations.

---

## When to Use

Use this workstream when:
- Auditing a codebase for a specific class of issue (security, performance, correctness, style)
- Reviewing a system for architectural health
- Evaluating a series of components against a standard
- Conducting a quality gate review before a release or milestone
- Assessing technical debt across a subsystem

---

## Phase 2: Research (Audit-Specific)

### Step 1: Define the Audit Criteria

Before examining anything, define what you're looking for:

| Dimension | Question | Pass Criteria | Fail Criteria |
|-----------|----------|---------------|---------------|
| (e.g., Security) | (e.g., Does input validation exist?) | (e.g., All user inputs sanitized) | (e.g., Raw user input in SQL/HTML) |

**Be specific.** "Is the code good?" is not an audit criterion. "Does every API endpoint validate input types before processing?" is.

### Step 2: Inventory the Audit Scope

List everything that will be examined:

| Item | Type | Size | Priority | Last Audited |
|------|------|------|----------|-------------|
| (file/module/endpoint) | (code/config/schema) | (lines/complexity) | (critical/normal/low) | (date or never) |

**Coverage tracking:** Mark each item as audited/not-audited as you progress. At the end, the coverage should be explicit — "Audited 47 of 52 endpoints; 5 skipped because [reason]."

### Step 3: Read the Implementation

For each item in scope:
- Read the actual code (not the documentation)
- Evaluate against each audit dimension
- Record findings with specific file paths and line numbers

### Step 4: Review Prior Audits

If this is a recurring audit (e.g., pre-release quality gate):
- Read all prior audit reports in this series
- What issues were found last time? Are they fixed?
- What issues recur? (These indicate structural problems, not one-off bugs.)
- What was the finding trend? (Improving, stable, degrading?)

### Step 5: Challenge Scope

- Am I auditing the right things? (Are the highest-risk components in scope?)
- Am I auditing at the right level? (Code-level vs. architecture-level vs. process-level?)
- Is the audit criteria complete, or am I missing a dimension?

---

## Phase 3: Create (Audit-Specific)

### The Audit Report

Structure:

```markdown
## Audit Summary
- Scope: [what was examined]
- Criteria: [what was evaluated]
- Coverage: [X of Y items examined]
- Finding count: [N critical, M moderate, P minor]

## Findings

### Finding #1: [Title]
- **Severity:** Critical / Moderate / Minor
- **Location:** [file:line]
- **Description:** [What was found]
- **Evidence:** [Code snippet or observation]
- **Impact:** [What could go wrong]
- **Recommendation:** [How to fix]

### Finding #2: ...

## Items Audited
| Item | Status | Findings |
|------|--------|----------|
| (file) | Pass / Fail / N/A | #1, #3 |

## Structural Observations
- [Patterns that appear across multiple findings — these indicate systemic issues]
- [Areas that are well-designed and should be used as reference implementations]

## Comparison with Prior Audits
| Metric | Prior | Current | Trend |
|--------|-------|---------|-------|
| Total findings | | | |
| Critical findings | | | |
| Recurring issues | | | |
| Coverage | | | |

## Recommendations
1. [Highest-priority fix]
2. [Structural improvement to prevent recurrence]
3. [Process change to catch issues earlier]
```

### Multi-Dimension Audit Grid

When auditing across multiple dimensions simultaneously:

| Item | Dimension 1 | Dimension 2 | Dimension 3 | Overall |
|------|------------|------------|------------|---------|
| (component) | Pass/Fail | Pass/Fail | Pass/Fail | Health score |

The grid provides a heat map of where problems cluster — by item (one bad component) or by dimension (one systemic weakness).

---

## Scope Validation Questions (Audit-Specific)

1. Am I auditing the highest-risk items, or the easiest-to-audit items?
2. Is my criteria comprehensive for the type of audit? (Security audits that only check for SQL injection miss XSS, CSRF, etc.)
3. Am I auditing at a consistent depth, or spending 80% of time on the first item?
4. Does the scope include items that changed recently? (Recent changes are highest-risk.)
5. Am I auditing the actual deployed code, or a different version?

---

## Verification Checklist (Audit-Specific)

Before presenting the audit report:

- [ ] Every item in scope is marked as audited or explicitly excluded with reason
- [ ] Every finding has a specific location (file, line number, endpoint)
- [ ] Every finding has evidence (code snippet, log output, reproduction steps)
- [ ] Severity ratings are calibrated consistently (same severity for same risk level)
- [ ] Structural observations identify patterns, not just individual issues
- [ ] Comparison with prior audits is included (if prior audits exist)
- [ ] Recommendations are actionable (not "improve code quality" but "add input validation to endpoints X, Y, Z")

---

## Reference Table Formats (Audit)

### Finding Tracker (Across Sessions)
| # | Finding | Severity | Location | Session Found | Session Fixed | Recurred? |
|---|---------|----------|----------|--------------|--------------|-----------|

### Audit Coverage Map
| Module/Area | Session 1 | Session 2 | Session 3 | Full Coverage? |
|-------------|----------|----------|----------|----------------|

### Recurring Issue Register
| Issue Pattern | First Found | Times Recurred | Root Cause | Structural Fix |
|--------------|------------|----------------|-----------|----------------|

---

## Common Anti-Patterns (Audit)

1. **Surface-level scanning** — Looking at code structure without reading the logic. A well-formatted function can still have a critical security flaw.
2. **First-item bias** — Spending disproportionate time on the first item audited, then rushing through the rest. Budget time per item and track it.
3. **Severity inflation** — Marking everything as "critical" to appear thorough. Calibrate severity honestly. If everything is critical, nothing is.
4. **Severity deflation** — Marking real problems as "minor" to make the report look better. The numbers should survive hostile review.
5. **Missing the forest** — Reporting 20 individual findings without identifying the structural pattern that explains them all. If 15 of 20 findings are the same category, the recommendation is "fix the structural cause," not "fix these 20 instances."
6. **Auditing the docs** — Reviewing documentation or comments instead of code. Documentation describes intent; code describes reality. Audit reality.
7. **Coverage gaps** — Reporting findings for the items you examined while leaving high-risk items unexamined. Explicit coverage tracking prevents this.
8. **Only auditing code** — Plans and design documents can also be audited. Sessions 51-52 audited an implementation plan and found the plan itself had errors (wrong nesting order, passive+preventDefault conflict). Catching errors in the plan is cheaper than catching them after implementation. Consider: "Is the plan correct?" as an audit criterion, not just "Is the code correct?"

---

## The 7-Dimension Audit Framework

For comprehensive component/artifact audits, evaluate across all seven dimensions. This framework was proven across 10 sessions with monotonically increasing defect detection (0 → 2 → 4 → 8 → 11 → 11 → 10 → 12 → 14 → 15).

| Dimension | What It Checks | Example Finding |
|-----------|---------------|-----------------|
| 1. **Structural validity** | Are all parts assigned correctly? Do references resolve? | "Component X references zone 'center' which doesn't exist in this layout" |
| 2. **Essential completeness** | Is anything critical missing? | "Mobile view has no way to trigger the primary action" |
| 3. **Use-case fit** | Does every part serve this user's actual needs? | "Component Z is a digital-mode tool; this is a voice-mode interface" |
| 4. **Emphasis/placement** | Are parts placed according to their importance? | "The star component is in a sidebar instead of the primary zone" |
| 5. **Balance/proportionality** | Is the quantitative distribution reasonable? | "Left column is 800px, right column is 200px — 600px gap" |
| 6. **Design coherence** | Is there a unifying thematic concept? | "No organizing principle — components seem randomly assigned" |
| 7. **Redundancy** | Are there duplicate or overlapping parts? | "Two components both provide the same action with different UI" |

Apply all 7 dimensions to each item under audit. The later dimensions (6, 7) were added in later sessions after they were found to catch defects the earlier dimensions missed.

---

## Example Session Outline

```
Session 2: Frontend Component Audit (Accessibility)

Pre-Flight: Read Session 1 audit report (found 14 findings, 3 critical).
            Verified 3 critical findings from Session 1 are now fixed.
            Build passes. Spot-checked 2 components — healthy.

Research:   Audit criteria: WCAG 2.1 AA compliance.
            Scope: 36 Vue components in src/components/.
            Prioritized: 12 interactive components first (forms, buttons, modals),
            then 24 display components.
            Session 1 patterns: missing aria-labels (systemic), color contrast
            issues in dark theme (3 instances), no keyboard navigation in modals.

Create:     Audit report with 23 findings:
            - 2 critical (modal trap — no keyboard escape, form with no labels)
            - 8 moderate (color contrast, missing aria attributes)
            - 13 minor (decorative images without alt="", redundant roles)
            Structural observation: All modals share the same base component
            (BaseModal.vue) — fixing keyboard handling THERE fixes it everywhere.
            Coverage: 36 of 36 components (100%).

Present:    Report presented. Stakeholder prioritized: fix BaseModal (cascading fix),
            then form labels, then color contrast.

Close:      23 findings (vs 14 in Session 1 — broader scope, not worse code).
            Session 1 critical findings all verified fixed.
            Recurring issue: aria-labels — structural fix recommended:
            add lint rule to catch missing labels at build time.
            Recommendation: Session 3 should audit the 8 page-level views
            for navigation and focus management.
```
