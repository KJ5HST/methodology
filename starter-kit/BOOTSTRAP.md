# Bootstrap Guide

Set up the Iterative Session Methodology for a new project in 10 minutes.

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

The methodology supports two ways to keep synced files (`SESSION_RUNNER.md`, `SAFEGUARDS.md`, `methodology_dashboard.py`) in your project:

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

`bin/sync` copies `SESSION_RUNNER.md`, `SAFEGUARDS.md`, and `methodology_dashboard.py` into the target. In `--mode=ignore` it also adds `.gitignore` entries and warns (non-destructively) if any of those files are currently tracked by git.

**Drift safety:** `bin/sync` refuses to overwrite a file that has local modifications not matching canonical or any historical version. The recommended pattern is to move per-project customizations into your CLAUDE.md's "Project-Specific Methodology Adaptations" section (see Step 5), then run sync. If you really need to discard local edits, pass `--force`.

Check status with `bin/status`:

```bash
../methodology/bin/status your-project/
../methodology/bin/status *       # across the portfolio (shell-expanded)
```

You'll see `current`, `N versions behind`, `locally modified`, or `missing` per file.

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
| `ROADMAP.md` | Feature inventory and future plans — what's built, what's next |
| `methodology_dashboard.py` | Health scanner — scores project health and methodology compliance |

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

---

## Step 5: Customizations Go in CLAUDE.md, Not in Synced Files

When a project needs to extend the base methodology — add a custom task mapping, an extra Phase 0 step, a project-specific Learning — those additions go in your **CLAUDE.md "Project-Specific Methodology Adaptations" section**, not in edits to `SESSION_RUNNER.md`.

Why: edits to synced files become drift. When the methodology updates, you either merge conflicts, miss the update, or lose your customization. Keeping synced files byte-identical to canonical means updates are friction-free, and your project's additions remain visible where agents already read them (CLAUDE.md is loaded every session).

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
| `CLAUDE.md` → Adaptations → Learnings | After each session — the table grows organically |
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
7. Agent auto-closes: self-assesses, writes handoff notes, commits, reports, stops

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
