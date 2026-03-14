![GitHub release](https://img.shields.io)
![GitHub tag (latest by date)](https://img.shields.io/github/v/tag/USERNAME/REPO)
![npm](https://img.shields.io)


# Iterative Session Methodology

A framework for producing high-quality software through structured, self-correcting AI agent sessions. Each session follows a fixed phase sequence, accumulates knowledge, and feeds lessons back into the process. The result: sessions compound — session 40 is dramatically better than session 10, using the same tools on the same type of work.

## The Problem

AI agents are capable but inconsistent. They skip steps, lose context between sessions, start implementing before researching, and treat speed as evidence of quality. A methodology document alone doesn't fix this — agents read it, understand it conceptually, and still skip steps. Understanding a concept and following a procedure are fundamentally different cognitive tasks.

This framework solves the problem with three layers:

| Layer | Document | Purpose |
|-------|----------|---------|
| **Cockpit checklist** | `SESSION_RUNNER.md` | Step-by-step procedure. Follow this. |
| **Flight manual** | `ITERATIVE_METHODOLOGY.md` | Theory and principles. Reference this. |
| **Mission procedures** | `workstreams/*.md` | Domain-specific adaptations. Execute these. |

The checklist constrains. The manual teaches. The mission procedures specialize. All three are needed.

## Evidence

Extracted from an 11-session UI/UX design series. Validated across 60+ sessions spanning implementation, CI integration, plugin architecture, code review, planning, and audit work.

| Metric | Session 1 | Session 10 | Session 40+ |
|--------|-----------|------------|-------------|
| Iterations to approval | 4 | 1 | 1 |
| Stakeholder corrections | 5 | 0 | 0 |
| Defects found in existing work | 0 | 15 | 15+ |
| Patterns in library | 5 | 40+ | Stable |

**What changed was not skill — it was methodology.** The same agent, same tools, same problem type, radically different outcomes.

## The 9 Principles

| # | Principle | One-Line Summary |
|---|-----------|-----------------|
| 1 | **Complete-Then-Create** | Finish ALL research before ANY creative work |
| 2 | **Self-Correcting Loop** | Every failure becomes a numbered anti-pattern. The process evolves. |
| 3 | **Hard Phase Gates** | You cannot skip phases. Gates are structural, not advisory. |
| 4 | **Knowledge Compounding** | Later sessions build on earlier sessions by citation, not re-derivation |
| 5 | **Honest Accounting** | What Went Right AND What Went Wrong, tracked quantitatively |
| 6 | **Scope Validation** | "Am I solving the right problem?" before "Am I solving the problem right?" |
| 7 | **Ascending Verification** | Move from assumptions to mechanical checks as trust increases |
| 8 | **Handoff Accountability** | Evaluate the previous session's handoff. Write yours knowing you'll be evaluated. |
| 9 | **Session Scope Bounding** | One deliverable per session. When it's done, close out. |

Principle 8 is the most important discovery. The bidirectional accountability loop — knowing the next session will score your handoff, having scored your predecessor's — is what makes sessions compound rather than stay isolated.

## The 6 Phases

```
Pre-Flight → Research → Create → Present → Implement → Verify & Close
```

Each phase is gated. You cannot enter the next phase until the current one is complete. The most valuable gate is between Present and Implement: no implementation begins without stakeholder approval.

## Quick Start
*NOTE: The absolute fastest way to use this is to tell Claude (or other service), "Use this methodology: https://github.com/KJ5HST/methodology". Claude will pull it down and put it in place for you.*

> **Important:** After setup completes, start a **new session** before giving Claude real work. Claude Code reads `CLAUDE.md` at session start — changes made during setup don't take effect until the next session. If you say "go" in the same session, Claude will work without the protocol.

### 1. Copy files to your project

Copy `starter-kit/SESSION_RUNNER.md`, `starter-kit/SAFEGUARDS.md`, and `starter-kit/SESSION_NOTES.md` to your project root. Copy the framework files (`ITERATIVE_METHODOLOGY.md`, `HOW_TO_USE.md`, `workstreams/`) to `docs/methodology/`.

### 2. Tell Claude to use it

Add this to your project's `CLAUDE.md` (Claude Code reads this file at the start of every session):

```markdown
## SESSION PROTOCOL — FOLLOW BEFORE DOING ANYTHING

Read and follow `SESSION_RUNNER.md` step by step. It is your operating procedure
for every session. It tells you what to read, when to stop, and how to close out.
```

**That's it.** Claude will orient, wait for your task, execute one deliverable, and auto-close with handoff notes for the next session. Everything cascades from that one instruction — `SESSION_RUNNER.md` tells Claude to read `SAFEGUARDS.md` and `SESSION_NOTES.md`, which establish commit discipline and session continuity.

### 3. Create a backlog

Create a `BACKLOG.md` at your project root with your current tasks and priorities. The session runner reads this during orientation. You can also tell claude to make a plan for your effort that follows this methodology. Once the plan is created, start a new session and either tell claude to implement the next phase of your plan, and tell it what file the plan is in, or build the backlog from that plan.

### Full setup guide

See **[`starter-kit/BOOTSTRAP.md`](starter-kit/BOOTSTRAP.md)** for the complete step-by-step guide including customization, first session checklist, and troubleshooting.

### What's in the starter kit

| File | Purpose |
|------|---------|
| `BOOTSTRAP.md` | Complete setup guide, customization, troubleshooting |
| `SESSION_RUNNER.md` | Cockpit checklist template (no project-specific history) |
| `SESSION_NOTES.md` | Empty template for session continuity |
| `SAFEGUARDS.md` | Safety rails: commit discipline, blast radius limits, mode switching |

## Repository Structure

```
├── README.md                         ← You are here
├── ITERATIVE_METHODOLOGY.md          ← Master framework (9 principles, 6 phases, 12 gates)
├── HOW_TO_USE.md                     ← Practical guide with 3 worked examples
│
├── workstreams/                      ← Domain-specific adaptations
│   ├── DESIGN_WORKSTREAM.md          ← UI/UX design, visual design, layout
│   ├── ARCHITECTURE_WORKSTREAM.md    ← System architecture, API design
│   ├── DEVELOPMENT_WORKSTREAM.md     ← Feature implementation, bug fix campaigns
│   ├── AUDIT_WORKSTREAM.md           ← Code audits, security reviews, quality gates
│   └── TEMPLATE_WORKSTREAM.md        ← Create your own workstream
│
└── starter-kit/                      ← Copy these to bootstrap a new project
    ├── BOOTSTRAP.md                  ← Setup guide
    ├── SESSION_RUNNER.md             ← Cockpit checklist template
    ├── SESSION_NOTES.md              ← Session continuity template
    └── SAFEGUARDS.md                 ← Safety rails template
```

## Key Concepts

### The Session Runner

The methodology framework describes WHAT to do and WHY. In practice, it needs an operational wrapper — a cockpit checklist — that ensures the phases are actually followed. The Session Runner provides:

- **Mandatory orientation** — prevents starting work without understanding current state
- **"1 and done" rule** — prevents scope creep and quality degradation
- **Automatic close-out** — prevents skipping the self-improvement loop
- **17 known failure modes** — documents agent tendencies with specific countermeasures
- **Degradation detection** — 7 warning signs that predict protocol erosion
- **Handoff accountability** — ensures each session sets up the next for success

### The Handoff Accountability Loop

Every session close-out includes two steps:

1. **Evaluate the previous session's handoff** — Score it 1-10. What helped? What was missing? What was wrong?
2. **Write your own handoff knowing the next session will score it** — Include key files, line numbers, gotchas, and traps.

This creates accountability that transforms handoff quality. Before this pattern: perfunctory notes. After: detailed, accurate, actionable handoffs with gotchas that catch real issues.

### Workstreams

Domain-specific adaptations of the master framework. Each workstream customizes the Research, Create, and Verify phases for its domain:

| Workstream | Best For |
|-----------|----------|
| **Design** | UI layouts, component arrangements, visual hierarchy |
| **Architecture** | Systems, APIs, data models, integration patterns |
| **Development** | Feature implementation, bug fix campaigns |
| **Audit** | Code reviews, security assessments, quality gates |

### When to Use / When Not to Use

**Use when:**
- You do the same TYPE of work repeatedly
- Quality matters more than speed on any individual session
- You want each session to be better than the last

**Don't use when:**
- One-off tasks with no repetition (the loop has nothing to feed into)
- Trivial tasks where the overhead exceeds the work
- Exploratory work with no defined deliverable

## Origin

Developed by Terrell Deppe (KJ5HST) using Claude Code (Anthropic) during development of a commercial software product. The methodology emerged organically from an 11-session design series, was codified into a reusable framework, and subsequently validated across 52+ sessions of varied work.

The framework is agent-independent — it works with any AI coding agent that supports persistent files and session-based interaction. It also works for human developers, though the Session Runner and known failure modes are specifically tuned for AI agent tendencies.

### What's New in v1.1

- **Protocol Erosion section** — documents how methodology discipline degrades over time and how to detect it early
- **Phase 1.5: Claim the Session** — write a stub before starting work so even crashed sessions leave a trace
- **Minimum Handoff Requirements** — 6 mandatory items with bad/good examples; "pick next from backlog" is explicitly called out as insufficient
- **Ghost session detection** — Phase 0 now checks for undocumented sessions between the last notes and current state
- **Fabrication warning** — honest accounting now explicitly addresses false credit and fabricated quotes
- **4 new failure modes** (#14-17): ghost sessions, minimal handoffs, fabrication, protocol erosion
- **Degradation Detection table** — 7 warning signs with responses
- **Quality Gates expanded** from 10 to 12

## License

Copyright 2026 by Terrell Deppe. You are free to share and adapt this material with appropriate attribution. You may use it to make money, but you may not call it your own, or sell it in any way.
