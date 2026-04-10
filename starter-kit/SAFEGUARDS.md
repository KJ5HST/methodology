# Safeguards

Hard rules for development safety. When this file and other guidance conflict, this file wins.

---

## The Two-Mode Problem

AI agents operate well in two distinct modes:

1. **Engineer Mode** — Narrow focus. Implement a specific feature, fix a specific bug, write a specific test. Head down, executing against a clear spec.
2. **Architect Mode** — Broad focus. Analyze the codebase, plan a feature, evaluate tradeoffs, design an approach. Head up, surveying the landscape.

**The danger zone is the transition between these modes.** When the agent is mid-implementation and "notices" something that could be improved, refactored, or redesigned — and acts on it without stopping — that's where catastrophic failures originate. The engineer picks up the architect's pen without putting down the wrench.

### The Rule

**Never switch modes without a commit boundary.**

- If you're in Engineer Mode and see something that needs Architect Mode thinking: **commit your current work first**, then switch.
- If you're in Architect Mode and want to start implementing: **get explicit approval first**, then switch.
- If you catch yourself thinking "while I'm at it..." or "I also noticed..." — that's the mode switch happening. **Stop. Commit. Ask.**

---

## Pre-Flight Checklist (Before Any Multi-File Change)

Run this before touching more than one file:

```
1. git status                    — What's the current state?
2. git diff                      — Any uncommitted changes?
3. Commit everything clean       — No exceptions. Commit BEFORE starting.
4. Verify the build passes       — Don't start from a broken state.
5. State your scope explicitly   — "I am changing X, Y, Z. Nothing else."
```

If there are uncommitted changes from a previous session, **do not touch them**. Report them to the user and ask how to proceed.

---

## Blast Radius Limits

### Hard Rules (No Exceptions)

| Rule | Why |
|------|-----|
| **Commit before any multi-file change** | Every disaster becomes a `git checkout` instead of a multi-hour recovery |
| **Never touch more than 5 files without committing first** | Forces incremental, recoverable progress |
| **Never refactor across module boundaries without plan mode** | Cross-module refactoring is Architect Mode work, period |
| **Never delete a file without verifying it's committed** | `git log --oneline -- <file>` before `rm`. No shortcuts. |
| **Never rename/move files as part of a "quick fix"** | Renames cascade. They are never quick. |
| **"Refactoring" always requires plan mode approval** | Refactoring is not a "just do it" activity. Ever. |

### Scope Creep Red Flags

If any of these phrases appear in the agent's reasoning, it must stop and commit before proceeding:

- "While I'm at it..."
- "I also noticed..."
- "It would be cleaner to..."
- "This is a good opportunity to..."
- "Let me also fix..."
- "This should really be..."

These phrases signal a mode switch is happening. The correct response is: **commit current work, then discuss the new scope with the user.**

---

## Session Recovery Protocol

**After any session crash, model upgrade, or fresh start, follow this checklist IN ORDER before taking any action:**

### Step 1: Orient (Read Only — Change Nothing)
```
1. Read SESSION_NOTES.md          — What was the last session doing?
2. Check GitHub Issues (`gh issue list`) — What are the current priorities? (Fall back to BACKLOG.md if no repo. BACKLOG.md should contain only open work items — for history see `CHANGELOG.md`, for feature inventory see `ROADMAP.md`.)
3. Read SAFEGUARDS.md             — Refresh the rules (this file)
4. git status                     — What's committed? What's not?
5. git log --oneline -10          — What were the recent commits?
6. git diff --stat                — What's changed but uncommitted?
```

### Step 2: Report (Tell the User What You See)
```
- "Here's the state I found: [summary]"
- "These files are uncommitted: [list]"
- "The last session was working on: [X]"
- "Build status: [passing/failing/unknown]"
```

### Step 3: Get Direction (Ask, Don't Assume)
```
- "Should I commit the uncommitted changes?"
- "Should I continue where the last session left off?"
- "Should I start fresh on something else?"
```

**NEVER resume work from a previous session without completing all three steps.** A new session does not inherit the judgment or context of the previous one. It must verify everything from scratch.

---

## Commit Discipline

### When to Commit

| Situation | Action |
|-----------|--------|
| Before starting any new task | Commit current state clean |
| After completing any task | Commit immediately |
| Before any refactoring | Commit current state clean |
| Every 15-20 minutes of active work | Checkpoint commit |
| Before switching between modules | Commit current module's changes |
| Before any file deletion or rename | Commit + verify |
| When you feel the urge to "clean up" adjacent code | Commit first, then discuss |

### Commit Message Format
- Feature work: `feat: [description]`
- Bug fixes: `fix: [description]`
- Checkpoint commits: `checkpoint: [what's done so far]`
- WIP commits: `[WIP] [what you're in the middle of]`

**Checkpoint and WIP commits are not optional luxuries. They are safety nets.**

---

## What the User Should Do

### Honest Feedback for the Operator

**The agent works best when you:**

1. **Give narrow, specific tasks.** "Add a login form to the dashboard" is perfect. "Clean up the frontend" is a disaster waiting to happen.

2. **Demand commits before scope expansion.** When the agent says "I also noticed X needs fixing," your response should be: "Commit what you have first." Every time.

3. **Don't leave the agent unsupervised on broad tasks.** If you're stepping away, give a bounded task with a clear definition of done.

4. **Watch for scope creep language.** "While I'm at it" and "it would be cleaner to" are red flags. Interrupt and redirect.

5. **Use plan mode as a hard gate.** If the agent wants to change the approach or redesign something, make it go through plan mode. Don't let it plan and execute in the same breath.

6. **Set explicit session boundaries.** "This session, only work on X. Nothing else." This gives the agent permission to ignore the things it "notices" and stay focused.

7. **After a session crash or model upgrade, expect the orientation step.** The agent should report what it sees before doing anything. If it jumps straight into action, say "Read SAFEGUARDS.md and orient first."

8. **Trust but verify.** After the agent says it committed, check `git log`. After the agent says tests pass, check the output. Trust is rebuilt through verification, not promises.

### Signs the Agent Is Going Off the Rails

| Warning Sign | What's Happening | Your Response |
|-------------|------------------|---------------|
| Multiple files changing across modules | Scope creep | "Commit now. What's your scope?" |
| "I noticed we could improve..." | Mode switch mid-task | "Stay on task. Note it for later." |
| Long silence followed by large diffs | Unsupervised refactoring | "Show me git status right now." |
| Recovering from its own errors | Compounding mistakes | "Stop. Show me what happened. Don't fix anything yet." |
| "This is almost done, just need to..." | Sunk cost fallacy | "Commit what works. We'll evaluate." |

---

## Recovery From Disaster

If the agent has made a mess (failed refactoring, deleted files, broken state):

### Step 1: STOP
Do not let the agent try to fix its own mess. Compounding errors is the #1 cause of data loss.

### Step 2: Assess
```
git status
git log --oneline -20
git stash list
git reflog (for recovering lost commits)
```

### Step 3: Decide Together
- Can we `git checkout` to a known good state?
- Do we need to cherry-pick specific commits?
- Is there uncommitted work worth saving?

### Step 4: Never Let It Happen Again
- What safeguard was skipped?
- Add it to this document if it's not already here.
