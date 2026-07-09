# Bootstrap Guide

Set up the Iterative Session Methodology for a new project in 10 minutes.

> **Prefer to learn by doing first?** Walk the [tutorials](https://github.com/KJ5HST/methodology/tree/main/docs/tutorials) — a hands-on track that installs the framework and runs a real session step by step (against your own repo or a bundled sample project). This guide is the reference you'll come back to when setting up your own project.

---

## What You'll Have When Done

```
your-projects/                        <-- parent directory (portfolio level)
├── methodology_dashboard.py          ← Portfolio health scanner (copied from tools/)
├── dashboard.html                    ← Generated dashboard (auto-refreshes in browser)
│
├── project-a/                        <-- each project gets methodology files:
│   ├── CLAUDE.md (or equivalent)     ← Your agent instructions (see CLAUDE_TEMPLATE.md)
│   ├── SESSION_RUNNER.md             ← Cockpit checklist (synced from methodology)
│   ├── SAFEGUARDS.md                 ← Safety rails (synced from methodology)
│   ├── SESSION_NOTES.md              ← Session continuity (copied from starter kit)
│   ├── BACKLOG.md                    ← Open work items only (you create this)
│   ├── CHANGELOG.md                  ← Completed work history (copied from starter kit)
│   ├── HANDOFFS.md                   ← Durable close-out receipts (copied from starter kit)
│   ├── ROADMAP.md                    ← Feature inventory & future plans (copied from starter kit)
│   ├── methodology_dashboard.py      ← Health scanner (synced from methodology)
│   │
│   └── docs/methodology/             ← The framework (copied from parent dir)
│       ├── ITERATIVE_METHODOLOGY.md
│       ├── HOW_TO_USE.md
│       ├── README.md
│       └── workstreams/
│
├── project-b/                        <-- same structure
└── project-c/                        <-- same structure
```

---

## Two adoption modes

The methodology supports two ways to keep the synced files current in your project (`bin/sync` distributes the full corpus — the operating files at your project root and the framework under `docs/methodology/`; see the next section for the complete list):

| Mode | What it means | Best for |
|------|---------------|----------|
| **Committed** (default) | Files live at project root and are committed to your repo | Single-project adopters. Standalone portability. Infrequent updates. |
| **Ignored** | Files live at project root but are gitignored. Synced from a sibling `methodology/` checkout via `bin/sync`. | Multi-project operators (5+ projects), methodology authors/forks. Updates propagate via one command. |

Both are first-class. You can start in committed mode and migrate to ignored mode later.

---

## Setup with `bin/sync` (recommended)

If you have a local `methodology/` checkout (sibling to your projects), use the sync tool:

```bash
# Committed mode (single project, default)
../methodology/bin/sync your-project/

# Ignored mode (multi-project operator)
../methodology/bin/sync your-project/ --mode=ignore

# Preview without writing
../methodology/bin/sync your-project/ --dry-run

# Pull from GitHub if you don't have a sibling methodology checkout (requires gh CLI)
../methodology/bin/sync your-project/ --source=github
```

`bin/sync` copies the full methodology corpus into the target: the operating files (`SESSION_RUNNER.md`, `SAFEGUARDS.md`, `RECOMMENDED_SKILLS.md`, `CONTEXT_TEMPLATE.md`, `CLAUDE_TEMPLATE.md`, `BOOTSTRAP.md`, `methodology_dashboard.py`) at the project root and the framework (`ITERATIVE_METHODOLOGY.md`, `HOW_TO_USE.md`, `workstreams/`) under `docs/methodology/`, creating subdirectories as needed. `SESSION_NOTES.md`, `CHANGELOG.md`, `HANDOFFS.md`, and `ROADMAP.md` are *seeded* at the root only when absent and are never overwritten afterward — once created they are yours to edit. The complete mapping is defined once in `bin/_manifest.py`. In `--mode=ignore` it also adds `.gitignore` entries for the tracked files (not the seeded ones, which you commit) and warns (non-destructively) if any tracked file is currently tracked by git.

**Drift safety:** `bin/sync` refuses to overwrite a file that has local modifications not matching canonical or any historical version. The recommended pattern is to move per-project customizations into your CLAUDE.md's "Project-Specific Methodology Adaptations" section (see Step 5), then run sync. If you really need to discard local edits, pass `--force`.

Check status with `bin/status`:

```bash
../methodology/bin/status your-project/
../methodology/bin/status *       # across the portfolio (shell-expanded)
```

You'll see `current`, `N versions behind`, `locally modified`, or `missing` per file.

**Updating an existing project from an earlier methodology version:** re-run `bin/sync`. Prefer `--source=local` from a *full* methodology checkout — an unmodified file that matches an older canonical version is recognized as upgradable and updated cleanly with no `--force`; a shallow clone or a downloaded tarball loses that git history, so the same files look "locally modified" and are held back. Run `bin/status` first: it shows which tracked files are `N versions behind`, and it flags any seed whose *format* predates the current methodology as `present (stale format)` (with a one-line migration note beneath the table) so the format lag is surfaced rather than silent. **Seed files do not update:** because `SESSION_NOTES.md`, `CHANGELOG.md`, `HANDOFFS.md`, and `ROADMAP.md` are seeded-once and never overwritten, a project moving up from an earlier methodology keeps its existing copies — including their *format*. So if you are adopting the authoritative action-ledger `CHANGELOG.md` (methodology v3.1+) over an older changelog, `bin/status` marks it `present (stale format)` and sync leaves your file untouched **by design**: reconcile its header and per-entry format against the current `starter-kit/CHANGELOG.md` seed by hand, or — if it holds no history worth keeping — delete it and re-run `bin/sync` to reseed the current shape.

---

## Setup by manual copy (always valid)

If you don't have (or don't want) the sync tool, copy files manually:

### Step 1: Copy the Framework Files

Copy `docs/methodology/` content (`ITERATIVE_METHODOLOGY.md`, `HOW_TO_USE.md`, `workstreams/`) from the methodology repo into your project's `docs/methodology/` directory. These files are project-independent — you should not need to modify them.

### Step 2: Copy the Starter Kit Files to Project Root

From the methodology `starter-kit/` directory:

| File | Purpose |
|------|---------|
| `SESSION_RUNNER.md` | The operating procedure — every session follows this |
| `SAFEGUARDS.md` | Safety rails — commit discipline, blast radius limits, mode switching |
| `SESSION_NOTES.md` | Session continuity — where handoff notes live between sessions |
| `CHANGELOG.md` | Completed work history — add entries as work is finished |
| `HANDOFFS.md` | Durable close-out receipts — one machine-checkable block per session |
| `ROADMAP.md` | Feature inventory and future plans — what's built, what's next |
| `methodology_dashboard.py` | Health scanner — scores project health and methodology compliance |

This table is the minimum manual set. The **authoritative, complete distribution list** — which also includes `RECOMMENDED_SKILLS.md` and the `CONTEXT_TEMPLATE.md`/`CLAUDE_TEMPLATE.md` templates at the project root, plus the framework under `docs/methodology/` — is defined once in `bin/_manifest.py` and applied by `bin/sync`. Copy those too for the full set; the templates are renamed to `CONTEXT.md`/`CLAUDE.md` (see Step 5).

Run the dashboard once to generate your first report:

```bash
python3 methodology_dashboard.py
```

This generates `dashboard.html` and opens it in your browser. The page auto-refreshes every 60 seconds. Add `dashboard.html` to your `.gitignore` — it's a generated artifact.

---

## Step 3: Create Your Task Tracking Files

Create three files at your project root for tracking work:

| File | Purpose | Source |
|------|---------|--------|
| `BACKLOG.md` | Open work items only (actionable tasks) | You create this — see example below |
| `CHANGELOG.md` | Completed work history with dates | From `starter-kit/CHANGELOG.md` (template) |
| `ROADMAP.md` | Feature inventory and future plans | From `starter-kit/ROADMAP.md` (template) |

**Why three files?** A single backlog file that accumulates completed items becomes unreadable. Keeping open work, completed work, and plans in separate files means:
- `BACKLOG.md` stays scannable (agents read this at session start)
- `CHANGELOG.md` captures what was done and when (reference only, not read at session start)
- `ROADMAP.md` tracks what's built and what's planned (reference only)

When you complete work: remove it from `BACKLOG.md`, add an entry to `CHANGELOG.md`.

### Migrating an existing BACKLOG.md

If your project already has a `BACKLOG.md` that has accumulated completed items, split it:

1. Create `CHANGELOG.md` — move all completed work entries (with dates and notes) out of BACKLOG.md into reverse-chronological sections
2. Create `ROADMAP.md` — move the feature inventory ("what's built") and future plans/proposals out of BACKLOG.md
3. Trim `BACKLOG.md` — remove all completed items, struck-through entries, and historical sections. Only open/actionable work remains.
4. Update your `CLAUDE.md` (or equivalent) references to mention all three files

After the split, `BACKLOG.md` should be scannable in under a minute.

**Minimal BACKLOG.md:**

```markdown
# Backlog

## Active
- [ ] [Task 1]
- [ ] [Task 2]

## Up Next
- [ ] [Task 3]
```

---

## Step 4: Create or Update Your CLAUDE.md

Use `starter-kit/CLAUDE_TEMPLATE.md` as a starting point. It includes:

- The SESSION PROTOCOL block (required)
- A **Project-Specific Methodology Adaptations** section (optional) where per-project customizations live

If you already have a `CLAUDE.md`, add the SESSION PROTOCOL block at the top:

```markdown
## SESSION PROTOCOL — FOLLOW BEFORE DOING ANYTHING

Read and follow `SESSION_RUNNER.md` step by step. It is your operating procedure
for every session. It tells you what to read, when to stop, and how to close out.

**Three rules you will be tempted to violate:**
1. **Orient first** — Read SAFEGUARDS.md → SESSION_NOTES.md → run methodology_dashboard.py → git status → report findings → WAIT FOR THE USER TO SPEAK
2. **1 and done** — One deliverable per session. When it's complete, close out. Do not start the next thing.
3. **Auto-close** — When done: evaluate previous handoff, self-assess, document learnings, write handoff notes, commit, report, STOP.
```

**Claude Code helper.** If you don't yet have a `CLAUDE.md`, running `/init` (Claude Code built-in) scaffolds one from the project's existing structure; then paste the SESSION PROTOCOL block above into the result. If you already have a `CLAUDE.md`, skip `/init` and paste the block directly. See [`RECOMMENDED_SKILLS.md`](RECOMMENDED_SKILLS.md).

---

## Step 5: Customizations Go in CLAUDE.md, Not in Synced Files

When a project needs to extend the base methodology — add a custom task mapping, an extra Phase 0 step, a project-specific Learning — those additions go in your **CLAUDE.md "Project-Specific Methodology Adaptations" section**, not in edits to `SESSION_RUNNER.md`.

Why: edits to synced files become drift. When the methodology updates, you either merge conflicts, miss the update, or lose your customization. Keeping synced files byte-identical to canonical means updates are friction-free, and your project's additions remain visible where agents already read them (CLAUDE.md is loaded every session).

**Keep CLAUDE.md lean — extract Learnings before they crowd the budget.** That every-session load has a flip side: CLAUDE.md competes for context with the work itself, so it has a practical size budget (Claude Code targets roughly 200 lines, and an oversized memory file measurably degrades how reliably the agent follows it). The Adaptations subsections — Learnings most of all — grow with every session and have no natural cap. When CLAUDE.md starts to feel heavy (check with `/context`), move the largest growing subsection to a committed `PROJECT_LEARNINGS.md` at your project root and leave a one-line pointer that tells the agent *when* to open it, since a referenced file is read on demand, not loaded automatically — write that pointer as a plain Markdown link, not an `@`-import, which Claude Code expands into context every session and would defeat the point:

> *Project Learnings live in [`PROJECT_LEARNINGS.md`](PROJECT_LEARNINGS.md) — read it when a task resembles earlier work (a workstream or problem you've hit before).*

This is the same discipline as the three-file `BACKLOG`/`CHANGELOG`/`ROADMAP` split above: the always-read file stays scannable; the accumulated record moves to a sibling read only when relevant. `PROJECT_LEARNINGS.md` is project-owned (committed, never synced), so it needs no tooling changes. Most projects never need this — extract only when the file actually approaches its budget.

Template section (from `CLAUDE_TEMPLATE.md`):

```markdown
## Project-Specific Methodology Adaptations

*Additions and overrides to the base methodology at `SESSION_RUNNER.md` and
`SAFEGUARDS.md` (synced from `methodology/`, not project-owned). The base
files govern unless explicitly overridden here.*

### Additional Phase 0 steps
(none)

### Additional task-to-workstream mappings
(none)

### Project-specific Learnings
(none)
```

Agents read CLAUDE.md at session start, so these additions are applied on top of the base protocol.

---

## Step 6: Identify the Build Equivalent

Every project has a command that confirms the deliverable is not broken. Identify it during setup and record it in `SAFEGUARDS.md` (see "Verify the Build Equivalent"):

| Project Type | Example Command |
|---|---|
| Software (Node.js) | `npm run build && npm test` |
| Software (Rust) | `cargo build && cargo test` |
| Documentation (Quarto) | `quarto render` |
| Documentation (LaTeX) | `pdflatex && bibtex && pdflatex` |
| Data pipeline | Pipeline-specific execution command |

For **documentation projects**, also identify:

- **The rendering tool** (Quarto, LaTeX, Sphinx, etc.) and its render command
- **Bibliography files** (`.bib`) — every citation key referenced in the document must exist in the bibliography. Rendering typically catches missing citations, but only if you render after every change.
- **Cross-reference targets** — figures, tables, and section labels that other parts of the document reference. Rendering verifies these resolve.

Record the build command in `SAFEGUARDS.md` so every session knows how to verify its work.

---

## Step 7: Customize the Task Mapping Table

Open `SESSION_RUNNER.md` and review the Phase 1 task-to-workstream mapping table.

- **If your project uses the base mappings:** leave the file alone.
- **If you need project-specific mappings:** add them to CLAUDE.md's "Additional task-to-workstream mappings" subsection (see Step 5). **Do NOT edit SESSION_RUNNER.md** — it's synced from canonical, and local edits will block future syncs until you resolve the drift.

---

## Step 8: Create a Sessions Directory (Optional)

```bash
mkdir -p docs/methodology/sessions
```

This is where session output documents go if you use them. The methodology works without explicit session documents — `SESSION_NOTES.md` carries the essential continuity — but formal session documents are useful for design series and audits.

---

## Step 9: Set Up the Methodology Dashboard (Recommended)

The methodology includes a health scanner that scores projects on 5 dimensions (activity, testing, documentation, CI/CD, methodology compliance) and generates an HTML dashboard that auto-refreshes every 60 seconds.

The dashboard auto-detects its context:
- **Inside a git repo** → single-project mode (also scans git submodules as separate entries)
- **Above git repos** → portfolio mode (scans all sibling repos)

### Per-Project Setup

`methodology_dashboard.py` is already at your project root (from Step 2 or `bin/sync`). Run:

```bash
python3 methodology_dashboard.py
```

Add `dashboard.html` to your `.gitignore` (it's a generated artifact).

### Portfolio Setup

To get a portfolio-wide view across all your projects, copy `tools/methodology_dashboard.py` from the methodology repo to the **parent directory** above your repos:

```
~/projects/                          <-- put methodology_dashboard.py here
~/projects/project-a/                <-- git repo (scanned)
~/projects/project-b/                <-- git repo (scanned)
```

Both are useful — per-project dashboard when inside a project, portfolio dashboard at the parent level.

The dashboard requires only Python 3 (stdlib, no pip dependencies) and works on macOS, Linux, and Windows.

---

## Step 10: Set Up Git Hooks (Optional)

The methodology works without hooks, but a `core.hooksPath` configuration can enforce commit discipline:

```bash
git config core.hooksPath .githooks
```

**Pre-commit hooks (recommended).** A pre-commit hook that runs the project's formatter, linter, type-checker, and fast tests on staged changes catches the same defects CI catches, but at commit time instead of after the fact — shifting failures left and reducing the ratio of red CI runs to green ones. The dashboard scores CI/CD presence (workflow files exist on the remote side); pre-commit is the complementary local-side lever the dashboard does not measure. Pick a hook runner that fits your stack — `pre-commit` (Python, polyglot), Husky + lint-staged (Node), `lefthook` (Go), `cargo-husky` (Rust), Maven Spotless plugin or Gradle git-hooks plugins (JVM), or a hand-written shell script in `.githooks/pre-commit` for projects that want zero new dependencies. The methodology is intentionally tool-agnostic here; what matters is that *some* check runs before the commit, not which one. Pocock's `/setup-pre-commit` is one option for Node/Husky projects — see [`RECOMMENDED_SKILLS.md`](RECOMMENDED_SKILLS.md).

**Ledger co-staging hook (recommended).** The one hook the methodology *does* ship is narrow and single-purpose: [`.githooks/pre-commit`](https://github.com/KJ5HST/methodology/blob/main/.githooks/pre-commit) refuses a commit that changes tracked content unless `CHANGELOG.md` is co-staged — the mechanical form of the Phase 3F close-out gate (failure mode #27, "unrecorded action"). Enable it with the `core.hooksPath` line above after copying it into your `.githooks/`; bypass a single commit with `git commit --no-verify` (Phase 0 reconcile-on-read backfills anything bypassed, so the ledger stays true on the next Orient); opt out permanently by deleting `CHANGELOG.md` and recording that in `CLAUDE.md`. It never blocks a repo that has no ledger yet, and it skips merges/rebases. Details in [`SAFEGUARDS.md`](SAFEGUARDS.md) → Commit Discipline → "Ledger Co-Staging Hook."

**Close-out completeness hook (optional, agent-specific).** The ledger hook guards the *action ledger*; the harder-to-see gap is a skipped *handoff report*. The durable fix ships in `SESSION_RUNNER.md` (the Phase 3D `HANDOFFS.md` receipt + Phase 0 reconcile). For an in-session catch — before the agent falls silent — an adopter may wire their agent harness's session-end / "stop" hook to grep `HANDOFFS.md` for a trailing `status: pending` (or run the canonical-only `bin/check-handoff`, copied in) and re-prompt to finish close-out. This is a *recommendation*, not a shipped hook: it is agent-specific harness config, soft-remind not hard-block. Details in [`SAFEGUARDS.md`](SAFEGUARDS.md) → Commit Discipline → "Close-Out Completeness Hook."

**Mechanical SAFEGUARDS enforcement (optional).** [`SAFEGUARDS.md`](SAFEGUARDS.md)'s "Blast Radius Limits" table lists destructive git operations as no-exception rules, enforced textually. For mechanical enforcement of those rules — `git push --force`, `git reset --hard`, `git clean -f`, etc. blocked at runtime by a Claude Code `PreToolUse` hook — the methodology recommends Pocock's `/git-guardrails-claude-code` skill, see [`RECOMMENDED_SKILLS.md`](RECOMMENDED_SKILLS.md). The methodology ships no *blast-radius* hook of its own (that skill is the structural countermeasure for failure modes #1, eager-to-start, and #17, protocol erosion) — the only hook it ships is the narrow ledger co-staging gate above.

---

## Updating an existing project

### With `bin/sync`

```bash
../methodology/bin/status your-project/    # see what's drifted
../methodology/bin/sync   your-project/    # apply updates
```

If `status` shows `locally modified`, sync will refuse to overwrite. Extract those customizations to CLAUDE.md's Adaptations section first, then re-run sync (or pass `--force` to discard local edits).

### Without `bin/sync`

Tell your agent: *"Update methodology using https://github.com/KJ5HST/methodology"*. It will fetch the latest starter-kit files and overlay them.

---

## Customization Guide

### What to Customize Immediately

| File | What to Change |
|------|---------------|
| `CLAUDE.md` → Adaptations section | Project-specific task mappings, Phase 0 steps, Learnings |
| `SAFEGUARDS.md` | Add project-specific hard rules if needed (note: this is a synced file — extensions belong in CLAUDE.md) |
| `BACKLOG.md` | Your project's open work items |
| `ROADMAP.md` | Your feature inventory and future plans |

### What to Customize Over Time

| File | When |
|------|------|
| `CLAUDE.md` → Adaptations → Learnings | After each session — the table grows organically; when it nears CLAUDE.md's size budget, extract it to a referenced `PROJECT_LEARNINGS.md` and leave a pointer (see Step 5) |
| `CLAUDE.md` → Adaptations → Phase 0 steps | When you discover project-specific orient needs |
| Workstream documents in `docs/methodology/workstreams/` | After 2-3 sessions in a workstream — add domain-specific patterns |

### What NOT to Customize

| File | Why |
|------|-----|
| `SESSION_RUNNER.md` | Synced from canonical. Local edits block future syncs. Put additions in CLAUDE.md Adaptations. |
| `ITERATIVE_METHODOLOGY.md` | The master framework is project-independent. If you find yourself editing it, you probably need a workstream document instead. |
| `HOW_TO_USE.md` | Reference material. Read it, don't edit it. |

---

## First Session Checklist

> **Start a new session after setup.** Claude Code reads `CLAUDE.md` at session start. If you set up the methodology and say "go" in the same session, Claude will work without the protocol. Always start a fresh session before your first real task.

After setup, your first session should:

1. Agent reads `SAFEGUARDS.md`, `SESSION_NOTES.md`, `BACKLOG.md` (CHANGELOG.md and ROADMAP.md are reference docs — not required at session start)
2. Agent runs `git status`, `git log --oneline -5`
3. Agent reports findings to you
4. Agent waits for you to give a task
5. You give a task — agent identifies the deliverable and workstream
6. Agent executes the deliverable
7. Agent auto-closes: self-assesses, writes handoff notes, records the `CHANGELOG.md` ledger entry (Phase 3F, failure mode #27), commits, reports, stops

There's no previous handoff to evaluate on Session 1. Starting from Session 2, the full close-out protocol (including handoff evaluation) kicks in.

---

## Troubleshooting

**Agent skips orientation after initial setup.**
You probably set up the methodology and said "go" in the same session. Start a new session.

**Agent skips orientation and starts working immediately.**
Say: "Read SESSION_RUNNER.md. Phase 0 is mandatory."

**Agent finishes the task and starts the next one.**
Say: "1 and done. Close out."

**Agent's close-out is perfunctory (no handoff evaluation, no learnings).**
Say: "Rate the previous session on how well it prepared you for success, document what you learned, and make sure the next session is set up for success — because you will be judged as well."

**Agent writes handoff notes verbally but not to files.**
Say: "Write to files first, then summarize."

**Agent does the literal minimum of what you asked.**
Say: "What was my underlying intent? Do the complete job."

**`bin/sync` refuses with "locally modified".**
A synced file has local edits. Run the suggested `diff` command to inspect, move any custom additions to CLAUDE.md's Adaptations section, then revert the local edits or pass `--force` to discard them.

For more troubleshooting, see `HOW_TO_USE.md` § Troubleshooting.
