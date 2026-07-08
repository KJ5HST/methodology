# Iterative Session Methodology

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![REUSE status](https://api.reuse.software/badge/github.com/KJ5HST/methodology)](https://api.reuse.software/info/github.com/KJ5HST/methodology)

A framework for producing high-quality software through structured, self-correcting AI agent sessions. Each session follows a fixed phase sequence, accumulates knowledge, and feeds lessons back into the process. The result: sessions compound — session 40 is dramatically better than session 10, using the same tools on the same type of work.

## The Problem

AI agents are capable but inconsistent. They skip steps, lose context between sessions, start implementing before researching, and treat speed as evidence of quality. A methodology document alone doesn't fix this — agents read it, understand it conceptually, and still skip steps. Understanding a concept and following a procedure are fundamentally different cognitive tasks.

This framework solves the problem with four layers:

| Layer | Document | Purpose |
|-------|----------|---------|
| **Cockpit checklist** | `SESSION_RUNNER.md` | Step-by-step procedure. Follow this. |
| **Flight manual** | `ITERATIVE_METHODOLOGY.md` | Theory and principles. Reference this. |
| **Mission procedures** | `workstreams/*_WORKSTREAM.md` | Domain-specific adaptations. Execute these. |
| **Campaign templates** | `workstreams/*_CAMPAIGN.md` | Multi-session campaign sequences extending a workstream. |

The checklist constrains. The manual teaches. The mission procedures specialize. Campaign templates sequence sessions across a multi-session deliverable. All four are needed.

## Evidence

Extracted from an initial 11-session UI/UX design series. Validated across 1100+ sessions spanning implementation, CI integration, plugin architecture, code review, planning, and audit work.

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
*NOTE: The absolute fastest way to use this is to tell Claude (or other service), "Use this methodology: https://github.com/KJ5HST/methodology". Claude will pull it down and put it in place for you. To update an existing project to the latest version, use the same approach: "Update methodology using https://github.com/KJ5HST/methodology".*

> **Important:** After setup completes, start a **new session** before giving Claude real work. Claude Code reads `CLAUDE.md` at session start — changes made during setup don't take effect until the next session. If you say "go" in the same session, Claude will work without the protocol.

### 1. Copy files to your project

**Option A — scripted (recommended if you have a local methodology checkout):**

```bash
../methodology/bin/sync your-project/             # committed mode (default)
../methodology/bin/sync your-project/ --mode=ignore  # or: multi-project operator mode
../methodology/bin/sync your-project/ --source=github  # or: pull from GitHub (needs gh CLI)
```

This copies the full methodology corpus into the target: the operating files (`SESSION_RUNNER.md`, `SAFEGUARDS.md`, `RECOMMENDED_SKILLS.md`, `CONTEXT_TEMPLATE.md`, `CLAUDE_TEMPLATE.md`, `BOOTSTRAP.md`, `methodology_dashboard.py`) to the project root, and the framework (`ITERATIVE_METHODOLOGY.md`, `HOW_TO_USE.md`, `workstreams/`) to `docs/methodology/`. These are kept current on every run. `SESSION_NOTES.md`, `CHANGELOG.md`, and `ROADMAP.md` are *seeded* at the root only when absent — once they exist they are yours and `bin/sync` never overwrites them. See [`starter-kit/BOOTSTRAP.md`](starter-kit/BOOTSTRAP.md) for the difference between committed and ignored modes.

**Option B — manual:**

Copy the starter-kit root-files to your project root — `SESSION_RUNNER.md`, `SAFEGUARDS.md`, `RECOMMENDED_SKILLS.md`, `CONTEXT_TEMPLATE.md`, `CLAUDE_TEMPLATE.md`, `BOOTSTRAP.md`, `methodology_dashboard.py`, plus `SESSION_NOTES.md`, `CHANGELOG.md`, and `ROADMAP.md` as starting points you then own. Copy the framework files (`ITERATIVE_METHODOLOGY.md`, `HOW_TO_USE.md`) and `workstreams/` to `docs/methodology/`. (Option A's `bin/sync` does all of this in one command.)

### 2. Tell Claude to use it

Add this to your project's `CLAUDE.md` (Claude Code reads this file at the start of every session):

```markdown
## SESSION PROTOCOL — FOLLOW BEFORE DOING ANYTHING

Read and follow `SESSION_RUNNER.md` step by step. It is your operating procedure
for every session. It tells you what to read, when to stop, and how to close out.
```

**That's it.** Claude will orient, wait for your task, execute one deliverable, and auto-close with handoff notes for the next session. Everything cascades from that one instruction — `SESSION_RUNNER.md` tells Claude to read `SAFEGUARDS.md` and `SESSION_NOTES.md`, which establish commit discipline and session continuity.

### 3. Set up task tracking

Create a `BACKLOG.md` at your project root with your current tasks and priorities — open work items only. Copy `starter-kit/CHANGELOG.md` and `starter-kit/ROADMAP.md` to your project root for completed work history and feature inventory. This three-file split keeps BACKLOG.md scannable (agents read it at session start) while preserving history in dedicated files. When you complete work, remove it from `BACKLOG.md` and add an entry to `CHANGELOG.md`. See **[`starter-kit/BOOTSTRAP.md`](starter-kit/BOOTSTRAP.md)** for migration steps if you have an existing monolithic BACKLOG.md.

### Full setup guide

See **[`starter-kit/BOOTSTRAP.md`](starter-kit/BOOTSTRAP.md)** for the complete step-by-step guide including customization, first session checklist, and troubleshooting.

### What's in the starter kit

| File | Purpose |
|------|---------|
| `BOOTSTRAP.md` | Complete setup guide, customization, troubleshooting |
| `SESSION_RUNNER.md` | Cockpit checklist template (no project-specific history) |
| `SESSION_NOTES.md` | Empty template for session continuity |
| `SAFEGUARDS.md` | Safety rails: commit discipline, blast radius limits, mode switching |
| `CLAUDE_TEMPLATE.md` | Template for project `CLAUDE.md` with SESSION PROTOCOL block and Adaptations section |
| `CONTEXT_TEMPLATE.md` | Project domain-glossary / `CONTEXT.md` template |
| `RECOMMENDED_SKILLS.md` | Index of recommended skills, cited at the relevant phase/workstream |
| `CHANGELOG.md` | Completed work history template — keeps BACKLOG.md lean |
| `ROADMAP.md` | Feature inventory and future plans template |
| `methodology_dashboard.py` | Health scanner: project scoring, risk assessment, compliance dashboard |

### Methodology Dashboard

`tools/methodology_dashboard.py` is a portfolio health scanner that turns methodology compliance into a visible, measurable signal.

**Two modes, auto-detected:**
- **Portfolio mode** — place the script in the parent directory above your repos. It discovers all sibling git repositories and scores them as a portfolio.
- **Single-project mode** — place the script inside a git repo. It scores that project and also discovers git submodules as separate entries.

**What it does:**
- **Discovers** git repositories automatically (sibling repos or submodules depending on mode)
- **Collects** metrics across 7 dimensions: git activity, file structure, tests, CI/CD, documentation, methodology compliance, dependencies
- **Scores** each project's health (0-100) across 5 weighted dimensions (activity, testing, documentation, CI/CD, methodology)
- **Assesses** risk with severity-tagged flags (critical/high/medium/low) for issues like abandonment, missing tests, no CI, large files, low velocity
- **Generates** a self-contained HTML dashboard with collapsible project cards, sortable by health/risk/name/activity
- **Prints** a color-coded terminal summary for quick at-a-glance status

**Live dashboard:** The generated HTML auto-refreshes every 60 seconds. Run the script once, open `dashboard.html` in your browser, and leave it open — it stays current as you work. Re-run the script whenever you want updated data.

Requires only Python 3 (stdlib, no dependencies). Works on macOS, Linux, and Windows.

#### Dashboard Overview

Portfolio health score, risk matrix, methodology compliance table, commit activity chart, and sortable project cards — all in a single self-contained HTML file.

![Dashboard overview showing health score, risk matrix, methodology compliance, and commit activity](docs/images/dashboard-overview.png)

#### Project Detail View

Expand any project card to see health breakdown by dimension, risk factors, git stats, code breakdown by language and category, test metrics, CI/CD status, documentation quality, dependency counts, methodology compliance checklist, and the 10 largest files.

![Expanded project detail showing health breakdown, code metrics, and methodology compliance](docs/images/dashboard-detail.png)

## Tutorials

New to the methodology? The **[tutorials](docs/tutorials/)** are a hands-on, progressive learning track — install the framework, run a real session end to end, and learn where the guardrails catch you. Each lesson has you *do* one thing against a real project (your own repo, or the bundled [sample project](docs/tutorials/sample-project/)), with a checkpoint at every step. The full track — Setup through Keeping Adopters Current (T1–T8) — is published; see the **[series index](docs/tutorials/)** for the full curriculum.

## Repository Structure

```
├── README.md                         ← You are here
├── ITERATIVE_METHODOLOGY.md          ← Master framework (9 principles, 6 phases, 12 gates)
├── HOW_TO_USE.md                     ← Practical guide with 3 worked examples
│
├── workstreams/                      ← Domain-specific adaptations and campaign templates
│   ├── DESIGN_WORKSTREAM.md          ← UI/UX design, visual design, layout
│   ├── ARCHITECTURE_WORKSTREAM.md    ← System architecture, API design
│   ├── DEVELOPMENT_WORKSTREAM.md     ← Feature implementation, bug fix campaigns
│   ├── AUDIT_WORKSTREAM.md           ← Code audits, security reviews, quality gates
│   ├── RESEARCH_DOCUMENTATION_WORKSTREAM.md ← Research papers, technical reports, regulatory analyses
│   ├── TEMPLATE_WORKSTREAM.md        ← Create your own workstream
│   ├── RESEARCH_EXHAUSTIVE_VERIFICATION_CAMPAIGN.md ← Multi-session campaign for exhaustive claim-source verification
│   ├── INHERITED_CODEBASE_FAMILIARIZATION_CAMPAIGN.md ← Multi-session campaign for taking over an unfamiliar codebase
│   └── TEMPLATE_CAMPAIGN.md          ← Create your own multi-session campaign template
│
├── starter-kit/                      ← Copy these to bootstrap a new project
│   ├── BOOTSTRAP.md                  ← Setup guide
│   ├── CLAUDE_TEMPLATE.md            ← Project CLAUDE.md template (protocol + Adaptations section)
│   ├── CONTEXT_TEMPLATE.md           ← Project domain-glossary / CONTEXT.md template
│   ├── RECOMMENDED_SKILLS.md         ← Index of recommended skills (cited by phase/workstream)
│   ├── SESSION_RUNNER.md             ← Cockpit checklist template
│   ├── SESSION_NOTES.md              ← Session continuity template
│   ├── SAFEGUARDS.md                 ← Safety rails template
│   ├── CHANGELOG.md                  ← Completed work history template
│   ├── ROADMAP.md                    ← Feature inventory & future plans template
│   └── methodology_dashboard.py      ← Health scanner (also in tools/)
│
├── docs/                             ← Tutorials and supporting docs
│   └── tutorials/                    ← Hands-on learning track + sample todo-CLI project
│
├── bin/                              ← Sync tools (v2.2+)
│   ├── sync                          ← Copy starter-kit files into a project (dual-mode, dual-source)
│   ├── status                        ← Report drift of synced files across projects
│   ├── check-links                   ← Validate relative links resolve in the adopter layout
│   ├── _manifest.py                  ← Shared (src, dest, disposition) manifest — single source of truth
│   └── tests.sh                      ← Test suite for the bin/ tooling
│
└── tools/                            ← Portfolio-level tooling
    └── methodology_dashboard.py      ← Health scanner & compliance dashboard
```

## Key Concepts

### The Session Runner

The methodology framework describes WHAT to do and WHY. In practice, it needs an operational wrapper — a cockpit checklist — that ensures the phases are actually followed. The Session Runner provides:

- **Mandatory orientation** — prevents starting work without understanding current state
- **"1 and done" rule** — prevents scope creep and quality degradation
- **Automatic close-out** — prevents skipping the self-improvement loop
- **27 known failure modes** — documents agent tendencies with specific countermeasures
- **Degradation detection** — 17 warning signs that predict protocol erosion
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
| **Research Documentation** | Research papers, technical reports, dissertations, regulatory analyses |

**Campaigns** (multi-session work patterns with reusable templates) extend a workstream when a deliverable cannot be produced in one session even after correct decomposition. Campaign templates live in `workstreams/` under the `*_CAMPAIGN.md` naming convention. See [`ITERATIVE_METHODOLOGY.md` §Multi-Session Campaigns](ITERATIVE_METHODOLOGY.md#multi-session-campaigns) and the realized example [`workstreams/RESEARCH_EXHAUSTIVE_VERIFICATION_CAMPAIGN.md`](workstreams/RESEARCH_EXHAUSTIVE_VERIFICATION_CAMPAIGN.md).

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

Developed by Terrell Deppe (KJ5HST) using Claude Code (Anthropic) during development of a commercial software product. The methodology emerged organically from an initial 11-session design series, was codified into a reusable framework, and subsequently validated across 1100+ sessions of varied work.

The framework is agent-independent — it works with any AI coding agent that supports persistent files and session-based interaction. It also works for human developers, though the Session Runner and known failure modes are specifically tuned for AI agent tendencies.

### What's New in v3.2

The **portfolio dashboard now scores document-only / research repositories fairly** instead of penalizing them for having no code to unit-test (rmsharp, [PR #50](https://github.com/KJ5HST/methodology/pull/50)). A doc-only repo previously drew 0/20 Testing and a HIGH "No test infrastructure" risk; now the dashboard detects it and reshapes the scoring. Advisory tool — nothing hard-fails.

- **Doc-only detection** — a bidirectional `.methodology-profile` marker (`doc-only` | `code`) overrides; otherwise a 200 source-LOC cap → a doc-corpus / render-toolchain check. The cap guarantees a mixed code+docs repo is never misclassified.
- **Render/Verification dimension** — when doc-only, the 2nd score slot is filled by an **honest static proxy** for render/verification *configuration* (a render toolchain + the v2.5 `pdffonts`/`fc-list`/`kpsewhich` dependency check + docs-render/link-check CI + verification artifacts); it never claims render *success*. Code-centric test risks are suppressed; the "Large files" flag is fixed to fire only on source files.
- **First functional scoring tests** — `tools/test_methodology_dashboard.py` (29 cases) wired into `bin/tests.sh`; `DASHBOARD_VERSION` → **2.8.0**.
- **No principle, phase, gate, workstream, or failure-mode change; the failure-mode count stays 27.**

### What's New in v3.1

`CHANGELOG.md` becomes a dependable cross-source **action ledger** — the authoritative record of *what was done here, ever* across backlog items, repository issues, and ad-hoc work (rmsharp, [PR #46](https://github.com/KJ5HST/methodology/pull/46)). The design's key finding: a close-out write-gate **alone** is not dependable, so the ledger rests on two mechanisms — **gate-on-write** at close-out *and* **reconcile-on-read** at orientation, which backfills anything the gate missed.

- **New failure mode #27, "Unrecorded action"** (appended; the count moves to **27 failure modes**) — a Phase 3F / Phase 6 close-out step records one dated, source-tagged entry per action (`[issue #<N>]` · `[BL-<N>]` · `[ad hoc]`), newest on top.
- **Reconcile-on-read** — Phase 0 diffs `git log` since the ledger frontier and backfills undocumented commits before new work. The self-healing backstop that makes the ledger true *when you read it*.
- **Tooling** — a dashboard ledger-lag freshness monitor (advisory only; `DASHBOARD_VERSION` → 2.7.0), a `starter-kit/CHANGELOG.md` seed recomposed to the action-ledger shape, and a shipped `.githooks/pre-commit` co-staging hook (bypassable with `--no-verify`; reconcile is the guarantee).
- **6 phases, 12 quality gates, four session types, and every workstream are unchanged** — the additions are FM #27, a Phase 0 reconcile step, and the close-out ledger step (propagated into every session-type and campaign checklist as Learning #8).

### What's New in v3.0

The methodology is now **MIT-licensed** ([#43](https://github.com/KJ5HST/methodology/issues/43), rmsharp). The bespoke source-available `LICENSE` is replaced with the verbatim standard MIT License. The major version bump marks a deliberate change to the *legal terms* — not the content: no principle, phase, gate, workstream, or failure-mode is touched, and the failure-mode count stays 26.

- **What changed legally.** MIT grants the right to use, copy, modify, merge, publish, distribute, sublicense, and **sell** — with attribution (the copyright and permission notice must be retained in copies). The previous license permitted commercial *operational* use but **forbade** selling or productizing the methodology itself; that no-resale restriction is now **intentionally dropped**. Anyone may sell the methodology or derivatives, attribution retained.
- **Why MIT.** It adds the standard `AS IS` warranty/liability disclaimer the bespoke license lacked (reducing the author's residual exposure), removes the interpretive ambiguity around "this methodology *itself*," and is instantly recognizable and GitHub-auto-detected. The trade-off — losing the no-sell guarantee — was weighed against a hardened-custom alternative (which would have closed the same two defects while keeping the restriction) and MIT was chosen by author decision.
- **Lockstep doc updates.** `LICENSE` → verbatim MIT (`Copyright (c) 2025-2026 Terrell Deppe (KJ5HST)`); `README.md` §License and the `CLAUDE.md` license line updated to match, so nothing contradicts the authoritative file.
- **Adopter impact: none mechanical.** `LICENSE` is not a `bin/sync`-distributed file, so installed projects pull no change from this release. If you redistribute or build on the methodology, you are now under MIT terms.

### What's New in v2.9

A combined release of two additive contributions that merged together ([#38](https://github.com/KJ5HST/methodology/pull/38), [#39](https://github.com/KJ5HST/methodology/pull/39), rmsharp): a hands-on **tutorial track** for newcomers, and a **reasoning-effort convention** that generalizes "match effort to the stakes" across the whole framework. No principle, phase, gate, workstream, or failure-mode changes — failure-mode count stays 26.

- **Hands-on tutorial track (#38).** A new [`docs/tutorials/`](docs/tutorials/) learning layer: a progressive, *do-one-thing-per-lesson* curriculum with a checkpoint at every step, run against your own repo or a bundled [sample todo-CLI project](docs/tutorials/sample-project/). The published **core trio** runs Setup (T1) → First Session, with a full worked transcript (T2) → Cautionary Use (T5), alongside a series index and a reusable tutorial template. The sample project intentionally leaves one feature unbuilt so a tutorial session implements it end to end. The tutorials are a **canonical-only learning aid — they are not distributed to adopter projects** by `bin/sync`, so the corpus an installed project receives is unchanged.
- **Reasoning-effort convention (#39).** The guidance to raise an agent's reasoning depth on high-stakes work — previously living only in the Research Documentation workstream — is promoted to a cross-cutting rule: the new **Matching Reasoning Effort to Stakes** section in `ITERATIVE_METHODOLOGY.md`. Set reasoning depth by the work's *blast radius × irreversibility × compounding cost* (the same risk lens Principles 3 and 9 already use); the inverse holds too, so cheap, reversible, mechanical work gets a lighter default. The rule is **agent-independent** — the brand-neutral core says *when and why*, while `RECOMMENDED_SKILLS.md` names concrete example settings as the *how*. The heavy workstreams and both campaigns cite the rule, and an anti-erosion clause keeps it from becoming a license to skip a gate: a deeper mode sharpens a phase — it never crosses a hard gate (failure mode #17).
- **Backward compatible.** Adopters absorb the reasoning-effort edits to distributed files (`ITERATIVE_METHODOLOGY.md`, `RECOMMENDED_SKILLS.md`, `SESSION_RUNNER.md`, `workstreams/*`) by re-running `bin/sync`; the tutorials are not synced and need no adopter action. These are additive — no methodology-content semantics change.

### What's New in v2.8

The first non-docs change in several releases (since v2.2's distribution tooling): `bin/sync` and `bin/status` now cover the **full methodology corpus**, not the legacy three files. Resolves the **B1** campaign — issue [#32](https://github.com/KJ5HST/methodology/issues/32) — across four contributor PRs ([#33](https://github.com/KJ5HST/methodology/pull/33)/[#34](https://github.com/KJ5HST/methodology/pull/34)/[#35](https://github.com/KJ5HST/methodology/pull/35)/[#37](https://github.com/KJ5HST/methodology/pull/37), rmsharp). No principle, phase, gate, workstream, or failure-mode changes — this is tooling.

- **The gap it closes.** `bin/sync` propagated only `SESSION_RUNNER.md`, `SAFEGUARDS.md`, and `methodology_dashboard.py`; `bin/status` inspected the same three. Every release since v2.5 also changed files *outside* that set (`RECOMMENDED_SKILLS.md`, `ITERATIVE_METHODOLOGY.md`, `workstreams/*`…), so adopters who synced "by the book" silently fell behind while `status` still reported `current` — **false confidence**.
- **Link reconciliation + `bin/check-links` (Phase 2, #33).** A distributed file's relative cross-references can't be correct in *both* the canonical repo layout and the adopter layout unless source and target are siblings in both ("the link-topology paradox"). Distributed files now author their cross-references for the **adopter** layout — extending the convention `SESSION_RUNNER.md` already followed — and a new `bin/check-links` validates every relative link against a simulated adopter tree (wired into `bin/tests.sh`). Tradeoff: those cross-boundary links resolve in an installed project but no longer when the canonical repo is browsed on GitHub.
- **Expanded `bin/sync` over a shared manifest (Phase 3, #34).** The flat three-file tuple becomes a `(src, dest, disposition)` manifest defined once in **`bin/_manifest.py`** — the single source of truth now read by `sync`, `status`, and `check-links`. `bin/sync` produces the full Option-B tree (operating files at the project root, framework under `docs/methodology/`, subdirectories created as needed) and adds a **`seed` disposition**: `SESSION_NOTES.md`, `CHANGELOG.md`, and `ROADMAP.md` are written only when absent and never overwritten afterward — even with `--force` — because once created they are the adopter's.
- **Per-file `bin/status` (Phase 4, #35).** `status` reports one row per distributed file (`Project · File · Disposition · Status`) over the shared manifest, so drift in *any* framework doc — not just the legacy three — is now visible. SEED files report `present`/`absent` only, and an absent seed is never miscounted as drift. The test suite grew from 28 to 50.
- **Checker hygiene (Phase 5, [#37](https://github.com/KJ5HST/methodology/pull/37), closes [#36](https://github.com/KJ5HST/methodology/issues/36)).** `bin/check-links --tree` now validates a real project *in place* without writing to it — adopter-owned placeholder files (`CONTEXT.md`, `CLAUDE.md`, …) are treated as allowed-absent rather than fabricated. The `--tree` mode added in Phase 3 had created up to 5 empty files in the validated tree; a Test 14 regression assertion now guards against it (suite at 51).
- **Backward compatible.** No methodology-content change; adopters pick up the full corpus by re-running `bin/sync`. Per-project customizations in `CLAUDE.md`'s Adaptations section are unaffected, locally-edited tracked files stay drift-protected, and seed files are never touched.

### What's New in v2.7.2

Docs-only dot release bundling three contributor fixes from the PR-14 review backlog — issues [#16](https://github.com/KJ5HST/methodology/issues/16), [#17](https://github.com/KJ5HST/methodology/issues/17), and [#19](https://github.com/KJ5HST/methodology/issues/19). No principle, phase, gate, workstream, or failure-mode changes.

- **Agent-level memory, named generically (#16).** `starter-kit/CONTEXT_TEMPLATE.md`'s "CONTEXT.md vs auto-memory" guidance becomes "CONTEXT.md vs **agent-level memory**" — the cross-project persistence layer is now named by what it does, not by Claude Code's brand term, with a gloss that other agents implement it under their own names (Cursor's memories, Cody's preferences). Keeps the methodology agent-independent.
- **A convention for citing skills from workstreams (#17).** `RECOMMENDED_SKILLS.md` now states the rule the docs already followed: cite **one** recommended skill inline at the point of recommendation; promote **two or more** for the same workstream to a dedicated `## Recommended Skills` section with a purpose→skill table. `TEMPLATE_WORKSTREAM.md` ships a matching optional scaffold.
- **Cross-reference completeness as Learning #7 (#19).** A new Learnings-table row plus a Phase 3F pre-commit hook codify the self-review check `git diff` can't do for you: when you add a citation or grow a numbered set (failure modes, principles, learnings…), the defect is the *missing* destination-side edit — so grep each cited destination and each nearby count claim before committing.
- **Backward compatible.** Docs-only; adopters absorb the starter-kit changes (`CONTEXT_TEMPLATE.md`, `RECOMMENDED_SKILLS.md`, `SESSION_RUNNER.md`, `TEMPLATE_WORKSTREAM.md`) via `bin/sync`.

### What's New in v2.7.1

Docs-only naming-consistency dot release resolving issue [#15](https://github.com/KJ5HST/methodology/issues/15). The methodology's two decimal-suffixed phase labels are renamed to the letter-suffix convention `SESSION_RUNNER.md` already uses, so the spec carries one consistent style for inserted sub-phases.

- **`Phase 1.5: Claim the Session` → `Phase 1B`** and **`Phase 2.5: Pre-Create Grill` → `Phase 2B`** in `ITERATIVE_METHODOLOGY.md`, each with a one-line clarifier: a letter suffix marks an *inserted bridge step* between two numbered phases — it does not subdivide a phase (there is no "Phase 1A"/"Phase 2A") and does not change the **"6 phases"** count.
- **Issue #15 scoped only Phase 2.5; the grep inventory found Phase 1.5 too** — the same "Claim the Session" step that `SESSION_RUNNER.md` and `CLAUDE.md` already call `1B`, rendered as a decimal here. Renaming only 2.5 would have left a fresh `1.5`-vs-`2B` split inside one file, so both decimals were standardized and the latent `1B`/`1.5` cross-doc inconsistency is closed in the same pass.
- **Live sites updated:** `ITERATIVE_METHODOLOGY.md` (both headers + 2 body refs), the `SESSION_RUNNER.md` task-mapping row, `RECOMMENDED_SKILLS.md` (2 sites), and 3 campaign/workstream templates (`INHERITED_CODEBASE_FAMILIARIZATION_CAMPAIGN.md`, `TEMPLATE_CAMPAIGN.md`, `RESEARCH_EXHAUSTIVE_VERIFICATION_CAMPAIGN.md`).
- **Changelog left verbatim by design.** Dated "What's New" entries below (v1.1 names `Phase 1.5`; v2.6 names `Phase 2.5`) and the frozen `docs/planning`/`docs/audits` records keep their original tokens — a changelog records what shipped under the name used at the time; this entry is the bridge.
- **Backward compatible.** No principle, phase, gate, workstream, or FM changes; the phase count is unchanged. Adopters absorb the starter-kit changes via `bin/sync`.

### What's New in v2.7

The first change to the unit of **"1 and done"** since the rule was written: one deliverable MAY now be a **verified vertical slice** — one capability end to end — under hard gates. Adopted from issues [#20](https://github.com/KJ5HST/methodology/issues/20) (model) and [#21](https://github.com/KJ5HST/methodology/issues/21) (guardrails).

- **Vertical-slice redefinition (#20).** The old "one horizontal layer per session" granularity was, in practice, a proxy for verifiability — a single sequential agent could only reliably verify a small blast radius. When a session has high-parallelism verification available, the proxy can relax *where the verification fully substitutes*. New `SESSION_RUNNER.md` §Vertical Slice Sessions defines four gates, all mandatory: **(a)** the full layer set pre-declared in a plan-mode contract before any code (a prior-session approval satisfies this; the implementing session re-verifies it at Orient); **(b)** a checkpoint commit at every layer boundary — the 5-file cap is unchanged and now explicitly *per-commit* (`SAFEGUARDS.md`); **(c)** the full build/test matrix plus exhaustive grep at *each* boundary, not once at the end; **(d)** per-surface *faithful* verification — "all tests ran" is not automatically faithful (a suite that bypasses row-level security passes a broken policy). **Evidence-gated, not self-certified:** missing per-boundary artifacts revert the session to horizontal scope at the last clean checkpoint. **Recoverability — not verifiability — is the ceiling on slice size**, and seven boundary types stay non-collapsible (irreversible migrations, operator-approval gates, plan ↔ implementation, cross-toolchain cutovers, and more). Principle 9 (Session Scope Bounding) extended to match.
- **Guardrails (#21).** New **failure mode #26 — "Mega-session masquerading as a vertical slice"** (appended; FMs 1–25 unchanged) with its own degradation-detection row: a slice is ONE capability mapped to ONE pre-declared layer list, and bundling two capabilities, two platform cutovers, or a plan + its code fails the slice test. **FM #17 (protocol erosion) gains an anti-erosion clause** — citing a "deeper dive" or any high-parallelism mode to skip an orientation, stub, or close-out step is erosion, not the model; *the allowance ADDS a gate, it removes no step*. **FM #18 (planning-to-implementation bleed) gains a discriminator** so pre-declared slices don't false-positive: implementing multiple layers of ONE pre-declared slice is not bundling.
- **Skills index restated.** The v2.6.2 forward-compatibility note is discharged: the "Phases spanned" reading guidance in `RECOMMENDED_SKILLS.md` now speaks vertical-slice vocabulary (a skill's span must stay inside the slice's declared layer set, and a span never substitutes for a contract), and the "A skill is not a phase" principle paragraph no longer presupposes the strict horizontal model.
- **Backward compatible.** The allowance is opt-in and gated; the strict horizontal "1 and done" remains the default and the fallback. No phase, gate, or workstream changes. Adopters who never declare a slice operate the methodology exactly as before.

### What's New in v2.6.2

Docs-only dot release resolving issue [#22](https://github.com/KJ5HST/methodology/issues/22) (Pocock skill enablement gap — investigation by [@rmsharp](https://github.com/rmsharp)). Strategy decided: **C (Reactive)** — enablement support happens per-request via the adopter's own `CLAUDE.md` adaptations (or `/grill-with-docs` lazy-creation), never via methodology-shipped templates, preserving *"methodology recommends; methodology does not reimplement."*

- **New "Phases spanned (compression risk)" column** on the external-skills table in `starter-kit/RECOMMENDED_SKILLS.md` — the bounding half of strategy C. Records, per skill and verbatim-verified at the pinned SHAs, which phases one invocation can cross: `/grill-with-docs` and `/improve-codebase-architecture` are flagged **high** (Phase 2 → 3 → 5 in a single invocation); `/diagnose` is medium by design (a debugging session *is* its span); the rest are low/zero. A reading-guidance paragraph tells adopters to plan the stop point before invoking a high-compression skill, cross-referencing the "A skill is not a phase" principle. The column carries an explicit forward-compatibility note: if the vertical-slice model proposed in [#20](https://github.com/KJ5HST/methodology/issues/20)/[#21](https://github.com/KJ5HST/methodology/issues/21) is adopted, it gets restated in that vocabulary.
- **`/triage` prerequisite contradiction resolved by footnote** — the skill's body recommends `/setup-matt-pocock-skills`, which this index declines. The citation stands; a prerequisite note instructs adopters to establish the issue-tracker label mapping themselves per `DEVELOPMENT_WORKSTREAM.md` §Issue Lifecycle (or accept the canonical state names as-is).
- **Backward compatible.** No principle, phase, gate, workstream, or FM changes. Issues #20/#21 (vertical-slice model + guardrails) remain open and are not prejudged by this release.

### What's New in v2.6.1

Docs-only dot release bundling four external contributions (all from [@rmsharp](https://github.com/rmsharp) — PRs [#18](https://github.com/KJ5HST/methodology/pull/18), [#23](https://github.com/KJ5HST/methodology/pull/23), [#25](https://github.com/KJ5HST/methodology/pull/25), [#27](https://github.com/KJ5HST/methodology/pull/27)).

- **Skill-citation discipline completed** (PR #18) — closes the gaps left by v2.6:
  - The two aspirational citations in `RECOMMENDED_SKILLS.md` are now real: `/init` gets an actual Claude Code helper paragraph in `BOOTSTRAP.md` Step 4 (greenfield scaffolder, with an explicit skip path for projects that already have a `CLAUDE.md`); `/fewer-permission-prompts` is dropped from the index (no natural citation site — the skill remains usable, the methodology just doesn't cite it).
  - **New principle: "A skill is not a phase"** in `ITERATIVE_METHODOLOGY.md` §Recommended Skills — a skill that pulls a session across a hard gate is failure mode #2 (keep-going) wearing a tool costume. Applies to every skill, indexed or independently installed; the methodology's gates bind every session regardless of which tools are loaded.
  - **New "Skills not recommended (and why)" subsection** in `RECOMMENDED_SKILLS.md` — 10-row table surfacing the v2.6 audit's deliberate omissions (`/to-issues`, `/to-prd`, `/tdd`-as-workflow, `/caveman`, `/zoom-out`, `/write-a-skill`, `/setup-matt-pocock-skills`, `/loop`, `/schedule`) plus two hedged post-audit entries (`/handoff`, `/prototype`), each with a one-line rationale. Closes the door on re-litigation and makes the audit decisions discoverable from the index itself.
- **Learnings-routing contradiction fixed** (PR #25, closes #24) — `SESSION_RUNNER.md` Phase 3C no longer tells adopters to edit the synced Learnings table. Dual-audience recomposition: adopter projects record learnings in their `CLAUDE.md` Adaptations section; the canonical repo appends to the seed table. The false "table starts empty" caption is corrected; `HOW_TO_USE.md` retargeted to match.
- **CLAUDE.md size budget** (PR #27, closes #26) — `BOOTSTRAP.md` Step 5 gains a size-budget rule (~200-line target) with an extract-to-`PROJECT_LEARNINGS.md` overflow valve, plus a warning to use a plain Markdown link (not an `@`-import) for the pointer so it stays read-on-demand.
- **Housekeeping** (PR #23) — `tools/__pycache__/` gitignored.
- **Backward compatible.** No principle, phase, gate, workstream, or session-type changes; no FM renumbering (count stays 25). Adopters absorb the starter-kit changes via `bin/sync`.

### What's New in v2.6

> **Methodology recommends; methodology does not reimplement.**

- **Skill-recommendation convention** — new content layer alongside phases, principles, workstreams, and campaigns. If a discipline can be expressed as a Claude Code skill (built-in like `/verify`, `/code-review`; community like Pocock's `/grill-me`, `/diagnose`), methodology cites the skill at the relevant phase or workstream instead of re-documenting the discipline in its own voice. Methodology owns *what to do and when*; skills own *how to do it*.
- **New `starter-kit/RECOMMENDED_SKILLS.md`** — canonical index of recommended skills with two tables (Pocock community skills + Claude Code built-ins). External entries include per-skill known-good commit SHAs for adopters who want to pin a verified version; Pocock entries carry a "fork for production reliance" note.
- **New `ITERATIVE_METHODOLOGY.md` §Recommended Skills** — short principle paragraph + pointer to the index. Inline citations in workstreams and `SESSION_RUNNER.md` reference skills by slash-command name without re-describing them.
- **Conceptual content distilled from a 16-skill audit** (`docs/audits/2026-05-02-mattpocock-skills-evaluation.md`):
  - **FM #25 — Horizontal slicing** appended to `SESSION_RUNNER.md` (FMs 1–24 unchanged).
  - **Phase 3F / Phase 6 step 8** gain an explicit "remove debug instrumentation before commit" gate, citing `/diagnose` for the tagged-debug-log convention.
  - **New `starter-kit/CONTEXT_TEMPLATE.md`** — project-level domain-glossary template; **Phase 2 Research gains a new step 1** ("read CONTEXT.md if present"), citing `/grill-with-docs` for maintenance.
  - **New Issue Lifecycle section in `DEVELOPMENT_WORKSTREAM.md`** — 5-state machine (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`) with transition rules, citing `/triage` for the workflow.
  - **New `Debugging Sessions` session type in `ITERATIVE_METHODOLOGY.md`** — naming + recognition only; cites `/diagnose` for the workflow.
  - **New Refactor Heuristics section in `ARCHITECTURE_WORKSTREAM.md`** — deepening + deletion-test heuristics from Ousterhout's *A Philosophy of Software Design*, citing `/improve-codebase-architecture` for the worked-session shape.
  - **New optional Phase 2.5 (Pre-Create Grill) in `ITERATIVE_METHODOLOGY.md`** + matching `SESSION_RUNNER.md` task-mapping row; cites `/grill-me` for the grill workflow.
  - **`starter-kit/BOOTSTRAP.md` Step 10** gains a tool-agnostic pre-commit hooks paragraph (cites `/setup-pre-commit` as one option) plus a mechanical-SAFEGUARDS-enforcement pointer to `/git-guardrails-claude-code`.
- **Refactor of existing content under the principle:**
  - `SESSION_RUNNER.md` §Phase 3E Runtime Smoke Test body shortened to a rule + citation of `/verify` and `/run`; intent preserved (the runtime-verify gate stays).
  - `AUDIT_WORKSTREAM.md` Light citation pass — new "Recommended Skills" callout cites `/code-review`, `/review`, `/security-review`. The 7-Dimension Audit Framework and per-phase audit framing stay as methodology-owned content.
- **Future-audit candidates flagged in release** (out of scope this release):
  - `AUDIT_WORKSTREAM.md` Medium/Heavy pass — per-phase citation audit beyond Light.
  - `RESEARCH_DOCUMENTATION_WORKSTREAM.md` — render-verification could cite `/verify`.
  - `SESSION_RUNNER.md` FM mechanical-enforcement column — depends on hook-conversion design.
  - `DEVELOPMENT_WORKSTREAM.md` citation audit beyond Issue Lifecycle.
- **Backward compatible.** No principle, phase, or quality-gate change. FM #25 appended (FMs 1–24 unchanged). Phase 2 step renumbered 1→2..7→8; the Phase 2 cross-references in `HOW_TO_USE.md` all cite by name, never by step number, so the renumber is safe. Adopters who never use the recommended skills continue to operate the methodology as written; the citations are recommendations, not hard dependencies.

### What's New in v2.5

- **Render-dependency completeness discipline** — closes the gap where rendering succeeds while the output silently uses fallback assets instead of the ones configured. Universal principle lands in `SAFEGUARDS.md` (new "Verify Render-Dependency Completeness" sub-section under "Verify the Build Equivalent"); concrete toolchain commands land in `RESEARCH_DOCUMENTATION_WORKSTREAM.md`. Resolves upstream issue [#12](https://github.com/KJ5HST/methodology/issues/12).
- **Two-tier check, by trigger:**
  - **Post-render** (e.g., `pdffonts` confirming all configured font faces actually embedded) — hard rule, part of the build-equivalent step, blocks commit on failure.
  - **Pre-render / setup** (e.g., `fc-list "<family>"` returning the expected face count; `kpsewhich` resolving per-face files) — soft prompt at Phase 0 when render-dep configuration changes.
- **Toolchain matrix gains a "Render-Dep Check" column** — per-toolchain canonical commands for Quarto, LaTeX, Sphinx, Pandoc, AsciiDoc, and (n/a) vanilla Markdown, listing static and post-render commands side-by-side.
- **New research-doc anti-pattern #20: Silent render-dependency fallback** — derived from the joy/ project's SBL BibLit case (Regular-only font, italic markup rendered as upright Latin glyphs for 47 sessions before being noticed visually). Mitigation cross-references the new toolchain column and SAFEGUARDS sub-section.
- **`RESEARCH_EXHAUSTIVE_VERIFICATION_CAMPAIGN.md` updated** — Render Verification section in the creation-mode REPORT.md template gains a render-dep completeness line so the campaign inherits the discipline.
- **Backward compatible** — no principle, phase, gate, or workstream changes; no FM renumbering; existing adopters absorb the new SAFEGUARDS sub-section via `bin/sync`. Domain-specific commands live in the research-doc workstream and only affect projects that use it.

### What's New in v2.4

- **Multi-session campaigns promoted to first-class layer** — campaign templates are now an explicit layer in the document hierarchy alongside workstreams. New section in `ITERATIVE_METHODOLOGY.md` (`§Multi-Session Campaigns`); new orientation step in `SESSION_RUNNER.md` (Phase 1 multi-session campaign check); new `workstreams/TEMPLATE_CAMPAIGN.md` skeleton.
- **Realized examples:**
  - `workstreams/RESEARCH_EXHAUSTIVE_VERIFICATION_CAMPAIGN.md` — extends the Research Documentation workstream for exhaustive primary-source verification; decomposes the work into a planning → execution → consolidation campaign. Supports creation and audit modes.
  - `workstreams/INHERITED_CODEBASE_FAMILIARIZATION_CAMPAIGN.md` — extends the Audit workstream for taking over an unfamiliar codebase; feeds the Development workstream via a prioritized backlog. Supports interview mode (departing owner available) and archaeology mode (owner gone).
- **No new principles, phases, gates, or workstreams.** The change is structural-vocabulary only: it names the campaign layer that already exists in practice and gives it a documented home.

### What's New in v2.3

Combined release covering two contributions: a new Research Documentation workstream and a SESSION_RUNNER content release distilled from a 90-session field audit of `rad-con/SESSION_RUNNER.md` (issue #6 → audit doc → issue #7). FMs 1–23 are unchanged — no canonical renumbering.

**Research Documentation workstream**

- **New `workstreams/RESEARCH_DOCUMENTATION_WORKSTREAM.md`** — adapts the methodology for research papers, technical reports, dissertations, and regulatory analyses
- **Source-corpus management procedures** — pre-flag completeness audit, WAF retrieval hierarchy, filename verification, post-hoc dedup
- **Claim-source audit pattern** — every numeric, dated, or attributed claim requires a ≤40-word quoted passage from a primary source; baseline ~22% unsupported / ~12% re-attribution rate from real-world use
- **19 documented anti-patterns** specific to research documentation, including citation drift, filename trust, premature delete on audit-flagged claims, and goal-language for constraints
- **Toolchain adaptation table** — Quarto, LaTeX, Sphinx, Pandoc, AsciiDoc, and Markdown equivalents for citation checking, render commands, cross-reference verification, and figure scripts
- **Audit Mode** — adapts the workstream's machinery for fresh-eyes review of existing research repositories; uses the `AUDIT_WORKSTREAM.md` review-session pattern with this workstream's verification checklist as audit criteria, the 19 anti-patterns as finding categories, and the claim-source map as an audit sampling instrument

**SESSION_RUNNER content release**

- **New Phase 3E: Runtime Smoke Test** — if a deliverable changes runtime behavior (startup config, service registration, plugin loading, dispatch, integration wiring), launch the application and verify before committing. "Build clean" is necessary but not sufficient. Phase numbering shifts: old 3E (Commit) → 3F, old 3F (Report and STOP) → 3G.
- **New Failure Mode #24: Build-passes-ship-it** — appended (not inserted), so existing FM numbers 1–23 are unchanged. Catches sessions that treat `mvn clean package` / `npm run build` success as runtime correctness when the deliverable is integration behavior.
- **Phase 1B framing** — added "structural control, not a suggestion" line. Mandatory close-out steps are how clean-delivery streaks don't collapse.
- **Planning Sessions anecdote** — concrete cost of skipping evidence-based inventory: a planning session missed 10+ scattered references because it never ran grep; two greps would have found them all.
- **5 new Learnings rows:**
  - #2 — Protocol discipline is perishable (14 clean sessions can collapse to 1/10 in 12 hours)
  - #3 — Plans should flag "here be dragons" areas
  - #4 — Verify plan output against completion criteria, not session duration (refined from community feedback to remove "collapse multi-session work into a single session" framing — that phrasing read as license to bend "1 and done")
  - #5 — Code review is a distinct deliverable; produce actionable plans, not vague critique
  - #6 — A plan written from memory of a file read is an assumption-level claim
- **Backward compatible.** No FM renumbering. Phase rename only affects sessions or memories that cite "Phase 3E Commit" by number — adopters should grep their memory + project notes for that string and update to "Phase 3F Commit."

### What's New in v2.2

- **`bin/sync` tool** — dual-mode (`--mode=commit` / `--mode=ignore`) and dual-source (`--source=local` / `--source=github`) sync for starter-kit files. Committed mode is the existing pattern; ignored mode is new, for multi-project operators who want methodology updates to propagate via one command from a sibling `methodology/` checkout.
- **`bin/status` tool** — drift reporter across one or many projects. Shows `current`, `N versions behind`, `locally modified`, or `missing` per synced file.
- **Drift safety** — `bin/sync` refuses to overwrite files with local modifications (not matching canonical or any historical version). Pass `--force` to override, or move customizations to CLAUDE.md's Adaptations section first.
- **`starter-kit/CLAUDE_TEMPLATE.md`** — new template for project `CLAUDE.md` files, including the **Project-Specific Methodology Adaptations** section. This is the canonical seam for per-project customizations (task mappings, Phase 0 steps, project Learnings, project failure modes) — keeping synced files byte-identical to canonical.
- **BOOTSTRAP.md rewrite** — documents committed vs ignored modes, the customization seam pattern, and the updating workflow (`bin/status` → `bin/sync`).
- **Backward compatible** — existing adopters on v2.1 who copy files manually continue to work unchanged. The scripted workflow is additive.

### What's New in v2.1

- **CHANGELOG.md and ROADMAP.md templates** — new starter-kit files that split task tracking into three focused files: BACKLOG.md (open work only), CHANGELOG.md (completed work history), ROADMAP.md (feature inventory and future plans)
- **Migration guide** — step-by-step instructions in BOOTSTRAP.md for projects with an existing monolithic BACKLOG.md
- **4 new failure modes** (#20-23): edit from memory, greenfield assumption, overwrite user edits, question-as-instruction
- **Artifact Integrity section** in SAFEGUARDS.md — read before edit, preserve user edits, verify the build equivalent
- **Build equivalent step** — new Step 6 in BOOTSTRAP.md for identifying and recording the project's verification command
- **Documentation project adaptations** — adaptation table and anti-patterns in TEMPLATE_WORKSTREAM.md, expanded audit scope in AUDIT_WORKSTREAM.md
- **Dashboard compliance updated** — methodology dashboard now checks for CHANGELOG.md and ROADMAP.md presence (6 → 8 required items)
- **Consistent references** — SAFEGUARDS.md, SESSION_RUNNER.md, and README updated to reference the three-file approach

### What's New in v2.0

- **Methodology Dashboard** — new portfolio health scanner (`tools/methodology_dashboard.py`) that scores projects on 5 dimensions (activity, testing, documentation, CI/CD, methodology compliance) and generates a self-contained HTML dashboard
- **Two scanning modes** — portfolio mode (scans sibling git repos) and single-project mode (scans the project + git submodules), auto-detected based on placement
- **Health scoring (0-100)** with 5 weighted dimensions and rule-based risk assessment (critical/high/medium/low flags)
- **Methodology compliance scoring (0-100)** — weighted checklist of required methodology items (SESSION_RUNNER, SAFEGUARDS, SESSION_NOTES, BACKLOG, docs/methodology/, workstreams/)
- **Color-coded terminal output** — at-a-glance status without opening the browser
- **Live HTML dashboard** — auto-refreshes every 60 seconds; collapsible project cards sortable by health, risk, name, or activity
- **Starter kit includes dashboard** — `starter-kit/methodology_dashboard.py` for per-project use
- **Zero dependencies** — Python 3 stdlib only, cross-platform (macOS, Linux, Windows)

### What's New in v1.2

- **Planning session discipline** — plans are deliverables, not preambles. A planning session closes out after the plan; implementation is a separate session.
- **Evidence-based inventory** — plans that involve deletion, migration, or renaming must include grep-based inventories of all affected symbols. No more assumption-based file lists.
- **Per-phase completion criteria** — every phase in a multi-phase plan must state what DONE looks like, verification commands, and an explicit session boundary.
- **Plan-mode exit trap** — explicit warning that Plan Mode's "Implement the following plan" preamble does NOT mean start coding. The plan is a draft until evidence-verified.
- **2 new failure modes** (#18-19): planning-to-implementation bleed, plan-mode bypass
- **2 new degradation detection signs** for planning discipline violations
- **Planning Session Checklist** — 5-item verification before closing a planning session
- **Learnings table** added to Session Runner — institutional memory that grows with each session

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

Iterative Session Methodology — Copyright © 2025-2026 Terrell Deppe (KJ5HST)

Licensed under the [MIT License](LICENSE). You are free to use, copy, modify, merge, publish, distribute, sublicense, and sell copies of this methodology, provided that the above copyright notice and the permission notice are retained in all copies or substantial portions.

The methodology is provided "as is", without warranty of any kind. See the [`LICENSE`](LICENSE) file for the authoritative text.
