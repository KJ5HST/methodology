#!/usr/bin/env python3
"""quality_ratchet.py — declared quality thresholds that bind every actor and only tighten.

WHY THIS EXISTS
---------------
The methodology's quality gates are mostly questions the actor asks itself. A
self-certified gate does not scale under N agents; it multiplies. The alternative is
to enforce on the ARTIFACT: a project declares the thresholds it already meets
(tests pass, coverage >= X, complexity <= Y, a link check exits 0) in one
machine-readable file, and a hook refuses any commit that LOOSENS one of them. The
threshold starts where the project is and only ever moves toward better. That is
the whole mechanism — a ratchet, not a ruler.

WHAT IT DOES NOT DO
-------------------
It ships no linter, coverage runner, or complexity tool: the methodology recommends,
it does not reimplement. Which command produces each number is the project's choice
(BOOTSTRAP.md Step 10 lists options per stack). It never edits code, never adjudicates
a review finding, and a gate it cannot run reports UNMEASURED, never pass. It holds
THRESHOLDS, not commands: a changed `command` or `extract` is printed as a warning and
left to review — the results file will show the discontinuity.

There is deliberately no --force. Loosening a threshold is a decision, and the only
way to take it is to edit .quality-gates.json under plan-mode approval and commit
with --no-verify, which the hook prints as a recorded bypass (SAFEGUARDS.md, Blast
Radius Limits; SESSION_RUNNER.md failure mode #17).

Python 3 stdlib only, cross-platform. Conventions follow context_budget.py.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

VERSION = "1.0.0"
CONFIG_NAME = ".quality-gates.json"
DEFAULT_RESULTS = ".quality-gates-results.json"
DIRECTIONS = ("min", "max")

R = "\033[0m"; B = "\033[1m"; D = "\033[2m"
RED = "\033[31m"; YEL = "\033[33m"; GRN = "\033[32m"; CYN = "\033[36m"

CLEAN, WARN, REFUSED, USAGE = 0, 1, 2, 3


# === PLUMBING ===

def run(argv, cwd=None, timeout=None, shell=False):
    try:
        p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                           timeout=timeout, shell=shell)
    except (OSError, subprocess.TimeoutExpired) as e:
        return 127, "", str(e)
    return p.returncode, p.stdout, p.stderr


def find_root(start=None):
    d = os.path.abspath(start or os.getcwd())
    while True:
        if os.path.exists(os.path.join(d, CONFIG_NAME)):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def load_manifest_text(text, where):
    """Parse manifest JSON; return (cfg, defects). Defects are strings a human can act on."""
    try:
        cfg = json.loads(text)
    except ValueError as e:
        return None, [f"{where}: not valid JSON ({e})"]
    return cfg, config_defects(cfg)


def config_defects(cfg):
    out = []
    gates = cfg.get("gates") if isinstance(cfg, dict) else None
    if not isinstance(gates, list):
        return ["`gates` must be a list"]
    seen = set()
    for i, g in enumerate(gates):
        tag = f"gate[{i}]"
        if not isinstance(g, dict):
            out.append(f"{tag}: not an object"); continue
        name = g.get("name")
        if not name or not isinstance(name, str):
            out.append(f"{tag}: missing `name`"); continue
        tag = f"gate {name!r}"
        if name in seen:
            out.append(f"{tag}: duplicate name — the ratchet keys on names")
        seen.add(name)
        if g.get("direction") not in DIRECTIONS:
            out.append(f"{tag}: `direction` must be one of {DIRECTIONS}")
        try:
            float(g.get("threshold"))
        except (TypeError, ValueError):
            out.append(f"{tag}: `threshold` must be a number")
        if "extract" in g:
            try:
                re.compile(g["extract"])
            except re.error as e:
                out.append(f"{tag}: `extract` is not a valid regex ({e})")
            if not g.get("command"):
                out.append(f"{tag}: `extract` without `command` — nothing to extract from")
    return out


def gate_map(cfg):
    return {g["name"]: g for g in cfg.get("gates", []) if isinstance(g, dict) and g.get("name")}


def blob_text(root, rev_path):
    rc, out, _ = run(["git", "cat-file", "-p", rev_path], cwd=root)
    return out if rc == 0 else None


def head_sha(root):
    rc, out, _ = run(["git", "rev-parse", "--short", "HEAD"], cwd=root)
    return out.strip() if rc == 0 else None


def sha12(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:12]


# === THE RATCHET (--precommit) ===

def compare(old_cfg, new_cfg):
    """Return (refusals, warnings) for the transition old -> new. Pure; no git.

    Refused: a gate removed; a direction changed; a `min` threshold lowered; a `max`
    threshold raised. Warned: a command/extract changed (the ratchet cannot judge it).
    Adding a gate and tightening a threshold always pass."""
    refusals, warnings = [], []
    old, new = gate_map(old_cfg), gate_map(new_cfg)
    for name, og in old.items():
        ng = new.get(name)
        if ng is None:
            refusals.append(f"gate {name!r} removed (was {og.get('direction')} "
                            f"{og.get('threshold')}) — removing a gate is the loosest loosening")
            continue
        if og.get("direction") != ng.get("direction"):
            refusals.append(f"gate {name!r}: direction {og.get('direction')} -> "
                            f"{ng.get('direction')} — a direction flip is not a tightening")
            continue
        try:
            ot, nt = float(og.get("threshold")), float(ng.get("threshold"))
        except (TypeError, ValueError):
            continue  # config_defects reports it; the ratchet has nothing to compare
        if og.get("direction") == "min" and nt < ot:
            refusals.append(f"gate {name!r}: floor lowered {ot:g} -> {nt:g}")
        elif og.get("direction") == "max" and nt > ot:
            refusals.append(f"gate {name!r}: ceiling raised {ot:g} -> {nt:g}")
        for k in ("command", "extract"):
            if og.get(k) != ng.get(k):
                warnings.append(f"gate {name!r}: `{k}` changed — the ratchet holds thresholds, "
                                f"not commands; review the diff and the next results file")
    return refusals, warnings


BYPASS_COST = """\
  · This commit makes a declared threshold weaker than HEAD's. Loosening requires
    plan-mode approval, in its own commit, with the reason in the ledger
    (SAFEGUARDS.md, Blast Radius Limits). Tightening never needs approval.
  · Bypass once: git commit --no-verify — recorded, not exempt: the manifest's git
    history shows the loosening and the dashboard reports it as a risk."""


def precommit(root):
    staged = blob_text(root, f":{CONFIG_NAME}")
    if staged is None:
        return CLEAN  # manifest not in this commit: nothing to ratchet
    new_cfg, defects = load_manifest_text(staged, "staged " + CONFIG_NAME)
    if new_cfg is None or defects:
        for m in defects:
            print(f"{RED}quality-ratchet: config defect — {m}{R}")
        print(f"{RED}refused: a manifest with defects would gate nothing{R}")
        return REFUSED
    old = blob_text(root, f"HEAD:{CONFIG_NAME}")
    if old is None:
        print(f"{D}quality-ratchet: first manifest commit ({len(new_cfg['gates'])} gate(s)) — "
              f"nothing to compare against{R}")
        return CLEAN
    old_cfg, _ = load_manifest_text(old, "HEAD " + CONFIG_NAME)
    if old_cfg is None:
        return CLEAN  # HEAD's copy is unparseable; the staged one is the first valid manifest
    refusals, warnings = compare(old_cfg, new_cfg)
    for m in warnings:
        print(f"{YEL}quality-ratchet: warning — {m}{R}")
    if refusals:
        print(f"{RED}{B}quality-ratchet: REFUSED — {len(refusals)} threshold(s) loosened{R}")
        for m in refusals:
            print(f"  {RED}✗ {m}{R}")
        print(BYPASS_COST)
        return REFUSED
    added = set(gate_map(new_cfg)) - set(gate_map(old_cfg))
    if added:
        print(f"{D}quality-ratchet: {len(added)} gate(s) added: {', '.join(sorted(added))}{R}")
    return CLEAN


# === MEASUREMENT (--run) ===

def measure_gate(root, g, timeout):
    """Run one gate. Returns a result dict; `status` is pass | fail | unmeasured."""
    res = {"name": g["name"], "direction": g["direction"], "threshold": float(g["threshold"]),
           "measured": None, "status": "unmeasured", "note": ""}
    cmd = g.get("command")
    if not cmd:
        res["note"] = "declared, no command"
        return res
    rc, out, err = run(cmd, cwd=root, timeout=timeout, shell=True)
    text = out + err
    if g.get("extract"):
        m = re.search(g["extract"], text, re.MULTILINE)
        if not m or not m.groups():
            res["note"] = f"extract matched nothing (exit {rc})"
            return res
        try:
            res["measured"] = float(m.group(1))
        except ValueError:
            res["note"] = f"extract captured {m.group(1)!r}, not a number"
            return res
    else:
        res["measured"] = float(rc)   # no extract: the exit code IS the measurement
    ok = (res["measured"] >= res["threshold"] if g["direction"] == "min"
          else res["measured"] <= res["threshold"])
    res["status"] = "pass" if ok else "fail"
    return res


def run_gates(root, cfg, timeout=600):
    results = [measure_gate(root, g, timeout) for g in cfg.get("gates", [])]
    summary = {s: sum(1 for r in results if r["status"] == s)
               for s in ("pass", "fail", "unmeasured")}
    snapshot = {"gates": results, "summary": summary,
                "manifest": sha12(cfg.get("gates", [])), "head": head_sha(root)}
    snapshot["results"] = sha12(snapshot["gates"])
    snapshot["ran_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    snapshot["version"] = VERSION
    return snapshot


def summary_line(snap):
    s, n = snap["summary"], len(snap["gates"])
    return (f"quality_ratchet: {s['pass']}/{n} pass · {s['fail']} fail · "
            f"{s['unmeasured']} unmeasured · results {snap['results']} · manifest {snap['manifest']}")


def render(snap, title):
    print(f"\n{D}{'─' * 74}{R}")
    colour = GRN if snap["summary"]["fail"] == 0 and snap["summary"]["unmeasured"] == 0 else (
        RED if snap["summary"]["fail"] else YEL)
    print(f"  {B}{title}{R}  {colour}{B}{summary_line(snap).split(': ', 1)[1]}{R}")
    print(f"{D}{'─' * 74}{R}")
    print(f"  {D}{'gate':<30}{'rule':>14}{'measured':>12}  status{R}")
    for r in snap["gates"]:
        rule = f"{'>=' if r['direction'] == 'min' else '<='} {r['threshold']:g}"
        meas = "—" if r["measured"] is None else f"{r['measured']:g}"
        col = {"pass": GRN, "fail": RED, "unmeasured": YEL}[r["status"]]
        note = f"  {D}{r['note']}{R}" if r.get("note") else ""
        print(f"  {r['name'][:30]:<30}{rule:>14}{meas:>12}  {col}{r['status']}{R}{note}")
    print(f"{D}{'─' * 74}{R}")
    print(f"  {D}cite in the receipt:{R} {summary_line(snap)}\n")


def results_path(root, cfg):
    return os.path.join(root, cfg.get("results_file") or DEFAULT_RESULTS)


def load_results(root, cfg):
    p = results_path(root, cfg)
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p))
    except ValueError:
        return None


def do_run(root, cfg, as_json=False):
    snap = run_gates(root, cfg)
    with open(results_path(root, cfg), "w") as f:
        json.dump(snap, f, indent=1, sort_keys=True)
        f.write("\n")
    if as_json:
        print(json.dumps(snap, indent=1, sort_keys=True))
    else:
        render(snap, "quality gates — run")
    if snap["summary"]["fail"]:
        return REFUSED
    return WARN if snap["summary"]["unmeasured"] else CLEAN


def do_status(root, cfg, as_json=False):
    snap = load_results(root, cfg)
    n = len(cfg.get("gates", []))
    if snap is None:
        msg = f"{n} gate(s) declared, never run here — `quality_ratchet.py --run` measures them"
        print(json.dumps({"gates": n, "results": None, "note": msg}) if as_json
              else f"{YEL}quality-ratchet: {msg}{R}")
        return WARN if n else CLEAN
    stale = snap.get("manifest") != sha12(cfg.get("gates", []))
    if as_json:
        snap["stale"] = stale
        print(json.dumps(snap, indent=1, sort_keys=True))
    else:
        render(snap, f"quality gates — last run {snap.get('ran_at', '?')} at {snap.get('head', '?')}")
        if stale:
            print(f"{YEL}quality-ratchet: the manifest changed since that run — re-run before "
                  f"citing it{R}")
    if stale:
        return WARN
    return REFUSED if snap["summary"]["fail"] else (WARN if snap["summary"]["unmeasured"] else CLEAN)


# === HOOK ===

HOOK = """#!/bin/sh
# installed by quality_ratchet.py — refuses a commit that LOOSENS a declared quality
# threshold in .quality-gates.json. Tightening and adding gates always pass.
exec python3 "$(git rev-parse --show-toplevel)/quality_ratchet.py" --precommit
"""
HOOK_LINE = HOOK.strip().splitlines()[-1]


def install_hook(root):
    rc, gd, err = run(["git", "rev-parse", "--git-dir"], cwd=root)
    if rc:
        print(f"{RED}not a git repository: {err}{R}"); return USAGE
    gd = gd.strip() if os.path.isabs(gd.strip()) else os.path.join(root, gd.strip())
    rc2, configured, _ = run(["git", "config", "--get", "core.hooksPath"], cwd=root)
    configured = configured.strip()
    if rc2 == 0 and configured:
        hooks = configured if os.path.isabs(configured) else os.path.join(root, configured)
    else:
        hooks = os.path.join(gd, "hooks")
    os.makedirs(hooks, exist_ok=True)
    p = os.path.join(hooks, "pre-commit")
    if os.path.exists(p):
        existing = open(p, errors="ignore").read()
        if "quality_ratchet.py" in existing:
            print(f"  already installed at {p}"); return CLEAN
        print(f"{YEL}a pre-commit hook already exists at {p} and is not ours — chain it:{R}")
        print(f"  add this line before its final exit (after a ledger gate, if you run one):\n"
              f"    python3 \"$(git rev-parse --show-toplevel)/quality_ratchet.py\" --precommit || exit $?")
        return WARN
    open(p, "w").write(HOOK); os.chmod(p, 0o755)
    print(f"  installed {p}")
    print(f"  {D}bypass with `git commit --no-verify` — recorded, not exempt{R}")
    return CLEAN


# === SELFTEST ===

def selftest():
    """Observe every gate FAILING as well as passing, in a throwaway git repo."""
    fails, passed = [], [0]

    def check(label, cond):
        print(f"  {GRN + 'PASS' if cond else RED + 'FAIL'}{R}  {label}")
        (passed.__setitem__(0, passed[0] + 1) if cond else fails.append(label))

    py = sys.executable.replace("\\", "/")
    base = {"version": 1, "gates": [
        {"name": "three", "direction": "min", "threshold": 3,
         "command": f'"{py}" -c "print(3)"', "extract": r"(\d+)"},
        {"name": "exit-zero", "direction": "max", "threshold": 0, "command": f'"{py}" -c "pass"'},
    ]}
    # --- pure ratchet arithmetic ---
    loosened = json.loads(json.dumps(base)); loosened["gates"][0]["threshold"] = 2
    raised = json.loads(json.dumps(base)); raised["gates"][1]["threshold"] = 1
    tightened = json.loads(json.dumps(base)); tightened["gates"][0]["threshold"] = 4
    removed = {"version": 1, "gates": base["gates"][:1]}
    flipped = json.loads(json.dumps(base)); flipped["gates"][0]["direction"] = "max"
    added = json.loads(json.dumps(base)); added["gates"].append(
        {"name": "new", "direction": "max", "threshold": 0})
    cmd_changed = json.loads(json.dumps(base)); cmd_changed["gates"][1]["command"] = "true"
    check("lowering a floor is refused", compare(base, loosened)[0])
    check("raising a ceiling is refused", compare(base, raised)[0])
    check("removing a gate is refused", compare(base, removed)[0])
    check("flipping a direction is refused", compare(base, flipped)[0])
    check("tightening passes", not compare(base, tightened)[0])
    check("adding a gate passes", not compare(base, added)[0])
    check("a changed command warns, not refuses",
          not compare(base, cmd_changed)[0] and compare(base, cmd_changed)[1])
    check("config defects are reported", config_defects({"gates": [{"name": "x", "direction": "up",
                                                                     "threshold": "n"}]}))
    # --- the hook, end to end, in a throwaway repo ---
    with tempfile.TemporaryDirectory() as d:
        run(["git", "init", "-q", d]); run(["git", "-C", d, "config", "user.email", "t@t"])
        run(["git", "-C", d, "config", "user.name", "t"])
        here = os.path.abspath(__file__)
        import shutil; shutil.copy(here, os.path.join(d, "quality_ratchet.py"))
        json.dump(base, open(os.path.join(d, CONFIG_NAME), "w"))
        run(["git", "-C", d, "add", "-A"]); run(["git", "-C", d, "commit", "-q", "-m", "base"])
        # --run: both gates pass; a results file appears; the summary line is citable
        rc, out, _ = run([py, "quality_ratchet.py", "--run"], cwd=d)
        check("--run exits 0 when every gate passes", rc == CLEAN)
        check("--run writes the results file", os.path.exists(os.path.join(d, DEFAULT_RESULTS)))
        check("--run prints a citable summary line", "quality_ratchet: 2/2 pass" in out)
        rc, out, _ = run([py, "quality_ratchet.py", "--status"], cwd=d)
        check("--status reads the last run", rc == CLEAN and "2/2 pass" in out)
        # a failing gate: exit 2; an uncommanded gate: unmeasured, exit 1
        failing = json.loads(json.dumps(base)); failing["gates"][0]["threshold"] = 4
        json.dump(failing, open(os.path.join(d, CONFIG_NAME), "w"))
        rc, out, _ = run([py, "quality_ratchet.py", "--run"], cwd=d)
        check("--run exits 2 on a failed gate", rc == REFUSED and "1 fail" in out)
        unm = json.loads(json.dumps(base)); unm["gates"].append(
            {"name": "declared-only", "direction": "min", "threshold": 1})
        json.dump(unm, open(os.path.join(d, CONFIG_NAME), "w"))
        rc, out, _ = run([py, "quality_ratchet.py", "--run"], cwd=d)
        check("a gate with no command is UNMEASURED (exit 1), never pass",
              rc == WARN and "1 unmeasured" in out)
        # the ratchet through git: install the hook, stage a loosening, commit is refused
        run([py, "quality_ratchet.py", "install-hook"], cwd=d)
        json.dump(loosened, open(os.path.join(d, CONFIG_NAME), "w"))
        run(["git", "-C", d, "add", CONFIG_NAME])
        rc, _, err = run(["git", "-C", d, "commit", "-q", "-m", "loosen"])
        check("the installed hook refuses a loosened threshold", rc != 0 and "REFUSED" in err + _)
        rc, _, _ = run(["git", "-C", d, "commit", "-q", "--no-verify", "-m", "loosen anyway"])
        check("--no-verify bypasses it (recorded in history, not exempt)", rc == 0)
        json.dump(tightened, open(os.path.join(d, CONFIG_NAME), "w"))
        run(["git", "-C", d, "add", CONFIG_NAME])
        rc, _, _ = run(["git", "-C", d, "commit", "-q", "-m", "tighten"])
        check("the installed hook passes a tightened threshold", rc == 0)
    if fails:
        print(f"\n{RED}selftest: {len(fails)} of {len(fails) + passed[0]} checks FAILED{R}")
        return REFUSED
    print(f"\n{GRN}selftest: OK — {passed[0]} checks observed failing and passing{R}")
    return CLEAN


# === CLI ===

def print_usage():
    print(f"quality_ratchet.py v{VERSION} — declared quality thresholds that only tighten")
    print("")
    print("Usage: python3 quality_ratchet.py <command> [--json]")
    print("")
    print("Commands:")
    print("  --run          Run every declared gate, write the results file, print the table")
    print("                 and a citable summary line. Exit 2 on any fail, 1 on unmeasured.")
    print("  --status       Report the last run without running anything.")
    print("  --precommit    What the hook runs: refuse a staged .quality-gates.json whose")
    print("                 thresholds are looser than HEAD's. Tightening/adding always pass.")
    print("  install-hook   Install (or explain how to chain) the pre-commit hook. Opt-in.")
    print("  --selftest     Observe every gate FAILING as well as passing.")
    print("  -h, --help     Show this help and exit.")
    print("")
    print("Exit: 0 clean · 1 warn/unmeasured · 2 refused/failed · 3 config or usage")
    print("")
    print("There is deliberately no --force. Loosening a threshold is an edit to")
    print(f"{CONFIG_NAME} under plan-mode approval, committed with --no-verify — a recorded bypass.")


def main():
    args = sys.argv[1:]
    if not args or "-h" in args or "--help" in args:
        print_usage(); return CLEAN if args else USAGE
    if "--selftest" in args:
        return selftest()
    if "--force" in args:
        print(f"{RED}there is no --force; edit {CONFIG_NAME} under plan-mode approval instead{R}")
        return USAGE
    root = find_root()
    if root is None:
        print(f"{RED}no {CONFIG_NAME} found at or above {os.getcwd()}{R}")
        print("  This tool refuses to invent thresholds for a project that has not declared them.")
        return USAGE
    if "--precommit" in args:
        return precommit(root)
    cfg, defects = load_manifest_text(open(os.path.join(root, CONFIG_NAME)).read(), CONFIG_NAME)
    if cfg is None or defects:
        for m in defects:
            print(f"{RED}quality-ratchet: config defect — {m}{R}")
        return USAGE
    as_json = "--json" in args
    if "install-hook" in args:
        return install_hook(root)
    if "--run" in args:
        return do_run(root, cfg, as_json)
    if "--status" in args:
        return do_status(root, cfg, as_json)
    print_usage(); return USAGE


if __name__ == "__main__":
    sys.exit(main())
