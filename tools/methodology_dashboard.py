#!/usr/bin/env python3
"""Methodology Dashboard -- Portfolio health and methodology compliance scanner.

Scans sibling project directories for git repositories, collects metrics across
7 dimensions (git, files, tests, CI/CD, docs, methodology, dependencies), scores
health and risk, generates a self-contained HTML dashboard, and opens it in the
default browser.

Part of the Iterative Session Methodology.
https://github.com/KJ5HST/methodology

MODES
-----
The dashboard auto-detects its context based on where it's placed:

  Portfolio mode (parent directory is NOT a git repo):
    Scans all sibling git repositories as separate projects.

       ~/projects/                       <-- put methodology_dashboard.py here
       ~/projects/project-a/             <-- scanned as project
       ~/projects/project-b/             <-- scanned as project

  Single-project mode (placed inside a git repo):
    Scans the project itself, plus any git submodules as separate entries.

       ~/projects/my-app/                <-- put methodology_dashboard.py here
       ~/projects/my-app/lib/submodule/  <-- scanned as separate entry

  A project that keeps its methodology files under methodology/ (BL-101, the new layout) keeps this
  file there too: it finds its own project one level up, scans it exactly as it scans a project
  whose files are at the root, and writes dashboard.html and dashboard_history.jsonl beside itself,
  so the project's root stays clean. `--sync` puts each project's copy where that project keeps its
  methodology files, and refuses a half-migrated project (the runner at both places) by name.

SETUP
-----
1. Copy this file to your desired location (see Modes above).

2. Run:

       python3 methodology_dashboard.py

   This generates dashboard.html, opens it in your browser, and prints a
   terminal summary. The HTML auto-refreshes every 60 seconds — leave it
   open and re-run the script whenever you want updated data.

CUSTOMIZATION
-------------
- EXCLUDE_DIRS: Add directory names to skip during project discovery.
  By default, common non-project directories are excluded. The methodology
  repo itself is deliberately NOT excluded — it is scored like any other
  project, and --sync skips it as a target on its own (it authors this file
  rather than receiving it).

- WALK_SKIP: Directories skipped during file traversal (build artifacts,
  vendor dependencies, etc.).

- METHODOLOGY_ITEMS: The weighted checklist used for compliance scoring.
  Adjust weights to match what matters most for your team. This is the
  checklist for a repo that ADOPTS the methodology.

- FRAMEWORK_ITEMS: The separate checklist scored instead of METHODOLOGY_ITEMS
  when a repo is detected as PUBLISHING the methodology rather than consuming
  it — a framework publisher owes different artifacts than an adopter, so
  scoring it against adopter-root files reports a false "partial adoption".

- .methodology-profile: A repo-root marker that overrules either structural
  detection when the heuristic is wrong about your repo. Only its first line
  that is neither blank nor a comment is read. It carries whitespace-separated
  tokens from two independent axes: repo CLASS (doc-only | code) and repo ROLE
  (framework | adopter). Naming one token of a pair forces that classification;
  naming both abstains on that axis alone and falls back to detection. Declaring
  is exact where detection is a guess.
"""

import ast
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# --- layout resolver: BEGIN ---
import os as _os
from pathlib import Path as _Path


def resolve_layout(root, anchor="SESSION_RUNNER.md"):
    """Return (kind, directory, found): kind is new|legacy|half|none, directory a Path or None,
    found the anchor paths that exist. A half-migrated tree has no directory, by design.
    A file found in both places is the framework's under methodology/ when the runner is under
    methodology/ and not at the root: the root copy is the project's own and is left alone, kind new,
    and found still names both. Any other tie stays half, and the runner cannot decide a tie about itself."""
    root = _Path(root)
    new, old = root / "methodology" / anchor, root / anchor
    found = tuple(p for p in (new, old) if _os.path.isfile(p))
    if len(found) == 2:
        if _os.path.isfile(root / "methodology" / "SESSION_RUNNER.md") and not _os.path.isfile(root / "SESSION_RUNNER.md"):
            return "new", new.parent, found
        return "half", None, found
    if not found:
        return "none", None, ()
    return ("new", new.parent, found) if found[0] == new else ("legacy", root, found)
# --- layout resolver: END ---

# === CONSTANTS ===

# Canonical dashboard version. Source of truth: methodology/starter-kit/methodology_dashboard.py.
# Every other copy (portfolio root + per-project) is a synced copy of the canonical and must
# carry the same value. A copy whose DASHBOARD_VERSION is older than the canonical is stale —
# re-sync from the canonical. Bump on any change to the canonical script.
# 2.19.0: BL-88 (docs/planning/dashboard-read-cap-class-adopter-drift-plan.md). The Class B read-cap
# row stops asserting a trimmer config it never read (P1, cb9b0ed, which shipped without a bump) and
# names a remedy only where the scanned project's own trimmer SOURCE declares the file, taking Class
# A's severity there (P2). Changed output on a distributed tool: MINOR. Fork-only -- upstream's line
# continues from 2.11.1, so the two stay apart until a dashboard PR reconciles them. (2.18.0, the
# resync's merge of upstream's 2.11.x line, is described in git: `git log -S'2.18.0'` on this file.)
# 2.22.0: BL-101 P5 (docs/planning/methodology-subdirectory-plan.md, section 7.2). The dashboard reads a
# project that keeps its methodology files under methodology/ exactly as it reads one that keeps them at
# the root: the checklist items keep their names and are LOCATED through the layout resolver, a project
# whose runner is under methodology/ is still an adopter, and a half-migrated tree (the runner at both
# places, or a state file at both with nothing to decide) is a HIGH risk that names both paths. Changed
# output on a distributed tool: MINOR.
# 2.21.0: BL-99. The manifest-history walk reads the FIRST-PARENT line (`_gate_manifest_history`):
# a repo that had merged a lineage with a different manifest printed "floor lowered" / "gate
# removed" rows nobody caused (9 of the 10 on this fork after the 2026-10 resync) and could miss a
# real loosening a merge resolved to. Changed output on a distributed tool: MINOR.
# 2.20.0: BL-95 R1, the 2026-10 resync (docs/planning/upstream-resync-2026-10-plan.md, D5). The
# `.gitattributes` seed (starter-kit/gitattributes, arriving from upstream's v4.1) is installed
# content: dotfiles are categorized as config by name (CONFIG_FILES), and the seed has its own row
# and signature set in _FRAMEWORK_INSTALLED_CONTENT. Changed output on a distributed tool: MINOR.
# Fork-only -- upstream's line continues from 2.11.3, so the two stay apart until a dashboard PR
# reconciles them.
DASHBOARD_VERSION = "2.22.0"

ROOT = Path(__file__).parent
# `"methodology"` was here and is deliberately gone (plan D4(c)): the scanner was structurally
# blind to its own home in portfolio mode — the one repo whose methodology signals it is best
# placed to check, and the subject of upstream issue #59. The self-scan is safe now that Layer 4
# classifies repo role; before that it read its own home as a 5%-adoption risk.
EXCLUDE_DIRS = {"BrogueCE-iOS", ".git", "__pycache__", "node_modules", ".venv", "venv"}
WALK_SKIP = {".git", ".claude", "node_modules", "__pycache__", ".venv", "venv", "target",
             "build", "dist", ".build", "DerivedData", "Pods", ".gradle"}

SOURCE_EXTS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".rs", ".c", ".cpp", ".cc", ".h", ".hh",
    ".hpp", ".m", ".mm", ".java", ".swift", ".ino", ".go", ".rb", ".php", ".cs",
    ".kt", ".scala", ".lua", ".sh", ".bash", ".zsh", ".pl", ".r",
}
TEST_PATTERNS = {"test_", "_test.", ".test.", ".spec.", "tests/", "__tests__/", "test/"}
# `.qmd`/`.rmd` (Quarto / R Markdown) are literate-document formats, not source — an R package's
# vignettes and articles are prose-with-embedded-code, the same bucket `.md` already lives in, not
# `.r`'s. Before this, a file with either extension outside a `docs/` path fell through
# categorize_file's whole ladder to "other": not source, not docs, not even LOC-counted (LOC is
# skipped for "other"). BL-34 — found scanning `nprcgenekeepr` (28 `.rmd` + 12 `.qmd`, 11 of the 12
# invisible with 0 LOC because only one lived under `docs/`).
DOC_EXTS = {".md", ".txt", ".rst", ".adoc", ".org", ".qmd", ".rmd"}
CONFIG_FILES = {
    "Dockerfile", "Makefile", "CMakeLists.txt", "Rakefile", "Gemfile",
    "Procfile", "fly.toml", "netlify.toml", "vercel.json",
    # Name-matched, not extension-matched: Path(".gitattributes").suffix is "" (a dotfile has no
    # suffix), so CONFIG_EXTS can never see it. Distributed as a SEED since the parallel-sessions
    # plan's Phase 1 (bin/_manifest.py), and categorized here so the installed-file tests hold.
    ".gitattributes",  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
}
CONFIG_EXTS = {
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".gitignore", ".editorconfig", ".eslintrc", ".prettierrc",
    ".gradle", ".properties", ".plist", ".xcconfig",
}
ASSET_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".icns", ".bmp",
    ".pdf", ".mp3", ".wav", ".ogg", ".ttf", ".woff", ".woff2", ".eot",
    ".bin", ".dat", ".zip", ".tar", ".gz",
}
LANG_MAP = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript",
    ".jsx": "JavaScript", ".rs": "Rust", ".c": "C", ".cpp": "C++", ".cc": "C++",
    ".h": "C/C++ Header", ".hh": "C++ Header", ".hpp": "C++ Header",
    ".m": "Objective-C", ".mm": "Objective-C++", ".java": "Java", ".swift": "Swift",
    ".ino": "Arduino", ".go": "Go", ".rb": "Ruby", ".php": "PHP", ".cs": "C#",
    ".kt": "Kotlin", ".scala": "Scala", ".lua": "Lua", ".sh": "Shell",
    ".bash": "Shell", ".zsh": "Shell", ".html": "HTML", ".css": "CSS",
    ".scss": "SCSS", ".less": "LESS", ".sql": "SQL",
    # BL-34 — `.r` was already in SOURCE_EXTS (so R LOC always counted toward Source), but had no
    # LANG_MAP entry, so it never got its own "Code by Language" row. Found against `nprcgenekeepr`
    # (603 `.r` files, 77,773 LOC — the bulk of that project's Source total — invisible in the
    # per-language breakdown).
    ".r": "R",
}

METHODOLOGY_ITEMS = [
    ("SESSION_RUNNER.md", 25, "file"),  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    ("SAFEGUARDS.md", 20, "file"),  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    ("SESSION_NOTES.md", 20, "file"),  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    ("BACKLOG.md", 15, "file"),
    ("CHANGELOG.md", 5, "file"),  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    ("HANDOFFS.md", 5, "file"),  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    ("ROADMAP.md", 5, "file"),  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    ("docs/methodology", 10, "dir"),  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    ("docs/methodology/workstreams", 10, "dir"),  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
]

# The compliance DENOMINATOR — derived from the checklist itself, never written as a literal.
# History is the argument for deriving it: the original six items summed to exactly 100, so the
# "%" label and a bare `* 0.2` health dimension were correct *by construction*; two 5-point items
# were later appended without re-cutting the scale, and from then on a fully-compliant project
# rendered "110%" over a 22-of-20 sub-score. A hardcoded denominator is what drifted, so a
# hardcoded 100 would drift again the next time this list grows.
#
# Adopter-root files that the methodology distributes are expected to appear on this checklist or
# to be recorded as deliberately unscored — an invariant the canonical test suite enforces against
# the distribution manifest (tools/test_methodology_dashboard.py, CHECKLIST_EXEMPT), since the
# manifest is canonical-only and an adopter's copy has nothing to check itself against.
METHODOLOGY_MAX = sum(weight for _, weight, _ in METHODOLOGY_ITEMS)

# The FRAMEWORK checklist — scored instead of METHODOLOGY_ITEMS when detect_repo_role says this
# repo PUBLISHES the methodology rather than consuming it. METHODOLOGY_ITEMS lists adopter-root
# DESTINATIONS; a distributor does not install a second copy of its own corpus into its own root,
# so grading it against that list asks a question it was never going to answer yes to.
#
# Two halves, both checkable by existence:
#   - does it publish a complete corpus (the artifacts an adopter receives, plus the machinery
#     that delivers them)?
#   - does it OPERATE the methodology it publishes (the root action ledger and close-out
#     receipts it asks every adopter to keep)?
# The second half is why the role swap is not a hiding place: without it, becoming a "framework"
# repo would stop the scanner asking whether the publisher runs its own rules.
#
# NOT SCORED, deliberately: the two paths detect_repo_role uses to prove the role
# (bin/_manifest.py, starter-kit/SESSION_RUNNER.md). If the evidence for the role also earned
# points, the raw sum would have a nonzero floor on the structural path and the "no corpus at
# all" branch would become an assertion over an input that can never occur — the same
# unreachable-signal defect this campaign exists to close, re-created inside its own fix. Their
# provenance is DISPLAYED on the card instead.
#
# NOT SCORED for a different reason: any distribution SEED source. Those are placeholders here
# (starter-kit/SESSION_NOTES.md is a 27-line stub, starter-kit/ROADMAP.md an 18-line skeleton),
# and crediting a placeholder is precisely the harm the prohibition in the campaign plan's
# §"Layer 4 — Repo role" names. (Cited by section, not by line: that plan says outright it is the
# second time its line citations went stale, and this one had already drifted 255 -> 275.)
# The canonical test suite enforces that rule mechanically against bin/_manifest.py.
FRAMEWORK_ITEMS = [
    ("ITERATIVE_METHODOLOGY.md", 15, "file"),      # the theory layer the runner cross-references  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    ("starter-kit/SAFEGUARDS.md", 15, "file"),     # the enforcement half of the runner
    ("workstreams", 15, "dir"),                    # 9 of the 24 distributed sources live here
    ("bin/sync", 15, "file"),                      # what separates HAVING a methodology from PUBLISHING one
    ("bin/tests.sh", 10, "file"),                  # the framework's build equivalent
    ("CHANGELOG.md", 10, "file"),                  # its OWN action ledger (FM #27)  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    ("HANDOFFS.md", 10, "file"),                   # its OWN close-out receipts (v3.3)  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    ("starter-kit/BOOTSTRAP.md", 5, "file"),       # the documented install path
    ("HOW_TO_USE.md", 5, "file"),                  # onboarding prose  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    ("bin/status", 5, "file"),                     # how an adopter learns its copy has drifted
]

# Derived for the same reason METHODOLOGY_MAX is (see above): a literal denominator is what
# drifted last time. Deliberately not 100 — a denominator of exactly 100 makes raw == pct, which
# renders every value-sweep test inert because an implementation that scaled the RAW sum would
# pass unnoticed.
FRAMEWORK_MAX = sum(weight for _, weight, _ in FRAMEWORK_ITEMS)

# Component C — CHANGELOG ledger-freshness thresholds (advisory only; see
# evaluate_changelog_freshness). This monitor stops rewarding mere presence: a CHANGELOG.md
# that exists but no longer tracks the work earns the "present" point, not the "fresh" one,
# and raises an advisory RISK line. It never hard-fails a score — the authoritative ledger
# gate lives in the session runner (FM #27 close-out + Phase 0 reconcile-on-read), not here.
LEDGER_UNLOGGED_MAX = 10       # Signal C: non-merge commits since CHANGELOG was last committed
LEDGER_LAG_DAYS_MAX = 21       # Signal B: days the ledger frontier may trail HEAD on an active repo
LEDGER_REAL_HISTORY_MIN = 10   # below this commit count a repo gets new-adopter grace (fresh seed)
SEED_SENTINEL = "METHODOLOGY-SEED-SENTINEL"  # Signal D: an untouched seed still carries this token
_DATED_ENTRY_RE = re.compile(r'^###\s+\d{4}-\d{2}-\d{2}', re.MULTILINE)
_BACKLOG_DONE_RE = re.compile(r'^\s*[-*]\s*\[x\]', re.IGNORECASE | re.MULTILINE)
_BACKLOG_BOX_RE = re.compile(r'^\s*[-*]\s*\[[x ]\]', re.IGNORECASE | re.MULTILINE)
_BACKLOG_BULLET_RE = re.compile(r'^\s*[-*]\s+\S', re.MULTILINE)
_FENCE_RE = re.compile(r'^\s*(?:```|~~~)')
_TABLE_SEP_RE = re.compile(r'^\s*\|[\s:|-]+\|\s*$')

# Signal F's table predicate: a cell that STARTS WITH one of these tokens, in a row of >= 3
# cells, ignoring the ID column. EMPIRICALLY TUNED — do not re-derive it. Against a real
# 643-line table backlog the campaign plan measured: *contains* a token = 321; *equals* a token
# = 227 (misses `**DONE (Session 30, ...)**` and counts the 2-cell Status legend); this predicate
# = 256, within 3 of an independent hand count of 253. All three counts reproduce here exactly.
# The plan calls the contains/equals gap of 94 "false positives"; treat that as the plan's
# characterization of why *contains* was rejected, not as a measured error count — it is the
# arithmetic 321 - 227, and roughly a third of those rows are ones this predicate also counts.
# What is independently verified is the ranking the choice rests on: *contains* admits
# NOTES-column prose that this predicate rejects. The plan records the three counts but not the
# token list, so this set was
# recovered by search: it reproduces all three numbers against that corpus, where a DONE-only set
# scores 277 rather than 321 on the *contains* probe. That is corroboration, NOT uniqueness — any
# superset adding tokens the corpus never uses reproduces the same three numbers, so this set is
# *a* set consistent with the tuning rather than provably *the* one. Only DONE / FIXED / RESOLVED
# are exercised by that corpus at all; the other five add 0 matches there, true or false, and are
# carried for conventions it happens not to use. All eight are pinned by test, because a token no
# test exercises is a token no one can safely change.
_BACKLOG_DONE_TOKENS = ("DONE", "COMPLETE", "COMPLETED", "SHIPPED", "FIXED", "RESOLVED",
                        "CLOSED", "✅")  # U+2705 WHITE HEAVY CHECK MARK
_BACKLOG_LOCATIONS = ("BACKLOG.md", "docs/BACKLOG.md", "docs/planning/BACKLOG.md")

# --- D4(b): the agent Read cap ----------------------------------------------------------------
# A SECOND large-file question, deliberately NOT a widening of the BL-5 code-smell check in
# assess_risks(). BL-5 asks "is this MODULE unwieldy?" — a judgment about structure, false for a
# 2,500-line chapter, which is why .md is excluded there and `vendor` after it: two consecutive
# narrowings, both earned by measured false positives. This asks "does a file a session must read
# IN FULL still fit in one read?" — a fact about the harness, true or false whatever the file is
# for. Separating them is ADDED POLICY: the ratified design says only that a 2,090-line .md must
# be able to trip *a* large-file risk, and taking that literally would regress BL-5's test.
#
# UNIT: BYTES, converted from the TOKEN cap the harness actually enforces. Re-denominated at
# Phase B (2026-08-26); it was LINES, and lines were not merely imprecise but STRICTLY DOMINATED.
# Measured over 18 watched ledgers in 5 repos: the 2,000-line threshold fired on 3 and stayed
# silent on 8 that a byte threshold at ANY point in the measured 2.2705-3.0300 B/token band
# catches, and it caught NOTHING a byte threshold misses. The B/line spread over that same
# population is 8.6x; the B/token spread is 1.33x. So this is not a re-tuning: one axis reports
# the quantity the cap is denominated in and the other does not.
# VALUE: harness behaviour, not a repo property and not taste — and DERIVED, never written as one
# opaque number, because a number goes stale when the harness moves and the command does not.
# What was measured, with the reproduction beside it:
#   * the cap states itself: "exceeds maximum allowed tokens (25000)".
#   * truncation is ANNOUNCED, never silent — a PARTIAL-view banner giving the delivered span,
#     the file's true length, the token count and the cap, warning against answering from it.
#   * it does NOT deliver a fixed number of lines. A 3,000-line file came back WHOLE; a 536-line
#     one did not. Delivery is whatever prefix fits the TOKEN cap.
#   * an explicit `limit` spanning an over-cap region neither truncates nor bypasses: it ERRORS
#     with NO content, which is also what makes it a free, exact token meter.
#   * PAST 256 KiB THERE IS NO PREFIX AT ALL. A default read is refused outright — "File content
#     (256.1KB) exceeds maximum allowed size (256KB)" — so the familiar consolation that
#     "truncation is ordered, and the top of the file still arrives" holds only BETWEEN the two
#     boundaries. 5 of those 18 fleet ledgers are already past this one.
# RE-MEASURE rather than restating those five sentences. The reproduction is
# docs/planning/read-cap-premise-correction-plan.md Appendix A, and it is the ONLY instrument that
# can falsify them: no test in this repository can, because nothing here invokes the agent's Read
# tool. A green suite is evidence that nothing ELSE broke.
# BASIS — the failure already happened here, and was found by accident rather than by any check:
#   git show 3aee4e3^:CHANGELOG.md | wc -l    -> 2,090
# Phase 0's reconcile then computed a frontier against a record it could not fully see.
# Re-measured since: that file is 186,704 B — roughly 2.97x the token cap but UNDER the 256 KiB
# refusal, so a default read of it came back as a truncated prefix with a banner, not as nothing.
# (An earlier draft of this comment said it was past the refusal. It is not: 186,704 < 262,144.
# A fixture-control assertion caught that, which is the only reason it is not shipped here.)
# The incident dates when the problem was NOTICED, not when it began, and the 2,000-line number
# derived from it recorded a symptom's size rather than a threshold.
# Same names, same values and same stated reason as starter-kit/methodology_trim.py's, so the
# reporter and the remedy cannot disagree about where the cliff is; a canonical test pins the
# literals together. Note precisely what that buys: it keeps the two copies CONSISTENT, and it
# kept them consistent throughout the period both were WRONG.
READ_CAP_TOKENS = 25_000
MIN_BYTES_PER_TOKEN = 2.27       # the measured FLOOR, not the mean — a guard that must not stay
                                 # silent on a truncating file assumes the densest content it will
                                 # meet. NOT context_budget.py's bytes_per_token, which estimates
                                 # a different quantity (opening context vs CLAUDE.md size).
READ_CAP_BYTES = int(READ_CAP_TOKENS * MIN_BYTES_PER_TOKEN)     # 56,750 B — computed, not written
READ_REFUSE_BYTES = 256 * 1024                                  # the hard, zero-content boundary

# PHASE C2 — the Class A pair, mirrored from methodology_trim.py and pinned to it by a canonical
# test, exactly as the four constants above are. THE REASON THEY EXIST HERE rather than only in
# the trimmer: this scanner re-implements the trimmer's trigger in collect_trim_metrics (it must,
# because it reports on repos where the tool is not installed), so a threshold that moved in the
# trimmer alone would leave this file emitting "the archive trigger fires" beside a `--check` that
# says it does not — naming a command whose output contradicts the row.
#
# THESE ARE NOT A REPLACEMENT FOR READ_CAP_BYTES; the two answer different questions and BOTH are
# reported. READ_CAP_BYTES answers "does one Read deliver this whole file?", which stays true of a
# Class A ledger and is why its risk row survives rather than being deleted (plan §7 rejects
# option D on exactly that ground). CLASS_A_FIRE_BYTES answers "is a trim worth doing?", and for a
# newest-on-top ledger whose truncation drops the OLDEST records the honest denominator for that
# is the hard refusal, not the cap.
CLASS_A_FIRE_BYTES = 192 * 1024   # 196,608 — see methodology_trim.py's block for the derivation
CLASS_A_STOP_BYTES = 96 * 1024    # 98,304  — reported, never applied here; this tool never trims

# The files a session opens to establish state, restricted to the ones the ADOPTER owns.
#
# THE JUSTIFICATION THAT STOOD HERE WAS FALSE FOR TWO OF THE SIX NAMES, and it is corrected rather
# than quietly dropped (Phase B / BL-52). It read "the files a session is instructed to read IN
# FULL ... step 6 (reconcile CHANGELOG.md and HANDOFFS.md against git log)". Step 6 is
# SESSION_RUNNER.md's reconcile, and its own stated mechanics are FRONTIER-BASED:
# `git log -1 --format=%H -- CHANGELOG.md`, then the commits after it. That reads git HISTORY, not
# the file. The HANDOFFS.md half is frontier-based the same way, and the one thing step 6 does
# look for INSIDE the file — a still-`pending` receipt — is at the TOP by construction and
# SAFEGUARDS.md prescribes a grep for it. Phase 3A reads ONE receipt, not the ledger.
# Measured, not just re-read: across 85 session transcripts of this repo each root ledger was read
# WHOLE exactly ONCE and read in PART 1,696 / 1,797 times. Roughly 1 in 85.
# Two further corrections to what was claimed: the runner says "in full" about exactly ONE file,
# SAFEGUARDS.md, which is deliberately NOT in this set (it is a TRACKED dest — see the test
# below); and no protocol text names `docs/BACKLOG.md` or `docs/planning/BACKLOG.md` at all, so
# those two are here by analogy to the root basename.
# THE SET IS NEVERTHELESS UNCHANGED, and that is a decision rather than an oversight. The row
# reports a real property — whether one read delivers the file — which stays true whoever reads
# it and however rarely. What was wrong was the REASON given, and a reason nobody re-checks is how
# this defect got here. Narrowing the population was deferred to a separate, fleet-visible call —
# and Phase C1 has since MADE that call: it PARTITIONED the six names without removing any, and
# the two `docs/**` locations were kept deliberately, on evidence, for the reason stated with the
# classes below. So the sentence above is still true, and it is now true by decision twice over
# rather than by deferral.
#
# Written as a literal, NOT derived from METHODOLOGY_ITEMS, because two of that checklist's file
# entries — SESSION_RUNNER.md and SAFEGUARDS.md — are TRACKED dests in bin/_manifest.py: files we
# install and keep current. Flagging those would re-earn Layer 7's narrowing at fleet scale, since
# one canonical breach would light up every adopter at once over a file they cannot edit. Every
# name below is a SEED dest (bin/sync writes a short stub once; adopter-owned forever after) or
# never a dest at all, so every line past the cap is the adopter's own record. A canonical test
# asserts that against bin/_manifest.py rather than restating it in a comment here.
#
# ROADMAP.md is a SEED too and is deliberately absent: the runner cites it as a pointer, never as
# a file read whole to compute anything. Absent above all: a book chapter. Nobody is instructed to
# read chap07.md in full, so truncating it produces no wrong answer — flagging it would re-create
# the very false positive BL-5's ext filter, one signal over, exists to kill.
#
# --- Phase C1: THE POPULATION IS TWO CLASSES, AND THE DIFFERENCE IS NOT COSMETIC ---------------
# The six names above were one set, and the paragraph before this one records what that cost: a
# justification that was FALSE for two of them, standing because nobody re-derived it. The split
# below is read off two INDEPENDENT, machine-checkable facts, never off judgment:
#
#   Class A   the trimmer has a config entry for it (its basename is a key of LEDGERS), AND the
#             protocol consumes it through a FRONTIER (`git log -1 --format=%H -- <file>`) or one
#             record at a time (Phase 3A), never as a whole file. Records are dated/fenced and
#             newest-on-top, so delivery being an ORDERED PREFIX means truncation removes the
#             OLDEST records -- the ones nothing was reading. Measured across 85 transcripts of
#             this repo: each root ledger was read WHOLE exactly ONCE, in PART 1,696/1,797 times.
#
#   Class B   the trimmer answers NO_CONFIG by design, AND the instructed access path IS the file
#             (SESSION_RUNNER.md steps 2 and 3), with NO REMEDY the reader can reach -- no
#             distributed file says what to do about an oversized one, which is the gap that
#             separates this class from A far more sharply than any threshold does.
#             ⚠ BL-88 P2: in a project whose OWN trimmer declares a Class B basename -- read from
#             that trimmer's source by _parse_trim_ledgers, never by running it -- the NO_CONFIG
#             conjunct and the NO-REMEDY half of the second are false FOR THAT PROJECT, so its row
#             names the remedy and takes Class A's severity. The access path is still the file,
#             and the name stays Class B: membership is declared, never read from LEDGERS.
#             ⚠ ORDERING: no Class B file has an ordering that GUARANTEES the needed part is in
#             the delivered prefix -- and the qualifier is the whole claim, so it is not dropped
#             here. An earlier draft of this comment said flatly "there is no record ordering that
#             puts the needed part at the top", which is FALSE of SESSION_NOTES.md: step 2 tells a
#             session to "focus on the ACTIVE TASK section at the top", the seed puts that heading
#             at line 9, and across 11 fleet repos it sits at byte offsets 132-23,013 -- inside
#             READ_CAP_BYTES in all 10 that have it. The true statement is that nothing ENFORCES
#             it, and the fleet shows both ways that fails: one file carries 23 KB of prose above
#             its ACTIVE TASK, and ONE (mts-system, 269,652 B) has no such heading at all -- zero
#             `## ` headings, its records opening at `### Session N`. Past READ_REFUSE_BYTES
#             ordering buys nothing for either class anyway. Where the absolute
#             form IS true is the backlogs: a backlog's bottom items are as live as its top ones,
#             so a truncated read silently loses OPEN WORK and the reader is told THAT something
#             was cut, never WHAT. (This correction is the paragraph above happening again --
#             a class justification asserted for all its names while holding for only some. It was
#             caught by review, not by a check, because no check here can reach prose.)
#
# WHY BOTH SETS ARE WRITTEN OUT AND THE UNION IS DERIVED, RATHER THAN THE REVERSE. Deriving the
# CLASS from the trimmer would make widening LEDGERS silently reassign a file -- exactly what
# read-cap-phase-c-plan.md section 10 dragon 6 says must FAIL rather than follow. So each class is
# DECLARED and a canonical test PINS Class A against the trimmer's own LEDGERS table; adding a
# name there without moving it here turns that test red, which is the point. Deriving the UNION
# instead is what makes "the population did not change" provable rather than asserted -- Phase C1
# moves no threshold (plan sections 8 and 9; section 7's A1 row, which reads otherwise, is the
# summary that drifted, and the threshold move is Phase C2).
#
# DISPOSITION OF THE TWO `docs/**` BACKLOG LOCATIONS: KEEP, BY ANALOGY, AND THE ANALOGY IS SAID
# OUT LOUD. Plan section 9 requires this be DECIDED rather than inherited. Neither is named as a
# file to read anywhere in SESSION_RUNNER.md or SAFEGUARDS.md, and across the whole DISTRIBUTED
# .md corpus (23 files at S176, taken off bin/_manifest.py's SOURCE column) both appear ZERO
# times. `docs/planning/BACKLOG.md` appeared once, in fork Learning #26, which cites this repo's
# own backlog as a WORKED EXAMPLE, not as a file anyone is told to open -- and that row left the
# distributed corpus for docs/FORK_LEARNINGS.md at the S176 resync. So they are watched by analogy
# to the root basename, and that is a weaker warrant than the other four have. They are kept
# anyway, for the reason plan section 7 rejects option D on:
# the row reports a REAL PROPERTY -- does one read deliver this file? -- which stays true however
# rarely anyone reads it, and dropping a name is a fleet-visible narrowing that buys nothing.
# Measured cost of keeping them: `docs/BACKLOG.md` matches NO file in the 5-repo fleet, so it
# emits nothing; `docs/planning/BACKLOG.md` matches exactly one, THIS repo's, at 0.54x the cap.
# A canonical test pins the "no protocol basis" half of that reasoning, so the day a protocol
# edit gives one of them a basis, this comment is forced to be revisited instead of quietly
# becoming false -- which is the failure the paragraph above records.
READ_CAP_CLASS_A = frozenset(("CHANGELOG.md", "HANDOFFS.md"))  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
READ_CAP_CLASS_B = frozenset(("SESSION_NOTES.md",) + _BACKLOG_LOCATIONS)  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations

# DERIVED, never re-listed. Phase C1's whole claim is that it repartitions this set without
# changing it, and a third literal spelling of the six names would make that claim unprovable.
READ_CAP_WATCHED = READ_CAP_CLASS_A | READ_CAP_CLASS_B


def read_cap_class(rel_posix):
    """"A", "B", or None for a name this scanner does not watch.

    The one place that knows the partition. Callers ask the question rather than re-deriving it
    from a membership test against the trimmer's grammar table -- which is what collect_trim_metrics
    did before Phase C1, and which was correct only because the two happened to coincide. They
    still coincide, and a canonical test asserts that they do; the difference is that the
    coincidence is now checked rather than relied on."""
    if rel_posix in READ_CAP_CLASS_A:
        return "A"
    if rel_posix in READ_CAP_CLASS_B:
        return "B"
    return None

# --- S38: the trim-trigger row ------------------------------------------------------------------
# D4(b) above reports a file that is ALREADY truncating. This reports the file that is heading
# there, and names what to do about it. The two are separate risks on purpose and neither
# subsumes the other: the ledgers in this repo are both well under the line cap today and both
# already over the byte budget, so a cap-only reporter is silent about the live problem.
#
# THE ARCHITECTURE, AND WHY THE DASHBOARD COMPUTES RATHER THAN ASKS. The design (§1.3) says the
# dashboard "reads the number rather than re-deriving it" AND that S38 owes an agreement test --
# "with the trimmer present, the dashboard's displayed headroom equals --check's". Those cannot
# both hold. A number OBTAINED by parsing `--check` makes that test an identity, which cannot
# fail; the repo has already paid for that mistake once (fork Learning #16 -- three losslessness
# guards inert at their call site behind a 13/13 mutation score). The owed test is only
# meaningful if the two sides are computed independently, so this module computes the line
# metric itself and the test compares it against a real `--check` run.
#
# That also keeps the rows READ-ONLY, which the ratified architecture requires, and matches
# §7.1's stated precedent: check_stale_version()/parse_version() interrogate another executable
# BY REGEX, without importing or running it. Nothing here executes a file it discovered.
#
# What is genuinely the trimmer's and cannot be re-derived is the BYTE BUDGET -- a judgment
# calibrated in design §5.4, not a formula. It is read out of the tool's source by regex, the
# same way parse_version reads DASHBOARD_VERSION. No budget -> the byte half abstains out loud
# (decision D4: a 0 from an unread source must not be reported as a clean state), and the line
# half, whose formula is published in CHANGELOG.md's own front matter, still answers.
TRIM_TOOL_NAME = "methodology_trim.py"  # layout: ok -- this tool's own file name, the key of _FRAMEWORK_INSTALLED_CONTENT; found through layout_locations

# The framework repo authors the tool under starter-kit/ and does not install a copy at its own
# root, exactly as it does for methodology_dashboard.py. So the root probe misses HERE, and the
# fallback is what lets the "present" branch be observed on the one repo whose trigger fires.
#
# ITS ORIGINAL REASON EXPIRED AT S39' AND THE SURVIVING ONE IS NARROWER. When this was written the
# tool was canonical-only, so the root probe missed on EVERY repo in existence and the present
# branch would have shipped never having run anywhere. `bin/sync` now installs the trimmer at
# adopter roots, so the root probe is the live path for every adopter and this fallback covers
# exactly one case: the framework repo scanning itself. Measured on a real sync rather than
# reasoned about -- find_trim_tool() on a freshly synced throwaway repo returns
# `methodology_trim.py` (the ROOT candidate), v1.0.0, budget 65536, and the fleet-wide `low`
# "watched but unmeasured" abstention row is gone from its risk list.
#   python3 -c "import sys;sys.path.insert(0,'bin');import _manifest as m;\
#     print([e for e in m.DISTRIBUTION if 'trim' in e[0]])"
#   -> [('starter-kit/methodology_trim.py', 'methodology_trim.py', 'tracked')]  since S39'
TRIM_TOOL_FRAMEWORK_REL = "starter-kit/" + TRIM_TOOL_NAME

_TRIM_VERSION_RE = re.compile(r'''^TRIM_VERSION\s*=\s*["']([^"']+)["']''', re.MULTILINE)

# DEFAULT_BUDGET_BYTES is written `64 * 1024`, NOT as a plain integer -- a digits-only regex
# matches nothing and silently reports "no budget", which looks exactly like "tool absent". The
# product form is parsed explicitly and multiplied; no eval, and a test pins the parsed value
# against the trimmer's real module constant so the two cannot drift apart unnoticed.
_TRIM_BUDGET_RE = re.compile(
    r"^DEFAULT_BUDGET_BYTES\s*=\s*([0-9_]+(?:\s*\*\s*[0-9_]+)*)", re.MULTILINE)

# TRIM_LINE_FIRE_BELOW IS GONE (Phase B). It was a SECOND distributed copy of design §5.2's
# published rate rule -- "archive when headroom falls below 15 records" -- pinned to the trimmer's
# literal by a canonical test. The rule itself was deleted from the trimmer, not re-tuned: it is
# denominated in records of headroom TO the cap, and a one-read CHANGELOG.md holds 20.9 records
# while a one-read HANDOFFS.md holds 4.3, so "cut until headroom is back above 30" is
# unsatisfiable on both at every honest cap. Keeping a copy here would leave the reporter
# advertising a threshold the remedy no longer has. The read metric is now a LEVEL and needs no
# rate constant on either side.

TRIM_ARCHIVE_DIR = "docs/archive"  # layout: ok -- the legacy half of TRIM_ARCHIVE_DIRS: the shard directory beside a root ledger

# U+00B7 MIDDLE DOT, spelled as an ESCAPE rather than pasted. Not for ASCII purity -- this file
# already carries 136 em-dashes and a handful of other non-ASCII characters. The reason is that
# a middle dot is visually indistinguishable from its lookalikes (U+2022, U+2027, U+30FB) inside
# a regex, where picking the wrong one silently stops matching and the count quietly drifts. The
# escape names the codepoint so a reviewer can check it. It is load-bearing, not decoration: the
# trimmer anchors a CHANGELOG record on the dated, SOURCE-TAGGED heading, so a looser
# `^### <date>` would count headings the trimmer does not and break the agreement test.
#   python3 -c "import collections,pathlib;print(collections.Counter(c for c in \
#     pathlib.Path('tools/methodology_dashboard.py').read_text() if ord(c)>127))"
_MIDDLE_DOT = "\u00b7"

# The ledgers the trimmer actually has a config entry for. READ_CAP_WATCHED is deliberately
# WIDER -- it holds six names, including SESSION_NOTES.md and three BACKLOG.md locations -- and
# the trimmer answers NO_CONFIG on every one of those by design ("there is deliberately no
# generic fallback: a generic rule is what would mis-zone a differently-shaped ledger"). Naming
# the trimmer as the remedy for a file it refuses would be a pointer the adopter cannot follow,
# which is the misdirection §7.3 exists to prevent. A canonical test asserts these keys against
# the trimmer's own LEDGERS table rather than restating them here.
TRIM_GRAMMARS = {
    "CHANGELOG.md": ("heading",  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
                     re.compile(r"^### \d{4}-\d{2}-\d{2} " + _MIDDLE_DOT + r" \[")),
    "HANDOFFS.md": ("fence", "handoff"),  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
}
# Applied per LINE by _trim_record_count, so `^` is a string anchor here and re.MULTILINE is
# deliberately absent. Compiling it with MULTILINE and then calling .findall over the whole text
# would count the same headings, but only until a fenced example contained one -- which the two
# seed ledgers both do, and which is the case that must not be counted.

_TRIM_FENCE_RE = re.compile(r"^(`{3,}|~{3,})(.*)$")

# Doc-only / research-repo scoring reshape (BL-5). A document-only repo (papers, dissertations,
# technical reports, regulatory analyses — the Research-Documentation workstream population, and
# partly this framework's own doc corpus) has nothing to unit-test, so the code-centric Testing
# dimension and its risks are a false penalty. When a repo is detected as doc-only, the second
# 0-20 score slot (dict key "testing", kept stable for JSON/portfolio/radar) is filled by a
# Render/Verification score instead, and the no-test-infra / thin-coverage risks are suppressed.
#
# The Render/Verification score is an HONEST PROXY: a static git+file scan cannot execute a
# render, so it measures render/verification *configuration and wiring* (toolchain configs, the
# v2.5 render-dependency checks like pdffonts/fc-list/kpsewhich, a docs-render / link-check CI
# pipeline, Research-Documentation verification artifacts) — never render *success*. It is
# labeled a proxy in the HTML card. Like every dimension here it is advisory; nothing hard-fails.
#
# Detection is marker-override -> source-cap -> corpus-disjunction (see detect_doc_only). The
# source cap keeps a mixed tooling repo (real code that should be tested) from being silently
# exempted; the bidirectional .methodology-profile marker lets an owner force either classification.
# These three thresholds are deliberate, stated round-number heuristics, not derived from a
# measured corpus of adopter repos — record that plainly rather than let the round numbers read
# as calibrated. DOC_ONLY_SOURCE_LOC_MAX in particular decides which of two scoring regimes a
# repo gets (see the 148-LOC misclassification documented near FRAMEWORK_INSTALLED_DOCS below), so a
# regression test pins the current value: change it deliberately, not by accident.
DOC_ONLY_SOURCE_LOC_MAX = 200            # source LOC at/below this is "essentially no real code"
DOC_ONLY_DOC_LOC_MIN    = 200            # doc LOC at/above this signals a real doc corpus
DOC_ONLY_DOC_FILES_MIN  = 3              # this many doc files also signals a real doc corpus

# The .methodology-profile marker answers TWO independent questions as of 2.10.0, so it is named
# for the file rather than for either axis. Each axis is a bidirectional pair: naming one token
# forces that classification, naming both abstains on THAT AXIS ONLY (decision D4 — a
# declaration this scanner cannot read is disclosed, never resolved by guessing), and tokens
# belonging to neither pair are ignored so an older synced twin cannot crash or flip on a marker
# naming an axis it has never heard of.
#
# The two pairs must stay DISJOINT: one file is one token bag, so a token serving both axes would
# let a single word silently answer two questions. A canonical test asserts it.
PROFILE_MARKER        = ".methodology-profile"
PROFILE_CORPUS_TOKENS = ("doc-only", "code")        # is there anything here to unit-test? (BL-5)
PROFILE_ROLE_TOKENS   = ("framework", "adopter")    # does this repo publish the methodology?


# === HELPERS ===

def git_cmd(path, *args, timeout=5):
    try:
        result = subprocess.run(
            ["git", "-C", str(path)] + list(args),
            capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


def git_show(path, spec, timeout=10):
    """`git show <spec>` as TEXT, unstripped, or None when it fails.

    Deliberately not git_cmd: that helper .strip()s its output and returns "" on failure. Both
    are wrong for a blob whose LINE COUNT is the thing being measured -- stripping silently
    drops leading and trailing blank lines, and "" makes an unreadable baseline look like an
    empty file rather than a reason to abstain.

    ENCODING IS PINNED, not left to the locale. `text=True` alone decodes with
    locale.getpreferredencoding(), so the same repo read under a non-UTF-8 LC_ALL decodes the
    middle dot in a dated CHANGELOG heading (0xC2 0xB7) as two characters, the record regex stops
    matching, the baseline record count collapses toward zero and the reported headroom inflates.
    The trimmer's own baseline read is `git_bytes(...).decode("utf-8", "replace")`, which is
    locale-independent; this matches it exactly, errors and all, so the two cannot drift apart on
    a machine neither of them chose."""
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "show", spec],
            capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    return result.stdout if result.returncode == 0 else None


def count_lines(filepath):
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except (OSError, UnicodeDecodeError):
        return 0


def categorize_file(rel_path, ext, name):
    rel_str = str(rel_path).replace("\\", "/").lower()
    # Test detection
    name_lower = name.lower()
    if any(p in name_lower for p in ["test_", "_test.", ".test.", ".spec."]):
        return "test"
    if any(p in rel_str for p in ["tests/", "__tests__/", "test/"]):
        return "test"
    if ext in SOURCE_EXTS:
        return "source"
    if ext in DOC_EXTS or "docs/" in rel_str:
        return "docs"
    # A dotfile has no Path.suffix, so the dotfile names CONFIG_EXTS lists (.gitignore, .editorconfig,
    # .eslintrc, .prettierrc) can only match on the whole name — they never matched before 2.11.3.
    if ext in CONFIG_EXTS or name in CONFIG_FILES or name.lower() in CONFIG_EXTS:
        return "config"
    if ext in ASSET_EXTS:
        return "assets"
    return "other"


def open_in_browser(filepath):
    """Open a file in the default browser, cross-platform."""
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(["open", str(filepath)])
        elif system == "Linux":
            subprocess.run(["xdg-open", str(filepath)])
        elif system == "Windows":
            os.startfile(str(filepath))
    except (OSError, FileNotFoundError):
        print(f"  Could not open browser. Open manually: {filepath}")


# === CANONICAL / SYNC ===

# The canonical dashboard lives at <portfolio>/methodology/starter-kit/methodology_dashboard.py.
# Every other copy (portfolio root + per-project) is a synced copy of it. The helpers below let
# any copy locate the canonical, compare versions, warn when it has gone stale, and (re)distribute
# the canonical to the portfolio root + every project (the --sync flag).
CANONICAL_REL = Path("methodology") / "starter-kit" / "methodology_dashboard.py"

_VERSION_RE = re.compile(r'''^DASHBOARD_VERSION\s*=\s*["']([^"']+)["']''', re.MULTILINE)

# Non-markdown files `bin/sync` installs into an ADOPTER project root, as adopter-relative dest
# paths, each paired with HOW THAT FILE PROVES IT IS OURS. Installing the methodology must not
# change how the adopter's OWN code is measured: these executables are thousands of lines against a
# 200-LOC doc-only cap, so counting them as adopter source made `bin/sync` destroy the very
# fair-scoring v3.2 shipped (a synced Quarto book flipped doc_only True -> False and got its "No
# test infrastructure" penalty back). The signal did not mean what it appeared to mean: it meant
# *we put our own tools in your repo and then counted them against you*. See §"Layer 7" of the
# campaign plan, which lives on the fork's `main` only:
# https://github.com/rmsharp/methodology/blob/main/docs/planning/dashboard-signal-integrity-plan.md
#
# Mirrors the non-markdown dests in bin/_manifest.py; a canonical test asserts the two agree, so
# the pair cannot drift silently (that plan's §8 learning 1 — make the cross-reference
# machine-checkable, not re-greppable). Markdown dests are deliberately NOT listed: this table
# exists to correct the source-LOC read, and a general "skip framework files" rule is exactly the
# laundering hole the exclusion must not become.
#
# WHY A TABLE AND NOT A TUPLE (S39', when the trimmer became the second installed executable).
# The membership list and the content gate were separate before, and that made one specific wrong
# edit both easy and green: `test_exclusion_list_matches_the_manifest` goes red the moment the
# manifest grows a non-markdown dest, and the cheapest way to green it is to append the name here.
# Measured, that edit accomplishes NOTHING — with `methodology_trim.py` on the old tuple and no
# content branch for it, the adopter fixture still read doc_only False, source_loc 1,632 and a HIGH
# "No test infrastructure". A green 323-test suite over a live fleet-wide regression. Deriving
# FRAMEWORK_INSTALLED_SOURCE from these keys makes that edit unwritable: a name reaches the
# exclusion only by declaring how it identifies itself.
#
# Each value is (version_pattern, structural_signatures). A file passes if the version pattern
# matches, or if it carries >= _FRAMEWORK_SIGNATURE_MIN of the signatures. An EMPTY signature tuple
# means "no structural fallback": sum(...) over it is 0, which cannot reach the minimum of 2, so the
# version constant is then the only way in. That is correct for a tool with no pre-constant releases
# in the wild, and it is pinned by a test rather than left to arithmetic a reader has to redo.
#
# The two patterns are deliberately DISTINCT rather than one generic version matcher. Widening
# _VERSION_RE would have been the smaller diff and it has two other consumers — parse_version() and
# check_stale_version(), which drives the "methodology_dashboard.py is stale" warning — so it would
# have changed staleness reporting as a side effect. Distinct patterns also mean neither tool's
# constant can launder the other's file, which a shared any-marker rule would have allowed.
# Structural signatures of the SCANNER, for copies too old to carry DASHBOARD_VERSION. Two must
# match. Three are ordinary function names, so two hits are suggestive rather than proof — this is
# a heuristic, and the .methodology-profile marker is the documented override. Measured need: a
# live adopter (feedback-loop-comparison) still runs a 1,614-line pre-version copy, and a
# DASHBOARD_VERSION-only gate silently skipped it — the fix quietly not applying is the same class
# of defect as the fix being wrong. (Moved up from below `is_framework_installed` at S39' so it is
# defined before the table that consumes it; the constant and its rationale are unchanged.)
_FRAMEWORK_SIGNATURES = (
    "METHODOLOGY_ITEMS",
    "def collect_all",
    "def score_health",
    "def assess_risks",
    "https://github.com/KJ5HST/methodology",
)
_FRAMEWORK_SIGNATURE_MIN = 2

# Arriving via upstream/main's PR #66 (context-budget gate, FM #28): a version constant, for a
# copy new enough to carry one (mirrors _VERSION_RE's own shape).
_CONTEXT_BUDGET_VERSION_RE = re.compile(r'''^VERSION\s*=\s*["']([^"']+)["']''', re.MULTILINE)
_CONTEXT_BUDGET_SIGNATURES = (
    "context_budget.py — size budgets",  # layout: ok -- a name printed in a message, never opened
    "CONFIG_NAME",
    "HISTORY_NAME",
    "growth_run",
)
# The seed config has no version constant of its own — signatures are the only way in (see the
# version_re-is-None guard in is_framework_installed). Structurally unreachable today:
# is_framework_installed() is only called when category == "source", and categorize_file()
# always buckets a .json extension as "config" (CONFIG_EXTS), never "source" — so this entry
# can never affect source-LOC either way. Given a real signature anyway so the completeness
# test below needs no special case that could hide a future gap if that call-site guard, or
# this file's extension, ever changes.
_CONTEXT_BUDGET_JSON_SIGNATURES = (
    "bytes_per_token",
    "fixed_harness_tokens",
    "growth_run",
    "calibrate_against",
)

# Arriving via upstream/main's PR #82 (the quality ratchet): a third installed executable, with its
# own `VERSION` constant and upstream's four structural signatures. Its pattern is the same text as
# the context-budget gate's, because both tools name their constant `VERSION` -- so, unlike the
# scanner's and the trimmer's, those two constants do satisfy each other's check (see
# is_framework_installed's docstring).
_QUALITY_RATCHET_VERSION_RE = re.compile(r'''^VERSION\s*=\s*["']([^"']+)["']''', re.MULTILINE)
_QUALITY_RATCHET_SIGNATURES = (
    "quality_ratchet.py — declared quality thresholds",  # layout: ok -- a name printed in a message, never opened
    "CONFIG_NAME",
    "def precommit",
    "def run_gates",
)
# Its seed config, like .context-budget.json above: no version constant, the same structural
# unreachability, and a real signature set for the same reason. The seed's `_example` gate carries
# these keys even while `gates` is empty, so a freshly seeded file matches.
_QUALITY_GATES_JSON_SIGNATURES = (
    "results_file",
    "\"direction\"",
    "\"threshold\"",
    "quality_ratchet.py",  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
)

# The ledger merge-driver seed (starter-kit/gitattributes, installed once as `.gitattributes`): no
# version constant, and like the two JSON seeds above it can never reach source-LOC (a dotfile is
# categorized as config by name), so its signatures exist for the completeness test. They are lines
# of the shipped seed's own comments and rules.
_GITATTRIBUTES_SIGNATURES = (
    "Methodology ledgers",
    "CHANGELOG.md merge=union",  # layout: ok -- a name printed in a message, never opened
    "HANDOFFS.md is deliberately NOT listed",  # layout: ok -- a name printed in a message, never opened
)

_FRAMEWORK_INSTALLED_CONTENT = {
    "methodology_dashboard.py": (_VERSION_RE, _FRAMEWORK_SIGNATURES),  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    # The trimmer has no pre-constant releases in the wild — v1.0.0 is its first shipped version and
    # it has declared TRIM_VERSION since it was written — so it gets no structural fallback. See the
    # empty-tuple paragraph above for why that is a refusal and not a hole.
    TRIM_TOOL_NAME:            (_TRIM_VERSION_RE, ()),
    "context_budget.py":       (_CONTEXT_BUDGET_VERSION_RE, _CONTEXT_BUDGET_SIGNATURES),  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    "quality_ratchet.py":      (_QUALITY_RATCHET_VERSION_RE, _QUALITY_RATCHET_SIGNATURES),  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    ".context-budget.json":    (None, _CONTEXT_BUDGET_JSON_SIGNATURES),  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    ".quality-gates.json":     (None, _QUALITY_GATES_JSON_SIGNATURES),  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    ".gitattributes":          (None, _GITATTRIBUTES_SIGNATURES),  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
}

# Derived, never hand-written — see the paragraph above. Order follows the dict, which follows
# bin/_manifest.py's DISTRIBUTION order, because the manifest-agreement test compares ORDERED
# tuples (its sibling markdown assertions are set-compared and say so).
FRAMEWORK_INSTALLED_SOURCE = tuple(_FRAMEWORK_INSTALLED_CONTENT)

# The markdown half of the same problem, and the mirror of the defect above. `bin/sync` also
# installs 23 markdown files, which on its own satisfies detect_doc_only's corpus
# disjunction (>= 3 doc files). Excluding only the scanner therefore FLIPPED the defect rather
# than fixing it: a 148-LOC utility repo that correctly read `code` before sync read `doc-only`
# after it, and lost a TRUE "No test infrastructure" risk. The old source cap had been masking
# that; removing the cap's grip on synced repos exposes it.
#
# ALL 23 markdown dests are listed, TRACKED *and* SEED. Listing only the 19 TRACKED ones was
# tried first, on the reasoning that a SEED is adopter-owned from creation (bin/_manifest.py) —
# and MEASURED AGAINST A REAL `bin/sync` RUN it does not close the hole: the four seeds
# (SESSION_NOTES/CHANGELOG/HANDOFFS/ROADMAP) plus the adopter's own README are 5 doc files, which
# clears DOC_ONLY_DOC_FILES_MIN (3) by themselves, so the 148-LOC fixture still flipped to
# doc-only. At sync time a seed is OUR template, not the adopter's writing; it only becomes their
# content later. The corpus question is "does this repo hold a real document corpus?", and a set
# of methodology bookkeeping files is not one no matter who later edits it.
#
# Used ONLY by detect_doc_only's corpus check, by operator decision: the question "is this a
# DOCUMENT project?" must not be answered with documents we installed. No content check is needed
# here (unlike the source list): excluding docs can only make doc-only classification HARDER, so
# a repo cannot use this list to launder anything — it would only penalize itself.
#
# SPLIT INTO THREE TIERS by how much a name's mere presence PROVES. Layer 7 split "distinctive"
# from "seed" and gated only the seeds; Layer 8 corrected where that line falls, because six of
# the names it called distinctive are nothing of the kind.
#
# Only a path UNDER docs/methodology/ is self-evidencing. That directory is this framework's own
# install location, so nothing lands there by coincidence.
#
# A bare ROOT filename proves nothing on its own, and calling it distinctive was a MEASURED
# REGRESSION against the pre-Layer-7 scanner: a documentation project that never heard of this
# framework, whose corpus was its own 302-line root `BOOTSTRAP.md`, had that file discounted, fell
# under DOC_ONLY_DOC_LOC_MIN, flipped `doc-only -> code`, and gained a false HIGH "No test
# infrastructure" — v3.2's exact false penalty, re-created a second time by the fix for its mirror.
# `BOOTSTRAP.md` and `SAFEGUARDS.md` are ordinary names for any onboarding or policy repo.
# Worse, ONE coincidental root name also unlocked the seed fold-in below, so the same repo's own
# CHANGELOG.md and ROADMAP.md were discounted too — one accident defeating the very gate Layer 7
# added to protect those four. Found by the pre-PR review; reproduced under both scanners.
FRAMEWORK_DISTINCTIVE_DOCS = (
    "docs/methodology/ITERATIVE_METHODOLOGY.md",  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    "docs/methodology/FRAMEWORK_APPARATUS.md",  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    "docs/methodology/HOW_TO_USE.md",  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    "docs/methodology/workstreams/DESIGN_WORKSTREAM.md",  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    "docs/methodology/workstreams/ARCHITECTURE_WORKSTREAM.md",  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    "docs/methodology/workstreams/DEVELOPMENT_WORKSTREAM.md",  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    "docs/methodology/workstreams/AUDIT_WORKSTREAM.md",  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    "docs/methodology/workstreams/RESEARCH_DOCUMENTATION_WORKSTREAM.md",  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    "docs/methodology/workstreams/TEMPLATE_WORKSTREAM.md",  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    "docs/methodology/workstreams/RESEARCH_EXHAUSTIVE_VERIFICATION_CAMPAIGN.md",  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    "docs/methodology/workstreams/INHERITED_CODEBASE_FAMILIARIZATION_CAMPAIGN.md",  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    "docs/methodology/workstreams/TEMPLATE_CAMPAIGN.md",  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
)

# The seven TRACKED root dests. `bin/sync` installs every one of them, so a real install always
# carries all seven — but any single one can also be a coincidence, so they are discounted only
# behind the same evidence gate as the seeds (see _framework_docs_are_evidenced).
FRAMEWORK_AMBIGUOUS_DOCS = (
    "SESSION_RUNNER.md",  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    "FRAMEWORK_LEARNINGS.md",  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    "SAFEGUARDS.md",  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    "RECOMMENDED_SKILLS.md",  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    "CONTEXT_TEMPLATE.md",  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    "CLAUDE_TEMPLATE.md",  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    "BOOTSTRAP.md",  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
)

# The full markdown dest set, kept as the union so the canonical drift test against
# bin/_manifest.py keeps checking all 23 names rather than silently narrowing to a subset.
FRAMEWORK_INSTALLED_DOCS = FRAMEWORK_DISTINCTIVE_DOCS + FRAMEWORK_AMBIGUOUS_DOCS

# How many of the seven ambiguous root names must co-occur to stand in for a docs/methodology/ path.
# `bin/sync` writes all seven, and README.md's manual Option B copies them as a set, so a genuine
# install clears this easily. A doc repo that happens to own three of these EXACT names is not a
# coincidence worth protecting. One or two is (BOOTSTRAP.md alone; BOOTSTRAP.md + SAFEGUARDS.md).
FRAMEWORK_AMBIGUOUS_EVIDENCE_MIN = 3

# The four SEED dests. These names are ORDINARY — thousands of repos author a CHANGELOG.md or a
# ROADMAP.md and never heard of this framework — so they are discounted only when one of the
# distinctive dests above proves the framework really was installed. Discounting them
# unconditionally was a measured regression: a spec repo that never ran `bin/sync`, whose corpus
# lived in its own 900-line CHANGELOG.md, lost that file from the corpus check, flipped
# `doc-only -> code`, and gained a false HIGH "No test infrastructure" — the exact false penalty
# v3.2 exists to remove, re-created by the fix for its mirror. Found by the delta boundary review.
#
# The evidence gate is deliberately NOT "is the installed scanner present": BOOTSTRAP.md documents
# a manual-copy install, and three real fleet repos carry framework markdown with no root scanner,
# so keying on the scanner would silently stop discounting for them.
FRAMEWORK_SEED_DOCS = (
    "SESSION_NOTES.md",  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    "CHANGELOG.md",  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    "HANDOFFS.md",  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
    "ROADMAP.md",  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations
)

# === LAYOUT (BL-101 P5; docs/planning/methodology-subdirectory-plan.md sections 4.1 and 4.3) ===========
#
# A project keeps its methodology files at its root (legacy) or one level down in methodology/ (new), and
# resolve_layout (the marked block near the top) answers which, from ONE anchor file the caller chooses:
# the framework's own files resolve through the runner, and a state file (a ledger, the notes, a config)
# through ITSELF, because the plan's tier 1 moves the first group and leaves the second at the root. Every
# name in this scanner's tables stays the LEGACY name (SESSION_RUNNER.md, docs/methodology/...): the card,
# the JSON export, the portfolio grid and the history all key on them. What changes is where a name is
# LOOKED FOR, in layout_locations() below, and a name found in a layout it does not belong to (the
# project's own root CHANGELOG.md, beside the framework's under methodology/) is the project's own and is
# never read as the framework's: the resolver's tie rule, decided for every tool at S276.
NEW_LAYOUT_DIR = "methodology"  # layout: ok -- the directory a migrated project keeps its methodology files in (plan 4.1)
RUNNER_NAME = "SESSION_RUNNER.md"  # layout: ok -- the framework anchor the resolver reads: where it is tracked decides the layout

# The state files, each its own anchor: the seeded ledgers and notes, and the three seeded configs.
LAYOUT_STATE_NAMES = FRAMEWORK_SEED_DOCS + (".context-budget.json", ".quality-gates.json", ".gitattributes")  # layout: ok -- the LEGACY name of a methodology file, the key every table and the card use; where it lives is resolved by layout_locations

# Every legacy-relative name the layout moves: the 30 destinations of bin/_manifest.py, derived from the
# tables above (a canonical test compares them to the manifest) plus the two directories the checklist scores.
LAYOUT_MOVED = (frozenset(FRAMEWORK_INSTALLED_DOCS) | frozenset(LAYOUT_STATE_NAMES)
                | frozenset(FRAMEWORK_INSTALLED_SOURCE)
                | frozenset(("docs/methodology", "docs/methodology/workstreams")))  # layout: ok -- the checklist's directory items, by their legacy names


def new_layout_rel(rel):
    """Where a legacy-relative methodology name lands in the new layout: flat under methodology/, with
    workstreams/ the one subdirectory, and docs/methodology/ dropped (plan decision D2)."""
    if rel == "docs/methodology":  # layout: ok -- the legacy docs/methodology/ prefix the new layout drops (plan decision D2)
        return NEW_LAYOUT_DIR
    if rel.startswith("docs/methodology/"):  # layout: ok -- the legacy docs/methodology/ prefix the new layout drops (plan decision D2)
        rel = rel[len("docs/methodology/"):]  # layout: ok -- the legacy docs/methodology/ prefix the new layout drops (plan decision D2)
    return NEW_LAYOUT_DIR + "/" + rel


def layout_anchor(rel):
    """The file whose location decides where `rel` lives: a state file is its own anchor, every other
    methodology file follows the runner (plan 4.3)."""
    return rel if rel in LAYOUT_STATE_NAMES else RUNNER_NAME


def layout_locations(path, rel):
    """Where the methodology file known by its legacy-relative name `rel` lives in the project at
    `path`: one Path, or two in a half-migrated tree (a file at either place counts, and the risk row
    carries the defect: never guess which copy is live). A name the layout does not move is read where it is."""
    if rel not in LAYOUT_MOVED:
        return [path / rel]
    kind = resolve_layout(path, layout_anchor(rel))[0]
    if kind == "new":
        return [path / new_layout_rel(rel)]
    if kind == "half":
        return [path / rel, path / new_layout_rel(rel)]
    return [path / rel]


# The directories a trim writes its shards and proofs into: docs/archive/ beside a root ledger, and
# methodology/archive/ beside one that moved (plan 4.1, methodology_trim.py 1.8.0).
TRIM_ARCHIVE_DIRS = (TRIM_ARCHIVE_DIR, NEW_LAYOUT_DIR + "/archive")


def layout_names(path):
    """(names, own) for classifying the files of one project by the names this scanner's tables hold.

    `names` maps the real relative path of each methodology file found under methodology/ to its LEGACY
    name; `own` holds the root-relative names that read as a methodology file's but are the PROJECT's own
    (the plan's tie rule, decided at S276: where the runner is under methodology/, the framework's
    CHANGELOG.md is methodology/CHANGELOG.md and a root one is the project's product changelog, which no
    methodology tool reads). A legacy or empty project gets two empty answers, so its files are classified
    by their own paths exactly as before. A half-migrated one maps the methodology/ copies and leaves the
    root copies as they are: never guess which copy is live."""
    names, own = {}, set()
    for rel in LAYOUT_MOVED:
        kind = resolve_layout(path, layout_anchor(rel))[0]
        if kind in ("new", "half"):
            names[new_layout_rel(rel)] = rel
        if kind == "new":
            own.add(rel)
    return names, own


DASHBOARD_NAME = "methodology_dashboard.py"  # layout: ok -- this tool's own file name, written by --sync into the place its project keeps it


def dashboard_copy_target(project_dir):
    """(path, refusal) of the dashboard copy a project keeps. `--sync` is a second sync channel outside the
    manifest (plan C15), so it resolves each target's layout itself: a migrated project's copy is
    methodology/methodology_dashboard.py and never also a root one; a legacy or empty project's is the
    root (the default until the contract stage); a half-migrated project has none to write, because
    nothing says which of its two layouts is live, and the refusal names both runner paths."""
    kind, _directory, found = resolve_layout(project_dir)
    if kind == "half":
        return None, "half-migrated: " + " and ".join(_relative_names(project_dir, found)) + " both exist"
    if kind == "new":
        return project_dir / NEW_LAYOUT_DIR / DASHBOARD_NAME, None
    return project_dir / DASHBOARD_NAME, None


def has_runner(path):
    """Whether the project holds a runner at either place: the adoption test, which used to ask the root alone."""
    return bool(resolve_layout(path, RUNNER_NAME)[2])


def _relative_names(path, found):
    out = []
    for f in found:
        try:
            out.append(Path(f).relative_to(path).as_posix())
        except ValueError:
            out.append(Path(f).name)
    return out


def project_layout(path):
    """{"kind", "directory", "found"} for a project: kind is new | legacy | half | none, directory "." or
    "methodology" (None for the last two), found the relative paths that settled it. The runner decides;
    a state file held at both places with no runner under methodology/ to break the tie also makes the
    project half-migrated, and that is named by the state file's own two paths."""
    kind, directory, found = resolve_layout(path, RUNNER_NAME)
    if kind != "half":
        for name in LAYOUT_STATE_NAMES:
            k, _d, f = resolve_layout(path, name)
            if k == "half":
                kind, directory, found = "half", None, f
                break
    where = None
    if directory is not None:
        where = "." if Path(directory) == Path(path) else NEW_LAYOUT_DIR
    # Where the action ledger lives, or would: its own anchor decides (tier 1 leaves it at the root).
    ledger = (NEW_LAYOUT_DIR + "/" if resolve_layout(path, "CHANGELOG.md")[0] == "new" else "") + "CHANGELOG.md"  # layout: ok -- the ledger's own file name: the resolver's anchor
    return {"kind": kind, "directory": where, "found": _relative_names(path, found), "ledger": ledger}


def is_framework_installed(rel_path, fpath):
    """True for a source file `bin/sync` installed at the adopter's project ROOT.

    Root-anchored, not basename-matched: an adopter's own `src/methodology_dashboard.py` stays
    their source, and the canonical repo's `tools/` + `starter-kit/` copies stay ITS source — it
    authors those files, so its own health score must keep paying for them.

    Content-verified, PER NAME: each installed executable proves itself with its own constant —
    the scanner with `DASHBOARD_VERSION` (or, for copies predating it, at least two structural
    signatures of the scanner), the trimmer with `TRIM_VERSION`, the context-budget gate and the
    quality ratchet each with its own `VERSION`. The pairing lives in `_FRAMEWORK_INSTALLED_CONTENT`,
    which this reads rather than re-stating, and which FRAMEWORK_INSTALLED_SOURCE is derived from — so
    no name can be excluded without declaring how it identifies itself. No tool's constant satisfies
    another entry's check, except that the last two name theirs alike: each one's `VERSION` satisfies
    the other's. The **whole file** is
    read,
    not a fixed prefix — an earlier version searched only the first 4096 bytes, and the real
    constant sits close enough to that boundary that ordinary growth of this module header would
    have crossed it, silently switching the exclusion off and regressing every doc-only adopter
    to the defect this exists to fix. (Measured at 2.10.1: byte 3,409, only 687 bytes clear of
    the old window. That margin is a snapshot, not an invariant — it was 1,572 bytes one commit
    earlier, and a single docstring addition consumed 56% of it, which is exactly the hazard.
    test_predicate_reads_the_whole_file_not_a_prefix is what actually holds the line.)
    A silent cliff inside the fix for a silent-signal bug is
    not a tradeoff worth keeping; the read costs nothing, since the file is read for line-counting
    anyway.

    **The threat model is accidental miscounting, not an adversarial adopter.** These checks make
    it unlikely that the scanner mistakes an adopter's own work for ours. They do NOT stop someone who
    deliberately pastes a version marker into their application to dodge a score — nothing
    file-local could, and the only thing they would win is a wrong dashboard for themselves.
    """
    content = _FRAMEWORK_INSTALLED_CONTENT.get(str(rel_path).replace("\\", "/"))
    if content is None:
        return False
    version_re, signatures = content
    try:
        with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
            text = fh.read()
    except OSError:
        return False
    # version_re is None for a file with no version constant of its own (e.g.
    # .context-budget.json) — signatures are then the only way in.
    if version_re is not None and version_re.search(text):
        return True
    hits = sum(1 for sig in signatures if sig in text)
    return hits >= _FRAMEWORK_SIGNATURE_MIN


# The losslessness proof `methodology_trim.py --write` leaves beside each shard it creates. Not a
# distributed file — the adopter's own tool WROTE it into their repo — which is why it needs its own
# predicate rather than an entry in the table above.
#
# WHY THIS EXISTS, and it is the defect S39' would otherwise have shipped. The exclusion above keeps
# the two installed executables out of the adopter's source count. It says nothing about what those
# executables PRODUCE. A single `--write` emits a fixed 220-line bash script into `docs/archive/`,
# and `.sh` is in SOURCE_EXTS — so a doc-only adopter who actually USES the tool we just shipped
# lands 220 lines of "their own source" against DOC_ONLY_SOURCE_LOC_MAX = 200, flips to `code`, and
# re-earns the false HIGH "No test infrastructure" risk that v3.2 exists to remove. Every subsequent
# trim adds another. Measured, not reasoned about: a real `--write` on a 28-record fixture gives
# `source_loc 220`, `doc_only False`. Shipping the tool while its ordinary use re-creates the
# regression the shipping work exists to prevent is shipping the defect by a different route.
#
# Three conditions, all required, so this cannot become a laundering hole: the file sits under the
# archive directory the trimmer writes to, it carries the `.verify.sh` suffix the trimmer gives it,
# and its content carries the generator banner. An adopter cannot get an arbitrary script exempted
# without putting it in that directory, under that name, with our banner in it — and the only thing
# they would win is a wrong dashboard for themselves (the same threat model as above).
_GENERATED_PROOF_SUFFIX = ".verify.sh"
_GENERATED_PROOF_BANNER = "generated by methodology_trim.py"  # layout: ok -- the banner text a generated proof carries, matched in file content and never opened as a path


def is_generated_proof(rel_path, fpath):
    """True for a losslessness-proof script `methodology_trim.py --write` generated in this repo."""
    rel_posix = str(rel_path).replace("\\", "/")
    if not any(rel_posix.startswith(d + "/") for d in TRIM_ARCHIVE_DIRS):
        return False
    if not rel_posix.endswith(_GENERATED_PROOF_SUFFIX):
        return False
    try:
        with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
            return _GENERATED_PROOF_BANNER in fh.read()
    except OSError:
        return False


def find_canonical(start):
    """Walk up from `start`, returning the resolved path to the canonical dashboard
    (methodology/starter-kit/methodology_dashboard.py), or None if not found locally.
    Silent-None lets adopters with no sibling methodology repo run without false warnings."""
    start = Path(start).resolve()
    for d in (start, *start.parents):
        candidate = d / CANONICAL_REL
        if candidate.is_file():
            return candidate.resolve()
    return None


def parse_version(path):
    """Read the DASHBOARD_VERSION string from a dashboard copy without importing it."""
    try:
        text = Path(path).read_text()
    except OSError:
        return None
    m = _VERSION_RE.search(text)
    return m.group(1) if m else None


def version_key(v):
    """Comparable tuple for a dotted version string (non-numeric chunks -> 0)."""
    key = []
    for chunk in str(v).split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        key.append(int(digits) if digits else 0)
    return tuple(key)


def check_stale_version():
    """Best-effort staleness check: if a newer canonical exists locally, warn on stderr.
    Silent when the canonical can't be found or when this copy IS the canonical.

    Issue #67 point 1: the remedy used to be the portfolio-wide --sync only -- disproportionate
    for a one-file problem. Now names both: the scoped fix for THIS copy first, the full sweep
    second."""
    self_path = Path(__file__).resolve()
    canonical = find_canonical(self_path.parent)
    if not canonical or canonical == self_path:
        return
    canon_ver = parse_version(canonical)
    if canon_ver and version_key(canon_ver) > version_key(DASHBOARD_VERSION):
        # The remedy must be PROPORTIONATE TO THE FINDING (issue #67). The finding is "this one
        # copy is old"; the old remedy was `--sync`, which is scoped from the CANONICAL's location
        # rather than the working directory, so it rewrites every discovered sibling — measured at
        # 26 files across 25 repos, including 7 creates in repos that do not gitignore the path and
        # 1 target where the file is git-tracked. An adopter who follows a one-line instruction
        # verbatim should not dirty eight unrelated repositories.
        #
        # A disproportionate remedy is one mechanism behind an IGNORED warning: in one adopter this
        # staleness line rode ~28 consecutive handoffs unacted-on. The measurement was never the
        # missing part — the safe per-project action is one `cp`, and the message never printed it.
        sys.stderr.write(
            f"  ⚠ methodology_dashboard.py is stale: this copy is v{DASHBOARD_VERSION}, "  # layout: ok -- a name printed in a message, never opened
            f"canonical is v{canon_ver}.\n"
            f"    Update just this copy:      python3 {canonical} --sync {resolve_single_project_root(self_path.parent)}\n"
            f"    Update the whole portfolio: python3 {canonical} --sync   "
            f"(writes every discovered project — preview first with --dry-run)\n"
        )


# --- S38 helpers: locating the trimmer, and computing the line metric without it ------------------

def find_trim_tool(path, role="adopter"):
    """Locate the ledger trimmer for the SCANNED project, or None.

    Root-anchored on the scanned project, mirroring is_framework_installed -- an adopter's own
    `tools/methodology_trim.py` is their file, not ours. The starter-kit/ fallback applies only
    to a framework repo, which authors the tool there and installs no root copy of it (see
    TRIM_TOOL_FRAMEWORK_REL for why that branch exists at all).

    Content-verified by regex, exactly as parse_version verifies a dashboard copy: a bare
    `.is_file()` would accept a directory or an unrelated same-named script. Nothing here
    imports or executes the file it found -- §7.1's precedent, and the reason the rows stay
    read-only. That holds for `ledgers` too (BL-88 P2): _parse_trim_ledgers PARSES the source
    and runs none of it."""
    candidates = layout_locations(path, TRIM_TOOL_NAME)
    if role == "framework":
        candidates.append(path / TRIM_TOOL_FRAMEWORK_REL)
    for cand in candidates:
        if not cand.is_file():
            continue
        try:
            text = cand.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        m = _TRIM_VERSION_RE.search(text)
        if m:
            return {"path": cand, "version": m.group(1),
                    "budget": _parse_trim_budget(text),
                    "ledgers": _parse_trim_ledgers(text)}
    return None


def _parse_trim_budget(text):
    """The trimmer's byte budget, read out of its source. None when it cannot be read.

    None is a real answer here, not a zero: the budget is a calibrated judgment (design §5.4)
    that no formula recovers, so an unparseable one makes the byte half of the trigger
    unanswerable and it says so rather than substituting a guess."""
    m = _TRIM_BUDGET_RE.search(text)
    if not m:
        return None
    total = 1
    for part in m.group(1).split("*"):
        part = part.strip().replace("_", "")
        if not part.isdigit():
            return None
        total *= int(part)
    return total or None


# BL-88 P2: the attribute uses of LEDGERS a reading survives -- each one only READS the table.
# Anything else on the name (`.pop`, `.update`, `.setdefault`, `.clear`, ...) could change what
# the literal says, so the reading abstains rather than follow it.
_TRIM_LEDGERS_READ_ONLY = frozenset(("get", "keys", "items", "values", "copy"))


def _parse_trim_ledgers(text):
    """The basenames a trimmer's LEDGERS table declares, read out of its SOURCE. None when the
    source alone cannot say.

    BL-88 P2 (docs/planning/dashboard-read-cap-class-adopter-drift-plan.md §8). The operator
    decided this is a SOURCE-TEXT read, never an execution: no adopter code runs inside the
    scanner -- §7.1's precedent and find_trim_tool's own contract. `ast.parse` honours that, since
    it builds a syntax tree and runs nothing, and it is used instead of a grep because a grep
    cannot tell an entry from a mention: nprcgenekeepr's widened trimmer spells SESSION_NOTES.md
    on three lines -- a comment, the key, and a `basename=` argument -- and one of them is a key.

    ABSTAIN, NEVER GUESS. The answer is the keys of ONE module-level `LEDGERS = {...}` display
    whose keys are all string constants, and only while nothing else in the file binds the name
    (assignment, import, def, class, except-as), stores into it, deletes from it, or calls a
    method on it that is not a read. Anything else returns None. The asymmetry is the reason: None
    leaves the Class B row exactly as P1 wrote it, so a false negative costs nothing, while a key
    the running tool would not have makes the row name a remedy that does not work. What no
    source read can see -- a mutation through `globals()` or from another module -- is the residue
    accepted in exchange for never executing the file."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, MemoryError, RecursionError):
        # ValueError: a null byte, on the 3.10 interpreter the suite runs (SyntaxError from 3.12).
        # MemoryError: the parser's own stack on a pathologically deep expression. RecursionError
        # is what other interpreters raise for that case; no input reaches it on 3.10.
        return None
    name = "LEDGERS"
    display = None
    for stmt in tree.body:
        if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Name) and stmt.targets[0].id == name):
            display = stmt       # a second one is caught by the walk below, as any binding is
    if display is None or not isinstance(display.value, ast.Dict):
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == name:
            if not isinstance(node.ctx, ast.Load) and node is not display.targets[0]:
                return None
        elif isinstance(node, ast.alias):
            if (node.asname or node.name.split(".")[0]) == name:
                return None
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                               ast.ExceptHandler)):
            if node.name == name:
                return None
        elif isinstance(node, (ast.Subscript, ast.Attribute)):
            on_name = isinstance(node.value, ast.Name) and node.value.id == name
            if on_name and isinstance(node, ast.Subscript) and not isinstance(node.ctx, ast.Load):
                return None
            if (on_name and isinstance(node, ast.Attribute)
                    and node.attr not in _TRIM_LEDGERS_READ_ONLY):
                return None
    keys = set()
    for k in display.value.keys:
        if not (isinstance(k, ast.Constant) and isinstance(k.value, str)):
            return None      # a computed key -- or None, which is how ast spells `**` unpacking
        keys.add(k.value)
    return sorted(keys)


def _trim_record_count(text, basename):
    """Records in a ledger under its declared grammar, FENCE-AWARE.

    Fence-awareness is not defensive polish. `starter-kit/CHANGELOG.md` carries three dated
    headings and `starter-kit/HANDOFFS.md` one ```handoff block, and in both files every one of
    them sits inside a documentation fence -- a fence-blind counter reads 3 and 1 where the
    truth is 0, and would report a confident slope for a freshly seeded ledger holding no
    records at all.

    Returns None -- ABSTAIN, never a count of zero -- for a basename this module has no grammar
    for, and for a text the trimmer's own zone classifier would REFUSE. Both matter: the trimmer
    treats a refusal as a reason to abstain and says so ("that is not a count of zero. Treating it
    as zero makes `de` the whole current record count and prints a confidently inflated headroom
    for a baseline the tool would itself refuse to read"), so a counter that always answers would
    print a number exactly where `--check` prints none."""
    grammar = TRIM_GRAMMARS.get(basename)
    if grammar is None:
        return None
    kind, pat = grammar
    n = 0
    fence = None
    last_start = -1
    hrs = []
    for idx, raw in enumerate(text.split("\n")):
        line = raw.rstrip()
        m = _TRIM_FENCE_RE.match(line)
        inside_before = fence is not None
        if m:
            marker, info = m.group(1), m.group(2).strip()
            if fence is None:
                fence = marker
                # No `and not inside_before` conjunct here, deliberately. This branch is reached
                # only when fence is None, which IS inside_before being False, so the conjunct
                # could never be false and no mutant could falsify it -- a comment wearing a
                # guard's clothes. It was written, observed unkillable, and removed. The fact it
                # asserted is real and is stated instead: a fence OPENER is never itself nested,
                # which is what makes a ```handoff line a record start rather than noise.
                if kind == "fence" and info == pat:
                    n += 1
                    last_start = idx
            elif marker[0] == fence[0] and len(marker) >= len(fence) and not info:
                # `and not info` is the trimmer's rule and it is load-bearing, not pedantry: a
                # closer carries no info string. Without it a nested ```python inside an open
                # fence reads as a closer here and as ordinary fenced content there, and every
                # record after it is counted by one side and not the other -- measured at 1 vs 2
                # on a three-fence fixture.
                fence = None
            continue
        if inside_before:
            continue
        if kind == "heading" and pat.match(line):
            n += 1
            last_start = idx
        if line.strip() == "---":
            hrs.append(idx)

    # The trimmer ASSERTS a footer_mode='none' declaration rather than trusting it: a standalone
    # '---' after the last record with content under it is content the config cannot name, and it
    # refuses. Mirror the refusal, do not model the whole zone split -- the dashboard has no need
    # to know where the footer starts, only whether the trimmer would have answered at all.
    if kind == "fence" and n and hrs:
        for i in hrs:
            if i > last_start and "\n".join(text.split("\n")[i + 1:]).strip():
                return None
    return n


# ⚠ PHASE B REMOVED THIS FUNCTION'S ONLY PRODUCTION CONSUMER, and it is kept deliberately rather
# than deleted or quietly left to rot. `trim_line_headroom` called it to find the baseline commit
# a RATE needs; the read metric is a LEVEL and needs no baseline, so nothing in this module calls
# it today. It is NOT dead by accident: it is the archive-event detector, it encodes a defect that
# cost a session to find (a shard committed before the ledger existed is not an archive event,
# because nothing shrank), and 18 assertions still pin that behaviour. Deleting it would discard
# earned coverage; giving it a new consumer would be a feature this session did not scope. Whether
# the S38 row should surface an archive baseline at all is part of Phase C's decision about that
# row's shape — decide it there, and delete or re-wire this then. Recorded, not drifted into
# (FM #17).
def _newest_archive_sha(path, basename):
    """The commit that ADDED the most recent shard of this ledger, or None.

    Ordered by position in the commit graph, never by timestamp: two archives committed in the
    same second are ordinary, and a timestamp tie falls back to sha order, which is arbitrary.
    The trimmer orders the same way and for the same reason; the agreement test is what holds
    the two together."""
    adir = path / TRIM_ARCHIVE_DIR
    if not adir.is_dir():
        return None
    stem = basename[:-3] if basename.endswith(".md") else basename
    shas = []
    for shard in sorted(adir.glob("%s-*.md" % stem)):
        try:
            rel = shard.relative_to(path).as_posix()
        except ValueError:
            continue
        sha = git_cmd(path, "log", "--diff-filter=A", "-1", "--format=%H", "--", rel)
        if not sha:
            continue
        # An archive EVENT is a commit in which the ledger actually SHRANK -- the trimmer's own
        # filter, and skipping it is not cosmetic. A shard committed separately from the trim
        # (the ordinary two-step manual archive), or copied in beside new entries, adds a sha
        # here that the trimmer discards; the two then compute against different baselines and
        # the row an operator reads stops matching `--check`, which is the one thing §1.3 names
        # as worse than a single gauge. It does not bite on this repo -- every shard here really
        # did shrink its ledger -- so the agreement test passed on luck of history until a
        # fixture was built for it.
        pre = git_show(path, "%s^:%s" % (sha, basename))
        post = git_show(path, "%s:%s" % (sha, basename))
        if pre is None or post is None:
            continue
        if len(pre.encode("utf-8")) <= len(post.encode("utf-8")):
            continue
        shas.append(sha)
    if not shas:
        return None
    if len(shas) == 1:
        return shas[0]
    # Ordered by position in the commit graph, never by timestamp: two archives committed in the
    # same second are ordinary, and a timestamp tie falls back to sha order, which is arbitrary.
    #
    # ABSTAIN rather than degrade. git_cmd returns "" on timeout, which is indistinguishable from
    # success -- and an empty walk collapses every rank to the same sentinel, leaving the stable
    # sort in FILENAME order, which for a date-stamped shard naming scheme silently selects the
    # OLDEST. That is the precise ordering this function's contract forbids, arrived at with no
    # error and no marker. If the walk cannot rank every candidate, say nothing.
    walk = (git_cmd(path, "rev-list", "--topo-order", "HEAD") or "").split()
    rank = {sha: i for i, sha in enumerate(walk)}
    if any(s not in rank for s in shas):
        return None
    shas.sort(key=lambda s: rank[s])
    return shas[0]


# `trim_line_headroom()` WAS HERE and was deleted with the rate rule it re-implemented (Phase B).
# It recomputed the trimmer's line headroom independently -- deliberately, so this half still
# answered when the trimmer was absent -- and it carried the whole abstention apparatus that a
# RATE needs: no baseline archive, an unreadable baseline blob, fewer than one record since the
# split. A LEVEL needs none of it. `size_bytes > READ_CAP_BYTES` is answerable from the file
# alone, with no git history and no baseline, so the read half now answers for every watched
# ledger in every repo -- including a freshly-bootstrapped one that has never archived, which is
# exactly the state in which the old rate abstained and reported nothing.


_KNOWN_FLAGS = {"--sync", "--dry-run", "--force", "--no-open", "--with-submodules", "--help", "-h"}


def _extract_sync_target(args):
    """First non-flag token in argv (any position, not only after --sync): the optional
    single-project sync scope. Order-independent — '--sync /path' and '--sync --force /path'
    both resolve to '/path'. None => sync the whole portfolio (today's unchanged default).

    Issue #67 point 2. Every current flag is dash-prefixed, so this is really just "the first
    bare word" — a FUTURE value-taking flag (e.g. a hypothetical --out FILE) would have its own
    value misread as the sync target; `_KNOWN_FLAGS` does no independent filtering against that
    today. Not a structural guard; any future value-taking flag needs its own dedicated test."""
    for a in args:
        if a not in _KNOWN_FLAGS and not a.startswith("-"):
            return a
    return None


def sync_dashboards(start, dry_run=False, target=None, force=False):
    """Copy the canonical dashboard to a single TARGET_DIR (if given) or to the portfolio root +
    every discovered project (target=None, today's default). In --dry-run mode nothing is
    written; the planned actions — including which targets --force would be needed for — are
    printed. Returns the count of files ACTUALLY written (0 for a dry run).

    NOTE: a live sync writes methodology_dashboard.py into every project, including the
    repos where it is still git-tracked — those need the Phase 3 `git rm --cached` +
    per-repo commit discipline. Tracked targets are flagged in the output.

    Issue #67 points 2/3/4 (docs/planning/issue67-fork-side-fix-plan.md, D1-D4): a write is
    gated (skipped without --force) when the target is already git-tracked, or is a brand-new
    file landing in a repo whose own .gitignore does not already cover it. The gate is computed
    BEFORE branching on dry_run, so a --dry-run preview shows [SKIPPED] honestly instead of
    promising a write --force would still be needed for."""
    canonical = find_canonical(start)
    if not canonical:
        sys.stderr.write("  Cannot locate canonical methodology/starter-kit/"
                         "methodology_dashboard.py — nothing synced.\n")  # layout: ok -- a name printed in a message, never opened
        return 0
    # .../starter-kit/methodology_dashboard.py -> starter-kit -> methodology -> portfolio root
    canon_repo = canonical.parent.parent.resolve()           # .../methodology
    portfolio_root = canonical.parent.parent.parent
    canon_text = canonical.read_text()
    canon_ver_display = parse_version(canonical) or DASHBOARD_VERSION   # see SS6 item 4: never
                                                                          # DASHBOARD_VERSION alone —
                                                                          # that's the RUNNING copy's
                                                                          # own version, not the
                                                                          # canonical's, whenever a
                                                                          # local stale copy invokes
                                                                          # --sync on itself.

    if target is not None:
        target_dir = Path(target).resolve()
        if not target_dir.is_dir():
            sys.stderr.write(f"  Target directory does not exist: {target_dir} — nothing synced.\n")
            return 0
        if target_dir == canon_repo or (target_dir / "methodology_dashboard.py") == canonical:  # layout: ok -- this tool's own file name: refuses the canonical copy as a target
            sys.stderr.write("  Refusing to sync the canonical's own authoring repo as a target.\n")
            return 0
        copy, why = dashboard_copy_target(target_dir)
        if copy is None:
            sys.stderr.write(f"  Target is {why}; nothing synced (never guessed).\n")
            return 0
        targets = [copy]
        refused = []
        scope_label = f"1 target ({target_dir})"
    else:
        # discover_projects() has TWO consumers — the portfolio scan and this WRITE path — so
        # widening it widens both. Dropping "methodology" from EXCLUDE_DIRS (D4(c)) is wanted for
        # the scan and NOT wanted here: it would make --sync create a third copy of this file at
        # the canonical repo's own root, unignored and beside the two it already authors. The
        # `t == canonical` skip below does not catch that, because canonical is
        # .../starter-kit/<name> and the new target is .../<name>. Skip the authoring repo
        # explicitly.
        targets = [portfolio_root / DASHBOARD_NAME]
        refused = []
        for proj in discover_projects(portfolio_root):
            if proj.resolve() == canon_repo:
                continue
            copy, why = dashboard_copy_target(proj)
            if copy is None:
                refused.append((proj, why))
            else:
                targets.append(copy)
        scope_label = f"portfolio root + {len(targets) - 1 + len(refused)} project(s)"

    print(f"Canonical: {canonical} (v{canon_ver_display})")
    print(f"{'DRY RUN — no files written.' if dry_run else 'Syncing.'} Targets: {scope_label}\n")

    written = skipped = inspected = 0
    for t in targets:
        t = t.resolve()
        if t == canonical:
            continue
        inspected += 1
        existing = t.read_text() if t.exists() else None
        if existing == canon_text:
            action = "unchanged"
        elif existing is None:
            action = "create"
        else:
            action = "update"

        tracked = bool(git_cmd(t.parent, "ls-files", "--error-unmatch", t.name))
        ignored = action == "create" and bool(git_cmd(t.parent, "check-ignore", t.name))
        gated = action != "unchanged" and (tracked or (action == "create" and not ignored))

        note = ""
        if gated and not force:
            skipped += 1
            note = ("  [SKIPPED — git-tracked; pass --force, then Phase 3 untrack]" if tracked else
                    "  [SKIPPED — new, ungitignored file; pass --force to create]")
        elif action != "unchanged":
            if not dry_run:
                shutil.copyfile(canonical, t)
            written += 1
            if tracked:
                note = "  [git-tracked — needs Phase 3 untrack]"

        try:
            label = t.relative_to(portfolio_root)
        except ValueError:
            label = t
        shown = "skip" if (gated and not force) else action
        print(f"  {shown:<9s} {label}{note}")

    for proj, why in refused:
        try:
            label = proj.relative_to(portfolio_root)
        except ValueError:
            label = proj
        print(f"  {'refuse':<9s} {label}  [{why}; never guessed, so move or remove one copy]")

    verb = "Would change" if dry_run else "Changed"
    tail = f" ({skipped} skipped — rerun with --force to include them)" if skipped else ""
    if refused:
        tail += f" ({len(refused)} half-migrated project(s) refused — --force does not apply)"
    print(f"\n  {verb} {written} of {inspected} target(s).{tail}")
    return 0 if dry_run else written


def print_usage():
    print(f"methodology_dashboard.py v{DASHBOARD_VERSION} — portfolio/project health scanner")  # layout: ok -- a name printed in a message, never opened
    print("")
    print("Usage: python3 methodology_dashboard.py [options]")  # layout: ok -- a name printed in a message, never opened
    print("")
    print("Options:")
    print("  --no-open          Do not open the generated dashboard.html in a browser.")  # layout: ok -- a name printed in a message, never opened
    print("  --with-submodules  In single-project mode, also scan git submodules as")
    print("                     separate entries (default: scan the project only).")
    print("  --sync [DIR]       Copy the canonical dashboard to DIR (a single project) if")
    print("                     given, or to the portfolio root and every discovered")
    print("                     project if omitted. Combine with --dry-run to preview,")
    print("                     --force to also write tracked/brand-new targets.")
    print("                     Each project's copy goes where it keeps its methodology")
    print("                     files (its root, or methodology/); a half-migrated")
    print("                     project is refused by name.")
    print("  --dry-run          With --sync, show planned changes without writing.")
    print("                     Alone, it is an error (nothing else in this tool writes")
    print("                     speculatively).")
    print("  --force            With --sync, also write targets that are git-tracked or")
    print("                     brand-new (and not already .gitignore'd). Without it,")
    print("                     those targets are listed but skipped.")
    print("  -h, --help         Show this help and exit.")


# === DISCOVERY ===

# BL-29: the two directories this script is actually checked into its OWN home repo at (see
# bin/_manifest.py — starter-kit/methodology_dashboard.py is the TRACKED distribution source;
# tools/methodology_dashboard.py is the canonical-only portfolio copy). Every OTHER copy —
# every adopter-installed copy, the portfolio-root copy — sits directly at the level it is meant
# to scan (bin/_manifest.py TRACKED dest; sync_dashboards()'s own target list), so
# resolve_single_project_root() only ever needs to bridge these two specific, known nestings.
_CANONICAL_IN_REPO_DIRS = ("tools", "starter-kit")


def resolve_single_project_root(script_dir):
    """Return the directory `main()` should treat as "the project to scan".

    Ordinarily `script_dir` (== `ROOT`, `Path(__file__).parent`) IS that directory. The
    methodology repo's own two checked-in copies are the one exception: `tools/` and
    `starter-kit/` both file this script one level BELOW the repo it belongs to, so
    `(script_dir / ".git").exists()` reads false there even while running the framework's own
    tool against the framework's own home — exactly the case `main()`'s `single_project`
    title-text branch already assumed could happen, but discovery never bridged. Reproduced live:
    `python3 tools/methodology_dashboard.py --no-open` printed "No projects found" run from this
    repo's own root, while the portfolio-root copy scanned this repo correctly.

    Narrow on purpose, not a generic upward walk — a generic walk could let an accidental copy
    anywhere in an unrelated subdirectory tree claim its ancestor as "the project". The parent is
    substituted only when its own name is one of the two locations this file is actually checked
    in at, AND the parent both is a git repo and carries `bin/_manifest.py` — the same structural
    marker `detect_repo_role()` already trusts to prove "this is the framework's own publishing
    repo", which no adopter can acquire via `bin/sync` (bin/ ships nothing through it).
    """
    if (script_dir / ".git").exists():
        return script_dir
    parent = script_dir.parent
    if (script_dir.name in _CANONICAL_IN_REPO_DIRS
            and (parent / ".git").exists()
            and (parent / "bin" / "_manifest.py").is_file()):
        return parent
    # BL-101 P5: an adopter's copy in the new layout sits in <project>/methodology/, one level below the
    # project it scans. Three facts together, none of them the directory's NAME alone (a directory named
    # methodology that is not a project's subdirectory, as this repository's own root is, has a .git of its
    # own and returned above): the project above is a git repository, and the runner is beside the copy.
    if (script_dir.name == NEW_LAYOUT_DIR and (parent / ".git").exists()
            and (script_dir / RUNNER_NAME).is_file()):
        return parent
    return script_dir


def output_dir(script_dir, root):
    """Where a run writes dashboard.html and dashboard_history.jsonl: beside the copy that ran, which is the
    project root for every copy but one. A copy that lives in <project>/methodology/ writes there, so the
    project root stays clean (plan 4.1 lists both files under methodology/) and its history is read back
    from the same place."""
    return script_dir if (root != script_dir and script_dir.name == NEW_LAYOUT_DIR) else root


def discover_projects(root, with_submodules=False):
    """Discover projects to scan.

    Two modes, auto-detected by whether `root` is itself a git repo:
    - Single-project mode (root is a git repo): scan the project only. Git submodules are
      scanned as separate entries ONLY when with_submodules=True (CLI: --with-submodules).
      Default is project-only: expanding submodules by default rendered a mislabeled
      mini-portfolio inside submodule-bearing repos (e.g. rad-con's 4 submodules).
    - Portfolio mode (root is NOT a git repo): scan sibling directories that contain .git/.
    """
    # Single-project mode: root is a git repo
    if (root / ".git").exists():
        projects = [root]
        if with_submodules:
            # Opt-in: discover git submodules (each appears as its own entry)
            submodule_output = git_cmd(root, "submodule", "status")
            for line in submodule_output.splitlines():
                parts = line.strip().lstrip("+-").split()
                if len(parts) >= 2:
                    submodule_path = root / parts[1]
                    if submodule_path.is_dir() and (submodule_path / ".git").exists():
                        projects.append(submodule_path)
        return projects

    # Portfolio mode: scan sibling directories
    projects = []
    try:
        for entry in sorted(root.iterdir()):
            if not entry.is_dir():
                continue
            if entry.name.startswith("."):
                continue
            if entry.name in EXCLUDE_DIRS:
                continue
            if (entry / ".git").exists():
                projects.append(entry)
    except OSError:
        pass
    return projects


# === COLLECTORS ===

def collect_git_metrics(path):
    metrics = {
        "total_commits": 0,
        "last_commit_date": None,
        "days_since_last_commit": None,
        "first_commit_date": None,
        "project_age_days": 0,
        "commit_velocity_30d": 0,
        "commit_velocity_7d": 0,
        "contributor_count": 0,
        "branch_count": 0,
        "recent_commits": [],
    }

    # Total commits
    count_str = git_cmd(path, "rev-list", "--count", "HEAD")
    metrics["total_commits"] = int(count_str) if count_str.isdigit() else 0

    # Recent commits with dates
    log_output = git_cmd(path, "log", "--format=%H|%ai|%s", "-20")
    now = datetime.now()
    commits = []
    for line in log_output.splitlines():
        parts = line.split("|", 2)
        if len(parts) == 3:
            commits.append({
                "hash": parts[0][:8],
                "date": parts[1][:10],
                "message": parts[2][:80],
            })

    metrics["recent_commits"] = commits[:5]

    if commits:
        # Last commit
        last_date_str = commits[0]["date"]
        try:
            last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
            metrics["last_commit_date"] = last_date_str
            metrics["days_since_last_commit"] = (now - last_date).days
        except ValueError:
            pass

    # First commit date. NOT `log --reverse --format=%ai -1`, which reads as "the oldest commit"
    # and is not: git applies `-n1` while walking, BEFORE `--reverse` re-orders what survived, so
    # that form returns the NEWEST commit. `first_commit_date` tracked HEAD and
    # `project_age_days` measured "days since the last commit" under the name "project age".
    #
    # Precisely — an earlier draft of this comment said the `commits < 10 and age > 30` risk below
    # "could never fire at all", and that overclaims: for a STALE repo whose newest commit is
    # itself over 30 days old the risk still fired, for the wrong reason. What the bug really did
    # was make the risk unreachable for every ACTIVE low-commit repo — exactly the young project
    # it exists to flag — while reporting a wrong age everywhere.
    # `--max-parents=0` names the root commit(s) directly and needs no ordering flag. A repo can
    # have MORE THAN ONE root (a merge of unrelated histories), so take the oldest rather than
    # whichever git happens to print first.
    root_log = git_cmd(path, "log", "--max-parents=0", "--format=%ai")
    root_dates = [ln[:10] for ln in root_log.splitlines() if ln.strip()]
    if root_dates:
        first_date_str = min(root_dates)
        try:
            first_date = datetime.strptime(first_date_str, "%Y-%m-%d")
            metrics["first_commit_date"] = first_date_str
            metrics["project_age_days"] = (now - first_date).days
        except ValueError:
            pass

    # Velocity
    since_30d = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    since_7d = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    v30 = git_cmd(path, "rev-list", "--count", f"--since={since_30d}", "HEAD")
    v7 = git_cmd(path, "rev-list", "--count", f"--since={since_7d}", "HEAD")
    metrics["commit_velocity_30d"] = int(v30) if v30.isdigit() else 0
    metrics["commit_velocity_7d"] = int(v7) if v7.isdigit() else 0

    # Contributors
    shortlog = git_cmd(path, "shortlog", "-sn", "HEAD")
    metrics["contributor_count"] = len([l for l in shortlog.splitlines() if l.strip()])

    # Branches
    branches = git_cmd(path, "branch", "-a")
    metrics["branch_count"] = len([l for l in branches.splitlines() if l.strip()])

    return metrics


def collect_file_metrics(path):
    metrics = {
        "total_files": 0,
        "total_loc": 0,
        "by_extension": defaultdict(lambda: {"count": 0, "loc": 0}),
        "by_language": defaultdict(lambda: {"count": 0, "loc": 0}),
        "by_category": {
            "source": {"count": 0, "loc": 0},
            # Framework-installed source (bin/sync's own files), held OUT of "source" so the
            # adopter is measured on code they wrote. Given its own bucket rather than silently
            # subtracted: every consumer then reads one consistent number, and the file stays
            # visible in the card's file-type table instead of vanishing from the inventory.
            "vendor": {"count": 0, "loc": 0},
            "test": {"count": 0, "loc": 0},
            "docs": {"count": 0, "loc": 0},
            "config": {"count": 0, "loc": 0},
            "assets": {"count": 0},
            "other": {"count": 0},
        },
        # Framework-installed markdown, counted alongside (NOT subtracted from) by_category.docs:
        # the documentation dimension keeps crediting it, only detect_doc_only's corpus check
        # discounts it. See FRAMEWORK_INSTALLED_DOCS for why the two questions differ.
        "framework_docs": {"count": 0, "loc": 0},
        "largest_files": [],
        "read_cap_watch": [],
        "directory_depth_max": 0,
        "directory_count": 0,
    }

    all_files = []
    watched = []
    dirs_seen = set()
    # Seed-named docs are held aside during the walk: whether they are OURS depends on evidence
    # that only appears elsewhere in the tree, which the walk may not have reached yet.
    seed_docs = {"count": 0, "loc": 0}
    ambiguous_docs = {"count": 0, "loc": 0}
    ambiguous_names = set()          # distinct dests, so one file cannot be counted as evidence twice
    saw_distinctive_framework_doc = False

    layout_name_of, layout_own = layout_names(path)

    for root_dir, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in WALK_SKIP]
        rel_root = Path(root_dir).relative_to(path)
        depth = len(rel_root.parts)
        metrics["directory_depth_max"] = max(metrics["directory_depth_max"], depth)
        dirs_seen.add(str(rel_root))

        for fname in files:
            fpath = Path(root_dir) / fname
            rel_path = fpath.relative_to(path)
            ext = fpath.suffix.lower()
            category = categorize_file(rel_path, ext, fname)
            rel_posix = str(rel_path).replace("\\", "/")
            # BL-101 P5: the NAME every table below is keyed by. A methodology file under methodology/ is
            # classified by its legacy name; a root file that is the project's own namesake (a product
            # CHANGELOG.md beside the framework's under methodology/) has no name and is never ours.
            class_name = layout_name_of.get(rel_posix, None if rel_posix in layout_own else rel_posix)
            # Layer 7: reclassify only what WE installed, and only where it would otherwise be
            # counted as the adopter's code. Checked after categorize_file so a file that is
            # already test/docs/config is untouched.
            if category == "source" and ((class_name is not None and is_framework_installed(class_name, fpath))
                                         or is_generated_proof(rel_path, fpath)):
                category = "vendor"

            metrics["total_files"] += 1

            # LOC for text files
            loc = 0
            if ext not in ASSET_EXTS and category not in ("assets", "other"):
                loc = count_lines(fpath)
                metrics["total_loc"] += loc

            # By extension
            if ext:
                metrics["by_extension"][ext]["count"] += 1
                metrics["by_extension"][ext]["loc"] += loc

            # By language
            lang = LANG_MAP.get(ext)
            if lang:
                metrics["by_language"][lang]["count"] += 1
                metrics["by_language"][lang]["loc"] += loc

            # By category
            if category in ("source", "vendor", "test", "docs", "config"):
                metrics["by_category"][category]["count"] += 1
                metrics["by_category"][category]["loc"] += loc
                if category == "docs":
                    if class_name in FRAMEWORK_DISTINCTIVE_DOCS:
                        metrics["framework_docs"]["count"] += 1
                        metrics["framework_docs"]["loc"] += loc
                        saw_distinctive_framework_doc = True
                    elif class_name in FRAMEWORK_AMBIGUOUS_DOCS:
                        # Held aside like the seeds: a root name is not self-evidencing (Layer 8).
                        ambiguous_docs["count"] += 1
                        ambiguous_docs["loc"] += loc
                        ambiguous_names.add(class_name)
                    elif class_name in FRAMEWORK_SEED_DOCS:
                        # Held aside; folded in below only if the framework is really installed.
                        seed_docs["count"] += 1
                        seed_docs["loc"] += loc
            elif category in ("assets", "other"):
                metrics["by_category"][category]["count"] += 1

            # Track for largest files. The vendor flag rides along so the "Large files" risk can
            # skip a file we installed without re-deriving the predicate at risk time.
            if loc > 0:
                all_files.append({"path": str(rel_path), "loc": loc, "ext": ext,
                                  "vendor": category == "vendor"})

            # D4(b): keyed by NAME, never by size rank, and deliberately outside the `loc > 0`
            # branch above so an empty watched file still reports its 0.
            #
            # This list must NOT inherit largest_files' top-ten window, and the reason is not
            # hypothetical: in this repo `docs/planning/BACKLOG.md` is ALREADY outside that
            # window, so a size threshold reading largest_files could not see it at any size —
            # D4(b)'s own defect class, re-created inside the fix for it. The two ledgers are
            # inside the window today and can leave it without changing by a byte, since the
            # window is a RANK. No distance is quoted here on purpose: the first draft of this
            # comment named one, a reviewer re-derived it and it was wrong, and any such figure
            # rots as the tree grows. Re-derive it instead:
            #   python3 -c "import sys;sys.path.insert(0,'tools');from methodology_dashboard \
            #     import collect_all;from pathlib import Path;\
            #     d=collect_all(Path('.').resolve());\
            #     print([f['path'] for f in d['files']['largest_files']])"
            if class_name in READ_CAP_WATCHED:
                # `lines` is kept and still reported: it is what a human scans a ledger by, and
                # dashboard_history.jsonl has carried the key since S38. It is no longer what the
                # verdict is computed from.
                try:
                    watched_bytes = fpath.stat().st_size
                except OSError:
                    watched_bytes = None
                entry = {"path": rel_posix, "lines": loc, "bytes": watched_bytes}
                if class_name != rel_posix:
                    entry["name"] = class_name        # the legacy name its class is looked up by
                watched.append(entry)

    # A root BOOTSTRAP.md — or a CHANGELOG.md — is ours only in a repo that also carries proof the
    # framework was installed: a docs/methodology/ path (nothing lands there by accident), or the
    # seven TRACKED root names co-occurring past FRAMEWORK_AMBIGUOUS_EVIDENCE_MIN. Neither the
    # ambiguous names nor the seeds are evidence FOR themselves, which is the Layer 8 correction:
    # letting them self-evidence is what discounted a non-adopter's own documentation.
    if saw_distinctive_framework_doc or len(ambiguous_names) >= FRAMEWORK_AMBIGUOUS_EVIDENCE_MIN:
        for held in (ambiguous_docs, seed_docs):
            metrics["framework_docs"]["count"] += held["count"]
            metrics["framework_docs"]["loc"] += held["loc"]

    metrics["directory_count"] = len(dirs_seen)
    all_files.sort(key=lambda f: f["loc"], reverse=True)
    metrics["largest_files"] = all_files[:10]
    metrics["read_cap_watch"] = sorted(
        watched, key=lambda f: (f["bytes"] if f["bytes"] is not None else -1), reverse=True)

    # Convert defaultdicts
    metrics["by_extension"] = dict(metrics["by_extension"])
    metrics["by_language"] = dict(metrics["by_language"])

    return metrics


def collect_test_metrics(file_metrics):
    source_loc = file_metrics["by_category"]["source"]["loc"]
    test_loc = file_metrics["by_category"]["test"]["loc"]
    test_count = file_metrics["by_category"]["test"]["count"]
    ratio = (test_loc / source_loc) if source_loc > 0 else 0.0

    return {
        "test_file_count": test_count,
        "test_loc": test_loc,
        "test_to_source_ratio": round(ratio, 3),
        "source_loc": source_loc,
    }


def collect_ci_metrics(path):
    metrics = {
        "has_ci": False,
        "ci_platform": None,
        "workflow_count": 0,
        "workflow_files": [],
    }

    # GitHub Actions
    gh_workflows = path / ".github" / "workflows"
    if gh_workflows.is_dir():
        ymls = list(gh_workflows.glob("*.yml")) + list(gh_workflows.glob("*.yaml"))
        if ymls:
            metrics["has_ci"] = True
            metrics["ci_platform"] = "GitHub Actions"
            metrics["workflow_count"] = len(ymls)
            metrics["workflow_files"] = [f.name for f in ymls]

    # Other CI systems
    for ci_file, ci_platform in [
        (".gitlab-ci.yml", "GitLab CI"),
        ("Jenkinsfile", "Jenkins"),
        (".circleci/config.yml", "CircleCI"),
        (".travis.yml", "Travis CI"),
    ]:
        if (path / ci_file).exists():
            metrics["has_ci"] = True
            metrics["ci_platform"] = ci_platform
            metrics["workflow_count"] = max(metrics["workflow_count"], 1)

    return metrics


def collect_doc_metrics(path, file_metrics):
    metrics = {
        "has_readme": False,
        "readme_loc": 0,
        "readme_quality": "none",
        "has_docs_dir": (path / "docs").is_dir(),
        "doc_file_count": file_metrics["by_category"]["docs"]["count"],
        "doc_total_loc": file_metrics["by_category"]["docs"]["loc"],
        "doc_to_source_ratio": 0.0,
        "has_changelog": False,
        "has_license": False,
        "has_contributing": False,
        "has_roadmap": False,
        "has_todo": False,
    }

    # README detection
    for name in ["README.md", "README.txt", "README.rst", "README", "readme.md"]:
        readme_path = path / name
        if readme_path.exists():
            metrics["has_readme"] = True
            metrics["readme_loc"] = count_lines(readme_path)
            break

    loc = metrics["readme_loc"]
    if loc == 0:
        metrics["readme_quality"] = "none"
    elif loc < 20:
        metrics["readme_quality"] = "stub"
    elif loc < 100:
        metrics["readme_quality"] = "basic"
    elif loc < 300:
        metrics["readme_quality"] = "good"
    else:
        metrics["readme_quality"] = "excellent"

    # Other docs
    source_loc = file_metrics["by_category"]["source"]["loc"]
    if source_loc > 0:
        metrics["doc_to_source_ratio"] = round(
            file_metrics["by_category"]["docs"]["loc"] / source_loc, 3
        )

    for check_name, key in [
        ("CHANGELOG", "has_changelog"),
        ("LICENSE", "has_license"),
        ("CONTRIBUTING", "has_contributing"),
        ("ROADMAP", "has_roadmap"),
        ("TODO", "has_todo"),
    ]:
        # BL-101 P5: a project that moved its state files keeps its changelog and roadmap under methodology/.
        top = [path] + ([path / NEW_LAYOUT_DIR] if resolve_layout(path)[0] == "new" else [])
        for entry in (e for d in top if d.is_dir() for e in d.iterdir()):
            if entry.name.upper().startswith(check_name):
                metrics[key] = True
                break
        # Also check docs/
        docs_dir = path / "docs"
        if docs_dir.is_dir():
            for entry in docs_dir.iterdir():
                if entry.name.upper().startswith(check_name):
                    metrics[key] = True
                    break

    return metrics


def _find_changelog(path):
    """LOCATION — return the Path to the changelog freshness should be measured against (project
    root or docs/), else None. Mirrors collect_doc_metrics's has_changelog detection
    (case-insensitive prefix), but restricted to regular files so a CHANGELOG *directory* is not
    treated as a ledger.

    Within a base, an exact `CHANGELOG.md` (any case) wins over every name-prefix sibling:
    `sorted()` alone returned `CHANGELOG-archive.md` ahead of `CHANGELOG.md` ('-' is 0x2D, '.' is
    0x2E), so freshness was measured against a deliberately frozen archive and the repo was then
    reported as lagging behind its own history. The prefix search remains as the fallback, so a
    project whose only changelog is `CHANGELOG.rst` is still measured.

    The preference is scoped WITHIN a base on purpose, so the pre-existing root-over-docs
    precedence is preserved exactly. Hoisting it across bases would additionally fix a root that
    holds only `CHANGELOG-archive.md` while an exact `docs/CHANGELOG.md` exists — but it would also
    silently move which file is measured, and with it the ±1 freshness point, for the repo shape
    that keeps a non-`.md` root changelog (`CHANGELOG.rst`) alongside an exact `docs/CHANGELOG.md`,
    where nothing is being shadowed and no defect here asks for a change. D3 is specifically about
    a fix that moves a score it claimed not to touch, so the narrower reading shipped. Both
    arrangements — the one fixed and the one deliberately left alone — are pinned by tests.

    This answers *which file*, never *does this repo keep an action ledger* — that is
    _find_action_ledger. Keeping the two questions apart is ratified decision D3."""
    bases = []
    # BL-101 P5: the directory the ledger lives in comes first (a no-op in a legacy tree, where it is `path`).
    for base in [loc.parent for loc in layout_locations(path, "CHANGELOG.md")] + [path, path / "docs"]:  # layout: ok -- the ledger's own file name: the resolver's anchor
        if base not in bases:
            bases.append(base)
    for base in bases:
        if not base.is_dir():
            continue
        exact = prefix = None
        try:
            for entry in sorted(base.iterdir()):
                if not entry.is_file():
                    continue
                upper = entry.name.upper()
                if upper == "CHANGELOG.MD":
                    exact = entry
                    break
                if prefix is None and upper.startswith("CHANGELOG"):
                    prefix = entry
        except OSError:
            pass          # keep whatever this base yielded before the listing failed
        if exact or prefix:
            return exact or prefix
    return None


def _find_action_ledger(path):
    """MEMBERSHIP — return the Path to this repo's action ledger (the root `CHANGELOG.md`,
    exactly), else None.

    Deliberately narrower than _find_changelog, and deliberately the same root-anchored, exact,
    case-sensitive name that collect_methodology_metrics probes for the compliance checklist:
    three subsystems used to answer "does this repo have a changelog" three different ways, and
    the risk layer trusted the widest of them. So a `docs/` product changelog — release notes for
    a shipped artifact, a different document with a different job — suppressed the finding that a
    methodology adopter kept no action ledger at all, and replaced it with advice to go update the
    release notes.

    One deliberate difference from the checklist probe, which uses a bare `exists()`: a
    `CHANGELOG.md` *directory* is not a ledger, so this requires a regular file, matching the same
    guard _find_changelog already applies. The cross-platform case divergence the two share is
    pre-existing and out of scope here (see the campaign plan §7 residual risk 6)."""
    for ledger in layout_locations(path, "CHANGELOG.md"):  # layout: ok -- the ledger's own file name: the resolver's anchor
        if ledger.is_file():
            return ledger
    return None


def _strip_fenced_blocks(text):
    """Drop fenced code blocks (``` or ~~~) before scanning for done-marks.

    A backlog that DOCUMENTS its own convention — "mark an item `- [x]`, then migrate it" — inside
    a fenced example is not a repo with unmigrated work. Counting that example is a match presented
    as a finding, which is the defect class this whole campaign exists to remove.

    Only a CLOSED fence is stripped. An unterminated one is left intact, which is the opposite of
    what a markdown renderer does and is deliberate: a single stray ``` line would otherwise swallow
    the rest of the file, and "no done-marks found" is not a harmless under-count here — it is
    reported as a clean backlog, which is defect 4 itself. A stray fence must not be able to
    manufacture a healthy verdict, so an unclosed one is treated as ordinary prose.
    """
    lines = text.splitlines()
    keep = [True] * len(lines)
    fence = start = None
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if fence is None:
            if _FENCE_RE.match(line):
                fence, start = stripped[:3], i
        elif stripped.startswith(fence):
            for j in range(start, i + 1):
                keep[j] = False
            fence = start = None
    return "\n".join(line for line, k in zip(lines, keep) if k)


def _split_row(line):
    """Split one markdown table row into cells on UNESCAPED pipes.

    `\\|` is the only way GFM lets a literal pipe sit inside a cell, and splitting on it invents
    cells that were never there — which can shift a prose fragment into the position the done
    predicate reads. Splitting on the escape is how a NOTES cell can fabricate a done-mark.
    """
    body = line.strip().strip("|")
    return [c.replace(r"\|", "|").strip() for c in re.split(r'(?<!\\)\|', body)]


def _header_line_indices(lines):
    """Indices of the table HEADER rows — each the row directly above a `|---|` separator.
    Line-by-line on purpose: _TABLE_SEP_RE is anchored but not MULTILINE, so it must be matched
    against individual lines and never searched across a whole document."""
    return {i - 1 for i, line in enumerate(lines)
            if i and _TABLE_SEP_RE.match(line) and lines[i - 1].strip().startswith("|")}


def _table_headers(text):
    """Yield the cell list of every table header row."""
    lines = text.splitlines()
    for i in sorted(_header_line_indices(lines)):
        yield _split_row(lines[i])


def _table_data_rows(text):
    """Yield the cell list of every table DATA row — skipping `|---|` separators AND header rows.

    Headers are excluded because a header is a label, not an item: a table with a `Completed` or
    `Resolved` column would otherwise count its own heading as a finished piece of work. (Zero rows
    of the 643-line corpus this predicate was tuned against are affected either way, so this
    protects against a shape that corpus happens not to contain rather than changing its count.)
    """
    lines = text.splitlines()
    headers = _header_line_indices(lines)
    for i, line in enumerate(lines):
        s = line.strip()
        if i in headers or not s.startswith("|") or _TABLE_SEP_RE.match(line):
            continue
        yield _split_row(line)


def _has_status_column(text):
    """True when some table header names a Status column. This, not the mere presence of a table,
    is what makes a table backlog readable: it is the author declaring that a column carries item
    state. A table with no such column (`| Item | Scope | Outcome |`) is item-bearing content whose
    convention this scanner cannot read, and it abstains rather than guess."""
    return any(any("STATUS" in c.upper() for c in header) for header in _table_headers(text))


def _cell_marks_done(cell):
    """The tuned predicate for one cell: strip markdown decoration, then match a leading token.
    `**DONE (Session 30, ...)**` is done; `blocked until SEC-013 is DONE` is not."""
    return cell.strip().strip("*`~ ").strip().upper().startswith(_BACKLOG_DONE_TOKENS)


def _count_table_done(text):
    """Data rows of >= 3 cells in which any cell BUT THE FIRST starts with a done token. The first
    cell is skipped because it is the ID column, and an ID may legitimately read `DONE-9` while the
    row itself is open. The >= 3 floor drops the 2-cell Status *legend*, which defines the
    vocabulary rather than reporting work.

    KNOWN LIMITATION, measured rather than assumed: the predicate is a union over every non-ID
    cell, not a read of the Status column, so a row whose TITLE cell begins with a done token
    ("Fixed login redirect", status READY) counts, as does a 3-column legend whose MEANING cell
    reads "Completed and tested". On the 643-line corpus this was tuned against, that costs
    nothing — all 256 counted rows are counted via a Status column (242) or sit in a table with no
    Status column at all (14), and NONE are counted only via some other column. Narrowing to the
    Status column is therefore not a free improvement: it would drop those 14 and move the ratified
    count to 242, so it is an operator decision, not an implementer's.
    """
    return sum(1 for cells in _table_data_rows(text)
               if len(cells) >= 3 and any(_cell_marks_done(c) for c in cells[1:]))


def _scan_backlog_done(path):
    """Signal F — backlog items marked done but never migrated to CHANGELOG.

    The methodology removes a backlog item from BACKLOG.md in the same commit that logs it to
    CHANGELOG.md, so a surviving done-mark is a proxy for 'completed but never migrated'.

    Returns `{"format", "done", "recognized", "source"}`. ABSTENTION IS A FIRST-CLASS RESULT
    (campaign decision D4): a `done` of 0 from a format this scanner cannot read is
    indistinguishable from a genuinely clean backlog, and that silence IS defect 4 — a real
    643-line table backlog carrying 256 done-marks reported "nothing unmigrated" for as long as
    the predicate was checkbox-only. So the count now travels with the convention it was read
    under, and `recognized` states whether the count can be trusted at all.

    The six formats, in decision order:

    - `unreadable` — the file exists but could not be read. Abstains: an I/O error is the one case
      where a 0 is guaranteed to mean nothing at all.
    - `checkbox`  — `- [x]` / `- [ ]` marks, counted by the unchanged checkbox regex. The count is
      unchanged for every input EXCEPT one this layer deliberately moves: marks inside a closed
      fenced block are no longer counted, because a documented example is not work.
    - `table`     — a table declaring a Status column, counted by the tuned predicate above.
    - `unrecognized` — item-bearing content whose done convention cannot be read: a table with no
      Status column (this repo's own `| Item | Scope | Outcome |` backlog), or plain list items
      with neither checkboxes nor a table. Abstains out loud.
    - `none`      — no checkboxes, no tables, no list items. NOT an abstention: an empty backlog is
      the healthy state and 0 is a correct measurement of it. Keeping this distinct is what stops
      the disclosure from firing on every adopter who is simply up to date.
    - `absent`    — no BACKLOG.md at any known location; nothing to recognize.

    `recognized` is True only for `checkbox` and `table` — the two formats whose count can be
    trusted. It is False for `none` and `absent` too, where the 0 is correct but is not the result
    of reading a convention; those two are distinguished from the abstaining formats by staying
    SILENT rather than by this flag.
    """
    for name in _BACKLOG_LOCATIONS:
        bl = path / name
        if not bl.is_file():
            continue
        try:
            raw = bl.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return {"format": "unreadable", "done": 0, "recognized": False, "source": name}
        text = _strip_fenced_blocks(raw)
        if _BACKLOG_BOX_RE.search(text):
            return {"format": "checkbox", "done": len(_BACKLOG_DONE_RE.findall(text)),
                    "recognized": True, "source": name}
        if _has_status_column(text):
            return {"format": "table", "done": _count_table_done(text),
                    "recognized": True, "source": name}
        if any(True for _ in _table_headers(text)) or _BACKLOG_BULLET_RE.search(text):
            return {"format": "unrecognized", "done": 0, "recognized": False, "source": name}
        return {"format": "none", "done": 0, "recognized": False, "source": name}
    return {"format": "absent", "done": 0, "recognized": False, "source": None}


def evaluate_changelog_freshness(path, git):
    """Component C — CHANGELOG ledger-lag / freshness monitor.

    Advisory only: it feeds at most a 1-point documentation nudge (present vs. fresh) plus
    RISK lines; it never hard-fails a score. The two lag signals are git-only and format-
    agnostic (they ask *when was the ledger last committed, and how far has HEAD moved since*),
    so they work for any project that keeps a CHANGELOG; the never-used signal keys on the
    methodology seed sentinel, and the backlog signal on unmigrated BACKLOG.md done-marks.
    `git` is the already-collected collect_git_metrics dict.
    """
    backlog = _scan_backlog_done(path)
    result = {
        "present": False,             # a changelog was LOCATED (root or docs/, best-available)
        "ledger_present": False,      # a root CHANGELOG.md action ledger EXISTS (membership)
        "unlogged_commits": 0,        # Signal C
        "frontier_lag_days": None,    # Signal B
        "dated_entry_count": 0,
        "has_seed_sentinel": False,
        "never_used": False,          # Signal D
        "backlog_done_unmigrated": backlog["done"],       # Signal F — pre-existing key
        "backlog_format": backlog["format"],              # which convention it was read under
        "backlog_recognized": backlog["recognized"],      # whether that count can be trusted
        "new_adopter_grace": False,
        "is_fresh": False,
        "signals": [],                # list of (severity, description) advisory tuples
    }

    # Membership, and the two findings that do not depend on locating a changelog, are computed
    # ABOVE the early return below — the return is about having nothing to measure freshness
    # against, which is not the same as having nothing to say.
    result["ledger_present"] = _find_action_ledger(path) is not None

    # Signal F keys on BACKLOG.md, not on any changelog, yet it used to be emitted below the early
    # return — so an adopter with unmigrated done-marks and NO ledger, strictly the worse case,
    # went silent while one with a ledger was warned. Adopter-scoped (root SESSION_RUNNER.md):
    # only an adopter follows the "remove from BACKLOG.md in the commit that logs it to CHANGELOG"
    # convention, so surviving done-marks are a defect there and not on a non-adopter sibling.
    #
    # Abstention (decision D4) rides the SAME adopter gate: a note that this scanner could not read
    # a backlog is only owed where the convention it cannot check actually applies. It is also
    # deliberately narrow — an EMPTY backlog reports a silent, correct 0 rather than abstaining,
    # because telling an adopter who is simply up to date that its "format was not recognized"
    # would itself be a signal that does not mean what it appears to mean.
    adopter = has_runner(path)
    if adopter and result["backlog_done_unmigrated"] > 0:
        result["signals"].append((
            "low",
            f"{backlog['source']}: {result['backlog_done_unmigrated']} done-marked item(s) "
            f"not migrated to CHANGELOG ({backlog['format']} format)",
        ))
    elif adopter and backlog["format"] in ("unrecognized", "unreadable"):
        why = ("could not be read" if backlog["format"] == "unreadable"
               else "done-mark format not recognized (no `- [x]` checkboxes and no Status column)")
        result["signals"].append((
            "low",
            f"{backlog['source']}: {why} — the unmigrated-work signal is inactive for this repo",
        ))

    changelog = _find_changelog(path)
    if changelog is None:
        # Absence is not judged here — assess_risks decides whether it is a defect (an adopter
        # with real history) or simply a project that keeps no ledger by design.
        return result
    result["present"] = True

    total_commits = git.get("total_commits", 0) or 0
    real_history = total_commits >= LEDGER_REAL_HISTORY_MIN
    grace = not real_history  # a young repo's fresh seed has not had a chance to go stale
    result["new_adopter_grace"] = grace

    # Signals C & B: git-only. A path outside a git repo yields "" and leaves both inert.
    # POSIX separators: `rel` is both a git pathspec (portable either way) and the display name in
    # every advisory below, so a Windows adopter's dashboard reads "docs/changelog.md" too.
    try:
        rel = changelog.relative_to(path).as_posix()
    except ValueError:
        rel = changelog.name
    last_touch = git_cmd(path, "log", "-1", "--format=%H", "--", rel)
    if last_touch:
        unlogged = git_cmd(path, "rev-list", "--count", "--no-merges", f"{last_touch}..HEAD")
        result["unlogged_commits"] = int(unlogged) if unlogged.isdigit() else 0
        ledger_date = git_cmd(path, "log", "-1", "--format=%ai", "--", rel)[:10]
        head_date = git_cmd(path, "log", "-1", "--format=%ai", "HEAD")[:10]
        try:
            d_ledger = datetime.strptime(ledger_date, "%Y-%m-%d")
            d_head = datetime.strptime(head_date, "%Y-%m-%d")
            result["frontier_lag_days"] = (d_head - d_ledger).days
        except ValueError:
            pass

    # Signal D: an untouched seed still carries the sentinel and has zero real dated entries.
    try:
        text = changelog.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        text = ""
    result["dated_entry_count"] = len(_DATED_ENTRY_RE.findall(text))
    result["has_seed_sentinel"] = SEED_SENTINEL in text
    result["never_used"] = (
        result["has_seed_sentinel"] and result["dated_entry_count"] == 0 and real_history
    )

    # The time-lag signal only makes sense on a repo that is otherwise active; a repo dormant
    # everywhere is already flagged by the activity score, so don't double-count it here.
    days_idle = git.get("days_since_last_commit")
    active = days_idle is not None and days_idle <= 90
    lag_days = result["frontier_lag_days"]

    lagging = (
        result["unlogged_commits"] >= LEDGER_UNLOGGED_MAX
        or (active and lag_days is not None and lag_days > LEDGER_LAG_DAYS_MAX)
    )
    # Fresh (earns the +1 nudge): present, and either under grace or neither lagging nor never-used.
    result["is_fresh"] = grace or not (lagging or result["never_used"])

    # Advisory RISK descriptions — suppressed under new-adopter grace so a fresh seed is silent.
    #
    # Each one NAMES the file it was computed against and does not call that file "the ledger",
    # because it may not be one. An adopter whose only changelog was `docs/changelog.md` used to be
    # told its "CHANGELOG ledger" was lagging: advice to go update a product release-notes file,
    # while the actual finding — no action ledger at all — was suppressed by the same file's
    # existence. Naming the measured file is what makes the advisory unable to misdirect.
    if not grace:
        if result["unlogged_commits"] >= LEDGER_UNLOGGED_MAX:
            result["signals"].append((
                "medium",
                f"{rel}: {result['unlogged_commits']} commits since it was "
                f"last updated (Component C)",
            ))
        if active and lag_days is not None and lag_days > LEDGER_LAG_DAYS_MAX:
            result["signals"].append((
                "low", f"{rel} trails HEAD by {lag_days} days",
            ))
        if result["never_used"]:
            result["signals"].append((
                "medium",
                f"{rel} present but never used — still the untouched seed on a repo with "
                "real commit history",
            ))

    return result


def collect_trim_metrics(path, files, role="adopter"):
    """S38 -- the trim-trigger row: one verdict per grow-and-must-be-read ledger, and the
    remedy. Since Phase B both halves are LEVELS in bytes -- the one-read cap and the context
    budget -- where the first half used to be a records-per-line RATE with a baseline commit.

    The remedy BRANCHES on whether the trimmer is installed for the scanned project (§7.3):
    present names a command the adopter can actually run, built from the located path; absent
    never does. Every advisory names the file it was computed against rather than saying "the
    ledger" -- a generic noun in this position once sent an adopter to update a product
    release-notes file while the real finding stayed suppressed.

    ONE DEPARTURE FROM §7.3, LABELLED AS SUCH RATHER THAN DRESSED AS A READING. The design says
    the absent branch "names the documented manual procedure". There is no such procedure to
    name: no distributed file documents ledger archiving, which is precisely what queue item S40
    is for (design §11 Phase 5 says so itself -- "Today zero distributed files say anything on
    the subject"). Verified over the WHOLE distributed set, not a convenient corner of it -- the
    design's own check greps `starter-kit/*.md`, which matches 11 of the 27 manifest entries, and
    a claim about "no distributed file" cannot be settled by a net that misses 12 of them
    (`HOW_TO_USE.md`, `ITERATIVE_METHODOLOGY.md`, `FRAMEWORK_APPARATUS.md`, and nine `workstreams/*.md`):
      python3 -c "import sys;sys.path.insert(0,'bin');import _manifest as m;\
        print('\n'.join(sorted(e[0] for e in m.DISTRIBUTION if e[0].endswith('.md'))))" \
        | xargs grep -l -i archiv
    -> `starter-kit/FRAMEWORK_LEARNINGS.md` (fork Learning #15's prose about PROVING a split
       lossless, not a procedure for performing one; that row has since left for
       docs/FORK_LEARNINGS.md), `HOW_TO_USE.md` (a worked example project's
       `POST /projects/:id/archive` endpoint), and, since S39', `starter-kit/BOOTSTRAP.md` (the
       one-line inventory entry describing what the newly distributed tool DOES -- a tool
       description, not a policy: it states no size norm, no trigger, and no procedure). None of
       the three documents ledger archiving, so the verdict is unchanged and the departure below
       still stands. The narrower `starter-kit/*.md` grep reached the same verdict, which is luck,
       not method -- and this result line is itself the demonstration, having gone from two files
       to three inside the very session that shipped the tool. Re-run it; do not read it.
    The `.md` filter is not cosmetic either: run unfiltered and the distributed set also returns
    THIS FILE, because the paragraph you are reading contains the word. A measurement that
    includes the measurer is the trap one over from the narrow-population one, and the fix for
    both is to state the population beside the number.
    So the absent branch states the measurement and says plainly that the byte half did not run.
    Inventing a destination would be the exact misdirection §7.3 exists to prevent. WHEN S40
    LANDS, this branch should point at the seed ledger's own archiving section.
    """
    result = {
        "tool_present": False,
        "tool_path": None,
        "tool_version": None,
        "budget_bytes": None,
        # BL-88 P2: the basenames the installed trimmer's OWN LEDGERS table declares, parsed from
        # its source -- None when it is absent or the reading abstained. Not to be confused with
        # "ledgers" below, which is THIS row's population: the watched Class A files it measured.
        "tool_ledgers": None,
        "ledgers": [],
        "signals": [],
    }

    # Same gate as the D4(b) risk: a project that never adopted the methodology is not told its
    # CHANGELOG.md is too long. Bound here rather than at risk time so the collector's output is
    # already scoped when assess_risks re-emits it verbatim.
    owes_ledger = has_runner(path) or role == "framework"
    if not owes_ledger:
        return result

    tool = find_trim_tool(path, role=role)
    if tool is not None:
        result["tool_present"] = True
        result["tool_version"] = tool["version"]
        result["budget_bytes"] = tool["budget"]
        result["tool_ledgers"] = tool["ledgers"]
        try:
            result["tool_path"] = tool["path"].relative_to(path).as_posix()
        except ValueError:
            result["tool_path"] = tool["path"].name

    # The population is CLASS A -- the watched names the trimmer has a config entry for -- which
    # is what keeps the row from pointing at a file the tool refuses.
    #
    # PHASE C1 CHANGED THE SPELLING, NOT THE SET, AND ON EVERY INPUT collect_all CAN PRODUCE IT
    # CHANGES NOTHING AT ALL -- said plainly because an earlier draft of this comment overstated it.
    # This filtered on `basename in TRIM_GRAMMARS`. collect_file_metrics only ever admits an exact
    # member of READ_CAP_WATCHED into read_cap_watch, so through collect_all the two filters are
    # EQUIVALENT, not merely equivalent-today: no path exists that the old filter accepts and the
    # new one rejects. The change is therefore not a bug fix and is not claimed as one.
    # WHAT IT DOES BUY, which is why it was made: this function takes `files` as a PARAMETER, so
    # its contract is wider than collect_all's output. Asked by basename, it answers "does the
    # trimmer know a grammar for a file with this name" -- which would hand a `docs/x/CHANGELOG.md`
    # a `--check` remedy if a caller ever passed one. Asked by class, it answers "is this one of
    # the watched files the trimmer can act on", which is the actual precondition for the remedy
    # below, and it makes an unclassified name a NO rather than a guess from the filename. A
    # canonical test drives that case directly, because collect_all cannot construct it.
    for w in files.get("read_cap_watch", []):
        if read_cap_class(w.get("name", w["path"])) != "A":
            continue
        fpath = path / w["path"]
        try:
            size_bytes = fpath.stat().st_size
        except OSError:
            continue
        # PHASE C2. This re-implements methodology_trim.py's Trigger, so it must move with it.
        # Every path that reaches here has already been filtered to class "A" by the guard above,
        # and w["path"] is repo-root-relative, so the ROOT SCOPING the trimmer applies is already
        # satisfied here by construction: read_cap_class() is a path lookup and answers None for a
        # nested ledger, which the guard skips. Stated rather than assumed, because the trimmer
        # reaches the same conclusion by a DIFFERENT route (an explicit relative_to check against
        # spec.basename) — the two must not drift, and a canonical test drives the nested case.
        read_fires = size_bytes > CLASS_A_FIRE_BYTES
        refused = size_bytes > READ_REFUSE_BYTES
        budget = result["budget_bytes"]
        byte_fires = None if budget is None else size_bytes > budget
        entry = {
            "path": w["path"], "lines": w["lines"], "bytes": size_bytes,
            "read_fires": read_fires, "refused": refused, "byte_fires": byte_fires,
            "fires": bool(read_fires or byte_fires),
        }
        result["ledgers"].append(entry)

        if not entry["fires"]:
            continue

        reasons = []
        if refused:
            # Stated separately and FIRST, because it is a different failure, not a worse one:
            # between the two boundaries a read returns a truncated prefix and says so, and past
            # this one it returns nothing at all -- so the front matter a reader is relying on is
            # not there either.
            reasons.append("{:,} B, PAST THE {:,} B HARD REFUSAL -- a default read of this file "
                           "returns NO CONTENT AT ALL, front matter included"
                           .format(size_bytes, READ_REFUSE_BYTES))
        elif read_fires:
            # "archive threshold", and STILL not the substring "read cap": the D4(b) risk row is
            # greppable on "read cap" and seven assertions plus the diagnostic trail in
            # dashboard_history.jsonl depend on that staying exclusive to it. The same discipline
            # keeps BL-5's "Large files detected" disjoint from both. Phase C2 changed the NUMBER
            # this row keys on, not that rule.
            #
            # WHY THE WORDING CHANGED WITH THE NUMBER. It used to say "against a 56,750 B one-read
            # budget -- a whole-file read comes back TRUNCATED". Both halves would now be wrong
            # here: the threshold is no longer the one-read budget, and truncation is no longer
            # what this row is about -- a Class A ledger is expected to sit past the cap and the
            # D4(b) row says so separately. What this row means at 192 KiB is that the file is
            # closing on the boundary where a read stops returning ANYTHING.
            reasons.append("{:,} B against the {:,} B Class A archive threshold -- within {:,} B "
                           "of the {:,} B hard refusal, past which a default read returns NO "
                           "CONTENT AT ALL"
                           .format(size_bytes, CLASS_A_FIRE_BYTES,
                                   READ_REFUSE_BYTES - size_bytes, READ_REFUSE_BYTES))
        if byte_fires:
            reasons.append("{:,} B against a {:,} B budget".format(size_bytes, budget))
        why = "; ".join(reasons)

        # `--check` and NOT `--write`, deliberately. A trigger firing is not the same as a trim
        # being the right move, and the tool knows the difference: on this repo `--write`
        # against HANDOFFS.md refuses twice over -- once because the undocumented set is
        # non-empty (a trim commit would advance the Phase 0 frontier and hide those commits
        # permanently) and once because SRF is past RED, where archiving resets the level and
        # not the rate. An advisory promising "--write to archive" would name a command that
        # declines, which is the misdirection this wording exists to avoid. `--check` reports
        # the full trigger and the refusal, writes nothing, and keeps this row read-only.
        if result["tool_present"]:
            remedy = ("run `python3 %s --file %s --check` for the full report and whether a "
                      "trim is the right move" % (result["tool_path"], w["path"]))
        else:
            remedy = ("%s is not installed here, so this must be archived by hand"
                      % TRIM_TOOL_NAME)
        result["signals"].append(
            ("medium", "%s: %s -- the archive trigger fires; %s" % (w["path"], why, remedy)))

    # THE ABSTENTION DISCLOSURE WAS HERE, AND PHASE B DELETED THE STATE IT DETECTED rather than
    # the disclosure alone -- which is why this note replaces it instead of the code being quietly
    # dropped. It fired once per repo where NEITHER half could measure a watched ledger: the line
    # RATE had no baseline archive AND the byte budget was unreadable. Decision D4 forbids
    # reporting a 0 from an unread source as a clean state, and a ledger about which this scanner
    # said nothing at all was exactly that.
    #
    # The read half is a LEVEL now. It answers from the file's own size, with no git history, no
    # baseline commit and no trimmer installed, so it answers for every watched ledger in every
    # repo -- including a freshly-bootstrapped one that has never archived, which was the
    # commonest way into the old silent state. The conjunction can no longer be true.
    #
    # AND NARROWING IT TO THE BYTE HALF ALONE WOULD BE A REGRESSION, NOT A SALVAGE. That is what
    # an early draft did: it fired whenever the budget was unavailable and told the whole adopter
    # fleet its ledgers were "unmeasured" over a budget no distributed file has ever named. The
    # conjunction was the fix for that. Restoring half of it would restore the bug -- so if a
    # future change gives the read half a way to abstain, re-add the CONJUNCTION, not this.

    return result


def checklist_pct(raw_score, maximum):
    """Normalize a raw weighted checklist sum to a true 0-100 percentage of ITS OWN scale.

    Two checklists now feed the same 0-20 health dimension and the same rendered "%", on
    different denominators (115 and 105). Passing the scale in is what keeps a single site
    knowing how to normalize; the alternative — consumers dividing by whichever module constant
    they think applies — is exactly the several-sites-know-the-scale arrangement that produced
    the 110%-rendered-as-a-percentage defect in the first place."""
    if maximum <= 0:
        return 0
    return int(round(100 * raw_score / maximum))


def compliance_pct(raw_score):
    """Normalize a raw weighted checklist sum to a true 0-100 percentage.

    Normalization happens ONCE, here on the producer side. Every consumer — the health
    dimension, the risk thresholds, the portfolio grid and the project card — then reads an
    already-correct percentage instead of re-deriving one, so no site can drift from the scale
    independently, and only this function knows the denominator.

    The health dimension does scale the rounded percentage again (`int(pct * 0.2)`), which on
    the current checklist credits one extra point at two of the twenty-four reachable sums
    (raw 40 and 80). That is deliberate: the alternative — each consumer dividing by
    METHODOLOGY_MAX itself — re-creates the several-sites-know-the-scale arrangement that
    produced the defect, at a cost of one advisory point in a 0-20 band."""
    return checklist_pct(raw_score, METHODOLOGY_MAX)


def collect_methodology_metrics(path, role="adopter"):
    """Score the repo against the checklist its ROLE makes it answerable to.

    `role` defaults to "adopter" so every existing caller keeps its meaning, and so a project
    dict produced by an older run stays readable.

    The result keeps the dict key `methodology` and every field name it had — portfolio
    aggregation, the JSON export and the radar all key on those, and a context-dependent
    meaning behind a stable key is the established convention here (the `testing` slot already
    holds Render/Verification for a doc-only repo). What is added is the identity of the
    checklist that ran, so no consumer has to infer it.
    """
    checklist = FRAMEWORK_ITEMS if role == "framework" else METHODOLOGY_ITEMS
    maximum = FRAMEWORK_MAX if role == "framework" else METHODOLOGY_MAX

    # One existence probe per item: the weighted score, the present/missing counts and the
    # per-item map are all derived from this single map (they were previously three separate
    # loops over the same paths, each re-hitting the filesystem).
    #
    # BL-101 P5: items are located through the layout (the names stay the legacy ones). For the PUBLISHER
    # that moves exactly its own CHANGELOG.md and HANDOFFS.md, the instance files it operates; its sources
    # (ITERATIVE_METHODOLOGY.md, workstreams/, bin/, starter-kit/) are not in LAYOUT_MOVED under those
    # names and are read where they are, so the same call serves both checklists.
    items = {}
    for item_path, weight, kind in checklist:
        items[item_path] = any(loc.is_dir() if kind == "dir" else loc.exists()
                               for loc in layout_locations(path, item_path))

    score = sum(weight for item_path, weight, _ in checklist if items[item_path])

    return {
        "role": role,
        "checklist": "framework" if role == "framework" else "adopter",
        "checklist_max": maximum,
        "methodology_files_present": sum(1 for present in items.values() if present),
        "methodology_files_total": len(checklist),
        # Both are exported: the raw weighted sum stays inspectable (and scale-independent for
        # the "no adoption at all" test), while compliance_pct is what may be rendered as a "%".
        "compliance_score": score,
        "compliance_pct": checklist_pct(score, maximum),
        "missing_files": [item_path for item_path, present in items.items() if not present],
        "items": items,
        # BL-101 P5: which layout this project is in, and the paths that settled it (additive).
        "layout": project_layout(path),
    }


def collect_dependency_metrics(path):
    dep_files = []
    total = 0

    # requirements.txt
    req = path / "requirements.txt"
    if req.exists():
        try:
            with open(req) as f:
                count = sum(1 for line in f if line.strip() and not line.strip().startswith("#"))
            dep_files.append({"file": "requirements.txt", "count": count})
            total += count
        except OSError:
            pass

    # package.json
    pkg = path / "package.json"
    if pkg.exists():
        try:
            with open(pkg) as f:
                data = json.load(f)
            deps = len(data.get("dependencies", {}))
            dev_deps = len(data.get("devDependencies", {}))
            dep_files.append({"file": "package.json", "count": deps + dev_deps,
                              "detail": f"{deps} deps + {dev_deps} devDeps"})
            total += deps + dev_deps
        except (OSError, json.JSONDecodeError):
            pass

    # Cargo.toml
    cargo = path / "Cargo.toml"
    if not cargo.exists():
        cargo = path / "src-tauri" / "Cargo.toml"
    if cargo.exists():
        try:
            with open(cargo) as f:
                in_deps = False
                count = 0
                for line in f:
                    stripped = line.strip()
                    if stripped.startswith("[dependencies") or stripped.startswith("[dev-dependencies"):
                        in_deps = True
                        continue
                    if stripped.startswith("[") and in_deps:
                        in_deps = False
                    if in_deps and stripped and not stripped.startswith("#"):
                        count += 1
            dep_files.append({"file": str(cargo.relative_to(path)), "count": count})
            total += count
        except OSError:
            pass

    # pom.xml (Maven)
    pom = path / "pom.xml"
    if pom.exists():
        try:
            with open(pom, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            # Simple count of <dependency> tags (rough but useful)
            count = content.count("<dependency>")
            if count > 0:
                dep_files.append({"file": "pom.xml", "count": count})
                total += count
        except OSError:
            pass

    # build.gradle / build.gradle.kts
    for gradle_name in ["build.gradle", "build.gradle.kts"]:
        gradle = path / gradle_name
        if gradle.exists():
            try:
                with open(gradle, "r", encoding="utf-8", errors="ignore") as f:
                    count = sum(1 for line in f if "implementation" in line or "api(" in line)
                if count > 0:
                    dep_files.append({"file": gradle_name, "count": count})
                    total += count
            except OSError:
                pass
            break

    # platformio.ini
    pio = path / "platformio.ini"
    if pio.exists():
        try:
            with open(pio) as f:
                count = 0
                for line in f:
                    if "lib_deps" in line:
                        count += 1
                for line in f:
                    if line.startswith(" ") or line.startswith("\t"):
                        count += 1
                    else:
                        break
            dep_files.append({"file": "platformio.ini", "count": max(count, 1)})
            total += max(count, 1)
        except OSError:
            pass

    return {"dependency_files": dep_files, "total_dependencies": total}


def collect_github_metrics(path):
    """Collect open issues and PR counts via gh CLI."""
    metrics = {"open_issues": None, "open_prs": None, "repo_slug": None}

    # Parse remote URL to get owner/repo
    remote = git_cmd(path, "remote", "get-url", "origin")
    if not remote:
        return metrics

    # Parse SSH or HTTPS URLs
    slug = None
    if "github.com" in remote:
        # git@github.com:owner/repo.git or https://github.com/owner/repo.git
        for prefix in ["git@github.com:", "https://github.com/"]:
            if remote.startswith(prefix):
                slug = remote[len(prefix):].rstrip(".git")
                break

    if not slug:
        return metrics

    metrics["repo_slug"] = slug

    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{slug}", "--jq",
             '{issues: .open_issues_count}'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            data = json.loads(result.stdout.strip())
            metrics["open_issues"] = data.get("issues", 0)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError, json.JSONDecodeError):
        pass

    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{slug}/pulls?state=open&per_page=1",
             "--jq", "length"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            count_str = result.stdout.strip()
            metrics["open_prs"] = int(count_str) if count_str.isdigit() else 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    return metrics


def collect_vulnerability_metrics(path):
    """Scan for dependency vulnerabilities using available audit tools."""
    metrics = {"vulnerabilities": [], "total_vulns": 0, "scanned": False}

    # npm audit
    pkg = path / "package.json"
    if pkg.exists() and (path / "node_modules").exists():
        try:
            result = subprocess.run(
                ["npm", "audit", "--json"],
                capture_output=True, text=True, timeout=30, cwd=str(path)
            )
            # npm audit returns non-zero when vulns found — that's expected
            data = json.loads(result.stdout)
            vuln_meta = data.get("metadata", {}).get("vulnerabilities", {})
            total = sum(vuln_meta.get(s, 0) for s in ["low", "moderate", "high", "critical"])
            if total > 0 or result.returncode == 0:
                metrics["scanned"] = True
                metrics["total_vulns"] += total
                for sev in ["critical", "high", "moderate", "low"]:
                    count = vuln_meta.get(sev, 0)
                    if count > 0:
                        metrics["vulnerabilities"].append({
                            "source": "npm", "severity": sev, "count": count
                        })
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError,
                json.JSONDecodeError, KeyError):
            pass
    elif pkg.exists() and (path / "package-lock.json").exists():
        # Can audit without node_modules if lock file exists
        try:
            result = subprocess.run(
                ["npm", "audit", "--json", "--package-lock-only"],
                capture_output=True, text=True, timeout=30, cwd=str(path)
            )
            data = json.loads(result.stdout)
            vuln_meta = data.get("metadata", {}).get("vulnerabilities", {})
            total = sum(vuln_meta.get(s, 0) for s in ["low", "moderate", "high", "critical"])
            if total > 0 or result.returncode == 0:
                metrics["scanned"] = True
                metrics["total_vulns"] += total
                for sev in ["critical", "high", "moderate", "low"]:
                    count = vuln_meta.get(sev, 0)
                    if count > 0:
                        metrics["vulnerabilities"].append({
                            "source": "npm", "severity": sev, "count": count
                        })
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError,
                json.JSONDecodeError, KeyError):
            pass

    return metrics


def collect_coverage_config(path):
    configs = []
    checks = [
        ".coveragerc", "setup.cfg", "pyproject.toml", "pytest.ini",
        "jest.config.js", "jest.config.ts", "jest.config.json",
        ".nycrc", ".nycrc.json", "vitest.config.ts", "vitest.config.js",
        "vite.config.ts", "vite.config.js",
        "jacoco.xml",
    ]
    for root_dir, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in WALK_SKIP]
        rel = Path(root_dir).relative_to(path)
        for name in checks:
            if name in files:
                # For vite.config files, only include if they contain coverage config
                if name.startswith("vite.config."):
                    try:
                        with open(Path(root_dir) / name) as f:
                            content = f.read()
                        if "coverage" not in content:
                            continue
                    except OSError:
                        continue
                label = name if rel == Path(".") else f"{rel}/{name}"
                configs.append(label)
        # Check package.json for jest/nyc/coverage-tool config
        if "package.json" in files:
            pkg = Path(root_dir) / "package.json"
            try:
                with open(pkg) as f:
                    data = json.load(f)
                top_level_keys = set(data.keys())
                dev_deps = data.get("devDependencies", {})
                found = []
                # Top-level jest or nyc config blocks
                if "jest" in top_level_keys:
                    found.append("jest")
                if "nyc" in top_level_keys:
                    found.append("nyc")
                # Coverage packages in devDependencies
                for pkg_name in ("c8", "@vitest/coverage-v8", "@vitest/coverage-istanbul"):
                    if pkg_name in dev_deps:
                        found.append(pkg_name)
                # Fallback: detect unknown @vitest/coverage-* variants
                if not any(f.startswith("@vitest/coverage") for f in found):
                    if any(k.startswith("@vitest/coverage") for k in dev_deps):
                        found.append("vitest-coverage")
                if found:
                    tag = ", ".join(sorted(found))
                    label = f"package.json ({tag})" if rel == Path(".") else f"{rel}/package.json ({tag})"
                    configs.append(label)
            except (OSError, json.JSONDecodeError):
                pass
        # Check requirements.txt for pytest-cov
        if "requirements.txt" in files:
            req = Path(root_dir) / "requirements.txt"
            try:
                with open(req) as f:
                    content = f.read()
                if "pytest-cov" in content:
                    label = "requirements.txt (pytest-cov)" if rel == Path(".") else f"{rel}/requirements.txt (pytest-cov)"
                    configs.append(label)
            except OSError:
                pass

    return configs


# === SCORING ===

# === BL-5: DOC-ONLY / RESEARCH-REPO SCORING ===

_RENDER_DEP_RE = re.compile(r'\b(?:pdffonts|fc-list|fc-match|kpsewhich|fc-cache)\b')
_DOCS_RENDER_CI_RE = re.compile(
    r'quarto|sphinx|mkdocs|latexmk|pandoc|mdbook|asciidoctor|typst|gh-pages', re.IGNORECASE)
_FONT_TOKEN_RE = re.compile(r'\b(?:mainfont|fontspec)\b', re.IGNORECASE)
_PANDOC_RE = re.compile(r'\bpandoc\b', re.IGNORECASE)
_QUARTO_RENDER_RE = re.compile(r'quarto\s+render', re.IGNORECASE)
_LINK_CHECK_RE = re.compile(r'lychee|htmltest|markdown-link-check|linkchecker', re.IGNORECASE)


def _read_capped(fpath, cap=200_000):
    """Read a text file with a size cap; '' on any error or if oversized. Keeps the render scan bounded."""
    try:
        if fpath.stat().st_size > cap:
            return ""
        return fpath.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def collect_render_metrics(path, files, ci, meth):
    """BL-5 — Render/Verification signals for a document/research repo.

    HONEST PROXY: a static scan cannot execute a render, so this scores render/verification
    *configuration and wiring*, never render *success*. Returns a 0-20 score that fills the
    second health slot (in place of Testing) when detect_doc_only says the repo is doc-only;
    ``toolchain_present`` also feeds detection. One bounded pass — glob for well-known config
    files and size-cap-read only a handful of root build files, the CI workflow bodies, and
    root *.tex / _quarto.yml. No full re-walk (precedent: collect_ci_metrics / collect_coverage_config).
    """
    result = {"score": 0, "toolchain_present": False, "render_dep_verified": False, "signals": []}

    def has(*globs):
        for g in globs:
            try:
                if next(path.glob(g), None) is not None:
                    return True
            except OSError:
                pass
        return False

    # Text corpus we are allowed to scan: root build drivers + CI workflow bodies + quarto/tex config.
    build_files = ["Makefile", "makefile", "justfile", "Justfile", "build.sh", "render.sh"]
    driver_present = any((path / b).is_file() for b in build_files)
    texts = [_read_capped(path / b) for b in build_files if (path / b).is_file()]
    wf_dir = path / ".github" / "workflows"
    if wf_dir.is_dir():
        for wf in sorted(wf_dir.glob("*.yml")) + sorted(wf_dir.glob("*.yaml")):
            texts.append(_read_capped(wf))
    for cfg in ("_quarto.yml", "_quarto.yaml"):
        if (path / cfg).is_file():
            texts.append(_read_capped(path / cfg))
    for tex in list(path.glob("*.tex"))[:5]:
        texts.append(_read_capped(tex))
    blob = "\n".join(texts)
    wf_names = " ".join(ci.get("workflow_files", []))

    score = 0

    # A. Render toolchain configured (up to 6).
    toolchain = has(
        "_quarto.yml", "_quarto.yaml", "*.qmd", "conf.py", "mkdocs.yml", "mkdocs.yaml",
        "book.toml", "_bookdown.yml", "latexmkrc", ".latexmkrc", "*.tex", "*.typ", "*.adoc",
        "antora-playbook.yml",
    )
    if not toolchain and (path / "_config.yml").is_file() and (path / "_toc.yml").is_file():
        toolchain = True  # Jupyter Book
    if not toolchain and _PANDOC_RE.search(blob):
        toolchain = True
    result["toolchain_present"] = toolchain
    if toolchain:
        score += 4
    if driver_present or _QUARTO_RENDER_RE.search(blob):
        score += 2  # a repeatable render driver, scripted not ad hoc
    result["signals"].append(("Render toolchain configured", toolchain))

    # B. Render-dependency verification — v2.5 hard rule / anti-pattern #20 (up to 6).
    dep_checked = bool(_RENDER_DEP_RE.search(blob))
    result["render_dep_verified"] = dep_checked
    if dep_checked:
        score += 4  # strongest signal: post-render embedding check is wired (pdffonts/fc-list/kpsewhich)
    if has("*.sty", "fonts") or _FONT_TOKEN_RE.search(blob):
        score += 2
    result["signals"].append(
        ("Render-dependency check wired (pdffonts/fc-list/kpsewhich)", dep_checked))

    # C. Render / link-check CI — the CI-equivalent (up to 5).
    render_ci = bool(_DOCS_RENDER_CI_RE.search(wf_names + "\n" + blob))
    if render_ci:
        score += 3
    link_check = (
        has(".lycheeignore", "lychee.toml", ".htmltest.yml", ".htmltest.yaml")
        or (path / "bin" / "check-links").is_file()
        or bool(_LINK_CHECK_RE.search(blob))
    )
    if link_check:
        score += 2
    result["signals"].append(("Render / link-check CI pipeline", render_ci or link_check))

    # D. Research-Documentation verification adoption (up to 3).
    verif_artifact = has(
        "VERIFICATION*", "*checklist*", "*source-audit*", "CITATION.cff", "references", "*.bib")
    if verif_artifact:
        score += 2
    ws_present = any(loc.is_file() for loc in layout_locations(
        path, "docs/methodology/workstreams/RESEARCH_DOCUMENTATION_WORKSTREAM.md")) or any(  # layout: ok -- a workstream's legacy name; the first is located through layout_locations
        (path / rel).is_file() for rel in (
            "workstreams/RESEARCH_DOCUMENTATION_WORKSTREAM.md",
            "RESEARCH_DOCUMENTATION_WORKSTREAM.md",  # layout: ok -- a workstream's legacy name; the first is located through layout_locations
        ))
    if ws_present:
        score += 1
    result["signals"].append(
        ("Research-Documentation verification artifacts", verif_artifact or ws_present))

    result["score"] = min(20, score)
    return result


# === QUALITY GATES (quality-ratchet plan, D6) ===
#
# Reads what the ratchet declares (.quality-gates.json) and, where present, what it last measured
# (its results file). Git-only for history: a loosened threshold is derived from the manifest's
# own commits — the scanner never executes a project command. ADVISORY, like every other signal
# here: the gate is the pre-commit ratchet, where it belongs; this reports its outcomes.
#
# An absent manifest is silent. So is a present-but-EMPTY one: bin/sync seeds it empty by decision
# (plan §8.4), so its bare presence proves sync ran, not that anything was declared — flagging it
# would fire on every synced adopter for a change they did not make (the CHECKLIST_EXEMPT rule).
GATES_MANIFEST = ".quality-gates.json"  # layout: ok -- the manifest's own file name; where it lives is resolved by gate_manifest_rels
GATES_RESULTS_DEFAULT = ".quality-gates-results.json"  # layout: ok -- the results file's own name; it lives beside the manifest unless the manifest names one
GATES_HISTORY_MAX = 50          # manifest commits scanned for loosenings, newest first


def gate_manifest_rels(path):
    """The two places the manifest may live, the one the project's layout names first (BL-101 P5). Both are
    always read for HISTORY: a manifest that moved has its older versions at the other path, and a walk by one
    name stops at the move, which hides a floor lowered inside the move commit and reads the move itself as a
    removal (plan E2)."""
    legacy, moved = GATES_MANIFEST, NEW_LAYOUT_DIR + "/" + GATES_MANIFEST
    return [moved, legacy] if resolve_layout(path, GATES_MANIFEST)[0] == "new" else [legacy, moved]


def _gate_map(cfg):
    gates = cfg.get("gates") if isinstance(cfg, dict) else None
    if not isinstance(gates, list):
        return {}
    return {g["name"]: g for g in gates if isinstance(g, dict) and isinstance(g.get("name"), str)}


def _gate_loosenings(old_cfg, new_cfg):
    """Loosenings in old -> new: a `min` lowered, a `max` raised, a direction flipped, a gate
    removed. Mirrors quality_ratchet.compare() deliberately (the scanner cannot import an
    adopter-root tool). A flip used to fall through both threshold branches and out of the
    function — refused by the tool, reported as nothing here (PR #82 review, section 4)."""
    out = []
    old, new = _gate_map(old_cfg), _gate_map(new_cfg)
    for name, og in old.items():
        ng = new.get(name)
        if ng is None:
            out.append({"name": name, "from": _num(og.get("threshold")), "to": None, "kind": "removed"})
            continue
        if og.get("direction") != ng.get("direction"):
            out.append({"name": name, "from": f"{og.get('direction')} {og.get('threshold')}",
                        "to": f"{ng.get('direction')} {ng.get('threshold')}", "kind": "direction flipped"})
            continue
        try:
            ot, nt = float(og.get("threshold")), float(ng.get("threshold"))
        except (TypeError, ValueError):
            continue
        if og.get("direction") == "min" and nt < ot:
            out.append({"name": name, "from": ot, "to": nt, "kind": "floor lowered"})
        elif og.get("direction") == "max" and nt > ot:
            out.append({"name": name, "from": ot, "to": nt, "kind": "ceiling raised"})
    return out


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return v


def _gate_command_changes(old_cfg, new_cfg):
    """A gate whose `command` or `extract` differs between two versions. Not a loosening — the
    scanner cannot know whether the new command is easier — but the tool warns on it at commit
    time and the bypass message promises the dashboard shows it, so it is an advisory here."""
    out = []
    old, new = _gate_map(old_cfg), _gate_map(new_cfg)
    for name, og in old.items():
        ng = new.get(name)
        if ng is None:
            continue
        for field in ("command", "extract"):
            if og.get(field) != ng.get(field):
                out.append({"name": name, "field": field})
    return out


def _gate_manifest_history(path):
    """[(sha, date, cfg)] newest first, capped, from the manifest's own git history. A version
    the commit deleted, or one that does not parse, is recorded as an EMPTY gate list flagged
    `_deleted` / `_unreadable` — never skipped. Skipping it dropped the deletion AND both pairs
    around it from the comparison (PR #82 review, 2a): an empty gate set is exactly the input
    that makes "every gate is missing" true, and that is the one case _gate_loosenings already
    handles.

    FIRST-PARENT ON PURPOSE (BL-99). Each version is later compared with the next older ROW, so
    the rows must be one line of ancestry. A plain `git log -- <path>` follows both parents of a
    merge whose manifest matches neither, and lists the two lineages interleaved by commit date:
    the newer of two sibling commits is then compared with a commit that is not its ancestor and
    reports a floor "lowered" that nobody lowered. It also follows only ONE parent of a merge that
    matches the other, so a merge that resolves to the lower of two floors is never compared with
    the line it merged into, and a real loosening reads as nothing. `--first-parent` compares every
    version, a merge included, with the line it landed on -- the base `quality_ratchet.py
    --precommit` uses (staged against HEAD), and what SAFEGUARDS' "a loosening resolved into a
    merge is caught by the dashboard" needs. The price: a loosening made on a side branch is
    reported at the merge that carried it in, not at the side commit (`git diff <sha>^1 <sha>`)."""
    rels = gate_manifest_rels(path)
    log = git_cmd(path, "log", "--first-parent", f"--max-count={GATES_HISTORY_MAX}",
                  "--format=%h|%ad", "--date=short", "--", *rels)
    hist = []
    for line in log.splitlines():
        sha, _, date = line.partition("|")
        raw = None
        for rel in rels:                 # the layout's own place first; a version has the manifest at one of them
            if _blob_exists(path, sha, rel):
                raw = git_cmd(path, "show", f"{sha}:{rel}")
                break
        if raw is None:
            hist.append((sha, date, {"gates": [], "_deleted": True}))
            continue
        try:
            cfg = json.loads(raw)
            if not isinstance(cfg, dict):
                raise ValueError("not an object")
            hist.append((sha, date, cfg))
        except ValueError:
            hist.append((sha, date, {"gates": [], "_unreadable": True}))
    return hist


def _blob_exists(path, sha, rel=GATES_MANIFEST):
    """Whether the manifest exists at `sha` — by exit code, which git_cmd discards. `git show`
    on a deleted path prints nothing to stdout, indistinguishable from an empty file."""
    try:
        r = subprocess.run(["git", "-C", str(path), "cat-file", "-e", f"{sha}:{rel}"],
                           capture_output=True, timeout=5)
        return r.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def collect_gate_metrics(path):
    m = {"manifest_present": False, "manifest_deleted": False, "declared": 0,
         "results_present": False, "results_stale": False, "summary": None, "failing": [],
         "unmeasured": [], "loosened": [], "commands_changed": [], "ran_at": None,
         "convention": "quality-gates.json v1"}
    mp = next((loc for loc in layout_locations(path, GATES_MANIFEST) if loc.is_file()), path / GATES_MANIFEST)
    # The history walk runs whenever the manifest HAS a history — including when the worktree
    # no longer has the file. Returning early on `not mp.is_file()` made the deleted-and-never-
    # re-added state, the largest loosening available, report nothing (PR #82 review, 2a).
    hist = _gate_manifest_history(path) if (mp.is_file() or _manifest_has_history(path)) else []
    _fold_history(m, hist)
    if not mp.is_file():
        m["manifest_deleted"] = bool(hist)
        return m
    m["manifest_present"] = True
    try:
        cfg = json.loads(mp.read_text(encoding="utf-8-sig", errors="ignore"))
    except (ValueError, OSError):
        m["convention"] = "unreadable manifest"
        return m
    gates = _gate_map(cfg)
    m["declared"] = len(gates)
    if not gates:
        return m

    # A results file the manifest NAMES is project-relative, as before; the default sits beside the manifest.
    rp = None
    if isinstance(cfg, dict):
        rp = path / cfg["results_file"] if cfg.get("results_file") else mp.parent / GATES_RESULTS_DEFAULT
    if rp is not None and rp.is_file():
        try:
            snap = json.loads(rp.read_text(encoding="utf-8", errors="ignore"))
        except (ValueError, OSError):
            snap = None
        if isinstance(snap, dict) and isinstance(snap.get("gates"), list):
            m["results_present"] = True
            m["ran_at"] = snap.get("ran_at")
            # Stale = the manifest changed since that run (the tool stamps a hash of `gates`).
            digest = hashlib.sha256(json.dumps(cfg.get("gates", []), sort_keys=True).encode()
                                    ).hexdigest()[:12]
            m["results_stale"] = snap.get("manifest") != digest
            results = [r for r in snap["gates"] if isinstance(r, dict)]
            m["summary"] = {k: sum(1 for r in results if r.get("status") == k)
                            for k in ("pass", "fail", "unmeasured")}
            m["failing"] = [r.get("name") for r in results if r.get("status") == "fail"]
            m["unmeasured"] = [r.get("name") for r in results if r.get("status") == "unmeasured"]
    return m


def _manifest_has_history(path):
    # The same line of ancestry the walk reads, so "has a history" and "was walked" cannot differ.
    return bool(git_cmd(path, "log", "--first-parent", "--max-count=1", "--format=%h", "--",
                        *gate_manifest_rels(path)))


def _fold_history(m, hist):
    """Each version is compared to the nearest OLDER version that declared a gate — the same
    base quality_ratchet.py uses — so 80 -> (deleted) -> 1 reads as 80 -> 1, not as 'added'."""
    for i, (sha, date, newer) in enumerate(hist):
        older = next((c for (_s, _d, c) in hist[i + 1:] if _gate_map(c)), None)
        if older is None:
            continue
        for l in _gate_loosenings(older, newer):
            l.update({"sha": sha, "date": date, "manifest_deleted": bool(newer.get("_deleted"))})
            m["loosened"].append(l)
        for c in _gate_command_changes(older, newer):
            c.update({"sha": sha, "date": date})
            m["commands_changed"].append(c)


def _profile_tokens(path):
    """Read .methodology-profile into a set of lowercase declaration tokens.

    ONE reader for both axes. Two readers would each have to re-implement six invariants
    (utf-8-sig, errors=ignore, the is_file and OSError guards, lowercasing, comment stripping)
    and they would drift — this file already documents three subsystems that disagreed about
    "does this repo have a changelog", and reconciling them was an entire layer of work.

    COMMENTS ARE STRIPPED BEFORE TOKENIZING, and that is load-bearing rather than cosmetic. The
    only marker in the live adopter population is 8 lines / 87 whitespace tokens: one
    declaration followed by seven lines of `#` prose explaining WHY the owner set it, and that
    prose mentions the opposite token twice. It survives being read as a token bag only because
    both mentions happen to carry trailing punctuation ("code," and "code."). Delete one comma
    and a reader that tokenizes comments discards the very override the file exists to assert.
    So scanning the whole file without stripping comments is strictly more dangerous than
    reading only the first token, which is what this replaces.
    """
    marker = path / PROFILE_MARKER
    try:
        if not marker.is_file():
            return frozenset()
        text = marker.read_text(encoding="utf-8-sig", errors="ignore")
    except OSError:
        return frozenset()
    # Everything from the first "#" on a line is prose, so a whole-line comment contributes
    # nothing and a trailing comment contributes only what precedes it. One rule covers both.
    #
    # ONLY THE FIRST LINE THAT SURVIVES THAT IS A DECLARATION; every later line is prose, even
    # uncommented prose. Mining the whole file was this reader's first shape and it was WRONG in
    # a way that inverted the very defect this layer fixes: an owner who wrote an unmarked
    # sentence of explanation — "We keep our docs in the framework style" — had a bare axis token
    # read as a deliberate override, and an adopter was graded as the publisher with
    # reason="marker" and nothing disclosed. Worse, "This is a code repository with helper
    # scripts" under a `doc-only` declaration fabricated a CONTRADICTION and destroyed the
    # override entirely. Reading tokens[0] never had that failure, so whole-file scanning would
    # have been a regression dressed as a fix. Composing the two axes needs one line, not two.
    for line in text.splitlines():
        declaration = line.split("#", 1)[0].strip()
        if declaration:
            return frozenset(declaration.lower().split())
    return frozenset()


def _resolve_marker_axis(tokens, axis):
    """Resolve one bidirectional axis of the profile marker.

    Returns (value, reason): (True|False, "marker") when exactly one of the pair is declared,
    (None, "marker-contradiction") when both are, (None, "") when neither is. The caller falls
    back to its heuristic for both None cases — but the reasons are kept distinct, because a
    contradiction is a declaration this scanner could not read and gets said out loud, while an
    absent declaration is simply silence.
    """
    positive, negative = axis
    declared_yes, declared_no = positive in tokens, negative in tokens
    if declared_yes and declared_no:
        return None, "marker-contradiction"
    if declared_yes:
        return True, "marker"
    if declared_no:
        return False, "marker"
    return None, ""


def detect_repo_role(path):
    """Classify a repo as the methodology's PUBLISHER or one of its consumers.

    Returns {"role": "framework"|"adopter", "reason": "marker"|"marker-contradiction"|
    "structural"|"default"}. Advisory only; nothing gates.

    The structural test is a three-way AND: distribution machinery, a starter-kit runner, and NO
    runner of its own at the root. The first two are the campaign plan's; the third mechanizes
    the plan's own description of the one shape this heuristic could misfire on — a repo that
    ships starter-kit/ templates plus distribution machinery *without installing to its own
    root*. A monorepo that vendors this framework and also genuinely runs it keeps its adoption
    grading, so the conjunct can only remove false positives, never create one.

    bin/ is a sound marker because the distribution manifest ships nothing from it: no adopter
    can acquire bin/_manifest.py through bin/sync, so no synced repo can drift into this branch.
    """
    role, reason = _resolve_marker_axis(_profile_tokens(path), PROFILE_ROLE_TOKENS)
    if role is not None:
        return {"role": "framework" if role else "adopter", "reason": reason}

    publishes = (path / "bin" / "_manifest.py").is_file()
    templates = (path / "starter-kit" / "SESSION_RUNNER.md").is_file()
    installed = has_runner(path)
    if publishes and templates and not installed:
        return {"role": "framework", "reason": reason or "structural"}
    return {"role": "adopter", "reason": reason or "default"}


def detect_doc_only(path, files, render):
    """BL-5 — classify a repo as document-only / research.

    Order: marker -> has-tests -> source-cap -> corpus. Each step before the corpus check is a
    reason this CANNOT be a document project; the corpus check is the only positive evidence.

    Returns {"is_doc_only": bool, "reason": "marker"|"marker-contradiction"|"heuristic"}.
    Advisory only; nothing gates.
    """
    # 1. Explicit bidirectional marker wins (force either classification). Read from the shared
    #    token set rather than the first word, so a marker can declare this axis and the role
    #    axis together in either order. Reading only tokens[0] meant "framework doc-only"
    #    silently discarded the doc-only declaration while "doc-only framework" honoured it.
    doc_only, reason = _resolve_marker_axis(_profile_tokens(path), PROFILE_CORPUS_TOKENS)
    if doc_only is not None:
        return {"is_doc_only": doc_only, "reason": reason}
    # A contradicted axis still falls through to the heuristic for its VALUE, but keeps its own
    # reason: the reader is owed the fact that a declaration was made and could not be read.
    reason = reason or "heuristic"

    # 2. A repo that HAS tests is not a document project, whatever its doc corpus looks like.
    #    This dimension exists to stop penalizing repos with nothing to unit-test; a repo with a
    #    real suite has already answered that question itself. Without this gate the tutorials'
    #    own sample project — a Python CLI with a green pytest suite — classified doc-only once
    #    `bin/sync` discounted the framework markdown around it, and then drew a "no tests"
    #    advisory ON A PASSING SUITE. A signal contradicted by the very metrics dict that emits it
    #    is this campaign's whole defect class, so it is gated here rather than explained on the
    #    card. Below the marker on purpose: an explicit `doc-only` declaration still wins, because
    #    declaring is exact where detection is a guess.
    if files.get("by_category", {}).get("test", {}).get("count", 0) > 0:
        return {"is_doc_only": False, "reason": reason}

    # 3. Source-cap short-circuit: real code should be tested; never silently exempt it.
    src = files["by_category"]["source"]["loc"]
    if src > DOC_ONLY_SOURCE_LOC_MAX:
        return {"is_doc_only": False, "reason": reason}

    # 4. Corpus disjunction (only when source is negligible): a real doc corpus OR a render
    #    toolchain — the latter catches a pure-LaTeX (or other toolchain-only) repo whose .tex
    #    files are not counted as docs (so its doc_loc is ~0; BL-34 added `.qmd`/`.rmd` to
    #    DOC_EXTS, so a pure-Quarto/R-Markdown corpus now clears the doc_loc/doc_files arms
    #    directly and no longer depends on this fallback), the exact source_loc≈0 research repo
    #    that must not be missed.
    #    Framework-installed markdown is discounted here and ONLY here: bin/sync ships 22 doc
    #    files, which clears DOC_ONLY_DOC_FILES_MIN by itself, so counting them would let the
    #    installer answer the question "is this a document project?" — the mirror of the very
    #    defect the source exclusion above fixes. `.get` keeps older synthetic `files` dicts
    #    (and any caller that builds one by hand) working unchanged.
    fw_docs = files.get("framework_docs", {"count": 0, "loc": 0})
    doc_loc = files["by_category"]["docs"]["loc"] - fw_docs["loc"]
    doc_files = files["by_category"]["docs"]["count"] - fw_docs["count"]
    corpus = (
        doc_loc >= DOC_ONLY_DOC_LOC_MIN
        or doc_files >= DOC_ONLY_DOC_FILES_MIN
        or render["toolchain_present"]
    )
    return {"is_doc_only": bool(corpus), "reason": reason}


def gates_summary_html(g):
    """One line: 'none declared' | 'N declared, never run' | 'P pass / F fail / U unmeasured
    (stale)' · 'k loosened'. Advisory text only; the numbers are the ratchet's, not the scanner's."""
    if not g or not g.get("manifest_present"):
        if g and g.get("manifest_deleted"):
            return f"manifest deleted &bull; {len(g.get('loosened', []))} loosened"
        return "None"
    n = g.get("declared", 0)
    if not n:
        return "manifest seeded, none declared"
    if not g.get("results_present"):
        text = f"{n} declared, never run"
    else:
        sm = g.get("summary") or {}
        text = (f"{n} declared &bull; {sm.get('pass', 0)} pass / {sm.get('fail', 0)} fail / "
                f"{sm.get('unmeasured', 0)} unmeasured")
        if g.get("results_stale"):
            text += " (stale)"
    if g.get("loosened"):
        text += f" &bull; {len(g['loosened'])} loosened"
    return text


def fmt_ratio(value, source_loc, doc_only=False):
    """Format a *-to-source ratio for display. A bare 0.000 misreads as 'no docs', so a repo with
    ~no source shows 'n/a' — qualified '(doc-only)' only when the repo was actually classified
    doc-only, else '(no source)' for a code repo that merely happens to have no source LOC."""
    if doc_only:
        return "n/a (doc-only)"
    if source_loc == 0:
        return "n/a (no source)"
    return f"{value:.3f}"


def score_health(metrics):
    scores = {}

    # 1. Activity (0-20)
    days = metrics["git"]["days_since_last_commit"]
    if days is None:
        scores["activity"] = 0
    elif days <= 7:
        scores["activity"] = 20
    elif days <= 14:
        scores["activity"] = 16
    elif days <= 30:
        scores["activity"] = 12
    elif days <= 60:
        scores["activity"] = 6
    elif days <= 90:
        scores["activity"] = 3
    else:
        scores["activity"] = 0

    # 2. Testing (0-20) — for a doc-only repo the Render/Verification proxy fills this slot
    #    instead (the dict key stays "testing" so JSON export / portfolio aggregation / the radar
    #    keep keying on it; only the display label swaps).
    if metrics.get("doc_only", {}).get("is_doc_only"):
        scores["testing"] = metrics["render"]["score"]
    else:
        ratio = metrics["tests"]["test_to_source_ratio"]
        test_count = metrics["tests"]["test_file_count"]
        if ratio >= 0.5:
            scores["testing"] = 20
        elif ratio >= 0.3:
            scores["testing"] = 16
        elif ratio >= 0.1:
            scores["testing"] = 12
        elif test_count > 0:
            scores["testing"] = 6
        else:
            scores["testing"] = 0
        if metrics.get("coverage_configs"):
            scores["testing"] = min(20, scores["testing"] + 2)
        # No points for a gate NAMED coverage (2.11.0 gave +2): `echo 100` earned it, from a
        # results file that is gitignored by default. The plan's own condition — a faithfulness
        # check beside any coverage floor — is not expressible from a name; until it is, gate
        # outcomes are advisory risks only (PR #82 review, section 4).

    # 3. Documentation (0-20)
    doc = metrics["docs"]
    readme_pts = {"excellent": 8, "good": 6, "basic": 4, "stub": 2, "none": 0}
    doc_score = readme_pts.get(doc["readme_quality"], 0)
    if doc["has_docs_dir"]:
        doc_score += 4
    if doc["has_changelog"]:
        # Component C: split the old flat +2 into +1 for presence and +1 for freshness, so a
        # stale or never-used ledger no longer scores the same as a maintained one. Total cap
        # is unchanged (a present + fresh ledger still earns 2).
        doc_score += 1
        if metrics.get("changelog", {}).get("is_fresh"):
            doc_score += 1
    if doc["has_license"]:
        doc_score += 2
    if doc["has_roadmap"]:
        doc_score += 2
    if doc["has_todo"]:
        doc_score += 2
    scores["documentation"] = min(20, doc_score)

    # 4. CI/CD (0-20)
    ci = metrics["ci"]
    if ci["has_ci"]:
        scores["ci_cd"] = 15
        if ci["workflow_count"] >= 2:
            scores["ci_cd"] = 20
    else:
        scores["ci_cd"] = 0

    # 5. Methodology (0-20) — from the normalized percentage, and clamped. This was the one
    #    dimension of the five with no clamp, so a checklist that outgrew its 100-point scale
    #    pushed both this sub-score and the "0-100" total past their bands.
    scores["methodology"] = min(20, int(metrics["methodology"]["compliance_pct"] * 0.2))

    scores["total"] = sum(scores.values())
    return scores


def assess_risks(metrics):
    risks = []
    doc_only = metrics.get("doc_only", {}).get("is_doc_only", False)
    render = metrics.get("render", {})
    # Defaulted rather than indexed: a metrics dict built before roles existed still reads as an
    # adopter, which is what it was.
    role = metrics["methodology"].get("role", "adopter")

    days = metrics["git"]["days_since_last_commit"]
    if days is not None and days > 90:
        risks.append({"severity": "critical", "description": f"Project appears abandoned (no commits in {days} days)"})
    elif days is not None and days > 30:
        risks.append({"severity": "high", "description": f"Stale project (no commits in {days} days)"})

    # BL-5: the code-centric test risks are a false penalty on a doc-only repo (nothing to
    # unit-test); suppress them and surface render/verification advisories (proxies) instead.
    if not doc_only:
        if metrics["tests"]["test_file_count"] == 0:
            risks.append({"severity": "high", "description": "No test infrastructure"})
        elif metrics["tests"]["test_to_source_ratio"] < 0.1:
            risks.append({"severity": "medium", "description": f"Test coverage is very thin (ratio: {metrics['tests']['test_to_source_ratio']:.2f})"})
    else:
        src = metrics["tests"]["source_loc"]
        if render.get("score", 0) == 0:
            risks.append({"severity": "medium", "description": "Documentation repo has no detectable render/verification pipeline (proxy)"})
        elif render.get("toolchain_present") and not render.get("render_dep_verified"):
            risks.append({"severity": "low", "description": "Render pipeline present but no post-render dependency check (pdffonts/fc-list/kpsewhich) — v2.5 render-dep discipline not wired (anti-pattern #20)"})
        if 0 < src <= DOC_ONLY_SOURCE_LOC_MAX:
            risks.append({"severity": "low", "description": f"Doc-only repo contains {src} LOC of helper source with no tests"})

    if not metrics["ci"]["has_ci"]:
        risks.append({"severity": "medium", "description": "No CI/CD pipeline"})

    if not metrics["docs"]["has_readme"] or metrics["docs"]["readme_quality"] == "stub":
        risks.append({"severity": "medium", "description": "README is missing or insufficient"})

    # Quality gates (D6) — advisory outcomes of the ratchet; a repo with no manifest, or the
    # empty seed, says nothing here (see collect_gate_metrics).
    g = metrics.get("gates", {})
    if g.get("manifest_deleted") and not g.get("declared"):
        last = g["loosened"][0] if g.get("loosened") else None
        where = f" in {last['sha']} ({last['date']})" if last else ""
        gone = len({l["name"] for l in g.get("loosened", []) if l.get("manifest_deleted")})
        risks.append({"severity": "medium",
                      "description": f"Quality-gate manifest deleted{where} — {gone} declared gate(s) "
                                     f"gone with it; thresholds only tighten (SAFEGUARDS Blast Radius; "
                                     f"FM #17)"})
    if g.get("declared"):
        n = g["declared"]
        if not g.get("results_present"):
            risks.append({"severity": "medium",
                          "description": f"{n} declared quality gate(s), never run here "
                                         f"(`quality_ratchet.py --run`)"})  # layout: ok -- a name printed in a message, never opened
        else:
            if g.get("results_stale"):
                risks.append({"severity": "low",
                              "description": "Quality-gate results predate the current manifest — "
                                             "re-run before citing them"})
            if g.get("failing"):
                names = ", ".join(str(x) for x in g["failing"][:4])
                risks.append({"severity": "high",
                              "description": f"{len(g['failing'])} of {n} declared quality gate(s) "
                                             f"measured outside their threshold: {names}"})
            if g.get("unmeasured"):
                risks.append({"severity": "low",
                              "description": f"{len(g['unmeasured'])} declared quality gate(s) "
                                             f"unmeasured (no command) — a threshold nothing "
                                             f"measures is a suggestion"})
        if g.get("loosened"):
            last = g["loosened"][0]
            if last["kind"] == "removed":
                what = "removed (manifest deleted)" if last.get("manifest_deleted") else "removed"
            elif last["kind"] == "direction flipped":
                what = f"direction flipped {last['from']} → {last['to']}"
            else:
                what = f"{last['kind']} {last['from']:g} → {last['to']:g}"
            more = f" (+{len(g['loosened']) - 1} earlier)" if len(g["loosened"]) > 1 else ""
            risks.append({"severity": "medium",
                          "description": f"Quality threshold `{last['name']}` {what} in "
                                         f"{last['sha']} ({last['date']}){more} — thresholds only "
                                         f"tighten (SAFEGUARDS Blast Radius; FM #17)"})
        if g.get("commands_changed"):
            c = g["commands_changed"][0]
            more = f" (+{len(g['commands_changed']) - 1} more)" if len(g["commands_changed"]) > 1 else ""
            risks.append({"severity": "low",
                          "description": f"Quality gate `{c['name']}` `{c['field']}` changed in "
                                         f"{c['sha']} ({c['date']}){more} — the ratchet holds "
                                         f"thresholds, not commands; review what it now measures"})

    # Both thresholds are stated in percent, so the partial-adoption test reads the normalized
    # percentage. The "none at all" test deliberately stays on the RAW sum: it is scale-
    # independent, so a single small-weight item in a future larger checklist cannot round down
    # to 0% and false-fire "no adoption" on a project that has some.
    meth = metrics["methodology"]
    meth_raw = meth["compliance_score"]
    meth_pct = meth["compliance_pct"]
    if role == "framework":
        # The adoption wording is not merely unflattering here, it is FALSE: the checklist paths
        # are adopter-root destinations, and a repo that publishes SESSION_RUNNER.md does not
        # install a second copy into its own root. Replaced rather than suppressed — a publisher
        # with half a corpus is a real finding, and going silent would be the mirror defect.
        missing = meth.get("missing_files", [])
        if meth_raw == 0:
            # Reachable precisely because the two files that prove the role are unscored.
            risks.append({"severity": "high",
                          "description": f"No framework corpus detected (0 of "
                                         f"{meth.get('checklist_max', FRAMEWORK_MAX)} framework "
                                         f"integrity)"})
        elif missing:
            # The percentage alone is not the finding: losing both root ledgers still scores in
            # the eighties, so a pct-only rung would say nothing about it. The member names are
            # what a reader can act on; the severity only ranks them.
            risks.append({"severity": "medium" if meth_pct < 50 else "low",
                          "description": f"Framework integrity incomplete ({meth_pct}%) — "
                                         f"missing: {', '.join(missing)}"})
    elif meth_raw == 0:
        risks.append({"severity": "high", "description": "No methodology adoption (0% compliance)"})
    elif meth_pct < 50:
        risks.append({"severity": "medium", "description": f"Partial methodology adoption ({meth_pct}%)"})

    # A profile marker that declares both tokens of one axis is a declaration this scanner could
    # not read. Disclosed once, however many axes conflict — decision D4 applied to the marker:
    # abstention is a first-class result and is never silent.
    if "marker-contradiction" in (meth.get("role_reason"),
                                  metrics.get("doc_only", {}).get("reason")):
        risks.append({"severity": "low",
                      "description": f"{PROFILE_MARKER} declares conflicting tokens; that axis "
                                     f"fell through to the heuristic"})

    if not metrics["docs"]["has_license"]:
        risks.append({"severity": "low", "description": "No LICENSE file"})

    # BL-5: only a large *source* file is a code-smell; a 2500-line chapter (.md/.tex) is normal for
    # a document repo. Scan for the largest *source* file over the threshold rather than inspecting
    # only largest[0], so a non-source #1 (e.g. a big lockfile/JSON) doesn't mask a real large source
    # file below it (helps mixed repos too — no doc_only branch needed).
    # Layer 7: and never a file WE installed. "Large files detected (methodology_dashboard.py:
    # 2,475 lines)" was firing on 4 of 10 real repos — the same defect class as the source-LOC
    # miscount, one signal over: we put our scanner in their repo, then flagged it as their
    # problem. The canonical repo still pays for the copies it authors (tools/, starter-kit/),
    # which are not root dests and so are never vendor.
    big_src = next((f for f in metrics["files"]["largest_files"]
                    if f["loc"] > 2000 and f.get("ext") in SOURCE_EXTS
                    and not f.get("vendor")), None)
    if big_src:
        risks.append({"severity": "medium", "description": f"Large files detected ({big_src['path']}: {big_src['loc']:,} lines)"})

    commits = metrics["git"]["total_commits"]
    age = metrics["git"]["project_age_days"]
    if commits < 10 and age > 30:
        risks.append({"severity": "medium", "description": f"Very low commit velocity ({commits} commits in {age} days)"})

    if metrics["git"]["branch_count"] > 5:
        risks.append({"severity": "low", "description": f"Multiple branches ({metrics['git']['branch_count']}) may indicate incomplete merges"})

    # Vulnerability risks
    vulns = metrics.get("vulnerabilities", {})
    if vulns.get("scanned"):
        crit = sum(v["count"] for v in vulns.get("vulnerabilities", []) if v["severity"] == "critical")
        high = sum(v["count"] for v in vulns.get("vulnerabilities", []) if v["severity"] == "high")
        if crit > 0:
            risks.append({"severity": "critical", "description": f"{crit} critical dependency vulnerabilit{'y' if crit == 1 else 'ies'}"})
        if high > 0:
            risks.append({"severity": "high", "description": f"{high} high-severity dependency vulnerabilit{'y' if high == 1 else 'ies'}"})

    # Component C: CHANGELOG ledger freshness (advisory). Decision D3 — a methodology adopter
    # (SESSION_RUNNER.md present) with real commit history but no ledger is a defect, not a
    # silent absence. For projects that keep a ledger, surface the ledger-lag signals.
    #
    # This is the one RISK that asks about membership, and therefore the only consumer of
    # `ledger_present` (root CHANGELOG.md, exactly) rather than `present` (any located changelog).
    # Reading `present` here is what let a `docs/` product changelog answer for a missing ledger.
    # The compliance checklist asks the same membership question independently and scores it; the
    # two agreeing is the point of _find_action_ledger, not a duplication to collapse.
    #
    # The gate is an explicit PREDICATE, not a probe of a checklist key. Reading
    # items["SESSION_RUNNER.md"] worked only while one checklist existed: under FRAMEWORK_ITEMS
    # that key is absent, so .get would return False forever and this risk would go unreachable
    # for every framework repo — silently, with no test failing. That is the same
    # unreachable-signal defect this campaign was opened to close, and it would have landed on
    # the one repo that dogfoods the ledger rule it publishes.
    lay = metrics["methodology"].get("layout") or {}
    if lay.get("kind") == "half":
        # Never guess which copy is live: the tools refuse a half-migrated tree and name both (plan 4.3).
        risks.append({"severity": "high",
                      "description": "Half-migrated methodology layout: " + " and ".join(lay["found"])
                                     + " both exist and nothing says which is live, so the tools refuse "
                                       "to guess (BL-101). Move or remove one copy"})
    cl = metrics.get("changelog", {})
    owes_ledger = (metrics["methodology"]["items"].get("SESSION_RUNNER.md", False)  # layout: ok -- the checklist key of the runner; its location was resolved when the item was probed
                   or role == "framework")
    if not cl.get("ledger_present") and owes_ledger and metrics["git"]["total_commits"] >= LEDGER_REAL_HISTORY_MIN:
        # The finding is identical; only the noun changes. Calling a publisher an "adopter" would
        # be the same category error this layer exists to remove from the score above.
        who = "Methodology framework repo" if role == "framework" else "Methodology adopter"
        # Named where the ledger would live: a project that moved its state files keeps it under methodology/.
        ledger = (metrics["methodology"].get("layout") or {}).get("ledger", "CHANGELOG.md")  # layout: ok -- the ledger's legacy path, the default project_layout reports and an older metrics dict lacks
        lead = "root CHANGELOG.md" if ledger == "CHANGELOG.md" else ledger  # layout: ok -- the ledger's legacy path: a root ledger is named as such, a moved one by its path
        risks.append({"severity": "medium",
                      "description": f"{who} has commit history but no {lead} action ledger (Component C)"})
    for sev, desc in cl.get("signals", []):
        risks.append({"severity": sev, "description": desc})

    # D4(b) — silent truncation, not a code smell. A second risk on purpose: it shares only the
    # adjective with "Large files detected" above, and shares no substring with it, so the two stay
    # independently greppable in dashboard_history.jsonl and the diagnostic trail that produced
    # BL-5's and Layer 7's narrowings survives intact.
    #
    # Gated on `owes_ledger` (bound above), which is ADDED POLICY and the reason it is here rather
    # than beside the BL-5 check: a project that never adopted the methodology is not told its
    # CHANGELOG.md is too long. Ungated, this fires on any repo that happens to keep a long
    # changelog — the assumption whose measured cost is recorded in FRAMEWORK_INSTALLED_SOURCE's
    # own comment. Severity is `high` (also added policy) because this is the only expense in the
    # set that produces silently WRONG answers rather than merely expensive ones. This row names no
    # remedy, and BOTH halves of the reason it used to give have since expired: the conditional
    # naming it deferred to queue item S38 shipped in 2.12.0 (collect_trim_metrics), and the
    # trimmer it called unreachable is in bin/_manifest.py as of S39'. What keeps the row bare is
    # now a scope boundary rather than a missing tool — the remedy is emitted by the trim row,
    # which owns the conditional wording and the abstentions; duplicating it here would give a
    # ledger past both thresholds two remedies for one problem. The dedup between the two rows is
    # raised and undecided (S38's residual 1), so this comment states the coupling rather than
    # pretending the rows are independent. ONE EXCEPTION since BL-88 P2: a Class B file whose
    # project's own trimmer declares it gets its remedy HERE, because the trim row's population
    # is Class A and never reaches that file -- still one remedy per problem, not two.
    if owes_ledger:
        for w in metrics["files"]["read_cap_watch"]:
            wb = w.get("bytes")
            if wb is None:
                continue
            if wb > READ_REFUSE_BYTES:
                # A DIFFERENT failure from truncation, not a worse degree of it, and it gets its
                # own row text for that reason. The consolation that makes truncation survivable
                # -- delivery is ordered top-down, so the front matter and the newest records
                # still arrive -- is FALSE here. Nothing arrives.
                risks.append({
                    "severity": "high",
                    "description": f"{w['path']} is {wb:,} B ({w['lines']:,} lines) — past the "
                                   f"{READ_REFUSE_BYTES:,} B hard limit, which is a HARDER "
                                   "boundary than the agent read cap and behaves differently: a "
                                   "default read is REFUSED OUTRIGHT and returns NO CONTENT AT "
                                   "ALL, front matter included. Ordered truncation does not save "
                                   "you here — there is no delivered prefix to be ordered. Read "
                                   "it with explicit offset/limit, or archive it"})
            elif wb > READ_CAP_BYTES:
                # PHASE C2 — THIS ROW IS NOW PER-CLASS, WHICH IS HOW THE DEDUP ENDS.
                # S38's residual 1 asked whether this row and the trim row should be deduplicated.
                # The answer plan §7 gives for option A1 is "make the rows DIFFERENT, not delete
                # one", and this is where that lands. Both rows still fire on a Class B file,
                # because for those two thresholds still coincide. On a Class A file they now
                # separate: the trim row is silent until 192 KiB, and this row keeps reporting the
                # one-read property — which is REAL and stays true — at a severity that says what
                # the reader should DO about it, which is nothing.
                #
                # ⚠ THE SEVERITY DROP IS THE FLEET-VISIBLE PART OF THIS PHASE, and it is a
                # judgment, not a derivation. §10 dragon 7: a guard can be correct and not worth
                # acting on. A Class A ledger between the cap and the archive threshold is the
                # adjudicated case (BL-52 third addendum) — ordered truncation drops the OLDEST
                # records, Phase 0 works from `git log`, and Phase 3A reads one receipt. Calling
                # that HIGH taught a reader to ignore the row, which is worse than not emitting it.
                # It is not dropped to "info" either: the property is real and a session that
                # genuinely needs the whole file still gets a partial answer.
                cls = read_cap_class(w.get("name", w["path"]))
                if cls == "A":
                    risks.append({
                        "severity": "low",
                        "description": f"{w['path']} is {wb:,} B ({w['lines']:,} lines) — past "
                                       f"the {READ_CAP_BYTES:,} B one-read budget for the agent "
                                       f"read cap, but this is a CLASS A ledger and that is "
                                       "expected rather than a fault. Delivery is an ordered "
                                       "prefix and the file is newest-on-top, so what a "
                                       "whole-file read drops is the OLDEST records; the front "
                                       "matter and the newest ones still arrive, which is what "
                                       "the protocol reads (Phase 0 reconciles from `git log`, "
                                       "Phase 3A reads ONE record). NO ACTION IS EXPECTED here: "
                                       f"the archive threshold for this class is {CLASS_A_FIRE_BYTES:,} B, "
                                       f"{CLASS_A_FIRE_BYTES - wb:,} B away. If you need the "
                                       "whole file, read it with an explicit offset/limit"})
                else:
                    # BL-88 — THIS ROW MAY ASSERT ONLY WHAT THIS MODULE EVALUATED. It used to print
                    # "the trimmer answers NO_CONFIG for it": a fact about a NEIGHBOURING TOOL's
                    # config table, read from nothing. That was true here only because LEDGERS and
                    # the declared classes coincide -- which a canonical test pins -- and FALSE in
                    # any tree that widened LEDGERS. This module is DISTRIBUTED to exactly such
                    # trees while its suite is not (absent from bin/_manifest.py), so the claim was
                    # being evaluated where nothing could check it: one adopter's trimmer gained a
                    # SESSION_NOTES.md spec and this row went on denying it. The class stays
                    # DECLARED (READ_CAP_CLASS_A/B above, and section 10 dragon 6 with it); only the
                    # prose stops speaking for the trimmer.
                    #
                    # AND THE REASON IS NOW PER-NAME. The comment above READ_CAP_CLASS_B already
                    # records that carrying the backlog justification to every Class B name is
                    # FALSE of SESSION_NOTES.md, and states the true weaker form -- but that
                    # correction reached the comment and never reached this row, so the row
                    # contradicted its own module. Measured across 12 fleet repos: every
                    # SESSION_NOTES.md with an `## ACTIVE TASK` heading has it at byte 132-9,490,
                    # inside READ_CAP_BYTES in all of them; one repo has no such heading at all,
                    # which is the case the weaker form exists for.
                    #
                    # P2 — AND WHERE IT HAS EVALUATED SOMETHING, IT MAY SAY SO. collect_trim_metrics
                    # reads the scanned project's own trimmer SOURCE (_parse_trim_ledgers: a parse,
                    # never an execution -- the operator's decision). Where that reading lists this
                    # file's BASENAME -- the key the trimmer itself looks up,
                    # `LEDGERS.get(path.name)` at any depth -- the conjunct that sets Class B apart
                    # from A, NO REMEDY the reader can reach, is checked false FOR THIS PROJECT, so
                    # the row appends the remedy and takes Class A's severity. Anything else -- no
                    # trimmer, a reading that abstained, a name it does not list, a metrics dict
                    # from an older copy -- leaves P1's row byte for byte, and a canonical test pins
                    # that against P1's output frozen as a literal: the failure path is the
                    # criterion. The CLASS does not move (dragon 6): read_cap_class() and both sets
                    # are untouched and the trim row's population stays Class A even here -- prose
                    # and severity consult a reading; membership does not.
                    if w.get("name", w["path"]) in _BACKLOG_LOCATIONS:
                        why = ("a backlog's bottom items are as live as its top ones, so what "
                               "truncates may be open work")
                    else:
                        why = ("nothing ENFORCES that the part you need is inside that prefix — "
                               "the protocol says to focus on the ACTIVE TASK section at the top "
                               "and the seed puts it there, but no check holds it there, and a "
                               "file carrying no such heading has no ordering to rely on")
                    desc = (f"{w['path']} is {wb:,} B ({w['lines']:,} lines) — past the "
                            f"{READ_CAP_BYTES:,} B one-read budget for the agent read cap, "
                            f"which is denominated in tokens ({READ_CAP_TOKENS:,}) and "
                            f"converted here at the densest content measured "
                            f"({MIN_BYTES_PER_TOKEN} B/token). A session reading it whole "
                            "gets a PARTIAL view — truncated to the prefix that fits the "
                            "token cap, and it SAYS SO in a banner naming the true "
                            "length, so the failure is loud rather than silent; an "
                            "explicit line range spanning the excess errors outright, "
                            "returning nothing. This is a CLASS B file and the "
                            f"instructed access path IS the file: {why}, and you are "
                            "told THAT something was cut, never WHAT")
                    trim = metrics.get("trim", {})
                    tool = trim.get("tool_path")
                    base = w["path"].rsplit("/", 1)[-1]
                    if (trim.get("tool_present") and tool
                            and base in (trim.get("tool_ledgers") or ())):
                        risks.append({
                            "severity": "low",
                            "description": desc + (
                                f". BUT THIS PROJECT HAS A REMEDY: its own `{tool}` declares a "
                                f"`LEDGERS` entry for `{base}` (read from its source, never "
                                f"run), so run `python3 {tool} --file {w['path']} --check` for "
                                "the full report and whether a trim is the right move")})
                    else:
                        risks.append({"severity": "high", "description": desc})

    # S38: the trim-trigger rows, re-emitted VERBATIM from the collector -- the same arrangement
    # the Component C signals above use. The collector owns the gate, the population and the
    # conditional remedy wording; nothing is re-decided here, so there is one place to read to
    # know what an operator was told. Absent key tolerated: a metrics dict built by an older
    # copy of this module has no "trim" entry, and that is not a finding.
    for sev, desc in metrics.get("trim", {}).get("signals", []):
        risks.append({"severity": sev, "description": desc})

    # Sort by severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    risks.sort(key=lambda r: severity_order.get(r["severity"], 99))

    return risks


def classify_activity(metrics):
    days = metrics["git"]["days_since_last_commit"]
    if days is None:
        return "dead"
    if days <= 14:
        return "active"
    if days <= 30:
        return "slowing"
    if days <= 90:
        return "stale"
    return "dead"


def worst_risk(risks):
    if not risks:
        return "healthy"
    return risks[0]["severity"]


def aggregate_portfolio(projects):
    if not projects:
        return {"health_score": 0, "project_count": 0, "total_commits": 0,
                "risk_counts": {}, "active_count": 0}

    health_scores = [p["scores"]["health"]["total"] for p in projects]
    total_commits = sum(p["git"]["total_commits"] for p in projects)
    risk_counts = defaultdict(int)
    for p in projects:
        wr = worst_risk(p["scores"]["risks"])
        risk_counts[wr] += 1

    activity_counts = defaultdict(int)
    for p in projects:
        activity_counts[p["scores"]["activity"]] += 1

    return {
        "health_score": round(sum(health_scores) / len(health_scores)),
        "project_count": len(projects),
        "total_commits": total_commits,
        "risk_counts": dict(risk_counts),
        "activity_counts": dict(activity_counts),
    }


# === COLLECT ALL ===

def collect_all(path):
    name = path.name
    git = collect_git_metrics(path)
    files = collect_file_metrics(path)
    tests = collect_test_metrics(files)
    ci = collect_ci_metrics(path)
    docs = collect_doc_metrics(path, files)
    # The role decides WHICH checklist collect_methodology_metrics scores, so it is resolved
    # first. It needs only the path (a marker read plus three existence probes), so unlike
    # doc-only detection it has no dependency on the collected metrics.
    role_info = detect_repo_role(path)
    meth = collect_methodology_metrics(path, role=role_info["role"])
    meth["role_reason"] = role_info["reason"]
    deps = collect_dependency_metrics(path)
    cov = collect_coverage_config(path)

    github = collect_github_metrics(path)
    vulns = collect_vulnerability_metrics(path)

    metrics = {
        "name": name,
        "path": str(path),
        "git": git,
        "files": files,
        "tests": tests,
        "ci": ci,
        "docs": docs,
        "methodology": meth,
        "dependencies": deps,
        "coverage_configs": cov,
        "github": github,
        "vulnerabilities": vulns,
    }

    # Component C: ledger freshness. Wired after the metrics dict is built (so it can read the
    # already-collected git metrics) and before the scores block (which consumes is_fresh).
    metrics["changelog"] = evaluate_changelog_freshness(path, git)

    # BL-5: render/verification signals + doc-only classification. Wired after the metrics dict is
    # built (so collect_render_metrics can read the collected ci/files) and before the scores block
    # (which consumes doc_only + render). Order matters: render feeds detect_doc_only.
    metrics["render"] = collect_render_metrics(path, files, ci, meth)
    metrics["doc_only"] = detect_doc_only(path, files, metrics["render"])
    # Quality gates (D6): declared thresholds, last measured outcomes, git-only loosening history.
    metrics["gates"] = collect_gate_metrics(path)

    # S38: the trim-trigger row. Wired after the metrics dict is built (it reads the collected
    # read_cap_watch line counts) and before the scores block, which re-emits its signals.
    metrics["trim"] = collect_trim_metrics(path, files, role=role_info["role"])

    metrics["scores"] = {
        "health": score_health(metrics),
        "risks": assess_risks(metrics),
        "activity": classify_activity(metrics),
    }

    return metrics


# === HTML GENERATION ===

SEVERITY_COLORS = {
    "critical": "#ff4444",
    "high": "#ff8800",
    "medium": "#ffcc00",
    "low": "#44aaff",
    "healthy": "#44ff88",
}

ACTIVITY_COLORS = {
    "active": "#44ff88",
    "slowing": "#ffcc00",
    "stale": "#ff8800",
    "dead": "#ff4444",
}


def health_color(score):
    if score >= 80:
        return "#44ff88"
    if score >= 60:
        return "#88cc44"
    if score >= 40:
        return "#ffcc00"
    if score >= 20:
        return "#ff8800"
    return "#ff4444"


def esc(text):
    """HTML-escape."""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def render_risk_matrix(projects):
    buckets = {"critical": [], "high": [], "medium": [], "low": [], "healthy": []}
    for p in projects:
        wr = worst_risk(p["scores"]["risks"])
        buckets[wr].append(p["name"])

    cells = ""
    for level in ["critical", "high", "medium", "low", "healthy"]:
        color = SEVERITY_COLORS[level]
        names = buckets[level]
        items = "".join(f'<div class="risk-item">{esc(n)}</div>' for n in names) if names else '<div class="risk-empty">--</div>'
        cells += f'''<div class="risk-cell" style="border-top: 3px solid {color}">
            <div class="risk-label" style="color: {color}">{level.upper()}</div>
            {items}
        </div>'''
    return f'<div class="risk-matrix">{cells}</div>'


def methodology_item_label(item_path, kind):
    """Human column label for a checklist item, derived from its path:
    'SESSION_RUNNER.md' -> 'Session Runner', 'docs/methodology' -> 'Methodology Dir'."""
    tail = item_path.rstrip("/").split("/")[-1]
    if tail.lower().endswith(".md"):
        tail = tail[:-3]
    label = tail.replace("_", " ").replace("-", " ").title()
    return f"{label} Dir" if kind == "dir" else label


def methodology_grid_headers():
    """The grid's full header row: Project + one column per checklist item + Score.

    Derived rather than hand-written because the cells below already derive from
    METHODOLOGY_ITEMS: a hand-maintained header list silently falls one column short of the
    data every time the checklist grows (which is how the two items appended in v2.1 left every
    project row running two cells wider than its headers)."""
    return (["Project"]
            + [methodology_item_label(p, kind) for p, _weight, kind in METHODOLOGY_ITEMS]
            + ["Score"])


def render_methodology_grid(projects):
    headers = methodology_grid_headers()
    item_keys = [item[0] for item in METHODOLOGY_ITEMS]

    rows = ""
    any_framework = False
    for p in projects:
        items = p["methodology"]["items"]
        cells = f'<td class="proj-name">{esc(p["name"])}</td>'
        # A framework repo was scored against a DIFFERENT checklist, and the two overlap only at
        # CHANGELOG.md and HANDOFFS.md — the two artifacts both a publisher and an adopter owe.
        # Rendering it against these columns does not break the table: it produces a correctly
        # aligned row of two ticks beside seven crosses, under headers naming files the repo was
        # never scored on. That is worse than a broken row and worse than an all-red one — it is
        # aligned AND partly true, so nothing looks wrong. A third glyph says "not applicable"
        # instead of asserting failure; the per-item finding lives on the project card, which
        # shows the checklist that actually ran.
        if p["methodology"].get("role") == "framework":
            any_framework = True
            cells += (f'<td class="meth-na" colspan="{len(item_keys)}" '
                      f'style="opacity:0.55">&mdash; framework checklist &mdash;</td>')
        else:
            for key in item_keys:
                present = items.get(key, False)
                if present:
                    cells += '<td class="meth-yes">&#10003;</td>'
                else:
                    cells += '<td class="meth-no">&#10007;</td>'
        # The colour ladder is stated in percent, so it reads the normalized percentage — on the
        # raw 0-115 sum its 80/40 rungs sat at the wrong places and the cell rendered ">100%".
        pct = p["methodology"]["compliance_pct"]
        score_color = "#44ff88" if pct >= 80 else "#ffcc00" if pct >= 40 else "#ff4444"
        dagger = "&#8224;" if p["methodology"].get("role") == "framework" else ""
        cells += f'<td style="color: {score_color}; font-weight: bold">{pct}%{dagger}</td>'
        rows += f"<tr>{cells}</tr>"

    header_row = "".join(f"<th>{h}</th>" for h in headers)
    legend = ""
    if any_framework:
        # "do not apply" would be the same kind of overstatement this campaign exists to remove:
        # two of these columns (CHANGELOG.md, HANDOFFS.md) ARE on the framework checklist too.
        legend = ('<div class="meth-legend" style="font-size:0.8em;opacity:0.7;margin-top:6px">'
                  '&#8224; framework repo &mdash; scored against the framework checklist, not '
                  'these columns. The two overlap only at CHANGELOG.md and HANDOFFS.md. See the '  # layout: ok -- a name printed in a message, never opened
                  'project card for the checklist that ran.</div>')
    return f'''<table class="meth-table">
        <thead><tr>{header_row}</tr></thead>
        <tbody>{rows}</tbody>
    </table>{legend}'''


def render_activity_bars(projects):
    max_v = max((p["git"]["commit_velocity_30d"] for p in projects), default=1) or 1
    bars = ""
    for p in projects:
        v30 = p["git"]["commit_velocity_30d"]
        v7 = p["git"]["commit_velocity_7d"]
        pct = int((v30 / max_v) * 100)
        color = ACTIVITY_COLORS[p["scores"]["activity"]]
        bars += f'''<div class="activity-row">
            <span class="activity-name">{esc(p["name"])}</span>
            <div class="activity-bar-bg">
                <div class="activity-bar" style="width: {pct}%; background: {color}"></div>
            </div>
            <span class="activity-nums">{v7}/7d &nbsp; {v30}/30d</span>
        </div>'''
    return f'<div class="activity-section">{bars}</div>'


def render_language_breakdown(by_lang):
    if not by_lang:
        return "<em>No source files detected</em>"
    sorted_langs = sorted(by_lang.items(), key=lambda x: x[1]["loc"], reverse=True)
    rows = ""
    for lang, data in sorted_langs[:10]:
        rows += f'<tr><td>{esc(lang)}</td><td class="num">{data["count"]:,}</td><td class="num">{data["loc"]:,}</td></tr>'
    return f'''<table class="detail-table">
        <thead><tr><th>Language</th><th>Files</th><th>LOC</th></tr></thead>
        <tbody>{rows}</tbody>
    </table>'''


def render_largest_files(files):
    if not files:
        return ""
    rows = ""
    for f in files:
        rows += f'<tr><td class="file-path">{esc(f["path"])}</td><td class="num">{f["loc"]:,}</td></tr>'
    return f'''<table class="detail-table">
        <thead><tr><th>File</th><th>LOC</th></tr></thead>
        <tbody>{rows}</tbody>
    </table>'''


def render_project_card(p):
    health = p["scores"]["health"]
    risks = p["scores"]["risks"]
    activity = p["scores"]["activity"]
    wr = worst_risk(risks)
    h_color = health_color(health["total"])
    a_color = ACTIVITY_COLORS[activity]
    r_color = SEVERITY_COLORS[wr]

    # Risk list
    risk_html = ""
    if risks:
        for r in risks:
            rc = SEVERITY_COLORS[r["severity"]]
            risk_html += f'<div class="risk-flag"><span class="risk-badge" style="background: {rc}">{r["severity"].upper()}</span> {esc(r["description"])}</div>'
    else:
        risk_html = '<div class="risk-flag" style="color: #44ff88">No risks identified</div>'

    # Methodology / framework checklist. The heading shows the normalized percentage with the raw
    # weighted sum kept inspectable beside it, so a reader can still see what the checklist
    # actually totalled without the "%" ever exceeding 100.
    #
    # The denominator is read from the project, not from the module global: a framework repo
    # scoring 105 of 105 rendered against METHODOLOGY_MAX would print the literal arithmetic
    # falsehood "100% (105 of 115)".
    meth = p["methodology"]
    meth_role = meth.get("role", "adopter")
    meth_max = meth.get("checklist_max", METHODOLOGY_MAX)
    meth_title = "Framework Integrity" if meth_role == "framework" else "Methodology Compliance"
    meth_compliance = f'{meth["compliance_pct"]}% ({meth["compliance_score"]} of {meth_max})'
    # Iterate the items that were SCORED rather than the adopter checklist, so every glyph on the
    # card names something the percentage above it actually counted.
    meth_items = ""
    for item_path, present in meth["items"].items():
        icon = "&#10003;" if present else "&#10007;"
        cls = "meth-yes" if present else "meth-no"
        meth_items += f'<span class="{cls}">{icon} {esc(item_path)}</span> '
    # Residual risk 8, stated on the card instead of only in the plan: this score is .exists()
    # and cannot tell a maintained artifact from an abandoned one. True of both checklists.
    meth_note = ('<div class="kv" style="font-size:0.8em;opacity:0.7;margin-top:6px">'
                 'presence check &mdash; the scanner does not verify these files are used')
    if meth_role == "framework":
        reason = meth.get("role_reason", "structural")
        provenance = {
            "marker": f"{PROFILE_MARKER} marker override",
            "marker-contradiction": (f"{PROFILE_MARKER} declared conflicting role tokens; "
                                     f"classified structurally"),
        }.get(reason, "structural: bin/_manifest.py + starter-kit/SESSION_RUNNER.md, "
                     "no root SESSION_RUNNER.md")  # layout: ok -- a name printed in a message, never opened
        # Never print the role silently: the marker is a one-word grading opt-out, so how this
        # repo came to be graded as a publisher has to be visible to whoever reads the score.
        meth_note += f'<br>role: framework &mdash; {esc(provenance)}'
    meth_note += '</div>'

    # CI info
    ci = p["ci"]
    if ci["has_ci"]:
        ci_html = f'{esc(ci["ci_platform"])} ({ci["workflow_count"]} workflow{"s" if ci["workflow_count"] != 1 else ""})'
    else:
        ci_html = '<span class="meth-no">None</span>'

    # Docs inventory
    doc = p["docs"]
    doc_items = []
    if doc["has_readme"]:
        doc_items.append(f'README ({doc["readme_loc"]:,}L, {doc["readme_quality"]})')
    if doc["has_docs_dir"]:
        doc_items.append(f'docs/ ({doc["doc_file_count"]} files)')
    if doc["has_changelog"]:
        doc_items.append("CHANGELOG")
    if doc["has_license"]:
        doc_items.append("LICENSE")
    if doc["has_roadmap"]:
        doc_items.append("ROADMAP")
    if doc["has_todo"]:
        doc_items.append("TODO")
    doc_html = ", ".join(doc_items) if doc_items else '<span class="meth-no">None</span>'

    # Coverage configs
    cov_html = ", ".join(p["coverage_configs"]) if p["coverage_configs"] else "None"

    # Quality gates (D6): declared · measured · loosened. Rendered for code repos beside the
    # coverage config; a doc-only card keeps its render proxy section.
    gates_html = gates_summary_html(p.get("gates", {}))

    # Dependencies
    dep_html = ""
    if p["dependencies"]["dependency_files"]:
        for df in p["dependencies"]["dependency_files"]:
            detail = f' ({df["detail"]})' if "detail" in df else ""
            dep_html += f'{esc(df["file"])}: {df["count"]}{detail}<br>'
    else:
        dep_html = "No dependency files detected"

    # Vulnerabilities
    vulns = p.get("vulnerabilities", {})
    if vulns.get("scanned") and vulns.get("vulnerabilities"):
        vuln_html = ""
        for v in vulns["vulnerabilities"]:
            vc = SEVERITY_COLORS.get(v["severity"], "#aaa")
            vuln_html += f'<span class="risk-badge" style="background: {vc}">{v["severity"].upper()}: {v["count"]}</span> '
        vuln_html = f'<div class="kv">{vuln_html} ({vulns["total_vulns"]} total)</div>'
    elif vulns.get("scanned"):
        vuln_html = '<div class="kv" style="color: #44ff88">No vulnerabilities found</div>'
    else:
        vuln_html = '<div class="kv" style="color: #888">Not scanned</div>'

    # GitHub
    gh = p.get("github", {})
    if gh.get("repo_slug"):
        gh_parts = []
        if gh.get("open_issues") is not None:
            gh_parts.append(f'Issues: <b>{gh["open_issues"]}</b>')
        if gh.get("open_prs") is not None:
            gh_parts.append(f'Open PRs: <b>{gh["open_prs"]}</b>')
        gh_html = " &bull; ".join(gh_parts) if gh_parts else "Connected"
        gh_html = f'<div class="kv">{gh_html} &bull; <a href="https://github.com/{esc(gh["repo_slug"])}" style="color: #44aaff">{esc(gh["repo_slug"])}</a></div>'
    else:
        gh_html = '<div class="kv" style="color: #888">No GitHub remote</div>'

    # Git info
    git = p["git"]
    days = git["days_since_last_commit"]
    days_str = f"{days}d ago" if days is not None else "never"

    # Recent commits
    commits_html = ""
    for c in git["recent_commits"]:
        commits_html += f'<div class="commit-line"><code>{c["hash"]}</code> <span class="commit-date">{c["date"]}</span> {esc(c["message"])}</div>'

    # Health dimension bars. BL-5: a doc-only repo's 2nd slot holds Render/Verification, not Testing.
    doc_only_info = p.get("doc_only", {})
    is_doc_only = doc_only_info.get("is_doc_only", False)
    render = p.get("render", {})
    src_loc = p["tests"]["source_loc"]
    # Layer 7: framework-installed files are held out of Source, so the file-type table shows the
    # excluded LOC on its own row. The row is emitted only when something was actually excluded —
    # a permanent "Framework 0 / 0" would be noise on the repos that never ran bin/sync.
    vendor = p["files"]["by_category"].get("vendor", {"count": 0, "loc": 0})
    vendor_row = (
        f'<tr><td>Framework (installed)</td><td class="num">{vendor["count"]:,}</td>'
        f'<td class="num">{vendor["loc"]:,}</td></tr>' if vendor["count"] else "")
    # Same disclosure in the Testing section, where "Source LOC: 0" on a repo that visibly
    # contains a multi-thousand-line file would otherwise read as a scanner error.
    vendor_note = (
        f'<div class="kv" style="font-size:0.8em;opacity:0.7">'
        f'(excludes {vendor["loc"]:,} LOC of framework-installed files)</div>'
        if vendor["count"] else "")
    dims = ["activity", "testing", "documentation", "ci_cd", "methodology"]
    # Slot 5 swaps label the same way slot 2 already does for a doc-only repo: the dict key stays
    # "methodology" for JSON export / portfolio aggregation / the radar, and only the display
    # label follows the checklist that ran.
    dim_labels = ["Activity", "Render/Verify" if is_doc_only else "Testing",
                  "Documentation", "CI/CD",
                  "Framework" if meth_role == "framework" else "Methodology"]
    dim_bars = ""
    for dim, label in zip(dims, dim_labels):
        val = health[dim]
        pct = int((val / 20) * 100)
        c = health_color(val * 5)
        dim_bars += f'''<div class="dim-row">
            <span class="dim-label">{label}</span>
            <div class="dim-bar-bg"><div class="dim-bar" style="width: {pct}%; background: {c}"></div></div>
            <span class="dim-val">{val}/20</span>
        </div>'''
    dim_footnote = ""
    if is_doc_only:
        reason = doc_only_info.get("reason", "heuristic")
        # The source_loc <= cap justification holds only on the heuristic path; a marker override
        # can force doc-only at any source size, so don't print a (possibly false) inequality there.
        detail = ("marker override" if reason == "marker"
                  else f"heuristic, source_loc {src_loc} &le; {DOC_ONLY_SOURCE_LOC_MAX}")
        dim_footnote = (
            '<div class="dim-footnote" style="font-size:0.8em;opacity:0.7;margin-top:4px">'
            'Render/Verify is an infrastructure proxy — the scanner cannot execute a render; '
            f'doc-only repo detected ({esc(detail)}).</div>')

    # Testing / Render-Verification card section (swap the whole block for a doc-only repo).
    if is_doc_only:
        sig_rows = "".join(
            f'<div class="kv">{"&#10003;" if ok else "&#10007;"} {esc(name)}</div>'
            for name, ok in render.get("signals", []))
        testing_section = f'''<div class="card-section">
                        <h4>Render / Verification (proxy)</h4>
                        {sig_rows}
                        <div class="kv">Render/Verify: <b>{render.get("score", 0)}/20</b></div>
                        <div class="kv" style="font-size:0.8em;opacity:0.7">(configuration proxy — scanner cannot execute a render)</div>
                    </div>'''
        doc_ratio_kv = f'Doc LOC: <b>{doc["doc_total_loc"]:,}</b>'
    else:
        testing_section = f'''<div class="card-section">
                        <h4>Testing</h4>
                        <div class="kv">Test Files: <b>{p["tests"]["test_file_count"]}</b></div>
                        <div class="kv">Test LOC: <b>{p["tests"]["test_loc"]:,}</b></div>
                        <div class="kv">Source LOC: <b>{p["tests"]["source_loc"]:,}</b></div>
                        {vendor_note}
                        <div class="kv">Test:Source Ratio: <b>{fmt_ratio(p["tests"]["test_to_source_ratio"], src_loc)}</b></div>
                        <div class="kv">Coverage Config: <b>{cov_html}</b></div>
                        <div class="kv">Quality Gates: <b>{gates_html}</b></div>
                    </div>'''
        doc_ratio_kv = f'Doc:Source Ratio: <b>{fmt_ratio(doc["doc_to_source_ratio"], src_loc)}</b>'

    return f'''
    <div class="project-card" id="card-{esc(p["name"])}">
        <div class="card-header" onclick="toggleCard(this)">
            <div class="card-title">
                <span class="card-name">{esc(p["name"])}</span>
                <span class="card-health" style="color: {h_color}">Health: {health["total"]}/100</span>
                <span class="card-risk" style="color: {r_color}">Risk: {wr.upper()}</span>
                <span class="card-activity" style="color: {a_color}">{activity.upper()}</span>
            </div>
            <div class="card-summary">
                {git["total_commits"]:,} commits &bull;
                {p["files"]["total_files"]:,} files &bull;
                {p["files"]["total_loc"]:,} LOC &bull;
                Last: {days_str} &bull;
                {git["contributor_count"]} contributor{"s" if git["contributor_count"] != 1 else ""}
            </div>
        </div>
        <div class="card-body">
            <div class="card-section">
                <h4>Health Breakdown</h4>
                {dim_bars}
                {dim_footnote}
            </div>

            <div class="card-section">
                <h4>Risk Factors</h4>
                {risk_html}
            </div>

            <div class="card-columns">
                <div class="card-col">
                    <div class="card-section">
                        <h4>Git</h4>
                        <div class="kv">Total Commits: <b>{git["total_commits"]:,}</b></div>
                        <div class="kv">Velocity (7d): <b>{git["commit_velocity_7d"]}</b></div>
                        <div class="kv">Velocity (30d): <b>{git["commit_velocity_30d"]}</b></div>
                        <div class="kv">Age: <b>{git["project_age_days"]}d</b> (since {git["first_commit_date"] or "?"})</div>
                        <div class="kv">Contributors: <b>{git["contributor_count"]}</b></div>
                        <div class="kv">Branches: <b>{git["branch_count"]}</b></div>
                    </div>

                    <div class="card-section">
                        <h4>Recent Commits</h4>
                        {commits_html}
                    </div>

                    {testing_section}

                    <div class="card-section">
                        <h4>CI/CD</h4>
                        <div class="kv">{ci_html}</div>
                    </div>

                    <div class="card-section">
                        <h4>Documentation</h4>
                        <div class="kv">{doc_html}</div>
                        <div class="kv">{doc_ratio_kv}</div>
                    </div>

                    <div class="card-section">
                        <h4>Dependencies</h4>
                        <div class="kv">{dep_html}</div>
                    </div>

                    <div class="card-section">
                        <h4>Vulnerabilities</h4>
                        {vuln_html}
                    </div>

                    <div class="card-section">
                        <h4>GitHub</h4>
                        {gh_html}
                    </div>
                </div>

                <div class="card-col">
                    <div class="card-section">
                        <h4>Code by Language</h4>
                        {render_language_breakdown(p["files"]["by_language"])}
                    </div>

                    <div class="card-section">
                        <h4>File Categories</h4>
                        <table class="detail-table">
                            <thead><tr><th>Category</th><th>Files</th><th>LOC</th></tr></thead>
                            <tbody>
                                <tr><td>Source</td><td class="num">{p["files"]["by_category"]["source"]["count"]:,}</td><td class="num">{p["files"]["by_category"]["source"]["loc"]:,}</td></tr>
                                {vendor_row}
                                <tr><td>Test</td><td class="num">{p["files"]["by_category"]["test"]["count"]:,}</td><td class="num">{p["files"]["by_category"]["test"]["loc"]:,}</td></tr>
                                <tr><td>Docs</td><td class="num">{p["files"]["by_category"]["docs"]["count"]:,}</td><td class="num">{p["files"]["by_category"]["docs"]["loc"]:,}</td></tr>
                                <tr><td>Config</td><td class="num">{p["files"]["by_category"]["config"]["count"]:,}</td><td class="num">{p["files"]["by_category"]["config"]["loc"]:,}</td></tr>
                                <tr><td>Assets</td><td class="num">{p["files"]["by_category"]["assets"]["count"]:,}</td><td class="num">--</td></tr>
                                <tr><td>Other</td><td class="num">{p["files"]["by_category"]["other"]["count"]:,}</td><td class="num">--</td></tr>
                            </tbody>
                        </table>
                        <div class="kv" style="margin-top: 8px">
                            Directories: <b>{p["files"]["directory_count"]:,}</b> &bull;
                            Max Depth: <b>{p["files"]["directory_depth_max"]}</b> &bull;
                            Total Files: <b>{p["files"]["total_files"]:,}</b> &bull;
                            Total LOC: <b>{p["files"]["total_loc"]:,}</b>
                        </div>
                    </div>

                    <div class="card-section">
                        <h4>{meth_title} ({meth_compliance})</h4>
                        <div class="meth-checklist">{meth_items}</div>
                        {meth_note}
                    </div>

                    <div class="card-section">
                        <h4>Top 10 Largest Files</h4>
                        {render_largest_files(p["files"]["largest_files"])}
                    </div>
                </div>
            </div>
        </div>
    </div>'''


def render_html(portfolio, projects, title="METHODOLOGY DASHBOARD", trend_html=""):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    h_color = health_color(portfolio["health_score"])

    # Count high+ risks
    high_risk_count = portfolio["risk_counts"].get("critical", 0) + portfolio["risk_counts"].get("high", 0)

    project_cards = "\n".join(render_project_card(p) for p in projects)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: 'SF Mono', 'Fira Code', 'Consolas', 'Monaco', monospace;
    background: #0d1117;
    color: #c9d1d9;
    line-height: 1.5;
    padding: 20px;
    max-width: 1600px;
    margin: 0 auto;
}}
h1 {{ color: #e6edf3; font-size: 24px; font-weight: 600; }}
h2 {{ color: #e6edf3; font-size: 18px; font-weight: 600; margin-bottom: 12px; }}
h3 {{ color: #c9d1d9; font-size: 15px; font-weight: 600; margin-bottom: 8px; }}
h4 {{ color: #8b949e; font-size: 13px; font-weight: 600; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px; }}

.header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 24px;
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    margin-bottom: 20px;
}}
.header-time {{ color: #8b949e; font-size: 13px; }}

.summary-bar {{
    display: flex;
    gap: 32px;
    padding: 20px 24px;
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    margin-bottom: 20px;
    flex-wrap: wrap;
}}
.summary-item {{ text-align: center; }}
.summary-value {{ font-size: 32px; font-weight: 700; }}
.summary-label {{ font-size: 12px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; }}

.section {{ margin-bottom: 20px; }}
.section-header {{
    padding: 12px 24px;
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px 8px 0 0;
    border-bottom: none;
}}
.section-body {{
    padding: 16px 24px;
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 0 0 8px 8px;
}}

.risk-matrix {{ display: flex; gap: 12px; flex-wrap: wrap; }}
.risk-cell {{
    flex: 1;
    min-width: 140px;
    background: #161b22;
    padding: 12px;
    border-radius: 6px;
    border: 1px solid #30363d;
}}
.risk-label {{ font-size: 12px; font-weight: 700; letter-spacing: 1px; margin-bottom: 8px; }}
.risk-item {{ font-size: 13px; padding: 2px 0; }}
.risk-empty {{ color: #484f58; font-style: italic; font-size: 13px; }}

.meth-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
.meth-table th {{ text-align: left; padding: 8px 12px; border-bottom: 2px solid #30363d; color: #8b949e; font-size: 12px; text-transform: uppercase; }}
.meth-table td {{ padding: 8px 12px; border-bottom: 1px solid #21262d; }}
.meth-yes {{ color: #44ff88; font-weight: bold; text-align: center; }}
.meth-no {{ color: #ff4444; font-weight: bold; text-align: center; }}
.proj-name {{ font-weight: 600; color: #e6edf3; }}

.activity-section {{ display: flex; flex-direction: column; gap: 8px; }}
.activity-row {{ display: flex; align-items: center; gap: 12px; }}
.activity-name {{ width: 200px; font-size: 13px; font-weight: 600; text-align: right; }}
.activity-bar-bg {{ flex: 1; height: 20px; background: #21262d; border-radius: 4px; overflow: hidden; }}
.activity-bar {{ height: 100%; border-radius: 4px; transition: width 0.3s; }}
.activity-nums {{ width: 130px; font-size: 12px; color: #8b949e; }}

.trend-chart {{ display: flex; flex-direction: column; gap: 4px; }}
.trend-row {{ display: flex; align-items: center; gap: 12px; }}
.trend-ts {{ width: 140px; font-size: 11px; color: #8b949e; text-align: right; font-family: monospace; }}
.trend-val {{ width: 30px; font-size: 13px; font-weight: 700; text-align: right; }}
.trend-risk {{ width: 60px; font-size: 11px; color: #8b949e; }}

.project-card {{
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    margin-bottom: 16px;
    overflow: hidden;
}}
.card-header {{
    padding: 16px 24px;
    cursor: pointer;
    border-bottom: 1px solid #30363d;
}}
.card-header:hover {{ background: #1c2129; }}
.card-title {{
    display: flex;
    align-items: center;
    gap: 20px;
    flex-wrap: wrap;
    margin-bottom: 4px;
}}
.card-name {{ font-size: 18px; font-weight: 700; color: #e6edf3; }}
.card-health {{ font-size: 14px; font-weight: 700; }}
.card-risk {{ font-size: 12px; font-weight: 700; padding: 2px 8px; border-radius: 4px; background: #21262d; }}
.card-activity {{ font-size: 12px; font-weight: 700; padding: 2px 8px; border-radius: 4px; background: #21262d; }}
.card-summary {{ font-size: 13px; color: #8b949e; }}
.card-body {{ padding: 16px 24px; display: none; }}
.card-body.expanded {{ display: block; }}
.card-section {{ margin-bottom: 16px; }}
.card-columns {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
@media (max-width: 1000px) {{ .card-columns {{ grid-template-columns: 1fr; }} }}

.dim-row {{ display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }}
.dim-label {{ width: 120px; font-size: 12px; color: #8b949e; }}
.dim-bar-bg {{ flex: 1; height: 14px; background: #21262d; border-radius: 3px; overflow: hidden; }}
.dim-bar {{ height: 100%; border-radius: 3px; }}
.dim-val {{ width: 50px; font-size: 12px; color: #8b949e; text-align: right; }}

.risk-flag {{ font-size: 13px; margin-bottom: 4px; }}
.risk-badge {{ font-size: 10px; padding: 1px 6px; border-radius: 3px; color: #0d1117; font-weight: 700; }}

.detail-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
.detail-table th {{ text-align: left; padding: 4px 8px; border-bottom: 1px solid #30363d; color: #8b949e; font-size: 11px; text-transform: uppercase; }}
.detail-table td {{ padding: 4px 8px; border-bottom: 1px solid #21262d; }}
.detail-table .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
.file-path {{ color: #79c0ff; font-size: 12px; }}

.kv {{ font-size: 13px; margin-bottom: 2px; }}
.kv b {{ color: #e6edf3; }}

.meth-checklist {{ font-size: 13px; line-height: 2; }}
.meth-checklist .meth-yes {{ color: #44ff88; }}
.meth-checklist .meth-no {{ color: #ff4444; }}

.commit-line {{ font-size: 12px; margin-bottom: 3px; color: #8b949e; }}
.commit-line code {{ color: #79c0ff; }}
.commit-date {{ color: #484f58; }}

.sort-controls {{ margin-bottom: 16px; display: flex; gap: 8px; align-items: center; }}
.sort-controls span {{ font-size: 12px; color: #8b949e; text-transform: uppercase; }}
.sort-btn {{
    background: #21262d;
    border: 1px solid #30363d;
    color: #c9d1d9;
    padding: 4px 12px;
    border-radius: 4px;
    font-family: inherit;
    font-size: 12px;
    cursor: pointer;
}}
.sort-btn:hover {{ background: #30363d; }}
.sort-btn.active {{ background: #388bfd; color: #fff; border-color: #388bfd; }}
</style>
</head>
<body>

<div class="header">
    <h1>{esc(title)}</h1>
    <div class="header-time">Generated: {now} &bull; dashboard v{DASHBOARD_VERSION}</div>
</div>

<div class="summary-bar">
    <div class="summary-item">
        <div class="summary-value" style="color: {h_color}">{portfolio["health_score"]}</div>
        <div class="summary-label">Portfolio Health</div>
    </div>
    <div class="summary-item">
        <div class="summary-value">{portfolio["project_count"]}</div>
        <div class="summary-label">Projects</div>
    </div>
    <div class="summary-item">
        <div class="summary-value" style="color: {SEVERITY_COLORS.get("high", "#ff8800") if high_risk_count > 0 else "#44ff88"}">{high_risk_count}</div>
        <div class="summary-label">High+ Risk</div>
    </div>
    <div class="summary-item">
        <div class="summary-value">{portfolio["total_commits"]:,}</div>
        <div class="summary-label">Total Commits</div>
    </div>
</div>

<div class="section">
    <div class="section-header"><h2>Risk Matrix</h2></div>
    <div class="section-body">{render_risk_matrix(projects)}</div>
</div>

<div class="section">
    <div class="section-header"><h2>Methodology Compliance</h2></div>
    <div class="section-body">{render_methodology_grid(projects)}</div>
</div>

<div class="section">
    <div class="section-header"><h2>Commit Activity (30 Days)</h2></div>
    <div class="section-body">{render_activity_bars(projects)}</div>
</div>

{f'<div class="section"><div class="section-header"><h2>Historical Trends</h2></div><div class="section-body">{trend_html}</div></div>' if trend_html else ''}

<div class="section">
    <div class="section-header"><h2>Project Details</h2></div>
    <div class="section-body">
        <div class="sort-controls">
            <span>Sort by:</span>
            <button class="sort-btn active" onclick="sortCards('health')">Health (worst first)</button>
            <button class="sort-btn" onclick="sortCards('risk')">Risk</button>
            <button class="sort-btn" onclick="sortCards('activity')">Activity</button>
            <button class="sort-btn" onclick="sortCards('name')">Name</button>
            <button class="sort-btn" onclick="toggleAll()">Expand/Collapse All</button>
        </div>
        <div id="project-cards">
            {project_cards}
        </div>
    </div>
</div>

<script>
function toggleCard(header) {{
    const body = header.nextElementSibling;
    body.classList.toggle('expanded');
    saveState();
}}

let allExpanded = false;
function toggleAll() {{
    const bodies = document.querySelectorAll('.card-body');
    allExpanded = !allExpanded;
    bodies.forEach(b => {{
        if (allExpanded) b.classList.add('expanded');
        else b.classList.remove('expanded');
    }});
    saveState();
}}

function sortCards(by) {{
    const container = document.getElementById('project-cards');
    const cards = Array.from(container.querySelectorAll('.project-card'));
    const data = {json.dumps({p["name"]: {
        "health": p["scores"]["health"]["total"],
        "risk": {"critical": 0, "high": 1, "medium": 2, "low": 3, "healthy": 4}.get(worst_risk(p["scores"]["risks"]), 4),
        "activity": {"dead": 0, "stale": 1, "slowing": 2, "active": 3}.get(p["scores"]["activity"], 0),
    } for p in projects})};

    cards.sort((a, b) => {{
        const aName = a.id.replace('card-', '');
        const bName = b.id.replace('card-', '');
        const aD = data[aName] || {{}};
        const bD = data[bName] || {{}};
        if (by === 'health') return (aD.health || 0) - (bD.health || 0);
        if (by === 'risk') return (aD.risk || 0) - (bD.risk || 0);
        if (by === 'activity') return (aD.activity || 0) - (bD.activity || 0);
        if (by === 'name') return aName.localeCompare(bName);
        return 0;
    }});
    cards.forEach(c => container.appendChild(c));

    document.querySelectorAll('.sort-btn').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    saveState();
}}

// --- State-preserving auto-refresh ---

function saveState() {{
    const expanded = [];
    document.querySelectorAll('.card-body.expanded').forEach(b => {{
        const card = b.closest('.project-card');
        if (card) expanded.push(card.id);
    }});
    const activeSort = document.querySelector('.sort-btn.active');
    sessionStorage.setItem('dashboard-state', JSON.stringify({{
        expanded: expanded,
        scroll: window.scrollY,
        sort: activeSort ? activeSort.textContent.trim() : null,
        allExpanded: allExpanded
    }}));
}}

function restoreState() {{
    try {{
        const state = JSON.parse(sessionStorage.getItem('dashboard-state'));
        if (!state) return;
        allExpanded = state.allExpanded || false;
        (state.expanded || []).forEach(id => {{
            const card = document.getElementById(id);
            if (card) {{
                const body = card.querySelector('.card-body');
                if (body) body.classList.add('expanded');
            }}
        }});
        if (state.sort) {{
            document.querySelectorAll('.sort-btn').forEach(b => {{
                if (b.textContent.trim() === state.sort) b.classList.add('active');
                else b.classList.remove('active');
            }});
        }}
        if (state.scroll) window.scrollTo(0, state.scroll);
    }} catch(e) {{}}
}}

restoreState();

setInterval(() => {{
    saveState();
    fetch(location.href).then(r => r.text()).then(html => {{
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const newBody = doc.querySelector('body');
        if (newBody) {{
            document.body.innerHTML = newBody.innerHTML;
            restoreState();
        }}
    }}).catch(() => {{}});
}}, 60000);
</script>

</body>
</html>'''


# === HISTORICAL TRENDING ===

HISTORY_FILE = "dashboard_history.jsonl"  # layout: ok -- the generated file's own name; written beside the copy that ran (output_dir)


def append_history(root, portfolio, projects):
    """Append current run metrics to JSONL history file."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        # Stamped so a scoring change is interpretable in the trend: history persists only
        # derived totals, and the trend renderer diffs first-vs-last across its window, so a
        # one-time re-scaling would otherwise render as a red regression arrow indistinguishable
        # from a project that genuinely got worse.
        "dashboard_version": DASHBOARD_VERSION,
        "portfolio": {
            "health_score": portfolio["health_score"],
            "project_count": portfolio["project_count"],
            "total_commits": portfolio["total_commits"],
            "risk_counts": portfolio.get("risk_counts", {}),
        },
        "projects": {
            p["name"]: {
                "health": p["scores"]["health"]["total"],
                "risk": worst_risk(p["scores"]["risks"]),
                "activity": p["scores"]["activity"],
                "commits": p["git"]["total_commits"],
                "test_files": p["tests"]["test_file_count"],
                "vulns": p.get("vulnerabilities", {}).get("total_vulns", 0),
            }
            for p in projects
        },
    }

    history_path = root / HISTORY_FILE
    try:
        with open(history_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def load_history(root, max_entries=30):
    """Load recent history entries."""
    history_path = root / HISTORY_FILE
    entries = []
    if not history_path.exists():
        return entries
    try:
        with open(history_path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except OSError:
        pass
    return entries[-max_entries:]


def render_trend_section(history):
    """Render portfolio health trend as a simple sparkline table."""
    if len(history) < 2:
        return ""

    # Portfolio health over time
    points = []
    for entry in history:
        ts = entry.get("timestamp", "")[:16].replace("T", " ")
        score = entry.get("portfolio", {}).get("health_score", 0)
        risk_counts = entry.get("portfolio", {}).get("risk_counts", {})
        hi_risk = risk_counts.get("critical", 0) + risk_counts.get("high", 0)
        points.append((ts, score, hi_risk))

    rows = ""
    max_score = max(p[1] for p in points) or 1
    for ts, score, hi_risk in points:
        pct = int((score / 100) * 100)
        c = health_color(score)
        rows += f'''<div class="trend-row">
            <span class="trend-ts">{esc(ts)}</span>
            <div class="activity-bar-bg" style="flex: 1">
                <div class="activity-bar" style="width: {pct}%; background: {c}"></div>
            </div>
            <span class="trend-val" style="color: {c}">{score}</span>
            <span class="trend-risk">Risk: {hi_risk}</span>
        </div>'''

    # Per-project trends (last vs first)
    first_projects = history[0].get("projects", {})
    last_projects = history[-1].get("projects", {})
    delta_rows = ""
    for name in sorted(last_projects.keys()):
        curr = last_projects[name].get("health", 0)
        prev = first_projects.get(name, {}).get("health", 0)
        delta = curr - prev
        if delta != 0:
            arrow = "&#9650;" if delta > 0 else "&#9660;"
            dc = "#44ff88" if delta > 0 else "#ff4444"
            delta_rows += f'<tr><td>{esc(name)}</td><td class="num">{prev}</td><td class="num">{curr}</td><td style="color: {dc}">{arrow} {delta:+d}</td></tr>'

    delta_table = ""
    if delta_rows:
        delta_table = f'''<div class="card-section" style="margin-top: 16px">
            <h4>Project Health Changes (First &rarr; Latest)</h4>
            <table class="detail-table">
                <thead><tr><th>Project</th><th>First</th><th>Latest</th><th>Delta</th></tr></thead>
                <tbody>{delta_rows}</tbody>
            </table>
        </div>'''

    return f'''<div class="dashboard-section">
        <h3>Portfolio Health Trend ({len(points)} snapshots)</h3>
        <div class="trend-chart">{rows}</div>
        {delta_table}
    </div>'''


# === MAIN ===

def main():
    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        print_usage()
        return

    if "--sync" in args:
        target = _extract_sync_target(args)
        sync_dashboards(Path(__file__).resolve().parent, dry_run="--dry-run" in args,
                         target=target, force="--force" in args)
        return

    # A flag named --dry-run must never write (issue #67). It is consulted ONLY inside the --sync
    # branch above, so bare `--dry-run` used to fall straight through to a full scan that wrote
    # dashboard.html AND appended to dashboard_history.jsonl — the exact opposite of what the name
    # promises, and silently, since nothing said the flag had been ignored. Refuse rather than
    # no-op: a silent no-op leaves the caller unable to tell "nothing to do" from "flag ignored",
    # which is the same class of unreadable signal as the defect above.
    if "--dry-run" in args:                                                    # issue #67 pt. 4
        sys.stderr.write(
            "  --dry-run only means something together with --sync (nothing else in this\n"
            "  tool writes speculatively).\n"
            "  Usage: python3 methodology_dashboard.py --sync [DIR] --dry-run\n"  # layout: ok -- a name printed in a message, never opened
        )
        sys.exit(2)

    # Warn (best-effort) if this copy is older than the canonical.
    check_stale_version()

    root = resolve_single_project_root(ROOT)
    out_dir = output_dir(ROOT, root)
    with_submodules = "--with-submodules" in args

    project_paths = discover_projects(root, with_submodules=with_submodules)

    if not project_paths:
        print("Methodology Dashboard: No projects found.")
        return

    # Determine title based on mode
    single_project = (root / ".git").exists()
    if single_project:
        title = f"{root.name.upper()} — METHODOLOGY DASHBOARD"
    else:
        title = "METHODOLOGY DASHBOARD"

    projects = []
    for path in project_paths:
        try:
            metrics = collect_all(path)
            projects.append(metrics)
        except Exception as e:
            print(f"  Warning: Failed to collect metrics for {path.name}: {e}")

    # Sort worst-first by health score
    projects.sort(key=lambda p: p["scores"]["health"]["total"])

    portfolio = aggregate_portfolio(projects)

    # Historical trending
    append_history(out_dir, portfolio, projects)
    history = load_history(out_dir)
    trend_html = render_trend_section(history)

    html = render_html(portfolio, projects, title=title, trend_html=trend_html)

    output_path = out_dir / "dashboard.html"  # layout: ok -- the generated file's own name; written beside the copy that ran (output_dir)
    output_path.write_text(html)

    # Open in browser (skip with --no-open or when piped)
    if "--no-open" not in sys.argv and sys.stdout.isatty():
        open_in_browser(output_path)

    # Terminal summary with ANSI colors
    R = "\033[0m"       # reset
    B = "\033[1m"       # bold
    D = "\033[2m"       # dim
    def c_health(score):
        if score >= 80: return "\033[32m"    # green
        if score >= 60: return "\033[92m"    # bright green
        if score >= 40: return "\033[33m"    # yellow
        if score >= 20: return "\033[91m"    # bright red
        return "\033[31m"                     # red
    def c_risk(sev):
        return {"critical": "\033[31m", "high": "\033[91m", "medium": "\033[33m",
                "low": "\033[36m", "healthy": "\033[32m"}.get(sev, "")
    def c_activity(act):
        return {"active": "\033[32m", "slowing": "\033[33m",
                "stale": "\033[91m", "dead": "\033[31m"}.get(act, "")

    W = 70
    ph = portfolio["health_score"]
    pc = c_health(ph)
    rc = portfolio.get("risk_counts", {})
    hi_risk = rc.get("critical", 0) + rc.get("high", 0)

    print(f"\n{D}{'─'*W}{R}")
    print(f"  {B}{title}{R}  {D}│{R}  {len(projects)} projects  {D}│  v{DASHBOARD_VERSION}{R}")
    print(f"{D}{'─'*W}{R}")
    total_vulns = sum(p.get("vulnerabilities", {}).get("total_vulns", 0) for p in projects)
    total_issues = sum(p.get("github", {}).get("open_issues", 0) or 0 for p in projects)
    print(f"  Health: {pc}{B}{ph}/100{R}    "
          f"High+ Risk: {c_risk('high') if hi_risk else c_risk('healthy')}{B}{hi_risk}{R}    "
          f"Commits: {B}{portfolio['total_commits']:,}{R}")
    print(f"  Issues: {B}{total_issues}{R}    "
          f"Vulns: {c_risk('high') if total_vulns else c_risk('healthy')}{B}{total_vulns}{R}    "
          f"History: {B}{len(load_history(out_dir))}{R} snapshots")
    print(f"{D}{'─'*W}{R}")

    # Column headers
    print(f"  {D}{'Project':<25s} {'Health':>8s}  {'Risk':>8s}  {'Activity':>8s}{R}")

    for p in projects:
        wr = worst_risk(p["scores"]["risks"])
        h = p["scores"]["health"]["total"]
        a = p["scores"]["activity"]
        hc = c_health(h)
        wrc = c_risk(wr)
        ac = c_activity(a)
        print(f"  {p['name']:<25s} {hc}{h:>5d}/100{R}  {wrc}{wr:>8s}{R}  {ac}{a:>8s}{R}")

    print(f"{D}{'─'*W}{R}")
    print(f"  {D}Dashboard: {output_path}{R}")
    print()


if __name__ == "__main__":
    main()
