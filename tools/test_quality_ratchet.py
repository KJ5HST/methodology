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

    def test_two_gates_over_one_command_run_it_once(self):
        # Two extracts over the same suite (passed count, failed count) must not run it twice:
        # a --run that takes bin/tests.sh twice is a --run nobody cites.
        marker = os.path.join(self.d, "runs.txt")
        cmd = f'"{PY}" -c "open({marker!r}, \'a\').write(\'x\'); print(\'7 passed, 1 failed\')"'
        cfg = manifest(gate("passed", "min", 7, command=cmd, extract=r"(\d+) passed"),
                       gate("failed", "max", 1, command=cmd, extract=r"passed, (\d+) failed"))
        snap = qr.run_gates(self.d, cfg)
        self.assertEqual([r["status"] for r in snap["gates"]], ["pass", "pass"])
        self.assertEqual(open(marker).read(), "x", "the shared command ran more than once")

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

    def test_no_base_note_when_head_holds_the_base(self):
        # An unrelated commit after the manifest's last change: HEAD still holds the base, and
        # `git log -- manifest` naming an older commit is not "HEAD has none".
        open(os.path.join(self.d, "unrelated.txt"), "w").write("x\n")
        subprocess.run(["git", "-C", self.d, "add", "unrelated.txt"], check=True)
        subprocess.run(["git", "-C", self.d, "commit", "-q", "-m", "unrelated"], check=True)
        self._stage(manifest(gate("cov", "min", 90)))
        rc, out = self._precommit()
        self.assertEqual(rc, qr.CLEAN)
        self.assertNotIn("comparing against", out)

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
        # "First" means never committed on this branch's history -- not "absent at HEAD".
        fresh = tempfile.TemporaryDirectory(); self.addCleanup(fresh.cleanup)
        for argv in (["git", "init", "-q", fresh.name],
                     ["git", "-C", fresh.name, "config", "user.email", "t@t"],
                     ["git", "-C", fresh.name, "config", "user.name", "t"]):
            subprocess.run(argv, check=True)
        open(os.path.join(fresh.name, "README"), "w").write("x\n")
        subprocess.run(["git", "-C", fresh.name, "add", "-A"], check=True)
        subprocess.run(["git", "-C", fresh.name, "commit", "-q", "-m", "base"], check=True)
        json.dump(manifest(gate("cov", "min", 1)), open(os.path.join(fresh.name, qr.CONFIG_NAME), "w"))
        subprocess.run(["git", "-C", fresh.name, "add", qr.CONFIG_NAME], check=True)
        import contextlib, io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = qr.precommit(fresh.name)
        self.assertEqual(rc, qr.CLEAN)
        self.assertIn("first manifest commit", buf.getvalue())

    # --- the deletion hole (PR #82 review, section 2a): a comparison needs two sides ---

    def _commit_removal(self):
        """Commit the manifest's removal as `--no-verify` would: index has none, HEAD keeps history."""
        subprocess.run(["git", "-C", self.d, "rm", "-q", "--cached", qr.CONFIG_NAME], check=True)
        subprocess.run(["git", "-C", self.d, "commit", "-q", "-m", "drop"], check=True)

    def test_removing_the_manifest_is_refused_as_the_loosest_loosening(self):
        subprocess.run(["git", "-C", self.d, "rm", "-q", "--cached", qr.CONFIG_NAME], check=True)
        rc, out = self._precommit()
        self.assertEqual(rc, qr.REFUSED)
        self.assertIn("manifest removed", out)
        self.assertIn("--no-verify", out)

    def test_readding_lower_after_a_committed_removal_is_refused(self):
        self._commit_removal()
        self._stage(manifest(gate("cov", "min", 1)))
        rc, out = self._precommit()
        self.assertEqual(rc, qr.REFUSED)       # 80 -> 1 via delete + re-add is still 80 -> 1
        self.assertIn("floor lowered", out)
        self._stage(manifest(gate("cov", "min", 80)))
        self.assertEqual(self._precommit()[0], qr.CLEAN)

    def test_an_already_removed_manifest_does_not_lock_the_repo(self):
        self._commit_removal()
        open(os.path.join(self.d, "unrelated.txt"), "w").write("x\n")
        subprocess.run(["git", "-C", self.d, "add", "unrelated.txt"], check=True)
        self.assertEqual(self._precommit()[0], qr.CLEAN)

    def test_an_unparseable_head_copy_is_skipped_for_the_newest_parseable(self):
        open(os.path.join(self.d, qr.CONFIG_NAME), "w").write("not json")
        subprocess.run(["git", "-C", self.d, "add", qr.CONFIG_NAME], check=True)
        subprocess.run(["git", "-C", self.d, "commit", "-q", "-m", "corrupt"], check=True)
        self._stage(manifest(gate("cov", "min", 70)))
        rc, out = self._precommit()
        self.assertEqual(rc, qr.REFUSED)       # compared against the 80 two commits back
        self.assertIn("floor lowered", out)
        self._stage(manifest(gate("cov", "min", 80)))
        self.assertEqual(self._precommit()[0], qr.CLEAN)

    def test_an_emptied_manifest_is_not_a_comparison_base(self):
        # Emptying the gate list is refused like a removal; bypassed, it must not become the
        # base that lets a later re-declaration land lower than what was declared before.
        self._stage(manifest())
        rc, out = self._precommit()
        self.assertEqual(rc, qr.REFUSED)
        subprocess.run(["git", "-C", self.d, "commit", "-q", "--no-verify", "-m", "empty anyway"], check=True)
        self._stage(manifest(gate("cov", "min", 1)))
        rc, out = self._precommit()
        self.assertEqual(rc, qr.REFUSED)       # 80 -> 1, with an empty manifest in between
        self.assertIn("floor lowered", out)

    def test_a_synced_empty_seed_is_not_a_comparison_base_either(self):
        # The seed adopters receive is empty; the first real declaration is a first commit.
        fresh = tempfile.TemporaryDirectory(); self.addCleanup(fresh.cleanup)
        for argv in (["git", "init", "-q", fresh.name],
                     ["git", "-C", fresh.name, "config", "user.email", "t@t"],
                     ["git", "-C", fresh.name, "config", "user.name", "t"]):
            subprocess.run(argv, check=True)
        json.dump(manifest(), open(os.path.join(fresh.name, qr.CONFIG_NAME), "w"))
        subprocess.run(["git", "-C", fresh.name, "add", "-A"], check=True)
        subprocess.run(["git", "-C", fresh.name, "commit", "-q", "-m", "seed"], check=True)
        json.dump(manifest(gate("cov", "min", 50)), open(os.path.join(fresh.name, qr.CONFIG_NAME), "w"))
        subprocess.run(["git", "-C", fresh.name, "add", qr.CONFIG_NAME], check=True)
        import contextlib, io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = qr.precommit(fresh.name)
        self.assertEqual(rc, qr.CLEAN)
        self.assertIn("first manifest commit", buf.getvalue())

    def test_precommit_cli_survives_a_manifest_missing_from_the_worktree(self):
        # Through the CLI: an ordinary `git rm` empties the worktree copy too. The tool must
        # still find the repo (git toplevel) and judge the removal, not exit 3 "refuses to invent".
        subprocess.run(["git", "-C", self.d, "rm", "-q", qr.CONFIG_NAME], check=True)
        p = subprocess.run([PY, str(STARTER), "--precommit"], cwd=self.d, capture_output=True, text=True)
        self.assertEqual(p.returncode, qr.REFUSED, p.stdout + p.stderr)
        self.assertIn("manifest removed", p.stdout)


class TestFindRootAndHookPath(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        self.d = td.name
        for argv in (["git", "init", "-q", self.d],
                     ["git", "-C", self.d, "config", "user.email", "t@t"],
                     ["git", "-C", self.d, "config", "user.name", "t"]):
            subprocess.run(argv, check=True)

    def test_find_root_is_the_git_toplevel_even_without_a_manifest(self):
        sub = os.path.join(self.d, "a", "b"); os.makedirs(sub)
        self.assertEqual(os.path.realpath(qr.find_root(sub)), os.path.realpath(self.d))

    def test_find_root_walks_up_to_a_manifest_outside_git(self):
        td = tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        json.dump(manifest(), open(os.path.join(td.name, qr.CONFIG_NAME), "w"))
        sub = os.path.join(td.name, "x"); os.makedirs(sub)
        self.assertEqual(os.path.realpath(qr.find_root(sub)), os.path.realpath(td.name))

    def test_install_hook_writes_the_path_of_the_file_that_is_running(self):
        # The canonical repo keeps the tool under starter-kit/; an adopter at the root. The hook
        # must exec whichever copy installed it, or every commit fails "can't open file".
        tools = os.path.join(self.d, "tools"); os.makedirs(tools)
        import shutil; shutil.copy(STARTER, os.path.join(tools, "quality_ratchet.py"))
        json.dump(manifest(gate("g", "min", 1, command="true")), open(os.path.join(self.d, qr.CONFIG_NAME), "w"))
        subprocess.run(["git", "-C", self.d, "add", "-A"], check=True)
        subprocess.run(["git", "-C", self.d, "commit", "-q", "-m", "base"], check=True)
        p = subprocess.run([PY, os.path.join(tools, "quality_ratchet.py"), "install-hook"],
                           cwd=self.d, capture_output=True, text=True)
        self.assertEqual(p.returncode, qr.CLEAN, p.stdout + p.stderr)
        hook = open(os.path.join(self.d, ".git", "hooks", "pre-commit")).read()
        self.assertIn("tools/quality_ratchet.py", hook)
        open(os.path.join(self.d, "unrelated.txt"), "w").write("x\n")
        subprocess.run(["git", "-C", self.d, "add", "unrelated.txt"], check=True)
        p = subprocess.run(["git", "-C", self.d, "commit", "-q", "-m", "after install"],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)


def _git(d, *args, check=True):
    return subprocess.run(["git", "-C", d, *args], check=check, capture_output=True, text=True)


def _put(d, rel, text="x\n"):
    p = os.path.join(d, *rel.split("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        f.write(text if isinstance(text, str) else json.dumps(text))
    return p


NEW_CONFIG = "methodology/" + qr.CONFIG_NAME   # layout: the new layout's path of the manifest
LEGACY_CONFIG = qr.CONFIG_NAME


class TestTheManifestMayLiveInEitherLayout(unittest.TestCase):
    """BL-101 P2 (plan section 4.3): a project keeps its manifest at its root (legacy) or under
    methodology/ (new). The ratchet reads the four-row table with the manifest as the anchor."""

    def setUp(self):
        td = tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        self.d = os.path.realpath(td.name)

    def _cli(self, *args, cwd=None):
        return subprocess.run([PY, str(STARTER), *args], cwd=cwd or self.d, capture_output=True, text=True)

    def test_manifest_location_reads_the_four_rows(self):
        self.assertEqual(qr.manifest_location(self.d), ("none", None))
        _put(self.d, LEGACY_CONFIG, manifest())
        self.assertEqual(qr.manifest_location(self.d), ("legacy", LEGACY_CONFIG))
        os.remove(os.path.join(self.d, LEGACY_CONFIG))
        _put(self.d, NEW_CONFIG, manifest())
        self.assertEqual(qr.manifest_location(self.d), ("new", NEW_CONFIG))
        _put(self.d, LEGACY_CONFIG, manifest())
        self.assertEqual(qr.manifest_location(self.d), ("half", None))

    def test_find_root_finds_a_manifest_that_lives_under_methodology(self):
        _put(self.d, NEW_CONFIG, manifest())
        sub = os.path.join(self.d, "src", "deep"); os.makedirs(sub)
        self.assertEqual(os.path.realpath(qr.find_root(self.d)), self.d)
        self.assertEqual(os.path.realpath(qr.find_root(sub)), self.d)

    def test_find_root_from_inside_methodology_is_the_project_not_that_directory(self):
        _git(self.d, "init", "-q")
        _put(self.d, NEW_CONFIG, manifest())
        self.assertEqual(os.path.realpath(qr.find_root(os.path.join(self.d, "methodology"))), self.d)

    def test_a_repository_that_is_itself_named_methodology_keeps_its_own_root(self):
        # This very repository is a directory called methodology/ whose manifest sits at its root.
        # Reading "a manifest in a directory named methodology" as the new layout would move its
        # root one level up, to a directory that is not a project.
        repo = os.path.join(self.d, "methodology")
        os.makedirs(repo); _git(repo, "init", "-q")
        _put(repo, LEGACY_CONFIG, manifest())
        sub = os.path.join(repo, "tools"); os.makedirs(sub)
        self.assertEqual(os.path.realpath(qr.find_root(repo)), os.path.realpath(repo))
        self.assertEqual(os.path.realpath(qr.find_root(sub)), os.path.realpath(repo))

    def test_run_in_the_new_layout_writes_its_results_beside_the_manifest(self):
        _put(self.d, NEW_CONFIG, manifest(gate("marker", "max", 0, command=f'"{PY}" -c "import os,sys; sys.exit(0 if os.path.exists(\'marker.txt\') else 1)"')))
        _put(self.d, "marker.txt")
        p = self._cli("--run")
        self.assertEqual(p.returncode, qr.CLEAN, p.stdout + p.stderr)
        self.assertTrue(os.path.exists(os.path.join(self.d, "methodology", qr.DEFAULT_RESULTS)))
        self.assertFalse(os.path.exists(os.path.join(self.d, qr.DEFAULT_RESULTS)), "no results file at the root")
        # the gate's command ran from the project root, not from methodology/
        self.assertIn("1/1 pass", p.stdout)
        s = self._cli("--status")
        self.assertEqual(s.returncode, qr.CLEAN, s.stdout + s.stderr)
        self.assertIn("1/1 pass", s.stdout)

    def test_run_in_the_legacy_layout_still_writes_its_results_at_the_root(self):
        _put(self.d, LEGACY_CONFIG, manifest(gate("ok", "max", 0, command=f'"{PY}" -c "pass"')))
        self.assertEqual(self._cli("--run").returncode, qr.CLEAN)
        self.assertTrue(os.path.exists(os.path.join(self.d, qr.DEFAULT_RESULTS)))
        self.assertFalse(os.path.exists(os.path.join(self.d, "methodology")))

    def test_an_explicit_results_file_is_relative_to_the_root_in_either_layout(self):
        cfg = manifest(gate("ok", "max", 0, command=f'"{PY}" -c "pass"')); cfg["results_file"] = "out/r.json"
        _put(self.d, NEW_CONFIG, cfg)
        os.makedirs(os.path.join(self.d, "out"))   # the tool writes the file, it does not make the directory
        self.assertEqual(self._cli("--run").returncode, qr.CLEAN)
        self.assertTrue(os.path.exists(os.path.join(self.d, "out", "r.json")))

    def test_a_half_migrated_tree_is_a_usage_error_that_names_both_and_runs_nothing(self):
        _put(self.d, LEGACY_CONFIG, manifest(gate("ok", "max", 0, command=f'"{PY}" -c "pass"')))
        _put(self.d, NEW_CONFIG, manifest(gate("ok", "max", 0, command=f'"{PY}" -c "pass"')))
        for args in (["--run"], ["--status"], ["install-hook"]):
            p = self._cli(*args)
            self.assertEqual(p.returncode, qr.USAGE, (args, p.stdout + p.stderr))
            self.assertIn(LEGACY_CONFIG, p.stdout); self.assertIn(NEW_CONFIG, p.stdout)
        self.assertFalse(os.path.exists(os.path.join(self.d, qr.DEFAULT_RESULTS)))
        self.assertFalse(os.path.exists(os.path.join(self.d, "methodology", qr.DEFAULT_RESULTS)))

    def test_manifest_location_decides_a_tie_by_the_framework_anchor(self):
        # S276's picker (plan 7.2b): a project whose runner is under methodology/ keeps its manifest
        # there, and a manifest at the root is the project's own, which the ratchet does not read.
        _put(self.d, LEGACY_CONFIG, manifest()); _put(self.d, NEW_CONFIG, manifest())
        self.assertEqual(qr.manifest_location(self.d), ("half", None))        # no runner: still refused
        _put(self.d, "methodology/SESSION_RUNNER.md", "runner\n")
        self.assertEqual(qr.manifest_location(self.d), ("new", NEW_CONFIG))
        _put(self.d, "SESSION_RUNNER.md", "runner\n")
        self.assertEqual(qr.manifest_location(self.d), ("half", None))        # a runner in both places decides nothing

    def test_a_tie_the_anchor_decides_runs_the_methodology_manifest_and_leaves_the_root_one_alone(self):
        _put(self.d, LEGACY_CONFIG, manifest(gate("users-own", "max", 0, command=f'"{PY}" -c "raise SystemExit(1)"')))
        _put(self.d, NEW_CONFIG, manifest(gate("ok", "max", 0, command=f'"{PY}" -c "pass"')))
        _put(self.d, "methodology/SESSION_RUNNER.md", "runner\n")
        p = self._cli("--run")
        self.assertEqual(p.returncode, qr.CLEAN, p.stdout + p.stderr)
        self.assertNotIn("users-own", p.stdout)
        self.assertTrue(os.path.exists(os.path.join(self.d, "methodology", qr.DEFAULT_RESULTS)))
        self.assertFalse(os.path.exists(os.path.join(self.d, qr.DEFAULT_RESULTS)), "nothing is written beside the user's file")


class _Repo(unittest.TestCase):
    """A throwaway repository holding a legacy manifest (cov >= 80) at its root, committed."""

    def setUp(self):
        td = tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        self.d = os.path.realpath(td.name)
        _git(self.d, "init", "-q")
        _git(self.d, "config", "user.email", "t@t")
        _git(self.d, "config", "user.name", "t")
        _put(self.d, LEGACY_CONFIG, manifest(gate("cov", "min", 80)))
        _git(self.d, "add", "-A"); _git(self.d, "commit", "-q", "-m", "base")

    def _commit(self, msg="c"):
        _git(self.d, "add", "-A"); _git(self.d, "commit", "-q", "--no-verify", "-m", msg)

    def _move(self, cfg=None):
        """git mv the manifest under methodology/, optionally rewriting it, all staged."""
        os.makedirs(os.path.join(self.d, "methodology"), exist_ok=True)
        _git(self.d, "mv", LEGACY_CONFIG, NEW_CONFIG)
        if cfg is not None:
            _put(self.d, NEW_CONFIG, cfg)
            _git(self.d, "add", NEW_CONFIG)

    def _precommit(self):
        import contextlib, io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = qr.precommit(self.d)
        return rc, buf.getvalue()


class TestPrecommitAcrossTheMove(_Repo):
    """BL-101 P2, plan C4. A move that reads as 'manifest removed' is refused for the wrong reason,
    a base search that stops at the move cannot see a loosening made inside it, and a manifest at
    the new path that nothing looks for is a ratchet that fails OPEN."""

    def test_a_pure_move_of_the_manifest_passes(self):
        self._move()
        rc, out = self._precommit()
        self.assertEqual(rc, qr.CLEAN, out)

    def test_a_move_that_lowers_a_floor_is_refused_and_names_the_change(self):
        self._move(manifest(gate("cov", "min", 70)))
        rc, out = self._precommit()
        self.assertEqual(rc, qr.REFUSED, out)
        self.assertIn("floor lowered 80 -> 70", out)

    def test_a_move_that_tightens_passes(self):
        self._move(manifest(gate("cov", "min", 90)))
        self.assertEqual(self._precommit()[0], qr.CLEAN)

    def test_a_move_that_adds_a_gate_passes(self):
        self._move(manifest(gate("cov", "min", 80), gate("new", "max", 0)))
        self.assertEqual(self._precommit()[0], qr.CLEAN)

    def test_a_move_that_drops_a_gate_is_refused(self):
        self._move(manifest(gate("other", "min", 1)))
        rc, out = self._precommit()
        self.assertEqual(rc, qr.REFUSED, out)
        self.assertIn("gate 'cov' removed", out)   # the gate, not 'manifest removed': the file moved

    def test_a_loosening_at_the_new_path_after_the_move_commit_is_refused(self):
        # The fail-open C4 measured: once the manifest is under methodology/ a ratchet that looks
        # only at the root finds nothing staged and nothing at HEAD, and passes every loosening.
        self._move(); self._commit("move")
        _put(self.d, NEW_CONFIG, manifest(gate("cov", "min", 70))); _git(self.d, "add", NEW_CONFIG)
        rc, out = self._precommit()
        self.assertEqual(rc, qr.REFUSED, out)
        self.assertIn("floor lowered 80 -> 70", out)

    def test_a_tightening_at_the_new_path_after_the_move_commit_passes(self):
        self._move(); self._commit("move")
        _put(self.d, NEW_CONFIG, manifest(gate("cov", "min", 95))); _git(self.d, "add", NEW_CONFIG)
        self.assertEqual(self._precommit()[0], qr.CLEAN)

    def test_the_base_is_found_across_the_move_when_the_head_copy_is_unusable(self):
        # The history walk must not stop at the move: A declared 90 at the root, the move commit
        # (bypassed) emptied the gates at the new path, and re-adding 80 is a loosening against A.
        _put(self.d, LEGACY_CONFIG, manifest(gate("cov", "min", 90))); self._commit("tighten to 90")
        self._move(manifest()); self._commit("move and empty")
        _put(self.d, NEW_CONFIG, manifest(gate("cov", "min", 80))); _git(self.d, "add", NEW_CONFIG)
        rc, out = self._precommit()
        self.assertEqual(rc, qr.REFUSED, out)
        self.assertIn("floor lowered 90 -> 80", out)
        self.assertIn("comparing against", out)   # the base came from further back than HEAD, and says so

    def test_the_base_is_the_newest_declaration_at_either_path(self):
        # After the move the history of the OLD path ends at the move. A walk that names only that
        # path never sees the tightening made later at the new one, so a loosening back to a value
        # between the two would pass.
        self._move(); self._commit("move")
        _put(self.d, NEW_CONFIG, manifest(gate("cov", "min", 95))); self._commit("tighten at the new path")
        _put(self.d, NEW_CONFIG, manifest()); self._commit("empty it (bypassed)")
        _put(self.d, NEW_CONFIG, manifest(gate("cov", "min", 92))); _git(self.d, "add", NEW_CONFIG)
        rc, out = self._precommit()
        self.assertEqual(rc, qr.REFUSED, out)
        self.assertIn("floor lowered 95 -> 92", out)

    def test_a_commit_that_held_both_layouts_is_neither_a_base_nor_a_head_copy(self):
        # A bypassed commit left the manifest in both places, the legacy copy lower than the truth.
        # Reading either copy as "the" manifest would hand the ratchet a weaker base; the commit is
        # skipped like an unparseable one, and HEAD's copy is not trusted either (the note says so).
        _put(self.d, LEGACY_CONFIG, manifest(gate("cov", "min", 60)))
        _put(self.d, NEW_CONFIG, manifest(gate("cov", "min", 70))); self._commit("both, bypassed")
        _git(self.d, "rm", "-q", LEGACY_CONFIG)
        rc, out = self._precommit()
        self.assertEqual(rc, qr.REFUSED, out)
        self.assertIn("floor lowered 80 -> 70", out)   # the base is the last unambiguous declaration
        self.assertIn("comparing against", out)

    def test_removing_the_manifest_at_the_new_path_is_refused(self):
        self._move(); self._commit("move")
        _git(self.d, "rm", "-q", NEW_CONFIG)
        rc, out = self._precommit()
        self.assertEqual(rc, qr.REFUSED, out)
        self.assertIn("manifest removed", out)

    def test_both_locations_in_the_index_is_half_migrated_and_refused_naming_both(self):
        _put(self.d, NEW_CONFIG, manifest(gate("cov", "min", 80))); _git(self.d, "add", NEW_CONFIG)
        rc, out = self._precommit()
        self.assertEqual(rc, qr.REFUSED, out)
        self.assertIn("half-migrated", out)
        self.assertIn(LEGACY_CONFIG, out); self.assertIn(NEW_CONFIG, out)

    def _tie(self, root_floor=10, new_floor=80, runner="methodology"):
        """Commit a manifest at BOTH paths (the root one is lower: it is somebody else's) and a runner
        tracked under methodology/, at the root, at both, or nowhere."""
        _put(self.d, LEGACY_CONFIG, manifest(gate("cov", "min", root_floor)))
        _put(self.d, NEW_CONFIG, manifest(gate("cov", "min", new_floor)))
        if runner in ("methodology", "both"):
            _put(self.d, "methodology/SESSION_RUNNER.md", "runner\n")
        if runner in ("root", "both"):
            _put(self.d, "SESSION_RUNNER.md", "runner\n")
        self._commit("a manifest in both places")

    def test_a_tie_the_runner_decides_judges_the_methodology_manifest_and_not_the_root_one(self):
        # S276's picker: the ratchet works inside methodology/. A loosening there is refused for the
        # loosening (not as "half-migrated"); a change to the root file, which is the user's, is not judged.
        self._tie()
        _put(self.d, NEW_CONFIG, manifest(gate("cov", "min", 70))); _git(self.d, "add", NEW_CONFIG)
        rc, out = self._precommit()
        self.assertEqual(rc, qr.REFUSED, out)
        self.assertIn("floor lowered 80 -> 70", out)
        self.assertNotIn("half-migrated", out)
        _git(self.d, "reset", "-q", "--", NEW_CONFIG); _put(self.d, NEW_CONFIG, manifest(gate("cov", "min", 80)))
        _put(self.d, LEGACY_CONFIG, manifest(gate("cov", "min", 1))); _git(self.d, "add", LEGACY_CONFIG)
        rc, out = self._precommit()
        self.assertEqual(rc, qr.CLEAN, out)

    def test_a_tie_the_runner_decides_takes_its_base_from_the_methodology_copy(self):
        self._tie(root_floor=95, new_floor=90)
        _put(self.d, NEW_CONFIG, manifest(gate("cov", "min", 85))); _git(self.d, "add", NEW_CONFIG)
        rc, out = self._precommit()
        self.assertEqual(rc, qr.REFUSED, out)
        self.assertIn("floor lowered 90 -> 85", out)   # not against the root file's 95

    def test_a_tie_the_runner_cannot_decide_is_still_refused_naming_both(self):
        for runner in ("root", "both", None):
            with self.subTest(runner=runner):
                self.setUp()
                self._tie(runner=runner)
                _put(self.d, NEW_CONFIG, manifest(gate("cov", "min", 85))); _git(self.d, "add", NEW_CONFIG)
                rc, out = self._precommit()
                self.assertEqual(rc, qr.REFUSED, out)
                self.assertIn("half-migrated", out)
                self.assertIn(LEGACY_CONFIG, out); self.assertIn(NEW_CONFIG, out)

    def test_a_runner_that_is_on_disk_but_not_tracked_decides_nothing(self):
        # The hook reads the INDEX; so does this. A runner in the worktree that was never added is not an anchor.
        self._tie(runner=None)
        _put(self.d, "methodology/SESSION_RUNNER.md", "runner\n")
        _put(self.d, NEW_CONFIG, manifest(gate("cov", "min", 85))); _git(self.d, "add", NEW_CONFIG)
        rc, out = self._precommit()
        self.assertEqual(rc, qr.REFUSED, out)
        self.assertIn("half-migrated", out)

    def test_a_manifest_first_committed_under_methodology_has_nothing_to_compare(self):
        td = tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        d = os.path.realpath(td.name)
        _git(d, "init", "-q"); _git(d, "config", "user.email", "t@t"); _git(d, "config", "user.name", "t")
        _put(d, NEW_CONFIG, manifest(gate("cov", "min", 80))); _git(d, "add", "-A")
        import contextlib, io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = qr.precommit(d)
        self.assertEqual(rc, qr.CLEAN)
        self.assertIn("first manifest commit", buf.getvalue())

    def test_a_defective_manifest_at_the_new_path_is_refused(self):
        self._move(); self._commit("move")
        _put(self.d, NEW_CONFIG, '{"gates": "nope"}'); _git(self.d, "add", NEW_CONFIG)
        self.assertEqual(self._precommit()[0], qr.REFUSED)

    def test_the_cli_judges_a_move_from_a_subdirectory_by_the_index(self):
        self._move(manifest(gate("cov", "min", 70)))
        sub = os.path.join(self.d, "src"); os.makedirs(sub)
        p = subprocess.run([PY, str(STARTER), "--precommit"], cwd=sub, capture_output=True, text=True)
        self.assertEqual(p.returncode, qr.REFUSED, p.stdout + p.stderr)
        self.assertIn("floor lowered 80 -> 70", p.stdout)


class TestTheInstalledHookAcrossTheMove(_Repo):
    """The hook install-hook writes execs the tool by path. After a move that path is wrong, which
    refuses every commit loudly (C4); the hook now also looks for the tool in the other layout."""

    def _install(self, tool_rel):
        import shutil
        dst = os.path.join(self.d, *tool_rel.split("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy(STARTER, dst)
        _git(self.d, "add", "-A"); _git(self.d, "commit", "-q", "--no-verify", "-m", "add the tool")
        p = subprocess.run([PY, dst, "install-hook"], cwd=self.d, capture_output=True, text=True)
        self.assertEqual(p.returncode, qr.CLEAN, p.stdout + p.stderr)
        return open(os.path.join(self.d, ".git", "hooks", "pre-commit")).read()

    def _commit_hooked(self, msg="c"):
        _git(self.d, "add", "-A")
        return subprocess.run(["git", "-C", self.d, "commit", "-q", "-m", msg], capture_output=True, text=True)

    def test_install_from_the_new_layout_names_that_copy_and_its_twin(self):
        self._move(); self._commit("move the manifest")
        hook = self._install("methodology/quality_ratchet.py")
        self.assertIn("methodology/quality_ratchet.py", hook)
        self.assertIn('"quality_ratchet.py"', hook, "the twin in the other layout")

    def test_a_canonical_style_path_has_no_twin(self):
        loop = [l for l in qr.hook_text("starter-kit/quality_ratchet.py").splitlines() if l.startswith("for t in ")]
        self.assertEqual(loop, ['for t in "starter-kit/quality_ratchet.py"; do'])

    def test_each_layout_names_the_other_as_its_twin(self):
        self.assertEqual(qr.layout_twin("quality_ratchet.py"), "methodology/quality_ratchet.py")
        self.assertEqual(qr.layout_twin("methodology/quality_ratchet.py"), "quality_ratchet.py")
        self.assertIsNone(qr.layout_twin("starter-kit/quality_ratchet.py"))
        self.assertIsNone(qr.layout_twin("tools/methodology/quality_ratchet.py"))

    def test_the_hook_from_the_new_layout_refuses_a_loosening_and_passes_a_tightening(self):
        self._move(); self._commit("move the manifest")
        self._install("methodology/quality_ratchet.py")
        _put(self.d, NEW_CONFIG, manifest(gate("cov", "min", 70)))
        p = self._commit_hooked("loosen")
        self.assertNotEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("floor lowered 80 -> 70", p.stdout + p.stderr)
        _put(self.d, NEW_CONFIG, manifest(gate("cov", "min", 85)))
        self.assertEqual(self._commit_hooked("tighten").returncode, 0)

    def test_the_hook_finds_the_tool_after_it_moves_to_the_other_layout(self):
        self._install("quality_ratchet.py")
        os.makedirs(os.path.join(self.d, "methodology"))
        _git(self.d, "mv", LEGACY_CONFIG, NEW_CONFIG)
        _git(self.d, "mv", "quality_ratchet.py", "methodology/quality_ratchet.py")
        p = self._commit_hooked("the pure move")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_a_move_that_loosens_is_refused_end_to_end_by_the_moved_tool(self):
        self._install("quality_ratchet.py")
        os.makedirs(os.path.join(self.d, "methodology"))
        _git(self.d, "mv", LEGACY_CONFIG, NEW_CONFIG)
        _git(self.d, "mv", "quality_ratchet.py", "methodology/quality_ratchet.py")
        _put(self.d, NEW_CONFIG, manifest(gate("cov", "min", 70)))
        p = self._commit_hooked("the move that loosens")
        self.assertNotEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("floor lowered 80 -> 70", p.stdout + p.stderr)

    def test_a_hook_whose_tool_is_nowhere_fails_loudly_and_says_what_to_do(self):
        self._install("quality_ratchet.py")
        os.remove(os.path.join(self.d, "quality_ratchet.py"))
        _put(self.d, "unrelated.txt")
        p = self._commit_hooked("no tool")
        self.assertNotEqual(p.returncode, 0, "a missing tool must refuse, never pass silently")
        self.assertIn("not found", p.stdout + p.stderr)
        self.assertIn("install-hook", p.stdout + p.stderr)


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
                   "shutil",
                   "pathlib"}   # the embedded layout-resolver block (BL-101 P2) imports it
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
