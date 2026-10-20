#!/usr/bin/env python3
"""close_out_report.py -- render and lint the Phase 3G close-out report.

One definition of the report's shape, used to print it and to check it, so a session never
hand-formats the last thing the operator reads.

  python3 close_out_report.py --deliverable T --outcome done --well W --badly B \\
          --predecessor P --next N          print the report
  python3 close_out_report.py --check FILE  lint a message ('-' reads stdin); exit 1 on any breach
  python3 close_out_report.py --hook        Claude Code Stop / SessionStart hook: payload on stdin; exit 0 always

The mechanical facts (session, date, both scores, HEAD, uncommitted count, the gate-run citation)
come from the newest receipt in HANDOFFS.md and from git, never from the caller. The five texts the
caller supplies are judgment, each at most FIELD_MAX characters; longer input is refused, not cut.

The hook only ever adds a message: every uncertainty resolves to allow, and an internal error is
swallowed (exit 0, never 2), so it cannot trap a session. It keeps its state under the clone's .git/
(never tracked). Python 3 stdlib only.
"""
import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone

__version__ = "1.1.0"

HEAD_RE = re.compile(r"^## Close-out report: (S\S+) · (\d{4}-\d{2}-\d{2})$")
LABELS = ("Deliverable", "Record", "Self-assessment", "Predecessor handoff", "Next session")
CLOSING = "Session over."
FIELDS = ("deliverable", "outcome", "well", "badly", "predecessor", "next")
FIELD_MAX = 300   # characters per judgment text: one short paragraph
OUTCOME_MAX = 20  # the outcome is one word (DONE, PARTIAL, BLOCKED), not a paragraph
TOTAL_MAX = 2000  # bytes for the whole report: one screen
_FENCE = re.compile(r"^```handoff\n(.*?)^```$", re.S | re.M)
_KEY = re.compile(r"^([a-z_]+):\s*(.*)$")
_GATE = re.compile(r"quality_ratchet:\s*([^;\n]*?pass[^;\n]*?unmeasured)")


def parse_receipts(text):
    """Every ```handoff block in `text`, newest first as written, as {key: first-line value}."""
    out = []
    for m in _FENCE.finditer(text):
        d = {}
        for line in m.group(1).splitlines():
            k = _KEY.match(line)
            if k and k.group(1) not in d:
                d[k.group(1)] = k.group(2)
        out.append(d)
    return out


def _git(*args, cwd=None):
    r = subprocess.run(["git", *args], capture_output=True, text=True, cwd=cwd)
    return r.stdout.strip() if r.returncode == 0 else ""


def facts(new, prev, head, dirty):
    """The mechanical facts of one report. Pure: the property test feeds it every archived receipt."""
    g = _GATE.search(new.get("runtime_smoke", ""))
    return {"session": new.get("session", "?"), "date": new.get("date", "?"),
            "self": new.get("self_score", ""), "pred": new.get("predecessor_score", ""),
            "pred_id": (prev or {}).get("session", "?"), "head": head, "dirty": dirty,
            "gate": g.group(1) if g else "not cited"}


def live_facts(ledger="HANDOFFS.md", cwd="."):
    """Facts from the newest receipt in `ledger` and from git in `cwd`. Raises ValueError if unusable."""
    with open(ledger, encoding="utf-8") as f:
        r = parse_receipts(f.read())
    if not r:
        raise ValueError(f"no handoff receipt in {ledger}")
    if r[0].get("status") != "complete":
        raise ValueError(f"newest receipt ({r[0].get('session', '?')}) is {r[0].get('status', '?')}, not complete: "
                         "write the close-out receipt first")
    for k in ("self_score", "predecessor_score"):
        if not re.fullmatch(r"\d+", r[0].get(k, "")):
            raise ValueError(f"newest receipt has no numeric {k}")
    head = _git("rev-parse", "--short", "HEAD", cwd=cwd)
    if not head:
        raise ValueError(f"no git HEAD in {cwd}")
    dirty = len([x for x in _git("status", "--porcelain", cwd=cwd).splitlines() if x])
    return facts(r[0], r[1] if len(r) > 1 else {}, head, dirty)


def render(m, deliverable, outcome, well, badly, predecessor, nxt):
    """The report. Refuses (ValueError) any empty or over-long text, a pipe, or a newline; never truncates."""
    given = dict(zip(FIELDS, (deliverable, outcome, well, badly, predecessor, nxt)))
    for k, v in given.items():
        if not v or not v.strip():
            raise ValueError(f"--{k} is required")
        cap = OUTCOME_MAX if k == "outcome" else FIELD_MAX
        if len(v) > cap:
            raise ValueError(f"--{k} is {len(v)} characters; the most is {cap}")
        if "|" in v or "\n" in v:
            raise ValueError(f"--{k} may not contain a pipe or a newline")
    lines = [f"## Close-out report: {m['session']} · {m['date']}", "",
             f"**{LABELS[0]}:** {deliverable} — {outcome.upper()}", "",
             f"**{LABELS[1]}:** HEAD `{m['head']}` · {m['dirty']} uncommitted · gate run: {m['gate']}", "",
             f"**{LABELS[2]}:** {m['self']}/10 — went well: {well}; did not: {badly}", "",
             f"**{LABELS[3]} ({m['pred_id']}):** {m['pred']}/10 — {predecessor}", "",
             f"**{LABELS[4]}:** {nxt}", "", CLOSING]
    text = "\n".join(lines) + "\n"
    n = len(text.encode("utf-8"))
    if n > TOTAL_MAX:
        raise ValueError(f"the report is {n} bytes; the most is {TOTAL_MAX}")
    return text


def lint(text, m):
    """Every rule the report breaks, as strings; [] means clean. R1-R7 are the seven rules of the report's shape."""
    errs = []
    lines = text.rstrip("\n").split("\n")
    nonblank = [x for x in lines if x.strip()]
    h = HEAD_RE.match(nonblank[0]) if nonblank else None
    if not h:
        errs.append("R1 the first line is not '## Close-out report: S<N> · <date>'")
    elif (h.group(1), h.group(2)) != (m["session"], m["date"]):
        errs.append("R1 the heading names a different session or date than the newest receipt")
    pos = -1
    for lab in LABELS:
        i = next((n for n, x in enumerate(lines) if re.match(rf"^\*\*{re.escape(lab)}[^*]*:\*\*", x)), None)
        if i is None:
            errs.append(f"R2 missing label: {lab}")
        elif i < pos:
            errs.append(f"R2 label out of order: {lab}")
        else:
            pos = i
    if nonblank[-1:] != [CLOSING]:
        errs.append(f"R3 the last non-blank line is not '{CLOSING}'")
    if f"{m['self']}/10" not in text or f"{m['pred']}/10" not in text:
        errs.append("R4 a score differs from the newest receipt's")
    if f"`{m['head']}`" not in text:
        errs.append("R5 the HEAD sha is stale or absent")
    if "|" in text:
        errs.append("R6 a pipe character: tables do not wrap in a terminal")
    n = len(text.encode("utf-8"))
    if n > TOTAL_MAX:
        errs.append(f"R7 {n} bytes exceeds {TOTAL_MAX}")
    return errs


def _state_path(gitdir, kind, sid):
    """A per-session state file under .git/. The id is the harness's; keep it a file name, never a path."""
    return os.path.join(gitdir, f"close-out-{kind}-{re.sub(r'[^A-Za-z0-9._-]', '_', str(sid))[:100]}")


def _log(gitdir, sid, what):
    """One line per block, unclean retry or accepted report: the trace that shows, after the fact, what the hook did."""
    try:
        with open(os.path.join(gitdir, "close-out-report.log"), "a", encoding="utf-8") as f:
            f.write(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} {sid} {what}\n")
    except OSError:
        pass


def _ident(receipt):
    return [receipt.get("session", "?"), receipt.get("date", "?"), receipt.get("status", "?")]


def decide(payload):
    """The Stop / SessionStart decision: the block dict, or None to allow.

    SessionStart records the newest receipt once per session_id (resume and compact never overwrite it).
    A close-out is OWED when the newest receipt is complete and is not the one the session began with, or
    that one was not yet complete. Owed, a final message that lints clean is stamped with [HEAD, commits
    ahead of upstream, receipt hash]; anything else is blocked unless the harness is already on its one
    forced retry or the stamp shows nothing changed since the last report. May raise: the CLI swallows it.
    """
    event, sid, cwd = payload.get("hook_event_name"), payload["session_id"], payload["cwd"]
    top, gitdir = _git("rev-parse", "--show-toplevel", cwd=cwd), _git("rev-parse", "--absolute-git-dir", cwd=cwd)
    if not (top and gitdir) or event not in ("SessionStart", "Stop"):
        return None
    ledger = os.path.join(top, "HANDOFFS.md")
    with open(ledger, encoding="utf-8") as f:
        newest = parse_receipts(f.read())[0]
    base, stamp = _state_path(gitdir, "baseline", sid), _state_path(gitdir, "stamp", sid)
    if event == "SessionStart":
        try:
            with open(base, "x", encoding="utf-8") as f:
                json.dump(_ident(newest), f)
        except FileExistsError:
            pass
        return None
    if not os.path.exists(base) or "last_assistant_message" not in payload:
        return None  # hook installed mid-session, or a harness that does not send the message: fail quiet
    with open(base, encoding="utf-8") as f:
        began = json.load(f)
    if newest.get("status") != "complete" or (began[:2] == _ident(newest)[:2] and began[2] == "complete"):
        return None  # no close-out has happened in this session
    m = live_facts(ledger, top)
    state = [m["head"], _git("rev-list", "--count", "@{upstream}..HEAD", cwd=top) or "0",
             hashlib.sha256(json.dumps(newest, sort_keys=True).encode()).hexdigest()[:12]]
    errs = lint(payload["last_assistant_message"], m)
    if not errs:
        with open(stamp, "w", encoding="utf-8") as f:
            json.dump(state, f)
        _log(gitdir, sid, "reported")
        return None
    codes = ",".join(dict.fromkeys(e.split()[0] for e in errs))
    if payload.get("stop_hook_active"):
        _log(gitdir, sid, f"retry-unclean {codes}")
        return None  # the harness allows ONE forced retry per Stop chain
    if os.path.exists(stamp):
        with open(stamp, encoding="utf-8") as f:
            if json.load(f) == state:
                return None  # a report was issued at this state and nothing has changed since
    _log(gitdir, sid, f"blocked {codes}")
    cmd = " ".join(["python3", shlex.quote(os.path.abspath(__file__)), "--ledger", shlex.quote(ledger),
                    "--cwd", shlex.quote(top)]) + (" --deliverable '...' --outcome done|partial|blocked "
                                                  "--well '...' --badly '...' --predecessor '...' --next '...'")
    return {"decision": "block", "reason":
            f"Close-out is complete but your final message is not the Phase 3G report ({'; '.join(errs[:3])}). "
            f"Run: {cmd} (each text at most {FIELD_MAX} characters, no '|'; the outcome is one word) and print "
            "its output verbatim as your entire final message, with nothing before or after it."}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--ledger", default="HANDOFFS.md", help="the receipt ledger (default HANDOFFS.md)")
    ap.add_argument("--cwd", default=".", help="the repository whose HEAD the report names")
    ap.add_argument("--check", metavar="FILE", help="lint FILE ('-' = stdin) instead of printing a report")
    ap.add_argument("--hook", action="store_true", help="act as a Claude Code Stop / SessionStart hook (stdin payload)")
    for f in FIELDS:
        ap.add_argument("--" + f)
    a = ap.parse_args(argv)
    if a.hook:
        try:
            out = decide(json.load(sys.stdin))
        except Exception:  # fail quiet: an error must never block a session, and exit 2 would
            out = None
        if out:
            print(json.dumps(out))
        return 0
    try:
        m = live_facts(a.ledger, a.cwd)
    except (OSError, ValueError) as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    if a.check:
        text = sys.stdin.read() if a.check == "-" else open(a.check, encoding="utf-8").read()
        errs = lint(text, m)
        print("\n".join(errs) if errs else "OK")
        return 1 if errs else 0
    try:
        sys.stdout.write(render(m, *(getattr(a, f) or "" for f in FIELDS)))
    except ValueError as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
