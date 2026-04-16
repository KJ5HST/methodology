# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repository Is

A standalone methodology framework for structured, self-correcting AI agent sessions. It is **not a software project** — it contains no code to build, test, or run. The deliverables are markdown documents.

**Repository:** `git@github.com:KJ5HST/methodology.git`
**Author:** Terrell Deppe (KJ5HST)
**License:** Free to share/adapt with attribution; may not be sold or claimed as your own.

## Document Hierarchy

Three layers, each serving a distinct purpose:

| Layer | File | Role |
|-------|------|------|
| Cockpit checklist | `starter-kit/SESSION_RUNNER.md` | Step-by-step operating procedure for every session |
| Flight manual | `ITERATIVE_METHODOLOGY.md` | Theory: 9 principles, 6 phases, 12 quality gates |
| Mission procedures | `workstreams/*.md` | Domain-specific adaptations (design, architecture, development, audit) |

`SESSION_RUNNER.md` is the entry point — it tells agents what to read, when to stop, and how to close out. Everything cascades from that single file.

## Architecture

The framework's core loop:

```
Pre-Flight → Research → Create → Present → Implement → Verify & Close
```

Each phase is hard-gated — you cannot skip ahead. The most critical gate is between Present and Implement (no implementation without stakeholder approval).

**The compounding mechanism** is the handoff accountability loop: each session evaluates its predecessor's handoff (scored 1-10) and writes its own knowing it will be scored. This bidirectional accountability is what makes session N+1 better than session N.

### Starter Kit Files (templates for adopting projects)

| File | Purpose |
|------|---------|
| `starter-kit/SESSION_RUNNER.md` | Operational checklist — users copy this to their project root |
| `starter-kit/SAFEGUARDS.md` | Commit discipline, blast radius limits, mode-switching rules |
| `starter-kit/SESSION_NOTES.md` | Empty template for session continuity between sessions |
| `starter-kit/BOOTSTRAP.md` | Step-by-step setup guide for new projects |
| `starter-kit/CHANGELOG.md` | Completed work history template — keeps BACKLOG.md lean |
| `starter-kit/ROADMAP.md` | Feature inventory and future plans template |
| `starter-kit/methodology_dashboard.py` | Health scanner — copy to project root for per-project dashboard |

### Tools

| File | Purpose |
|------|---------|
| `tools/methodology_dashboard.py` | Portfolio health scanner — scores projects on activity, testing, docs, CI/CD, methodology compliance; generates HTML dashboard. Place in parent directory above project repos. Python 3 stdlib only, cross-platform. |

### Workstreams (domain-specific adaptations)

| File | Domain |
|------|--------|
| `workstreams/DESIGN_WORKSTREAM.md` | UI/UX, visual design, layout |
| `workstreams/ARCHITECTURE_WORKSTREAM.md` | Systems, APIs, data models |
| `workstreams/DEVELOPMENT_WORKSTREAM.md` | Feature implementation, bug fixes |
| `workstreams/AUDIT_WORKSTREAM.md` | Code audits, security reviews |
| `workstreams/TEMPLATE_WORKSTREAM.md` | Blank template for creating new workstreams |

## Key Concepts to Preserve When Editing

- **SESSION_RUNNER.md documents 23 failure modes** with specific countermeasures. These are empirically derived from 60+ sessions — do not remove or weaken them without strong justification.
- **Phase 0 (Orient) must remain mandatory and blocking** — the most common failure mode is agents skipping orientation and starting work immediately.
- **"1 and done" rule** — one deliverable per session, then close out. This is structural, not advisory.
- **Ghost session detection** (Phase 0, step 5) exists because crashed sessions that leave no trace cause the next session to work from stale state.
- **Phase 1B (Claim the Session)** exists for the same reason — writing a stub before technical work ensures even crashed sessions leave evidence.
- **Minimum handoff requirements** (Phase 3D) are non-negotiable: key files with line numbers, gotchas, specific next steps. "Pick next from backlog" is explicitly insufficient.
- **Plan Mode exit trap** — Plan Mode auto-generates "Implement the following plan" as a preamble. The SESSION_RUNNER explicitly warns this does NOT mean "start coding."

## Versioning

Changes are tracked via git commits and the README's "What's New" section. Current version: v2.1. Key additions by version:

- **v1.0:** Initial 9 principles, 6 phases, 4 workstreams
- **v1.1:** Protocol erosion detection, ghost session prevention, minimum handoff requirements, 4 new failure modes (#14-17)
- **v1.2:** Planning session discipline, evidence-based inventory, phase boundaries
- **v2.0:** Methodology Dashboard — portfolio health scanner with dual-mode detection, health/risk scoring, methodology compliance checking, live HTML dashboard with auto-refresh, color-coded terminal output, starter-kit inclusion
- **v2.1:** CHANGELOG.md and ROADMAP.md templates, three-file task tracking split, migration guide for monolithic backlogs, dashboard compliance updates, 4 new failure modes (#20-23), Artifact Integrity safeguards, build equivalent step in BOOTSTRAP, documentation project adaptations
