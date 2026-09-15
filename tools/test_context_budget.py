#!/usr/bin/env python3
"""Behaviour tests for starter-kit/context_budget.py — the FM #28 size-budget gate.

CANONICAL-ONLY. Not in bin/_manifest.py, so adopters do not receive it. The tool's own
`--selftest` ships to them and covers every pure gate; what cannot ship is this file's
git fixtures, which need a scratch repository with a real merge in it.

WHY THIS FILE EXISTS AT ALL. Until the 2026-08-15 `calibrate()` repair it had no test asserting
its arithmetic — the tool's bin/tests.sh block covered install-hook, sync distribution and the
selftest gates, all of which stayed green while the fit itself returned noise on any repo
that had merged another lineage of its regressor. A shipped executable can be arbitrarily
wrong in a dimension nothing asserts. That is the same argument the harness already makes
for the ledger trimmer at bin/tests.sh:237-244.

DISCIPLINE THIS FILE IS WRITTEN UNDER (inherited from tools/test_methodology_trim.py):

  * PROVE THE FIXTURE FIRST. Every fixture asserts what it IS before anything is asserted
    about what the code does to it. A merge fixture that failed to create a merge would
    make the D1 tests pass for the wrong reason, forever.
  * DRIVE EACH GUARD RED. Green is not evidence until red has been observed. Each defect
    below is exhibited as well as fixed: D1 through `first_parent=False`, which is the
    real pre-change behaviour preserved as a parameter for exactly this purpose, and D2
    through `_string_size_at`, a verbatim re-implementation of the shipped comparison.
  * NARROW THE GUARD, DO NOT ONLY DELETE IT. The plausible weaker implementation is shown
    to give the WRONG answer on the same fixture, which is what makes the strong version
    load-bearing rather than merely present.
  * ASSERT ON VALUES, NEVER ON A TOOL'S EXIT CODE. An exit code is a union over every
    check the tool runs, so adding a check silently re-labels unrelated assertions.

THE PRE-CHANGE TOOL is blob be2721a5fa12df027636d1451d84301293467fae — `git cat-file blob
be2721a` — should anyone need to re-run the four-way fit that motivated this.
"""

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True          # no starter-kit/__pycache__ from this import

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
CB_PY = REPO / "starter-kit" / "context_budget.py"

_spec = importlib.util.spec_from_file_location("context_budget", str(CB_PY))
cb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cb)


def git(repo, *args, when=None, check=True):
    """Run git in `repo`. `when` pins BOTH author and committer date, which is what makes
    the ordering fixtures reproducible — %cI reads the committer date, not the author's.
    `check=False` is for the deliberate conflict in the merge fixture."""
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    if when:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = when
    p = subprocess.run(["git", "-C", str(repo), *args], env=env,
                       capture_output=True, text=True)
    if check and p.returncode:
        raise AssertionError(f"git {' '.join(args)} failed: {p.stderr.strip()}")
    return p.stdout.strip()


def write_commit(repo, name, size, when, msg=None):
    (Path(repo) / name).write_text("x" * size)
    git(repo, "add", name)
    git(repo, "commit", "-m", msg or f"{name} -> {size}", when=when)


def new_repo(d):
    git(d, "init", "-q", "-b", "main")
    return d


# ---------------------------------------------------------------------------------
# D1 — lineage. `git log -- <path>` walks ALL merged ancestry, so on a repository that
# has merged another lineage of the same file, two size series interleave by commit
# date and "the size of X at time T" stops being a function.
# ---------------------------------------------------------------------------------

class TestLineage(unittest.TestCase):

    def _forked_repo(self, d):
        """main: 100 B at t0, 200 B at t2. A side branch carries 50,000 B at t1 — a size
        that NEVER existed on main — and is merged at t3, the merge RESOLVING the file to
        300 B.

        The resolution matters, and the first draft of this fixture got it wrong. A merge
        taken with `-s ours` leaves the tree TREESAME to the first parent, and git's
        DEFAULT history simplification then prunes the side branch from `git log -- <path>`
        on its own — so the defect does not reproduce and every assertion below would have
        passed against the broken code. D1 requires a merge that genuinely changed the
        target, which is exactly the case this framework's own workflow produces: a fork
        syncing an upstream that has edited the same file.
        """
        new_repo(d)
        write_commit(d, "CLAUDE.md", 100, "2026-01-01T00:00:00+00:00")
        git(d, "checkout", "-q", "-b", "side")
        write_commit(d, "CLAUDE.md", 50000, "2026-01-02T00:00:00+00:00")
        git(d, "checkout", "-q", "main")
        write_commit(d, "CLAUDE.md", 200, "2026-01-03T00:00:00+00:00")
        git(d, "merge", "--no-commit", "--no-ff", "side", check=False)   # conflicts, by design
        (Path(d) / "CLAUDE.md").write_text("x" * 300)                    # the resolution
        git(d, "add", "CLAUDE.md")
        git(d, "commit", "-m", "merge side", when="2026-01-04T00:00:00+00:00")
        return d

    def test_fixture_really_has_a_merge_and_a_foreign_size(self):
        """PROVE THE FIXTURE. Without a real two-parent merge, without the side branch's
        size being reachable through the ancestry walk, and without the merge having
        actually changed the file, every assertion below would pass vacuously. This test
        failed first on the original fixture and is the only reason that was caught."""
        with tempfile.TemporaryDirectory() as d:
            self._forked_repo(d)
            parents = git(d, "rev-list", "--parents", "-n", "1", "HEAD").split()
            self.assertEqual(len(parents), 3, "HEAD is not a two-parent merge")
            allsizes = {s for _, s in cb.size_history(d, "CLAUDE.md", first_parent=False)[0]}
            self.assertIn(50000, allsizes, "the foreign lineage is not reachable at all")
            self.assertEqual((Path(d) / "CLAUDE.md").stat().st_size, 300,
                             "the merge did not change the file, so it is TREESAME-pruned")

    def test_first_parent_excludes_the_foreign_lineage(self):
        with tempfile.TemporaryDirectory() as d:
            self._forked_repo(d)
            hist, skipped, err = cb.size_history(d, "CLAUDE.md")
            self.assertIsNone(err)
            self.assertEqual(skipped, 0)
            self.assertEqual([s for _, s in hist], [100, 200, 300])

    def test_the_defect_it_replaces_admits_a_size_that_never_existed_here(self):
        """DRIVE IT RED. first_parent=False is the shipped pre-change behaviour."""
        with tempfile.TemporaryDirectory() as d:
            self._forked_repo(d)
            defective, _, _ = cb.size_history(d, "CLAUDE.md", first_parent=False)
            self.assertIn(50000, [s for _, s in defective])

    def test_size_at_disagrees_between_the_two_views_on_the_same_instant(self):
        """The consequence, stated as the quantity that actually feeds the regression:
        at 2026-01-02T12:00Z main's CLAUDE.md was 100 B. The ancestry-walking view says
        50,000 B — a 500x error in the regressor, silently."""
        with tempfile.TemporaryDirectory() as d:
            self._forked_repo(d)
            when = cb.parse_iso("2026-01-02T12:00:00Z")
            good = cb.size_at(cb.size_history(d, "CLAUDE.md")[0], when)
            bad = cb.size_at(cb.size_history(d, "CLAUDE.md", first_parent=False)[0], when)
            self.assertEqual(good, 100)
            self.assertEqual(bad, 50000)

    def test_a_treesame_merge_is_pruned_even_without_first_parent(self):
        """The boundary of D1, pinned so nobody re-derives it the hard way (this session
        did): git's default history simplification already drops a side branch whose merge
        did not change the target. The defect needs a merge that DID."""
        with tempfile.TemporaryDirectory() as d:
            new_repo(d)
            write_commit(d, "CLAUDE.md", 100, "2026-01-01T00:00:00+00:00")
            git(d, "checkout", "-q", "-b", "side")
            write_commit(d, "CLAUDE.md", 50000, "2026-01-02T00:00:00+00:00")
            git(d, "checkout", "-q", "main")
            write_commit(d, "CLAUDE.md", 200, "2026-01-03T00:00:00+00:00")
            git(d, "merge", "-q", "-s", "ours", "side", "-m", "merge",
                when="2026-01-04T00:00:00+00:00")
            self.assertNotIn(50000, [s for _, s in
                                     cb.size_history(d, "CLAUDE.md", first_parent=False)[0]])

    def test_presence_control_no_merge_means_the_two_views_agree(self):
        """Without this the D1 tests could be passing because --first-parent drops
        something unconditionally, rather than because it drops the foreign lineage."""
        with tempfile.TemporaryDirectory() as d:
            new_repo(d)
            write_commit(d, "CLAUDE.md", 100, "2026-01-01T00:00:00+00:00")
            write_commit(d, "CLAUDE.md", 200, "2026-01-03T00:00:00+00:00")
            self.assertEqual(cb.size_history(d, "CLAUDE.md")[0],
                             cb.size_history(d, "CLAUDE.md", first_parent=False)[0])

    def test_a_missing_target_is_an_empty_history_not_an_error(self):
        with tempfile.TemporaryDirectory() as d:
            new_repo(d)
            write_commit(d, "other.md", 10, "2026-01-01T00:00:00+00:00")
            hist, skipped, err = cb.size_history(d, "CLAUDE.md")
            self.assertEqual((hist, skipped, err), ([], 0, None))

    def test_a_non_repository_surfaces_the_error_never_an_empty_history(self):
        """'no history' and 'git could not run' must not be the same value — that
        conflation is the defect run() was written to avoid (tool docstring :54)."""
        with tempfile.TemporaryDirectory() as d:
            hist, _, err = cb.size_history(d, "CLAUDE.md")
            self.assertIsNone(hist)
            self.assertTrue(err)


# ---------------------------------------------------------------------------------
# D2 — timezone. git %cI emits a numeric offset that moves with the season; transcripts
# end in Z. Ordered as STRINGS that is not chronological.
# ---------------------------------------------------------------------------------

def _string_size_at(hist_iso, iso):
    """The shipped pre-change comparison, verbatim (context_budget.py:402/:410 at blob
    be2721a): sort ISO strings, take the last one <= the target string."""
    best = None
    for when, size in sorted(hist_iso):
        if when <= iso:
            best = size
    return best


class TestTimezone(unittest.TestCase):

    # The real pair from the authoring fork: its commit 7603f10 shrank CLAUDE.md
    # 52,909 -> 8,519 B at 19:42:50-05:00, which is 2026-08-02T00:42:50Z — AFTER a session
    # that opened at 2026-08-01T21:25:28Z. String order says the opposite.
    COMMIT = "2026-08-01T19:42:50-05:00"
    SESSION = "2026-08-01T21:25:28Z"

    def test_fixture_the_string_comparison_really_is_wrong_here(self):
        """PROVE THE FIXTURE. If these strings did not mis-order, the pair would be a
        decoration rather than a regression test."""
        self.assertLess(self.COMMIT, self.SESSION, "chosen pair does not mis-order as strings")
        self.assertGreater(cb.parse_iso(self.COMMIT), cb.parse_iso(self.SESSION),
                           "chosen pair is not actually inverted in real time")

    def test_size_at_scores_the_session_against_the_size_that_was_live(self):
        hist = [(cb.parse_iso("2026-07-20T12:00:00-04:00"), 52909),
                (cb.parse_iso(self.COMMIT), 8519)]
        self.assertEqual(cb.size_at(hist, cb.parse_iso(self.SESSION)), 52909)

    def test_the_defect_it_replaces_scores_it_against_the_wrong_size(self):
        """DRIVE IT RED against the narrowed implementation."""
        hist_iso = [("2026-07-20T12:00:00-04:00", 52909), (self.COMMIT, 8519)]
        self.assertEqual(_string_size_at(hist_iso, self.SESSION), 8519)

    # A DST-straddling pair whose lexical order is the REVERSE of its real order. Not
    # every mixed-offset pair inverts — the first pair tried here did not, which is why
    # the fixture is asserted below before it is relied on.
    EARLIER = "2026-08-01T20:00:00-04:00"     # = 2026-08-02T00:00:00Z, first in real time
    LATER = "2026-08-01T19:30:00-05:00"       # = 2026-08-02T00:30:00Z, second in real time

    def test_fixture_the_dst_pair_really_inverts(self):
        """PROVE THE FIXTURE, again: lexically LATER sorts before EARLIER."""
        self.assertLess(self.LATER, self.EARLIER, "pair does not invert lexically")
        self.assertLess(cb.parse_iso(self.EARLIER), cb.parse_iso(self.LATER),
                        "pair is not in the claimed real-time order")

    def test_history_is_ordered_chronologically_not_lexically(self):
        """A repository whose commits straddle a DST boundary — every long-lived one."""
        with tempfile.TemporaryDirectory() as d:
            new_repo(d)
            write_commit(d, "CLAUDE.md", 100, self.EARLIER)
            write_commit(d, "CLAUDE.md", 200, self.LATER)
            hist, _, _ = cb.size_history(d, "CLAUDE.md")
            self.assertEqual([s for _, s in hist], [100, 200])
            # The narrowed implementation orders the same two records the other way.
            self.assertEqual([s for _, s in sorted([(self.EARLIER, 100), (self.LATER, 200)])],
                             [200, 100])

    def test_offsets_and_z_agree_on_the_instant(self):
        self.assertEqual(cb.parse_iso("2026-08-02T00:42:50Z"), cb.parse_iso(self.COMMIT))
        self.assertEqual(cb.parse_iso("2026-08-02T02:42:50+02:00"), cb.parse_iso(self.COMMIT))

    def test_unparseable_stamps_are_counted_not_silently_dropped(self):
        self.assertIsNone(cb.parse_iso("yesterday"))
        self.assertIsNone(cb.parse_iso(""))
        self.assertIsNone(cb.parse_iso("2026-02-30T00:00:00Z"))     # shape ok, date not

    def test_a_naive_stamp_is_read_as_utc(self):
        """Documented assumption, pinned so it is a decision rather than an accident."""
        self.assertEqual(cb.parse_iso("2026-08-02T00:42:50"), cb.parse_iso("2026-08-02T00:42:50Z"))


# ---------------------------------------------------------------------------------
# D3 — goodness of fit. The tool must not hand back a constant it cannot support.
# ---------------------------------------------------------------------------------

class TestFitGate(unittest.TestCase):

    def test_a_known_line_is_recovered_exactly(self):
        slope, inter, r2 = cb.linfit([(x, 3*x + 7) for x in range(1, 12)])
        self.assertAlmostEqual(slope, 3.0, places=9)
        self.assertAlmostEqual(inter, 7.0, places=9)
        self.assertAlmostEqual(r2, 1.0, places=9)

    def test_this_repos_own_four_way_fit_is_reproduced_from_its_recorded_points(self):
        """The 2026-08-15 `calibrate()` repair's table is a claim about arithmetic; this pins it.
        Points chosen so the corrected fit is strong and the scrambled one is not."""
        good = [(8519, 45000), (11064, 46000), (20000, 49000), (52909, 61000)]
        _, _, r2_good = cb.linfit(good)
        self.assertGreater(r2_good, 0.9)
        scrambled = [(8519, 61000), (11064, 45000), (20000, 46000), (52909, 49000)]
        _, _, r2_bad = cb.linfit(scrambled)
        self.assertLess(r2_bad, cb.MIN_R2)

    def test_no_regressor_variance_is_None_not_a_fabricated_line(self):
        self.assertIsNone(cb.linfit([(5, 1), (5, 2), (5, 3)]))

    def test_no_response_variance_leaves_r2_undefined_never_perfect(self):
        self.assertIsNone(cb.linfit([(1, 9), (2, 9), (3, 9)])[2])

    def test_the_floor_admits_and_refuses(self):
        self.assertIsNone(cb.calibration_verdict(0.3557, 0.8054, cb.MIN_R2))
        self.assertIsNotNone(cb.calibration_verdict(0.0678, 0.0503, cb.MIN_R2))

    def test_the_boundary_is_inclusive(self):
        """A floor that refused its own boundary value would be a different floor."""
        self.assertIsNone(cb.calibration_verdict(0.3557, cb.MIN_R2, cb.MIN_R2))
        self.assertIsNotNone(cb.calibration_verdict(0.3557, cb.MIN_R2 - 1e-9, cb.MIN_R2))

    def test_a_negative_slope_is_refused_however_tight_the_fit(self):
        """NARROWED-GUARD CHECK. An R²-only gate — the obvious weaker implementation —
        would accept this and print a NEGATIVE bytes-per-token."""
        self.assertIsNotNone(cb.calibration_verdict(-0.3557, 0.999, cb.MIN_R2))

    def test_an_undefined_r2_is_refused(self):
        self.assertIsNotNone(cb.calibration_verdict(0.3557, None, cb.MIN_R2))

    def test_the_refusal_says_which_test_failed(self):
        """A refusal that does not name its cause sends the reader back to the source."""
        self.assertIn("R²", cb.calibration_verdict(0.0678, 0.0503, cb.MIN_R2))
        self.assertIn("slope", cb.calibration_verdict(-0.3557, 0.999, cb.MIN_R2))

    def test_the_floor_is_configurable_per_project(self):
        self.assertIsNone(cb.calibration_verdict(0.3557, 0.30, 0.25))
        self.assertIsNotNone(cb.calibration_verdict(0.3557, 0.30, 0.75))


class TestFitGateEndToEnd(unittest.TestCase):
    """The unit gate above proves the verdict; this proves calibrate() ACTS on it — that
    a refused fit suppresses the number rather than printing it with a caveat beside it.

    It can only run where transcripts for this repository exist, which is a developer
    machine and not CI, so it skips rather than failing. Skipped is honest; asserting
    against whatever transcripts happen to be present would not be.
    """

    def setUp(self):
        slug = "-" + str(REPO).strip("/").replace("/", "-")
        self.tdir = Path.home() / ".claude" / "projects" / slug
        if not self.tdir.exists() or not any(self.tdir.glob("*.jsonl")):
            self.skipTest(f"no transcripts at {self.tdir}")
        cfgp = REPO / ".context-budget.json"
        if not cfgp.exists():
            self.skipTest("this repo has no .context-budget.json")
        self.cfg = json.loads(cfgp.read_text())
        # "Any transcript exists" is not "enough to fit". calibrate() refuses below its own
        # minimum (4 usable sessions; 3 sizes in history) and prints "not enough" — on a machine
        # with one or two transcripts for this path both tests below RAN and FAILED against
        # that message, while a worktree (different slug) skipped and a well-used clone passed.
        # Ask the tool rather than re-deriving its rule here: a probe at an impossible floor
        # either reaches the fit (and refuses the constant) or stops short of it.
        rc, out = self._run(1.01)
        if "not enough" in out:
            self.skipTest("transcripts present but below calibrate()'s fit minimum: "
                          + out.strip().splitlines()[-1])

    def _run(self, floor):
        import contextlib, io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cb.calibrate(str(REPO), {**self.cfg, "calibrate_min_r2": floor})
        return rc, buf.getvalue()

    def test_an_impossible_floor_suppresses_the_constant_entirely(self):
        rc, out = self._run(1.01)
        self.assertEqual(rc, cb.WARN)
        self.assertIn("no constant recommended", out)
        self.assertNotIn("bytes/token", out)

    def test_an_admitting_floor_prints_the_constant(self):
        """Presence control: without it, a calibrate() that never printed anything would
        pass the test above."""
        rc, out = self._run(0.0)
        self.assertEqual(rc, cb.CLEAN)
        self.assertIn("bytes/token", out)
        self.assertNotIn("no constant recommended", out)


# ---------------------------------------------------------------------------------
# D4 / D5 — what the ledger row and the remediation text say.
# ---------------------------------------------------------------------------------

class TestLedgerRow(unittest.TestCase):

    OVER_BYTES = {"class": "read-mandated", "lines": 359, "max_lines": 1200,
                  "bytes": 72449, "max_bytes": 65536, "status": "over",
                  "findings": [{"kind": "bytes", "msg": "x"}]}

    def test_a_read_mandated_file_over_BYTES_reports_bytes(self):
        self.assertEqual(cb.ledger_dimension(self.OVER_BYTES), ("72,449 B", "65,536 B"))

    def test_the_defect_it_replaces_named_the_ceiling_that_did_not_fire(self):
        """DRIVE IT RED against the narrowed implementation: class-only selection, which
        is what the tool did, reports lines for this row — the ceiling that passed."""
        r = self.OVER_BYTES
        by_class = (f"{r['lines']:,} ln" if r["class"] == "read-mandated"
                    else f"{r['bytes']:,} B")
        self.assertEqual(by_class, "359 ln")
        self.assertNotEqual(by_class, cb.ledger_dimension(r)[0])

    def test_a_read_mandated_file_over_LINES_still_reports_lines(self):
        r = {**self.OVER_BYTES, "lines": 1500,
             "findings": [{"kind": "lines", "msg": "x"}]}
        self.assertEqual(cb.ledger_dimension(r), ("1,500 ln", "1,200 ln"))

    def test_over_both_reports_bytes_deterministically(self):
        r = {**self.OVER_BYTES, "lines": 1500,
             "findings": [{"kind": "bytes", "msg": "x"}, {"kind": "lines", "msg": "y"}]}
        self.assertEqual(cb.ledger_dimension(r)[0], "72,449 B")

    def test_nothing_fired_falls_back_to_bytes_for_every_class(self):
        """2026-08-26 CHANGED THIS EXPECTATION; the change is the assertion. A read-mandated file
        used to fall back to LINES because that was the unit the surrounding trim rule was written
        in. The rule is byte-denominated now, and the cap it proxies always was token-denominated,
        so lines were the figure least able to explain the verdict -- across these same files the
        B/line spread is 8.6x against 1.33x for B/token. The class no longer selects a dimension
        at all; bytes are the fallback for everyone."""
        self.assertEqual(cb.ledger_dimension({**self.OVER_BYTES, "findings": [],
                                              "status": "ok"}), ("72,449 B", "65,536 B"))
        self.assertEqual(cb.ledger_dimension({"class": "resident", "bytes": 900,
                                              "lines": 9, "max_bytes": 1000,
                                              "findings": []}), ("900 B", "1,000 B"))

    def test_a_non_size_finding_does_not_hijack_the_dimension(self):
        """Unchanged in intent, re-pointed 2026-08-26: a `protected` finding still must not select
        a dimension, so the row falls through to the default -- which is now bytes. Paired with
        the line case below, so this cannot pass merely because everything reports bytes."""
        r = {**self.OVER_BYTES, "findings": [{"kind": "protected", "msg": "x"}]}
        self.assertEqual(cb.ledger_dimension(r)[0], "72,449 B")

    def test_a_line_finding_still_selects_lines(self):
        """The control that keeps the test above honest. 2026-08-26 moved the DEFAULT, not the
        dispatch: a fired `lines` ceiling must still be reported in lines, or the row would once
        again name a ceiling that did not fire -- the exact defect ledger_dimension exists for."""
        r = {**self.OVER_BYTES, "findings": [{"kind": "lines", "msg": "x"}]}
        self.assertEqual(cb.ledger_dimension(r), ("359 ln", "1,200 ln"))

    def test_an_undeclared_ceiling_renders_rather_than_crashing(self):
        """The pre-change expression formatted max_bytes unconditionally, so a resident
        file declaring only max_lines raised TypeError inside the renderer."""
        self.assertEqual(cb.ledger_dimension({"class": "resident", "bytes": 10,
                                              "lines": 1, "findings": []}), ("10 B", "—"))

    def test_the_resident_total_pseudo_row_renders(self):
        """main() appends a synthetic row that has no line count at all."""
        self.assertEqual(cb.ledger_dimension(
            {"path": "(resident total)", "class": "resident", "status": "over",
             "bytes": 20000, "max_bytes": 18600,
             "findings": [{"kind": "bytes", "msg": "x"}]}), ("20,000 B", "18,600 B"))


class TestRemediationText(unittest.TestCase):

    def test_no_remedy_names_a_directory_from_the_tools_home_project(self):
        """server/, mobile/*/ and database/ exist in no repository but the one the tool
        was written in, and were printed verbatim to every adopter."""
        for kind, remedies in cb.REMEDIES.items():
            for name, how in remedies:
                for token in ("server/", "mobile/", "database/"):
                    self.assertNotIn(token, how, f"{kind}/{name} names {token}")

    def test_measured_claims_are_attributed_not_deictic(self):
        """'10 of 11 rows of one table HERE were wrong' reads, in an adopter's terminal,
        as a claim about the adopter's own repository. It was never measured there."""
        compute = dict((n, h) for n, h in cb.REMEDIES["bytes"])["Compute"]
        self.assertIn("10 of 11", compute)
        self.assertNotIn("table here", compute)

    def test_raising_the_ceiling_is_still_offered_last(self):
        """Ordering is the message: it is the only remedy that removes the signal."""
        self.assertEqual(cb.REMEDIES["bytes"][-1][0], "Raise the ceiling")


class TestToolInvariants(unittest.TestCase):

    def test_the_tool_and_its_selftest_agree_the_gates_all_fire(self):
        p = subprocess.run([sys.executable, str(CB_PY), "--selftest"],
                           capture_output=True, text=True, cwd=str(REPO))
        rows = [l for l in p.stdout.splitlines() if l.strip().startswith(("PASS", "FAIL"))]
        self.assertGreater(len(rows), 30, "selftest row population collapsed")
        self.assertEqual([l for l in rows if l.strip().startswith("FAIL")], [])

    def test_there_is_still_no_force_escape_hatch(self):
        src = CB_PY.read_text().split("def selftest")[0]
        self.assertNotIn('"--force" in args', src)


class TestTokenCeiling(unittest.TestCase):
    """The ceiling is denominated in TOKENS, the unit the read cap is actually in.

    WHY THIS CLASS EXISTS. A byte ceiling is `tokens x density`, and density is a property
    of the content, so every compaction silently moves it. Measured on the authoring fork: the
    declared 73,728 B ceiling for starter-kit/FRAMEWORK_LEARNINGS.md certified `ok` a size
    the agent read tool REFUSES at 25,486 tokens, and four of the five configured ceilings
    converted to more than the 25,000-token cap. Nothing went red, because nothing checked.

    THE CLASS GATE IS THE LOAD-BEARING PART: the read cap binds a
    file that is read WHOLE. A file read in PART is not bound by it -- measured over 80
    transcripts, one such file was read whole once and in part 243 times. So an on-demand
    file must NOT be judged against the cap, and test_narrowing_* below shows that dropping
    the class gate gives the WRONG answer on the same fixture rather than merely a louder one.
    """

    def _spec(self, **kw):
        d = {"path": "t.md", "class": "read-mandated"}
        d.update(kw)
        return d

    # --- fixture proof -------------------------------------------------------------

    def test_fixture_is_what_the_other_tests_assume(self):
        """Prove the fixture BEFORE asserting anything about the code that reads it."""
        with tempfile.TemporaryDirectory() as d:
            Path(d, "t.md").write_bytes(b"x" * 60000)
            self.assertEqual(os.path.getsize(os.path.join(d, "t.md")), 60000)
            r = cb.measure_file(d, self._spec())
            self.assertEqual(r["bytes"], 60000, "fixture size must reach measure_file intact")
            self.assertEqual(r["class"], "read-mandated")

    # --- the guard that makes the shipped defect unrepresentable -------------------

    def test_a_max_tokens_above_the_read_cap_is_a_config_defect(self):
        cfg = {"read_cap_tokens": 25000}
        bad = cb.config_defects({"files": [self._spec(max_tokens=26000)]}, cfg)
        self.assertTrue(bad, "a ceiling above the read cap must be reported, not clamped silently")
        self.assertIn("26,000", " ".join(bad))

    def test_a_max_tokens_at_or_below_the_cap_is_clean(self):
        cfg = {"read_cap_tokens": 25000}
        self.assertEqual(cb.config_defects({"files": [self._spec(max_tokens=25000)]}, cfg), [])

    # --- the core check ------------------------------------------------------------

    def test_a_whole_read_file_over_its_token_ceiling_is_over(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "t.md").write_bytes(b"x" * 60000)
            r = cb.measure_file(d, self._spec(max_tokens=20000),
                                cfg={"bytes_per_token": 2.5})
            self.assertEqual(r["tokens"], 24000, "60,000 B / 2.5 = 24,000 tok")
            self.assertEqual(r["status"], "over")
            self.assertTrue([f for f in r["findings"] if f["kind"] == "tokens"])

    def test_a_whole_read_file_under_its_token_ceiling_is_ok(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "t.md").write_bytes(b"x" * 40000)
            r = cb.measure_file(d, self._spec(max_tokens=20000),
                                cfg={"bytes_per_token": 2.5})
            self.assertEqual(r["tokens"], 16000)
            self.assertEqual(r["status"], "ok")

    # --- the class gate, narrowed rather than merely deleted -----------------------

    def test_an_on_demand_file_is_not_judged_against_the_read_cap(self):
        """The cap binds a WHOLE read. One adopter ships a 1.2 MB on-demand file."""
        with tempfile.TemporaryDirectory() as d:
            Path(d, "t.md").write_bytes(b"x" * 900000)
            r = cb.measure_file(d, self._spec(**{"class": "on-demand", "max_tokens": 20000}),
                                cfg={"bytes_per_token": 2.5})
            self.assertIsNone(r.get("tokens"),
                              "an on-demand file must not be given a token verdict at all")
            self.assertEqual(r["status"], "ok")

    def test_narrowing_the_class_gate_to_all_classes_gives_the_wrong_answer(self):
        """The weaker implementation (no class gate) is shown WRONG on the same fixture."""
        self.assertNotIn("on-demand", cb.WHOLE_READ_CLASSES,
                         "on-demand inside WHOLE_READ_CLASSES would redden every "
                         "partially-read file -- the per-file-vs-per-row error itself")
        # A FROZEN LITERAL, not a set derived from the tuple -- deriving it would make this
        # an identity that no narrowing mutant can falsify. Widened DELIBERATELY on 2026-08-30 to
        # admit "read-set", the Phase 0 mandatory read pair (SESSION_RUNNER.md +
        # SAFEGUARDS.md). That pair is read WHOLE, which is exactly the condition
        # for the cap to bind, so gating it in BYTES ONLY would have reintroduced the density
        # drift the token arm exists to remove -- on the two files the read-set PR is about.
        # The assertion above is the one that carries this test's purpose and is unchanged:
        # "on-demand" must stay OUT.
        self.assertEqual(set(cb.WHOLE_READ_CLASSES),
                         {"resident", "read-mandated", "read-set"})

    # --- adopter compatibility: an un-migrated config keeps working ----------------

    def test_max_tokens_is_derived_from_max_bytes_when_absent(self):
        """Every shipped adopter config declares max_bytes and nothing else."""
        mt, derived = cb.token_ceiling({}, self._spec(max_bytes=45400))
        self.assertTrue(derived)
        self.assertEqual(mt, 20000, "45,400 / 2.27 = 20,000 -- derived at the FLOOR")

    def test_the_derived_ceiling_is_conservative_not_optimistic(self):
        """Dividing by the FLOOR maximises the token estimate, so it can never certify
        an unreadable file as fine. Direction matters and has been got wrong twice."""
        lo, _ = cb.token_ceiling({}, self._spec(max_bytes=100000))
        self.assertGreater(100000 / 2.27, 100000 / 2.89)
        self.assertEqual(lo, min(int(100000 / 2.27), 25000))

    def test_a_derived_ceiling_is_clamped_at_the_read_cap(self):
        """vscode_quarto_ext declares 65,536 B = 28,870 tok. It must not become a
        ceiling ABOVE the cap -- that is the defect being fixed."""
        mt, derived = cb.token_ceiling({}, self._spec(max_bytes=65536))
        self.assertTrue(derived)
        self.assertEqual(mt, 25000)

    def test_a_file_with_no_ceiling_of_either_kind_gets_no_token_verdict(self):
        mt, derived = cb.token_ceiling({}, self._spec())
        self.assertIsNone(mt)

    # --- density: per-file measured beats global beats floor -----------------------

    def test_a_per_file_measured_density_overrides_the_global(self):
        bpt, src = cb.file_density({"bytes_per_token": 2.8},
                                   self._spec(bytes_per_token=2.4193))
        self.assertAlmostEqual(bpt, 2.4193)
        self.assertEqual(src, "measured")

    def test_the_floor_is_used_when_nothing_is_declared(self):
        bpt, src = cb.file_density({}, self._spec())
        self.assertAlmostEqual(bpt, cb.MIN_BYTES_PER_TOKEN)
        self.assertEqual(src, "floor")

    # --- a green you cannot justify becomes a warn --------------------------------

    def test_a_file_that_has_drifted_from_its_measured_density_warns(self):
        """A 2026-08-27 compaction cut a file 23.6%; its density moved 3.0444 -> 2.8897, which is
        what inverted the ceiling. Drift past the threshold must stop the confident ok."""
        with tempfile.TemporaryDirectory() as d:
            Path(d, "t.md").write_bytes(b"x" * 40000)
            spec = self._spec(max_tokens=20000, bytes_per_token=2.5, measured_bytes=60000)
            r = cb.measure_file(d, spec, cfg={})
            self.assertEqual(r["status"], "warn",
                             "33% drift from the measured size must not report a bare ok")
            self.assertTrue([f for f in r["findings"] if f["kind"] == "density"])

    def test_no_drift_leaves_the_ok_intact(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "t.md").write_bytes(b"x" * 40000)
            spec = self._spec(max_tokens=20000, bytes_per_token=2.5, measured_bytes=40000)
            r = cb.measure_file(d, spec, cfg={})
            self.assertEqual(r["status"], "ok")

    # --- the second enforcement site must move with the first ---------------------

    def test_a_fired_token_ceiling_is_reported_in_tokens(self):
        """The row must show the figure behind its own verdict. A file UNDER its byte
        ceiling and OVER the read cap is the case bytes cannot explain."""
        r = {"class": "read-mandated", "bytes": 56673, "max_bytes": 73728,
             "tokens": 25514, "max_tokens": 25000,
             "findings": [{"kind": "tokens", "msg": "x"}]}
        self.assertEqual(cb.ledger_dimension(r), ("≈25,514 tok", "25,000 tok"))

    def test_bytes_still_win_when_both_fire(self):
        """The first size finding decides the dimension; bytes are appended first."""
        r = {"class": "read-mandated", "bytes": 162781, "max_bytes": 65536,
             "tokens": 65979, "max_tokens": 25000,
             "findings": [{"kind": "bytes", "msg": "x"}, {"kind": "tokens", "msg": "y"}]}
        self.assertEqual(cb.ledger_dimension(r)[0], "162,781 B")

    def test_main_passes_cfg_into_measure_file(self):
        """cfg is optional on measure_file so old callers keep working -- which means a
        caller that forgets it runs the token arm at the FLOOR and silently ignores every
        per-file measured density. Green tests would not have caught it; this does."""
        src = CB_PY.read_text()
        self.assertIn("measure_file(root, s, cfg)", src,
                      "main() must pass cfg, or the density and read_cap_tokens a "
                      "project declares are computed and then discarded")

    def test_precommit_enforces_the_token_ceiling_too(self):
        """The plan's own lesson: cfg['classes'] was a KeyError at BOTH sites. A gate that
        reports and cannot refuse is half a gate."""
        src = CB_PY.read_text()
        pre = src.split("def precommit")[1].split("# === SELFTEST")[0]
        self.assertIn("token_ceiling", pre,
                      "precommit still gates on bytes alone while the report gates on tokens")


# ---------------------------------------------------------------------------------
# D3 — the size a GATE measures. run() returns p.stdout.strip(), so precommit()'s
# `len(staged.encode())` measured one byte short on any content ending in a newline,
# which is all of it. The error is silent, self-consistent, and in the direction that
# makes an over-budget file look smaller than it is.
# ---------------------------------------------------------------------------------

def _stripped_size(repo, rev):
    """VERBATIM re-implementation of the pre-change measurement, kept so the defect can be
    exhibited rather than only described -- the same role `_string_size_at` plays for D2.
    This is what precommit() computed before blob_bytes() existed."""
    rc, out, _ = cb.run(["git", "show", rev], cwd=str(repo))
    return len(out.encode()) if rc == 0 else None


class TestBlobBytes(unittest.TestCase):
    """The gate's unit of measurement.

    WHY THIS CLASS EXISTS. A one-byte undercount sounds cosmetic. It is not: a ceiling is a
    strict `>` comparison, so a file at exactly ceiling+1 true bytes measures at exactly the
    ceiling and the gate ALLOWS it. The defect is therefore not "a slightly wrong number in
    a report" but "a commit that is over budget passes" -- exhibited below on a fixture
    built to sit on that edge, because a fixture 500 B over would be caught either way and
    would prove nothing about the boundary.
    """

    CEIL = 1000

    def _repo(self, d):
        """BIG.md at exactly CEIL+1 true bytes: CEIL 'x' plus one newline. HEAD holds a
        5-byte version, so the relative rule's `new > old` arm is satisfied and cannot be
        what decides these tests."""
        new_repo(d)
        Path(d, ".context-budget.json").write_text(json.dumps({
            "classes": {"resident": {"total_bytes": 999999}},
            "files": [{"path": "BIG.md", "class": "resident", "max_bytes": self.CEIL}]}))
        Path(d, "BIG.md").write_text("tiny\n")
        git(d, "add", "-A"); git(d, "commit", "-m", "base", when="2026-01-01T00:00:00Z")
        Path(d, "BIG.md").write_text("x" * self.CEIL + "\n")
        git(d, "add", "BIG.md")
        return d

    # --- fixture proof -------------------------------------------------------------

    def test_fixture_sits_exactly_one_byte_past_the_ceiling(self):
        """Prove the fixture BEFORE asserting anything about the code that reads it. If it
        drifts off the edge these tests keep passing while testing nothing about it."""
        with tempfile.TemporaryDirectory() as d:
            self._repo(d)
            true = int(git(d, "cat-file", "-s", ":BIG.md"))
            self.assertEqual(true, self.CEIL + 1,
                             "fixture must sit exactly one byte over, or the edge is untested")
            self.assertEqual(int(git(d, "cat-file", "-s", "HEAD:BIG.md")), 5)

    # --- the defect, exhibited ------------------------------------------------------

    def test_the_pre_change_expression_measures_one_byte_short(self):
        """RED: green is not evidence until red has been observed."""
        with tempfile.TemporaryDirectory() as d:
            self._repo(d)
            self.assertEqual(_stripped_size(d, ":BIG.md"), self.CEIL,
                             "the pre-change expression must land exactly ON the ceiling")

    def test_blob_bytes_reports_the_true_object_size(self):
        with tempfile.TemporaryDirectory() as d:
            self._repo(d)
            self.assertEqual(cb.blob_bytes(d, ":BIG.md"), self.CEIL + 1)
            self.assertEqual(cb.blob_bytes(d, "HEAD:BIG.md"), 5)

    def test_the_two_measurements_differ_by_exactly_the_trailing_newline(self):
        with tempfile.TemporaryDirectory() as d:
            self._repo(d)
            self.assertEqual(cb.blob_bytes(d, ":BIG.md") - _stripped_size(d, ":BIG.md"), 1)

    # --- and the one byte is enough to flip the verdict -----------------------------

    def test_one_byte_decides_whether_an_over_budget_commit_is_refused(self):
        """The whole point. Same fixture, same ceiling, opposite answers."""
        with tempfile.TemporaryDirectory() as d:
            self._repo(d)
            true, stripped = cb.blob_bytes(d, ":BIG.md"), _stripped_size(d, ":BIG.md")
            self.assertGreater(true, self.CEIL, "true size IS over the ceiling")
            self.assertFalse(stripped > self.CEIL,
                             "the pre-change size is NOT over it — so the gate passed")

    def test_precommit_now_refuses_that_commit(self):
        with tempfile.TemporaryDirectory() as d:
            self._repo(d)
            cfg = json.loads(Path(d, ".context-budget.json").read_text())
            self.assertEqual(cb.precommit(d, cfg), cb.BREACH)

    # --- the relative rule must survive the fix, or the gate blocks its own remedy ---

    def _restage(self, d, size):
        Path(d, "BIG.md").write_text("x" * size + "\n")
        git(d, "add", "BIG.md")

    def test_a_commit_that_shrinks_an_over_budget_file_still_passes(self):
        with tempfile.TemporaryDirectory() as d:
            self._repo(d)
            git(d, "commit", "-m", "over", "--no-verify", when="2026-01-02T00:00:00Z")
            self._restage(d, 900)
            cfg = json.loads(Path(d, ".context-budget.json").read_text())
            self.assertEqual(cb.blob_bytes(d, "HEAD:BIG.md"), self.CEIL + 1,
                             "fixture proof: HEAD really is the over-budget version")
            self.assertEqual(cb.precommit(d, cfg), cb.CLEAN)

    def test_a_commit_that_grows_an_already_over_budget_file_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            self._repo(d)
            git(d, "commit", "-m", "over", "--no-verify", when="2026-01-02T00:00:00Z")
            self._restage(d, 1500)
            cfg = json.loads(Path(d, ".context-budget.json").read_text())
            self.assertEqual(cb.precommit(d, cfg), cb.BREACH)

    # --- narrowing, not only deletion ----------------------------------------------

    def test_blob_bytes_is_none_rather_than_zero_for_a_rev_that_does_not_resolve(self):
        """None and 0 are different facts. A missing HEAD blob means 'new file', which the
        caller turns into 0; a helper that returned 0 itself would make 'absent' and
        'empty' the same, and an empty file would read as unchanged rather than as new."""
        with tempfile.TemporaryDirectory() as d:
            self._repo(d)
            self.assertIsNone(cb.blob_bytes(d, "HEAD:NOT_THERE.md"))
            self.assertIsNone(cb.blob_bytes(d, ":NOT_THERE.md"))
            Path(d, "EMPTY.md").write_text("")
            git(d, "add", "EMPTY.md")
            self.assertEqual(cb.blob_bytes(d, ":EMPTY.md"), 0,
                             "an EMPTY staged file is 0 bytes, which is not the same as absent")

    def test_blob_bytes_survives_content_that_is_not_valid_utf8(self):
        """The narrowed alternative does not merely give a wrong NUMBER here — it CRASHES.

        run() passes text=True, and subprocess decodes with the strict default, so a
        budgeted file that is not valid UTF-8 raises UnicodeDecodeError inside run(). That
        exception is not one of the four run() catches (FileNotFoundError, Timeout, OSError
        and its subclasses), so it propagates out of precommit() and takes the pre-commit
        hook — and therefore the commit — down with it. `git cat-file -s` never decodes,
        so it answers correctly instead. Found by running this test, not by predicting it.
        """
        with tempfile.TemporaryDirectory() as d:
            new_repo(d)
            Path(d, "B.bin").write_bytes(b"\xff\xfe\x00abc")
            git(d, "add", "B.bin")
            self.assertEqual(cb.blob_bytes(d, ":B.bin"), 6)
            with self.assertRaises(UnicodeDecodeError):
                _stripped_size(d, ":B.bin")

    def test_precommit_completes_on_a_repo_with_a_non_utf8_budgeted_file(self):
        """The end-to-end consequence of the line above: before the fix this call raised."""
        with tempfile.TemporaryDirectory() as d:
            new_repo(d)
            Path(d, "B.bin").write_bytes(b"\xff\xfe\x00abc")
            git(d, "add", "B.bin")
            cfg = {"classes": {"resident": {"total_bytes": 999999}},
                   "files": [{"path": "B.bin", "class": "resident", "max_bytes": 4}]}
            self.assertEqual(cb.precommit(d, cfg), cb.BREACH,
                             "6 B over a 4 B ceiling, measured without decoding")

    def test_crlf_content_loses_more_than_the_single_trailing_byte(self):
        """A SECOND, INDEPENDENT loss path, and the larger one. run() passes text=True, so
        subprocess applies universal-newline translation and every CRLF collapses to LF
        BEFORE .strip() takes the trailing one. Deleting .strip() would not have fixed
        this; not decoding at all does. The plan's 'one byte short' framing is the
        floor of the error, not its size."""
        with tempfile.TemporaryDirectory() as d:
            new_repo(d)
            Path(d, "CRLF.md").write_bytes(b"alpha\r\nbeta\r\n")   # 13 B on disk
            git(d, "add", "CRLF.md")
            self.assertEqual(cb.blob_bytes(d, ":CRLF.md"), 13)
            self.assertEqual(_stripped_size(d, ":CRLF.md"), 10,
                             "2 B to newline translation + 1 B to strip = 3 B lost")
            self.assertEqual(cb.blob_bytes(d, ":CRLF.md")
                             - _stripped_size(d, ":CRLF.md"), 3)

    def test_precommit_no_longer_measures_through_a_stripped_stdout(self):
        """Pin the call site, not just the helper: a later edit could reintroduce the
        stripped read beside a blob_bytes() that is still defined and no longer used."""
        src = CB_PY.read_text()
        pre = src.split("def precommit")[1].split("# === SELFTEST")[0]
        self.assertIn("blob_bytes(root", pre)
        self.assertNotIn("len(staged.encode())", pre)
        self.assertNotIn("len(head.encode())", pre)


# ---------------------------------------------------------------------------------
# D4 — cfg["classes"]["resident"] was a DIRECT key access at two sites. A config that
# declares no `classes` key raised KeyError, and an adopter's hand-written config is
# exactly the one that will lack it.
# ---------------------------------------------------------------------------------

def _direct_class_access(cfg):
    """VERBATIM re-implementation of the pre-change access, so the crash is exhibited."""
    return cfg["classes"]["resident"]


class TestClassSpec(unittest.TestCase):

    NO_CLASSES = {"files": [{"path": "CLAUDE.md", "class": "resident", "max_bytes": 100000}]}

    def test_the_pre_change_access_raises_on_a_config_with_no_classes_key(self):
        """RED."""
        with self.assertRaises(KeyError):
            _direct_class_access(self.NO_CLASSES)

    def test_class_spec_returns_an_empty_mapping_instead(self):
        self.assertEqual(cb.class_spec(self.NO_CLASSES, "resident"), {})
        self.assertEqual(cb.class_spec({"classes": None}, "resident"), {})
        self.assertEqual(cb.class_spec({"classes": {}}, "resident"), {})
        self.assertEqual(cb.class_spec(None, "resident"), {})

    def test_class_spec_returns_the_declared_budget_when_there_is_one(self):
        cfg = {"classes": {"resident": {"total_bytes": 34000, "warn_bytes": 30000}}}
        self.assertEqual(cb.class_spec(cfg, "resident")["total_bytes"], 34000)
        self.assertEqual(cb.class_spec(cfg, "read-mandated"), {},
                         "a class the config does not declare has no budget, not a crash")

    def test_neither_site_still_reaches_through_the_classes_key_directly(self):
        """Both sites had to move together or the crash relocates rather than closing.
        Scoped past the docstring that quotes the old expression on purpose."""
        src = CB_PY.read_text()
        code = src.split('def class_spec')[0] + src.split('    return ((cfg or {})')[1]
        self.assertNotIn('cfg["classes"]', code)

    def test_a_run_over_a_config_with_no_classes_key_completes(self):
        """End to end: the crash was in render() and main(), not in a helper."""
        with tempfile.TemporaryDirectory() as d:
            new_repo(d)
            Path(d, ".context-budget.json").write_text(json.dumps(self.NO_CLASSES))
            Path(d, "CLAUDE.md").write_text("hello\n")
            p = subprocess.run([sys.executable, str(CB_PY)], cwd=d,
                               capture_output=True, text=True)
            self.assertNotIn("KeyError", p.stderr)
            self.assertIn("resident total", p.stdout)
            self.assertIn("no ceiling declared", p.stdout,
                          "an undeclared ceiling must SAY so, not print a bare number")

    def test_the_over_ceiling_pseudo_row_is_still_labelled_resident_total(self):
        """A NON-VACUOUS WITNESS for the parenthesised label. It is emitted ONLY when the
        class is over its ceiling, and none of the three instrumented adopters is over --
        so an assertion taken against their output runs on an empty population and passes
        whatever the code does. This fixture is deliberately OVER so the row exists."""
        with tempfile.TemporaryDirectory() as d:
            new_repo(d)
            Path(d, ".context-budget.json").write_text(json.dumps({
                "classes": {"resident": {"total_bytes": 1000}},
                "files": [{"path": "CLAUDE.md", "class": "resident"}]}))
            Path(d, "CLAUDE.md").write_text("x" * 1500)
            p = subprocess.run([sys.executable, str(CB_PY), "--json"], cwd=d,
                               capture_output=True, text=True)
            rows = json.loads(p.stdout)
            paths = [r["path"] for r in rows["files"]]
            self.assertIn("(resident total)", paths,
                          "the pseudo-row must exist when the class is over")
            row = [r for r in rows["files"] if r["path"] == "(resident total)"][0]
            self.assertEqual(row["bytes"], 1500)
            self.assertEqual(row["status"], "over")
            self.assertIn("across all auto-loaded files", row["findings"][0]["msg"],
                          "the resident wording is what the adopters are compared on")

    def test_a_declared_ceiling_still_renders_exactly_as_before(self):
        """The byte-identity criterion, asserted on the rendered text rather than assumed:
        the instrumented adopters all declare a resident total, and their line must not
        move because a class they do not declare became representable."""
        with tempfile.TemporaryDirectory() as d:
            new_repo(d)
            Path(d, ".context-budget.json").write_text(json.dumps({
                "classes": {"resident": {"total_bytes": 34000}},
                "files": [{"path": "CLAUDE.md", "class": "resident", "max_bytes": 100000}]}))
            Path(d, "CLAUDE.md").write_text("x" * 4999 + "\n")
            p = subprocess.run([sys.executable, str(CB_PY)], cwd=d,
                               capture_output=True, text=True)
            plain = re.sub(r"\x1b\[[0-9;]*m", "", p.stdout)
            self.assertIn("resident total 5,000 B / 34,000 B ceiling", plain)


# ---------------------------------------------------------------------------------
# D5 — the class aggregate. Two per-file ceilings DO NOT SUM: bytes can move out of
# SAFEGUARDS.md into SESSION_RUNNER.md leaving both rows green while the Phase 0 read
# is unchanged. main() reports the total; precommit() must be able to REFUSE on it, or
# the tool ships an aggregate that reports and cannot gate.
# ---------------------------------------------------------------------------------

class TestClassTotals(unittest.TestCase):

    def _cfg(self, total=1000, **kw):
        c = {"classes": {"pair": dict({"total_bytes": total}, **kw)},
             "files": [{"path": "A.md", "class": "pair"},
                       {"path": "B.md", "class": "pair"}]}
        return c

    def _results(self, a, b, cls="pair"):
        return [{"path": "A.md", "class": cls, "bytes": a, "findings": [], "status": "ok"},
                {"path": "B.md", "class": cls, "bytes": b, "findings": [], "status": "ok"}]

    # --- the core arithmetic --------------------------------------------------------

    def test_a_class_total_is_the_sum_of_its_members(self):
        t = cb.class_totals(self._cfg(), self._results(400, 300))
        pair = [c for c in t if c["class"] == "pair"][0]
        self.assertEqual(pair["bytes"], 700)
        self.assertEqual(pair["status"], "ok")

    def test_the_total_fires_while_every_member_is_individually_green(self):
        """THE WHOLE POINT. Neither file has a per-file ceiling at all here, so nothing
        could have caught this except the aggregate."""
        t = cb.class_totals(self._cfg(total=1000), self._results(600, 600))
        pair = [c for c in t if c["class"] == "pair"][0]
        self.assertEqual(pair["bytes"], 1200)
        self.assertEqual(pair["status"], "over")

    def test_moving_bytes_between_members_leaves_the_total_unmoved(self):
        """The failure mode in one assertion: a transfer both per-file rows would allow.

        The first version of this test read `assertEqual(a, b, 1200)`, where unittest takes
        the third positional as the failure MESSAGE. It therefore asserted only that
        class_totals is symmetric under swapping member sizes — which addition is by
        construction — and stayed green against a mutant that halved every total.
        """
        a = cb.class_totals(self._cfg(), self._results(900, 300))
        b = cb.class_totals(self._cfg(), self._results(300, 900))
        self.assertEqual(a[-1]["bytes"], 1200)
        self.assertEqual(b[-1]["bytes"], 1200)
        self.assertEqual(a[-1]["bytes"], b[-1]["bytes"])

    def test_a_class_exactly_at_its_ceiling_is_not_over(self):
        """THE EDGE. `total > ceil` and `total >= ceil` agree on every fixture except a
        class sitting exactly ON the ceiling, so without this case the `>`/`>=` mutant
        survives the whole suite — it did, until this test was added."""
        t = cb.class_totals(self._cfg(total=1000), self._results(500, 500))
        pair = [c for c in t if c["class"] == "pair"][0]
        self.assertEqual(pair["bytes"], 1000)
        self.assertEqual(pair["status"], "ok", "at the ceiling is not over it")

    def test_one_byte_past_the_ceiling_is_over(self):
        """Paired control: without it, 'at the ceiling is ok' could be satisfied by a
        predicate that never fires at all."""
        t = cb.class_totals(self._cfg(total=1000), self._results(500, 501))
        self.assertEqual([c for c in t if c["class"] == "pair"][0]["status"], "over")

    def test_a_declared_ceiling_of_zero_is_still_a_ceiling(self):
        """`if ceil and ...` made a DECLARED 0 indistinguishable from an undeclared one,
        which silently disables the gate for a config that plainly declares it."""
        t = cb.class_totals({"classes": {"z": {"total_bytes": 0}}},
                            [{"path": "a", "class": "z", "bytes": 1,
                              "findings": [], "status": "ok"}])
        self.assertEqual(t[-1]["status"], "over")

    def test_a_declared_file_whose_name_starts_with_a_paren_is_counted(self):
        """The pseudo-row filter must key on a FLAG we set, never on a path the project
        supplies. Filtering on `path.startswith("(")` dropped this file from every class
        total while main()'s resident sum and precommit()'s arm still counted it."""
        t = cb.class_totals({"classes": {"pair": {"total_bytes": 1000}}},
                            [{"path": "(draft) notes.md", "class": "pair", "bytes": 1200,
                              "findings": [], "status": "ok"}])
        self.assertEqual(t[-1]["bytes"], 1200)
        self.assertEqual(t[-1]["status"], "over")

    def test_a_class_warn_line_is_read_rather_than_merely_declared(self):
        """The distributed SEED has carried classes.resident.warn_bytes since it shipped
        and NOTHING read it. A declared number no code consults is a false claim."""
        t = cb.class_totals(self._cfg(total=1000, warn_bytes=600), self._results(400, 300))
        self.assertEqual([c for c in t if c["class"] == "pair"][0]["status"], "warn")

    # --- narrowing, not only deleting -----------------------------------------------

    def test_a_declared_class_with_no_members_totals_zero_rather_than_vanishing(self):
        t = cb.class_totals({"classes": {"ghost": {"total_bytes": 10}}, "files": []}, [])
        self.assertIn("ghost", [c["class"] for c in t],
                      "a class that disappears when its files are renamed is a gate that "
                      "stops gating without saying so")
        self.assertEqual([c for c in t if c["class"] == "ghost"][0]["bytes"], 0)

    def test_pseudo_rows_are_not_counted_a_second_time(self):
        """main() appends `(pair total)` INTO results. A second call must not re-sum it."""
        res = self._results(600, 600) + [
            {"path": "(pair total)", "class": "pair", "bytes": 1200, "aggregate": True,
             "findings": [], "status": "over"}]
        self.assertEqual(cb.class_totals(self._cfg(), res)[-1]["bytes"], 1200,
                         "an aggregate-flagged row is this function's own output, "
                         "not a member")

    def test_resident_is_reported_even_when_the_config_declares_no_class(self):
        t = cb.class_totals({"files": []}, [])
        self.assertEqual([c["class"] for c in t], ["resident"])
        self.assertIsNone(t[0]["total_bytes"])

    def test_resident_leads_and_the_rest_are_alphabetical(self):
        """Deterministic, and NOT dict order — otherwise the rendered output depends on
        how the config happened to be typed."""
        cfg = {"classes": {"zeta": {}, "alpha": {}, "resident": {}}, "files": []}
        self.assertEqual([c["class"] for c in cb.class_totals(cfg, [])],
                         ["resident", "alpha", "zeta"])

    # --- a SYNTHETIC THIRD CLASS, the phase's own DONE criterion ---------------------

    def test_a_synthetic_third_class_totals_correctly(self):
        cfg = {"classes": {"resident": {"total_bytes": 100},
                           "pair": {"total_bytes": 1000},
                           "third": {"total_bytes": 50}},
               "files": []}
        res = (self._results(600, 600)
               + [{"path": "C.md", "class": "third", "bytes": 80,
                   "findings": [], "status": "ok"},
                  {"path": "D.md", "class": "third", "bytes": 5,
                   "findings": [], "status": "ok"},
                  {"path": "CLAUDE.md", "class": "resident", "bytes": 40,
                   "findings": [], "status": "ok"}])
        got = {c["class"]: (c["bytes"], c["status"]) for c in cb.class_totals(cfg, res)}
        self.assertEqual(got["resident"], (40, "ok"))
        self.assertEqual(got["pair"], (1200, "over"))
        self.assertEqual(got["third"], (85, "over"),
                         "the third class must be totalled on its OWN members, 80 + 5")


class TestPrecommitClassArm(unittest.TestCase):
    """A gate that reports and cannot refuse is half a gate (plan 3.4(b))."""

    CEIL = 1000

    def _repo(self, d, a, b):
        new_repo(d)
        Path(d, ".context-budget.json").write_text(json.dumps({
            "classes": {"pair": {"total_bytes": self.CEIL}},
            "files": [{"path": "A.md", "class": "pair"},
                      {"path": "B.md", "class": "pair"}]}))
        Path(d, "A.md").write_text("a" * a)
        Path(d, "B.md").write_text("b" * b)
        git(d, "add", "-A"); git(d, "commit", "-m", "base", when="2026-01-01T00:00:00Z")
        return json.loads(Path(d, ".context-budget.json").read_text())

    def _stage(self, d, a, b):
        Path(d, "A.md").write_text("a" * a)
        Path(d, "B.md").write_text("b" * b)
        git(d, "add", "-A")

    def test_fixture_starts_under_the_class_ceiling(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = self._repo(d, 400, 300)
            self.assertEqual(cb.precommit(d, cfg), cb.CLEAN)

    def test_a_commit_that_pushes_the_class_over_is_refused(self):
        """Neither file has a per-file ceiling, so ONLY the aggregate can catch this."""
        with tempfile.TemporaryDirectory() as d:
            cfg = self._repo(d, 400, 300)
            self._stage(d, 600, 600)
            self.assertEqual(cb.precommit(d, cfg), cb.BREACH)

    def test_a_commit_that_shrinks_an_over_budget_class_passes(self):
        """The relative rule on the aggregate: the gate must never block its own remedy.

        The interesting case is a commit that is STILL OVER the ceiling and merely smaller
        than HEAD. Shrinking to green would pass under any implementation and would prove
        nothing about the relative rule; this fixture is over on both sides.
        """
        with tempfile.TemporaryDirectory() as d:
            cfg = self._repo(d, 600, 600)
            self.assertEqual(cb.blob_bytes(d, "HEAD:A.md")
                             + cb.blob_bytes(d, "HEAD:B.md"), 1200)
            self.assertGreater(1200, self.CEIL,
                               "fixture proof: HEAD is already over the class ceiling")
            self._stage(d, 550, 550)                       # 1,100 — still over, but smaller
            self.assertGreater(1100, self.CEIL, "fixture proof: the remedy is still over")
            self.assertEqual(cb.precommit(d, cfg), cb.CLEAN,
                             "a reduction must pass even while the class stays over")

    def test_the_same_over_class_still_refuses_a_commit_that_grows_it(self):
        """Paired control for the test above: over-and-shrinking passes, over-and-growing
        does not. Without this pair, 'passes' could just mean 'never refuses'."""
        with tempfile.TemporaryDirectory() as d:
            cfg = self._repo(d, 600, 600)
            self._stage(d, 700, 600)                       # 1,300 — over and grown
            self.assertEqual(cb.precommit(d, cfg), cb.BREACH)

    def test_moving_bytes_between_members_is_refused_though_both_files_are_green(self):
        """The exact hole the aggregate exists to close, driven end to end."""
        with tempfile.TemporaryDirectory() as d:
            cfg = json.loads(json.dumps(self._repo(d, 400, 300)))
            for f in cfg["files"]:
                f["max_bytes"] = 5000          # per-file ceilings neither file can trip
            self._stage(d, 1100, 100)          # 1,200 total: over the CLASS ceiling only
            self.assertEqual(cb.precommit(d, cfg), cb.BREACH)

    def test_without_the_class_arm_that_same_commit_would_pass(self):
        """NARROW the guard rather than only deleting it: the weaker implementation —
        per-file ceilings alone — is shown to give the WRONG answer on the same fixture."""
        with tempfile.TemporaryDirectory() as d:
            cfg = json.loads(json.dumps(self._repo(d, 400, 300)))
            for f in cfg["files"]:
                f["max_bytes"] = 5000
            self._stage(d, 1100, 100)
            weaker = dict(cfg); weaker["classes"] = {}      # aggregate removed, nothing else
            self.assertEqual(cb.precommit(d, weaker), cb.CLEAN,
                             "per-file ceilings alone must be shown to MISS this")

    def test_deleting_a_member_is_credited_as_the_reduction_it_is(self):
        """THE REMEDY THE GATE MUST NOT BLOCK. Removing a member is the most direct way to
        shrink an over-budget class. The first version of this arm skipped any member
        absent from the WORKTREE before bookkeeping, so `git rm` dropped the member from
        the HEAD side too and the survivors read as pure growth: a measured 60,000 ->
        45,000 B reduction was REFUSED, reported as `30,000 -> 45,000`."""
        with tempfile.TemporaryDirectory() as d:
            cfg = self._repo(d, 30000, 30000)
            cfg["classes"]["pair"]["total_bytes"] = 40000
            self.assertEqual(cb.blob_bytes(d, "HEAD:A.md")
                             + cb.blob_bytes(d, "HEAD:B.md"), 60000)
            git(d, "rm", "-q", "B.md")
            Path(d, "A.md").write_text("a" * 45000)
            git(d, "add", "-A")
            self.assertEqual(cb.precommit(d, cfg), cb.CLEAN,
                             "60,000 -> 45,000 B is a reduction and must pass")

    def test_a_member_staged_but_absent_from_the_worktree_is_still_counted(self):
        """The mirror failure: the index is what gets committed. A member present in the
        index but deleted from disk was skipped and counted as ZERO, so an index holding
        1,800 B against a 1,000 B ceiling PASSED."""
        with tempfile.TemporaryDirectory() as d:
            cfg = self._repo(d, 100, 100)
            self._stage(d, 900, 900)
            os.remove(os.path.join(d, "B.md"))          # gone from disk, still in the index
            self.assertEqual(cb.blob_bytes(d, ":B.md"), 900,
                             "fixture proof: the index still holds B.md")
            self.assertEqual(cb.precommit(d, cfg), cb.BREACH,
                             "1,800 B against a 1,000 B ceiling must refuse")

    def test_a_rename_that_shrinks_the_class_passes(self):
        """The second entry point, found only by an adversarial reviewer. Here the deleted
        path is not a config member at all — the config was updated to name the new file —
        so the worktree fix does not reach it. The HEAD baseline must therefore be summed
        over HEAD'S OWN config, not today's, or every member that LEAVES a class takes its
        HEAD bytes out of the baseline the relative rule compares against."""
        with tempfile.TemporaryDirectory() as d:
            cfg = self._repo(d, 30000, 30000)
            cfg["classes"]["pair"]["total_bytes"] = 40000
            git(d, "mv", "B.md", "C.md")
            Path(d, "C.md").write_text("c" * 20000)     # 60,000 -> 50,000: a reduction
            cfg["files"] = [{"path": "A.md", "class": "pair"},
                            {"path": "C.md", "class": "pair"}]
            Path(d, ".context-budget.json").write_text(json.dumps(cfg))
            git(d, "add", "-A")
            self.assertEqual(cb.precommit(d, cfg), cb.CLEAN,
                             "a rename that shrinks the class must not be refused")

    def test_the_head_baseline_comes_from_heads_config_not_the_staged_one(self):
        """Pin the mechanism, not just the symptom."""
        src = CB_PY.read_text()
        pre = src.split("def precommit")[1].split("# === SELFTEST")[0]
        self.assertIn('f"HEAD:{CONFIG_NAME}"', pre,
                      "the baseline must consult HEAD's own declaration of the class")

    def test_an_undeclared_class_total_gates_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = self._repo(d, 600, 600)
            cfg["classes"]["pair"].pop("total_bytes")
            self.assertEqual(cb.precommit(d, cfg), cb.CLEAN)


class TestThisRepoReadSetPartition(unittest.TestCase):
    """The repo's OWN config declares the Phase 0 mandatory-read pair in TOKENS, one ceiling per
    file, and the two are meant to PARTITION the 25,000-token read cap: the pair fits one Read
    only if the per-file ceilings sum to no more than the cap. Nothing in the tool holds that
    sum — config_defects() checks each max_tokens against the cap singly — and the byte class
    ceiling that used to guard it (redundant by construction while the partition held) was
    dropped in PR #80's F3 fix. So the invariant lived in prose. Re-partitioning "by hand", which
    the config itself instructs when read_cap_tokens changes, had no check to fail (PR #80
    re-review, G1). RED first: with SESSION_RUNNER.md's ceiling raised 19,200 -> 22,000 the tool
    reported OK, config_defects [], and this suite passed 116/116."""

    def setUp(self):
        cfgp = REPO / ".context-budget.json"
        if not cfgp.exists():
            self.skipTest("this repo has no .context-budget.json")
        self.cfg = json.loads(cfgp.read_text())

    def _members_by_class(self):
        out = {}
        for spec in self.cfg.get("files", []):
            if spec.get("max_tokens") is not None:
                out.setdefault(spec.get("class"), []).append(spec)
        return out

    def test_whole_read_class_token_ceilings_partition_the_read_cap(self):
        cap = int(self.cfg.get("read_cap_tokens", cb.READ_CAP_TOKENS))
        checked = 0
        for cls, members in self._members_by_class().items():
            if cls not in cb.WHOLE_READ_CLASSES or len(members) < 2:
                continue
            total = sum(int(m["max_tokens"]) for m in members)
            self.assertLessEqual(
                total, cap,
                f"class {cls!r}: per-file max_tokens sum to {total:,} > the {cap:,}-token read "
                f"cap ({', '.join(m['path'] + '=' + str(m['max_tokens']) for m in members)}) — "
                f"every member can pass its own ceiling while the pair no longer fits one Read")
            checked += 1
        # Presence control: the assertion above is vacuous if no class qualifies. This repo's
        # read-set pair is the reason the test exists, so it must have been examined.
        self.assertGreaterEqual(checked, 1, "no whole-read class with >= 2 token-ceilinged "
                                            "members found — the partition was not checked")

    def test_the_read_set_pair_is_the_class_examined(self):
        members = self._members_by_class().get("read-set", [])
        self.assertEqual(sorted(m["path"] for m in members),
                         ["starter-kit/SAFEGUARDS.md", "starter-kit/SESSION_RUNNER.md"])


class TestReserveIdentity(unittest.TestCase):
    """framework_share := READ_CAP_BYTES - adopter_reserve_bytes, plan 3.4(c)."""

    def test_read_cap_bytes_is_computed_not_written(self):
        self.assertEqual(cb.READ_CAP_BYTES,
                         int(cb.READ_CAP_TOKENS * cb.MIN_BYTES_PER_TOKEN))
        self.assertEqual(cb.READ_CAP_BYTES, 56750)

    def test_it_agrees_with_the_trimmer_which_computes_it_the_same_way(self):
        """Two tools carrying the same cap must not drift by someone editing a literal."""
        src = (REPO / "starter-kit" / "methodology_trim.py").read_text()
        self.assertIn("READ_CAP_BYTES = int(READ_CAP_TOKENS * MIN_BYTES_PER_TOKEN)", src)

    def test_the_share_is_the_cap_minus_the_reserve(self):
        self.assertEqual(cb.framework_share({}), (56750, 0, 56750))
        self.assertEqual(cb.framework_share({"adopter_reserve_bytes": 28000}),
                         (28750, 28000, 56750))

    def test_a_derived_class_ceiling_ignores_the_written_number(self):
        """DERIVED, NOT PICKED: the computed value is what is in force."""
        ceil, derived = cb.class_ceiling({"adopter_reserve_bytes": 6750},
                                         {"total_bytes": 999, "derive_from_read_cap": True})
        self.assertTrue(derived)
        self.assertEqual(ceil, 50000)

    def test_a_written_ceiling_that_disagrees_with_the_derivation_is_reported(self):
        bad = cb.config_defects({"classes": {"read-set":
                                {"total_bytes": 999, "derive_from_read_cap": True}}})
        self.assertTrue(bad, "a number not in force must be reported, never silently used")
        self.assertIn("56,750", " ".join(bad))

    def test_a_written_ceiling_that_agrees_is_clean(self):
        self.assertEqual(cb.config_defects({"classes": {"read-set":
                         {"total_bytes": 56750, "derive_from_read_cap": True}}}), [])

    def test_a_reserve_that_consumes_the_whole_cap_is_reported(self):
        bad = cb.config_defects({"adopter_reserve_bytes": 56750})
        self.assertTrue(bad)
        self.assertIn("no file can satisfy", " ".join(bad))

    def test_a_negative_reserve_is_reported(self):
        self.assertTrue(cb.config_defects({"adopter_reserve_bytes": -1}))

    def test_the_identity_is_not_asserted_at_module_scope(self):
        """A module-scope assert runs at IMPORT, so a mutant violating it dies with a
        traceback BEFORE the code under test runs and is scored killed by the crash."""
        src = CB_PY.read_text()
        top = [l for l in src.splitlines()
               if l.startswith("assert ") or l.startswith("assert(")]
        self.assertEqual(top, [], f"module-scope assert(s) found: {top}")

    def test_config_defects_is_actually_called_by_the_tool(self):
        """It was defined, unit-tested, and NEVER RUN, while the distributed seed told
        adopters a max_tokens above the cap 'is rejected as a config defect'. A guard
        nothing calls is a comment shaped like a guard — and 'asserted at run time' is
        not true of a function with no call site."""
        src = CB_PY.read_text()
        # Scoped to the two function BODIES. Counting "config_defects(" across the whole
        # file matched three calls inside selftest() and one occurrence inside a comment,
        # so the guard stayed green with BOTH real call sites deleted — a guard whose net
        # is wider than its claim asserts nothing about the claim.
        def body_of(fn):
            """The body of one top-level def, ending at the next top-level def. `main()`
            lives AFTER the SELFTEST banner, so slicing the file at that banner drops it
            entirely — which is how the first version of this fix raised IndexError."""
            i = src.index(f"def {fn}(")
            rest = src[i:]
            m = re.search(r"\n(?=def |if __name__)", rest[1:])
            return rest[: m.start() + 1] if m else rest
        for name, chunk in (("main()", body_of("main")),
                            ("precommit()", body_of("precommit"))):
            code = [l for l in chunk.splitlines()
                    if "config_defects(" in l and not l.lstrip().startswith("#")]
            self.assertTrue(code, f"config_defects() is not called in {name}")

    def test_a_config_defect_makes_the_run_breach(self):
        with tempfile.TemporaryDirectory() as d:
            new_repo(d)
            Path(d, ".context-budget.json").write_text(json.dumps({
                "adopter_reserve_bytes": 99999,
                "files": [{"path": "CLAUDE.md", "class": "resident"}]}))
            Path(d, "CLAUDE.md").write_text("ok\n")
            p = subprocess.run([sys.executable, str(CB_PY)], cwd=d,
                               capture_output=True, text=True)
            self.assertEqual(p.returncode, cb.BREACH)
            self.assertIn("config defect", re.sub(r"\x1b\[[0-9;]*m", "", p.stdout))


if __name__ == "__main__":
    unittest.main(verbosity=1)
