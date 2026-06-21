# [Domain Name] Workstream

Adaptation of the [Iterative Session Methodology](../ITERATIVE_METHODOLOGY.md) for [describe the type of work].

---

## When to Use

Use this workstream when:
- [Condition 1]
- [Condition 2]
- [Condition 3]

---

## Recommended Skills *(optional — keep only if ≥2 skills apply)*

Follows the citation-shape convention ([`RECOMMENDED_SKILLS.md`](../../../RECOMMENDED_SKILLS.md) §How this index is used). If this workstream recommends **one** skill, cite it inline at the point of recommendation and **delete this section**. If **two or more** skills apply, keep it: a short intro naming what the methodology owns vs. what each skill owns, then a table.

| [Purpose] | Recommended skill |
|---|---|
| [What you are trying to do] | `/[skill]` |

When a recommended skill is unavailable, the discipline in this document is the operative guidance — the skill is a sharper instrument, not a hard dependency.

---

## Recommended Reasoning Tier *(optional — set this domain's default)*

One line keying this workstream's default reasoning tier to its blast radius × irreversibility × compounding cost, citing `ITERATIVE_METHODOLOGY.md` §Matching Reasoning Effort to Stakes. Heavy / irreversible / compounding → deepest mode; cheap / reversible / mechanical → lighter. Delete if the domain's tier is unremarkable.

---

## Phase 2: Research ([Domain]-Specific)

### Step 1: Study the [Requirements/Domain/Problem]

[What to read, extract, and understand before anything else.]

Key questions:
- [Domain-specific question 1]
- [Domain-specific question 2]
- [Domain-specific question 3]

### Step 2: Inventory [Components/Systems/Materials]

Map what you're working with:

| Item | [Column 2] | [Column 3] | [Column 4] |
|------|-----------|-----------|-----------|

### Step 3: Read [Implementations/Contracts/Specs]

[What to read beyond the surface level. What does "reading the implementation" mean in this domain?]

### Step 4: Review Prior Work

[How to find and use previous session outputs in this domain.]

### Step 5: Challenge Scope

[Domain-specific scope validation questions.]

### Step 6: Validate [Domain Fit / Technology Choice / Tool Selection]

[Domain-specific validation of whether you're using the right approach.]

### Step 7: Verify Assumptions

[What critical assumptions exist in this domain, and how to verify them.]

---

## Phase 3: Create ([Domain]-Specific)

### The Deliverable

[What does the Phase 3 output look like for this domain? Document structure, diagram format, plan template, etc.]

### Key Design Decisions

[What are the most important decisions in this domain? What makes a good design vs. a bad one?]

---

## Scope Validation Questions ([Domain]-Specific)

1. [Question]
2. [Question]
3. [Question]
4. [Question]
5. [Question]

---

## Verification Checklist ([Domain]-Specific)

Before presenting:

- [ ] [Check 1]
- [ ] [Check 2]
- [ ] [Check 3]
- [ ] [Check 4]
- [ ] [Check 5]

---

## Reference Table Formats ([Domain])

### [Table Name]
| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|

---

## Common Anti-Patterns ([Domain])

1. **[Name]** — [Description of the mistake and why it happens.]
2. **[Name]** — [Description.]
3. **[Name]** — [Description.]

---

## Adaptation Notes for Documentation Projects

When adapting this template for a documentation project (Quarto, LaTeX, Sphinx, etc.), make the following substitutions:

| Software Concept | Documentation Equivalent |
|---|---|
| Build passes | Document renders without errors |
| Tests pass | Citations resolve, cross-references resolve, figures generate |
| Code review | Peer review of document sections |
| Component inventory | Section inventory (headings, figures, tables, cross-references) |
| Regression test | Re-render and verify all existing cross-references still resolve |
| Deploy | Render final output (PDF, HTML) |
| Design system | Style guide, citation convention, terminology conventions |
| Prototype | Rendered draft |

Additional documentation-specific anti-patterns:
- **Edit from memory.** Modifying a section based on a stale mental model rather than re-reading it. Particularly dangerous after context compaction.
- **Greenfield framing.** Writing as if the organization has no existing capabilities when it does. Destroys credibility with domain-expert readers.
- **Overwriting user edits.** Regenerating figures, tables, or sections the user manually refined.
- **Citation drift.** Referencing citation keys that do not exist in the bibliography file. Render after every edit to catch immediately.
- **Redundant restatement.** Repeating the same argument in multiple sections during incremental drafting. Conduct a structural review after major additions.

---

## Example Session Outline

```
Session N: [Work Item Name]

Pre-Flight: [What was checked]
Research:   [What was examined]
Create:     [What was designed]
Present:    [Approval result]
Implement:  [What was changed]
Close:      [Metrics and learnings]
```
