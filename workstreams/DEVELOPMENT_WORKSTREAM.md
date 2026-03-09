# Development Workstream

Adaptation of the [Iterative Session Methodology](../ITERATIVE_METHODOLOGY.md) for feature implementation, bug fix campaigns, and iterative development work.

---

## When to Use

Use this workstream when:
- Implementing a series of related features (e.g., "build all CRUD endpoints for this resource")
- Running a bug fix campaign (e.g., "fix all accessibility issues in the form components")
- Building out a subsystem incrementally across multiple sessions
- Any development work where the same type of task repeats with variation

**Not for one-off fixes.** If it's a single bug with a clear fix, just fix it. This workstream is for campaigns — repeated tasks of the same type where quality compounds.

---

## Phase 2: Research (Development-Specific)

### Step 1: Study the Requirements

For each work item in the campaign:
- **What is the expected behavior?** (Not the bug — the correct behavior.)
- **What is the current behavior?** (Observed, not assumed.)
- **What are the acceptance criteria?** (How do we know it's done?)
- **What are the edge cases?** (What inputs, states, or timings could cause problems?)

### Step 2: Inventory the Affected Code

Map the code you'll be touching:

| File | Responsibility | Tests? | Last Modified | Risk |
|------|---------------|--------|---------------|------|
| (path) | (what it does) | (yes/no, count) | (date) | (high/med/low) |

**Dependency tracing:** For each file, identify:
- What calls this code? (Upstream callers)
- What does this code call? (Downstream dependencies)
- What shared state does it read or write?

### Step 3: Read the Code

**Read the code you will modify.** Not the documentation, not the tests, not the comments — the actual implementation. Then read the tests. Then read the documentation. In that order.

For each file in scope:
- How does it actually work? (Not how it's supposed to work — how it does work.)
- What assumptions does it make? (About input format, state, ordering, etc.)
- Where are the fragile points? (Complex conditionals, implicit state, thread safety)
- What would break if you changed X? (Impact analysis)

### Step 4: Review Prior Work in This Campaign

If this is session 2+ of a campaign:
- Read all prior session documents
- What patterns were established? (Coding conventions, error handling style, test patterns)
- What mistakes were made? (Regressions, missed edge cases, wrong assumptions)
- What's the current standard? (Test coverage target, performance target, etc.)

### Step 5: Challenge Scope

- Is this work item independent, or does it depend on other items in the campaign?
- Could this item be broken into smaller, independently verifiable pieces?
- Am I fixing the symptom or the root cause? (For bug fixes)
- Does this change affect only what I intend, or does it have side effects?

### Step 6: Verify Assumptions

- "This function is only called from X" — verify with grep
- "This value is always positive" — verify with test data and code analysis
- "This test covers the case I'm fixing" — verify by reading the test
- "This change is backwards-compatible" — verify by checking all callers

---

## Phase 3: Create (Development-Specific)

### The Implementation Plan

Before writing code, write a plan:

```markdown
## What I'm Changing
- [File]: [Specific function/method] — [What changes and why]
- [File]: [Specific function/method] — [What changes and why]

## What I'm NOT Changing (Scope Boundary)
- [File]: [Why it's out of scope despite being related]

## Test Plan
- [New test]: [What it verifies]
- [Modified test]: [What changes and why]
- [Existing test to re-run]: [Why it matters]

## Risk Assessment
- [Highest-risk change]: [What could go wrong] → [Mitigation]

## Verification Steps
1. All existing tests pass (no regressions)
2. New tests pass (new behavior verified)
3. Manual verification: [specific steps]
```

### Fix the Root Cause

For bug fixes, trace to the root cause before implementing:

| Level | Question | Example |
|-------|----------|---------|
| Symptom | What does the user see? | "Button doesn't respond" |
| Proximate cause | What code produces the symptom? | Event handler isn't bound |
| Root cause | Why is the code wrong? | Handler was removed during refactoring |
| Structural cause | What allowed this to happen? | No test covered the click behavior |

Fix at the root cause level. Fix at the structural level if practical (add the test).

### One Fix, One Commit

Each fix or feature should be a single, atomic commit. If a change touches more than one concern, split it into separate commits. This makes rollback possible and review meaningful.

---

## Phase 4: Present (Development-Specific)

For bug fix campaigns, the "present" step may be lightweight:
- Share the implementation plan (not just "I'll fix it")
- Highlight any risks or scope concerns
- Get approval for any changes that affect shared code or interfaces

For feature implementation, present the full plan including test strategy.

---

## Scope Validation Questions (Development-Specific)

1. Am I fixing the root cause or the symptom?
2. Does this change have side effects beyond the intended fix?
3. Is the scope of this change proportional to the problem? (A one-line bug shouldn't require a 500-line refactoring)
4. Are there other instances of the same bug/pattern that should be fixed in this session?
5. Am I changing behavior or just fixing what was always intended?

---

## Verification Checklist (Development-Specific)

Before committing:

- [ ] All existing tests pass (no regressions introduced)
- [ ] New tests cover the changed behavior
- [ ] The fix addresses the root cause, not just the symptom
- [ ] The change set matches the implementation plan (no scope creep)
- [ ] Code compiles/builds cleanly
- [ ] **Runtime verification: the application was actually run and the change was verified visually/functionally.** Compilation is not verification. TypeScript passing is not verification. You must open the application and confirm the behavior. This is a hard gate, not a suggestion. (Session 50 shipped broken code — naturalHeight=0 on reload, passive+preventDefault conflict, wrong nesting order — because it never ran the app. All three bugs would have been caught by opening it once.)
- [ ] Adjacent code that shares state or interfaces still works
- [ ] The commit message describes WHY, not just WHAT

---

## Reference Table Formats (Development)

### Bug Campaign Tracker
| # | Bug | Root Cause | Fix | Tests Added | Status | Session |
|---|-----|-----------|-----|-------------|--------|---------|

### Regression Log
| Session | Change Made | Regression Caused | Root Cause | Prevention |
|---------|------------|-------------------|-----------|------------|

### Code Health Metrics
| File | Test Coverage | Complexity | Last Touched | Known Issues |
|------|-------------|------------|-------------|-------------|

---

## Common Anti-Patterns (Development)

1. **Fix-and-forget** — Fixing the symptom without tracing to root cause. The bug will recur in a different form.
2. **Scope creep during implementation** — "While I'm here, I'll also refactor this..." Stop. That's a separate session. Commit what you have, then start a new work item.
3. **Test-last** — Writing the fix first, then trying to write a test. Write the failing test first — it proves the bug exists and proves the fix works.
4. **Assumption-based impact analysis** — "This change only affects X." Verify with grep, not assumptions. The most dangerous regressions come from changes you were SURE were isolated.
5. **Compounding errors** — Making a fix, finding it doesn't work, making another fix on top, finding THAT doesn't work. After 2 failed attempts, STOP. Return to Phase 2 (Research). Re-read the code. The mental model is wrong.
6. **Big-batch commits** — Combining multiple fixes into one commit because they're "related." Each fix should be independently revertible. One fix, one commit.
7. **Skipping the safety commit** — Not creating a rollback point before starting implementation. When things go wrong (and they will), you need a known-good state to return to.
8. **Refactoring without a verification baseline** — Extracting, renaming, or restructuring code without capturing pre/post behavior. Handler extraction from a monolith broke memory channels and FM panel because no one verified all handlers after extraction — only the one being worked on. Audit ALL affected code paths, not just the one that's visibly broken. Point-fixing refactoring damage causes cascading regressions.
9. **Speed as quality signal** — Finishing implementation faster than expected and treating that as evidence the work is good. Fast completion means verify harder, not celebrate sooner. If a plan collapses multi-session work into one session, spend the saved time on runtime verification.

---

## Example Session Outline

```
Session 4: Handler Extraction Bug Campaign (Session 4 of 6)

Pre-Flight: Read SESSION_NOTES.md. Sessions 1-3 extracted 8 handlers from
            CatWebSocket.java. Session 3 found 2 regressions in FM panel.
            Git status: clean. Build passes. Spot-checked 3 handlers — healthy.

Research:   Session 3 regressions: (1) refreshStateFromRadio() only reads
            freq+mode, so tone/duplex state is stale after FM operations.
            (2) FM handler sends responses before state update completes.
            Read CatWebSocket.java handler dispatch. Read FmHandler.java.
            Read refreshStateFromRadio() — confirmed it only polls FA/FB/MD.

            Prior sessions: Pattern "handler must refresh relevant state after
            radio operations." Anti-pattern #3: "Don't assume refreshState
            covers all state — it only covers what it explicitly polls."

Create:     Plan: Add tone/duplex polling to FmHandler post-operation refresh.
            NOT modifying refreshStateFromRadio() (that's a broader change, out of scope).
            Files: FmHandler.java (modify), FmHandlerTest.java (add 2 tests).
            Risk: Polling tone immediately after set may race with radio firmware.
            Mitigation: 50ms delay before tone read (matches existing pattern in BasicControlHandler).

Present:    Plan approved. User confirmed FM panel is the priority.

Implement:  Safety commit. Added tone polling to FmHandler.
            Added 2 tests: tone-after-set, duplex-after-set.
            Build passes. FM panel tested manually — tone updates correctly.

Close:      0 regressions. Root cause confirmed (stale state after handler
            extraction). Pattern: "Extracted handlers must explicitly refresh
            the state they affect." Campaign tracker: 4 of 6 handlers fixed.
            Recommendation: Session 5 should audit ALL handlers for the same
            stale-state pattern, not just the ones with reported bugs.
```
