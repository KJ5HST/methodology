#!/usr/bin/env python3
"""Functional tests for methodology_dashboard.py scoring — the BL-5 doc-only reshape plus the
signal-integrity campaign, whose ratified plan lives on the fork's `main` only:
https://github.com/rmsharp/methodology/blob/main/docs/planning/dashboard-signal-integrity-plan.md

Canonical-only (NOT in bin/_manifest.py; adopters never receive it). Run:

    python3 tools/test_methodology_dashboard.py

Design notes:
- Import ONLY the tools/ module (via importlib); byte-compare the starter-kit/ twin with
  filecmp — never import it, so no starter-kit/__pycache__ is generated.
- `sys.dont_write_bytecode = True` is set before the import, so no __pycache__ at all.
- The pure scoring helpers are driven with synthetic metrics/files dicts + tempfile trees; this
  is the first functional coverage of score_health / assess_risks / the doc-only detection.
- Campaign tests are written RED-FIRST: every defect-proving assertion was run against unpatched
  code and watched to FAIL before the scanner was touched, because the suite was green against
  all eight filed and unfiled defects (a test that passes against the bug is not coverage — plan
  §8 learning 2). The remaining campaign tests are regression locks and guard-the-guard checks,
  which are expected to pass both before and after; they are marked as such where it is not
  obvious from the name.
"""

import sys
sys.dont_write_bytecode = True

import contextlib
import filecmp
import copy
import importlib.util
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS_PY = os.path.join(HERE, "methodology_dashboard.py")
STARTER_PY = os.path.join(os.path.dirname(HERE), "starter-kit", "methodology_dashboard.py")
STARTER_CONTEXT_BUDGET = os.path.join(os.path.dirname(HERE), "starter-kit", "context_budget.py")

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
        "methodology": {"compliance_score": 0, "compliance_pct": 0, "items": {}},
        "coverage_configs": [],
        "changelog": {"present": False, "is_fresh": False, "signals": []},
        # `read_cap_watch` is indexed directly by the D4(b) risk, not `.get`-with-default: a silent
        # default is exactly how a signal in this scanner went permanently unreachable with no test
        # failing. So it must exist here. base_metrics shallow-merges top-level keys only, so every
        # existing caller passing files={"largest_files": [...]} keeps read_cap_watch == [].
        "files": {"largest_files": [], "read_cap_watch": []},
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
        # .tex isn't counted as docs (.qmd/.rmd are in DOC_EXTS, but .tex stays out), so
        # doc_loc≈0; only toolchain_present rescues it. Real-scan proof: TestFrameworkInstalledExclusion
        # .test_a_pure_quarto_repo_below_doc_thresholds_still_doc_only_via_toolchain.
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
        (self.p / md.PROFILE_MARKER).write_text("code\n")
        r = md.detect_doc_only(self.p, files(src=0, docs_loc=800, docs_count=12),
                               {"toolchain_present": True})
        self.assertFalse(r["is_doc_only"])
        self.assertEqual(r["reason"], "marker")

    def test_marker_doc_only_forces_doc_only(self):
        (self.p / md.PROFILE_MARKER).write_text("doc-only\n")
        r = md.detect_doc_only(self.p, files(src=4500, docs_loc=0, docs_count=0),
                               {"toolchain_present": False})
        self.assertTrue(r["is_doc_only"])
        self.assertEqual(r["reason"], "marker")

    def test_marker_unknown_token_falls_through(self):
        (self.p / md.PROFILE_MARKER).write_text("banana\n")
        r = md.detect_doc_only(self.p, files(src=4500), {"toolchain_present": False})
        self.assertFalse(r["is_doc_only"])
        self.assertEqual(r["reason"], "heuristic")

    def test_marker_with_utf8_bom_is_honored(self):
        # A BOM-prefixed marker (Notepad-authored) must still be read as the token, not silently
        # dropped to the heuristic (which would flip to the opposite of the owner's request).
        (self.p / md.PROFILE_MARKER).write_bytes(b"\xef\xbb\xbfcode\n")
        r = md.detect_doc_only(self.p, files(src=0, docs_loc=800, docs_count=12),
                               {"toolchain_present": True})
        self.assertFalse(r["is_doc_only"])
        self.assertEqual(r["reason"], "marker")

    def test_doc_only_thresholds_are_pinned_not_left_to_drift(self):
        # These three constants are stated heuristics, not derived from a measured corpus (see
        # the comment above their declaration) — but "unmeasured" must not mean "unpinned".
        # test_source_cap_boundary above already hardcodes 200/201 as its own boundary literals,
        # so it happens to catch drift in DOC_ONLY_SOURCE_LOC_MAX too, but that coverage is
        # implicit and would silently vanish if that fixture were ever rewritten to derive its
        # boundary from the constant instead of a literal. Assert all three values directly so a
        # future edit to any of them is a deliberate, visible decision, not a silent drift.
        self.assertEqual(md.DOC_ONLY_SOURCE_LOC_MAX, 200)
        self.assertEqual(md.DOC_ONLY_DOC_LOC_MIN, 200)
        self.assertEqual(md.DOC_ONLY_DOC_FILES_MIN, 3)


class TestBL34LanguageAndDocExtensions(unittest.TestCase):
    """Found while answering a question about an adopter project's "Code by
    Language" card. Two independent gaps in the same three constants:
    - `.r` was already in SOURCE_EXTS (R always counted toward Source LOC) but had no LANG_MAP
      entry, so it never got its own "Code by Language" row (603 files / 77,773 LOC, invisible).
    - `.qmd`/`.rmd` were in neither SOURCE_EXTS nor DOC_EXTS, so a file with either extension
      outside a `docs/` path fell through categorize_file's whole ladder to "other" — not source,
      not docs, not even LOC-counted (LOC is skipped entirely for "other").
    RED-first (Learning #12): both gaps confirmed by direct execution against an adopter project
    before either constant was touched.
    """

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.p = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()

    def test_r_source_gets_its_own_language_row(self):
        write_tree(self.p, {"analysis.R": "x <- 1\ny <- 2\n"})
        m = md.collect_file_metrics(self.p)
        self.assertIn("R", m["by_language"], "an .R file must appear in Code by Language")
        self.assertEqual(m["by_language"]["R"]["count"], 1)
        self.assertEqual(m["by_category"]["source"]["count"], 1,
                         "R must still count as Source -- BL-34 only adds the missing language row")

    def test_r_extension_is_case_insensitive(self):
        # collect_file_metrics lowercases fpath.suffix, so the conventional uppercase ".R" and a
        # bare ".r" both resolve to the one LANG_MAP key.
        write_tree(self.p, {"a.R": "x <- 1\n", "b.r": "y <- 2\n"})
        m = md.collect_file_metrics(self.p)
        self.assertEqual(m["by_language"]["R"]["count"], 2)

    def test_qmd_is_docs_not_other(self):
        write_tree(self.p, {"article.qmd": "# Title\n" + "prose\n" * 10})
        m = md.collect_file_metrics(self.p)
        self.assertEqual(m["by_category"]["docs"]["count"], 1)
        self.assertEqual(m["by_category"]["other"]["count"], 0)
        self.assertGreater(m["by_category"]["docs"]["loc"], 0,
                           "LOC is skipped entirely for \"other\" -- must not silently stay 0")

    def test_rmd_is_docs_not_other(self):
        write_tree(self.p, {"vignette.Rmd": "# Title\n" + "prose\n" * 10})
        m = md.collect_file_metrics(self.p)
        self.assertEqual(m["by_category"]["docs"]["count"], 1)
        self.assertEqual(m["by_category"]["other"]["count"], 0)
        self.assertGreater(m["by_category"]["docs"]["loc"], 0)

    def test_qmd_and_rmd_are_not_also_a_language_row(self):
        # Precedent: DOC_EXTS's other members (.md, .txt, .rst, .adoc, .org) have no LANG_MAP
        # entry either -- "Code by Language" is a programming-language signal, not a doc-format
        # one, so a doc extension should never double as both.
        write_tree(self.p, {"article.qmd": "# T\nprose\n", "vignette.Rmd": "# T\nprose\n"})
        m = md.collect_file_metrics(self.p)
        self.assertNotIn("Quarto", m["by_language"])
        self.assertNotIn("R Markdown", m["by_language"])

    def test_rmd_analysis_repo_flips_doc_only_and_softens_the_test_risk(self):
        """The downstream classification consequence review found this fix under-described.
        Quarto's own `.qmd` was already a render-toolchain marker (detect_doc_only's fallback
        arm), so a Quarto repo was already doc_only before this fix -- what changed for Quarto
        is only its REPORTED metrics. Bare `.Rmd` has no toolchain marker at all (`_bookdown.yml`
        is one; a plain analysis project has neither that nor `*.qmd`), so adding `.rmd` to
        DOC_EXTS is what newly clears the corpus disjunction for that class and flips
        doc_only False -> True -- a real classification change, not a metrics-only one.

        Verified directly against `upstream/main` (pre-fix) before writing this: the identical
        fixture there reads doc_only=False with "No test infrastructure" (HIGH) in the risk
        list. Believed correct -- an R-Markdown analysis project is exactly the population
        BL-5/v3.2 exists to score fairly, and the has-tests gate (test_b_synced_code_repo...
        analogue) still protects a real R package with a tests/ dir -- but nothing pinned the
        consequence before this test, so a future DOC_EXTS edit could silently un-flip it.
        """
        write_tree(self.p, {
            "helper.R": "f <- function(x) x + 1\n" * 30,
            **{f"analysis{i}.Rmd": "---\ntitle: a\n---\n\n" + "prose text here\n" * 30
               for i in range(5)},
            "README.md": "# Analysis\n",
        })
        m = md.collect_all(self.p)
        self.assertTrue(m["doc_only"]["is_doc_only"],
                        "a bare .Rmd analysis project (no toolchain marker) must read doc-only")
        self.assertEqual(m["tests"]["source_loc"], 30,
                         "the helper's own LOC is still counted, just not against the doc-only cap")
        self.assertNotIn("No test infrastructure",
                         [r["description"] for r in m["scores"]["risks"]],
                         "the HIGH risk must be softened once the repo reads as doc-only")


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


# --- Signal-integrity campaign, Layer 1 (defects 1, 2, 8) -------------------------------------

# The raw weighted sum, computed HERE from the checklist rather than read from the module, so
# these assertions can be driven against unpatched code (which has no METHODOLOGY_MAX at all).
RAW_MAX = sum(w for _, w, _ in md.METHODOLOGY_ITEMS)

# Adopter-root files that bin/_manifest.py distributes but that are deliberately NOT compliance
# checklist items. Every exemption states WHY, so the structural guard below fails loudly the
# next time a distributed artifact is added without a decision — which is exactly how HANDOFFS.md
# (SEED since v3.3) went two releases unscored. Kept here rather than in the scanner: the manifest
# is canonical-only, so an adopter's copy of the dashboard has nothing to check it against.
CHECKLIST_EXEMPT = {
    "RECOMMENDED_SKILLS.md": "index of optional skill recommendations; using them is elective, "
                             "so its presence says nothing about methodology adoption",
    "FRAMEWORK_LEARNINGS.md": "canonical framework learnings, synced read-only; an adopter never "
                              "writes it and receives it automatically with SESSION_RUNNER.md, so "
                              "its presence measures sync, not adoption. Scoring it would also "
                              "re-cut METHODOLOGY_MAX and move every already-compliant adopter's "
                              "percentage for a change they did not make",
    "CONTEXT_TEMPLATE.md": "template; the operating artifact is the adopter's CONTEXT.md instance",
    "CLAUDE_TEMPLATE.md": "template; the operating artifact is the adopter's CLAUDE.md instance",
    "BOOTSTRAP.md": "one-time setup guide, not a per-session operating artifact",
    "methodology_dashboard.py": "the scanner itself — scoring its own presence is circular",
    "methodology_trim.py": "the ledger trimmer (S39'): sync installs it automatically alongside "
                           "the scanner, so like FRAMEWORK_LEARNINGS.md its presence measures "
                           "sync, not adoption — an adopter cannot fail to have it and cannot "
                           "demonstrate anything by having it. Scoring it would also re-cut "
                           "METHODOLOGY_MAX and move every already-compliant adopter's percentage "
                           "for a change they did not make. Whether an adopter USES it is a "
                           "different question, and the dashboard already answers it in the "
                           "trim-trigger row rather than in the compliance checklist",
    "context_budget.py": "an elective size-governance gate, same class as the scanner above — "
                         "its presence indicates a pre-commit hook was installed, not that the "
                         "session-operating discipline this checklist measures was followed",
    ".context-budget.json": "SEED config for the context-budget gate above; scored the same way "
                            "for the same reason, not a session-operating artifact",
    "quality_ratchet.py": "the quality-ratchet gate (quality-ratchet plan D2), same class as "
                          "context_budget.py: sync installs it, so its presence measures sync, "
                          "not adoption; whether a project DECLARES gates is answered by the "
                          "dashboard's gate metrics, not by the compliance checklist",
    ".quality-gates.json": "SEED manifest for the ratchet above — starts empty by decision "
                           "(plan §8.4), so its presence proves only that sync ran; a declared "
                           "gate count and its outcomes are reported as risks/points instead",
    ".gitattributes": "SEED merge-driver config (parallel-sessions plan, Phase 1): it makes concurrent "
                      "ledger merges clean, which says nothing about whether sessions follow the "
                      "runner; sync installs it, so its presence measures sync. A dashboard advisory "
                      "for a missing merge driver was considered and deferred until Phase 5 "
                      "measures concurrent sessions (plan §8A, item 11)",
}


def manifest_adopter_root_dests():
    """Adopter-ROOT destinations from bin/_manifest.py (dests with no directory component)."""
    manifest_path = os.path.join(os.path.dirname(HERE), "bin", "_manifest.py")
    spec = importlib.util.spec_from_file_location("methodology_manifest_under_test", manifest_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return [dest for _src, dest, _disp in mod.DISTRIBUTION if "/" not in dest]


def full_compliance_tree(p):
    """Create every METHODOLOGY_ITEMS artifact under `p` — a 100%-compliant adopter."""
    for item_path, _w, kind in md.METHODOLOGY_ITEMS:
        target = p / item_path
        if kind == "dir":
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f"# {item_path}\n")


class TestComplianceScaleIsHonest(unittest.TestCase):
    """Defects 1 & 2: a 110-point weighted sum was rendered as a percentage and fed an
    UNCLAMPED health dimension, so a fully-compliant adopter's card read 'Methodology
    Compliance (110%)' over a 22/20 sub-score and a 102/100 total."""

    def test_max_is_derived_from_the_checklist_never_a_literal(self):
        # A hardcoded denominator is what drifted in the first place (v2.1 appended two 5-point
        # items to a scale cut for exactly 100), so the constant must be computed, not written.
        self.assertEqual(md.METHODOLOGY_MAX, RAW_MAX)
        self.assertEqual(md.METHODOLOGY_MAX, sum(w for _, w, _ in md.METHODOLOGY_ITEMS))

    def test_full_compliance_is_100_percent_not_the_raw_sum(self):
        self.assertEqual(md.compliance_pct(RAW_MAX), 100)
        self.assertEqual(md.compliance_pct(0), 0)
        self.assertLessEqual(md.compliance_pct(RAW_MAX), 100)

    def test_methodology_dimension_is_clamped_to_its_band(self):
        # Driven at full compliance: today int(110 * 0.2) == 22 in a 0-20 band, and the
        # "0-100" total reaches 102.
        m = base_metrics(methodology={"compliance_score": RAW_MAX, "compliance_pct": 100})
        s = md.score_health(m)
        self.assertEqual(s["methodology"], 20)
        self.assertLessEqual(s["total"], 100)

    def test_dimension_reads_the_normalized_percent_at_intermediate_values(self):
        """The endpoints cannot tell the two readings apart — at 0 both give 0, and at full
        compliance the clamp alone yields 20 either way. So a suite driven only at 0% and 100%
        stays green against a dimension that clamps but never normalizes, which is where every
        partially-compliant repo (i.e. the whole adopter fleet) actually lives. Verified by
        mutation: reading compliance_score instead of compliance_pct at the dimension survived
        all 44 tests before this lock existed."""
        discriminating = 0
        for raw in range(0, md.METHODOLOGY_MAX + 1, 5):
            pct = md.compliance_pct(raw)
            m = base_metrics(methodology={"compliance_score": raw, "compliance_pct": pct})
            got = md.score_health(m)["methodology"]
            self.assertEqual(got, int(pct * 0.2), f"dimension is not the normalized pct at raw={raw}")
            self.assertLessEqual(got, 20, f"dimension escaped its band at raw={raw}")
            if got != min(20, int(raw * 0.2)):
                discriminating += 1
        # Guard the guard: if no sampled value separated the two readings, the loop above would
        # be green against the unnormalized implementation and prove nothing.
        self.assertGreater(discriminating, 0,
                           "no sampled value distinguishes the normalized read from the raw sum")

    def test_clamp_holds_even_if_the_percentage_is_out_of_range(self):
        # Defense in depth: normalization makes >100 unreachable through the producer, so the
        # clamp is only load-bearing if compliance_pct is ever wrong. Drive it directly.
        m = base_metrics(methodology={"compliance_score": 999, "compliance_pct": 150})
        self.assertEqual(md.score_health(m)["methodology"], 20)

    def test_no_dimension_or_total_escapes_its_band_at_full_compliance(self):
        m = base_metrics(methodology={"compliance_score": RAW_MAX, "compliance_pct": 100},
                         tests={"test_to_source_ratio": 0.6, "test_file_count": 9, "source_loc": 500},
                         ci={"has_ci": True, "workflow_count": 3},
                         docs={"readme_quality": "excellent", "has_docs_dir": True,
                               "has_changelog": True, "has_license": True,
                               "has_roadmap": True, "has_todo": True},
                         changelog={"present": True, "is_fresh": True, "signals": []})
        s = md.score_health(m)
        for dim in ("activity", "testing", "documentation", "ci_cd", "methodology"):
            self.assertLessEqual(s[dim], 20, f"{dim} escaped its 0-20 band")
        self.assertEqual(s["total"], 100)

    def test_partial_adoption_risk_states_the_normalized_percent(self):
        raw = 52
        pct = md.compliance_pct(raw)
        m = base_metrics(methodology={"compliance_score": raw, "compliance_pct": pct})
        descs = risk_descs(m)
        self.assertTrue(any(f"Partial methodology adoption ({pct}%)" in d for d in descs),
                        f"expected the normalized percent in the risk text; got {descs}")
        if pct != raw:  # the two coincide only if the checklist is ever re-cut to sum 100
            self.assertFalse(any(f"({raw}%)" in d for d in descs),
                             "the raw weighted sum must not be rendered as a percentage")

    def test_zero_adoption_test_reads_the_raw_sum_not_the_percentage(self):
        # Scale-independence: a single small-weight item in a future larger checklist can round
        # to 0% — it must NOT be reported as "no methodology adoption".
        m = base_metrics(methodology={"compliance_score": 0, "compliance_pct": 0})
        self.assertTrue(any("No methodology adoption" in d for d in risk_descs(m)))
        some = base_metrics(methodology={"compliance_score": 5, "compliance_pct": 0})
        descs = risk_descs(some)
        self.assertFalse(any("No methodology adoption" in d for d in descs))
        self.assertTrue(any("Partial methodology adoption" in d for d in descs))


class TestChecklistCurrency(unittest.TestCase):
    """Defect 8: HANDOFFS.md has shipped to adopters as a SEED since v3.3 (bin/_manifest.py:47)
    and was never added to the compliance checklist. The structural guard turns that one-off
    omission into an invariant, so the next distributed artifact cannot repeat it."""

    def test_handoffs_is_a_checklist_item_weighted_like_its_twin(self):
        by_path = {p: (w, kind) for p, w, kind in md.METHODOLOGY_ITEMS}
        self.assertIn("HANDOFFS.md", by_path)
        self.assertEqual(by_path["HANDOFFS.md"], by_path["CHANGELOG.md"],
                         "HANDOFFS.md and CHANGELOG.md are structural twins (both SEED, both "
                         "lifetime-stable) and must carry the same weight and kind")

    def test_every_distributed_adopter_root_file_is_scored_or_exempt(self):
        checklist = {p for p, _w, _k in md.METHODOLOGY_ITEMS}
        unaccounted = [d for d in manifest_adopter_root_dests()
                       if d not in checklist and d not in CHECKLIST_EXEMPT]
        self.assertEqual(unaccounted, [],
                         "distributed adopter-root file(s) neither on METHODOLOGY_ITEMS nor in "
                         "CHECKLIST_EXEMPT — add the item or record why it is not scored")

    def test_exemptions_are_real_manifest_entries_with_a_reason(self):
        # Guard the guard: a stale exemption would silently weaken the invariant above.
        dests = set(manifest_adopter_root_dests())
        for name, reason in CHECKLIST_EXEMPT.items():
            self.assertIn(name, dests, f"CHECKLIST_EXEMPT lists {name}, which is not distributed")
            self.assertTrue(reason.strip(), f"exemption for {name} states no reason")


class TestMethodologyGridAlignment(unittest.TestCase):
    """Load-bearing, not cosmetic: the header row was hand-written at six item columns while the
    cells derive from METHODOLOGY_ITEMS, so v2.1's two added items have silently run every
    project row wider than its headers ever since."""

    def test_headers_are_derived_from_the_checklist(self):
        headers = md.methodology_grid_headers()
        self.assertEqual(len(headers), len(md.METHODOLOGY_ITEMS) + 2)  # Project + items + Score
        self.assertEqual(headers[0], "Project")
        self.assertEqual(headers[-1], "Score")

    def test_derived_labels_are_pinned_exactly(self):
        # Pinned in full rather than spot-checked, so a wording change is never invisible. Note
        # the one deliberate rename: the hand-written row's "Workstreams" becomes "Workstreams
        # Dir", matching the "Methodology Dir" convention for the two directory items. It cost
        # nothing to change because the hand-written headers were misaligned anyway — with 8
        # headers over 10 cells, "Workstreams" was sitting above the ROADMAP.md column.
        self.assertEqual(md.methodology_grid_headers(), [
            "Project", "Session Runner", "Safeguards", "Session Notes", "Backlog",
            "Changelog", "Handoffs", "Roadmap", "Methodology Dir", "Workstreams Dir", "Score",
        ])

    def test_rendered_grid_has_one_header_per_cell(self):
        p = {"name": "demo",
             "methodology": {"items": {k: True for k, _w, _k in md.METHODOLOGY_ITEMS},
                             "compliance_score": RAW_MAX, "compliance_pct": 100}}
        html = md.render_methodology_grid([p])
        self.assertEqual(html.count("<th>"), len(md.METHODOLOGY_ITEMS) + 2)
        row = html.split("<tbody>")[1]
        self.assertEqual(row.count("<td"), len(md.METHODOLOGY_ITEMS) + 2)
        self.assertEqual(html.count("<th>"), row.count("<td"),
                         "header row and project row must be the same width")

    def test_grid_renders_the_percentage_not_the_raw_sum(self):
        p = {"name": "demo",
             "methodology": {"items": {k: True for k, _w, _k in md.METHODOLOGY_ITEMS},
                             "compliance_score": RAW_MAX, "compliance_pct": 100}}
        html = md.render_methodology_grid([p])
        self.assertIn(">100%<", html)
        if RAW_MAX != 100:  # they coincide only if the checklist is ever re-cut to sum 100
            self.assertNotIn(f">{RAW_MAX}%<", html)


class TestHistoryVersionStamp(unittest.TestCase):
    """Residual risk 1: dashboard_history.jsonl persists only derived totals with no scale
    marker, and the trend renderer diffs first-vs-last — so a one-time scoring change renders
    as a red regression arrow indistinguishable from a real one. The stamp is what makes the
    discontinuity interpretable."""

    def test_history_entry_records_the_dashboard_version(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            portfolio = {"health_score": 70, "project_count": 1, "total_commits": 5,
                         "risk_counts": {}}
            projects = [{"name": "demo",
                         "scores": {"health": {"total": 70}, "risks": [], "activity": "active"},
                         "git": {"total_commits": 5}, "tests": {"test_file_count": 2}}]
            md.append_history(root, portfolio, projects)
            line = (root / md.HISTORY_FILE).read_text().strip()
            entry = json.loads(line)
            self.assertEqual(entry.get("dashboard_version"), md.DASHBOARD_VERSION)


# --- Signal-integrity campaign, Layer 2 (defects 5, 6, 7) -------------------------------------


def write_tree(p, files_map):
    """Materialize {relative path: content} under `p`, creating parent directories."""
    for name, content in files_map.items():
        fp = p / name
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)


def git_repo(case, files_map, extra_commits=0, tail_files=None, dates=None):
    """A temp git repo with controllable history DEPTH and DATES.

    `files_map` lands in the first commit, then `extra_commits` empty commits, then `tail_files`
    in a final commit — which is how a test places a file at a chosen distance from HEAD (the
    lag signals are computed from `git log -1 -- <file>` against HEAD). `dates`, when given, is
    an (author_date_for_first, author_date_for_the_rest) pair so day-lag can be exercised
    without waiting three weeks.
    """
    td = tempfile.TemporaryDirectory()
    case.addCleanup(td.cleanup)
    p = Path(td.name)
    subprocess.run(["git", "init", "-q", str(p)], check=True)

    def commit(msg, when=None):
        env = dict(os.environ)
        if when:
            env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = when
        subprocess.run(["git", "-C", str(p), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(p), "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-q", "--allow-empty", "-m", msg], check=True, env=env)

    first_date, rest_date = dates if dates else (None, None)
    write_tree(p, files_map)
    commit("init", first_date)
    for i in range(extra_commits):
        commit(f"filler {i}", rest_date)
    if tail_files:
        write_tree(p, tail_files)
        commit("tail", rest_date)
    return p


class TestLedgerLocators(unittest.TestCase):
    """Defects 5 & 7. One locator was answering two different questions: *is there a changelog to
    measure freshness against* (best-available — root or `docs/`, name-prefix, case-insensitive)
    and *does this repo keep an action ledger* (root `CHANGELOG.md`, exactly — what
    METHODOLOGY_ITEMS already probes). Conflating them let a `docs/` product changelog answer the
    membership question, so the adopter that had no ledger at all was never told so."""

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.p = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()

    # -- membership: _find_action_ledger, root-anchored and exact (RED: no such function today)
    def test_the_action_ledger_is_the_root_changelog(self):
        write_tree(self.p, {"CHANGELOG.md": "# ledger\n"})
        self.assertEqual(md._find_action_ledger(self.p), self.p / "CHANGELOG.md")

    def test_a_docs_changelog_is_not_an_action_ledger(self):
        write_tree(self.p, {"docs/changelog.md": "# product release notes\n"})
        self.assertIsNone(md._find_action_ledger(self.p))

    def test_an_archive_is_not_an_action_ledger(self):
        write_tree(self.p, {"CHANGELOG-archive.md": "# frozen history\n"})
        self.assertIsNone(md._find_action_ledger(self.p))

    def test_a_changelog_directory_is_not_an_action_ledger(self):
        # Mirrors _find_changelog's is_file() guard: a CHANGELOG/ directory is not a ledger.
        (self.p / "CHANGELOG.md").mkdir()
        self.assertIsNone(md._find_action_ledger(self.p))

    def test_membership_agrees_with_the_compliance_checklist_probe(self):
        """Guard the guard, by CALLING the checklist rather than re-implementing it — a guard that
        restates the thing it is guarding cannot detect the two drifting apart."""
        for tree, expected in (({"CHANGELOG.md": "x"}, True),
                               ({"docs/changelog.md": "x"}, False),
                               ({"CHANGELOG-archive.md": "x"}, False),
                               # A lowercase root file has no platform-independent answer: a
                               # case-insensitive filesystem satisfies the CHANGELOG.md probe and a
                               # case-sensitive one does not (plan §7 residual risk 6, pre-existing
                               # and out of scope). Whatever the platform answers, the invariant
                               # under test is that BOTH probes answer it the same way.
                               ({"changelog.md": "x"}, None)):
            with tempfile.TemporaryDirectory() as td:
                p = Path(td)
                write_tree(p, tree)
                ledger = md._find_action_ledger(p) is not None
                checklist = md.collect_methodology_metrics(p)["items"]["CHANGELOG.md"]
                self.assertEqual(ledger, checklist,
                                 f"the two probes must answer alike; tree={tree}")
                if expected is not None:
                    self.assertEqual(ledger, expected, tree)

    def test_the_one_documented_divergence_from_the_checklist_probe(self):
        # The checklist probes a bare exists(), so a CHANGELOG.md DIRECTORY scores as present for
        # compliance while it is correctly not a ledger. Pinned so the docstring's claim of "the
        # same question, one deliberate difference" stays true, and so the divergence cannot grow
        # silently.
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "CHANGELOG.md").mkdir()
            self.assertTrue(md.collect_methodology_metrics(p)["items"]["CHANGELOG.md"])
            self.assertIsNone(md._find_action_ledger(p))

    # -- location: _find_changelog, defect 7 (archive shadowing)
    def test_an_exact_changelog_wins_over_an_archive_sibling(self):
        # 'CHANGELOG-archive.md' sorts BEFORE 'CHANGELOG.md' ('-' is 0x2D, '.' is 0x2E), so the
        # sorted()-first locator measured freshness against a deliberately frozen file and then
        # reported it as lagging.
        write_tree(self.p, {"CHANGELOG.md": "# ledger\n", "CHANGELOG-archive.md": "# frozen\n"})
        self.assertEqual(md._find_changelog(self.p), self.p / "CHANGELOG.md")

    def test_root_precedence_outranks_the_exact_name_across_bases(self):
        """CHARACTERIZATION — this pins a LIMITATION, not a fix, so it cannot change by accident.
        The exact-name preference is scoped within a base, so a root holding only a frozen archive
        still shadows an exact `docs/CHANGELOG.md`. Hoisting the preference across bases would fix
        this arrangement, but the same hoist would silently move which file is measured — and with
        it the ±1 freshness point — for the neighbouring shape pinned in the test below, where a
        non-`.md` root changelog coexists with an exact `docs/CHANGELOG.md` and nothing is being
        shadowed at all. D3 exists precisely because a fix that quietly moves a score it claimed
        not to touch is how this class of defect propagates, so the narrower reading shipped and
        this arrangement was left as it was."""
        write_tree(self.p, {"CHANGELOG-archive.md": "# frozen\n", "docs/CHANGELOG.md": "# live\n"})
        self.assertEqual(md._find_changelog(self.p), self.p / "CHANGELOG-archive.md")

    def test_a_non_md_root_changelog_still_outranks_docs(self):
        # The behavior a cross-base hoist would have changed, pinned so it cannot: root wins, and
        # nothing about this tree involves an archive or any defect this layer fixes.
        write_tree(self.p, {"CHANGELOG.rst": "# root\n", "docs/CHANGELOG.md": "# docs\n"})
        self.assertEqual(md._find_changelog(self.p), self.p / "CHANGELOG.rst")

    def test_a_lowercase_exact_changelog_is_preferred_over_an_archive(self):
        # _find_changelog is documented as case-insensitive (it mirrors has_changelog), so the
        # exact-match preference must be too, or the shadowing simply persists for changelog.md
        # ('C' 0x43 sorts before 'c' 0x63).
        write_tree(self.p, {"changelog.md": "# live\n", "CHANGELOG-archive.md": "# frozen\n"})
        self.assertEqual(md._find_changelog(self.p), self.p / "changelog.md")

    def test_the_prefix_fallback_survives(self):
        # Regression lock: the prefix search is the FALLBACK, not removed. A repo whose only
        # changelog is CHANGELOG.rst is still located and measured.
        write_tree(self.p, {"CHANGELOG.rst": "# rst\n"})
        self.assertEqual(md._find_changelog(self.p), self.p / "CHANGELOG.rst")

    def test_a_root_prefix_match_is_returned_even_when_a_docs_base_exists(self):
        """The test above gives the repo no `docs/` directory at all, so it exercises only the
        single-base path — a rewrite that mishandled the second base could not fail it. The far
        more common shape is a root changelog plus an ordinary `docs/` tree, and that is what this
        pins: the root prefix match is returned, and the presence of a second base does not cost
        the repo its changelog — which would cost the +1 freshness point and silence every
        Component-C advisory, but NOT the +1 presence point, since that comes from
        `collect_doc_metrics.has_changelog`, an independent scan D3 leaves untouched. (Conflating
        those two is the very thing this layer exists to stop doing.) This began as a
        cross-base-accumulation lock against an implementation that carried
        a `fallback` across bases; the shipped locator resolves per base and returns before `docs/`
        is scanned, so what survives here is the behavior, not the original mechanism."""
        write_tree(self.p, {"CHANGELOG.rst": "# rst\n", "docs/guide.md": "# guide\n"})
        self.assertEqual(md._find_changelog(self.p), self.p / "CHANGELOG.rst")

    def test_root_precedence_is_unchanged_when_both_are_exact(self):
        # Regression lock: preferring an exact match must not reorder the bases.
        write_tree(self.p, {"CHANGELOG.md": "# root\n", "docs/CHANGELOG.md": "# docs\n"})
        self.assertEqual(md._find_changelog(self.p), self.p / "CHANGELOG.md")

    def test_the_two_locators_disagree_on_purpose(self):
        """The dual predicate stated as one assertion: the same tree answers YES to location and
        NO to membership. If these two ever collapse into one answer, defect 5 is back."""
        write_tree(self.p, {"docs/changelog.md": "# product release notes\n"})
        self.assertIsNotNone(md._find_changelog(self.p))
        self.assertIsNone(md._find_action_ledger(self.p))


class TestSignalReachability(unittest.TestCase):
    """Defect 6: Signal F (unmigrated `BACKLOG.md` done-marks) was emitted BELOW the
    `changelog is None` early return, so an adopter with 60 unmigrated done-marks and no ledger
    at all — strictly the worse case — received FEWER warnings than one with a ledger. A correct
    assertion over an input that never executes is issue #61's own failure mode."""

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.p = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()

    def _freshness(self, files_map, commits=50):
        write_tree(self.p, files_map)
        return md.evaluate_changelog_freshness(
            self.p, {"total_commits": commits, "days_since_last_commit": 1})

    def test_the_backlog_signal_fires_with_no_changelog_at_all(self):
        r = self._freshness({"SESSION_RUNNER.md": "# runner\n",
                             "BACKLOG.md": "- [x] shipped\n" * 60})
        self.assertFalse(r["present"])
        self.assertEqual(r["backlog_done_unmigrated"], 60)
        self.assertTrue(any("not migrated" in d for _sev, d in r["signals"]),
                        "Signal F must not depend on an unrelated file existing")

    def test_the_backlog_signal_still_fires_with_a_changelog(self):
        # Regression lock for the move: the case that already worked must keep working.
        r = self._freshness({"SESSION_RUNNER.md": "# runner\n",
                             "CHANGELOG.md": "# ledger\n",
                             "BACKLOG.md": "- [x] shipped\n" * 60})
        self.assertTrue(r["present"])
        self.assertTrue(any("not migrated" in d for _sev, d in r["signals"]))

    def test_the_backlog_signal_stays_adopter_scoped_with_no_changelog(self):
        # The v3.2 fold-in gate must survive the move: a non-adopter sibling that keeps a [x]
        # backlog does not follow the migrate-on-log convention, so it is not a defect there.
        r = self._freshness({"BACKLOG.md": "- [x] shipped\n" * 60})
        self.assertEqual(r["backlog_done_unmigrated"], 60)
        self.assertFalse(any("not migrated" in d for _sev, d in r["signals"]))

    def test_the_backlog_signal_is_not_suppressed_by_new_adopter_grace(self):
        """Found by mutation: every other test here drives real history, so grace-suppressing
        Signal F while moving it survived the whole suite. Grace exists because a *fresh seed* has
        not had a chance to go stale — it says nothing about a backlog that arrived carrying 60
        unmigrated done-marks, and this signal never was grace-scoped. Pin that."""
        young = {"SESSION_RUNNER.md": "# runner\n", "BACKLOG.md": "- [x] shipped\n" * 60}
        # `new_adopter_grace` is only computed once a changelog is located, so grace is
        # OBSERVABLE only in the with-ledger case — assert it there...
        with_ledger = self._freshness({**young, "CHANGELOG.md": "# ledger\n"},
                                      commits=md.LEDGER_REAL_HISTORY_MIN - 1)
        self.assertTrue(with_ledger["new_adopter_grace"], "fixture must actually be under grace")
        self.assertTrue(any("not migrated" in d for _sev, d in with_ledger["signals"]),
                        "Signal F is not grace-scoped and must keep firing on a young repo")
        # ...and separately drive the intersection of both defect conditions: young history AND
        # no changelog at all, where the emission's new position is what makes it reachable.
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            write_tree(p, young)
            r = md.evaluate_changelog_freshness(
                p, {"total_commits": md.LEDGER_REAL_HISTORY_MIN - 1, "days_since_last_commit": 1})
            self.assertFalse(r["present"])
            self.assertTrue(any("not migrated" in d for _sev, d in r["signals"]))

    def test_no_signal_is_stranded_below_the_early_return(self):
        """Guard the guard, STRUCTURALLY. Rather than naming Signal F — which the two tests above
        already cover — this derives the invariant: every advisory that does not name the located
        changelog is one that did not need a changelog to be computed, so it must survive the
        changelog's absence. Today Signal F is the only such advisory, so the two formulations
        coincide; the structural one keeps holding when the next file-independent signal is added
        in the wrong place, and the literal one would not."""
        runner_and_backlog = {"SESSION_RUNNER.md": "# runner\n",
                              "BACKLOG.md": "- [x] shipped\n" * 60}
        with_ledger = self._freshness({**runner_and_backlog, "CHANGELOG.md": "# ledger\n"})
        located = md._find_changelog(self.p).name
        file_independent = {d for _sev, d in with_ledger["signals"] if located not in d}
        self.assertTrue(file_independent, "fixture emits no file-independent advisory to check")
        with tempfile.TemporaryDirectory() as td:   # same fixture, minus the changelog
            p = Path(td)
            write_tree(p, runner_and_backlog)
            without = md.evaluate_changelog_freshness(
                p, {"total_commits": 50, "days_since_last_commit": 1})
        self.assertFalse(without["present"])
        self.assertTrue(file_independent <= {d for _sev, d in without["signals"]},
                        "an advisory that never needed a changelog vanished when the changelog did")


STATUS_TABLE_BACKLOG = """\
# Backlog

## Status Legend

| Status | Meaning |
|--------|---------|
| `DONE` | Completed and tested |
| `READY` | Ready to implement (no blockers) |

## Critical Issues

| ID | Issue | Status | Notes |
|----|-------|--------|-------|
| SEC-013 | Refresh tokens stored as plaintext | DONE | hash_token() utility |
| SEC-014 | JWT tokens in localStorage | DONE | httpOnly cookies + CSRF |
| B-001 | Pagination field mismatch | READY | blocked until SEC-013 is DONE |
| B-002 | Duplicate files need cleanup | IN_PROGRESS | will be DONE next session |
| DONE-9 | Misleading ID column | READY | the ID itself starts with a done token |

## Later

| ID | Initiative | Duration | Status |
|----|-----------|----------|--------|
| INIT-1 | Migration | 3 weeks | **DONE (Session 30, 2026-01-01)** |
| INIT-2 | Rollout | 2 weeks | BLOCKED |
"""

FENCED_DOC_BACKLOG = """\
# Backlog

Format reference — mark an item done like this before migrating it to CHANGELOG.md:

```markdown
- [x] a completed item that exists only inside a documentation example
- [x] a second one
```

## Open

- [ ] a genuinely open item
"""

OUTCOME_TABLE_BACKLOG = """\
# Operational Backlog (fork-only)

> **STATUS: RETIRED** — verbose task bodies are removed at close-out.

## Open items

None.

## Completed items

| Item | Scope | Outcome |
|------|-------|---------|
| **BL-1** | wsfct migration | ✅ Complete in `rmsharp/wsfct` (operator). |
| **BL-4** | Housekeeping | ✅ DONE 2026-07-06 — plans archived. |
"""

EMPTY_BACKLOG = """\
# Backlog

## Active
<!-- Current work items -->

## Up Next
<!-- Upcoming tasks -->
"""


class TestBacklogFormatAndAbstention(unittest.TestCase):
    """Defect 4 (`BACKLOG.md` done-marks are counted checkbox-only, so a table backlog reads 0)
    plus the fenced-code-block false positive, under campaign decision D4: ABSTENTION IS A
    FIRST-CLASS RESULT.

    A silent `0` is defect 4 itself — it is indistinguishable from a clean backlog, which is how
    a 643-line table backlog carrying 256 done-marks reported "nothing unmigrated". So the scanner
    now reports WHICH convention it read, and says out loud when it could not read one.

    The table predicate (*a cell that starts with a done token, in a row of >= 3 cells, ignoring
    the ID column*) is empirically tuned in the campaign plan against that real backlog and is NOT
    re-derived here — see `_BACKLOG_DONE_TOKENS`. `STATUS_TABLE_BACKLOG` is a compact fixture that
    exercises each property the tuning depends on by name (prose false positives, the 2-cell
    legend, a done token in the ID column, a decorated cell, a moving Status column), rather than
    vendoring 51 KB of an adopter's real backlog into this repo; the real-corpus count of 256 is
    reproduced as runtime-smoke evidence at close-out instead.

    RED-FIRST: every assertion below that proves a defect was driven against the unpatched
    scanner and watched to fail — `_count_backlog_done` returned 0 for the table fixture, 2 for
    the fenced one, and 0 (silently) for the abstention fixture. The regression locks assert
    BEHAVIOUR that is unchanged (a checkbox backlog still counts 60), but they are still new
    tests: they call `_scan_backlog_done`, which did not exist before this layer, so none of them
    could execute against the old module — the invariant is preserved, the assertion is not.
    """

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.p = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()

    def _scan(self, text):
        write_tree(self.p, {"BACKLOG.md": text})
        return md._scan_backlog_done(self.p)

    def _freshness(self, files_map, commits=50):
        write_tree(self.p, files_map)
        return md.evaluate_changelog_freshness(
            self.p, {"total_commits": commits, "days_since_last_commit": 1})

    # --- the table predicate, property by property -------------------------------------------

    def test_a_status_table_backlog_is_counted(self):
        """RED: the checkbox-only scanner returns 0 for every table backlog ever written."""
        r = self._scan(STATUS_TABLE_BACKLOG)
        self.assertEqual(r["format"], "table")
        self.assertTrue(r["recognized"])
        self.assertEqual(r["done"], 3, "SEC-013, SEC-014 and INIT-1 are the only done rows")

    def test_prose_containing_a_done_token_is_not_a_done_row(self):
        """The 94-false-positive class the tuning rejected: a NOTES cell that merely mentions a
        done token ("blocked until SEC-013 is DONE") is not a completed item. A *contains*
        predicate scored 321 on the real corpus against a hand count of 253."""
        r = self._scan(
            "| ID | Issue | Status | Notes |\n"
            "|----|-------|--------|-------|\n"
            "| B-001 | Pagination | READY | blocked until SEC-013 is DONE |\n")
        self.assertEqual(r["done"], 0)

    def test_a_done_token_in_the_id_column_is_ignored(self):
        """Why the predicate skips cell 0: an ID may legitimately start with a done token
        (`DONE-9`) while the row's actual status is READY."""
        r = self._scan(
            "| ID | Issue | Status | Notes |\n"
            "|----|-------|--------|-------|\n"
            "| DONE-9 | Misleading ID | READY | still open |\n")
        self.assertEqual(r["done"], 0)

    def test_the_two_cell_legend_is_not_counted(self):
        """Why the predicate needs >= 3 cells: a Status *legend* defines the vocabulary, it does
        not report work. An *equals* predicate scored 227 and counted this row."""
        r = self._scan(
            "| Status | Meaning |\n"
            "|--------|---------|\n"
            "| `DONE` | Completed and tested |\n")
        self.assertEqual(r["done"], 0)

    def test_a_decorated_done_cell_is_counted(self):
        """Why the predicate is *starts-with* and not *equals*: real backlogs write
        `**DONE (Session 30, ...)**`, which no equality test matches."""
        r = self._scan(
            "| ID | Initiative | Duration | Status |\n"
            "|----|-----------|----------|--------|\n"
            "| INIT-1 | Migration | 3 weeks | **DONE (Session 30, 2026-01-01)** |\n")
        self.assertEqual(r["done"], 1)

    def test_the_status_column_may_sit_anywhere_but_the_id_column(self):
        """Guard the guard: across the real corpus's 27 tables the Status column lands at index
        2 (20 tables), 3, 4 and even 0, and 3 tables carry no Status column at all — which is why
        the predicate scans every non-ID cell rather than a fixed column index."""
        r = self._scan(STATUS_TABLE_BACKLOG)
        self.assertEqual(r["done"], 3, "a fixed Status index would miss the trailing-Status table")

    # --- the fenced-code-block false positive ------------------------------------------------

    def test_a_fenced_example_is_not_a_done_mark(self):
        """RED: today this counts 2. A doc that *documents* the `- [x]` convention inside a fenced
        example is not a repo with unmigrated work — it is a match presented as a finding, the
        campaign's own root defect."""
        r = self._scan(FENCED_DOC_BACKLOG)
        self.assertEqual(r["done"], 0)
        self.assertEqual(r["format"], "checkbox",
                         "the surviving `- [ ]` outside the fence still identifies the convention")
        self.assertTrue(r["recognized"])

    def test_a_fenced_table_is_not_a_done_row(self):
        """The same containment on the new surface: a fenced example of the *table* convention
        must not be counted either."""
        r = self._scan(
            "# Backlog\n\nExample:\n\n```markdown\n"
            "| ID | Issue | Status | Notes |\n"
            "|----|-------|--------|-------|\n"
            "| X-1 | example | DONE | not real |\n"
            "```\n\n- [ ] a real open item\n")
        self.assertEqual(r["done"], 0)

    # --- abstention (decision D4) -------------------------------------------------------------

    def test_an_unreadable_table_abstains_visibly(self):
        """RED: today this reports a silent 0, indistinguishable from a clean backlog. A table
        with no Status column carries item state this scanner cannot interpret, so it must say so
        rather than assert a count it cannot support. This is this repo's own backlog shape
        (`| Item | Scope | Outcome |`) and the plan names it as the abstention case."""
        r = self._scan(OUTCOME_TABLE_BACKLOG)
        self.assertEqual(r["format"], "unrecognized")
        self.assertFalse(r["recognized"])
        self.assertEqual(r["done"], 0)

    def test_the_abstention_is_visible_to_an_adopter(self):
        f = self._freshness({"SESSION_RUNNER.md": "# runner\n",
                             "BACKLOG.md": OUTCOME_TABLE_BACKLOG})
        self.assertFalse(f["backlog_recognized"])
        self.assertTrue(any("not recognized" in d for _sev, d in f["signals"]),
                        "an unreadable format must abstain out loud, never report a silent 0")
        self.assertTrue(any("BACKLOG.md" in d for _sev, d in f["signals"]),
                        "the advisory must name the file it was computed against")

    def test_the_abstention_is_adopter_scoped(self):
        """Same gate as Signal F itself: only an adopter follows the migrate-on-log convention, so
        only an adopter is owed a note about the scanner's inability to check it."""
        f = self._freshness({"BACKLOG.md": OUTCOME_TABLE_BACKLOG})
        self.assertFalse(any("not recognized" in d for _sev, d in f["signals"]))

    def test_an_empty_backlog_is_silent_rather_than_abstaining(self):
        """The abstention must stay NARROW. An empty backlog is the healthy state, not an
        unreadable one: it carries no item rows and no checkboxes, so 0 is a correct measurement
        and there is nothing to disclose. Two live adopters keep exactly this file; advising them
        that a format was 'not recognized' would be a signal that does not mean what it appears
        to mean — the defect class this campaign exists to remove."""
        r = self._scan(EMPTY_BACKLOG)
        self.assertEqual(r["format"], "none")
        self.assertEqual(r["done"], 0)
        f = self._freshness({"SESSION_RUNNER.md": "# runner\n", "BACKLOG.md": EMPTY_BACKLOG})
        self.assertFalse(any("not recognized" in d for _sev, d in f["signals"]))

    def test_a_prose_bullet_backlog_abstains(self):
        """The other side of that boundary: plain list items with no checkbox and no table DO
        carry item state the scanner cannot read, so they abstain rather than report 0."""
        r = self._scan("# Backlog\n\n- Fix the login redirect (done)\n- Add rate limiting\n")
        self.assertEqual(r["format"], "unrecognized")
        self.assertFalse(r["recognized"])

    def test_an_absent_backlog_is_not_an_abstention(self):
        """A repo that keeps no backlog at all has no format to fail to recognize."""
        write_tree(self.p, {"SESSION_RUNNER.md": "# runner\n"})
        r = md._scan_backlog_done(self.p)
        self.assertEqual(r["format"], "absent")
        self.assertIsNone(r["source"])
        f = md.evaluate_changelog_freshness(
            self.p, {"total_commits": 50, "days_since_last_commit": 1})
        self.assertFalse(any("not recognized" in d for _sev, d in f["signals"]))

    # --- regression locks ---------------------------------------------------------------------

    def test_a_checkbox_backlog_counts_exactly_as_before(self):
        """The one behaviour this layer must not move: the checkbox predicate is unchanged."""
        r = self._scan("- [x] shipped\n" * 60)
        self.assertEqual(r["format"], "checkbox")
        self.assertEqual(r["done"], 60)
        f = self._freshness({"SESSION_RUNNER.md": "# runner\n",
                             "BACKLOG.md": "- [x] shipped\n" * 60})
        self.assertEqual(f["backlog_done_unmigrated"], 60)
        self.assertTrue(any("not migrated" in d for _sev, d in f["signals"]))

    def test_an_all_open_checkbox_backlog_is_a_recognized_zero(self):
        """A recognized 0 and an abstained 0 are different findings, which is the whole of D4."""
        r = self._scan("- [ ] still open\n- [ ] also open\n")
        self.assertEqual(r["format"], "checkbox")
        self.assertTrue(r["recognized"])
        self.assertEqual(r["done"], 0)

    def test_the_search_order_over_backlog_locations_is_unchanged(self):
        write_tree(self.p, {"BACKLOG.md": "- [x] root\n",
                            "docs/planning/BACKLOG.md": STATUS_TABLE_BACKLOG})
        r = md._scan_backlog_done(self.p)
        self.assertEqual(r["source"], "BACKLOG.md")
        self.assertEqual(r["done"], 1)

    def test_the_emitted_metrics_key_contract_is_preserved(self):
        """`backlog_done_unmigrated` is in the JSON contract; the new keys are additive."""
        f = self._freshness({"SESSION_RUNNER.md": "# runner\n",
                             "BACKLOG.md": STATUS_TABLE_BACKLOG})
        self.assertEqual(f["backlog_done_unmigrated"], 3)
        self.assertEqual(f["backlog_format"], "table")
        self.assertTrue(f["backlog_recognized"])

    # --- mutation-driven coverage --------------------------------------------------------------
    #
    # Every test below closes a hole found by MUTATION, not by RED-first: each one pins a decision
    # that the suite above could not distinguish from its opposite. Two further mutants survive and
    # are deliberately NOT "fixed", because they are inert by construction rather than untested —
    # inventing a test for either would assert a property over an input that cannot violate it,
    # which is the campaign's own §8 learning 2:
    #
    #   * `elif` -> `if` on the abstention branch. An unrecognized format always reports done == 0,
    #     so the two branches are already mutually exclusive; the `elif` documents that, it does not
    #     enforce it.
    #   * dropping the separator-row skip in `_table_rows`. A separator cell contains only `-` and
    #     `:`, which can never start with a done token, so the skip is clarity rather than behaviour.

    def test_checkbox_format_wins_when_a_backlog_carries_both(self):
        """Precedence is a real decision, and no fixture above forced it. Checkbox wins, because
        that is the reading this layer promised not to move; a backlog carrying both conventions is
        reported under the one whose count is already load-bearing."""
        r = self._scan(
            "| ID | Task | Status | Notes |\n"
            "|----|------|--------|-------|\n"
            "| A-1 | a | DONE | |\n"
            "| A-2 | b | DONE | |\n"
            "| A-3 | c | DONE | |\n"
            "\n## Also\n\n- [x] one checkbox item\n")
        self.assertEqual(r["format"], "checkbox")
        self.assertEqual(r["done"], 1)

    def test_a_status_word_in_a_data_row_is_not_a_header(self):
        """A header is the row directly above a `|---|` separator — not any row that happens to
        say "Status". Otherwise a single NOTES cell reading "Status: DONE" would silently promote
        an unreadable table to a counted one, turning an honest abstention into a fabricated count."""
        r = self._scan(
            "| Item | Scope | Outcome |\n"
            "|------|-------|---------|\n"
            "| BL-1 | migration | Status: DONE |\n"
            "| BL-2 | cleanup | DONE 2026-01-01 |\n")
        self.assertEqual(r["format"], "unrecognized")
        self.assertEqual(r["done"], 0)

    # The token list is written out LITERALLY here on purpose. A first version of this test built
    # its fixture by iterating md._BACKLOG_DONE_TOKENS and asserting done == len(that tuple) —
    # which passes no matter which tokens are removed, because fixture and expectation move
    # together. Mutation caught it: dropping a token survived the "coverage" written to pin it.
    # A test derived from the thing under test cannot falsify it (campaign §8 learning 2).
    EXPECTED_DONE_TOKENS = ("DONE", "COMPLETE", "COMPLETED", "SHIPPED", "FIXED", "RESOLVED",
                            "CLOSED", "✅")

    def test_the_published_done_token_set_is_pinned(self):
        self.assertEqual(md._BACKLOG_DONE_TOKENS, self.EXPECTED_DONE_TOKENS,
                         "the done-token set is a published predicate — changing it changes every "
                         "adopter's Signal F, so it changes here first")

    def test_every_shipped_done_token_is_counted(self):
        """The real 643-line corpus only exercises DONE, FIXED and RESOLVED, so the other five
        tokens shipped untested — dropping any one of them changed nothing the suite could see."""
        rows = "".join(f"| A-{i} | task | {tok} | notes |\n"
                       for i, tok in enumerate(self.EXPECTED_DONE_TOKENS))
        r = self._scan("| ID | Task | Status | Notes |\n|----|------|--------|-------|\n"
                       + rows + "| A-99 | open one | READY | notes |\n")
        self.assertEqual(r["done"], len(self.EXPECTED_DONE_TOKENS),
                         "every documented done token must count, and READY must not")

    def test_a_recognized_zero_is_distinguishable_from_an_abstained_zero(self):
        """The whole of D4, asserted on the emitted metrics: `backlog_recognized` must report the
        CONVENTION, never merely `done > 0`. A backlog with only open checkboxes is a trustworthy
        0; an unreadable table is not — and both report 0."""
        f = self._freshness({"SESSION_RUNNER.md": "# runner\n", "BACKLOG.md": "- [ ] open\n"})
        self.assertEqual(f["backlog_done_unmigrated"], 0)
        self.assertTrue(f["backlog_recognized"], "an all-open checkbox backlog is a KNOWN zero")
        f2 = self._freshness({"SESSION_RUNNER.md": "# runner\n",
                              "BACKLOG.md": OUTCOME_TABLE_BACKLOG})
        self.assertEqual(f2["backlog_done_unmigrated"], 0)
        self.assertFalse(f2["backlog_recognized"], "an unreadable table is an UNKNOWN zero")

    def test_a_horizontal_rule_is_not_an_item(self):
        """Keeps the abstention narrow. `---` is a markdown horizontal rule, not a list item, and
        an otherwise-empty backlog containing one is still the healthy empty state. A bullet
        predicate loose enough to match it would abstain on ordinary formatting."""
        r = self._scan("# Backlog\n\n## Active\n\n---\n\n## Up Next\n")
        self.assertEqual(r["format"], "none")

    def test_a_fence_is_closed_only_by_its_own_marker(self):
        """A ``` block is not closed by a ~~~ line inside it. Otherwise the remainder of the
        example leaks back into the scan and is counted as real work."""
        r = self._scan("# Backlog\n\n```markdown\n~~~\n- [x] leaked example\n```\n\n- [ ] real\n")
        self.assertEqual(r["done"], 0)
        self.assertEqual(r["format"], "checkbox")

    # --- review-driven coverage ----------------------------------------------------------------
    #
    # Everything below closes a hole found by the 5-lens adversarial boundary review, which caught
    # what RED-first and two mutation rounds both missed. The first two are REGRESSIONS the review
    # found in this layer's own new code.

    def test_an_unterminated_fence_does_not_swallow_the_file(self):
        """REGRESSION the review caught. A markdown renderer lets an unclosed ``` run to end of
        file; doing that here let ONE stray fence line hide every done-mark below it and report a
        clean backlog — strictly worse than the checkbox-only scanner this layer replaces, and the
        exact silent-zero this layer exists to remove. Only CLOSED fences are stripped."""
        text = "# Backlog\n\n```\n\n## Notes\n\n- [x] a\n- [x] b\n- [x] c\n"
        r = self._scan(text)
        self.assertEqual(r["done"], 3)
        self.assertEqual(len(md._BACKLOG_DONE_RE.findall(text)), 3,
                         "and it must still agree with the pre-Layer-3 reading on this input")

    def test_a_stray_fence_cannot_manufacture_a_trusted_zero(self):
        """The worst sibling of the unterminated-fence regression, and the reason the fix is "do
        not strip an unclosed fence" rather than "redirect the empty case": with a Status table
        ABOVE the stray fence, swallowing the tail returned format `table`, done 0, recognized
        TRUE — an affirmatively trusted zero, worse than abstaining. Also covers the case where the
        document is genuinely balanced to a renderer (a 4-backtick outer fence) so the author has
        no visual cue anything is wrong."""
        r = self._scan("# Backlog\n\n| ID | Item | Status |\n|----|------|--------|\n"
                       "| A-1 | x | OPEN |\n\n```text\n- [x] BL-1 shipped\n- [x] BL-2 shipped\n")
        self.assertEqual(r["done"], 2)
        outer = self._scan("# Backlog\n\n````markdown\n```\n````\n\n- [x] BL-1\n- [x] BL-2\n")
        self.assertEqual(outer["done"], 2, "a 4-backtick fence renders balanced; do not swallow it")

    def test_a_header_row_is_not_a_finished_item(self):
        """REGRESSION the review caught. A table whose column is headed `Completed` counted its own
        HEADING as one unmigrated item — a label read as work, which is this campaign's root defect
        reproduced inside its own fix."""
        r = self._scan("| ID | Status | Completed | Notes |\n"
                       "|----|--------|-----------|-------|\n"
                       "| A-1 | READY | no | still open |\n")
        self.assertEqual(r["format"], "table")
        self.assertEqual(r["done"], 0)

    def test_an_escaped_pipe_does_not_fabricate_a_done_mark(self):
        """REGRESSION the review caught. `\\|` is the only way GFM lets a literal pipe sit inside a
        cell; splitting on it invents cells that were never in the table and can shift a prose
        fragment into the position the predicate reads — so a NOTES cell mentioning "DONE upstream"
        marked an open row complete. The row below is READY and must count 0."""
        r = self._scan("| ID | Task | Status | Notes |\n|----|------|--------|-------|\n"
                       r"| B-1 | a thing | READY | see `foo \| bar` — DONE upstream |" "\n")
        self.assertEqual(r["format"], "table")
        self.assertEqual(r["done"], 0)

    def test_an_inline_code_span_does_not_close_a_fence(self):
        """The fence marker is three characters, not two: a line opening with a two-backtick inline
        code span sits INSIDE the block and must not close it, or the rest of the example leaks
        back in and is counted as work."""
        r = self._scan("# Backlog\n\n```markdown\n``code`` in an example\n- [x] fenced item\n```\n"
                       "\n- [ ] real open item\n")
        self.assertEqual(r["done"], 0)

    def test_a_tilde_fence_is_stripped_too(self):
        """`_FENCE_RE` accepts ~~~ as well as ```, and nothing exercised it: deleting ~~~ support
        entirely survived the suite and re-created the false positive this layer removes."""
        r = self._scan("# Backlog\n\n~~~markdown\n- [x] fenced example\n~~~\n\n- [ ] real\n")
        self.assertEqual(r["done"], 0)

    def test_a_backlog_below_the_root_is_found_and_named(self):
        """No test ever read a non-root location, so `_BACKLOG_LOCATIONS` was effectively a
        one-element tuple as far as the suite could tell — and the advisory that promises to name
        its source file could not fail against a hardcoded "BACKLOG.md"."""
        write_tree(self.p, {"SESSION_RUNNER.md": "# runner\n",
                            "docs/planning/BACKLOG.md": "- [x] shipped\n" * 3})
        r = md._scan_backlog_done(self.p)
        self.assertEqual(r["source"], "docs/planning/BACKLOG.md")
        self.assertEqual(r["done"], 3)
        f = md.evaluate_changelog_freshness(
            self.p, {"total_commits": 50, "days_since_last_commit": 1})
        self.assertTrue(any("docs/planning/BACKLOG.md" in d for _sev, d in f["signals"]),
                        "the advisory must name the file it actually read")

    def test_a_three_column_table_is_counted(self):
        """The `>= 3` floor was only ever tested from below (2-cell rows excluded). A 3-column
        backlog is the boundary case and had no coverage at all."""
        r = self._scan("| ID | Task | Status |\n|----|------|--------|\n"
                       "| A-1 | a thing | DONE |\n| A-2 | another | READY |\n")
        self.assertEqual(r["done"], 1)

    def test_done_tokens_are_matched_case_insensitively_and_through_decoration(self):
        """`_cell_marks_done` upper-cases and strips backticks/asterisks; neither was exercised, so
        dropping either survived both the suite and the 643-line runtime smoke."""
        r = self._scan("| ID | Task | Status | Notes |\n|----|------|--------|-------|\n"
                       "| A-1 | a | done | lowercase |\n"
                       "| A-2 | b | `DONE` | code-span |\n"
                       "| A-3 | c | Done — 2026-01-01 | mixed case + trailer |\n"
                       "| A-4 | d | READY | still open |\n")
        self.assertEqual(r["done"], 3)

    def test_a_bolded_status_header_still_declares_a_table(self):
        r = self._scan("| ID | Task | **Status** | Notes |\n|:---|:----:|-----------:|------|\n"
                       "| A-1 | a | DONE | x |\n")
        self.assertEqual(r["format"], "table")
        self.assertEqual(r["done"], 1, "alignment-colon separators must parse too")

    @unittest.skipIf(os.geteuid() == 0, "root can read a 000-mode file")
    def test_an_unreadable_backlog_abstains_rather_than_reporting_zero(self):
        """An I/O error is the one case where 0 is guaranteed to mean nothing at all, and it was
        the one branch that still reported a silent 0 — D4's own definition of defect 4."""
        write_tree(self.p, {"SESSION_RUNNER.md": "# runner\n", "BACKLOG.md": "- [x] a\n"})
        bl = self.p / "BACKLOG.md"
        bl.chmod(0o000)
        try:
            r = md._scan_backlog_done(self.p)
            self.assertEqual(r["format"], "unreadable")
            self.assertFalse(r["recognized"])
            f = md.evaluate_changelog_freshness(
                self.p, {"total_commits": 50, "days_since_last_commit": 1})
            self.assertTrue(any("inactive for this repo" in d for _sev, d in f["signals"]),
                            "an unreadable backlog must abstain, not report a clean 0")
        finally:
            bl.chmod(0o644)

    def test_the_union_predicates_known_false_positives_are_pinned(self):
        """CHARACTERIZATION, not endorsement. The tuned predicate is a union over every non-ID
        cell rather than a read of the Status column, so a TITLE cell beginning with a done token
        and a 3-column legend's MEANING cell both count. Measured on the 643-line corpus this was
        tuned against, that costs nothing — all 256 rows are counted via a Status column (242) or
        sit in a table with no Status column (14), and none only via another column. Narrowing is
        an operator decision (it would move the ratified count to 242), so the behaviour is pinned
        here rather than silently changed."""
        title = self._scan("| ID | Task | Status | Notes |\n|----|------|--------|-------|\n"
                           "| B-5 | Fixed login redirect | READY | still open |\n")
        self.assertEqual(title["done"], 1, "known false positive: a done token in the TITLE cell")
        legend = self._scan("| Status | Meaning | Example |\n|--------|---------|--------|\n"
                            "| `DONE` | Completed and tested | A-1 |\n"
                            "| ID | Task | Status |\n|----|------|--------|\n"
                            "| A-9 | real | READY |\n")
        self.assertEqual(legend["done"], 1, "known false positive: a 3-column legend")


class TestAdvisoriesNameTheirSource(unittest.TestCase):
    """Defect 5's misdirecting half. An adopter whose only changelog was a `docs/` product
    release-notes file was told its "CHANGELOG ledger" was lagging — advice to go update a
    release-notes file, while the real finding (no action ledger at all) stayed suppressed. An
    advisory that names the file it was computed against cannot misdirect."""

    def _signals(self, p):
        r = md.evaluate_changelog_freshness(
            p, {"total_commits": 50, "days_since_last_commit": 1})
        return [d for _sev, d in r["signals"]]

    def test_the_commit_lag_advisory_names_the_file(self):
        # docs/changelog.md in the first commit, then 12 commits that never touch it.
        p = git_repo(self, {"docs/changelog.md": "# product release notes\n"}, extra_commits=12)
        descs = self._signals(p)
        lag = [d for d in descs if "commits since it was last updated" in d]
        self.assertEqual(len(lag), 1, f"expected exactly one commit-lag advisory; got {descs}")
        self.assertIn("docs/changelog.md", lag[0])
        self.assertNotIn("ledger", lag[0].lower())

    def test_the_day_lag_advisory_names_the_file(self):
        p = git_repo(self, {"docs/changelog.md": "# product release notes\n"}, extra_commits=1,
                     dates=("2026-01-01T12:00:00", "2026-06-01T12:00:00"))
        descs = self._signals(p)
        day = [d for d in descs if "days" in d]
        self.assertEqual(len(day), 1, f"expected exactly one day-lag advisory; got {descs}")
        self.assertIn("docs/changelog.md", day[0])
        self.assertNotIn("ledger", day[0].lower())

    def test_the_never_used_advisory_names_the_file(self):
        # Same misdirection class as the two lag messages: "CHANGELOG present but never used"
        # reads as a statement about the action ledger even when the file found was docs/.
        p = git_repo(self, {"docs/changelog.md": f"# notes\n{md.SEED_SENTINEL}\n"},
                     extra_commits=1)
        descs = self._signals(p)
        never = [d for d in descs if "never used" in d]
        self.assertEqual(len(never), 1, f"expected exactly one never-used advisory; got {descs}")
        self.assertIn("docs/changelog.md", never[0])

    def test_a_root_ledger_advisory_names_the_root_file(self):
        # The naming is uniform, not a special case for docs/: the same code path names
        # CHANGELOG.md when that is what it measured.
        p = git_repo(self, {"CHANGELOG.md": "# ledger\n"}, extra_commits=12)
        lag = [d for d in self._signals(p) if "commits since it was last updated" in d]
        self.assertEqual(len(lag), 1)
        self.assertIn("CHANGELOG.md", lag[0])

    def test_advisory_paths_are_posix_on_every_platform(self):
        # The displayed path is a rendered string, not a filesystem argument — pin the separator
        # so the message reads the same in a Windows adopter's dashboard. Asserted only over
        # advisories that actually carry a nested path, so this cannot pass vacuously against an
        # implementation that names no file at all.
        p = git_repo(self, {"docs/changelog.md": "# notes\n"}, extra_commits=12)
        descs = self._signals(p)
        naming = [d for d in descs if "changelog.md" in d.lower()]
        self.assertTrue(naming, f"no advisory named its source file; got {descs}")
        for d in naming:
            self.assertIn("docs/changelog.md", d)
            self.assertNotIn("\\", d)


class TestMembershipRiskGating(unittest.TestCase):
    """The membership risk's two guards, driven at the pure layer for precision. Both live on the
    one line this layer rewrote, and both were unpinned: mutation showed that DELETING the
    history gate and an OFF-BY-ONE on it each survived the whole suite."""

    def _flagged(self, commits, adopter=True, ledger=False):
        m = base_metrics(
            git={"total_commits": commits},
            methodology={"compliance_score": 25, "compliance_pct": md.compliance_pct(25),
                         "items": {"SESSION_RUNNER.md": adopter}},
            changelog={"present": False, "ledger_present": ledger, "is_fresh": False,
                       "signals": []})
        return any("no root CHANGELOG.md" in d for d in risk_descs(m))

    def test_a_brand_new_adopter_is_not_scolded_for_a_ledger_it_has_not_owed_yet(self):
        self.assertFalse(self._flagged(md.LEDGER_REAL_HISTORY_MIN - 1))

    def test_the_history_threshold_is_inclusive(self):
        self.assertTrue(self._flagged(md.LEDGER_REAL_HISTORY_MIN))

    def test_a_non_adopter_is_never_flagged_however_long_its_history(self):
        self.assertFalse(self._flagged(10_000, adopter=False))

    def test_a_repo_with_a_ledger_is_never_flagged(self):
        self.assertFalse(self._flagged(10_000, ledger=True))


class TestLedgerIdentityEndToEnd(unittest.TestCase):
    """Ratified decision D3 driven through `collect_all`: LOCATION (which changelog to measure
    freshness against) and MEMBERSHIP (does this repo keep an action ledger) are different
    questions, and fixing the second must not silently cost the first. The obvious fix —
    narrowing the one locator to the root — passes the membership test and quietly drops a
    documentation point for exactly the adopter class the defect is about."""

    def _adopter_with_only_a_docs_changelog(self):
        # 12 commits, so the repo has real history and gets no new-adopter grace, with the
        # changelog committed LAST so it is not also lagging: the finding under test is
        # membership, not freshness.
        return git_repo(self, {"SESSION_RUNNER.md": "# runner\n" * 5,
                               "README.md": "# demo\n" * 60},
                        extra_commits=10,
                        tail_files={"docs/changelog.md": "# Product release notes\n\n## 1.2.0\n"})

    def test_the_adopter_is_told_it_has_no_action_ledger(self):
        m = md.collect_all(self._adopter_with_only_a_docs_changelog())
        self.assertGreaterEqual(m["git"]["total_commits"], md.LEDGER_REAL_HISTORY_MIN)
        self.assertTrue(m["changelog"]["present"], "located for freshness")
        self.assertFalse(m["changelog"]["ledger_present"], "but it is not an action ledger")
        descs = [r["description"] for r in m["scores"]["risks"]]
        self.assertTrue(any("no root CHANGELOG.md" in d for d in descs),
                        f"the adopter must learn it has no action ledger; got {descs}")

    def test_the_same_adopter_keeps_its_documentation_freshness_point(self):
        """D3's regression lock, and the reason the obvious fix is wrong: `is_fresh` is computed
        after the `changelog is None` early return, so a root-only locator leaves it False and
        `score_health` silently withholds its +1 — a scoring change under a no-scoring-change
        claim."""
        m = md.collect_all(self._adopter_with_only_a_docs_changelog())
        self.assertTrue(m["docs"]["has_changelog"])
        self.assertTrue(m["changelog"]["is_fresh"], "freshness still measured against docs/")
        earned = md.score_health(m)["documentation"]
        self.assertLess(earned, 20, "the control below is only meaningful under the 0-20 cap")
        stale = {**m, "changelog": {**m["changelog"], "is_fresh": False}}
        self.assertEqual(earned - md.score_health(stale)["documentation"], 1,
                         "the +1 freshness point must still be earned, not silently dropped")

    def test_an_adopter_with_a_real_ledger_is_not_flagged(self):
        # Regression lock on the other side of the predicate: a root CHANGELOG.md satisfies
        # membership, so the risk must stay silent.
        p = git_repo(self, {"SESSION_RUNNER.md": "# runner\n" * 5, "README.md": "# demo\n" * 60},
                     extra_commits=10, tail_files={"CHANGELOG.md": "# ledger\n\n### 2026-07-25 · x\n"})
        m = md.collect_all(p)
        self.assertTrue(m["changelog"]["ledger_present"])
        self.assertFalse(any("no root CHANGELOG.md" in r["description"]
                             for r in m["scores"]["risks"]))

    def test_a_non_adopter_with_no_ledger_is_not_flagged(self):
        # Regression lock: the risk stays adopter-scoped. A sibling project that keeps no ledger
        # by design is not a methodology defect.
        m = md.collect_all(git_repo(self, {"README.md": "# demo\n" * 60}, extra_commits=10))
        self.assertFalse(m["changelog"]["ledger_present"])
        self.assertFalse(any("no root CHANGELOG.md" in r["description"]
                             for r in m["scores"]["risks"]))


# === LAYER 4 — REPO ROLE (plan defect 3 / upstream issue #59) ===

# The marker filename is written out LITERALLY in the tests below rather than read from the
# module constant. That is deliberate and it is the stronger assertion: an owner types this exact
# filename into their repo, so a test that asks the scanner what it calls its own marker can never
# catch a rename that breaks every marker already in the wild.
PROFILE_FILE = ".methodology-profile"

# The two paths detect_repo_role uses to PROVE the role. They must never be scored — see
# TestFrameworkChecklist.test_detection_inputs_are_not_scored for why this is load-bearing.
DETECTION_INPUTS = ("bin/_manifest.py", "starter-kit/SESSION_RUNNER.md")

CANONICAL_ROOT = Path(os.path.dirname(HERE))


def framework_tree(p):
    """The minimum tree detect_repo_role must classify as framework by structure alone:
    distribution machinery + a starter-kit runner, and NO root runner of its own."""
    (p / "bin").mkdir(parents=True, exist_ok=True)
    (p / "bin" / "_manifest.py").write_text("DISTRIBUTION = []\n")
    (p / "starter-kit").mkdir(parents=True, exist_ok=True)
    (p / "starter-kit" / "SESSION_RUNNER.md").write_text("# runner\n")


def full_framework_tree(p):
    """framework_tree plus every FRAMEWORK_ITEMS artifact — a 100% framework repo."""
    framework_tree(p)
    for item_path, _w, kind in md.FRAMEWORK_ITEMS:
        target = p / item_path
        if kind == "dir":
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f"# {item_path}\n")


class TestProfileMarkerAxes(unittest.TestCase):
    """The .methodology-profile marker gains a SECOND axis in this layer, so one file now answers
    two independent questions. Every test here was driven against the shipped tokens[0] reader
    first; the ones marked RED failed, which is what proves detect_doc_only could not stay
    untouched — the plan's own Layer 4 proof ('a doc-only framework marker satisfies both axes')
    is unsatisfiable while only the first token is read."""

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.p = Path(self._td.name)
        # 400 source LOC and no doc corpus: the HEURISTIC says "not doc-only", so any doc-only
        # verdict below can only have come from the marker, and any heuristic verdict means the
        # owner's declaration was lost. Without this the two paths are indistinguishable.
        self.files = files(src=400, docs_loc=0, docs_count=0)
        self.render = {"toolchain_present": False}

    def _marker(self, text):
        (self.p / PROFILE_FILE).write_text(text)

    def _doc_only(self):
        return md.detect_doc_only(self.p, self.files, self.render)

    def test_the_marker_constant_is_the_filename_owners_actually_write(self):
        self.assertEqual(md.PROFILE_MARKER, PROFILE_FILE)

    def test_axis_token_sets_are_disjoint(self):
        """One file is one token bag, so the two axes share a namespace. If a token ever served
        both, a single word would silently answer two questions."""
        self.assertEqual(set(md.PROFILE_CORPUS_TOKENS) & set(md.PROFILE_ROLE_TOKENS), set())

    def test_axes_compose_in_either_order(self):
        """RED against tokens[0]: 'framework doc-only' returned is_doc_only False / heuristic —
        the owner's doc-only declaration was discarded because it was not written first."""
        for text in ("doc-only framework", "framework doc-only"):
            with self.subTest(marker=text):
                self._marker(text)
                self.assertTrue(self._doc_only()["is_doc_only"], f"{text!r} lost the corpus axis")
                self.assertEqual(md.detect_repo_role(self.p)["role"], "framework")

    def test_a_leading_comment_does_not_swallow_the_declaration(self):
        """RED against tokens[0]: a marker whose first line is a comment returned heuristic,
        so a well-documented marker was worth less than an undocumented one."""
        self._marker("# why this repo is classified this way\ndoc-only\n")
        r = self._doc_only()
        self.assertTrue(r["is_doc_only"])
        self.assertEqual(r["reason"], "marker")

    def test_comment_prose_is_never_tokenized(self):
        """The blocker this layer was found to have, verified against the only marker in the live
        population. church_growth's .methodology-profile is 8 lines / 87 whitespace tokens: one
        declaration plus SEVEN lines of '#' prose that MENTION the opposite token. It survives
        today only because both mentions carry trailing punctuation ('code,' and 'code.').
        Remove one comma and a naive full-token scan discards the override the file exists to
        assert — so switching to full-token scanning WITHOUT stripping comments is strictly more
        dangerous than tokens[0]. The fixture below is a shortened PARAPHRASE of that file with
        the trailing punctuation removed from its 'code' mentions — not a copy of it."""
        self._marker(
            "doc-only\n"
            "# This project is a content/strategy repository with no application source code\n"
            "# Without this marker the dashboard misclassifies this repo as code because the\n"
            "# dashboard script itself is the only source-extension file in the repo\n"
        )
        r = self._doc_only()
        self.assertTrue(r["is_doc_only"], "comment prose overrode the declaration")
        self.assertEqual(r["reason"], "marker")
        self.assertEqual(md.detect_repo_role(self.p)["role"], "adopter")

    def test_a_trailing_comment_on_the_declaration_line_is_prose_too(self):
        """Found by mutation, not by design: every comment fixture above puts the comment on its
        OWN line, so a reader that stripped whole-line comments but not trailing ones passed the
        entire suite. 'doc-only # actually this is code' would then declare both tokens and
        abstain — the owner's declaration lost to their own annotation."""
        self._marker("doc-only   # this is not code, whatever the extension census says\n")
        r = self._doc_only()
        self.assertTrue(r["is_doc_only"])
        self.assertEqual(r["reason"], "marker")

    def test_a_trailing_comment_cannot_fabricate_a_role(self):
        self._marker("adopter  # not the framework repo\n")
        self.assertEqual(md.detect_repo_role(self.p), {"role": "adopter", "reason": "marker"})

    def test_comment_prose_cannot_fabricate_a_role_either(self):
        self._marker("doc-only\n# this repo is not the framework repo\n")
        self.assertEqual(md.detect_repo_role(self.p)["reason"], "default")

    def test_a_contradiction_abstains_on_that_axis_only(self):
        """Decision D4 applied to the marker: a declaration that cannot be read is abstained on
        OUT LOUD, never resolved silently. Today word order decides it — 'doc-only code' returns
        True and 'code doc-only' returns False, from the same two words."""
        self._marker("doc-only code framework\n")
        r = self._doc_only()
        self.assertEqual(r["reason"], "marker-contradiction")
        self.assertFalse(r["is_doc_only"], "contradicted axis must fall through to the heuristic")
        # ...while the UNcontradicted axis on the same line still resolves.
        self.assertEqual(md.detect_repo_role(self.p)["role"], "framework")

    def test_contradiction_is_order_independent(self):
        for text in ("doc-only code", "code doc-only"):
            with self.subTest(marker=text):
                self._marker(text)
                self.assertEqual(self._doc_only()["reason"], "marker-contradiction")

    def test_unknown_tokens_are_ignored_not_treated_as_a_contradiction(self):
        """Forward compatibility in both directions: an adopter running an OLDER synced twin must
        not crash or flip on a marker naming an axis it has never heard of, and a newer twin must
        ignore tokens a future axis adds."""
        self._marker("doc-only banana quantum\n")
        r = self._doc_only()
        self.assertTrue(r["is_doc_only"])
        self.assertEqual(r["reason"], "marker")

    def test_bom_and_crlf_survive_on_both_axes(self):
        (self.p / PROFILE_FILE).write_bytes(b"\xef\xbb\xbfframework doc-only\r\n")
        self.assertEqual(md.detect_repo_role(self.p)["reason"], "marker")
        self.assertEqual(md.detect_repo_role(self.p)["role"], "framework")
        self.assertTrue(self._doc_only()["is_doc_only"])

    def test_only_the_first_declaration_line_is_read(self):
        """Found by adversarial review, and it is the defect this layer nearly SHIPPED. The first
        version of the reader mined every line for tokens, so an owner's own uncommented sentence
        of explanation was read as a deliberate override — inverting the very defect Layer 4
        fixes. Both cases below are prose a real owner might plausibly write, and reading only the
        first declaration line is what makes them inert. Reading tokens[0] never had this bug, so
        whole-file scanning would have been a regression dressed up as a fix."""
        runner = self.p / "SESSION_RUNNER.md"
        runner.write_text("# an ordinary adopter\n")

        # (a) prose naming the opposite role must not promote an adopter to publisher.
        self._marker("doc-only\nWe keep our docs in the framework style\n")
        self.assertEqual(md.detect_repo_role(self.p)["role"], "adopter")
        self.assertTrue(self._doc_only()["is_doc_only"], "prose must not disturb the corpus axis")

        # (b) prose naming the opposite corpus token must not fabricate a contradiction and
        #     destroy a declaration the owner did make.
        self._marker("doc-only\nThis is a code repository with a few helper scripts\n")
        r = self._doc_only()
        self.assertTrue(r["is_doc_only"])
        self.assertEqual(r["reason"], "marker")

    def test_prose_below_the_declaration_cannot_fabricate_a_role(self):
        self._marker("adopter\nSee the methodology framework for details\n")
        self.assertEqual(md.detect_repo_role(self.p), {"role": "adopter", "reason": "marker"})

    def test_case_is_ignored(self):
        self._marker("FRAMEWORK\n")
        self.assertEqual(md.detect_repo_role(self.p)["role"], "framework")

    def test_empty_and_absent_markers_fall_through(self):
        self.assertEqual(md.detect_repo_role(self.p)["reason"], "default")   # absent
        self._marker("   \n\n")
        self.assertEqual(md.detect_repo_role(self.p)["reason"], "default")
        self._marker("# only a comment\n")
        self.assertEqual(md.detect_repo_role(self.p)["reason"], "default")


class TestRepoRoleDetection(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.p = Path(self._td.name)

    def test_this_repository_is_detected_as_framework(self):
        r = md.detect_repo_role(CANONICAL_ROOT)
        self.assertEqual(r["role"], "framework")
        self.assertEqual(r["reason"], "structural")

    def test_a_bare_repo_is_an_adopter_by_default(self):
        self.assertEqual(md.detect_repo_role(self.p), {"role": "adopter", "reason": "default"})

    def test_the_structural_heuristic_needs_every_conjunct(self):
        (self.p / "bin").mkdir()
        (self.p / "bin" / "_manifest.py").write_text("DISTRIBUTION = []\n")
        self.assertEqual(md.detect_repo_role(self.p)["role"], "adopter",
                         "distribution machinery alone must not imply the framework role")
        (self.p / "starter-kit").mkdir()
        (self.p / "starter-kit" / "SESSION_RUNNER.md").write_text("# runner\n")
        self.assertEqual(md.detect_repo_role(self.p)["role"], "framework")

    def test_a_repo_that_vendors_the_framework_and_also_adopts_it_stays_an_adopter(self):
        """Plan residual risk 3, mechanized: the misfire class is a repo that ships starter-kit/
        templates plus distribution machinery WITHOUT installing to its own root. A monorepo that
        vendors this framework and ALSO runs it keeps its adoption grading — this conjunct can
        only remove false positives, never create one."""
        framework_tree(self.p)
        (self.p / "SESSION_RUNNER.md").write_text("# my own runner\n")
        self.assertEqual(md.detect_repo_role(self.p)["role"], "adopter")

    def test_the_marker_overrides_the_structure_in_both_directions(self):
        framework_tree(self.p)
        (self.p / PROFILE_FILE).write_text("adopter\n")
        self.assertEqual(md.detect_repo_role(self.p), {"role": "adopter", "reason": "marker"})
        (self.p / PROFILE_FILE).write_text("framework\n")
        self.assertEqual(md.detect_repo_role(self.p), {"role": "framework", "reason": "marker"})

    def test_a_marker_contradiction_falls_back_to_the_structure(self):
        framework_tree(self.p)
        (self.p / PROFILE_FILE).write_text("framework adopter\n")
        r = md.detect_repo_role(self.p)
        self.assertEqual(r, {"role": "framework", "reason": "marker-contradiction"})

    def test_a_synthesised_adopter_tree_is_not_misdetected(self):
        """The heuristic's whole safety argument is that bin/ ships nothing to adopters, so no
        synced repo can acquire bin/_manifest.py. This drives a SYNTHESISED adopter tree — the
        sweep over the 10 real sibling repos is an out-of-band session verification recorded in
        CHANGELOG.md, and naming it here would make the suite look like it re-runs it."""
        for name in ("SESSION_RUNNER.md", "SAFEGUARDS.md", "CHANGELOG.md", "HANDOFFS.md"):
            (self.p / name).write_text(f"# {name}\n")
        (self.p / "docs" / "methodology" / "workstreams").mkdir(parents=True)
        self.assertEqual(md.detect_repo_role(self.p)["role"], "adopter")


class TestFrameworkChecklist(unittest.TestCase):
    def test_max_is_derived_from_the_checklist_never_a_literal(self):
        self.assertEqual(md.FRAMEWORK_MAX, sum(w for _, w, _ in md.FRAMEWORK_ITEMS))

    def test_the_checklist_is_pinned_verbatim(self):
        """Pinned in full rather than spot-checked: a test that only iterates FRAMEWORK_ITEMS
        cannot notice a member being deleted, because the fixture it builds shrinks with it —
        the campaign has hit that trap three times."""
        self.assertEqual(md.FRAMEWORK_ITEMS, [
            ("ITERATIVE_METHODOLOGY.md", 15, "file"),
            ("starter-kit/SAFEGUARDS.md", 15, "file"),
            ("workstreams", 15, "dir"),
            ("bin/sync", 15, "file"),
            ("bin/tests.sh", 10, "file"),
            ("CHANGELOG.md", 10, "file"),
            ("HANDOFFS.md", 10, "file"),
            ("starter-kit/BOOTSTRAP.md", 5, "file"),
            ("HOW_TO_USE.md", 5, "file"),
            ("bin/status", 5, "file"),
        ])

    def test_every_framework_item_exists_in_this_repository(self):
        """Independent of the constant under test: the filesystem is the oracle. A renamed or
        deleted artifact makes the checklist score a path that cannot be satisfied, which is
        defect 3's own shape (grading a repo against files it was never going to have)."""
        for item_path, _w, kind in md.FRAMEWORK_ITEMS:
            target = CANONICAL_ROOT / item_path
            with self.subTest(item=item_path):
                self.assertTrue(target.is_dir() if kind == "dir" else target.is_file(),
                                f"FRAMEWORK_ITEMS scores {item_path}, which does not exist here")

    def test_no_framework_item_is_a_distribution_seed(self):
        """The operator-ratified mechanization of the prohibition in the plan's §"Layer 4 — Repo
        role" (cited by section: that citation had already drifted 255 -> 275). Its stated harm
        is crediting placeholders, and every placeholder it names is a manifest SEED source:
        starter-kit/SESSION_NOTES.md (a 27-line stub) and starter-kit/ROADMAP.md (an 18-line
        skeleton). Excluding SEED sources draws that line mechanically instead of by reading."""
        manifest_path = os.path.join(os.path.dirname(HERE), "bin", "_manifest.py")
        spec = importlib.util.spec_from_file_location("manifest_seed_check", manifest_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        seed_srcs = {src for src, _dest, disp in mod.DISTRIBUTION if disp == "seed"}
        self.assertTrue(seed_srcs, "guard is inert if the manifest declares no seeds")
        offenders = [p for p, _w, _k in md.FRAMEWORK_ITEMS if p in seed_srcs]
        self.assertEqual(offenders, [],
                         "a FRAMEWORK_ITEMS path is a distribution SEED — those are placeholders "
                         "in this repo, and scoring one credits an empty stub (plan :255)")

    def test_detection_inputs_are_not_scored(self):
        """Load-bearing, not tidiness. If the two files that PROVE the role also earn points, the
        raw sum has a nonzero floor on the structural path and the 'no corpus at all' branch
        becomes an assertion over an input that can never occur — defect 6's exact failure class,
        re-created inside the campaign that closed it."""
        scored = {p for p, _w, _k in md.FRAMEWORK_ITEMS}
        for probe in DETECTION_INPUTS:
            self.assertNotIn(probe, scored)

    def test_zero_is_reachable_for_a_structurally_detected_repo(self):
        """The consequence of the rule above, driven rather than argued."""
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        p = Path(td.name)
        framework_tree(p)                       # detected, but publishes nothing
        m = md.collect_methodology_metrics(p, role="framework")
        self.assertEqual(m["compliance_score"], 0)
        self.assertEqual(m["compliance_pct"], 0)

    def test_a_framework_repo_is_scored_on_the_framework_checklist(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        p = Path(td.name)
        full_framework_tree(p)
        m = md.collect_methodology_metrics(p, role="framework")
        self.assertEqual(m["checklist"], "framework")
        self.assertEqual(m["checklist_max"], md.FRAMEWORK_MAX)
        self.assertEqual(m["compliance_score"], md.FRAMEWORK_MAX)
        self.assertEqual(m["compliance_pct"], 100)
        self.assertEqual(m["missing_files"], [])
        # Keyed by the checklist that actually ran — no adopter key may appear.
        self.assertEqual(set(m["items"]), {p for p, _w, _k in md.FRAMEWORK_ITEMS})
        self.assertNotIn("SESSION_NOTES.md", m["items"])

    def test_adopter_scoring_is_byte_for_byte_what_it_was(self):
        """The regression lock the plan's Layer 4 proof asks for: an adopter fixture's score is
        UNCHANGED. Driven at full compliance and at a partial score."""
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        p = Path(td.name)
        full_compliance_tree(p)
        m = md.collect_methodology_metrics(p)
        self.assertEqual(m["checklist"], "adopter")
        self.assertEqual(m["checklist_max"], md.METHODOLOGY_MAX)
        self.assertEqual(m["compliance_score"], md.METHODOLOGY_MAX)
        self.assertEqual(m["compliance_pct"], 100)
        self.assertEqual(set(m["items"]), {x for x, _w, _k in md.METHODOLOGY_ITEMS})

    def test_checklist_pct_normalizes_against_the_checklist_that_ran(self):
        self.assertEqual(md.checklist_pct(md.FRAMEWORK_MAX, md.FRAMEWORK_MAX), 100)
        self.assertEqual(md.checklist_pct(md.METHODOLOGY_MAX, md.METHODOLOGY_MAX), 100)
        self.assertEqual(md.checklist_pct(0, md.FRAMEWORK_MAX), 0)
        self.assertEqual(md.checklist_pct(5, 0), 0)          # degenerate denominator
        # The single-argument form keeps meaning the adopter scale.
        self.assertEqual(md.compliance_pct(md.METHODOLOGY_MAX), 100)

    def test_the_two_checklists_do_not_share_a_denominator_by_accident(self):
        """A denominator of exactly 100 would make raw == pct and render every value-sweep test
        inert: an implementation that scaled the RAW sum would pass. Both scales are deliberately
        off 100, which is what keeps Layer 1's discipline testable here too."""
        self.assertNotEqual(md.FRAMEWORK_MAX, 100)
        self.assertNotEqual(md.METHODOLOGY_MAX, 100)


class TestFrameworkRisks(unittest.TestCase):
    def _fw(self, score, missing=(), items=None):
        return base_metrics(methodology={
            "role": "framework", "checklist": "framework", "checklist_max": md.FRAMEWORK_MAX,
            "compliance_score": score, "compliance_pct": md.checklist_pct(score, md.FRAMEWORK_MAX),
            "missing_files": list(missing), "items": items or {},
        })

    def test_the_adoption_risks_never_fire_on_a_framework_repo(self):
        """The word 'adoption' is the falsehood — the checklist paths are adopter-root
        DESTINATIONS, and a repo that publishes SESSION_RUNNER.md does not install a second copy
        into its own root.

        MEASURED against unpatched code rather than assumed, because the first draft of this
        docstring claimed a risk at 95% that does not exist: raw 0 yields HIGH 'No methodology
        adoption (0% compliance)' and raw 40 (38%) yields medium 'Partial methodology adoption
        (38%)', while a complete corpus fires nothing at all — the partial rung is pct < 50. So
        the sweep below is only a RED at the first two scores, and the third is a lock, not a
        proof. Saying which is which is the difference between a test and a belief."""
        for score in (0, 40, md.FRAMEWORK_MAX):
            with self.subTest(score=score):
                descs = risk_descs(self._fw(score, missing=["bin/sync"] if score else []))
                self.assertFalse(any("methodology adoption" in d for d in descs), descs)
                self.assertFalse(any("adoption" in d for d in descs), descs)

    def test_an_adopter_still_gets_the_adoption_risks(self):
        descs = risk_descs(base_metrics(methodology={"compliance_score": 52,
                                                     "compliance_pct": md.compliance_pct(52)}))
        self.assertTrue(any("Partial methodology adoption" in d for d in descs))

    def test_no_corpus_at_all_is_high_and_names_the_framework(self):
        descs = risk_descs(self._fw(0))
        self.assertTrue(any("No framework corpus" in d for d in descs), descs)
        self.assertEqual([r["severity"] for r in md.assess_risks(self._fw(0))
                          if "No framework corpus" in r["description"]], ["high"])

    def test_an_incomplete_corpus_names_the_missing_members(self):
        """A percentage alone is not a finding here: losing BOTH root ledgers still scores 81%,
        so a pct-only rule would say nothing about it. The member names carry the signal."""
        m = self._fw(md.FRAMEWORK_MAX - 20, missing=["CHANGELOG.md", "HANDOFFS.md"])
        descs = risk_descs(m)
        hit = [d for d in descs if "Framework integrity incomplete" in d]
        self.assertEqual(len(hit), 1, descs)
        self.assertIn("CHANGELOG.md", hit[0])
        self.assertIn("HANDOFFS.md", hit[0])

    def test_a_complete_corpus_raises_no_framework_risk(self):
        descs = risk_descs(self._fw(md.FRAMEWORK_MAX))
        self.assertFalse(any("Framework integrity" in d for d in descs), descs)
        self.assertFalse(any("No framework corpus" in d for d in descs), descs)

    def test_the_ledger_risk_stays_reachable_for_a_framework_repo(self):
        """The regression this layer would otherwise inflict on the campaign itself. The ledger
        risk is gated on items.get('SESSION_RUNNER.md'); under FRAMEWORK_ITEMS that key does not
        exist, so the gate would return False permanently and the risk would go UNREACHABLE with
        no test failing — defect 6's exact failure class, on the one repo that dogfoods the v3.1
        ledger it publishes."""
        m = self._fw(md.FRAMEWORK_MAX)
        m["changelog"] = {"present": False, "ledger_present": False, "is_fresh": False,
                          "signals": []}
        descs = risk_descs(m)
        hit = [d for d in descs if "no root CHANGELOG.md" in d]
        self.assertEqual(len(hit), 1, descs)
        self.assertNotIn("adopter", hit[0], "a framework repo is not an adopter")

    def test_a_framework_repo_that_keeps_its_ledger_is_not_flagged(self):
        m = self._fw(md.FRAMEWORK_MAX)
        m["changelog"] = {"present": True, "ledger_present": True, "is_fresh": True,
                          "signals": []}
        self.assertFalse(any("no root CHANGELOG.md" in d for d in risk_descs(m)))

    def test_a_marker_contradiction_is_disclosed_on_either_axis(self):
        role_conflict = self._fw(md.FRAMEWORK_MAX)
        role_conflict["methodology"]["role_reason"] = "marker-contradiction"
        self.assertTrue(any("conflicting tokens" in d for d in risk_descs(role_conflict)))

        corpus_conflict = base_metrics(doc_only={"is_doc_only": False,
                                                 "reason": "marker-contradiction"})
        self.assertTrue(any("conflicting tokens" in d for d in risk_descs(corpus_conflict)))

    def test_one_disclosure_even_when_both_axes_conflict(self):
        m = self._fw(md.FRAMEWORK_MAX)
        m["methodology"]["role_reason"] = "marker-contradiction"
        m["doc_only"] = {"is_doc_only": False, "reason": "marker-contradiction"}
        self.assertEqual(len([d for d in risk_descs(m) if "conflicting tokens" in d]), 1)

    def test_a_clean_marker_raises_no_disclosure(self):
        m = self._fw(md.FRAMEWORK_MAX)
        m["methodology"]["role_reason"] = "marker"
        self.assertFalse(any("conflicting tokens" in d for d in risk_descs(m)))


class TestFrameworkRendering(unittest.TestCase):
    def _proj(self, role, items, pct, name="demo"):
        return {"name": name,
                "methodology": {"role": role, "items": items, "compliance_score": 0,
                                "compliance_pct": pct, "checklist_max": md.FRAMEWORK_MAX}}

    def test_a_framework_row_shows_no_false_crosses(self):
        """RED today, and measured rather than assumed: the two checklists overlap at exactly
        CHANGELOG.md and HANDOFFS.md, so a framework-keyed items dict rendered against the nine
        adopter columns gives TWO ticks beside SEVEN crosses — under headers naming files the
        repo was never scored on. The row stays the right WIDTH, so nothing looks broken and the
        existing alignment assertion passes against the defect. Aligned and PARTLY TRUE is worse
        than aligned and all-false: the two accidental ticks make the row look considered."""
        html = md.render_methodology_grid(
            [self._proj("framework", {p: True for p, _w, _k in md.FRAMEWORK_ITEMS}, 100)])
        row = html.split("<tbody>")[1]
        self.assertEqual(row.count("meth-no"), 0, "framework row must not render adopter crosses")
        self.assertEqual(row.count("meth-yes"), 0, "nor adopter checks")
        self.assertIn("meth-na", row)

    def test_a_framework_row_keeps_the_grid_aligned(self):
        """A colspan cell still has to add up. Counting <td> tags alone would call a 3-cell
        framework row 'aligned' against 11 headers, so the width is summed over colspans."""
        html = md.render_methodology_grid(
            [self._proj("framework", {}, 100), self._proj(
                "adopter", {k: True for k, _w, _k in md.METHODOLOGY_ITEMS}, 100, name="adopter")])
        self.assertEqual(html.count("<th>"), len(md.METHODOLOGY_ITEMS) + 2)
        rows = html.split("<tbody>")[1].split("</tbody>")[0].split("<tr>")[1:]
        self.assertEqual(len(rows), 2)
        for row in rows:
            width = 0
            for tag in re.findall(r'<td\b[^>]*>', row):
                span = re.search(r'colspan="(\d+)"', tag)
                width += int(span.group(1)) if span else 1
            self.assertEqual(width, len(md.METHODOLOGY_ITEMS) + 2,
                             f"row width {width} does not fill the header row: {row[:120]}")

    def test_the_legend_appears_only_when_a_framework_row_does(self):
        adopter_only = md.render_methodology_grid(
            [self._proj("adopter", {k: True for k, _w, _k in md.METHODOLOGY_ITEMS}, 100)])
        self.assertNotIn("framework repo", adopter_only)
        with_framework = md.render_methodology_grid([self._proj("framework", {}, 100)])
        self.assertIn("framework repo", with_framework)
        # The legend must not overstate. Saying these columns "do not apply" to a framework repo
        # would be the same class of falsehood this layer removes from the score: two of them
        # (CHANGELOG.md, HANDOFFS.md) are on BOTH checklists, and on this repo both are present.
        shared = ({p for p, _w, _k in md.METHODOLOGY_ITEMS}
                  & {p for p, _w, _k in md.FRAMEWORK_ITEMS})
        self.assertTrue(shared, "guard is inert if the checklists stop overlapping")
        for name in shared:
            self.assertIn(name, with_framework,
                          "the legend must name the columns that DO apply to a framework repo")
        self.assertNotIn("do not apply", with_framework)

    def test_a_project_dict_with_no_role_still_renders_as_an_adopter(self):
        """Back-compat lock: render_methodology_grid is called with hand-built dicts in this
        suite and receives whatever collect_all produced in an older run."""
        html = md.render_methodology_grid(
            [{"name": "legacy",
              "methodology": {"items": {k: True for k, _w, _k in md.METHODOLOGY_ITEMS},
                              "compliance_score": md.METHODOLOGY_MAX, "compliance_pct": 100}}])
        self.assertIn("meth-yes", html)
        self.assertNotIn("meth-na", html)


class TestFrameworkEndToEnd(unittest.TestCase):
    def _repo(self, build):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        p = Path(td.name)
        subprocess.run(["git", "init", "-q", str(p)], check=True)
        build(p)
        (p / "README.md").write_text("# framework\n" * 60)
        subprocess.run(["git", "-C", str(p), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(p), "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-q", "-m", "init"], check=True)
        return p

    def test_a_framework_repo_end_to_end(self):
        m = md.collect_all(self._repo(full_framework_tree))
        self.assertEqual(m["methodology"]["role"], "framework")
        self.assertEqual(m["methodology"]["compliance_pct"], 100)
        self.assertEqual(m["scores"]["health"]["methodology"], 20)
        self.assertLessEqual(m["scores"]["health"]["total"], 100)
        self.assertFalse(any("adoption" in r["description"] for r in m["scores"]["risks"]))

        card = md.render_project_card(m)
        self.assertIn("Framework Integrity", card)
        self.assertNotIn("Methodology Compliance", card)
        # The heading must state the checklist that ran. Rendering the adopter denominator here
        # would print the literal arithmetic falsehood "100% (105 of 115)".
        self.assertIn(f"({md.FRAMEWORK_MAX} of {md.FRAMEWORK_MAX})", card)
        self.assertNotIn(f"of {md.METHODOLOGY_MAX})", card)
        # Every glyph on the card must name something the score actually counted.
        self.assertIn("bin/sync", card)
        self.assertNotIn("SESSION_NOTES.md", card)
        self.assertIn("structural", card)     # role provenance is never printed silently
        # The Health Breakdown label, asserted separately from the section heading above. Found
        # by mutation: reverting ONLY the dimension label left the whole suite green, because
        # every other assertion here reads the heading.
        self.assertIn('<span class="dim-label">Framework</span>', card)
        self.assertNotIn('<span class="dim-label">Methodology</span>', card)

    def test_this_repository_end_to_end(self):
        """The defect itself, on the real tree. At HEAD this scan produces compliance 10 of 115
        = 9%, a methodology dimension of 1/20 and a medium 'Partial methodology adoption (9%)'
        risk on the repo that publishes the methodology."""
        m = md.collect_all(CANONICAL_ROOT)
        self.assertEqual(m["methodology"]["role"], "framework")
        self.assertEqual(m["methodology"]["compliance_score"], md.FRAMEWORK_MAX)
        self.assertFalse(any("adoption" in r["description"] for r in m["scores"]["risks"]))
        # Not a whitewash: the findings that are TRUE of this repo must survive the reframing.
        self.assertTrue(any("No CI/CD pipeline" in r["description"]
                            for r in m["scores"]["risks"]))

    def test_the_role_provenance_on_the_card_is_wired_end_to_end(self):
        """Found by adversarial review: role_reason travelled from detect_repo_role to the card
        through collect_all with nothing pinning the wire. Both regressions are silent-and-wrong
        rather than loud — hardcoding the reason makes a MARKER-classified repo's card assert
        'structural: bin/_manifest.py + starter-kit/SESSION_RUNNER.md' about a repo that has
        neither file. A card that misstates why it graded you is this campaign's own defect."""
        def marked(p):
            (p / PROFILE_FILE).write_text("framework\n")     # no structural evidence at all
        m = md.collect_all(self._repo(marked))
        self.assertEqual(m["methodology"]["role"], "framework")
        self.assertEqual(m["methodology"]["role_reason"], "marker")
        card = md.render_project_card(m)
        self.assertIn("marker override", card)
        self.assertNotIn("bin/_manifest.py", card)

    def test_a_marker_contradiction_survives_the_wire_to_the_card(self):
        """The other unpinned half: dropping detect_repo_role's `reason or` fall-through would
        silently delete the D4 disclosure for every structurally-classified repo."""
        def conflicted(p):
            full_framework_tree(p)
            (p / PROFILE_FILE).write_text("framework adopter\n")
        m = md.collect_all(self._repo(conflicted))
        self.assertEqual(m["methodology"]["role"], "framework")
        self.assertEqual(m["methodology"]["role_reason"], "marker-contradiction")
        self.assertTrue(any("conflicting tokens" in r["description"]
                            for r in m["scores"]["risks"]))
        self.assertIn("conflicting role tokens", md.render_project_card(m))

    def test_the_presence_check_disclosure_is_on_both_cards(self):
        """Plan residual risk 8 names this footnote as THE honest disclosure for presence-based
        scoring, and it was never actually shipped. It is equally true of both checklists: a repo
        can score 100% while running a years-old runner, because .exists() cannot tell a
        maintained artifact from an abandoned one."""
        fw = md.render_project_card(md.collect_all(self._repo(full_framework_tree)))
        ad = md.render_project_card(md.collect_all(self._repo(full_compliance_tree)))
        for card, which in ((fw, "framework"), (ad, "adopter")):
            with self.subTest(card=which):
                self.assertIn("presence check", card)
                self.assertIn("does not verify these files are used", card)


class TestQualityGateSignals(unittest.TestCase):
    """Quality-ratchet plan D6 / Phase 3. RED-first against the 2.10.7 scanner, which has no
    `gates` key: every assertion below on a risk, a point, or a card string failed there.

    Silence is asserted as deliberately as signal (v3.6 D4): an absent manifest and the EMPTY
    seed bin/sync installs must produce no risk, or every synced adopter would gain one for a
    change they did not make."""

    def _repo(self, files_map, commits=None):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        p = Path(td.name)
        subprocess.run(["git", "init", "-q", str(p)], check=True)
        def commit(msg):
            subprocess.run(["git", "-C", str(p), "add", "-A"], check=True)
            subprocess.run(["git", "-C", str(p), "-c", "user.email=t@t", "-c", "user.name=t",
                            "commit", "-q", "-m", msg], check=True)
        for name, content in files_map.items():
            fp = p / name
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(content)
        commit("init")
        for msg, extra in (commits or []):
            for name, content in extra.items():
                (p / name).write_text(content)
            commit(msg)
        return p

    CODE = {
        "app.py": "def f():\n    return 1\n" * 40,
        "tests/test_app.py": "def test_f():\n    assert True\n" * 10,
        "README.md": "# App\n\nA thing.\n" * 5,
    }

    @staticmethod
    def _manifest(*gates):
        return json.dumps({"version": 1, "gates": list(gates)})

    @staticmethod
    def _gate(name, direction="min", threshold=1, **kw):
        g = {"name": name, "direction": direction, "threshold": threshold}; g.update(kw); return g

    @staticmethod
    def _results(cfg_text, statuses):
        cfg = json.loads(cfg_text)
        digest = hashlib.sha256(json.dumps(cfg["gates"], sort_keys=True).encode()).hexdigest()[:12]
        return json.dumps({"manifest": digest, "ran_at": "2026-09-15T00:00:00+00:00",
                           "gates": [{"name": g["name"], "status": st}
                                     for g, st in zip(cfg["gates"], statuses)],
                           "summary": {k: statuses.count(k) for k in ("pass", "fail", "unmeasured")}})

    def _gate_risks(self, m):
        return [r["description"] for r in m["scores"]["risks"]
                if "quality" in r["description"].lower() or "gate" in r["description"].lower()]

    def test_no_manifest_is_silent(self):
        m = md.collect_all(self._repo(self.CODE))
        self.assertFalse(m["gates"]["manifest_present"])
        self.assertEqual(self._gate_risks(m), [])
        self.assertIn("Quality Gates: <b>None</b>", md.render_project_card(m))

    def test_the_empty_seed_is_silent(self):
        seed = (CANONICAL_ROOT / "starter-kit" / "quality-gates.json").read_text(encoding="utf-8")
        m = md.collect_all(self._repo({**self.CODE, ".quality-gates.json": seed}))
        self.assertTrue(m["gates"]["manifest_present"])
        self.assertEqual(m["gates"]["declared"], 0)
        self.assertEqual(self._gate_risks(m), [], "the seed is a template: presence proves sync")
        self.assertIn("manifest seeded, none declared", md.render_project_card(m))

    def test_declared_but_never_run_is_an_advisory(self):
        cfg = self._manifest(self._gate("cov", "min", 80), self._gate("lint", "max", 0))
        m = md.collect_all(self._repo({**self.CODE, ".quality-gates.json": cfg}))
        self.assertEqual(m["gates"]["declared"], 2)
        risks = self._gate_risks(m)
        self.assertEqual(len(risks), 1)
        self.assertIn("2 declared quality gate(s), never run here", risks[0])
        self.assertIn("2 declared, never run", md.render_project_card(m))

    def test_a_failing_gate_is_named_and_high(self):
        cfg = self._manifest(self._gate("cov", "min", 80), self._gate("lint", "max", 0))
        m = md.collect_all(self._repo({**self.CODE, ".quality-gates.json": cfg,
                                       ".quality-gates-results.json": self._results(cfg, ["pass", "fail"])}))
        risk = [r for r in m["scores"]["risks"] if "outside their threshold" in r["description"]]
        self.assertEqual(len(risk), 1)
        self.assertEqual(risk[0]["severity"], "high")
        self.assertIn("lint", risk[0]["description"])
        self.assertIn("1 pass / 1 fail / 0 unmeasured", md.render_project_card(m))
        self.assertEqual(self._gate_risks(m).__len__(), 1, "a run present: no 'never run' advisory")

    def test_stale_results_are_flagged_and_earn_no_points(self):
        cfg_old = self._manifest(self._gate("coverage", "min", 80))
        cfg_new = self._manifest(self._gate("coverage", "min", 85))
        m = md.collect_all(self._repo({**self.CODE, ".quality-gates.json": cfg_new,
                                       ".quality-gates-results.json": self._results(cfg_old, ["pass"])}))
        self.assertTrue(m["gates"]["results_stale"])
        self.assertTrue(any("predate the current manifest" in r for r in self._gate_risks(m)))
        self.assertIn("(stale)", md.render_project_card(m))

    def test_a_gate_named_coverage_earns_no_points(self):
        # PR #82 review, section 4: the +2 keyed on a passing gate NAMED "coverage" — `echo 100`
        # earned it, from a gitignored results file no reviewer saw. Dropped until a faithfulness
        # gate is required beside it (the plan's own condition); score a measurement, never a name.
        base = md.collect_all(self._repo(self.CODE))
        cfg = self._manifest(self._gate("coverage", "min", 80, command="echo 100", extract=r"(\d+)"))
        with_cov = md.collect_all(self._repo({**self.CODE, ".quality-gates.json": cfg,
                                              ".quality-gates-results.json": self._results(cfg, ["pass"])}))
        self.assertEqual(with_cov["scores"]["health"]["testing"], base["scores"]["health"]["testing"])
        self.assertNotIn("coverage_measured_pass", with_cov["gates"])

    def test_an_unmeasured_gate_is_a_low_advisory(self):
        cfg = self._manifest(self._gate("cov", "min", 80), self._gate("declared-only", "min", 1))
        m = md.collect_all(self._repo({**self.CODE, ".quality-gates.json": cfg,
                                       ".quality-gates-results.json": self._results(cfg, ["pass", "unmeasured"])}))
        self.assertTrue(any("unmeasured (no command)" in r for r in self._gate_risks(m)))

    def test_a_loosening_in_git_history_is_a_risk_with_its_sha(self):
        cfg1 = self._manifest(self._gate("cov", "min", 80), self._gate("cc", "max", 10))
        cfg2 = self._manifest(self._gate("cov", "min", 70), self._gate("cc", "max", 10))   # floor lowered
        cfg3 = self._manifest(self._gate("cov", "min", 70))                                # gate removed
        p = self._repo({**self.CODE, ".quality-gates.json": cfg1},
                       commits=[("loosen", {".quality-gates.json": cfg2}),
                                ("remove", {".quality-gates.json": cfg3})])
        m = md.collect_all(p)
        kinds = [(l["name"], l["kind"]) for l in m["gates"]["loosened"]]
        self.assertEqual(kinds, [("cc", "removed"), ("cov", "floor lowered")], "newest first")
        sha = subprocess.run(["git", "-C", str(p), "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True).stdout.strip()
        risk = [r for r in m["scores"]["risks"] if "thresholds only tighten" in r["description"]]
        self.assertEqual(len(risk), 1)
        self.assertIn(f"`cc` removed in {sha}", risk[0]["description"])
        self.assertIn("(+1 earlier)", risk[0]["description"])
        self.assertIn("2 loosened", md.render_project_card(m))

    def _git(self, p, *args):
        return subprocess.run(["git", "-C", str(p), "-c", "user.email=t@t", "-c", "user.name=t", *args],
                              check=True, capture_output=True, text=True).stdout.strip()

    def test_a_deleted_manifest_is_reported_while_it_stays_deleted(self):
        # The largest loosening available: delete the file. The scanner used to return before
        # its history walk whenever the worktree had no manifest, so this state reported nothing.
        cfg = self._manifest(self._gate("cov", "min", 80), self._gate("cc", "max", 10))
        p = self._repo({**self.CODE, ".quality-gates.json": cfg})
        self._git(p, "rm", "-q", ".quality-gates.json"); self._git(p, "commit", "-q", "-m", "delete")
        sha = self._git(p, "rev-parse", "--short", "HEAD")
        m = md.collect_all(p)
        self.assertFalse(m["gates"]["manifest_present"])
        self.assertTrue(m["gates"]["manifest_deleted"])
        self.assertEqual(sorted((l["name"], l["kind"]) for l in m["gates"]["loosened"]),
                         [("cc", "removed"), ("cov", "removed")])
        self.assertTrue(all(l["sha"] == sha for l in m["gates"]["loosened"]))
        risk = [r for r in m["scores"]["risks"] if "thresholds only tighten" in r["description"]]
        self.assertEqual(len(risk), 1)
        self.assertIn("manifest deleted", risk[0]["description"])
        self.assertIn(sha, risk[0]["description"])
        self.assertIn("deleted", md.render_project_card(m))

    def test_delete_then_readd_lower_reports_the_net_loosening(self):
        # Mirrors quality_ratchet.newest_committed: each version is compared to the nearest OLDER
        # version that declared a gate, so 80 -> (deleted) -> 1 reads as 80 -> 1, not as "added".
        cfg1 = self._manifest(self._gate("cov", "min", 80))
        cfg2 = self._manifest(self._gate("cov", "min", 1))
        p = self._repo({**self.CODE, ".quality-gates.json": cfg1})
        self._git(p, "rm", "-q", ".quality-gates.json"); self._git(p, "commit", "-q", "-m", "delete")
        (p / ".quality-gates.json").write_text(cfg2)
        self._git(p, "add", "-A"); self._git(p, "commit", "-q", "-m", "re-add lower")
        m = md.collect_all(p)
        kinds = [(l["name"], l["kind"], l["from"], l["to"]) for l in m["gates"]["loosened"]]
        self.assertEqual(kinds, [("cov", "floor lowered", 80.0, 1.0), ("cov", "removed", 80.0, None)])

    def _git_at(self, p, when, *args, check=True):
        # The plain `git log` orders by COMMITTER date, so a test about how two lineages interleave
        # has to set it: commits made in the same second tie, and a tie is not a topology.
        env = {**os.environ, "GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when}
        return subprocess.run(["git", "-C", str(p), "-c", "user.email=t@t", "-c", "user.name=t", *args],
                              check=check, capture_output=True, text=True, env=env).stdout.strip()

    def _two_lineages(self, base, side, mainline, merged, side_date, main_date):
        """A repo whose manifest forks into two lineages and is joined by a --no-ff merge whose
        resolution is `merged`. Returns (path, merge sha). `side` and `mainline` each change the
        manifest relative to `base`; the dates say which of the two the plain `git log` lists first."""
        p = self._repo({**self.CODE, ".quality-gates.json": base})
        trunk = self._git(p, "symbolic-ref", "--short", "HEAD")
        self._git(p, "checkout", "-q", "-b", "side")
        (p / ".quality-gates.json").write_text(side)
        self._git_at(p, side_date, "add", "-A"); self._git_at(p, side_date, "commit", "-q", "-m", "side")
        self._git(p, "checkout", "-q", trunk)
        (p / ".quality-gates.json").write_text(mainline)
        self._git_at(p, main_date, "add", "-A"); self._git_at(p, main_date, "commit", "-q", "-m", "mainline")
        # Both lineages changed the manifest, so the merge conflicts: resolve it to `merged`.
        self._git_at(p, "2030-03-01T12:00:00", "merge", "--no-ff", "--no-commit", "side", check=False)
        (p / ".quality-gates.json").write_text(merged)
        self._git_at(p, "2030-03-01T12:00:00", "add", "-A")
        self._git_at(p, "2030-03-01T12:00:00", "commit", "-q", "-m", "merge side")
        return p, self._git(p, "rev-parse", "--short", "HEAD")

    def test_a_merged_lineage_is_not_read_as_one_line(self):
        # `git log -- <manifest>` without --first-parent follows BOTH parents of a merge whose
        # manifest matches neither, so it lists the two lineages interleaved by commit date, and the
        # fold compares each row with the next older ROW: the newer of two sibling commits was
        # compared with a commit that is not its ancestor. Here the mainline (120, tightened from
        # 100) is listed above the side branch (148 plus a gate), and the scan printed "cov floor
        # lowered 148 -> 120" and "ledger removed" -- changes nobody made: every version below is a
        # tightening against its own parent, and the merge keeps the better of both and adds a gate.
        # (A merge that matched ONE parent would hide this: git follows only that parent.)
        base = self._manifest(self._gate("cov", "min", 100))
        side = self._manifest(self._gate("cov", "min", 148), self._gate("ledger", "max", 0))
        mainline = self._manifest(self._gate("cov", "min", 120))
        merged = self._manifest(self._gate("cov", "min", 148), self._gate("ledger", "max", 0),
                                self._gate("lint", "max", 0))
        p, _merge = self._two_lineages(base, side, mainline, merged=merged,
                                       side_date="2030-01-01T12:00:00", main_date="2030-02-01T12:00:00")
        m = md.collect_all(p)
        self.assertEqual(m["gates"]["loosened"], [])
        self.assertEqual(m["gates"]["commands_changed"], [])
        self.assertFalse([r for r in m["scores"]["risks"] if "thresholds only tighten" in r["description"]])

    def test_a_loosening_a_merge_resolves_to_is_reported_at_the_merge(self):
        # The other direction, and the one SAFEGUARDS depends on: merge commits skip the pre-commit
        # hook, so "a loosening resolved into a merge is caught by the dashboard's read of the
        # manifest's history". Both lineages tighten against `base` (120 and 110), and the merge
        # resolves to the LOWER of the two -- a loosening of the line it merged into (120 -> 110).
        # The merge matches the side branch, so the plain log follows only that parent: the
        # mainline's 120 was never compared with anything, and the scan reported nothing.
        base = self._manifest(self._gate("cov", "min", 100))
        side = self._manifest(self._gate("cov", "min", 110))
        mainline = self._manifest(self._gate("cov", "min", 120))
        p, merge = self._two_lineages(base, side, mainline, merged=side,
                                      side_date="2030-01-01T12:00:00", main_date="2030-02-01T12:00:00")
        m = md.collect_all(p)
        self.assertEqual([(l["name"], l["kind"], l["from"], l["to"], l["sha"])
                          for l in m["gates"]["loosened"]],
                         [("cov", "floor lowered", 120.0, 110.0, merge)])

    def test_a_loosening_a_side_branch_carried_in_is_attributed_to_the_merge(self):
        # A loosening made on a side branch reaches the line the repo is on only through the merge,
        # so the merge is where it is reported -- compared with the line it merged INTO, which is the
        # comparison the pre-commit ratchet makes against HEAD. Trace it with
        # `git diff <sha>^1 <sha> -- .quality-gates.json`: a clean merge shows no combined diff.
        base = self._manifest(self._gate("cov", "min", 100))
        side = self._manifest(self._gate("cov", "min", 50))
        p = self._repo({**self.CODE, ".quality-gates.json": base})
        trunk = self._git(p, "symbolic-ref", "--short", "HEAD")
        self._git(p, "checkout", "-q", "-b", "side")
        (p / ".quality-gates.json").write_text(side)
        self._git(p, "add", "-A"); self._git(p, "commit", "-q", "-m", "lower the floor")
        self._git(p, "checkout", "-q", trunk)
        (p / "README.md").write_text("# App\n\nChanged on the trunk.\n")
        self._git(p, "add", "-A"); self._git(p, "commit", "-q", "-m", "unrelated trunk change")
        self._git(p, "merge", "--no-ff", "-q", "-m", "merge side", "side")      # clean: no conflict
        merge = self._git(p, "rev-parse", "--short", "HEAD")
        m = md.collect_all(p)
        self.assertEqual([(l["name"], l["kind"], l["from"], l["to"], l["sha"])
                          for l in m["gates"]["loosened"]],
                         [("cov", "floor lowered", 100.0, 50.0, merge)])

    def test_a_direction_flip_is_a_loosening(self):
        cfg1 = self._manifest(self._gate("cov", "min", 80))
        cfg2 = self._manifest(self._gate("cov", "max", 80))
        p = self._repo({**self.CODE, ".quality-gates.json": cfg1},
                       commits=[("flip", {".quality-gates.json": cfg2})])
        m = md.collect_all(p)
        self.assertEqual([(l["name"], l["kind"]) for l in m["gates"]["loosened"]],
                         [("cov", "direction flipped")])
        self.assertTrue(any("thresholds only tighten" in r for r in self._gate_risks(m)))

    def test_a_changed_command_is_a_low_advisory_not_a_loosening(self):
        cfg1 = self._manifest(self._gate("cov", "min", 80, command="pytest --cov", extract=r"(\d+)%"))
        cfg2 = self._manifest(self._gate("cov", "min", 80, command="echo 'TOTAL 99%'", extract=r"(\d+)%"))
        p = self._repo({**self.CODE, ".quality-gates.json": cfg1},
                       commits=[("swap", {".quality-gates.json": cfg2})])
        m = md.collect_all(p)
        self.assertEqual(m["gates"]["loosened"], [])
        self.assertEqual([(c["name"], c["field"]) for c in m["gates"]["commands_changed"]], [("cov", "command")])
        risk = [r for r in m["scores"]["risks"] if "command" in r["description"] and "cov" in r["description"]]
        self.assertEqual(len(risk), 1)
        self.assertEqual(risk[0]["severity"], "low")

    def test_tightening_and_adding_are_not_loosenings(self):
        cfg1 = self._manifest(self._gate("cov", "min", 80))
        cfg2 = self._manifest(self._gate("cov", "min", 90), self._gate("cc", "max", 10))
        p = self._repo({**self.CODE, ".quality-gates.json": cfg1},
                       commits=[("tighten+add", {".quality-gates.json": cfg2})])
        m = md.collect_all(p)
        self.assertEqual(m["gates"]["loosened"], [])
        self.assertFalse(any("thresholds only tighten" in r for r in self._gate_risks(m)))

    def test_history_scan_is_git_only_and_never_runs_a_gate_command(self):
        # A gate whose command would leave a footprint if executed: the scanner must not run it.
        marker = "scanner-ran-me.txt"
        cfg = self._manifest(self._gate("touch", "max", 0, command=f"touch {marker}"))
        p = self._repo({**self.CODE, ".quality-gates.json": cfg})
        md.collect_all(p)
        self.assertFalse((p / marker).exists(), "collect_all executed a declared gate command")

    def test_doc_only_repo_keeps_its_render_slot(self):
        # The measured-coverage bonus lives in the code branch only; a doc-only repo's 2nd slot is
        # the render proxy, and a coverage gate there must not leak points into it.
        cfg = self._manifest(self._gate("coverage", "min", 80))
        docs = {"chapter1.md": "# Ch1\n" + "prose line\n" * 400,
                "chapter2.md": "# Ch2\n" + "prose line\n" * 400,
                "_quarto.yml": "format:\n  pdf:\n    mainfont: TeX Gyre\n",
                ".quality-gates.json": cfg,
                ".quality-gates-results.json": self._results(cfg, ["pass"])}
        m = md.collect_all(self._repo(docs))
        self.assertTrue(m["doc_only"]["is_doc_only"])
        self.assertEqual(m["scores"]["health"]["testing"], m["render"]["score"])


class TestDotfileConfigCategory(unittest.TestCase):
    """CONFIG_EXTS lists dotfile names (.gitignore, .editorconfig, …), but categorize_file is called
    with Path.suffix, which is "" for a dotfile — so none of them ever matched and every one read as
    "other" (found in S30 while categorizing the .gitattributes seed). Display only: no score reads it."""

    def cat(self, name):
        return md.categorize_file(Path(name), Path(name).suffix.lower(), name)

    def test_dotfiles_listed_as_config_are_config(self):
        for name in (".gitignore", ".editorconfig", ".eslintrc", ".prettierrc"):
            self.assertEqual(self.cat(name), "config", name)

    def test_a_dotfile_not_listed_is_still_other(self):
        self.assertEqual(self.cat(".mailmap"), "other")

    def test_suffix_matching_is_unchanged(self):
        self.assertEqual(self.cat("settings.json"), "config")
        self.assertEqual(self.cat("notes.xyz"), "other")


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
        """⚠ PINNED TWICE ON PURPOSE — the module attribute AND the starter-kit source text. Bump
        BOTH or this goes red. 2.19.0: the Class B
        read-cap row asserts only what it evaluated and names a remedy it has read from the
        project's own trimmer source -- changed output on a distributed tool, so MINOR.
        2.20.0: the `.gitattributes` seed becomes installed content -- changed output
        on a distributed tool, so MINOR. 2.21.0: the manifest-history walk is first-parent,
        so a merged lineage no longer prints loosenings nobody caused -- changed output, so MINOR.
        2.22.0: the dashboard reads a project that keeps its methodology files under
        methodology/ as it reads one that keeps them at the root -- changed output, so MINOR."""
        self.assertEqual(md.DASHBOARD_VERSION, "2.22.0")
        starter_src = Path(STARTER_PY).read_text(encoding="utf-8")
        self.assertTrue(re.search(r'^DASHBOARD_VERSION\s*=\s*"2\.22\.0"', starter_src, re.MULTILINE),
                        "starter-kit twin must also declare DASHBOARD_VERSION 2.22.0")


class TestCliRemedyProportionality(unittest.TestCase):
    """Issue #67 — the CLI must not answer a small finding with a portfolio-wide write, and a
    flag named --dry-run must never write. Both are CLI-surface behaviors, so both are driven
    through a real subprocess: importing the module cannot observe main()'s argument handling.
    """

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.p = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()

    def _project(self, name="proj"):
        """A minimal git project with its own copy of the scanner, ready to run."""
        proj = self.p / name
        proj.mkdir(parents=True)
        write_tree(proj, {"README.md": "# p\n"})
        subprocess.run(["git", "init", "-q", str(proj)], check=True)
        subprocess.run(["git", "-C", str(proj), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(proj), "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-qm", "i"], check=True)
        shutil.copy(TOOLS_PY, proj / "methodology_dashboard.py")
        return proj

    def test_bare_dry_run_refuses_instead_of_writing(self):
        # The defect: --dry-run was consulted ONLY inside the --sync branch, so on its own it
        # fell through to a full scan and wrote both artifacts. Assert the artifacts, not just
        # the exit code — "it exits non-zero" would still pass if it wrote and then failed.
        proj = self._project()
        r = subprocess.run([sys.executable, "methodology_dashboard.py", "--dry-run"],
                           cwd=proj, capture_output=True, text=True)
        self.assertEqual(r.returncode, 2, "bare --dry-run must be an error, not a silent full run")
        self.assertFalse((proj / "dashboard.html").exists(),
                         "--dry-run must not write dashboard.html")
        self.assertFalse((proj / "dashboard_history.jsonl").exists(),
                         "--dry-run must not append to dashboard_history.jsonl")
        self.assertIn("--sync", r.stderr, "the refusal must say what the flag is actually for")

    def test_a_normal_run_still_writes(self):
        # Presence control: without it, a scanner that refused EVERY invocation would pass the
        # test above and look fixed.
        proj = self._project()
        r = subprocess.run([sys.executable, "methodology_dashboard.py", "--no-open"],
                           cwd=proj, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertTrue((proj / "dashboard.html").exists(),
                        "a plain run must still generate the dashboard")

    # NOTE: upstream's third test in this class is deliberately not carried:
    # `test_stale_warning_leads_with_the_project_scoped_remedy` asserts a literal `"cp "` in the
    # stale-copy warning, and this branch's warning prints a `--sync` scoped to the one project
    # instead, so it would fail against the design that replaced it, not catch a defect. The two
    # tests above assert behaviour this branch keeps (a bare `--dry-run` exits 2 and writes
    # nothing; a plain run writes dashboard.html) and are restored as upstream wrote them.


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

    def test_full_compliance_tree_end_to_end_never_exceeds_100(self):
        """The live blast radius (plan §2.1): an adopter with every checklist artifact scored
        compliance 110 -> methodology 22/20 -> total 90/100, and its card read '110%'."""
        p = self._repo({"README.md": "# demo\n" * 60})
        full_compliance_tree(p)
        subprocess.run(["git", "-C", str(p), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(p), "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-q", "-m", "compliance"], check=True)
        m = md.collect_all(p)

        self.assertEqual(m["methodology"]["missing_files"], [])
        self.assertEqual(m["methodology"]["compliance_score"], md.METHODOLOGY_MAX)
        self.assertEqual(m["methodology"]["compliance_pct"], 100)
        self.assertEqual(m["scores"]["health"]["methodology"], 20)
        self.assertLessEqual(m["scores"]["health"]["total"], 100)

        card = md.render_project_card(m)
        self.assertIn(f"Methodology Compliance (100% ({md.METHODOLOGY_MAX} of "
                      f"{md.METHODOLOGY_MAX}))", card)
        self.assertNotIn(f"Methodology Compliance ({md.METHODOLOGY_MAX}%)", card)
        self.assertIn("HANDOFFS.md", card)
        self.assertFalse(any("methodology adoption" in r["description"]
                             for r in m["scores"]["risks"]))

    def test_pre_v33_adopter_tree_end_to_end(self):
        """Ratified decision D2's accepted cost, driven end to end: an adopter that has every
        checklist artifact EXCEPT HANDOFFS.md (the shape of every project seeded before v3.3)
        scores below 100% until it re-seeds — and the shortfall it is told about is exactly the
        weight of the file it is missing."""
        p = self._repo({"README.md": "# demo\n" * 60})
        full_compliance_tree(p)
        (p / "HANDOFFS.md").unlink()
        subprocess.run(["git", "-C", str(p), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(p), "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-q", "-m", "pre-v3.3"], check=True)
        m = md.collect_all(p)
        handoffs_weight = next(w for path, w, _ in md.METHODOLOGY_ITEMS if path == "HANDOFFS.md")

        self.assertEqual(m["methodology"]["missing_files"], ["HANDOFFS.md"])
        self.assertEqual(m["methodology"]["compliance_score"],
                         md.METHODOLOGY_MAX - handoffs_weight)
        self.assertLess(m["methodology"]["compliance_pct"], 100)
        # Still a healthy repo: the missing seed costs at most one point of the 0-20 dimension.
        self.assertGreaterEqual(m["scores"]["health"]["methodology"], 19)
        self.assertLessEqual(m["scores"]["health"]["total"], 100)
        self.assertFalse(any("methodology adoption" in r["description"]
                             for r in m["scores"]["risks"]))

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


def installed_scanner(loc=3070, version="2.10.0", marker=True):
    """Text that stands in for the copy `bin/sync` installs at an adopter's root.

    The predicate reads a NAME and a MARKER, never a size, so a faithful stand-in only has to
    declare DASHBOARD_VERSION near the top and be long. `version` deliberately defaults to an
    OLDER release: adopters lag canonical, and an exclusion that only recognized the current
    version would leave every lagging adopter still mis-measured.
    """
    head = f'#!/usr/bin/env python3\n"""stand-in."""\n'
    if marker:
        head += f'DASHBOARD_VERSION = "{version}"\n'
    return head + "".join(f"def gen_{i}():\n    return {i}\n" for i in range(loc // 2))


def installed_trimmer(loc=1600, version="1.0.0", marker=True):
    """Text that stands in for the ledger trimmer `bin/sync` installs at an adopter's root.

    The SECOND executable adopters receive, and it proves itself by a DIFFERENT constant than the
    scanner does. Measured against the real tool rather than assumed:

        grep -c DASHBOARD_VERSION starter-kit/methodology_trim.py                      -> 0
        for s in METHODOLOGY_ITEMS 'def collect_all' 'def score_health' \\
                 'def assess_risks' https://github.com/KJ5HST/methodology; do \\
          grep -c -- "$s" starter-kit/methodology_trim.py; done                        -> 0 0 0 0 0

    So the earlier predicate answered False for this file on BOTH of its arms, and putting the
    name on the exclusion tuple alone would not have changed that — the content gate is the work.

    Those two are ZERO-counts, which is why they are quoted and the tool's line count and the
    line number of its TRIM_VERSION are NOT. Both of those were published here with real measured
    values and both were falsified before this session ended, by this session's own later edit to
    the trimmer's module docstring. A count that moves whenever anyone touches a comment is a
    liability in a docstring; re-derive it (`wc -l starter-kit/methodology_trim.py`) if you need
    it. `loc` below is a nominal default chosen to sit well above DOC_ONLY_SOURCE_LOC_MAX, not a
    claim about the shipped file's size — the test that pins the fixture against the REAL artifact
    is test_every_shipped_executable_is_recognized_from_its_real_source. `version` defaults to the
    shipped one; unlike the scanner there are no pre-constant copies in the wild to lag behind.
    """
    head = '#!/usr/bin/env python3\n"""stand-in."""\n'
    if marker:
        head += f'TRIM_VERSION = "{version}"\n'
    return head + "".join(f"def gen_{i}():\n    return {i}\n" for i in range(loc // 2))


class TestFrameworkInstalledExclusion(unittest.TestCase):
    """Layer 7 — `bin/sync` installs a 3,070-line scanner into the adopter's ROOT while the
    doc-only cap is 200 LOC, so the source-cap short-circuit fired before the corpus disjunction
    was ever consulted: **installing the methodology destroyed the doc-only fair-scoring v3.2
    shipped**. Live since v3.2; found by Layer 5's late boundary review, ratified as fix A.

    RED-first: (a)/(d) were driven against the pre-fix scanner and watched to FAIL (a reported
    doc_only=False with source_loc=3070 and a HIGH "No test infrastructure" risk). The
    anti-laundering and manifest-agreement tests are guard-the-guard checks — they constrain the
    fix rather than prove the defect, and are expected to pass only after it.
    """

    def _repo(self, files_map):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        p = Path(td.name)
        subprocess.run(["git", "init", "-q", str(p)], check=True)
        write_tree(p, files_map)
        subprocess.run(["git", "-C", str(p), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(p), "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-q", "-m", "init"], check=True)
        return p

    # The synced doc corpus: a Quarto book. If .qmd files were NOT doc-extensions,
    # the render-toolchain arm of the disjunction would be the ONLY thing that could carry this fixture
    # — the exact source_loc≈0 research repo the doc-only rule exists for. Since .qmd/.rmd are in DOC_EXTS,
    # this two-chapter fixture's own doc_loc (~400) now ALSO clears DOC_ONLY_DOC_LOC_MIN on its
    # own — it still proves is_doc_only stays True, just no longer in isolation from the corpus
    # arm. `test_a_pure_quarto_repo_below_doc_thresholds_still_doc_only_via_toolchain` below is the
    # fixture that isolates the toolchain arm.
    QUARTO = {
        "_quarto.yml": "project:\n  type: book\n",
        "ch1.qmd": "# Ch1\n" + "prose\n" * 200,
        "ch2.qmd": "# Ch2\n" + "prose\n" * 200,
        "README.md": "# Monograph\n\nA Quarto book.\n" * 4,
    }

    # A single short chapter — doc_loc and doc_files both stay under the thresholds even with
    # .qmd counted as docs, so is_doc_only can ONLY be reached via render.toolchain_present.
    QUARTO_MINIMAL = {
        "_quarto.yml": "project:\n  type: book\n",
        "index.qmd": "# Index\none line of prose\n",
    }

    def test_a_synced_doc_repo_is_still_doc_only(self):
        """RED: reported False (source_loc 3,070 > the 200 cap) before the exclusion."""
        p = self._repo({**self.QUARTO, "methodology_dashboard.py": installed_scanner()})
        m = md.collect_all(p)
        self.assertTrue(m["doc_only"]["is_doc_only"],
                        "installing the methodology must not change a doc repo's classification")
        self.assertEqual(m["tests"]["source_loc"], 0,
                         "the adopter wrote no source; only the installed scanner was present")
        self.assertGreater(m["files"]["by_category"]["vendor"]["loc"], 2000,
                           "the excluded LOC must remain visible, not vanish from the inventory")

    def test_a_pure_quarto_repo_below_doc_thresholds_still_doc_only_via_toolchain(self):
        """Guard-the-guard: adding .qmd to DOC_EXTS must not make the toolchain arm of the
        corpus disjunction unreachable through real scanning. QUARTO_MINIMAL's own doc_loc/doc_files
        are asserted BELOW both thresholds, so is_doc_only=True here can only be explained by
        render.toolchain_present — the same real-scan proof QUARTO used to carry alone."""
        p = self._repo(dict(self.QUARTO_MINIMAL))
        m = md.collect_all(p)
        docs = m["files"]["by_category"]["docs"]
        self.assertLess(docs["loc"], md.DOC_ONLY_DOC_LOC_MIN,
                         "fixture must stay under the doc-LOC threshold to isolate the toolchain arm")
        self.assertLess(docs["count"], md.DOC_ONLY_DOC_FILES_MIN,
                         "fixture must stay under the doc-files threshold to isolate the toolchain arm")
        self.assertTrue(m["render"]["toolchain_present"], "_quarto.yml must be detected")
        self.assertTrue(m["doc_only"]["is_doc_only"],
                         "a real Quarto repo too small for the doc-corpus arms must still be caught")

    def test_d_no_test_risk_absent_when_synced_doc_repo_present_when_real(self):
        """RED: the HIGH risk was present on the synced doc repo before the exclusion."""
        def risks_of(m):
            return [r["description"] for r in m["scores"]["risks"]]

        synced_doc = md.collect_all(
            self._repo({**self.QUARTO, "methodology_dashboard.py": installed_scanner()}))
        self.assertNotIn("No test infrastructure", risks_of(synced_doc))
        # Control: the risk must still fire where it is TRUE, or the fix is just suppression.
        real_code = md.collect_all(self._repo({
            "app.py": "def f(x):\n    return x\n" * 200,
            "README.md": "# app\n",
        }))
        self.assertIn("No test infrastructure", risks_of(real_code))

    def test_b_synced_code_repo_still_reads_as_code(self):
        p = self._repo({
            "app/core.py": "def f(x):\n    return x\n" * 500,   # 1,000 own LOC, over the cap
            "README.md": "# app\n",
            "methodology_dashboard.py": installed_scanner(),
        })
        m = md.collect_all(p)
        self.assertFalse(m["doc_only"]["is_doc_only"])
        self.assertEqual(m["tests"]["source_loc"], 1000,
                         "the adopter's own source must survive the exclusion intact")

    def test_c_unsynced_doc_repo_is_unchanged(self):
        """Regression guard on the v3.2 path — no exclusion applies, nothing moves."""
        m = md.collect_all(self._repo(self.QUARTO))
        self.assertTrue(m["doc_only"]["is_doc_only"])
        self.assertEqual(m["files"]["by_category"]["vendor"], {"count": 0, "loc": 0})

    def test_rejected_cap_fix_would_misclassify_a_real_code_repo(self):
        """CHARACTERIZATION of why fix **B** was rejected. Passes before AND after Layer 7 — it
        constrains a future session, it does not prove this layer. Labeled so nobody mistakes it
        for coverage (plan §8 learning 2).

        It also **corrects the plan's own RED-first clause (b)**, which asserts that the synced
        code fixture "must be seen to fail against a wrong fix such as B". Measured, it is not —
        and the reason is not the one this docstring gave before Layer 6 re-measured it. Post
        Layer 7 the installed scanner is categorized `vendor`, so the cap never sees it: it sees
        only the adopter's own 1,000 LOC. Raising the cap therefore does not keep the fixture
        above it — it merely lets control fall through to the corpus disjunction, which this
        fixture fails on a single README with no render toolchain. So the fixture reads `code` at
        **every** cap (measured 200 / 1,000 / 3,100 / 4,100 / 6,000 / 10,000), and no threshold
        moves it at all. What B actually breaks is an **unsynced** real code repo
        with a doc corpus, whose OWN source sits under the raised cap: it silently becomes
        doc-only and loses its "No test infrastructure" risk. That — not the synced fixture — is
        v3.2's written guarantee (a mixed code+docs repo is never misclassified) being
        surrendered, so that is what this test pins.
        """
        p = self._repo({
            "app/core.py": "def f(x):\n    return x\n" * 500,   # 1,000 own LOC
            "GUIDE.md": "# guide\n" + "prose\n" * 200,
            "DESIGN.md": "# design\n" + "prose\n" * 200,
            "README.md": "# app\n" * 20,
        })
        original = md.DOC_ONLY_SOURCE_LOC_MAX
        self.addCleanup(setattr, md, "DOC_ONLY_SOURCE_LOC_MAX", original)
        self.assertFalse(md.collect_all(p)["doc_only"]["is_doc_only"])   # under the real cap
        md.DOC_ONLY_SOURCE_LOC_MAX = 4100                                # simulate fix B
        m = md.collect_all(p)
        self.assertTrue(m["doc_only"]["is_doc_only"],
                        "characterizing WHY B was rejected: a real code repo flips to doc-only")
        self.assertNotIn("No test infrastructure",
                         [r["description"] for r in m["scores"]["risks"]],
                         "and loses the risk that was true — the harm, not merely the label")

    # --- anti-laundering: the exclusion must only ever remove a file WE put there -------------

    def test_adopters_own_file_of_the_same_name_is_not_excluded(self):
        """Root-anchored, not basename-matched: a nested same-named file stays adopter source."""
        p = self._repo({
            "src/methodology_dashboard.py": installed_scanner(loc=3000),
            "README.md": "# app\n",
        })
        m = md.collect_all(p)
        self.assertGreater(m["tests"]["source_loc"], 200)
        self.assertEqual(m["files"]["by_category"]["vendor"]["count"], 0)
        self.assertFalse(m["doc_only"]["is_doc_only"])

    def test_root_file_without_the_marker_is_not_excluded(self):
        """Content-verified: renaming an application to the framework's name does not hide it."""
        p = self._repo({
            "methodology_dashboard.py": installed_scanner(loc=3000, marker=False),
            "README.md": "# app\n",
        })
        m = md.collect_all(p)
        self.assertGreater(m["tests"]["source_loc"], 200)
        self.assertEqual(m["files"]["by_category"]["vendor"]["count"], 0)

    def test_canonical_repo_still_pays_for_the_file_it_authors(self):
        """This repo publishes the scanner from tools/ + starter-kit/ — neither is a root dest, so
        both stay ITS source. A framework that laundered its own largest file would be scoring
        itself by a rule it does not apply to anyone else."""
        p = self._repo({
            "tools/methodology_dashboard.py": installed_scanner(loc=3000),
            "starter-kit/methodology_dashboard.py": installed_scanner(loc=3000),
            "README.md": "# framework\n",
        })
        m = md.collect_all(p)
        self.assertEqual(m["files"]["by_category"]["vendor"]["count"], 0)
        self.assertGreater(m["tests"]["source_loc"], 3000)

    def test_a_test_file_named_like_the_scanner_is_still_a_test(self):
        """categorize_file runs first, so the reclassification can only ever touch `source`.

        Boundary review caught that the end-to-end half of this is INERT: `test_*` is categorized
        before the predicate is consulted, so `collect_all` here never calls
        is_framework_installed at all and the assertions below would hold with the whole
        reclassification deleted. Kept for the ordering guarantee, honestly labeled, and paired
        with a direct call so the predicate is actually exercised on this input.
        """
        p = self._repo({"test_methodology_dashboard.py": installed_scanner(loc=400)})
        m = md.collect_all(p)
        self.assertEqual(m["files"]["by_category"]["vendor"]["count"], 0)
        self.assertGreater(m["files"]["by_category"]["test"]["loc"], 0)
        # Direct: even asked outright, the predicate rejects it — it is not a root dest name.
        self.assertFalse(md.is_framework_installed(
            Path("test_methodology_dashboard.py"), p / "test_methodology_dashboard.py"))

    def test_predicate_reads_the_whole_file_not_a_prefix(self):
        """The real scanner declares DASHBOARD_VERSION only a few hundred bytes clear of where a
        4096-byte read window ended, so ordinary growth of the module header would have switched
        the exclusion off silently — a signal that stops meaning what it appears to mean, inside
        the fix for exactly that bug. RED against the windowed version. (The margin is a snapshot,
        deliberately not asserted here: it was ~1,572 bytes when this test was written and 687 by
        the time the release branch was cut. This test does not depend on the number, which is the
        point — assert the behavior, not the measurement.)"""
        p = self._repo({"methodology_dashboard.py":
                        "# padding\n" * 900 + 'DASHBOARD_VERSION = "2.10.1"\n' + "x = 1\n" * 2000})
        self.assertTrue(md.is_framework_installed(
            Path("methodology_dashboard.py"), p / "methodology_dashboard.py"))
        self.assertEqual(md.collect_all(p)["tests"]["source_loc"], 0)

    def test_the_real_shipped_artifact_is_recognized(self):
        """Guard-the-guard, and it passes both before and after by construction — the real file's
        marker still sits inside the old 4,096-byte window, so this cannot RED against it
        (test_predicate_reads_the_whole_file_not_a_prefix is what catches that). Its value is as a
        stand-in-vs-real-artifact drift guard. Every other fixture uses a stand-in. If the stand-in and the real file ever diverge in
        a way the predicate cares about, only this test notices."""
        real = Path(STARTER_PY).read_text(encoding="utf-8")
        p = self._repo({"methodology_dashboard.py": real, "README.md": "# adopter\n"})
        m = md.collect_all(p)
        self.assertEqual(m["files"]["by_category"]["vendor"]["count"], 1)
        self.assertEqual(m["tests"]["source_loc"], 0)

    def test_every_shipped_executable_is_recognized_from_its_real_source(self):
        """The generalization of the test above, and the one that was MISSING: nothing iterated
        FRAMEWORK_INSTALLED_SOURCE, so every content fixture hardcoded the scanner. A future name
        added to the table with a content rule that does not match its own shipped file would ship
        the v3.2 regression under a green suite — the tuple would agree with the manifest and the
        predicate would still answer False.

        Reads each name's REAL artifact out of starter-kit/, resolved through the manifest rather
        than by assuming `starter-kit/<dest>`: the source path is the manifest's business, and
        hardcoding it here would re-introduce exactly the duplicated cross-reference the
        manifest-agreement test exists to prevent."""
        src_for = {dest: src for src, dest, _d in self._manifest().DISTRIBUTION}
        # 6 once upstream's quality ratchet ships quality_ratchet.py
        # and its .quality-gates.json seed, and the loop below checks both against their real files.
        # 7 with upstream's v4.1 `.gitattributes` seed.
        self.assertEqual(len(md.FRAMEWORK_INSTALLED_SOURCE), 7,
                         "population guard: update this test's expectations deliberately when a "
                         "further executable ships, rather than letting the loop silently cover less")
        for dest in md.FRAMEWORK_INSTALLED_SOURCE:
            real = Path(os.path.dirname(HERE), src_for[dest]).read_text(encoding="utf-8")
            p = self._repo({dest: real, "README.md": "# adopter\n"})
            self.assertTrue(
                md.is_framework_installed(Path(dest), p / dest),
                f"{dest} is on the exclusion table but its own shipped source does not satisfy "
                f"the content rule declared for it — the exclusion is inert for this file")
            self.assertEqual(md.collect_all(p)["tests"]["source_loc"], 0,
                             f"{dest} was recognized but still counted as adopter source")

    def test_pre_version_copies_are_recognized_by_structure(self):
        """A live adopter still runs a 1,614-line copy that predates DASHBOARD_VERSION entirely.
        A version-only gate silently skipped it — the fix not applying is as bad as it being
        wrong, and worse to notice. Two structural signatures are required, so an unrelated
        application cannot trip it by mentioning one word."""
        legacy = ('#!/usr/bin/env python3\n'
                  '"""Methodology Dashboard -- Portfolio health scanner.\n'
                  'https://github.com/KJ5HST/methodology\n"""\n'
                  'METHODOLOGY_ITEMS = []\n'
                  'def collect_all(p):\n    return {}\n' + "x = 1\n" * 1600)
        self.assertNotIn("DASHBOARD_VERSION", legacy)
        p = self._repo({"methodology_dashboard.py": legacy, "README.md": "# adopter\n"})
        self.assertEqual(md.collect_all(p)["tests"]["source_loc"], 0)

    def test_one_incidental_signature_is_not_enough(self):
        """Guard-the-guard on the structural fallback: a single mention must not exempt a file."""
        app = ("# our internal dashboard\n"
               "def collect_all(items):\n    return list(items)\n" + "y = 2\n" * 1000)
        p = self._repo({"methodology_dashboard.py": app, "README.md": "# adopter\n"})
        self.assertFalse(md.is_framework_installed(
            Path("methodology_dashboard.py"), p / "methodology_dashboard.py"))
        self.assertGreater(md.collect_all(p)["tests"]["source_loc"], 200)

    # --- The SECOND installed executable ------------------------------------------------
    #
    # The scanner's own exclusion fixed this defect for the scanner. Shipping the trimmer re-opens it for a file that
    # proves itself by a different constant, so the fix does not generalize for free: the two
    # RED-first tests below were driven against the earlier scanner and watched to FAIL
    # (doc_only=False, source_loc=1632, the HIGH "No test infrastructure" risk back).

    def test_a_synced_doc_repo_with_the_trimmer_is_still_doc_only(self):
        """RED: reported False (source_loc 1,632 > the 200 cap) before the trimmer was recognized."""
        p = self._repo({**self.QUARTO, "methodology_trim.py": installed_trimmer()})
        m = md.collect_all(p)
        self.assertTrue(m["doc_only"]["is_doc_only"],
                        "installing the trimmer must not change a doc repo's classification")
        self.assertEqual(m["tests"]["source_loc"], 0,
                         "the adopter wrote no source; only the installed trimmer was present")
        self.assertGreater(m["files"]["by_category"]["vendor"]["loc"], 800,
                           "the excluded LOC must remain visible, not vanish from the inventory")

    def test_trimmer_alone_does_not_reintroduce_the_no_test_risk(self):
        """RED: the HIGH risk was present on a doc repo carrying only the trimmer."""
        def risks_of(m):
            return [r["description"] for r in m["scores"]["risks"]]

        synced = md.collect_all(
            self._repo({**self.QUARTO, "methodology_trim.py": installed_trimmer()}))
        self.assertNotIn("No test infrastructure", risks_of(synced))

    def test_both_installed_executables_are_excluded_together(self):
        """A REAL `bin/sync` leaves both at the root; excluding one and not the other still
        breaks the adopter, so the whole-install case is pinned rather than inferred."""
        p = self._repo({**self.QUARTO,
                        "methodology_dashboard.py": installed_scanner(),
                        "methodology_trim.py": installed_trimmer()})
        m = md.collect_all(p)
        self.assertTrue(m["doc_only"]["is_doc_only"])
        self.assertEqual(m["tests"]["source_loc"], 0)
        self.assertGreater(m["files"]["by_category"]["vendor"]["loc"], 4000,
                           "both executables must land in vendor, not one of them")

    def test_a_lookalike_trimmer_without_its_version_constant_is_not_excluded(self):
        """GUARD-THE-GUARD, and green before the fix as well as after — it constrains the fix, it
        does not prove it (an absence assertion is trivially true before the name
        exists). It earns its place by producer mutation: deleting the trimmer's content check
        makes it fail. An adopter's own 1,000-line `methodology_trim.py` is THEIRS."""
        app = ("# our own ledger trimmer\n" + "y = 2\n" * 1000)
        p = self._repo({"methodology_trim.py": app, "README.md": "# adopter\n"})
        self.assertFalse(md.is_framework_installed(
            Path("methodology_trim.py"), p / "methodology_trim.py"))
        self.assertGreater(md.collect_all(p)["tests"]["source_loc"], 200)

    def test_adopters_own_nested_trimmer_is_not_excluded(self):
        """Root-anchored for the trimmer too, not basename-matched."""
        p = self._repo({"tools/methodology_trim.py": installed_trimmer(loc=1000),
                        "README.md": "# app\n"})
        m = md.collect_all(p)
        self.assertGreater(m["tests"]["source_loc"], 200)
        self.assertEqual(m["files"]["by_category"]["vendor"]["count"], 0)

    def test_the_scanner_marker_does_not_launder_the_trimmer_or_the_reverse(self):
        """Each name proves itself with ITS OWN constant. A shared any-of-these-markers rule would
        make the two interchangeable, so a file could be exempted by carrying the wrong tool's
        constant — the laundering hole the per-file table exists to close."""
        wrong_marker_trimmer = ('#!/usr/bin/env python3\nDASHBOARD_VERSION = "2.12.0"\n'
                                + "y = 2\n" * 1000)
        p = self._repo({"methodology_trim.py": wrong_marker_trimmer, "README.md": "# a\n"})
        self.assertFalse(md.is_framework_installed(
            Path("methodology_trim.py"), p / "methodology_trim.py"),
            "a file named methodology_trim.py must not be exempted by the SCANNER's constant")
        wrong_marker_scanner = ('#!/usr/bin/env python3\nTRIM_VERSION = "1.0.0"\n'
                                + "y = 2\n" * 1000)
        q = self._repo({"methodology_dashboard.py": wrong_marker_scanner, "README.md": "# a\n"})
        self.assertFalse(md.is_framework_installed(
            Path("methodology_dashboard.py"), q / "methodology_dashboard.py"),
            "and not the reverse either")

    def test_a_lookalike_trimmer_carrying_the_SCANNERS_signatures_is_not_excluded(self):
        """The trimmer's entry declares an EMPTY structural-signature tuple, meaning 'no fallback —
        TRIM_VERSION or nothing'. Without this test that field is unexercised: the harness proved
        that swapping `()` for the scanner's five signatures survives the whole suite, which would
        let a file named methodology_trim.py be exempted by carrying two scanner function names it
        has no business having. RED-first against that mutant."""
        impostor = ("# our own trimmer\n"
                    "def collect_all(items):\n    return list(items)\n"
                    "def score_health(m):\n    return 0\n" + "y = 2\n" * 1000)
        p = self._repo({"methodology_trim.py": impostor, "README.md": "# adopter\n"})
        self.assertFalse(md.is_framework_installed(
            Path("methodology_trim.py"), p / "methodology_trim.py"),
            "the trimmer declares no structural fallback — only TRIM_VERSION may exempt it")
        self.assertGreater(md.collect_all(p)["tests"]["source_loc"], 200)

    # --- what the shipped tool WRITES, which the exclusion above says nothing about --------------

    def _real_trim_output(self, tmp):
        """Run the REAL trimmer's --write on a real fixture ledger and return the repo path.

        Deliberately not a stand-in: the whole defect is that the generated artifact's size and
        shape come from the tool, so a hand-written fixture would be asserting my guess about its
        output rather than its output."""
        subprocess.run(["git", "init", "-q", str(tmp)], check=True)
        hdr = "# Changelog — Authoritative Action Ledger\n\nIntro prose.\n\n---\n\n## 2026-01\n\n"
        recs = "".join(f"### 2026-01-{i:02d} · [ad hoc] Entry {i}\n\nBody line {i}.\n\n"
                       for i in range(28, 0, -1))
        (tmp / "CHANGELOG.md").write_text(hdr + recs, encoding="utf-8")
        (tmp / "README.md").write_text("# adopter\n" * 5, encoding="utf-8")
        subprocess.run(["git", "-C", str(tmp), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(tmp), "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-q", "-m", "init"], check=True)
        trimmer = os.path.join(os.path.dirname(HERE), "starter-kit", "methodology_trim.py")
        r = subprocess.run([sys.executable, trimmer, "--file", str(tmp / "CHANGELOG.md"),
                            "--write", "--cut", "10"], capture_output=True, text=True)
        proofs = list((tmp / "docs" / "archive").glob("*.verify.sh"))
        self.assertEqual(len(proofs), 1,
                         f"fixture control: --write must emit exactly one proof script; "
                         f"stdout={r.stdout[-400:]} stderr={r.stderr[-400:]}")
        return proofs[0]

    def test_the_generated_proof_script_is_not_counted_as_adopter_source(self):
        """RED: `source_loc` was 220 against a 200 cap, `doc_only` False — a doc-only adopter who
        USES the tool this session ships re-earned the exact v3.2 regression the shipping work
        exists to prevent, by a different route."""
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        p = Path(td.name)
        proof = self._real_trim_output(p)
        # Fixture control: the artifact must actually be big enough to trip the cap, or this test
        # would pass for the wrong reason on a future, shorter template.
        self.assertGreater(md.count_lines(proof), md.DOC_ONLY_SOURCE_LOC_MAX,
                           "fixture control: the generated proof must exceed the source cap, "
                           "otherwise this test cannot observe the defect it is written for")
        m = md.collect_all(p)
        self.assertEqual(m["tests"]["source_loc"], 0,
                         "the tool's own generated proof is not the adopter's source")
        self.assertGreater(m["files"]["by_category"]["vendor"]["loc"], 0,
                           "and it must stay visible in the inventory, not vanish")

    def test_the_proof_exclusion_is_anchored_on_all_three_conditions(self):
        """Guard-the-guard, and each condition is broken separately — a predicate proven only by
        its happy path is a predicate whose ANDs are untested."""
        banner = "#!/usr/bin/env bash\n# generated by methodology_trim.py v1.0.0\n" + "x=1\n" * 300
        cases = {
            "docs/archive/s.verify.sh": True,                       # all three hold
            "s.verify.sh": False,                                   # wrong directory
            "docs/archive/s.sh": False,                             # wrong suffix
        }
        for rel, expected in cases.items():
            p = self._repo({rel: banner, "README.md": "# a\n"})
            self.assertEqual(md.is_generated_proof(Path(rel), p / rel), expected,
                             f"{rel}: expected is_generated_proof == {expected}")
        # ...and the content condition, at the one path where the other two DO hold.
        rel = "docs/archive/s.verify.sh"
        p = self._repo({rel: "#!/usr/bin/env bash\n" + "x=1\n" * 300, "README.md": "# a\n"})
        self.assertFalse(md.is_generated_proof(Path(rel), p / rel),
                         "a script at the right path and suffix but without the generator banner "
                         "is the adopter's own — the content check is what stops that")

    def test_every_excluded_source_name_declares_a_content_check(self):
        """THE STRUCTURAL GUARD, and the reason this session exists rather than appending a name.

        The failure this closes: `test_exclusion_list_matches_the_manifest` goes red when the
        manifest grows a non-markdown dest, and the cheapest way to make it green is to append the
        name to FRAMEWORK_INSTALLED_SOURCE — which passes that test while `is_framework_installed`
        still has no rule for the file. Deriving the tuple FROM the content table makes that edit
        impossible to write. Asserted as an ordered tuple because the manifest test compares
        ordered tuples."""
        self.assertEqual(md.FRAMEWORK_INSTALLED_SOURCE,
                         tuple(md._FRAMEWORK_INSTALLED_CONTENT),
                         "the exclusion tuple must BE the content table's keys, in order — a name "
                         "with no declared content check must not be expressible")
        for name, (version_re, signatures) in md._FRAMEWORK_INSTALLED_CONTENT.items():
            # None is legal (see is_framework_installed's own guard) for a file with no version
            # constant of its own — signatures are then the only way in, and an empty signature
            # tuple alongside a None version_re would be a genuine, silent no-op entry, so a
            # compiled pattern OR a non-empty signature tuple is required, never neither.
            self.assertTrue(version_re is None or hasattr(version_re, "search"),
                            f"{name} declares a version_re that is neither None nor compiled")
            self.assertIsInstance(signatures, tuple,
                                  f"{name}'s structural fallback must be a tuple (possibly empty)")
            if version_re is None:
                self.assertTrue(signatures,
                                f"{name} has no version_re AND no signatures — unreachable, inert entry")

    def _manifest(self):
        manifest_path = os.path.join(os.path.dirname(HERE), "bin", "_manifest.py")
        spec = importlib.util.spec_from_file_location("manifest_for_exclusion", manifest_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def installed_markdown(self):
        """The markdown `bin/sync` installs, read from the MANIFEST — the independent source of
        truth. Fixtures are built from this, never from the scanner constant they exercise."""
        mod = self._manifest()
        return [dest for _s, dest, _disp in mod.DISTRIBUTION if dest.endswith(".md")]

    def test_exclusion_list_matches_the_manifest(self):
        """Machine-checkable cross-reference (plan §8 learning 1). The scanner cannot import
        bin/_manifest.py — adopters have no bin/ — so the names are duplicated by necessity; this
        asserts the duplicates can never drift from their source of truth."""
        mod = self._manifest()
        non_markdown = tuple(dest for _s, dest, _d in mod.DISTRIBUTION
                             if not dest.endswith(".md"))
        self.assertEqual(non_markdown, md.FRAMEWORK_INSTALLED_SOURCE,
                         "bin/sync installs a non-markdown file the exclusion does not know about "
                         "(or vice versa) — update FRAMEWORK_INSTALLED_SOURCE")
        tracked_md = tuple(dest for _s, dest, disp in mod.DISTRIBUTION
                           if dest.endswith(".md") and disp == mod.TRACKED)
        seed_md = tuple(dest for _s, dest, disp in mod.DISTRIBUTION
                        if dest.endswith(".md") and disp == mod.SEED)
        self.assertEqual(set(tracked_md), set(md.FRAMEWORK_INSTALLED_DOCS),
                         "the doc discount must cover exactly the TRACKED markdown dests — "
                         "compared as a set because Layer 8 groups them by evidence tier, not by "
                         "manifest order")
        self.assertEqual(seed_md, md.FRAMEWORK_SEED_DOCS,
                         "the evidence-gated discount must be exactly the SEED markdown dests")
        self.assertEqual(set(tracked_md) & set(seed_md), set(),
                         "a dest discounted both ways would be counted out twice")

        # Layer 8: the two tiers must PARTITION the union — every TRACKED dest is either
        # self-evidencing or evidence-gated, never both and never neither. A name that fell out of
        # both tiers would stop being discounted on a real install with no test noticing.
        self.assertEqual(set(md.FRAMEWORK_DISTINCTIVE_DOCS) & set(md.FRAMEWORK_AMBIGUOUS_DOCS),
                         set(), "a dest in both tiers would be double-counted as evidence")
        self.assertEqual(set(md.FRAMEWORK_DISTINCTIVE_DOCS) | set(md.FRAMEWORK_AMBIGUOUS_DOCS),
                         set(tracked_md), "the two tiers must partition the TRACKED markdown dests")
        # Only a docs/methodology/ path may be self-evidencing. A bare root name is exactly what
        # Layer 8 demoted, so letting one back in unconditionally would re-open the regression.
        for dest in md.FRAMEWORK_DISTINCTIVE_DOCS:
            self.assertTrue(dest.startswith("docs/methodology/"),
                            f"{dest} is a root-level name and cannot be self-evidencing — a "
                            f"non-adopter can own that filename by coincidence")
        # bin/sync installs all seven ambiguous names, so a genuine install always clears the
        # threshold. If this ever inverts, real installs silently stop being discounted.
        self.assertGreaterEqual(len(md.FRAMEWORK_AMBIGUOUS_DOCS),
                                md.FRAMEWORK_AMBIGUOUS_EVIDENCE_MIN,
                                "a real bin/sync install must be able to satisfy the ambiguous "
                                "evidence threshold on its own")

    # --- per-file signatures: the BL-31 follow-up gap (a listed name proves nothing about a
    # DIFFERENT file's content) --------------------------------------------------------------
    #
    # test_every_framework_installed_source_name_has_a_signature (upstream's own name for this
    # same completeness gate) is deliberately not carried over: this fork's design derives
    # FRAMEWORK_INSTALLED_SOURCE FROM _FRAMEWORK_INSTALLED_CONTENT's own keys (see the constant's
    # definition), so the two can never disagree by construction, and
    # test_every_excluded_source_name_declares_a_content_check above already asserts the
    # stronger, ordered-tuple form of the same invariant.

    def test_the_real_context_budget_artifact_is_recognized(self):
        """Guard-the-guard, mirrors test_the_real_shipped_artifact_is_recognized: uses the REAL
        starter-kit/context_budget.py content, not a synthetic stand-in, so a future edit to
        that file that drifts from its own declared signatures is caught here, not only in a
        fixture that could drift right alongside it."""
        real = Path(STARTER_CONTEXT_BUDGET).read_text(encoding="utf-8")
        self.assertTrue(md.is_framework_installed(
            Path("context_budget.py"), Path(STARTER_CONTEXT_BUDGET)))
        p = self._repo({"context_budget.py": real, "README.md": "# adopter\n"})
        m = md.collect_all(p)
        self.assertEqual(m["files"]["by_category"]["vendor"]["count"], 1)
        self.assertEqual(m["tests"]["source_loc"], 0)

    def test_a_synced_repo_with_each_installed_source_file_is_still_doc_only(self):
        """THE regression test for the exclusion, over every non-markdown file `bin/sync`
        installs. Each is written from its REAL starter-kit/ source into a genuine doc-only repo,
        alone and then all together as a real install writes them, and none may count as the
        adopter's source, flip doc_only True -> False, or raise the false HIGH "No test
        infrastructure" — v3.2's exact false penalty.

        It began as context_budget.py's test, reproducing the maintainer's PR #71 finding: the
        NAME was listed, but its content was checked against methodology_dashboard.py's
        signatures, so it was never excluded (RED against that version). The PR #80 review, F2,
        found the same gap one name over: with methodology_trim.py's version_re and signatures
        neutralized in both twins, the suite stayed green while a synced fixture read `code`. RED
        against that mutant, and against the same neutralization of context_budget.py and of
        `.context-budget.json`. NOT of methodology_dashboard.py: the neutralized strings sit in
        the scanner's own signature table, so the real file still matches itself — this class's
        stand-in fixtures (installed_scanner()) are what catch that one.

        The names come from bin/_manifest.py, never from the constant under test, so a file the
        manifest installs and the scanner does not know about fails here by name.
        `.context-budget.json` is bucketed `config` before the predicate is consulted (see its
        _FRAMEWORK_INSTALLED_CONTENT entry), so its end-to-end half cannot fail on its signatures:
        the direct predicate call holds those, and its category is asserted so that reason stays
        checked."""
        mod = self._manifest()
        installed = [(src, dest) for src, dest, _disp in mod.DISTRIBUTION
                     if not dest.endswith(".md")]
        real = {dest: (CANONICAL_ROOT / src).read_text(encoding="utf-8")
                for src, dest in installed}

        def category(dest):
            return md.categorize_file(Path(dest), Path(dest).suffix.lower(), dest)

        def assert_still_doc_only(installed_files):
            m = md.collect_all(self._repo({**self.QUARTO, **installed_files}))
            self.assertEqual(m["tests"]["source_loc"], 0,
                             "a framework-installed file must not count as the adopter's source")
            self.assertTrue(m["doc_only"]["is_doc_only"],
                            "installing the methodology must not flip a doc-only repo to code")
            self.assertNotIn("No test infrastructure",
                             [r["description"] for r in m["scores"]["risks"]],
                             "the false HIGH risk this whole exclusion exists to prevent")
            vendor = m["files"]["by_category"]["vendor"]
            self.assertEqual(vendor["count"],
                             sum(1 for dest in installed_files if category(dest) == "source"),
                             "each installed file that would read as source must read as vendor")
            return vendor

        for src, dest in installed:
            with self.subTest(installed=dest):
                vendor = assert_still_doc_only({dest: real[dest]})
                if category(dest) == "source":
                    self.assertGreater(vendor["loc"], 0,
                                       "the excluded LOC must stay visible, not vanish")
                else:
                    self.assertEqual(category(dest), "config",
                                     f"{dest} passes end to end only because it is config — if "
                                     "that changes, its signature entry decides this test")
                self.assertTrue(md.is_framework_installed(Path(dest), CANONICAL_ROOT / src),
                                f"the real {src} must match its own _FRAMEWORK_INSTALLED_CONTENT "
                                "entry")
        with self.subTest(installed="all, as bin/sync writes them"):
            assert_still_doc_only(real)
        # Checked last, so a name the scanner lacks still reports its own failure above first.
        self.assertEqual({dest for _src, dest in installed}, set(md.FRAMEWORK_INSTALLED_SOURCE),
                         "this test must cover exactly the scanner's own list")

    def test_seed_docs_need_evidence_the_framework_was_installed(self):
        """The delta boundary review's confirmed regression, and the plan's RED-first clause (c)
        — "an UNSYNCED doc repo is unchanged" — instantiated where it can actually fail.

        The shipped clause-(c) test uses the Quarto fixture, whose `_quarto.yml` satisfies the
        render-toolchain arm of the corpus disjunction; that arm short-circuits the doc counts, so
        that fixture is STRUCTURALLY INCAPABLE of detecting a doc-corpus discount. This one is
        plain markdown with no toolchain, so the discount is the only thing that can move it.

        Measured regression it pins: a spec repo that never ran `bin/sync`, whose corpus is its own
        900-line CHANGELOG.md, was flipped `doc-only -> code` and handed a false HIGH "No test
        infrastructure" — the v3.2 false penalty, re-created by the fix for its mirror.
        """
        spec = self._repo({
            "README.md": "# Spec\n\nA specification repository.\n",
            "docs/spec.md": "# Spec\n" + "clause\n" * 190,
            "CHANGELOG.md": "# Changelog\n" + "- a change\n" * 900,   # the adopter's OWN
        })
        m = md.collect_all(spec)
        self.assertFalse(m["render"]["toolchain_present"],
                         "guard-the-guard: no toolchain, so only the doc counts can decide this")
        self.assertEqual(m["files"]["framework_docs"], {"count": 0, "loc": 0},
                         "nothing here is ours — the framework was never installed")
        self.assertTrue(m["doc_only"]["is_doc_only"])
        self.assertNotIn("No test infrastructure",
                         [r["description"] for r in m["scores"]["risks"]])

    def test_seed_docs_are_discounted_once_the_framework_is_present(self):
        """The other side of the gate: with a distinctive dest present the seeds ARE ours, so a
        synced repo cannot use them to look like a document corpus."""
        tree = {"README.md": "# app\n",
                "tool.py": "def s(x):\n    return x\n" * 74,          # 148 own LOC
                "CHANGELOG.md": "# Changelog\n" + "- a change\n" * 900}
        for dest in self.installed_markdown():
            tree[dest] = "# framework doc\n" + "prose\n" * 60
        m = md.collect_all(self._repo(tree))
        # Derived from the manifest, never a literal: a hardcoded floor silently stops asserting
        # the whole set the moment DISTRIBUTION grows (it read 21 while the set was already 22).
        self.assertGreaterEqual(m["files"]["framework_docs"]["count"],
                                len(self.installed_markdown()))
        self.assertFalse(m["doc_only"]["is_doc_only"])
        self.assertIn("No test infrastructure",
                      [r["description"] for r in m["scores"]["risks"]])

    # === Layer 8 — an ambiguous ROOT name is not evidence for itself ===================
    #
    # RED against the pre-Layer-8 scanner: it listed all 17 TRACKED markdown dests as
    # "distinctive" and discounted them unconditionally, so a non-adopter's own root file was
    # subtracted from its own doc corpus. Found by the pre-PR review, reproduced under both the
    # branch scanner and the PR base before being fixed.

    def test_an_ambiguous_root_name_alone_is_not_evidence(self):
        """The confirmed regression: a documentation project that never heard of this framework,
        whose corpus is its own root BOOTSTRAP.md, was flipped `doc-only -> code` and handed a
        false HIGH "No test infrastructure" — v3.2's exact false penalty, re-created a second time.

        Measured before the fix: doc_only True -> False, framework_docs {'count': 1, 'loc': 302}.
        BOOTSTRAP.md and SAFEGUARDS.md are ordinary names for any onboarding or policy repo.
        """
        for own in ("BOOTSTRAP.md", "SAFEGUARDS.md", "RECOMMENDED_SKILLS.md"):
            with self.subTest(own_file=own):
                repo = self._repo({
                    "README.md": "# Field Guide\n\nA documentation project.\n",
                    own: "# Ours\n" + "our own prose, nothing to do with any framework\n" * 300,
                })
                m = md.collect_all(repo)
                self.assertEqual(m["files"]["framework_docs"], {"count": 0, "loc": 0},
                                 f"{own} is the repo's OWN file — nothing here was installed")
                self.assertTrue(m["doc_only"]["is_doc_only"],
                                f"a doc repo owning {own} must still read doc-only")
                self.assertNotIn("No test infrastructure",
                                 [r["description"] for r in m["scores"]["risks"]])

    def test_one_ambiguous_name_does_not_unlock_the_seed_fold_in(self):
        """The sharper half: before the fix, ONE coincidental root name set the evidence flag and
        unlocked the seed fold-in, so the same repo's own CHANGELOG.md and ROADMAP.md were
        discounted too — one accident defeating the gate Layer 7 built to protect those four.

        Measured before the fix: framework_docs {'count': 3, 'loc': 546}.
        """
        repo = self._repo({
            "README.md": "# Field Guide\n\nA documentation project.\n",
            "BOOTSTRAP.md": "# Onboarding\n" + "our own onboarding prose\n" * 300,
            "CHANGELOG.md": "# Changelog\n" + "our own release history\n" * 120,
            "ROADMAP.md": "# Roadmap\n" + "our own plans\n" * 120,
        })
        m = md.collect_all(repo)
        self.assertEqual(m["files"]["framework_docs"], {"count": 0, "loc": 0},
                         "one ambiguous root name must not make the seeds ours")
        self.assertTrue(m["doc_only"]["is_doc_only"])

    def test_ambiguous_names_are_discounted_once_enough_co_occur(self):
        """The other side of the gate, so the fix cannot silently stop discounting real installs.
        Seven ambiguous root names as of S34 (FRAMEWORK_LEARNINGS.md joined the set).
        README.md's manual Option B copies the root files as a SET, and `bin/sync` writes all six,
        so a genuine install clears FRAMEWORK_AMBIGUOUS_EVIDENCE_MIN without any
        docs/methodology/ path present. Built from the manifest, not from the scanner constant.
        """
        mod = self._manifest()
        root_md = [d for _s, d, disp in mod.DISTRIBUTION
                   if d.endswith(".md") and disp == mod.TRACKED and "/" not in d]
        self.assertGreaterEqual(len(root_md), md.FRAMEWORK_AMBIGUOUS_EVIDENCE_MIN)
        tree = {"README.md": "# app\n",
                "tool.py": "def s(x):\n    return x\n" * 74,        # 148 own LOC, under the cap
                "CHANGELOG.md": "# Changelog\n" + "- a change\n" * 900}
        for dest in root_md:
            tree[dest] = "# framework doc\n" + "prose\n" * 60
        m = md.collect_all(self._repo(tree))
        self.assertGreaterEqual(m["files"]["framework_docs"]["count"], len(root_md) + 1,
                                "the root framework docs AND the seed must both be discounted")
        self.assertFalse(m["doc_only"]["is_doc_only"],
                         "a code repo must not be flipped doc-only by the docs we installed")

    def test_a_docs_methodology_path_is_evidence_on_its_own(self):
        """A path under docs/methodology/ is this framework's own install location, so one is
        proof. This is the tier that stays unconditional."""
        tree = {"README.md": "# app\n",
                "tool.py": "def s(x):\n    return x\n" * 74,
                "docs/methodology/ITERATIVE_METHODOLOGY.md": "# theory\n" + "prose\n" * 200,
                "CHANGELOG.md": "# Changelog\n" + "- a change\n" * 900}
        m = md.collect_all(self._repo(tree))
        self.assertGreaterEqual(m["files"]["framework_docs"]["count"], 2,
                                "one docs/methodology/ path must also unlock the seed fold-in")

    # === Layer 8 — a repo that HAS tests is never a document project =====================

    def test_a_repo_with_tests_is_never_doc_only(self):
        """The tutorials' own sample project: a Python CLI with a green pytest suite classified
        doc-only once `bin/sync` discounted the framework markdown around it, and then drew a
        "no tests" advisory ON A PASSING SUITE — a signal contradicted by the same metrics dict
        that emits it. It also made T7's Track B worked example unproducible, since the tutorial
        tells the learner to read a Testing dimension off a card that no longer renders one.
        """
        tree = {"README.md": "# todo\n", "GUIDE.md": "# guide\n", "NOTES.md": "# notes\n",
                "todo.py": "def add(x):\n    return x\n" * 40,       # 80 LOC, under the cap
                "tests/test_todo.py": "def test_add():\n    assert True\n" * 20}
        m = md.collect_all(self._repo(tree))
        self.assertGreater(m["files"]["by_category"]["test"]["count"], 0,
                           "guard-the-guard: the fixture must actually carry a test file")
        self.assertFalse(m["doc_only"]["is_doc_only"],
                         "a repo with a real suite has already answered the question this "
                         "dimension exists to ask")
        self.assertNotIn("Doc-only repo contains",
                         " ".join(r["description"] for r in m["scores"]["risks"]),
                         "the doc-only advisory must not fire on a repo with tests")

    def test_the_marker_still_overrides_the_has_tests_gate(self):
        """Declaring is exact where detection is a guess, so the has-tests gate sits BELOW the
        marker: a repo that declares `doc-only` keeps it even with a test file present."""
        tree = {"README.md": "# r\n",
                ".methodology-profile": "doc-only\n",
                "tests/test_x.py": "def test_x():\n    assert True\n" * 20}
        m = md.collect_all(self._repo(tree))
        self.assertTrue(m["doc_only"]["is_doc_only"])
        self.assertEqual(m["doc_only"]["reason"], "marker")

    def test_installed_docs_do_not_make_a_code_repo_doc_only(self):
        """The MIRROR defect, unmasked by the source exclusion and closed by operator decision.

        RED against the source-exclusion-only tree: this repo read doc_only=True and LOST its
        "No test infrastructure" risk, because bin/sync's 21 installed markdown files clear
        DOC_ONLY_DOC_FILES_MIN (3) on their own. Installing the methodology must not answer the
        question "is this a document project?" in EITHER direction.
        """
        tree = {
            "tool.py": "def s(x):\n    return x\n" * 74,      # 148 own LOC — under the 200 cap
            "README.md": "# Tiny tool\n\nA small utility.\n",
            "methodology_dashboard.py": installed_scanner(),
        }
        # Built from the MANIFEST, never from md.FRAMEWORK_INSTALLED_DOCS: a fixture assembled by
        # iterating the constant under test cannot fail when that constant is wrong, and would
        # degrade this from a behavioural RED to an AttributeError (absence, not wrongness).
        for dest in self.installed_markdown():
            tree[dest] = "# framework doc\n" + "prose\n" * 60
        m = md.collect_all(self._repo(tree))
        self.assertFalse(m["doc_only"]["is_doc_only"],
                         "a 148-LOC code repo must not become doc-only by being synced")
        self.assertIn("No test infrastructure",
                      [r["description"] for r in m["scores"]["risks"]],
                      "and it must keep the risk that is TRUE of it")
        # The documentation dimension deliberately still counts them, so no adopter's score moves.
        self.assertGreater(m["files"]["framework_docs"]["count"], 3)
        self.assertEqual(m["files"]["by_category"]["docs"]["count"],
                         m["files"]["framework_docs"]["count"] + 1)   # + the adopter's README

    def test_an_adopters_own_doc_corpus_still_counts(self):
        """Guard-the-guard on the above: the discount must not swallow real documentation."""
        tree = {"ch1.md": "# a\n" + "prose\n" * 100,
                "ch2.md": "# b\n" + "prose\n" * 100,
                "ch3.md": "# c\n" + "prose\n" * 100}
        for dest in self.installed_markdown():
            tree[dest] = "# framework doc\n" + "prose\n" * 60
        m = md.collect_all(self._repo(tree))
        self.assertTrue(m["doc_only"]["is_doc_only"])

    def test_large_file_risk_ignores_the_installed_scanner(self):
        """RED: fired as `Large files detected (methodology_dashboard.py: 2,475 lines)` — live on
        4 of 10 real repos. Same class as the source miscount, one signal over. (The quoted LOC is
        the value actually observed in the field, not this file's fixture default: adopters lag
        canonical, so the real strings were 2,055 and 2,475, never the stand-in's 3,073.)"""
        def large_risks(m):
            # `in r` would test dict KEYS and silently return [] always — a check that cannot
            # fail. It passed vacuously here once; the control case below is what exposed it.
            return [r["description"] for r in m["scores"]["risks"]
                    if "Large files" in r["description"]]

        synced = md.collect_all(self._repo({
            "app.py": "def f(x):\n    return x\n" * 50,
            "README.md": "# app\n",
            "methodology_dashboard.py": installed_scanner(),
        }))
        self.assertEqual(large_risks(synced), [])
        # Control: a genuinely large file the ADOPTER wrote must still be flagged, and a repo
        # that has both must be flagged for its own file rather than silently masked by ours.
        own = md.collect_all(self._repo({
            "huge.py": "def f(x):\n    return x\n" * 1200,   # 2,400 own LOC
            "README.md": "# app\n",
            "methodology_dashboard.py": installed_scanner(),
        }))
        flagged = large_risks(own)
        self.assertEqual(len(flagged), 1)
        self.assertIn("huge.py", flagged[0])
        self.assertNotIn("methodology_dashboard.py", flagged[0])

    def test_stale_installed_version_is_still_excluded(self):
        """Adopters lag canonical; the marker check must match any version, not the current one."""
        for version in ("2.8.0", "2.9.2", "2.10.1", "2.10.2"):
            with self.subTest(version=version):
                p = self._repo({**self.QUARTO,
                                "methodology_dashboard.py": installed_scanner(version=version)})
                self.assertTrue(md.collect_all(p)["doc_only"]["is_doc_only"])

    # --- disclosure: what was excluded stays visible -------------------------------------------

    def test_card_discloses_the_exclusion(self):
        p = self._repo({
            "app/core.py": "def f(x):\n    return x\n" * 500,
            "README.md": "# app\n",
            "methodology_dashboard.py": installed_scanner(),
        })
        card = md.render_project_card(md.collect_all(p))
        self.assertIn("Framework (installed)", card,
                      "the excluded file must still appear in the file-type table")
        self.assertIn("excludes", card,
                      "'Source LOC' must say what it excludes, or it reads as a scanner error")

    def test_card_omits_the_disclosure_when_nothing_was_excluded(self):
        """Guard-the-guard; passes both before and after, since asserting the ABSENCE of a string
        is trivially true before that string exists. Labeled per the module docstring's rule."""
        card = md.render_project_card(md.collect_all(self._repo({
            "app.py": "def f(x):\n    return x\n" * 200, "README.md": "# app\n"})))
        self.assertNotIn("Framework (installed)", card)

    def test_doc_only_footnote_is_true_after_the_exclusion(self):
        """The card justifies doc-only with `source_loc <= cap`. Excluding at the classification
        alone would have left that inequality printing '3070 <= 200' — a false statement, in a
        campaign about signals that do not mean what they appear to mean.

        NOTE, found while writing this test and deliberately NOT fixed here (pre-existing, cosmetic,
        outside Layer 7's ratified scope): the footnote is built with a literal `&le;` entity and
        then passed through `esc()`, so the card ships `&amp;le;` and the reader sees the entity
        text rather than "≤". Recorded for a later layer; asserting the true current output rather
        than the intended one keeps this test honest about what ships.
        """
        card = md.render_project_card(md.collect_all(
            self._repo({**self.QUARTO, "methodology_dashboard.py": installed_scanner()})))
        self.assertIn("source_loc 0 &amp;le; 200", card)
        self.assertNotIn("source_loc 3", card,
                         "the justification must not still quote the installed scanner's LOC")


class TestD4ReadCapTruncation(unittest.TestCase):
    """The agent-read-cap check: the one of three defects that is NOT a mechanical edit.

    The literal reading — put `.md` into `SOURCE_EXTS` so the existing "Large files detected" risk
    can see it — regresses the large-file check, whose ratified `test_large_file_ext_filter` (below, untouched)
    asserts a 2,500-line chapter must NOT trip it, and whose narrowing was earned by measurement.
    A SECOND risk is used instead, because the two share only the adjective:

      code-smell question   "is this MODULE unwieldy?"   — structure; false for a chapter
      read-cap question     "does a file a session must read IN FULL still fit in one read?"
                                                        — harness behaviour; true or false
                                                          whatever the file is for

    That separation is ADDED POLICY, labelled as such here and in the ledger entry. What the design
    requires is only that a 2,090-line `.md` be able to trip *a* large-file risk.

    RED-FIRST, and watched: every assertion below was run against the unpatched scanner and
    observed to fail (the metrics key is absent -> KeyError; the risk string appears nowhere).
    """

    def _repo(self, files_map, runner=True):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        p = Path(td.name)
        subprocess.run(["git", "init", "-q", str(p)], check=True)
        if runner:
            (p / "SESSION_RUNNER.md").write_text("# Session Runner\n" + "step\n" * 40)
        for name, content in files_map.items():
            fp = p / name
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(content)
        subprocess.run(["git", "-C", str(p), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(p), "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-q", "-m", "init"], check=True)
        return p

    @staticmethod
    def _lines(n):
        return "x\n" * n

    @staticmethod
    def _bytes(n):
        """EXACTLY n bytes, and still line-structured so `loc` stays meaningful. Phase B moved the
        verdict onto bytes, so a fixture built by LINE count no longer controls the variable under
        test: `_lines(2500)` is 5,000 B, an order of magnitude under the cap, and every assertion
        built on it would go quietly green for the wrong reason."""
        assert n >= 2, "a line-structured fixture needs at least one 'x\\n'"
        full, rest = divmod(n, 2)
        body = "x\n" * full
        if rest:                       # pad the last line by one byte, keeping the trailing \n
            body = "xx\n" + "x\n" * (full - 1)
        assert len(body.encode()) == n, (len(body.encode()), n)
        return body

    # --- the constant -------------------------------------------------------------------------

    def test_cap_agrees_with_the_trimmer(self):
        """The reporter and the remedy must not disagree about where the cliff is. Independent
        operands: one side is read out of THIS module, the other parsed out of the OTHER tool's
        source text.

        Phase B pins BOTH INPUTS, not the product. Pinning only the product would let the two
        tools agree on 56,750 B while disagreeing about what it means -- and the whole point of
        deriving it is that the inputs, not the boundary, are what a future session re-measures.
        Note what this still does NOT buy, unchanged from before and worth restating: it keeps the
        two copies CONSISTENT, and it kept them consistent throughout the period both were WRONG.
        Only Appendix A can say whether they are right."""
        trim_src = (Path(STARTER_PY).parent / "methodology_trim.py").read_text(encoding="utf-8")
        mt = re.search(r"^READ_CAP_TOKENS\s*=\s*([0-9_]+)", trim_src, re.MULTILINE)
        self.assertIsNotNone(mt, "methodology_trim.py must declare READ_CAP_TOKENS")
        self.assertEqual(md.READ_CAP_TOKENS, int(mt.group(1).replace("_", "")))
        mb = re.search(r"^MIN_BYTES_PER_TOKEN\s*=\s*([0-9.]+)", trim_src, re.MULTILINE)
        self.assertIsNotNone(mb, "methodology_trim.py must declare MIN_BYTES_PER_TOKEN")
        self.assertEqual(md.MIN_BYTES_PER_TOKEN, float(mb.group(1)))
        mr = re.search(r"^READ_REFUSE_BYTES\s*=\s*(\d+)\s*\*\s*(\d+)", trim_src, re.MULTILINE)
        self.assertIsNotNone(mr, "methodology_trim.py must declare READ_REFUSE_BYTES")
        self.assertEqual(md.READ_REFUSE_BYTES, int(mr.group(1)) * int(mr.group(2)))
        self.assertEqual(md.READ_CAP_BYTES,
                         int(md.READ_CAP_TOKENS * md.MIN_BYTES_PER_TOKEN),
                         "the cap must stay DERIVED; a hardcoded literal is the defect Phase B "
                         "removed, one level over")
        self.assertLess(md.READ_CAP_BYTES, md.READ_REFUSE_BYTES,
                        "the soft cap must sit below the hard refusal, or the refusal branch is "
                        "unreachable and its row is dead code")
        # The Class A pair is pinned the same way, by parsing the OTHER tool's source. Same
        # discipline, same limit: this keeps the two copies CONSISTENT and says nothing about
        # whether the pair is right, which only a fresh measurement can answer.
        mf = re.search(r"^CLASS_A_FIRE_BYTES\s*=\s*(\d+)\s*\*\s*(\d+)", trim_src, re.MULTILINE)
        self.assertIsNotNone(mf, "methodology_trim.py must declare CLASS_A_FIRE_BYTES")
        self.assertEqual(md.CLASS_A_FIRE_BYTES, int(mf.group(1)) * int(mf.group(2)))
        ms = re.search(r"^CLASS_A_STOP_BYTES\s*=\s*(\d+)\s*\*\s*(\d+)", trim_src, re.MULTILINE)
        self.assertIsNotNone(ms, "methodology_trim.py must declare CLASS_A_STOP_BYTES")
        self.assertEqual(md.CLASS_A_STOP_BYTES, int(ms.group(1)) * int(ms.group(2)))
        # AND THE BUDGET, which is the half the later change moved. It is written `192 * 1024`, so a
        # digits-only regex would miss it -- the same trap _parse_trim_budget exists for. Reusing
        # that parser here would make this an identity against the module under test, so the
        # arithmetic is redone independently.
        mdb = re.search(r"^DEFAULT_BUDGET_BYTES\s*=\s*(\d+)\s*\*\s*(\d+)", trim_src, re.MULTILINE)
        self.assertIsNotNone(mdb, "methodology_trim.py must declare DEFAULT_BUDGET_BYTES")
        self.assertEqual(int(mdb.group(1)) * int(mdb.group(2)), md.CLASS_A_FIRE_BYTES,
                         "option C1 raised the byte budget to MEET the Class A arm; if they have "
                         "drifted apart, one of the two arms is pre-empting the other again and "
                         "that is the inertness plan §5 warns about")
        self.assertLess(md.CLASS_A_STOP_BYTES, md.CLASS_A_FIRE_BYTES,
                        "hysteresis: the stop must be below the fire, or a trim re-fires on the "
                        "next record (ledger-trimmer-design.md §5.2)")

    def test_the_line_denominated_cap_is_gone_from_both_tools(self):
        """Phase B DELETED it rather than re-tuning it, and a deletion is only durable if
        something notices it coming back. A future session re-adding `READ_CAP_LINES` here would
        otherwise silently restore a second, contradictory axis beside the byte one."""
        trim_src = (Path(STARTER_PY).parent / "methodology_trim.py").read_text(encoding="utf-8")
        self.assertFalse(hasattr(md, "READ_CAP_LINES"))
        self.assertFalse(hasattr(md, "TRIM_LINE_FIRE_BELOW"))
        self.assertIsNone(re.search(r"^READ_CAP_LINES\s*=", trim_src, re.MULTILINE))
        self.assertIsNone(re.search(r"^LINE_FIRE_BELOW\s*=", trim_src, re.MULTILINE))
        self.assertIsNone(re.search(r"^LINE_STOP_ABOVE\s*=", trim_src, re.MULTILINE))
        self.assertIsNotNone(re.search(r"^SEED_PLAUSIBLE_MAX_LINES\s*=\s*2000", trim_src,
                                       re.MULTILINE),
                             "J3's line ceiling was RENAMED, not deleted -- it answers a "
                             "different question (is this plausibly a fresh seed?) and its value "
                             "is deliberately unchanged")

    def test_watched_set_never_names_a_tracked_dest(self):
        """THE LOAD-BEARING INVARIANT, and the reason the population is a literal rather than the
        methodology checklist. `SESSION_RUNNER.md` and `SAFEGUARDS.md` are TRACKED dests: we
        install them and keep them current. Flagging one would re-earn Layer 7's narrowing at
        fleet scale — a single canonical breach lighting up every adopter at once over a file they
        cannot edit. Asserted against `bin/_manifest.py` itself, so the two sides are genuinely
        independent rather than two spellings of one comprehension."""
        manifest_src = (Path(STARTER_PY).parent.parent / "bin" / "_manifest.py").read_text(
            encoding="utf-8")
        tracked = set(re.findall(r'\(\s*"[^"]+"\s*,\s*"([^"]+)"\s*,\s*TRACKED\s*\)', manifest_src))
        self.assertIn("SESSION_RUNNER.md", tracked, "fixture check: the manifest must still mark "
                                                    "SESSION_RUNNER.md TRACKED, or this test is "
                                                    "asserting nothing")
        self.assertEqual(md.READ_CAP_WATCHED & tracked, set())

    # --- the collector ------------------------------------------------------------------------

    def test_collector_reports_watched_file_lines(self):
        p = self._repo({"CHANGELOG.md": self._lines(2500)})
        m = md.collect_file_metrics(p)
        watch = {w["path"]: w["lines"] for w in m["read_cap_watch"]}
        self.assertEqual(watch.get("CHANGELOG.md"), 2500)

    def test_collector_ignores_unwatched_names(self):
        p = self._repo({"chapter07.md": self._lines(2500)})
        m = md.collect_file_metrics(p)
        self.assertEqual([w["path"] for w in m["read_cap_watch"]], [])

    def test_watch_list_is_not_capped_by_the_top_ten(self):
        """Keyed by NAME, never by size rank. `largest_files` is `all_files[:10]`, so a ledger
        pushed past rank 10 leaves the window and no threshold on that list could see it at ANY
        size — D4(b)'s own defect class, re-created by the fix for it. (An earlier draft of this
        docstring quoted how many source files it would take; a reviewer re-derived the number and
        it was wrong. The claim needs no distance, and a distance would rot.)"""
        big = {f"src{i}.py": self._lines(9000 + i) for i in range(12)}
        p = self._repo({**big, "HANDOFFS.md": self._lines(2400)})
        m = md.collect_file_metrics(p)
        self.assertNotIn("HANDOFFS.md", [f["path"] for f in m["largest_files"]],
                         "fixture check: HANDOFFS.md must be pushed OUT of the top ten, or this "
                         "test proves nothing")
        self.assertEqual({w["path"] for w in m["read_cap_watch"]}, {"HANDOFFS.md"})

    # --- the risk -----------------------------------------------------------------------------

    def test_risk_fires_past_the_cap(self):
        n = md.READ_CAP_BYTES + 2
        m = md.collect_all(self._repo({"CHANGELOG.md": self._bytes(n)}))
        descs = [r["description"] for r in m["scores"]["risks"]]
        self.assertTrue(any(f"CHANGELOG.md is {n:,} B" in d and "read cap" in d for d in descs),
                        f"expected a read-cap row, got {descs}")
        self.assertFalse(any("hard limit" in d for d in descs),
                         "between the two boundaries the row must describe TRUNCATION, not the "
                         "zero-content refusal -- they are different failures")

    def test_risk_silent_under_the_cap(self):
        """GUARD-THE-GUARD, labelled per this file's docstring rule: asserting the ABSENCE of a
        string is trivially true before that string exists, so this was one of the two tests in
        this class that were GREEN against the unpatched scanner. It is not RED-first coverage
        and must not be counted as such. It earns its place by mutation instead — see
        test_boundary_is_exactly_the_cap, which pins the comparison the mutant moves."""
        m = md.collect_all(self._repo({"CHANGELOG.md": self._bytes(md.READ_CAP_BYTES - 2)}))
        self.assertFalse(any("read cap" in r["description"] for r in m["scores"]["risks"]))

    def test_boundary_is_exactly_the_cap(self):
        """Pins the comparison itself, both sides. Without this the `>` -> `>=` producer mutant
        survived the entire suite: nothing exercised a file of exactly the cap, so the boundary
        was free to move by one in either direction undetected. The same lesson one level
        down — the predicate was covered, its EDGE was not.

        Phase B moved the axis, and BOTH boundaries now need this treatment: the soft cap and the
        256 KiB hard refusal are separate comparisons in separate branches, and an edge test on
        one says nothing about the other."""
        exact = md.collect_all(self._repo({"CHANGELOG.md": self._bytes(md.READ_CAP_BYTES)}))
        self.assertFalse(any("read cap" in r["description"] for r in exact["scores"]["risks"]),
                         "a file of exactly READ_CAP_BYTES still fits in one read")
        over = md.collect_all(self._repo({"CHANGELOG.md": self._bytes(md.READ_CAP_BYTES + 2)}))
        self.assertTrue(any("read cap" in r["description"] for r in over["scores"]["risks"]),
                        "past the cap must fire")

    def test_the_hard_refusal_boundary_is_its_own_edge_and_its_own_row(self):
        """The second comparison, pinned the same way. Exactly at READ_REFUSE_BYTES a default read
        still returns a truncated prefix, so the TRUNCATION row is correct; past it there is no
        prefix at all and the row must say so instead. Without both sides, `>` -> `>=` on the
        refusal branch is invisible, and so is a change that merges the two rows into one."""
        at = md.collect_all(self._repo({"CHANGELOG.md": self._bytes(md.READ_REFUSE_BYTES)}))
        at_d = [r["description"] for r in at["scores"]["risks"]]
        self.assertTrue(any("one-read budget" in d for d in at_d),
                        "exactly at the refusal it truncates")
        self.assertFalse(any("hard limit" in d for d in at_d),
                         "exactly at the refusal is not yet refused")
        past = md.collect_all(self._repo({"CHANGELOG.md": self._bytes(md.READ_REFUSE_BYTES + 2)}))
        past_d = [r["description"] for r in past["scores"]["risks"]]
        self.assertTrue(any("hard limit" in d and "NO CONTENT AT ALL" in d for d in past_d),
                        f"past the refusal must say nothing is delivered, got {past_d}")
        # NOT `"read cap" not in d`: the refusal row names the read cap too, in order to say it
        # is a DIFFERENT and harder boundary. The exclusive thing is the truncation VERDICT, so
        # the phrase that only the truncation branch emits is what this asserts on.
        self.assertFalse(any("one-read budget" in d for d in past_d),
                         "the two rows are exclusive: a refused file is not a truncated one, and "
                         "emitting both would give one file two contradictory remedies")
        self.assertTrue(all(r["severity"] == "high" for r in past["scores"]["risks"]
                            if "hard limit" in r["description"]))

    def test_empty_watched_file_still_reports_zero(self):
        """The collector deliberately appends OUTSIDE the `loc > 0` branch, so a watched file that
        is empty still appears with 0 rather than vanishing. Nothing tested that: the mutant
        `if loc > 0 and rel_posix in READ_CAP_WATCHED` survived the whole suite, which made the
        comment stating the intent unfalsifiable — a comment shaped like a design decision."""
        p = self._repo({"CHANGELOG.md": "", "HANDOFFS.md": self._lines(3)})
        m = md.collect_file_metrics(p)
        watch = {w["path"]: w["lines"] for w in m["read_cap_watch"]}
        self.assertEqual(watch.get("CHANGELOG.md"), 0,
                         "an empty watched file must be reported as 0, not omitted")

    def test_risk_is_gated_on_owing_a_ledger(self):
        """GUARD-THE-GUARD by construction (see test_risk_silent_under_the_cap): also green
        against the unpatched scanner, because pre-change no risk description contained the
        string at all. Its real proof is the producer mutant — replacing `if owes_ledger:` with
        `if True:` turns this red, which was run and observed.

        The claim it locks: a repo that never adopted the methodology is not told its CHANGELOG.md
        is too long. The scanner's own Layer 8 comment records a MEASURED regression from exactly
        that assumption."""
        m = md.collect_all(self._repo({"CHANGELOG.md": self._bytes(md.READ_CAP_BYTES + 2)},
                                      runner=False))
        self.assertFalse(any("read cap" in r["description"] for r in m["scores"]["risks"]))

    def test_one_row_per_breaching_file(self):
        """THE SEVERITY WAS SPLIT, NOT THE POPULATION. Still one row per file — that half is
        untouched and is what this test was written for. What changed is the blanket
        `all(... == "high")`, which stopped being true the moment the rows became per-class: a
        Class A ledger over the one-read cap is the adjudicated case and reports `low`.

        The per-file count is asserted first and separately, so a future change that collapsed the
        rows would still fail here even if every surviving row had the right severity."""
        m = md.collect_all(self._repo({"CHANGELOG.md": self._bytes(md.READ_CAP_BYTES + 2),
                                       "HANDOFFS.md": self._bytes(md.READ_CAP_BYTES + 4),
                                       "SESSION_NOTES.md": self._bytes(md.READ_CAP_BYTES + 6)}))
        rows = [r for r in m["scores"]["risks"] if "read cap" in r["description"]]
        self.assertEqual(len(rows), 3, "each file is separately actionable; an aggregate row "
                                       "naming only the worst hides the others")
        by_file = {n: r["severity"] for n in ("CHANGELOG.md", "HANDOFFS.md", "SESSION_NOTES.md")
                   for r in rows if r["description"].startswith(n)}
        self.assertEqual(by_file, {"CHANGELOG.md": "low", "HANDOFFS.md": "low",
                                   "SESSION_NOTES.md": "high"},
                         "Class A drops to low at this size, Class B stays high — same bytes, "
                         "different class, different severity")

    def test_backlog_is_watched_at_every_documented_location(self):
        n = md.READ_CAP_BYTES + 2
        for loc in md._BACKLOG_LOCATIONS:
            with self.subTest(loc=loc):
                m = md.collect_all(self._repo({loc: self._bytes(n)}))
                self.assertTrue(any(f"{loc} is {n:,} B" in r["description"]
                                    for r in m["scores"]["risks"]))

    def test_bl5_code_smell_row_is_untouched_and_independent(self):
        """Guard-the-guard, from the NEW signal's side. The two risks must coexist without either
        suppressing the other, and their strings must share no substring, so the diagnostic trail
        that produced the large-file check's narrowings survives in `dashboard_history.jsonl`."""
        m = md.collect_all(self._repo({"CHANGELOG.md": self._bytes(md.READ_CAP_BYTES + 2),
                                       "app.py": "x = 1\n" * 2500}))
        descs = [r["description"] for r in m["scores"]["risks"]]
        self.assertTrue(any("Large files detected" in d and "app.py" in d for d in descs))
        self.assertTrue(any("read cap" in d and "CHANGELOG.md" in d for d in descs))
        self.assertFalse(any("Large files detected" in d and "CHANGELOG.md" in d for d in descs),
                         "the code-smell risk must still never name a markdown file")

    def test_the_real_historical_blob_fires(self):
        """The strongest fixture available: not a synthetic file, but the actual artifact that
        actually breached the cap in this repository and was found by accident rather than by any
        check. Coverage does not depend on it — test_risk_fires_past_the_cap carries the same
        assertion synthetically — so a shallow clone skips rather than fails."""
        blob = subprocess.run(["git", "show", "3aee4e3^:CHANGELOG.md"],
                              capture_output=True, text=True,
                              cwd=str(Path(STARTER_PY).parent.parent))
        if blob.returncode != 0:
            self.skipTest("object 3aee4e3^ not present (shallow clone)")
        self.assertEqual(blob.stdout.count("\n"), 2090,
                         "fixture check: the historical blob must still be 2,090 lines")
        size = len(blob.stdout.encode("utf-8"))
        # WHICH BRANCH this artifact belongs in is a fact about it, not a choice, so it is
        # asserted rather than assumed. Re-measured at Phase B: 186,704 B -- about 2.97x the token
        # cap, and UNDER the 256 KiB refusal. So it TRUNCATED; it was not refused. A draft of this
        # test asserted the opposite and this control is what caught it.
        self.assertGreater(size, md.READ_CAP_BYTES,
                           "fixture check: the artifact must be past the one-read cap")
        self.assertLess(size, md.READ_REFUSE_BYTES,
                        "fixture check: and UNDER the hard refusal, or the assertion below is "
                        "testing the wrong branch")
        m = md.collect_all(self._repo({"CHANGELOG.md": blob.stdout}))
        self.assertTrue(any(f"CHANGELOG.md is {size:,} B" in r["description"]
                            and "one-read budget" in r["description"]
                            for r in m["scores"]["risks"]),
                        "the artifact that motivated this whole guard must trip the branch that "
                        "matches what actually happened to it")


class TestD4RootCommitDate(unittest.TestCase):
    """The root-commit-date fix.

    `git log --reverse --format=%ai -1` looks like "the oldest commit" and is not: git applies
    `-n1` while walking, BEFORE `--reverse` re-orders what survived, so it returns the NEWEST
    commit. `first_commit_date` therefore tracked HEAD, `project_age_days` sat near 0 for every
    repo ever scanned, and the `commits < 10 and age > 30` risk could never fire.

    RED-FIRST, and watched: run against the unpatched scanner these assertions FAIL with
    first_commit_date == the newest date (2026-08-01), not the root's 2020-01-02.
    """

    def _dated_repo(self, dates):
        """A repo with one commit per date, in the order given. Dates are pinned through the
        environment, so the fixture's own history is a REAL git history and the assertion reads
        it back through the scanner rather than being handed it."""
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        p = Path(td.name)
        subprocess.run(["git", "init", "-q", str(p)], check=True)
        for i, d in enumerate(dates):
            (p / f"f{i}.md").write_text(f"# commit {i}\n")
            stamp = f"{d}T12:00:00 +0000"
            env = {**os.environ, "GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp}
            subprocess.run(["git", "-C", str(p), "add", "-A"], check=True)
            subprocess.run(["git", "-C", str(p), "-c", "user.email=t@t", "-c", "user.name=t",
                            "commit", "-q", "-m", f"c{i}"], check=True, env=env)
        return p

    def test_first_commit_date_is_the_root_not_head(self):
        p = self._dated_repo(["2020-01-02", "2023-06-15", "2026-08-01"])
        g = md.collect_git_metrics(p)
        self.assertEqual(g["first_commit_date"], "2020-01-02")
        self.assertNotEqual(g["first_commit_date"], g["last_commit_date"],
                            "a 3-commit repo spanning 6 years must not report one date for both "
                            "ends of its history")

    def test_project_age_is_measured_from_the_root(self):
        p = self._dated_repo(["2020-01-02", "2026-08-01"])
        g = md.collect_git_metrics(p)
        # Whatever 'now' is, the age must be at least the span of the fixture's own history.
        span = (datetime(2026, 8, 1) - datetime(2020, 1, 2)).days
        self.assertGreaterEqual(g["project_age_days"], span)

    def test_low_velocity_risk_can_fire_at_all(self):
        """The consequence, asserted at the risk surface rather than at the metric: with age
        pinned to ~0 this risk was unreachable for every repo, at any commit count.

        THE FIXTURE HAS TO DISCRIMINATE, and the first version of it did not. Written with two
        commits in 2020 it passed against the UNPATCHED scanner — the buggy query returned the
        *newest* commit, which in that fixture was still six years old, so `age > 30` held for the
        wrong reason and the test was green against the bug it was written to catch. That is this
        file's own docstring rule ("a test that passes against the bug is not coverage"), and it
        took catching. The discriminating shape is an OLD root with a RECENT tip: the bug reads
        the tip and computes age ~0 (risk cannot fire); the fix reads the root (risk fires).
        """
        recent = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        p = self._dated_repo(["2020-01-02", recent])
        m = md.collect_all(p)
        self.assertTrue(any("Very low commit velocity" in r["description"]
                            for r in m["scores"]["risks"]),
                        "2 commits in a repo rooted in 2020 must trip the low-velocity risk, "
                        "however recently it was last touched")

    def test_single_commit_repo_still_reports_its_one_date(self):
        """Guard-the-guard: the fix must not regress the degenerate case, where the root IS head."""
        p = self._dated_repo(["2024-03-04"])
        g = md.collect_git_metrics(p)
        self.assertEqual(g["first_commit_date"], "2024-03-04")
        self.assertEqual(g["last_commit_date"], "2024-03-04")

    def test_root_date_survives_a_merge_of_two_unrelated_histories(self):
        """A repo can have MORE THAN ONE root. Whatever query replaces `--reverse -1` has to pick
        the OLDEST root, not just any root, or the fix trades one wrong answer for another."""
        p = self._dated_repo(["2021-05-06"])
        other = tempfile.TemporaryDirectory()
        self.addCleanup(other.cleanup)
        q = Path(other.name)
        subprocess.run(["git", "init", "-q", str(q)], check=True)
        (q / "z.md").write_text("# other\n")
        stamp = "2018-02-03T12:00:00 +0000"
        env = {**os.environ, "GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp}
        subprocess.run(["git", "-C", str(q), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(q), "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-q", "-m", "other-root"], check=True, env=env)
        subprocess.run(["git", "-C", str(p), "remote", "add", "other", str(q)], check=True)
        subprocess.run(["git", "-C", str(p), "fetch", "-q", "other"], check=True)
        # Resolve the fetched head by ASKING git, not by guessing between "master" and "main":
        # the first draft hard-coded those two and would error out under any other
        # `init.defaultBranch`, which is a machine-configuration dependency, not a property of
        # the code under test.
        other_head = subprocess.run(
            ["git", "-C", str(p), "rev-parse", "--verify", "-q", "refs/remotes/other/HEAD"],
            capture_output=True, text=True).stdout.strip()
        if not other_head:
            refs = subprocess.run(["git", "-C", str(p), "for-each-ref", "--format=%(refname)",
                                   "refs/remotes/other/"], capture_output=True, text=True)
            candidates = [r for r in refs.stdout.split() if not r.endswith("/HEAD")]
            self.assertTrue(candidates, "fixture check: fetch produced no remote-tracking ref")
            other_head = candidates[0]
        merge_stamp = "2021-05-07T12:00:00 +0000"
        menv = {**os.environ, "GIT_AUTHOR_DATE": merge_stamp, "GIT_COMMITTER_DATE": merge_stamp}
        subprocess.run(["git", "-C", str(p), "-c", "user.email=t@t", "-c", "user.name=t",
                        "merge", "-q", "--allow-unrelated-histories", "--no-edit", other_head],
                       check=True, env=menv)
        g = md.collect_git_metrics(p)
        self.assertEqual(g["first_commit_date"], "2018-02-03",
                         "with two roots the older one is the project's true start")



class TestD4SelfExclusion(unittest.TestCase):
    """`EXCLUDE_DIRS` contained the literal `"methodology"`, so in portfolio mode the
    instrument was structurally blind to its own home — the one repo whose methodology signals it
    is best placed to check, and the subject of upstream issue #59.

    RED-FIRST, and watched: against the unpatched scanner `discover_projects` returns [] for a
    portfolio root whose only project is named `methodology/`.
    """

    def _portfolio(self, names):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        for n in names:
            d = root / n
            d.mkdir(parents=True)
            (d / "README.md").write_text(f"# {n}\n")
            subprocess.run(["git", "init", "-q", str(d)], check=True)
            subprocess.run(["git", "-C", str(d), "add", "-A"], check=True)
            subprocess.run(["git", "-C", str(d), "-c", "user.email=t@t", "-c", "user.name=t",
                            "commit", "-q", "-m", "init"], check=True)
        return root

    def test_a_project_named_methodology_is_discovered(self):
        root = self._portfolio(["methodology"])
        found = [p.name for p in md.discover_projects(root)]
        self.assertEqual(found, ["methodology"])

    def test_methodology_is_not_in_the_exclusion_set(self):
        self.assertNotIn("methodology", md.EXCLUDE_DIRS)

    def test_the_real_exclusions_still_exclude(self):
        """Narrowed, not deleted (Learning #12's sibling): removing one member must not empty the
        set. A guard proven only by deletion is proven only to run."""
        root = self._portfolio(["realproject", "node_modules", "venv", "__pycache__"])
        found = sorted(p.name for p in md.discover_projects(root))
        self.assertEqual(found, ["realproject"])

    def test_sync_does_not_target_the_authoring_repo(self):
        """`discover_projects()` has TWO consumers, and D4(c) widened both. The scan wanted it;
        `sync_dashboards()` did not — with `methodology` discoverable, --sync gained a target at
        the canonical repo's OWN root, creating a third, unignored copy of the file beside the
        two that repo already authors. The `t == canonical` skip does not catch it (canonical is
        .../starter-kit/<name>; the new target is .../<name>).

        This was missed entirely by the author and found in adversarial review. It is asserted on
        the DRY-RUN output rather than by writing anything, and the fixture is a real directory
        layout, not a stubbed discover_projects."""
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        canon = root / "methodology" / "starter-kit"
        canon.mkdir(parents=True)
        (canon / "methodology_dashboard.py").write_text(
            Path(TOOLS_PY).read_text(encoding="utf-8"), encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(root / "methodology")], check=True)
        other = root / "adopter"
        other.mkdir()
        (other / "README.md").write_text("# adopter\n")
        subprocess.run(["git", "init", "-q", str(other)], check=True)

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            md.sync_dashboards(canon / "methodology_dashboard.py", dry_run=True)
        out = buf.getvalue()
        self.assertNotIn("methodology/methodology_dashboard.py", out.replace(str(root) + "/", ""),
                         "--sync must not target the repo that AUTHORS the dashboard")
        self.assertIn("adopter", out, "fixture check: a real adopter target must still be found, "
                                      "or this test would pass on an empty target list")


class TestBL29SelfScanRoot(unittest.TestCase):
    """The PORTFOLIO-mode self-scan was fixed (TestD4SelfExclusion above) but left a
    different self-scan gap open. `ROOT = Path(__file__).parent` is the script's own directory --
    correct for every adopter-installed copy and the portfolio-root copy, which all sit exactly
    where `bin/_manifest.py` / `sync_dashboards()` place them, at the root of what they scan. The
    methodology repo's own two checked-in copies are the one exception: `tools/` and
    `starter-kit/` both file this script one level BELOW the repo it belongs to, so
    `(ROOT / ".git").exists()` reads false there even though `main()`'s own `single_project`
    title-text branch already assumes that case can happen. RED-FIRST: `resolve_single_project_root`
    does not exist on unpatched code, so every test below fails with AttributeError.
    """

    def _framework_repo(self, in_repo_dir):
        """A tempdir shaped like the methodology repo itself: a git root carrying
        `bin/_manifest.py` (the structural marker `detect_repo_role()` already trusts), with this
        script filed `in_repo_dir` levels below that root -- e.g. "tools" or "starter-kit"."""
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        (root / "bin").mkdir()
        (root / "bin" / "_manifest.py").write_text("DISTRIBUTION = []\n")
        script_dir = root / in_repo_dir
        script_dir.mkdir(parents=True)
        return root, script_dir

    def test_bridges_the_canonical_tools_copy_to_its_repo_root(self):
        root, script_dir = self._framework_repo("tools")
        self.assertEqual(md.resolve_single_project_root(script_dir), root)

    def test_bridges_the_canonical_starter_kit_copy_to_its_repo_root(self):
        root, script_dir = self._framework_repo("starter-kit")
        self.assertEqual(md.resolve_single_project_root(script_dir), root)

    def test_a_normally_placed_copy_is_unchanged(self):
        """The documented, common case -- an adopter or portfolio-root copy sitting exactly where
        it is meant to scan -- must not be redirected anywhere."""
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        self.assertEqual(md.resolve_single_project_root(root), root)

    def test_a_tools_dir_with_no_manifest_marker_is_not_bridged(self):
        """An adopter repo that happens to have its own `tools/` directory, with no
        `bin/_manifest.py` at its root, must fall through to the pre-existing (portfolio-mode)
        behavior -- the bridge is scoped to the framework's own home, not any repo with a
        similarly-named subdirectory."""
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        script_dir = root / "tools"
        script_dir.mkdir()
        self.assertEqual(md.resolve_single_project_root(script_dir), script_dir,
                         "no bin/_manifest.py at the grandparent -- must not bridge")

    def test_a_differently_named_nested_dir_is_not_bridged(self):
        """Only the two directories this file is actually checked into (bin/_manifest.py) are
        bridged -- not a generic upward walk that would let ANY nested placement claim its
        ancestor as "the project"."""
        root, script_dir = self._framework_repo("scripts")
        self.assertEqual(md.resolve_single_project_root(script_dir), script_dir)

    def test_end_to_end_self_scan_no_longer_reports_no_projects_found(self):
        """Integration-level reproduction of the reported bug: `python3 tools/methodology_dashboard.py
        --no-open`, run from a fixture shaped like this repo, must scan the repo itself instead of
        printing "No projects found"."""
        root, script_dir = self._framework_repo("tools")
        # A minimal but real repo -- collect_all() needs at least a commit to read git metrics from.
        (root / "README.md").write_text("# framework\n")
        subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-q", "-m", "init"], check=True)
        script = script_dir / "methodology_dashboard.py"
        script.write_text(Path(TOOLS_PY).read_text(encoding="utf-8"), encoding="utf-8")
        result = subprocess.run(["python3", str(script), "--no-open"], cwd=str(script_dir),
                                capture_output=True, text=True, timeout=30)
        self.assertNotIn("No projects found", result.stdout)
        self.assertIn(root.name.upper(), result.stdout,
                      "single-project title must name the repo, proving it was actually scanned")


class TestIssue67ScopedSync(unittest.TestCase):
    """Upstream issue #67: `check_stale_version()`'s only remedy was a portfolio-wide `--sync` for a one-file
    problem, `sync_dashboards()` had no target scope and no confirm-before-overwrite gate, and a
    bare `--dry-run` silently fell through to a full scan-and-write. RED-FIRST throughout
    (Learning #12): every assertion below was run against the unpatched functions and watched to
    fail for the reason named in its own docstring, matching the design's own test table by row
    number. Fixture idiom matches the existing TestD4SelfExclusion precedent
    (test_sync_does_not_target_the_authoring_repo): a real temp directory tree + real `git init`,
    never a stubbed discover_projects."""

    def _canon_and_portfolio(self):
        """A canonical repo (methodology/starter-kit/methodology_dashboard.py) plus an empty
        portfolio root to hang targets off of. Mirrors the existing precedent fixture exactly."""
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        canon_dir = root / "methodology" / "starter-kit"
        canon_dir.mkdir(parents=True)
        canon = canon_dir / "methodology_dashboard.py"
        canon.write_text(Path(TOOLS_PY).read_text(encoding="utf-8"), encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(root / "methodology")], check=True)
        return root, canon

    def _git_init(self, path):
        path.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init", "-q", str(path)], check=True)
        return path

    def _git_commit_all(self, path):
        subprocess.run(["git", "-C", str(path), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(path), "-c", "user.email=t@t", "-c", "user.name=t",
                         "commit", "-q", "-m", "init"], check=True)

    def _run_sync(self, canon, **kwargs):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            written = md.sync_dashboards(canon, **kwargs)
        return written, out.getvalue(), err.getvalue()

    def _run_cli(self, script, args, cwd):
        return subprocess.run(["python3", str(script)] + list(args), cwd=str(cwd),
                               capture_output=True, text=True, timeout=30)

    # --- Row 1 -------------------------------------------------------------------------------

    def test_check_stale_version_recommends_scoped_target(self):
        """Row 1: today's message has exactly one remedy (portfolio --sync) for a one-file
        problem. RED against unpatched code because no scoped remedy string exists at all."""
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        canon_dir = root / "methodology" / "starter-kit"
        canon_dir.mkdir(parents=True)
        canon = canon_dir / "methodology_dashboard.py"
        real_src = Path(TOOLS_PY).read_text(encoding="utf-8")
        canon_src, n = re.subn(r'DASHBOARD_VERSION = "[^"]+"',
                                'DASHBOARD_VERSION = "9.9.9"', real_src)
        self.assertEqual(n, 1, "fixture check: the version-bump substitution must actually apply "
                               "exactly once")
        canon.write_text(canon_src, encoding="utf-8")

        adopter = root / "adopter"
        adopter.mkdir()
        adopter_copy = adopter / "methodology_dashboard.py"
        adopter_copy.write_text(Path(TOOLS_PY).read_text(encoding="utf-8"), encoding="utf-8")

        driver = ("import importlib.util, sys\n"
                   "spec = importlib.util.spec_from_file_location('m', sys.argv[1])\n"
                   "m = importlib.util.module_from_spec(spec)\n"
                   "spec.loader.exec_module(m)\n"
                   "m.check_stale_version()\n")
        result = subprocess.run(["python3", "-c", driver, str(adopter_copy)],
                                 capture_output=True, text=True, timeout=30)
        self.assertIn(str(adopter), result.stderr,
                      "the warning must name a remedy scoped to THIS copy's own directory")
        self.assertIn("--sync", result.stderr)

    # --- Row 2 -------------------------------------------------------------------------------

    def test_extract_sync_target_is_order_independent(self):
        """Row 2: `_extract_sync_target` doesn't exist yet -- RED with AttributeError."""
        self.assertEqual(md._extract_sync_target(["--sync", "/some/dir"]), "/some/dir")
        self.assertEqual(md._extract_sync_target(["--sync", "--force", "/some/dir"]), "/some/dir",
                         "a flag between --sync and the target must not shift the parse")
        self.assertEqual(md._extract_sync_target(["/some/dir", "--sync"]), "/some/dir",
                         "the target token may precede --sync on the command line")
        self.assertIsNone(md._extract_sync_target(["--sync", "--dry-run"]),
                          "no bare-word token present => whole-portfolio mode, not a crash")

    # --- Rows 3-6 ------------------------------------------------------------------------------

    def test_sync_accepts_a_single_target_directory(self):
        """Row 3: scoped mode must not fall through to full portfolio discovery -- a distractor
        project would only appear in the output if discover_projects() still ran. RED with
        TypeError against unpatched code (no `target` kwarg)."""
        root, canon = self._canon_and_portfolio()
        target = self._git_init(root / "solo")
        (target / ".gitignore").write_text("methodology_dashboard.py\n")
        self._git_init(root / "adopter")
        written, out, err = self._run_sync(canon, target=str(target))
        self.assertNotIn("adopter", out,
                         "a scoped sync must not even inspect other portfolio members")
        self.assertIn("1 target", out)
        self.assertEqual(written, 1)

    def test_sync_target_writes_only_that_target(self):
        """Row 4: filesystem-level scope check -- only the named target gets a new file. RED
        with TypeError against unpatched code."""
        root, canon = self._canon_and_portfolio()
        target = self._git_init(root / "solo")
        (target / ".gitignore").write_text("methodology_dashboard.py\n")
        other = self._git_init(root / "adopter")
        self._run_sync(canon, target=str(target))
        self.assertTrue((target / "methodology_dashboard.py").exists())
        self.assertFalse((other / "methodology_dashboard.py").exists())
        self.assertFalse((root / "methodology_dashboard.py").exists(),
                         "the portfolio-root copy must not be touched by a scoped sync either")

    def test_sync_target_nonexistent_directory_errors_without_writing(self):
        """Row 5: RED with TypeError against unpatched code; no such guard exists today."""
        root, canon = self._canon_and_portfolio()
        ghost = root / "does-not-exist"
        written, out, err = self._run_sync(canon, target=str(ghost))
        self.assertEqual(written, 0)
        self.assertFalse(ghost.exists())
        self.assertIn("does not exist", err)

    def test_sync_target_refuses_canonical_authoring_repo(self):
        """Row 6: scoped mode's own analogue of test_sync_does_not_target_the_authoring_repo.
        RED with TypeError against unpatched code; no such guard exists in scoped mode today."""
        root, canon = self._canon_and_portfolio()
        written, out, err = self._run_sync(canon, target=str(root / "methodology"))
        self.assertEqual(written, 0)
        self.assertIn("authoring repo", err)

    # --- Rows 7-11: the --force gate ------------------------------------------------------------

    def _tracked_target(self, root, canon):
        target = self._git_init(root / "tracked")
        (target / "methodology_dashboard.py").write_text("# stale content, not canonical\n")
        self._git_commit_all(target)
        return target

    def test_sync_skips_git_tracked_target_without_force(self):
        """Row 7: today's code writes a git-tracked target unconditionally -- RED because the
        file ends up equal to canonical text instead of staying stale."""
        root, canon = self._canon_and_portfolio()
        target = self._tracked_target(root, canon)
        written, out, err = self._run_sync(canon, target=str(target))
        self.assertEqual(written, 0)
        self.assertEqual((target / "methodology_dashboard.py").read_text(),
                         "# stale content, not canonical\n")
        self.assertIn("[SKIPPED — git-tracked; pass --force, then Phase 3 untrack]", out)

    def test_sync_writes_git_tracked_target_with_force(self):
        """Row 8: `force` kwarg doesn't exist yet -- RED with TypeError. Also asserts the
        written note is EXACTLY the tracked-and-written note, with no residual "needs --force"
        text once --force has already been satisfied (SS6 item 3)."""
        root, canon = self._canon_and_portfolio()
        target = self._tracked_target(root, canon)
        written, out, err = self._run_sync(canon, target=str(target), force=True)
        self.assertEqual(written, 1)
        self.assertEqual((target / "methodology_dashboard.py").read_text(),
                         canon.read_text(encoding="utf-8"))
        self.assertIn("[git-tracked — needs Phase 3 untrack]", out)
        self.assertNotIn("SKIPPED", out)
        self.assertNotIn("needs --force", out)

    def test_sync_skips_new_ungitignored_target_without_force(self):
        """Row 9: today's code creates a brand-new target unconditionally -- RED because the
        file would exist afterward."""
        root, canon = self._canon_and_portfolio()
        target = self._git_init(root / "brand-new")
        written, out, err = self._run_sync(canon, target=str(target))
        self.assertEqual(written, 0)
        self.assertFalse((target / "methodology_dashboard.py").exists())
        self.assertIn("[SKIPPED — new, ungitignored file; pass --force to create]", out)

    def test_sync_creates_new_gitignored_target_without_force(self):
        """Row 10, CONTROL: proves the gate does not over-fire on an already-.gitignore'd new
        file. Must use the new target=/force= kwargs to be genuinely RED (TypeError against the
        old two-positional-argument signature) -- calling with only a plain start/dry_run
        wouldn't touch the new code path at all and would pass vacuously today."""
        root, canon = self._canon_and_portfolio()
        target = self._git_init(root / "brand-new")
        (target / ".gitignore").write_text("methodology_dashboard.py\n")
        written, out, err = self._run_sync(canon, target=str(target), force=False)
        self.assertEqual(written, 1)
        self.assertEqual((target / "methodology_dashboard.py").read_text(),
                         canon.read_text(encoding="utf-8"))
        self.assertNotIn("SKIPPED", out)

    def test_sync_updates_existing_untracked_target_without_force(self):
        """Row 11, CONTROL: the tool's routine self-heal case -- an ordinary update of an
        already-existing, already-untracked target -- must keep working without --force. Same
        new-kwarg RED reasoning as row 10: guards against an over-broad gate regressing routine
        use."""
        root, canon = self._canon_and_portfolio()
        target = self._git_init(root / "existing")
        (target / "methodology_dashboard.py").write_text("# old, untracked copy\n")
        written, out, err = self._run_sync(canon, target=str(target), force=False)
        self.assertEqual(written, 1)
        self.assertEqual((target / "methodology_dashboard.py").read_text(),
                         canon.read_text(encoding="utf-8"))
        self.assertNotIn("SKIPPED", out)

    # --- Row 12: dry-run must preview the gate honestly --------------------------------------

    def test_sync_dry_run_previews_skips_accurately(self):
        """Row 12: the fix. Every design candidate's own dry-run computed the gate INSIDE the
        dry_run branch, so a preview never showed [SKIPPED] and a later real run without --force
        wrote less than the preview promised. RED with TypeError against unpatched code (no
        `target`/`force` kwargs to exercise the gate through in the first place)."""
        root, canon = self._canon_and_portfolio()
        target = self._tracked_target(root, canon)

        written, out, err = self._run_sync(canon, target=str(target), dry_run=True)
        self.assertEqual(written, 0)
        self.assertIn("[SKIPPED", out)
        self.assertIn("Would change 0 of 1", out)
        self.assertEqual((target / "methodology_dashboard.py").read_text(),
                         "# stale content, not canonical\n", "dry-run must never write")

        written, out, err = self._run_sync(canon, target=str(target), dry_run=True, force=True)
        self.assertEqual(written, 0, "D6: a dry run always returns 0, even with --force")
        self.assertNotIn("SKIPPED", out)
        self.assertIn("Would change 1 of 1", out)
        self.assertEqual((target / "methodology_dashboard.py").read_text(),
                         "# stale content, not canonical\n",
                         "--dry-run --force previews the real action; it still writes nothing")

    # --- Row 13 --------------------------------------------------------------------------------

    def test_bare_dry_run_without_sync_errors_and_writes_nothing(self):
        """Row 13: direct reproduction of issue #67 point 4. RED because today's bare --dry-run
        exits 0 and writes dashboard.html + appends history. Real subprocess against a
        temp-copied script -- ROOT is `Path(__file__).parent`, so the copy's own directory
        becomes the (single-project) scan root, exactly the self-referential case this fix
        exists to guard."""
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = self._git_init(Path(td.name))
        script = root / "methodology_dashboard.py"
        script.write_text(Path(TOOLS_PY).read_text(encoding="utf-8"), encoding="utf-8")

        result = self._run_cli(script, ["--dry-run"], cwd=root)
        self.assertEqual(result.returncode, 2)
        self.assertIn("only means something together with --sync", result.stderr)
        self.assertFalse((root / "dashboard.html").exists())
        self.assertFalse((root / "dashboard_history.jsonl").exists())

    # --- Row 14 ----------------------------------------------------------------------------------

    def test_sync_dry_run_with_target_still_works(self):
        """Row 14, CONTROL: a scoped dry-run's preview text must be scoped to exactly the given
        directory, excluding other portfolio members -- "unaffected by the guard" alone would
        pass vacuously today (RED FOR A DIFFERENT REASON: today's `main()` never even calls
        `_extract_sync_target`, so a directory token on argv is silently ignored and a scoped
        `--sync DIR --dry-run` previews the WHOLE portfolio; this test drives sync_dashboards()
        directly with the new target= kwarg, so it goes RED with TypeError, same as rows 3-6, but
        exists specifically to catch a future `main()` that extracts the target and forgets to
        pass it through)."""
        root, canon = self._canon_and_portfolio()
        target = self._git_init(root / "solo")
        self._git_init(root / "adopter")
        written, out, err = self._run_sync(canon, target=str(target), dry_run=True)
        self.assertIn(f"1 target ({target.resolve()})", out,
                     "resolved, since sync_dashboards() resolves the target directory itself")
        self.assertNotIn("adopter", out)

    # --- Row 15 --------------------------------------------------------------------------------

    def test_usage_documents_sync_target_and_force(self):
        """Row 15: neither string exists in print_usage() today -- RED by absence."""
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            md.print_usage()
        out = buf.getvalue()
        self.assertIn("--sync [DIR]", out)
        self.assertIn("--force", out)

    # --- Row 16 --------------------------------------------------------------------------------

    def test_sync_end_to_end_via_main_writes_only_the_target(self):
        """Row 16: genuine CLI-level integration test through the real main()/argv path, unlike
        rows 3-11 which call sync_dashboards() directly and so cannot catch main() extracting the
        target but forgetting to pass it through. RED because today's main() has no
        _extract_sync_target call at all and unconditionally full-portfolio-syncs on --sync."""
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        canon_dir = self._git_init(root / "methodology" / "starter-kit").parent
        script = canon_dir / "starter-kit" / "methodology_dashboard.py"
        script.write_text(Path(TOOLS_PY).read_text(encoding="utf-8"), encoding="utf-8")
        target = self._git_init(root / "solo")
        (target / ".gitignore").write_text("methodology_dashboard.py\n")
        self._git_init(root / "adopter")

        result = self._run_cli(script, ["--sync", str(target)], cwd=root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((target / "methodology_dashboard.py").exists())
        self.assertFalse((root / "adopter" / "methodology_dashboard.py").exists())
        self.assertFalse((root / "methodology_dashboard.py").exists())


TRIM_PY = os.path.join(os.path.dirname(HERE), "starter-kit", "methodology_trim.py")


def _load_trimmer():
    """The trimmer as a module, for use as an INDEPENDENT operand only.

    The dashboard never imports it -- that is the whole architecture (interrogate by
    regex, without importing). These tests do, precisely so that the value the dashboard parsed
    out of the tool's SOURCE TEXT can be compared against the value the tool itself defines.
    Two spellings of one comprehension would assert nothing."""
    spec = importlib.util.spec_from_file_location("methodology_trim_under_test", TRIM_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestS38TrimTriggerRow(unittest.TestCase):
    """The conditional trim-trigger row.

    RED-FIRST, and watched: every assertion below was run against the pre-change scanner
    (`git show HEAD:tools/methodology_dashboard.py`) and observed to fail -- the collector,
    the constants and the metrics key do not exist there, so each fails with AttributeError or
    KeyError rather than passing vacuously.

    The design says that the dashboard "reads the number rather than re-deriving it" and
    in the same paragraph owes an AGREEMENT TEST against `--check`. Those two
    cannot both be honoured: a number obtained BY parsing `--check` makes the agreement test an
    identity that cannot fail. The dashboard therefore computes independently, and
    test_headroom_agrees_with_a_real_check_run is a test that can actually go red.
    """

    REPO = Path(HERE).parent          # the canonical repo, used as a live fixture

    # --- fixtures -------------------------------------------------------------------------------

    def _repo(self, files_map, runner=True, archive=None, ledger="CHANGELOG.md"):
        """A repo whose archive shard, if any, is a REAL archive event.

        An earlier version of this helper wrote the shard in the same commit that created the
        ledger, and every fixture built on it was unrepresentative: the trimmer counts a shard as
        an archive event only when the LEDGER ACTUALLY SHRANK in that commit, so those repos had
        no baseline at all as far as `--check` was concerned. The tests passed anyway because the
        dashboard was, at that point, equally permissive -- two implementations agreeing on a
        state neither would ever meet in the wild. The shard is now committed the way a real trim
        commits one: an inflated ledger first, then the shrunk ledger and the shard together."""
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        p = Path(td.name)
        subprocess.run(["git", "init", "-q", str(p)], check=True)
        if runner:
            (p / "SESSION_RUNNER.md").write_text("# Session Runner\n" + "step\n" * 40)

        if archive is not None:
            # commit 1 -- the pre-archive ledger, deliberately larger than what follows.
            pre = p / ledger
            pre.parent.mkdir(parents=True, exist_ok=True)
            pre.write_text((files_map.get(ledger, "# ledger\n")) + ("padding\n" * 400))
            self._commit(p, "pre-archive ledger")
            ap = p / "docs" / "archive" / archive
            ap.parent.mkdir(parents=True, exist_ok=True)
            ap.write_text("# archived shard\n")

        for name, content in files_map.items():
            fp = p / name
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(content)
        self._commit(p, "archive event" if archive is not None else "init")

        if archive is not None:
            # Fixture control: the shard commit must really be an archive event, or every
            # headroom this repo produces is measured against a baseline the trimmer rejects.
            self.assertIsNotNone(
                md._newest_archive_sha(p, Path(ledger).name),
                "fixture is not a real archive event: the ledger did not shrink in the shard "
                "commit, so the trimmer would find no baseline here")
        return p

    @staticmethod
    def _commit(p, msg):
        subprocess.run(["git", "-C", str(p), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(p), "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-q", "-m", msg], check=True)

    @staticmethod
    def _entries(n, start=0, body=30):
        return "".join("### 2026-01-%02d %s [ad hoc] entry %d\n\n%s\n"
                       % (i % 28 + 1, md._MIDDLE_DOT, i, "x\n" * body)
                       for i in range(start, start + n))

    def _sized(self, name, n_bytes, **kw):
        """A repo whose `name` is EXACTLY n_bytes, still line-structured.

        Phase B moved this row's first half onto bytes, so a fixture sized by entry COUNT no
        longer controls the variable under test -- `_entries(6)` is a couple of hundred bytes
        against a 56,750 B cap, and every assertion built on it would go green for the wrong
        reason."""
        head = "# Changelog\n\n"
        pad = n_bytes - len(head.encode())
        assert pad >= 2, "fixture too small to be line-structured"
        full, rest = divmod(pad, 2)
        body = ("xx\n" + "x\n" * (full - 1)) if rest else ("x\n" * full)
        text = head + body
        assert len(text.encode()) == n_bytes, (len(text.encode()), n_bytes)
        return self._repo({name: text}, **kw)

    def _descs(self, path, expect_role=None):
        """Signals plus the collector's own dict.

        The `role` parameter this helper used to take was DEAD: collect_all detects the role
        itself, so passing role="framework" controlled nothing and two tests looked like they
        were exercising a branch they were not selecting. It is now an ASSERTION about the role
        collect_all actually detected, which is the thing those tests meant to establish."""
        m = md.collect_all(path)
        if expect_role is not None:
            self.assertEqual(m["methodology"].get("role"), expect_role,
                             "fixture: this test depends on the detected repo role")
        return [d for _s, d in m["trim"]["signals"]], m["trim"]

    # --- the constants, each pinned to an INDEPENDENT operand -----------------------------------

    def test_grammars_agree_with_the_trimmer_config_table(self):
        """THE POPULATION, and the defect it prevents. `READ_CAP_WATCHED` is deliberately wider
        than the set of ledgers the trimmer can act on -- it names SESSION_NOTES.md and three
        BACKLOG.md locations, and the trimmer answers NO_CONFIG on every one of them by design.
        A row naming the trimmer for one of those would point an adopter at a refusal. Asserted
        against the trimmer's own LEDGERS table, not against a restatement of it."""
        trim = _load_trimmer()
        self.assertEqual(sorted(md.TRIM_GRAMMARS), sorted(trim.LEDGERS))
        # ...and prove the wider set really is wider, or the assertion above is vacuous.
        self.assertTrue(set(md.READ_CAP_WATCHED) - set(md.TRIM_GRAMMARS),
                        "fixture check: READ_CAP_WATCHED must hold names the trimmer refuses, "
                        "or this test is guarding nothing")

    def test_no_rate_threshold_survives_in_either_tool(self):
        """WHAT THIS REPLACED, and why the replacement is an absence. This used to pin
        `md.TRIM_LINE_FIRE_BELOW` against the trimmer's `LINE_FIRE_BELOW` -- a SECOND distributed
        copy of the design's rate rule. The rule was deleted from both tools rather than
        re-tuning it, so the agreement to assert is that neither has re-grown one: a reporter
        advertising a threshold the remedy no longer has is exactly the drift the original pin
        existed to catch, one level up."""
        trim_src = Path(TRIM_PY).read_text(encoding="utf-8")
        self.assertFalse(hasattr(md, "TRIM_LINE_FIRE_BELOW"))
        for gone in ("LINE_FIRE_BELOW", "LINE_STOP_ABOVE"):
            self.assertIsNone(re.search(r"(?m)^%s\s*=" % gone, trim_src),
                              "%s came back; if the rate rule is being restored it needs a "
                              "feasibility argument, because a one-read HANDOFFS.md holds ~4 "
                              "records and the old rule demanded 30 of headroom" % gone)
        self.assertEqual(md.READ_CAP_BYTES, int(md.READ_CAP_TOKENS * md.MIN_BYTES_PER_TOKEN))

    def test_budget_is_parsed_from_the_product_form(self):
        """THE TRAP THIS TEST EXISTS FOR: the trimmer writes `DEFAULT_BUDGET_BYTES = 64 * 1024`,
        not a plain integer. A digits-only regex matches nothing, returns None, and the byte
        half of the trigger silently reports "unavailable" on a repo where the tool is sitting
        right there. Compared against the tool's own module constant, which is an operand this
        module never sees."""
        trim = _load_trimmer()
        parsed = md._parse_trim_budget(Path(TRIM_PY).read_text(encoding="utf-8"))
        self.assertEqual(parsed, trim.DEFAULT_BUDGET_BYTES)
        self.assertIsNotNone(parsed)
        # The form really is a product, or the test above proves nothing about the parser.
        self.assertRegex(Path(TRIM_PY).read_text(encoding="utf-8"),
                         r"(?m)^DEFAULT_BUDGET_BYTES\s*=\s*\d+\s*\*\s*\d+")

    def test_unparseable_budget_abstains_rather_than_guessing(self):
        self.assertIsNone(md._parse_trim_budget("DEFAULT_BUDGET_BYTES = compute_it()\n"))
        self.assertIsNone(md._parse_trim_budget("nothing here\n"))
        self.assertEqual(md._parse_trim_budget("DEFAULT_BUDGET_BYTES = 64 * 1024\n"), 65536)
        self.assertEqual(md._parse_trim_budget("DEFAULT_BUDGET_BYTES = 65_536\n"), 65536)

    # --- A4, branch 1: the present branch names a command the trimmer really accepts ------------

    def test_named_command_uses_flags_the_trimmer_accepts(self):
        """A4's present-branch risk: this module carries a copy of ANOTHER tool's interface and
        goes stale when that interface moves. The flags are not compared against a hardcoded
        literal -- the command is lifted out of the emitted advisory and actually RUN, and the
        assertion is that the trimmer did not reject its arguments.

        Asserted on argparse's own rejection text and on the finding CODES, never on the exit
        code: `--check` exits 1 BY DESIGN when the trigger fires, so an exit-code assertion here
        would read a working tool as a broken one."""
        descs, trim_metrics = self._descs(self.REPO, expect_role="framework")
        self.assertTrue(trim_metrics["tool_present"],
                        "fixture check: the canonical repo must locate its own trimmer, or the "
                        "present branch is not under test at all")
        if not descs:
            self.skipTest("this repo's own trim trigger is not currently firing on either "
                          "ledger (S64 cleared HANDOFFS.md's; CHANGELOG.md's was already clear) "
                          "-- this test's fixture precondition needs a live over-budget ledger "
                          "and will run again once one exists")
        cmds = [c for d in descs for c in re.findall(r"`([^`]+)`", d)]
        self.assertTrue(cmds, "the present branch must name at least one runnable command")
        for cmd in cmds:
            parts = cmd.split()
            self.assertEqual(parts[:1], ["python3"], cmd)
            proc = subprocess.run(parts, cwd=str(self.REPO), capture_output=True, text=True,
                                  timeout=120)
            self.assertNotIn("unrecognized arguments", proc.stderr, cmd)
            self.assertNotIn("invalid choice", proc.stderr, cmd)
            self.assertNotIn("expected one argument", proc.stderr, cmd)
            self.assertIn("[CHECK]", proc.stdout,
                          "the named command must actually reach the trigger report: " + cmd)

    def test_present_branch_never_promises_a_write(self):
        """A trigger firing is not a trim being correct, and the tool knows the difference: on
        this repo `--write` refuses (undocumented set non-empty, and SRF past RED). An advisory
        ending "--write to archive" would name a command that declines."""
        descs, _ = self._descs(self.REPO, expect_role="framework")
        if not descs:
            self.skipTest("this repo's own trim trigger is not currently firing on either "
                          "ledger (S64 cleared HANDOFFS.md's; CHANGELOG.md's was already clear) "
                          "-- this test's fixture precondition needs a live over-budget ledger "
                          "and will run again once one exists")
        for d in descs:
            self.assertNotIn("--write", d)

    # --- A4, branch 2: the absent branch, which no developer machine runs by accident -----------

    def test_absent_branch_names_the_file_and_never_a_command(self):
        """A4's absent-branch risk: this branch never runs where the tool is installed, so
        nothing checks that it says anything useful. It must name the FILE it was computed
        against (a generic noun in this position once misdirected an adopter) and must not name
        a command the adopter does not have."""
        # Sized off CLASS_A_FIRE_BYTES, not READ_CAP_BYTES. This is a Class A ledger and
        # that is now the arm that fires it; at the old size the branch stays silent and the
        # "must still speak" assertion below fails on a fixture precondition rather than on the
        # behaviour it is guarding.
        p = self._sized("CHANGELOG.md", md.CLASS_A_FIRE_BYTES + 2)

        descs, trim_metrics = self._descs(p)
        self.assertFalse(trim_metrics["tool_present"],
                         "fixture check: the trimmer must be absent, or this is the other branch")
        self.assertTrue(descs, "the absent branch must still speak when the read metric fires")
        joined = "\n".join(descs)
        self.assertIn("CHANGELOG.md", joined, "the advisory must name the file it measured")
        self.assertNotIn("python3", joined,
                         "the absent branch must not name a command the adopter cannot run")
        self.assertNotIn("`", joined)

    def test_the_silent_watched_ledger_state_can_no_longer_OCCUR(self):
        """WHAT THIS REPLACED. Two tests used to guard a `low` advisory -- "watched but
        unmeasured" -- that fired where NEITHER half spoke: no archive, so the RATE had no
        baseline, and no trimmer, so no budget. The design forbids reporting a 0 from an unread
        source as a clean state, and that was the state which met the description.

        Phase B removed the STATE, not just the row, so the honest assertion is that the
        conjunction cannot arise: the read half is a LEVEL and answers from the file's own size,
        with no git history and no trimmer installed. This fixture is the exact repo the old
        advisory fired on -- day-one adopter, no archive, no tool -- and the scanner now has a
        verdict for it.

        THE DELETED ROW MUST ALSO STAY DELETED. Narrowing it to the byte half alone (fire whenever
        the budget is unknown) would put a permanent unactionable row on every repo in the fleet
        over a budget no distributed file has ever named -- an early draft did exactly that, and
        the conjunction was the fix for it. Asserted, because restoring "half" of a deleted guard
        is the likeliest way this comes back."""
        p = self._repo({"CHANGELOG.md": "# Changelog\n\n" + self._entries(6)})
        descs, trim_metrics = self._descs(p)
        self.assertFalse(trim_metrics["tool_present"], "fixture: no trimmer")
        self.assertIsNone(md._newest_archive_sha(p, "CHANGELOG.md"), "fixture: no archive")
        led = [l for l in trim_metrics["ledgers"] if l["path"] == "CHANGELOG.md"][0]
        self.assertIsNone(led["byte_fires"], "fixture: the budget really is unknown here")
        self.assertIn("read_fires", led, "the read half must still have spoken")
        self.assertIs(led["read_fires"], False)
        self.assertFalse([d for d in descs if "watched but unmeasured" in d],
                         "the advisory guarded a state that can no longer occur: %r" % descs)
        self.assertFalse([d for d in descs if "unmeasured" in d or "abstain" in d], descs)

    def test_a_measurable_ledger_under_both_thresholds_says_nothing(self):
        """The control for the test above, and the fleet-noise property it protects. A ledger the
        scanner CAN measure and which is under both thresholds must produce no row at all -- not a
        reassuring one. Without this, deleting the advisory could be "passed" by a scanner that
        had simply stopped emitting anything."""
        p = self._sized("CHANGELOG.md", md.READ_CAP_BYTES - 2)
        descs, trim_metrics = self._descs(p)
        led = [l for l in trim_metrics["ledgers"] if l["path"] == "CHANGELOG.md"][0]
        self.assertFalse(led["fires"])
        self.assertEqual(descs, [], "a quiet ledger gets no row: %r" % descs)

    def test_unreadable_budget_is_not_reported_as_an_absent_tool(self):
        """An installed trimmer whose budget constant cannot be parsed is a DIFFERENT finding
        from a missing trimmer. An earlier draft reported the second for both, which would have
        told an operator looking straight at an installed tool that it was not installed."""
        p = self._repo({
            "CHANGELOG.md": "# Changelog\n\n" + self._entries(6),
            "methodology_trim.py": 'TRIM_VERSION = "9.9.9"\nDEFAULT_BUDGET_BYTES = later()\n',
        }, archive="CHANGELOG-through-2025-12-31.md")
        descs, trim_metrics = self._descs(p)
        # The DISTINCTION is what this test is for, and Phase B moved where it is observable: the
        # advisory that used to carry it guarded a state that can no longer occur and was deleted,
        # so the assertion is now on the metrics dict, which is what the HTML card and
        # dashboard_history.jsonl both read. `tool_present` True with `budget_bytes` None is a
        # different finding from `tool_present` False, and conflating them once told an operator
        # looking straight at an installed tool that it was not there.
        self.assertTrue(trim_metrics["tool_present"], "an installed tool must read as installed")
        self.assertIsNone(trim_metrics["budget_bytes"], "and its unparseable budget as unknown")
        self.assertEqual(trim_metrics["tool_version"], "9.9.9",
                         "the version parsed, so 'absent' would be plainly wrong here")
        absent = self._repo({"CHANGELOG.md": "# Changelog\n\n" + self._entries(6)})
        _d, absent_metrics = self._descs(absent)
        self.assertFalse(absent_metrics["tool_present"],
                         "control: the OTHER finding must be distinguishable, or the pair above "
                         "asserts nothing")
        self.assertNotIn("is not installed", "\n".join(descs))

    # --- The owed agreement test -------------------------------------------------------------

    def test_read_verdict_agrees_with_a_real_check_run(self):
        """The owed agreement test, re-pointed onto the metric that replaced the
        rate. The two operands stay genuinely independent -- the left is computed by this module
        from `stat()`, the right is parsed out of a real subprocess run of the OTHER tool, which
        measures `len(text.encode())` -- so this can fail, and it fails under any drift in either
        the measurement or the threshold.

        BOTH halves are compared on purpose. Agreeing on the SIZE while disagreeing about the CAP
        would leave the reporter and the remedy pointing at different cliffs, which is the exact
        failure the original pin was written against."""
        trim_metrics = md.collect_trim_metrics(
            self.REPO, md.collect_file_metrics(self.REPO), role="framework")
        measured = {l["path"]: l for l in trim_metrics["ledgers"]}
        self.assertTrue(measured, "fixture check: the canonical repo must expose trimmable "
                                  "ledgers, or nothing is compared")
        # VACUITY GUARD, kept from the version this replaced. A loop that silently compares
        # nothing passes; the comparisons are counted rather than hoped for.
        compared = 0
        for rel, led in measured.items():
            proc = subprocess.run(
                ["python3", TRIM_PY, "--file", rel, "--check"],
                cwd=str(self.REPO), capture_output=True, text=True, timeout=120)
            # THE REGEX WAS RE-POINTED, and the reason is the whole point of the test.
            # The row now names the threshold ACTUALLY IN FORCE, which for a root Class A ledger
            # is the archive threshold and not the one-read cap. Matching only the old wording
            # would have made this test fail loudly (it did) rather than quietly agree about a
            # number the trimmer no longer keys on -- so the alternation below is written to
            # accept EITHER row and then assert WHICH one it got, never to accept both silently.
            m = re.search(r"\[TRIGGER_READ\] ([\d,]+) B against (?:a|the) ([\d,]+) B "
                          r"(one-read cap|Class A archive threshold)", proc.stdout)
            self.assertIsNotNone(
                m, "unexpected --check output for %s: %s" % (rel, proc.stdout))
            self.assertEqual(led["bytes"], int(m.group(1).replace(",", "")),
                             "displayed size for %s must equal --check's" % rel)
            expected_arm = (md.CLASS_A_FIRE_BYTES if m.group(3) == "Class A archive threshold"
                            else md.READ_CAP_BYTES)
            self.assertEqual(expected_arm, int(m.group(2).replace(",", "")),
                             "the reporter and the remedy must agree where the cliff is")
            # Every entry in collect_trim_metrics["ledgers"] is class A by the collector's own
            # filter AND is repo-root-relative, so the trimmer -- which decides root-ness by an
            # independent relative_to check -- must reach the same conclusion. If these two ever
            # drift, this is where it shows.
            self.assertEqual(m.group(3), "Class A archive threshold",
                             "%s is in the collector's Class A ledger list, so the trimmer must "
                             "also have classified it as a ROOT Class A ledger; a 'one-read cap' "
                             "row here means the two tools disagree about scoping" % rel)
            self.assertEqual(led["read_fires"],
                             led["bytes"] > int(m.group(2).replace(",", "")),
                             "the displayed verdict for %s must follow from the two numbers "
                             "it displays" % rel)
            compared += 1
        self.assertGreaterEqual(compared, 1,
                                "no agreement was actually asserted (%d ledgers)" % len(measured))

    # --- the record counter, at the two points the live repo does NOT discriminate --------------

    def test_fenced_records_are_not_counted(self):
        """The live ledgers cannot prove this: every dated heading in the root CHANGELOG.md is a
        real entry, so a fence-blind counter scores identically there. The SEED ledgers are the
        discriminating fixture and they are real artifacts, not synthetic ones -- every dated
        heading in the `CHANGELOG.md` seed as shipped before ledger-format 2 and the one
        ```handoff block in `starter-kit/HANDOFFS.md` sit inside documentation fences. A
        fence-blind counter reads 3 and 1 where the truth is 0, and would print a confident slope
        for a freshly seeded ledger that holds no records at all. Since ledger-format 2 the live
        `CHANGELOG.md` seed is a pointer with no fenced examples, so that half reads the frozen
        copy in tools/fixtures/ (its blob id asserted, as tools/test_methodology_trim.py does)."""
        fixture = self.REPO / "tools" / "fixtures" / "seed-CHANGELOG-ledger-format-1.md"
        raw = fixture.read_bytes()
        self.assertEqual(hashlib.sha1(b"blob %d\0" % len(raw) + raw).hexdigest(),
                         "47bc848591fb4ee6906dde885c28f53348af0f26",
                         "the frozen format-1 seed changed; it must stay the seed as shipped")
        seed_cl = raw.decode("utf-8")
        seed_ho = (self.REPO / "starter-kit" / "HANDOFFS.md").read_text(encoding="utf-8")
        # Fixture control: the naive counts really are non-zero, or "0" proves nothing.
        self.assertGreater(len(re.findall(r"(?m)^### \d{4}-\d{2}-\d{2}", seed_cl)), 0)
        self.assertGreater(len(re.findall(r"(?m)^```handoff", seed_ho)), 0)
        self.assertEqual(md._trim_record_count(seed_cl, "CHANGELOG.md"), 0)
        self.assertEqual(md._trim_record_count(seed_ho, "HANDOFFS.md"), 0)
        # The live thin seed is still a fresh ledger: no records.
        live_cl = (self.REPO / "starter-kit" / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertEqual(md._trim_record_count(live_cl, "CHANGELOG.md"), 0)

    def test_record_counter_matches_the_trimmers_zoning_on_every_real_ledger(self):
        """Seven real files, including both archives and both seeds. The dashboard's counter and
        the trimmer's fence-aware classify_zones are separate implementations; this is what
        makes the headroom agreement above more than a coincidence on two files."""
        trim = _load_trimmer()
        targets = ["CHANGELOG.md", "HANDOFFS.md",
                   "starter-kit/CHANGELOG.md", "starter-kit/HANDOFFS.md"]
        targets += [str(q.relative_to(self.REPO).as_posix())
                    for q in sorted((self.REPO / "docs" / "archive").glob("*.md"))]
        existing = [rel for rel in targets if (self.REPO / rel).is_file()]
        self.assertGreaterEqual(len(existing), 4,
                                "fixture check: the four named ledgers must exist")
        checked = 0
        for rel in targets:
            fp = self.REPO / rel
            if not fp.is_file():
                continue
            base = "CHANGELOG.md" if "CHANGELOG" in fp.name else "HANDOFFS.md"
            text = fp.read_text(encoding="utf-8")
            zones = trim.classify_zones(text, trim.LEDGERS[base], trim.Result(fp))
            if zones is None:
                continue
            self.assertEqual(md._trim_record_count(text, base), len(zones.starts), rel)
            checked += 1
        # Every ledger that exists must have been compared, up to six: the floor is the population,
        # so a tree with fewer archives is not failed for lacking them, and a loop that compared
        # nothing still is.
        self.assertGreaterEqual(checked, min(6, len(existing)),
                                "fixture check: too few real ledgers compared (%d of %d)"
                                % (checked, len(existing)))

    # --- the review fixes, each held by the fixture that exposed it ------------------------------
    #
    # Every test in this block was written AFTER a producer mutant reverting the corresponding
    # fix survived the suite. A fix with no test is a fix that gets undone.

    def test_a_shard_commit_that_did_not_shrink_the_ledger_is_not_a_baseline(self):
        """The trimmer counts an archive EVENT, not a shard file: `if pre is None or post is None
        or pre <= post: continue`. Without the same filter the dashboard picks a baseline the
        trimmer rejects, and the two gauges disagree -- measured at headroom 248 against
        `--check`'s 35 on one review fixture, and at a firing trigger the dashboard missed on
        another. It does not bite on this repo, because every shard here really did shrink its
        ledger, so the live agreement test passed on luck of history until this fixture existed."""
        cl = "# Changelog\n\n" + self._entries(6)
        p = self._repo({"CHANGELOG.md": cl + "padding\n" * 400}, archive=None)
        # A real event: shard `a`, committed with a shrink.
        (p / "docs" / "archive").mkdir(parents=True, exist_ok=True)
        (p / "docs" / "archive" / "CHANGELOG-through-a.md").write_text("# real\n")
        (p / "CHANGELOG.md").write_text(cl)
        self._commit(p, "shard a + shrink")
        real = subprocess.run(["git", "-C", str(p), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
        # A stray shard dropped in later, with the ledger GROWING in the same commit.
        (p / "docs" / "archive" / "CHANGELOG-through-z.md").write_text("# stray\n")
        (p / "CHANGELOG.md").write_text(cl + self._entries(3, start=6))
        self._commit(p, "stray shard, ledger grew")

        self.assertEqual(md._newest_archive_sha(p, "CHANGELOG.md"), real,
                         "the stray shard's commit is not an archive event and must not become "
                         "the baseline")

    def test_a_shard_commit_where_the_ledger_is_unchanged_is_not_a_baseline(self):
        """The EDGE of the filter, not just its interior: `pre <= post`, so pre == post is
        excluded too. `<=` -> `<` survived the suite until this fixture pinned equality -- the
        two-step manual archive (commit the shard, then commit the trimmed ledger) produces
        exactly this shape."""
        cl = "# Changelog\n\n" + self._entries(6)
        p = self._repo({"CHANGELOG.md": cl + "padding\n" * 400}, archive=None)
        (p / "docs" / "archive").mkdir(parents=True, exist_ok=True)
        (p / "docs" / "archive" / "CHANGELOG-through-a.md").write_text("# real\n")
        (p / "CHANGELOG.md").write_text(cl)
        self._commit(p, "shard a + shrink")
        real = subprocess.run(["git", "-C", str(p), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
        # Shard committed alone: the ledger is byte-identical across this commit.
        before = (p / "CHANGELOG.md").read_bytes()
        (p / "docs" / "archive" / "CHANGELOG-through-z.md").write_text("# shard only\n")
        self._commit(p, "shard z alone, ledger untouched")
        self.assertEqual((p / "CHANGELOG.md").read_bytes(), before,
                         "fixture: the ledger must be unchanged across the shard commit")

        self.assertEqual(md._newest_archive_sha(p, "CHANGELOG.md"), real)

    def test_an_unrankable_shard_abstains_rather_than_falling_back_to_filename_order(self):
        """git_cmd returns "" on timeout, indistinguishable from success. An empty walk collapses
        every rank to one sentinel and the stable sort leaves FILENAME order, which for a
        date-stamped naming scheme silently selects the OLDEST -- the exact ordering this
        function's contract forbids, reached with no error and no marker.

        The timeout is injected at `git_cmd` rather than simulated by stalling git: the failure
        being tested is "the walk came back empty", and that is what git_cmd hands back on
        timeout. Two GENUINE archive events are built first, so the function really is in the
        branch that has to choose between candidates."""
        cl = "# Changelog\n\n" + self._entries(6)
        p = self._repo({"CHANGELOG.md": cl + "padding\n" * 400}, archive=None)
        (p / "docs" / "archive").mkdir(parents=True, exist_ok=True)
        (p / "docs" / "archive" / "CHANGELOG-through-a.md").write_text("# older\n")
        (p / "CHANGELOG.md").write_text(cl)
        self._commit(p, "shard a + shrink")
        (p / "CHANGELOG.md").write_text(cl + "padding\n" * 400)
        self._commit(p, "grow")
        (p / "docs" / "archive" / "CHANGELOG-through-z.md").write_text("# newer\n")
        (p / "CHANGELOG.md").write_text(cl)
        self._commit(p, "shard z + shrink")

        # Control: with a working walk it answers, and answers with the graph-newest.
        newest = md._newest_archive_sha(p, "CHANGELOG.md")
        self.assertIsNotNone(newest, "fixture: two real archive events must be present")

        real_git_cmd = md.git_cmd

        def flaky(path, *args, **kw):
            if args[:1] == ("rev-list",):
                return ""              # exactly what git_cmd returns on timeout
            return real_git_cmd(path, *args, **kw)

        md.git_cmd = flaky
        try:
            self.assertIsNone(md._newest_archive_sha(p, "CHANGELOG.md"),
                              "an unrankable candidate set must abstain, never silently degrade "
                              "to filename order")
        finally:
            md.git_cmd = real_git_cmd
        # And the injection was real: the working call still answers afterwards.
        self.assertEqual(md._newest_archive_sha(p, "CHANGELOG.md"), newest)

    def test_a_nested_fence_with_an_info_string_is_not_a_closer(self):
        """The trimmer closes a fence only on a marker with an EMPTY info string. Dropping that
        conjunct flips the fence state on a nested ```python, and every record after it is
        counted by one side and not the other. Compared against the trimmer's own zoning, so the
        two operands stay independent."""
        trim = _load_trimmer()
        text = ("# Handoffs\n\n"
                "```handoff\nsession: S1\n"
                "```python\nstill inside the S1 record\n```\n\n"
                "```handoff\nsession: S2\n```\n")
        zones = trim.classify_zones(text, trim.LEDGERS["HANDOFFS.md"],
                                    trim.Result(Path("HANDOFFS.md")))
        self.assertIsNotNone(zones)
        self.assertEqual(len(zones.starts), 2, "fixture check: the trimmer must see two records")
        self.assertEqual(md._trim_record_count(text, "HANDOFFS.md"), 2)

    def test_a_ledger_the_trimmer_refuses_to_zone_abstains_here_too(self):
        """`LEDGERS['HANDOFFS.md']` declares footer_mode='none' and classify_zones ASSERTS the
        declaration: a standalone '---' after the last record with content under it returns None
        (ZONE_UNCLASSIFIED). The trimmer treats that as a reason to abstain and says why -- "that
        is not a count of zero" -- so a counter that always answers prints a confident headroom
        exactly where `--check` prints none."""
        trim = _load_trimmer()
        refused = ("# Handoffs\n\n```handoff\nsession: S1\n```\n\n"
                   "---\n\nTrailing prose the config cannot classify.\n")
        self.assertIsNone(
            trim.classify_zones(refused, trim.LEDGERS["HANDOFFS.md"],
                                trim.Result(Path("HANDOFFS.md"))),
            "fixture check: the trimmer must refuse this shape")
        self.assertIsNone(md._trim_record_count(refused, "HANDOFFS.md"))

        # Control: the same file without the trailing content classifies, and both agree.
        ok = "# Handoffs\n\n```handoff\nsession: S1\n```\n\n---\n"
        z = trim.classify_zones(ok, trim.LEDGERS["HANDOFFS.md"], trim.Result(Path("HANDOFFS.md")))
        self.assertIsNotNone(z)
        self.assertEqual(md._trim_record_count(ok, "HANDOFFS.md"), len(z.starts))

    def test_the_trim_fence_regex_does_not_rebind_the_pre_existing_one(self):
        """A REGRESSION I CAUSED AND THE REVIEW CAUGHT. The first draft named this module's new
        fence regex `_FENCE_RE`, which already existed at module scope as the sole detector for
        `_strip_fenced_blocks()`. The later binding won, and the two differ on INDENTED fences --
        the old pattern allows leading whitespace, the new one anchors at column 0 -- so an
        indented documentation example stopped being stripped and its `- [x]` lines became
        phantom unmigrated done-marks in the backlog signal. Measured at 0 before, 2 after.

        Asserted on BEHAVIOUR, not on the names: renaming the constant back would satisfy a
        name-based check while re-creating the defect."""
        backlog = ("# Backlog\n\nExample of a done-mark:\n\n"
                   "    ```markdown\n"
                   "    - [x] a DOCUMENTATION EXAMPLE, not a real done-mark\n"
                   "    - [x] and another\n"
                   "    ```\n\n"
                   "- [ ] a real open item\n")
        self.assertEqual(md._strip_fenced_blocks(backlog).count("- [x]"), 0,
                         "an indented fenced example must still be stripped")
        # Fixture control: the marks really are there before stripping.
        self.assertEqual(backlog.count("- [x]"), 2)
        # And the two regexes must remain distinct objects with distinct patterns.
        self.assertNotEqual(md._FENCE_RE.pattern, md._TRIM_FENCE_RE.pattern)

    def test_unknown_basename_abstains_instead_of_counting_zero(self):
        self.assertIsNone(md._trim_record_count("### 2026-01-01 x\n", "BACKLOG.md"))

    def test_a_dated_heading_without_a_source_tag_is_not_a_record(self):
        """Closes a survivor: loosening the grammar to `^### <date>` changes nothing on any real
        ledger here, because every dated heading in them happens to be source-tagged. The
        distinguishing input has to be built, and it is checked against the trimmer's own zoning
        rather than against my expectation of it."""
        trim = _load_trimmer()
        text = ("# Changelog\n\n"
                "### 2026-01-01 %s [ad hoc] a real entry\n\nbody\n\n"
                "### 2026-01-02 a heading that is dated but not an entry\n\nbody\n"
                % md._MIDDLE_DOT)
        zones = trim.classify_zones(text, trim.LEDGERS["CHANGELOG.md"],
                                    trim.Result(Path("CHANGELOG.md")))
        self.assertIsNotNone(zones)
        self.assertEqual(len(zones.starts), 1,
                         "fixture check: the trimmer must see exactly one record here")
        self.assertEqual(md._trim_record_count(text, "CHANGELOG.md"), 1)

    def test_shard_added_before_the_ledger_existed_is_not_an_archive_event(self):
        """A shard committed before the ledger exists cannot be an archive event -- there is no
        pre-image to have shrunk from -- so the rate has no baseline and must say so.

        This test previously asserted the "baseline unreadable" reason and passed for the wrong
        reason: the shard was accepted as an event, `git show` then failed on the missing blob,
        and the abstention arrived one step too late. With the shrink filter the candidate is
        rejected up front, which is what the trimmer does. `git_show`'s own None-on-failure
        contract is pinned directly below rather than through this path."""
        # Built inline: _repo's archive= path now ASSERTS that the shard commit is a real event,
        # and this test's whole point is a shard commit that is not one.
        p = self._repo({"README.md": "# r\n"})
        ap = p / "docs" / "archive" / "CHANGELOG-through-2025-12-31.md"
        ap.parent.mkdir(parents=True, exist_ok=True)
        ap.write_text("# archived shard\n")
        self._commit(p, "shard, with no ledger in the tree at all")
        (p / "CHANGELOG.md").write_text("# Changelog\n\n" + self._entries(8))
        self._commit(p, "add the ledger after the shard")

        # Asserted on the DETECTOR directly. Phase B removed this function's production consumer
        # (see its comment in the scanner), so routing the assertion through collect_all would now
        # prove nothing about it -- the very shape of vacuity this suite keeps catching.
        self.assertIsNone(md._newest_archive_sha(p, "CHANGELOG.md"))
        led = [l for l in md.collect_all(p)["trim"]["ledgers"]
               if l["path"] == "CHANGELOG.md"][0]
        self.assertFalse(led["read_fires"], "and the read half answers regardless, as it must")

    def test_git_show_returns_none_for_a_missing_blob(self):
        """Pinned directly, because the shrink filter now rejects most ways of reaching it
        through trim_line_headroom. "" would make a missing blob look like an empty file and the
        slope would be computed against a fabricated zero-line baseline."""
        p = self._repo({"CHANGELOG.md": "# Changelog\n"})
        self.assertIsNone(md.git_show(p, "HEAD:does-not-exist.md"))
        self.assertIsNone(md.git_show(p, "no-such-ref:CHANGELOG.md"))
        self.assertEqual(md.git_show(p, "HEAD:CHANGELOG.md"), "# Changelog\n")

    def test_git_show_decodes_utf8_regardless_of_locale(self):
        """The record grammar turns on U+00B7. `text=True` alone decodes with the LOCALE, so under
        a non-UTF-8 environment the middle dot's bytes stop being a middle dot, the heading regex
        stops matching, the baseline record count collapses and the reported headroom inflates --
        measured by the review at 34 against `--check`'s 20 on this very repo. The trimmer's
        baseline read is always UTF-8; this asserts the same.

        `LC_ALL=C` ALONE IS NOT ENOUGH and a test that used it would pass vacuously: Python's
        UTF-8 mode coerces the C locale back to UTF-8, so the unpinned code still works. PYTHONUTF8=0
        is what actually makes the child prefer US-ASCII. The child is asked what it will use, and
        the test SKIPS rather than passes if the platform refuses to move off UTF-8 -- a green
        result here has to mean the hostile case was really exercised."""
        env = dict(os.environ, LC_ALL="C", LANG="C", PYTHONUTF8="0", PYTHONCOERCECLOCALE="0")
        probe = subprocess.run(
            [sys.executable, "-c", "import locale;print(locale.getpreferredencoding(False))"],
            capture_output=True, text=True, env=env, check=True).stdout.strip()
        if probe.lower().replace("-", "") in ("utf8",):
            self.skipTest("platform will not leave UTF-8 (child reports %r)" % probe)

        p = self._repo({"CHANGELOG.md": "### 2026-01-01 %s [ad hoc] x\n" % md._MIDDLE_DOT})
        # The child's own stdout is ASCII under this locale, so it must NOT try to print the
        # character -- doing so raises UnicodeEncodeError on correct code and the test would fail
        # for a reason that has nothing to do with git_show. It reports a verdict instead.
        child = (
            "import sys;sys.path.insert(0,%r);import methodology_dashboard as m;"
            "from pathlib import Path;"
            "t=m.git_show(Path(%r), 'HEAD:CHANGELOG.md');"
            "print('VERDICT', 'DOT' if '\\u00b7' in t else 'NODOT',"
            " t.encode('unicode_escape').decode('ascii')[:60])" % (HERE, str(p))
        )
        out = subprocess.run([sys.executable, "-c", child],
                             capture_output=True, text=True, env=env)
        self.assertEqual(out.returncode, 0,
                         "git_show must not raise under a non-UTF-8 locale: %s" % out.stderr)
        self.assertIn("VERDICT DOT", out.stdout,
                      "git_show must decode UTF-8 under %s; got %s" % (probe, out.stdout))

    def test_newest_archive_is_chosen_by_graph_order_not_by_filename(self):
        """Closes a survivor: on this repo the shards' alphabetical order happens to match their
        commit order, so dropping the graph sort changes nothing. The fixture inverts the two --
        shard `a` is committed FIRST and shard `z` second -- so filename order names the oldest
        and only graph order names the newest. (The trimmer records the same mutant as
        undecidable for ITS fixtures; this one decides it.)"""
        cl = "# Changelog\n\n" + self._entries(4)
        p = self._repo({"CHANGELOG.md": cl + "padding\n" * 400}, archive=None)

        # Archive event 1: shard `a`, committed WITH a shrink. Both shards must be real events
        # now that the shrink filter is in place, or neither is a candidate to choose between.
        (p / "docs" / "archive").mkdir(parents=True, exist_ok=True)
        (p / "docs" / "archive" / "CHANGELOG-through-a.md").write_text("# older shard\n")
        (p / "CHANGELOG.md").write_text(cl)
        self._commit(p, "shard a (older) + shrink")
        older_sha = subprocess.run(["git", "-C", str(p), "rev-parse", "HEAD"],
                                   capture_output=True, text=True, check=True).stdout.strip()

        # Grow again, then archive event 2: shard `z`, also with a shrink.
        (p / "CHANGELOG.md").write_text(cl + "padding\n" * 400)
        self._commit(p, "grow")
        (p / "docs" / "archive" / "CHANGELOG-through-z.md").write_text("# newer shard\n")
        (p / "CHANGELOG.md").write_text(cl)
        self._commit(p, "shard z (newer) + shrink")
        newer_sha = subprocess.run(["git", "-C", str(p), "rev-parse", "HEAD"],
                                   capture_output=True, text=True, check=True).stdout.strip()

        self.assertNotEqual(older_sha, newer_sha)
        self.assertEqual(md._newest_archive_sha(p, "CHANGELOG.md"), newer_sha,
                         "the baseline must be the most recent shard by COMMIT GRAPH position, "
                         "not the first one the glob happened to return")

    # --- abstention and gating ------------------------------------------------------------------

    def test_no_prior_archive_still_yields_a_verdict(self):
        """Every adopter on day one is in this state, and it is the case Phase B most changes.
        A RATE with no baseline had no value and had to abstain out loud -- which meant the half
        guarding truncation said nothing at all on a brand-new repo. A LEVEL reads the file's own
        size, so day one is answerable like any other day."""
        p = self._repo({"CHANGELOG.md": "# Changelog\n\n" + self._entries(6)})
        trim_metrics = md.collect_all(p)["trim"]
        led = [l for l in trim_metrics["ledgers"] if l["path"] == "CHANGELOG.md"]
        self.assertEqual(len(led), 1)
        self.assertIsNone(md._newest_archive_sha(p, "CHANGELOG.md"),
                          "fixture: there must be no archive baseline, or this proves nothing")
        self.assertIsNotNone(led[0]["read_fires"], "the read half must answer without a baseline")
        self.assertFalse(led[0]["read_fires"], "and this small fixture is under the cap")
        self.assertNotIn("abstains", led[0],
                         "abstention was the rate's machinery and went with it")

    def test_non_adopter_is_never_told_about_its_changelog(self):
        """The same gate the D4(b) risk uses. A project that never adopted the methodology keeps
        whatever changelog it likes; ungated, this row fires on any repo with a long one -- the
        assumption whose measured cost is already recorded in FRAMEWORK_INSTALLED_SOURCE."""
        p = self._repo({"CHANGELOG.md": "# Changelog\n\n" + self._entries(60, body=60)},
                       runner=False, archive="CHANGELOG-through-2025-12-31.md")
        trim_metrics = md.collect_all(p)["trim"]
        self.assertEqual(trim_metrics["signals"], [])
        self.assertEqual(trim_metrics["ledgers"], [])

    # --- the EDGES, not only the predicates ------------------------------------

    def _exact(self, base_lines, base_records, live_lines, live_records, trimmer=None):
        """A repo whose line metric lands on an arithmetic point I choose.

        headroom = (2000 - live_lines) * de // dl, so the fixture pins de and dl directly rather
        than hoping a plausible-looking ledger happens to land near a threshold. The archive
        shard is added in the SAME commit as the baseline, because the split is the commit that
        added the shard and the baseline blob is the ledger as of that commit."""
        def ledger(n_lines, n_records):
            out = []
            for i in range(n_records):
                out.append("### 2026-01-%02d %s [ad hoc] entry %d" % (i % 28 + 1, md._MIDDLE_DOT, i))
                out.append("")
                out.append("body")
            pad = n_lines - len(out)
            self.assertGreaterEqual(pad, 0, "fixture arithmetic: asked for too few lines")
            out.extend(["filler"] * pad)
            text = "\n".join(out) + "\n"
            self.assertEqual(text.count("\n"), n_lines)
            return text

        files_map = {"CHANGELOG.md": ledger(base_lines, base_records)}
        if trimmer is not None:
            files_map["methodology_trim.py"] = trimmer
        p = self._repo(files_map, archive="CHANGELOG-through-2025-12-31.md")
        (p / "CHANGELOG.md").write_text(ledger(live_lines, live_records))
        self._commit(p, "grow")
        # Fixture control: the baseline the dashboard will measure against must be the shard
        # commit, and the arithmetic above is stated in terms of that blob.
        split = md._newest_archive_sha(p, "CHANGELOG.md")
        self.assertIsNotNone(split)
        base = md.git_show(p, "%s:CHANGELOG.md" % split)
        self.assertEqual(base.count("\n"), base_lines, "fixture: baseline blob line count")
        self.assertEqual(md._trim_record_count(base, "CHANGELOG.md"), base_records,
                         "fixture: baseline blob record count")
        return p

    def test_read_level_exactly_at_the_class_a_threshold_does_not_fire(self):
        """`size > threshold` fires; the threshold itself does not. `>` -> `>=` is precisely the
        mutant that survived the whole suite one session ago on this very signal, so the exact
        boundary is exercised deliberately.

        THE THRESHOLD CHANGE MOVED THE BOUNDARY THIS PAIR GUARDS, and the rename is part of the change: these
        ledgers are Class A, and the arm that decides for them is CLASS_A_FIRE_BYTES. Testing the
        old constant here would have kept a green pair guarding a boundary the collector no longer
        keys on -- true arithmetic about a dead threshold."""
        p = self._sized("CHANGELOG.md", md.CLASS_A_FIRE_BYTES)
        led = [l for l in md.collect_all(p)["trim"]["ledgers"] if l["path"] == "CHANGELOG.md"][0]
        self.assertEqual(led["bytes"], md.CLASS_A_FIRE_BYTES, "fixture: exactly the threshold")
        self.assertFalse(led["read_fires"], "a file of exactly the threshold does not fire")
        self.assertFalse(led["refused"])

    def test_read_level_just_past_the_class_a_threshold_fires(self):
        """The control for the test above: same fixture shape, two bytes larger."""
        p = self._sized("CHANGELOG.md", md.CLASS_A_FIRE_BYTES + 2)
        led = [l for l in md.collect_all(p)["trim"]["ledgers"] if l["path"] == "CHANGELOG.md"][0]
        self.assertTrue(led["read_fires"])
        self.assertFalse(led["refused"], "past the threshold is not yet the hard refusal")
        self.assertTrue(led["fires"])

    def test_a_class_a_ledger_BETWEEN_the_cap_and_the_threshold_stays_QUIET(self):
        """THE BAND THE THRESHOLD CHANGE CREATED, and the assertion that proves the move actually happened.

        Before the change this size fired. It is now the adjudicated band: past the one-read cap, so a
        whole-file read truncates, but nowhere near the point where archiving is worth doing.
        Without this test the pair above would pass equally well against an implementation that
        simply never fires."""
        p = self._sized("CHANGELOG.md", md.READ_CAP_BYTES + 2)
        led = [l for l in md.collect_all(p)["trim"]["ledgers"] if l["path"] == "CHANGELOG.md"][0]
        self.assertGreater(led["bytes"], md.READ_CAP_BYTES, "fixture: over the one-read cap")
        self.assertLess(led["bytes"], md.CLASS_A_FIRE_BYTES, "fixture: under the Class A arm")
        self.assertFalse(led["read_fires"],
                         "a Class A ledger in this band must NOT fire -- if it does, the "
                         "collector is still keying on READ_CAP_BYTES")
        self.assertFalse(led["fires"], "and the byte arm must not fire here either, or option C1 "
                                       "was not applied and the trigger is inert")

    def test_size_exactly_at_the_budget_does_not_fire(self):
        """`size > budget` fires; equality does not. Same edge, the other metric. The fixture
        carries its own trimmer with a small budget so the boundary is reachable without
        writing a 64 KB file."""
        stub = 'TRIM_VERSION = "0.0.1"\nDEFAULT_BUDGET_BYTES = 900\n'
        p = self._exact(base_lines=40, base_records=4, live_lines=60, live_records=6,
                        trimmer=stub)
        cl = p / "CHANGELOG.md"
        text = cl.read_text()
        # Pad to EXACTLY the budget, keeping the trailing newline so the line metric is unmoved.
        pad = 900 - len(text.encode("utf-8"))
        self.assertGreater(pad, 0, "fixture arithmetic: ledger already exceeds the stub budget")
        cl.write_text(text[:-1] + ("p" * pad) + "\n")
        self.assertEqual(cl.stat().st_size, 900)
        self._commit(p, "pad to exactly the budget")

        trim_metrics = md.collect_all(p)["trim"]
        self.assertEqual(trim_metrics["budget_bytes"], 900)
        led = [l for l in trim_metrics["ledgers"] if l["path"] == "CHANGELOG.md"][0]
        self.assertEqual(led["bytes"], 900)
        self.assertFalse(led["byte_fires"], "a ledger of exactly the budget must not fire")

        # Control: one byte more, and it does.
        cl.write_text(cl.read_text()[:-1] + "q\n")
        self.assertEqual(cl.stat().st_size, 901)
        led2 = [l for l in md.collect_all(p)["trim"]["ledgers"]
                if l["path"] == "CHANGELOG.md"][0]
        self.assertTrue(led2["byte_fires"])

    # --- what the operator actually READS: the severities and the numbers ----------------------
    #
    # Written after a review pointed out that every one of these survived the full module: the
    # tests asserted that a row EXISTED and what it said in prose, never what severity it carried
    # or whether its figures were the figures that were measured. A row is a severity plus a
    # number; asserting the sentence around them is asserting the packaging.

    def test_the_authored_severities_are_pinned(self):
        """`medium` -> `critical` and `low` -> `high` both survived the suite. Severity is not
        decoration here: worst_risk() drives the portfolio row, the terminal colour and the
        High+ Risk count, so a wrong tier is a wrong dashboard for every project."""
        # THE SYNTHETIC HALF RUNS FIRST, AND THAT ORDER IS THE POINT. This half depends
        # on no live file at all, but it used to sit BELOW the `skipTest` that guards the live
        # half, so whenever this repo's own trigger fell quiet the skip aborted the method and
        # took the synthetic pin with it. That is not hypothetical: it is exactly how this test
        # hid a dead fixture for three days: a change re-denominated the Class A read
        # arm and re-sized this same `READ_CAP_BYTES + 2` fixture in two sibling tests, missed
        # this one, and its own run could not see the miss -- the change silenced the live rows,
        # so this method skipped and never reached the stale line. It surfaced only later,
        # when HANDOFFS.md crossed 196,608 B and un-muted it. A skip that covers assertions it
        # has no bearing on is a mute button, so the guard now covers only what it is about.
        #
        # The `low` tier went with the "watched but unmeasured" advisory that was deleted, so the
        # only severity this row can now author is `medium`. Pinned from the other side: a
        # firing ledger with no trimmer must still be advisory, never escalated. At
        # READ_CAP_BYTES + 2 that ledger fires NEITHER arm (the byte arm is None here --
        # no trimmer, no budget), so the signal set came back EMPTY and the severity assertion
        # went vacuous in the only direction that matters: a set with nothing in it can never
        # contain the wrong tier. Both fixture preconditions are therefore asserted separately
        # and BEFORE it, so a future re-denomination fails as a fixture defect and names itself.
        p = self._sized("CHANGELOG.md", md.CLASS_A_FIRE_BYTES + 2)
        _d2, tm2 = self._descs(p)
        self.assertTrue(tm2["signals"],
                        "fixture: a ledger past the Class A arm must emit a row, or the severity "
                        "assertion below passes on an empty set")
        self.assertFalse(tm2["tool_present"],
                         "fixture: this half is the NO-TRIMMER path -- if the tool is present "
                         "here it is exercising the other branch")
        self.assertEqual({sev for sev, _d in tm2["signals"]}, {"medium"},
                         "a firing archive trigger is advisory even with no tool to run")

        # ...and now the live half, which is the only part with a live precondition.
        _descs, tm = self._descs(self.REPO, expect_role="framework")
        if not tm["signals"]:
            self.skipTest("this repo's own trim trigger is not currently firing on either "
                          "ledger -- only the LIVE half below needs that precondition; the "
                          "synthetic pin above has already run")
        sevs = {s for s, _d in tm["signals"]}
        self.assertEqual(sevs, {"medium"},
                         "a firing archive trigger is advisory, not a high+ finding: %r" % sevs)

    def test_the_advisory_carries_the_numbers_that_were_measured(self):
        """Swapping the byte figures between two ledgers, or printing any other headroom, left
        all 310 tests green. The row is checked against the collector's own measurements here,
        each figure tied to the ledger it belongs to -- and the operands are independent: one
        side is the rendered sentence, the other is `Path.stat()` / the collected dict."""
        descs, tm = self._descs(self.REPO, expect_role="framework")
        by_path = {l["path"]: l for l in tm["ledgers"]}
        self.assertGreaterEqual(len(by_path), 2, "fixture: at least two ledgers must be measured")
        checked = 0
        for d in descs:
            rel = d.split(":")[0]
            if rel not in by_path:
                continue
            led = by_path[rel]
            on_disk = (self.REPO / rel).stat().st_size
            self.assertEqual(led["bytes"], on_disk, rel)
            self.assertIn("{:,} B".format(on_disk), d,
                          "the row must quote the size it measured, for %s" % rel)
            # ONE ARM AT A TIME. Before Phase B the first half was a records-per-line RATE, so a
            # firing row ALWAYS carried the byte reason too and this could assert it
            # unconditionally. Both halves are byte LEVELS now, so assert the reason for each arm
            # that actually fired and the absence of the one that did not, or the row could quote
            # a threshold nothing tested against.
            #
            # THE PARAGRAPH THAT STOOD HERE DESCRIBED A STATE THAT NO LONGER EXISTS, and it is
            # recorded rather than merely deleted because it is what made the stale assertion
            # below look reasonable. It said the two arms had "DIFFERENT thresholds -- the
            # one-read cap is the lower -- so a ledger can fire on the read arm alone, and this
            # repo's own CHANGELOG.md is in exactly that state." The threshold change falsified both halves:
            # the read arm is CLASS_A_FIRE_BYTES, which on this repo is BYTE-EQUAL to the
            # trimmer's default budget (196,608 == 196,608), so the arms move together and
            # CHANGELOG.md fires BOTH. The `else` branch just below is therefore unreachable on
            # self.REPO while those two constants remain equal -- it is kept because the
            # constants are independent by design and may diverge again, but it is NOT currently
            # a live guard, and the synthetic siblings are what cover that state today.
            if led["byte_fires"]:
                self.assertIn("{:,} B budget".format(tm["budget_bytes"]), d,
                              "a byte-arm breach must quote the budget, for %s" % rel)
            else:
                self.assertNotIn("B budget", d,
                                 "%s is under the byte budget; the row must not imply it is "
                                 "over one" % rel)
            if led["refused"]:
                # NOTE THE WORDING: the trim ADVISORY says "HARD REFUSAL"; the D4(b) RISK row says
                # "hard limit". Two different sentences in two different places, deliberately, and
                # asserting the risk row's phrasing here would have made this branch unfalsifiable.
                # No ledger in this repo is past 262,144 B today, so nothing would have caught it
                # -- test_the_refusal_advisory_says_nothing_is_delivered exercises it synthetically.
                self.assertIn("{:,} B HARD REFUSAL".format(md.READ_REFUSE_BYTES), d, rel)
                # THE THRESHOLD CHANGE EMPTIED THIS GUARD AND IT STAYED GREEN THAT WAY. It read
                # `assertNotIn("one-read budget", ...)`, which was the read arm's own wording
                # until the rewording; `collect_trim_metrics` has not emitted that substring
                # since (the only two sites are the D4(b) risk row, a different function), so the
                # guard could no longer fail for any producer. The PROPERTY it was defending is
                # live and still worth defending -- `refused` and `read_fires` are exclusive
                # branches, and a file getting both sentences gets two contradictory remedies --
                # so it is restated against the wording the branch actually emits now. This is
                # the same assertion test_the_refusal_advisory_says_nothing_is_delivered makes
                # synthetically; kept here too because that one cannot see the live population.
                self.assertNotIn("Class A archive threshold", d,
                                 "%s is past the hard refusal; it is not a merely-oversized "
                                 "file and must not also be described as one" % rel)
            elif led["read_fires"]:
                self.assertIn("{:,} B Class A archive threshold".format(md.CLASS_A_FIRE_BYTES),
                              d, rel)
                # THE HEADROOM IS PER-LEDGER, AND THAT IS THE POINT. The string this replaces was
                # a bare constant -- identical for every ledger, so it survived exactly the figure
                # swap this method's docstring says it exists to catch. `READ_REFUSE_BYTES -
                # on_disk` is a function of THIS ledger's own size, computed here from Path.stat()
                # rather than from the collector, so the two operands stay independent and a row
                # quoting another ledger's distance fails.
                # THE WHOLE CLAUSE, NOT THE HEADROOM ALONE. Stopping after the distance left the
                # DENOMINATOR it is a distance *to* asserted by nothing: a producer printing the
                # right headroom against the wrong stated boundary passed green (mutant M10).
                # Both figures are matched in one span so the pair has to agree.
                self.assertIn("within {:,} B of the {:,} B hard refusal".format(
                    md.READ_REFUSE_BYTES - on_disk, md.READ_REFUSE_BYTES), d, rel)
            self.assertTrue(led["read_fires"] or led["byte_fires"],
                            "a row was emitted for %s with neither arm firing" % rel)
            self.assertNotIn("{:,} B".format(
                next(v["bytes"] for k, v in by_path.items() if k != rel)), d,
                "the row must not quote the OTHER ledger's size")
            checked += 1
        self.assertEqual(checked, len(descs),
                         "every emitted row must have been checked, not just the first")

    def test_the_refusal_advisory_says_nothing_is_delivered(self):
        """The branch the live repo cannot reach: no ledger here is past 262,144 B, so the
        conditional in test_the_advisory_carries_the_numbers_that_were_measured would sit
        unfalsifiable without this. Exercised synthetically, and paired with the truncation case so
        it cannot pass by both branches emitting the same sentence."""
        p = self._sized("CHANGELOG.md", md.READ_REFUSE_BYTES + 2)
        descs, tm = self._descs(p)
        led = [l for l in tm["ledgers"] if l["path"] == "CHANGELOG.md"][0]
        self.assertTrue(led["refused"], "fixture: must be past the hard refusal")
        d = "\n".join(descs)
        self.assertIn("{:,} B HARD REFUSAL".format(md.READ_REFUSE_BYTES), d)
        self.assertIn("NO CONTENT AT ALL", d,
                      "the whole point of this branch is that the delivered prefix is empty")
        self.assertNotIn("Class A archive threshold", d,
                         "a refused file is not a merely-oversized one; emitting both gives one "
                         "file two contradictory remedies")
        # THIS CONTROL WAS RE-SIZED AND RE-WORDED. It used to sit at READ_CAP_BYTES + 2 and
        # grep for "one-read budget"; at the new arm that size emits NOTHING, so the control went
        # empty and the assertion failed -- correctly, because an empty control cannot show the two
        # branches are distinct. It now sits just past the Class A arm, where the non-refusal
        # branch does speak, and greps that branch's own new wording.
        under = self._sized("CHANGELOG.md", md.CLASS_A_FIRE_BYTES + 2)
        d2 = "\n".join(self._descs(under)[0])
        self.assertTrue(d2, "control: the non-refusal branch must actually emit something")
        self.assertIn("Class A archive threshold", d2,
                      "control: the truncation branch must be distinct")
        self.assertNotIn("HARD REFUSAL", d2)

    def test_the_named_tool_must_content_verify_not_merely_exist(self):
        """The detection contract is `.is_file()` AND a content check by regex, and dropping
        the second half survived the suite. A bare existence probe accepts an adopter's unrelated
        same-named script and then prints a command against it."""
        p = self._repo({
            "CHANGELOG.md": "# Changelog\n\n" + self._entries(6),
            "methodology_trim.py": "# an adopter's own script, nothing to do with ours\n",
        })
        self.assertTrue((p / "methodology_trim.py").is_file(), "fixture: the file must exist")
        self.assertIsNone(md.find_trim_tool(p),
                          "a same-named file with no TRIM_VERSION is not our tool")
        # Control: add the constant and it is found, so the None above is about CONTENT.
        (p / "methodology_trim.py").write_text('TRIM_VERSION = "1.2.3"\n')
        found = md.find_trim_tool(p)
        self.assertIsNotNone(found)
        self.assertEqual(found["version"], "1.2.3")

    def test_the_collected_tool_version_is_the_tools_own(self):
        """`tool_version` was collected and read by nothing -- falsifying it survived the suite.
        It is the field a future staleness check will key on, so it is pinned to the trimmer's
        real constant rather than left as decoration."""
        trim = _load_trimmer()
        _descs, tm = self._descs(self.REPO, expect_role="framework")
        self.assertEqual(tm["tool_version"], trim.TRIM_VERSION)
        self.assertEqual(tm["tool_path"], md.TRIM_TOOL_FRAMEWORK_REL)

    def test_risks_reemit_the_collector_verbatim(self):
        """assess_risks re-emits and does not re-decide, so there is one place to read to know
        what an operator was told."""
        m = md.collect_all(self.REPO)
        descs = {r["description"] for r in m["scores"]["risks"]}
        if not m["trim"]["signals"]:
            self.skipTest("this repo's own trim trigger is not currently firing on either "
                          "ledger (S64 cleared HANDOFFS.md's; CHANGELOG.md's was already clear) "
                          "-- this test's fixture precondition needs a live over-budget ledger "
                          "and will run again once one exists")
        for _sev, d in m["trim"]["signals"]:
            self.assertIn(d, descs)

    def test_score_is_untouched_by_the_new_rows(self):
        """The row is advisory. Risks feed the displayed worst-severity, never the 0-100 score.

        GUARD-THE-GUARD, and labelled: this is the ONE test in this class that also passes
        against the pre-change scanner, because score_health never read `trim` there either. A
        green absence-assertion is not coverage, so it earns its place by
        producer mutation instead -- adding `- 2 * len(metrics["trim"]["signals"])` to
        score_health's total was applied and observed to fail this test (72 != 68). It is a
        forward tripwire against a later edit quietly turning an advisory into a penalty."""
        m = md.collect_all(self.REPO)
        before = m["scores"]["health"]["total"]
        stripped = dict(m)
        stripped["trim"] = {"signals": [], "ledgers": [], "tool_present": False,
                            "tool_path": None, "tool_version": None, "budget_bytes": None}
        self.assertEqual(md.score_health(stripped)["total"], before)


class TestPhaseC1ReadCapClasses(unittest.TestCase):
    """The partition change -- the watched population
    becomes TWO CLASSES, and each guard finally claims something true of the files it watches.

    WHAT THIS CHANGE DELIBERATELY DOES NOT DO: move a threshold. The design says option A1
    "changes no threshold and cannot degenerate anything" and its first criterion names
    none; a summary table that reads as if two thresholds move is the summary
    that drifted. The threshold move is the next change, which must be bundled with the budget change
    (`DEFAULT_BUDGET_BYTES`) or it is inert. So the population assertion below is not a
    formality -- it is the phase's central claim, and it is asserted against a FROZEN literal
    rather than against the module's own union, which would be an identity.

    NOT RED-FIRST, and labelled as such per this file's docstring rule: `READ_CAP_CLASS_A`,
    `READ_CAP_CLASS_B` and `read_cap_class` do not exist before this phase, so every assertion
    here fails with AttributeError against the pre-change scanner -- which proves the names are
    new, not that the behaviour they pin was wrong. What earns these tests their place is
    MUTATION: each one below states, in its own docstring, the producer mutant it kills.
    """

    REPO = Path(HERE).parent

    # The six names as they stood before this change, copied here as a FROZEN literal and
    # deliberately never derived from the module. Comparing the module's union against the
    # module's own parts would be an identity that cannot fail.
    POPULATION_AT_PHASE_B = frozenset((
        "SESSION_NOTES.md", "CHANGELOG.md", "HANDOFFS.md",
        "BACKLOG.md", "docs/BACKLOG.md", "docs/planning/BACKLOG.md",
    ))

    # --- the partition --------------------------------------------------------------------------

    def test_every_watched_name_resolves_to_exactly_one_class(self):
        """The first DONE criterion, asserted three ways because a partition can fail
        in three directions: overlap, gap, and a classifier that disagrees with the sets it reads.

        ⚠ THE COVERAGE HALF IS ASSERTED AGAINST THE FROZEN POPULATION, NEVER AGAINST
        `READ_CAP_WATCHED`, AND THAT IS NOT A STYLE CHOICE. The union is DERIVED from the two
        classes, so `assertEqual(A | B, READ_CAP_WATCHED)` expands to `A | B == A | B` — an
        identity that cannot fail. The first draft of this test asserted exactly
        that, and the mutation round is what caught it: narrowing a class (M1, M8) shrinks the
        union in lockstep, so the tautological form stayed green on both while claiming to be
        the assertion that covers them. Compare to a literal that does not move.

        KILLS: `read_cap_class` returning a constant or forgetting a branch (M5, M6); a name
        listed in both classes (M10); a name dropped from a class, which under a derived union
        leaves it in NEITHER (M1, M8)."""
        self.assertEqual(md.READ_CAP_CLASS_A & md.READ_CAP_CLASS_B, frozenset(),
                         "the classes must be DISJOINT: a name in both gets two verdicts")
        self.assertEqual(set(md.READ_CAP_CLASS_A | md.READ_CAP_CLASS_B),
                         set(self.POPULATION_AT_PHASE_B),
                         "the classes must COVER the population: a name that fell out of both is "
                         "no longer watched at all, and under a derived union nothing else says so")
        self.assertTrue(md.READ_CAP_CLASS_A, "fixture check: Class A must be non-empty")
        self.assertTrue(md.READ_CAP_CLASS_B, "fixture check: Class B must be non-empty")
        for name in sorted(self.POPULATION_AT_PHASE_B):
            with self.subTest(name=name):
                self.assertIn(md.read_cap_class(name), ("A", "B"))
                self.assertEqual(md.read_cap_class(name) == "A", name in md.READ_CAP_CLASS_A)
                self.assertEqual(md.read_cap_class(name) == "B", name in md.READ_CAP_CLASS_B)
        self.assertIsNone(md.read_cap_class("chap07.md"),
                          "an unwatched name must classify as None, not fall into a default class")
        self.assertIsNone(md.read_cap_class("SESSION_RUNNER.md"),
                          "a TRACKED dest is not watched at all, and must not acquire a class by "
                          "the classifier being permissive")

    def test_the_split_repartitioned_the_population_without_changing_it(self):
        """PHASE C1'S CENTRAL CLAIM. Against a frozen literal of the six names as Phase B left
        them -- not against the module's own union, which cannot disagree with itself.

        KILLS: any add or drop, including the two `docs/**` locations this phase was required to
        disposition. Dropping one is a defensible decision; doing it SILENTLY, inside a phase
        whose plan says it cannot degenerate anything, is not."""
        self.assertEqual(set(md.READ_CAP_WATCHED), set(self.POPULATION_AT_PHASE_B))

    def test_the_union_is_derived_rather_than_a_third_spelling_of_the_six_names(self):
        """The claim above is only PROVABLE while `READ_CAP_WATCHED` is computed from the classes.
        Re-listing the names as a literal would leave the population correct and the guarantee
        gone -- the two could then drift apart and only this assertion would notice.

        Read out of the SOURCE TEXT, because there is no runtime difference between a derived
        frozenset and an identical literal one -- which is exactly why it needs asserting.

        KILLS: `READ_CAP_WATCHED = frozenset((...six names...))` restored beside the classes."""
        src = Path(STARTER_PY).read_text(encoding="utf-8")
        m = re.search(r"(?m)^READ_CAP_WATCHED\s*=\s*(.+)$", src)
        self.assertIsNotNone(m, "the module must still declare READ_CAP_WATCHED at module scope")
        self.assertRegex(m.group(1).strip(), r"^READ_CAP_CLASS_A\s*\|\s*READ_CAP_CLASS_B$",
                         "READ_CAP_WATCHED must stay DERIVED from the two classes; a literal "
                         "re-listing makes 'the population did not change' unprovable")

    # --- the pin: class membership is asserted against the trimmer, never restated ---------------

    def test_class_a_is_pinned_to_the_trimmers_ledgers_table(self):
        """The second DONE criterion: a canonical test must FAIL if a name is added
        to `LEDGERS` without moving class. This is that test.

        The direction matters. Class A is DECLARED,
        not derived from `LEDGERS` -- derivation would make widening the trimmer silently
        reassign a file's class, which is the failure the dragon names. Declaring it and pinning
        it here means the widening turns this red and a human moves the name deliberately.

        Operands are independent: one side is this module's constant, the other is the trimmer's
        own executed module. This is the pattern
        test_grammars_agree_with_the_trimmer_config_table established, applied to the class.

        KILLS: moving CHANGELOG.md or HANDOFFS.md to Class B; adding a third name to Class A."""
        trim = _load_trimmer()
        self.assertEqual(sorted(n.rsplit("/", 1)[-1] for n in md.READ_CAP_CLASS_A),
                         sorted(trim.LEDGERS),
                         "Class A IS the set of watched names the trimmer can act on. If LEDGERS "
                         "gained or lost a key, move the name between the classes here "
                         "deliberately -- and re-read plan section 10 dragon 6 first")

    def test_class_b_is_exactly_the_set_the_trimmer_refuses(self):
        """The other half of the pin, and it fails independently. Without it, a name added to BOTH
        `LEDGERS` and Class B would be caught only by the A-side assertion above -- and a future
        edit that relaxes that one would leave nothing watching this.

        The trimmer's refusal is asserted by CALLING it, not by reading its table twice: for each
        Class B basename the config lookup must come back empty, which is the `NO_CONFIG` answer
        the plan and the module comment both cite as the reason these files get no trim row.

        ⚠ THE NON-EMPTY GUARD BELOW IS LOAD-BEARING, not decoration: this is a subTest loop over
        `READ_CAP_CLASS_B`, and a loop over an empty sequence runs its body ZERO times and passes.
        Emptying Class B would otherwise be caught only by a SIBLING test, and a test that depends
        on its neighbour for its own non-vacuity is one edit away from asserting nothing.

        KILLS: a Class B name that also acquires a `LEDGERS` entry — the case where the trimmer is
        widened and this file is not. It does NOT independently kill a name PROMOTED to Class A;
        that one is the A-side pin's, and an earlier draft of this docstring claimed it here."""
        trim = _load_trimmer()
        self.assertTrue(md.READ_CAP_CLASS_B,
                        "fixture check: Class B must be non-empty, or the loop below runs zero "
                        "times and this test passes without asserting anything")
        for name in sorted(md.READ_CAP_CLASS_B):
            with self.subTest(name=name):
                self.assertIsNone(trim.LEDGERS.get(name.rsplit("/", 1)[-1]),
                                  "a Class B name must be one the trimmer has NO config for; "
                                  "naming the trimmer as its remedy would point an adopter at a "
                                  "refusal")

    # --- the class is what the trim row is now selected by ---------------------------------------

    def test_the_trim_row_population_is_class_a_at_the_constants_and_at_the_output(self):
        """The class and the old basename filter select the same two names today. That is the
        precondition for the partition changing no behaviour, so it is asserted rather than assumed --
        and asserted at BOTH ends, because agreeing at the constants says nothing about what the
        collector actually emitted.

        GUARD-THE-GUARD on the output half: it also passes against the pre-change collector, since
        the two filters coincide. Its companion below is the one that can tell them apart."""
        for name in sorted(md.READ_CAP_WATCHED):
            with self.subTest(name=name):
                self.assertEqual(md.read_cap_class(name) == "A",
                                 name.rsplit("/", 1)[-1] in md.TRIM_GRAMMARS,
                                 "class membership and grammar membership must still coincide; "
                                 "if they have diverged, the trim row's population changed and "
                                 "Phase C1's no-behaviour-change claim no longer holds")
        rows = {l["path"] for l in md.collect_all(self.REPO)["trim"]["ledgers"]}
        self.assertTrue(rows, "fixture check: this repo must produce at least one trim row, or "
                              "the assertion below is vacuous")
        self.assertTrue(rows <= set(md.READ_CAP_CLASS_A),
                        "every emitted trim row must be a Class A file: %r" % sorted(rows))

    def test_a_watched_name_in_no_class_gets_no_trim_row_even_when_its_basename_matches(self):
        """THE ONE ASSERTION THAT CAN TELL THE TWO FILTERS APART — and it does so at the FUNCTION'S
        contract, not in production. Said plainly, because an earlier draft of this docstring did
        not: `collect_file_metrics` only ever admits exact members of `READ_CAP_WATCHED` into
        `read_cap_watch`, so through `collect_all` the old and new filters are equivalent on every
        input that can exist, and the partition changed no production behaviour. What this test proves
        is that `collect_trim_metrics` honours its own contract — it takes `files` as a PARAMETER,
        so a caller can hand it a name `collect_all` never would, and the function should answer NO
        rather than guess from the filename. Read the kill of the revert-to-basename mutant that
        way, and not as evidence of a live bug.

        `docs/CHANGELOG.md` has a basename the trimmer knows a grammar for, and no class. Under
        the old `basename in TRIM_GRAMMARS` filter it would be handed a trim row -- naming
        `--check` against a path this scanner never decided to watch. Under class membership it is
        skipped, because `read_cap_class` returns None and an unclassified file has no verdict to
        emit. The class system forces the decision instead of guessing it from the filename.

        No monkeypatching: `collect_trim_metrics` takes its population from the `files` dict it is
        handed, so the case is constructed directly.

        KILLS: reverting the filter to `basename in TRIM_GRAMMARS`."""
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        p = Path(td.name)
        (p / "SESSION_RUNNER.md").write_text("# Session Runner\n" + "step\n" * 40)
        big = "x\n" * ((md.READ_CAP_BYTES + 100) // 2)
        (p / "docs").mkdir()
        (p / "docs" / "CHANGELOG.md").write_text(big)
        (p / "CHANGELOG.md").write_text(big)

        self.assertIsNone(md.read_cap_class("docs/CHANGELOG.md"),
                          "fixture check: docs/CHANGELOG.md must be unclassified, or this test is "
                          "not exercising the case it was written for")
        self.assertIn("CHANGELOG.md", md.TRIM_GRAMMARS,
                      "fixture check: the basename must be one the trimmer knows, or the old "
                      "filter would have skipped it too and the two agree vacuously")

        unclassified = md.collect_trim_metrics(
            p, {"read_cap_watch": [{"path": "docs/CHANGELOG.md", "lines": 9, "bytes": None}]})
        self.assertEqual([l["path"] for l in unclassified["ledgers"]], [],
                         "an unclassified watched name must get NO trim row")
        self.assertEqual(unclassified["signals"], [])

        # Positive control: the same harness, one directory up, does produce the row -- so the
        # empty result above is the filter working, not the fixture failing to reach the code.
        #
        # ⚠ THE THRESHOLD CHANGE HAD TO GROW THIS CONTROL'S FILE. It used to inherit whatever size the fixture
        # happened to have, which fired the old 65,536 B arm; at 196,608 it went silent and this
        # assertion failed -- correctly. A control that does not fire proves nothing about the
        # branch it is controlling for, so the size is now set EXPLICITLY from the constant rather
        # than left to the fixture, and it moves with any future retune.
        (p / "CHANGELOG.md").write_bytes(b"x" * (md.CLASS_A_FIRE_BYTES + 1))
        classified = md.collect_trim_metrics(
            p, {"read_cap_watch": [{"path": "CHANGELOG.md", "lines": 9, "bytes": None}]})
        self.assertEqual([l["path"] for l in classified["ledgers"]], ["CHANGELOG.md"])
        self.assertTrue(classified["signals"], "the control must actually fire")

    # --- the disposition, and the evidence it rests on --------------------------------------------

    def test_the_two_docs_backlog_locations_have_no_protocol_basis(self):
        """The third DONE criterion is a DECISION -- keep or drop, but decide it. The
        decision was KEEP, and this pins the evidence the decision rests on so that the reasoning
        recorded beside the classes cannot quietly become false.

        The claim: neither `docs/BACKLOG.md` nor `docs/planning/BACKLOG.md` is named as a file to
        read anywhere in the protocol, so both are watched by analogy to the root basename -- a
        weaker warrant than the other four names have, and one worth saying out loud rather than
        letting a reader assume parity.

        The net is the WHOLE distributed .md corpus taken off bin/_manifest.py's SOURCE column,
        not just the two protocol files: a claim about "no distributed file" cannot be settled by
        a net that misses most of them. The net once had one hit, a learning row
        citing this repo's own backlog as a WORKED EXAMPLE (evidence ABOUT the file, not an
        instruction to open it), allowed for by name. That row has left the distributed corpus,
        so both locations now read [] -- which a net that read nothing
        would also return, so the root basename's own hits are asserted non-empty first.

        THIS TEST IS SUPPOSED TO GO RED IF THE PROTOCOL CHANGES. That is its job: the day a runner
        edit gives one of these locations a real basis, the KEEP decision has a stronger warrant
        than "by analogy" and the comment beside the classes must be rewritten to say so."""
        root = Path(HERE).parent
        sys.path.insert(0, str(root / "bin"))
        try:
            import _manifest
            distributed_md = [r[0] for r in _manifest.DISTRIBUTION if r[0].endswith(".md")]
        finally:
            sys.path.remove(str(root / "bin"))
        self.assertGreater(len(distributed_md), 15,
                           "fixture check: the distributed .md corpus must be the wide net, not a "
                           "handful of files")

        for protocol_file in ("starter-kit/SESSION_RUNNER.md", "starter-kit/SAFEGUARDS.md"):
            text = (root / protocol_file).read_text(encoding="utf-8")
            self.assertIn("BACKLOG.md", text,
                          "fixture check: %s must still name the ROOT backlog, or the absence "
                          "assertions below are trivially true" % protocol_file)
            for loc in ("docs/BACKLOG.md", "docs/planning/BACKLOG.md"):
                with self.subTest(file=protocol_file, loc=loc):
                    self.assertNotIn(loc, text)

        hits = {loc: sorted(f for f in distributed_md
                            if loc in (root / f).read_text(encoding="utf-8"))
                for loc in ("BACKLOG.md", "docs/BACKLOG.md", "docs/planning/BACKLOG.md")}
        self.assertIn("starter-kit/SESSION_RUNNER.md", hits["BACKLOG.md"],
                      "fixture check: the net must read the corpus -- the runner names the ROOT "
                      "backlog, so an empty hit list here means nothing below was read")
        self.assertEqual(hits["docs/BACKLOG.md"], [],
                         "docs/BACKLOG.md is named nowhere in the distributed corpus; if that has "
                         "changed, its disposition is no longer 'by analogy'")
        self.assertEqual(hits["docs/planning/BACKLOG.md"], [],
                         "docs/planning/BACKLOG.md is named nowhere in the distributed corpus since "
                         "fork Learning #26 left it (S176); if that has changed, revisit the comment "
                         "beside READ_CAP_CLASS_A")

    # --- the phase's own boundary -----------------------------------------------------------------

    def test_phase_c2_moved_exactly_the_ratified_thresholds_and_nothing_else(self):
        """SUCCESSOR TO THE TEST THAT ASSERTED THE CLASSES HAD NO THRESHOLDS, converted deliberately.

        The earlier version asserted the classes had acquired NO thresholds, because attaching one was
        a later step's job and would be inert before the budget was settled (`DEFAULT_BUDGET_BYTES`). The later step did both
        in one change, so the guard flips from "none exist" to "exactly these exist".

        ⚠ AND THE EARLIER VERSION HAD A HOLE THAT THE LATER CHANGE WALKED STRAIGHT THROUGH — recorded rather than
        quietly fixed, because it is the failure this class already ships two learnings about.
        Its docstring claimed a namespace check "which no per-class threshold can slip past
        WHATEVER IT IS CALLED". It was implemented as
        `[n for n in dir(md) if n.startswith("READ_CAP_CLASS")]` — one prefix. The later constants are
        named `CLASS_A_FIRE_BYTES` / `CLASS_A_STOP_BYTES`, chosen for what they guard rather than
        to evade anything, and the guard stayed GREEN through the very change it was written to
        gate. A guard you can walk around by picking a name has coverage that is a property of the
        change, not of the codebase. The check below is a SUBSTRING sweep over the whole namespace
        asserting the EXACT expected set, which is what the earlier docstring already claimed.

        KILLS: any of the six pinned literals moving; any further per-class constant landing under
        any spelling without a session deciding to add it here."""
        # FROZEN LITERALS on both sides. `READ_CAP_BYTES` is defined in this module as
        # `int(READ_CAP_TOKENS * MIN_BYTES_PER_TOKEN)`, so asserting that identity would assert
        # nothing.
        self.assertEqual(md.READ_CAP_BYTES, 56_750,
                         "C2 did NOT move the one-read budget. It is a measured harness fact, not "
                         "a policy knob; the Class A arm is a separate constant beside it")
        self.assertEqual(md.READ_REFUSE_BYTES, 262_144, "the hard refusal did not move either")
        self.assertEqual(md.READ_CAP_TOKENS, 25_000)
        self.assertEqual(md.MIN_BYTES_PER_TOKEN, 2.27)
        self.assertEqual(md.CLASS_A_FIRE_BYTES, 196_608, "192 KiB, ratified at Phase C2")
        self.assertEqual(md.CLASS_A_STOP_BYTES, 98_304, "96 KiB, ratified at Phase C2")
        self.assertLess(md.CLASS_A_FIRE_BYTES, md.READ_REFUSE_BYTES,
                        "plan §3 caveat 1: the Class A arm fires BELOW the hard refusal, never at "
                        "it — a trigger set at the refusal parks the file on the cliff edge")
        self.assertGreater(md.CLASS_A_FIRE_BYTES, md.READ_CAP_BYTES,
                           "control: the Class A arm must be LOOSER than the one-read cap, or the "
                           "phase changed nothing")

        # The population is still two frozen sets and still carries no threshold of its own.
        class_names = sorted(n for n in dir(md) if n.startswith("READ_CAP_CLASS"))
        self.assertEqual(class_names, ["READ_CAP_CLASS_A", "READ_CAP_CLASS_B"])
        for name in class_names:
            self.assertIsInstance(getattr(md, name), frozenset,
                                  "%s must stay a set of names; a threshold smuggled in as a dict "
                                  "value would pass the name check above" % name)

        # THE WIDENED GUARD — substring, not prefix, over every public module-level name. The
        # expected set is exhaustive and sorted, so an addition fails rather than being absorbed.
        per_class = sorted(n for n in dir(md)
                           if not n.startswith("_") and ("CLASS_A" in n or "CLASS_B" in n))
        self.assertEqual(per_class,
                         ["CLASS_A_FIRE_BYTES", "CLASS_A_STOP_BYTES",
                          "READ_CAP_CLASS_A", "READ_CAP_CLASS_B"],
                         "a per-class name landed that no phase ratified, or one was renamed. "
                         "Update this list in the session that adds it, and say why: %r"
                         % per_class)

class TestPhaseC2PerClassRiskRows(unittest.TestCase):
    """The DASHBOARD half of the threshold change — the two threshold sites an earlier inventory left owned by
    no one, and which were fenced rather than resolved.

    WHY THIS IS IN THE CHANGE AT ALL, since its criterion names only trimmer-side things. Because the threshold change
    is the change that CREATES the disagreement: move the trimmer's trigger and leave this file,
    and `collect_trim_metrics` keeps emitting "the archive trigger fires; run `--check`" beside a
    `--check` that reports it does not. The row would name a command whose output contradicts it —
    which the comment above that remedy says the wording exists to avoid. The change was widened
    to cover both sites; this class is that half.

    ⚠ CLASS B CANNOT BE EXERCISED BY THIS REPOSITORY. Its only Class B file within the watched set
    is `docs/planning/BACKLOG.md`, which is comfortably under the cap, so the Class B branch of the
    risk row is unreachable through `collect_all` here. Every Class B assertion below therefore
    drives `assess_risks` with a CONSTRUCTED metrics dict. That is a real limitation, not a
    workaround: it means the Class B row is covered by unit test only and has never been observed
    on a live tree in this repo.
    """

    @classmethod
    def setUpClass(cls):
        """A REAL scan supplies the metrics shape; only `read_cap_watch` is substituted.

        The first draft hand-built the dict and it raised KeyError on `tests.test_file_count` --
        assess_risks reads far more of the structure than the D4(b) rows do. Hand-shaping it would
        have coupled this class to every future key assess_risks learns to read, and the failure
        mode is an ERROR that looks like a product bug rather than a fixture one."""
        cls._td = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._td.cleanup)
        p = Path(cls._td.name)
        subprocess.run(["git", "init", "-q", str(p)], check=True)
        (p / "SESSION_RUNNER.md").write_text("# r\n")
        (p / "README.md").write_text("# fx\n")
        subprocess.run(["git", "-C", str(p), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(p), "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-q", "-m", "init"], check=True)
        cls._base = md.collect_all(p)
        cls._base["trim"] = {"signals": []}      # the trim row is asserted separately, below

    @classmethod
    def _metrics(cls, path, size, lines=100):
        m = copy.deepcopy(cls._base)
        m["files"]["read_cap_watch"] = [{"path": path, "bytes": size, "lines": lines}]
        return m

    def test_FIXTURE_the_base_scan_emits_no_read_cap_row_of_its_own(self):
        """Control. If the borrowed scan already carried a read-cap row, every assertion below
        would be reading someone else's row and would pass for the wrong reason."""
        rows = [r for r in md.assess_risks(copy.deepcopy(self._base))
                if "read cap" in r["description"]]
        self.assertEqual(rows, [], "the fixture repo must be clean of read-cap rows: %r" % rows)

    def _rows_for(self, path, size):
        rows = md.assess_risks(self._metrics(path, size))
        return [r for r in rows if path in r["description"] and "read cap" in r["description"]]

    def test_a_class_A_ledger_over_the_cap_is_LOW_and_says_no_action_is_expected(self):
        """The fleet-visible half of this change. A Class A ledger between the one-read cap and the
        archive threshold is the ADJUDICATED case: truncation is ordered and
        the file is newest-on-top, so what drops is the oldest records. Reporting that as HIGH
        taught a reader to ignore the row."""
        rows = self._rows_for("HANDOFFS.md", md.READ_CAP_BYTES + 1)
        self.assertEqual(len(rows), 1, "exactly one read-cap row per watched file: %r" % rows)
        self.assertEqual(rows[0]["severity"], "low",
                         "a Class A ledger over the cap but under the archive threshold is "
                         "expected, not a fault")
        self.assertIn("CLASS A", rows[0]["description"])
        self.assertIn("NO ACTION IS EXPECTED", rows[0]["description"])
        self.assertIn("{:,}".format(md.CLASS_A_FIRE_BYTES), rows[0]["description"],
                      "the row must name the threshold that WOULD matter, so the reader can see "
                      "how far away it is")

    def test_a_class_B_file_over_the_cap_is_still_HIGH_and_says_why(self):
        """Class B rows STAY, and still say why. This is the design's "make the rows DIFFERENT, not
        delete one" — the severity and the row's existence are what this test is for.

        ⚠ THE "WHY" IT PINS CHANGED, DELIBERATELY, AND THE ASSERTION WAS REPLACED RATHER
        THAN REMOVED. It used to assert `"NO_CONFIG"` was present — i.e. that the row told the
        reader the trimmer had no config for this file. That claim was never evaluated by this
        module and is false in a tree that widened `LEDGERS`, so the row stopped making it; see
        `test_the_class_B_row_makes_NO_CLAIM_about_any_trimmer_config` below, which now forbids it.
        What survives unchanged is everything this test was really protecting: the row exists, it
        is HIGH, and it names the class. Deleting the assertion would have left the "says why" in
        the test's own name unbacked, so it is re-pointed at the access-path reason instead."""
        rows = self._rows_for("SESSION_NOTES.md", md.READ_CAP_BYTES + 1)
        self.assertEqual(len(rows), 1, "%r" % rows)
        self.assertEqual(rows[0]["severity"], "high")
        self.assertIn("CLASS B", rows[0]["description"])
        self.assertIn("the instructed access path IS the file", rows[0]["description"],
                      "the row must still say WHY being over the cap matters for this class — "
                      "that the protocol sends the reader at the file itself")

    def test_the_class_B_row_makes_NO_CLAIM_about_any_trimmer_config(self):
        """The row may assert only what the emitter EVALUATED, and it evaluates no trimmer.

        It used to print *"the trimmer answers NO_CONFIG for it"* — a fact about a NEIGHBOURING
        TOOL's configuration, read from nothing, in a module whose class sets are frozen literals.
        That sentence is true here only because `LEDGERS` and the declared classes happen to
        coincide, and a canonical test pins that coincidence. **It is not true in a tree that
        widened `LEDGERS`**, and this module is DISTRIBUTED to exactly such trees, where no test
        pins anything (`tools/test_methodology_dashboard.py` is absent from `bin/_manifest.py`).

        This does NOT relax the declared/derived split — see the two class pins above, unchanged.
        The class stays declared; the PROSE stops claiming the trimmer's answer.

        KILLS: re-introducing any mention of the trimmer or its config into this row on a tree
        where nothing was read -- this fixture carries no trimmer. The probe appends a remedy ONLY
        where the scanned project's own trimmer SOURCE declares the file;
        `TestBL88P2TrimmerSourceProbe` pins that arm, and pins this one byte-identical to the unprobed row."""
        for name in sorted(md.READ_CAP_CLASS_B):
            with self.subTest(name=name):
                rows = self._rows_for(name, md.READ_CAP_BYTES + 1)
                self.assertEqual(len(rows), 1, "%r" % rows)
                d = rows[0]["description"]
                self.assertNotIn("NO_CONFIG", d,
                                 "the row asserts a fact about the trimmer's config that this "
                                 "module never reads")
                self.assertNotIn("the trimmer", d,
                                 "no claim about the trimmer belongs in a row that never asks it")

    def test_the_backlog_justification_is_printed_ONLY_for_the_backlogs(self):
        """*"A backlog's bottom items are as live as its top ones"* is a reason about BACKLOGS.

        The module comment above `READ_CAP_CLASS_B` already records that carrying it to every
        Class B name is false of `SESSION_NOTES.md` — whose instructed read target is the ACTIVE
        TASK section at the TOP — and states the true weaker form: nothing ENFORCES it. That
        correction reached the comment and never reached the row. This is that, closed.

        Measured across 12 fleet repos: every `SESSION_NOTES.md` carrying an
        `## ACTIVE TASK` heading has it at byte 132-9,490, inside READ_CAP_BYTES in all of them;
        one project has no such heading at all, which is the case the weaker form is for.

        KILLS: printing the backlog clause for SESSION_NOTES.md; dropping it from the backlogs."""
        clause = "bottom items are as live as its top ones"
        for name in sorted(md.READ_CAP_CLASS_B):
            with self.subTest(name=name):
                d = self._rows_for(name, md.READ_CAP_BYTES + 1)[0]["description"]
                if name in md._BACKLOG_LOCATIONS:
                    self.assertIn(clause, d, "a backlog's row loses the reason that IS true of it")
                else:
                    self.assertNotIn(clause, d,
                                     "%s is not a backlog; its bottom is its OLDEST record" % name)
                    self.assertIn("ENFORCES", d,
                                  "the weaker form the module comment settled must reach the row")

    def test_THE_DISCRIMINATOR_same_size_opposite_severity(self):
        """The pair above proves little separately — a rule that returned `low` for everything
        would pass the first, and one that returned `high` for everything would pass the second.
        Identical bytes, different class, opposite severity is what proves the branch is live."""
        size = md.READ_CAP_BYTES + 1
        a = self._rows_for("HANDOFFS.md", size)
        b = self._rows_for("SESSION_NOTES.md", size)
        self.assertEqual(len(a), 1); self.assertEqual(len(b), 1)
        self.assertNotEqual(a[0]["severity"], b[0]["severity"],
                            "same size, different class, and the severity did not move — the "
                            "per-class branch is not wired")
        self.assertEqual((a[0]["severity"], b[0]["severity"]), ("low", "high"))

    def test_the_hard_refusal_row_is_UNCHANGED_and_still_HIGH_for_BOTH_classes(self):
        """The change relaxed nothing past READ_REFUSE_BYTES. There the prefix stops existing, the
        consolation that makes truncation survivable is FALSE, and ordering buys neither class
        anything — so this row must not have acquired a class."""
        for path in ("HANDOFFS.md", "SESSION_NOTES.md"):
            rows = md.assess_risks(self._metrics(path, md.READ_REFUSE_BYTES + 1))
            hits = [r for r in rows if path in r["description"] and "hard limit" in r["description"]]
            self.assertEqual(len(hits), 1, "%s: %r" % (path, rows))
            self.assertEqual(hits[0]["severity"], "high",
                             "%s past the hard refusal must stay HIGH whatever its class" % path)
            self.assertIn("NO CONTENT AT ALL", hits[0]["description"])

    def test_a_class_A_ledger_UNDER_the_cap_emits_no_read_cap_row_at_all(self):
        """Control against the severity drop becoming a row that is simply always present."""
        self.assertEqual(self._rows_for("HANDOFFS.md", md.READ_CAP_BYTES - 1), [])

    def test_collect_trim_metrics_keys_on_the_class_A_arm_not_the_one_read_cap(self):
        """The SECOND unowned site. This collector re-implements the trimmer's trigger — it must,
        because it reports on repos where the tool is not installed — so a threshold that moved in
        the trimmer alone leaves it contradicting `--check`.

        Driven at three sizes across both thresholds rather than at one, because a single sample
        cannot distinguish "keys on the new arm" from "always False"."""
        files = {"read_cap_watch": [{"path": "CHANGELOG.md", "bytes": 0, "lines": 1}]}
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            (repo / "SESSION_RUNNER.md").write_text("# r\n")
            for size, expected in ((md.READ_CAP_BYTES + 1, False),
                                   (md.CLASS_A_FIRE_BYTES, False),
                                   (md.CLASS_A_FIRE_BYTES + 1, True)):
                (repo / "CHANGELOG.md").write_bytes(b"x" * size)
                out = md.collect_trim_metrics(repo, files, role="framework")
                led = [l for l in out["ledgers"] if l["path"] == "CHANGELOG.md"]
                self.assertEqual(len(led), 1, "%d: %r" % (size, out["ledgers"]))
                self.assertEqual(led[0]["read_fires"], expected,
                                 "at %s B the read arm must be %s — it keys on "
                                 "CLASS_A_FIRE_BYTES (%s), not READ_CAP_BYTES (%s)"
                                 % ("{:,}".format(size), expected,
                                    "{:,}".format(md.CLASS_A_FIRE_BYTES),
                                    "{:,}".format(md.READ_CAP_BYTES)))


# The Class B over-cap row before the trimmer-source probe, FROZEN. Captured from the module before
# the probe existed, for a watched file of READ_CAP_BYTES + 1 bytes and 100 lines, with nothing evaluated
# about any trimmer. A LITERAL on purpose: the criterion -- "a probe that finds nothing or
# fails must leave the row byte-identical to the unprobed row" -- is a claim about that OUTPUT, and a reference
# computed by the code under test would only compare the new code with itself.
# If a ratified constant these rows print moves (READ_CAP_BYTES, READ_CAP_TOKENS,
# MIN_BYTES_PER_TOKEN), regenerate them from the module as it stood before that change.
_P1_CLASS_B_ROWS = {
    'BACKLOG.md': (
        'BACKLOG.md is 56,751 B (100 lines) — past the 56,750 B one-read budget for the agent'
        ' read cap, which is denominated in tokens (25,000) and converted here at the densest'
        ' content measured (2.27 B/token). A session reading it whole gets a PARTIAL view — '
        'truncated to the prefix that fits the token cap, and it SAYS SO in a banner naming '
        'the true length, so the failure is loud rather than silent; an explicit line range '
        'spanning the excess errors outright, returning nothing. This is a CLASS B file and '
        "the instructed access path IS the file: a backlog's bottom items are as live as its "
        'top ones, so what truncates may be open work, and you are told THAT something was '
        'cut, never WHAT'
    ),
    'SESSION_NOTES.md': (
        'SESSION_NOTES.md is 56,751 B (100 lines) — past the 56,750 B one-read budget for the'
        ' agent read cap, which is denominated in tokens (25,000) and converted here at the '
        'densest content measured (2.27 B/token). A session reading it whole gets a PARTIAL '
        'view — truncated to the prefix that fits the token cap, and it SAYS SO in a banner '
        'naming the true length, so the failure is loud rather than silent; an explicit line '
        'range spanning the excess errors outright, returning nothing. This is a CLASS B file'
        ' and the instructed access path IS the file: nothing ENFORCES that the part you need'
        ' is inside that prefix — the protocol says to focus on the ACTIVE TASK section at '
        'the top and the seed puts it there, but no check holds it there, and a file carrying'
        ' no such heading has no ordering to rely on, and you are told THAT something was '
        'cut, never WHAT'
    ),
    'docs/BACKLOG.md': (
        'docs/BACKLOG.md is 56,751 B (100 lines) — past the 56,750 B one-read budget for the '
        'agent read cap, which is denominated in tokens (25,000) and converted here at the '
        'densest content measured (2.27 B/token). A session reading it whole gets a PARTIAL '
        'view — truncated to the prefix that fits the token cap, and it SAYS SO in a banner '
        'naming the true length, so the failure is loud rather than silent; an explicit line '
        'range spanning the excess errors outright, returning nothing. This is a CLASS B file'
        " and the instructed access path IS the file: a backlog's bottom items are as live as"
        ' its top ones, so what truncates may be open work, and you are told THAT something '
        'was cut, never WHAT'
    ),
    'docs/planning/BACKLOG.md': (
        'docs/planning/BACKLOG.md is 56,751 B (100 lines) — past the 56,750 B one-read budget'
        ' for the agent read cap, which is denominated in tokens (25,000) and converted here '
        'at the densest content measured (2.27 B/token). A session reading it whole gets a '
        'PARTIAL view — truncated to the prefix that fits the token cap, and it SAYS SO in a '
        'banner naming the true length, so the failure is loud rather than silent; an '
        'explicit line range spanning the excess errors outright, returning nothing. This is '
        "a CLASS B file and the instructed access path IS the file: a backlog's bottom items "
        'are as live as its top ones, so what truncates may be open work, and you are told '
        'THAT something was cut, never WHAT'
    ),
}

# The sentence the probe appends when -- and only when -- the scanned project's own trimmer SOURCE declares
# a LEDGERS entry for the file's basename. Spelled here independently of the module's own format
# string, for the same reason as the literal above.
_P2_REMEDY = (". BUT THIS PROJECT HAS A REMEDY: its own `{tool}` declares a `LEDGERS` entry for "
              "`{base}` (read from its source, never run), so run `python3 {tool} --file {path} "
              "--check` for the full report and whether a trim is the right move")


class TestBL88P2TrimmerSourceProbe(unittest.TestCase):
    """The Class B row may name a remedy it has CHECKED, and only then lower itself.

    The probe is a SOURCE-TEXT read of the scanned project's own
    `methodology_trim.py`, never an execution -- no adopter code runs inside the scanner, which is
    the precedent `find_trim_tool` already follows for the version and the budget.

    THE FAILURE PATH IS THE CRITERION. Four trees are scanned through `collect_all` -- the surface
    an adopter's copy actually runs -- one per outcome: the trimmer declares the file (CONFIG), it
    does not (NO CONFIG), it cannot be read (LOAD FAILURE, a deliberately broken fixture trimmer,
    never a wait for a real one), and there is none (ABSENT). Only CONFIG may differ from the unprobed row, and
    the other three are compared to that row as a FROZEN LITERAL rather than to each other.

    THE DECLARED/DERIVED SPLIT IS NOT ENGAGED, AND ONE TEST SAYS SO. The probe changes prose and severity only: the
    file's CLASS stays declared, and the trim row's population stays Class A even in a tree whose
    trimmer declares a Class B name."""

    NOTES = "SESSION_NOTES.md"

    @classmethod
    def setUpClass(cls):
        cls.trim = _load_trimmer()
        cls.canonical = Path(TRIM_PY).read_text(encoding="utf-8")
        cls.patched = cls._splice(cls.canonical)
        cls.broken = cls.canonical + "\n\ndef deliberately_broken(:\n    pass\n"
        cls.scans = {
            "config": cls._scan(cls.patched),
            "no config": cls._scan(cls.canonical),
            "load failure": cls._scan(cls.broken),
            "absent": cls._scan(None),
        }

    @staticmethod
    def _splice(text):
        """The canonical trimmer widened the way an adopter widened its own: one more entry
        in the LEDGERS literal, keyed by basename. Importable, so it can also serve as the
        independent operand for what such a file DEFINES."""
        anchor = "LEDGERS = {\n"
        assert text.count(anchor) == 1, "the canonical LEDGERS literal moved: %d" % text.count(anchor)
        entry = ('    "SESSION_NOTES.md": LedgerSpec(\n'
                 '        basename="SESSION_NOTES.md",\n'
                 '        record_kind="heading",\n'
                 '        footer_mode="none",\n'
                 '        date_of_record=_handoff_date,\n'
                 '        record_start=re.compile(r"^### What Session \\d+ Did\\b"),\n'
                 '    ),\n')
        return text.replace(anchor, anchor + entry, 1)

    @staticmethod
    def _notes_text():
        """Exactly READ_CAP_BYTES + 1 bytes over exactly 100 lines -- the shape of the literal."""
        size = md.READ_CAP_BYTES + 1
        width = size // 100
        lines = ["x" * (width - 1) + "\n"] * 99
        last = size - sum(len(l) for l in lines)
        return "".join(lines) + "y" * (last - 1) + "\n"

    @classmethod
    def _scan(cls, trimmer_text):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            subprocess.run(["git", "init", "-q", str(p)], check=True)
            (p / "SESSION_RUNNER.md").write_text("# r\n")
            (p / "README.md").write_text("# fx\n")
            (p / cls.NOTES).write_text(cls._notes_text())
            if trimmer_text is not None:
                (p / md.TRIM_TOOL_NAME).write_text(trimmer_text, encoding="utf-8")
            subprocess.run(["git", "-C", str(p), "add", "-A"], check=True)
            subprocess.run(["git", "-C", str(p), "-c", "user.email=t@t", "-c", "user.name=t",
                            "commit", "-q", "-m", "init"], check=True)
            return md.collect_all(p)

    @staticmethod
    def _rows(metrics, path):
        return [r for r in metrics["scores"]["risks"]
                if path in r["description"] and "read cap" in r["description"]]

    @staticmethod
    def _defines(text):
        """What a trimmer source DEFINES, by executing it -- in the TEST, as the independent
        operand the scanner must never become."""
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "trim_fixture.py"
            f.write_text(text, encoding="utf-8")
            spec = importlib.util.spec_from_file_location("trim_fixture_under_test", f)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return sorted(mod.LEDGERS)

    # --- the fixtures prove themselves first ----------------------------------------------------

    def test_FIXTURE_every_scan_holds_the_literals_file_and_finds_its_trimmer(self):
        """Without this, a wrong byte count or a trimmer `find_trim_tool` skipped would make every
        comparison below pass or fail for the wrong reason -- the LOAD FAILURE arm in particular is
        only exercised if the broken file is FOUND and then fails to parse."""
        for label, m in self.scans.items():
            with self.subTest(scan=label):
                w = [w for w in m["files"]["read_cap_watch"] if w["path"] == self.NOTES]
                self.assertEqual(w, [{"path": self.NOTES, "lines": 100,
                                      "bytes": md.READ_CAP_BYTES + 1}])
                self.assertEqual(m["trim"]["tool_present"], label != "absent")
        with self.assertRaises(SyntaxError):
            compile(self.broken, "broken_fixture", "exec")
        self.assertEqual(self._defines(self.patched),
                         sorted(list(self.trim.LEDGERS) + [self.NOTES]),
                         "the widened fixture must DEFINE exactly one more entry than canonical")

    # --- the reading ------------------------------------------------------------------------------

    def test_the_source_reading_matches_what_the_trimmer_DEFINES(self):
        """Independent operands, as `_parse_trim_budget`'s pin already does: the scanner's reading
        of the source against the keys the module defines when it IS executed -- here, in a test."""
        self.assertEqual(md._parse_trim_ledgers(self.canonical), sorted(self.trim.LEDGERS))
        self.assertEqual(md._parse_trim_ledgers(self.patched), self._defines(self.patched))
        self.assertIn(self.NOTES, md._parse_trim_ledgers(self.patched))

    def test_a_name_the_source_only_MENTIONS_is_not_a_config(self):
        """Why the reading is a PARSE and not a grep. An adopter's widened trimmer spells
        SESSION_NOTES.md on three lines -- a comment, the key, and a `basename=` argument -- and a
        grep counts all three. A false positive is the harmful direction: it names a remedy that
        does not work."""
        mention = '    "SESSION_NOTES.md": LedgerSpec(\n'
        text = (self.canonical
                + "\n# " + mention
                + '\n_EXAMPLE = """\n' + mention + '"""\n')
        self.assertIn('"SESSION_NOTES.md": LedgerSpec(', text,
                      "control: a grep for the entry's own spelling WOULD match this source")
        self.assertEqual(md._parse_trim_ledgers(text), sorted(self.trim.LEDGERS))

    def test_the_reading_ABSTAINS_rather_than_guesses(self):
        """None -- not an empty list, and not a best effort -- whenever the source alone cannot
        say what LEDGERS holds. An abstention costs nothing (the row stays P1's); a guess could
        name a remedy that does not work."""
        cases = {
            "syntax error": 'LEDGERS = {"SESSION_NOTES.md": None}\ndef f(:\n',
            "null byte": 'LEDGERS = {"SESSION_NOTES.md": None}\x00\n',
            "no LEDGERS": "X = 1\n",
            "not a dict display": 'LEDGERS = dict(SESSION_NOTES=None)\n',
            "computed key": 'K = "SESSION_NOTES.md"\nLEDGERS = {K: None}\n',
            "a non-string key": 'LEDGERS = {"SESSION_NOTES.md": None, 1: None}\n',
            "dict unpacking": 'LEDGERS = {"SESSION_NOTES.md": None, **OTHER}\n',
            "only inside a function": 'def f():\n    LEDGERS = {"SESSION_NOTES.md": None}\n',
            "subscript store after": ('LEDGERS = {"CHANGELOG.md": None}\n'
                                      'LEDGERS["SESSION_NOTES.md"] = None\n'),
            "subscript delete after": ('LEDGERS = {"SESSION_NOTES.md": None}\n'
                                       'del LEDGERS["SESSION_NOTES.md"]\n'),
            "mutating method": ('LEDGERS = {"SESSION_NOTES.md": None}\n'
                                'LEDGERS.pop("SESSION_NOTES.md")\n'),
            "rebound": 'LEDGERS = {"SESSION_NOTES.md": None}\nLEDGERS = {}\n',
            "rebound in a function": ('LEDGERS = {"SESSION_NOTES.md": None}\n'
                                      'def f():\n    global LEDGERS\n    LEDGERS = {}\n'),
            "imported": 'from elsewhere import LEDGERS\n',
            "imported after": 'LEDGERS = {"SESSION_NOTES.md": None}\nfrom elsewhere import LEDGERS\n',
            "imported under the name": ('LEDGERS = {"SESSION_NOTES.md": None}\n'
                                        'from elsewhere import OTHER as LEDGERS\n'),
            "imported as a package": 'LEDGERS = {"SESSION_NOTES.md": None}\nimport LEDGERS.sub\n',
            "a def of the name": 'LEDGERS = {"SESSION_NOTES.md": None}\ndef LEDGERS():\n    pass\n',
            "a class of the name": 'LEDGERS = {"SESSION_NOTES.md": None}\nclass LEDGERS:\n    pass\n',
            "except-as the name": ('LEDGERS = {"SESSION_NOTES.md": None}\ntry:\n    pass\n'
                                   'except Exception as LEDGERS:\n    pass\n'),
            "an alias by chained assignment": ('LEDGERS = ALIAS = {"SESSION_NOTES.md": None}\n'
                                               'ALIAS.pop("SESSION_NOTES.md")\n'),
            "pathologically deep": 'LEDGERS = {"SESSION_NOTES.md": None}\nX = ' + "not " * 100000 + "1\n",
        }
        for label, text in cases.items():
            with self.subTest(case=label):
                self.assertIsNone(md._parse_trim_ledgers(text))
        # CONTROLS: the same shapes read when nothing disturbs them, including the read-only use
        # the trimmer itself makes of the table -- so the abstentions above are not "always None".
        self.assertEqual(md._parse_trim_ledgers('LEDGERS = {"SESSION_NOTES.md": None}\n'),
                         ["SESSION_NOTES.md"])
        self.assertEqual(md._parse_trim_ledgers('X, Y = 1, 2\nLEDGERS = {"B.md": 1, "A.md": 2}\n'
                                                'spec = LEDGERS.get("A.md")\n'
                                                'other = LEDGERS["B.md"]\n'
                                                'for k, v in LEDGERS.items():\n    pass\n'
                                                'n = (LEDGERS.keys(), LEDGERS.values(), LEDGERS.copy())\n'),
                         ["A.md", "B.md"])
        self.assertEqual(md._parse_trim_ledgers("LEDGERS = {}\n"), [])

    def test_the_reading_NEVER_RUNS_the_source(self):
        """The operator's decision, pinned: a source whose top level would write a file and exit
        is read, and neither happens."""
        with tempfile.TemporaryDirectory() as tmp:
            sentinel = Path(tmp) / "ran"
            text = ("open(%r, 'w').write('ran')\n"
                    'LEDGERS = {"SESSION_NOTES.md": None}\n'
                    "raise SystemExit(3)\n" % str(sentinel))
            self.assertEqual(md._parse_trim_ledgers(text), ["SESSION_NOTES.md"])
            self.assertFalse(sentinel.exists(), "the scanner executed the trimmer it was reading")

    def test_the_scan_carries_the_reading_for_each_outcome(self):
        expected = {"config": sorted(list(self.trim.LEDGERS) + [self.NOTES]),
                    "no config": sorted(self.trim.LEDGERS),
                    "load failure": None,
                    "absent": None}
        for label, m in self.scans.items():
            with self.subTest(scan=label):
                self.assertEqual(m["trim"]["tool_ledgers"], expected[label])

    # --- the row ----------------------------------------------------------------------------------

    def test_CONFIG_the_row_gains_the_remedy_and_takes_class_A_severity(self):
        rows = self._rows(self.scans["config"], self.NOTES)
        self.assertEqual(len(rows), 1, "%r" % rows)
        self.assertEqual(rows[0]["severity"], "low",
                         "a Class B file whose project CAN act on it drops to the Class A "
                         "severity (plan §8 P2)")
        self.assertEqual(rows[0]["description"],
                         _P1_CLASS_B_ROWS[self.NOTES]
                         + _P2_REMEDY.format(tool="methodology_trim.py", base=self.NOTES,
                                             path=self.NOTES),
                         "P2 APPENDS a sentence to P1's row; it rewrites nothing P1 said")

    def test_NO_CONFIG_LOAD_FAILURE_and_ABSENT_leave_the_row_byte_identical_to_P1(self):
        """THE CRITERION. Compared to the frozen literal, never to each other: three arms that
        drifted together would agree with one another and all be wrong."""
        for label in ("no config", "load failure", "absent"):
            with self.subTest(scan=label):
                rows = self._rows(self.scans[label], self.NOTES)
                self.assertEqual(len(rows), 1, "%r" % rows)
                self.assertEqual(rows[0]["severity"], "high")
                self.assertEqual(rows[0]["description"], _P1_CLASS_B_ROWS[self.NOTES])

    def test_the_probe_selects_NO_CLASS(self):
        """Dragon 6. In the one tree whose trimmer declares SESSION_NOTES.md, the file is still
        Class B and the trim row's population is still Class A only -- the probe reached the
        prose and nothing else."""
        m = self.scans["config"]
        self.assertEqual(md.read_cap_class(self.NOTES), "B")
        self.assertEqual([l["path"] for l in m["trim"]["ledgers"]], [],
                         "the trim-row population admitted a Class B file because its trimmer "
                         "declares it -- that is class membership following LEDGERS")
        self.assertFalse([s for s in m["trim"]["signals"] if self.NOTES in s[1]])

    def test_every_class_B_name_resolves_by_BASENAME_as_the_trimmer_does(self):
        """The trimmer looks a file up by `LEDGERS.get(path.name)` at any depth, so a nested
        `docs/planning/BACKLOG.md` is answered by a `BACKLOG.md` entry -- and the remedy must
        still name the path the reader has, not the basename."""
        base = copy.deepcopy(self.scans["absent"])
        for name in sorted(md.READ_CAP_CLASS_B):
            with self.subTest(name=name):
                m = copy.deepcopy(base)
                m["files"]["read_cap_watch"] = [{"path": name, "bytes": md.READ_CAP_BYTES + 1,
                                                 "lines": 100}]
                m["trim"] = {"signals": [], "tool_present": True,
                             "tool_path": "methodology_trim.py",
                             "tool_ledgers": ["BACKLOG.md", "CHANGELOG.md", "HANDOFFS.md",
                                              "SESSION_NOTES.md"]}
                rows = self._rows({"scores": {"risks": md.assess_risks(m)}}, name)
                self.assertEqual(len(rows), 1, "%r" % rows)
                self.assertEqual(rows[0]["severity"], "low")
                self.assertEqual(rows[0]["description"],
                                 _P1_CLASS_B_ROWS[name]
                                 + _P2_REMEDY.format(tool="methodology_trim.py",
                                                     base=name.rsplit("/", 1)[-1], path=name))

    def test_a_reading_the_scan_cannot_vouch_for_is_not_trusted(self):
        """The remedy needs all three: a tool that was FOUND, a path to name, and a reading that
        lists the basename. Each missing one leaves P1's row."""
        base = copy.deepcopy(self.scans["absent"])
        bad = {
            "tool not present": {"tool_present": False, "tool_path": "methodology_trim.py",
                                 "tool_ledgers": ["SESSION_NOTES.md"]},
            "no tool path": {"tool_present": True, "tool_path": None,
                             "tool_ledgers": ["SESSION_NOTES.md"]},
            "reading abstained": {"tool_present": True, "tool_path": "methodology_trim.py",
                                  "tool_ledgers": None},
            "name not declared": {"tool_present": True, "tool_path": "methodology_trim.py",
                                  "tool_ledgers": ["CHANGELOG.md", "HANDOFFS.md"]},
            "an older metrics dict": {},
        }
        for label, trim in bad.items():
            with self.subTest(case=label):
                m = copy.deepcopy(base)
                m["trim"] = dict(trim, signals=[])
                rows = [r for r in md.assess_risks(m)
                        if self.NOTES in r["description"] and "read cap" in r["description"]]
                self.assertEqual([(r["severity"], r["description"]) for r in rows],
                                 [("high", _P1_CLASS_B_ROWS[self.NOTES])])

    def test_the_probe_touches_neither_the_class_A_row_nor_the_hard_refusal_row(self):
        """The probe is confined to the Class B arm between the cap and the refusal. A Class A ledger is
        already LOW and already remedied by the trim row; past the refusal nothing arrives at all,
        and a remedy sentence must not soften that row's severity."""
        base = copy.deepcopy(self.scans["absent"])
        declared = {"signals": [], "tool_present": True, "tool_path": "methodology_trim.py",
                    "tool_ledgers": ["CHANGELOG.md", "HANDOFFS.md", "SESSION_NOTES.md"]}
        for path, size in (("HANDOFFS.md", md.READ_CAP_BYTES + 1),
                           (self.NOTES, md.READ_REFUSE_BYTES + 1)):
            with self.subTest(path=path):
                rows_by = {}
                for label, trim in (("declared", declared), ("none", {"signals": []})):
                    m = copy.deepcopy(base)
                    m["files"]["read_cap_watch"] = [{"path": path, "bytes": size, "lines": 100}]
                    m["trim"] = copy.deepcopy(trim)
                    rows_by[label] = [(r["severity"], r["description"])
                                      for r in md.assess_risks(m) if path in r["description"]]
                self.assertTrue(rows_by["none"], "control: the row exists at this size")
                self.assertEqual(rows_by["declared"], rows_by["none"])
                self.assertFalse(any("HAS A REMEDY" in d for _, d in rows_by["declared"]))


# === The dashboard understands both layouts ===========
#
# A project keeps its methodology files at its root (legacy) or one level down in methodology/ (new);
# tools/layout_resolver.py answers which. Every test below builds a real tree with tools/layout_fixtures.py,
# in every shape the layout has (legacy, new, tier1, half, empty), puts a real git history under it, and
# asserts a VALUE the dashboard computed: a score, a path, a risk row. Written RED-first (each class was
# run against the unpatched dashboard before any change to it, and the layers below name what failed).

_LF_SPEC = importlib.util.spec_from_file_location("layout_fixtures_under_test", os.path.join(HERE, "layout_fixtures.py"))
lf = importlib.util.module_from_spec(_LF_SPEC)
_LF_SPEC.loader.exec_module(lf)


def layout_project(case, layout, *, contents=None, extra_commits=0, remove=(), extra=None, backlog=True,
                   name="proj", archive=False, generated=False):
    """A git repository holding the ``layout`` shape of the methodology's files (plus the project's own
    BACKLOG.md, which the manifest does not distribute and the checklist scores). ``remove`` deletes
    files from the tree before the first commit, ``extra`` adds {relative path: text}."""
    td = tempfile.TemporaryDirectory()
    case.addCleanup(td.cleanup)
    p = Path(td.name) / name
    lf.build_tree(p, layout, contents=contents, archive=archive, generated=generated)
    if backlog:
        (p / "BACKLOG.md").write_text("# Backlog\n", encoding="utf-8")
    for rel in remove:
        (p / rel).unlink()
    for rel, text in (extra or {}).items():
        (p / rel).parent.mkdir(parents=True, exist_ok=True)
        (p / rel).write_text(text, encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(p)], check=True)
    git = ["git", "-C", str(p), "-c", "user.email=t@t", "-c", "user.name=t"]
    subprocess.run(git + ["add", "-A"], check=True)
    subprocess.run(git + ["commit", "-q", "-m", "init"], check=True)
    for i in range(extra_commits):
        subprocess.run(git + ["commit", "-q", "--allow-empty", "-m", "filler %d" % i], check=True)
    return p


def risk_texts(project):
    return [(r["severity"], r["description"]) for r in md.collect_all(project)["scores"]["risks"]]


class TestBL101P5Checklist(unittest.TestCase):
    """The compliance checklist, the adoption test and the role test read the project through the
    resolver, so a project that moved its files scores what it scored before it moved."""

    def test_a_complete_adopter_scores_the_full_checklist_in_every_layout(self):
        for layout in ("legacy", "new", "tier1"):
            with self.subTest(layout=layout):
                m = md.collect_methodology_metrics(layout_project(self, layout))
                self.assertEqual(m["compliance_score"], md.METHODOLOGY_MAX)
                self.assertEqual(m["missing_files"], [])
                self.assertEqual(m["compliance_pct"], 100)

    def test_the_item_labels_are_the_same_names_in_every_layout(self):
        # Portfolio aggregation, the JSON export and the card's glyph row all key on these names.
        want = [item for item, _w, _k in md.METHODOLOGY_ITEMS]
        for layout in ("legacy", "new", "tier1"):
            with self.subTest(layout=layout):
                m = md.collect_methodology_metrics(layout_project(self, layout))
                self.assertEqual(list(m["items"]), want)

    def test_a_missing_file_is_missing_in_the_layout_it_would_have_lived_in(self):
        # The probe must not be satisfied by a file of the same name in the OTHER place's namesake path.
        for layout, gone in (("legacy", "SAFEGUARDS.md"), ("new", "methodology/SAFEGUARDS.md"),
                             ("tier1", "methodology/SAFEGUARDS.md")):
            with self.subTest(layout=layout):
                m = md.collect_methodology_metrics(layout_project(self, layout, remove=(gone,)))
                self.assertEqual(m["missing_files"], ["SAFEGUARDS.md"])
                self.assertEqual(m["compliance_score"], md.METHODOLOGY_MAX - 20)

    def test_the_metrics_name_the_layout_they_read(self):
        want = {"legacy": ("legacy", "."), "new": ("new", "methodology"), "tier1": ("new", "methodology"),
                "empty": ("none", None)}
        for layout, (kind, directory) in want.items():
            with self.subTest(layout=layout):
                lay = md.collect_methodology_metrics(layout_project(self, layout))["layout"]
                self.assertEqual((lay["kind"], lay["directory"]), (kind, directory))

    def test_a_half_migrated_tree_is_a_high_risk_naming_both_runners(self):
        p = layout_project(self, "half")
        lay = md.collect_methodology_metrics(p)["layout"]
        self.assertEqual(lay["kind"], "half")
        self.assertEqual(sorted(lay["found"]), ["SESSION_RUNNER.md", "methodology/SESSION_RUNNER.md"])
        rows = [(s, d) for s, d in risk_texts(p) if "half-migrated" in d.lower()]
        self.assertEqual(len(rows), 1, rows)
        severity, text = rows[0]
        self.assertEqual(severity, "high")
        self.assertIn("methodology/SESSION_RUNNER.md", text)
        self.assertIn(" SESSION_RUNNER.md", text.replace("methodology/SESSION_RUNNER.md", ""))

    def test_a_half_migrated_tree_is_scored_for_what_is_there_not_zeroed(self):
        # Never guess which copy is live: a file present at either place counts, and the risk row carries the defect.
        m = md.collect_methodology_metrics(layout_project(self, "half"))
        self.assertEqual(m["compliance_score"], md.METHODOLOGY_MAX)

    def test_a_half_migrated_tree_counts_a_file_held_only_under_methodology(self):
        # The union cuts both ways: the half fixture holds everything at the root, so this one moves a single
        # file to the OTHER place and removes it from the root. A mutant that dropped the methodology copy
        # from the half answer survived every other test (found by a mutation pass).
        p = layout_project(self, "half", remove=("SAFEGUARDS.md",), extra={"methodology/SAFEGUARDS.md": "# safeguards\n"})
        m = md.collect_methodology_metrics(p)
        self.assertEqual(m["layout"]["kind"], "half")
        self.assertTrue(m["items"]["SAFEGUARDS.md"])
        self.assertEqual(m["compliance_score"], md.METHODOLOGY_MAX)

    def test_no_other_shape_raises_the_half_migrated_row(self):
        for layout in ("legacy", "new", "tier1", "empty"):
            with self.subTest(layout=layout):
                rows = [d for _s, d in risk_texts(layout_project(self, layout)) if "half-migrated" in d.lower()]
                self.assertEqual(rows, [])

    def test_a_ledger_held_in_both_places_with_the_runner_at_the_root_is_half_migrated(self):
        # The runner cannot decide a tie about a state file when the runner itself is at the root.
        p = layout_project(self, "legacy", extra={"methodology/CHANGELOG.md": "# a second ledger\n"})
        lay = md.collect_methodology_metrics(p)["layout"]
        self.assertEqual(lay["kind"], "half")
        self.assertIn("methodology/CHANGELOG.md", lay["found"])

    def test_an_adopter_that_moved_is_still_owed_a_ledger(self):
        # The gate that notices a missing action ledger keyed on the root runner: in the new layout it went quiet.
        for layout, gone in (("legacy", "CHANGELOG.md"), ("new", "methodology/CHANGELOG.md")):
            with self.subTest(layout=layout):
                p = layout_project(self, layout, remove=(gone,), extra_commits=md.LEDGER_REAL_HISTORY_MIN + 2)
                rows = [d for _s, d in risk_texts(p) if "action ledger" in d]
                self.assertEqual(len(rows), 1, rows)

    def test_a_vendored_framework_is_still_an_adopter_when_its_runner_is_under_methodology(self):
        # bin/_manifest.py + starter-kit/SESSION_RUNNER.md and NO root runner is how the PUBLISHER is recognised;
        # a project that vendors those and installs its own runner under methodology/ is not the publisher.
        vendored = {"bin/_manifest.py": "DISTRIBUTION = []\n", "starter-kit/SESSION_RUNNER.md": "# runner\n"}
        for layout, role in (("legacy", "adopter"), ("new", "adopter")):
            with self.subTest(layout=layout):
                p = layout_project(self, layout, extra=vendored)
                self.assertEqual(md.detect_repo_role(p)["role"], role)
        publisher = layout_project(self, "empty", extra=vendored)
        self.assertEqual(md.detect_repo_role(publisher)["role"], "framework")


QUARTO_BOOK = {
    "_quarto.yml": "project:\n  type: book\n",
    "ch1.qmd": "# Ch1\n" + "prose\n" * 200,
    "ch2.qmd": "# Ch2\n" + "prose\n" * 200,
    "README.md": "# Monograph\n\nA Quarto book.\n" * 4,
}


def installed_tool_contents():
    """What `bin/sync` writes for the four executables: each carries the constant its own predicate reads."""
    body = "".join("def gen_%d():\n    return %d\n" % (i, i) for i in range(800))
    return {"methodology_dashboard.py": installed_scanner(), "methodology_trim.py": installed_trimmer(),
            "context_budget.py": 'VERSION = "1.0.0"\n' + body, "quality_ratchet.py": 'VERSION = "1.0.0"\n' + body}


def card_projection(project):
    """What the scores and the file inventory say about a project, with every layout-dependent PATH removed:
    two projects that differ only in where their methodology files live must project identically."""
    m = md.collect_all(project)
    cat = {k: v for k, v in m["files"]["by_category"].items()}
    return {
        "health": m["scores"]["health"],
        "doc_only": m["doc_only"]["is_doc_only"],
        "categories": cat,
        "framework_docs": m["files"]["framework_docs"],
        "total_files": m["files"]["total_files"],
        "compliance": (m["methodology"]["compliance_score"], m["methodology"]["compliance_pct"]),
        "risks": sorted((r["severity"], r["description"].replace("methodology/", "")) for r in m["scores"]["risks"]),
        "ledger": (m["changelog"]["present"], m["changelog"]["ledger_present"], m["changelog"]["unlogged_commits"]),
        "trim_tool": m["trim"]["tool_present"],
    }


class TestBL101P5Walk(unittest.TestCase):
    """The installed-source fingerprint and the read-cap watch: a methodology file is recognised by
    the name the tables hold, wherever the layout put it, and a file of the same name that is the
    PROJECT's own (a root CHANGELOG.md beside the framework's under methodology/) is never read as ours."""

    def test_installing_the_methodology_leaves_a_doc_repo_doc_only_in_every_layout(self):
        for layout in ("legacy", "new", "tier1"):
            with self.subTest(layout=layout):
                p = layout_project(self, layout, contents=installed_tool_contents(), extra=QUARTO_BOOK)
                m = md.collect_all(p)
                self.assertTrue(m["doc_only"]["is_doc_only"])
                self.assertEqual(m["tests"]["source_loc"], 0, "the adopter wrote no source; the four tools are ours")
                self.assertGreater(m["files"]["by_category"]["vendor"]["loc"], 5000)

    def test_the_card_projects_the_same_in_every_layout(self):
        # Both trees get a docs/ of their own: see the next test for why that is part of the comparison.
        own = dict(QUARTO_BOOK, **{"docs/index.md": "# Docs\n\nThe project's own documentation.\n"})
        projections = {layout: card_projection(layout_project(self, layout, contents=installed_tool_contents(),
                                                              extra=own, extra_commits=12))
                       for layout in ("legacy", "new", "tier1")}
        self.assertEqual(projections["new"], projections["legacy"])
        self.assertEqual(projections["tier1"], projections["legacy"])

    def test_the_docs_directory_point_belongs_to_the_projects_own_docs_not_to_the_methodologys(self):
        # PINNED ON PURPOSE, not an accident. `has_docs_dir` is a bare presence check, and a legacy adopter
        # satisfies it with docs/methodology/ alone, so every synced project has earned 4 documentation points
        # for a directory the methodology put there. In the new layout nothing of ours is under docs/, so a
        # project with no docs/ of its own loses them when it migrates. Recorded as a known consequence:
        # parity would mean rewarding methodology/ as documentation, or changing every legacy score.
        want = {"legacy": True, "new": False, "tier1": False}
        for layout, has in want.items():
            with self.subTest(layout=layout):
                self.assertIs(md.collect_all(layout_project(self, layout))["docs"]["has_docs_dir"], has)
        own = layout_project(self, "new", extra={"docs/index.md": "# Docs\n"})
        self.assertIs(md.collect_all(own)["docs"]["has_docs_dir"], True)

    def test_a_projects_own_root_changelog_is_not_the_frameworks_ledger(self):
        product = "# Release notes\n\n" + "- shipped a thing\n" * 300
        p = layout_project(self, "new", extra={"CHANGELOG.md": product})
        m = md.collect_all(p)
        watched = sorted(w["path"] for w in m["files"]["read_cap_watch"])
        self.assertEqual(watched, ["BACKLOG.md", "methodology/CHANGELOG.md", "methodology/HANDOFFS.md",
                                   "methodology/SESSION_NOTES.md"])
        self.assertEqual(md._find_action_ledger(p), p / "methodology" / "CHANGELOG.md")
        control = layout_project(self, "new")
        self.assertEqual(m["files"]["framework_docs"]["loc"], md.collect_all(control)["files"]["framework_docs"]["loc"],
                         "the project's own 300-line changelog must not be discounted as ours")

    def test_a_generated_proof_under_methodology_archive_is_not_the_adopters_source(self):
        proof = "#!/bin/sh\n# generated by methodology_trim.py\n" + "echo step\n" * 220
        for layout, shard_dir in (("legacy", "docs/archive"), ("new", "methodology/archive")):
            with self.subTest(layout=layout):
                p = layout_project(self, layout, contents=installed_tool_contents(),
                                   extra={shard_dir + "/CHANGELOG-through-2026-01-01.md.verify.sh": proof})
                files = md.collect_all(p)["files"]["by_category"]
                self.assertEqual(files["source"]["loc"], 0)
                self.assertGreaterEqual(files["vendor"]["loc"], 220 + 5000)

    def test_a_script_that_only_sits_in_an_archive_directory_is_still_source(self):
        # Anti-laundering: all three conditions stay required (the directory, the suffix, the banner).
        banner = "#!/bin/sh\n# generated by methodology_trim.py\n" + "echo step\n" * 220
        plain = "#!/bin/sh\n" + "echo step\n" * 220
        for rel, text in (("methodology/archive/x.md.verify.sh", plain),      # no banner
                          ("methodology/archive/x.sh", banner),               # no suffix
                          ("elsewhere/archive/x.md.verify.sh", banner)):      # not an archive directory of the layout
            with self.subTest(rel=rel):
                p = layout_project(self, "new", contents=installed_tool_contents(), extra={rel: text})
                self.assertGreaterEqual(md.collect_all(p)["files"]["by_category"]["source"]["loc"], 220)

    def test_the_ledger_is_measured_where_it_lives(self):
        for layout, rel in (("legacy", "CHANGELOG.md"), ("new", "methodology/CHANGELOG.md"), ("tier1", "CHANGELOG.md")):
            with self.subTest(layout=layout):
                p = layout_project(self, layout, extra_commits=12)
                cl = md.collect_all(p)["changelog"]
                self.assertTrue(cl["present"])
                self.assertTrue(cl["ledger_present"])
                self.assertEqual(cl["unlogged_commits"], 12)
                self.assertTrue(any(d.startswith(rel + ": 12 commits since it was last updated") for _s, d in cl["signals"]),
                                cl["signals"])

    def test_the_trim_row_finds_the_trimmer_and_the_ledger_where_they_live(self):
        big = "# Handoffs\n\n" + "x" * (md.CLASS_A_FIRE_BYTES + 1000)
        want = {"legacy": ("methodology_trim.py", "HANDOFFS.md"),
                "new": ("methodology/methodology_trim.py", "methodology/HANDOFFS.md"),
                "tier1": ("methodology/methodology_trim.py", "HANDOFFS.md")}
        for layout, (tool, ledger) in want.items():
            with self.subTest(layout=layout):
                p = layout_project(self, layout, contents={"HANDOFFS.md": big, "methodology_trim.py": installed_trimmer()})
                trim = md.collect_all(p)["trim"]
                self.assertTrue(trim["tool_present"])
                self.assertEqual(trim["tool_path"], tool)
                self.assertEqual([e["path"] for e in trim["ledgers"] if e["fires"]], [ledger])
                self.assertTrue(any("python3 %s --file %s --check" % (tool, ledger) in d for _s, d in trim["signals"]),
                                trim["signals"])

    def test_the_read_cap_rows_classify_a_file_by_its_name_not_its_directory(self):
        # 100 kB: past the one-read budget, short of the Class A archive threshold; the row says which class.
        ledger = "# Handoffs\n\n" + "x" * 100000
        notes = "# Notes\n\n" + "x" * 60000
        for layout, prefix in (("legacy", ""), ("new", "methodology/")):
            with self.subTest(layout=layout):
                p = layout_project(self, layout, contents={"HANDOFFS.md": ledger, "SESSION_NOTES.md": notes})
                rows = {d.split(" is ")[0]: (s, d) for s, d in risk_texts(p) if " one-read budget " in d}
                self.assertEqual(sorted(rows), [prefix + "HANDOFFS.md", prefix + "SESSION_NOTES.md"])
                self.assertIn("CLASS A", rows[prefix + "HANDOFFS.md"][1])
                self.assertIn("CLASS B", rows[prefix + "SESSION_NOTES.md"][1])


class TestBL101P5Sync(unittest.TestCase):
    """C15: `--sync` is a second sync channel, outside the manifest. Each target's layout is resolved, so a
    migrated project gets `methodology/methodology_dashboard.py` and never a second copy at its root, and a
    copy that lives in methodology/ finds its project, writes beside itself and warns with the project's path."""

    CANON_TEXT = None

    def _portfolio(self, projects):
        """A portfolio root holding the canonical authoring repo and one git project per {name: layout}.
        Every project ignores methodology_dashboard.py, so a create is not gated by the --force rule."""
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        canon = root / "methodology" / "starter-kit" / "methodology_dashboard.py"
        canon.parent.mkdir(parents=True)
        canon.write_text(Path(TOOLS_PY).read_text(encoding="utf-8"), encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(root / "methodology")], check=True)
        made = {}
        for name, layout in projects.items():
            p = root / name
            lf.build_tree(p, layout, generated=False)
            for rel in ("methodology_dashboard.py", "methodology/methodology_dashboard.py"):
                if (p / rel).exists():
                    (p / rel).write_text("# a stale copy\n", encoding="utf-8")
            (p / ".gitignore").write_text("methodology_dashboard.py\n", encoding="utf-8")
            subprocess.run(["git", "init", "-q", str(p)], check=True)
            made[name] = p
        return root, canon, made

    def _run_sync(self, canon, **kw):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            written = md.sync_dashboards(canon, **kw)
        return written, out.getvalue(), err.getvalue()

    def test_a_portfolio_sync_writes_each_project_in_the_layout_it_is_in(self):
        root, canon, p = self._portfolio({"legacy": "legacy", "migrated": "new", "half": "half", "empty": "empty"})
        text = canon.read_text(encoding="utf-8")
        written, out, err = self._run_sync(canon)
        self.assertEqual((p["legacy"] / "methodology_dashboard.py").read_text(encoding="utf-8"), text)
        self.assertEqual((p["migrated"] / "methodology" / "methodology_dashboard.py").read_text(encoding="utf-8"), text)
        self.assertFalse((p["migrated"] / "methodology_dashboard.py").exists(),
                         "a migrated project must never get a second dashboard at its root")
        self.assertEqual((p["empty"] / "methodology_dashboard.py").read_text(encoding="utf-8"), text,
                         "an empty project gets the default layout's place (the legacy root, until the contract stage)")
        # The portfolio root is not a git repository, so a new copy there is gated without --force (issue #67):
        # three writes, the half-migrated project refused, and nothing created at the portfolio root.
        self.assertFalse((root / "methodology_dashboard.py").exists())
        self.assertEqual(written, 3, out)       # legacy, migrated, empty

    def test_a_half_migrated_project_is_refused_by_name_and_left_untouched(self):
        root, canon, p = self._portfolio({"half": "half"})
        written, out, err = self._run_sync(canon)
        self.assertEqual((p["half"] / "methodology_dashboard.py").read_text(encoding="utf-8"), "# a stale copy\n")
        self.assertFalse((p["half"] / "methodology" / "methodology_dashboard.py").exists())
        self.assertTrue(any("half-migrated" in l for l in out.splitlines()), out)
        self.assertIn("methodology/SESSION_RUNNER.md", out)

    def test_a_dry_run_names_the_resolved_path_and_writes_nothing(self):
        root, canon, p = self._portfolio({"migrated": "new"})
        before = (p["migrated"] / "methodology" / "methodology_dashboard.py").read_text(encoding="utf-8")
        written, out, err = self._run_sync(canon, dry_run=True)
        self.assertEqual(written, 0)
        self.assertEqual((p["migrated"] / "methodology" / "methodology_dashboard.py").read_text(encoding="utf-8"), before)
        lines = [l for l in out.splitlines() if "migrated" in l]
        self.assertEqual(len(lines), 1, out)
        self.assertIn("migrated/methodology/methodology_dashboard.py", lines[0])

    def test_a_single_target_resolves_its_layout_too(self):
        root, canon, p = self._portfolio({"migrated": "new", "legacy": "legacy"})
        written, out, err = self._run_sync(canon, target=str(p["migrated"]))
        self.assertEqual(written, 1)
        self.assertEqual((p["migrated"] / "methodology" / "methodology_dashboard.py").read_text(encoding="utf-8"),
                         canon.read_text(encoding="utf-8"))
        self.assertFalse((p["migrated"] / "methodology_dashboard.py").exists())
        self.assertEqual((p["legacy"] / "methodology_dashboard.py").read_text(encoding="utf-8"), "# a stale copy\n")

    def test_a_single_half_migrated_target_is_refused_without_writing(self):
        root, canon, p = self._portfolio({"half": "half"})
        written, out, err = self._run_sync(canon, target=str(p["half"]))
        self.assertEqual(written, 0)
        self.assertIn("half-migrated", err)
        self.assertEqual((p["half"] / "methodology_dashboard.py").read_text(encoding="utf-8"), "# a stale copy\n")


class TestBL101P5CopyInsideMethodology(unittest.TestCase):
    """A dashboard that sits in <project>/methodology/ is one level below the project it scans. The two
    names tried are an ordinary project and a project literally NAMED methodology (this repository is one:
    check-overhead and check-ledger --all each took such a directory for a subdirectory)."""

    NAMES = ("proj", "methodology")

    def _project(self, name, layout="new", **kw):
        text = Path(TOOLS_PY).read_text(encoding="utf-8")
        return layout_project(self, layout, name=name, contents={"methodology_dashboard.py": text}, **kw)

    def test_the_project_root_is_found_from_the_copy_in_methodology(self):
        for name in self.NAMES:
            with self.subTest(name=name):
                p = self._project(name)
                self.assertEqual(md.resolve_single_project_root(p / "methodology"), p)

    def test_it_is_not_found_when_nothing_beside_the_copy_says_it_is_a_methodology_directory(self):
        p = self._project("proj")
        (p / "methodology" / "SESSION_RUNNER.md").unlink()
        self.assertEqual(md.resolve_single_project_root(p / "methodology"), p / "methodology")
        loose = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, loose, True)
        (loose / "methodology").mkdir()
        (loose / "methodology" / "SESSION_RUNNER.md").write_text("# runner\n", encoding="utf-8")
        self.assertEqual(md.resolve_single_project_root(loose / "methodology"), loose / "methodology",
                         "no .git above it: a directory named methodology is not a project's subdirectory")

    def test_a_copy_at_the_project_root_is_unchanged(self):
        for name in self.NAMES:
            with self.subTest(name=name):
                p = self._project(name, "legacy")
                self.assertEqual(md.resolve_single_project_root(p), p)

    def _run(self, p):
        return subprocess.run([sys.executable, "-B", str(p / "methodology" / "methodology_dashboard.py"), "--no-open"],
                              cwd=str(p.parent), capture_output=True, text=True, timeout=60)

    def test_the_copy_scans_its_project_and_writes_beside_itself(self):
        for name in self.NAMES:
            with self.subTest(name=name):
                p = self._project(name, extra_commits=3)
                r = self._run(p)
                self.assertNotIn("No projects found", r.stdout + r.stderr)
                self.assertIn("1 projects", r.stdout)
                self.assertTrue((p / "methodology" / "dashboard.html").is_file())
                self.assertTrue((p / "methodology" / "dashboard_history.jsonl").is_file())
                self.assertFalse((p / "dashboard.html").exists(), "the project root stays clean")
                self.assertFalse((p / "dashboard_history.jsonl").exists())
                again = self._run(p)
                self.assertRegex(re.sub(r"\x1b\[[0-9;]*m", "", again.stdout), r"History: 2 snapshots")

    def test_the_stale_copy_warning_names_the_project_not_its_methodology_directory(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        canon = root / "methodology" / "starter-kit" / "methodology_dashboard.py"
        canon.parent.mkdir(parents=True)
        canon.write_text(re.sub(r'DASHBOARD_VERSION = "[^"]+"', 'DASHBOARD_VERSION = "9.9.9"',
                                Path(TOOLS_PY).read_text(encoding="utf-8"), count=1), encoding="utf-8")
        adopter = root / "adopter"
        lf.build_tree(adopter, "new", generated=False, contents={"methodology_dashboard.py": Path(TOOLS_PY).read_text(encoding="utf-8")})
        subprocess.run(["git", "init", "-q", str(adopter)], check=True)
        driver = ("import importlib.util, sys\n"
                  "spec = importlib.util.spec_from_file_location('m', sys.argv[1])\n"
                  "m = importlib.util.module_from_spec(spec)\n"
                  "spec.loader.exec_module(m)\n"
                  "m.check_stale_version()\n")
        r = subprocess.run([sys.executable, "-B", "-c", driver, str(adopter / "methodology" / "methodology_dashboard.py")],
                           capture_output=True, text=True, timeout=30)
        shown = adopter.resolve()      # the copy reports its own real path (macOS: /var is /private/var)
        self.assertIn("--sync %s\n" % shown, r.stderr)
        self.assertNotIn("--sync %s" % (shown / "methodology"), r.stderr)


class TestBL101P5Gates(unittest.TestCase):
    """The quality-gate read (collect_gate_metrics) finds the manifest where it lives and follows its history
    across the move that took it there. Without that a migrated project silently loses its gate signals, and a
    floor lowered INSIDE the move commit is invisible: the same class as 'a gate fails open when
    its file moves'."""

    G = TestQualityGateSignals

    def _repo(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        p = Path(td.name)
        subprocess.run(["git", "init", "-q", str(p)], check=True)
        return p

    def _commit(self, p, msg):
        subprocess.run(["git", "-C", str(p), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(p), "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", msg], check=True)

    def _manifest(self, floor, name="suite"):
        return self.G._manifest(self.G._gate(name, "min", floor))

    def _moved(self, before, after, then_delete=False):
        """Commit 1 holds the manifest at the root, commit 2 moves it under methodology/ (and may change it)."""
        p = self._repo()
        (p / ".quality-gates.json").write_text(self._manifest(before), encoding="utf-8")
        self._commit(p, "init")
        (p / "methodology").mkdir()
        subprocess.run(["git", "-C", str(p), "mv", ".quality-gates.json", "methodology/.quality-gates.json"], check=True)
        (p / "methodology" / ".quality-gates.json").write_text(self._manifest(after), encoding="utf-8")
        self._commit(p, "move")
        if then_delete:
            subprocess.run(["git", "-C", str(p), "rm", "-q", "methodology/.quality-gates.json"], check=True)
            self._commit(p, "delete")
        return p

    def test_the_manifest_is_read_where_it_lives(self):
        for rel in (".quality-gates.json", "methodology/.quality-gates.json"):
            with self.subTest(rel=rel):
                p = self._repo()
                (p / rel).parent.mkdir(exist_ok=True)
                (p / rel).write_text(self._manifest(5), encoding="utf-8")
                self._commit(p, "init")
                m = md.collect_gate_metrics(p)
                self.assertTrue(m["manifest_present"])
                self.assertEqual(m["declared"], 1)

    def test_the_results_file_beside_the_manifest_is_read(self):
        p = self._repo()
        cfg = json.loads(self._manifest(5))
        digest = hashlib.sha256(json.dumps(cfg["gates"], sort_keys=True).encode()).hexdigest()[:12]
        (p / "methodology").mkdir()
        (p / "methodology" / ".quality-gates.json").write_text(json.dumps(cfg), encoding="utf-8")
        (p / "methodology" / ".quality-gates-results.json").write_text(
            json.dumps({"ran_at": "2026-10-07T00:00:00", "manifest": digest,
                        "gates": [{"name": "suite", "status": "pass"}]}), encoding="utf-8")
        self._commit(p, "init")
        m = md.collect_gate_metrics(p)
        self.assertTrue(m["results_present"])
        self.assertFalse(m["results_stale"])
        self.assertEqual(m["summary"]["pass"], 1)

    def test_a_floor_lowered_in_place_is_a_loosening_control(self):
        p = self._repo()
        (p / ".quality-gates.json").write_text(self._manifest(100), encoding="utf-8")
        self._commit(p, "init")
        (p / ".quality-gates.json").write_text(self._manifest(90), encoding="utf-8")
        self._commit(p, "lower")
        self.assertEqual([(l["kind"], l["from"], l["to"]) for l in md.collect_gate_metrics(p)["loosened"]],
                         [("floor lowered", 100.0, 90.0)])

    def test_a_floor_lowered_in_the_move_commit_is_still_seen(self):
        m = md.collect_gate_metrics(self._moved(100, 90))
        self.assertEqual([(l["name"], l["kind"], l["from"], l["to"]) for l in m["loosened"]],
                         [("suite", "floor lowered", 100.0, 90.0)])

    def test_a_pure_move_loosens_nothing(self):
        m = md.collect_gate_metrics(self._moved(100, 100))
        self.assertEqual((m["loosened"], m["commands_changed"]), ([], []))

    def test_a_manifest_deleted_after_the_move_is_still_a_removal(self):
        m = md.collect_gate_metrics(self._moved(100, 100, then_delete=True))
        self.assertTrue(m["manifest_deleted"])
        self.assertEqual([(l["name"], l["kind"]) for l in m["loosened"]], [("suite", "removed")])


class TestBL101P5TheFrameworkRepoItself(unittest.TestCase):
    """The PUBLISHER's checklist asks whether the repo OPERATES what it publishes: its own CHANGELOG.md and
    HANDOFFS.md. When this repository's own instance files move, those two
    are under methodology/ while its sources (ITERATIVE_METHODOLOGY.md, workstreams/, bin/, starter-kit/)
    stay where they are; the framework checklist must follow the first and not the second."""

    def _framework(self, moved):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        p = Path(td.name) / "framework"
        full_framework_tree(p)
        if moved:
            (p / "methodology").mkdir()
            for name in ("CHANGELOG.md", "HANDOFFS.md"):
                (p / name).rename(p / "methodology" / name)
        subprocess.run(["git", "init", "-q", str(p)], check=True)
        git = ["git", "-C", str(p), "-c", "user.email=t@t", "-c", "user.name=t"]
        subprocess.run(git + ["add", "-A"], check=True)
        subprocess.run(git + ["commit", "-q", "-m", "init"], check=True)
        for i in range(md.LEDGER_REAL_HISTORY_MIN + 2):
            subprocess.run(git + ["commit", "-q", "--allow-empty", "-m", "filler %d" % i], check=True)
        return p

    def test_the_framework_checklist_scores_the_same_with_its_ledgers_moved(self):
        for moved in (False, True):
            with self.subTest(moved=moved):
                m = md.collect_methodology_metrics(self._framework(moved), role="framework")
                self.assertEqual(m["compliance_score"], md.FRAMEWORK_MAX)
                self.assertEqual(m["missing_files"], [])

    def test_a_moved_framework_ledger_is_not_reported_missing_and_the_card_agrees(self):
        for moved in (False, True):
            with self.subTest(moved=moved):
                p = self._framework(moved)
                m = md.collect_all(p)
                self.assertEqual(m["methodology"]["role"], "framework")
                self.assertTrue(m["changelog"]["ledger_present"])
                self.assertEqual([d for _s, d in risk_texts(p) if "action ledger" in d], [])


class TestBL101P5NameTables(unittest.TestCase):
    """The dashboard is one distributed file and cannot import the manifest, so it carries its own tables of the
    names the layout moves. This is the canonical-only test that holds them to bin/_manifest.py, which
    LAYOUT_MOVED's own comment names as its guard."""

    def test_the_names_the_layout_moves_are_the_manifests_destinations_and_the_two_directories(self):
        m = lf._manifest()
        dests = {dest for _s, dest, _d in m.DISTRIBUTION}
        self.assertEqual(len(dests), 30)
        self.assertEqual(md.LAYOUT_MOVED - {"docs/methodology", "docs/methodology/workstreams"}, dests)

    def test_the_state_files_are_exactly_the_manifests_seeds(self):
        m = lf._manifest()
        seeds = {dest for _s, dest, disp in m.DISTRIBUTION if disp == m.SEED}
        self.assertEqual(set(md.LAYOUT_STATE_NAMES), seeds)

    def test_a_destination_lands_where_the_manifests_table_puts_it(self):
        m = lf._manifest()
        for src, dest, _d in m.DISTRIBUTION:
            with self.subTest(dest=dest):
                self.assertEqual(md.new_layout_rel(dest), m.NEW_LAYOUT[src])


if __name__ == "__main__":
    unittest.main(verbosity=2)
