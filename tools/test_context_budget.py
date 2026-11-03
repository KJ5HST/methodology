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
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

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

    def test_only_the_floor_refusal_names_the_floor(self):
        """TestFitGateEndToEnd tells a refusal the floor decided from one the data decided by
        this word. Were the floor's refusal to lose it, a calibrate() that ignored its floor
        would be skipped there instead of caught; were a data refusal to gain it, an honest
        skip would turn into a failure."""
        self.assertIn("floor", cb.calibration_verdict(0.0678, 0.0503, cb.MIN_R2))
        self.assertNotIn("floor", cb.calibration_verdict(-0.3557, 0.999, cb.MIN_R2))
        self.assertNotIn("floor", cb.calibration_verdict(0.3557, None, cb.MIN_R2))

    def test_the_floor_is_configurable_per_project(self):
        self.assertIsNone(cb.calibration_verdict(0.3557, 0.30, 0.25))
        self.assertIsNotNone(cb.calibration_verdict(0.3557, 0.30, 0.75))


class TestCalibrateFromALinkedWorktree(unittest.TestCase):
    """D9 (parallel-sessions plan): a linked `git worktree` has a path of its own, but its
    sessions belong to the same project — so --calibrate run there must look where the MAIN
    checkout's transcripts are. It derived the slug from the worktree's own path and reported
    `no transcripts at …` in the very isolation unit the plan recommends for parallel actors."""

    def test_a_linked_worktree_finds_the_main_checkouts_transcripts(self):
        import contextlib, io
        from unittest import mock
        with tempfile.TemporaryDirectory() as t:
            main, wt, home = Path(t) / "main", Path(t) / "wt", Path(t) / "home"
            main.mkdir(); home.mkdir()
            subprocess.run(["git", "init", "-q", "-b", "main", str(main)], check=True)
            git(main, "commit", "-q", "--allow-empty", "-m", "x")
            git(main, "worktree", "add", "-q", str(wt))
            slug = "-" + str(main.resolve()).strip("/").replace("/", "-")
            tdir = home / ".claude" / "projects" / slug
            tdir.mkdir(parents=True)
            (tdir / "s.jsonl").write_text('{"timestamp": "2026-10-01T00:00:00Z"}\n')
            buf = io.StringIO()
            with mock.patch.dict(os.environ, {"HOME": str(home)}), contextlib.redirect_stdout(buf):
                cb.calibrate(str(wt), {})
            self.assertNotIn("no transcripts at", buf.getvalue(),
                             "--calibrate from a linked worktree did not find the main checkout's transcripts")

    def test_the_main_checkout_and_its_worktree_share_one_transcript_dir(self):
        with tempfile.TemporaryDirectory() as t:
            main, wt = Path(t) / "main", Path(t) / "wt"
            main.mkdir()
            subprocess.run(["git", "init", "-q", "-b", "main", str(main)], check=True)
            git(main, "commit", "-q", "--allow-empty", "-m", "x")
            git(main, "worktree", "add", "-q", str(wt))
            self.assertEqual(cb.transcript_dir(str(wt)), cb.transcript_dir(str(main)))
            self.assertEqual(cb.transcript_dir(str(main)).name,
                             "-" + str(main.resolve()).strip("/").replace("/", "-"))

    def test_outside_a_repository_the_directory_itself_is_the_key(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(cb.transcript_dir(t).name, "-" + str(Path(t).resolve()).strip("/").replace("/", "-"))


class TestFitGateEndToEnd(unittest.TestCase):
    """The unit gate above proves the verdict; this proves calibrate() ACTS on it — that
    a refused fit suppresses the number rather than printing it with a caveat beside it.

    It can only run where transcripts for this repository exist, which is a developer
    machine and not CI, so it skips rather than failing. Skipped is honest; asserting
    against whatever transcripts happen to be present would not be.
    """

    def setUp(self):
        self.tdir = cb.transcript_dir(str(REPO))   # the tool's own key, so a worktree finds them too
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
        # either reaches the fit (and refuses the constant) or stops short of it. "Cannot fit"
        # is the same stop one step later: every usable session saw one size of the file, so
        # there is no line to fit. A stop the tool does not name falls through and FAILS below,
        # which is the safe direction — loud, never a silent skip.
        rc, out = self._run(1.01)
        if "not enough" in out or "cannot fit" in out:
            self.skipTest("transcripts present but calibrate() stops short of the fit: "
                          + out.strip().splitlines()[-1])
        # Reaching the fit is not enough either. The verdict refuses a non-positive slope or an
        # undefined R² at EVERY floor, so where this machine's transcripts fit that way (four
        # transcripts and a slope of −3.57 on 2026-09-16) the presence control below FAILED
        # whatever calibrate() did with the floor — the floor is this pair's only variable, and
        # there it decides nothing. So probe the admitting floor too: a refusal there that does
        # not cite the floor was decided by the data. One that DOES cite it is not skipped — at
        # 0.0 no defined R² falls below the floor, so it would mean calibrate() applied some
        # floor other than the one it was given, which is what this pair exists to catch.
        rc, out = self._run(0.0)
        refusal = [ln for ln in out.splitlines() if "no constant recommended" in ln]
        if refusal and "floor" not in refusal[0]:
            self.skipTest("the data refuse the fit at every floor, so the floor under test "
                          "decides nothing here: " + refusal[0].split(" — ", 1)[-1].strip(" ,"))

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


# ---------------------------------------------------------------------------------
# The command line. `--status` was cited as a command — in session receipts and as a
# proposed gate — while the tool had no such flag and ignored every argument it did not
# know, so each of those runs was the default measurement, history append included. A
# status read now measures and writes nothing, and an argument the tool does not know is
# refused before the tree is read. `--check` -- what an adopter's instructions type, and
# what the ledger trimmer calls its own report-only run -- is a second name for `--status`.
# Every other refusal names what the user most likely meant, where anything can be said.
# ---------------------------------------------------------------------------------

# Frozen here on purpose: a set derived from the code cannot be asserted to cover the code.
ACCEPTED_ARGUMENTS = frozenset({"install-hook", "--precommit", "--calibrate", "--selftest",
                                "--json", "--status", "--check", "--remote"})


class TestCommandLine(unittest.TestCase):

    def _project(self, d):
        """A committed project the tool can measure, with no history file yet. Proved clean
        before use; test_the_default_run_still_writes_its_row proves the same fixture
        writes, so an empty status after a run is a non-write, not a run that never got
        far enough to write."""
        new_repo(d)
        Path(d, ".context-budget.json").write_text(json.dumps({
            "classes": {"resident": {"total_bytes": 34000}},
            "files": [{"path": "CLAUDE.md", "class": "resident", "max_bytes": 100000}]}))
        Path(d, "CLAUDE.md").write_text("x" * 999 + "\n")
        git(d, "add", "-A")
        git(d, "commit", "-q", "-m", "baseline")
        self.assertEqual(self._dirt(d), "", "fixture: the project must start clean")

    def _run(self, d, *args):
        return subprocess.run([sys.executable, str(CB_PY), *args], cwd=d,
                              capture_output=True, text=True)

    def _dirt(self, d):
        """--ignored as well: upstream leaves the history file untracked, and an adopter
        may ignore it, so a write must show whichever way the project treats the file."""
        return git(d, "status", "--porcelain", "--ignored")

    def _rows(self, d):
        p = Path(d, cb.HISTORY_NAME)
        return len(p.read_text().splitlines()) if p.exists() else 0

    def test_status_prints_what_the_default_run_prints_and_only_the_default_run_appends(self):
        """--status runs FIRST: an append advances the growth-run counter, so the reverse
        order would compare two different counts rather than two different writes."""
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            self._run(d)
            Path(d, "CLAUDE.md").write_text("x" * 1999 + "\n")
            self.assertEqual(self._rows(d), 1, "fixture: one history row before")
            status = self._run(d, "--status")
            rows_after_status = self._rows(d)
            bare = self._run(d)
            self.assertEqual(rows_after_status, 1, "--status appended a history row")
            self.assertEqual(self._rows(d), 2,
                             "fixture: the size change is real, so the default run appends")
            self.assertEqual(status.stdout, bare.stdout)
            self.assertEqual(status.returncode, bare.returncode)

    def test_status_writes_nothing_with_or_without_json(self):
        for argv in (["--status"], ["--status", "--json"]):
            with self.subTest(argv=argv), tempfile.TemporaryDirectory() as d:
                self._project(d)
                p = self._run(d, *argv)
                self.assertNotIn("Traceback", p.stderr)
                self.assertEqual(self._dirt(d), "", f"{' '.join(argv)} wrote to the project")
                if "--json" in argv:
                    self.assertIn("files", json.loads(p.stdout))

    def test_the_default_run_still_writes_its_row(self):
        """PRESENCE CONTROL for the two above, on the same fixture."""
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            self._run(d)
            self.assertEqual(self._rows(d), 1)
            self.assertIn(cb.HISTORY_NAME, self._dirt(d))

    def test_check_is_status_under_a_second_name(self):
        """An adopter's session notes say "Re-measure (`python3 context_budget.py --check`)
        before writing more", and the ledger trimmer's --check means "report, never write".
        So --check is the status run: the same output and exit code, and no write. The
        fixture is the one the default run is shown writing to above."""
        for check, status in ((["--check"], ["--status"]),
                              (["--check", "--json"], ["--status", "--json"])):
            with self.subTest(argv=check), tempfile.TemporaryDirectory() as d:
                self._project(d)
                s = self._run(d, *status)
                c = self._run(d, *check)
                self.assertNotEqual(c.returncode, cb.USAGE, f"{' '.join(check)} was refused")
                self.assertEqual(c.stdout, s.stdout)
                self.assertEqual(c.returncode, s.returncode)
                self.assertEqual(self._dirt(d), "", f"{' '.join(check)} wrote to the project")

    def _assert_refused(self, arg):
        """Returns the refusal's own line, ANSI stripped, for the hint tests below."""
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            p = self._run(d, arg)
            out = re.sub(r"\x1b\[[0-9;]*m", "", p.stdout)
            self.assertEqual(p.returncode, cb.USAGE)
            self.assertIn(f"unknown argument: {arg}", out)
            self.assertIn("Usage:", out)
            self.assertEqual(self._dirt(d), "", f"a refused {arg} touched the project")
            # The config loads, so the 3 above came from the argument and not from a
            # missing or unreadable .context-budget.json, which exits 3 too.
            self.assertNotEqual(self._run(d).returncode, cb.USAGE)
        lines = [l for l in out.splitlines() if l.startswith("unknown argument:")]
        self.assertEqual(len(lines), 1, out)
        return lines[0]

    def test_an_unknown_argument_is_refused_and_touches_nothing(self):
        self._assert_refused("--zzz")

    def test_force_is_refused_like_any_other_unknown_argument(self):
        """The usage text says there is deliberately no --force. Until arguments were
        checked, passing it ran the default measurement, so nothing could observe that."""
        self._assert_refused("--force")

    def test_force_is_told_the_one_way_to_permit_growth(self):
        """Refused, and told where the decision it wanted is made."""
        self.assertIn(cb.CONFIG_NAME, self._assert_refused("--force"))

    def test_a_preview_or_a_do_it_flag_is_told_the_command_it_meant(self):
        """What the sibling tools use each for: --dry-run previews without writing (the
        dashboard), --run and --write do the real thing (the ratchet, the trimmer)."""
        self.assertIn("did you mean --status?", self._assert_refused("--dry-run"))
        for arg in ("--run", "--write"):
            with self.subTest(arg=arg):
                self.assertIn("run with no argument", self._assert_refused(arg))

    def test_a_misspelling_is_offered_the_command_it_is_closest_to(self):
        self.assertIn("did you mean --status?", self._assert_refused("--stauts"))

    def test_an_argument_like_nothing_accepted_is_offered_nothing(self):
        """CONTROL for the two above: the suggestion is not unconditional."""
        line = self._assert_refused("--zzz")
        self.assertEqual(line, "unknown argument: --zzz")

    def test_the_suggestion_cutoff_offers_version_nothing(self):
        """Pins the cutoff, measured rather than chosen: at difflib's default of 0.6,
        --version is offered --json, which is not what anyone typing it meant."""
        self.assertEqual(self._assert_refused("--version"), "unknown argument: --version")

    def test_each_unknown_argument_gets_its_own_line_and_its_own_hint(self):
        """They used to share one line, which has no room for a hint apiece."""
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            p = self._run(d, "--force", "--zzz")
            out = re.sub(r"\x1b\[[0-9;]*m", "", p.stdout)
            self.assertEqual(p.returncode, cb.USAGE)
            lines = [l for l in out.splitlines() if l.startswith("unknown argument:")]
            self.assertEqual(len(lines), 2, out)
            self.assertTrue(lines[0].startswith("unknown argument: --force "), lines[0])
            self.assertIn(cb.CONFIG_NAME, lines[0])
            self.assertEqual(lines[1], "unknown argument: --zzz")
            self.assertEqual(self._dirt(d), "")

    def test_the_accepted_arguments_are_exactly_the_frozen_set_and_all_documented(self):
        self.assertEqual(set(cb.ACCEPTED_ARGUMENTS), ACCEPTED_ARGUMENTS)
        usage = subprocess.run([sys.executable, str(CB_PY), "--help"],
                               capture_output=True, text=True).stdout
        for a in sorted(ACCEPTED_ARGUMENTS | {"-h", "--help"}):
            # Bounded, so "-h" is not found inside "--help" nor "--json" inside a longer flag.
            self.assertRegex(usage, rf"(?<![\w-]){re.escape(a)}(?![\w-])",
                             f"{a} is accepted but not in the usage text")

    def test_the_selftest_escape_hatch_check_still_reads_the_accepted_list(self):
        """The selftest refuses "--force" anywhere in the source before `def selftest`, and
        that is the one existing guard able to see the accepted list, which is why the list
        sits above it. It splits on the FIRST mention, so a second one earlier in the file --
        a comment is enough -- silently narrows the check to whatever lies above it. That
        happened while this list was being written, and --force added to it then passed the
        selftest."""
        src = CB_PY.read_text()
        self.assertEqual(src.index("def selftest"), src.index("\ndef selftest(") + 1,
                         "the check's split point is no longer the function itself")
        self.assertIn("ACCEPTED_ARGUMENTS = (", src.split("def selftest")[0])

    def test_help_still_wins_over_an_unknown_argument(self):
        """Run where there is no config at all: help reads nothing, so it needs none."""
        with tempfile.TemporaryDirectory() as d:
            p = self._run(d, "--help", "--zzz")
            self.assertEqual(p.returncode, cb.CLEAN)
            self.assertIn("Usage:", p.stdout)
            self.assertNotIn("unknown argument", p.stdout)


# ---------------------------------------------------------------------------------
# The growth-run advisory. Its second sentence was a literal -- "Nothing is over a
# ceiling yet" -- printed whenever the run fired, so a run whose headline read OVER, with
# four rows marked over, said nothing was. The sentence is now chosen by `worst`, the
# variable the headline prints, so the two cannot disagree.
# ---------------------------------------------------------------------------------

NOT_OVER_YET = "Nothing is over a ceiling yet — that is the point. Ceilings fire late."
FIRED_AS_WELL = "A ceiling has fired as well — see the rows marked over."


def _plain(text):
    """ANSI stripped and whitespace collapsed: the advisory wraps mid-sentence."""
    return " ".join(re.sub(r"\x1b\[[0-9;]*m", "", text).split())


class TestGrowthRunAdvisory(unittest.TestCase):

    # Every status render() ranks, lowest first. Frozen, not read from the tool.
    STATUSES = ("ok", "unmeasured", "warn", "instrument-failed", "over")

    def _row(self, status):
        row = {"path": "A.md", "class": "resident", "bytes": 1500, "lines": 1,
               "max_bytes": 1000, "status": status, "findings": []}
        if status == "unmeasured":
            row["reason"] = "file does not exist"
        if status == "over":
            row["findings"] = [{"kind": "bytes", "msg": "1,500 B exceeds the 1,000 B ceiling"}]
        return row

    def _render(self, status, run_hit):
        import contextlib, io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cb.render("/nonexistent", [self._row(status)], [], 12, run_hit, {},
                      {"resident_bytes": 1500}, totals=[])
        return _plain(buf.getvalue())

    def test_the_advisory_never_says_nothing_is_over_when_the_headline_says_over(self):
        """The matrix: every status render() can rank worst, with and without the run."""
        for status in self.STATUSES:
            for run_hit in (True, False):
                with self.subTest(worst=status, run_hit=run_hit):
                    out = self._render(status, run_hit)
                    # Prove the fixture: the headline reads the status this cell is about,
                    # and the advisory is printed exactly when the run fired.
                    self.assertIn(f"context budget {status.upper()} ", out)
                    self.assertEqual("growth run: 12 consecutive" in out, run_hit)
                    if status == "over":
                        self.assertNotIn("Nothing is over a ceiling", out)
                    if status == "over" and run_hit:
                        self.assertIn(FIRED_AS_WELL, out)

    def test_the_not_over_advisory_still_prints_the_original_sentence(self):
        """PRESENCE CONTROL for the matrix: without it, deleting the sentence outright
        would pass the assertion above. Every status below `over` keeps it word for word,
        instrument-failed included: the sentence follows the headline, and no row's status
        is over."""
        for status in self.STATUSES[:-1]:
            with self.subTest(worst=status):
                out = self._render(status, True)
                self.assertIn(NOT_OVER_YET, out)
                self.assertNotIn(FIRED_AS_WELL, out)

    def test_an_over_project_with_a_fired_growth_run_says_so_end_to_end(self):
        """The real main() -> render() path: a resident class over its total, a growth-run
        limit of 2, and a seeded history the current size extends to a run of 2."""
        with tempfile.TemporaryDirectory() as d:
            new_repo(d)
            Path(d, ".context-budget.json").write_text(json.dumps({
                "growth_run": 2,
                "classes": {"resident": {"total_bytes": 1000}},
                "files": [{"path": "CLAUDE.md", "class": "resident"}]}))
            Path(d, "CLAUDE.md").write_text("x" * 1500)
            Path(d, cb.HISTORY_NAME).write_text("".join(
                json.dumps({"resident_bytes": n, "files": {"CLAUDE.md": n}}) + "\n"
                for n in (1300, 1400)))
            p = subprocess.run([sys.executable, str(CB_PY)], cwd=d,
                               capture_output=True, text=True)
            out = _plain(p.stdout)
            self.assertNotIn("Traceback", p.stderr)
            self.assertIn("context budget OVER ", out, "fixture: the project must be over")
            self.assertIn("(resident total)", out, "fixture: the over row must exist")
            self.assertIn("growth run: 2 consecutive", out, "fixture: the run must fire")
            self.assertNotIn("Nothing is over a ceiling", out)
            self.assertIn(FIRED_AS_WELL, out)


# ---------------------------------------------------------------------------------
# Status precedence in measure_file(). Each check wrote the row's status in turn, so the
# last one to run won: a byte ceiling set `over`, then a structure pattern below its
# minimum overwrote it with `instrument-failed`, which render() ranks BELOW `over`. The
# headline followed the row, and the growth-run advisory said nothing was over a ceiling
# directly above the finding that said one was. A check may raise a status, never lower it.
# ---------------------------------------------------------------------------------

# No line of the fixture files below starts with "## ", so this pattern always fails.
FAILING_PATTERN = [{"pattern": "^## ", "expect_min": 1}]


class TestStatusPrecedence(unittest.TestCase):

    def _project(self, d):
        """A resident file over its byte ceiling that also fails a structure pattern, and a
        history the current size extends to a growth run of 2 against a limit of 2. No
        class total is declared, so the file's row is the only one that can be over."""
        new_repo(d)
        Path(d, ".context-budget.json").write_text(json.dumps({
            "growth_run": 2,
            "files": [{"path": "CLAUDE.md", "class": "resident", "max_bytes": 1000,
                       "structure": FAILING_PATTERN}]}))
        Path(d, "CLAUDE.md").write_text("x" * 1500)
        Path(d, cb.HISTORY_NAME).write_text("".join(
            json.dumps({"resident_bytes": n, "files": {"CLAUDE.md": n}}) + "\n"
            for n in (1300, 1400)))

    def _run(self, d, *args):
        return subprocess.run([sys.executable, str(CB_PY), *args], cwd=d,
                              capture_output=True, text=True)

    def _measure(self, d, **spec):
        """1,500 B in a class outside the token arm, so the byte and structure checks are
        the only two that can write the row's status."""
        Path(d, "t.md").write_text("x" * 1500)
        return cb.measure_file(d, {"path": "t.md", "class": "on-demand",
                                   "structure": FAILING_PATTERN, **spec})

    @staticmethod
    def _kinds(row):
        return sorted(f["kind"] for f in row["findings"])

    def test_a_row_over_its_ceiling_that_also_fails_a_pattern_reads_over_end_to_end(self):
        """The real main() -> render() path. The exit is BREACH either way; what changed is
        what the headline and the advisory say."""
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            p = self._run(d, "--status")
            out = _plain(p.stdout)
            self.assertNotIn("Traceback", p.stderr)
            # Prove the fixture: both checks fired, and the run fired.
            self.assertIn("1,500 B exceeds the 1,000 B ceiling", out)
            self.assertIn("fewer than the declared minimum", out)
            self.assertIn("growth run: 2 consecutive", out)
            self.assertIn("context budget OVER ", out)
            self.assertNotIn("Nothing is over a ceiling", out)
            self.assertIn(FIRED_AS_WELL, out)
            self.assertEqual(p.returncode, cb.BREACH)

    def test_the_json_report_gives_that_row_as_over(self):
        with tempfile.TemporaryDirectory() as d:
            self._project(d)
            p = self._run(d, "--status", "--json")
            self.assertNotIn("Traceback", p.stderr)
            row = json.loads(p.stdout)["files"][0]
            self.assertEqual(row["path"], "CLAUDE.md")
            self.assertIn("bytes", self._kinds(row), "fixture: the byte ceiling must fire")
            self.assertIn("instrument", self._kinds(row), "fixture: the pattern must fail")
            self.assertEqual(row["status"], "over")

    def test_a_row_that_only_fails_its_pattern_is_still_instrument_failed(self):
        """CONTROL: the guard must not stop the status being set at all."""
        with tempfile.TemporaryDirectory() as d:
            r = self._measure(d, max_bytes=2000)
            self.assertEqual(self._kinds(r), ["instrument"], "fixture: only the pattern fails")
            self.assertEqual(r["status"], "instrument-failed")

    def test_a_warn_row_that_fails_its_pattern_is_raised_to_instrument_failed(self):
        """Raising still works: `warn` ranks below `instrument-failed`."""
        with tempfile.TemporaryDirectory() as d:
            r = self._measure(d, max_bytes=2000, warn_bytes=1000)
            self.assertEqual(self._kinds(r), ["bytes", "instrument"])
            self.assertIn("warn line", r["findings"][0]["msg"],
                          "fixture: the byte finding must be the warn line, not a ceiling")
            self.assertEqual(r["status"], "instrument-failed")


# ---------------------------------------------------------------------------------
# A checkout nobody fetched reads as "current" (issue #100, finding 1). Both
# bin/status and the synced check trust the methodology checkout beside the project, so a
# checkout months behind its remote reports no drift. These tests ask whether that
# checkout is behind the newest release its remote lists. Every remote here is a local
# bare repository (offline, deterministic) or a script that never answers; nothing
# touches a network. What this file cannot show: real latency, HTTPS credential prompts,
# proxies, rate limits, a sandbox that blocks the network.
# ---------------------------------------------------------------------------------

def _copy_methodology(dest):
    """What a methodology checkout needs for bin/status to run from it: bin/status and
    its two siblings, and every distributed file (report() reads each one's canonical
    sha). context_budget.py is among the distributed files, and bin/status loads it."""
    spec = importlib.util.spec_from_file_location("_manifest", str(REPO / "bin" / "_manifest.py"))
    manifest = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(manifest)
    wanted = {"bin/status", "bin/_manifest.py", "bin/_manifest_reader.py",
              *(src for src, _dest, _disp in manifest.DISTRIBUTION)}
    for rel in sorted(wanted):
        target = Path(dest, rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, target)


def release_fixture(base, tags=("v1.0", "v1.1"), at="v1.0", methodology=False,
                    remote_drops=(), extra_tags=()):
    """Three repositories under `base`: `work` (the history: one untagged commit, then one
    commit per tag), `remote.git` (a bare clone of it, the remote) and `checkout` (a clone
    of the remote, detached at `at`). `remote_drops` are deleted from the remote AFTER the
    checkout cloned it, so the checkout holds a tag its remote lacks. Returns `checkout`."""
    base = Path(base)
    work = base / "work"
    work.mkdir()
    new_repo(work)
    if methodology:
        _copy_methodology(work)
        git(work, "add", "-A")
        git(work, "commit", "-q", "-m", "methodology files", when="2026-01-01T00:00:00Z")
    write_commit(work, "base.txt", 5, "2026-01-02T00:00:00Z")
    for i, tag in enumerate(tags):
        write_commit(work, "release.txt", 10 + i, f"2026-02-0{i + 1}T00:00:00Z", msg=f"release {tag}")
        git(work, "tag", tag)
    for tag in extra_tags:
        git(work, "tag", tag)
    git(base, "clone", "-q", "--bare", str(work), str(base / "remote.git"))
    git(base, "clone", "-q", str(base / "remote.git"), str(base / "checkout"))
    git(base / "checkout", "checkout", "-q", "--detach", at)
    for tag in remote_drops:
        git(base / "remote.git", "tag", "-d", tag)
    return base / "checkout"


def hotfix_fixture(base, hotfix_commits=5):
    """`checkout`, whose HEAD merges a hotfix line tagged v1.0.1 into main, which carries v1.1.
    The newest release reachable from HEAD is v1.1, but v1.0.1 is nearer in commits, so
    `git describe` names it. The remote is a bare clone and the checkout a clone of it."""
    base = Path(base)
    work = base / "work"
    work.mkdir()
    new_repo(work)
    write_commit(work, "base.txt", 5, "2026-01-01T00:00:00Z")
    write_commit(work, "release.txt", 10, "2026-01-02T00:00:00Z", msg="release v1.0")
    git(work, "tag", "v1.0")
    git(work, "checkout", "-q", "-b", "hotfix")
    for i in range(hotfix_commits):
        write_commit(work, "hot.txt", 20 + i, f"2026-01-0{3 + i}T00:00:00Z")
    git(work, "tag", "v1.0.1")
    git(work, "checkout", "-q", "main")
    write_commit(work, "release.txt", 30, "2026-01-10T00:00:00Z", msg="release v1.1")
    git(work, "tag", "v1.1")
    git(work, "merge", "-q", "--no-ff", "-m", "merge the hotfix", "hotfix", when="2026-01-11T00:00:00Z")
    git(base, "clone", "-q", "--bare", str(work), str(base / "remote.git"))
    git(base, "clone", "-q", str(base / "remote.git"), str(base / "checkout"))
    return base / "checkout"


def git_shim(base):
    """A `git` ahead of the real one on PATH that logs each call's argv, prefixed with the
    value of GIT_TERMINAL_PROMPT. Returns (env for a subprocess, the log's path)."""
    shim_dir = Path(base) / "shim"
    shim_dir.mkdir()
    log = Path(base) / "git-calls.log"
    shim = shim_dir / "git"
    shim.write_text('#!/bin/sh\nprintf "%s\\n" "$GIT_TERMINAL_PROMPT $*" >> "$GIT_SHIM_LOG"\n'
                    'exec "$REAL_GIT" "$@"\n')
    os.chmod(shim, 0o755)
    env = dict(os.environ, PATH=f"{shim_dir}{os.pathsep}{os.environ['PATH']}",
               GIT_SHIM_LOG=str(log), REAL_GIT=shutil.which("git"))
    env.pop("METHODOLOGY_REMOTE_CHECK", None)   # the shell suite exports it; a test of the check wants it on
    return env, log


def remote_calls(log):
    return ([line for line in Path(log).read_text().splitlines() if " ls-remote " in line]
            if Path(log).exists() else [])


def hang_remote(base, checkout, seconds=20):
    """Point `checkout`'s origin at an ssh URL whose ssh command never answers: a shell that
    starts a `sleep` of its own (a grandchild of git, holding git's pipes) and waits for it.
    Returns (env that makes git use it, the file naming the two pids of each call)."""
    pids = Path(base) / "hang.pids"
    script = Path(base) / "hang-ssh"
    script.write_text(f'#!/bin/sh\nsleep {seconds} &\necho "$$ $!" >> "{pids}"\nwait\n')
    os.chmod(script, 0o755)
    git(checkout, "remote", "set-url", "origin", "ssh://hang.invalid/x.git")
    env = dict(os.environ, GIT_SSH_COMMAND=str(script))
    env.pop("METHODOLOGY_REMOTE_CHECK", None)   # the shell suite exports it; bin/status must ask here
    return env, pids


def processes_gone(pids_file, wait=3.0):
    """True once every pid named in `pids_file` is gone. Polled: a killed process group is
    reaped a moment after the kill."""
    pids = [int(p) for p in Path(pids_file).read_text().split()]
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        if not [pid for pid in pids if _running(pid)]:
            return True
        time.sleep(0.1)
    return False


def _running(pid):
    """Neither gone nor a zombie. A killed process nobody has reaped yet (a container whose
    PID 1 does not reap) still answers signal 0, and it is not running."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    state = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True)
    return bool(state.stdout.strip()) and not state.stdout.strip().startswith("Z")


class TestProcessesGone(unittest.TestCase):
    """The helper the hanging-remote tests rely on must not read a zombie as running."""

    def _pids(self, tmp, pid):
        f = Path(tmp, "p.pids")
        f.write_text(f"{pid}\n")
        return f

    def test_a_process_that_has_exited_but_not_been_reaped_is_gone(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = subprocess.Popen(["true"])
            try:
                time.sleep(0.5)    # exited; nobody has waited for it: a zombie
                self.assertTrue(processes_gone(self._pids(tmp, p.pid), wait=1.0))
            finally:
                p.wait()

    def test_control_a_process_that_is_running_is_not_gone(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = subprocess.Popen(["sleep", "5"])
            try:
                self.assertFalse(processes_gone(self._pids(tmp, p.pid), wait=0.5))
            finally:
                p.kill()
                p.wait()


class TestReleaseOrdering(unittest.TestCase):
    """A release tag is `v` and integers separated by dots, ordered as a tuple of integers
    of any depth. As text v1.9 outranks v1.10; and a rule of `vN.N` would read a future
    v4.2.1 as no newer than v4.2 (this repository already has v2.6.1 and v3.0.1)."""

    def test_a_release_tag_reads_as_its_integers_and_nothing_else_does(self):
        for tag, key in (("v1.0", (1, 0)), ("v4.2.1", (4, 2, 1)), ("v10", (10,)),
                         ("v4.2-rc1", None), ("nightly", None), ("V4.2", None), ("v", None),
                         ("v4..2", None), ("4.2", None), ("v4.2.", None)):
            with self.subTest(tag=tag):
                self.assertEqual(cb.release_key(tag), key)

    def test_the_newest_release_is_chosen_by_integers_not_by_text(self):
        self.assertEqual(cb.newest_release(["v1.9", "v1.10", "v1.2"]), "v1.10")
        self.assertEqual(cb.newest_release(["v4.2", "v4.2.1", "v4.1.9"]), "v4.2.1")
        self.assertIsNone(cb.newest_release(["nightly", "v2.0-rc1"]))


class TestReleaseLag(unittest.TestCase):
    """release_lag(checkout) -> (message, reason): the message when the checkout's newest
    reachable release is older than the newest the remote lists, the reason when it could
    not tell, and (None, None) when the checkout is current or ahead."""

    BEHIND = "checkout at v1.0, newest release v1.1 (behind: git pull)"

    def _lag(self, **kw):
        with tempfile.TemporaryDirectory() as tmp:
            fx = release_fixture(tmp, **kw)
            self.assertEqual(git(fx, "remote", "get-url", "origin"), str(Path(tmp, "remote.git")),
                             "fixture: origin must be the local bare repository")
            return cb.release_lag(str(fx))

    def test_a_checkout_one_release_behind_is_told_so(self):
        self.assertEqual(self._lag(), (self.BEHIND, None))

    def test_a_current_checkout_and_one_ahead_of_its_remote_are_told_nothing(self):
        self.assertEqual(self._lag(at="v1.1"), (None, None))
        self.assertEqual(self._lag(at="v1.1", remote_drops=("v1.1",)), (None, None))

    def test_releases_are_ordered_as_integers_of_any_depth(self):
        self.assertEqual(self._lag(tags=("v1.9", "v1.10"), at="v1.9"),
                         ("checkout at v1.9, newest release v1.10 (behind: git pull)", None))
        self.assertEqual(self._lag(tags=("v1.1", "v1.1.1"), at="v1.1"),
                         ("checkout at v1.1, newest release v1.1.1 (behind: git pull)", None))

    def test_tags_that_are_not_releases_are_not_newer(self):
        self.assertEqual(self._lag(tags=("v1.0",), extra_tags=("v1.1-rc1", "nightly")),
                         (None, None))

    def test_the_checkouts_release_is_the_highest_it_contains_not_the_nearest_tag(self):
        """`git describe` names the tag nearest in commits. After a hotfix line is merged back
        that can be an older release than one HEAD also contains, and the checkout was told it
        was behind a release it already had."""
        with tempfile.TemporaryDirectory() as tmp:
            fx = hotfix_fixture(tmp)
            self.assertEqual(git(fx, "describe", "--tags", "--abbrev=0", "--match", "v[0-9]*"), "v1.0.1",
                             "fixture: the nearest tag is the older release")
            self.assertIn("v1.1", git(fx, "tag", "--merged", "HEAD").split(),
                          "fixture: the newer release is reachable from HEAD")
            self.assertEqual(cb.release_lag(str(fx)), (None, None))

    def test_a_nearer_pre_release_tag_does_not_hide_the_release_below_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = release_fixture(tmp, tags=("v1.0", "v1.1-rc1"), at="v1.1-rc1")
            self.assertEqual(git(fx, "describe", "--tags", "--abbrev=0", "--match", "v[0-9]*"), "v1.1-rc1",
                             "fixture: the nearest tag is the pre-release")
            self.assertEqual(cb.release_lag(str(fx)), (None, None))

    def test_a_directory_inside_another_repository_is_not_taken_for_a_checkout(self):
        """git -C walks up to an enclosing repository. A copy of the methodology files kept inside
        an application's repository would be reported with the application's tags."""
        with tempfile.TemporaryDirectory() as tmp:
            fx = release_fixture(tmp)
            self.assertEqual(cb.release_lag(str(fx)), (self.BEHIND, None), "control: the enclosing repository is behind")
            vendored = fx / "vendor" / "methodology"
            vendored.mkdir(parents=True)
            msg, why = cb.release_lag(str(vendored))
            self.assertIsNone(msg)
            self.assertIn("not the root", why)

    def test_a_directory_that_is_not_a_repository_says_so_and_does_not_blame_the_tags(self):
        with tempfile.TemporaryDirectory() as tmp:
            msg, why = cb.release_lag(tmp)
            self.assertIsNone(msg)
            self.assertNotIn("release tag", why)

    def test_a_checkout_that_cannot_be_compared_says_why_and_is_not_told_it_is_behind(self):
        msg, why = self._lag(at="v1.0~1")
        self.assertIsNone(msg)
        self.assertIn("release tag", why)
        msg, why = self._lag(tags=("v1.0",), remote_drops=("v1.0",))
        self.assertEqual((msg, "origin lists no release tag" in why), (None, True), why)
        msg, why = self._lag(tags=("v1.0-rc1",), at="v1.0-rc1")
        self.assertEqual((msg, "no release tag" in why), (None, True), why)
        with tempfile.TemporaryDirectory() as tmp:
            fx = release_fixture(tmp)
            git(fx, "remote", "remove", "origin")
            msg, why = cb.release_lag(str(fx))
            self.assertIsNone(msg)
            self.assertIn("origin", why)
            git(fx, "remote", "add", "origin", str(Path(tmp, "no-such-remote.git")))
            began = time.monotonic()
            msg, why = cb.release_lag(str(fx))
            self.assertIsNone(msg)
            self.assertTrue(why)
            self.assertLess(time.monotonic() - began, 3, "an unreachable remote must fail at once")

    def test_a_remote_that_never_answers_returns_within_the_timeout_and_leaves_nothing_running(self):
        """The ssh command here starts a `sleep` of its own, so the process holding git's pipes
        is a grandchild. subprocess.run(timeout=) kills git and then waits for those pipes to
        close: for the full 20 s of the sleep. The call must instead kill the whole group."""
        with tempfile.TemporaryDirectory() as tmp:
            fx = release_fixture(tmp)
            env, pids = hang_remote(tmp, fx)
            with mock.patch.dict(os.environ, env):
                began = time.monotonic()
                msg, why = cb.release_lag(str(fx), timeout=1)
                took = time.monotonic() - began
            self.assertTrue(pids.exists(), "fixture: the hanging ssh command must have started")
            self.assertIsNone(msg)
            self.assertIn("timed out", why)
            self.assertLess(took, 4, f"returned after {took:.1f} s against a 1 s timeout")
            self.assertTrue(processes_gone(pids), "the ssh command or its sleep is still running")

    def test_an_interrupt_kills_what_the_call_started(self):
        """The call starts git in its own session so that a timeout can kill the whole group; for
        the same reason a Ctrl-C reaches this process only. It must not leave git and ssh running."""
        real = subprocess.Popen
        made = []

        def spy(*a, **k):
            made.append(real(*a, **k))
            return made[-1]

        with mock.patch.object(subprocess, "Popen", spy), \
                mock.patch.object(real, "communicate", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                cb.run_bounded(["sleep", "30"])
        self.assertEqual(len(made), 1, "fixture: the call started one process")
        deadline = time.monotonic() + 3
        while made[0].poll() is None and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertIsNotNone(made[0].poll(), "the interrupted call left its child running")
        if made[0].poll() is None:
            made[0].kill()

    def test_ssh_is_asked_never_to_prompt_and_the_users_own_ssh_command_is_kept(self):
        """GIT_TERMINAL_PROMPT=0 does not stop an ssh prompt; BatchMode does. The option is
        ADDED to the command in force (the environment's, else core.sshCommand, else ssh), so a
        configured key is not replaced by the default one."""
        with tempfile.TemporaryDirectory() as tmp:
            fx = release_fixture(tmp)
            git(fx, "remote", "set-url", "origin", "ssh://nohost.invalid/x.git")
            log = Path(tmp, "ssh.log")
            fake = Path(tmp, "bin", "ssh")
            fake.parent.mkdir()
            fake.write_text(f'#!/bin/sh\nprintf "%s\\n" "$*" >> "{log}"\nexit 255\n')
            os.chmod(fake, 0o755)
            clean = {k: v for k, v in os.environ.items() if k not in ("GIT_SSH_COMMAND", "GIT_SSH")}
            # git prefers a global core.sshCommand to GIT_SSH: the user's own configuration must
            # not decide what this test sees
            clean.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", HOME=tmp)
            for how, expect, batch in (("neither", "nohost.invalid", True),
                                       ("env", "-i key-from-env", True),
                                       ("config", "-i key-from-config", True),
                                       ("wrapper", "nohost.invalid", False)):
                with self.subTest(how=how):
                    log.unlink(missing_ok=True)
                    env = dict(clean, PATH=f"{fake.parent}{os.pathsep}{clean['PATH']}")
                    if how == "env":
                        env["GIT_SSH_COMMAND"] = f"{fake} -i key-from-env"
                    if how == "config":
                        git(fx, "config", "core.sshCommand", f"{fake} -i key-from-config")
                    if how == "wrapper":      # a GIT_SSH program: no option can be added to it
                        git(fx, "config", "--unset", "core.sshCommand")
                        env["GIT_SSH"] = str(fake)
                    with mock.patch.dict(os.environ, env, clear=True):
                        msg, why = cb.release_lag(str(fx))
                    self.assertIsNone(msg)
                    self.assertTrue(why, "a failed ssh must read as not checked")
                    seen = log.read_text()
                    self.assertIn(expect, seen)
                    self.assertEqual("-o BatchMode=yes" in seen, batch, seen)


class TestRemoteFlag(unittest.TestCase):
    """context_budget.py --remote: the check is opt-in there, so Phase 0's --status makes no
    network call at every session start, and it is never run by --precommit."""

    MSG = "checkout at v1.0, newest release v1.1 (behind: git pull)"

    def _project(self, tmp, synced=True, **kw):
        """A committed project whose two synced files match the checkout's, so a synced row
        can only be `ok` and the remote row is the one thing that can change the verdict."""
        fx = release_fixture(tmp, methodology=True, **kw)
        proj = Path(tmp, "proj")
        proj.mkdir()
        new_repo(proj)
        cfg = {"classes": {"resident": {"total_bytes": 34000}},
               "files": [{"path": "CLAUDE.md", "class": "resident", "max_bytes": 100000}]}
        if synced:
            cfg["synced"] = [{"path": n, "canonical": f"../checkout/starter-kit/{n}"}
                             for n in ("SAFEGUARDS.md", "SESSION_RUNNER.md")]
            for n in ("SAFEGUARDS.md", "SESSION_RUNNER.md"):
                shutil.copy2(fx / "starter-kit" / n, proj / n)
        Path(proj, ".context-budget.json").write_text(json.dumps(cfg))
        Path(proj, "CLAUDE.md").write_text("x" * 999 + "\n")
        git(proj, "add", "-A")
        git(proj, "commit", "-q", "-m", "baseline")
        return fx, proj

    def _run(self, proj, env, *args):
        return subprocess.run([sys.executable, str(CB_PY), *args], cwd=proj, env=env,
                              capture_output=True, text=True)

    def test_the_default_run_makes_no_remote_call_and_a_stale_checkout_is_a_warn_with_the_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx, proj = self._project(tmp)
            env, log = git_shim(tmp)
            plain = self._run(proj, env, "--status")
            self.assertEqual((plain.returncode, remote_calls(log)), (cb.CLEAN, []),
                             "fixture: clean, and no remote call without --remote")
            self.assertNotIn("newest release", plain.stdout)
            flagged = self._run(proj, env, "--status", "--remote")
            self.assertNotIn("Traceback", flagged.stderr)
            self.assertIn(self.MSG, _plain(flagged.stdout))
            self.assertEqual(flagged.returncode, cb.WARN, "a stale checkout is a warn, never a breach")
            calls = remote_calls(log)
            self.assertEqual(len(calls), 1, "two synced files in ONE checkout are one remote call")
            self.assertTrue(calls[0].startswith("0 "), f"GIT_TERMINAL_PROMPT=0 missing: {calls[0]}")
            self.assertIn("-c protocol.version=0 ls-remote", calls[0],
                          "one round trip, not git's default two")

    def test_a_current_checkout_prints_nothing_and_changes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            _fx, proj = self._project(tmp, at="v1.1")
            env, log = git_shim(tmp)
            out = self._run(proj, env, "--status", "--remote")
            self.assertEqual((out.returncode, len(remote_calls(log))), (cb.CLEAN, 1))
            self.assertNotIn("newest release", out.stdout)
            self.assertNotIn("not checked", out.stdout)

    def test_precommit_never_asks_a_remote_even_when_told_to(self):
        with tempfile.TemporaryDirectory() as tmp:
            _fx, proj = self._project(tmp)
            env, log = git_shim(tmp)
            self._run(proj, env, "--status", "--remote")
            self.assertEqual(len(remote_calls(log)), 1, "control: --remote on --status does call")
            for argv in (["--precommit"], ["--precommit", "--remote"]):
                with self.subTest(argv=argv):
                    out = self._run(proj, env, *argv)
                    self.assertNotIn("Traceback", out.stderr)
                    self.assertEqual(len(remote_calls(log)), 1, f"{argv} made a remote call")

    def test_a_remote_that_never_answers_stops_neither_tool_and_the_exit_code_is_the_runs_own(self):
        """Both tools at once against one hanging remote, so the wait is paid once."""
        with tempfile.TemporaryDirectory() as tmp:
            fx, proj = self._project(tmp)
            env, pids = hang_remote(tmp, fx)
            bare = Path(tmp, "bare")
            bare.mkdir()
            began = time.monotonic()
            budget = subprocess.Popen([sys.executable, str(CB_PY), "--status", "--remote"], cwd=proj,
                                      env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            status = subprocess.Popen([sys.executable, str(fx / "bin" / "status"), "--source=local",
                                       str(bare)], env=env, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, text=True)
            budget_out, budget_err = budget.communicate(timeout=60)
            status_out, status_err = status.communicate(timeout=60)
            took = time.monotonic() - began
            self.assertNotIn("Traceback", budget_err + status_err)
            self.assertIn("remote not checked", _plain(budget_out))
            self.assertEqual(budget.returncode, cb.CLEAN)
            self.assertIn("SESSION_RUNNER.md", status_out, "bin/status still prints its table")
            self.assertIn("remote not checked: ", status_out)
            self.assertEqual(status.returncode, 0)
            self.assertLess(took, cb.REMOTE_TIMEOUT_SECONDS + 4)
            self.assertEqual(len(pids.read_text().splitlines()), 2, "fixture: both tools reached the remote")
            self.assertTrue(processes_gone(pids))

    def test_json_stays_json_and_carries_the_stale_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            _fx, proj = self._project(tmp)
            env, _log = git_shim(tmp)
            out = self._run(proj, env, "--status", "--remote", "--json")
            report = json.loads(out.stdout)
            stale = [r for r in report["synced"] if r["status"] == "warn"]
            self.assertEqual(len(stale), 1)
            self.assertIn(self.MSG, stale[0]["findings"][0]["msg"])
            self.assertEqual(report["remote_not_checked"], [])
            plain = json.loads(self._run(proj, env, "--status", "--json").stdout)
            self.assertNotIn("remote_not_checked", plain, "the key belongs to --remote runs")

    def test_a_synced_checkout_that_is_not_there_is_named_and_asks_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            _fx, proj = self._project(tmp)
            cfg = json.loads(Path(proj, ".context-budget.json").read_text())
            for spec in cfg["synced"]:
                spec["canonical"] = spec["canonical"].replace("../checkout/", "../nowhere/")
            Path(proj, ".context-budget.json").write_text(json.dumps(cfg))
            env, log = git_shim(tmp)
            out = self._run(proj, env, "--status", "--remote")
            self.assertNotIn("Traceback", out.stderr)
            self.assertIn("nowhere is not a directory", _plain(out.stdout))
            self.assertEqual(remote_calls(log), [])

    def test_the_flag_with_nothing_synced_says_so_and_asks_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            _fx, proj = self._project(tmp, synced=False)
            env, log = git_shim(tmp)
            out = self._run(proj, env, "--status", "--remote")
            self.assertIn("remote not checked: no synced file is declared", _plain(out.stdout))
            self.assertEqual(remote_calls(log), [])
            as_json = json.loads(self._run(proj, env, "--status", "--remote", "--json").stdout)
            self.assertEqual(as_json["remote_not_checked"], ["no synced file is declared"])


class TestStatusReleaseLag(unittest.TestCase):
    """bin/status checks by default (a person runs it), after the table, in local mode only:
    --source=github has just cloned the source, which is current by construction."""

    MSG = "checkout at v1.0, newest release v1.1 (behind: git pull)"

    def _status(self, fx, project, env=None, *args):
        if env is None:   # the shell suite exports METHODOLOGY_REMOTE_CHECK=0; these tests want the check on
            env = {k: v for k, v in os.environ.items() if k != "METHODOLOGY_REMOTE_CHECK"}
        return subprocess.run([sys.executable, str(fx / "bin" / "status"), "--source=local",
                               str(project), *args], env=env, capture_output=True, text=True)

    def test_a_stale_checkout_is_named_after_the_table_and_exit_stays_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = release_fixture(tmp, methodology=True)
            project = Path(tmp, "project")
            project.mkdir()
            out = self._status(fx, project)
            self.assertNotIn("Traceback", out.stderr)
            lines = out.stdout.rstrip().splitlines()
            self.assertEqual(lines[-1], f"warning: {self.MSG}")
            self.assertTrue(any(line.startswith("Project") for line in lines[:-1]),
                            "fixture: the table is printed before the warning")
            self.assertEqual(out.returncode, 0)
            self.assertEqual(cb.release_lag(str(fx))[0], self.MSG, "bin/status and the tool agree")
            self.assertFalse((fx / "starter-kit" / "__pycache__").exists(),
                             "loading the tool left bytecode in the checkout")

    def test_METHODOLOGY_REMOTE_CHECK_0_switches_the_check_off_without_a_word(self):
        """A run that must not touch the network (the shell suite calls bin/status about twenty times
        from a checkout whose origin may be GitHub) sets it. Any other value leaves the check on."""
        with tempfile.TemporaryDirectory() as tmp:
            fx = release_fixture(tmp, methodology=True)
            project = Path(tmp, "project")
            project.mkdir()
            env, log = git_shim(tmp)
            on = self._status(fx, project, env)
            self.assertEqual(len(remote_calls(log)), 1, "control: unset, it asks the remote once")
            self.assertIn("warning:", on.stdout)
            for value, asks in (("0", 0), ("1", 1)):
                with self.subTest(value=value):
                    Path(log).unlink(missing_ok=True)
                    out = self._status(fx, project, dict(env, METHODOLOGY_REMOTE_CHECK=value))
                    self.assertEqual(len(remote_calls(log)), asks)
                    self.assertEqual("warning:" in out.stdout, bool(asks))
                    if not asks:
                        self.assertNotIn("not checked", out.stdout)
                    self.assertIn("source: local", out.stdout, "the table is printed either way")
                    self.assertEqual(out.returncode, 0)

    def test_the_shell_suite_switches_the_check_off_for_its_own_calls(self):
        text = (REPO / "bin" / "tests.sh").read_text(encoding="utf-8")
        self.assertRegex(text, r"(?m)^export METHODOLOGY_REMOTE_CHECK=0$")

    def test_a_current_checkout_prints_no_warning_and_no_not_checked_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = release_fixture(tmp, methodology=True, at="v1.1")
            project = Path(tmp, "project")
            project.mkdir()
            out = self._status(fx, project)
            self.assertIn("source: local", out.stdout)
            self.assertNotIn("warning:", out.stdout)
            self.assertNotIn("not checked", out.stdout)

    def test_a_tool_that_cannot_be_loaded_is_not_checked_not_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = release_fixture(tmp, methodology=True)
            project = Path(tmp, "project")
            project.mkdir()
            (fx / "starter-kit" / "context_budget.py").write_text("this is not python (\n")
            out = self._status(fx, project)
            self.assertNotIn("Traceback", out.stderr)
            self.assertEqual(out.returncode, 0)
            self.assertIn("remote not checked: ", out.stdout)

    def test_the_github_source_has_just_cloned_so_it_asks_no_remote(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = release_fixture(tmp, methodology=True)
            project = Path(tmp, "project")
            project.mkdir()
            env, log = git_shim(tmp)
            env["METHODOLOGY_SOURCE_URL"] = f"file://{Path(tmp, 'remote.git')}"
            out = subprocess.run([sys.executable, str(fx / "bin" / "status"), "--source=github",
                                  str(project)], env=env, capture_output=True, text=True)
            self.assertIn("source: github", out.stdout, out.stdout + out.stderr)
            self.assertIn(" clone ", Path(log).read_text(), "fixture: the shim saw the clone")
            self.assertEqual(remote_calls(log), [])
            self.assertNotIn("warning:", out.stdout)


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


# The classes whose files are read TOGETHER, in one Read. Only the Phase 0 pair is: the other
# whole-read classes (cb.WHOLE_READ_CLASSES) are read whole, but one file per Read.
READ_TOGETHER_CLASSES = ("read-set",)


def token_partition(cfg):
    """(violations, checked) for the classes whose files must fit ONE Read together.

    A class's per-file max_tokens partition the read cap only if its files are read in the same
    Read. Each violation is (class, total, cap, members); checked counts the classes examined."""
    cap = int(cfg.get("read_cap_tokens", cb.READ_CAP_TOKENS))
    by_class = {}
    for spec in cfg.get("files", []):
        if spec.get("max_tokens") is not None:
            by_class.setdefault(spec.get("class"), []).append(spec)
    violations, checked = [], 0
    for cls, members in by_class.items():
        if cls not in READ_TOGETHER_CLASSES or len(members) < 2:
            continue
        total = sum(int(m["max_tokens"]) for m in members)
        if total > cap:
            violations.append((cls, total, cap, members))
        checked += 1
    return violations, checked


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

    def test_the_read_set_token_ceilings_partition_the_read_cap(self):
        violations, checked = token_partition(self.cfg)
        for cls, total, cap, members in violations:
            self.fail(
                f"class {cls!r}: per-file max_tokens sum to {total:,} > the {cap:,}-token read "
                f"cap ({', '.join(m['path'] + '=' + str(m['max_tokens']) for m in members)}) — "
                f"every member can pass its own ceiling while the pair no longer fits one Read")
        # Presence control: the assertion above is vacuous if no class qualifies. This repo's
        # read-set pair is the reason the test exists, so it must have been examined.
        self.assertGreaterEqual(checked, 1, "no read-set class with >= 2 token-ceilinged "
                                            "members found — the partition was not checked")

    def test_the_read_set_pair_is_the_class_examined(self):
        members = [s for s in self.cfg.get("files", [])
                   if s.get("class") == "read-set" and s.get("max_tokens") is not None]
        self.assertEqual(sorted(m["path"] for m in members),
                         ["starter-kit/SAFEGUARDS.md", "starter-kit/SESSION_RUNNER.md"])


class TestTokenPartitionRule(unittest.TestCase):
    """Only files read in the SAME Read share the cap. The Phase 0 pair (class read-set) is read
    together; a read-mandated or resident file is read whole but on its own, so two of them at
    25,000 tokens each are two full Reads, not one Read over its cap. Summing every whole-read
    class refused exactly that config. RED first: under the every-class sum, the two tests below
    that declare a read-mandated pair at 25,000 each failed (50,000 > 25,000)."""

    @staticmethod
    def _cfg(*files):
        return {"files": [{"path": p, "class": c, "max_tokens": t} for p, c, t in files]}

    def test_separately_read_files_do_not_share_the_cap(self):
        cfg = self._cfg(("A.md", "read-mandated", 25_000), ("B.md", "read-mandated", 25_000),
                        ("C.md", "resident", 20_000), ("D.md", "resident", 20_000))
        self.assertEqual(token_partition(cfg), ([], 0))

    def test_a_read_set_pair_past_the_cap_is_still_refused(self):
        cfg = self._cfg(("R.md", "read-set", 19_200), ("S.md", "read-set", 6_000))
        violations, checked = token_partition(cfg)
        self.assertEqual(checked, 1)
        self.assertEqual([(v[0], v[1], v[2]) for v in violations], [("read-set", 25_200, 25_000)])

    def test_a_read_set_pair_within_the_cap_passes(self):
        cfg = self._cfg(("R.md", "read-set", 18_222), ("S.md", "read-set", 6_777),
                        ("A.md", "read-mandated", 25_000), ("B.md", "read-mandated", 25_000))
        self.assertEqual(token_partition(cfg), ([], 1))

    def test_a_read_set_pair_at_exactly_the_cap_fits(self):
        cfg = self._cfg(("R.md", "read-set", 19_000), ("S.md", "read-set", 6_000))
        self.assertEqual(token_partition(cfg), ([], 1))


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
