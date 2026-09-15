#!/usr/bin/env python3
"""Unit tests for starter-kit/quality_ratchet.py — the declared-threshold ratchet.

CANONICAL-ONLY. Not in bin/_manifest.py, so adopters do not receive it; they get the
tool's own --selftest. This suite imports the starter-kit module directly (the one
bin/sync distributes), so what is tested is what ships.

Every gate is observed FAILING as well as passing (Learning #12): a ratchet whose
refusal was never seen to fire is a suggestion with a hook attached.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
STARTER = REPO / "starter-kit" / "quality_ratchet.py"

_spec = importlib.util.spec_from_file_location("quality_ratchet", STARTER)
qr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(qr)

PY = sys.executable


def manifest(*gates):
    return {"version": 1, "gates": list(gates)}


def gate(name, direction="min", threshold=1, **kw):
    g = {"name": name, "direction": direction, "threshold": threshold}
    g.update(kw)
    return g


class TestCompareIsTheRatchet(unittest.TestCase):
    """compare(old, new) is pure — no git — so every rule is testable without a repo."""

    def setUp(self):
        self.base = manifest(gate("cov", "min", 80), gate("cc", "max", 10))

    def test_lowering_a_floor_is_refused(self):
        new = manifest(gate("cov", "min", 79), gate("cc", "max", 10))
        refusals, _ = qr.compare(self.base, new)
        self.assertEqual(len(refusals), 1)
        self.assertIn("floor lowered 80 -> 79", refusals[0])

    def test_raising_a_ceiling_is_refused(self):
        new = manifest(gate("cov", "min", 80), gate("cc", "max", 11))
        refusals, _ = qr.compare(self.base, new)
        self.assertEqual(len(refusals), 1)
        self.assertIn("ceiling raised 10 -> 11", refusals[0])

    def test_removing_a_gate_is_refused(self):
        refusals, _ = qr.compare(self.base, manifest(gate("cov", "min", 80)))
        self.assertEqual(len(refusals), 1)
        self.assertIn("'cc' removed", refusals[0])

    def test_flipping_a_direction_is_refused(self):
        new = manifest(gate("cov", "max", 80), gate("cc", "max", 10))
        refusals, _ = qr.compare(self.base, new)
        self.assertTrue(any("direction min -> max" in r for r in refusals))

    def test_tightening_passes(self):
        new = manifest(gate("cov", "min", 85), gate("cc", "max", 8))
        self.assertEqual(qr.compare(self.base, new), ([], []))

    def test_adding_a_gate_passes(self):
        new = manifest(*self.base["gates"], gate("links", "max", 0))
        self.assertEqual(qr.compare(self.base, new), ([], []))

    def test_unchanged_passes(self):
        self.assertEqual(qr.compare(self.base, json.loads(json.dumps(self.base))), ([], []))

    def test_a_changed_command_warns_but_does_not_refuse(self):
        old = manifest(gate("cov", "min", 80, command="a"))
        new = manifest(gate("cov", "min", 80, command="b"))
        refusals, warnings = qr.compare(old, new)
        self.assertEqual(refusals, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn("`command` changed", warnings[0])

    def test_equal_threshold_written_as_string_is_not_a_loosening(self):
        # JSON hand-edits sometimes quote numbers; "80" == 80 for the ratchet's purposes.
        new = manifest(gate("cov", "min", "80"), gate("cc", "max", 10))
        self.assertEqual(qr.compare(self.base, new)[0], [])


class TestConfigDefects(unittest.TestCase):
    def test_clean_manifest_has_no_defects(self):
        self.assertEqual(qr.config_defects(manifest(gate("a"), gate("b", "max", 0))), [])

    def test_each_defect_is_named(self):
        cfg = manifest(
            {"direction": "min", "threshold": 1},                 # no name
            gate("dup"), gate("dup"),                             # duplicate
            gate("dirn", "up", 1),                                # bad direction
            gate("num", "min", "many"),                           # non-numeric threshold
            gate("rx", "min", 1, command="x", extract="("),       # bad regex
            gate("orphan", "min", 1, extract="(\\d+)"),           # extract without command
        )
        d = "\n".join(qr.config_defects(cfg))
        for token in ("missing `name`", "duplicate name", "`direction` must be",
                      "`threshold` must be a number", "not a valid regex",
                      "`extract` without `command`"):
            self.assertIn(token, d)

    def test_gates_must_be_a_list(self):
        self.assertEqual(qr.config_defects({"gates": {}}), ["`gates` must be a list"])
        self.assertEqual(qr.config_defects("nope"), ["`gates` must be a list"])


class TestMeasureGate(unittest.TestCase):
    def test_extracted_number_compared_against_a_floor(self):
        g = gate("n", "min", 3, command=f'"{PY}" -c "print(\'value 7\')"', extract=r"value (\d+)")
        r = qr.measure_gate(os.getcwd(), g, 30)
        self.assertEqual((r["measured"], r["status"]), (7.0, "pass"))
        g["threshold"] = 8
        self.assertEqual(qr.measure_gate(os.getcwd(), g, 30)["status"], "fail")

    def test_without_extract_the_exit_code_is_the_measurement(self):
        ok = gate("exit", "max", 0, command=f'"{PY}" -c "pass"')
        bad = gate("exit", "max", 0, command=f'"{PY}" -c "raise SystemExit(3)"')
        self.assertEqual(qr.measure_gate(os.getcwd(), ok, 30)["status"], "pass")
        r = qr.measure_gate(os.getcwd(), bad, 30)
        self.assertEqual((r["measured"], r["status"]), (3.0, "fail"))

    def test_no_command_is_unmeasured_never_pass(self):
        r = qr.measure_gate(os.getcwd(), gate("declared", "min", 0), 30)
        self.assertEqual(r["status"], "unmeasured")
        self.assertIsNone(r["measured"])

    def test_extract_that_matches_nothing_is_unmeasured_never_pass(self):
        g = gate("n", "min", 0, command=f'"{PY}" -c "print(\'no digits\')"', extract=r"(\d+)")
        r = qr.measure_gate(os.getcwd(), g, 30)
        self.assertEqual(r["status"], "unmeasured")
        self.assertIn("matched nothing", r["note"])

    def test_a_missing_command_is_unmeasured_not_pass(self):
        # A threshold of `max 0` with a command that cannot even start must not read as pass:
        # the shell's 127 is the measurement, and 127 > 0.
        g = gate("ghost", "max", 0, command="definitely-not-a-real-command-xyz")
        self.assertEqual(qr.measure_gate(os.getcwd(), g, 30)["status"], "fail")


class TestRunStatusAndResultsFile(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.d = td.name
        subprocess.run(["git", "init", "-q", self.d], check=True)
        self.cfg = manifest(
            gate("three", "min", 3, command=f'"{PY}" -c "print(3)"', extract=r"(\d+)"),
            gate("exit", "max", 0, command=f'"{PY}" -c "pass"'))
        json.dump(self.cfg, open(os.path.join(self.d, qr.CONFIG_NAME), "w"))

    def test_run_writes_results_and_returns_clean(self):
        rc = qr.do_run(self.d, self.cfg, as_json=True)
        self.assertEqual(rc, qr.CLEAN)
        snap = json.load(open(os.path.join(self.d, qr.DEFAULT_RESULTS)))
        self.assertEqual(snap["summary"], {"pass": 2, "fail": 0, "unmeasured": 0})
        self.assertEqual(len(snap["results"]), 12)
        self.assertEqual(snap["manifest"], qr.sha12(self.cfg["gates"]))

    def test_results_hash_is_stable_across_runs_and_independent_of_time(self):
        qr.do_run(self.d, self.cfg, as_json=True)
        a = json.load(open(os.path.join(self.d, qr.DEFAULT_RESULTS)))
        qr.do_run(self.d, self.cfg, as_json=True)
        b = json.load(open(os.path.join(self.d, qr.DEFAULT_RESULTS)))
        self.assertEqual(a["results"], b["results"])

    def test_summary_line_is_citable(self):
        snap = qr.run_gates(self.d, self.cfg)
        line = qr.summary_line(snap)
        self.assertTrue(line.startswith("quality_ratchet: 2/2 pass · 0 fail · 0 unmeasured · results "))
        self.assertIn("· manifest ", line)

    def test_status_before_any_run_says_never_run(self):
        import contextlib, io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = qr.do_status(self.d, self.cfg, as_json=True)
        self.assertEqual(rc, qr.WARN)
        self.assertIn("never run here", buf.getvalue())

    def test_status_flags_a_stale_manifest(self):
        qr.do_run(self.d, self.cfg, as_json=True)
        import contextlib, io
        buf = io.StringIO()
        changed = manifest(*self.cfg["gates"], gate("new", "max", 0))
        with contextlib.redirect_stdout(buf):
            rc = qr.do_status(self.d, changed, as_json=True)
        self.assertEqual(rc, qr.WARN)
        self.assertTrue(json.loads(buf.getvalue())["stale"])

    def test_a_failing_gate_exits_refused_and_an_unmeasured_one_warns(self):
        failing = manifest(gate("three", "min", 4, command=f'"{PY}" -c "print(3)"', extract=r"(\d+)"))
        self.assertEqual(qr.do_run(self.d, failing, as_json=True), qr.REFUSED)
        unm = manifest(gate("declared", "min", 1))
        self.assertEqual(qr.do_run(self.d, unm, as_json=True), qr.WARN)


class TestPrecommitThroughGit(unittest.TestCase):
    """The ratchet as git sees it: the INDEX vs HEAD, never the worktree."""

    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.d = td.name
        for argv in (["git", "init", "-q", self.d],
                     ["git", "-C", self.d, "config", "user.email", "t@t"],
                     ["git", "-C", self.d, "config", "user.name", "t"]):
            subprocess.run(argv, check=True)
        self.base = manifest(gate("cov", "min", 80))
        self._write(self.base)
        subprocess.run(["git", "-C", self.d, "add", "-A"], check=True)
        subprocess.run(["git", "-C", self.d, "commit", "-q", "-m", "base"], check=True)

    def _write(self, cfg):
        json.dump(cfg, open(os.path.join(self.d, qr.CONFIG_NAME), "w"))

    def _stage(self, cfg):
        self._write(cfg)
        subprocess.run(["git", "-C", self.d, "add", qr.CONFIG_NAME], check=True)

    def _precommit(self):
        import contextlib, io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = qr.precommit(self.d)
        return rc, buf.getvalue()

    def test_manifest_not_in_the_commit_passes(self):
        self.assertEqual(self._precommit()[0], qr.CLEAN)

    def test_staged_loosening_is_refused(self):
        self._stage(manifest(gate("cov", "min", 70)))
        rc, out = self._precommit()
        self.assertEqual(rc, qr.REFUSED)
        self.assertIn("REFUSED", out)
        self.assertIn("--no-verify", out)  # the cost of bypass is printed, never hidden

    def test_staged_tightening_passes(self):
        self._stage(manifest(gate("cov", "min", 90)))
        self.assertEqual(self._precommit()[0], qr.CLEAN)

    def test_the_index_not_the_worktree_is_what_is_ratcheted(self):
        # Stage a tightening, then loosen only the worktree copy: the commit is the index.
        self._stage(manifest(gate("cov", "min", 90)))
        self._write(manifest(gate("cov", "min", 10)))
        self.assertEqual(self._precommit()[0], qr.CLEAN)
        # And the mirror: stage a loosening, then "fix" only the worktree — still refused.
        self._stage(manifest(gate("cov", "min", 10)))
        self._write(manifest(gate("cov", "min", 90)))
        self.assertEqual(self._precommit()[0], qr.REFUSED)

    def test_a_staged_manifest_with_defects_is_refused(self):
        self._stage(manifest(gate("cov", "sideways", 80)))
        rc, out = self._precommit()
        self.assertEqual(rc, qr.REFUSED)
        self.assertIn("config defect", out)

    def test_first_manifest_commit_has_nothing_to_compare(self):
        subprocess.run(["git", "-C", self.d, "rm", "-q", "--cached", qr.CONFIG_NAME], check=True)
        subprocess.run(["git", "-C", self.d, "commit", "-q", "-m", "drop"], check=True)
        self._stage(manifest(gate("cov", "min", 1)))
        rc, out = self._precommit()
        self.assertEqual(rc, qr.CLEAN)
        self.assertIn("first manifest commit", out)


class TestToolInvariants(unittest.TestCase):
    def test_no_force_escape_hatch(self):
        src = STARTER.read_text(encoding="utf-8")
        self.assertNotIn('"--force" in args and', src)
        rc = subprocess.run([PY, str(STARTER), "--force"], capture_output=True, text=True)
        self.assertEqual(rc.returncode, qr.USAGE)
        self.assertIn("no --force", rc.stdout)

    def test_stdlib_only(self):
        import ast
        tree = ast.parse(STARTER.read_text(encoding="utf-8"))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module.split(".")[0])
        # sys.stdlib_module_names is 3.10+; pin the allowed set so the test runs on older
        # interpreters too, which is where a stray third-party import would bite first.
        allowed = {"hashlib", "json", "os", "re", "subprocess", "sys", "tempfile", "datetime",
                   "shutil"}
        self.assertTrue(names <= allowed, names - allowed)

    def test_selftest_is_green(self):
        rc = subprocess.run([PY, str(STARTER), "--selftest"], capture_output=True, text=True)
        self.assertEqual(rc.returncode, 0, rc.stdout + rc.stderr)

    def test_seed_manifest_is_valid_and_empty(self):
        seed = json.load(open(REPO / "starter-kit" / "quality-gates.json"))
        self.assertEqual(seed["gates"], [], "the seed starts empty by decision (plan §8.4)")
        self.assertEqual(qr.config_defects(seed), [])
        # The example gate must itself be a valid gate, or it teaches a broken schema.
        self.assertEqual(qr.config_defects({"gates": [seed["_example"]]}), [])


if __name__ == "__main__":
    unittest.main()
