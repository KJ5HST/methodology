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

import filecmp
import importlib.util
import json
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
        "methodology": {"compliance_score": 0, "compliance_pct": 0, "items": {}},
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
    "CONTEXT_TEMPLATE.md": "template; the operating artifact is the adopter's CONTEXT.md instance",
    "CLAUDE_TEMPLATE.md": "template; the operating artifact is the adopter's CLAUDE.md instance",
    "BOOTSTRAP.md": "one-time setup guide, not a per-session operating artifact",
    "methodology_dashboard.py": "the scanner itself — scoring its own presence is circular",
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
        self.assertEqual(md.DASHBOARD_VERSION, "2.10.4")
        starter_src = Path(STARTER_PY).read_text(encoding="utf-8")
        self.assertTrue(re.search(r'^DASHBOARD_VERSION\s*=\s*"2\.10\.4"', starter_src, re.MULTILINE),
                        "starter-kit twin must also declare DASHBOARD_VERSION 2.10.4")


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

    # The synced doc corpus: a Quarto book, whose .qmd files are NOT doc-extensions, so the
    # render-toolchain arm of the disjunction is what has to carry it — the exact source_loc≈0
    # research repo BL-5 exists for.
    QUARTO = {
        "_quarto.yml": "project:\n  type: book\n",
        "ch1.qmd": "# Ch1\n" + "prose\n" * 200,
        "ch2.qmd": "# Ch2\n" + "prose\n" * 200,
        "README.md": "# Monograph\n\nA Quarto book.\n" * 4,
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
        # bin/sync installs all six ambiguous names, so a genuine install always clears the
        # threshold. If this ever inverts, real installs silently stop being discounted.
        self.assertGreaterEqual(len(md.FRAMEWORK_AMBIGUOUS_DOCS),
                                md.FRAMEWORK_AMBIGUOUS_EVIDENCE_MIN,
                                "a real bin/sync install must be able to satisfy the ambiguous "
                                "evidence threshold on its own")

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
        self.assertGreaterEqual(m["files"]["framework_docs"]["count"], 21)
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
