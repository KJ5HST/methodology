# Design Workstream

Adaptation of the [Iterative Session Methodology](../ITERATIVE_METHODOLOGY.md) for UI/UX design, visual design, and layout work.

---

## When to Use

Use this workstream when designing:
- User interface layouts (pages, views, dashboards)
- Component arrangements and information architecture
- Visual hierarchy and interaction flow
- Profile/theme/configuration variants of the same interface

---

## Phase 2: Research (Design-Specific)

### Step 1: Study the User

Read requirements, personas, use case documents. Extract:
- **Who is the user?** Experience level, goals, frustrations.
- **What is their workflow?** Step-by-step from session start to session end.
- **What do they look at constantly?** (Primary information needs)
- **What do they DO most?** (Primary actions)
- **What's the tempo?** Fast (contest exchanges) vs slow (casual browsing)?
- **What do they NOT need?** (Exclusion is as important as inclusion.)

### Step 2: Inventory Components

Build a reference table of all available components:

| Component | Category | Size (Height) | Width Sensitivity | Has Variants? | Notes |
|-----------|----------|---------------|-------------------|---------------|-------|

**Size classes** for rough estimation:
- **XS** (24-40px): Toolbars, toggle bars, single-row controls
- **S** (60-120px): Meters, badges, compact indicators
- **M** (120-200px): Moderate control groups, forms, compact panels
- **L** (200-400px): Lists, tables, complex panels
- **XL** (400px+): Full displays, maps, canvases

### Step 3: Read Component Implementations

**The inventory tells you what a component IS. The implementation tells you how it BEHAVES.**

For each candidate component, read its source and document:

| Component | Width Sensitivity | Actual Height (by variant) | Responsive Behavior | Interactive Elements |
|-----------|-------------------|---------------------------|---------------------|---------------------|

**What to look for:**
- Minimum comfortable width (sliders, grids, and button rows have minimum widths)
- Actual height by variant (often differs significantly from size class estimates)
- Does it wrap, scroll, collapse, or truncate at narrow widths?
- Does it have distinct variants (full/compact/minimal)?
- Does it have special modes (focus mode, collapsed mode)?

### Step 4: Review Prior Designs

Read ALL previous design documents in this series. For each:
- What patterns were discovered?
- What mistakes were made?
- What observations apply to the current design?

### Step 5: Challenge Scope

Apply the Splitting Test:
- Does this design encompass multiple user modes?
- Do those modes have different primary components, different tempos, different user postures?
- If so, should they be separate designs?

### Step 6: Validate Domain Fit

For each component included:
- Does this user community have its own tool ecosystem?
- Is this component FROM that ecosystem, or a generic substitute?
- Four outcomes: rejection, confirmation, identity, complementary.

### Step 7: Verify Component Claims

For any component whose variant support or responsive behavior matters to the design:
- Read the component source directly
- Confirm variant prop exists AND is used in conditional rendering
- Two-step verification: (1) Does it declare the capability? (2) Does it implement the capability?

---

## Phase 3: Create (Design-Specific)

### The Star Component

Identify the ONE component that defines this design's identity. It goes in the most prominent position.

**The star component is the single most important design decision.** It differentiates this design from every other variant. Each design should answer: "What component makes this design THIS design and not another?"

### Layout Design

For multi-column layouts, design each zone:
- **What goes where** — assign components to zones based on workflow, not convenience
- **Column balance** — measure total height per column; columns in the same row should be within ~150px of each other
- **Width sensitivity** — components needing 450px+ cannot go in narrow sidebars
- **Collapsed-by-default** — complex components can be present but collapsed (~40px header) until expanded on demand

### Thematic Grouping

Group components by user cognitive model, not by technical category:

| Pattern | LEFT | CENTER | RIGHT | When to Use |
|---------|------|--------|-------|-------------|
| Monitor / Act / Navigate | Signal monitoring | Primary actions | Navigation tools | General-purpose interfaces |
| RX/TX Split | Receive chain | Action zone | Transmit chain | Interfaces with clear input/output duality |
| Hunt / Exchange | Finding targets | Shared logging | Working targets | Search-and-engage workflows |
| Cognitive Mode Split | Technical monitoring | Operational navigation | Information management | Multi-tasking interfaces |

### View Differentiation

If the design has multiple views (e.g., compact/expanded/mobile):
- Each view should have a different star component or different variant of the star
- The mobile/focus view should substitute or add one profile-specific component
- **Both-views-operational**: If the user has two distinct operational modes, map them to different views rather than different densities of the same view

### Exclusion Documentation

For every component NOT included, document why:
- "Not needed for this user's workflow" (with specific reasoning)
- "Domain-inappropriate" (with domain-ecosystem validation result)
- "Filler — the user would miss nothing if it weren't here"

---

## Scope Validation Questions (Design-Specific)

Before designing, answer:

1. Does this design serve one user mode or multiple?
2. For each mode: what is the primary component, the operating tempo, and the user posture?
3. Do any modes have DIFFERENT primary components, DIFFERENT tempos, or DIFFERENT postures? → Split.
4. Is this a personal-operation design (user manages their own work) or group-management (user manages others)?
5. Does this user community have specialized tools? Are our components from that ecosystem?

---

## Verification Checklist (Design-Specific)

Before presenting the design:

- [ ] Every included component has a documented rationale (WHY it's here)
- [ ] Every excluded component has a documented rationale (WHY it's not)
- [ ] Column heights are calculated from actual component measurements, not estimates
- [ ] Width-sensitive components are not placed in zones narrower than their minimum
- [ ] The star component is identified and prominently placed
- [ ] Mobile/focus view has at least one component that differentiates it from other designs
- [ ] Component variant claims are verified against source code (not trusted from descriptions)
- [ ] The design was built from the user's workflow, not from the existing component arrangement

---

## Common Anti-Patterns (Design)

1. **Rubber-stamping** — Accepting the existing layout and only rearranging zones. Start from the user's needs, not from the current file.
2. **Name-based inclusion** — Including a component because its name sounds relevant without reading its implementation.
3. **Filler** — Including components because space is available, not because the user needs them. Test: "What would the user miss if this weren't here?" If the answer is "nothing," remove it.
4. **Center dominance** — Stacking too many components in the widest column, creating a tower effect while sidebars are half-empty.
5. **Generic Focus** — Using the same mobile/minimal view for every design. Each design's mobile view should reflect its identity.
6. **Pattern force-fitting** — Applying a pattern from a previous design that worked in a different context. Patterns are tools, not mandates.
7. **Description-level verification** — Trusting component descriptions or agent summaries about variant support without reading the source.

---

## Example Session Outline

```
Session 6: Emcomm Profile Design

Pre-Flight: Read SAFEGUARDS.md, SESSION_NOTES.md, git status. Workspace clean.
            Existing profile builds. Spot-checked default and CW profiles — healthy.

Research:   Read EMERGENCY_COMMUNICATIONS.md use case. Extracted operator persona
            (ARES field communicator). Read ALL 22 plugin directories via Explore
            agent. Built reference table with actual heights and width sensitivity.
            Read 5 prior design docs. Challenged scope: NCS vs Field Operator —
            same primary panel, no split needed.

Create:     Star panel: memories (preprogrammed repeater channels).
            Thematic split: Monitor & Configure / Navigate & Log / Document & Awareness.
            Column balance: LEFT 372 / CENTER 291 / RIGHT 336 (36px L-R difference).
            Documented 7 user testing questions for unfamiliar domain areas.

Present:    Design approved. User noted domain knowledge limits, deferred questions
            to future user testing.

Implement:  Safety commit. Modified 2 files (profile JSON + manifest).
            Built and verified. Spot-checked adjacent profiles.

Close:      11 bugs found in existing profile (tied record).
            0 user corrections. 3 new patterns discovered.
            Recommendations: restore ALL-plugins research standard for future sessions.
```
