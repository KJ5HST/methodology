#!/usr/bin/env python3
"""Tests for starter-kit/close_out_report.py -- the Phase 3G report generator and lint.

Not distributed to adopters (it reads this repository's own ledger). Imports the starter-kit module
directly, so what is tested is what ships. stdlib unittest.

Every lint rule is observed REFUSING a corrupted report (a rule never seen to fire is a
suggestion), and the property test renders a report for every complete receipt this repository
has ever kept -- the live ledger and every archived shard -- and requires each to lint clean.

The hook's decision table (HookTable, one test per row) is driven with the payload shape measured
from the real harness (claude 2.1.288). HookMutants then copies the tool, breaks one decision at a
time, and requires the named row to go red -- a row that cannot fail proves nothing.
"""
import glob
import importlib.util
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True  # keep starter-kit/ free of __pycache__

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TOOL = os.path.join(REPO, "starter-kit", "close_out_report.py")


def load(path, name="close_out_report"):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cor = load(TOOL)

LEDGER = """# Handoffs

```handoff
session: S2
date: 2026-10-03
status: {status}
self_score: 8
predecessor_score: 7
active_task: demo
runtime_smoke: n/a; quality_ratchet: 11/11 pass · 0 fail · 0 unmeasured · results abc
```

```handoff
session: S1
date: 2026-10-02
status: complete
self_score: 7
predecessor_score: 8
active_task: x
```
"""
TEXTS = dict(deliverable="demo", outcome="done", well="a", badly="b", predecessor="c", nxt="d")


def sh(*a, cwd):
    return subprocess.run(a, cwd=cwd, capture_output=True, text=True, check=True).stdout


def make_repo(status="complete"):
    t = tempfile.mkdtemp()
    sh("git", "init", "-q", ".", cwd=t)
    sh("git", "config", "user.email", "t@e.com", cwd=t)
    sh("git", "config", "user.name", "T", cwd=t)
    sh("git", "config", "commit.gpgsign", "false", cwd=t)
    with open(os.path.join(t, "HANDOFFS.md"), "w", encoding="utf-8") as f:
        f.write(LEDGER.format(status=status))
    sh("git", "add", ".", cwd=t)
    sh("git", "commit", "-qm", "c", cwd=t)
    return t


def run_cli(*args, cwd, stdin=None):
    return subprocess.run([sys.executable, TOOL, *args], cwd=cwd, input=stdin, capture_output=True, text=True)


class Parse(unittest.TestCase):
    def test_receipts_in_order_first_line_value(self):
        r = cor.parse_receipts(LEDGER.format(status="complete"))
        self.assertEqual([x["session"] for x in r], ["S2", "S1"])
        self.assertEqual(r[0]["self_score"], "8")

    def test_prose_mentioning_the_fence_is_not_a_receipt(self):
        s = "run `grep -c '^```handoff' HANDOFFS.md`\n" + LEDGER.format(status="complete")
        self.assertEqual(len(cor.parse_receipts(s)), 2)

    def test_gate_citation_and_default(self):
        r = cor.parse_receipts(LEDGER.format(status="complete"))
        self.assertEqual(cor.facts(r[0], r[1], "h", 0)["gate"], "11/11 pass · 0 fail · 0 unmeasured")
        self.assertEqual(cor.facts(r[1], {}, "h", 0)["gate"], "not cited")


class Render(unittest.TestCase):
    def setUp(self):
        self.repo = make_repo()
        self.addCleanup(lambda: __import__("shutil").rmtree(self.repo))
        self.m = cor.live_facts(os.path.join(self.repo, "HANDOFFS.md"), self.repo)

    def good(self):
        return cor.render(self.m, *TEXTS.values())

    def test_output_lints_clean_and_has_the_shape(self):
        t = self.good()
        self.assertEqual(cor.lint(t, self.m), [])
        self.assertTrue(t.startswith("## Close-out report: S2 · 2026-10-03\n"))
        self.assertTrue(t.endswith("\nSession over.\n"))
        self.assertIn("**Predecessor handoff (S1):** 7/10", t)

    def test_head_is_computed_from_git_not_the_receipt(self):
        self.assertEqual(self.m["head"], sh("git", "rev-parse", "--short", "HEAD", cwd=self.repo).strip())

    def test_refuses_each_empty_text(self):
        for i, k in enumerate(cor.FIELDS):
            v = list(TEXTS.values())
            v[i] = " "
            with self.assertRaises(ValueError, msg=k):
                cor.render(self.m, *v)

    def test_refuses_over_long_text_instead_of_truncating(self):
        v = list(TEXTS.values())
        v[2] = "x" * (cor.FIELD_MAX + 1)
        with self.assertRaisesRegex(ValueError, "301 characters"):
            cor.render(self.m, *v)

    def test_accepts_exactly_the_field_cap(self):
        v = list(TEXTS.values())
        v[2] = "x" * cor.FIELD_MAX
        self.assertEqual(cor.lint(cor.render(self.m, *v), self.m), [])

    def test_refuses_pipe_and_newline(self):
        for bad in ("a | b", "a\nb"):
            v = list(TEXTS.values())
            v[4] = bad
            with self.assertRaises(ValueError):
                cor.render(self.m, *v)

    def test_worst_case_fits_the_total_cap(self):
        m = dict(self.m, gate="x" * 60)
        full = ["y" * cor.FIELD_MAX, "y" * cor.OUTCOME_MAX] + ["y" * cor.FIELD_MAX] * 4
        self.assertLessEqual(len(cor.render(m, *full).encode()), cor.TOTAL_MAX)

    def test_refuses_a_paragraph_as_the_outcome(self):
        v = list(TEXTS.values())
        v[1] = "z" * (cor.OUTCOME_MAX + 1)
        with self.assertRaisesRegex(ValueError, "--outcome"):
            cor.render(self.m, *v)


class LintMutants(unittest.TestCase):
    """Ten corruptions of a good report; each must be refused, and by the rule it targets."""

    def setUp(self):
        self.repo = make_repo()
        self.addCleanup(lambda: __import__("shutil").rmtree(self.repo))
        self.m = cor.live_facts(os.path.join(self.repo, "HANDOFFS.md"), self.repo)
        self.good = cor.render(self.m, *TEXTS.values())

    def refused(self, text, rule):
        errs = cor.lint(text, self.m)
        self.assertTrue(any(e.startswith(rule) for e in errs), f"{rule} not raised: {errs}")

    def test_drop_closing_line(self):
        self.refused(self.good.replace("\nSession over.\n", "\n"), "R3")

    def test_text_after_closing_line(self):
        self.refused(self.good + "\nShall I continue?\n", "R3")

    def test_prefix_before_heading(self):
        self.refused("Here is the summary:\n\n" + self.good, "R1")

    def test_heading_names_another_session(self):
        self.refused(self.good.replace("S2 ·", "S9 ·"), "R1")

    def test_wrong_self_score(self):
        self.refused(self.good.replace("8/10", "9/10"), "R4")

    def test_wrong_predecessor_score(self):
        self.refused(self.good.replace("7/10", "6/10"), "R4")

    def test_stale_head(self):
        self.refused(self.good.replace(self.m["head"], "deadbee"), "R5")

    def test_missing_label(self):
        self.refused(self.good.replace("**Next session:**", "Next:"), "R2")

    def test_labels_out_of_order(self):
        t = self.good.replace("**Record:**", "**Zed:**").replace("**Next session:**", "**Record:**")
        self.refused(t.replace("**Zed:**", "**Next session:**"), "R2")

    def test_table_pipe(self):
        self.refused(self.good.replace("DONE", "DONE | x"), "R6")

    def test_over_total_cap(self):
        self.refused(self.good.replace("demo", "x" * 2100, 1), "R7")

    def test_empty_message_is_refused_not_crashed(self):
        self.assertTrue(cor.lint("", self.m))


class Cli(unittest.TestCase):
    def setUp(self):
        self.repo = make_repo()
        self.addCleanup(lambda: __import__("shutil").rmtree(self.repo))
        self.args = ["--deliverable", "demo", "--outcome", "done", "--well", "a", "--badly", "b",
                     "--predecessor", "c", "--next", "d"]

    def test_print_then_check_round_trip(self):
        p = run_cli(*self.args, cwd=self.repo)
        self.assertEqual(p.returncode, 0, p.stderr)
        c = run_cli("--check", "-", cwd=self.repo, stdin=p.stdout)
        self.assertEqual((c.returncode, c.stdout.strip()), (0, "OK"))

    def test_check_refuses_a_hand_written_report(self):
        c = run_cli("--check", "-", cwd=self.repo, stdin="Done. All shipped.\n")
        self.assertEqual(c.returncode, 1)
        self.assertIn("R1", c.stdout)

    def test_report_goes_stale_after_a_commit(self):
        p = run_cli(*self.args, cwd=self.repo)
        with open(os.path.join(self.repo, "n.txt"), "w") as f:
            f.write("x")
        sh("git", "add", ".", cwd=self.repo)
        sh("git", "commit", "-qm", "later", cwd=self.repo)
        c = run_cli("--check", "-", cwd=self.repo, stdin=p.stdout)
        self.assertEqual(c.returncode, 1)
        self.assertIn("R5", c.stdout)

    def test_missing_text_is_refused_with_exit_2(self):
        p = run_cli("--deliverable", "demo", cwd=self.repo)
        self.assertEqual(p.returncode, 2)
        self.assertIn("--outcome is required", p.stderr)

    def test_pending_receipt_is_refused(self):
        r = make_repo("pending")
        self.addCleanup(lambda: __import__("shutil").rmtree(r))
        p = run_cli(*self.args, cwd=r)
        self.assertEqual(p.returncode, 2)
        self.assertIn("not complete", p.stderr)

    def test_missing_ledger_is_refused(self):
        p = run_cli(*self.args, "--ledger", "nope.md", cwd=self.repo)
        self.assertEqual(p.returncode, 2)

    def test_dirty_count_is_reported(self):
        with open(os.path.join(self.repo, "u.txt"), "w") as f:
            f.write("x")
        self.assertIn("1 uncommitted", run_cli(*self.args, cwd=self.repo).stdout)


NEW_RECEIPT = """```handoff
session: S3
date: 2026-10-04
status: {status}
self_score: 6
predecessor_score: 8
active_task: next
runtime_smoke: n/a
```

"""


class HookCase(unittest.TestCase):
    """A repository whose newest receipt is pending, a session id, and the means to fire the hook at it.
    TOOL_PATH is rebound by HookMutants to a broken copy of the tool."""

    TOOL_PATH = TOOL

    def setUp(self):
        self.repo = make_repo("pending")
        self.addCleanup(shutil.rmtree, self.repo, ignore_errors=True)
        self.mod = load(self.TOOL_PATH, "hook_under_test")
        self.sid = "sess-1"
        self.gitdir = os.path.join(self.repo, ".git")

    def payload(self, event, msg="", active=False, sid=None, cwd=None, source="startup"):
        p = {"session_id": sid or self.sid, "transcript_path": "/x", "cwd": cwd or self.repo, "hook_event_name": event}
        if event == "SessionStart":
            p["source"] = source
        else:  # the Stop payload as the real harness sent it; msg=None leaves the message out entirely
            p.update({"prompt_id": "p", "permission_mode": "default", "stop_hook_active": active,
                      "background_tasks": [], "session_crons": []})
            if msg is not None:
                p["last_assistant_message"] = msg
        return p

    def start(self, **kw):
        return self.mod.decide(self.payload("SessionStart", **kw))

    def stop(self, msg="", **kw):
        return self.mod.decide(self.payload("Stop", msg, **kw))

    def hook_cli(self, payload):
        return subprocess.run([sys.executable, self.TOOL_PATH, "--hook"], cwd=self.repo, capture_output=True,
                              text=True, input=payload if isinstance(payload, str) else json.dumps(payload))

    def write_ledger(self, text, msg="ledger"):
        with open(os.path.join(self.repo, "HANDOFFS.md"), "w", encoding="utf-8") as f:
            f.write(text)
        sh("git", "add", ".", cwd=self.repo)
        sh("git", "commit", "-qm", msg, cwd=self.repo)

    def close_out(self):  # the session completes its receipt and commits it
        self.write_ledger(LEDGER.format(status="complete"), "close-out")

    def commit(self, name="n.txt"):
        with open(os.path.join(self.repo, name), "w") as f:
            f.write("x")
        sh("git", "add", ".", cwd=self.repo)
        sh("git", "commit", "-qm", name, cwd=self.repo)

    def report(self):
        m = self.mod.live_facts(os.path.join(self.repo, "HANDOFFS.md"), self.repo)
        return self.mod.render(m, *TEXTS.values())

    def log(self):
        p = os.path.join(self.gitdir, "close-out-report.log")
        if not os.path.exists(p):
            return ""
        with open(p, encoding="utf-8") as f:
            return f.read()

    def assertBlocked(self, r):
        self.assertIsNotNone(r, "expected a block, got allow")
        self.assertEqual(r["decision"], "block")


class HookTable(HookCase):
    """The hook's decision table, one test per row (rows 1-10 are the core cases; 11 onward were added later)."""

    def test_row01_receipt_still_pending_allows(self):
        self.start()
        self.assertIsNone(self.stop("hello"))

    def test_row02_closed_out_but_not_reported_blocks(self):
        self.start()
        self.close_out()
        r = self.stop("Done.")
        self.assertBlocked(r)
        self.assertIn("close_out_report.py", r["reason"])  # it names the command to run
        self.assertIn("--deliverable", r["reason"])
        self.assertIn("R1", r["reason"])                   # and what was wrong
        self.assertIn("sess-1 blocked R1,R2", self.log())  # one trace line per block

    def test_row03_the_harness_forced_retry_allows(self):
        self.start()
        self.close_out()
        self.assertIsNone(self.stop("Done.", active=True))
        self.assertIn("retry-unclean R1", self.log())
        self.assertNotIn("blocked", self.log())

    def test_row04_a_clean_report_allows_and_is_stamped(self):
        self.start()
        self.close_out()
        self.assertIsNone(self.stop(self.report()))
        self.assertEqual(len(glob_(self.gitdir, "close-out-stamp-*")), 1)
        self.assertIn("reported", self.log())

    def test_row05_later_chat_after_the_report_allows(self):
        self.start()
        self.close_out()
        self.stop(self.report())
        self.assertIsNone(self.stop("Sure, anything else?"))

    def test_row06_a_commit_after_the_report_blocks(self):
        self.start()
        self.close_out()
        self.stop(self.report())
        self.commit()  # an action after the report changes the state the report described
        self.assertBlocked(self.stop("Pushed."))

    def test_row07_resume_keeps_the_baseline(self):
        self.start()
        self.close_out()
        self.start(source="resume")
        self.assertBlocked(self.stop("x"))

    def test_row08_a_stale_report_is_not_accepted(self):
        self.start()
        self.close_out()
        old = self.report()
        self.stop(old)
        self.commit()
        r = self.stop(old)
        self.assertBlocked(r)
        self.assertIn("R5", r["reason"])

    def test_row09_no_baseline_allows(self):
        self.close_out()  # the hook was installed after this session began
        self.assertIsNone(self.stop("Done."))

    def test_row10_an_internal_error_exits_zero_silently(self):
        self.start()
        self.close_out()
        self.write_ledger("not a ledger\n")
        p = self.hook_cli(self.payload("Stop", "Done."))
        self.assertEqual((p.returncode, p.stdout), (0, ""))

    def test_row11_a_payload_without_the_message_allows(self):
        self.start()
        self.close_out()
        self.assertIsNone(self.stop(None))

    def test_row12_a_session_started_in_a_subdirectory_still_blocks(self):
        sub = os.path.join(self.repo, "sub")
        os.mkdir(sub)
        self.mod.decide(self.payload("SessionStart", cwd=sub))
        self.close_out()
        self.assertBlocked(self.mod.decide(self.payload("Stop", "Done.", cwd=sub)))

    def test_row13_a_repository_without_a_ledger_is_silent(self):
        os.remove(os.path.join(self.repo, "HANDOFFS.md"))
        for ev in ("SessionStart", "Stop"):
            p = self.hook_cli(self.payload(ev, "Done."))
            self.assertEqual((p.returncode, p.stdout), (0, ""), ev)

    def test_row14_state_lives_in_dot_git_never_in_the_tree(self):
        self.start()
        self.close_out()
        self.stop(self.report())
        self.assertEqual(sh("git", "status", "--porcelain", cwd=self.repo), "")
        for pat in ("close-out-baseline-*", "close-out-stamp-*", "close-out-report.log"):
            self.assertEqual(len(glob_(self.gitdir, pat)), 1, pat)

    def test_row15_a_session_id_with_slashes_is_a_file_name_not_a_path(self):
        sid = "a/../../b"
        self.mod.decide(self.payload("SessionStart", sid=sid))
        self.close_out()
        self.assertBlocked(self.mod.decide(self.payload("Stop", "Done.", sid=sid)))
        self.assertTrue(os.path.exists(os.path.join(self.gitdir, "close-out-baseline-a_.._.._b")))

    def test_row16_a_receipt_claimed_and_completed_in_the_session_is_owed(self):
        done = LEDGER.format(status="complete")
        self.write_ledger(done)  # the session begins with S2 complete...
        self.start()
        claimed = done.replace("# Handoffs\n\n", "# Handoffs\n\n" + NEW_RECEIPT.format(status="pending"), 1)
        self.write_ledger(claimed, "claim")
        self.assertIsNone(self.stop("working"))
        self.write_ledger(claimed.replace("status: pending", "status: complete"), "close-out")  # ...and closes out S3
        self.assertBlocked(self.stop("Done."))

    def test_row17_a_session_that_began_complete_owes_nothing(self):
        self.close_out()
        self.start()
        self.assertIsNone(self.stop("Done."))

    def test_row18_the_reasons_command_runs_from_anywhere_and_its_output_is_accepted(self):
        self.start()
        self.close_out()
        r = self.stop("Done.")
        cmd = re.search(r"Run: (.*?) --deliverable", r["reason"]).group(1)
        elsewhere = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, elsewhere, ignore_errors=True)
        argv = shlex.split(cmd) + ["--deliverable", "demo", "--outcome", "done", "--well", "a", "--badly", "b",
                                   "--predecessor", "c", "--next", "d"]
        p = subprocess.run(argv, cwd=elsewhere, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIsNone(self.stop(p.stdout, active=True))
        self.assertIn("reported", self.log())


def glob_(d, pat):
    return glob.glob(os.path.join(d, pat))


class HookCli(HookCase):
    """The --hook flag as the harness calls it: a payload on stdin, JSON on stdout only to block, exit 0."""

    def test_a_block_is_printed_as_json_and_exits_zero(self):
        self.hook_cli(self.payload("SessionStart"))
        self.close_out()
        p = self.hook_cli(self.payload("Stop", "Done."))
        self.assertEqual(p.returncode, 0, p.stderr)
        out = json.loads(p.stdout)
        self.assertEqual(out["decision"], "block")
        self.assertIn("reason", out)

    def test_an_allow_prints_nothing(self):
        p = self.hook_cli(self.payload("SessionStart"))
        self.assertEqual((p.returncode, p.stdout, p.stderr), (0, "", ""))

    def test_garbage_or_empty_stdin_exits_zero_silently(self):
        for junk in ("not json", ""):
            p = self.hook_cli(junk)
            self.assertEqual((p.returncode, p.stdout), (0, ""), repr(junk))

    def test_hook_mode_runs_before_the_pending_refusal_that_render_mode_makes(self):
        self.assertEqual(run_cli(*[x for k in ("deliverable", "outcome", "well", "badly", "predecessor", "next")
                                   for x in ("--" + k, "x")], cwd=self.repo).returncode, 2)  # render refuses
        self.assertEqual(self.hook_cli(self.payload("Stop", "hello")).returncode, 0)  # the hook never does


# What is broken, the edits that break it (each anchor must occur exactly once), the row that must go red.
HOOK_MUTANTS = [
    ("the forced-retry guard is dropped", [('if payload.get("stop_hook_active"):', "if False:")],
     "test_row03_the_harness_forced_retry_allows"),
    ("the already-reported stamp check is dropped", [("if json.load(f) == state:", "if False:")],
     "test_row05_later_chat_after_the_report_allows"),
    ("SessionStart overwrites the baseline", [('with open(base, "x", encoding="utf-8")', 'with open(base, "w", encoding="utf-8")')],
     "test_row07_resume_keeps_the_baseline"),
    ("a missing baseline counts as owed",
     [('if not os.path.exists(base) or "last_assistant_message" not in payload:',
       'if "last_assistant_message" not in payload:'),
      ('with open(base, encoding="utf-8") as f:\n        began = json.load(f)',
       'began = ["?", "?", "?"]')],
     "test_row09_no_baseline_allows"),
    ("an internal error exits 2", [("            out = None\n        if out:", "            return 2\n        if out:")],
     "test_row10_an_internal_error_exits_zero_silently"),
    ("the stamp ignores HEAD", [('state = [m["head"], ', 'state = ["x", ')],
     "test_row06_a_commit_after_the_report_blocks"),
    ("a missing message is read as empty",
     [('if not os.path.exists(base) or "last_assistant_message" not in payload:', "if not os.path.exists(base):"),
      ('lint(payload["last_assistant_message"], m)', 'lint(payload.get("last_assistant_message", ""), m)')],
     "test_row11_a_payload_without_the_message_allows"),
    ("the session id is used as a path", [("[:100]", "[:100] if 0 else str(sid)")],
     "test_row15_a_session_id_with_slashes_is_a_file_name_not_a_path"),
    ("the ledger is looked for in the payload's cwd, not the repository root",
     [('ledger = os.path.join(top, "HANDOFFS.md")', 'ledger = os.path.join(cwd, "HANDOFFS.md")')],
     "test_row12_a_session_started_in_a_subdirectory_still_blocks"),
    ("a receipt that began pending is not owed", [('and began[2] == "complete"', "")],
     "test_row02_closed_out_but_not_reported_blocks"),
    ("a receipt claimed in the session is not owed", [('(began[:2] == _ident(newest)[:2] and began[2] == "complete")', '(began[2] == "complete")')],
     "test_row16_a_receipt_claimed_and_completed_in_the_session_is_owed"),
    ("a block leaves no log line", [('_log(gitdir, sid, f"blocked {codes}")', "pass")],
     "test_row02_closed_out_but_not_reported_blocks"),
    ("an unclean retry leaves no log line", [('_log(gitdir, sid, f"retry-unclean {codes}")', "pass")],
     "test_row03_the_harness_forced_retry_allows"),
    ("an accepted report leaves no log line", [('_log(gitdir, sid, "reported")', "pass")],
     "test_row04_a_clean_report_allows_and_is_stamped"),
    ("the command in the reason names no ledger or repository",
     [('"--ledger", shlex.quote(ledger),\n                    "--cwd", shlex.quote(top)]', "]")],
     "test_row18_the_reasons_command_runs_from_anywhere_and_its_output_is_accepted"),
]


def _run_row(tool_path, row):
    cls = type("Row", (HookTable,), {"TOOL_PATH": tool_path})
    return unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(unittest.TestSuite([cls(row)]))


class HookMutants(unittest.TestCase):
    """One decision broken at a time in a copy of the tool; the named row must go red, and the same row must
    be green on an unbroken copy at the same path, so a red row is the mutation's doing and not the copy's."""

    @staticmethod
    def make(name, edits, row):
        def test(self):
            with open(TOOL, encoding="utf-8") as f:
                src = f.read()
            d = tempfile.mkdtemp()
            self.addCleanup(shutil.rmtree, d, ignore_errors=True)
            copies = {}
            for kind in ("control", "mutant"):  # the real file name, in its own directory: rows name it
                os.mkdir(os.path.join(d, kind))
                copies[kind] = os.path.join(d, kind, "close_out_report.py")
            control, mutant = copies["control"], copies["mutant"]
            with open(control, "w", encoding="utf-8") as f:
                f.write(src)
            for old, new in edits:
                self.assertEqual(src.count(old), 1, f"mutation anchor must occur exactly once: {old!r}")
                src = src.replace(old, new)
            with open(mutant, "w", encoding="utf-8") as f:
                f.write(src)
            load(mutant, "mutant")  # a file that no longer imports is not a mutant, it is a typo
            self.assertTrue(_run_row(control, row).wasSuccessful(), f"{row} is red on an UNBROKEN copy")
            self.assertFalse(_run_row(mutant, row).wasSuccessful(), f"{row} stayed green with: {name}")
        return test


for _i, (_name, _edits, _row) in enumerate(HOOK_MUTANTS, 1):
    setattr(HookMutants, f"test_mutant{_i:02d}_{re.sub(r'[^a-z0-9]+', '_', _name.lower())[:48]}",
            HookMutants.make(_name, _edits, _row))


class Property(unittest.TestCase):
    """A report for every complete receipt the repository has ever kept lints clean."""

    def receipts(self):
        paths = [os.path.join(REPO, "HANDOFFS.md")]
        paths += sorted(p for p in glob.glob(os.path.join(REPO, "docs", "archive", "HANDOFFS*.md")))
        out = []
        for p in paths:
            with open(p, encoding="utf-8") as f:
                rs = cor.parse_receipts(f.read())
            # within one file, newest first; the predecessor is the next block
            out += [(os.path.basename(p), r, rs[i + 1] if i + 1 < len(rs) else {}) for i, r in enumerate(rs)]
        return [x for x in out if x[1].get("status") == "complete"]

    def test_every_complete_receipt_renders_and_lints_clean(self):
        rs = self.receipts()
        self.assertGreaterEqual(len(rs), 30, "the ledger and its archives should hold at least thirty complete receipts")
        bad, unscored = [], []
        for fname, r, prev in rs:
            if not (r.get("self_score", "").isdigit() and r.get("predecessor_score", "").isdigit()):
                unscored.append((fname, r.get("session"), r.get("date")))
                continue
            m = cor.facts(r, prev, "abc1234", 0)
            try:
                text = cor.render(m, "d", "done", "w", "b", "p", "n")
            except ValueError as e:
                bad.append(f"{fname} {r.get('session')} {r.get('date')}: {e}")
                continue
            errs = cor.lint(text, m)
            if errs:
                bad.append(f"{fname} {r.get('session')} {r.get('date')}: {errs}")
        self.assertEqual(bad, [], "\n".join(bad[:10]))
        # The first receipt ever written (S1, 2026-07-08) predates predecessor_score. It is the one
        # pinned exception; a second unscored receipt means the ledger stopped recording scores.
        self.assertEqual([(s, d) for _, s, d in unscored], [("S1", "2026-07-08")])  # by receipt, not by the file a trim may have moved it to


if __name__ == "__main__":
    unittest.main()
