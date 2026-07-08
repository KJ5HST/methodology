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
  By default, common non-project directories are excluded. If you have
  the methodology repo cloned as a sibling, add its directory name here.

- WALK_SKIP: Directories skipped during file traversal (build artifacts,
  vendor dependencies, etc.).

- METHODOLOGY_ITEMS: The weighted checklist used for compliance scoring.
  Adjust weights to match what matters most for your team.
"""

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

# === CONSTANTS ===

# Canonical dashboard version. Source of truth: methodology/starter-kit/methodology_dashboard.py.
# Every other copy (portfolio root + per-project) is a synced copy of the canonical and must
# carry the same value. A copy whose DASHBOARD_VERSION is older than the canonical is stale —
# re-sync from the canonical. Bump on any change to the canonical script.
DASHBOARD_VERSION = "2.8.0"

ROOT = Path(__file__).parent
EXCLUDE_DIRS = {"methodology", "BrogueCE-iOS", ".git", "__pycache__", "node_modules", ".venv", "venv"}
WALK_SKIP = {".git", ".claude", "node_modules", "__pycache__", ".venv", "venv", "target",
             "build", "dist", ".build", "DerivedData", "Pods", ".gradle"}

SOURCE_EXTS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".rs", ".c", ".cpp", ".cc", ".h", ".hh",
    ".hpp", ".m", ".mm", ".java", ".swift", ".ino", ".go", ".rb", ".php", ".cs",
    ".kt", ".scala", ".lua", ".sh", ".bash", ".zsh", ".pl", ".r",
}
TEST_PATTERNS = {"test_", "_test.", ".test.", ".spec.", "tests/", "__tests__/", "test/"}
DOC_EXTS = {".md", ".txt", ".rst", ".adoc", ".org"}
CONFIG_FILES = {
    "Dockerfile", "Makefile", "CMakeLists.txt", "Rakefile", "Gemfile",
    "Procfile", "fly.toml", "netlify.toml", "vercel.json",
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
}

METHODOLOGY_ITEMS = [
    ("SESSION_RUNNER.md", 25, "file"),
    ("SAFEGUARDS.md", 20, "file"),
    ("SESSION_NOTES.md", 20, "file"),
    ("BACKLOG.md", 15, "file"),
    ("CHANGELOG.md", 5, "file"),
    ("ROADMAP.md", 5, "file"),
    ("docs/methodology", 10, "dir"),
    ("docs/methodology/workstreams", 10, "dir"),
]

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
DOC_ONLY_SOURCE_LOC_MAX = 200            # source LOC at/below this is "essentially no real code"
DOC_ONLY_DOC_LOC_MIN    = 200            # doc LOC at/above this signals a real doc corpus
DOC_ONLY_DOC_FILES_MIN  = 3              # this many doc files also signals a real doc corpus
DOC_ONLY_MARKER         = ".methodology-profile"  # bidirectional opt-in: token "doc-only" | "code"


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
    if ext in CONFIG_EXTS or name in CONFIG_FILES:
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
    Silent when the canonical can't be found or when this copy IS the canonical."""
    self_path = Path(__file__).resolve()
    canonical = find_canonical(self_path.parent)
    if not canonical or canonical == self_path:
        return
    canon_ver = parse_version(canonical)
    if canon_ver and version_key(canon_ver) > version_key(DASHBOARD_VERSION):
        sys.stderr.write(
            f"  ⚠ methodology_dashboard.py is stale: this copy is v{DASHBOARD_VERSION}, "
            f"canonical is v{canon_ver}.\n"
            f"    Re-sync: python3 {canonical} --sync\n"
        )


def sync_dashboards(start, dry_run=False):
    """Copy the canonical dashboard to the portfolio root + every discovered project.
    In --dry-run mode nothing is written; the planned actions are printed. Returns the
    count of files that were (or would be) changed.

    NOTE: a live sync writes methodology_dashboard.py into every project, including the
    repos where it is still git-tracked — those need the Phase 3 `git rm --cached` +
    per-repo commit discipline. Tracked targets are flagged in the output."""
    canonical = find_canonical(start)
    if not canonical:
        sys.stderr.write("  Cannot locate canonical methodology/starter-kit/"
                         "methodology_dashboard.py — nothing synced.\n")
        return 0
    # .../starter-kit/methodology_dashboard.py -> starter-kit -> methodology -> portfolio root
    portfolio_root = canonical.parent.parent.parent
    canon_text = canonical.read_text()

    targets = [portfolio_root / "methodology_dashboard.py"]
    for proj in discover_projects(portfolio_root):
        targets.append(proj / "methodology_dashboard.py")

    print(f"Canonical: {canonical} (v{DASHBOARD_VERSION})")
    print(f"{'DRY RUN — no files written.' if dry_run else 'Syncing.'} "
          f"Targets: portfolio root + {len(targets) - 1} project(s)\n")

    changed = inspected = 0
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
        note = ""
        if t.exists() and git_cmd(t.parent, "ls-files", "--error-unmatch", t.name):
            note = "  [git-tracked — needs Phase 3 untrack]"
        if action != "unchanged":
            changed += 1
            if not dry_run:
                shutil.copyfile(canonical, t)
        try:
            label = t.relative_to(portfolio_root)
        except ValueError:
            label = t
        print(f"  {action:<9s} {label}{note}")

    verb = "Would change" if dry_run else "Changed"
    print(f"\n  {verb} {changed} of {inspected} target(s).")
    return changed


def print_usage():
    print(f"methodology_dashboard.py v{DASHBOARD_VERSION} — portfolio/project health scanner")
    print("")
    print("Usage: python3 methodology_dashboard.py [options]")
    print("")
    print("Options:")
    print("  --no-open          Do not open the generated dashboard.html in a browser.")
    print("  --with-submodules  In single-project mode, also scan git submodules as")
    print("                     separate entries (default: scan the project only).")
    print("  --sync             Copy the canonical dashboard to the portfolio root and")
    print("                     every discovered project (use --dry-run to preview).")
    print("  --dry-run          With --sync, show planned changes without writing.")
    print("  -h, --help         Show this help and exit.")


# === DISCOVERY ===

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

    # First commit date
    first_log = git_cmd(path, "log", "--reverse", "--format=%ai", "-1")
    if first_log:
        first_date_str = first_log[:10]
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
            "test": {"count": 0, "loc": 0},
            "docs": {"count": 0, "loc": 0},
            "config": {"count": 0, "loc": 0},
            "assets": {"count": 0},
            "other": {"count": 0},
        },
        "largest_files": [],
        "directory_depth_max": 0,
        "directory_count": 0,
    }

    all_files = []
    dirs_seen = set()

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
            if category in ("source", "test", "docs", "config"):
                metrics["by_category"][category]["count"] += 1
                metrics["by_category"][category]["loc"] += loc
            elif category in ("assets", "other"):
                metrics["by_category"][category]["count"] += 1

            # Track for largest files
            if loc > 0:
                all_files.append({"path": str(rel_path), "loc": loc, "ext": ext})

    metrics["directory_count"] = len(dirs_seen)
    all_files.sort(key=lambda f: f["loc"], reverse=True)
    metrics["largest_files"] = all_files[:10]

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
        for entry in path.iterdir() if path.exists() else []:
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
    """Return the Path to a CHANGELOG in the project root or docs/, else None.
    Mirrors collect_doc_metrics's has_changelog detection (case-insensitive prefix), but
    restricted to regular files so a CHANGELOG *directory* is not treated as a ledger."""
    for base in (path, path / "docs"):
        if not base.is_dir():
            continue
        try:
            for entry in sorted(base.iterdir()):
                if entry.is_file() and entry.name.upper().startswith("CHANGELOG"):
                    return entry
        except OSError:
            continue
    return None


def _count_backlog_done(path):
    """Signal F: BACKLOG.md checklist items still marked done (`- [x]`). The methodology
    removes a backlog item from BACKLOG.md in the same commit that logs it to CHANGELOG, so
    surviving done-marks are a best-effort proxy for 'completed but never migrated'."""
    for name in ("BACKLOG.md", "docs/BACKLOG.md", "docs/planning/BACKLOG.md"):
        bl = path / name
        if bl.is_file():
            try:
                return len(_BACKLOG_DONE_RE.findall(bl.read_text(encoding="utf-8", errors="ignore")))
            except OSError:
                return 0
    return 0


def evaluate_changelog_freshness(path, git):
    """Component C — CHANGELOG ledger-lag / freshness monitor.

    Advisory only: it feeds at most a 1-point documentation nudge (present vs. fresh) plus
    RISK lines; it never hard-fails a score. The two lag signals are git-only and format-
    agnostic (they ask *when was the ledger last committed, and how far has HEAD moved since*),
    so they work for any project that keeps a CHANGELOG; the never-used signal keys on the
    methodology seed sentinel, and the backlog signal on unmigrated BACKLOG.md done-marks.
    `git` is the already-collected collect_git_metrics dict.
    """
    result = {
        "present": False,
        "unlogged_commits": 0,        # Signal C
        "frontier_lag_days": None,    # Signal B
        "dated_entry_count": 0,
        "has_seed_sentinel": False,
        "never_used": False,          # Signal D
        "backlog_done_unmigrated": _count_backlog_done(path),  # Signal F
        "new_adopter_grace": False,
        "is_fresh": False,
        "signals": [],                # list of (severity, description) advisory tuples
    }

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
    try:
        rel = str(changelog.relative_to(path))
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
    if not grace:
        if result["unlogged_commits"] >= LEDGER_UNLOGGED_MAX:
            result["signals"].append((
                "medium",
                f"CHANGELOG ledger lag: {result['unlogged_commits']} commits since it was "
                f"last updated (Component C)",
            ))
        if active and lag_days is not None and lag_days > LEDGER_LAG_DAYS_MAX:
            result["signals"].append((
                "low", f"CHANGELOG frontier trails HEAD by {lag_days} days",
            ))
        if result["never_used"]:
            result["signals"].append((
                "medium",
                "CHANGELOG present but never used — still the untouched seed on a repo with "
                "real commit history",
            ))
    # Signal F is adopter-scoped: only a methodology adopter (root SESSION_RUNNER.md) follows the
    # "remove from BACKLOG.md in the commit that logs it to CHANGELOG" convention, so surviving
    # done-marks are a defect only there — not on a non-adopter sibling that keeps a [x] backlog.
    if result["backlog_done_unmigrated"] > 0 and (path / "SESSION_RUNNER.md").is_file():
        result["signals"].append((
            "low",
            f"{result['backlog_done_unmigrated']} done-marked BACKLOG.md item(s) not migrated "
            f"to CHANGELOG",
        ))

    return result


def collect_methodology_metrics(path):
    present = 0
    missing = []

    for item_path, weight, kind in METHODOLOGY_ITEMS:
        full_path = path / item_path
        exists = full_path.is_dir() if kind == "dir" else full_path.exists()
        if exists:
            present += 1
        else:
            missing.append(item_path)

    # Weighted score
    score = 0
    for item_path, weight, kind in METHODOLOGY_ITEMS:
        full_path = path / item_path
        exists = full_path.is_dir() if kind == "dir" else full_path.exists()
        if exists:
            score += weight

    return {
        "methodology_files_present": present,
        "methodology_files_total": len(METHODOLOGY_ITEMS),
        "compliance_score": score,
        "missing_files": missing,
        "items": {
            item_path: (path / item_path).is_dir() if kind == "dir" else (path / item_path).exists()
            for item_path, weight, kind in METHODOLOGY_ITEMS
        },
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
    ws_present = any((path / rel).is_file() for rel in (
        "docs/methodology/workstreams/RESEARCH_DOCUMENTATION_WORKSTREAM.md",
        "workstreams/RESEARCH_DOCUMENTATION_WORKSTREAM.md",
        "RESEARCH_DOCUMENTATION_WORKSTREAM.md",
    ))
    if ws_present:
        score += 1
    result["signals"].append(
        ("Research-Documentation verification artifacts", verif_artifact or ws_present))

    result["score"] = min(20, score)
    return result


def detect_doc_only(path, files, render):
    """BL-5 — classify a repo as document-only / research: marker -> source-cap -> corpus.

    Returns {"is_doc_only": bool, "reason": "marker"|"heuristic"|""}. Advisory only; nothing gates.
    """
    # 1. Explicit bidirectional marker wins (force either classification).
    marker = path / DOC_ONLY_MARKER
    try:
        if marker.is_file():
            tokens = marker.read_text(encoding="utf-8-sig", errors="ignore").strip().split()
            token = tokens[0].lower() if tokens else ""
            if token == "doc-only":
                return {"is_doc_only": True, "reason": "marker"}
            if token == "code":
                return {"is_doc_only": False, "reason": "marker"}
            # empty/unknown -> fall through to the heuristic
    except OSError:
        pass

    # 2. Source-cap short-circuit: real code should be tested; never silently exempt it.
    src = files["by_category"]["source"]["loc"]
    if src > DOC_ONLY_SOURCE_LOC_MAX:
        return {"is_doc_only": False, "reason": "heuristic"}

    # 3. Corpus disjunction (only when source is negligible): a real doc corpus OR a render
    #    toolchain — the latter catches a pure-LaTeX/Quarto repo whose .tex/.qmd are not counted
    #    as docs (so its doc_loc is ~0), the exact source_loc≈0 research repo that must not be missed.
    doc_loc = files["by_category"]["docs"]["loc"]
    doc_files = files["by_category"]["docs"]["count"]
    corpus = (
        doc_loc >= DOC_ONLY_DOC_LOC_MIN
        or doc_files >= DOC_ONLY_DOC_FILES_MIN
        or render["toolchain_present"]
    )
    return {"is_doc_only": bool(corpus), "reason": "heuristic"}


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

    # 5. Methodology (0-20)
    scores["methodology"] = int(metrics["methodology"]["compliance_score"] * 0.2)

    scores["total"] = sum(scores.values())
    return scores


def assess_risks(metrics):
    risks = []
    doc_only = metrics.get("doc_only", {}).get("is_doc_only", False)
    render = metrics.get("render", {})

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

    meth = metrics["methodology"]["compliance_score"]
    if meth == 0:
        risks.append({"severity": "high", "description": "No methodology adoption (0% compliance)"})
    elif meth < 50:
        risks.append({"severity": "medium", "description": f"Partial methodology adoption ({meth}%)"})

    if not metrics["docs"]["has_license"]:
        risks.append({"severity": "low", "description": "No LICENSE file"})

    # BL-5: only a large *source* file is a code-smell; a 2500-line chapter (.md/.tex) is normal for
    # a document repo. Scan for the largest *source* file over the threshold rather than inspecting
    # only largest[0], so a non-source #1 (e.g. a big lockfile/JSON) doesn't mask a real large source
    # file below it (helps mixed repos too — no doc_only branch needed).
    big_src = next((f for f in metrics["files"]["largest_files"]
                    if f["loc"] > 2000 and f.get("ext") in SOURCE_EXTS), None)
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
    cl = metrics.get("changelog", {})
    adopter = metrics["methodology"]["items"].get("SESSION_RUNNER.md", False)
    if not cl.get("present") and adopter and metrics["git"]["total_commits"] >= LEDGER_REAL_HISTORY_MIN:
        risks.append({"severity": "medium",
                      "description": "Methodology adopter has commit history but no CHANGELOG ledger (Component C)"})
    for sev, desc in cl.get("signals", []):
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
    meth = collect_methodology_metrics(path)
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


def render_methodology_grid(projects):
    headers = ["Project", "Session Runner", "Safeguards", "Session Notes", "Backlog", "Methodology Dir", "Workstreams", "Score"]
    item_keys = [item[0] for item in METHODOLOGY_ITEMS]

    rows = ""
    for p in projects:
        items = p["methodology"]["items"]
        cells = f'<td class="proj-name">{esc(p["name"])}</td>'
        for key in item_keys:
            present = items.get(key, False)
            if present:
                cells += '<td class="meth-yes">&#10003;</td>'
            else:
                cells += '<td class="meth-no">&#10007;</td>'
        score = p["methodology"]["compliance_score"]
        score_color = "#44ff88" if score >= 80 else "#ffcc00" if score >= 40 else "#ff4444"
        cells += f'<td style="color: {score_color}; font-weight: bold">{score}%</td>'
        rows += f"<tr>{cells}</tr>"

    header_row = "".join(f"<th>{h}</th>" for h in headers)
    return f'''<table class="meth-table">
        <thead><tr>{header_row}</tr></thead>
        <tbody>{rows}</tbody>
    </table>'''


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

    # Methodology checklist
    meth_items = ""
    for item_path, weight, kind in METHODOLOGY_ITEMS:
        present = p["methodology"]["items"].get(item_path, False)
        icon = "&#10003;" if present else "&#10007;"
        cls = "meth-yes" if present else "meth-no"
        meth_items += f'<span class="{cls}">{icon} {esc(item_path)}</span> '

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
    dims = ["activity", "testing", "documentation", "ci_cd", "methodology"]
    dim_labels = ["Activity", "Render/Verify" if is_doc_only else "Testing",
                  "Documentation", "CI/CD", "Methodology"]
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
                        <div class="kv">Test:Source Ratio: <b>{fmt_ratio(p["tests"]["test_to_source_ratio"], src_loc)}</b></div>
                        <div class="kv">Coverage Config: <b>{cov_html}</b></div>
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
                        <h4>Methodology Compliance ({p["methodology"]["compliance_score"]}%)</h4>
                        <div class="meth-checklist">{meth_items}</div>
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

HISTORY_FILE = "dashboard_history.jsonl"


def append_history(root, portfolio, projects):
    """Append current run metrics to JSONL history file."""
    entry = {
        "timestamp": datetime.now().isoformat(),
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
        sync_dashboards(Path(__file__).resolve().parent, dry_run="--dry-run" in args)
        return

    # Warn (best-effort) if this copy is older than the canonical.
    check_stale_version()

    root = ROOT
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
    append_history(root, portfolio, projects)
    history = load_history(root)
    trend_html = render_trend_section(history)

    html = render_html(portfolio, projects, title=title, trend_html=trend_html)

    output_path = root / "dashboard.html"
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
          f"History: {B}{len(load_history(root))}{R} snapshots")
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
