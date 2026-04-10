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
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# === CONSTANTS ===

ROOT = Path(__file__).parent
EXCLUDE_DIRS = {"methodology", ".git", "__pycache__", "node_modules", ".venv", "venv"}
WALK_SKIP = {".git", "node_modules", "__pycache__", ".venv", "venv", "target",
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


# === DISCOVERY ===

def discover_projects(root):
    """Discover projects to scan.

    Two modes, auto-detected:
    - Single-project mode: if root itself is a git repo, scan it plus any
      git submodules (each submodule appears as its own entry).
    - Portfolio mode: if root is NOT a git repo, scan sibling directories
      that contain .git/ (the original behavior).
    """
    # Single-project mode: root is a git repo
    if (root / ".git").exists():
        projects = [root]
        # Discover git submodules
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
            if ext not in ASSET_EXTS and category != "assets":
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


def collect_coverage_config(path):
    configs = []
    checks = [
        ".coveragerc", "setup.cfg", "pyproject.toml",
        "jest.config.js", "jest.config.ts", "jest.config.json",
        ".nycrc", ".nycrc.json", "vitest.config.ts", "vitest.config.js",
        "jacoco.xml",
    ]
    for name in checks:
        if (path / name).exists():
            configs.append(name)
    # Check package.json for jest/coverage config
    pkg = path / "package.json"
    if pkg.exists():
        try:
            with open(pkg) as f:
                data = json.load(f)
            if "jest" in data or "nyc" in data:
                configs.append("package.json (jest/nyc)")
        except (OSError, json.JSONDecodeError):
            pass

    return configs


# === SCORING ===

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

    # 2. Testing (0-20)
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
        doc_score += 2
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

    days = metrics["git"]["days_since_last_commit"]
    if days is not None and days > 90:
        risks.append({"severity": "critical", "description": f"Project appears abandoned (no commits in {days} days)"})
    elif days is not None and days > 30:
        risks.append({"severity": "high", "description": f"Stale project (no commits in {days} days)"})

    if metrics["tests"]["test_file_count"] == 0:
        risks.append({"severity": "high", "description": "No test infrastructure"})
    elif metrics["tests"]["test_to_source_ratio"] < 0.1:
        risks.append({"severity": "medium", "description": f"Test coverage is very thin (ratio: {metrics['tests']['test_to_source_ratio']:.2f})"})

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

    largest = metrics["files"]["largest_files"]
    if largest and largest[0]["loc"] > 2000:
        risks.append({"severity": "medium", "description": f"Large files detected ({largest[0]['path']}: {largest[0]['loc']:,} lines)"})

    commits = metrics["git"]["total_commits"]
    age = metrics["git"]["project_age_days"]
    if commits < 10 and age > 30:
        risks.append({"severity": "medium", "description": f"Very low commit velocity ({commits} commits in {age} days)"})

    if metrics["git"]["branch_count"] > 5:
        risks.append({"severity": "low", "description": f"Multiple branches ({metrics['git']['branch_count']}) may indicate incomplete merges"})

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
    }

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

    # Git info
    git = p["git"]
    days = git["days_since_last_commit"]
    days_str = f"{days}d ago" if days is not None else "never"

    # Recent commits
    commits_html = ""
    for c in git["recent_commits"]:
        commits_html += f'<div class="commit-line"><code>{c["hash"]}</code> <span class="commit-date">{c["date"]}</span> {esc(c["message"])}</div>'

    # Health dimension bars
    dims = ["activity", "testing", "documentation", "ci_cd", "methodology"]
    dim_labels = ["Activity", "Testing", "Documentation", "CI/CD", "Methodology"]
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

                    <div class="card-section">
                        <h4>Testing</h4>
                        <div class="kv">Test Files: <b>{p["tests"]["test_file_count"]}</b></div>
                        <div class="kv">Test LOC: <b>{p["tests"]["test_loc"]:,}</b></div>
                        <div class="kv">Source LOC: <b>{p["tests"]["source_loc"]:,}</b></div>
                        <div class="kv">Test:Source Ratio: <b>{p["tests"]["test_to_source_ratio"]:.3f}</b></div>
                        <div class="kv">Coverage Config: <b>{cov_html}</b></div>
                    </div>

                    <div class="card-section">
                        <h4>CI/CD</h4>
                        <div class="kv">{ci_html}</div>
                    </div>

                    <div class="card-section">
                        <h4>Documentation</h4>
                        <div class="kv">{doc_html}</div>
                        <div class="kv">Doc:Source Ratio: <b>{doc["doc_to_source_ratio"]:.3f}</b></div>
                    </div>

                    <div class="card-section">
                        <h4>Dependencies</h4>
                        <div class="kv">{dep_html}</div>
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


def render_html(portfolio, projects, title="METHODOLOGY DASHBOARD"):
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
    <div class="header-time">Generated: {now}</div>
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


# === MAIN ===

def main():
    root = ROOT

    project_paths = discover_projects(root)

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
    html = render_html(portfolio, projects, title=title)

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
    print(f"  {B}{title}{R}  {D}│{R}  {len(projects)} projects")
    print(f"{D}{'─'*W}{R}")
    print(f"  Health: {pc}{B}{ph}/100{R}    "
          f"High+ Risk: {c_risk('high') if hi_risk else c_risk('healthy')}{B}{hi_risk}{R}    "
          f"Commits: {B}{portfolio['total_commits']:,}{R}")
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
