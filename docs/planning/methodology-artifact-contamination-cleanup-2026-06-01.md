# Methodology-Artifact Cross-Contamination Cleanup — Plan

**Status:** PLAN (deliverable of portfolio Session 505, 2026-06-01). Not yet executed.
**Author:** Session 505 (portfolio oversight).
**Scope of THIS document:** A planning document only. No cleanup was performed in the planning session. Each phase below is a **separate execution session** with its own STOP point.
**Operator-chosen target design:** KEEP per-project dashboards + establish ONE canonical source (starter-kit) with a sync/version check; FIX the dashboard script's submodule misfire. (Decided 2026-06-01.)

---

## 1. Problem statement

The methodology ships several same-named artifacts that each project is meant to have its own copy of — `methodology_dashboard.py`, `dashboard.html`, `SESSION_NOTES.md`, `SESSION_RUNNER.md`, `SAFEGUARDS.md`. Over ~3 months these have cross-contaminated because there is **no canonical source, no sync mechanism, and the dashboard script silently changes behavior based on directory contents.** Concretely:

1. **The dashboard script has drifted into 3+ incompatible versions** with no single source of truth. The portfolio-root copy is the *most* evolved; the starter-kit "canonical" is **stale**; several projects froze at older snapshots.
2. **The script misfires in repos with git submodules.** Run inside `rad-con` (4 submodules) it renders a multi-row mini-portfolio of rad-con + its submodules — the operator's "sub-projects built the portfolio dashboard instead of their own." Verified: `rad-con/dashboard.html` (generated 2026-06-01) has 210 `<tr>` rows and names 6 projects.
3. **The script was committed into 6 project repos' git history** (should be a synced/ignored tool, not tracked source).
4. **The portfolio `SESSION_NOTES.md` and per-project notes have no enforced boundary.** wsjt-l engineering work is logged in BOTH the portfolio notes (S498, S504) AND wsjt-l's own notes (through S531). "Portfolio session vs sub-project session" has no consistent answer.

### Root cause (one line)
Same-named artifacts copied per project with **no canonical source, no sync, a mode-auto-detecting script that expands submodules by default, and no rule separating portfolio-level from project-level session logging.**

---

## 2. Evidence inventory (grep-based — ground truth as of 2026-06-01)

> Commands used are listed in §6 so the executor can re-run and confirm nothing has shifted.

### 2.1 `methodology_dashboard.py` — every copy, version, tracking, ignore status

Canonical reference points: **starter-kit = 1614 lines** (`2ae416a0…`), **portfolio-root = 1859 lines** (`a1cae340…`, the superset).

| Location | Lines | Version | Git-tracked? | `.gitignore`d? |
|---|---|---|---|---|
| `/Users/terrell/code/methodology_dashboard.py` (portfolio root) | 1859 | **portroot — superset / newest** | n/a (root not a repo) | n/a |
| `methodology/starter-kit/methodology_dashboard.py` | 1614 | **kit — STALE vs portroot** | tracked (methodology) | — |
| ham-radio-olympics | 1513 | DRIFTED (oldest) | **TRACKED** | no |
| nothamlib | 1569 | DRIFTED | **TRACKED** | no |
| ResortApp | 1569 | DRIFTED | **TRACKED** | no |
| rad-con | 1614 | =kit | **TRACKED** | no |
| radio-digital | 1614 | =kit | **TRACKED** | no |
| wsjtx-arm | 1614 | =kit | **TRACKED** | no |
| ftx1-cat | 1614 | =kit | untracked | no |
| panelkit-ui | 1614 | =kit | untracked | no |
| mark-down | 1614 | =kit | untracked | no |
| Morse-Trainer | 1614 | =kit | untracked | no |
| net-audio | 1614 | =kit | untracked | no |
| panelkit | 1614 | =kit | untracked | no |
| radio-web | 1614 | =kit | untracked | no |
| hamlib | 1569 | DRIFTED | untracked | **YES** |
| wsjt-l | 1614 | =kit | untracked | **YES** |

**Tracked-into-history (need `git rm --cached`):** ham-radio-olympics, nothamlib, ResortApp, rad-con, radio-digital, wsjtx-arm.
**Drifted versions (need re-sync):** ham-radio-olympics (1513), nothamlib (1569), ResortApp (1569), hamlib (1569).
**Already gitignored (target convention, 2 of 16):** hamlib, wsjt-l.

### 2.2 What the portfolio-root superset adds over the kit (must be folded into canonical)
`git diff --no-index --stat` = **305 insertions, 60 deletions.** New functions present in portroot, absent in kit:
`collect_github_metrics`, `collect_vulnerability_metrics`, `collect_coverage_config`, `render_risk_matrix`, `render_methodology_grid`, `render_activity_bars`, `render_language_breakdown`, `render_largest_files`, `render_project_card`, historical trending (`append_history`, `load_history`, `render_trend_section`).
**Implication:** the portfolio-root copy is the de-facto current version. Making the kit canonical = promote portroot → kit FIRST, then redistribute. Do **not** overwrite portroot with the older kit.

### 2.3 `dashboard.html` (generated output) — stray copies
Present (untracked) in: **rad-con (PORTFOLIO/mini-portfolio content — the misfire)**, wsjt-l, ftx1-cat, ham-radio-olympics, nothamlib, radio-digital, ResortApp, wsjtx-arm, hamlib.
All are gitignored as `dashboard.html` in their repos → safe untracked cruft (deletion does not touch git).
**`dashboard.html` NOT yet gitignored in:** radio-sdk, tax-forms, pdfink, mcarc (none currently carry a stray copy, but add the ignore when they adopt the dashboard).

> ⚠ **DO NOT TOUCH `ham-radio-olympics/templates/dashboard.html`.** It is that app's own Flask/Jinja template (`{% extends "base.html" %}`, competitor profile page), TRACKED and legitimate. It is unrelated to the methodology dashboard. Confirmed: no portfolio signature strings present.

### 2.4 The submodule misfire — exact location and cause
`methodology_dashboard.py:discover_projects()` (lines 170–206) and `main()` (line 1772):
- Lines **180–190**: single-project mode returns `[root]` **plus each git submodule as its own project entry** (`submodule status` walk).
- Line **1772**: `single_project = (root / ".git").exists()` → title becomes `"RAD-CON — METHODOLOGY DASHBOARD"`, but the body still lists every submodule row.
- Net effect in rad-con: a 5+ row mini-portfolio mislabeled as a single-project view.

### 2.5 Session-notes boundary
- Portfolio `SESSION_NOTES.md` contains sub-project engineering sessions: **S498 (wsjt-l dec-data schema)**, **S504 (wsjt-l upstream-drift review)**. 80 sub-project-name mentions total.
- **No evidence** any sub-repo *wrote into* the portfolio `SESSION_NOTES.md` (grep for `code/SESSION_NOTES` writes = none). The contamination is one-directional: sub-project work logged *up* into portfolio notes, plus dashboard mode-confusion (documented as a gotcha already in `hamlib/SESSION_NOTES.md:122` and `radio-digital/SESSION_NOTES.md`).

---

## 3. Target design (per operator decision)

- **One canonical source:** `methodology/starter-kit/methodology_dashboard.py`. Every other copy (portfolio root + each project) is a **synced copy**, never independently edited.
- **Per-project copies kept** (single-project-mode dashboard stays a per-project capability).
- **Sync + version check:** add a `DASHBOARD_VERSION` constant (none exists today — verified). The script self-reports its version; a sync helper copies the canonical to every consumer; running a stale copy prints a one-line "newer canonical available — run sync" warning.
- **Submodule misfire fixed in the script:** single-project mode scans the project **only** by default; submodule rows become opt-in via `--with-submodules`.
- **Tracking convention (RECOMMENDED, see §7 Decision D1):** the script and `dashboard.html` are **gitignored + synced** in every project (matches hamlib/wsjt-l today), NOT tracked source. Untrack the 6 committed copies.
- **Session-notes boundary:** portfolio `SESSION_NOTES.md` = portfolio-oversight sessions only; project engineering = that project's own `SESSION_NOTES.md`. Documented in both SESSION_RUNNER copies.

---

## 4. Phased execution plan (each phase = ONE session)

### Phase 1 — Establish the canonical script (methodology repo ONLY)
**Files:** `methodology/starter-kit/methodology_dashboard.py` (+ portfolio-root copy resynced).
1. `git diff --no-index methodology/starter-kit/methodology_dashboard.py methodology_dashboard.py` — review the full 305/60 diff. Confirm portroot is a clean superset (no portfolio-only hacks that break single-project mode).
2. Promote portfolio-root content into the starter-kit copy (kit becomes == portroot behavior).
3. Add `DASHBOARD_VERSION = "x.y.z"` constant near the top; print it in CLI output and embed in generated HTML footer.
4. Resync portfolio root from the new canonical (`cp methodology/starter-kit/methodology_dashboard.py methodology_dashboard.py`).
**DONE looks like:** starter-kit and portfolio-root copies are byte-identical and carry the version constant; one canonical file exists.
**Verify:**
```
shasum -a 256 methodology/starter-kit/methodology_dashboard.py methodology_dashboard.py   # identical
python3 methodology_dashboard.py --no-open        # portfolio mode: 21 projects, exit 0
( cd wsjt-l && python3 ../methodology_dashboard.py --no-open ) # sanity: single-project still runs
```
**Commit:** methodology repo, one commit. **STOP — this phase is one session.**

### Phase 2 — Fix the submodule misfire + add the sync helper (canonical script)
**Files:** `methodology/starter-kit/methodology_dashboard.py` (then resync portfolio root).
1. `discover_projects()`: single-project mode returns `[root]` only. Gate the submodule walk behind a new `--with-submodules` flag (default off). Keep portfolio mode unchanged.
2. Add a `--sync` (or sibling `sync_dashboard.sh`) helper that copies the canonical to the portfolio root + every discovered project, and a stale-version warning when a copy's `DASHBOARD_VERSION` < canonical.
3. Resync portfolio root.
**DONE looks like:** running the script inside a submodule-bearing repo yields a single-row dashboard for that repo; `--with-submodules` reproduces the old multi-row view; stale-copy warning fires on an older version.
**Verify:**
```
( cd rad-con && python3 ../methodology_dashboard.py --no-open ) && grep -c "<tr" rad-con/dashboard.html   # expect single-project (no submodule rows)
( cd rad-con && python3 ../methodology_dashboard.py --with-submodules --no-open )                          # old behavior restored
python3 methodology_dashboard.py --no-open   # portfolio mode unaffected: 21 projects
```
**Commit:** methodology repo, one commit. **STOP.**

> Phases 1 and 2 MAY be combined into a single "canonical script" session if the executor judges the script edits cohesive — both touch only the one file in the methodology repo. Keep them split if the diff review in Phase 1 surfaces surprises.

### Phase 3 — Redistribute canonical + purge stray artifacts (per-project, batched)
**Touches up to 16 project repos.** Per SAFEGUARDS blast-radius: **one commit per repo**, never `git add -A`.
For each project repo:
1. If `methodology_dashboard.py` is TRACKED (ham-radio-olympics, nothamlib, ResortApp, rad-con, radio-digital, wsjtx-arm): `git rm --cached methodology_dashboard.py`.
2. Ensure `.gitignore` contains both `methodology_dashboard.py` and `dashboard.html` (already has `dashboard.html` in 15/16; add `methodology_dashboard.py` everywhere except hamlib/wsjt-l which have it).
3. `cp` the canonical script into the project (overwrites drifted 1513/1569 copies).
4. Delete stray generated `dashboard.html` (gitignored cruft) — EXCEPT never touch `ham-radio-olympics/templates/dashboard.html`.
5. Commit that repo: `chore: sync methodology dashboard to canonical vX.Y.Z; untrack from history`.
**DONE looks like:** every project's `methodology_dashboard.py` is byte-identical to canonical and gitignored; no tracked copies remain; no stray portfolio-content `dashboard.html`.
**Verify (run from portfolio root):**
```
# every copy identical to canonical:
for r in */; do f="$r/methodology_dashboard.py"; [ -f "$f" ] && shasum -a 256 "$f"; done | awk '{print $1}' | sort -u   # expect 1 hash
# nothing tracked anymore:
for r in */; do [ -d "$r/.git" ] && git -C "$r" ls-files --error-unmatch methodology_dashboard.py 2>/dev/null && echo "STILL TRACKED: $r"; done   # expect no output
```
**Caution:** rad-con, wsjtx-arm, wsjt-l, panelkit-ui carry **uncommitted changes and large unpushed backlogs from prior sessions** (orient 2026-06-01: rad-con +18, wsjtx-arm +47, wsjt-l +10). Do NOT bundle their pending work; stage only the two filenames per repo. Coordinate pushes with the operator (these are historically operator-gated). MAY be split into several sessions (e.g. tracked-repos batch, then untracked-repos batch). **STOP per batch.**

### Phase 4 — Define the session-notes boundary (docs/process)
**Files:** `SESSION_RUNNER.md` (portfolio) + `methodology/starter-kit/SESSION_RUNNER.md`.
1. Add an explicit rule: portfolio `SESSION_NOTES.md` records portfolio-oversight/methodology sessions only; all project engineering is logged in that project's own `SESSION_NOTES.md`. A session run from a project directory writes that project's notes, full stop.
2. Add an orientation check: confirm `pwd` and which `SESSION_NOTES.md` you are reading/writing before Phase 0 step 2.
3. Leave existing misfiled entries (S498, S504) in place but add a one-line note that they were project work logged at portfolio level (do not migrate — low value, history-rewrite risk).
**DONE looks like:** the rule exists in both runners; no future ambiguity about which notes file a session uses.
**Verify:** `grep -n "portfolio-oversight" SESSION_RUNNER.md methodology/starter-kit/SESSION_RUNNER.md`.
**Commit:** methodology repo for the starter-kit copy; portfolio `SESSION_RUNNER.md` is in the non-repo oversight dir (save as file, per prior-session convention). **STOP.**

---

## 5. Risk & rollback
- **Reversibility:** every project change is a single per-repo commit → `git revert` / `git checkout` restores instantly. Stray-file deletions only remove gitignored generated output (regenerated by re-running the script).
- **Highest-risk step:** `git rm --cached` on the 6 tracked repos. Mitigation: per-repo commit, verify `git status` shows only the two filenames before committing.
- **radio-digital deliberately tracked the script** (documented in its notes). Confirm Decision D1 with the operator before untracking it (§7).
- **Do not regenerate** `dashboard.html` files the operator may be viewing live until Phase 1/2 land, or the live view shows old code.

## 6. Re-runnable evidence commands
```
# 6.1 all copies + version + tracked + ignored
for r in */; do repo=${r%/}; [ "$repo" = methodology ] && continue; [ -d "$repo/.git" ] || continue;
  for f in methodology_dashboard.py dashboard.html; do
    [ -f "$repo/$f" ] || continue;
    t=$(git -C "$repo" ls-files --error-unmatch "$f" 2>/dev/null && echo TRACKED || echo untracked);
    i=$(git -C "$repo" check-ignore "$f" 2>/dev/null && echo ignored || echo -);
    echo "$repo/$f $t $i"; done; done
# 6.2 version map vs canonical
KIT=$(shasum -a 256 methodology/starter-kit/methodology_dashboard.py|awk '{print $1}')
for r in */; do f="$r/methodology_dashboard.py"; [ -f "$f" ] && { s=$(shasum -a 256 "$f"|awk '{print $1}'); [ "$s" = "$KIT" ] && echo "$r =kit" || echo "$r DRIFT"; }; done
# 6.3 submodule misfire proof
grep -c "<tr" rad-con/dashboard.html
```

## 7. Open decisions for the operator (resolve before Phase 3)
- **D1 (recommended: gitignore + sync).** Per-project script: **gitignored + synced** (treat as external tool; untrack the 6 tracked copies) vs **keep tracked + sync**. Recommendation: gitignore+sync — avoids a churn commit in every repo on each canonical update, and matches the hamlib/wsjt-l precedent. radio-digital's deliberate tracking is the one explicit counter-precedent; confirm overriding it.
- **D2.** Submodule default: confirm single-project mode should default to **root-only** (operator called the submodule expansion a "misfire", so default-off is assumed). `--with-submodules` preserves the capability.
- **D3.** Sync mechanism: lightweight (`--sync` flag / `sync_dashboard.sh` run manually during methodology adoption) vs enforced (a hook). Recommendation: lightweight manual sync + stale-version warning; no hook.

## 8. Planning-session checklist (SESSION_RUNNER Phase 2)
- [x] Plan document written with file paths and line numbers.
- [x] Grep-based inventory completed for all affected symbols/files (§2, re-runnable in §6).
- [x] Each phase has explicit completion criteria + verification commands.
- [x] Each phase marked "separate session" with a STOP point.
- [x] Open decisions surfaced for the operator (§7).
