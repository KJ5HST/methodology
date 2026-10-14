#!/usr/bin/env python3
"""Unit tests for the methodology/ layout work (BL-101, phase P1).

CANONICAL-ONLY. None of tools/layout_resolver.py, tools/layout_fixtures.py or
bin/check-layout-literals is in bin/_manifest.py, so adopters do not receive them: phases
P2-P6 embed the resolver's marked block in each shipped tool, and assert here that every
copy is byte-identical to this module's (the dashboard twin test is the precedent).

The contract is docs/planning/methodology-subdirectory-plan.md section 4.3 (the four-row
table) and section 7.1 (what P1 is done when). Every rule is observed failing as well as
passing (Learning #12): the scanner section builds trees that must be refused.
"""
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True  # a test run must not generate tools/__pycache__

HERE = Path(__file__).resolve().parent
REPO = HERE.parent


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_script(name, path):
    import importlib.machinery
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    mod = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, loader))
    loader.exec_module(mod)
    return mod


lr = _load("layout_resolver", HERE / "layout_resolver.py")
lf = _load("layout_fixtures", HERE / "layout_fixtures.py")
cll = _load_script("check_layout_literals", REPO / "bin" / "check-layout-literals")


def touch(root, *rel):
    p = Path(root).joinpath(*rel)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("x\n", encoding="utf-8")
    return p


class Scratch(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self.root = Path(self._td.name)


class TestTheFourRows(Scratch):
    """Section 4.3, one test per row of the table."""

    def test_row_1_the_runner_under_methodology_is_the_new_layout(self):
        touch(self.root, "methodology", "SESSION_RUNNER.md")
        kind, directory, found = lr.resolve_layout(self.root)
        self.assertEqual(kind, "new")
        self.assertEqual(directory, self.root / "methodology")
        self.assertEqual(found, (self.root / "methodology" / "SESSION_RUNNER.md",))

    def test_row_2_the_runner_at_the_root_is_the_legacy_layout(self):
        touch(self.root, "SESSION_RUNNER.md")
        kind, directory, found = lr.resolve_layout(self.root)
        self.assertEqual(kind, "legacy")
        self.assertEqual(directory, self.root)
        self.assertEqual(found, (self.root / "SESSION_RUNNER.md",))

    def test_row_3_both_is_half_migrated_and_names_both_never_guesses(self):
        touch(self.root, "SESSION_RUNNER.md")
        touch(self.root, "methodology", "SESSION_RUNNER.md")
        kind, directory, found = lr.resolve_layout(self.root)
        self.assertEqual(kind, "half")
        self.assertIsNone(directory, "a half-migrated tree must not yield a directory to guess with")
        self.assertEqual(set(found), {self.root / "SESSION_RUNNER.md",
                                      self.root / "methodology" / "SESSION_RUNNER.md"})

    def test_row_4_neither_is_none(self):
        kind, directory, found = lr.resolve_layout(self.root)
        self.assertEqual((kind, directory, found), ("none", None, ()))

    def test_the_framework_repo_resolves_to_none(self):
        # Row 4's own example: the canonical repo keeps the runner at starter-kit/, not at its root.
        self.assertTrue((REPO / "starter-kit" / "SESSION_RUNNER.md").is_file())
        self.assertEqual(lr.resolve_layout(REPO)[0], "none")


class TestAnchors(Scratch):
    """The table is keyed on one file. A caller picks the anchor for the class of files it reads,
    which is what lets a tier-1-only adopter (framework files moved, ledgers not) be read correctly."""

    def test_the_state_anchor_resolves_independently_of_the_runner(self):
        touch(self.root, "methodology", "SESSION_RUNNER.md")
        touch(self.root, "CHANGELOG.md")
        self.assertEqual(lr.resolve_layout(self.root)[0], "new")
        kind, directory, _ = lr.resolve_layout(self.root, "CHANGELOG.md")
        self.assertEqual((kind, directory), ("legacy", self.root))

    def test_a_directory_named_like_the_anchor_does_not_count(self):
        (self.root / "SESSION_RUNNER.md").mkdir()
        self.assertEqual(lr.resolve_layout(self.root)[0], "none")

    def test_an_unrelated_methodology_directory_is_not_a_layout(self):
        touch(self.root, "methodology", "notes.txt")
        touch(self.root, "SESSION_RUNNER.md")
        self.assertEqual(lr.resolve_layout(self.root)[:2], ("legacy", self.root))

    def test_a_string_root_is_accepted(self):
        touch(self.root, "SESSION_RUNNER.md")
        self.assertEqual(lr.resolve_layout(str(self.root))[0], "legacy")


class TestTheFrameworkAnchorDecidesATie(Scratch):
    """Decided 2026-10-06 (S275 close-out picker, plan 7.2a) for the ledger, and 2026-10-07 (S276 close-out
    picker, plan 7.2b) for every file: a project whose SESSION_RUNNER.md is under methodology/ keeps its
    methodology files there, and a same-named file at the root is the project's own, which the methodology
    tools leave alone: the ledger beside a product changelog, the ratchet's manifest, the budget gate's
    config. It is not a request a caller makes. The resolver takes no argument for it, so a tool cannot
    forget to ask (the S276 build asked in the tools that read a ledger and not in the ratchet, and that
    difference is what he overruled)."""

    ANCHORS = ("CHANGELOG.md", "HANDOFFS.md", ".quality-gates.json", ".context-budget.json")

    def both(self, anchor, runner="methodology"):
        touch(self.root, anchor)
        touch(self.root, "methodology", anchor)
        if runner in ("methodology", "both"):
            touch(self.root, "methodology", "SESSION_RUNNER.md")
        if runner in ("root", "both"):
            touch(self.root, "SESSION_RUNNER.md")

    def decided(self, anchor):
        kind, directory, found = lr.resolve_layout(self.root, anchor)
        self.assertEqual((kind, directory), ("new", self.root / "methodology"))
        self.assertEqual(set(found), {self.root / anchor, self.root / "methodology" / anchor},
                         "found names both, so a caller can say which root file it is leaving alone")

    def test_a_ledger_in_both_places_with_the_runner_under_methodology_is_the_new_layout(self):
        self.both("CHANGELOG.md")
        self.decided("CHANGELOG.md")

    def test_the_receipts_ledger_is_decided_the_same_way(self):
        self.both("HANDOFFS.md")
        self.decided("HANDOFFS.md")

    def test_a_manifest_in_both_places_is_the_methodology_one_when_the_runner_is_there(self):
        # S276's picker: the ratchet works inside methodology/ and a root manifest is the user's own.
        self.both(".quality-gates.json")
        self.decided(".quality-gates.json")

    def test_the_budget_gates_config_is_decided_the_same_way(self):
        self.both(".context-budget.json")
        self.decided(".context-budget.json")

    def test_the_resolver_takes_no_request_for_the_rule(self):
        import inspect
        self.assertEqual(list(inspect.signature(lr.resolve_layout).parameters), ["root", "anchor"])

    def test_a_file_in_both_places_with_no_runner_under_methodology_stays_refused(self):
        for anchor in self.ANCHORS:
            for runner in (None, "root", "both"):
                with self.subTest(anchor=anchor, runner=runner):
                    with tempfile.TemporaryDirectory() as td:
                        self.root = Path(td)
                        self.both(anchor, runner)
                        self.assertEqual(lr.resolve_layout(self.root, anchor)[:2], ("half", None))

    def test_the_framework_anchor_cannot_decide_against_itself(self):
        touch(self.root, "SESSION_RUNNER.md")
        touch(self.root, "methodology", "SESSION_RUNNER.md")
        self.assertEqual(lr.resolve_layout(self.root)[:2], ("half", None))
        self.assertEqual(lr.resolve_layout(self.root, "SESSION_RUNNER.md")[:2], ("half", None))

    def test_every_other_shape_answers_by_the_four_rows(self):
        runner, new_runner = ("SESSION_RUNNER.md",), ("methodology", "SESSION_RUNNER.md")
        ledger, new_ledger = ("CHANGELOG.md",), ("methodology", "CHANGELOG.md")
        for shape, kind in (([], "none"), ([runner], "none"), ([new_runner], "none"),
                            ([new_runner, ledger], "legacy"),       # tier 1: the ledger stays at the root
                            ([new_runner, new_ledger], "new"),
                            ([runner, ledger], "legacy"),
                            ([runner, new_ledger], "new"),
                            ([runner, new_runner, ledger, new_ledger], "half")):   # two runners: no anchor decides
            with self.subTest(shape=shape):
                with tempfile.TemporaryDirectory() as td:
                    for part in shape:
                        touch(td, *part)
                    self.assertEqual(lr.resolve_layout(td, "CHANGELOG.md")[0], kind)

    def test_the_tier_1_tree_still_reads_legacy_for_the_ledger(self):
        # The runner moved and the ledger did not (plan 4.6): there is no tie, so the rule is not reached.
        touch(self.root, "methodology", "SESSION_RUNNER.md")
        touch(self.root, "CHANGELOG.md")
        self.assertEqual(lr.resolve_layout(self.root, "CHANGELOG.md")[:2], ("legacy", self.root))


class TestEveryEmbeddedCopyIsByteIdentical(unittest.TestCase):
    """Each shipped tool that resolves the layout carries the module's block, byte for byte (plan 4.3).
    A copy that drifted is a second resolver with its own answers. P2 embeds it in the ratchet; each
    later phase appends the tool it touches to COPIES (the dashboard, the trimmer, the budget gate)."""

    COPIES = ("starter-kit/context_budget.py", "starter-kit/methodology_dashboard.py", "starter-kit/methodology_trim.py",
              "starter-kit/quality_ratchet.py",   # the gate layer, the trimmer, the budget gate and the dashboard (its tools/ twin is asserted below)
              "bin/sync", "bin/status", "bin/check-links")   # the sync layer; each later layer appends the tools it carries

    def test_each_copy_equals_the_modules_block_and_carries_exactly_one(self):
        block = lr.embedded_block((HERE / "layout_resolver.py").read_text(encoding="utf-8"))
        for rel in self.COPIES:
            text = (REPO / rel).read_text(encoding="utf-8")
            self.assertEqual(text.count(lr.BEGIN), 1, rel + ": one BEGIN marker")
            self.assertEqual(lr.embedded_block(text), block, rel + ": the block differs from tools/layout_resolver.py")

    def test_the_dashboards_canonical_only_twin_carries_the_same_block(self):
        # tools/methodology_dashboard.py is scanned for the markers by no directory walk below (that one reads
        # starter-kit/ and bin/), and the dashboard suite loads THIS copy, so a block that reached only the
        # starter-kit/ copy would pass the list above and leave the tested file without a resolver.
        block = lr.embedded_block((HERE / "layout_resolver.py").read_text(encoding="utf-8"))
        text = (HERE / "methodology_dashboard.py").read_text(encoding="utf-8")
        self.assertEqual(text.count(lr.BEGIN), 1, "tools/methodology_dashboard.py: one BEGIN marker")
        self.assertEqual(lr.embedded_block(text), block, "tools/methodology_dashboard.py: the block differs")

    def test_every_tool_that_carries_the_markers_is_listed(self):
        def carries(p):
            try:
                return lr.BEGIN in p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                return False
        carriers = sorted(str(p.relative_to(REPO)) for d in ("starter-kit", "bin")
                          for p in (REPO / d).iterdir() if p.is_file() and carries(p))
        self.assertEqual(carriers, sorted(self.COPIES),
                         "a shipped tool embeds the block but its copy is not asserted here")


class TestTheBlockIsEmbeddable(Scratch):
    """Shipped tools are single stdlib files, so each carries the same marked block (section 4.3)."""

    def setUp(self):
        super().setUp()
        self.source = (HERE / "layout_resolver.py").read_text(encoding="utf-8")
        self.block = lr.embedded_block(self.source)

    def test_the_module_carries_one_marked_block(self):
        self.assertIsNotNone(self.block)
        self.assertTrue(self.block.startswith(lr.BEGIN))
        self.assertTrue(self.block.rstrip("\n").endswith(lr.END))
        self.assertEqual(self.source.count(lr.BEGIN), 1)
        self.assertEqual(self.source.count(lr.END), 1)

    def test_the_block_runs_alone_and_answers_the_four_rows(self):
        ns = {}
        exec(compile(self.block, "<block>", "exec"), ns)
        resolve = ns["resolve_layout"]
        self.assertEqual(resolve(self.root)[0], "none")
        touch(self.root, "SESSION_RUNNER.md")
        self.assertEqual(resolve(self.root)[0], "legacy")
        touch(self.root, "methodology", "SESSION_RUNNER.md")
        self.assertEqual(resolve(self.root)[0], "half")
        (self.root / "SESSION_RUNNER.md").unlink()
        self.assertEqual(resolve(self.root)[0], "new")

    def test_the_block_agrees_with_the_module_on_every_tree_shape(self):
        ns = {}
        exec(compile(self.block, "<block>", "exec"), ns)
        tie = [("methodology", "SESSION_RUNNER.md"), ("CHANGELOG.md",), ("methodology", "CHANGELOG.md")]
        for shapes in ([], [("SESSION_RUNNER.md",)], [("methodology", "SESSION_RUNNER.md")],
                       [("SESSION_RUNNER.md",), ("methodology", "SESSION_RUNNER.md")], tie,
                       [("CHANGELOG.md",), ("methodology", "CHANGELOG.md")]):
            with tempfile.TemporaryDirectory() as td:
                for s in shapes:
                    touch(td, *s)
                self.assertEqual(ns["resolve_layout"](td), lr.resolve_layout(td))
                for anchor in ("CHANGELOG.md", ".quality-gates.json"):
                    self.assertEqual(ns["resolve_layout"](td, anchor), lr.resolve_layout(td, anchor), (shapes, anchor))

    def test_the_block_imports_only_the_standard_library(self):
        import ast
        mods = set()
        for node in ast.walk(ast.parse(self.block)):
            if isinstance(node, ast.Import):
                mods.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                mods.add((node.module or "").split(".")[0])
        self.assertLessEqual(mods, {"os", "pathlib"})

    def test_embedded_block_finds_a_copy_inside_another_file(self):
        host = "import sys\n\n" + self.block + "\n\ndef main():\n    pass\n"
        self.assertEqual(lr.embedded_block(host), self.block)

    def test_embedded_block_is_none_without_markers_and_refuses_unbalanced_ones(self):
        self.assertIsNone(lr.embedded_block("import sys\n"))
        with self.assertRaises(ValueError):
            lr.embedded_block(lr.BEGIN + "\nx = 1\n")
        with self.assertRaises(ValueError):
            lr.embedded_block(self.block + "\n" + self.block)


# The plan's section 4.1, typed out: the one place the target layout is written as literals, so a change to
# the manifest cannot quietly reshape what "the new layout" means. 34 files, none of them at the root.
S41_FRAMEWORK = ["SESSION_RUNNER.md", "SAFEGUARDS.md", "FRAMEWORK_LEARNINGS.md", "RECOMMENDED_SKILLS.md",
                 "BOOTSTRAP.md", "CONTEXT_TEMPLATE.md", "CLAUDE_TEMPLATE.md",
                 "ITERATIVE_METHODOLOGY.md", "FRAMEWORK_APPARATUS.md", "HOW_TO_USE.md",
                 "methodology_dashboard.py", "methodology_trim.py", "context_budget.py", "quality_ratchet.py"]
S41_WORKSTREAMS = ["DESIGN_WORKSTREAM.md", "ARCHITECTURE_WORKSTREAM.md", "DEVELOPMENT_WORKSTREAM.md",
                   "AUDIT_WORKSTREAM.md", "RESEARCH_DOCUMENTATION_WORKSTREAM.md", "TEMPLATE_WORKSTREAM.md",
                   "RESEARCH_EXHAUSTIVE_VERIFICATION_CAMPAIGN.md",
                   "INHERITED_CODEBASE_FAMILIARIZATION_CAMPAIGN.md", "TEMPLATE_CAMPAIGN.md"]
S41_STATE = ["SESSION_NOTES.md", "CHANGELOG.md", "HANDOFFS.md", "ROADMAP.md",
             ".context-budget.json", ".quality-gates.json", ".gitattributes"]
S41_GENERATED = ["dashboard.html", "dashboard_history.jsonl", ".context-budget-history.jsonl",
                 ".quality-gates-results.json"]


class TestFixtureTrees(Scratch):
    """Trees in both layouts, built from the manifest, for every later phase to reuse."""

    def build(self, layout, **kw):
        return set(lf.build_tree(self.root, layout, **kw))

    def test_the_new_tree_is_exactly_section_4_1(self):
        want = {"methodology/" + n for n in S41_FRAMEWORK + S41_STATE + S41_GENERATED}
        want |= {"methodology/workstreams/" + n for n in S41_WORKSTREAMS}
        self.assertEqual(self.build("new"), want)
        self.assertEqual(len(want), 34)

    def test_the_legacy_tree_is_the_manifest_plus_the_generated_files(self):
        manifest = _load("_manifest", REPO / "bin" / "_manifest.py")
        want = {dest for _, dest, _ in manifest.DISTRIBUTION} | set(S41_GENERATED)
        self.assertEqual(self.build("legacy"), want)

    def test_the_legacy_tree_is_what_bin_sync_writes_into_a_project(self):
        # Faithfulness (gate d): a fixture that no real adopter looks like proves nothing about adopters.
        import subprocess
        project = self.root / "real"
        project.mkdir()
        subprocess.run(["git", "init", "-q", str(project)], check=True)
        r = subprocess.run([sys.executable, "-B", str(REPO / "bin" / "sync"), "--source=local", str(project)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        synced = {p.relative_to(project).as_posix() for p in project.rglob("*")
                  if p.is_file() and ".git" not in p.relative_to(project).parts}
        fixture_root = self.root / "fixture"
        fixture_root.mkdir()
        built = set(lf.build_tree(fixture_root, "legacy", generated=False))
        self.assertEqual(built, synced)

    def test_the_tier_1_tree_moves_only_what_the_manifest_tracks(self):
        built = self.build("tier1")
        want = {"methodology/" + n for n in S41_FRAMEWORK} | \
               {"methodology/workstreams/" + n for n in S41_WORKSTREAMS} | set(S41_STATE) | set(S41_GENERATED)
        self.assertEqual(built, want)
        self.assertEqual(lr.resolve_layout(self.root)[0], "new")
        self.assertEqual(lr.resolve_layout(self.root, "CHANGELOG.md")[:2], ("legacy", self.root))

    def test_the_half_tree_has_the_runner_in_both_places(self):
        built = self.build("half")
        self.assertIn("SESSION_RUNNER.md", built)
        self.assertIn("methodology/SESSION_RUNNER.md", built)
        self.assertEqual(lr.resolve_layout(self.root)[0], "half")

    def test_the_empty_tree_has_no_files(self):
        self.assertEqual(self.build("empty"), set())
        self.assertEqual(lr.resolve_layout(self.root)[0], "none")

    def test_both_anchors_agree_on_the_two_pure_layouts(self):
        for layout, kind in (("legacy", "legacy"), ("new", "new")):
            with tempfile.TemporaryDirectory() as td:
                lf.build_tree(td, layout)
                for anchor in ("SESSION_RUNNER.md", "CHANGELOG.md", ".quality-gates.json"):
                    self.assertEqual(lr.resolve_layout(td, anchor)[0], kind, (layout, anchor))

    def test_the_archive_follows_its_tier(self):
        self.assertTrue(any(p.startswith("docs/archive/") for p in self.build("legacy", archive=True)))
        with tempfile.TemporaryDirectory() as td:
            self.assertTrue(any(p.startswith("methodology/archive/") for p in lf.build_tree(td, "new", archive=True)))
        with tempfile.TemporaryDirectory() as td:
            # tier 2 moves the archive, so a tier-1 tree keeps it where it was
            self.assertTrue(any(p.startswith("docs/archive/") for p in lf.build_tree(td, "tier1", archive=True)))

    def test_the_manifests_table_maps_the_three_kinds_of_destination(self):
        # was lf.new_path, a rule of this module's own; P6 made the manifest's NEW_LAYOUT the one table
        table = _load("_manifest", REPO / "bin" / "_manifest.py").NEW_LAYOUT
        self.assertEqual(table["starter-kit/CHANGELOG.md"], "methodology/CHANGELOG.md")
        self.assertEqual(table["HOW_TO_USE.md"], "methodology/HOW_TO_USE.md")
        self.assertEqual(table["workstreams/DESIGN_WORKSTREAM.md"], "methodology/workstreams/DESIGN_WORKSTREAM.md")

    def test_contents_override_by_file_name(self):
        lf.build_tree(self.root, "new", contents={"CHANGELOG.md": "# my ledger\n"})
        self.assertEqual((self.root / "methodology" / "CHANGELOG.md").read_text(encoding="utf-8"), "# my ledger\n")
        self.assertNotEqual((self.root / "methodology" / "HANDOFFS.md").read_text(encoding="utf-8"), "# my ledger\n")

    def test_it_refuses_to_build_into_a_non_empty_directory_or_an_unknown_layout(self):
        touch(self.root, "keep.txt")
        with self.assertRaises(ValueError):
            lf.build_tree(self.root, "new")
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                lf.build_tree(td, "sideways")

    def test_every_path_stays_inside_the_root(self):
        for layout in lf.LAYOUTS:
            with tempfile.TemporaryDirectory() as td:
                for rel in lf.build_tree(td, layout, archive=True):
                    self.assertFalse(rel.startswith(("/", "..")) or ".." in Path(rel).parts, rel)
                    self.assertTrue((Path(td) / rel).is_file(), rel)


PY_TOOL = '''"""A docstring that names CHANGELOG.md is prose, not a read."""
# a comment naming HANDOFFS.md is prose too
from pathlib import Path
LEDGER = Path(".") / "CHANGELOG.md"
MSG = "error: HANDOFFS.md is missing"
ACKED = "SESSION_NOTES.md"  # layout: ok -- a label printed in a report, never opened
UNREASONED = "ROADMAP.md"  # layout: ok
SRC = "starter-kit/SESSION_RUNNER.md"
DOC = "docs/methodology/HOW_TO_USE.md"
DIR = "docs/methodology"
NEW = "methodology/CHANGELOG.md"
URL = "https://github.com/KJ5HST/methodology/blob/main/README.md"
RX = r"CHANGELOG\.md"
F = f"{Path('.')}/HANDOFFS.md"
CFG = ".quality-gates.json"
# --- layout resolver: BEGIN ---
BLOCK = ("SESSION_RUNNER.md", "methodology")
# --- layout resolver: END ---
'''

SH_TOOL = '''#!/bin/bash
# CHANGELOG.md in a comment is prose
git ls-files --error-unmatch CHANGELOG.md   # trailing comment naming HANDOFFS.md
echo "see $top/HANDOFFS.md"
cp starter-kit/CHANGELOG.md /dev/null
msg='a # inside quotes is not a comment, CHANGELOG.md'
'''


def site_lines(sites):
    return sorted(s.line for s in sites)


class TestTheScannerReadsCode(unittest.TestCase):
    """Section 7.1: list every line that names a methodology file's root path in a shipped tool."""

    def setUp(self):
        self.sites, self.acked, self.prose, self.problems = cll.scan_text("starter-kit/t.py", PY_TOOL)
        self.by_line = {s.line: s for s in self.sites}
        self.src = PY_TOOL.split("\n")

    def line_of(self, needle):
        hits = [i + 1 for i, l in enumerate(self.src) if l.startswith(needle)]
        self.assertEqual(len(hits), 1, needle)
        return hits[0]

    def test_a_path_literal_is_a_site(self):
        s = self.by_line[self.line_of("LEDGER")]
        self.assertEqual((s.shape, s.names), ("path", ("CHANGELOG.md",)))
        self.assertIn("bare", s.kinds)

    def test_a_message_that_names_a_file_is_a_site_marked_text(self):
        self.assertEqual(self.by_line[self.line_of("MSG")].shape, "text")

    def test_docstrings_and_comments_are_prose_not_sites(self):
        for needle in ("PY_TOOL", '"""A docstring'):
            self.assertNotIn(1, self.by_line)
        self.assertNotIn(2, self.by_line)
        self.assertEqual({p.line for p in self.prose}, {1, 2})

    def test_the_canonical_source_path_is_not_a_root_literal(self):
        self.assertNotIn(self.line_of("SRC"), self.by_line)

    def test_a_layout_path_is_a_site(self):
        self.assertIn("layout-path", self.by_line[self.line_of("DOC")].kinds)
        self.assertEqual(self.by_line[self.line_of("DIR")].kinds, ("layout-path",))

    def test_a_hardcoded_new_layout_path_is_a_site(self):
        self.assertIn("new-path", self.by_line[self.line_of("NEW")].kinds)

    def test_a_url_that_contains_methodology_is_not_a_site(self):
        self.assertNotIn(self.line_of("URL"), self.by_line)

    def test_the_regex_form_and_the_fstring_form_are_sites(self):
        self.assertIn(self.line_of("RX"), self.by_line)
        self.assertIn(self.line_of("F ="), self.by_line)

    def test_a_dotfile_name_is_found(self):
        self.assertEqual(self.by_line[self.line_of("CFG")].names, (".quality-gates.json",))

    def test_a_marker_with_a_reason_acknowledges_the_site(self):
        n = self.line_of("ACKED")
        self.assertNotIn(n, self.by_line)
        self.assertEqual([a.line for a in self.acked], [n])

    def test_a_marker_without_a_reason_acknowledges_nothing(self):
        s = self.by_line[self.line_of("UNREASONED")]
        self.assertIn("reason", s.note)

    def test_the_resolver_block_is_exempt(self):
        n = self.line_of("BLOCK")
        self.assertNotIn(n, self.by_line)
        self.assertNotIn(n, {p.line for p in self.prose})

    def test_exactly_the_expected_sites_are_reported(self):
        want = [self.line_of(k) for k in ("LEDGER", "MSG", "UNREASONED", "DOC", "DIR", "NEW", "RX", "F =", "CFG")]
        self.assertEqual(site_lines(self.sites), sorted(want))
        self.assertEqual(self.problems, [])

    def test_a_python_file_that_does_not_parse_is_a_problem_never_a_silent_skip(self):
        sites, acked, prose, problems = cll.scan_text("starter-kit/bad.py", "def (:\n")
        self.assertEqual(sites, [])
        self.assertEqual(len(problems), 1)
        self.assertIn("starter-kit/bad.py", problems[0])

    def test_unbalanced_resolver_markers_are_a_problem(self):
        text = "# --- layout resolver: " + "BEGIN ---\nx = 1\n"
        self.assertEqual(len(cll.scan_text("starter-kit/t.py", text)[3]), 1)


class TestWhatIsNotAMethodologyFileName(unittest.TestCase):
    """A URL to a methodology file, and a different file whose name merely contains one, are not sites.
    Added because two scanner mutants (URLs not excluded, the name's left boundary loosened) survived
    a suite that had no such case."""

    NOT_SITES = (
        'U = "https://github.com/KJ5HST/methodology/blob/main/CHANGELOG.md"\n'
        'V = "https://raw.githubusercontent.com/o/r/main/HANDOFFS.md"\n'
        'W = "BACKUP-CHANGELOG.md"\n'
        'X = "old.HANDOFFS.md"\n'
        'Y = "test_methodology_dashboard.py"\n'
        'Z = "README.md"\n'
    )

    def test_none_of_these_is_a_site(self):
        self.assertEqual(cll.scan_text("starter-kit/t.py", self.NOT_SITES)[0], [])

    def test_the_same_names_standing_alone_are_sites(self):
        text = 'A = "CHANGELOG.md"\nB = "HANDOFFS.md"\nC = "methodology_dashboard.py"\n'
        self.assertEqual(site_lines(cll.scan_text("starter-kit/t.py", text)[0]), [1, 2, 3])


class TestTheCanonicalDirectoryMayBeASeparateConstant(unittest.TestCase):
    """`root / "starter-kit" / "NAME"` and os.path.join(root, "tools", "NAME") name the canonical repository's own
    layout exactly as "starter-kit/NAME" does, but the directory is its own constant. Found by reading the first
    real run, which flagged bin/check-learnings:125."""

    JOINED = (
        'A = ROOT / "starter-kit" / "SESSION_RUNNER.md"\n'
        'B = os.path.join(root, "tools", "methodology_dashboard.py")\n'
        'C = Path("starter-kit") / "BOOTSTRAP.md"\n'
        'D = ROOT / "CHANGELOG.md"\n'
    )

    def test_only_the_root_relative_join_is_a_site(self):
        sites = cll.scan_text("bin/x", "#!/usr/bin/env python3\n" + self.JOINED)[0]
        self.assertEqual(site_lines(sites), [5])

    def test_the_archive_directory_is_a_layout_path_because_trims_write_shards_there(self):
        sites = cll.scan_text("starter-kit/t.py", 'ARCHIVE_DIR = "docs/archive"\nSRC = "starter-kit/SAFEGUARDS.md"\n')[0]
        self.assertEqual([(x.line, x.kinds) for x in sites], [(1, ("layout-path",))])


class TestTheScannerReadsShell(unittest.TestCase):
    def setUp(self):
        self.sites, self.acked, self.prose, self.problems = cll.scan_text(".githooks/pre-commit", SH_TOOL)

    def test_a_command_that_names_a_ledger_is_a_site(self):
        self.assertIn(3, site_lines(self.sites))

    def test_a_variable_prefixed_path_is_a_root_literal(self):
        self.assertIn(4, site_lines(self.sites))

    def test_comments_are_prose_and_a_hash_inside_quotes_is_not_a_comment(self):
        self.assertEqual(site_lines(self.sites), [3, 4, 6])
        self.assertEqual({p.line for p in self.prose}, {2, 3})

    def test_the_canonical_source_prefix_is_not_a_root_literal(self):
        self.assertNotIn(5, site_lines(self.sites))

    def test_a_name_standing_alone_is_a_path_and_a_name_in_a_sentence_is_text(self):
        text = ("#!/bin/bash\n"
                "git ls-files --error-unmatch CHANGELOG.md\n"
                "git cat-file -e HEAD:CHANGELOG.md\n"
                'cat > "$top/HANDOFFS.md"\n'
                "echo That is methodology_trim.py's job\n"
                "echo Prepend an entry to CHANGELOG.md.\n")
        sites = cll.scan_text(".githooks/h", text)[0]
        self.assertEqual({s.line: s.shape for s in sites}, {2: "path", 3: "path", 4: "path", 5: "text", 6: "text"})


class TestTheScanSet(Scratch):
    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def test_the_shipped_tools_are_scanned_and_the_table_and_the_suite_are_not(self):
        self.write("starter-kit/a.py", 'X = "CHANGELOG.md"\n')
        self.write("bin/tool", '#!/usr/bin/env python3\nX = "HANDOFFS.md"\n')
        self.write("bin/tests.sh", '#!/bin/bash\necho CHANGELOG.md\n')
        self.write("bin/_manifest.py", 'X = "CHANGELOG.md"\n')
        self.write(".githooks/pre-commit", '#!/bin/bash\necho CHANGELOG.md\n')
        self.write("tools/test_x.py", 'X = "CHANGELOG.md"\n')
        self.write("starter-kit/notes.md", 'CHANGELOG.md\n')
        report = cll.scan_root(self.root)
        self.assertEqual(sorted(report["files"]), [".githooks/pre-commit", "bin/tool", "starter-kit/a.py"])
        self.assertEqual(sorted({s.file for s in report["sites"]}), [".githooks/pre-commit", "bin/tool", "starter-kit/a.py"])
        self.assertIn("bin/tests.sh", report["not_scanned"])
        self.assertIn("bin/_manifest.py", report["not_scanned"])

    def test_a_byte_identical_dashboard_twin_is_scanned_once(self):
        self.write("starter-kit/methodology_dashboard.py", 'X = "CHANGELOG.md"\n')
        self.write("tools/methodology_dashboard.py", 'X = "CHANGELOG.md"\n')
        report = cll.scan_root(self.root)
        self.assertEqual(report["files"], ["starter-kit/methodology_dashboard.py"])
        self.assertTrue(any("tools/methodology_dashboard.py" in n for n in report["not_scanned"]))

    def test_a_dashboard_twin_that_differs_is_scanned_too(self):
        self.write("starter-kit/methodology_dashboard.py", 'X = "CHANGELOG.md"\n')
        self.write("tools/methodology_dashboard.py", 'X = "HANDOFFS.md"\n')
        self.assertEqual(sorted(cll.scan_root(self.root)["files"]),
                         ["starter-kit/methodology_dashboard.py", "tools/methodology_dashboard.py"])

    def test_this_repository_scans_the_tools_it_names_and_parses_cleanly(self):
        report = cll.scan_root(REPO)
        for name in ("starter-kit/methodology_dashboard.py", "starter-kit/methodology_trim.py",
                     ".githooks/pre-commit", "bin/check-handoff"):
            self.assertIn(name, report["files"])
        self.assertEqual(report["problems"], [])


class TestToolsAlreadyResolvedStayAtZero(unittest.TestCase):
    """A tool that phase P2-P5 has worked scans at zero unacknowledged sites, and stays there: the
    scanner is not a gate until P6, so this is what stops a later edit putting a root literal back.
    Each phase appends the tools it resolved; P6 replaces the list with the gate."""

    RESOLVED = (".githooks/pre-commit", "starter-kit/quality_ratchet.py",   # the gate layer
                "starter-kit/methodology_trim.py",   # the trimmer
                "starter-kit/context_budget.py",   # the budget gate
                "starter-kit/methodology_dashboard.py")   # the dashboard: its tools/ twin is the same bytes; each later layer appends the tools it resolves

    def test_each_resolved_tool_reports_no_site(self):
        for rel in self.RESOLVED:
            sites, _acked, _prose, problems = cll.scan_text(rel, (REPO / rel).read_text(encoding="utf-8"))
            self.assertEqual(problems, [], rel)
            self.assertEqual([(s.line, s.text) for s in sites], [], rel + " names a root path again")


class TestTheScannerCommand(Scratch):
    CMD = [sys.executable, "-B", str(REPO / "bin" / "check-layout-literals")]

    def run_cmd(self, *args):
        import subprocess
        return subprocess.run(self.CMD + list(args), capture_output=True, text=True)

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def test_exit_1_and_the_list_when_a_tool_holds_a_root_literal(self):
        self.write("starter-kit/a.py", 'X = "CHANGELOG.md"\n')
        r = self.run_cmd("--root", str(self.root))
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("starter-kit/a.py:1", r.stdout)
        self.assertIn("CHANGELOG.md", r.stdout)

    def test_exit_0_when_every_site_is_resolved_or_acknowledged(self):
        self.write("starter-kit/a.py", 'X = "CHANGELOG.md"  # layout: ok -- a label, never opened\n')
        r = self.run_cmd("--root", str(self.root))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("1 acknowledged", r.stdout)

    def test_exit_2_when_nothing_was_scanned_so_a_wrong_root_cannot_read_green(self):
        r = self.run_cmd("--root", str(self.root))
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("0 files", r.stdout + r.stderr)

    def test_exit_2_and_the_file_named_when_a_tool_does_not_parse(self):
        self.write("starter-kit/a.py", 'X = "CHANGELOG.md"\n')
        self.write("starter-kit/bad.py", "def (:\n")
        r = self.run_cmd("--root", str(self.root))
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("starter-kit/bad.py", r.stdout + r.stderr)

    def test_all_adds_the_prose_and_the_acknowledged_lines(self):
        self.write("starter-kit/a.py", '"""CHANGELOG.md in a docstring."""\nX = "HANDOFFS.md"  # layout: ok -- a label\nY = "ROADMAP.md"\n')
        plain = self.run_cmd("--root", str(self.root)).stdout
        full = self.run_cmd("--root", str(self.root), "--all").stdout
        self.assertNotIn("docstring", plain)
        self.assertIn("docstring", full)
        self.assertIn("a label", full)

    def test_the_summary_line_counts_sites_files_acknowledged_and_prose(self):
        self.write("starter-kit/a.py", '"""CHANGELOG.md"""\nX = "HANDOFFS.md"\nY = "ROADMAP.md"  # layout: ok -- label\n')
        out = self.run_cmd("--root", str(self.root)).stdout
        self.assertIn("1 file", out)
        self.assertIn("1 site", out)
        self.assertIn("1 acknowledged", out)
        self.assertIn("1 prose", out)


class TestCanonicalOnly(unittest.TestCase):
    def test_the_resolver_is_not_distributed(self):
        manifest = _load("_manifest", REPO / "bin" / "_manifest.py")
        names = {Path(p).name for row in manifest.DISTRIBUTION for p in row[:2]}
        self.assertNotIn("layout_resolver.py", names)
        self.assertNotIn("test_layout_resolver.py", names)


if __name__ == "__main__":
    unittest.main()
