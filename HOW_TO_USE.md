# How to Use the Iterative Session Methodology

A practical guide for applying the methodology to real work. Includes quick start, three detailed examples, lifecycle guidance (greenfield through refactoring), and instructions for creating custom workstreams.

---

## Table of Contents

1. [Quick Start (5 Minutes)](#quick-start)
2. [Core Concepts](#core-concepts)
3. [Example 1: Greenfield API Design](#example-1-greenfield-api-design)
4. [Example 2: Bug Fix Campaign (Maintenance)](#example-2-bug-fix-campaign)
5. [Example 3: System Refactoring](#example-3-system-refactoring)
6. [Lifecycle Guide: Greenfield to Maintenance to Refactoring](#lifecycle-guide)
7. [Running Your First Session](#running-your-first-session)
8. [Creating a Custom Workstream](#creating-a-custom-workstream)
9. [Using This with AI Agents](#using-this-with-ai-agents)
10. [Scaling: Solo to Team](#scaling)
11. [Troubleshooting](#troubleshooting)

---

## Quick Start

**To use this methodology, you need three things:**

1. **The master framework:** `ITERATIVE_METHODOLOGY.md` — defines the 6 phases, 12 gates, and self-improvement loop
2. **A workstream template:** Pick the one that matches your domain (design, architecture, development, audit) or create your own from `TEMPLATE_WORKSTREAM.md`
3. **A place to store session outputs:** Create a directory for your session documents (e.g., `sessions/{workstream-name}/`)

**Every session follows the same loop:**

```
Pre-Flight → Research → Create → Present → Implement → Verify & Close
```

That's it. The power comes not from any individual session but from the self-improvement loop that makes each session better than the last.

---

## Core Concepts

### Sessions

A **session** is one pass through the 6-phase loop, producing one deliverable. Sessions are the atomic unit of work in this methodology.

Examples of a session:
- Design one API endpoint
- Fix one category of bugs across a subsystem
- Audit one module for security issues
- Design one UI profile layout

Sessions are typically scoped to complete in 1-4 hours. If a work item would take longer, split it into multiple sessions.

### Workstreams

A **workstream** is a series of sessions doing the same TYPE of work. The workstream template adapts the universal phases to a specific domain.

Examples of workstreams:
- "API Design" — 8 sessions, each designing one endpoint group
- "Accessibility Bug Campaign" — 5 sessions, each fixing one component category
- "Profile UI Design" — 11 sessions, each designing one operator profile

The workstream is where knowledge compounds. Session 1 invents patterns. Session 5 applies them automatically. Session 10 validates them.

### The Self-Improvement Loop

After every session, you write:
- **What Went Right** (becomes a reusable pattern)
- **What Went Wrong** (becomes a numbered anti-pattern)
- **Recommendations for next session** (tracked for compliance)

This loop is the methodology's core innovation. It means your process improves even when your skills stay constant.

### Quality Gates

Gates are structural controls that prevent you from moving forward with bad work:
- You cannot create without completing research
- You cannot implement without stakeholder approval
- You cannot close without verifying adjacent work

Gates feel slow when the work is easy. They save hours when the work is hard.

---

## Example 1: Greenfield API Design

**Scenario:** You're building a REST API for a task management system. It has 6 resource types (projects, tasks, users, comments, labels, attachments). You'll design and implement each resource's endpoints as a separate session.

### Session 1: Projects API

#### Phase 1: Pre-Flight
```
- Read project requirements doc
- No prior sessions (greenfield — this is Session 1)
- Database schema exists but has no endpoints yet
- Adjacent systems: auth service (healthy), notification service (healthy)
```

#### Phase 2: Research
```
Study requirements:
  - Projects have: name, description, owner, members, status, created/updated dates
  - Operations: CRUD + list with filters + archive/unarchive
  - Authorization: owners can do everything; members can read and update; non-members can't access

Inventory existing code:
  - Database schema: projects table, project_members junction table
  - Auth middleware: provides req.user with id and roles
  - Existing patterns: none (first endpoint group)

Read implementations:
  - Auth middleware actually only provides user ID, not roles (docs were wrong)
  - Database schema has a soft-delete column (archived_at) — archive != delete

Challenge scope:
  - Should project membership endpoints be here or separate? → Same resource, keep together.
  - Should notifications on project changes be in scope? → No, that's a separate system.
    Document as integration point.
```

#### Phase 3: Create
```
Endpoint Design:

  POST   /projects              — Create project (owner = caller)
  GET    /projects              — List projects (caller is member of)
  GET    /projects/:id          — Get project details
  PATCH  /projects/:id          — Update project fields
  POST   /projects/:id/archive  — Archive project (owner only)
  POST   /projects/:id/restore  — Restore archived project (owner only)
  DELETE /projects/:id          — Hard delete (owner only, project must be archived first)

  POST   /projects/:id/members       — Add member (owner only)
  DELETE /projects/:id/members/:uid   — Remove member (owner only, can't remove self)

Authorization model:
  - Middleware checks project membership for all /projects/:id/* routes
  - Owner check is a separate middleware for destructive operations

Error contracts:
  - 400: validation errors (missing required fields, invalid formats)
  - 401: not authenticated
  - 403: authenticated but not authorized (not a member, not the owner)
  - 404: project not found OR caller is not a member (don't leak existence)
  - 409: conflict (e.g., delete non-archived project, add existing member)

Gaps:
  - No pagination design yet — needed for list endpoint. Will address in Session 2
    after seeing the pattern needed.
  - No rate limiting — document as future work.
```

#### Phase 4: Present
```
Presented to team lead. Feedback:
  - "404 for non-members is smart — prevents enumeration. Approved."
  - "Add a GET /projects/:id/members endpoint for listing members."
  → Added to design. No other changes needed.
```

#### Phase 5: Implement
```
Safety commit: "chore: pre-projects-api snapshot"

Files created:
  - routes/projects.js (endpoint handlers)
  - middleware/projectAuth.js (membership + owner checks)
  - tests/projects.test.js (24 test cases)

Files NOT modified:
  - routes/index.js (just mounts the new route file — trivial)
  - middleware/auth.js (existing, works as-is)
```

#### Phase 6: Verify & Close
```
Verification:
  - All 24 tests pass
  - Manual testing: create, read, update, archive, restore, delete, members — all work
  - Auth service still healthy (adjacent check)
  - Notification service still healthy (adjacent check)

What Went Right:
  1. Reading the auth middleware revealed it only provides user ID, not roles.
     Design adjusted before implementation. Would have been a runtime bug otherwise.
     → Pattern: "Read middleware implementations, not just their docs."
  2. The archive-before-delete requirement was discovered from the database schema
     (soft-delete column), not from the requirements doc (which just says "delete").
     → Pattern: "Schema reveals business rules that requirements docs miss."

What Went Wrong:
  1. Initially forgot the list-members endpoint. Caught at Present phase.
     → Anti-pattern #1: "CRUD isn't complete without list operations on sub-resources."
  2. No pagination design. Deferred to Session 2, but this means Session 2 will have
     to retrofit pagination onto the list endpoint.
     → Recommendation for Session 2: Design pagination first, then apply to Tasks list.

Performance Metrics:
  | Metric                 | Session 1 |
  |------------------------|-----------|
  | Iterations to approval | 1 (minor addition) |
  | Stakeholder corrections| 1 (missing endpoint) |
  | Research depth         | Schema + middleware + requirements |
  | Patterns discovered    | 2 |
  | Anti-patterns added    | 1 |
```

### Session 2: Tasks API

Session 2 would start by reading Session 1's output, applying its patterns ("read middleware implementations," "schema reveals business rules"), avoiding its anti-pattern ("include list operations on sub-resources"), and addressing its recommendation ("design pagination first").

**This is the self-improvement loop in action.** Session 2 starts with Session 1's lessons already internalized.

### By Session 6: Attachments API

By the sixth session, the workstream would have accumulated:
- 8-12 patterns (pagination, error handling, authorization, file upload, etc.)
- 5-8 anti-patterns (common mistakes specific to this API)
- A reference table of all endpoints designed, their authorization models, and test coverage
- A performance comparison table showing consistent single-iteration approval
- A trajectory narrative noting that Sessions 4-6 found 0 stakeholder corrections

**The API is more consistent than if all 6 resource types had been designed in one session**, because each session applied accumulated lessons from all previous sessions.

---

## Example 2: Bug Fix Campaign

**Scenario:** Your frontend app has 14 reported accessibility bugs across form components. You'll fix them in a campaign of 3 sessions, grouped by root cause.

### Session 1: Missing ARIA Labels (7 bugs)

#### Pre-Flight
```
- Read all 14 bug reports. Group by root cause:
  - 7 bugs: missing aria-label or aria-labelledby
  - 4 bugs: color contrast below 4.5:1 ratio
  - 3 bugs: keyboard navigation broken in modals
- This session: the 7 ARIA label bugs
- Workspace clean. Build passes. Spot-checked 3 non-affected components — healthy.
```

#### Research
```
Study the 7 bugs:
  - Bug #101: Login form — email input has no label
  - Bug #102: Login form — password input has no label
  - Bug #105: Search bar — search input has no label
  - Bug #108: Settings form — 4 toggle switches have no labels
  - Bug #112: Comment box — textarea has no label
  - Bug #115: Filter dropdown — select has no label
  - Bug #118: Date picker — input has no label

Inventory affected files:
  | File                | Inputs | Has Labels? | Tests? |
  |---------------------|--------|-------------|--------|
  | LoginForm.vue       | 2      | No          | 3 (no a11y tests) |
  | SearchBar.vue       | 1      | No          | 2 (no a11y tests) |
  | SettingsPanel.vue   | 4      | No          | 5 (no a11y tests) |
  | CommentBox.vue      | 1      | No          | 1 (no a11y tests) |
  | FilterBar.vue       | 1      | No          | 2 (no a11y tests) |
  | DatePicker.vue      | 1      | No          | 4 (no a11y tests) |

Read implementations:
  - LoginForm: Uses <input> directly without <label> or aria attributes
  - SearchBar: Has a visible "Search" text but it's a <span>, not a <label>
  - SettingsPanel: Uses a custom ToggleSwitch component — the component itself
    doesn't support aria-label prop passthrough. ROOT CAUSE: ToggleSwitch.vue.
  - Others: Similar pattern — <input> without associated <label>

Structural observation:
  ToggleSwitch.vue is used in 8 components across the app, not just SettingsPanel.
  Fixing ToggleSwitch fixes the structural cause for all current AND future toggles.

Challenge scope:
  The 4 toggle switch bugs are really 1 structural bug (ToggleSwitch component).
  Should I fix ToggleSwitch in this session? YES — it's the root cause.
  Should I audit all 8 usages? YES — they likely all have the same problem.
```

#### Create
```
Implementation plan:

  1. Fix ToggleSwitch.vue — add aria-label prop passthrough
     - ToggleSwitch.vue: add `label` prop, render as aria-label on <input type="checkbox">
     - This fixes Bug #108 AND prevents the same bug in 7 other components

  2. Fix 5 direct input issues:
     - LoginForm.vue: add <label for="email"> and <label for="password">
     - SearchBar.vue: change <span> to <label for="search-input">
     - CommentBox.vue: add <label for="comment">
     - FilterBar.vue: add <label for="filter-select">  (visually hidden)
     - DatePicker.vue: add aria-label="Select date" on <input>

  3. Add accessibility tests to each file:
     - Test: every <input> has an associated label (via <label for> or aria-label)

  Files NOT modified:
     - Any component not in the bug list (even if it might have similar issues —
       that's a separate audit session, not scope creep)

  Risk: ToggleSwitch prop change could break existing usages if they pass
  unexpected props. Mitigation: the new prop is optional with no default behavior change.
```

#### Present
```
Plan approved. Stakeholder: "Good catch on the ToggleSwitch structural fix.
Please also add a lint rule to catch missing labels in the future."
→ Added ESLint plugin (eslint-plugin-vuejs-accessibility) to the plan.
```

#### Verify & Close
```
All 7 bugs verified fixed. 12 new tests added.
Spot-checked 3 ToggleSwitch usages outside the bug list — all now have labels
because the component was fixed structurally.
ESLint plugin added — catches missing labels at build time.

What Went Right:
  1. Reading ToggleSwitch.vue revealed the structural root cause. Fixing one
     component fixed 8 usages across the app, not just the 4 reported bugs.
     → Pattern: "Trace bugs to shared components — one structural fix beats N instance fixes."
  2. ESLint rule prevents this class of bug from recurring.
     → Pattern: "After fixing a bug class, add a lint rule to prevent recurrence."

What Went Wrong:
  1. Initially planned to fix only the 4 reported toggle bugs, not audit all 8 usages.
     Research step caught this, but the plan should have included "audit all usages
     of the root-cause component" from the start.
     → Anti-pattern #1: "Fixing reported instances without auditing all instances
        of the structural cause."

Performance:
  | Metric                 | Session 1 |
  |------------------------|-----------|
  | Iterations to approval | 1 |
  | Stakeholder corrections| 0 (lint rule was an addition, not a correction) |
  | Bugs fixed             | 7 reported + 4 unreported (structural fix) |
  | Tests added            | 12 |
  | Structural fixes       | 1 (ToggleSwitch) + 1 (lint rule) |

Recommendation for Session 2:
  For the color contrast bugs, check if there's a shared theme/variable causing
  multiple contrast failures (same structural pattern as ToggleSwitch).
```

### Sessions 2-3

Session 2 (color contrast) would start by reading Session 1's output and applying the "trace to shared components" pattern — checking whether a shared CSS variable or theme token is causing all 4 contrast failures.

Session 3 (keyboard navigation) would have two sessions of accumulated patterns and anti-patterns, making it the most efficient session in the campaign.

**By Session 3:** The campaign has not only fixed 14 bugs but also added structural fixes (ToggleSwitch, lint rule, possibly theme variables) that prevent entire categories of bugs from recurring. The session documents serve as an accessibility audit record.

---

## Example 3: System Refactoring

**Scenario:** Your backend has a monolithic request handler (2,000 lines) that routes WebSocket commands to inline handler code. You need to extract each command group into its own handler class. This is a 6-session refactoring campaign.

### Why This Needs the Methodology

Refactoring is the highest-risk development activity. The code works before you start. If you make a mistake, it breaks. The blast radius is every feature that touches the refactored code.

The methodology protects against the specific failure mode of refactoring: **compounding regressions**. Fix A breaks B. Fix B breaks C. Fix C re-breaks A. Each fix makes the situation worse because the mental model is incomplete.

### Session 1: Extract Audio Handlers

#### Pre-Flight
```
- Read SAFEGUARDS.md (mandatory for refactoring)
- Git status: clean. Build: 247 tests pass. Workspace is known-good.
- Spot-checked WebSocket connections, API endpoints, audio streaming — all healthy.
- The monolith: CatWebSocket.java, 1,100 lines, 45 command handlers inline.
```

#### Research
```
Study the monolith:
  - 45 handlers, grouped by domain:
    audio (6), basic-control (8), receiver (5), transmitter (4), menu (7),
    digital (5), logging (4), integration (3), hamlib (3)
  - Each handler follows the same pattern: receive JSON → extract params →
    call RadioController → send response
  - Shared state: all handlers access this.radioController directly
  - Shared utilities: sendResponse(), sendError(), sendState()

Read the audio handlers specifically (this session's scope):
  - setAudioDevice, getAudioDevices, setAudioVolume, getAudioLevel,
    startAudioStream, stopAudioStream
  - They use: radioController.getAudioManager(), radioController.getStreamBridge()
  - No cross-handler dependencies (audio handlers don't call non-audio handlers)

Review prior work:
  - Session 1 (no prior sessions in this workstream)
  - But: read the project's SAFEGUARDS.md for refactoring rules

Challenge scope:
  - Extract ONLY audio handlers in this session
  - Do NOT refactor the dispatch mechanism (that's a later session)
  - Do NOT change handler behavior — pure extraction, zero behavior change
```

#### Create
```
Extraction plan:

  New file: AudioHandler.java
  - Contains 6 audio command handlers
  - Receives RadioController via constructor injection
  - Receives WebSocket session via method parameter (not stored)
  - Same method signatures as current inline handlers

  Modified file: CatWebSocket.java
  - Import AudioHandler
  - Create AudioHandler instance in constructor
  - Replace 6 inline handler blocks with delegation: audioHandler.handle(cmd, data, session)
  - No other changes. The remaining 39 handlers stay inline.

  Files NOT modified:
  - RadioController.java (no changes)
  - AudioWebSocket.java (different class, not in scope)
  - Any other handler code (this session extracts audio only)

  Test plan:
  - All existing tests pass WITHOUT modification (behavior must not change)
  - New test: AudioHandlerTest.java — unit tests for extracted handlers
  - Manual: connect WebSocket, send audio commands, verify responses match pre-extraction behavior

  Risk:
  - Highest risk: breaking the handler dispatch (wrong method routing)
  - Mitigation: dispatch change is 6 lines, each a direct delegation
  - Rollback: safety commit. If any test fails after extraction, revert entirely.
    Do NOT attempt to fix forward.

  CRITICAL RULE: If extraction causes ANY test failure, revert to the safety
  commit. Do not try to fix the extraction. A failed extraction means the
  mental model of the code is wrong — go back to Research.
```

#### Present
```
Plan approved. Stakeholder: "The rollback rule is important. Follow it strictly.
We've had refactoring sessions that caused cascading damage from fix-forward attempts."
```

#### Implement
```
Safety commit: "chore: pre-audio-handler-extraction snapshot"

Created: AudioHandler.java (6 handlers, 180 lines)
Modified: CatWebSocket.java (replaced 6 inline blocks with 6 delegation calls)
Created: AudioHandlerTest.java (12 test cases)

Build: 259 tests pass (247 existing + 12 new). Zero failures.
Manual: audio commands work identically to pre-extraction.
Adjacent: WebSocket connections healthy, other handlers unaffected.
```

#### Verify & Close
```
What Went Right:
  1. Strict "extract only, zero behavior change" scope prevented the temptation
     to improve the handlers while extracting them.
     → Pattern: "Pure extraction — change structure, not behavior. Improvements are
        a separate session after the extraction is verified stable."
  2. The rollback rule was not needed (all tests passed), but having it defined
     upfront removed the temptation to fix-forward if something had broken.
     → Pattern: "Define rollback criteria BEFORE starting. The decision to revert
        should be automatic, not a judgment call made under pressure."

What Went Wrong:
  1. Almost forgot to verify that the extracted handler handles WebSocket session
     cleanup on disconnect. Caught during manual testing — disconnect during
     audio stream left the stream running. The inline handler had cleanup code
     tied to the onClose callback that wasn't extracted.
     → Anti-pattern #1: "Extraction must include lifecycle code (init, cleanup,
        error handling), not just happy-path handlers."
  2. CatWebSocket.java is still 920 lines after extracting 180 lines. The remaining
     39 handlers are tightly coupled to shared state in CatWebSocket.
     → Observation: later sessions will need to refactor shared state access.
        Document as a design decision for Session 3+.

Performance:
  | Metric                 | Session 1 |
  |------------------------|-----------|
  | Iterations to approval | 1 |
  | Stakeholder corrections| 0 |
  | Tests before           | 247 |
  | Tests after            | 259 (+12 new) |
  | Test failures          | 0 |
  | Lines extracted        | 180 |
  | Regressions            | 1 (lifecycle code — caught in verification) |

Recommendation for Session 2:
  When extracting the next handler group, explicitly check for lifecycle code
  (onOpen, onClose, onError callbacks) that references the handlers being extracted.
  Add "lifecycle code audit" as a research step.
```

### Sessions 2-6

Each subsequent session extracts one handler group, applying all accumulated patterns:
- Session 2: Applies "include lifecycle code" lesson from Session 1
- Session 3: Discovers shared state needs a different access pattern → adds pattern
- Session 4: Finds that two handler groups share a utility method → adds pattern for shared utilities
- Session 5: Previous session's regressions are zero; methodology is mature for this codebase
- Session 6: Extracts the last group and refactors the dispatch mechanism (now that all handlers are extracted, the dispatch is just a map of command → handler)

**By Session 6:** The 1,100-line monolith is now 14 focused handler classes, each independently testable, each extracted without regressions. The session documents serve as a complete refactoring record — anyone can read them to understand WHY each handler is structured the way it is.

---

## Lifecycle Guide

The methodology adapts to every phase of a project's lifecycle. The phases, gates, and self-improvement loop are constant; what changes is the workstream and the relative emphasis on each phase.

### Greenfield (Building Something New)

**Workstream:** Architecture → Design → Development (in sequence)
**Emphasis:** Phase 2 (Research) and Phase 3 (Create) are the heaviest phases

When building from scratch:

1. **Start with an Architecture workstream** (2-4 sessions)
   - Session 1: Overall system architecture (components, interfaces, data flow)
   - Session 2: Data model design
   - Session 3: API contract design
   - Session 4: Integration and deployment architecture

2. **Follow with a Design workstream** (if there's a UI)
   - One session per major view or user workflow
   - Each session reads all prior design sessions

3. **Then a Development workstream** for implementation
   - One session per feature or component group
   - Each session reads the architecture and design documents as reference
   - Implementation follows the approved designs mechanically

**Greenfield-specific guidance:**
- Session 1 of any greenfield workstream has no prior sessions to learn from. Accept that it will be the roughest session. The methodology kicks in starting Session 2.
- Establish patterns early. Session 1's patterns will be applied to every subsequent session. Invest extra time in getting Session 1 right.
- Don't try to design everything in one session. Split into multiple sessions — each one will be better than the last.

### Growth (Adding Features to an Existing System)

**Workstream:** Development (primarily), with occasional Architecture or Design sessions for larger features
**Emphasis:** Phase 2 (Research) shifts to understanding existing code and integration points

When adding features:

1. **Read existing code before designing new code.** The methodology's Phase 2 (Research) naturally handles this — "Inventory existing architecture" and "Read implementations" are standard steps.

2. **Check for adjacent work.** Features don't exist in isolation. Phase 1 (Pre-Flight) spot-checks adjacent artifacts. Phase 6 (Verify) confirms you didn't break them.

3. **Build on accumulated patterns.** If this is Session 8 of a development workstream, you have 7 sessions of patterns, anti-patterns, and reference tables. Use them.

4. **Watch for scope creep.** New features are tempting vehicles for "while I'm here" improvements. The methodology's implementation plan (Phase 3) explicitly lists files NOT modified, creating a scope boundary.

### Maintenance (Fixing Bugs, Updating Dependencies, Routine Work)

**Workstream:** Development or Audit
**Emphasis:** Phase 2 (Research) focuses on root cause analysis; Phase 6 (Verify) is critical for regression prevention

When maintaining:

1. **Group related bugs into campaigns.** Don't fix bugs one at a time — group them by root cause and run a workstream. The self-improvement loop makes each fix in the campaign better than the last.

2. **Trace to structural causes.** The Development workstream's "Fix the Root Cause" section explicitly pushes past symptoms to structural issues. A lint rule that prevents a bug category is worth more than 10 individual fixes.

3. **Track recurring issues.** The Audit workstream's "Recurring Issue Register" tracks bugs that keep coming back. If the same bug appears in 3 sessions, the fix isn't working — the structural cause hasn't been addressed.

4. **Maintenance sessions can be lighter.** If the fix is well-understood and low-risk, Phases 3 (Create) and 4 (Present) can be brief. But Phase 2 (Research) and Phase 6 (Verify) should never be skipped — even "obvious" fixes can cause regressions.

### Refactoring (Changing Structure Without Changing Behavior)

**Workstream:** Development (with Architecture session first for large refactors)
**Emphasis:** Phase 1 (Pre-Flight) and Phase 6 (Verify) are paramount. The safety commit is non-negotiable.

When refactoring:

1. **ALWAYS run an Architecture session first** for any refactoring that touches more than 3 files. Design the target structure before moving code. "Refactoring" without a target architecture is just moving code around.

2. **Pure extraction, then improvement.** Session 1 of a refactoring workstream should ONLY change structure — zero behavior changes. Once the extraction is verified stable (tests pass, no regressions), THEN you can improve the extracted code in a subsequent session. Mixing structure changes with behavior changes is the #1 cause of refactoring regressions.

3. **The rollback rule.** Define rollback criteria before starting. "If any existing test fails after extraction, revert entirely." This must be automatic — not a judgment call made under pressure when things are broken and you're tempted to "just fix this one thing."

4. **Verify aggressively.** After every file change, run the full test suite. After every session, spot-check adjacent systems. Refactoring regressions are the most insidious bugs because the code "looks better" but something subtle is broken.

5. **Track the shrink.** Refactoring campaigns should track: lines in monolith before/after, number of extracted modules, test count before/after, regressions per session. The trajectory should show: monolith shrinking, modules growing, tests growing, regressions decreasing.

### When Lifecycles Overlap

Real projects aren't cleanly phased. You're adding features while fixing bugs while refactoring the mess from last quarter. The methodology handles this through **workstream isolation:**

- Each workstream has its own session documents, pattern library, and performance table
- Sessions in different workstreams don't interfere with each other
- Cross-workstream insights are captured in the master framework, not in individual workstreams

**Example:** You're running a Development workstream (adding features) and an Audit workstream (security review) simultaneously. The audit finds that your new feature has a SQL injection vulnerability. This finding goes into the Audit workstream's session document AND becomes an anti-pattern in the Development workstream's pattern library. Both workstreams benefit.

---

## Running Your First Session

Step-by-step instructions for your very first session with the methodology.

### Before You Start

1. **Choose your workstream.** What type of work are you doing? Pick the matching template from `workstreams/` or create a new one from `TEMPLATE_WORKSTREAM.md`.

2. **Create a sessions directory.** `sessions/{workstream-name}/` — this is where your session documents will live.

3. **Read the master framework.** `ITERATIVE_METHODOLOGY.md` — understand the 6 phases, 12 gates, and self-improvement loop. You don't need to memorize it; you'll reference it during the session.

4. **Read your workstream template.** Understand the domain-specific adaptations for research, creation, and verification.

### During the Session

Follow the 6 phases in order. For each phase:

1. **Do the work described in the phase.**
2. **Check the gate before moving to the next phase.**
3. **If the gate doesn't pass, stay in the current phase until it does.**

For your first session specifically:
- Phase 2 (Research) will feel long. That's correct. Do NOT shortcut it.
- Phase 3 (Create) should produce a document, not code/implementation.
- Phase 4 (Present) requires you to STOP and wait for approval. This feels unnatural. Do it anyway.
- Phase 6 (Close) is where you write learnings. This feels like paperwork. It's actually the most valuable step — it's what makes Session 2 better than Session 1.

### After the Session

1. **Save your session document** to `sessions/{workstream-name}/session-01-{name}.md`
2. **Update the performance tracking table** (it only has one row — that's fine)
3. **Write recommendations for the next session** even if you're also running the next session. Future-you benefits from present-you's fresh perspective.

### Your Second Session

This is where the methodology starts to pay off:

1. **Read Session 1's output.** All of it.
2. **Apply Session 1's patterns.** They're yours now.
3. **Avoid Session 1's anti-patterns.** They're named and numbered.
4. **Check Session 1's recommendations.** Apply them.
5. **At the end, compare performance metrics.** Are you improving?

By Session 3, the loop is automatic. By Session 5, you'll wonder how you worked without it.

---

## Creating a Custom Workstream

When none of the provided workstreams fit your domain:

1. **Copy `TEMPLATE_WORKSTREAM.md`** to `{your-domain}_WORKSTREAM.md`
2. **Fill in the domain-specific sections:**
   - Phase 2: What does research look like in your domain? What do you read?
   - Phase 3: What is the deliverable? What does a good design look like?
   - Scope validation: What questions catch scope problems in your domain?
   - Verification: What does "done right" look like? What would a checklist include?
   - Anti-patterns: What are the common mistakes in your domain?
3. **Run 2-3 sessions with the template.** After each session, update the template with lessons learned.
4. **By Session 3, the template will be tailored to your domain.**

### Workstream Ideas

The methodology works for any repeated skilled work:

| Domain | Star Deliverable | Key Research Focus |
|--------|-----------------|-------------------|
| API Design | Endpoint contract document | Existing APIs, consumer needs, auth model |
| Database Migration | Migration plan with rollback steps | Current schema, data volumes, dependent queries |
| Test Suite Design | Test plan with coverage targets | Code paths, edge cases, failure modes |
| Documentation | Style guide conformant doc | Reader persona, existing docs, terminology |
| Performance Optimization | Optimization plan with baseline | Current metrics, bottleneck analysis, target thresholds |
| Security Hardening | Threat model + remediation plan | Attack surface, OWASP top 10, existing controls |
| Onboarding Materials | Learning path document | New hire persona, existing knowledge, common stumbling blocks |

---

## Using This with AI Agents

This methodology was developed by and for AI agent sessions (Claude Code). It works equally well for human sessions, but AI agents benefit from specific adaptations — particularly the Session Runner, which was created to solve problems unique to AI agent operation.

### The Session Runner

#### The Problem It Solves

The methodology framework (`ITERATIVE_METHODOLOGY.md`) describes 9 principles, 6 phases, 12 quality gates, and a self-improvement loop. It is comprehensive, well-organized, and nearly useless as an operating procedure — because agents don't follow reference documents, they follow checklists.

This distinction was discovered through a post-mortem analysis of repeated session failures. The methodology was created during an 11-session profile design series that achieved remarkable results: single-iteration approval, 0 stakeholder corrections, monotonically increasing defect detection. But every subsequent effort that tried to USE the methodology — rather than invent it in real time — failed to follow it.

**The pattern:**

| Effort | Had the methodology? | Followed it? | Result |
|--------|---------------------|-------------|--------|
| Profile design (11 sessions) | Built it during execution | Yes (it was being discovered) | First-pass approval, 0 corrections |
| Ragchew redesign (Feb 21) | Yes, fully documented | No — jumped straight to editing | All changes reverted |
| Handler refactoring (Feb 16) | Yes | No — no pre/post verification baseline | Broke memory channels + FM panel, cascading regressions |
| FT8 optimization (Feb 7) | Yes | No — skipped baseline benchmark | 5→1 decode regression undetected through 8 commits |
| Sidebar unification (Feb 23) | Yes, explicitly cited | Partially — 4-5 session restarts | Plan was thorough; execution required repeated user intervention |

**The root cause:** The methodology document explains WHAT to do and WHY. It does not provide a step-by-step procedure that an agent can execute mechanically. Agents understand concepts but skip steps. They read the flight manual and think they can fly — but they need a pre-flight checklist.

#### The Three-Layer Hierarchy

The solution is three layers of documentation, each serving a different purpose:

```
SESSION_RUNNER.md          ← Cockpit checklist (FOLLOW this)
    ↓ references
ITERATIVE_METHODOLOGY.md   ← Flight manual (REFERENCE this)
    ↓ adapted by
Workstream prompts          ← Mission procedures (EXECUTE these)
```

| Layer | Document | Read it to... | Length |
|-------|----------|---------------|--------|
| **Operating procedure** | `SESSION_RUNNER.md` (project root) | Know what to do RIGHT NOW, step by step | ~150 lines |
| **Master framework** | `ITERATIVE_METHODOLOGY.md` | Understand WHY the steps exist | ~587 lines |
| **Workstream prompts** | e.g., `DEVELOPMENT_WORKSTREAM.md` | Know HOW to execute for a specific domain | Varies |

The session runner is deliberately short. It fits in a single read. Every line is an imperative instruction, not an explanation. It does not teach — it directs.

#### What the Session Runner Contains

**Phase 0: Orient** — Read governing docs, check workspace state, report to user, STOP. The agent must not start working until the user has spoken. This phase exists because agents have a documented tendency to skip orientation and jump into producing output.

**Phase 1: Receive Task** — Interpret the user's prompt, identify the ONE deliverable, and map it to the correct workstream document. A mapping table translates common user prompts (e.g., "Design the contest profile") to specific workstream docs and deliverables. The agent states its understanding back to the user for confirmation.

**Phase 2: Execute** — Follow the workstream document's phases sequentially, with hard gates. Execute ONE deliverable only.

**Phase 3: Close Out** — The automatic close-out protocol. When the deliverable is complete, the agent executes all of these WITHOUT being asked:
- **3A: Evaluate the previous session's handoff** — Score it 1-10, document what helped, what was missing, what was wrong. This is the compounding mechanism — it creates accountability for handoff quality.
- **3B: Self-assess** — Compare work to previous sessions' quality bar
- **3C: Document learnings** — Update workstream prompt and SESSION_RUNNER learnings table
- **3D: Write handoff notes** — Update SESSION_NOTES.md for the next session. **The agent knows the next session will score these notes**, which changes the quality of what gets written.
- **3E: Commit** — All changes committed
- **3F: Report and STOP** — Summary to user including previous session's handoff score, then session is over

The close-out is the most important innovation. Before the session runner, close-out was manual — the user had to explicitly tell the agent to self-assess, update the prompt, and stop. The agent's natural tendency is to finish the deliverable and immediately start the next one (Failure Mode #2). Making close-out automatic and mandatory means the self-improvement loop runs every session, not just the sessions where the user remembers to ask for it.

The **handoff accountability loop** (steps 3A and 3D) is what makes sessions compound. Without it, handoff notes are perfunctory. With it — knowing the next session will score you, and having scored your predecessor — handoff notes include gotchas, file references with line numbers, and explicit warnings about traps. This single change (added around Session 34) correlated with 14 consecutive clean deliveries.

**Known Failure Modes** — A table of 19 documented agent tendencies with specific countermeasures. This table exists because agents exhibit predictable failure patterns:

| # | Tendency | Countermeasure |
|---|----------|----------------|
| 1 | Eager to start (skip orientation) | Phase 0 is mandatory; user must speak first |
| 2 | Keep going past the deliverable | "1 and done" — close-out fires when deliverable is complete |
| 3 | Skim documents (retain gist, not steps) | Follow the checklist step by step |
| 4 | Assume context after compaction | Trust files, not memory |
| 5 | Equate helpfulness with volume | Quality over quantity |
| 6 | Skip close-out (treat it as cleanup) | Close-out is mandatory and automatic |
| 7 | Ask user to solve process problems | Read the docs first |
| 8 | Redesign during implementation | Commit first, note it for a future session |
| 9 | Task-in-prompt bypass | Phase 0 exists for the user, not the agent |
| 10 | Skip handoff evaluation | Phase 3A is now a mandatory structural step |
| 11 | Gaps from memory | Re-read files before making claims in close-out |
| 12 | Workstream transfer amnesia | Discipline doesn't auto-transfer; re-apply checklist |
| 13 | Literal minimum | Understand underlying intent, not just literal words |
| 14 | Ghost session (crash with no trace) | Phase 1B: write a stub to SESSION_NOTES.md before starting work |
| 15 | Minimal handoff ("pick next from backlog") | Phase 3D has 6 minimum requirements; score ≤4/10 without them |
| 16 | False credit / fabrication | Never claim deliverables you didn't produce |
| 17 | Protocol erosion (skip "just one" step) | Every step exists because a session failed without it |
| 18 | Planning-to-implementation bleed | The plan is the deliverable; close out after the plan |
| 19 | Plan-mode bypass | Plan-mode output is a draft; write to docs/planning/ with evidence first |

The failure modes table serves two purposes: it warns the agent about its own tendencies, and it gives the user language for course-correction ("You're doing Failure Mode #2 — stop and close out").

**Launch Prompt Templates** — Short prompts the user can paste to start a session. The session runner encodes everything else (what to read, when to stop, how to close). This means the user's effort to start a session drops from a paragraph of instructions to a single sentence.

#### Why This Works (Theory)

The session runner compensates for three structural properties of AI agents:

1. **Stateless sessions.** Each session starts with zero context from the previous session. The methodology's self-improvement loop generates context (session documents, patterns, anti-patterns), but the agent must be DIRECTED to read it. The session runner's Phase 0 (Orient) is that direction.

2. **Reward-seeking behavior.** Agents are trained to produce output. Stopping feels unproductive. Research feels like overhead. Close-out feels like cleanup. The session runner reframes these as mandatory steps, not optional nice-to-haves. Phase 0 says "STOP" in capital letters. Phase 3 says "AUTOMATIC — without being asked."

3. **Concept vs. procedure gap.** Agents can understand a methodology conceptually after reading it once. But understanding a concept and following a procedure are fundamentally different cognitive tasks. The methodology document teaches concepts; the session runner provides procedures. An agent that has "understood" the methodology will still skip steps — because understanding doesn't produce compliance, checklists do.

This mirrors a well-known finding in aviation safety: pilots who understand aerodynamics still crash without pre-flight checklists. The checklist doesn't teach — it constrains. The session runner is the same mechanism applied to AI agent sessions.

#### Integrating the Session Runner with Your Project

To use the session runner in your own project:

1. **Place `SESSION_RUNNER.md` at the project root** (alongside your CLAUDE.md or equivalent agent instructions file).

2. **Reference it at the top of your agent instructions:**
   ```
   ## SESSION PROTOCOL — FOLLOW BEFORE DOING ANYTHING
   Read and follow SESSION_RUNNER.md step by step.
   ```

3. **Update the task-to-workstream mapping table** (Phase 1) to match your project's workstream prompts.

4. **Update the failure modes table** with any tendencies specific to your project. The 19 documented modes are common to most AI agent work, but your project may surface additional ones.

5. **Put the methodology framework in a known location** (e.g., `docs/methodology/`) so the session runner can reference it.

The session runner is project-independent. The 4 phases and the failure modes table apply to any project using the iterative methodology. What changes per project is the task-to-workstream mapping and any project-specific failure modes.

### Agent-Specific Guidance

Beyond the session runner, AI agents benefit from these adaptations. These findings come from 60+ real sessions, not speculation.

1. **Agents lose context between sessions.** The session document IS the context transfer mechanism. Write session documents as if the next agent has never seen the codebase — because they haven't (they'll have compacted context at best). Context also degrades WITHIN a session due to compaction. Never write claims from memory — re-read the file.

2. **Agents are tempted to skip Research.** The Phase 2 gate exists precisely because agents (like humans) want to start creating immediately. The gate is structural — enforce it.

3. **Agents may not self-correct.** The self-improvement loop requires honest What Went Wrong sections. If the agent produces only "What Went Right," prompt for failures: "What would a hostile reviewer say you got wrong?"

4. **Agents do the literal minimum.** When asked to "make X a plugin," an agent will create the plugin but leave the hardcoded version in place. The fix is structural: before acting, ask "What is the user's UNDERLYING intent?" — not "What are the literal words?" This failure mode caused significant user trust damage in Sessions 1-9.

5. **Discipline doesn't transfer across workstreams.** An agent that writes excellent handoffs on workstream A will revert to perfunctory handoffs when switching to workstream B. The close-out checklist must be consciously re-applied on every workstream change.

6. **Speed feels like quality to agents.** When a plan collapses multi-session work into a single fast session, agents treat the speed as evidence of quality and skip verification. The opposite is true: saved time should be spent on runtime verification.

7. **Write to files first, then summarize verbally.** Agents naturally do the reverse — explain to the user, then (maybe) write it down. A verbal summary not written to persistent files is worthless to the next session. The rule: files first, then talk.

4. **Parallel research is an agent superpower.** Agents can read 20 files in parallel via sub-agents. Use this to make Phase 2 comprehensive without being slow. The original methodology used Explore agents to read all 22 plugin directories in a single turn.

5. **Verify agent claims mechanically.** When an agent says "this component supports X," verify with grep or direct reading. Trust but verify — anti-pattern #31 in the original methodology exists because an agent incorrectly claimed variant support for 5 components.

6. **The "1 and done" rule is essential for agents.** Human developers naturally stop at the end of a work session (they get tired, they go home). Agents don't. They will continue producing output indefinitely, and each additional deliverable after the first is lower quality because the context window is filling up. One excellent deliverable per session is the optimal strategy.

7. **Close-out is where the compound interest accrues.** The session runner's Phase 3 (Close Out) is the mechanism that makes Session N+1 better than Session N. If close-out is skipped — as agents are prone to do — the self-improvement loop breaks and every session starts from scratch. Making close-out automatic and mandatory is the single highest-ROI change in the session runner.

### Multi-Agent Teams

For large workstreams, agents can work in parallel on different sessions:
- Agent A: Session for resource X
- Agent B: Session for resource Y
- Both read the same prior session outputs
- Both produce session documents that Agent C (or the next round) reads

The session documents are the coordination mechanism. Agents don't need to communicate directly — they communicate through accumulated patterns and anti-patterns.

Each agent should follow its own copy of the session runner. The orient phase is the same; the deliverable is different; the close-out feeds into the shared workstream prompt.

---

## Scaling

### Solo Developer

The methodology works for one person doing repeated work:
- You are both the creator and the stakeholder
- Phase 4 (Present) becomes self-review with a specific checklist
- The self-improvement loop still works — your session documents teach future-you

### Small Team (2-5)

- One person creates, another reviews at Phase 4
- Session documents are shared — everyone reads prior sessions
- Pattern library is team-wide — patterns discovered by one member benefit all
- Performance table creates healthy accountability

### Larger Teams

- Workstream leads maintain the pattern library and performance table
- Session documents are stored in a shared location (wiki, repo, shared drive)
- Anti-patterns become team standards: "We don't do #29 (domain-tool mismatch)"
- New team members read the session history to absorb the team's accumulated knowledge — this is better than tribal knowledge because it's documented, numbered, and traced to specific experiences

---

## Troubleshooting

### "The methodology feels too heavy for this task."

If the task is truly one-off and trivial, don't use the methodology. It's designed for repeated work where quality compounds. For a single fix with no repetition, just fix it.

If the task feels trivial but is actually part of a series (you'll do 5 more like it), use the methodology. The overhead of Session 1 pays for itself by Session 3.

### "I keep skipping Phase 4 (Present) because I'm sure the design is right."

This is the most common failure mode. The sessions where you're "sure" are the sessions where you're most likely to be wrong, because overconfidence correlates with blind spots.

Force the gate: show the design to someone (a colleague, an AI, even a rubber duck document review) before implementing.

### "My What Went Wrong section is always empty."

You're not looking hard enough. Every session has something that could have gone better. If you genuinely can't find anything, ask: "What would I do differently if I ran this session again?" or "What took longer than it should have?" or "What assumption did I make that I didn't verify?"

### "The self-improvement loop isn't improving anything."

Check:
1. Are you actually reading prior session documents? (Not skimming — reading.)
2. Are your anti-patterns specific enough to be actionable? ("Be more careful" is not actionable. "Verify domain-ecosystem fit before including a component" is.)
3. Are you tracking recommendations compliance? If Session 2 doesn't address Session 1's recommendations, the loop is broken.

### "Sessions are taking too long."

Phase 2 (Research) is the heaviest phase. If it's taking too long:
- Are you researching things that don't affect the design? (Stay focused on what matters for THIS session.)
- Can you parallelize research? (AI agents can; humans can batch-read.)
- Is the scope too large for one session? (Split into multiple sessions.)

Phase 5 (Implement) should be fast if Phase 3 (Create) was thorough. If implementation is slow, the design wasn't detailed enough.

### "I have 15 sessions and the pattern library is huge."

This is a good problem. At 15+ sessions:
- Mature patterns (applied 5+ times) can move to a "Standard Patterns" section
- Anti-patterns that haven't been triggered in 5+ sessions can move to an archive
- The performance table should show stable metrics — if it does, the methodology is mature for this workstream
- Consider writing a "workstream summary" that captures the most important lessons for someone starting fresh
