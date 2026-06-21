# Tutorial 1: Setup & First Bootstrap

> **Objective:** Install the Iterative Session Methodology into a project so that every future session has an operating procedure to follow.
> **Prerequisites:** None — this is where the series starts. You need a terminal, `git`, and Python 3. New here? Read the [series index](README.md) first.
> **Time:** ~15 minutes
> **What you'll produce:** A bootstrapped project — `SESSION_RUNNER.md`, `SAFEGUARDS.md`, `SESSION_NOTES.md`, the three task-tracking files, a `CLAUDE.md` with the SESSION PROTOCOL block, and a generated dashboard — ready for its first real session in Tutorial 2.
> **Track:** Pick one and stick with it for this pass —
> **A** (your own repo): apply each step to a project you care about; the sample run is your reference.
> **B** ([sample project](sample-project/)): use the bundled todo CLI and follow along step-for-step in a throwaway sandbox.

## Why this matters

Setup is the cheapest place to make the methodology pay off and the easiest to skip. The entire self-correcting loop — orient, one deliverable, close out, score the handoff — only runs if the operating procedure is installed where the agent reads it. Fifteen minutes here is what makes session N+1 reliably better than session N. The case for why that compounding is worth it is documented, not promised:

- [The Problem](../../README.md#the-problem) and [Evidence](../../README.md#evidence) — why the methodology exists and what it changed.
- [When to Use This Methodology](../../ITERATIVE_METHODOLOGY.md#when-to-use-this-methodology) — and when not to.
- [The Self-Improvement Loop](../../ITERATIVE_METHODOLOGY.md#the-self-improvement-loop) — the compounding payoff Tutorial 2 lets you feel firsthand.

## Before you start

Confirm your toolchain, then choose where you'll install the framework.

```sh
git --version        # any recent git
python3 --version    # Python 3.8+
```

- **Track A — your own repo.** Pick a project you can practice in. So setup is trivial to undo, work on a scratch branch:
  ```sh
  cd your-project
  git switch -c methodology-practice
  ```
- **Track B — the bundled sample.** Copy the sample *out* of the methodology repo into a throwaway location, so your practice edits never touch the methodology checkout, and make it a standalone repo. Run the copy from inside your methodology checkout and capture where that checkout is — you'll point `bin/sync` at it in Step 1:
  ```sh
  # from inside your methodology checkout (wherever you cloned it):
  METH=$PWD
  cp -r docs/tutorials/sample-project ~/todo-practice
  cd ~/todo-practice
  git init -q && git add -A && git commit -qm "start: sample todo CLI"
  ```

**Checkpoint:** You're inside a git repo you're willing to throw away or revert. Track B learners: run `python -m pytest` — all tests pass. That green suite is this project's [build equivalent](../../starter-kit/SAFEGUARDS.md#verify-the-build-equivalent); you'll record it in Step 4.

## Steps

Each step is one action and its expected result. Don't skip ahead — the final step (start a fresh session) only works if the earlier ones put the protocol on disk first.

### 1. Copy the methodology files into your project

You have two ways to do this; both are first-class. The scripted path is fastest if you have a local `methodology/` checkout (Track B learners already do — it's where the sample came from). Point the command at that checkout: Track B uses the `$METH` it set in "Before you start"; Track A learners who keep the portfolio layout (projects as siblings of the checkout) can use the relative `../methodology/` form. `bin/sync` runs from the local checkout regardless of `--source` (the script must exist on disk; `--source` only changes where the *contents* are read from).

```sh
# Scripted (committed mode is the default):
"$METH"/bin/sync .            # Track B — $METH is your methodology checkout
../methodology/bin/sync .     # Track A — a sibling checkout, per the portfolio layout

# …or pull canonical contents from GitHub instead of the local checkout (needs the gh CLI):
"$METH"/bin/sync . --source=github
```

For the manual path, or the difference between committed and ignored modes, see [`BOOTSTRAP.md` §Setup with `bin/sync`](../../starter-kit/BOOTSTRAP.md#setup-with-binsync-recommended) and [§Setup by manual copy](../../starter-kit/BOOTSTRAP.md#setup-by-manual-copy-always-valid).

**Expected result:** `bin/sync` copies the **full methodology corpus** into the project — the operating files at the root (`SESSION_RUNNER.md`, `SAFEGUARDS.md`, `RECOMMENDED_SKILLS.md`, the `CONTEXT_TEMPLATE.md`/`CLAUDE_TEMPLATE.md` templates, `BOOTSTRAP.md`, `methodology_dashboard.py`) and the framework (`ITERATIVE_METHODOLOGY.md`, `HOW_TO_USE.md`, `workstreams/`) under `docs/methodology/` — and *seeds* `SESSION_NOTES.md`, `CHANGELOG.md`, and `ROADMAP.md` at the root when they're absent. The exact mapping is defined once in [`bin/_manifest.py`](../../bin/_manifest.py).
**Checkpoint:** the operating files are at your project root and the framework is under `docs/methodology/` — `ls SESSION_RUNNER.md SAFEGUARDS.md methodology_dashboard.py` and `ls docs/methodology/` both succeed.

### 2. Tell your agent to use it — the SESSION PROTOCOL block

The agent reads `CLAUDE.md` at the start of every session, so the methodology is "installed" the moment this block is the first thing in that file. Add it to your project's `CLAUDE.md` (create the file if there isn't one — Track B starts without one):

```markdown
## SESSION PROTOCOL — FOLLOW BEFORE DOING ANYTHING

Read and follow `SESSION_RUNNER.md` step by step. It is your operating procedure
for every session. It tells you what to read, when to stop, and how to close out.
```

The full block (with the three rules you'll be tempted to violate) and the `CLAUDE_TEMPLATE.md` starting point are in [`BOOTSTRAP.md` §Step 4](../../starter-kit/BOOTSTRAP.md#step-4-create-or-update-your-claudemd). If you're starting a `CLAUDE.md` from scratch, Claude Code's `/init` can scaffold one from the project structure first — then paste the block in.

**Expected result:** `CLAUDE.md` exists at the project root and opens with the SESSION PROTOCOL heading.
**Checkpoint:** The first section of `CLAUDE.md` is `## SESSION PROTOCOL — FOLLOW BEFORE DOING ANYTHING`.

### 3. Set up task tracking — the three-file split

Open work, completed history, and future plans live in three separate files so the one the agent reads at session start (`BACKLOG.md`) stays scannable. See [`BOOTSTRAP.md` §Step 3](../../starter-kit/BOOTSTRAP.md#step-3-create-your-task-tracking-files).

Step 1's `bin/sync` already *seeded* `CHANGELOG.md` and `ROADMAP.md` at your root (they're SEED files — written once, then yours to edit). `BACKLOG.md` is the one it deliberately doesn't create: it's adopter-owned, so it's the file you author here. (If you took the manual copy path instead of `bin/sync`, copy `CHANGELOG.md`/`ROADMAP.md` from `starter-kit/` per [`BOOTSTRAP.md` §Step 3](../../starter-kit/BOOTSTRAP.md#step-3-create-your-task-tracking-files).)

- **Track B:** the sample already ships a [`BACKLOG.md`](sample-project/BACKLOG.md) — that *is* your project backlog. Its first item, `F1: todo done <id>`, is exactly the feature you'll build end-to-end in Tutorial 2. Confirm the seeded `CHANGELOG.md` and `ROADMAP.md` are present.
- **Track A:** author a `BACKLOG.md` with your open items only (no completed work); `CHANGELOG.md` and `ROADMAP.md` are already at your root from Step 1.

**Expected result:** three files at the root — `BACKLOG.md` (open items only, hand-authored) plus the seeded `CHANGELOG.md` and `ROADMAP.md`.
**Checkpoint:** `BACKLOG.md` lists only actionable work and reads in under a minute; `CHANGELOG.md` and `ROADMAP.md` both exist.

### 4. Record your build equivalent

Every project has one command that confirms the deliverable isn't broken. Identify it now and record it in `SAFEGUARDS.md`'s [Verify the Build Equivalent](../../starter-kit/SAFEGUARDS.md#verify-the-build-equivalent) section, per [`BOOTSTRAP.md` §Step 6](../../starter-kit/BOOTSTRAP.md#step-6-identify-the-build-equivalent). For the sample project (Track B) it's the test suite:

```sh
python -m pytest        # the documented runner
python -m unittest      # stdlib fallback, zero dependencies
```

**Expected result:** your project's verification command is written down where every session will look for it.
**Checkpoint:** You can name your build equivalent without thinking. Track B: `python -m pytest` reports all green.

### 5. Generate the dashboard

```sh
python3 methodology_dashboard.py
```

This writes `dashboard.html` and opens it; the page auto-refreshes every 60 seconds. Add `dashboard.html` to your `.gitignore` — it's a generated artifact. See [`BOOTSTRAP.md` §Step 9](../../starter-kit/BOOTSTRAP.md#step-9-set-up-the-methodology-dashboard-recommended).

**Expected result:** a health report you can open in a browser.
**Checkpoint:** `dashboard.html` exists and your project's methodology-compliance score is no longer zero.

### 6. Stop here — then start a *fresh* session

This is the one step everyone gets wrong. The agent read `CLAUDE.md` when this session began — *before* you installed the protocol — so the procedure you just set up is not loaded in the session you set it up in. Do **not** give a real task now.

**Expected result:** setup is complete and committed; no feature work has begun.
**Checkpoint:** You have started a brand-new session (or are about to). The agent's first act in that session is to orient — read `SAFEGUARDS.md` and `SESSION_NOTES.md`, run the dashboard, check `git status`, report, and wait for you. That's [`BOOTSTRAP.md` §First Session Checklist](../../starter-kit/BOOTSTRAP.md#first-session-checklist), and it's exactly what Tutorial 2 walks through.

## Common mistakes

Cite the failure mode by number; link the list, don't paste it.
(Full list: [Known Failure Modes](../../starter-kit/SESSION_RUNNER.md#known-failure-modes).)

- **Setting up and saying "go" in the same session.** The just-installed protocol isn't loaded yet, so the agent works unguided — Phase 0 never runs. This is **FM #1 (eager to start)** in a setup costume; the countermeasure is Step 6 above — start a fresh session before your first real task.
- **Customizing by editing `SESSION_RUNNER.md` (or `SAFEGUARDS.md`).** Those edits become drift and block future `bin/sync` updates. Put project-specific mappings and steps in your `CLAUDE.md` "Project-Specific Methodology Adaptations" section instead — see [`BOOTSTRAP.md` §Step 5](../../starter-kit/BOOTSTRAP.md#step-5-customizations-go-in-claudemd-not-in-synced-files) and [§Step 7](../../starter-kit/BOOTSTRAP.md#step-7-customize-the-task-mapping-table). Keeping synced files byte-identical to canonical is the same protocol-integrity instinct that **FM #17 (protocol erosion)** guards: don't subtract from, or fork, the shared procedure.

## You produced

A bootstrapped project: the operating procedure (`SESSION_RUNNER.md`), the safety rails (`SAFEGUARDS.md`), session continuity (`SESSION_NOTES.md`), the three task-tracking files, a `CLAUDE.md` that points every session at the procedure, and a health dashboard. Nothing has run a session yet — that's the point. In Tutorial 2 you start a fresh session against this very project and take one backlog item (Track B: `F1: todo done <id>`) through all six phases to a single shipped deliverable.

## Next

→ **[Tutorial 2: Your First Session, End-to-End](T2_first_session.md)** — run one full 6-phase pass to one deliverable, with Phase 0 Orient and the Present gate front and center.
