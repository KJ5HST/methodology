# Bootstrap Guide

Set up the Iterative Session Methodology for a new project in 10 minutes.

---

## What You'll Have When Done

```
your-projects/                        <-- parent directory (portfolio level)
├── methodology_dashboard.py          ← Portfolio health scanner (copied from tools/)
├── .claude/settings.local.json       ← Auto-run hook (optional, recommended)
│
├── project-a/                        <-- each project gets methodology files:
│   ├── CLAUDE.md (or equivalent)     ← Your existing agent instructions
│   ├── SESSION_RUNNER.md             ← Cockpit checklist (copied from starter kit)
│   ├── SAFEGUARDS.md                 ← Safety rails (copied from starter kit)
│   ├── SESSION_NOTES.md              ← Session continuity (copied from starter kit)
│   ├── BACKLOG.md                    ← Your project's task list (you create this)
│   │
│   └── docs/methodology/             ← The framework (copied from parent dir)
│       ├── ITERATIVE_METHODOLOGY.md  ← Master framework (9 principles, 6 phases)
│       ├── HOW_TO_USE.md             ← Practical guide with examples
│       ├── README.md                 ← Overview and file map
│       └── workstreams/              ← Domain-specific adaptations
│           ├── DESIGN_WORKSTREAM.md
│           ├── ARCHITECTURE_WORKSTREAM.md
│           ├── DEVELOPMENT_WORKSTREAM.md
│           ├── AUDIT_WORKSTREAM.md
│           └── TEMPLATE_WORKSTREAM.md
│
├── project-b/                        <-- same structure
└── project-c/                        <-- same structure
```

---

## Step 1: Copy the Framework Files

Copy the entire `docs/methodology/` directory (excluding `starter-kit/` and `sessions/`) into your project.

These files are project-independent. You should not need to modify them.

## Step 2: Copy the Starter Kit Files to Project Root

Copy these files from `starter-kit/` to your **project root**:

| File | Purpose |
|------|---------|
| `SESSION_RUNNER.md` | The operating procedure — every session follows this |
| `SAFEGUARDS.md` | Safety rails — commit discipline, blast radius limits, mode switching |
| `SESSION_NOTES.md` | Session continuity — where handoff notes live between sessions |
| `methodology_dashboard.py` | Health scanner — scores project health and methodology compliance |

The markdown files are templates designed to be customized. The dashboard is a standalone Python 3 script (no dependencies) that works out of the box.

Add `dashboard.html` to your `.gitignore` — it's a generated artifact.

## Step 3: Create Your BACKLOG.md

Create a `BACKLOG.md` at your project root. This is project-specific — there's no template because every project's task structure is different. At minimum, include:

```markdown
# Backlog

## Current Milestone
[What you're working toward]

## Active
- [ ] [Task 1]
- [ ] [Task 2]

## Up Next
- [ ] [Task 3]

## Done
- [x] [Completed task]
```

## Step 4: Add the Session Protocol to Your Agent Instructions

Add this block to the top of your `CLAUDE.md` (or equivalent agent instructions file):

```markdown
## SESSION PROTOCOL — FOLLOW BEFORE DOING ANYTHING

**Read and follow `SESSION_RUNNER.md` step by step.** It is your operating procedure for every session. It tells you what to read, when to stop, and how to close out.

**Three rules you will be tempted to violate:**
1. **Orient first** — Read SAFEGUARDS.md → SESSION_NOTES.md → git status → report findings → WAIT FOR THE USER TO SPEAK
2. **1 and done** — One deliverable per session. When it's complete, close out. Do not start the next thing.
3. **Auto-close** — When done: evaluate previous handoff, self-assess, document learnings, write handoff notes, commit, report, STOP.

`SESSION_RUNNER.md` documents known failure modes and their countermeasures. The protocol compensates for documented tendencies to skip orientation, skip close-out, and continue past the deliverable.
```

## Step 5: Customize the Task Mapping Table

Open `SESSION_RUNNER.md` and update the Phase 1 task-to-workstream mapping table to match your project's workstream documents. The starter version has generic examples — replace them with your actual workstream docs.

## Step 6: Create a Sessions Directory

```bash
mkdir -p docs/methodology/sessions
```

This is where session output documents go (if you use them). The methodology works without explicit session documents — `SESSION_NOTES.md` carries the essential continuity — but formal session documents are useful for design series and audits where you want a permanent record.

## Step 7: Set Up the Methodology Dashboard (Recommended)

The methodology includes a health scanner that runs at the start of every Claude Code session. It scores projects on 5 dimensions (activity, testing, documentation, CI/CD, methodology compliance) and generates an HTML dashboard.

The dashboard auto-detects its context:
- **Inside a git repo** → single-project mode (also scans git submodules as separate entries)
- **Above git repos** → portfolio mode (scans all sibling repos)

### Per-Project Setup (single-project mode)

Copy `tools/methodology_dashboard.py` to your **project root** and set up the auto-run hook:

```bash
cp <methodology-repo>/tools/methodology_dashboard.py .
```

Create or update `.claude/settings.local.json` in your project root:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "command": "python3 methodology_dashboard.py",
        "once": true
      }
    ]
  }
}
```

Add `dashboard.html` to your `.gitignore` (it's a generated artifact).

### Portfolio Setup (multi-project mode)

To get a portfolio-wide view across all your projects, copy the same file to the **parent directory** above your repos and set up the hook there:

```
~/projects/                          <-- put methodology_dashboard.py here
~/projects/.claude/settings.local.json  <-- hook here
~/projects/project-a/                <-- git repo (scanned)
~/projects/project-b/                <-- git repo (scanned)
```

You can use both — the per-project dashboard runs when you're working inside a project, and the portfolio dashboard runs when you're at the parent level.

The dashboard requires only Python 3 (stdlib, no pip dependencies) and works on macOS, Linux, and Windows.

## Step 8: Set Up Git Hooks (Optional)

The methodology works without hooks, but a `core.hooksPath` configuration can enforce commit discipline:

```bash
git config core.hooksPath .githooks
```

---

## Customization Guide

### What to Customize Immediately

| File | What to Change |
|------|---------------|
| `SESSION_RUNNER.md` | Phase 1 task-to-workstream mapping table |
| `SAFEGUARDS.md` | Add project-specific hard rules if needed |
| `BACKLOG.md` | Your project's actual tasks |

### What to Customize Over Time

| File | When |
|------|------|
| `SESSION_RUNNER.md` Known Failure Modes | When you discover new agent tendencies specific to your project |
| `SESSION_RUNNER.md` Learnings | After each session — the table grows organically |
| Workstream documents | After 2-3 sessions in a workstream — add domain-specific patterns and anti-patterns |

### What NOT to Customize

| File | Why |
|------|-----|
| `ITERATIVE_METHODOLOGY.md` | The master framework is project-independent. If you find yourself editing it, you probably need a workstream document instead. |
| `HOW_TO_USE.md` | Reference material. Read it, don't edit it. |

---

## First Session Checklist

> **Start a new session after setup.** Claude Code reads `CLAUDE.md` at session start. If you set up the methodology and say "go" in the same session, Claude will work without the protocol — it hasn't re-read `CLAUDE.md` since the session protocol block was added. Always start a fresh session before your first real task.

After setup, your first session should:

1. Agent reads `SAFEGUARDS.md`, `SESSION_NOTES.md`, `BACKLOG.md`
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
You probably set up the methodology and said "go" in the same session. Start a new session — Claude reads `CLAUDE.md` at session start, so changes made mid-session don't take effect until the next one.

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

For more troubleshooting, see `HOW_TO_USE.md` § Troubleshooting.
