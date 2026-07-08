#!/usr/bin/env python3
"""Functional tests for methodology_dashboard.py scoring — focused on the BL-5 doc-only reshape.

Canonical-only (NOT in bin/_manifest.py; adopters never receive it). Run:

    python3 tools/test_methodology_dashboard.py

Design notes:
- Import ONLY the tools/ module (via importlib); byte-compare the starter-kit/ twin with
  filecmp — never import it, so no starter-kit/__pycache__ is generated.
- `sys.dont_write_bytecode = True` is set before the import, so no __pycache__ at all.
- The pure scoring helpers are driven with synthetic metrics/files dicts + tempfile trees; this
  is the first functional coverage of score_health / assess_risks / the doc-only detection.
"""

import sys
sys.dont_write_bytecode = True

import filecmp
import importlib.util
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS_PY = os.path.join(HERE, "methodology_dashboard.py")
STARTER_PY = os.path.join(os.path.dirname(HERE), "starter-kit", "methodology_dashboard.py")

_spec = importlib.util.spec_from_file_location("methodology_dashboard_under_test", TOOLS_PY)
md = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(md)


def files(src=0, docs_loc=0, docs_count=0):
    """A minimal files["by_category"] shape for detect_doc_only."""
    return {"by_category": {"source": {"loc": src, "count": 1 if src else 0},
                            "docs": {"loc": docs_loc, "count": docs_count}}}


def base_metrics(**over):
    """A complete-enough metrics dict for score_health / assess_risks; override nested keys by
    passing a dict (shallow-merged) or replace top-level keys outright."""
    m = {
        "git": {"days_since_last_commit": 1, "total_commits": 50,
                "project_age_days": 100, "branch_count": 1},
        "tests": {"test_file_count": 0, "test_to_source_ratio": 0.0,
                  "source_loc": 0, "test_loc": 0},
        "ci": {"has_ci": False, "workflow_count": 0},
        "docs": {"readme_quality": "good", "has_docs_dir": True, "has_changelog": False,
                 "has_license": True, "has_roadmap": False, "has_todo": False,
                 "has_readme": True, "doc_to_source_ratio": 0.0, "doc_total_loc": 5000},
        "methodology": {"compliance_score": 0, "items": {}},
        "coverage_configs": [],
        "changelog": {"present": False, "is_fresh": False, "signals": []},
        "files": {"largest_files": []},
        "vulnerabilities": {},
        "render": {"score": 0, "toolchain_present": False,
                   "render_dep_verified": False, "signals": []},
        "doc_only": {"is_doc_only": False, "reason": ""},
    }
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(m.get(k), dict):
            m[k] = {**m[k], **v}
        else:
            m[k] = v
    return m


def risk_descs(metrics):
    return [r["description"] for r in md.assess_risks(metrics)]


class TestDetection(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.p = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()

    def test_mixed_repo_not_doc_only(self):
        # The core constraint: a mixed tooling repo (real code that should be tested) stays code.
        r = md.detect_doc_only(self.p, files(src=4500, docs_loc=900, docs_count=40),
                               {"toolchain_present": False})
        self.assertFalse(r["is_doc_only"])
        self.assertEqual(r["reason"], "heuristic")

    def test_markdown_research_is_doc_only(self):
        r = md.detect_doc_only(self.p, files(src=0, docs_loc=800, docs_count=12),
                               {"toolchain_present": False})
        self.assertTrue(r["is_doc_only"])
        self.assertEqual(r["reason"], "heuristic")

    def test_pure_latex_research_via_toolchain(self):
        # .tex/.qmd aren't counted as docs, so doc_loc≈0; only toolchain_present rescues it.
        r = md.detect_doc_only(self.p, files(src=0, docs_loc=0, docs_count=0),
                               {"toolchain_present": True})
        self.assertTrue(r["is_doc_only"])

    def test_empty_repo_not_doc_only(self):
        r = md.detect_doc_only(self.p, files(0, 0, 0), {"toolchain_present": False})
        self.assertFalse(r["is_doc_only"])

    def test_source_cap_boundary(self):
        render = {"toolchain_present": False}
        self.assertTrue(md.detect_doc_only(self.p, files(src=200, docs_count=5), render)["is_doc_only"])
        self.assertFalse(md.detect_doc_only(self.p, files(src=201, docs_count=5), render)["is_doc_only"])

    def test_marker_code_forces_not_doc_only(self):
        (self.p / md.DOC_ONLY_MARKER).write_text("code\n")
        r = md.detect_doc_only(self.p, files(src=0, docs_loc=800, docs_count=12),
                               {"toolchain_present": True})
        self.assertFalse(r["is_doc_only"])
        self.assertEqual(r["reason"], "marker")

    def test_marker_doc_only_forces_doc_only(self):
        (self.p / md.DOC_ONLY_MARKER).write_text("doc-only\n")
        r = md.detect_doc_only(self.p, files(src=4500, docs_loc=0, docs_count=0),
                               {"toolchain_present": False})
        self.assertTrue(r["is_doc_only"])
        self.assertEqual(r["reason"], "marker")

    def test_marker_unknown_token_falls_through(self):
        (self.p / md.DOC_ONLY_MARKER).write_text("banana\n")
        r = md.detect_doc_only(self.p, files(src=4500), {"toolchain_present": False})
        self.assertFalse(r["is_doc_only"])
        self.assertEqual(r["reason"], "heuristic")

    def test_marker_with_utf8_bom_is_honored(self):
        # A BOM-prefixed marker (Notepad-authored) must still be read as the token, not silently
        # dropped to the heuristic (which would flip to the opposite of the owner's request).
        (self.p / md.DOC_ONLY_MARKER).write_bytes(b"\xef\xbb\xbfcode\n")
        r = md.detect_doc_only(self.p, files(src=0, docs_loc=800, docs_count=12),
                               {"toolchain_present": True})
        self.assertFalse(r["is_doc_only"])
        self.assertEqual(r["reason"], "marker")


class TestRenderMetrics(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.p = Path(self._td.name)
        self.files = files(src=0, docs_loc=800, docs_count=12)
        self.ci = {"workflow_files": []}
        self.meth = {"items": {}}

    def tearDown(self):
        self._td.cleanup()

    def _score(self):
        return md.collect_render_metrics(self.p, self.files, self.ci, self.meth)

    def test_none_scores_zero(self):
        r = self._score()
        self.assertEqual(r["score"], 0)
        self.assertFalse(r["toolchain_present"])
        self.assertFalse(r["render_dep_verified"])

    def test_toolchain_only(self):
        (self.p / "_quarto.yml").write_text("project:\n  type: book\n")
        r = self._score()
        self.assertTrue(r["toolchain_present"])
        self.assertEqual(r["score"], 4)  # +4 toolchain, no driver/dep/ci/artifact

    def test_render_dep_check_flag(self):
        (self.p / "Makefile").write_text("render:\n\tpdffonts out.pdf\n")
        r = self._score()
        self.assertTrue(r["render_dep_verified"])   # pdffonts token
        # +2 driver (Makefile) +4 dep check = 6
        self.assertEqual(r["score"], 6)

    def test_all_signals_score_twenty(self):
        (self.p / "_quarto.yml").write_text("format:\n  pdf:\n    mainfont: TeX Gyre\n")
        (self.p / "Makefile").write_text("all:\n\tquarto render\n\tpdffonts out.pdf\n")
        (self.p / ".lycheeignore").write_text("http://x\n")
        (self.p / "CITATION.cff").write_text("cff-version: 1.2.0\n")
        (self.p / "RESEARCH_DOCUMENTATION_WORKSTREAM.md").write_text("# ws\n")
        r = self._score()
        # A: toolchain 4 + driver 2 | B: pdffonts 4 + mainfont 2 | C: render-ci 3 + lychee 2
        # | D: CITATION.cff 2 + workstream 1  => 20
        self.assertEqual(r["score"], 20)

    def test_score_capped_at_twenty(self):
        # Even with redundant signals the score never exceeds 20.
        (self.p / "_quarto.yml").write_text("mainfont: X\n")
        (self.p / "Makefile").write_text("quarto render\npdffonts a\nfc-list\nkpsewhich b\n")
        (self.p / ".lycheeignore").write_text("x\n")
        (self.p / "lychee.toml").write_text("x\n")
        (self.p / "CITATION.cff").write_text("x\n")
        (self.p / "refs.bib").write_text("@book{a}\n")
        (self.p / "RESEARCH_DOCUMENTATION_WORKSTREAM.md").write_text("x\n")
        # Exact-value lock (not the tautological `<= 20`): redundant signals must still land on 20,
        # so a broken bucket weight / regex / double-count moves it off 20 and fails.
        self.assertEqual(self._score()["score"], 20)


class TestScoreHealth(unittest.TestCase):
    def test_doc_only_fills_testing_slot_with_render_score(self):
        m = base_metrics(doc_only={"is_doc_only": True}, render={"score": 14})
        self.assertEqual(md.score_health(m)["testing"], 14)

    def test_code_repo_testing_ladder_regression_lock(self):
        # ratio 0.35 -> 16 on the classic ladder; must be unchanged for a code repo.
        m = base_metrics(tests={"test_to_source_ratio": 0.35, "test_file_count": 5, "source_loc": 1000})
        self.assertEqual(md.score_health(m)["testing"], 16)

    def test_all_dims_bounded_and_total_is_sum(self):
        for m in (base_metrics(doc_only={"is_doc_only": True}, render={"score": 11}),
                  base_metrics(tests={"test_to_source_ratio": 0.6, "test_file_count": 9, "source_loc": 500})):
            s = md.score_health(m)
            dims = ["activity", "testing", "documentation", "ci_cd", "methodology"]
            for d in dims:
                self.assertGreaterEqual(s[d], 0)
                self.assertLessEqual(s[d], 20)
            self.assertEqual(s["total"], sum(s[d] for d in dims))
            self.assertLessEqual(s["total"], 100)


class TestRiskReshaping(unittest.TestCase):
    def test_no_test_infra_suppressed_when_doc_only(self):
        m = base_metrics(doc_only={"is_doc_only": True},
                         render={"score": 0}, tests={"test_file_count": 0, "source_loc": 0})
        descs = risk_descs(m)
        self.assertNotIn("No test infrastructure", descs)
        self.assertTrue(any("no detectable render/verification pipeline" in d for d in descs))

    def test_no_test_infra_kept_for_mixed_repo(self):
        m = base_metrics(tests={"test_file_count": 0, "source_loc": 3000})
        self.assertIn("No test infrastructure", risk_descs(m))

    def test_helper_loc_risk_when_doc_only_has_small_source(self):
        m = base_metrics(doc_only={"is_doc_only": True},
                         render={"score": 8, "toolchain_present": True, "render_dep_verified": True},
                         tests={"test_file_count": 0, "source_loc": 150})
        self.assertTrue(any("150 LOC of helper source" in d for d in risk_descs(m)))

    def test_large_file_ext_filter(self):
        doc_big = base_metrics(files={"largest_files": [{"loc": 2500, "ext": ".md", "path": "chap.md"}]})
        self.assertFalse(any("Large files detected" in d for d in risk_descs(doc_big)))
        src_big = base_metrics(files={"largest_files": [{"loc": 2500, "ext": ".py", "path": "big.py"}]})
        self.assertTrue(any("Large files detected" in d for d in risk_descs(src_big)))

    def test_large_file_source_not_masked_by_nonsource_number_one(self):
        # A big lockfile/JSON at rank #1 must not hide a genuine large source file below it.
        m = base_metrics(files={"largest_files": [
            {"loc": 15000, "ext": ".json", "path": "package-lock.json"},
            {"loc": 3000, "ext": ".py", "path": "app.py"},
        ]})
        descs = risk_descs(m)
        self.assertTrue(any("Large files detected" in d and "app.py" in d for d in descs))

    def test_render_dep_advisory_fires_when_toolchain_unverified(self):
        # anti-pattern #20: toolchain present but no post-render dependency check wired.
        m = base_metrics(doc_only={"is_doc_only": True},
                         render={"score": 6, "toolchain_present": True, "render_dep_verified": False},
                         tests={"test_file_count": 0, "source_loc": 0})
        self.assertTrue(any("no post-render dependency check" in d for d in risk_descs(m)))

    def test_render_dep_advisory_silent_when_verified(self):
        m = base_metrics(doc_only={"is_doc_only": True},
                         render={"score": 12, "toolchain_present": True, "render_dep_verified": True},
                         tests={"test_file_count": 0, "source_loc": 0})
        self.assertFalse(any("no post-render dependency check" in d for d in risk_descs(m)))


class TestFmtRatioAndTwins(unittest.TestCase):
    def test_fmt_ratio(self):
        self.assertEqual(md.fmt_ratio(0.0, 0, True), "n/a (doc-only)")    # actually doc-only
        self.assertEqual(md.fmt_ratio(0.0, 0, False), "n/a (no source)")  # code repo, no source
        self.assertNotIn("doc-only", md.fmt_ratio(0.0, 0))                # default is NOT doc-only
        self.assertEqual(md.fmt_ratio(0.25, 400, False), "0.250")

    def test_twins_byte_identical(self):
        self.assertTrue(filecmp.cmp(TOOLS_PY, STARTER_PY, shallow=False),
                        "tools/ and starter-kit/ dashboards must be byte-identical")

    def test_dashboard_version(self):
        self.assertEqual(md.DASHBOARD_VERSION, "2.8.0")
        starter_src = Path(STARTER_PY).read_text(encoding="utf-8")
        self.assertTrue(re.search(r'^DASHBOARD_VERSION\s*=\s*"2\.8\.0"', starter_src, re.MULTILINE),
                        "starter-kit twin must also declare DASHBOARD_VERSION 2.8.0")


class TestEndToEnd(unittest.TestCase):
    """Exercise the WIRED path (collect_all -> render/detect/score/risk + render_project_card) so a
    wiring or card-display regression cannot pass while every pure-helper test stays green."""

    def _repo(self, files_map):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        p = Path(td.name)
        subprocess.run(["git", "init", "-q", str(p)], check=True)
        for name, content in files_map.items():
            fp = p / name
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(content)
        subprocess.run(["git", "-C", str(p), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(p), "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-q", "-m", "init"], check=True)
        return p

    def test_doc_only_tree_end_to_end(self):
        p = self._repo({
            "chapter1.md": "# Ch1\n" + "prose line\n" * 400,
            "chapter2.md": "# Ch2\n" + "prose line\n" * 400,
            "_quarto.yml": "format:\n  pdf:\n    mainfont: TeX Gyre\n",
            "Makefile": "render:\n\tquarto render\n\tpdffonts out.pdf\n",
        })
        m = md.collect_all(p)
        self.assertTrue(m["doc_only"]["is_doc_only"])
        # The Testing slot is filled by the render score end to end.
        self.assertEqual(m["scores"]["health"]["testing"], m["render"]["score"])
        self.assertGreater(m["render"]["score"], 0)
        self.assertFalse(any("No test infrastructure" in r["description"]
                             for r in m["scores"]["risks"]))
        card = md.render_project_card(m)
        self.assertIn("Render / Verification (proxy)", card)
        self.assertIn("infrastructure proxy", card)
        self.assertNotIn("<h4>Testing</h4>", card)

    def test_code_tree_end_to_end_keeps_testing(self):
        p = self._repo({
            "app.py": "def f():\n    return 1\n" * 150,   # ~300 source LOC -> over the 200 cap
            "test_app.py": "def test_f():\n    assert True\n" * 10,
            "README.md": "# app\n" * 5,
        })
        m = md.collect_all(p)
        self.assertFalse(m["doc_only"]["is_doc_only"])
        card = md.render_project_card(m)
        self.assertIn("<h4>Testing</h4>", card)
        self.assertNotIn("Render / Verification", card)


if __name__ == "__main__":
    unittest.main(verbosity=2)
