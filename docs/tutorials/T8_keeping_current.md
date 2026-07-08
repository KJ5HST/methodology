# Tutorial 8: Keeping Adopters Current

> **Objective:** Keep an installed project in step with the canonical methodology as it evolves — read drift with **`bin/status`**, apply updates with **`bin/sync`**, and absorb a new release *without losing your project-specific customizations.*
> **Prerequisites:** [Tutorial 7: Portfolio & Dashboard Ops](T7_portfolio_dashboard.md) — you've installed the framework (T1), run sessions and a campaign on one project (T2–T6), and zoomed out to the whole portfolio (T7). This is the **final** tutorial: it keeps everything the previous seven built *current.* You need a local `methodology/` checkout (Track B learners already have one — the sample came from it). New here? Start at the [series index](README.md).
> **Time:** ~20 minutes
> **What you'll produce:** An adopter project whose `bin/status` reads **`current` / `present` across the whole corpus** — reached the honest way: you detected real drift, previewed and applied the update, and handled a file you'd *locally modified* by relocating the edit into `CLAUDE.md` instead of force-overwriting it.
> **Track:** Pick one and stick with it for this pass —
> **A** (your own repo): a project you installed the framework into earlier (its files may genuinely be behind by now). Point the commands at your sibling `../methodology/` checkout.
> **B** ([sample project](sample-project/)): the todo-CLI you bootstrapped in [Tutorial 1](T1_setup.md). Set `METH` to the methodology checkout it came from, as you did in T1, and run the commands against it.

## Why this matters

The framework you installed in Tutorial 1 is not frozen — it ships releases. Every release since v2.5 changed files *beyond* the original three that the old sync tool tracked, so adopters who synced "by the book" could **silently fall behind while the tool still reported `current`** — false confidence about whether you're running the latest discipline. The [v2.8 distribution work](../../README.md#whats-new-in-v28) closed exactly that gap: `bin/sync` and `bin/status` now cover the **full corpus** over a single shared manifest, so "am I current?" stops being a guess and becomes a per-file answer you can read.

- [§What's New in v2.8](../../README.md#whats-new-in-v28) — the corpus-wide `bin/sync`/`bin/status`, the `seed` disposition, and the false-confidence gap this closes.
- [`BOOTSTRAP.md` §Updating an existing project](../../starter-kit/BOOTSTRAP.md#updating-an-existing-project) — the canonical update workflow (`bin/status` → `bin/sync`) and the manual fallback.
- [`BOOTSTRAP.md` §Step 5 — Customizations go in CLAUDE.md, not in synced files](../../starter-kit/BOOTSTRAP.md#step-5-customizations-go-in-claudemd-not-in-synced-files) — the customization seam that makes staying current friction-free *forever*.

This tutorial does not restate what each file is, how disposition is decided, or the exact distribution list — that lives once in [`bin/_manifest.py`](../../bin/_manifest.py) and the docs above. It makes you *run the update loop once* and survive the one move that breaks it: editing a synced file in place.

## Before you start

You need the same local `methodology/` checkout your project was installed from — `bin/sync`/`bin/status` are scripts on disk there; they read canonical content from that checkout (`source: local`). Track B: set `METH` to it exactly as in [Tutorial 1](T1_setup.md), e.g. `METH=~/Development/methodology`. Track A: if you kept the portfolio layout (your project a sibling of the checkout), the relative `../methodology/` form works.

```sh
# Track B — confirm the checkout and that your sample was installed from it:
ls "$METH"/bin/sync                 # the tool exists on disk
ls SESSION_RUNNER.md docs/methodology/ITERATIVE_METHODOLOGY.md   # T1 put the corpus here
```

**Checkpoint:** `"$METH"/bin/sync` (or `../methodology/bin/sync`) exists, and your project already has `SESSION_RUNNER.md` at its root and `docs/methodology/` populated from Tutorial 1. If not, run [Tutorial 1](T1_setup.md) first — there's nothing to keep current until something is installed.

## Steps

Each step is one action. Step 1 *reads* state, Step 2 makes drift visible, Step 3 is the update loop, Step 4 is the one trap that breaks it, and Step 5 makes it a habit across the portfolio. Don't skip ahead.

### 1. See exactly where you stand — `bin/status` (it writes nothing)

`bin/status` is the read-only audit: it compares every distributed file in your project against the canonical checkout and prints one row per file. Run it from inside your project:

```sh
"$METH"/bin/status .          # Track B — $METH is your methodology checkout
../methodology/bin/status .   # Track A — a sibling checkout
```

Right after a clean Tutorial-1 install, every row is `current` (TRACKED files match canonical) or `present` (SEED files exist):

```
source: local (/Users/you/Development/methodology)
Project  File                                       Disposition  Status
adopter  SESSION_RUNNER.md                          tracked      current
adopter  SAFEGUARDS.md                              tracked      current
adopter  RECOMMENDED_SKILLS.md                      tracked      current
…
adopter  SESSION_NOTES.md                           seed         present
adopter  CHANGELOG.md                               seed         present
adopter  ROADMAP.md                                 seed         present
adopter  docs/methodology/ITERATIVE_METHODOLOGY.md  tracked      current
…
```

The two **dispositions** are the whole model ([`bin/_manifest.py`](../../bin/_manifest.py)): **TRACKED** files are canonical-owned — `bin/sync` keeps them current and `bin/status` can report `current` / `N versions behind` / `locally modified` / `missing`. **SEED** files (`SESSION_NOTES.md`, `CHANGELOG.md`, `ROADMAP.md`) are *yours* after first creation — `bin/status` reports `present` / `absent` (and, for a seed whose *format* predates the current methodology, `present (stale format)` — advisory only, never drift), and an absent seed is **not** drift.

**Expected result:** A per-file table, every TRACKED row `current` and every SEED row `present` — and your working tree is byte-for-byte unchanged (status never writes).
**Checkpoint:** You can point at any row and say which disposition it is and what its status word means — and you confirm status changed *nothing* (`git status` in your project shows no new modifications from running it).

### 2. Make real drift visible — simulate "I installed before the last release"

In real life drift appears when the canonical repo ships a release after you installed. To *see* it now without waiting, roll one TRACKED file back to an earlier release tag — you're pretending you installed at v2.8 while the checkout has since moved to v2.9 — and delete a seed to show the contrast:

```sh
git -C "$METH" show v2.8:starter-kit/SESSION_RUNNER.md > SESSION_RUNNER.md   # pretend this was installed at v2.8
rm CHANGELOG.md                                                              # pretend a seed was never committed
"$METH"/bin/status .
```

```
adopter  SESSION_RUNNER.md  tracked  1 version behind
adopter  CHANGELOG.md        seed     absent
```

`bin/status` names the gap precisely: `SESSION_RUNNER.md` is **1 version behind** (v2.9 added a reasoning-effort line your v2.8 copy is missing — that's the exact content you'd be running without), and `CHANGELOG.md` is **absent**. `N versions behind` counts how many distinct committed versions of that file lie between yours and canonical, so your own number may differ from the `1` above. The seed's `absent` is reported but is *not* a defect to chase — it's a file you own.

**Expected result:** Status flips the rolled-back file to `N versions behind` and the deleted seed to `absent`; everything else stays `current` / `present`.
**Checkpoint:** You can state *which* file is behind and by how much from the report alone — the "am I current?" guess is now an evidence-backed answer. That conversion is the false-confidence gap [v2.8](../../README.md#whats-new-in-v28) closed.

### 3. Bring it current — preview first, then sync

The update loop is **status → dry-run → sync → status**. Look before you leap with `--dry-run` (writes nothing — it only prints intent), then apply:

```sh
"$METH"/bin/sync . --dry-run     # preview: 'would write' / 'would create', nothing touched
"$METH"/bin/sync .               # apply
"$METH"/bin/status .             # confirm
```

The dry run shows intent; the real run reports `updated` for the file that drifted and `created` for the re-seeded one — and every file that was already current reports `unchanged`, so sync only ever touches what actually moved:

```
  version: v2.9
  files:
    SESSION_RUNNER.md: updated
    CHANGELOG.md: created
    …                 (every other file: unchanged)
```

The `version:` line is `git describe --tags` of your checkout, so it reads whatever release you're on. After sync, status returns every row to `current` / `present`. (SEED note: sync re-creates a seed *only when it's absent* — an existing seed is never clobbered, even with `--force`, because once it exists it's yours.)

**Expected result:** `--dry-run` changes nothing; the real run writes only the drifted/absent files; the follow-up status is all `current` / `present` again.
**Checkpoint:** Your project is current, and you reached it by previewing first — you never overwrote a file without seeing the intent. You've run the whole loop once.

### 4. The one trap — customizations don't go in synced files

Now the move that breaks everything. Say you want this project to always run its linter in Phase 5, so you edit `SESSION_RUNNER.md` directly. The next sync refuses:

```sh
# (you appended a custom note to SESSION_RUNNER.md)
"$METH"/bin/sync .
```

```
  ERROR: the following files have local modifications that don't match
  any canonical or historical version and would be overwritten:
    SESSION_RUNNER.md

  The recommended pattern (see plan §3.2) is to move per-project
  customizations into CLAUDE.md's 'Project-Specific Methodology
  Adaptations' section, keeping synced files byte-identical to canonical.

  To proceed anyway and overwrite local changes, pass --force.
```

Sync **exits non-zero and writes nothing** — it will not silently eat an edit it doesn't recognize (`bin/status` labels the same file `locally modified`). The tempting fix is `--force`, and used *first* it is the wrong one: it discards your edit **and** leaves you forking the shared procedure every release — that is **FM #17 (protocol erosion)** wearing a convenience flag, the exact slow-drip that slides a 9/10 chain to 1/10 ([Known Failure Modes](../../starter-kit/SESSION_RUNNER.md#known-failure-modes)). The right fix is the **customization seam**: move the rule into `CLAUDE.md`'s *Project-Specific Methodology Adaptations* section, then restore the file to canonical and re-sync clean ([`BOOTSTRAP.md` §Step 5](../../starter-kit/BOOTSTRAP.md#step-5-customizations-go-in-claudemd-not-in-synced-files); [§Troubleshooting](../../starter-kit/BOOTSTRAP.md#troubleshooting)):

```sh
# 1. record the linter rule in CLAUDE.md → "Project-Specific Methodology Adaptations"
# 2. now that the intent is safe, discard the orphaned in-file edit and take canonical:
"$METH"/bin/sync . --force        # safe HERE — the customization already lives in CLAUDE.md
"$METH"/bin/status .              # SESSION_RUNNER.md → current
```

`--force` is dangerous only when it runs *before* you've relocated the edit; once the intent lives in `CLAUDE.md` — which every session already reads — discarding the in-file copy loses nothing. Your customization survives, the synced file stays byte-identical to canonical, and the next release applies without a single conflict.

**Expected result:** Sync refuses the unrecognized edit (exit non-zero, no write); after you move the rule to `CLAUDE.md` and re-sync, `SESSION_RUNNER.md` is `current` and your customization is intact in `CLAUDE.md`.
**Checkpoint:** Your project is current *and* still does the project-specific thing you wanted — because the customization lives in the file built to hold it, not in the file built to be replaced. If your instinct in Step 4 was to reach straight for `--force`, you just learned why the seam exists.

### 5. Make it routine — and keep the checkout itself fresh

Two habits turn this into maintenance you don't think about:

- **Audit the portfolio before a work session.** `bin/status` takes many paths and shell-expands globs, so one command reports drift across every project — the [Tutorial 7](T7_portfolio_dashboard.md) portfolio cousin: the dashboard tells you *where* the next session goes; `bin/status` tells you whether the framework that project runs on is itself current first.

  ```sh
  "$METH"/bin/status ~/projects/*     # one row per file, per project
  ```

- **Pull the checkout before you trust "current."** `status`/`sync` compare against your **local** checkout (`source: local`), so `current` means "current with whatever your checkout holds" — a stale checkout reports green against an old canonical. Update the checkout first, or compare against GitHub directly ([`BOOTSTRAP.md` §Updating](../../starter-kit/BOOTSTRAP.md#updating-an-existing-project)):

  ```sh
  git -C "$METH" pull                 # bring the checkout to the latest release, THEN status/sync
  "$METH"/bin/status . --source=github   # or: compare straight against canonical on GitHub (needs gh CLI)
  ```

Keeping current is cheap and fully reversible — the **lighter default** the [Matching Reasoning Effort to Stakes](../../ITERATIVE_METHODOLOGY.md#matching-reasoning-effort-to-stakes) rule reserves for low-blast-radius work. The deep reasoning belongs to the sessions this maintenance *protects*, not to the sync itself.

**Expected result:** You can audit every project's drift in one command and you know why a fresh checkout (or `--source=github`) must precede trusting a `current`.
**Checkpoint:** You can describe the full update loop — pull the checkout, `bin/status` the project(s), `bin/sync` what drifted, relocate any in-file customizations to `CLAUDE.md` — without re-reading this page.

## Common mistakes

Cite the failure mode by number; link the list, don't paste it.
(Full list: [Known Failure Modes](../../starter-kit/SESSION_RUNNER.md#known-failure-modes).)

- **Editing a synced file in place — then forcing past the refusal.** A direct edit to `SESSION_RUNNER.md` / `SAFEGUARDS.md` / any TRACKED file becomes drift that blocks the next update; reaching for `--force` *before* relocating the edit discards your work and keeps you forking the shared procedure release after release. That's **FM #17 (protocol erosion)** — improvement-by-subtraction-or-fork during a session. The countermeasure is the customization seam: project additions live in `CLAUDE.md`'s Adaptations section, synced files stay byte-identical to canonical ([`BOOTSTRAP.md` §Step 5](../../starter-kit/BOOTSTRAP.md#step-5-customizations-go-in-claudemd-not-in-synced-files)).
- **Trusting memory that you're current instead of running `bin/status`.** "I synced a while ago, I'm probably fine" is exactly the false confidence the v2.8 work existed to kill — the old tool tracked three files and reported `current` while the rest of the corpus silently fell behind. Read the per-file report, don't assume ([§What's New in v2.8](../../README.md#whats-new-in-v28)).
- **Syncing from a stale checkout.** `status`/`sync` compare against your local `methodology/` checkout, so `current` against a checkout you never `git pull` isn't current against canonical. Pull the checkout first, or pass `--source=github` to compare against the live repo.
- **Chasing an `absent` seed as if it were drift.** `SESSION_NOTES.md` / `CHANGELOG.md` / `ROADMAP.md` are adopter-owned; `absent` is a legitimate state, not a defect. Sync will re-seed a missing one, but you never *have* to — they're yours, not canonical's.

## You produced

An installed project whose `bin/status` reads `current` / `present` across all 21 distributed files — reached honestly. You ran the read-only audit, manufactured real drift and watched status name it to the file, previewed with `--dry-run` and applied with `bin/sync`, and — the move that matters — handled a file you'd locally modified by relocating the edit into `CLAUDE.md` rather than force-overwriting it. Staying current is no longer a hope; it's a loop you can run on one project or the whole portfolio, and you know the one trap that turns "friction-free forever" into "merge conflict every release."

That closes the series. Tutorial 1 installed the framework; Tutorials 2–6 ran it on one project through sessions, a custom workstream, and a campaign; Tutorial 7 zoomed out to the portfolio; and Tutorial 8 keeps all of it current as the canonical methodology itself evolves.

## Next

→ **You've finished the track.** There's no Tutorial 9 — T8 was the final roadmap stop, and the [curriculum](README.md#curriculum) is complete. The real next step isn't another lesson: point [`bin/status`](../../starter-kit/BOOTSTRAP.md#updating-an-existing-project) at your actual projects, bring the drifted ones current, and go run a real session — with [Phase 0 Orient](T2_first_session.md), the [Present gate](T5_cautionary.md), and the [handoff ratchet](T3_compounding_loop.md) now muscle memory. Loop back to the [series index](README.md) any time you want to re-run a lesson on a new project.
