# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repository Is

A standalone methodology framework for structured, self-correcting AI agent sessions. It is **not a software project** — it contains no code to build, test, or run. The deliverables are markdown documents.

**Repository:** `git@github.com:KJ5HST/methodology.git`
**Author:** Terrell Deppe (KJ5HST)
**License:** Free to use, adapt, and implement with attribution — including for commercial operational use; may not be sold or commercially exploited as a standalone product/service/training material. See `LICENSE`.

## Document Hierarchy

Three layers, each serving a distinct purpose:

| Layer | File | Role |
|-------|------|------|
| Cockpit checklist | `starter-kit/SESSION_RUNNER.md` | Step-by-step operating procedure for every session |
| Flight manual | `ITERATIVE_METHODOLOGY.md` | Theory: 9 principles, 6 phases, 12 quality gates |
| Mission procedures | `workstreams/*_WORKSTREAM.md` | Domain-specific adaptations (design, architecture, development, audit, research documentation) |
| Campaign templates | `workstreams/*_CAMPAIGN.md` | Multi-session campaigns extending a workstream |

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
| `workstreams/RESEARCH_DOCUMENTATION_WORKSTREAM.md` | Research papers, technical reports, dissertations, regulatory analyses |
| `workstreams/TEMPLATE_WORKSTREAM.md` | Blank template for creating new workstreams |

### Campaigns (multi-session work patterns within a workstream)

| File | Purpose |
|------|---------|
| `workstreams/RESEARCH_EXHAUSTIVE_VERIFICATION_CAMPAIGN.md` | Multi-session campaign template for exhaustive primary-source verification. Extends the Research Documentation workstream when per-session Phase 6 audit cannot complete the work. Supports both creation mode (writing) and audit mode (reviewing). |
| `workstreams/INHERITED_CODEBASE_FAMILIARIZATION_CAMPAIGN.md` | Multi-session campaign template for taking over an unfamiliar codebase. Extends the Audit workstream; feeds the Development workstream via a prioritized backlog. Supports interview mode (departing owner available) and archaeology mode (owner gone). |
| `workstreams/TEMPLATE_CAMPAIGN.md` | Blank template for creating new campaigns (parallel to `TEMPLATE_WORKSTREAM.md`). |

## Key Concepts to Preserve When Editing

- **SESSION_RUNNER.md documents 26 failure modes** with specific countermeasures. These are empirically derived from 60+ sessions — do not remove or weaken them without strong justification. FMs 1–25 must not be renumbered; new FMs append at the end (e.g., FM #24 was appended in v2.3, FM #25 in v2.6, and FM #26 in v2.7, not inserted).
- **Phase 0 (Orient) must remain mandatory and blocking** — the most common failure mode is agents skipping orientation and starting work immediately.
- **"1 and done" rule** — one deliverable per session, then close out. This is structural, not advisory. Since v2.7 the one deliverable MAY be a pre-declared verified vertical slice (issues #20/#21; `SESSION_RUNNER.md` §Vertical Slice Sessions) — the allowance adds a gate and removes no step; one capability never means a second capability.
- **Ghost session detection** (Phase 0, step 5) exists because crashed sessions that leave no trace cause the next session to work from stale state.
- **Phase 1B (Claim the Session)** exists for the same reason — writing a stub before technical work ensures even crashed sessions leave evidence.
- **Minimum handoff requirements** (Phase 3D) are non-negotiable: key files with line numbers, gotchas, specific next steps. "Pick next from backlog" is explicitly insufficient.
- **Plan Mode exit trap** — Plan Mode auto-generates "Implement the following plan" as a preamble. The SESSION_RUNNER explicitly warns this does NOT mean "start coding."

## Versioning

Changes are tracked via git commits and the README's "What's New" section. Current version: v2.7.2. Key additions by version:

- **v1.0:** Initial 9 principles, 6 phases, 4 workstreams
- **v1.1:** Protocol erosion detection, ghost session prevention, minimum handoff requirements, 4 new failure modes (#14-17)
- **v1.2:** Planning session discipline, evidence-based inventory, phase boundaries
- **v2.0:** Methodology Dashboard — portfolio health scanner with dual-mode detection, health/risk scoring, methodology compliance checking, live HTML dashboard with auto-refresh, color-coded terminal output, starter-kit inclusion
- **v2.1:** CHANGELOG.md and ROADMAP.md templates, three-file task tracking split, migration guide for monolithic backlogs, dashboard compliance updates, 4 new failure modes (#20-23), Artifact Integrity safeguards, build equivalent step in BOOTSTRAP, documentation project adaptations
- **v2.2:** `bin/sync` + `bin/status` distribution tooling (dual-mode commit/ignore, dual-source local/github), CLAUDE_TEMPLATE.md customization seam, BOOTSTRAP.md rewrite, drift-safety guard on sync
- **v2.3:** Combined release covering two contributions. (1) **Research Documentation workstream** — adapts the methodology for research papers, technical reports, dissertations, and regulatory analyses; source-corpus management, claim-source audit pattern, 19 documented anti-patterns, toolchain adaptation table (Quarto/LaTeX/Sphinx/Pandoc/AsciiDoc/Markdown), Audit Mode for fresh-eyes review of existing repositories. (2) **SESSION_RUNNER content release** from rad-con audit (issue #6, #7) — new Phase 3E Runtime Smoke Test (renumber 3E→3F, 3F→3G), new FM #24 (build-passes-ship-it, appended — FMs 1–23 unchanged), Phase 1B "structural control" framing, Planning Sessions grep anecdote, 5 new Learnings rows.
- **v2.4:** Multi-session campaigns promoted to first-class layer — new vocabulary and document home for campaign templates that extend a workstream. New section in `ITERATIVE_METHODOLOGY.md` (§Multi-Session Campaigns); new orientation step in `SESSION_RUNNER.md` (Phase 1 multi-session campaign check); new `workstreams/TEMPLATE_CAMPAIGN.md`. No principle, phase, gate, or workstream changes. Realized examples: `workstreams/RESEARCH_EXHAUSTIVE_VERIFICATION_CAMPAIGN.md` (extends Research Documentation) and `workstreams/INHERITED_CODEBASE_FAMILIARIZATION_CAMPAIGN.md` (extends Audit).
- **v2.5:** Render-dependency completeness discipline (resolves upstream issue #12, drafted from `docs/planning/font-discipline-proposal.md`). Universal principle in `starter-kit/SAFEGUARDS.md` (new "Verify Render-Dependency Completeness" sub-section under "Verify the Build Equivalent"): build success is not asset-use success. Two-tier check: post-render is a **hard rule** (part of build-equivalent — e.g., `pdffonts` confirms all configured font faces embedded); pre-render / setup is a **soft prompt** that fires at Phase 0 when render-dep config changes (e.g., `fc-list`, `kpsewhich`). Concrete commands in `workstreams/RESEARCH_DOCUMENTATION_WORKSTREAM.md` — new Render Verification bullet, new Verification Checklist item, new "Render-Dep Check" column on the toolchain matrix (per-toolchain static + post-render commands for Quarto/LaTeX/Sphinx/Pandoc/AsciiDoc), and new anti-pattern #20 "Silent render-dependency fallback" (derived from the joy/ SBL BibLit case: 47 sessions of italic markup silently rendered as upright Latin glyphs). `workstreams/RESEARCH_EXHAUSTIVE_VERIFICATION_CAMPAIGN.md` Render Verification section gains a render-dep completeness line so the campaign inherits the discipline. No principle, phase, gate, or workstream changes; no FM renumbering.
- **v2.6:** Skill-recommendation convention — new content layer alongside phases, principles, workstreams, and campaigns. Principle: *methodology recommends; methodology does not reimplement.* New `starter-kit/RECOMMENDED_SKILLS.md` (canonical index with per-skill known-good SHAs for external skills) + new `ITERATIVE_METHODOLOGY.md` §Recommended Skills (principle paragraph + index pointer). Conceptual content distilled from the 2026-05-02 Pocock-skills audit lands as new FM #25 (horizontal slicing, appended — 1–24 unchanged), `SESSION_RUNNER.md` Phase 3F and `ITERATIVE_METHODOLOGY.md` Phase 6 step 8 gain an explicit "remove debug instrumentation before commit" gate (cites `/diagnose`), new `starter-kit/CONTEXT_TEMPLATE.md` + Phase 2 read-step (cites `/grill-with-docs`), new Issue Lifecycle section in `DEVELOPMENT_WORKSTREAM.md` (cites `/triage`), new Debugging Sessions session type (cites `/diagnose`), new Refactor Heuristics in `ARCHITECTURE_WORKSTREAM.md` (cites Ousterhout + `/improve-codebase-architecture`), new optional Phase 2.5 Pre-Create Grill (cites `/grill-me`), pre-commit + git-guardrails paragraphs in `BOOTSTRAP.md` Step 10 (cite `/setup-pre-commit` + `/git-guardrails-claude-code`). Existing-content refactors: `SESSION_RUNNER.md` Phase 3E body shortened to cite `/verify` + `/run` (intent preserved); `AUDIT_WORKSTREAM.md` gains a Light Recommended-Skills callout citing `/code-review`, `/review`, `/security-review`. Audit doc lands at `docs/audits/2026-05-02-mattpocock-skills-evaluation.md` with a drop/keep/refactor Implementation Status header. Phase 2 step renumbered 1→2..7→8; `HOW_TO_USE.md` Phase 2 cross-references all cite by name, never by step number, so the renumber is safe. No principle, phase, gate, or workstream changes. Adopters who never use the recommended skills continue to operate the methodology as written.
- **v2.6.1:** Docs-only dot release bundling four external contributions (rmsharp PRs #18/#23/#25/#27). (1) **Skill-citation discipline completed** (#18): `/init` actually cited in `BOOTSTRAP.md` Step 4 with a skip path for existing CLAUDE.md projects; `/fewer-permission-prompts` dropped from the index (no natural citation site); new "A skill is not a phase" principle paragraph in `ITERATIVE_METHODOLOGY.md` §Recommended Skills (a skill that pulls a session across a hard gate is FM #2 wearing a tool costume — gates bind regardless of loaded tools); new "Skills not recommended (and why)" 10-row subsection in `RECOMMENDED_SKILLS.md` surfacing the v2.6 audit's deliberate omissions plus hedged post-audit entries (`/handoff`, `/prototype`). (2) **Learnings-routing fix** (#25, closes #24): `SESSION_RUNNER.md` Phase 3C dual-audience recomposition — adopters record learnings in `CLAUDE.md` Adaptations, canonical repo appends to the seed table; false "table starts empty" caption corrected; `HOW_TO_USE.md` retargeted. (3) **CLAUDE.md size budget** (#27, closes #26): `BOOTSTRAP.md` Step 5 size-budget rule + extract-to-`PROJECT_LEARNINGS.md` overflow valve + plain-link (not `@`-import) pointer warning. (4) `tools/__pycache__/` gitignored (#23). No principle, phase, gate, workstream, or FM changes; FM count stays 25.
- **v2.6.2:** Docs-only dot release resolving issue #22 (Pocock skill enablement gap, rmsharp investigation) under **strategy C (Reactive)**: enablement is per-request via adopter `CLAUDE.md` adaptations or `/grill-with-docs` lazy-creation — no methodology-shipped templates (preserves "methodology recommends; methodology does not reimplement"). (1) **Bounding axis:** new "Phases spanned (compression risk)" column on `RECOMMENDED_SKILLS.md`'s external-skills table — verbatim-verified per-skill phase spans at the pinned SHAs (`/grill-with-docs` + `/improve-codebase-architecture` = HIGH, Phase 2→3→5; `/diagnose` = medium by design); reading-guidance paragraph (plan the stop point before invoking high-compression skills; "A skill is not a phase" cross-ref); in-file forward-compat note to restate in vertical-slice vocabulary if #20/#21 land. (2) **`/triage` contradiction:** resolved by footnote — citation stands, adopters establish the label mapping themselves per `DEVELOPMENT_WORKSTREAM.md` §Issue Lifecycle instead of running the declined `/setup-matt-pocock-skills`. Issues #20/#21 remain open and unprejudged. No principle, phase, gate, workstream, or FM changes.
- **v2.7:** Vertical-slice model — the first change to the unit of "1 and done" (issues #20/#21, adopted by operator decision 2026-06-12). One deliverable MAY be a **verified vertical slice** (one capability end to end) under four mandatory gates: (a) layer set pre-declared in a plan-mode contract before any code (prior-session approval satisfies; implementing session re-verifies at Orient), (b) checkpoint commit at every layer boundary (5-file cap unchanged, clarified *per-commit* in `SAFEGUARDS.md`), (c) full build/test matrix + exhaustive grep at *each* boundary, (d) per-surface faithful verification ("all tests ran" is not automatically faithful). **Evidence-gated, not self-certified** — missing per-boundary artifacts revert the session to horizontal scope at the last clean checkpoint. Recoverability, not verifiability, is the ceiling on slice size; seven boundary types stay non-collapsible (irreversible migrations, operator-approval gates, plan ↔ implementation, cross-toolchain cutovers, live-device verification, unfaithful-suite surfaces, recoverability ceiling). New `SESSION_RUNNER.md` §Vertical Slice Sessions; Principle 9 extended; guardrails: new **FM #26** "mega-session masquerading as a vertical slice" (appended — 1–25 unchanged) + degradation row, FM #17 anti-erosion clause (the allowance ADDS a gate, removes no step), FM #18 discriminator + degradation-row exception for pre-declared slices, 6-phase-model mirroring note. Touch-ups: `RECOMMENDED_SKILLS.md` phase-map guidance restated in vertical-slice vocabulary (v2.6.2's forward-compat note discharged); §Recommended Skills "compress two sessions into one" sentence reworked. Strict horizontal "1 and done" remains the default and the fallback; no phase, gate, or workstream changes.
- **v2.7.2:** Docs-only dot release bundling three external contributions (rmsharp PRs #29/#30/#31), each resolving one PR-14-review issue. (1) **Agent-level memory generalization** (#29, closes #16): `starter-kit/CONTEXT_TEMPLATE.md`'s "CONTEXT.md vs auto-memory" guidance is renamed "CONTEXT.md vs **agent-level memory**" — the second persistence layer is now named by capability (persistence scoped to the agent across all projects) rather than by Claude Code's brand term, with a one-line gloss that agents implement it under different names (Claude Code's auto-memory, Cursor's memories, Cody's preferences); keeps the methodology agent-independent. (2) **Workstream skill-citation convention** (#30, closes #17): `starter-kit/RECOMMENDED_SKILLS.md` §How this index is used gains a **count-threshold rule** — one recommended skill is cited inline at the point of recommendation (e.g. `DEVELOPMENT_WORKSTREAM.md` §Issue Lifecycle → `/triage`; `ARCHITECTURE_WORKSTREAM.md` §Refactor Heuristics → `/improve-codebase-architecture`), while two or more skills for one workstream are promoted to a dedicated `## Recommended Skills` section with a purpose→skill table (e.g. `AUDIT_WORKSTREAM.md`'s `/code-review`/`/review`/`/security-review`). A single-row table is heavier than the inline citation it would replace, so the section earns its overhead only at ≥2 skills; `workstreams/TEMPLATE_WORKSTREAM.md` gains a matching optional "Recommended Skills" scaffold (delete-if-one, keep-if-≥2). (3) **Cross-reference completeness Learning** (#31, closes #19): the v2.6 self-review heuristic is formalized as **Learning #7** in the `SESSION_RUNNER.md` Learnings table (appended — 1–6 unchanged) plus a Phase 3F pre-commit hook — when a change adds a citation/index/glossary/cross-reference or modifies a numbered set (FMs, principles, phases, anti-patterns, learnings), `git diff` shows only the present-side edit, so grep each cited destination and each nearby set-size claim before committing. No principle, phase, gate, workstream, or FM changes; FM count stays 26.
