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
from datetime import datetime, timedelta, timezone
from pathlib import Path

VERSION = "1.2.0"
CONFIG_NAME = ".context-budget.json"
HISTORY_NAME = ".context-budget-history.jsonl"

R = "\033[0m"; B = "\033[1m"; D = "\033[2m"
RED = "\033[31m"; YEL = "\033[33m"; GRN = "\033[32m"; CYN = "\033[36m"
W = 74

CLEAN, WARN, BREACH, USAGE = 0, 1, 2, 3

# === THE READ CAP, AND WHY THE CEILING IS DENOMINATED IN TOKENS ===
#
# A size ceiling exists to keep a file readable. "Readable" is denominated in TOKENS --
# the agent read tool refuses a range over READ_CAP_TOKENS -- while a ceiling written in
# BYTES is `tokens x density`, and density is a property of the CONTENT. So every edit
# that changes how densely the file is written silently moves a byte ceiling, and nothing
# goes red. Measured on the authoring fork of this tool: a declared 73,728 B ceiling
# certified `ok` a file the read tool REFUSES at 25,486 tokens, and four of five declared
# ceilings converted to more than the cap. Declaring the ceiling in tokens makes that
# class of defect unrepresentable rather than merely fixed once.
READ_CAP_TOKENS = 25_000

# The FLOOR of a measured 2.2705-3.0300 B/token band, not its mean. Dividing bytes by the
# floor MAXIMISES the token estimate, so a ceiling derived from it is conservative: it can
# never certify an unreadable file as fine. Direction matters here and is easy to invert --
# a LOWER B/token yields a HIGHER token count. Only ever use this to DERIVE a ceiling when
# no measured density is available; never as a measurement of a file you can meter.
MIN_BYTES_PER_TOKEN = 2.27

# The cap re-denominated onto bytes: 25,000 x 2.27 = 56,750 B. COMPUTED, never written --
# the same expression starter-kit/methodology_trim.py:129 uses, so the two tools cannot
# drift apart by someone editing a literal in one of them. It answers "does ONE Read
# deliver this whole file?", which is a different question from the per-call token limit
# and is why both constants exist rather than one.
READ_CAP_BYTES = int(READ_CAP_TOKENS * MIN_BYTES_PER_TOKEN)

# A file-size ceiling only bites when the file is read WHOLE. Measured over 80 transcripts,
# one such file was read whole once and in part 243 times, and a partial read returns whole
# ROWS: the cost was per-row, the guard was per-file, and a budget on the wrong unit is not
# conservative, it is unmeasured. So the read cap is applied ONLY to classes the protocol
# orders read whole. An on-demand file gets no token verdict at all -- its budget belongs
# on the unit actually read (a row, a record, a section).
WHOLE_READ_CLASSES = ("resident", "read-mandated", "read-set")

# "read-set" is the Phase 0 MANDATORY READ -- the runner plus the safeguards file, the pair
# every session is ordered to read IN FULL before any work. It is a separate class from
# "read-mandated" because a project's read-mandated ledgers are typically far larger than the
# procedure pair, and a total over the union of the two partitions nothing. Adding it here is
# additive: no shipped config declares this class yet, so no adopter's verdict moves until
# they declare it themselves.

# A density is measured against a particular content. Once the file has drifted this far
# from the size it was measured at, the derived ceiling is no longer justified: report a
# warn rather than a confident ok, and say so. This is the signal whose absence let a
# stale ceiling report `ok` for two days after the compaction that invalidated it.
DENSITY_DRIFT_WARN = 0.25


def file_density(cfg, spec):
    """(bytes_per_token, source). Per-file measured beats the config global beats the
    floor. Returns the source so output can say which, rather than presenting a derived
    number and a measured one in the same voice."""
    d = spec.get("bytes_per_token")
    if d:
        return float(d), "measured"
    g = (cfg or {}).get("bytes_per_token")
    if g:
        return float(g), "config"
    return MIN_BYTES_PER_TOKEN, "floor"


def token_ceiling(cfg, spec):
    """(max_tokens, derived). An explicit max_tokens governs. Otherwise derive one from
    max_bytes at the conservative floor so an un-migrated config keeps working AND gains
    the guard with no edit. Either way the result is clamped at the read cap: a ceiling
    above it cannot be satisfied by any file, so honouring it would be honouring nonsense.
    None when the spec declares no ceiling of either kind."""
    cap = int((cfg or {}).get("read_cap_tokens", READ_CAP_TOKENS))
    mt = spec.get("max_tokens")
    if mt:
        return min(int(mt), cap), False
    mb = spec.get("max_bytes")
    if mb:
        return min(int(mb / MIN_BYTES_PER_TOKEN), cap), True
    return None, False


def class_spec(cfg, name):
    """The declared budget for one class, or {} when the config declares none.

    `cfg["classes"]["resident"]` was a DIRECT key access at two sites, so a config that
    declares no `classes` key raised KeyError -- and an adopter's hand-written config is
    exactly the one that will lack it. Both sites move together or the crash relocates
    rather than closing. Returning {} rather than None keeps every caller a `.get()`.
    """
    return ((cfg or {}).get("classes") or {}).get(name) or {}


def framework_share(cfg):
    """(share, reserve, cap) — the DERIVED ceiling for a read set, and its inputs.

        framework_share := READ_CAP_BYTES - adopter_reserve_bytes

    where READ_CAP_BYTES is this module's constant unless the config overrides
    `read_cap_tokens`, in which case the cap is re-derived from it at the same floor and
    returned as `cap_bytes` so callers report the number in force, not the constant.

    THE CEILING IS DERIVED, NOT PICKED. A number someone typed drifts from the cap it is
    supposed to be a partition of and nothing notices; a number computed from the cap
    cannot. `adopter_reserve_bytes` is the share of one read reserved for the ADOPTER's own
    always-read files, which the framework does not own and cannot size. Reserve zero is
    the honest first ship: it credits the framework with the whole read, which is the
    LEAST favourable assumption for the framework's own numbers, so a shortfall measured
    at reserve zero cannot be blamed on the reserve.
    """
    # READ_CAP_BYTES is the default, so the identity in the docstring is the one that
    # runs. A project that overrides `read_cap_tokens` gets its own cap re-derived at the
    # same floor -- reported as `cap_bytes` so a caller can name the number actually in
    # force rather than printing the module constant beside a different value.
    cap = (cfg or {}).get("read_cap_tokens")
    cap_bytes = READ_CAP_BYTES if cap is None else int(int(cap) * MIN_BYTES_PER_TOKEN)
    reserve = int((cfg or {}).get("adopter_reserve_bytes", 0) or 0)
    return cap_bytes - reserve, reserve, cap_bytes


def class_ceiling(cfg, spec):
    """(ceiling, derived). A class either DECLARES total_bytes or DERIVES it from the cap.

    Returning `derived` lets a caller say which it is rather than presenting a computed
    number and a typed one in the same voice — the same distinction file_density() draws
    between a measured density and the floor."""
    if (spec or {}).get("derive_from_read_cap"):
        share, _reserve, _cap = framework_share(cfg)
        return share, True
    return (spec or {}).get("total_bytes"), False


def class_totals(cfg, results):
    """[{class, bytes, total_bytes, warn_bytes, status}] for every DECLARED class.

    Two per-file ceilings do not sum. Bytes can move from SAFEGUARDS.md into
    SESSION_RUNNER.md with both rows green while the Phase 0 read is unchanged, so the
    thing the cap is actually about -- the total a session must read -- goes unguarded
    unless something totals it. This is that something, and it is generalised over N
    classes rather than hardcoded to `resident`: a project whose read set is a different
    class, or which declares three, gets the same arm with no code change.

    ORDER IS DETERMINISTIC AND `resident` LEADS. Not dict order, which would make the
    output depend on how the config happened to be typed; and resident first because that
    is where it has always printed, which is what keeps the rendered line byte-identical
    for every config that declares only that one.

    A class DECLARED with no member files totals 0 rather than vanishing -- a class that
    silently disappears when its files are renamed is a gate that stops gating without
    saying so. Rows whose path is parenthesised are this function's own output from an
    earlier call and are excluded, or a second call would count them twice.
    """
    declared = (cfg or {}).get("classes") or {}
    # `resident` is always reported, declared or not. The tool computes it unconditionally
    # -- it is the header's number and the growth-run series' subject -- so it always HAS a
    # total; whether a CEILING was declared for it is a separate question, answered by
    # total_bytes being None. Dropping the line when the config omits the class would make
    # a config that declares nothing quieter than one that declares a ceiling it passes.
    names = sorted(set(declared) | {"resident"}, key=lambda n: (n != "resident", n))
    out = []
    for name in names:
        spec = class_spec(cfg, name)
        total = sum(r.get("bytes", 0) for r in results
                    if r.get("class") == name and not r.get("aggregate"))
        ceil, _derived = class_ceiling(cfg, spec)
        warn = spec.get("warn_bytes")
        status = "ok"
        # `is not None`, never truthiness: a DECLARED total_bytes of 0 is a ceiling that
        # nothing can satisfy, and reading it as "undeclared" disables the gate while the
        # config plainly declares one.
        if ceil is not None and total > ceil:
            status = "over"
        elif warn is not None and total > warn:
            status = "warn"
        out.append({"class": name, "bytes": total, "total_bytes": ceil,
                    "warn_bytes": warn, "status": status})
    return out


def config_defects(cfg, defaults=None):
    """Ceilings that cannot be satisfied by any file. Reported, never silently clamped --
    a clamp would fix the symptom and leave the operator believing a number that is not
    in force. Returns a list of human-readable strings; empty means clean."""
    cap = int((defaults or cfg or {}).get("read_cap_tokens", READ_CAP_TOKENS))
    out = []
    for spec in (cfg or {}).get("files", []):
        mt = spec.get("max_tokens")
        if mt and int(mt) > cap:
            out.append(f"{spec.get('path')}: max_tokens {int(mt):,} exceeds the "
                       f"{cap:,}-token read cap by {int(mt)-cap:,} — no file can satisfy it")

    # --- the reserve identity, checked where it can actually fail --------------------
    # framework_share := READ_CAP_BYTES - adopter_reserve_bytes. NOT a module-scope
    # assert: a module-scope assert runs at IMPORT, so it would fire in every test that
    # merely imports this file, and a mutant that violated it would die with a traceback
    # BEFORE the code under test ran -- scored killed by the crash rather than by the
    # behaviour. Checked here, per config, at run time, where a wrong value is reachable.
    share, reserve, cap_bytes = framework_share(defaults or cfg or {})
    if reserve < 0:
        out.append(f"adopter_reserve_bytes {reserve:,} is negative — a reserve is a share "
                   f"of the read cap, not a credit against it")
    elif share <= 0:
        out.append(f"adopter_reserve_bytes {reserve:,} leaves a framework share of "
                   f"{share:,} B against a {cap_bytes:,} B read cap — no file can satisfy "
                   f"a ceiling of zero or less")
    for name, cspec in sorted(((cfg or {}).get("classes") or {}).items()):
        cspec = cspec or {}
        if not cspec.get("derive_from_read_cap"):
            continue
        written = cspec.get("total_bytes")
        if written is not None and int(written) != share:
            # Reported, never silently honoured OR silently overwritten: the derived value
            # is what is in force, and an operator reading the config would otherwise
            # believe the number they typed.
            out.append(f"class {name}: total_bytes {int(written):,} disagrees with the "
                       f"derived framework share {share:,} B "
                       f"(read cap {cap_bytes:,} B - adopter_reserve_bytes "
                       f"{reserve:,}) — the DERIVED value is in force, not the written one")
    return out



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


def blob_bytes(root, rev):
    """Size of a git blob in BYTES, asked of git. None when `rev` does not resolve.

    NEVER `len(run(["git", "show", rev]).encode())`. run() returns `p.stdout.strip()`,
    so any content ending in a newline measures one byte short: on the authoring fork a
    54,363 B starter-kit/SESSION_RUNNER.md came back as 54,362 from that expression. A size
    gate that miscounts bytes is the wrong thing to build on -- and the error is silent,
    self-consistent, and in the direction that makes an over-budget file look smaller.

    `git cat-file -s` reports the object's recorded size and never decodes it, so it is
    also correct for content that is not valid UTF-8, where `text=True` would have
    replaced bytes and changed the length. Same idiom as size_history() already uses.
    """
    rc, size, _ = run(["git", "cat-file", "-s", rev], cwd=root)
    return int(size) if rc == 0 and size.isdigit() else None


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

def measure_file(root, spec, cfg=None):
    """One budgeted file. status ∈ ok | warn | over | unmeasured.

    `cfg` is optional so existing callers keep working; without it the token arm
    falls back to the conservative floor rather than silently not running."""
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
    out["max_lines"] = spec.get("max_lines")
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

    # --- the token arm: the unit the read cap is actually denominated in ---------
    # Applied ONLY to classes the protocol orders read WHOLE (WHOLE_READ_CLASSES). An
    # on-demand file is read in part, so its whole-file token count is not the cost
    # it pays and is deliberately not computed -- a verdict on the wrong unit is
    # worse than no verdict, because it reads as though someone measured something.
    if out["class"] in WHOLE_READ_CLASSES:
        max_tok, derived = token_ceiling(cfg, spec)
        if max_tok:
            bpt, dsrc = file_density(cfg, spec)
            out["tokens"] = int(out["bytes"] / bpt)
            out["max_tokens"] = max_tok
            out["density"] = bpt
            out["density_source"] = dsrc
            out["ceiling_derived"] = derived
            if out["tokens"] > max_tok:
                over(f"≈{out['tokens']:,} tokens exceeds the {max_tok:,}-token ceiling by "
                     f"{out['tokens']-max_tok:,} — at {bpt:.4f} B/token ({dsrc})"
                     + (f", derived from max_bytes at the {MIN_BYTES_PER_TOKEN} floor"
                        if derived else ""), "tokens")
            # A density is only justified near the size it was measured at. Past the
            # drift threshold say so, rather than reporting an ok nobody can defend.
            mb = spec.get("measured_bytes")
            if mb and out["status"] == "ok":
                drift = abs(out["bytes"] - int(mb)) / float(mb)
                if drift > DENSITY_DRIFT_WARN:
                    out["findings"].append({"kind": "density", "msg":
                        f"density {bpt:.4f} B/token was measured at {int(mb):,} B; the file "
                        f"is now {out['bytes']:,} B ({drift*100:.0f}% drift). The token "
                        f"figure above is provisional — re-measure before trusting it."})
                    out["status"] = "warn"

    # structure: a declared pattern matching FEWER records than expected is an
    # instrument failure, not a pass.
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
  ("Move", "Relocate the section into the document that owns it — a module- or "
           "subsystem-level doc a session opens only once it knows the task. Resident "
           "context is for what a session needs BEFORE it knows the task."),
  ("Compute", "Replace any hand-maintained count or list with the command that "
              "produces it. A count written into a read-often file is a future lie — "
              "on the project this was measured, 10 of 11 rows of one such table were "
              "wrong by the time anyone checked."),
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


def render(root, results, synced, run_len, run_hit, cfg, snapshot, totals=None,
           defects=()):
    print(f"\n{D}{'─'*W}{R}")
    worst = "ok"
    order = {"ok": 0, "unmeasured": 1, "warn": 2, "instrument-failed": 3, "over": 4}
    for r in list(results) + list(synced) + list(totals or []):
        if order[r["status"]] > order[worst]:
            worst = r["status"]
    # A config defect is an instrument failure and main() exits BREACH on one, so the
    # headline has to say so. It was computed over `results + synced` alone while defects
    # were deliberately kept out of `results`, which put a green OK on the most-read line
    # of a run that exits 2. The class totals join for the same reason: a class past its
    # warn line had its status computed and then read by nothing.
    if defects and order["instrument-failed"] > order[worst]:
        worst = "instrument-failed"
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
        size, ceil = ledger_dimension(r)
        cc = status_colour(r["status"])
        print(f"  {name:<34s}{size:>12s}{str(ceil):>12s}  {cc}{r['status']}{R}")
    for r in synced:
        cc = status_colour(r["status"])
        print(f"  {short(r['path']):<34s}{'synced':>12s}{'canonical':>12s}  {cc}{r['status']}{R}")

    # One total per DECLARED class, resident first. For a config that declares only
    # resident -- which is every instrumented adopter today -- this loop emits exactly the
    # one line it always did, byte for byte, including the growth-run suffix. Only the
    # undeclared-ceiling case is new, and it says so rather than crashing.
    print(f"{D}{'─'*W}{R}")
    for ct in (totals if totals is not None else class_totals(cfg, results)):
        ceil = ct["total_bytes"]
        ceil_s = f"{ceil:,} B ceiling" if ceil else "no ceiling declared"
        # The growth run is a series over `resident_bytes` in the history file, so it is
        # reported on the resident row and nowhere else. Printing it beside a class it was
        # not computed over would put a true number in a place that makes it false.
        run_s = (f"   {D}growth run {run_len}/{cfg.get('growth_run', 10)}{R}"
                 if ct["class"] == "resident" else "")
        # The status is PRINTED, not merely computed. A class between its warn line and
        # its ceiling used to set status="warn" that nothing read: render showed only
        # bytes and ceiling, and main()'s exit code saw class rows only when they were
        # OVER. The declared warn_bytes therefore produced no warning anywhere, in a tool
        # whose whole subject is numbers that are declared and not honoured.
        st = "" if ct["status"] == "ok" else f"  {status_colour(ct['status'])}{ct['status']}{R}"
        print(f"  {ct['class']} total {B}{ct['bytes']:,} B{R} / {ceil_s}{st}{run_s}")

    # Config defects print SEPARATELY from file findings and are not a results row: a row
    # must be able to show the figure behind its own verdict (ledger_dimension), and a
    # ceiling that cannot be satisfied has no size to show. They are also the worst thing
    # on screen -- an unsatisfiable ceiling means every verdict below it is measured
    # against a number that is not in force -- so they print first.
    if defects:
        print(f"{D}{'─'*W}{R}")
        print(f"  {RED}{B}config defect{R} — a ceiling that is not in force")
        for m in defects:
            print(f"    · {m}")

    findings = [(r, f) for r in results + synced for f in r["findings"]]
    if not findings and not run_hit and not defects:
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


def ledger_dimension(r):
    """(size, ceiling) for one ledger row — reported in the dimension that ACTUALLY FIRED.

    A read-mandated file now defaults to BYTES, and that changed on 2026-08-26.
    It defaulted to lines because lines were the unit the surrounding trim rule was written
    in -- never because the cap came in lines. It does not: the agent read cap is
    TOKEN-denominated, and tokens track bytes, not lines. Measured across the fleet, the
    B/line spread over these very files is 8.6x against 1.33x for B/token, so a line figure
    is the one least able to explain a read-cap verdict. The trim rule has since been
    re-denominated onto bytes as well (methodology_trim.py READ_CAP_BYTES), so the default
    here and the unit the rule is written in agree again -- on the other axis.
    (Reproduction: rmsharp/methodology, docs/planning/read-cap-premise-correction-plan.md, App. A.)

    The BYTE ceiling was already able to be the one that fires, and a row reading
    `359 ln / 1,200 ln  over` then pointed at a ceiling that did not, while the 72,449 B
    behind the verdict appeared only in the prose further down. A ledger row that cannot
    show the figure behind its own verdict is precisely the read-past-it failure this tool
    exists to interrupt.

    The first size finding still decides the dimension; only the nothing-fired default
    moved. `bytes` is appended before `lines` in measure_file, so a file over both reports
    bytes. A `max_lines` ceiling that fires is still reported in lines -- the ceilings are
    not being removed here, only the default when neither has fired.

    A TOKEN ceiling can now fire too, and when it does the row reports tokens -- the unit
    this docstring already argued the cap is denominated in, back when bytes were the best
    available proxy for it. Bytes are appended before tokens in measure_file, so a file
    over both still reports bytes; tokens surface exactly in the case bytes cannot explain,
    which is a file UNDER its byte ceiling and OVER the read cap. That case is not
    hypothetical: it is the shipped defect this arm was added for.
    """
    fired = next((f["kind"] for f in r.get("findings", [])
                  if f["kind"] in ("bytes", "lines", "tokens")), None)
    if fired == "tokens":
        return (f"≈{r['tokens']:,} tok",
                f"{r['max_tokens']:,} tok" if r.get("max_tokens") else "—")
    if (fired or "bytes") == "lines":
        return (f"{r['lines']:,} ln",
                f"{r['max_lines']:,} ln" if r.get("max_lines") else "—")
    return (f"{r['bytes']:,} B",
            f"{r['max_bytes']:,} B" if r.get("max_bytes") else "—")


# === CALIBRATE ===

# A fit whose regressor explains less than half the variance in opening context is
# not a measurement of bytes-per-token — it is the slope of a cloud. The floor is
# the majority-of-variance line, chosen because it is statable without reference to
# any one project's result rather than tuned to admit a particular fit. Override per
# project with "calibrate_min_r2" in the config.
MIN_R2 = 0.50

_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})"
                  r"(?:\.(\d+))?(Z|z|[+-]\d{2}:?\d{2})?$")


def parse_iso(s):
    """ISO-8601 → aware datetime, or None if it does not parse.

    Timestamps reach this tool from two sources that do not agree on format: git
    `%cI` emits a numeric offset that moves with the season (`-05:00` and `-04:00`
    both occur in the authoring repository's history), while session transcripts end in
    `Z`. Ordering those AS STRINGS is not chronological — `2026-08-01T19:42:50-05:00`
    is really `2026-08-02T00:42:50Z` but string-sorts *before* `2026-08-01T21:25:28Z`,
    which scores that session against the wrong file size. Every comparison in this
    section is therefore between aware datetimes.

    A timestamp carrying no offset at all is read as UTC. That is an assumption, not
    a measurement — neither real source emits one — and it is stated here rather than
    left to whatever a comparison happened to do with it.
    """
    m = _ISO.match(s.strip()) if s else None
    if not m:
        return None
    y, mo, d, h, mi, sec, frac, off = m.groups()
    micro = int(frac.ljust(6, "0")[:6]) if frac else 0
    tz = timezone.utc
    if off and off not in ("Z", "z"):
        digits = off[1:].replace(":", "")
        tz = timezone((1 if off[0] == "+" else -1)
                      * timedelta(hours=int(digits[:2]), minutes=int(digits[2:4])))
    try:
        return datetime(int(y), int(mo), int(d), int(h), int(mi), int(sec), micro, tz)
    except ValueError:
        return None                      # e.g. month 13 — matched the shape, not a date


def size_history(root, target, first_parent=True):
    """(history, skipped, error) — `target`'s size over time on ONE line of development.

    `git log -- <path>` walks ALL merged ancestry. On a repository that has merged
    another lineage of the same file — every fork that syncs an upstream, which is
    the workflow this methodology documents — two unrelated size series interleave
    by commit date and "the size of X at time T" stops being a function. Measured on
    this framework's own fork: all-ancestry yields 54 size records against
    `--first-parent`'s 42, and the fit's R² falls from 0.81 to 0.05. So this asks the
    question actually being asked: how large was this file, *here*, on this branch.

    `first_parent=False` exists only so the regression test can exhibit that defect
    against a fixture repository. Nothing in the tool passes it.

    `skipped` counts commits whose timestamp did not parse, so a silently shrinking
    sample is reported rather than inferred.
    """
    argv = ["git", "log", "--format=%H %cI"]
    if first_parent:
        argv.append("--first-parent")
    argv += ["--", target]
    rc, log, err = run(argv, cwd=root)
    if rc:
        return None, 0, err
    hist, skipped = [], 0
    for line in log.split("\n"):
        if not line.strip():
            continue
        sha, _, iso = line.partition(" ")
        when = parse_iso(iso)
        if when is None:
            skipped += 1
            continue
        rc2, size, _ = run(["git", "cat-file", "-s", f"{sha}:{target}"], cwd=root)
        if rc2 == 0 and size.isdigit():
            hist.append((when, int(size)))
    hist.sort(key=lambda t: t[0])
    return hist, skipped, None


def size_at(hist, when):
    """The size in effect at `when` — the last record at or before it, not the nearest.

    Requires `hist` chronologically sorted, which is why it may stop at the first
    record past `when`: that early exit is only correct under the ordering
    size_history establishes, and breaking it would break this.
    """
    best = None
    for t, size in hist:
        if t <= when:
            best = size
        else:
            break
    return best


def linfit(pts):
    """Ordinary least squares over [(x, y)] → (slope, intercept, r2).

    Returns None when the regressor has no variance: no line is determined, and
    inventing one would be the same error this tool exists to catch. `r2` is None —
    never 0.0, never 1.0 — when the response has no variance to explain, because an
    undefined statistic rendered as a number is indistinguishable from a measured one.
    """
    n = len(pts)
    sx = sum(p[0] for p in pts); sy = sum(p[1] for p in pts)
    sxx = sum(p[0]**2 for p in pts); sxy = sum(p[0]*p[1] for p in pts)
    den = n*sxx - sx*sx
    if den == 0:
        return None
    slope = (n*sxy - sx*sy) / den
    inter = (sy - slope*sx) / n
    my = sy/n
    ss_tot = sum((p[1]-my)**2 for p in pts)
    ss_res = sum((p[1] - (inter + slope*p[0]))**2 for p in pts)
    return slope, inter, (1 - ss_res/ss_tot if ss_tot else None)


def calibration_verdict(slope, r2, floor):
    """None if the fit supports a bytes-per-token constant, else why it does not.

    Separated from the printing so it can be observed refusing. The slope test is
    not redundant with the R² test: a tight fit with a NEGATIVE slope has a high R²
    and still means "more bytes, fewer tokens", whose reciprocal is not a conversion.
    """
    if slope is None or slope <= 0:
        return (f"the slope is {slope:.4f} — more bytes fitting FEWER tokens is not a "
                f"conversion, and its reciprocal is not bytes-per-token")
    if r2 is None:
        return "R² is undefined — opening context never varied, so nothing was explained"
    if r2 < floor:
        return (f"R² = {r2:.4f} is below the {floor:.2f} floor — the regressor explains "
                f"{r2*100:.0f}% of the variance in opening context")
    return None


def calibrate(root, cfg):
    """Re-derive bytes-per-token by regressing each session's opening context against
    the size of the resident file at that moment. Writes nothing. A tool whose thesis
    is 'store a fact as the command that produces it' must not carry its own constant
    as an unmeasured literal.

    It must equally not hand back a constant it cannot support. Below the floor the
    fit is printed in full and the derived number is REFUSED: printing `1/slope`
    beside R² = 0.05 with the same confidence as R² = 0.81 is exactly the
    read-past-it failure (FM #28) this tool was built to interrupt, committed by the
    tool itself. An adopter has no second instrument to catch it with.
    """
    slug = "-" + str(Path(root).resolve()).strip("/").replace("/", "-")
    tdir = Path.home() / ".claude" / "projects" / slug
    if not tdir.exists():
        print(f"{CYN}no transcripts at {tdir} — cannot calibrate{R}")
        return WARN
    target = cfg.get("calibrate_against", "CLAUDE.md")
    hist, skipped, err = size_history(root, target)
    if hist is None:
        print(f"{RED}git log failed: {err}{R}")
        return USAGE
    if skipped:
        print(f"{YEL}{skipped} commit timestamp(s) for {target} did not parse and were "
              f"dropped from the history{R}")
    if len(hist) < 3:
        print(f"{CYN}only {len(hist)} sizes of {target} in history — not enough{R}")
        return WARN

    pts, undated = [], 0
    for f in sorted(tdir.glob("*.jsonl")):
        first_ts = first_ctx = None
        try:
            # `with`, because this loop BREAKS out on the first usage record — one
            # descriptor per transcript was being left to the garbage collector, and a
            # project with hundreds of them can exhaust the process limit before the fit
            # is ever reached.
            with open(f, errors="ignore") as fh:
                for line in fh:
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
                        first_ctx = (u.get("input_tokens", 0)
                                     + u.get("cache_read_input_tokens", 0)
                                     + u.get("cache_creation_input_tokens", 0))
                        break
        except OSError:
            continue
        if first_ts and first_ctx:
            when = parse_iso(first_ts)
            if when is None:
                undated += 1
                continue
            s = size_at(hist, when)
            if s:
                pts.append((s, first_ctx))
    if undated:
        print(f"{YEL}{undated} transcript(s) had an unparseable opening timestamp and were "
              f"dropped{R}")
    if len(pts) < 4:
        print(f"{CYN}only {len(pts)} usable sessions — not enough to fit{R}")
        return WARN
    fitted = linfit(pts)
    if fitted is None:
        print(f"{CYN}no variation in {target} size across sessions — cannot fit{R}")
        return WARN
    slope, inter, r2 = fitted

    print(f"\n  n={len(pts)} sessions, regressor = bytes({target}), "
          f"{len(hist)} sizes on this branch")
    print(f"  opening_tokens ≈ {inter:,.0f} + {slope:.4f} × bytes      "
          f"R² = {'undefined' if r2 is None else f'{r2:.4f}'}")

    floor = cfg.get("calibrate_min_r2", MIN_R2)
    refused = calibration_verdict(slope, r2, floor)
    if refused:
        print(f"\n  {RED}{B}no constant recommended{R} — {refused},")
        print(f"  so 1/slope is an artefact of the scatter rather than a measurement.")
        print(f"\n  {B}What to check, cheapest first:{R}")
        print(f"    1. Is {target} the right regressor? It has to be BOTH auto-loaded into")
        print(f"       every session AND actually varying in size over the window. Set")
        print(f'       "calibrate_against" in {CONFIG_NAME}.')
        print(f"    2. Does this project's opening context come mostly from elsewhere —")
        print(f"       other resident files, tool schemas, agent-level memory? Then no")
        print(f"       single file's byte count will track it, and none should be expected to.")
        print(f"    3. Did {target} really vary here? {len(hist)} recorded sizes on this branch.")
        print(f"\n  {D}the fit is printed above in full so you can judge it yourself; "
              f"nothing was written{R}\n")
        return WARN

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
    prevents its own remedy. The same rule governs the class-aggregate arm below."""
    bad = []
    # Surfaced here too, or the hook enforces ceilings while silently disagreeing with the
    # config about what they are. Printed rather than added to `bad`: a config defect is
    # not a file that grew, and the relative rule has nothing to say about it.
    for m in config_defects(cfg):
        print(f"{YEL}context-budget: config defect — {m}{R}")
    staged, head = {}, {}
    for spec in cfg.get("files", []):
        if os.path.isabs(spec["path"]):
            continue  # files outside the repo are not part of this commit
        # A COMMIT CONTAINS THE INDEX, NOT THE WORKTREE, and this loop must be driven by
        # the index or the aggregate below is wrong in BOTH directions. The worktree test
        # that used to stand here (`if not os.path.exists(path): continue`) ran BEFORE any
        # bookkeeping, which meant:
        #   * a member removed by `git rm` was dropped from the HEAD side as well as the
        #     staged side, so deleting a member -- the most direct remedy for an
        #     over-budget class -- was not credited and the survivors read as pure growth.
        #     Measured: a 4,200 -> 1,300 B reduction was REFUSED, reported as 1,200 -> 1,300.
        #   * a member staged with content but absent from the worktree was skipped
        #     entirely and counted as ZERO, so an index holding 1,800 B against a 1,000 B
        #     ceiling PASSED.
        # Both are the same line, and both are the failure the relative rule exists to
        # prevent. `git cat-file -s :path` reads the INDEX and does not care whether the
        # worktree copy still exists, which is exactly the question a pre-commit hook asks.
        new = blob_bytes(root, f":{spec['path']}")
        old = blob_bytes(root, f"HEAD:{spec['path']}")
        if new is None and old is None:
            continue  # not tracked on either side — nothing this commit can be judged on
        cls = spec.get("class", "resident")
        staged[cls] = staged.get(cls, 0) + (new or 0)
        if new is None:
            continue  # deleted: there is no per-file verdict to give, only the aggregate
        old = old or 0
        ceil = spec.get("max_bytes")
        if ceil and new > ceil and new > old:
            bad.append((spec["path"], old, new, ceil, "B", f"{ceil:,} B"))
            continue
        # The token ceiling gates here too, or the tool reports in one unit and refuses
        # in another. Same relative rule: a commit that SHRINKS an over-budget file is
        # never blocked, so the gate can never prevent its own remedy.
        if spec.get("class", "resident") in WHOLE_READ_CLASSES:
            max_tok, _derived = token_ceiling(cfg, spec)
            if max_tok:
                bpt, _src = file_density(cfg, spec)
                ntok, otok = int(new / bpt), int(old / bpt)
                if ntok > max_tok and ntok > otok:
                    bad.append((spec["path"], otok, ntok, max_tok, "tok",
                                f"{max_tok:,} tok"))

    # THE BASELINE IS HEAD'S OWN DECLARATION, NOT TODAY'S.
    # `head` must answer "what did this class contain at HEAD?", and only HEAD's config can
    # say. Summing HEAD blob sizes over the CURRENT member list silently drops the bytes of
    # any member that LEAVES the class in this commit — renamed with the config updated to
    # match, or reclassified — so a rename that shrinks a class read as pure growth and was
    # refused. Falls back to the current list when HEAD has no config (the first commit that
    # adds one), which is the only case where there is no prior declaration to consult.
    head = {}
    rc_cfg, head_cfg_raw, _ = run(["git", "show", f"HEAD:{CONFIG_NAME}"], cwd=root)
    head_files = cfg.get("files", [])
    if rc_cfg == 0:
        try:
            head_files = (json.loads(head_cfg_raw) or {}).get("files", head_files)
        except ValueError:
            pass          # unparseable HEAD config — fall back rather than guess
    for spec in head_files:
        if os.path.isabs(spec.get("path", "")):
            continue
        prev = blob_bytes(root, f"HEAD:{spec['path']}")
        if prev is None:
            continue
        cls = spec.get("class", "resident")
        head[cls] = head.get(cls, 0) + prev

    # --- the class-aggregate arm ---------------------------------------------------
    # PER-FILE CEILINGS DO NOT SUM. Bytes can move out of SAFEGUARDS.md and into
    # SESSION_RUNNER.md leaving both rows green while the Phase 0 read is unchanged, so
    # the quantity the cap is actually about goes unguarded unless something totals it.
    # main() reports that total; without this arm the tool would ship an aggregate that
    # REPORTS AND CANNOT REFUSE, which is half a gate. Same relative rule throughout.
    for name, cspec in sorted((cfg.get("classes") or {}).items()):
        ceil, _derived = class_ceiling(cfg, cspec)
        if ceil is None:
            continue  # `not ceil` would treat a DECLARED total_bytes of 0 as undeclared
        new_t, old_t = staged.get(name, 0), head.get(name, 0)
        if new_t > ceil and new_t > old_t:
            bad.append((f"({name} total)", old_t, new_t, ceil, "B", f"{ceil:,} B"))
    if not bad:
        return CLEAN
    print(f"\n{RED}{B}context-budget: REFUSED{R}")
    for path, old, new, ceil, unit, ceil_s in bad:
        print(f"  {B}{path}{R}  {old:,} -> {new:,} {unit}   ceiling {ceil_s}")
        print(f"    +{new-old:,} {unit} this commit, {new-ceil:,} {unit} over.")
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

    # --- calibration: the comparisons, the arithmetic, and the gate on the result ---
    # This exact pair is the one the authoring fork of this tool was mis-fitted on.
    # The second check is the CONTROL: it asserts the string comparison really does
    # give the wrong answer here, so the first check is not passing for free.
    early = parse_iso("2026-08-01T19:42:50-05:00")        # = 2026-08-02T00:42:50Z
    later = parse_iso("2026-08-01T21:25:28Z")
    check("a -05:00 stamp later in UTC compares as later", early > later)
    check("...and comparing that same pair AS STRINGS is the wrong answer",
          "2026-08-01T19:42:50-05:00" < "2026-08-01T21:25:28Z")
    check("both offset signs land on the same instant",
          parse_iso("2026-08-01T19:42:50-05:00") == parse_iso("2026-08-02T02:42:50+02:00"))
    check("fractional seconds with Z parse", parse_iso("2026-08-01T21:25:28.417Z") is not None)
    check("a non-timestamp is None, never a silent default", parse_iso("not-a-date") is None)
    check("date-shaped but impossible is None too", parse_iso("2026-13-01T00:00:00Z") is None)

    h = [(parse_iso("2026-01-01T00:00:00Z"), 100), (parse_iso("2026-01-03T00:00:00Z"), 300)]
    check("size_at gives the size in EFFECT, not the nearest record",
          size_at(h, parse_iso("2026-01-03T18:00:00Z")) == 300
          and size_at(h, parse_iso("2026-01-02T18:00:00Z")) == 100)
    check("size_at before all history is None, never the first size",
          size_at(h, parse_iso("2025-06-01T00:00:00Z")) is None)

    f = linfit([(x, 3*x + 7) for x in (1, 2, 3, 4)])
    check("linfit recovers a known slope and intercept exactly",
          f and abs(f[0]-3) < 1e-9 and abs(f[1]-7) < 1e-9 and abs(f[2]-1) < 1e-9)
    check("linfit refuses a regressor with no variance", linfit([(5, 1), (5, 2), (5, 3)]) is None)
    f = linfit([(1, 9), (2, 9), (3, 9)])
    check("R² is undefined — not 1.0 — when the response never varies", f and f[2] is None)
    f = linfit([(1, 50), (2, 10), (3, 90), (4, 20)])
    check("a scatter fits with a low R²", f and f[2] < MIN_R2)

    check("a fit above the floor is accepted", calibration_verdict(0.36, 0.81, MIN_R2) is None)
    check("a fit exactly AT the floor is accepted",
          calibration_verdict(0.36, MIN_R2, MIN_R2) is None)
    check("a low-R² fit is refused, however confident the number looks",
          calibration_verdict(0.07, 0.05, MIN_R2) is not None)
    check("a NEGATIVE slope is refused however good the fit",
          calibration_verdict(-0.36, 0.99, MIN_R2) is not None)
    check("an undefined R² is refused, not treated as perfect",
          calibration_verdict(0.36, None, MIN_R2) is not None)

    # The ledger row must name the ceiling that fired. A read-mandated file over its
    # BYTE ceiling reported as `359 ln / 1,200 ln` points at the ceiling that did not.
    row = {"class": "read-mandated", "lines": 359, "max_lines": 1200,
           "bytes": 72449, "max_bytes": 65536, "status": "over",
           "findings": [{"kind": "bytes", "msg": "x"}]}
    check("the row shows the ceiling that fired, not the class default",
          ledger_dimension(row) == ("72,449 B", "65,536 B"))
    check("with nothing fired, a read-mandated row now reports BYTES (since 2026-08-26)",
          ledger_dimension({**row, "findings": [], "status": "ok"}) == ("72,449 B", "65,536 B"))
    check("a LINE finding still reports lines -- only the default moved, not the dispatch",
          ledger_dimension({**row, "findings": [{"kind": "lines", "msg": "x"}]})
          == ("359 ln", "1,200 ln"))
    check("an undeclared ceiling renders as — rather than crashing",
          ledger_dimension({"class": "resident", "bytes": 10, "lines": 1,
                            "findings": []}) == ("10 B", "—"))

    check("the byte remedies name no directory from the tool's home project",
          not any(s in REMEDIES["bytes"][0][1] for s in ("server/", "mobile/", "database/")))

    # --- the class aggregate. Every gate must be observed FAILING, not just passing, and
    # this is the only coverage of the new arm that reaches an adopter at all.
    pair = {"classes": {"pair": {"total_bytes": 1000, "warn_bytes": 600}},
            "files": [{"path": "A.md", "class": "pair"},
                      {"path": "B.md", "class": "pair"}]}
    def _rows(a, b, cls="pair"):
        return [{"path": "A.md", "class": cls, "bytes": a, "findings": [], "status": "ok"},
                {"path": "B.md", "class": cls, "bytes": b, "findings": [], "status": "ok"}]
    tot = {c["class"]: c for c in class_totals(pair, _rows(600, 600))}["pair"]
    check("a class total fires while every member is individually green",
          tot["bytes"] == 1200 and tot["status"] == "over")
    tot = {c["class"]: c for c in class_totals(pair, _rows(300, 200))}["pair"]
    check("a class total under both its ceiling and its warn line passes",
          tot["bytes"] == 500 and tot["status"] == "ok")
    tot = {c["class"]: c for c in class_totals(pair, _rows(400, 300))}["pair"]
    check("a class past its warn line but under its ceiling WARNS -- the seed has "
          "declared classes.resident.warn_bytes since it shipped and nothing read it",
          tot["bytes"] == 700 and tot["status"] == "warn")
    check("moving bytes between members leaves the total unmoved -- the hole per-file "
          "ceilings cannot see",
          class_totals(pair, _rows(900, 300))[-1]["bytes"]
          == class_totals(pair, _rows(300, 900))[-1]["bytes"] == 1200)
    three = {"classes": {"resident": {"total_bytes": 100}, "pair": {"total_bytes": 1000},
                         "third": {"total_bytes": 50}}, "files": []}
    got = {c["class"]: c["bytes"] for c in class_totals(
        three, _rows(600, 600) + _rows(80, 5, "third") + _rows(40, 0, "resident"))}
    check("a third class totals on its OWN members",
          got == {"resident": 40, "pair": 1200, "third": 85})
    check("declared classes report in a deterministic order, resident first",
          [c["class"] for c in class_totals(
              {"classes": {"zeta": {}, "alpha": {}, "resident": {}}}, [])]
          == ["resident", "alpha", "zeta"])
    check("a declared class with no members totals 0 rather than vanishing",
          class_totals({"classes": {"ghost": {"total_bytes": 10}}}, [])[-1]["bytes"] == 0)
    check("this function's own pseudo-row is not counted a second time",
          class_totals(pair, _rows(600, 600) + [{"path": "(pair total)", "class": "pair",
                                                 "bytes": 1200, "findings": [],
                                                 "aggregate": True,
                                                 "status": "over"}])[-1]["bytes"] == 1200)
    check("a DECLARED file whose name starts with '(' is still counted",
          class_totals({"classes": {"pair": {"total_bytes": 1000}}},
                       [{"path": "(draft) notes.md", "class": "pair", "bytes": 1200,
                         "findings": [], "status": "ok"}])[-1]["bytes"] == 1200)
    check("a declared class ceiling of 0 is a ceiling, not an absent one",
          class_totals({"classes": {"z": {"total_bytes": 0}}},
                       [{"path": "a", "class": "z", "bytes": 1, "findings": [],
                         "status": "ok"}])[-1]["status"] == "over")

    # --- the reserve identity: framework_share := READ_CAP_BYTES - adopter_reserve_bytes
    check("READ_CAP_BYTES is computed from the cap, never written",
          READ_CAP_BYTES == int(READ_CAP_TOKENS * MIN_BYTES_PER_TOKEN) == 56750)
    check("the framework share is the cap minus the reserve",
          framework_share({"adopter_reserve_bytes": 28000}) == (28750, 28000, 56750))
    check("a derived class ceiling ignores the number written beside it",
          class_ceiling({}, {"total_bytes": 999, "derive_from_read_cap": True})
          == (56750, True))
    check("a written ceiling that disagrees with the derivation is REPORTED",
          config_defects({"classes": {"r": {"total_bytes": 999,
                                            "derive_from_read_cap": True}}}) != [])
    check("a written ceiling that agrees is clean",
          config_defects({"classes": {"r": {"total_bytes": 56750,
                                            "derive_from_read_cap": True}}}) == [])
    check("a reserve that consumes the whole cap is refused",
          config_defects({"adopter_reserve_bytes": 56750}) != [])
    check("a config with no classes key does not raise", class_spec({}, "resident") == {})

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

    results = [measure_file(root, s, cfg) for s in cfg.get("files", [])]
    synced = [check_synced(root, s) for s in cfg.get("synced", [])]
    # config_defects() had NO call site: it was defined, unit-tested, and never run, while
    # the distributed seed told adopters "a max_tokens above this is rejected as a config
    # defect". A guard nothing calls is a comment shaped like a guard. Wired here so the
    # reserve identity above is genuinely asserted at run time rather than merely written.
    defects = config_defects(cfg)
    resident = sum(r.get("bytes", 0) for r in results if r["class"] == "resident")
    # `resident_bytes` stays the growth-run series' key -- load_history()/growth_run()
    # read it out of every record already on disk, so renaming it would silently reset
    # the run to zero on a file that looks fine. class_bytes is additive beside it.
    snapshot = {"resident_bytes": resident,
                "class_bytes": {c["class"]: c["bytes"] for c in class_totals(cfg, results)},
                "files": {r["path"]: r.get("bytes") for r in results}}

    # Computed BEFORE the pseudo-rows below are appended: class_totals() excludes
    # parenthesised paths for the same reason, but relying on one guard where two are
    # cheap is how a double count gets shipped.
    totals = class_totals(cfg, results)
    for ct in totals:
        ceil = ct["total_bytes"]
        if not ceil or ct["bytes"] <= ceil:
            continue
        # "auto-loaded" describes the resident class specifically, so the resident wording
        # -- and therefore the (resident total) row the adopters are compared on -- is
        # unchanged, while another class gets a sentence that is true of it.
        where = ("across all auto-loaded files" if ct["class"] == "resident"
                 else f"across the {ct['class']} class")
        results.append({"path": f"({ct['class']} total)", "class": ct["class"],
                        "status": "over", "bytes": ct["bytes"], "max_bytes": ceil,
                        # The marker class_totals() filters on. A flag, never the path:
                        # the path is user-supplied data and a project may legitimately
                        # declare a file whose name starts with "(".
                        "aggregate": True,
                        "findings": [{"kind": "bytes", "msg":
                                      f"{ct['bytes']:,} B {where} exceeds the "
                                      f"{ceil:,} B ceiling"}]})

    hist = load_history(root)
    run_len, run_hit = growth_run(hist, snapshot, cfg.get("growth_run", 10))
    append_history(root, snapshot, hist)

    if "--json" in args:
        print(json.dumps({"resident_bytes": resident, "growth_run": run_len,
                          "class_totals": totals, "config_defects": defects,
                          "files": results, "synced": synced},
                         indent=2, default=str))
    else:
        render(root, results, synced, run_len, run_hit, cfg, snapshot, totals,
               defects)

    # Class totals vote too. Without them a class in WARN was invisible to the exit code,
    # so a CI step gating on it could not see the one signal that arrives before a breach.
    states = [r["status"] for r in results + synced] + [c["status"] for c in totals]
    # A config defect is an INSTRUMENT failure, which this tool's own ordering already
    # ranks above `over`: if a declared ceiling is not the one in force, every verdict
    # measured against it is unreliable, including the green ones.
    if defects or "over" in states or "instrument-failed" in states:
        return BREACH
    if "warn" in states or "unmeasured" in states or run_hit:
        return WARN
    return CLEAN


if __name__ == "__main__":
    sys.exit(main())
