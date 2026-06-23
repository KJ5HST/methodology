# Tutorial 7: Portfolio & Dashboard Ops

> **Objective:** Zoom out from one project to many — run the health dashboard in **portfolio mode** across every repo at once, read the risk matrix and the methodology-compliance grid, and turn the picture into a single decision: *where your next session goes.*
> **Prerequisites:** [Tutorial 6: Multi-Session Campaigns](T6_campaigns.md) — you've now run a full arc on **one** project (install in T1, sessions in T2–T3, an audit and a custom workstream in T4, a campaign in T6). This tutorial is the first to operate *above* a single project. New here? Start at the [series index](README.md).
> **Time:** ~20 minutes
> **What you'll produce:** A generated **portfolio `dashboard.html`** covering two or more projects, and a one-line, evidence-backed allocation decision — *"next session → project X, because dimension Y is red,"* or the equally valid *"leave project Z alone; it shouldn't run the methodology at all."*
> **Track:** Pick one and stick with it for this pass —
> **A** (your own repos): point the scanner at the parent directory above the projects you actually maintain and read your real portfolio.
> **B** ([sample project](sample-project/)): stand up a two-repo portfolio — your Tutorial 1–6 sample (high compliance) beside a bare, un-adopted second repo (zero compliance) — and let the contrast drive the decision.

## Why this matters

Every tutorial so far lived *inside* one project — install it, run sessions in it, audit it, run a campaign across it. But the people who get the most from this methodology run it across a *portfolio*: a dozen repos in different states of health, only some of which should even be using the framework. At that scale "which project needs me next?" stops being answerable from memory. The [methodology dashboard](../../README.md#methodology-dashboard) exists to answer it — it *"turns methodology compliance into a visible, measurable signal"* across every repo at once, so you spend scarce session capacity where it pays off instead of where it's top of mind.

- [§Methodology Dashboard](../../README.md#methodology-dashboard) — what the scanner is and its **two auto-detected modes** (per-project vs. portfolio); the seven metric dimensions and the five weighted health scores.
- [Dashboard Overview](../../README.md#dashboard-overview) and [Project Detail View](../../README.md#project-detail-view) — the portfolio summary, the risk matrix, the compliance table, and what expanding a single project card shows.
- [When to Use / When Not to Use](../../README.md#when-to-use--when-not-to-use) and [When to Use This Methodology](../../ITERATIVE_METHODOLOGY.md#when-to-use-this-methodology) — because the dashboard surfaces *candidates*, and deciding which ones deserve the methodology (and which emphatically don't) is the actual skill.

This tutorial does not restate the dashboard's metrics, scoring formula, or risk thresholds — they live in [§Methodology Dashboard](../../README.md#methodology-dashboard), one source of truth. It makes you *run portfolio mode once* and convert the picture into one allocation decision, the move every single-project tutorial has been building toward.

## Before you start

In [Tutorial 1](T1_setup.md#5-generate-the-dashboard) you ran `methodology_dashboard.py` from *inside* your project — that's **single-project mode**, and it scored that one repo. Portfolio mode is the same scanner with the same command; the only thing that changes is **where the script sits**: in the parent directory *above* your repos, where it auto-detects that it isn't itself in a git repo and scans the siblings instead. To see a portfolio you need at least two sibling git repos.

```sh
# Track B — from the parent directory that holds your Tutorial 1–6 sample (e.g. ~ if the sample is ~/todo-practice):
ls todo-practice/SESSION_RUNNER.md          # your adopted sample is here, a git repo with high compliance
# create a second project that has NOT adopted the methodology, beside the first:
mkdir throwaway-script && ( cd throwaway-script && git init -q && \
  printf 'print("hi")\n' > main.py && git add . && git commit -qm "init" )
cp todo-practice/methodology_dashboard.py .  # T1's bin/sync put the scanner at the sample root; lift a copy up one level
```

**Checkpoint:** Your parent directory holds **two or more sibling git repos** and a copy of `methodology_dashboard.py`, and the parent directory is **not itself a git repo** (run `ls .git` here and expect "No such file" — that's what makes the scanner pick portfolio mode). Track B: you can see `todo-practice/`, `throwaway-script/`, and `methodology_dashboard.py` side by side.

## Steps

Each step is one action. Steps 1–2 *generate* the portfolio view, Step 3 *reads* it, Step 4 turns it into the one decision that is the deliverable, and Step 5 makes the score something you steer by over time. Don't skip ahead.

### 1. Confirm the portfolio shape — two projects in two different states

The teaching contrast is the point, so look before you run. Your sample project has been through six tutorials: it has `SESSION_RUNNER.md`, `SAFEGUARDS.md`, `SESSION_NOTES.md`, `BACKLOG.md`, `CHANGELOG.md`, `ROADMAP.md`, and `docs/methodology/` — the kind of files the [methodology-compliance checklist](../../README.md#methodology-dashboard) scores, plus a green test suite and a history of real commits. The throwaway repo has one file and one commit and *none* of that. One repo is the methodology working as designed; the other is a project that has never heard of it.

**Expected result:** You can state, before running anything, that the sample should score high on compliance and *clearly lower risk* than the throwaway — though even the adopted sample isn't spotless (it ships no CI, an honest medium flag) — while the throwaway is the reverse on every dimension.
**Checkpoint:** You know which repo is the "adopted" one and which is the "cold" one — so when the dashboard agrees with you, you'll trust it, and when it surprises you, you'll look closer.

### 2. Run portfolio mode — one command, the whole portfolio

From the parent directory, run the exact command from Tutorial 1 — only the *location* differs:

```sh
python3 methodology_dashboard.py        # same command as T1 §5; run from the PARENT dir → portfolio mode
```

Because the working directory isn't a git repo, the scanner [auto-detects portfolio mode](../../README.md#methodology-dashboard), discovers every sibling git repo, scores each, and aggregates them. It prints a color-coded portfolio summary to the terminal and writes a single self-contained `dashboard.html` (the same generated artifact you `.gitignore`d in T1 — leave it open and it auto-refreshes every 60 seconds).

**Expected result:** The terminal lists **two projects**, each with a health score out of 100, a worst-risk level, and an activity state — *not* a single-project readout. `dashboard.html` is written and opens.
**Checkpoint:** The terminal summary shows ≥2 projects and a portfolio-level health line. If it shows only one, the scanner picked single-project mode — you're running it from inside a repo; move up to the non-git parent and re-run.

### 3. Read the risk matrix and the compliance grid — find where attention is owed

Open `dashboard.html` and read it top-down, the way it's meant to be read ([Dashboard Overview](../../README.md#dashboard-overview)): the portfolio summary bar, then the **risk matrix** (projects bucketed critical / high / medium / low / healthy), then the **methodology-compliance table** (each project's checklist and percentage). Expand the throwaway repo's card ([Project Detail View](../../README.md#project-detail-view)) to see *which* dimensions are red — you'll find 0% methodology compliance, no tests, no CI, no README.

| | Your sample (adopted) | The throwaway (cold) |
|---|---|---|
| Methodology compliance | high — the checklist is satisfied | **0%** — none of the files exist |
| Testing | a real, green suite | none |
| Risk bucket | **medium** — one honest `No CI/CD` flag, far healthier than the cold repo | **high** — 0% methodology, no tests, no CI |

Notice the sample isn't spotless — its worst risk is **medium**, not healthy: it ships no CI workflow, and the card will show a couple of other honest gaps. That's the dashboard working as intended — it surfaces a real shortfall even in your well-tended project, which is exactly why you read the *named dimensions* rather than a single color.

**Expected result:** You can name each project's health/100, its worst-risk bucket, and its compliance %, and point at the specific red dimensions on the cold repo's card.
**Checkpoint:** You can say *why* the dashboard ranks one repo riskier than the other in terms of named dimensions — not "it looks worse," but "0% methodology, zero tests, no CI." The dashboard turned a vibe into evidence.

### 4. Turn the picture into ONE decision — and don't adopt everywhere it shows red

The dashboard is a decision *input*, not a trophy. Its output for you is a single sentence: which project gets your next session, and why. But here is the judgment the red doesn't make for you — **a project scoring 0% compliance is not automatically a project that needs the methodology.** If the throwaway is a one-off script you'll run twice and delete, its 0% is the *correct* score and the right next action is *nothing*: forcing the framework onto one-off, trivial, or exploratory work is the inverse waste the canonical guidance warns against ([README §When to Use / When Not to Use](../../README.md#when-to-use--when-not-to-use); [§When to Use This Methodology](../../ITERATIVE_METHODOLOGY.md#when-to-use-this-methodology)). So the decision has two honest forms:

- *"Next session → bootstrap the throwaway (run [Tutorial 1](T1_setup.md) on it), because it's real, repeated work sitting at high risk and 0% compliance."* — the dashboard found a genuine gap.
- *"No methodology for the throwaway — it's a one-off; 0% is the right score and the dashboard is working."* — the dashboard found a non-problem, and you said so.

Reading the dashboard to reach this is cheap and fully reversible — the **lighter default** the [Matching Reasoning Effort to Stakes](../../ITERATIVE_METHODOLOGY.md#matching-reasoning-effort-to-stakes) rule reserves for low-blast-radius work. The deep reasoning belongs to the session this decision *sends you into* — especially if the dashboard points at work big enough to need the [campaign](T6_campaigns.md) you ran in Tutorial 6, whose planning session runs at your deepest tier.

**Expected result:** One written sentence naming a project, a dashboard dimension as its evidence, and a When-to-Use verdict — either "bootstrap it" or "leave it."
**Checkpoint:** Your decision cites a *named dimension* (compliance %, risk bucket, activity) and reflects a deliberate When-to-Use call. If your instinct was "adopt the methodology on every repo that showed red," you just caught yourself — that's the mistake Step 4 exists to prevent.

### 5. Keep the score honest over time — re-run, and watch it move for the right reason

A health score is longitudinal, not a one-time readout. If your decision was "bootstrap the throwaway," do it and re-run the scanner: its methodology dimension climbs off zero as the real files arrive, exactly as your sample's did across T1–T6. That moving compliance line — backed by sessions actually run — is the portfolio-scale cousin of the handoff ratchet from [Tutorial 3](T3_compounding_loop.md). What it is *not* is a number to inflate: the compliance dimension scores the *presence* of files, so you could bump it by touching empty `SESSION_RUNNER.md` stubs without running a single disciplined session. That's a vanity metric that hides drift — watch the [trend](../../starter-kit/SESSION_RUNNER.md#degradation-detection), not the snapshot.

**Expected result:** You understand the compliance score as a signal you act on across sessions, and you can distinguish an honest rise (sessions run; files that exist because they're used) from a gamed one (empty stubs created to move the number).
**Checkpoint:** You can describe what would make a project's methodology score rise *honestly* versus *dishonestly* — and you'd trust only the first.

## Common mistakes

Cite the failure mode by number; link the list, don't paste it.
(Full list: [Known Failure Modes](../../starter-kit/SESSION_RUNNER.md#known-failure-modes).)

- **Mistaking a high compliance score for a well-run project.** The methodology dimension scores file *presence* — `SESSION_RUNNER.md`, `SAFEGUARDS.md`, `SESSION_NOTES.md`, `BACKLOG.md`, `docs/methodology/`. You can satisfy the checklist with empty stubs and never run a disciplined session: the score is necessary, not sufficient. A number you *maintain* in place of a discipline you *practice* is exactly how a 9/10 chain slides to 1/10 — **FM #17 (protocol erosion)**; the countermeasure is to read the [trend](../../starter-kit/SESSION_RUNNER.md#degradation-detection), not a single green snapshot.
- **Adopting the methodology everywhere the dashboard shows red.** A one-off or throwaway repo *should* score 0% — that's the scanner working, not a backlog item. Forcing the framework onto work it doesn't fit produces ceremony with no payoff; the canonical guidance names exactly when **not** to adopt ([README §When to Use / When Not to Use](../../README.md#when-to-use--when-not-to-use), [§When to Use This Methodology](../../ITERATIVE_METHODOLOGY.md#when-to-use-this-methodology)).
- **Confusing single-project and portfolio mode.** Run the scanner inside a repo and it scores that one project (and its submodules); run it from the parent directory above your repos and it scores them as a portfolio. If you expected the whole portfolio and got one project — or the reverse — check where the script is sitting; the [two modes are auto-detected by location](../../README.md#methodology-dashboard).
- **Generating the dashboard and never acting on it.** A health report you read and forget is a vanity metric. The deliverable of a portfolio pass is a *decision* — which project gets the next session, or the explicit verdict that one shouldn't — not the HTML file.

## You produced

A real portfolio: a generated `dashboard.html` scoring two or more projects at once, and a one-line allocation decision backed by a named dimension — *"next session → X because Y,"* or the deliberate *"leave Z alone."* You ran the same scanner from Tutorial 1 in its other mode, read the risk matrix and the methodology-compliance grid, and — just as importantly — refused to adopt the framework on a repo that didn't warrant it. Methodology compliance is no longer a feeling about your projects; it's a measurable signal you steer the whole portfolio by, and you know the difference between a score that rose because the work got better and one that rose because someone gamed the checklist.

## Next

→ **[Tutorial 8: Keeping Adopters Current](T8_keeping_current.md)** — the dashboard tells you *where* to spend a session; `bin/status`/`bin/sync` keep the framework those projects run on *current* as the canonical repo evolves. Before you move on, do this one for real on Track A: point the scanner at the parent directory above your real repos and let the risk matrix — not your memory of which project felt neglected — choose your next session.
