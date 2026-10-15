#!/usr/bin/env python3
"""Unit tests for the sync layer in both layouts.

CANONICAL-ONLY, like tools/test_layout_resolver.py and tools/test_checker_layouts.py: bin/sync,
bin/status and bin/check-links are not in bin/_manifest.py, so adopters do not receive them. The
contract: no blank seed beside a real ledger and no second runner, ignore mode, status and
check-links following the layout, and the manifest staying data so --source=github can read it.

Layer 0 (this file's first classes): the manifest's second literal table, NEW_LAYOUT, and the reader
that reads it as data. Later layers add bin/sync, bin/status and bin/check-links, each driven as a
command in a scratch project. Every rule is observed failing as well as passing (Learning #12).
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True  # a test run must not generate bin/__pycache__ or tools/__pycache__

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
MANIFEST = REPO / "bin" / "_manifest.py"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


manifest = _load("_manifest", MANIFEST)
reader = _load("_manifest_reader", REPO / "bin" / "_manifest_reader.py")
lf = _load("layout_fixtures", HERE / "layout_fixtures.py")
lr = _load("layout_resolver", HERE / "layout_resolver.py")
tlr = _load("test_layout_resolver", HERE / "test_layout_resolver.py")  # the target layout, typed out as literals

DISPOSITIONS = (manifest.TRACKED, manifest.SEED)
SYNC = REPO / "bin" / "sync"
STATUS = REPO / "bin" / "status"
CHECK_LINKS = REPO / "bin" / "check-links"
LITERALS = REPO / "bin" / "check-layout-literals"
LEGACY = {dest for _s, dest, _d in manifest.DISTRIBUTION}
NEW = set(manifest.NEW_LAYOUT.values())
SEED_SRCS = [src for src, _dest, disp in manifest.DISTRIBUTION if disp == manifest.SEED]
TRACKED_SRCS = [src for src, _dest, disp in manifest.DISTRIBUTION if disp == manifest.TRACKED]


def git(path, *args):
    subprocess.run(["git", "-C", str(path), "-c", "user.email=t@t", "-c", "user.name=t", "-c", "commit.gpgsign=false", *args],
                   check=True, capture_output=True)


def files_of(project):
    """Every file in a project tree as a set of POSIX paths, .git left out."""
    root = Path(project)
    return {p.relative_to(root).as_posix() for p in root.rglob("*")
            if p.is_file() and ".git" not in p.relative_to(root).parts}


def run_sync(project, *args, source=None):
    """bin/sync as a command; returns the CompletedProcess with stdout and stderr joined in .out."""
    env = dict(os.environ)
    env.pop("METHODOLOGY_SOURCE_URL", None)
    if source is not None:
        env["METHODOLOGY_SOURCE_URL"] = "file://" + str(source)
    r = subprocess.run([sys.executable, "-B", str(SYNC), str(project), *args], capture_output=True, text=True, env=env)
    r.out = r.stdout + r.stderr
    return r


def run_status(*projects, source=None, github=False):
    """bin/status as a command. Returns the CompletedProcess with .out, .rows (the table's rows as
    (project, file, disposition, status)) and .layouts ({project name: the text after its `layout:` name})."""
    env = dict(os.environ)
    env.pop("METHODOLOGY_SOURCE_URL", None)
    if source is not None:
        env["METHODOLOGY_SOURCE_URL"] = "file://" + str(source)
    args = ["--source=github"] if github or source is not None else []
    r = subprocess.run([sys.executable, "-B", str(STATUS), *args, *map(str, projects)], capture_output=True, text=True, env=env)
    r.out = r.stdout + r.stderr
    lines = r.stdout.splitlines()
    r.layouts = {}
    for line in lines:
        if line.startswith("layout: "):
            name, _, rest = line[len("layout: "):].partition("  ")
            r.layouts[name] = rest.strip()
    r.rows = []
    if any(line.startswith("Project ") for line in lines):
        header = next(i for i, line in enumerate(lines) if line.startswith("Project "))
        for line in lines[header + 1:]:
            if not line.strip():
                break
            r.rows.append(tuple(cell.strip() for cell in line.split(None, 3)))
    return r


def scratch_canonical(root, docs):
    """A tiny canonical repository: the real bin/check-links and bin/_manifest.py, and a one-line markdown stub at
    every distributed source, with `docs` (src -> text) replacing the stubs it names. Returns its bin/check-links.
    check-links resolves its repository from its own path, so this is how a test chooses what the docs say."""
    root = Path(root)
    (root / "bin").mkdir(parents=True)
    for name in ("check-links", "_manifest.py"):
        shutil.copyfile(REPO / "bin" / name, root / "bin" / name)
    for src, _dest, _disp in manifest.DISTRIBUTION:
        (root / src).parent.mkdir(parents=True, exist_ok=True)
        (root / src).write_text(docs.get(src, "# stub\n"), encoding="utf-8")
    return root / "bin" / "check-links"


def run_check_links(script, *args):
    r = subprocess.run([sys.executable, "-B", str(script), *args], capture_output=True, text=True)
    r.out = r.stdout + r.stderr
    return r


_BASES = {}


def base_tree(kind):
    """A project synced once by the real bin/sync, built the first time it is asked for and copied afterwards
    (a run is about a second): "legacy" is what sync writes today, "new" is --layout new on an empty project."""
    if kind not in _BASES:
        keep = tempfile.mkdtemp(prefix="sync-base-")
        project = Path(keep) / kind
        project.mkdir()
        git(project, "init", "-q")
        r = run_sync(project, *(("--layout", "new") if kind == "new" else ()))
        assert r.returncode == 0, "the %s base tree could not be built:\n%s" % (kind, r.out)
        _BASES[kind] = project
    return _BASES[kind]


def tearDownModule():
    for project in _BASES.values():
        shutil.rmtree(project.parent, ignore_errors=True)


def section_4_1_destinations():
    """The new destination of every distributed file, from the target layout as
    tools/test_layout_resolver.py types it: flat under methodology/, workstreams/ the one subdirectory."""
    return ({"methodology/" + n for n in tlr.S41_FRAMEWORK + tlr.S41_STATE}
            | {"methodology/workstreams/" + n for n in tlr.S41_WORKSTREAMS})


class Scratch(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory(prefix="sync-layouts-")
        self.addCleanup(self._td.cleanup)
        self.root = Path(self._td.name)

    def manifest_with(self, old=None, new=None, *, name="_manifest.py"):
        """A copy of the real manifest with one unique text replaced (old -> new), written under
        a fresh directory; returns its path. The anchor must occur once, or the fixture is wrong."""
        text = MANIFEST.read_text(encoding="utf-8")
        if old is not None:
            self.assertEqual(text.count(old), 1, "fixture anchor not unique in bin/_manifest.py: %r" % old)
            text = text.replace(old, new)
        d = Path(tempfile.mkdtemp(dir=self.root))
        path = d / name
        path.write_text(text, encoding="utf-8")
        return path

    def read(self, path):
        rows, _markers = reader.read_manifest(path, DISPOSITIONS)
        return reader.read_new_layout(path, rows)

    def project(self, kind=None):
        """A fresh project directory: empty (a git repository), or a copy of the legacy or new base tree."""
        d = self.root / ("project%d" % len(list(self.root.iterdir())))
        if kind is None:
            d.mkdir()
            git(d, "init", "-q")
        else:
            shutil.copytree(base_tree(kind), d)
        return d


class TestTheManifestsSecondTable(unittest.TestCase):
    """C16: the layout-dependent destinations are a second LITERAL table, never a function, so
    --source=github reads them as data and bin/tests.sh Test 53 can still build its source from the file."""

    def test_it_names_a_new_destination_for_every_distributed_file_and_no_other(self):
        srcs = [src for src, _dest, _disp in manifest.DISTRIBUTION]
        self.assertEqual(sorted(manifest.NEW_LAYOUT), sorted(srcs))
        self.assertEqual(len(srcs), 30)

    def test_the_destinations_are_exactly_section_4_1(self):
        self.assertEqual(set(manifest.NEW_LAYOUT.values()), section_4_1_destinations())
        self.assertEqual(len(set(manifest.NEW_LAYOUT.values())), 30, "two files share one new destination")

    def test_the_workstreams_stay_one_level_down_and_everything_else_is_flat(self):
        for src, dest, _disp in manifest.DISTRIBUTION:
            want = ("methodology/workstreams/" if dest.startswith("docs/methodology/workstreams/")
                    else "methodology/") + Path(dest).name
            self.assertEqual(manifest.NEW_LAYOUT[src], want, src)

    def test_the_fixture_trees_are_built_from_the_table_not_from_a_rule_of_their_own(self):
        with tempfile.TemporaryDirectory() as td:
            built = set(lf.build_tree(td, "new", generated=False))
        self.assertEqual(built, set(manifest.NEW_LAYOUT.values()))
        self.assertFalse(hasattr(lf, "new_path"), "layout_fixtures still carries its own mapping rule")

    def test_the_tier_1_tree_moves_only_the_tracked_rows_to_the_tables_destinations(self):
        with tempfile.TemporaryDirectory() as td:
            built = set(lf.build_tree(td, "tier1", generated=False))
        want = {manifest.NEW_LAYOUT[src] if disp == manifest.TRACKED else dest
                for src, dest, disp in manifest.DISTRIBUTION}
        self.assertEqual(built, want)

    def test_the_reader_reads_the_real_table_as_data_and_it_equals_the_modules(self):
        rows, _markers = reader.read_manifest(MANIFEST, DISPOSITIONS)
        self.assertEqual(reader.read_new_layout(MANIFEST, rows), manifest.NEW_LAYOUT)


class TestTheReaderReadsTheTableAsData(Scratch):
    ROADMAP = '    "starter-kit/ROADMAP.md": "methodology/ROADMAP.md",'
    RUNNER = '    "starter-kit/SESSION_RUNNER.md": "methodology/SESSION_RUNNER.md",'

    def test_a_source_that_predates_the_table_has_none_and_is_still_readable(self):
        path = self.manifest_with("NEW_LAYOUT = {", "OTHER_LAYOUT = {")
        rows, _markers = reader.read_manifest(path, DISPOSITIONS)
        self.assertEqual(len(rows), 30)
        self.assertIsNone(reader.read_new_layout(path, rows))

    def test_the_table_is_never_run_only_read(self):
        marker = self.root / "EXECUTED"
        path = self.manifest_with("NEW_LAYOUT = {", "import pathlib; pathlib.Path(%r).touch()\nNEW_LAYOUT = {" % str(marker))
        self.assertEqual(self.read(path), manifest.NEW_LAYOUT)
        self.assertFalse(marker.exists(), "reading the manifest ran its code")

    def test_a_row_with_no_destination_is_refused_and_named(self):
        path = self.manifest_with(self.ROADMAP, "")
        with self.assertRaises(reader.ManifestError) as cm:
            self.read(path)
        self.assertIn("starter-kit/ROADMAP.md", str(cm.exception))

    def test_a_destination_for_a_file_the_manifest_does_not_distribute_is_refused_and_named(self):
        path = self.manifest_with(self.ROADMAP, self.ROADMAP + '\n    "starter-kit/GHOST.md": "methodology/GHOST.md",')
        with self.assertRaises(reader.ManifestError) as cm:
            self.read(path)
        self.assertIn("starter-kit/GHOST.md", str(cm.exception))

    def test_a_key_written_twice_is_refused_because_the_last_would_win_without_a_word(self):
        path = self.manifest_with(self.ROADMAP, self.ROADMAP + '\n    "starter-kit/ROADMAP.md": "methodology/ROADMAP2.md",')
        with self.assertRaises(reader.ManifestError) as cm:
            self.read(path)
        self.assertIn("starter-kit/ROADMAP.md", str(cm.exception))

    def test_two_files_sharing_one_destination_are_refused_naming_both(self):
        path = self.manifest_with(self.ROADMAP, '    "starter-kit/ROADMAP.md": "methodology/SESSION_RUNNER.md",')
        with self.assertRaises(reader.ManifestError) as cm:
            self.read(path)
        msg = str(cm.exception)
        self.assertIn("starter-kit/ROADMAP.md", msg)
        self.assertIn("starter-kit/SESSION_RUNNER.md", msg)

    def test_an_unsafe_destination_is_refused_before_anything_could_be_written(self):
        for why, bad in (("climbs out", "methodology/../ESCAPED.md"), ("absolute", "/etc/ESCAPED.md"),
                         ("inside .git", "methodology/.git/hooks/pre-commit"), ("names no file", "."),
                         ("empty", ""), ("NUL byte", "methodology/RO\\x00ADMAP.md")):
            with self.subTest(why):
                path = self.manifest_with(self.ROADMAP, '    "starter-kit/ROADMAP.md": "%s",' % bad)
                with self.assertRaises(reader.ManifestError) as cm:
                    self.read(path)
                self.assertIn("starter-kit/ROADMAP.md", str(cm.exception))

    def test_a_destination_outside_methodology_is_refused_because_the_resolver_would_not_find_it(self):
        for bad in ("ROADMAP.md", "docs/methodology/ROADMAP.md", "other/ROADMAP.md"):
            with self.subTest(bad):
                path = self.manifest_with(self.ROADMAP, '    "starter-kit/ROADMAP.md": "%s",' % bad)
                with self.assertRaises(reader.ManifestError) as cm:
                    self.read(path)
                self.assertIn(bad, str(cm.exception))

    def test_a_table_that_is_not_a_dict_of_strings_is_refused(self):
        for shape in ('NEW_LAYOUT = ["a", "b"]\nIGNORED = {', 'NEW_LAYOUT = {"starter-kit/ROADMAP.md": 3}\nIGNORED = {'):
            with self.subTest(shape):
                path = self.manifest_with("NEW_LAYOUT = {", shape)
                with self.assertRaises(reader.ManifestError):
                    self.read(path)

    def test_a_table_that_changes_after_its_assignment_is_refused_naming_it(self):
        extra = '{"starter-kit/ROADMAP.md": "methodology/ROADMAP.md"}'
        for how, line in (("update", "NEW_LAYOUT.update(%s)" % extra), ("item", 'NEW_LAYOUT["starter-kit/ROADMAP.md"] = "methodology/X.md"'),
                          ("second assignment", "NEW_LAYOUT = %s" % extra), ("augmented", "NEW_LAYOUT |= %s" % extra),
                          ("del", 'del NEW_LAYOUT["starter-kit/ROADMAP.md"]')):
            with self.subTest(how):
                path = self.manifest_with("SEED_FORMAT_MARKERS = {", line + "\nSEED_FORMAT_MARKERS = {")
                with self.assertRaises(reader.ManifestError) as cm:
                    self.read(path)
                self.assertIn("NEW_LAYOUT", str(cm.exception))


class TestSyncChoosesTheLayout(Scratch):
    """`--layout auto` (the default): a legacy tree stays legacy, a migrated one stays migrated, an empty
    directory gets the default, which stays legacy until the contract release."""

    def test_an_empty_project_gets_the_legacy_layout_by_default(self):
        d = self.project()
        r = run_sync(d)
        self.assertEqual(r.returncode, 0, r.out)
        self.assertEqual(files_of(d), LEGACY)
        self.assertIn("  layout:  legacy", r.out)

    def test_layout_legacy_on_an_empty_project_writes_the_legacy_tree_and_no_methodology_directory(self):
        d = self.project()
        r = run_sync(d, "--layout", "legacy")
        self.assertEqual(r.returncode, 0, r.out)
        self.assertEqual(files_of(d), LEGACY)
        self.assertFalse((d / "methodology").exists())
        self.assertIn("  layout:  legacy (requested)", r.out)

    def test_layout_new_on_an_empty_project_writes_the_tables_destinations_and_no_root_copy(self):
        d = self.project()
        r = run_sync(d, "--layout", "new")
        self.assertEqual(r.returncode, 0, r.out)
        self.assertEqual(files_of(d), NEW)
        self.assertEqual(lr.resolve_layout(d)[0], "new")
        self.assertIn("  layout:  new", r.out)
        for dest in LEGACY - NEW:
            self.assertFalse((d / dest).exists(), dest)

    def test_the_new_tree_sync_writes_is_the_fixture_tree_of_the_plans_section_4_1(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = set(lf.build_tree(td, "new", generated=False))
        self.assertEqual(files_of(base_tree("new")), fixture)

    def test_a_migrated_project_stays_migrated_under_auto_and_a_second_run_changes_nothing(self):
        d = self.project("new")
        before = {p: (d / p).read_bytes() for p in files_of(d)}
        r = run_sync(d)
        self.assertEqual(r.returncode, 0, r.out)
        self.assertIn("  layout:  new", r.out)
        self.assertEqual(files_of(d), NEW)
        self.assertEqual({p: (d / p).read_bytes() for p in files_of(d)}, before)
        self.assertNotRegex(r.out, r"(created|updated|would write)")

    def test_a_legacy_project_stays_legacy_under_auto_and_grows_no_methodology_directory(self):
        d = self.project("legacy")
        r = run_sync(d)
        self.assertEqual(r.returncode, 0, r.out)
        self.assertIn("  layout:  legacy", r.out)
        self.assertFalse((d / "methodology").exists())
        self.assertEqual(files_of(d), LEGACY)

    def test_the_layout_line_says_how_the_layout_was_chosen(self):
        self.assertIn("found", run_sync(self.project("new"), "--dry-run").out.split("layout:")[1].splitlines()[0])
        self.assertIn("requested", run_sync(self.project(), "--layout", "new", "--dry-run").out.split("layout:")[1].splitlines()[0])
        self.assertIn("default", run_sync(self.project(), "--dry-run").out.split("layout:")[1].splitlines()[0])

    def test_a_dry_run_writes_nothing_in_either_layout(self):
        for kind in (None, "legacy", "new"):
            for extra in ((), ("--layout", "new")) if kind is None else ((),):
                with self.subTest(kind=kind, extra=extra):
                    d = self.project(kind)
                    before = files_of(d)
                    r = run_sync(d, "--dry-run", *extra)
                    self.assertEqual(r.returncode, 0, r.out)
                    self.assertEqual(files_of(d), before)

    def test_an_unknown_layout_is_a_usage_error_that_lists_the_choices(self):
        d = self.project()
        r = run_sync(d, "--layout", "sideways")
        self.assertEqual(r.returncode, 2, r.out)
        for choice in ("auto", "legacy", "new"):
            self.assertIn(choice, r.out)
        self.assertIn("invalid choice", r.out)   # not argparse's "unrecognized arguments": the option must exist
        self.assertEqual(files_of(d), set())


class TestSyncRefusesWhatWouldDamageAProject(Scratch):
    """A tool that writes the new layout into a legacy tree leaves a second, current runner beside the stale one
    an agent still reads, and a blank ledger beside the real one. The guard runs before any write."""

    def refused(self, d, *args, names=()):
        before = {p: (d / p).read_bytes() for p in files_of(d)}
        r = run_sync(d, *args)
        self.assertEqual(r.returncode, 2, r.out)
        self.assertEqual({p: (d / p).read_bytes() for p in files_of(d)}, before, "a refused run wrote something")
        for n in names:
            self.assertIn(n, r.out)
        return r

    def test_a_legacy_project_asked_for_the_new_layout_is_refused_and_the_migration_tool_is_named(self):
        d = self.project("legacy")
        r = self.refused(d, "--layout", "new", names=("migrate-layout",))
        self.assertFalse((d / "methodology").exists())
        self.assertNotIn("not built", r.out)  # the tool exists: a refusal names a command that exists, without a caveat
        self.assertTrue((REPO / "bin" / "migrate-layout").is_file())
        self.refused(d, "--layout", "new", "--dry-run")

    def test_a_migrated_project_asked_for_the_legacy_layout_is_refused_and_no_root_runner_appears(self):
        d = self.project("new")
        self.refused(d, "--layout", "legacy")
        self.assertFalse((d / "SESSION_RUNNER.md").exists())
        self.refused(d, "--layout", "legacy", "--dry-run")

    def test_a_half_migrated_project_is_refused_whatever_is_asked_and_both_paths_are_named(self):
        d = self.project("legacy")
        (d / "methodology").mkdir()
        shutil.copyfile(d / "SESSION_RUNNER.md", d / "methodology" / "SESSION_RUNNER.md")
        for args in ((), ("--layout", "auto"), ("--layout", "legacy"), ("--layout", "new")):
            with self.subTest(args=args):
                self.refused(d, *args, names=(str(d / "SESSION_RUNNER.md"), str(d / "methodology" / "SESSION_RUNNER.md")))

    def test_a_refusal_prints_the_same_header_a_run_does_and_no_files_section(self):
        r = self.refused(self.project("legacy"), "--layout", "new")
        for line in ("sync: ", "  source:  local", "  mode:    commit"):
            self.assertIn(line, r.out)
        self.assertIn("ERROR", r.out)
        self.assertNotIn("  files:", r.out)


class TestSyncDoesNotShadowAProjectsOwnFiles(Scratch):
    """The seed half: a seed is the project's after its first creation, and a ledger that sits at the root
    (tier 1, or the project's own product changelog) is not a reason to create a blank one beside it."""

    def tier_1(self):
        """A migrated project whose seeds still sit at the root, each holding text of its own."""
        d = self.project("new")
        for src in SEED_SRCS:
            legacy = manifest.DISTRIBUTION[[r[0] for r in manifest.DISTRIBUTION].index(src)][1]
            (d / manifest.NEW_LAYOUT[src]).unlink()
            (d / legacy).parent.mkdir(parents=True, exist_ok=True)
            (d / legacy).write_text("the project's own %s\n" % legacy, encoding="utf-8")
        return d

    def test_no_seed_is_created_under_methodology_beside_a_seed_at_the_root(self):
        d = self.tier_1()
        r = run_sync(d)
        self.assertEqual(r.returncode, 0, r.out)
        for src in SEED_SRCS:
            legacy = manifest.DISTRIBUTION[[r[0] for r in manifest.DISTRIBUTION].index(src)][1]
            self.assertFalse((d / manifest.NEW_LAYOUT[src]).exists(), "a blank seed beside the real " + legacy)
            self.assertEqual((d / legacy).read_text(encoding="utf-8"), "the project's own %s\n" % legacy)
        self.assertIn("not created", r.out)

    def test_the_tracked_files_are_still_kept_current_under_methodology_in_that_tree(self):
        d = self.tier_1()
        (d / "methodology" / "SAFEGUARDS.md").unlink()
        r = run_sync(d)
        self.assertEqual(r.returncode, 0, r.out)
        self.assertTrue((d / "methodology" / "SAFEGUARDS.md").is_file())

    def test_a_seed_absent_everywhere_is_created_where_the_layout_puts_it(self):
        d = self.project("new")
        (d / manifest.NEW_LAYOUT["starter-kit/ROADMAP.md"]).unlink()
        r = run_sync(d)
        self.assertEqual(r.returncode, 0, r.out)
        self.assertTrue((d / "methodology" / "ROADMAP.md").is_file())
        self.assertFalse((d / "ROADMAP.md").exists())

    def test_a_product_changelog_at_the_root_beside_the_frameworks_under_methodology_is_left_alone(self):
        d = self.project("new")
        (d / "CHANGELOG.md").write_text("# the product's changelog\n", encoding="utf-8")
        ledger = (d / "methodology" / "CHANGELOG.md").read_bytes()
        r = run_sync(d)
        self.assertEqual(r.returncode, 0, r.out)
        self.assertEqual((d / "CHANGELOG.md").read_text(encoding="utf-8"), "# the product's changelog\n")
        self.assertEqual((d / "methodology" / "CHANGELOG.md").read_bytes(), ledger)

    def test_a_seed_is_never_overwritten_under_methodology_even_with_force(self):
        d = self.project("new")
        (d / "methodology" / "HANDOFFS.md").write_text("my receipts\n", encoding="utf-8")
        r = run_sync(d, "--force")
        self.assertEqual(r.returncode, 0, r.out)
        self.assertEqual((d / "methodology" / "HANDOFFS.md").read_text(encoding="utf-8"), "my receipts\n")


class TestSyncKeepsTrackedFilesCurrentUnderMethodology(Scratch):
    def test_a_locally_modified_file_blocks_the_run_without_force_and_is_named_by_its_new_path(self):
        d = self.project("new")
        (d / "methodology" / "SAFEGUARDS.md").write_text("edited here\n", encoding="utf-8")
        r = run_sync(d)
        self.assertEqual(r.returncode, 2, r.out)
        self.assertIn("methodology/SAFEGUARDS.md", r.out)
        self.assertEqual((d / "methodology" / "SAFEGUARDS.md").read_text(encoding="utf-8"), "edited here\n")
        forced = run_sync(d, "--force")
        self.assertEqual(forced.returncode, 0, forced.out)
        self.assertEqual((d / "methodology" / "SAFEGUARDS.md").read_bytes(),
                         (REPO / "starter-kit" / "SAFEGUARDS.md").read_bytes())

    def test_a_file_one_canonical_version_behind_is_upgraded_without_force(self):
        # history is keyed by the SOURCE path, so a file recognised at the root is recognised under methodology/
        src = "starter-kit/SAFEGUARDS.md"
        shas = subprocess.run(["git", "-C", str(REPO), "log", "--format=%H", "-n", "40", "--", src],
                              capture_output=True, text=True).stdout.split()
        current = (REPO / src).read_bytes()
        older = None
        for sha in shas:
            blob = subprocess.run(["git", "-C", str(REPO), "show", "%s:%s" % (sha, src)], capture_output=True).stdout
            if blob and blob != current:
                older = blob
                break
        if older is None:
            self.skipTest("this checkout has no older version of %s to plant" % src)
        d = self.project("new")
        (d / "methodology" / "SAFEGUARDS.md").write_bytes(older)
        r = run_sync(d)
        self.assertEqual(r.returncode, 0, r.out)
        self.assertEqual((d / "methodology" / "SAFEGUARDS.md").read_bytes(), current)
        self.assertIn("methodology/SAFEGUARDS.md: updated", r.out)

    def test_the_files_section_names_every_row_at_its_destination_in_the_layout(self):
        r = run_sync(self.project(), "--layout", "new", "--dry-run")
        listed = {line.split(":")[0].strip() for line in r.out.split("  files:")[1].splitlines() if ": " in line}
        self.assertEqual(listed, NEW)


class TestSyncIgnoreModeFollowsTheLayout(Scratch):
    """Ignore mode lists the TRACKED destinations file by file, so the list, the detection of an ignored
    project and the `git rm --cached` hint all have to follow the layout."""

    def entries(self, d):
        return {line.strip() for line in (d / ".gitignore").read_text(encoding="utf-8").splitlines()
                if line.strip().startswith("/")}

    def test_a_new_layout_project_in_ignore_mode_ignores_the_tracked_files_under_methodology_only(self):
        d = self.project()
        r = run_sync(d, "--layout", "new", "--mode", "ignore")
        self.assertEqual(r.returncode, 0, r.out)
        tracked = {"/" + manifest.NEW_LAYOUT[src] for src in TRACKED_SRCS}
        self.assertEqual(self.entries(d), tracked)
        self.assertNotIn("/methodology/CHANGELOG.md", self.entries(d))   # a seed is committed, never ignored
        self.assertNotIn("/SESSION_RUNNER.md", self.entries(d))

    def test_a_second_ignore_mode_run_adds_no_entry_and_says_so(self):
        d = self.project()
        first = run_sync(d, "--layout", "new", "--mode", "ignore")
        self.assertEqual(first.returncode, 0, first.out)
        written = (d / ".gitignore").read_bytes()
        second = run_sync(d, "--mode", "ignore")
        self.assertEqual(second.returncode, 0, second.out)
        self.assertEqual((d / ".gitignore").read_bytes(), written, "the second run added entries that were already there")
        self.assertIn(".gitignore: entries already present", second.out)

    def test_a_legacy_project_in_ignore_mode_is_unchanged(self):
        d = self.project()
        r = run_sync(d, "--mode", "ignore")
        self.assertEqual(r.returncode, 0, r.out)
        self.assertEqual(self.entries(d), {"/" + dest for src, dest, disp in manifest.DISTRIBUTION if disp == manifest.TRACKED})

    def test_ignore_mode_is_detected_from_either_layouts_entries(self):
        for layout, kind in (("new", "new"), ("legacy", "legacy")):
            with self.subTest(layout):
                d = self.project(kind)
                first = "/" + (manifest.NEW_LAYOUT[TRACKED_SRCS[0]] if layout == "new" else
                               [r[1] for r in manifest.DISTRIBUTION if r[0] == TRACKED_SRCS[0]][0])
                (d / ".gitignore").write_text(first + "\n", encoding="utf-8")
                r = run_sync(d, "--dry-run")
                self.assertIn("mode:    ignore", r.out)

    def test_the_hint_for_files_git_already_tracks_names_the_new_destinations(self):
        d = self.project("new")
        git(d, "add", "-A")
        git(d, "commit", "-qm", "adopt")
        r = run_sync(d, "--mode", "ignore")
        self.assertEqual(r.returncode, 0, r.out)
        hint = [line for line in r.out.splitlines() if "rm --cached" in line]
        self.assertEqual(len(hint), 1, r.out)
        self.assertIn("methodology/SESSION_RUNNER.md", hint[0])
        self.assertNotIn(" SESSION_RUNNER.md", hint[0])


class TestSyncFromGithubReadsTheTable(Scratch):
    """C16: --source=github reads the clone's manifest as data, so the new table has to be readable the same way,
    and a source that predates it has to leave a legacy project working and a new one refused."""

    def source(self, old=None, new=None):
        d = self.root / ("source%d" % len(list(self.root.glob("source*"))))
        d.mkdir()
        git(d, "init", "-q", "-b", "main")
        for src, _dest, _disp in manifest.DISTRIBUTION:
            (d / src).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / src, d / src)
        (d / "bin").mkdir()
        text = MANIFEST.read_text(encoding="utf-8")
        if old is not None:
            self.assertEqual(text.count(old), 1, old)
            text = text.replace(old, new)
        (d / "bin" / "_manifest.py").write_text(text, encoding="utf-8")
        git(d, "add", "-A")
        git(d, "commit", "-qm", "a source")
        return d

    def test_a_source_that_carries_the_table_installs_the_new_layout(self):
        d = self.project()
        r = run_sync(d, "--source=github", "--layout", "new", source=self.source())
        self.assertEqual(r.returncode, 0, r.out)
        self.assertEqual(files_of(d), NEW)

    def test_a_source_that_carries_the_table_keeps_a_new_project_new_under_auto(self):
        d = self.project("new")
        r = run_sync(d, "--source=github", source=self.source())
        self.assertEqual(r.returncode, 0, r.out)
        self.assertEqual(files_of(d), NEW)

    def test_a_source_without_the_table_still_serves_a_legacy_project(self):
        src = self.source("NEW_LAYOUT = {", "NO_LAYOUT_HERE = {")
        d = self.project()
        r = run_sync(d, "--source=github", source=src)
        self.assertEqual(r.returncode, 0, r.out)
        self.assertEqual(files_of(d), LEGACY)

    def test_a_source_without_the_table_cannot_serve_the_new_layout_and_says_why_in_one_line(self):
        src = self.source("NEW_LAYOUT = {", "NO_LAYOUT_HERE = {")
        for kind, args in ((None, ("--layout", "new")), ("new", ())):
            with self.subTest(kind=kind):
                d = self.project(kind)
                before = files_of(d)
                r = run_sync(d, "--source=github", *args, source=src)
                self.assertEqual(r.returncode, 1, r.out)
                self.assertIn("NEW_LAYOUT", r.out)
                self.assertIn("file://" + str(src), r.out)
                self.assertNotIn("Traceback", r.out)
                self.assertEqual(files_of(d), before)

    def test_a_source_with_a_defective_table_is_refused_for_every_project_naming_the_entry(self):
        src = self.source('    "starter-kit/ROADMAP.md": "methodology/ROADMAP.md",\n', "")
        for kind in (None, "legacy", "new"):
            with self.subTest(kind=kind):
                d = self.project(kind)
                before = files_of(d)
                r = run_sync(d, "--source=github", source=src)
                self.assertEqual(r.returncode, 1, r.out)
                self.assertIn("error: the bin/_manifest.py in file://" + str(src), r.out)
                self.assertIn("starter-kit/ROADMAP.md", r.out)
                self.assertNotIn("Traceback", r.out)
                self.assertEqual(files_of(d), before)


class TestStatusNamesAndReadsTheLayout(Scratch):
    """Status reads each project at the place its layout puts the files, and says which layout that is.
    A status over a portfolio names each project's layout, so a half-migrated portfolio is
    visible and a half-migrated project is an error."""

    def states(self, r, project):
        return {file: (disp, state) for name, file, disp, state in r.rows if name == project.name}

    def test_a_legacy_project_reads_current_at_its_legacy_places(self):
        d = self.project("legacy")
        r = run_status(d)
        self.assertEqual(r.returncode, 0, r.out)
        self.assertEqual(r.layouts[d.name], "legacy")
        states = self.states(r, d)
        self.assertEqual(set(states), LEGACY)
        for src, dest, disp in manifest.DISTRIBUTION:
            self.assertEqual(states[dest], (disp, "current" if disp == manifest.TRACKED else "present"), dest)

    def test_a_migrated_project_reads_current_at_the_new_places_and_every_row_is_named_by_its_new_path(self):
        d = self.project("new")
        r = run_status(d)
        self.assertEqual(r.returncode, 0, r.out)
        self.assertEqual(r.layouts[d.name], "new")
        states = self.states(r, d)
        self.assertEqual(set(states), NEW)
        for src, _dest, disp in manifest.DISTRIBUTION:
            self.assertEqual(states[manifest.NEW_LAYOUT[src]], (disp, "current" if disp == manifest.TRACKED else "present"), src)

    def test_an_empty_project_is_none_and_every_file_reads_missing_or_absent_at_the_legacy_places(self):
        d = self.project()
        r = run_status(d)
        self.assertEqual(r.returncode, 0, r.out)
        self.assertTrue(r.layouts[d.name].startswith("none"), r.layouts)
        states = self.states(r, d)
        self.assertEqual(set(states), LEGACY)
        self.assertEqual({st for disp, st in states.values()}, {"missing", "absent"})

    def test_a_half_migrated_project_is_one_row_naming_both_paths_and_the_run_still_reports_the_others(self):
        half = self.project("legacy")
        (half / "methodology").mkdir()
        shutil.copyfile(half / "SESSION_RUNNER.md", half / "methodology" / "SESSION_RUNNER.md")
        fine = self.project("new")
        r = run_status(half, fine)
        self.assertEqual(r.returncode, 0, r.out)
        self.assertEqual(r.layouts[half.name], "half-migrated: SESSION_RUNNER.md and methodology/SESSION_RUNNER.md")
        self.assertEqual(self.states(r, half), {"-": ("-", "half-migrated")})
        self.assertEqual(set(self.states(r, fine)), NEW)

    def test_a_layout_line_is_not_a_table_row_so_a_row_count_by_project_name_still_reads_one_per_file(self):
        # bin/tests.sh Test 15 counts the rows that start with the project's name; the layout line names the project
        # too, and counting every line that mentions it read 31 for 30 files (found by the shell suite, not by this one)
        d = self.project("legacy")
        r = run_status(d)
        starts = [line for line in r.stdout.splitlines() if line.startswith(d.name + " ")]
        self.assertEqual(len(starts), len(manifest.DISTRIBUTION))
        self.assertEqual([line for line in r.stdout.splitlines() if d.name in line and not line.startswith(d.name + " ")],
                         ["layout: %s  legacy" % d.name])

    def test_a_mixed_portfolio_names_every_projects_layout_in_the_order_given(self):
        legacy, new, empty = self.project("legacy"), self.project("new"), self.project()
        r = run_status(legacy, new, empty)
        self.assertEqual(list(r.layouts), [legacy.name, new.name, empty.name])
        self.assertEqual([v.split()[0] for v in r.layouts.values()], ["legacy", "new", "none"])

    def test_a_missing_directory_is_still_a_row_of_its_own(self):
        r = run_status(self.root / "nowhere")
        self.assertEqual(r.rows, [("%s" % (self.root / "nowhere"), "-", "-", "missing-dir")])

    def test_drift_is_found_under_methodology_by_the_same_history_walk(self):
        d = self.project("new")
        (d / "methodology" / "SAFEGUARDS.md").write_text("edited here\n", encoding="utf-8")
        self.assertEqual(self.states(run_status(d), d)["methodology/SAFEGUARDS.md"], ("tracked", "locally modified"))
        src = "starter-kit/SAFEGUARDS.md"
        shas = subprocess.run(["git", "-C", str(REPO), "log", "--format=%H", "-n", "40", "--", src],
                              capture_output=True, text=True).stdout.split()
        current = (REPO / src).read_bytes()
        older = next((b for b in (subprocess.run(["git", "-C", str(REPO), "show", "%s:%s" % (sha, src)], capture_output=True).stdout
                                  for sha in shas) if b and b != current), None)
        if older is None:
            self.skipTest("this checkout has no older version of %s to plant" % src)
        (d / "methodology" / "SAFEGUARDS.md").write_bytes(older)
        state = self.states(run_status(d), d)["methodology/SAFEGUARDS.md"][1]
        self.assertRegex(state, r"^\d+ versions? behind$")


class TestStatusFindsSeedsWhereTheProjectKeepsThem(Scratch):
    """A seed in the new layout may still sit at the root (tier 1, or the project's own changelog), and its
    format marker is keyed by the seed, not by where it happens to be."""

    def states(self, r, project):
        return {file: (disp, state) for name, file, disp, state in r.rows if name == project.name}

    def test_a_seed_at_the_root_of_a_migrated_project_reads_present_at_the_root(self):
        d = self.project("new")
        (d / "methodology" / "ROADMAP.md").unlink()
        (d / "ROADMAP.md").write_text("my roadmap\n", encoding="utf-8")
        r = run_status(d)
        states = self.states(r, d)
        self.assertEqual(r.layouts[d.name], "new")
        self.assertEqual(states["methodology/SESSION_RUNNER.md"], ("tracked", "current"))   # the project is read as migrated ...
        self.assertEqual(states["ROADMAP.md"], ("seed", "present"))                          # ... and this seed where it sits
        self.assertNotIn("methodology/ROADMAP.md", states)

    def test_a_seed_absent_everywhere_is_absent_and_never_drift(self):
        d = self.project("new")
        (d / "methodology" / "ROADMAP.md").unlink()
        r = run_status(d)
        self.assertEqual(self.states(r, d)["methodology/ROADMAP.md"], ("seed", "absent"))

    def test_a_ledger_under_methodology_that_predates_the_seed_format_is_flagged_and_routed_by_its_seed(self):
        d = self.project("new")
        (d / "methodology" / "CHANGELOG.md").write_text("# an old ledger\n", encoding="utf-8")
        r = run_status(d)
        self.assertEqual(self.states(r, d)["methodology/CHANGELOG.md"], ("seed", "present (stale format)"))
        self.assertIn("methodology/CHANGELOG.md", r.out.split("note:")[1])
        self.assertIn("replace the rules text or old header", r.out)   # the CHANGELOG route, found by the seed's name

    def test_a_stale_ledger_at_the_root_of_a_migrated_project_is_flagged_the_same_way(self):
        d = self.project("new")
        (d / "methodology" / "HANDOFFS.md").unlink()
        (d / "HANDOFFS.md").write_text("# old receipts\n", encoding="utf-8")
        r = run_status(d)
        self.assertEqual(r.layouts[d.name], "new")
        self.assertEqual(self.states(r, d)["HANDOFFS.md"], ("seed", "present (stale format)"))
        self.assertIn("'## Size, and when to archive'", r.out)   # the HANDOFFS route


class TestStatusFromGithubReadsTheTable(Scratch):
    def source(self, old=None, new=None):
        d = self.root / ("source%d" % len(list(self.root.glob("source*"))))
        d.mkdir()
        git(d, "init", "-q", "-b", "main")
        for src, _dest, _disp in manifest.DISTRIBUTION:
            (d / src).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / src, d / src)
        (d / "bin").mkdir()
        text = MANIFEST.read_text(encoding="utf-8")
        if old is not None:
            self.assertEqual(text.count(old), 1, old)
            text = text.replace(old, new)
        (d / "bin" / "_manifest.py").write_text(text, encoding="utf-8")
        git(d, "add", "-A")
        git(d, "commit", "-qm", "a source")
        return d

    def test_a_migrated_project_reads_current_against_a_source_that_carries_the_table(self):
        d = self.project("new")
        r = run_status(d, source=self.source())
        self.assertEqual(r.returncode, 0, r.out)
        self.assertEqual({file: state for name, file, disp, state in r.rows if disp == "tracked"},
                         {manifest.NEW_LAYOUT[src]: "current" for src in TRACKED_SRCS})

    def test_a_source_without_the_table_still_reports_legacy_projects_and_says_what_it_cannot_for_a_migrated_one(self):
        src = self.source("NEW_LAYOUT = {", "NO_LAYOUT_HERE = {")
        legacy, new = self.project("legacy"), self.project("new")
        r = run_status(legacy, new, source=src)
        self.assertEqual(r.returncode, 0, r.out)
        self.assertEqual({st for n, f, d_, st in r.rows if n == legacy.name and d_ == "tracked"}, {"current"})
        self.assertEqual([row for row in r.rows if row[0] == new.name], [(new.name, "-", "-", "source-predates-new-layout")])

    def test_a_source_with_a_defective_table_is_refused_naming_the_entry(self):
        src = self.source('    "starter-kit/ROADMAP.md": "methodology/ROADMAP.md",\n', "")
        r = run_status(self.project("new"), source=src)
        self.assertEqual(r.returncode, 1, r.out)
        self.assertIn("error: the bin/_manifest.py in file://" + str(src), r.out)
        self.assertIn("starter-kit/ROADMAP.md", r.out)
        self.assertNotIn("Traceback", r.out)


RUNNER = "starter-kit/SESSION_RUNNER.md"
LEGACY_ONLY = "[a](docs/methodology/FRAMEWORK_APPARATUS.md)\n"   # the apparatus is two directories down at the legacy root only
NEW_ONLY = "[a](FRAMEWORK_APPARATUS.md)\n"                      # ... and a sibling in the new layout
IN_BOTH = "[a](SAFEGUARDS.md)\n"                                # a sibling of the runner in both


class TestCheckLinksSimulatesBothLayouts(Scratch):
    """check-links simulates the adopter tree from the manifest, so it has to be able to simulate the new
    one. Whether the docs link correctly in both is asserted elsewhere in the suite; this is the instrument for it."""

    def script(self, text):
        return scratch_canonical(self.root / ("canon%d" % len(list(self.root.glob("canon*")))), {RUNNER: text})

    def test_a_link_valid_in_both_layouts_passes_in_each_and_in_both_together(self):
        script = self.script(IN_BOTH)
        for args in ((), ("--layout", "legacy"), ("--layout", "new"), ("--layout", "both")):
            with self.subTest(args=args):
                r = run_check_links(script, *args)
                self.assertEqual(r.returncode, 0, r.out)
                self.assertIn("check-links: OK", r.out)

    def test_a_link_authored_for_the_legacy_layout_fails_in_the_new_one_naming_the_new_path(self):
        script = self.script(LEGACY_ONLY)
        self.assertEqual(run_check_links(script).returncode, 0)                       # the default is the legacy tree, as before
        r = run_check_links(script, "--layout", "new")
        self.assertEqual(r.returncode, 1, r.out)
        self.assertIn("methodology/SESSION_RUNNER.md:1", r.out)
        self.assertIn("docs/methodology/FRAMEWORK_APPARATUS.md", r.out)
        self.assertIn("new layout", r.out)

    def test_a_link_authored_for_the_new_layout_fails_in_the_legacy_one_and_passes_in_the_new(self):
        script = self.script(NEW_ONLY)
        self.assertEqual(run_check_links(script, "--layout", "new").returncode, 0)
        r = run_check_links(script)
        self.assertEqual(r.returncode, 1, r.out)
        self.assertIn("SESSION_RUNNER.md:1", r.out)

    def test_both_runs_each_layout_names_each_verdict_and_fails_if_either_does(self):
        for text in (LEGACY_ONLY, NEW_ONLY):
            with self.subTest(text=text):
                r = run_check_links(self.script(text), "--layout", "both")
                self.assertEqual(r.returncode, 1, r.out)
                self.assertIn("legacy layout", r.out)
                self.assertIn("new layout", r.out)
                self.assertIn("check-links: OK", r.out)      # the layout that holds still says so
                self.assertIn("check-links: FAIL", r.out)

    def test_the_default_run_prints_the_message_it_always_did(self):
        r = run_check_links(self.script(IN_BOTH))
        self.assertRegex(r.out, r"^check-links: OK — \d+ relative link\(s\) across \d+ distributed markdown files resolve in the simulated adopter tree\.\n$")

    def test_the_placeholder_parent_workstream_is_allowed_absent_beside_the_template_in_either_layout(self):
        script = scratch_canonical(self.root / "canon_placeholder", {"workstreams/TEMPLATE_CAMPAIGN.md": "[p](PARENT_WORKSTREAM.md)\n"})
        for layout in ("legacy", "new"):
            with self.subTest(layout):
                self.assertEqual(run_check_links(script, "--layout", layout).returncode, 0)
        elsewhere = scratch_canonical(self.root / "canon_elsewhere", {RUNNER: "[p](PARENT_WORKSTREAM.md)\n"})
        self.assertEqual(run_check_links(elsewhere, "--layout", "new").returncode, 1)

    def test_the_projects_own_files_are_allowed_absent_at_the_project_root_in_each_layout(self):
        legacy = self.script("[a](CLAUDE.md)\n")          # a sibling of the runner, which is at the root
        self.assertEqual(run_check_links(legacy).returncode, 0)
        up = self.script("[a](../CLAUDE.md)\n")           # one level up from methodology/
        self.assertEqual(run_check_links(up, "--layout", "new").returncode, 0)
        self.assertEqual(run_check_links(self.script("[a](CLAUDE.md)\n"), "--layout", "new").returncode, 1)

    def test_a_companion_of_the_move_is_allowed_absent_beside_the_runner_in_each_layout(self):
        """A project's PROJECT_LEARNINGS.md goes where its methodology files go (a companion of the move): the project
        root in the legacy layout, methodology/ in the new one, so a link to it is as good as a link to a sibling of the
        runner and a link up to the root is not (the file is not there once the project has moved)."""
        sibling = self.script("[a](PROJECT_LEARNINGS.md)\n")
        self.assertEqual(run_check_links(sibling).returncode, 0)
        self.assertEqual(run_check_links(sibling, "--layout", "new").returncode, 0)
        up = self.script("[a](../PROJECT_LEARNINGS.md)\n")
        self.assertEqual(run_check_links(up, "--layout", "new").returncode, 1)

    def test_the_checker_never_writes_to_the_canonical_checkout_it_simulates_from(self):
        script = self.script(IN_BOTH)
        before = files_of(script.parent.parent)
        run_check_links(script, "--layout", "both")
        self.assertEqual(files_of(script.parent.parent), before)


class TestCheckLinksTreeModeReadsTheTreesLayout(Scratch):
    """`--tree` validates a tree a sync produced, so it has to read that tree's layout, never assume it."""

    def tree(self, layout, text):
        d = self.root / ("tree-" + layout)
        lf.build_tree(d, layout, generated=False, contents={"SESSION_RUNNER.md": text})
        return d

    def test_a_migrated_tree_is_read_as_the_new_layout(self):
        r = run_check_links(CHECK_LINKS, "--tree", str(self.tree("new", NEW_ONLY)))
        self.assertEqual(r.returncode, 0, r.out)
        self.assertIn("new layout", r.out)

    def test_a_legacy_tree_is_read_as_the_legacy_layout(self):
        r = run_check_links(CHECK_LINKS, "--tree", str(self.tree("legacy", LEGACY_ONLY)))
        self.assertEqual(r.returncode, 0, r.out)
        self.assertNotIn("new layout", r.out)

    def test_the_same_link_that_passes_in_one_tree_fails_in_the_other_because_it_dangles_there(self):
        for kind, text, target in (("new", LEGACY_ONLY, "docs/methodology/FRAMEWORK_APPARATUS.md"),
                                   ("legacy", NEW_ONLY, "FRAMEWORK_APPARATUS.md")):
            with self.subTest(kind):
                r = run_check_links(CHECK_LINKS, "--tree", str(self.tree(kind, text)))
                self.assertEqual(r.returncode, 1, r.out)
                self.assertIn(target, r.out)
                self.assertNotIn("distributed file missing", r.out)   # the tree was found where its layout puts it

    def test_a_tree_from_bin_sync_is_read_in_its_own_layout(self):
        for kind in ("legacy", "new"):
            with self.subTest(kind):
                d = self.root / ("synced-" + kind)
                shutil.copytree(base_tree(kind), d)
                r = run_check_links(CHECK_LINKS, "--tree", str(d))
                self.assertEqual("new layout" in r.out, kind == "new", r.out)
                for line in r.out.splitlines():
                    if line.startswith("  ") and ":" in line:
                        self.assertEqual(line.strip().startswith("methodology/"), kind == "new", line)

    def test_a_half_migrated_tree_is_refused_naming_both_paths(self):
        d = self.tree("legacy", IN_BOTH)
        (d / "methodology").mkdir()
        shutil.copyfile(d / "SESSION_RUNNER.md", d / "methodology" / "SESSION_RUNNER.md")
        r = run_check_links(CHECK_LINKS, "--tree", str(d))
        self.assertEqual(r.returncode, 2, r.out)
        self.assertIn(str(d / "methodology" / "SESSION_RUNNER.md"), r.out)

    def test_both_layouts_at_once_make_no_sense_for_one_tree_and_are_refused(self):
        r = run_check_links(CHECK_LINKS, "--tree", str(self.tree("new", IN_BOTH)), "--layout", "both")
        self.assertEqual(r.returncode, 2, r.out)
        self.assertIn("--layout both", r.out)   # says what was refused, not just the usage line

    def test_an_explicit_layout_overrides_the_one_the_tree_has(self):
        d = self.tree("legacy", IN_BOTH)
        self.assertEqual(run_check_links(CHECK_LINKS, "--tree", str(d)).returncode, 0)        # read as legacy: it is
        r = run_check_links(CHECK_LINKS, "--tree", str(d), "--layout", "new")                 # asked to read it as new: no files there
        self.assertEqual(r.returncode, 1, r.out)
        self.assertIn("distributed file missing", r.out)
        self.assertIn("(new layout)", r.out)
        n = self.tree("new", IN_BOTH)
        self.assertEqual(run_check_links(CHECK_LINKS, "--tree", str(n), "--layout", "legacy").returncode, 1)

    def test_help_exits_zero_and_lists_the_layout_option(self):
        for flag in ("--help", "-h"):
            r = run_check_links(CHECK_LINKS, flag)
            self.assertEqual(r.returncode, 0, r.out)
            self.assertIn("--layout", r.out)
            self.assertIn("legacy|new|both", r.out)

    def test_an_option_given_twice_is_a_usage_error_not_a_silent_last_wins(self):
        a, b = self.tree("legacy", IN_BOTH), self.tree("new", IN_BOTH)
        r = run_check_links(CHECK_LINKS, "--tree", str(a), "--tree", str(b))
        self.assertEqual(r.returncode, 2, r.out)
        self.assertIn("usage", r.out)
        r = run_check_links(CHECK_LINKS, "--layout", "new", "--layout", "legacy")
        self.assertEqual(r.returncode, 2, r.out)

    def test_an_unknown_layout_is_a_usage_error(self):
        r = run_check_links(CHECK_LINKS, "--layout", "sideways")
        self.assertEqual(r.returncode, 2, r.out)
        self.assertIn("usage", r.out)
        for choice in ("legacy", "new", "both"):
            self.assertIn(choice, r.out)


class TestNoShippedToolNamesARootPath(unittest.TestCase):
    """P6's last row: the literal scanner is wired in at zero. The declared gate (layout-literals) is measured at
    close-out; this is the same check where a suite run sees it, so a new literal is caught the commit after it is
    written and not the session after."""

    def test_the_scanner_reads_no_site_in_this_repository(self):
        r = subprocess.run([sys.executable, "-B", str(LITERALS)], capture_output=True, text=True, cwd=str(REPO))
        self.assertEqual(r.returncode, 0, "a shipped tool names a methodology file by a root path:\n" + r.stdout + r.stderr)
        self.assertIn(" 0 sites ", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
