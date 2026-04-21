# Methodology v2.2: Sync Tools + Multi-Project Migration Plan

**Status:** RELEASED (Part A) on 2026-04-21 (Session 366) — Phases 1–3 shipped as v2.2. Part B (§5 Phases 4–7 operator migration) remains pending.
**Date:** 2026-04-20 (plan); 2026-04-21 (Part A released)
**Owner:** methodology repo
**Release tag:** v2.2 (ships `bin/sync`, `bin/status`, updated BOOTSTRAP; universal improvements)
**Secondary scope:** user's internal 12-project migration to gitignored-mode (private operator adoption)

---

## 1. Context & Problem Statement

### 1A. What the methodology already does right (preserve)

The methodology is an open-source framework (`github.com/KJ5HST/methodology`, 1 star, 1 active fork `rmsharp/methodology`). Its **documented Quick Start** — in README.md §Quick Start — is:

1. Copy `starter-kit/SESSION_RUNNER.md`, `SAFEGUARDS.md`, `SESSION_NOTES.md`, `CHANGELOG.md`, `ROADMAP.md` into project root.
2. Copy framework files into `docs/methodology/`.
3. Add a SESSION PROTOCOL block to project's `CLAUDE.md`.
4. For updates: "tell Claude to fetch from GitHub" (documented phrasing).

This pattern is **fine for external adopters with a single project**. We do NOT break it.

### 1B. The user's problem (operator at scale)

The methodology's author runs **14 projects** following this framework. Symptoms:

- **4 drifted versions** of `methodology_dashboard.py` across projects (`fbfee851`, `bdea7b19`, `c218eb21`, `9d71de2e`).
- **≥4 variant families** of `SESSION_RUNNER.md` (clean drift, heavy customization, re-numbered, tiny customization).
- **Each methodology update requires N manual project commits** to propagate — high-friction, easy to forget, silently diverges.
- **Misdirection bug:** 8 projects lack a project-local `methodology_dashboard.py`, so the Phase 0 orient step fell back to the portfolio-level script, reporting wrong scope. This was the proximate trigger for this plan.

### 1C. What's missing in the methodology today

Three gaps — each affects external adopters AND the user:

1. **No drift-visibility tool.** Neither external adopters nor the user can easily see "my copy is N versions behind canonical."
2. **BOOTSTRAP.md describes manual copy but offers no script.** The update workflow ("tell Claude to fetch from GitHub") is agent-dependent and informal — the ham-radio-olympics project encoded this as a custom Learning row #2 because it wasn't in the methodology itself.
3. **No canonical pattern for per-project customizations.** Projects that need to extend the base methodology (adding task mappings, Phase 0 steps, Learnings) today edit the shared file, causing drift. The starter-kit offers no seam for legitimate per-project additions.

### 1D. The plan's two halves

**Part A — methodology v2.2 release (§4, §5 Phases 1-3):** universal improvements shipped to the methodology repo. Benefits external adopters AND the user.

**Part B — user's internal 12-project migration (§5 Phases 4-6):** operator-specific adoption of the new tooling in gitignored-mode. NOT part of the v2.2 release; just the user's private consequence.

---

## 2. Inventory

### 2A. Projects in scope for Part B (user's internal migration)

Excluded per user direction: **rad-con**, **hamlib** (explicit out-of-scope today).

| Project | SESSION_RUNNER.md | SAFEGUARDS.md | methodology_dashboard.py | Customizations to preserve |
|---|---|---|---|---|
| ftx1-cat | committed | committed | — | none |
| ham-radio-olympics | committed | committed | committed | Learnings row #2 (methodology-fetch-from-GitHub) |
| mark-down | committed | committed | — | none |
| Morse-Trainer | committed | committed | — | none |
| net-audio | committed | committed | — | none |
| nothamlib | committed | committed | committed | none |
| panelkit | committed | committed | — | none |
| panelkit-ui | committed | committed | — | none |
| radio-digital | committed | committed | — | none |
| radio-web | committed | committed | — | none |
| ResortApp | committed | committed | committed | 4-line SESSION_RUNNER diff (needs review) |
| wsjtx-arm | committed | committed | committed | Persona system (Contributor/Consumer) in Phase 0 steps 5-9; custom doc dirs (`docs/contributor/`, `docs/consumer/`); 8 custom Learnings rows |

### 2B. Customization patterns observed

Three legitimate categories:

1. **Learnings table extensions.** Row-additive — ham-radio-olympics #2, wsjtx-arm #2-9.
2. **Task-to-workstream mapping extensions.** wsjtx-arm adds persona branch decisions.
3. **Phase 0 step additions.** wsjtx-arm adds "Ask: Which persona" step.

Category 1 is purely additive. Categories 2-3 modify control flow.

### 2C. Methodology repo today

```
methodology/
├── CLAUDE.md                    (dev instructions for this repo)
├── README.md                    (external-facing Quick Start)
├── HOW_TO_USE.md
├── ITERATIVE_METHODOLOGY.md
├── starter-kit/                 (what adopters copy into projects)
│   ├── BOOTSTRAP.md
│   ├── CHANGELOG.md
│   ├── ROADMAP.md
│   ├── SAFEGUARDS.md
│   ├── SESSION_NOTES.md
│   ├── SESSION_RUNNER.md
│   └── methodology_dashboard.py
├── tools/
│   └── methodology_dashboard.py (byte-identical to starter-kit version; duplication is legacy)
├── workstreams/*.md
└── docs/
    ├── images/
    └── planning/                (new — this document lives here)
```

### 2D. External adopters (awareness)

- `rmsharp/methodology` fork — last push 2026-04-16. Evidently tracking starter-kit updates. Any change to the documented pattern in README.md or BOOTSTRAP.md should be backward-compatible with the manual-copy workflow they likely use.

---

## 3. Design Decisions (captured)

### 3.1 Sync tool — dual-mode, dual-source

**Tool:** `methodology/bin/sync`

**Two orthogonal axes:**

| Axis | Values | Meaning |
|------|--------|---------|
| **Mode** | `commit` (default) / `ignore` | What relationship the project has to the synced files |
| **Source** | `local` (default if sibling dir exists) / `github` | Where the canonical files come from |

**Mode semantics:**

- `--mode=commit` (default, external-friendly): copies files; does NOT touch `.gitignore`; assumes adopter will commit them. Matches README Quick Start.
- `--mode=ignore` (operator-at-scale): copies files; adds `.gitignore` entries; if files are currently tracked, prints warning with `git rm --cached` instructions (does NOT automatically execute the rm — keeps the destructive step explicit).

**Source semantics:**

- `--source=local` (default if `../methodology/starter-kit/` exists): copies from sibling methodology/ dir. Fast. Works offline.
- `--source=github`: fetches via `gh api repos/KJ5HST/methodology/contents/starter-kit/<file>` and writes locally. Required when no sibling methodology/ exists (e.g., fresh clone on a new machine, external adopters without sibling layout). This replaces the informal "tell Claude to fetch from GitHub" workflow with a script.

**Auto-detection:** If `../methodology/starter-kit/` exists, default `source=local`; otherwise default `source=github`.

### 3.2 Per-project customizations → CLAUDE.md section

**Universal pattern (promoted to starter-kit + BOOTSTRAP):**

Add a new optional section to project CLAUDE.md:

```markdown
## Project-Specific Methodology Adaptations

*Additions and overrides to the base methodology at `SESSION_RUNNER.md` and
`SAFEGUARDS.md` (synced from `methodology/`, not project-owned). The base
files govern unless explicitly overridden here.*

### Additional Phase 0 steps
(none / <list>)

### Additional task-to-workstream mappings
(none / <table rows>)

### Project-specific Learnings
(none / <table rows>)
```

Agents already read CLAUDE.md on every session. Making this section an **explicit seam** means customizations don't require editing the synced-from-canonical files.

This is universal advice and belongs in `starter-kit/BOOTSTRAP.md` and `README.md`.

### 3.3 Committed vs gitignored — it's the operator's choice

**Methodology ships both patterns as first-class.** README Quick Start shows committed mode (simple default). BOOTSTRAP.md documents both, with guidance:

- Use **committed mode** (default) if: single-project adoption, you want standalone portability, you don't mind the once-in-a-while manual update.
- Use **ignored mode** if: multi-project adoption, you're also the methodology author, you want updates to propagate via `bin/sync` from a sibling methodology/ checkout.

The user's 12 projects adopt ignored mode in Part B. External adopters default to committed mode (no change).

### 3.4 Release as v2.2

- `methodology/starter-kit/CHANGELOG.md` gets a v2.2 entry.
- `README.md` "What's New" section updated with v2.2.
- Tagged release on GitHub so external adopters (incl. rmsharp fork) see it.

---

## 4. Target State

### 4A. Methodology repo after v2.2

```
methodology/
├── CLAUDE.md
├── README.md                    (Quick Start now references bin/sync)
├── HOW_TO_USE.md
├── ITERATIVE_METHODOLOGY.md
├── starter-kit/
│   ├── BOOTSTRAP.md             (UPDATED — dual-mode workflow, customization seam)
│   ├── CHANGELOG.md             (NEW v2.2 entry)
│   ├── CLAUDE_TEMPLATE.md       (NEW — project CLAUDE.md template with the Adaptations section)
│   ├── ROADMAP.md
│   ├── SAFEGUARDS.md
│   ├── SESSION_NOTES.md
│   ├── SESSION_RUNNER.md
│   └── methodology_dashboard.py
├── bin/                         (NEW)
│   ├── sync                     (NEW — dual-mode, dual-source tool)
│   └── status                   (NEW — drift reporter)
├── tools/
│   └── methodology_dashboard.py (unchanged)
├── workstreams/*.md
└── docs/
    ├── images/
    └── planning/
        └── methodology-as-environment-plan.md  (this doc)
```

### 4B. A user project in ignored mode (e.g., `net-audio` after Part B)

Locally present, gitignored, untracked:
- `SESSION_RUNNER.md`
- `SAFEGUARDS.md`
- `methodology_dashboard.py`
- `dashboard.html` (was already gitignored)

Tracked and project-owned:
- `CLAUDE.md` — has new "Project-Specific Methodology Adaptations" section (empty for simple projects; populated for wsjtx-arm-style customizations)
- `SESSION_NOTES.md`
- Everything else project-specific

`.gitignore` additions:
```
# Methodology files (synced from ../methodology/; run ../methodology/bin/sync .)
/SESSION_RUNNER.md
/SAFEGUARDS.md
/methodology_dashboard.py
```

### 4C. An external adopter's project after v2.2 (unchanged from v2.1 shape)

Same files as today, all committed. They optionally start using `bin/sync --mode=commit --source=github` to update, or continue with the manual flow.

### 4D. `bin/sync` contract

```
methodology/bin/sync <project-path> [--mode=commit|ignore] [--source=local|github] [--dry-run]
```

Behavior:
1. Determine mode (flag or detect existing .gitignore entries → ignore; else commit).
2. Determine source (flag or auto-detect local sibling dir).
3. If `--source=github`: fetch files via `gh api` (requires `gh` installed + auth).
4. Copy `SESSION_RUNNER.md`, `SAFEGUARDS.md`, `methodology_dashboard.py` to `<project-path>/`.
5. If `--mode=ignore`: ensure `.gitignore` entries present (idempotent); if files are currently tracked, print `git rm --cached` warning but do NOT execute.
6. Print summary: source, mode, files changed, methodology version.
7. `--dry-run` prints what would happen without modifying files.

### 4E. `bin/status` contract

```
methodology/bin/status [<project-path>|<glob>]  [--source=local|github]
```

Prints a per-project table:

```
Project             Mode       SESSION_RUNNER   SAFEGUARDS   DASHBOARD
ftx1-cat            ignored    current          current      current
net-audio           ignored    current          current      current
radio-digital       ignored    1 version behind current      current
some-external-proj  committed  current          current      current
```

"current", "N versions behind", "locally modified", "missing".

### 4F. v2.2 CHANGELOG entry (draft language)

```markdown
## v2.2 — Sync tooling + customization seam

### Added
- `bin/sync` — dual-mode (commit/ignore), dual-source (local/github) sync tool. Replaces manual copy step in BOOTSTRAP.
- `bin/status` — drift reporter across projects.
- Starter-kit `CLAUDE_TEMPLATE.md` with "Project-Specific Methodology Adaptations" section template.

### Changed
- BOOTSTRAP.md: documents both committed-mode (default, single-project) and ignored-mode (advanced, multi-project author) adoption. Customization seam pattern is canonical.
- README.md §Quick Start: references `bin/sync` alongside the manual copy option.

### Notes
- Backward compatible. Existing adopters using committed-mode need not change anything.
- The internal 12-project migration at KJ5HST-LABS adopts ignored-mode — see docs/planning/methodology-as-environment-plan.md Part B.
```

---

## 5. Phased Plan

**Each phase is ONE session. Close out, commit, stop.**

### PART A — Methodology v2.2 release (universal, public)

#### Phase 1 — Build `bin/sync` and `bin/status`

**Deliverable:** Two working scripts in `methodology/bin/` (Python 3 stdlib only, matching existing tooling convention) with a tested dry-run mode.

**Scope:**
- `bin/sync` implements modes, sources, and the contract in §4D.
- `bin/status` implements the contract in §4E.
- Unit tests (even informal — shell scripts validating behavior) for:
  - commit mode + local source (baseline)
  - ignore mode + local source
  - commit mode + github source (requires `gh` auth; skip if unauthenticated)
  - dry-run doesn't modify files
  - auto-detect chooses correct source

**Verify commands:**
```bash
mkdir -p /tmp/fake-project/.git && cd /tmp/fake-project
../../Users/terrell/Documents/code/methodology/bin/sync . --mode=commit --source=local --dry-run
# Should print intent without modifying
../../Users/terrell/Documents/code/methodology/bin/sync . --mode=commit --source=local
diff SESSION_RUNNER.md /Users/terrell/Documents/code/methodology/starter-kit/SESSION_RUNNER.md
# Expect: no diff
../../Users/terrell/Documents/code/methodology/bin/status .
# Expect: all "current"
```

**Session boundary:** Tools exist, contract met, tests pass. Do NOT update BOOTSTRAP yet. Do NOT migrate projects yet. Close out.

#### Phase 2 — Update starter-kit docs + add CLAUDE_TEMPLATE.md

**Deliverable:** Documentation changes in methodology/ reflecting the new tooling and customization seam.

**Scope:**
- `starter-kit/BOOTSTRAP.md`: rewrite setup steps to show `bin/sync --mode=commit` (default) as the new baseline; document `--mode=ignore` as advanced; document customization seam.
- `starter-kit/CLAUDE_TEMPLATE.md`: new file with project CLAUDE.md template including the "Project-Specific Methodology Adaptations" section.
- `README.md` §Quick Start: keep the simple copy instruction but add "Or run: `methodology/bin/sync your-project/`" as the scripted alternative.
- `README.md` "What's New": v2.2 entry.
- `starter-kit/CHANGELOG.md`: v2.2 entry (per §4F).

**Verify:** A fresh external adopter can follow BOOTSTRAP.md end-to-end without referencing any other doc AND use either mode successfully.

**Session boundary:** Docs updated, v2.2 entries drafted (not yet tagged). Close out.

#### Phase 3 — Release methodology v2.2

**Deliverable:** Tagged v2.2 release on GitHub.

**Scope:**
- Commit Phases 1+2 work if not already committed.
- `git tag v2.2`, `git push --tags`.
- Optionally: GitHub Release with CHANGELOG entry as release notes.
- Update `docs/planning/methodology-as-environment-plan.md` status from APPROVED → RELEASED (Part A).

**Verify:** `gh release view v2.2` shows the release. rmsharp fork can fetch and see v2.2.

**Session boundary:** Methodology v2.2 is public. Close out. Part A complete.

---

### PART B — User's 12-project migration (private operator adoption)

#### Phase 4 — Pilot migration (one project)

**Deliverable:** ONE project converted to ignored-mode end-to-end.

**Pilot candidate:** `net-audio` — clean tree, no customizations, smallest surface.

**Scope:**
- `cd net-audio`
- `../methodology/bin/sync . --mode=ignore`
- `git rm --cached SESSION_RUNNER.md SAFEGUARDS.md methodology_dashboard.py` (as warned by sync)
- Commit: `methodology: externalize methodology files — synced from ../methodology/, gitignored here`.
- Verify orient step still works (run `python3 methodology_dashboard.py`, confirm local-scope report).

**Verify commands:**
```bash
git status --short     # SESSION_RUNNER/SAFEGUARDS/dashboard.py not shown (gitignored)
ls SESSION_RUNNER.md SAFEGUARDS.md methodology_dashboard.py  # all present locally
python3 methodology_dashboard.py | head -5    # reports on net-audio only
../methodology/bin/status .                    # shows "current" for all three
```

**Session boundary:** Pilot migrated + verified. Close out. Do NOT batch additional projects.

#### Phase 5 — Migrate remaining simple projects

**Deliverable:** Simple projects (no customizations) all in ignored-mode. Suggested batch size: 3-4 per session (each is ~2 min once the pattern is validated).

**Projects:** ftx1-cat, mark-down, Morse-Trainer, nothamlib, panelkit, panelkit-ui, radio-digital, radio-web (8 projects).

**Scope per project:** Same as Phase 4. Record any surprises in session notes.

**Verify:** `../methodology/bin/status *` across portfolio shows all migrated projects as "current" in ignored-mode.

**Session boundary:** After each batch. Do NOT include customized projects in this phase.

#### Phase 6 — Migrate customized projects

**Deliverable:** ham-radio-olympics, ResortApp, wsjtx-arm each migrated to ignored-mode with their customizations moved to CLAUDE.md's new "Project-Specific Methodology Adaptations" section.

**Scope per project:**
1. Extract current customizations from the project's SESSION_RUNNER.md (diff vs starter-kit).
2. Populate CLAUDE.md's new Adaptations section with the extracted content (preserving session-tagged evidence).
3. Run `bin/sync . --mode=ignore`.
4. Verify that the synced SESSION_RUNNER.md (base) + CLAUDE.md Adaptations section together reproduce the project's effective protocol.
5. `git rm --cached` and commit.

**Suggested order (simplest first):** ham-radio-olympics → ResortApp → wsjtx-arm. wsjtx-arm is the hardest (persona system + 8 Learnings + custom doc dirs).

**Verify:** agent running orient in each project sees the base protocol AND the project adaptations. Semantic equivalence to pre-migration behavior.

**Session boundary:** After each project. wsjtx-arm MUST be its own session — no batching.

#### Phase 7 — Portfolio-root consistency

**Deliverable:** Portfolio-root `~/Documents/code/CLAUDE.md` reflects the new pattern. Portfolio-root `methodology_dashboard.py` remains the portfolio-scanning variant (different from starter-kit version — preserves custom `BrogueCE-iOS` exclusion etc.).

**Scope:**
- Update portfolio CLAUDE.md's SESSION PROTOCOL section if it's inconsistent with v2.2.
- Document in portfolio CLAUDE.md that per-project sessions use `<project>/SESSION_RUNNER.md` (synced) while portfolio-level sessions use portfolio-root resources.
- Clean up any stale references to the old copy-in pattern.

**Session boundary:** Close out. Part B complete for in-scope projects.

#### Phase 8 (future, not in this plan) — rad-con + hamlib

Explicit out-of-scope today. Apply Phase 4/6 pattern when the user says go.

---

## 6. Risks & Mitigations

| # | Risk | Probability | Impact | Mitigation |
|---|------|-------------|--------|------------|
| 1 | `bin/sync` bugs cause file corruption in a consumer project | low | medium | `--dry-run` mode required in Phase 1; Phase 4 pilot exercises the real thing on one project before any others |
| 2 | External adopters on v2.1 manual flow are confused by v2.2 changes | low | low | BOOTSTRAP.md keeps simple-copy as a valid option; `bin/sync` is additive not replacing |
| 3 | `--source=github` breaks when `gh` is unauthenticated or offline | medium | low | Fall back to clear error: "run `gh auth login` or use --source=local with a sibling methodology/ checkout" |
| 4 | wsjtx-arm customization migration loses content | medium | medium | Phase 6 diffs before and after; explicit its-own-session constraint |
| 5 | rmsharp fork diverges in ways that conflict with v2.2 | low | n/a (external fork) | We own our main; fork-managed by fork author |
| 6 | Operator forgets to run `bin/sync` and project goes stale | low | low | `bin/status` surfaces it; session orient step can check (future enhancement, not in v2.2) |
| 7 | Fresh clone on new machine without `methodology/` sibling | medium | medium | `bin/sync --source=github` handles this; documented in BOOTSTRAP |
| 8 | Phase 5/6 sessions bundle multiple projects despite guidance | medium | medium | Plan explicit boundary per project; session handoff reviews check this in 3A |
| 9 | v2.2 tag pushed before Phase 2 docs complete | low | medium | Phase 3 gate requires Phase 1 AND 2 complete |

---

## 7. Open questions (resolved)

| Q | Resolution |
|---|------------|
| Bash or Python for bin tools? | **Python** — matches existing tooling convention (methodology_dashboard.py is Python stdlib-only) |
| Dual-mode or single-mode sync? | **Dual-mode** — serves external adopters AND the user |
| Announce as v2.2? | **Yes** — CHANGELOG + README "What's New" + GitHub release tag |
| Empty Adaptations sections in CLAUDE.md during Phase 5? | **No** — only populate where real customizations exist (Phase 6 projects). Template in CLAUDE_TEMPLATE.md documents the pattern. |

---

## 8. Definition of Done

### Part A — methodology v2.2 release (public)
- [ ] `methodology/bin/sync` exists, meets §4D contract, tested
- [ ] `methodology/bin/status` exists, meets §4E contract, tested
- [ ] `starter-kit/BOOTSTRAP.md` documents dual-mode + customization seam
- [ ] `starter-kit/CLAUDE_TEMPLATE.md` exists with Adaptations section
- [ ] `starter-kit/CHANGELOG.md` has v2.2 entry
- [ ] `README.md` §Quick Start references `bin/sync` + "What's New" mentions v2.2
- [ ] v2.2 tagged and pushed to GitHub
- [ ] Optionally: GitHub Release created

### Part B — user's 12-project migration (private)
- [ ] net-audio pilot complete (Phase 4)
- [ ] 8 simple projects migrated (Phase 5): ftx1-cat, mark-down, Morse-Trainer, nothamlib, panelkit, panelkit-ui, radio-digital, radio-web
- [ ] 3 customized projects migrated (Phase 6): ham-radio-olympics, ResortApp, wsjtx-arm
- [ ] Portfolio-root CLAUDE.md consistent (Phase 7)
- [ ] `../methodology/bin/status <all>` shows all 12 projects in ignored-mode, all "current"

### Out of scope (explicitly)
- rad-con, hamlib — per user direction today; handle in a future phase
- Any changes to methodology CONTENT (Phase 0-3 protocol, 23 failure modes, workstreams) — this plan is about DISTRIBUTION, not content
- Orientation-step auto-sync (agent auto-runs `bin/sync` on stale detection) — future enhancement, not in v2.2
- History rewriting in projects — the plan uses `git rm --cached` (stops tracking) not `filter-repo` (rewrites)

---

## 9. Non-goals

- Do NOT touch rad-con or hamlib in this plan's execution.
- Do NOT change methodology content (protocol, failure modes, workstream docs).
- Do NOT break the existing documented external pattern. Committed-mode remains first-class in Quick Start.
- Do NOT introduce tooling beyond `bin/sync` + `bin/status` in v2.2. Resist scope creep.
- Do NOT auto-execute `git rm --cached` from `bin/sync` — destructive operations stay explicit.
