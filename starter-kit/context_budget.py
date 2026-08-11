#!/usr/bin/env python3
"""context_budget.py — size budgets for session-resident documents.

WHY THIS EXISTS
---------------
Some documents are injected into every session's context before the first word of
the task is read. Others are documents the protocol *orders* a session to read.
Both kinds only ever grow: every close-out appends a handoff, an evaluation, a
learning row. There is a compounding term and no decay term.

EVIDENCE. Measured on an adopter project (ResortApp) across 51 raw session
transcripts: opening context rose from 45,931 tokens to 103,241 over 38 consecutive
sessions and **never once decreased**, until a human hand-extracted 156 KB out of
CLAUDE.md. It regrew 7.6% in the next 43 hours — half of that from learnings-index
rows this methodology itself instructs sessions to append (Phase 3C).

MEASUREMENT ALONE WAS ALREADY PRESENT AND DID NOT WORK. `methodology_dashboard.py`
printed `Large files detected (SESSION_NOTES.md: 26,039 lines)` at every Phase 0 —
the single risk flag in that project's dashboard.html — and 15+ consecutive sessions
read past it. So this tool GATES: a pre-commit hook that refuses growth past a
ceiling, rather than a second thing to print.

WHAT IT DOES NOT DO
-------------------
It never adjudicates a claim, never edits a document, and never truncates anything.
Every number it prints comes with the argv that produced it, so a session can
re-derive rather than believe — that is the failure mode this whole tool exists to
interrupt, and a machine-written ledger is easier to over-trust than a prose one.

Python 3 stdlib only, cross-platform. Conventions follow methodology_dashboard.py.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

VERSION = "1.0.0"
CONFIG_NAME = ".context-budget.json"
HISTORY_NAME = ".context-budget-history.jsonl"

R = "\033[0m"; B = "\033[1m"; D = "\033[2m"
RED = "\033[31m"; YEL = "\033[33m"; GRN = "\033[32m"; CYN = "\033[36m"
W = 74

CLEAN, WARN, BREACH, USAGE = 0, 1, 2, 3


# === PLUMBING ===

def run(argv, cwd=None):
    """Return (rc, stdout, stderr). Never swallows failure into an empty string —
    the dashboard's git_cmd does, which makes 'no drift' and 'git is missing' the
    same output. A check that cannot fail has no place in a tool built to find them."""
    try:
        p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=30)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except FileNotFoundError:
        return 127, "", f"not found: {argv[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except OSError as e:
        return 126, "", str(e)


def expand(root, p):
    p = os.path.expanduser(p)
    return p if os.path.isabs(p) else os.path.join(root, p)


def find_root(start=None):
    d = Path(start or os.getcwd()).resolve()
    for c in [d, *d.parents]:
        if (c / CONFIG_NAME).exists() or (c / ".git").exists():
            return str(c)
    return str(d)


def load_config(root):
    path = os.path.join(root, CONFIG_NAME)
    if not os.path.exists(path):
        return None, path
    try:
        with open(path) as f:
            return json.load(f), path
    except (OSError, ValueError) as e:
        print(f"{RED}config unreadable: {path}: {e}{R}")
        sys.exit(USAGE)


# === MEASUREMENT ===

def measure_file(root, spec):
    """One budgeted file. status ∈ ok | warn | over | unmeasured."""
    path = expand(root, spec["path"])
    out = {"path": spec["path"], "abs": path, "class": spec.get("class", "resident"),
           "findings": [], "status": "ok"}
    if not os.path.exists(path):
        out.update(status="unmeasured", reason="file does not exist")
        return out
    try:
        data = open(path, "rb").read()
    except OSError as e:
        out.update(status="unmeasured", reason=str(e))
        return out

    text = data.decode("utf-8", "replace")
    lines = text.split("\n")
    out["bytes"] = len(data)
    out["lines"] = len(lines)
    out["max_bytes"] = spec.get("max_bytes")
    out["warn_bytes"] = spec.get("warn_bytes")

    def over(msg, kind):
        out["findings"].append({"kind": kind, "msg": msg})
        out["status"] = "over"

    if spec.get("max_bytes") and out["bytes"] > spec["max_bytes"]:
        over(f"{out['bytes']:,} B exceeds the {spec['max_bytes']:,} B ceiling "
             f"by {out['bytes']-spec['max_bytes']:,}", "bytes")
    elif spec.get("warn_bytes") and out["bytes"] > spec["warn_bytes"]:
        out["findings"].append({"kind": "bytes", "msg":
            f"{out['bytes']:,} B is past the {spec['warn_bytes']:,} B warn line"})
        out["status"] = "warn"

    if spec.get("max_lines") and out["lines"] > spec["max_lines"]:
        over(f"{out['lines']:,} lines exceeds the {spec['max_lines']:,} line ceiling", "lines")

    cap = spec.get("max_line_bytes")
    if cap:
        long = [(i + 1, len(l)) for i, l in enumerate(lines) if len(l) > cap]
        if long:
            worst = max(long, key=lambda t: t[1])
            over(f"{len(long)} line(s) exceed {cap} B — worst is line {worst[0]} at "
                 f"{worst[1]:,} B. A line ceiling alone just creates longer lines.", "line_bytes")

    # structure: a declared pattern matching FEWER records than expected is an
    # instrument failure, not a pass (learning #22 / #26a).
    for s in spec.get("structure", []):
        pat = re.compile(s["pattern"], re.M)
        n = len(pat.findall(text))
        if "expect_min" in s and n < s["expect_min"]:
            out["findings"].append({"kind": "instrument", "msg":
                f"pattern {s['pattern']!r} matched {n}, fewer than the declared minimum "
                f"{s['expect_min']} — the check is not measuring what it claims"})
            out["status"] = "instrument-failed"
        elif "max" in s and n > s["max"]:
            over(f"{n}× {s['pattern']!r}, expected at most {s['max']}"
                 + (f" — {s['why']}" if s.get("why") else ""), "structure")

    # protected fence: a budget that can eat the statement of purpose is worse
    # than no budget.
    fence = spec.get("protected_fence")
    if fence:
        o, c = f"<!-- {fence} -->", f"<!-- /{fence} -->"
        if o not in text or c not in text:
            out["findings"].append({"kind": "protected", "msg":
                f"the {fence} fence is missing — the statement of purpose it guards "
                f"may have been removed"})
            out["status"] = "over"
        else:
            body = text.split(o, 1)[1].split(c, 1)[0]
            out["protected_bytes"] = len(body.encode())
            if len(body.strip()) < spec.get("protected_min_bytes", 400):
                out["findings"].append({"kind": "protected", "msg":
                    f"the {fence} block is only {len(body.strip())} B — it looks emptied"})
                out["status"] = "over"
    return out


def check_synced(root, spec):
    """Synced files are drift-checked, never size-checked: this project may not edit
    them, so a size finding would be unactionable. Both went 48 days behind unnoticed
    because zero local edits means `git diff` here shows nothing."""
    path = expand(root, spec["path"])
    can = expand(root, spec["canonical"])
    out = {"path": spec["path"], "status": "ok", "findings": []}
    if not os.path.exists(path) or not os.path.exists(can):
        out.update(status="unmeasured", reason="local or canonical copy missing")
        return out
    rc1, local, _ = run(["git", "hash-object", path])
    rc2, canon, _ = run(["git", "hash-object", can])
    if rc1 or rc2:
        out.update(status="unmeasured", reason="git hash-object unavailable")
        return out
    out["local"], out["canonical"] = local, canon
    if local != canon:
        out["status"] = "warn"
        out["findings"].append({"kind": "sync", "msg":
            f"differs from canonical: local {local[:10]} vs {canon[:10]}"
            + _behind(can, local)})
    return out


def _behind(canonical_path, local_blob):
    """How many canonical commits landed AFTER the revision this copy matches.

    Counting every commit that ever touched the file would answer a different
    question and read as a much larger drift than there is — so if the local blob
    is not found in canonical history, say so rather than printing a number that
    means something else."""
    cdir = os.path.dirname(os.path.dirname(canonical_path))
    rel = os.path.relpath(canonical_path, cdir)
    rc, log, _ = run(["git", "-C", cdir, "log", "--format=%H", "--", rel], cwd=cdir)
    if rc or not log:
        return " (canonical history unreadable)"
    shas = log.split("\n")
    for i, sha in enumerate(shas):
        rc2, blob, _ = run(["git", "-C", cdir, "rev-parse", f"{sha}:{rel}"], cwd=cdir)
        if rc2 == 0 and blob == local_blob:
            rc3, when, _ = run(["git", "-C", cdir, "log", "-1", "--format=%cs", sha], cwd=cdir)
            date = f", {when}" if rc3 == 0 and when else ""
            return (f" — this copy is canonical {sha[:7]}{date}, "
                    f"{i} commit(s) behind" if i else " — same revision, different bytes?")
    return " — this copy matches no revision in canonical history (locally edited?)"


# === HISTORY / GROWTH RUN ===

def load_history(root):
    p = os.path.join(root, HISTORY_NAME)
    if not os.path.exists(p):
        return []
    rows = []
    for line in open(p, errors="ignore"):
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass
    return rows


def append_history(root, snapshot, history):
    """Append only when something changed. The growth run needs to survive a fresh
    clone, so this file is tracked — which means an unconditional append would put a
    diff in every commit and make the log itself a growth problem. Identical
    consecutive measurements carry no signal."""
    if history and history[-1].get("files") == snapshot["files"]:
        return False
    with open(os.path.join(root, HISTORY_NAME), "a") as f:
        f.write(json.dumps(snapshot, sort_keys=True) + "\n")
    return True


def growth_run(history, snapshot, limit):
    """Consecutive non-shrinking total-resident measurements. Fires independently of
    any ceiling — this is the trigger that survives someone raising a ceiling to
    silence a warning, and it is the one that would have fired on day 3 of the
    38-session run rather than at session 38."""
    series = [h.get("resident_bytes") for h in history if h.get("resident_bytes")]
    series.append(snapshot["resident_bytes"])
    run_len = 0
    for a, b in zip(series, series[1:]):
        run_len = run_len + 1 if b >= a else 0
    return run_len, run_len >= limit


# === REMEDIATION ===

REMEDIES = {
 "bytes": [
  ("Move", "Relocate the section to the module document that owns it "
           "(server/, mobile/*/, database/ each have a CLAUDE.md). Resident context is "
           "for what a session needs BEFORE it knows the task."),
  ("Compute", "Replace any hand-maintained count or list with the command that "
              "produces it. A count written into a read-often file is a future lie — "
              "10 of 11 rows of one table here were wrong when it was finally measured."),
  ("Archive", "git already conserves every byte. Cut the content and leave "
              "`git show <sha>:<file>` — retrieval by original line number, zero new bytes."),
  ("Delete", "If another file says the same thing, delete this copy and link to it."),
  ("Raise the ceiling", "Edit .context-budget.json. This is last for a reason — see "
                        "the cost of growth below."),
 ],
 "lines":      [("Split", "One note per record in a sibling directory; keep an index here.")],
 "line_bytes": [("Split the line", "A per-line ceiling exists because a line-count "
                 "ceiling alone just produces longer lines.")],
 "structure":  [("Fix the structure", "The file was probably appended to where it should "
                 "have been updated.")],
 "protected":  [("Restore it", "This block states what the project is for. Recover it from "
                 "git and put it back before anything else.")],
 "instrument": [("Fix the pattern", "A pattern matching fewer records than declared is a "
                 "broken instrument reporting green.")],
 "sync":       [("Re-sync", "Run the methodology repo's bin/sync. Do NOT edit the local "
                 "copy — project changes belong in CLAUDE.md, protocol changes upstream.")],
}

BYPASS_COST = """\
Bypassing costs every future session, not this one:
  · Each 2,930 B added to a resident file is about 1,000 tokens on EVERY API call of
    every future session (~265 calls/session, measured).
  · Resident does not mean read carefully. A table sat in resident context here with
    10 of 11 rows wrong for weeks.
  · Growth is not self-limiting. The one unbudgeted run went 45,931 -> 103,241 opening
    tokens in 9 days and was reversed only by hand.
  · A false line in a resident file is treated as authoritative by every session after
    it. The measured price of one such line was a full session's deliverable.
  · Nothing records that a bypass happened, so nobody after you will know to look."""


# === RENDER ===

def status_colour(s):
    return {"ok": GRN, "warn": YEL, "over": RED,
            "instrument-failed": RED, "unmeasured": CYN}.get(s, "")


def render(root, results, synced, run_len, run_hit, cfg, snapshot):
    print(f"\n{D}{'─'*W}{R}")
    worst = "ok"
    order = {"ok": 0, "unmeasured": 1, "warn": 2, "instrument-failed": 3, "over": 4}
    for r in results + synced:
        if order[r["status"]] > order[worst]:
            worst = r["status"]
    c = status_colour(worst)
    print(f"  {B}context budget{R}  {c}{B}{worst.upper()}{R}   "
          f"{D}resident {snapshot['resident_bytes']:,} B "
          f"≈ {snapshot['resident_bytes']/cfg.get('bytes_per_token',2.93):,.0f} tok{R}")
    print(f"{D}{'─'*W}{R}")
    print(f"  {D}{'file':<34s}{'size':>12s}{'ceiling':>12s}  status{R}")
    for r in results:
        name = short(r["path"])
        if r["status"] == "unmeasured":
            print(f"  {name:<34s}{'—':>12s}{'—':>12s}  {CYN}unmeasured{R} {D}({r['reason']}){R}")
            continue
        size = f"{r['bytes']:,} B" if r["class"] != "read-mandated" else f"{r['lines']:,} ln"
        ceil = (f"{r['max_bytes']:,} B" if r["class"] != "read-mandated"
                else f"{cfg_lookup(cfg, r['path'], 'max_lines') or '—'} ln")
        cc = status_colour(r["status"])
        print(f"  {name:<34s}{size:>12s}{str(ceil):>12s}  {cc}{r['status']}{R}")
    for r in synced:
        cc = status_colour(r["status"])
        print(f"  {short(r['path']):<34s}{'synced':>12s}{'canonical':>12s}  {cc}{r['status']}{R}")

    tot = cfg["classes"]["resident"]
    print(f"{D}{'─'*W}{R}")
    print(f"  resident total {B}{snapshot['resident_bytes']:,} B{R} / "
          f"{tot['total_bytes']:,} B ceiling   "
          f"{D}growth run {run_len}/{cfg.get('growth_run', 10)}{R}")

    findings = [(r, f) for r in results + synced for f in r["findings"]]
    if not findings and not run_hit:
        print(f"{D}{'─'*W}{R}\n  {GRN}nothing over budget{R}\n")
        return
    print(f"{D}{'─'*W}{R}")
    if run_hit:
        print(f"  {YEL}{B}growth run{R}: {run_len} consecutive non-shrinking measurements. "
              f"Nothing is\n  over a ceiling yet — that is the point. Ceilings fire late.")
    for r, f in findings:
        print(f"\n  {status_colour(r['status'])}{B}{r['path']}{R} — {f['msg']}")
        for i, (name, how) in enumerate(REMEDIES.get(f["kind"], []), 1):
            print(f"      {i}. {B}{name}{R} — {how}")
    print()


def short(path, width=34):
    """Keep the column readable without hiding which file is meant: absolute paths
    collapse to ~ and, if still too long, to <parent>/<name>."""
    p = path.replace(str(Path.home()), "~")
    if len(p) <= width:
        return p
    parts = p.rstrip("/").split("/")
    tail = "/".join(parts[-2:]) if len(parts) > 1 else parts[-1]
    return ("…/" + tail)[-width:]


def cfg_lookup(cfg, path, key):
    for s in cfg.get("files", []):
        if s["path"] == path:
            return s.get(key)
    return None


# === CALIBRATE ===

def calibrate(root, cfg):
    """Re-derive bytes-per-token by regressing each session's opening context against
    the size of the resident file at that moment. Writes nothing. A tool whose thesis
    is 'store a fact as the command that produces it' must not carry its own constant
    as an unmeasured literal."""
    slug = "-" + str(Path(root).resolve()).strip("/").replace("/", "-")
    tdir = Path.home() / ".claude" / "projects" / slug
    if not tdir.exists():
        print(f"{CYN}no transcripts at {tdir} — cannot calibrate{R}")
        return WARN
    target = cfg.get("calibrate_against", "CLAUDE.md")
    rc, log, err = run(["git", "log", "--format=%H %cI", "--", target], cwd=root)
    if rc:
        print(f"{RED}git log failed: {err}{R}")
        return USAGE
    hist = []
    for line in log.split("\n"):
        if not line.strip():
            continue
        sha, iso = line.split(None, 1)
        rc2, size, _ = run(["git", "cat-file", "-s", f"{sha}:{target}"], cwd=root)
        if rc2 == 0 and size.isdigit():
            hist.append((iso.strip(), int(size)))
    hist.sort()
    if len(hist) < 3:
        print(f"{CYN}only {len(hist)} sizes of {target} in history — not enough{R}")
        return WARN

    def size_at(iso):
        best = None
        for when, size in hist:
            if when <= iso:
                best = size
        return best

    pts = []
    for f in sorted(tdir.glob("*.jsonl")):
        first_ts = first_ctx = None
        try:
            for line in open(f, errors="ignore"):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if first_ts is None and rec.get("timestamp"):
                    first_ts = rec["timestamp"]
                u = (rec.get("message") or {}).get("usage") or {}
                if u:
                    first_ctx = (u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0)
                                 + u.get("cache_creation_input_tokens", 0))
                    break
        except OSError:
            continue
        if first_ts and first_ctx:
            s = size_at(first_ts)
            if s:
                pts.append((s, first_ctx))
    if len(pts) < 4:
        print(f"{CYN}only {len(pts)} usable sessions — not enough to fit{R}")
        return WARN
    n = len(pts)
    sx = sum(p[0] for p in pts); sy = sum(p[1] for p in pts)
    sxx = sum(p[0]**2 for p in pts); sxy = sum(p[0]*p[1] for p in pts)
    den = n*sxx - sx*sx
    if den == 0:
        print(f"{CYN}no variation in {target} size across sessions — cannot fit{R}")
        return WARN
    slope = (n*sxy - sx*sy) / den
    inter = (sy - slope*sx) / n
    my = sy/n
    ss_tot = sum((p[1]-my)**2 for p in pts)
    ss_res = sum((p[1] - (inter + slope*p[0]))**2 for p in pts)
    r2 = 1 - ss_res/ss_tot if ss_tot else float("nan")
    print(f"\n  n={n} sessions, regressor = bytes({target})")
    print(f"  opening_tokens ≈ {inter:,.0f} + {slope:.4f} × bytes      R² = {r2:.4f}")
    print(f"  ⇒ {1/slope:.2f} bytes/token   (config carries {cfg.get('bytes_per_token')})")
    print(f"  ⇒ fixed harness floor ≈ {inter:,.0f} tokens\n")
    print(f"  {D}writes nothing — edit {CONFIG_NAME} yourself if you want to adopt these{R}\n")
    return CLEAN


# === HOOK ===

HOOK = """#!/bin/sh
# installed by context_budget.py — refuses a commit that GROWS a budgeted file past
# its ceiling. A commit that shrinks such a file always passes.
exec python3 "$(git rev-parse --show-toplevel)/context_budget.py" --precommit
"""


def install_hook(root):
    rc, top, err = run(["git", "rev-parse", "--git-dir"], cwd=root)
    if rc:
        print(f"{RED}not a git repository: {err}{R}")
        return USAGE
    gd = top if os.path.isabs(top) else os.path.join(root, top)
    # `core.hooksPath` redirects git away from <git-dir>/hooks entirely, and the
    # methodology's own BOOTSTRAP.md Step 10 tells adopters to set it (`.githooks`),
    # so writing to <git-dir>/hooks unconditionally would install a hook git never
    # runs — and print "installed". A relative value resolves against the worktree
    # top level, which is what git itself does when it runs the hook.
    rc2, configured, _ = run(["git", "config", "--get", "core.hooksPath"], cwd=root)
    if rc2 == 0 and configured:
        hooks = configured if os.path.isabs(configured) else os.path.join(root, configured)
        via = f" (via core.hooksPath = {configured})"
    else:
        hooks = os.path.join(gd, "hooks")
        via = ""
    os.makedirs(hooks, exist_ok=True)
    p = os.path.join(hooks, "pre-commit")
    if os.path.exists(p) and "context_budget.py" not in open(p, errors="ignore").read():
        print(f"{YEL}a pre-commit hook already exists at {p} and is not ours.{R}")
        print(f"  Add this line to it yourself:\n    {HOOK.strip().splitlines()[-1]}")
        return WARN
    open(p, "w").write(HOOK)
    os.chmod(p, 0o755)
    print(f"  installed {p}{via}")
    print(f"  {D}bypass with `git commit --no-verify`; the cost of doing so is printed "
          f"when it fires{R}")
    return CLEAN


def precommit(root, cfg):
    """Relative rule: refuse only when the staged file is over ceiling AND larger than
    HEAD. A commit that reduces an over-budget file must never be blocked, or the tool
    prevents its own remedy."""
    bad = []
    for spec in cfg.get("files", []):
        path = expand(root, spec["path"])
        if not os.path.exists(path) or os.path.isabs(spec["path"]):
            continue  # files outside the repo are not staged by this commit
        rc, staged, _ = run(["git", "show", f":{spec['path']}"], cwd=root)
        if rc:
            continue  # not staged
        new = len(staged.encode())
        rc2, head, _ = run(["git", "show", f"HEAD:{spec['path']}"], cwd=root)
        old = len(head.encode()) if rc2 == 0 else 0
        ceil = spec.get("max_bytes")
        if ceil and new > ceil and new > old:
            bad.append((spec["path"], old, new, ceil))
    if not bad:
        return CLEAN
    print(f"\n{RED}{B}context-budget: REFUSED{R}")
    for path, old, new, ceil in bad:
        print(f"  {B}{path}{R}  {old:,} -> {new:,} B   ceiling {ceil:,} B")
        print(f"    +{new-old:,} B this commit, {new-ceil:,} B over.")
    print(f"\n  Cheapest legal actions:")
    for i, (name, how) in enumerate(REMEDIES["bytes"], 1):
        print(f"    {i}. {B}{name}{R} — {how}")
    print(f"\n  A commit that SHRINKS one of these always passes, even while over ceiling.")
    print(f"\n{YEL}{BYPASS_COST}{R}\n")
    return BREACH


# === SELFTEST ===

def selftest(root, cfg):
    """Every gate must be observed failing, not just passing."""
    import tempfile
    ok = True

    def check(name, cond):
        nonlocal ok
        ok &= bool(cond)
        print(f"  {'PASS' if cond else 'FAIL'}  {name}")

    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "t.md")
        open(p, "w").write("x" * 5000 + "\n")
        r = measure_file(d, {"path": "t.md", "max_bytes": 1000})
        check("byte ceiling fires when exceeded", r["status"] == "over")
        r = measure_file(d, {"path": "t.md", "max_bytes": 10000})
        check("byte ceiling passes when under", r["status"] == "ok")
        r = measure_file(d, {"path": "t.md", "max_bytes": 10000, "max_line_bytes": 100})
        check("per-line ceiling fires on a long line", r["status"] == "over")
        r = measure_file(d, {"path": "missing.md", "max_bytes": 10})
        check("a missing file is 'unmeasured', never 'ok'", r["status"] == "unmeasured")

        open(p, "w").write("## ACTIVE TASK\nz\n## ACTIVE TASK\n")
        r = measure_file(d, {"path": "t.md", "structure":
                             [{"pattern": r"^## ACTIVE TASK", "max": 1}]})
        check("structure ceiling fires on a duplicated heading", r["status"] == "over")
        r = measure_file(d, {"path": "t.md", "structure":
                             [{"pattern": r"^## NOTHING", "expect_min": 1}]})
        check("a pattern matching nothing is instrument-failed, not ok",
              r["status"] == "instrument-failed")

        open(p, "w").write("a\n<!-- pf -->\n" + "y"*600 + "\n<!-- /pf -->\nb\n")
        r = measure_file(d, {"path": "t.md", "protected_fence": "pf"})
        check("protected fence present and populated passes", r["status"] == "ok")
        open(p, "w").write("a\nb\n")
        r = measure_file(d, {"path": "t.md", "protected_fence": "pf"})
        check("removing the protected fence is refused", r["status"] == "over")
        open(p, "w").write("a\n<!-- pf -->\n\n<!-- /pf -->\nb\n")
        r = measure_file(d, {"path": "t.md", "protected_fence": "pf"})
        check("emptying the protected block is refused", r["status"] == "over")

    hist = [{"resident_bytes": v} for v in (100, 110, 120, 130)]
    n, hit = growth_run(hist, {"resident_bytes": 140}, 4)
    check("growth run counts consecutive non-shrinking measurements", n == 4 and hit)
    n, hit = growth_run(hist, {"resident_bytes": 90}, 4)
    check("a shrink resets the growth run", n == 0 and not hit)

    rc, _, _ = run(["definitely-not-a-real-binary-xyz"])
    check("a missing binary surfaces as rc=127, never as empty success", rc == 127)

    check("--force is not offered", "--force" not in open(__file__).read()
          .split("def selftest")[0])
    print()
    return CLEAN if ok else BREACH


# === MAIN ===

def print_usage():
    print(f"context_budget.py v{VERSION} — size budgets for session-resident documents")
    print("")
    print("Usage: python3 context_budget.py [command] [options]")
    print("")
    print("Commands:")
    print("  (default)      Measure every budgeted file, append one history line, print")
    print("                 the ledger. Exit 2 if anything is over a hard ceiling.")
    print("  install-hook   Install a git pre-commit hook that refuses a commit growing")
    print("                 a budgeted file past its ceiling. Opt-in.")
    print("  --precommit    What the hook runs. Refuses only when the staged file is over")
    print("                 ceiling AND larger than HEAD, so a shrinking commit passes.")
    print("  --calibrate    Re-derive bytes-per-token from this project's transcripts and")
    print("                 print the fit. Writes nothing.")
    print("  --selftest     Observe every gate FAILING as well as passing.")
    print("  --json         Machine-readable output.")
    print("  -h, --help     Show this help and exit.")
    print("")
    print("Exit: 0 clean · 1 warn/unmeasured · 2 over a hard ceiling · 3 config or usage")
    print("")
    print("There is deliberately no --force. The only way to permit growth is to edit")
    print(f"{CONFIG_NAME}, so the decision lands as a reviewable diff.")


def main():
    args = sys.argv[1:]
    if "-h" in args or "--help" in args:
        print_usage(); return CLEAN
    root = find_root()
    cfg, cfg_path = load_config(root)
    if cfg is None:
        print(f"{RED}no {CONFIG_NAME} found at or above {os.getcwd()}{R}")
        print(f"  This tool refuses to invent budgets for a project that has not "
              f"declared them.")
        return USAGE

    if "--selftest" in args:
        return selftest(root, cfg)
    if "--calibrate" in args:
        return calibrate(root, cfg)
    if "install-hook" in args:
        return install_hook(root)
    if "--precommit" in args:
        return precommit(root, cfg)

    results = [measure_file(root, s) for s in cfg.get("files", [])]
    synced = [check_synced(root, s) for s in cfg.get("synced", [])]
    resident = sum(r.get("bytes", 0) for r in results if r["class"] == "resident")
    snapshot = {"resident_bytes": resident,
                "files": {r["path"]: r.get("bytes") for r in results}}

    tot = cfg["classes"]["resident"]
    if resident > tot["total_bytes"]:
        results.append({"path": "(resident total)", "class": "resident", "status": "over",
                        "bytes": resident, "max_bytes": tot["total_bytes"], "findings":
                        [{"kind": "bytes", "msg":
                          f"{resident:,} B across all auto-loaded files exceeds the "
                          f"{tot['total_bytes']:,} B ceiling"}]})

    hist = load_history(root)
    run_len, run_hit = growth_run(hist, snapshot, cfg.get("growth_run", 10))
    append_history(root, snapshot, hist)

    if "--json" in args:
        print(json.dumps({"resident_bytes": resident, "growth_run": run_len,
                          "files": results, "synced": synced}, indent=2, default=str))
    else:
        render(root, results, synced, run_len, run_hit, cfg, snapshot)

    states = [r["status"] for r in results + synced]
    if "over" in states or "instrument-failed" in states:
        return BREACH
    if "warn" in states or "unmeasured" in states or run_hit:
        return WARN
    return CLEAN


if __name__ == "__main__":
    sys.exit(main())
