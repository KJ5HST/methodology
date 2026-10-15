#!/usr/bin/env python3
"""Unit tests for bin/migrate-layout.

CANONICAL-ONLY, like tools/test_sync_layouts.py: bin/migrate-layout is not in bin/_manifest.py, so adopters
do not receive it. The contract is a dry run by default; a refusal of a dirty tree, a half-migrated tree, a destination that
exists and a
tree where bin/status does not read every TRACKED file current; the plan printed as data; the apply as ONE
commit with every moved file at 90% similarity or better; a committed ledger entry or a frozen shard never
rewritten.

Every test drives the tool as a command in a scratch git project that the real bin/sync wrote and that is
then committed, so the fixture is what an adopter is and not what a test imagines. The tool is asked for
--json, which is the report as data; a few tests read the text a person reads. Every rule is observed failing
as well as passing (Learning #12), and the tests are written before the code they pin.
"""
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True  # a test run must not generate bin/__pycache__ or tools/__pycache__

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
MIGRATE = REPO / "bin" / "migrate-layout"
SYNC = REPO / "bin" / "sync"
STATUS = REPO / "bin" / "status"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_script(name, path):
    import importlib.machinery
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


manifest = _load("_manifest", REPO / "bin" / "_manifest.py")
LEGACY = [(src, dest, disp) for src, dest, disp in manifest.DISTRIBUTION]
TRACKED_DESTS = [dest for _s, dest, disp in LEGACY if disp == manifest.TRACKED]
SEED_DESTS = [dest for _s, dest, disp in LEGACY if disp == manifest.SEED]
NEW_OF = {dest: manifest.NEW_LAYOUT[src] for src, dest, _d in LEGACY}  # legacy destination -> new destination


def git(path, *args, check=True):
    """git -C path ... ; returns stdout. A failure raises, naming the command and what git said."""
    r = subprocess.run(["git", "-C", str(path), "-c", "user.email=t@t", "-c", "user.name=t",
                        "-c", "commit.gpgsign=false", *args], capture_output=True, text=True)
    if check and r.returncode:
        raise AssertionError("git %s failed in %s:\n%s%s" % (" ".join(args), path, r.stdout, r.stderr))
    return r.stdout


def run_migrate(project, *args, json_out=True, checks=False):
    """bin/migrate-layout as a command. With json_out the report is read as data into .report (None when the
    output is not JSON); .out is stdout and stderr joined. An --apply skips the before-and-after checks unless
    `checks` is asked for: they take seconds, and TestTheChecks is where they are asserted."""
    cmd = [sys.executable, "-B", str(MIGRATE), str(project)]
    if json_out:
        cmd.append("--json")
    if "--apply" in args and not checks and "--skip-checks" not in args:
        cmd.append("--skip-checks")
    r = subprocess.run([*cmd, *args], capture_output=True, text=True)
    r.out = r.stdout + r.stderr
    try:
        r.report = json.loads(r.stdout) if json_out else None
    except ValueError:
        r.report = None
    return r


def tree_state(project):
    """Everything about a project a read-only run must leave alone: HEAD, the status, and a digest of every
    file's bytes (the .git directory left out)."""
    root = Path(project)
    digests = {}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if p.is_file() and ".git" not in rel.parts:
            digests[rel.as_posix()] = hashlib.sha1(p.read_bytes()).hexdigest()
    return (git(project, "rev-parse", "HEAD").strip(), git(project, "status", "--porcelain"), digests)


def files_of(project):
    root = Path(project)
    return {p.relative_to(root).as_posix() for p in root.rglob("*")
            if p.is_file() and ".git" not in p.relative_to(root).parts}


def commit_all(project, message):
    git(project, "add", "-A")
    git(project, "commit", "-q", "-m", message)


def ledger_with_entries(seed_text, n=40):
    """The CHANGELOG.md seed without its sentinel, followed by n dated entries: a ledger an adopter has been
    keeping, large enough that one more entry does not take a rename below 90% similarity."""
    text = re.sub(r"<!-- METHODOLOGY-SEED-SENTINEL.*?-->\n", "", seed_text, flags=re.S)
    entries = "".join("### 2026-09-%02d · [ad hoc] Entry %d\n\n%s%s\n\n" % (
        1 + i % 28, i, ("Body of entry %d. " % i) * 14,
        " See SESSION_RUNNER.md and [the guide](docs/methodology/HOW_TO_USE.md)." if i == 3 else "") for i in range(n))
    return text.rstrip("\n") + "\n\n" + entries


CLAUDE_MD = """# Project

<!-- SESSION PROTOCOL -->
Read and follow `SESSION_RUNNER.md` step by step. Orient first: read SAFEGUARDS.md, then SESSION_NOTES.md,
then run `methodology_dashboard.py`.

This project follows `docs/methodology/workstreams/DEVELOPMENT_WORKSTREAM.md` in standard mode, and the
theory is in [the manual](docs/methodology/ITERATIVE_METHODOLOGY.md).

Kept qualified on purpose (a path with a directory in front is not a bare name):
the canonical copy is `../methodology/starter-kit/SESSION_RUNNER.md`, and upstream is
https://github.com/KJ5HST/methodology/blob/main/SESSION_RUNNER.md and `starter-kit/SAFEGUARDS.md`.

Not a methodology file: SESSION_RUNNER.mdx, MY_CHANGELOG.md, NOTES-CHANGELOG.md.
"""

def gates_text():
    """The seed .quality-gates.json (its prose and all, so it is the size a real adopter's is) with one gate declared,
    which is what an adopter that has started using the ratchet holds."""
    cfg = json.loads((REPO / "starter-kit" / "quality-gates.json").read_text(encoding="utf-8"))
    cfg["results_file"] = ".quality-gates-results.json"
    cfg["gates"] = [{
        "name": "ledger-lag", "direction": "max", "threshold": 3,
        "command": "git rev-list --count --no-merges \"$(git log -1 --format=%H -- CHANGELOG.md)..HEAD\"",
        "why": "Commits after the newest commit that touched CHANGELOG.md -- Phase 0's reconcile set.",
    }]
    return json.dumps(cfg, indent=2, ensure_ascii=False) + "\n"


GITIGNORE = """# generated by the methodology tools: the page is anchored to the root, the results file is not;
# the two history files are tracked (nothing here ignores them), as five of the twelve real adopters keep them
/dashboard.html
.quality-gates-results.json
"""


def customise(project):
    """Make the freshly synced project look like an adopter that has been working: a ledger with entries, a
    CLAUDE.md that names its methodology files, configs that name them too, a .gitignore, generated files, a
    project-owned file beside the methodology ones under docs/methodology/, and two ledger shards."""
    p = Path(project)
    seed = (REPO / "starter-kit" / "CHANGELOG.md").read_text(encoding="utf-8")
    (p / "CHANGELOG.md").write_text(ledger_with_entries(seed), encoding="utf-8")
    (p / "CLAUDE.md").write_text(CLAUDE_MD, encoding="utf-8")
    (p / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    (p / ".quality-gates.json").write_text(gates_text(), encoding="utf-8")
    (p / "docs" / "methodology").mkdir(parents=True, exist_ok=True)
    (p / "docs" / "methodology" / "PROJECT_CONVENTIONS.md").write_text("# Conventions\n\nThis project's own.\n", encoding="utf-8")
    for name in ("dashboard_history.jsonl", ".context-budget-history.jsonl"):
        (p / name).write_text('{"timestamp": "2026-09-01T00:00:00"}\n', encoding="utf-8")
    # places that name a moved file and that the tool reports and does not edit
    (p / ".github" / "workflows").mkdir(parents=True)
    (p / ".github" / "workflows" / "ci.yml").write_text(
        "on:\n  push:\n    paths-ignore:\n      - 'CHANGELOG.md'\n      - 'SESSION_NOTES.md'\n      - 'docs/methodology/**'\njobs: {}\n", encoding="utf-8")
    (p / ".claude").mkdir()
    (p / ".claude" / "settings.json").write_text(
        '{"permissions": {"allow": ["Read(SESSION_RUNNER.md)", "Bash(python3 methodology_dashboard.py:*)"]}}\n', encoding="utf-8")
    (p / ".githooks").mkdir()
    (p / ".githooks" / "pre-commit").write_text(
        "#!/bin/sh\ngit ls-files --error-unmatch CHANGELOG.md >/dev/null 2>&1 || exit 0\n", encoding="utf-8")
    (p / "README.md").write_text("See docs/methodology/HOW_TO_USE.md for the method; the product log is CHANGELOG.md.\n", encoding="utf-8")
    (p / "docs" / "archive").mkdir(parents=True, exist_ok=True)
    for name in ("CHANGELOG-through-2026-08-01.md", "CHANGELOG-through-2026-08-01.md.verify.sh",
                 "HANDOFFS-through-2026-08-02.md", "HANDOFFS-through-2026-08-02.md.verify.sh"):
        (p / "docs" / "archive" / name).write_text("# shard %s\n" % name, encoding="utf-8")
    (p / "docs" / "archive" / "project-notes.md").write_text("# The project's own archive\n", encoding="utf-8")


_BASE = []


def base_project():
    """A legacy adopter, built once by the real bin/sync, customised and committed. Tests copy it."""
    if not _BASE:
        keep = tempfile.mkdtemp(prefix="migrate-base-")
        project = Path(keep) / "adopter"
        project.mkdir()
        git(project, "init", "-q")
        git(project, "config", "user.name", "Adopter")
        git(project, "config", "user.email", "adopter@example.com")
        git(project, "config", "commit.gpgsign", "false")
        r = subprocess.run([sys.executable, "-B", str(SYNC), str(project)], capture_output=True, text=True)
        assert r.returncode == 0, "the base project could not be synced:\n%s%s" % (r.stdout, r.stderr)
        customise(project)
        commit_all(project, "an adopter at the legacy layout")
        # generated files that are ignored, so not committed: they exist on disk only
        (project / "dashboard.html").write_text("<!-- generated -->\n", encoding="utf-8")
        (project / ".quality-gates-results.json").write_text("{}\n", encoding="utf-8")
        _BASE.append(project)
    return _BASE[0]


def tearDownModule():
    for project in _BASE:
        shutil.rmtree(project.parent, ignore_errors=True)


class TestThePureRules(unittest.TestCase):
    """The rules the tool applies, called as functions: a command costs seconds, a rule costs nothing, and these are
    the cases a whole-project test only reaches by accident."""

    @classmethod
    def setUpClass(cls):
        cls.m = _load_script("migrate_layout", MIGRATE)

    # --- .gitignore ---
    def test_a_gitignore_entry_follows_only_when_it_is_anchored_and_exactly_a_moved_path(self):
        mapping = {"dashboard.html": "methodology/dashboard.html", "docs/archive/CHANGELOG-through-2026-01-01.md":
                   "methodology/archive/CHANGELOG-through-2026-01-01.md"}
        text = ("# a comment naming /dashboard.html\n/dashboard.html\ndashboard.html\n!/dashboard.html\n"
                "/dashboard.html.bak\ndocs/archive/CHANGELOG-through-2026-01-01.md\n/other.html\n\n")
        got, n = self.m.rewrite_gitignore(text, mapping)
        self.assertEqual(got, ("# a comment naming /dashboard.html\n/methodology/dashboard.html\ndashboard.html\n"
                               "!/methodology/dashboard.html\n/dashboard.html.bak\n"
                               "/methodology/archive/CHANGELOG-through-2026-01-01.md\n/other.html\n\n"))
        self.assertEqual(n, 3)

    def test_a_gitignore_keeps_its_line_endings(self):
        got, n = self.m.rewrite_gitignore("a\r\n/dashboard.html\r\nb", {"dashboard.html": "methodology/dashboard.html"})
        self.assertEqual(got, "a\r\n/methodology/dashboard.html\r\nb")

    # --- the standing-alone rule ---
    def rewrite(self, text, mapping=None):
        mapping = mapping or {"SESSION_RUNNER.md": "methodology/SESSION_RUNNER.md"}
        return self.m.token_rewriter(mapping)(text)

    def test_a_name_is_rewritten_where_it_stands_alone(self):
        for text in ("SESSION_RUNNER.md", "`SESSION_RUNNER.md`", "(SESSION_RUNNER.md)", "read SESSION_RUNNER.md.", '"SESSION_RUNNER.md"',
                     "--file=SESSION_RUNNER.md", "SESSION_RUNNER.md:12", "[x](SESSION_RUNNER.md#top)", "SESSION_RUNNER.md, and"):
            got, n = self.rewrite(text)
            self.assertEqual(n, 1, text)
            self.assertEqual(got, text.replace("SESSION_RUNNER.md", "methodology/SESSION_RUNNER.md"), text)

    def test_a_name_inside_another_name_or_behind_a_directory_is_left(self):
        for text in ("SESSION_RUNNER.mdx", "SESSION_RUNNER.md.bak", "SESSION_RUNNER.md2", "/SESSION_RUNNER.md", "./SESSION_RUNNER.md",
                     "~/SESSION_RUNNER.md", "~SESSION_RUNNER.md", "a/SESSION_RUNNER.md", "MY_SESSION_RUNNER.md", "my-SESSION_RUNNER.md",
                     "xSESSION_RUNNER.md", ".SESSION_RUNNER.md", "https://example.org/SESSION_RUNNER.md"):
            self.assertEqual(self.rewrite(text), (text, 0), text)

    def test_the_longest_path_wins_and_each_occurrence_is_counted(self):
        mapping = {"docs/x/a.md": "m/a.md", "a.md": "m/a.md"}
        self.assertEqual(self.rewrite("docs/x/a.md and a.md and a.md", mapping), ("m/a.md and m/a.md and m/a.md", 3))

    def test_an_empty_map_changes_nothing(self):
        """An empty alternation matches the empty string between two non-word characters, so the text must have some."""
        for text in ("SESSION_RUNNER.md", "a  b , c", "", "(  )"):
            self.assertEqual(self.m.token_rewriter({})(text), (text, 0), repr(text))

    # --- a JSON config, rewritten as text ---
    MAP = {"SESSION_RUNNER.md": "methodology/SESSION_RUNNER.md", "CHANGELOG.md": "methodology/CHANGELOG.md",
           ".quality-gates-results.json": "methodology/.quality-gates-results.json"}

    def rj(self, text):
        return self.m.rewrite_json(text, self.MAP)

    def test_a_value_that_is_exactly_a_moved_path_follows_and_the_layout_of_the_file_is_kept(self):
        text = '{\n\t"files": [\n\t\t{"path": "SESSION_RUNNER.md", "n": 1},\n\t\t{ "path":"CHANGELOG.md" }\n\t],\n\t"results_file": ".quality-gates-results.json"\n}\n'
        got, n = self.rj(text)
        self.assertEqual(got, text.replace('"SESSION_RUNNER.md"', '"methodology/SESSION_RUNNER.md"')
                         .replace('"CHANGELOG.md"', '"methodology/CHANGELOG.md"')
                         .replace('".quality-gates-results.json"', '"methodology/.quality-gates-results.json"'))
        self.assertEqual(n, 3)

    def test_a_value_that_only_contains_a_moved_path_is_not_a_path(self):
        text = '{"path": "docs/SESSION_RUNNER.md", "note": "see SESSION_RUNNER.md", "name": "CHANGELOG.md.bak"}'
        self.assertEqual(self.rj(text), (text, 0))

    def test_canonical_and_every_underscore_key_are_left(self):
        text = '{"synced": [{"path": "SESSION_RUNNER.md", "canonical": "SESSION_RUNNER.md", "_": "SESSION_RUNNER.md"}], "_why": "CHANGELOG.md"}'
        got, n = self.rj(text)
        self.assertEqual(got, text.replace('"path": "SESSION_RUNNER.md"', '"path": "methodology/SESSION_RUNNER.md"'))
        self.assertEqual(n, 1)

    def test_a_path_bearing_key_inside_a_prose_subtree_makes_the_rewrite_unsafe(self):
        """The text rewrite cannot tell scope; the structure check can. The file is not half-edited: it is refused."""
        with self.assertRaises(self.m.Unsafe):
            self.rj('{"_example": {"path": "SESSION_RUNNER.md"}, "files": [{"path": "SESSION_RUNNER.md"}]}')

    def test_a_gate_command_is_rewritten_by_token_and_the_prose_beside_it_is_not(self):
        text = '{"gates": [{"command": "git log -- CHANGELOG.md && cat SESSION_RUNNER.md.bak", "why": "see CHANGELOG.md"}]}'
        got, n = self.rj(text)
        self.assertEqual(got, text.replace("-- CHANGELOG.md", "-- methodology/CHANGELOG.md"))
        self.assertEqual(n, 1)

    def test_non_ascii_text_survives_byte_for_byte(self):
        raw = '{"_": "a — dash é", "dash": "—", "path": "SESSION_RUNNER.md", "raw": "—"}'
        got, n = self.rj(raw)
        self.assertEqual(got, raw.replace('"SESSION_RUNNER.md"', '"methodology/SESSION_RUNNER.md"'))
        self.assertEqual(n, 1)

    def test_a_rewritten_command_keeps_its_non_ascii_characters_as_they_were_written(self):
        text = '{"gates": [{"command": "echo — CHANGELOG.md é"}]}'
        got, n = self.rj(text)
        self.assertEqual(got, '{"gates": [{"command": "echo — methodology/CHANGELOG.md é"}]}')
        self.assertEqual(n, 1)

    def test_text_that_is_not_json_is_a_value_error(self):
        with self.assertRaises(ValueError):
            self.rj("{ not json")

    def test_a_value_that_is_not_a_string_is_left(self):
        text = '{"path": 3, "files": [1, null, true], "results_file": null}'
        self.assertEqual(self.rj(text), (text, 0))

    # --- the ledger entry ---
    ENTRY = "### 2026-10-07 · [ad hoc] Layout migration: x\n\nbody\n"

    def test_an_entry_goes_under_the_current_months_heading(self):
        text = "front\n\n---\n\n## 2026-10\n\n### 2026-10-01 · [ad hoc] old\n\nold body\n"
        got = self.m.insert_entry(text, self.ENTRY, "2026-10")
        self.assertEqual(got, "front\n\n---\n\n## 2026-10\n\n" + self.ENTRY + "\n### 2026-10-01 · [ad hoc] old\n\nold body\n")

    def test_an_entry_gets_a_new_month_heading_above_an_older_months(self):
        text = "front\n\n## 2026-09\n\n### 2026-09-01 · [ad hoc] old\n\nold body\n"
        got = self.m.insert_entry(text, self.ENTRY, "2026-10")
        self.assertEqual(got, "front\n\n## 2026-10\n\n" + self.ENTRY + "\n## 2026-09\n\n### 2026-09-01 · [ad hoc] old\n\nold body\n")

    def test_an_entry_goes_above_the_first_entry_when_there_is_no_month_heading(self):
        text = "front\n\n### 2026-09-01 · [ad hoc] old\n\nold body\n"
        got = self.m.insert_entry(text, self.ENTRY, "2026-10")
        self.assertEqual(got, "front\n\n" + self.ENTRY + "\n### 2026-09-01 · [ad hoc] old\n\nold body\n")

    def test_an_entry_goes_at_the_end_of_a_ledger_with_no_entry_and_the_seed_sentinel_is_dropped(self):
        text = ("front\n\n<!-- METHODOLOGY-SEED-SENTINEL: fresh ledger.\n     more. -->\n\n---\n\n<!-- Entries go below. -->\n")
        got = self.m.insert_entry(text, self.ENTRY, "2026-10")
        self.assertNotIn("SENTINEL", got)
        self.assertTrue(got.endswith("<!-- Entries go below. -->\n\n" + self.ENTRY), got)

    # --- the entry never lands in a fenced example ---
    SEEDED = ("# Changelog\n\nintro\n\n## How to add an entry\n\n"
              "```\n### YYYY-MM-DD · [SOURCE] summary\n```\n\n"
              "```\n### 2026-01-15 · [ad hoc] Ship the export-retry fix\n- **Change:** x\n```\n\n"
              "<!-- Entries go below, newest on top. -->\n\n")

    def test_an_example_heading_inside_a_fence_is_not_taken_for_the_first_entry(self):
        text = self.SEEDED + "### 2026-09-01 · [ad hoc] old\n\nold body\n"
        got = self.m.insert_entry(text, self.ENTRY, "2026-10")
        self.assertEqual(got, self.SEEDED + self.ENTRY + "\n### 2026-09-01 · [ad hoc] old\n\nold body\n")

    def test_a_month_heading_inside_a_fence_is_not_taken_for_the_first_month(self):
        header = "front\n\n```\n## 2026-01\n\n### 2026-01-15 · [ad hoc] example\n```\n\n<!-- Entries go below. -->\n\n"
        text = header + "## 2026-09\n\n### 2026-09-01 · [ad hoc] old\n\nold body\n"
        got = self.m.insert_entry(text, self.ENTRY, "2026-10")
        self.assertEqual(got, header + "## 2026-10\n\n" + self.ENTRY + "\n## 2026-09\n\n### 2026-09-01 · [ad hoc] old\n\nold body\n")

    def test_the_current_months_heading_after_a_fenced_example_takes_the_entry_under_it(self):
        header = "front\n\n```\n### 2026-01-15 · [ad hoc] example\n```\n\n"
        text = header + "## 2026-10\n\n### 2026-10-01 · [ad hoc] old\n\nold body\n"
        got = self.m.insert_entry(text, self.ENTRY, "2026-10")
        self.assertEqual(got, header + "## 2026-10\n\n" + self.ENTRY + "\n### 2026-10-01 · [ad hoc] old\n\nold body\n")

    def test_a_ledger_whose_only_dated_headings_are_fenced_examples_takes_the_entry_at_the_end(self):
        text = ("front\n\n<!-- METHODOLOGY-SEED-SENTINEL: fresh ledger.\n     more. -->\n\n"
                + self.SEEDED[self.SEEDED.index("## How"):])
        got = self.m.insert_entry(text, self.ENTRY, "2026-10")
        self.assertNotIn("SENTINEL", got)
        self.assertTrue(got.endswith("<!-- Entries go below, newest on top. -->\n\n" + self.ENTRY), got)
        self.assertIn("```\n### 2026-01-15 · [ad hoc] Ship the export-retry fix\n- **Change:** x\n```\n", got)

    def test_a_tilde_fence_is_a_fence(self):
        header = "front\n\n~~~\n### 2026-01-15 · [ad hoc] example\n~~~\n\n"
        text = header + "### 2026-09-01 · [ad hoc] old\n\nold body\n"
        got = self.m.insert_entry(text, self.ENTRY, "2026-10")
        self.assertEqual(got, header + self.ENTRY + "\n### 2026-09-01 · [ad hoc] old\n\nold body\n")

    def test_a_fence_with_an_info_string_opens_one(self):
        header = "front\n\n```markdown\n### 2026-01-15 · [ad hoc] example\n```\n\n"
        text = header + "### 2026-09-01 · [ad hoc] old\n\nold body\n"
        got = self.m.insert_entry(text, self.ENTRY, "2026-10")
        self.assertEqual(got, header + self.ENTRY + "\n### 2026-09-01 · [ad hoc] old\n\nold body\n")

    def test_a_shorter_fence_inside_a_longer_one_does_not_close_it(self):
        header = "front\n\n````\n```\n### 2026-01-15 · [ad hoc] example\n```\nx\n````\n\n"
        text = header + "### 2026-09-01 · [ad hoc] old\n\nold body\n"
        got = self.m.insert_entry(text, self.ENTRY, "2026-10")
        self.assertEqual(got, header + self.ENTRY + "\n### 2026-09-01 · [ad hoc] old\n\nold body\n")

    def test_a_line_with_an_info_string_does_not_close_a_fence(self):
        header = "front\n\n```\n```python\n### 2026-01-15 · [ad hoc] example\n```\n\n"
        text = header + "### 2026-09-01 · [ad hoc] old\n\nold body\n"
        got = self.m.insert_entry(text, self.ENTRY, "2026-10")
        self.assertEqual(got, header + self.ENTRY + "\n### 2026-09-01 · [ad hoc] old\n\nold body\n")

    def test_a_closing_fence_longer_than_the_opening_one_closes_it(self):
        header = "front\n\n```\n### 2026-01-15 · [ad hoc] example\n`````\n\n"
        text = header + "### 2026-09-01 · [ad hoc] old\n\nold body\n"
        got = self.m.insert_entry(text, self.ENTRY, "2026-10")
        self.assertEqual(got, header + self.ENTRY + "\n### 2026-09-01 · [ad hoc] old\n\nold body\n")

    def test_a_line_of_the_other_fence_character_does_not_close_a_fence(self):
        header = "front\n\n```\n~~~\n### 2026-01-15 · [ad hoc] example\n```\n\n"
        text = header + "### 2026-09-01 · [ad hoc] old\n\nold body\n"
        got = self.m.insert_entry(text, self.ENTRY, "2026-10")
        self.assertEqual(got, header + self.ENTRY + "\n### 2026-09-01 · [ad hoc] old\n\nold body\n")

    def test_a_ledger_with_dos_line_endings_keeps_its_fence_and_its_place(self):
        header = "front\r\n\r\n```\r\n### 2026-01-15 · [ad hoc] example\r\n```\r\n\r\n"
        text = header + "### 2026-09-01 · [ad hoc] old\r\n\r\nold body\r\n"
        got = self.m.insert_entry(text, self.ENTRY, "2026-10")
        self.assertEqual(got, header + self.ENTRY + "\n### 2026-09-01 · [ad hoc] old\r\n\r\nold body\r\n")

    def test_a_line_of_two_backticks_is_not_a_fence(self):
        header = "front\n\n``not a fence``\n\n"
        text = header + "### 2026-09-01 · [ad hoc] old\n\nold body\n"
        got = self.m.insert_entry(text, self.ENTRY, "2026-10")
        self.assertEqual(got, header + self.ENTRY + "\n### 2026-09-01 · [ad hoc] old\n\nold body\n")

    def test_a_fence_that_never_closes_after_the_first_entry_is_not_this_tools_concern(self):
        text = "front\n\n### 2026-09-01 · [ad hoc] old\n\n```\nnever closed\n"
        got = self.m.insert_entry(text, self.ENTRY, "2026-10")
        self.assertEqual(got, "front\n\n" + self.ENTRY + "\n### 2026-09-01 · [ad hoc] old\n\n```\nnever closed\n")

    def test_a_fence_that_never_closes_before_any_entry_is_refused_not_guessed(self):
        text = "front\n\n```\n### 2026-01-15 · [ad hoc] example\n\n### 2026-09-01 · [ad hoc] old\n"
        with self.assertRaises(self.m.Unsafe) as cm:
            self.m.insert_entry(text, self.ENTRY, "2026-10")
        self.assertIn("never closes", str(cm.exception))

    def test_the_entry_text_names_the_tool_the_tier_the_count_and_what_was_edited(self):
        report = {"tier": "1", "canonical": {"sha": "abcdef0123456789", "modified": False}}
        text = self.m.ledger_entry_text(report, [{}] * 5, ["CLAUDE.md", ".gitignore"], "2026-10-07")
        self.assertTrue(text.startswith("### 2026-10-07 · [ad hoc] Layout migration: "))
        for piece in ("tier 1", "5 files", "abcdef0", "`CLAUDE.md`, `.gitignore`", "`bin/migrate-layout`"):
            self.assertIn(piece, text)
        self.assertNotIn("abcdef01", text)
        none = self.m.ledger_entry_text(report, [{}] * 5, [], "2026-10-07")
        self.assertIn("no file (none named a moved path)", none)

    # --- what a check difference is ---
    def sides(self, **over):
        side = {"status": {"exit": 0, "tracked": 23, "current": 23}, "ledger": {"exit": 0}, "handoff": {"exit": 1},
                "links": {"exit": 0, "framework": 0, "project": 0}, "proofs": {"count": 2, "histogram": {"0": 2}},
                "history": {"commits": 4}}
        before, after = dict(side), dict(side)
        after["history"] = {"commits": 5}
        for k, (b, a) in over.items():
            before[k], after[k] = b, a
        return before, after

    def test_nothing_that_must_hold_changing_is_no_difference(self):
        self.assertEqual(self.m.check_differences(*self.sides()), [])

    def test_each_rule_names_itself(self):
        s = lambda **kw: self.m.check_differences(*self.sides(**kw))
        self.assertEqual(s(status=({"exit": 0, "tracked": 23, "current": 23}, {"exit": 0, "tracked": 23, "current": 22})), ["status"])
        self.assertEqual(s(status=({"exit": 0, "tracked": 23, "current": 23}, {"exit": 1, "tracked": 0, "current": 0})), ["status"])
        self.assertEqual(s(ledger=({"exit": 0}, {"exit": 1})), ["ledger"])
        self.assertEqual(s(handoff=({"exit": 1}, {"exit": 0})), ["handoff"])
        self.assertEqual(s(proofs=({"count": 2, "histogram": {"0": 2}}, {"count": 2, "histogram": {"0": 1, "1": 1}})), ["proofs"])
        self.assertEqual(s(history=({"commits": 4}, {"commits": 4})), ["history"])

    def test_a_status_that_is_bad_on_both_sides_is_still_a_difference_because_the_rule_is_about_after(self):
        """bin/status must read every TRACKED file current AFTER the move, whatever it read before."""
        s = lambda **kw: self.m.check_differences(*self.sides(**kw))
        short = {"exit": 0, "tracked": 23, "current": 22}
        self.assertEqual(s(status=(short, short)), ["status"])
        failed = {"exit": 1, "tracked": 0, "current": 0}
        self.assertEqual(s(status=(failed, failed)), ["status"], "tracked == current == 0 but bin/status did not run")

    def test_a_project_without_a_ledger_has_no_history_to_lose(self):
        self.assertEqual(self.m.check_differences(*self.sides(history=({"commits": 0}, {"commits": 0}))), [])

    # --- the links cell: the framework's documents are judged, the project's own files are reported ---
    def cell(self, exit_code, framework, project):
        return {"exit": exit_code, "framework": framework, "project": project}

    def test_a_framework_link_that_newly_dangles_is_a_difference_and_the_rule_is_about_the_count(self):
        s = lambda **kw: self.m.check_differences(*self.sides(**kw))
        self.assertEqual(s(links=(self.cell(0, 0, 0), self.cell(1, 2, 0))), ["links"])
        self.assertEqual(s(links=(self.cell(1, 2, 0), self.cell(1, 3, 0))), ["links"], "one more is a change")
        self.assertEqual(s(links=(self.cell(1, 2, 0), self.cell(1, 2, 0))), [], "a count that did not change is not one")
        self.assertEqual(s(links=(self.cell(1, 3, 0), self.cell(1, 2, 0))), ["links"], "nor is one fewer: like the other checks, the rule is that it did not change")

    def test_links_in_the_projects_own_files_are_reported_and_never_a_difference(self):
        """A committed ledger entry is never edited, so a link in one that was right where the ledger sat is not the move's defect."""
        s = lambda **kw: self.m.check_differences(*self.sides(**kw))
        self.assertEqual(s(links=(self.cell(0, 0, 0), self.cell(1, 0, 6))), [])

    def test_a_links_check_that_could_not_be_read_after_the_move_is_a_difference_never_a_zero(self):
        s = lambda **kw: self.m.check_differences(*self.sides(**kw))
        self.assertEqual(s(links=(self.cell(0, 0, 0), self.cell(2, None, None))), ["links"])
        self.assertEqual(s(links=(self.cell(0, 0, 0), self.cell("timeout", None, None))), ["links"])

    def test_the_cell_counts_the_dangling_links_by_whether_the_file_they_sit_in_is_the_frameworks(self):
        legacy, new = TRACKED_DESTS[0], NEW_OF[TRACKED_DESTS[0]]
        owned = NEW_OF[SEED_DESTS[0]]
        text = ("check-links: FAIL — 3 dangling link(s) in the tree at /x (new layout):\n"
                "  %s:12  ->  gone.md\n  %s:7  ->  docs/methodology/HOW_TO_USE.md\n  %s:3  ->  also-gone.md\n\n"
                "Distributed files author cross-references for the ADOPTER layout. Fix the target above, not the layout.\n"
                % (new, owned, legacy))
        got = self.m.links_cell(1, text)
        self.assertEqual((got["exit"], got["framework"], got["project"]), (1, 2, 1), "either layout's name for a framework file counts")
        ok = self.m.links_cell(0, "check-links: OK — 80 relative link(s) across 23 distributed markdown files resolve in the tree at /x.\n")
        self.assertEqual((ok["exit"], ok["framework"], ok["project"]), (0, 0, 0))

    def test_a_framework_document_missing_from_the_tree_counts_as_a_framework_failure(self):
        """check-links reports a distributed file it cannot find as line 0 with a placeholder target; that is a framework document too."""
        text = ("check-links: FAIL — 1 dangling link(s) in the tree at /x (new layout):\n"
                "  %s:0  ->  <distributed file missing from tree>\n" % NEW_OF[TRACKED_DESTS[0]])
        got = self.m.links_cell(1, text)
        self.assertEqual((got["framework"], got["project"]), (1, 0))

    def test_a_failure_whose_lines_cannot_be_read_is_unknown_and_a_run_that_could_not_decide_has_no_counts(self):
        """An exit 1 with no line in the known shape would otherwise read as zero dangling: a green made of a format change."""
        shaped = "  %s:3  ->  x.md\n" % NEW_OF[TRACKED_DESTS[0]]  # a line in the known shape, from a run that did not decide
        for code, text in ((1, "check-links: FAIL — the output changed shape\n"), (2, "usage: check-links\n"), (2, shaped), ("timeout", shaped)):
            got = self.m.links_cell(code, text)
            self.assertEqual((got["framework"], got["project"]), (None, None), (code, text))

    # --- which files are a ledger, a CI file and the rest ---
    def test_a_path_is_sorted_into_its_category(self):
        want = {".github/workflows/ci.yml": "ci", ".circleci/config.yml": "ci", ".gitlab-ci.yml": "ci", "Jenkinsfile": "ci",
                ".claude/settings.json": "harness", ".githooks/pre-commit": "hooks", "CHANGELOG.md": "ledger",
                "methodology/HANDOFFS.md": "ledger", "SESSION_NOTES.md": "ledger",
                "docs/archive/CHANGELOG-through-2026-01-01.md": "ledger", "methodology/archive/HANDOFFS-through-2026-01-01-2.md": "ledger",
                "docs/archive/notes.md": "other", "README.md": "other", "src/CHANGELOG.md": "other", "ROADMAP.md": "other"}
        for path, cat in want.items():
            self.assertEqual(self.m.hit_category(path), cat, path)

    def test_a_machine_read_file_is_sorted_by_what_a_machine_does_with_it(self):
        """The report used to put a project's tests, scripts and proofs in `other` with its prose. The
        text is the file's own, read for a first line; a prose extension under tests/ is prose (the survey's prototype
        sorted tests/eval/PHASE_E_AGREEMENT_REPORT.md as a test, because its directory rule ran first)."""
        want = [("tests/test_read_budget.py", "", "tests"), ("tests/testthat/test-x.R", "", "tests"), ("src/foo_test.go", "", "tests"),
                ("pkg/conftest.py", "", "tests"), ("web/app.test.ts", "", "tests"),
                ("tests/helpers.py", "", "tests"), ("test/fixtures/data.json", "", "tests"), ("spec/models/user.rb", "", "tests"),
                ("docs/x/SESSION_NOTES-pointer-collapse.verify.sh", "", "proofs"), ("verify-all.sh", "", "proofs"),
                ("scripts/refresh.py", "", "scripts"), ("run.sh", "", "scripts"), ("web/scripts/archive.ts", "", "scripts"),
                ("vignettes/data-raw/build.R", "", "scripts"),
                ("bin/refresh", "#!/usr/bin/env python3\nprint(1)\n", "scripts"), ("bin/notes", "just text\n", "other"),
                ("Makefile", "", "config"), (".Rbuildignore", "", "config"), ("package.json", "", "config"), ("tox.ini", "", "config"),
                ("docker-compose.yml", "", "config"),
                (".husky/pre-commit", "", "hooks"), (".pre-commit-config.yaml", "", "hooks"), (".githooks/commit-msg", "", "hooks"),
                (".github/workflows/ci.yml", "", "ci"), (".claude/settings.json", "", "harness"),
                ("tests/eval/REPORT.md", "", "other"), ("tests/README.md", "", "other"), ("docs/guide.qmd", "", "other"),
                ("README.md", "", "other"), ("notes.txt", "", "other"), ("data/table.csv", "", "other")]
        for path, text, cat in want:
            self.assertEqual(self.m.hit_category(path, text), cat, path)
        self.assertEqual(self.m.CATEGORIES, ("ci", "hooks", "tests", "proofs", "scripts", "config", "harness", "ledger", "other"))
        self.assertEqual(self.m.MACHINE_READ, ("ci", "hooks", "tests", "proofs", "scripts", "config"))

    def test_a_pattern_list_a_program_reads_is_config_except_the_gitignore(self):
        """`.vscodeignore` carried 26 mentions of moved names (21 on code lines) and was filed under
        `other` with the prose, 26 of that adopter's 254 mentions there. vsce 3.6.0 matches each line with minimatch and no `matchBase`, so a bare name is the project root's
        and `methodology/SESSION_RUNNER.md` is packaged. A `.gitignore` stays prose: git matches a bare name at any depth,
        so an entry the tool does not anchor-rewrite still ignores the moved file."""
        want = [(".vscodeignore", "config"), ("pkg/.npmignore", "config"), (".vercelignore", "config"), (".dockerignore", "config"),
                ("mts-backend/.railwayignore", "config"), (".Rbuildignore", "config"), (".gcloudignore", "config"),
                (".gitignore", "other"), ("docs/.gitignore", "other"), ("ignore", "other"), (".ignore-me", "other"),
                ("notes.vscodeignore", "other"), ("vscodeignore", "other")]
        for path, cat in want:
            self.assertEqual(self.m.hit_category(path), cat, path)

    # --- the pattern rule ---
    PATTERN_MAP = {"SESSION_RUNNER.md": "methodology/SESSION_RUNNER.md", "CHANGELOG.md": "methodology/CHANGELOG.md",
                   "docs/methodology/HOW_TO_USE.md": "methodology/HOW_TO_USE.md", "dashboard.html": "methodology/dashboard.html"}

    def test_a_regex_line_that_covers_a_file_where_it_is_and_not_where_it_goes_is_exposed(self):
        e = self.m.pattern_exposure("^SESSION_RUNNER.*\\.md$\n^README\\.md$\n", self.PATTERN_MAP)
        self.assertEqual(e["exposed"], ["SESSION_RUNNER.md"])
        self.assertEqual(e["lines"], [{"line": 1, "text": "^SESSION_RUNNER.*\\.md$", "files": ["SESSION_RUNNER.md"]}])
        self.assertEqual(e["unread"], 0)

    def test_a_line_matches_without_regard_to_case(self):
        """R 4.6.1 built a probe package without FOO.txt under `^foo\\.txt$`."""
        self.assertEqual(self.m.pattern_exposure("^session_runner.*\\.md$\n", self.PATTERN_MAP)["exposed"], ["SESSION_RUNNER.md"])

    def test_a_line_that_matches_a_directory_covers_what_is_under_it(self):
        """R 4.6.1 left docsdir/inner.txt out of a package under `^docsdir$`; the files under docs/methodology/ move out of it."""
        e = self.m.pattern_exposure("^docs$\n", self.PATTERN_MAP)
        self.assertEqual(e["exposed"], ["docs/methodology/HOW_TO_USE.md"])

    def test_a_line_that_covers_the_destination_clears_the_exposure(self):
        """The same probe built `methodology/SESSION_RUNNER.md` into the package, and one more line, `^methodology$`, stopped it."""
        for extra in ("^methodology$", "^methodology/", "methodology"):
            e = self.m.pattern_exposure("^SESSION_RUNNER.*\\.md$\n%s\n" % extra, self.PATTERN_MAP)
            self.assertEqual((e["exposed"], e["lines"]), ([], []), extra)

    def test_a_line_that_still_matches_after_the_move_is_not_exposed(self):
        self.assertEqual(self.m.pattern_exposure("SESSION_RUNNER\n", self.PATTERN_MAP)["exposed"], [])

    def test_a_hash_line_is_a_pattern_not_a_comment(self):
        """R 4.6.1 left ALPHA.md out of a package under the single line `# |ALPHA`: a line that starts with # is a regular
        expression, here an alternation. Skipping hash lines would miss it; a plain remark matches no path, so it costs nothing."""
        self.assertEqual(self.m.pattern_exposure("# |^SESSION_RUNNER\\.md$\n", self.PATTERN_MAP)["exposed"], ["SESSION_RUNNER.md"])
        self.assertEqual(self.m.pattern_exposure("# SESSION_RUNNER.md is ignored below\n", self.PATTERN_MAP)["exposed"], [])

    def test_a_line_that_is_not_a_regular_expression_is_counted_and_the_rest_are_read(self):
        e = self.m.pattern_exposure("[unclosed\n^CHANGELOG\\.md$\n", self.PATTERN_MAP)
        self.assertEqual((e["unread"], e["exposed"], [x["line"] for x in e["lines"]]), (1, ["CHANGELOG.md"], [2]))

    def test_a_posix_class_is_counted_as_unread_not_misread(self):
        """`[[:alpha:]]` is a character class to R's PCRE and a set containing `[` and `:` to Python's `re`, so evaluating it
        would answer for a different pattern. It is counted as a line not evaluated, and said quietly."""
        import io
        import contextlib
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            e = self.m.pattern_exposure("^[[:alpha:]]+\\.md$\n^[[:^digit:]]+\\.md$\n^CHANGELOG\\.md$\n", self.PATTERN_MAP)
        self.assertEqual((e["unread"], e["exposed"]), (2, ["CHANGELOG.md"]), "the negated class is a class too")
        self.assertEqual(err.getvalue(), "")

    def test_an_empty_line_is_not_a_pattern(self):
        """An empty regular expression would match every path; R drops the empty lines, so the rule does."""
        for text in ("", "\n\n", "\r\n"):
            e = self.m.pattern_exposure(text, self.PATTERN_MAP)
            self.assertEqual((e["exposed"], e["lines"], e["unread"]), ([], [], 0), repr(text))

    def test_a_file_exposed_by_two_lines_is_listed_under_both_and_counted_once(self):
        e = self.m.pattern_exposure("^SESSION_RUNNER\\.md$\n^SESSION_.*\\.md$\n", self.PATTERN_MAP)
        self.assertEqual(e["exposed"], ["SESSION_RUNNER.md"])
        self.assertEqual([(x["line"], x["files"]) for x in e["lines"]], [(1, ["SESSION_RUNNER.md"]), (2, ["SESSION_RUNNER.md"])])

    def test_the_lines_come_in_line_order_not_in_the_order_the_files_were_found(self):
        """The map lists SESSION_RUNNER.md before dashboard.html, and the line that covers dashboard.html is the first line."""
        e = self.m.pattern_exposure("^dashboard\\.html$\n^SESSION_RUNNER\\.md$\n", self.PATTERN_MAP)
        self.assertEqual([x["line"] for x in e["lines"]], [1, 2])

    def test_the_files_of_a_line_come_in_name_order(self):
        """The map lists SESSION_RUNNER.md before CHANGELOG.md; the one line that covers both lists them in name order."""
        e = self.m.pattern_exposure("^[A-Z_]+\\.md$\n", self.PATTERN_MAP)
        self.assertEqual(e["lines"][0]["files"], ["CHANGELOG.md", "SESSION_RUNNER.md"])

    def test_nothing_moves_so_nothing_is_exposed(self):
        self.assertEqual(self.m.pattern_exposure("^SESSION_RUNNER.*\\.md$\n", {})["exposed"], [])

    # --- the vsce rule ---
    # Each row is (pattern, path, answer) as minimatch 10.2.5 with `{ dot: true }` gave it, the call vsce 3.9.2 makes
    # (`package.js` `collectFiles`); the rows were measured by running minimatch through node.
    VSCE_ORACLE = [
        ("a/**", "a", False), ("a/**", "a/b", True), ("a/**", "a/b/c", True), ("**", "a", True), ("**", "a/b", True), ("**", ".x", True),
        ("**/*.map", "x.map", True), ("**/*.map", "a/b/x.map", True), ("**/*.map", "a.map/b", False),
        ("*.md", "x.md", True), ("*.md", "a/x.md", False), ("*.md", ".md", True), ("*", ".hidden", True), ("*", "a/b", False),
        ("SESSION_RUNNER.md", "SESSION_RUNNER.md", True), ("SESSION_RUNNER.md", "methodology/SESSION_RUNNER.md", False),
        ("methodology/**", "methodology/SESSION_RUNNER.md", True), ("methodology/**", "methodology", False),
        ("/a", "a", False), ("./a", "a", False), ("a/./b", "a/b", False), ("a/", "a", False), ("dir/", "dir/x", False),
        ("{a,b}.md", "a.md", True), ("{a,b}.md", "b.md", True), ("{a,b}.md", "c.md", False),
        ("[ab].md", "a.md", True), ("[ab].md", "c.md", False), ("[!a].md", "b.md", True), ("[!a].md", "a.md", False),
        ("[^a].md", "b.md", True), ("[a-c].md", "b.md", True), ("[a-c].md", "d.md", False),
        ("a?c", "abc", True), ("a?c", "a/c", False), ("a?c", "ac", False),
        ("**/.git/**", ".git/x", True), ("**/.git/**", "a/.git/x", True), ("**/.git", ".git", True), ("**/.git", "a/.git", True),
        (".eslintrc*", ".eslintrc.json", True), (".eslintrc*", "a/.eslintrc.json", False),
        ("a**b", "axxb", True), ("a**b", "a/b", False), ("a**/b", "a/x/b", False), ("**a", "xa", True), ("**a", "x/a", False),
        ("a/**/b", "a/b", True), ("a/**/b", "a/x/b", True), ("a/**/b", "a/x/y/b", True), ("a/**/b", "a/x/c", False),
        ("**/a", "a", True), ("**/a", "x/a", True), ("**/a", "x/ab", False), ("**/**", "a", True),
        ("a/*", "a/b", True), ("a/*", "a", False), ("a/*", "a/b/c", False), ("a b", "a b", True),
        ("{a,b,c}.md", "c.md", True), ("{a,b,c}.md", "b.md", True), ("{a,b,c}.md", "d.md", False),
        ("{a,b/c}.md", "b/c.md", True), ("{a,{b,c}}.md", "c.md", True), ("x{,y}", "x", True), ("x{,y}", "xy", True),
        ("session_runner.md", "SESSION_RUNNER.md", False),
    ]
    VSCE_MAP = {"SESSION_RUNNER.md": "methodology/SESSION_RUNNER.md", "CHANGELOG.md": "methodology/CHANGELOG.md",
                "docs/methodology/HOW_TO_USE.md": "methodology/HOW_TO_USE.md",
                "docs/archive/CHANGELOG-through-2026-08-01.md": "methodology/archive/CHANGELOG-through-2026-08-01.md",
                "methodology_trim.py": "methodology/methodology_trim.py", ".context-budget.json": "methodology/.context-budget.json"}

    def vsce(self, text, mapping=None):
        return self.m.vscodeignore_exposure(text, self.VSCE_MAP if mapping is None else mapping)

    def test_the_translation_of_a_glob_answers_as_minimatch_does(self):
        for pattern, path, want in self.VSCE_ORACLE:
            match = self.m.vsce_glob(pattern)
            self.assertIsNotNone(match, "a pattern the table lists is one the rule reads: " + pattern)
            self.assertIs(match(path), want, "%r against %r" % (pattern, path))

    def test_a_glob_it_does_not_read_is_none_and_never_a_guess(self):
        """An extended glob, a numeric or letter range, a backslash, a POSIX class, a lone brace and an empty path segment are
        read differently by minimatch than by any reading made here, so they are counted and not evaluated."""
        for pattern in ("+(a|b)", "@(a|b)", "!(a)", "?(a)b", "*(a)", "x{1..3}", "x{a..c}", "a\\*b", "[[:upper:]]*", "{a}", "x{", "x}", "a//b", "[a", "[]", "[]a]", "[z-a]"):
            self.assertIsNone(self.m.vsce_glob(pattern), pattern)

    def test_a_bare_name_is_the_project_roots_and_not_the_new_directorys(self):
        """vsce 3.9.2 matches `SESSION_RUNNER.md` against `methodology/SESSION_RUNNER.md` as false: the move leaves the file
        packaged. The same row of the probe read vsce 3.6.0 (`vsce ls`): the file was listed after the move."""
        e = self.vsce("SESSION_RUNNER.md\nREADME.md\n")
        self.assertEqual(e["exposed"], ["SESSION_RUNNER.md"])
        self.assertEqual(e["lines"][0], {"line": 1, "text": "SESSION_RUNNER.md", "files": ["SESSION_RUNNER.md"]})
        self.assertEqual(e["unread"], 0)

    def test_a_line_for_the_new_directory_clears_every_line_it_covers(self):
        for extra in ("methodology/**", "methodology", "methodology/"):
            e = self.vsce("SESSION_RUNNER.md\ndocs/**\n**/*.py\n" + extra + "\n")
            self.assertEqual((e["exposed"], e["lines"]), ([], []), extra)

    def test_a_directory_name_covers_what_is_under_it_and_a_leaf_glob_does_not(self):
        """vsce adds `/**` to a line whose last segment has no `*` (`package.js` line 1295), so `docs` is `docs/**`; `docs/*` is
        not, and minimatch gives `a/*` against `a/b/c` as false."""
        deep = {"docs/methodology/HOW_TO_USE.md": "methodology/HOW_TO_USE.md"}
        for line in ("docs", "docs/", "docs/**", "**/docs/**"):
            self.assertEqual(self.vsce(line + "\n", deep)["exposed"], ["docs/methodology/HOW_TO_USE.md"], line)
        self.assertEqual(self.vsce("docs/*\n", deep)["exposed"], [])
        self.assertEqual(self.vsce("docs/*\n", {"docs/x.md": "methodology/x.md"})["exposed"], ["docs/x.md"])

    def test_a_double_star_leaf_covers_the_file_at_any_depth_and_so_still_covers_it_after_the_move(self):
        e = self.vsce("**/*.py\n")
        self.assertEqual(e["exposed"], [], "methodology/methodology_trim.py is ignored too")

    def test_a_star_does_not_cross_a_directory_so_it_stops_covering_the_moved_file(self):
        """`*.md` against `methodology/SESSION_RUNNER.md` is false with no `matchBase`: a person who wrote it to mean every
        markdown file at any depth is exposed by the move."""
        e = self.vsce("*.md\n")
        self.assertEqual(e["exposed"], ["CHANGELOG.md", "SESSION_RUNNER.md"],
                         "a file below the root (docs/methodology/HOW_TO_USE.md) is not covered by `*.md` where it is")

    def test_a_star_reaches_a_dot_file(self):
        """`{ dot: true }`: `*` against `.hidden` and `*.md` against `.md` are true."""
        self.assertEqual(self.vsce("*.json\n")["exposed"], [".context-budget.json"])

    def test_the_rule_is_case_sensitive(self):
        self.assertEqual(self.vsce("session_runner.md\n")["exposed"], [])

    def test_a_line_written_the_gitignore_way_matches_nothing(self):
        """`/SESSION_RUNNER.md` and `./SESSION_RUNNER.md` are false against `SESSION_RUNNER.md` (measured): they cover it neither
        where it is nor where it goes, so they are not exposed, and a person who meant them as the root's is told nothing."""
        e = self.vsce("/SESSION_RUNNER.md\n./CHANGELOG.md\n")
        self.assertEqual((e["exposed"], e["unread"]), ([], 0), "they are read, and cover nothing")

    def test_a_negation_brings_a_file_back_and_applies_to_a_directory_name_too(self):
        """vsce keeps a file when ANY negation matches it, whatever its place among the lines (`collectFiles`: `!ignore.some(...) ||
        negate.some(...)`), and the `/**` it adds to a directory name is added to a negation as well."""
        deep = {"docs/methodology/HOW_TO_USE.md": "methodology/HOW_TO_USE.md"}
        self.assertEqual(self.vsce("docs/**\n!docs/methodology/HOW_TO_USE.md\n", deep)["exposed"], [], "it is packaged where it is")
        self.assertEqual(self.vsce("!docs/methodology\ndocs/**\n", deep)["exposed"], [], "a negation above the line it undoes counts too")
        self.assertEqual(self.vsce("docs/**\nmethodology/**\n!methodology/HOW_TO_USE.md\n", deep)["exposed"],
                         ["docs/methodology/HOW_TO_USE.md"], "a negation that brings it back where it goes leaves it packaged")

    def test_vsces_own_default_list_is_part_of_the_answer(self):
        """The root `.gitattributes` is on vsce's default list and `methodology/.gitattributes` is not: `bin/migrate-layout`
        moves it, and 1 of the 36 files a real move put into an adopter's `.vsix` was this one."""
        e = self.vsce("", {".gitattributes": "methodology/.gitattributes"})
        self.assertEqual(e["exposed"], [".gitattributes"])
        self.assertEqual(e["lines"], [{"line": 0, "text": "(vsce default) .gitattributes", "files": [".gitattributes"]}])
        self.assertEqual(self.vsce("methodology/**\n", {".gitattributes": "methodology/.gitattributes"})["exposed"], [])

    def test_a_file_vsce_never_ignores_stays_packaged_whatever_the_file_says(self):
        """`!package.json` and `!README.md` are appended to every list."""
        moved = {"README.md": "methodology/README.md", "package.json": "methodology/package.json"}
        self.assertEqual(self.vsce("README.md\npackage.json\n", moved)["exposed"], [])

    def test_a_hash_line_is_a_comment_and_a_line_is_trimmed(self):
        """Unlike R, vsce drops a line that starts with `#` after trimming it."""
        self.assertEqual(self.vsce("# SESSION_RUNNER.md\n   # CHANGELOG.md\n")["exposed"], [])
        self.assertEqual(self.vsce("   SESSION_RUNNER.md \t\n")["exposed"], ["SESSION_RUNNER.md"])
        self.assertEqual(self.vsce("  #note.md\n", {"#note.md": "methodology/#note.md"})["exposed"], [], "dropped before it is read as a pattern")

    def test_a_line_break_of_any_kind_and_a_byte_order_mark_are_read_as_vsce_reads_them(self):
        """vsce splits on `\\n` and on `\\r`, and `String.prototype.trim` removes a byte order mark; the number printed is the
        line an editor shows, so `\\r\\n` is one break."""
        e = self.vsce("# a\r\nSESSION_RUNNER.md\r\nCHANGELOG.md\r\n")
        self.assertEqual([(x["line"], x["text"]) for x in e["lines"]], [(2, "SESSION_RUNNER.md"), (3, "CHANGELOG.md")])
        self.assertEqual([x["line"] for x in self.vsce("# a\rSESSION_RUNNER.md\r")["lines"]], [2], "a lone carriage return breaks too")
        self.assertEqual(self.vsce("﻿SESSION_RUNNER.md\n")["exposed"], ["SESSION_RUNNER.md"])

    def test_a_brace_list_is_one_line_that_covers_several_files(self):
        e = self.vsce("{SESSION_RUNNER,CHANGELOG}.md\n")
        self.assertEqual(e["exposed"], ["CHANGELOG.md", "SESSION_RUNNER.md"])
        self.assertEqual([(x["line"], x["files"]) for x in e["lines"]], [(1, ["CHANGELOG.md", "SESSION_RUNNER.md"])])

    def test_a_line_that_is_not_read_is_counted_and_the_rest_are_read(self):
        e = self.vsce("@(SESSION_RUNNER|CHANGELOG).md\nx{1..3}\nCHANGELOG\\.md\n[[:upper:]]*.md\n{a}\nCHANGELOG.md\n")
        self.assertEqual((e["unread"], e["exposed"], [x["line"] for x in e["lines"]]), (5, ["CHANGELOG.md"], [6]))

    def test_the_lines_come_in_line_order_the_defaults_last_and_the_files_in_name_order(self):
        e = self.vsce("CHANGELOG.md\n*.md\nSESSION_RUNNER.md\n", {**self.VSCE_MAP, ".gitattributes": "methodology/.gitattributes"})
        self.assertEqual([(x["line"], x["files"]) for x in e["lines"]],
                         [(1, ["CHANGELOG.md"]), (2, ["CHANGELOG.md", "SESSION_RUNNER.md"]), (3, ["SESSION_RUNNER.md"]),
                          (0, [".gitattributes"])])

    def test_a_file_that_a_line_and_the_directory_it_stands_for_both_cover_is_listed_once(self):
        """`a/**/b` and the `a/**/b/**` vsce adds both match `a/b/b`: the line names the file once."""
        e = self.vsce("a/**/b\n", {"a/b/b": "z/b"})
        self.assertEqual((e["exposed"], [(x["line"], x["files"]) for x in e["lines"]]), (["a/b/b"], [(1, ["a/b/b"])]))

    def test_every_entry_of_vsces_own_lists_is_one_the_tool_reads(self):
        for name in self.m.VSCE_DEFAULT_IGNORE + self.m.VSCE_NOT_IGNORED:
            self.assertIsNotNone(self.m.vsce_glob(name), name)
        self.assertEqual((len(self.m.VSCE_DEFAULT_IGNORE), self.m.VSCE_NOT_IGNORED), (32, ("package.json", "README.md")))

    def test_vsce_nothing_moves_so_nothing_is_exposed(self):
        self.assertEqual(self.m.vscodeignore_exposure("SESSION_RUNNER.md\n", {})["exposed"], [])

    def test_only_the_files_the_trimmer_writes_are_shards(self):
        yes = ("CHANGELOG-through-2026-08-01.md", "HANDOFFS-through-2026-08-02-3.md.verify.sh", "SESSION_NOTES-through-x.md")
        no = ("CHANGELOG-archive.md", "CHANGELOG-through-x.md.bak", "ROADMAP-through-x.md", "a/CHANGELOG-through-x.md", "CHANGELOG-through-.txt")
        for name in yes:
            self.assertTrue(self.m.SHARD_RE.match(name), name)
        for name in no:
            self.assertFalse(self.m.SHARD_RE.match(name), name)

    # --- the gitattributes rule ---
    def test_a_gitattributes_that_holds_only_the_seeds_rules_is_the_seeds(self):
        seed = "# comment\nCHANGELOG.md merge=union\n*.jsonl merge=union\n"
        self.assertTrue(self.m.seed_rules_only("CHANGELOG.md merge=union\n\n# another comment\n", seed))
        self.assertTrue(self.m.seed_rules_only(seed, seed))
        self.assertTrue(self.m.seed_rules_only("", seed))
        self.assertFalse(self.m.seed_rules_only(seed + "*.png binary\n", seed))

    # --- ignore mode ---
    def test_ignore_mode_is_a_gitignore_that_lists_a_tracked_destination_in_either_layout(self):
        with tempfile.TemporaryDirectory() as d:
            gi = Path(d) / ".gitignore"
            self.assertFalse(self.m.is_ignore_mode(d))
            for text, want in (("/SESSION_RUNNER.md\n", True), ("/methodology/SESSION_RUNNER.md\n", True),
                               ("/docs/methodology/ITERATIVE_METHODOLOGY.md\n", True), ("SESSION_RUNNER.md\n", False),
                               ("/CHANGELOG.md\n", False), ("/dashboard.html\n", False), ("# /SESSION_RUNNER.md\n", False)):
                gi.write_text(text, encoding="utf-8")
                self.assertEqual(self.m.is_ignore_mode(d), want, text)

    # --- what the plan moves ---
    def plan(self, files, tier="all", kind="legacy"):
        with tempfile.TemporaryDirectory() as d:
            for rel in files:
                path = Path(d) / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("x\n", encoding="utf-8")
            return self.m.plan_moves(d, tier, set(files), kind)

    def test_a_session_notes_shard_moves_and_a_nested_or_lookalike_file_does_not(self):
        files = ["docs/archive/SESSION_NOTES-through-2026-08-01.md", "docs/archive/SESSION_NOTES-through-2026-08-01.md.verify.sh",
                 "docs/archive/sub/CHANGELOG-through-2026-08-01.md", "docs/archive/CHANGELOG-archive.md"]
        moves, left, collisions = self.plan(files)
        self.assertEqual({m["src"]: m["dest"] for m in moves},
                         {"docs/archive/SESSION_NOTES-through-2026-08-01.md": "methodology/archive/SESSION_NOTES-through-2026-08-01.md",
                          "docs/archive/SESSION_NOTES-through-2026-08-01.md.verify.sh": "methodology/archive/SESSION_NOTES-through-2026-08-01.md.verify.sh"})
        self.assertEqual({x["path"] for x in left}, {"docs/archive/sub/CHANGELOG-through-2026-08-01.md", "docs/archive/CHANGELOG-archive.md"})
        self.assertEqual(collisions, [])

    def test_a_generated_file_and_a_shard_that_already_exist_at_their_destination_are_collisions(self):
        files = ["dashboard.html", "methodology/dashboard.html", "docs/archive/CHANGELOG-through-2026-08-01.md",
                 "methodology/archive/CHANGELOG-through-2026-08-01.md", "SESSION_NOTES.md", "methodology/SESSION_NOTES.md"]
        moves, left, collisions = self.plan(files)
        self.assertEqual(collisions, ["methodology/SESSION_NOTES.md", "methodology/archive/CHANGELOG-through-2026-08-01.md",
                                      "methodology/dashboard.html"])
        self.assertEqual(moves, [])

    def test_tier_1_plans_only_the_tracked_rows_and_tier_2_only_the_rest(self):
        files = ["SESSION_RUNNER.md", "CHANGELOG.md", "dashboard.html", "docs/archive/CHANGELOG-through-2026-08-01.md"]
        self.assertEqual([m["src"] for m in self.plan(files, "1")[0]], ["SESSION_RUNNER.md"])
        self.assertEqual(sorted(m["src"] for m in self.plan(files, "2")[0]),
                         sorted(["CHANGELOG.md", "dashboard.html", "docs/archive/CHANGELOG-through-2026-08-01.md"]))

    # --- directories a move empties ---
    def test_only_the_directories_a_move_emptied_are_removed_and_never_the_root(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a" / "b").mkdir(parents=True)
            (root / "a" / "keep.txt").write_text("x", encoding="utf-8")
            (root / "c" / "d" / "e").mkdir(parents=True)
            self.m.remove_empty_parents(root, "a/b/gone.md")
            self.assertFalse((root / "a" / "b").exists())
            self.assertTrue((root / "a").is_dir(), "a directory that still holds a file was removed")
            self.m.remove_empty_parents(root, "c/d/e/gone.md")
            self.assertFalse((root / "c").exists())
            self.assertTrue(root.is_dir())

    # --- what git calls dirty ---
    def test_the_cleanup_never_removes_the_project_root_even_when_it_empties_it(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "project"
            (root / "c" / "d").mkdir(parents=True)
            self.m.remove_empty_parents(root, "c/d/gone.md")
            self.assertFalse((root / "c").exists())
            self.assertTrue(root.is_dir(), "the project root was removed")

    def test_a_staged_rename_is_one_dirty_path_and_not_two(self):
        with tempfile.TemporaryDirectory() as d:
            git(d, "init", "-q")
            (Path(d) / "a.txt").write_text("hello world\n" * 20, encoding="utf-8")
            commit_all(d, "a")
            git(d, "mv", "a.txt", "b.txt")
            (Path(d) / "new.txt").write_text("n\n", encoding="utf-8")
            self.assertEqual(sorted(self.m.dirty_paths(d)), ["b.txt", "new.txt"])


class Adopter(unittest.TestCase):
    """A scratch copy of the base project for each test."""

    def setUp(self):
        self._td = tempfile.TemporaryDirectory(prefix="migrate-layout-")
        self.addCleanup(self._td.cleanup)
        self.project = Path(self._td.name) / "adopter"
        shutil.copytree(base_project(), self.project, symlinks=True)

    def commit(self, message="a change"):
        commit_all(self.project, message)

    def moves(self, report):
        return {m["src"]: m["dest"] for m in report["moves"]}


class TestUsageAndNothingToDo(unittest.TestCase):
    """The shapes of project the tool is not for, and what it says about each."""

    def setUp(self):
        self._td = tempfile.TemporaryDirectory(prefix="migrate-usage-")
        self.addCleanup(self._td.cleanup)
        self.root = Path(self._td.name)

    def test_a_missing_directory_is_a_usage_error(self):
        r = run_migrate(self.root / "nope")
        self.assertEqual(r.returncode, 2, r.out)
        self.assertIn("not a directory", r.out)

    def test_a_directory_that_is_not_a_git_repository_is_refused(self):
        (self.root / "plain").mkdir()
        r = run_migrate(self.root / "plain")
        self.assertEqual(r.returncode, 1, r.out)
        self.assertEqual(r.report["status"], "refused")
        self.assertEqual([x["code"] for x in r.report["refusals"]], ["not-a-repository"])

    def test_a_subdirectory_of_a_repository_is_not_the_top_of_one(self):
        outer = self.root / "outer"
        (outer / "inner").mkdir(parents=True)
        git(outer, "init", "-q")
        (outer / "inner" / "SESSION_RUNNER.md").write_text("# runner\n", encoding="utf-8")
        commit_all(outer, "a repository with a project inside it")
        r = run_migrate(outer / "inner")
        self.assertEqual(r.returncode, 1, r.out)
        self.assertEqual([x["code"] for x in r.report["refusals"]], ["not-a-repository"])

    def test_a_repository_with_no_methodology_files_has_nothing_to_migrate(self):
        project = self.root / "bare"
        project.mkdir()
        git(project, "init", "-q")
        (project / "README.md").write_text("# bare\n", encoding="utf-8")
        commit_all(project, "a project that has not adopted the methodology")
        before = tree_state(project)
        r = run_migrate(project, "--apply")
        self.assertEqual(r.returncode, 0, r.out)
        self.assertEqual(r.report["status"], "nothing-to-do")
        self.assertEqual(r.report["moves"], [])
        self.assertEqual(tree_state(project), before, "a project with nothing to migrate was changed")

    def test_a_repository_with_no_commits_is_refused(self):
        project = self.root / "fresh"
        project.mkdir()
        git(project, "init", "-q")
        (project / "SESSION_RUNNER.md").write_text("# runner\n", encoding="utf-8")
        r = run_migrate(project)
        self.assertEqual(r.returncode, 1, r.out)
        self.assertIn("no-commits", [x["code"] for x in r.report["refusals"]])


class TestTheDryRun(Adopter):
    """Dry run is the default: it reads, prints the plan as data and writes nothing."""

    def test_it_writes_nothing(self):
        before = tree_state(self.project)
        r = run_migrate(self.project)
        self.assertEqual(r.returncode, 0, r.out)
        self.assertEqual(r.report["mode"], "dry-run")
        self.assertEqual(tree_state(self.project), before, "a dry run changed the project")

    def test_it_plans_one_move_for_every_manifest_file_the_project_holds(self):
        r = run_migrate(self.project)
        got = self.moves(r.report)
        for dest in (d for _s, d, _x in LEGACY):
            self.assertEqual(got.get(dest), NEW_OF[dest], "no move planned for %s" % dest)

    def test_it_plans_the_two_tracked_history_files_the_generated_ignored_ones_and_the_ledger_shards(self):
        r = run_migrate(self.project)
        got = self.moves(r.report)
        self.assertEqual(got["dashboard_history.jsonl"], "methodology/dashboard_history.jsonl")
        self.assertEqual(got[".context-budget-history.jsonl"], "methodology/.context-budget-history.jsonl")
        self.assertEqual(got["dashboard.html"], "methodology/dashboard.html")
        self.assertEqual(got[".quality-gates-results.json"], "methodology/.quality-gates-results.json")
        for shard in ("CHANGELOG-through-2026-08-01.md", "CHANGELOG-through-2026-08-01.md.verify.sh",
                      "HANDOFFS-through-2026-08-02.md", "HANDOFFS-through-2026-08-02.md.verify.sh"):
            self.assertEqual(got["docs/archive/" + shard], "methodology/archive/" + shard)

    def test_it_moves_nothing_else_and_names_what_it_leaves(self):
        r = run_migrate(self.project)
        got = self.moves(r.report)
        self.assertNotIn("docs/methodology/PROJECT_CONVENTIONS.md", got)
        self.assertNotIn("docs/archive/project-notes.md", got)
        self.assertNotIn("CLAUDE.md", got)
        self.assertNotIn(".gitignore", got)
        left = {x["path"]: x["reason"] for x in r.report["left_in_place"]}
        self.assertIn("docs/methodology/PROJECT_CONVENTIONS.md", left)
        self.assertIn("docs/archive/project-notes.md", left)

    def test_each_move_says_whether_git_tracks_the_file(self):
        r = run_migrate(self.project)
        tracked = {m["src"]: m["tracked"] for m in r.report["moves"]}
        self.assertTrue(tracked["SESSION_RUNNER.md"])
        self.assertTrue(tracked["dashboard_history.jsonl"])
        self.assertTrue(tracked[".context-budget-history.jsonl"])
        self.assertFalse(tracked["dashboard.html"])
        self.assertFalse(tracked[".quality-gates-results.json"])

    def test_the_text_a_person_reads_names_the_mode_and_prints_every_git_mv(self):
        r = run_migrate(self.project, json_out=False)
        self.assertEqual(r.returncode, 0, r.out)
        self.assertRegex(r.out, r"(?i)dry run")
        self.assertIn("--apply", r.out)
        self.assertIn("git mv SESSION_RUNNER.md methodology/SESSION_RUNNER.md", r.out)
        self.assertIn("git mv docs/methodology/ITERATIVE_METHODOLOGY.md methodology/ITERATIVE_METHODOLOGY.md", r.out)

    def test_the_report_names_the_layout_and_the_tier(self):
        r = run_migrate(self.project)
        self.assertEqual(r.report["layout"], "legacy")
        self.assertEqual(r.report["tier"], "all")


class TestRefusals(Adopter):
    """A dirty tree, a half-migrated tree, a destination that exists and a tree where bin/status does
    not read every TRACKED file current are each refused, under a dry run and under --apply, and nothing is written."""

    def refused(self, code, *args):
        before = tree_state(self.project)
        for mode in ((), ("--apply",)):
            r = run_migrate(self.project, *args, *mode)
            self.assertEqual(r.returncode, 1, r.out)
            self.assertEqual(r.report["status"], "refused", r.out)
            self.assertIn(code, [x["code"] for x in r.report["refusals"]], r.out)
            self.assertEqual(tree_state(self.project), before, "a refused run changed the project")
        return r.report

    def test_a_modified_tracked_file_is_a_dirty_tree(self):
        (self.project / "README.md").write_text("changed\n", encoding="utf-8")
        self.commit("a readme")
        (self.project / "README.md").write_text("changed again\n", encoding="utf-8")
        self.refused("dirty-tree")

    def test_an_untracked_file_is_a_dirty_tree(self):
        (self.project / "scratch.txt").write_text("x\n", encoding="utf-8")
        report = self.refused("dirty-tree")
        dirty = next(x for x in report["refusals"] if x["code"] == "dirty-tree")
        self.assertIn("scratch.txt", " ".join(dirty["paths"]))

    def test_a_runner_at_the_root_and_under_methodology_is_half_migrated(self):
        (self.project / "methodology").mkdir()
        (self.project / "methodology" / "SESSION_RUNNER.md").write_text("# a second runner\n", encoding="utf-8")
        self.commit("a second runner")
        report = self.refused("half-migrated")
        self.assertEqual(report["layout"], "half-migrated")
        self.assertEqual([x["code"] for x in report["refusals"]], ["half-migrated"],
                         "the runner's collision is the half-migrated refusal and is not listed a second time")
        half = next(x for x in report["refusals"] if x["code"] == "half-migrated")
        self.assertIn("SESSION_RUNNER.md", half["message"])
        self.assertIn("methodology/SESSION_RUNNER.md", half["message"])

    def test_a_destination_that_exists_is_refused_and_named(self):
        (self.project / "methodology").mkdir()
        (self.project / "methodology" / "SAFEGUARDS.md").write_text("# someone else's\n", encoding="utf-8")
        self.commit("a file where a move would land")
        report = self.refused("destination-exists")
        found = next(x for x in report["refusals"] if x["code"] == "destination-exists")
        self.assertEqual(found["paths"], ["methodology/SAFEGUARDS.md"])

    def test_a_locally_modified_tracked_file_is_not_current(self):
        (self.project / "SAFEGUARDS.md").write_text("# edited here\n", encoding="utf-8")
        self.commit("edit a synced file")
        report = self.refused("not-current")
        found = next(x for x in report["refusals"] if x["code"] == "not-current")
        self.assertIn("SAFEGUARDS.md", " ".join(found["paths"]))
        self.assertIn("bin/sync", found["message"])

    def test_a_missing_tracked_file_is_not_current(self):
        git(self.project, "rm", "-q", "RECOMMENDED_SKILLS.md")
        self.commit("remove a synced file")
        report = self.refused("not-current")
        found = next(x for x in report["refusals"] if x["code"] == "not-current")
        self.assertIn("RECOMMENDED_SKILLS.md", " ".join(found["paths"]))

    def test_a_project_in_ignore_mode_is_refused_as_unsupported(self):
        gi = self.project / ".gitignore"
        gi.write_text(gi.read_text(encoding="utf-8") + "/SESSION_RUNNER.md\n", encoding="utf-8")
        self.commit("ignore mode")
        self.refused("ignore-mode")

    def test_a_stale_format_seed_is_advice_and_not_a_refusal(self):
        """bin/status reports a seed that predates the current format as advisory only; the tool must not
        read that as drift."""
        (self.project / "HANDOFFS.md").write_text("# Handoffs\n\nAn old shape, no format marker.\n", encoding="utf-8")
        self.commit("an old-format seed")
        r = run_migrate(self.project)
        self.assertEqual(r.returncode, 0, r.out)
        self.assertEqual(r.report["status"], "ok")

    def test_a_clean_current_project_has_no_refusal(self):
        r = run_migrate(self.project)
        self.assertEqual(r.report["refusals"], [])
        self.assertEqual(r.report["status"], "ok")

    def test_every_refusal_is_reported_together_not_one_at_a_time(self):
        (self.project / "scratch.txt").write_text("x\n", encoding="utf-8")
        (self.project / "methodology").mkdir()
        (self.project / "methodology" / "SAFEGUARDS.md").write_text("# someone else's\n", encoding="utf-8")
        r = run_migrate(self.project)
        codes = [x["code"] for x in r.report["refusals"]]
        self.assertIn("dirty-tree", codes)
        self.assertIn("destination-exists", codes)


def name_status(project, rev="HEAD"):
    """{(src, dest): score} for the renames of one commit as git reports them (-M, so 50% and up are found)."""
    out = git(project, "diff", "-M", "--name-status", "-z", rev + "~1", rev).split("\0")
    renames, i = {}, 0
    while i < len(out):
        status = out[i]
        if status.startswith("R"):
            renames[(out[i + 1], out[i + 2])] = int(status[1:])
            i += 3
        else:
            i += 2 if status else 1
    return renames


def configs_rewritten_by_layer_3(path):
    """The files whose bytes a migration changes on purpose: the two configs, and the ledger that takes its entry."""
    return Path(path).name in (".context-budget.json", ".quality-gates.json", "CHANGELOG.md")


class TestApply(Adopter):
    """--apply writes the migration as ONE commit: every tracked move a rename git can follow."""

    def apply(self, *args):
        before = git(self.project, "rev-parse", "HEAD").strip()
        r = run_migrate(self.project, "--apply", *args)
        return before, r

    def test_it_makes_exactly_one_commit_on_top_of_head_and_leaves_the_tree_clean(self):
        before, r = self.apply()
        self.assertEqual(r.returncode, 0, r.out)
        self.assertEqual(r.report["status"], "applied")
        self.assertEqual(git(self.project, "rev-list", "--count", before + "..HEAD").strip(), "1")
        self.assertEqual(git(self.project, "rev-parse", "HEAD~1").strip(), before)
        self.assertEqual(git(self.project, "status", "--porcelain"), "")
        self.assertEqual(r.report["commit"]["sha"], git(self.project, "rev-parse", "HEAD").strip())

    def test_every_planned_move_happened_and_a_file_that_is_not_rewritten_keeps_its_bytes(self):
        before = {rel: (self.project / rel).read_bytes() for rel in files_of(self.project)}
        plan = run_migrate(self.project).report
        moves = {m["src"]: m["dest"] for m in plan["moves"]}
        self.assertGreaterEqual(len(moves), 30)
        _, r = self.apply()
        self.assertEqual(r.returncode, 0, r.out)
        for src, dest in moves.items():
            self.assertFalse((self.project / src).exists(), "%s was left behind" % src)
            self.assertTrue((self.project / dest).is_file(), "%s did not arrive" % dest)
            if not configs_rewritten_by_layer_3(src):
                self.assertEqual((self.project / dest).read_bytes(), before[src], "%s changed in the move" % dest)

    def test_git_sees_each_tracked_move_as_a_rename_at_90_percent_or_better(self):
        plan = run_migrate(self.project).report
        tracked = {m["src"]: m["dest"] for m in plan["moves"] if m["tracked"]}
        _, r = self.apply()
        seen = name_status(self.project)
        for src, dest in tracked.items():
            self.assertIn((src, dest), seen, "git does not see %s -> %s as a rename" % (src, dest))
            self.assertGreaterEqual(seen[(src, dest)], 90, "%s -> %s fell below 90%%" % (src, dest))
        reported = {(x["src"], x["dest"]): x["score"] for x in r.report["commit"]["renames"]}
        self.assertEqual(reported, {(s, d): seen[(s, d)] for s, d in tracked.items()}, "the report and git disagree")

    def test_an_ignored_generated_file_is_moved_without_git_and_stays_ignored(self):
        _, r = self.apply()
        self.assertEqual(r.returncode, 0, r.out)
        for name in ("dashboard.html", ".quality-gates-results.json"):
            self.assertFalse((self.project / name).exists())
            self.assertTrue((self.project / "methodology" / name).is_file())
            self.assertNotIn("methodology/" + name, git(self.project, "ls-files").splitlines())
            ignored = subprocess.run(["git", "-C", str(self.project), "check-ignore", "-q", "methodology/" + name])
            self.assertEqual(ignored.returncode, 0, "methodology/%s is not ignored after the move" % name)

    def test_an_anchored_gitignore_entry_follows_its_file_and_an_unanchored_one_is_left(self):
        _, r = self.apply()
        text = (self.project / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("/methodology/dashboard.html\n", text)
        self.assertNotIn("\n/dashboard.html\n", text)
        self.assertIn("\n.quality-gates-results.json\n", text, "an unanchored entry still matches and must not change")
        self.assertIn("# generated by the methodology tools", text, "a comment was disturbed")
        rewrite = next(x for x in r.report["rewrites"] if x["path"] == ".gitignore")
        self.assertEqual(rewrite["replacements"], 1)

    def test_what_the_tool_leaves_stays_and_only_the_directories_it_emptied_go(self):
        _, r = self.apply()
        self.assertTrue((self.project / "docs" / "methodology" / "PROJECT_CONVENTIONS.md").is_file())
        self.assertTrue((self.project / "docs" / "archive" / "project-notes.md").is_file())
        self.assertFalse((self.project / "docs" / "methodology" / "workstreams").exists(), "an emptied directory was left")

    def test_a_directory_the_moves_emptied_entirely_is_removed(self):
        git(self.project, "rm", "-q", "-r", "docs/methodology/PROJECT_CONVENTIONS.md", "docs/archive/project-notes.md")
        self.commit("remove the project's own files")
        _, r = self.apply()
        self.assertEqual(r.returncode, 0, r.out)
        self.assertFalse((self.project / "docs" / "methodology").exists())
        self.assertFalse((self.project / "docs" / "archive").exists())

    def test_the_commit_message_names_the_tool_the_tier_and_carries_every_trailer(self):
        _, r = self.apply("--trailer", "Co-Authored-By: A Tester <a@example.com>", "--trailer", "Reviewed-by: B <b@example.com>")
        message = git(self.project, "log", "-1", "--format=%B")
        subject = message.splitlines()[0]
        self.assertIn("methodology/", subject)
        self.assertIn("bin/migrate-layout", message)
        self.assertIn("tier all", message)
        self.assertIn("a rename at 90% similarity or better", message)
        moves = r.report["moves"]
        plain = sum(1 for m in moves if not m["tracked"])
        self.assertEqual(plain, 2)
        self.assertIn("%d file(s) with git mv, %d without git" % (len(moves) - plain, plain), message)
        self.assertIn(r.report["canonical"]["sha"], message)
        self.assertTrue(message.rstrip().endswith("Reviewed-by: B <b@example.com>"), message)
        self.assertIn("Co-Authored-By: A Tester <a@example.com>", message)
        parsed = git(self.project, "log", "-1", "--format=%(trailers:only,unfold)")
        self.assertIn("Co-Authored-By: A Tester <a@example.com>", parsed, "git does not read the trailers as trailers")
        self.assertIn("Reviewed-by: B <b@example.com>", parsed)

    def test_bin_status_then_reads_every_tracked_file_current_at_its_new_place(self):
        _, r = self.apply()
        status = subprocess.run([sys.executable, "-B", str(STATUS), str(self.project)], capture_output=True, text=True)
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertRegex(status.stdout, r"layout: adopter\s+new")
        rows = [line for line in status.stdout.splitlines() if " tracked " in line]
        self.assertEqual(len(rows), len(TRACKED_DESTS))
        for line in rows:
            self.assertTrue(line.rstrip().endswith("current"), line)
            self.assertIn(" methodology/", " " + line)

    def test_a_second_run_finds_nothing_to_do_and_adds_no_commit(self):
        self.apply()
        head = git(self.project, "rev-parse", "HEAD").strip()
        r = run_migrate(self.project, "--apply")
        self.assertEqual(r.returncode, 0, r.out)
        self.assertEqual(r.report["status"], "nothing-to-do")
        self.assertEqual(git(self.project, "rev-parse", "HEAD").strip(), head)


class TestTheTiers(Adopter):
    """Tier 1 is the framework's files, tier 2 the project's state; tier 1 alone is a stopping point."""

    def test_tier_1_moves_the_tracked_files_and_nothing_of_the_projects_state(self):
        r = run_migrate(self.project, "--apply", "--tier", "1")
        self.assertEqual(r.returncode, 0, r.out)
        for dest in TRACKED_DESTS:
            self.assertTrue((self.project / NEW_OF[dest]).is_file(), dest)
            self.assertFalse((self.project / dest).exists(), dest)
        for dest in SEED_DESTS:
            self.assertTrue((self.project / dest).is_file(), "%s moved in tier 1" % dest)
            self.assertFalse((self.project / NEW_OF[dest]).exists(), dest)
        for name in ("dashboard.html", "dashboard_history.jsonl"):
            self.assertTrue((self.project / name).is_file(), "%s moved in tier 1" % name)
        self.assertTrue((self.project / "docs" / "archive" / "CHANGELOG-through-2026-08-01.md").is_file())
        self.assertEqual(git(self.project, "status", "--porcelain"), "")

    def test_tier_1_names_what_it_leaves_of_the_framework_directory_and_not_the_archive_it_does_not_touch(self):
        r = run_migrate(self.project, "--tier", "1")
        left = [x["path"] for x in r.report["left_in_place"]]
        self.assertIn("docs/methodology/PROJECT_CONVENTIONS.md", left)
        self.assertNotIn("docs/archive/project-notes.md", left, "the archive is tier 2's: a tier-1 run has no opinion about it")
        both = [x["path"] for x in run_migrate(self.project).report["left_in_place"]]
        self.assertIn("docs/archive/project-notes.md", both)

    def test_tier_2_alone_is_refused_before_tier_1(self):
        before = tree_state(self.project)
        r = run_migrate(self.project, "--apply", "--tier", "2")
        self.assertEqual(r.returncode, 1, r.out)
        self.assertEqual([x["code"] for x in r.report["refusals"]], ["tier-order"])
        self.assertEqual(tree_state(self.project), before)

    def test_tier_1_then_tier_2_reaches_the_same_tree_as_all_at_once(self):
        a = self.project
        b = Path(self._td.name) / "second"
        shutil.copytree(a, b, symlinks=True)
        self.assertEqual(run_migrate(a, "--apply", "--tier", "1").returncode, 0)
        r = run_migrate(a, "--apply", "--tier", "2")
        self.assertEqual(r.returncode, 0, r.out)
        self.assertEqual(run_migrate(b, "--apply").returncode, 0)
        self.assertEqual(files_of(a), files_of(b))
        self.assertEqual((a / "methodology" / "CHANGELOG.md").read_text(encoding="utf-8").count("Layout migration"), 2,
                         "each run of the tool owes the ledger one entry")
        self.assertEqual((b / "methodology" / "CHANGELOG.md").read_text(encoding="utf-8").count("Layout migration"), 1)
        for rel in sorted(files_of(a)):
            if not configs_rewritten_by_layer_3(Path(rel).name):
                self.assertEqual((a / rel).read_bytes(), (b / rel).read_bytes(), rel)

    def test_all_after_tier_1_moves_only_what_tier_1_left(self):
        run_migrate(self.project, "--apply", "--tier", "1")
        plan = run_migrate(self.project)
        self.assertEqual(plan.returncode, 0, plan.out)
        srcs = {m["src"] for m in plan.report["moves"]}
        self.assertTrue(srcs.isdisjoint(TRACKED_DESTS))
        self.assertTrue(set(SEED_DESTS) <= srcs)

    def test_a_second_tier_1_run_finds_nothing_to_do(self):
        run_migrate(self.project, "--apply", "--tier", "1")
        r = run_migrate(self.project, "--apply", "--tier", "1")
        self.assertEqual(r.report["status"], "nothing-to-do")


class TestTheGitattributesSeed(Adopter):
    """The seed moves; a .gitattributes that holds rules of the project's own stays where it is."""

    def test_the_seed_moves_with_the_rest(self):
        r = run_migrate(self.project, "--apply")
        self.assertTrue((self.project / "methodology" / ".gitattributes").is_file())
        self.assertFalse((self.project / ".gitattributes").exists())

    def test_a_file_with_a_rule_of_the_projects_own_stays_and_is_named(self):
        ga = self.project / ".gitattributes"
        ga.write_text(ga.read_text(encoding="utf-8") + "inst/extdata/example.txt text eol=lf\n", encoding="utf-8")
        self.commit("a rule of the project's own")
        r = run_migrate(self.project, "--apply")
        self.assertEqual(r.returncode, 0, r.out)
        self.assertTrue(ga.is_file(), "the project's own .gitattributes was moved")
        self.assertIn("inst/extdata/example.txt", ga.read_text(encoding="utf-8"))
        self.assertFalse((self.project / "methodology" / ".gitattributes").exists())
        self.assertIn(".gitattributes", [x["path"] for x in r.report["left_in_place"]])


class TestARefusedCommitRollsBack(Adopter):
    """A hook that refuses the migration commit must leave the project exactly as it was, files that git does not
    track included: the tool started from a clean tree and gives one back."""

    def test_a_refusing_hook_restores_the_tree_and_exits_3(self):
        hook = self.project / ".git" / "hooks" / "pre-commit"
        hook.write_text("#!/bin/sh\necho 'refused by the test hook' >&2\nexit 1\n", encoding="utf-8")
        hook.chmod(0o755)
        before = tree_state(self.project)
        r = run_migrate(self.project, "--apply")
        self.assertEqual(r.returncode, 3, r.out)
        self.assertEqual(r.report["status"], "rolled-back")
        self.assertIn("refused by the test hook", r.report["commit"]["error"])
        self.assertEqual(tree_state(self.project), before, "the rollback did not restore the project")
        self.assertFalse((self.project / "methodology").exists(), "an empty methodology/ was left behind")

    def test_the_hook_ran_because_the_tool_does_not_bypass_it(self):
        marker = self.project / "hook-ran"
        hook = self.project / ".git" / "hooks" / "pre-commit"
        hook.write_text("#!/bin/sh\ntouch '%s'\nexit 0\n" % marker, encoding="utf-8")
        hook.chmod(0o755)
        r = run_migrate(self.project, "--apply")
        self.assertEqual(r.returncode, 0, r.out)
        self.assertTrue(marker.exists(), "the pre-commit hook did not run: the tool bypassed it")


EXPECTED_CLAUDE_MD = """# Project

<!-- SESSION PROTOCOL -->
Read and follow `methodology/SESSION_RUNNER.md` step by step. Orient first: read methodology/SAFEGUARDS.md, then methodology/SESSION_NOTES.md,
then run `methodology/methodology_dashboard.py`.

This project follows `methodology/workstreams/DEVELOPMENT_WORKSTREAM.md` in standard mode, and the
theory is in [the manual](methodology/ITERATIVE_METHODOLOGY.md).

Kept qualified on purpose (a path with a directory in front is not a bare name):
the canonical copy is `../methodology/starter-kit/SESSION_RUNNER.md`, and upstream is
https://github.com/KJ5HST/methodology/blob/main/SESSION_RUNNER.md and `starter-kit/SAFEGUARDS.md`.

Not a methodology file: SESSION_RUNNER.mdx, MY_CHANGELOG.md, NOTES-CHANGELOG.md.
"""


class TestTheRewriteOfClaudeMd(Adopter):
    """CLAUDE.md is loaded from the project root, so a name in it is relative to the root: the paths of the files
    that moved are rewritten and a name with a directory in front of it, or inside a longer name,
    is not a methodology file of the project's and is left."""

    def test_a_moved_path_or_bare_name_is_rewritten_and_nothing_else_changes(self):
        r = run_migrate(self.project, "--apply")
        self.assertEqual(r.returncode, 0, r.out)
        self.assertEqual((self.project / "CLAUDE.md").read_text(encoding="utf-8"), EXPECTED_CLAUDE_MD)

    def test_the_report_counts_the_replacements_and_shows_the_diff(self):
        r = run_migrate(self.project)
        rw = next(x for x in r.report["rewrites"] if x["path"] == "CLAUDE.md")
        self.assertEqual(rw["replacements"], 6)
        self.assertEqual(rw["final"], "CLAUDE.md")
        self.assertIn("-Read and follow `SESSION_RUNNER.md` step by step.", rw["diff"])
        self.assertIn("+Read and follow `methodology/SESSION_RUNNER.md` step by step.", rw["diff"])

    def test_a_dry_run_does_not_write_it(self):
        before = (self.project / "CLAUDE.md").read_text(encoding="utf-8")
        run_migrate(self.project)
        self.assertEqual((self.project / "CLAUDE.md").read_text(encoding="utf-8"), before)

    def test_tier_1_rewrites_only_the_names_of_the_files_it_moved(self):
        r = run_migrate(self.project, "--apply", "--tier", "1")
        text = (self.project / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("`methodology/SESSION_RUNNER.md`", text)
        self.assertIn("methodology/SAFEGUARDS.md", text)
        self.assertIn(", then SESSION_NOTES.md,", text, "a tier-2 file is still at the root and must keep its bare name")

    def test_a_project_without_a_claude_md_is_migrated_all_the_same(self):
        git(self.project, "rm", "-q", "CLAUDE.md")
        self.commit("no CLAUDE.md")
        r = run_migrate(self.project, "--apply")
        self.assertEqual(r.returncode, 0, r.out)
        self.assertNotIn("CLAUDE.md", [x["path"] for x in r.report["rewrites"]])


class TestTheRewriteOfTheConfigs(Adopter):
    """The two JSON configs move with the project's state and name paths in their values: the path a file
    is read at, the results file, a gate's command. They are rewritten as text, so the rest of the file is the bytes
    it was; a prose key (one that starts with an underscore) and the `canonical` path (the sibling checkout, which
    does not move) are left."""

    def budget(self):
        return (self.project / ".context-budget.json").read_text(encoding="utf-8")

    def test_the_budget_paths_follow_and_the_canonical_path_and_the_prose_do_not(self):
        before = self.budget()
        for old in ('"path": "SESSION_NOTES.md"', '"path": "SESSION_RUNNER.md"', '"path": "SAFEGUARDS.md"',
                    '"canonical": "../methodology/starter-kit/SESSION_RUNNER.md"'):
            self.assertEqual(before.count(old), 1, "the seed no longer has %s once" % old)
        r = run_migrate(self.project, "--apply")
        self.assertEqual(r.returncode, 0, r.out)
        want = (before.replace('"path": "SESSION_NOTES.md"', '"path": "methodology/SESSION_NOTES.md"')
                .replace('"path": "SESSION_RUNNER.md"', '"path": "methodology/SESSION_RUNNER.md"')
                .replace('"path": "SAFEGUARDS.md"', '"path": "methodology/SAFEGUARDS.md"'))
        self.assertEqual((self.project / "methodology" / ".context-budget.json").read_text(encoding="utf-8"), want)

    def test_the_gates_results_file_and_command_follow_and_the_prose_does_not(self):
        before = (self.project / ".quality-gates.json").read_text(encoding="utf-8")
        r = run_migrate(self.project, "--apply")
        want = (before.replace('"results_file": ".quality-gates-results.json"',
                               '"results_file": "methodology/.quality-gates-results.json"')
                .replace("-- CHANGELOG.md)..HEAD", "-- methodology/CHANGELOG.md)..HEAD"))
        self.assertNotEqual(want, before)
        got = (self.project / "methodology" / ".quality-gates.json").read_text(encoding="utf-8")
        self.assertEqual(got, want)
        self.assertIn("Commits after the newest commit that touched CHANGELOG.md", got, "a prose value was rewritten")
        json.loads(got)

    def test_the_rewritten_gate_command_still_counts_from_the_ledgers_newest_commit(self):
        """Right after the move both the old and the new command read 0 (the move commit is the newest commit that
        touched either path), so the discriminating case is later: a commit that touches the moved ledger, then one
        that does not. Counted from the ledger's real place that is 1; counted from the old path it is 2."""
        run_migrate(self.project, "--apply")
        ledger = self.project / "methodology" / "CHANGELOG.md"
        ledger.write_text(ledger.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        self.commit("a commit that touches the ledger")
        (self.project / "README.md").write_text("a later commit\n", encoding="utf-8")
        self.commit("a commit that does not")
        gates = json.loads((self.project / "methodology" / ".quality-gates.json").read_text(encoding="utf-8"))
        out = subprocess.run(gates["gates"][0]["command"], shell=True, cwd=self.project, capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "1", "the command did not count from the ledger's newest commit")

    def test_the_report_names_each_config_by_its_old_and_its_new_place(self):
        r = run_migrate(self.project)
        got = {x["path"]: x["final"] for x in r.report["rewrites"]}
        self.assertEqual(got[".context-budget.json"], "methodology/.context-budget.json")
        self.assertEqual(got[".quality-gates.json"], "methodology/.quality-gates.json")

    def test_a_fresh_clone_with_no_generated_files_still_gets_the_results_file_and_the_ignore_entry_moved(self):
        (self.project / "dashboard.html").unlink()
        (self.project / ".quality-gates-results.json").unlink()
        r = run_migrate(self.project, "--apply")
        self.assertEqual(r.returncode, 0, r.out)
        gates = json.loads((self.project / "methodology" / ".quality-gates.json").read_text(encoding="utf-8"))
        self.assertEqual(gates["results_file"], "methodology/.quality-gates-results.json")
        self.assertIn("/methodology/dashboard.html\n", (self.project / ".gitignore").read_text(encoding="utf-8"))

    def test_tier_1_leaves_the_configs_at_the_root_and_rewrites_only_the_paths_of_files_it_moved(self):
        r = run_migrate(self.project, "--apply", "--tier", "1")
        self.assertEqual(r.returncode, 0, r.out)
        text = self.budget()
        self.assertIn('"path": "methodology/SESSION_RUNNER.md"', text)
        self.assertIn('"path": "SESSION_NOTES.md"', text, "a tier-2 file is still at the root")
        gates = json.loads((self.project / ".quality-gates.json").read_text(encoding="utf-8"))
        self.assertEqual(gates["results_file"], ".quality-gates-results.json")
        self.assertIn("-- CHANGELOG.md)", gates["gates"][0]["command"])

    def test_a_config_that_is_not_json_is_moved_and_not_rewritten(self):
        (self.project / ".quality-gates.json").write_text("{ this is not json\n", encoding="utf-8")
        self.commit("a broken config")
        r = run_migrate(self.project, "--apply")
        self.assertEqual(r.returncode, 0, r.out)
        self.assertEqual((self.project / "methodology" / ".quality-gates.json").read_text(encoding="utf-8"), "{ this is not json\n")
        self.assertNotIn(".quality-gates.json", [x["path"] for x in r.report["rewrites"]])


def entry_split(text):
    """(entries, rest): the `### ` headings of a ledger in order."""
    return re.findall(r"^### (\d{4}-\d{2}-\d{2} · .*)$", text, flags=re.M)


class TestTheLedgerEntry(Adopter):
    """The migration commit carries ONE new ledger entry, and it never rewrites a committed one."""

    def ledger(self, rel="methodology/CHANGELOG.md"):
        return (self.project / rel).read_text(encoding="utf-8")

    def test_one_entry_is_prepended_and_every_older_line_is_untouched(self):
        before = self.ledger("CHANGELOG.md")
        r = run_migrate(self.project, "--apply")
        self.assertEqual(r.returncode, 0, r.out)
        after = self.ledger()
        new = entry_split(after)
        old = entry_split(before)
        self.assertEqual(len(new), len(old) + 1)
        self.assertEqual(new[1:], old)
        self.assertRegex(new[0], r"^\d{4}-\d{2}-\d{2} · \[ad hoc\] Layout migration: ")
        diff = git(self.project, "diff", "-M", "HEAD~1", "HEAD", "--", "methodology/CHANGELOG.md", "CHANGELOG.md")
        removed = [l for l in diff.splitlines() if l.startswith("-") and not l.startswith("---")]
        self.assertEqual(removed, [], "the migration removed or rewrote a line of the ledger")

    def test_an_example_in_a_fenced_block_of_the_ledger_header_does_not_take_the_entry(self):
        # A ledger that kept the v3.7 seed text has a 'How to add an entry' section that shows an example
        # heading in a fence; the tool's entry sat at line 48 of the moved ledger, inside that fence.
        example = "```\n### 2026-01-15 · [ad hoc] Ship the export-retry fix\n- **Change:** exports retry once\n```\n\n"
        marker = "<!-- Entries go below"
        text = self.ledger("CHANGELOG.md")
        self.assertEqual(text.count(marker), 1)
        (self.project / "CHANGELOG.md").write_text(text.replace(marker, example + marker), encoding="utf-8")
        self.commit("a fenced example in the ledger header")
        r = run_migrate(self.project, "--apply")
        self.assertEqual(r.returncode, 0, r.out)
        after = self.ledger()
        self.assertIn(example, after, "the example block was edited")
        self.assertEqual(after.count("Layout migration"), 1)
        self.assertGreater(after.index("Layout migration"), after.index(marker))
        self.assertEqual(after.count("```") % 2, 0)
        self.assertLess(after.index("Layout migration"), after.index("### 2026-09-"))

    def test_a_ledger_with_a_fence_that_never_closes_before_its_first_entry_is_refused_and_nothing_is_written(self):
        marker = "<!-- Entries go below"
        text = self.ledger("CHANGELOG.md")
        (self.project / "CHANGELOG.md").write_text(text.replace(marker, "```\n### 2026-01-15 · [ad hoc] example\n\n" + marker), encoding="utf-8")
        self.commit("a fence that never closes")
        before = tree_state(self.project)
        r = run_migrate(self.project, "--apply")
        self.assertEqual(r.returncode, 1, r.out)
        self.assertEqual(r.report["status"], "refused", r.out)
        self.assertEqual([x["code"] for x in r.report["refusals"]], ["rewrite-unsafe"], r.out)
        self.assertIn("never closes", r.report["refusals"][0]["message"])
        self.assertEqual(tree_state(self.project), before)

    def test_the_entry_sits_above_the_first_entry_and_the_ledger_still_passes_check_ledger(self):
        run_migrate(self.project, "--apply")
        after = self.ledger()
        first = after.index("### ")
        self.assertTrue(after[first:].startswith("### 20"), after[first:first + 40])
        self.assertIn("Layout migration", after[first:after.index("### 2026-09-")])
        check = subprocess.run([sys.executable, "-B", str(REPO / "bin" / "check-ledger"), "--file", "methodology/CHANGELOG.md"],
                               cwd=self.project, capture_output=True, text=True)
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

    def test_the_entry_says_what_moved_what_was_rewritten_and_by_which_tool(self):
        r = run_migrate(self.project, "--apply")
        text = r.report["ledger_entry"]["text"]
        self.assertIn("`bin/migrate-layout`", text)
        self.assertIn("tier all", text)
        self.assertIn("38 files", text)
        for path in ("CLAUDE.md", ".gitignore", "methodology/.context-budget.json", "methodology/.quality-gates.json"):
            self.assertIn("`%s`" % path, text)
        self.assertIn(text.strip(), self.ledger())

    def test_a_dry_run_shows_the_entry_and_writes_nothing(self):
        before = tree_state(self.project)
        r = run_migrate(self.project)
        self.assertEqual(r.report["ledger_entry"]["path"], "methodology/CHANGELOG.md")
        self.assertIn("Layout migration", r.report["ledger_entry"]["text"])
        self.assertEqual(tree_state(self.project), before)

    def test_a_ledger_that_does_not_move_in_tier_1_takes_the_entry_where_it_is(self):
        r = run_migrate(self.project, "--apply", "--tier", "1")
        self.assertEqual(r.returncode, 0, r.out)
        self.assertIn("Layout migration", self.ledger("CHANGELOG.md"))
        self.assertFalse((self.project / "methodology" / "CHANGELOG.md").exists())
        self.assertEqual(r.report["ledger_entry"]["path"], "CHANGELOG.md")

    def test_a_project_with_no_ledger_gets_no_entry_and_is_migrated_all_the_same(self):
        git(self.project, "rm", "-q", "CHANGELOG.md")
        self.commit("no ledger")
        r = run_migrate(self.project, "--apply")
        self.assertEqual(r.returncode, 0, r.out)
        self.assertIsNone(r.report["ledger_entry"])

    def test_the_entry_goes_under_a_heading_for_the_current_month_and_makes_one_when_the_month_has_turned(self):
        import datetime
        month = datetime.date.today().strftime("%Y-%m")
        base = self.ledger("CHANGELOG.md")
        first = base.index("### ")
        for heading, expect_new_heading in (("## %s\n\n" % month, False), ("## 2001-01\n\n", True)):
            project = Path(self._td.name) / ("m%d" % expect_new_heading)
            shutil.copytree(self.project, project, symlinks=True)
            (project / "CHANGELOG.md").write_text(base[:first] + heading + base[first:], encoding="utf-8")
            commit_all(project, "a month heading")
            self.assertEqual(run_migrate(project, "--apply").returncode, 0)
            after = (project / "methodology" / "CHANGELOG.md").read_text(encoding="utf-8")
            self.assertEqual(after.count("## %s\n" % month), 1, after[first - 50:first + 400])
            i_entry = after.index("Layout migration")
            self.assertGreater(i_entry, after.index("## %s\n" % month))
            if expect_new_heading:
                self.assertLess(after.index("## %s\n" % month), after.index("## 2001-01"))
                self.assertLess(i_entry, after.index("## 2001-01"))

    def test_a_ledger_too_small_to_take_an_entry_and_stay_a_rename_is_refused_and_rolled_back(self):
        seed = (REPO / "starter-kit" / "CHANGELOG.md").read_text(encoding="utf-8")
        (self.project / "CHANGELOG.md").write_text(seed, encoding="utf-8")
        self.commit("a ledger with no entries yet")
        before = tree_state(self.project)
        r = run_migrate(self.project, "--apply")
        self.assertEqual(r.returncode, 3, r.out)
        self.assertEqual(r.report["status"], "rolled-back")
        self.assertIn("below 90% similarity", r.report["commit"]["error"])
        self.assertIn("CHANGELOG.md", r.report["commit"]["error"])
        self.assertEqual(tree_state(self.project), before)


class TestTheHitsItWillNotRewrite(Adopter):
    """The tool lists every hit it will not rewrite and why: CI workflows, `.claude/` rules, `.githooks/`
    copies, ledger links (a committed ledger entry is never edited) and anything else that names a moved file."""

    PLACES = {"ci": ".github/workflows/ci.yml", "harness": ".claude/settings.json", "hooks": ".githooks/pre-commit",
              "other": "README.md"}
    CATEGORIES = ["ci", "hooks", "tests", "proofs", "scripts", "config", "harness", "ledger", "other"]  # nine categories

    def test_each_category_counts_its_mentions_and_names_the_files_and_lines(self):
        nr = run_migrate(self.project).report["not_rewritten"]
        self.assertEqual({k: (v["mentions"], v["files"]) for k, v in nr.items() if k != "ledger"},
                         {"ci": (3, 1), "harness": (2, 1), "hooks": (1, 1), "other": (2, 1),
                          "tests": (0, 0), "proofs": (0, 0), "scripts": (0, 0), "config": (0, 0)})
        self.assertEqual([(s["file"], s["line"]) for s in nr["ci"]["sites"]],
                         [(".github/workflows/ci.yml", 4), (".github/workflows/ci.yml", 5), (".github/workflows/ci.yml", 6)])
        self.assertEqual(nr["ci"]["sites"][2]["names"], ["docs/methodology/"], "a CI filter on the directory is a hit")
        self.assertEqual([(s["file"], s["line"]) for s in nr["hooks"]["sites"]], [(".githooks/pre-commit", 2)])
        site = nr["harness"]["sites"][0]
        self.assertEqual((site["file"], site["line"]), (".claude/settings.json", 1))
        self.assertEqual(sorted(site["names"]), ["SESSION_RUNNER.md", "methodology_dashboard.py"])
        self.assertIn("Read(SESSION_RUNNER.md)", site["text"])

    def test_a_binary_file_that_contains_a_moved_name_is_not_a_hit(self):
        (self.project / "data.bin").write_bytes(b"\x00\x01\x02 CHANGELOG.md \x00\xff")
        self.commit("a binary file")
        other = run_migrate(self.project).report["not_rewritten"]["other"]
        self.assertEqual((other["mentions"], other["files"]), (2, 1), "only README.md names a moved file")
        self.assertNotIn("data.bin", [s["file"] for s in other["sites"]])

    def test_sites_are_capped_per_category_and_the_count_is_not(self):
        (self.project / "README.md").write_text("see CHANGELOG.md\n" * 30, encoding="utf-8")
        self.commit("a readme that names the ledger thirty times")
        other = run_migrate(self.project).report["not_rewritten"]["other"]
        self.assertEqual((other["mentions"], other["files"], len(other["sites"])), (30, 1, 25))

    def test_the_ledger_links_are_counted_and_not_listed(self):
        nr = run_migrate(self.project).report["not_rewritten"]
        self.assertGreaterEqual(nr["ledger"]["mentions"], 2)
        self.assertGreaterEqual(nr["ledger"]["files"], 1)
        self.assertEqual(nr["ledger"]["sites"], [], "a ledger's links are counted, never listed one by one")

    def test_none_of_them_is_edited_by_an_apply(self):
        before = {rel: (self.project / rel).read_bytes() for rel in self.PLACES.values()}
        r = run_migrate(self.project, "--apply")
        self.assertEqual(r.returncode, 0, r.out)
        for rel, data in before.items():
            self.assertEqual((self.project / rel).read_bytes(), data, "%s was edited" % rel)
        self.assertEqual(r.report["not_rewritten"]["ci"]["mentions"], 3)

    def test_a_moved_file_a_rewritten_file_and_a_qualified_name_are_not_hits(self):
        nr = run_migrate(self.project).report["not_rewritten"]
        self.assertEqual(sorted(nr), sorted(self.CATEGORIES), "nothing was scanned")
        listed = {s["file"] for cat in nr.values() for s in cat["sites"]}
        self.assertIn(".github/workflows/ci.yml", listed, "the scan found nothing, so the absences below prove nothing")
        self.assertNotIn("SAFEGUARDS.md", listed, "a moved framework document is not scanned")
        self.assertNotIn("CLAUDE.md", listed, "a file the tool rewrites is not a hit")
        self.assertNotIn(".gitignore", listed)

    def test_no_hits_still_prints_every_category(self):
        for rel in self.PLACES.values():
            git(self.project, "rm", "-q", rel)
        self.commit("remove the places that name a moved file")
        nr = run_migrate(self.project).report["not_rewritten"]
        self.assertEqual(sorted(nr), sorted(self.CATEGORIES))
        for name in self.CATEGORIES:
            if name != "ledger":
                self.assertEqual((nr[name]["mentions"], nr[name]["files"], nr[name]["sites"], nr[name]["paths"]), (0, 0, [], []), name)

    def test_the_text_a_person_reads_lists_them(self):
        r = run_migrate(self.project, json_out=False)
        self.assertRegex(r.out, r"(?m)^not rewritten")
        self.assertIn(".github/workflows/ci.yml:4", r.out)
        self.assertRegex(r.out, r"(?m)^\s+ledger:\s+\d+ mention")


class TestTheMachineReadFilesAreListedApartFromProse(Adopter):
    """On a real migration every check the tool runs passed and the adopter's own CI broke,
    because the report put the tests and proofs that read a moved path in `other` with its prose, showed 25 sites of 2,647
    mentions in 73 files, and none of the four files that broke was among them. A machine-read file is now listed, every
    one, under its own kind. The scan rule itself is unchanged: only the sorting and the listing are new."""

    PROOFS = ("docs/architecture-history/SESSION_NOTES-pointer-collapse.verify.sh",
              "docs/architecture-history/SESSION_NOTES-pointer-collapse-S254.verify.sh")
    BREAKERS = {"tests/test_read_budget.py": 'RUNNER = "SESSION_RUNNER.md"\n',
                "tests/test_session_notes_census.py": 'LEDGER = "SESSION_NOTES.md"\n',
                PROOFS[0]: '#!/bin/bash\nLIVE="SESSION_NOTES.md"\n',
                PROOFS[1]: '#!/bin/bash\nLIVE="SESSION_NOTES.md"\n'}

    def add(self, files, message="files that name a moved file"):
        for rel, text in files.items():
            path = self.project / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        self.commit(message)

    def rows(self, nr, cat):
        return {x["file"]: x for x in nr[cat]["paths"]}

    def test_the_four_files_that_broke_an_adopter_are_listed_each_under_its_kind(self):
        self.add(self.BREAKERS)
        nr = run_migrate(self.project).report["not_rewritten"]
        self.assertEqual(sorted(self.rows(nr, "tests")), ["tests/test_read_budget.py", "tests/test_session_notes_census.py"])
        self.assertEqual(sorted(self.rows(nr, "proofs")), sorted(self.PROOFS))
        row = self.rows(nr, "tests")["tests/test_read_budget.py"]
        self.assertEqual((row["line"], row["mentions"], row["code_mentions"], row["names"]), (1, 1, 1, ["SESSION_RUNNER.md"]))
        self.assertIn("RUNNER", row["text"])
        proof = self.rows(nr, "proofs")[self.PROOFS[0]]
        self.assertEqual((proof["line"], proof["names"]), (2, ["SESSION_NOTES.md"]))
        listed = {s["file"] for s in nr["other"]["sites"]}
        self.assertFalse(listed & set(self.BREAKERS), "a file is in one category, not two")
        self.assertEqual((nr["other"]["mentions"], nr["other"]["files"]), (2, 1), "other keeps only the README's two mentions")
        kinds = ("tests", "proofs", "scripts", "config", "other")
        self.assertEqual(sum(nr[k]["mentions"] for k in kinds), 2 + 4, "the split moves mentions; it neither adds nor drops one")

    def test_every_machine_read_file_is_listed_though_the_sites_stay_capped(self):
        files = {"tests/test_n%02d.py" % i: 'LEDGER = "CHANGELOG.md"\n' for i in range(30)}
        files["tests/test_big.py"] = 'LEDGER = "CHANGELOG.md"\n' * 60
        self.add(files)
        tests = run_migrate(self.project).report["not_rewritten"]["tests"]
        self.assertEqual((tests["mentions"], tests["files"]), (90, 31))
        self.assertEqual(len(tests["sites"]), 25, "sites stay capped at 25 as before")
        self.assertEqual({s["file"] for s in tests["sites"]}, {"tests/test_big.py"}, "the capped sites are all one file's: the crowd-out the machine-read listing prevents")
        self.assertEqual([x["file"] for x in tests["paths"]], sorted(files), "the file list is complete and sorted")
        big = next(x for x in tests["paths"] if x["file"] == "tests/test_big.py")
        self.assertEqual((big["mentions"], big["code_mentions"]), (60, 60))

    def test_a_prose_file_under_a_test_directory_stays_in_other(self):
        self.add({"tests/NOTES.md": "The ledger is CHANGELOG.md.\n"})
        nr = run_migrate(self.project).report["not_rewritten"]
        self.assertEqual(nr["tests"]["paths"], [])
        self.assertIn("tests/NOTES.md", {s["file"] for s in nr["other"]["sites"]})

    def test_a_script_is_found_by_its_extension_or_by_its_first_line(self):
        self.add({"scripts/refresh.py": 'LEDGER = "CHANGELOG.md"\n',
                  "scripts/refresh": '#!/usr/bin/env python3\nLEDGER = "CHANGELOG.md"\n',
                  "scripts/notes": "the ledger is CHANGELOG.md\n"})
        nr = run_migrate(self.project).report["not_rewritten"]
        self.assertEqual(sorted(self.rows(nr, "scripts")), ["scripts/refresh", "scripts/refresh.py"])
        self.assertEqual(self.rows(nr, "scripts")["scripts/refresh"]["line"], 2)
        self.assertIn("scripts/notes", {s["file"] for s in nr["other"]["sites"]}, "no extension and no first line: text")

    def test_a_config_and_a_hook_framework_file_and_a_hook_git_does_not_track_are_listed_too(self):
        self.add({"Makefile": "ledger:\n\tcat CHANGELOG.md\n", ".pre-commit-config.yaml": "files: CHANGELOG.md\n"})
        hook = self.project / ".git" / "hooks" / "pre-commit"
        hook.write_text('#!/bin/sh\n# installed by context_budget.py\nexec python3 "$(git rev-parse --show-toplevel)/context_budget.py" --precommit\n', encoding="utf-8")
        nr = run_migrate(self.project).report["not_rewritten"]
        self.assertEqual(sorted(self.rows(nr, "config")), ["Makefile"])
        hooks = self.rows(nr, "hooks")
        self.assertEqual(sorted(hooks), [".git/hooks/pre-commit", ".githooks/pre-commit", ".pre-commit-config.yaml"])
        self.assertEqual([x["file"] for x in nr["hooks"]["paths"]], sorted(hooks),
                         "sorted by file, though the hook git does not track is read after the tracked ones")
        self.assertEqual({k: bool(v.get("untracked")) for k, v in hooks.items()},
                         {".git/hooks/pre-commit": True, ".githooks/pre-commit": False, ".pre-commit-config.yaml": False})
        self.assertEqual((hooks[".git/hooks/pre-commit"]["mentions"], hooks[".git/hooks/pre-commit"]["code_mentions"],
                          hooks[".git/hooks/pre-commit"]["line"]), (2, 1, 3), "the comment names the tool and runs nothing; line 3 execs it")

    def test_a_mention_on_a_comment_line_is_counted_and_marked(self):
        self.add({"tests/test_c.py": "# the ledger is CHANGELOG.md\n", "tests/test_d.py": '# CHANGELOG.md\nLEDGER = "CHANGELOG.md"\n'})
        rows = self.rows(run_migrate(self.project).report["not_rewritten"], "tests")
        self.assertEqual((rows["tests/test_c.py"]["mentions"], rows["tests/test_c.py"]["code_mentions"]), (1, 0))
        self.assertEqual((rows["tests/test_d.py"]["mentions"], rows["tests/test_d.py"]["code_mentions"], rows["tests/test_d.py"]["line"]), (2, 1, 2),
                         "the row points at the first mention on a code line")

    def test_two_names_on_one_line_are_two_mentions_on_code_lines(self):
        self.add({"tests/test_two.py": 'LEDGERS = ["CHANGELOG.md", "HANDOFFS.md"]\n'})
        row = self.rows(run_migrate(self.project).report["not_rewritten"], "tests")["tests/test_two.py"]
        self.assertEqual((row["mentions"], row["code_mentions"], row["names"]), (2, 2, ["CHANGELOG.md", "HANDOFFS.md"]))

    def test_a_comment_only_file_is_printed_after_the_files_that_name_a_moved_path_on_a_code_line(self):
        self.add({"tests/test_a.py": "# the ledger is CHANGELOG.md\n", "tests/test_z.py": 'LEDGER = "CHANGELOG.md"\n'})
        out = run_migrate(self.project, json_out=False).out
        self.assertLess(out.index("tests/test_z.py:1"), out.index("tests/test_a.py:1"), "the candidates come first, though a sorts before z")

    def test_a_file_with_several_mentions_says_how_many_are_on_code_lines(self):
        self.add({"tests/test_two.py": '# CHANGELOG.md\nLEDGERS = ["CHANGELOG.md", "HANDOFFS.md"]\n'})
        out = run_migrate(self.project, json_out=False).out
        self.assertRegex(out, r"tests/test_two\.py:2 .*\(3 mentions, 2 on code lines\)")

    def test_a_hook_git_does_not_track_is_marked_on_its_own_row(self):
        """The moves list also says `not tracked` of a plain move, so the words alone prove nothing about the hook."""
        hook = self.project / ".git" / "hooks" / "pre-commit"
        hook.write_text('#!/bin/sh\n# installed by context_budget.py\nexec python3 "$(git rev-parse --show-toplevel)/context_budget.py" --precommit\n', encoding="utf-8")
        out = run_migrate(self.project, json_out=False).out
        self.assertRegex(out, r"\.git/hooks/pre-commit:3 .*\[not tracked: per clone\]")
        self.assertNotRegex(out, r"\.githooks/pre-commit:\d+ .*\[not tracked")

    def test_the_text_says_what_the_list_is_and_is_not(self):
        self.add(self.BREAKERS)
        self.add({"tests/test_c.py": "# the ledger is CHANGELOG.md\n"}, "a test that names it only in a comment")
        out = run_migrate(self.project, json_out=False).out
        self.assertRegex(out, r"(?m)^\s+machine-read files that name a moved path")
        for row in ("tests/test_read_budget.py:1", "tests/test_session_notes_census.py:1", self.PROOFS[0] + ":2", self.PROOFS[1] + ":2"):
            self.assertIn(row, out)
        for phrase in ("candidates", "does not run them", "necessary, not sufficient", "rehearse"):
            self.assertIn(phrase, out)
        self.assertRegex(out, r"tests/test_c\.py:1 .*\[comment lines only\]")
        self.assertRegex(out, r"(?m)^\s+tests:\s+3 mention\(s\) in 3 file\(s\)")

    def test_a_project_with_none_says_so_in_every_kind(self):
        out = run_migrate(self.project, json_out=False).out
        for kind in ("tests", "proofs", "scripts", "config"):
            self.assertRegex(out, r"(?m)^\s+%s:\s+0 mention\(s\) in 0 file\(s\)" % kind)

    def test_listing_a_file_never_edits_it(self):
        self.add(self.BREAKERS)
        before = {rel: (self.project / rel).read_bytes() for rel in self.BREAKERS}
        r = run_migrate(self.project, "--apply", json_out=False)
        self.assertEqual(r.returncode, 0, r.out)
        for rel, data in before.items():
            self.assertEqual((self.project / rel).read_bytes(), data, "%s was edited" % rel)
        self.assertIn("tests/test_read_budget.py:1", r.out, "an apply prints the list too")


class TestAPatternThatStopsMatchingIsListed(Adopter):
    """The list of machine-read files reads whole names, so a root `.Rbuildignore` of
    regular expressions (`^SESSION_RUNNER.*\\.md$`) was listed only for the comment lines that spelled a name out, and the
    row a person read was the harmless one. The file is now read as the program reads it: every non-empty line a
    case-insensitive regular expression, a line that matches a path or a directory above it covers it, and a moved file is
    exposed when a line covers it where it is and none covers it where it goes. A candidate, never a verdict: Python's `re`,
    not R's engine. A packager's ignore file (`.vscodeignore`) is config, not prose."""

    LINES = "^SESSION_RUNNER.*\\.md$\n^methodology_trim\\.py$\n^dashboard\\.html$\n"
    REMARKED = "# keep the framework files out of the build\n" + LINES

    def put(self, text, rel=".Rbuildignore", message="an ignore file"):
        path = self.project / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        self.commit(message)

    def report(self, *args):
        return run_migrate(self.project, *args).report["not_rewritten"]

    def row(self, nr, rel=".Rbuildignore", cat="config"):
        return next((x for x in nr[cat]["paths"] if x["file"] == rel), None)

    def test_a_file_of_regular_expressions_is_listed_though_it_names_no_file(self):
        self.put(self.REMARKED)
        nr = self.report()
        row = self.row(nr)
        self.assertEqual((row["mentions"], row["code_mentions"], row["names"]), (0, 0, []), "no whole name is spelled out in it")
        self.assertEqual([x["line"] for x in row["patterns"]["lines"]], [2, 3, 4])
        self.assertEqual(row["patterns"]["exposed"], ["SESSION_RUNNER.md", "dashboard.html", "methodology_trim.py"])
        self.assertEqual(row["patterns"]["unread"], 0)
        self.assertEqual((row["line"], row["text"]), (2, "^SESSION_RUNNER.*\\.md$"), "the row points at the first line that stops matching, not at line 1")
        self.assertEqual((nr["config"]["files"], nr["config"]["mentions"]), (1, 0), "a pattern is not a mention of a name")

    def test_a_file_that_also_spells_a_name_out_is_one_row_with_both(self):
        self.put("# the ledger is CHANGELOG.md\n^SESSION_RUNNER.*\\.md$\n")
        nr = self.report()
        row = self.row(nr)
        self.assertEqual((row["mentions"], row["code_mentions"], row["line"]), (1, 0, 1), "the row, as it was")
        self.assertEqual(row["patterns"]["exposed"], ["SESSION_RUNNER.md"])
        self.assertEqual(sum(1 for x in nr["config"]["paths"] if x["file"] == ".Rbuildignore"), 1)
        self.assertEqual((nr["config"]["files"], nr["config"]["mentions"]), (1, 1))

    def test_a_row_whose_patterns_stop_matching_is_not_marked_comment_lines_only(self):
        """The file spells a name out only in a comment, and that is the harmless half: the marker would tell a reader to skip a
        file whose patterns are the exposure."""
        self.put("# the ledger is CHANGELOG.md\n^SESSION_RUNNER.*\\.md$\n")
        row_line = next(l for l in run_migrate(self.project, json_out=False).out.splitlines() if ".Rbuildignore:1" in l)
        self.assertNotIn("[comment lines only]", row_line)
        self.put("# the ledger is CHANGELOG.md\n", message="the same file without the pattern")
        row_line = next(l for l in run_migrate(self.project, json_out=False).out.splitlines() if ".Rbuildignore:1" in l)
        self.assertIn("[comment lines only]", row_line, "with nothing else in it the marker is still true")

    def test_a_line_that_covers_the_new_directory_clears_every_line_it_covers(self):
        self.put(self.LINES + "^methodology$\n")
        nr = self.report()
        self.assertIsNone(self.row(nr))
        self.assertEqual(nr["config"]["files"], 0)

    def test_a_line_that_covers_a_directory_exposes_the_files_under_it(self):
        self.put("^docs$\n")
        exposed = self.row(self.report())["patterns"]["exposed"]
        self.assertIn("docs/methodology/HOW_TO_USE.md", exposed)
        self.assertIn("docs/archive/CHANGELOG-through-2026-08-01.md", exposed)
        self.assertNotIn("docs/methodology/PROJECT_CONVENTIONS.md", exposed, "the project's own file stays where it is")

    def test_tier_one_leaves_the_ledgers_in_place_so_their_lines_stay_covered(self):
        self.put("^CHANGELOG.*\\.md$\n^SESSION_RUNNER.*\\.md$\n")
        self.assertEqual(self.row(self.report("--tier", "1"))["patterns"]["exposed"], ["SESSION_RUNNER.md"])
        self.assertEqual(self.row(self.report())["patterns"]["exposed"], ["CHANGELOG.md", "SESSION_RUNNER.md"])

    def test_only_the_file_at_the_root_is_read(self):
        self.put("^SESSION_RUNNER.*\\.md$\n", rel="pkg/.Rbuildignore")
        nr = self.report()
        self.assertIsNone(self.row(nr, "pkg/.Rbuildignore"))
        self.assertEqual(nr["config"]["files"], 0)

    def test_a_line_that_is_not_a_regular_expression_is_counted_and_the_rest_are_read(self):
        self.put("[unclosed\n^CHANGELOG\\.md$\n")
        patterns = self.row(self.report())["patterns"]
        self.assertEqual((patterns["unread"], patterns["exposed"]), (1, ["CHANGELOG.md"]))

    def test_a_project_without_one_lists_no_pattern(self):
        nr = self.report()
        for cat in ("ci", "hooks", "tests", "proofs", "scripts", "config"):
            self.assertTrue(all("patterns" not in x for x in nr[cat]["paths"]), cat)
        self.assertEqual(nr["config"]["files"], 0)

    def test_the_text_says_which_lines_stop_matching_and_what_would_cover_the_new_place(self):
        self.put(self.REMARKED)
        out = run_migrate(self.project, json_out=False).out
        self.assertRegex(out, r"\.Rbuildignore:2 .*\^SESSION_RUNNER\.\*\\\.md\$")
        row_line = out.split(".Rbuildignore:2")[1].split("\n")[0]
        self.assertNotIn("[comment lines only]", row_line, "it is a pattern row, not a comment-only one")
        self.assertNotIn("mentions", row_line, "a row of patterns spells no name out, so it has no count of mentions to print")
        for phrase in ("line 2:", "line 4:", "SESSION_RUNNER.md", "dashboard.html", "^methodology$", "case-insensitive regular expression",
                       "Python", "a candidate, not a verdict"):
            self.assertIn(phrase, out)
        self.assertRegex(out, r"(?m)^\s+config:\s+0 mention\(s\) in 1 file\(s\)")
        self.assertRegex(out, r"3 line\(s\) cover 3 moved file\(s\)")

    def test_a_line_that_covers_many_files_names_three_and_counts_the_rest(self):
        self.put("^docs$\n")
        out = run_migrate(self.project, json_out=False).out
        self.assertRegex(out, r"line 1: \^docs\$  stops covering [^,\n]+, [^,\n]+, [^,\n]+ and \d+ more\n")
        self.assertRegex(out, r"\n      1 line\(s\) cover (?!1 )\d+ moved file\(s\)", "the line count and the file count are two numbers")

    def test_a_line_that_cannot_be_read_is_said_in_the_text(self):
        self.put("[unclosed\n^CHANGELOG\\.md$\n")
        self.assertRegex(run_migrate(self.project, json_out=False).out, r"1 line\(s\) could not be read as a regular expression")

    def test_a_file_whose_only_lines_cannot_be_read_gets_no_row(self):
        self.put("[unclosed\n")
        nr = self.report()
        self.assertIsNone(self.row(nr))
        self.assertEqual(nr["config"]["files"], 0)

    def test_a_file_git_does_not_track_is_not_read(self):
        (self.project / ".git" / "info" / "exclude").write_text(".Rbuildignore\n", encoding="utf-8")
        (self.project / ".Rbuildignore").write_text(self.LINES, encoding="utf-8")
        r = run_migrate(self.project)
        self.assertEqual(r.report["status"], "ok", r.out)
        self.assertIsNone(self.row(r.report["not_rewritten"]))

    def test_a_row_of_patterns_sorts_with_the_candidates_not_with_the_comment_only_files(self):
        self.put("# CHANGELOG.md\n", rel=".Acfg.json", message="a config that names it only in a comment; it sorts before .Rbuildignore")
        self.put(self.LINES)
        out = run_migrate(self.project, json_out=False).out
        self.assertLess(out.index(".Rbuildignore:1"), out.index(".Acfg.json:1"), "by name alone .Acfg.json comes first")

    def test_listing_a_pattern_file_never_edits_it(self):
        self.put(self.LINES)
        before = (self.project / ".Rbuildignore").read_bytes()
        r = run_migrate(self.project, "--apply", json_out=False)
        self.assertEqual(r.returncode, 0, r.out)
        self.assertEqual((self.project / ".Rbuildignore").read_bytes(), before)
        self.assertIn(".Rbuildignore:1", r.out, "an apply prints the list too")

    # --- a packager's ignore file ---
    def test_a_packagers_ignore_file_that_names_a_moved_file_is_config_not_prose(self):
        self.put("SESSION_RUNNER.md\nCHANGELOG.md\n", rel=".vscodeignore")
        nr = self.report()
        row = self.row(nr, ".vscodeignore")
        self.assertEqual((row["mentions"], row["code_mentions"]), (2, 2))
        self.assertNotIn(".vscodeignore", {s["file"] for s in nr["other"]["sites"]}, "a file is in one category, not two")
        self.put("SESSION_RUNNER.md\nCHANGELOG.md\n", rel=".npmignore")
        npm = self.row(self.report(), ".npmignore")
        self.assertEqual((npm["mentions"], npm["code_mentions"]), (2, 2))
        self.assertNotIn("patterns", npm, "only vsce's matching was read and run: any other pattern list is listed, never judged")

    def test_a_gitignore_below_the_root_stays_prose(self):
        self.put("CHANGELOG.md\n", rel="web/.gitignore")
        nr = self.report()
        self.assertIsNone(self.row(nr, "web/.gitignore"))
        self.assertIn("web/.gitignore", {s["file"] for s in nr["other"]["sites"]})


class TestAPackagersIgnoreFileIsEvaluated(Adopter):
    """Listing a root `.vscodeignore` as config and never judging it let a
    move that put 36 files into an adopter's `.vsix` pass every check the tool prints; only the adopter's own
    `release-gate` (78 files against 42) saw it. The file is now read as vsce reads it (`package.js` `collectFiles`, vsce
    3.9.2: each line a minimatch pattern with `{ dot: true }` and no `matchBase`, `/**` added to a directory name, vsce's own
    default list, any negation brings a file back) and a moved file is exposed when it is ignored where it is and packaged
    where it goes. Listed, never edited, no refusal; the answer is this tool's translation of minimatch, not minimatch."""

    LINES = "docs/**\nSESSION_RUNNER.md\nCHANGELOG.md\n"

    def put(self, text, rel=".vscodeignore", message="an ignore file"):
        path = self.project / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        self.commit(message)

    def report(self, *args):
        return run_migrate(self.project, *args).report["not_rewritten"]

    def row(self, nr, rel=".vscodeignore", cat="config"):
        return next((x for x in nr[cat]["paths"] if x["file"] == rel), None)

    def test_a_file_that_ignores_names_and_a_directory_is_listed_with_what_the_move_exposes(self):
        self.put("# keep the framework out of the .vsix\n" + self.LINES)
        row = self.row(self.report())
        p = row["patterns"]
        self.assertEqual((row["mentions"], row["code_mentions"]), (2, 2), "the row, as it was: the two bare names")
        self.assertEqual([x["line"] for x in p["lines"]], [2, 3, 4, 0], "line order, the default list last")
        for name in ("SESSION_RUNNER.md", "CHANGELOG.md", "docs/methodology/HOW_TO_USE.md", ".gitattributes"):
            self.assertIn(name, p["exposed"], name)
        self.assertNotIn("docs/methodology/PROJECT_CONVENTIONS.md", p["exposed"], "the project's own file stays where it is")
        self.assertEqual(p["unread"], 0)
        self.assertEqual(p["lines"][-1]["text"], "(vsce default) .gitattributes")
        self.assertEqual((row["line"], row["text"]), (3, "SESSION_RUNNER.md"), "an existing row keeps its pointer: its first mention")
        self.put("# keep the framework out of the .vsix\ndocs/**\n", message="a file that names no moved file")
        fresh = self.row(self.report())
        self.assertEqual((fresh["line"], fresh["text"], fresh["mentions"]), (2, "docs/**", 0), "a new row points at the first line that stops matching")

    def test_a_line_for_the_new_directory_clears_every_exposure_and_the_row_of_patterns(self):
        self.put(self.LINES + "methodology/**\n")
        row = self.row(self.report())
        self.assertEqual(row["mentions"], 2, "the file still names two moved files, which is the existing row")
        self.assertNotIn("patterns", row)
        self.put("src/**\nmethodology/**\n", message="a file that names no moved file")
        nr = self.report()
        self.assertIsNone(self.row(nr))
        self.assertEqual(nr["config"]["files"], 0)

    def test_a_file_that_names_nothing_moved_is_still_a_row_when_the_default_list_exposes_a_file(self):
        """The root `.gitattributes` is on vsce's default list and moves to `methodology/.gitattributes`."""
        self.put("src/**\n")
        row = self.row(self.report())
        self.assertEqual(row["patterns"]["exposed"], [".gitattributes"])
        self.assertEqual((row["mentions"], row["code_mentions"], row["names"], row["line"], row["untracked"]), (0, 0, [], 0, False))

    def test_tier_one_leaves_the_ledgers_in_place_so_their_lines_stay_covered(self):
        self.put("CHANGELOG.md\nSESSION_RUNNER.md\n")
        tier1 = self.row(self.report("--tier", "1"))["patterns"]["exposed"]
        self.assertIn("SESSION_RUNNER.md", tier1)
        self.assertNotIn("CHANGELOG.md", tier1)
        self.assertIn("CHANGELOG.md", self.row(self.report())["patterns"]["exposed"])

    def test_only_the_file_at_the_root_is_read_and_only_when_git_tracks_it(self):
        self.put("SESSION_RUNNER.md\n", rel="pkg/.vscodeignore")
        below = self.row(self.report(), "pkg/.vscodeignore")
        self.assertEqual(below["mentions"], 1, "the machine-read listing includes it, as a pattern list")
        self.assertNotIn("patterns", below, "but only the file at the root is evaluated")
        (self.project / ".git" / "info" / "exclude").write_text(".vscodeignore\n", encoding="utf-8")
        (self.project / ".vscodeignore").write_text("SESSION_RUNNER.md\n", encoding="utf-8")
        r = run_migrate(self.project)
        self.assertEqual(r.report["status"], "ok", r.out)
        self.assertIsNone(self.row(r.report["not_rewritten"]))

    def test_the_text_says_which_lines_stop_matching_and_what_would_cover_the_new_place(self):
        self.put("# keep the framework out of the .vsix\n" + self.LINES)
        out = run_migrate(self.project, json_out=False).out
        self.assertRegex(out, r"\.vscodeignore:3 .*SESSION_RUNNER\.md")
        row_line = out.split(".vscodeignore:3")[1].split("\n")[0]
        self.assertNotIn("[comment lines only]", row_line)
        for phrase in ("line 2: docs/**  stops covering", "line 3: SESSION_RUNNER.md  stops covering SESSION_RUNNER.md",
                       "vsce's default list: .gitattributes  stops covering .gitattributes", "methodology/**", "minimatch",
                       "no matchBase", "a bare name is the project root's", "a candidate, not a verdict"):
            self.assertIn(phrase, out)
        self.assertNotIn("case-insensitive regular expression", out, "that sentence is R's, and this project has no .Rbuildignore")
        self.assertRegex(out, r"\d+ line\(s\) cover \d+ moved file\(s\)")

    def test_a_line_that_covers_many_files_names_three_and_counts_the_rest(self):
        self.put("docs/**\n")
        out = run_migrate(self.project, json_out=False).out
        self.assertRegex(out, r"line 1: docs/\*\*  stops covering [^,\n]+, [^,\n]+, [^,\n]+ and \d+ more\n")

    def test_a_line_that_cannot_be_read_is_said_in_the_text(self):
        self.put("@(SESSION_RUNNER|CHANGELOG).md\nx{1..3}\nCHANGELOG.md\n")
        out = run_migrate(self.project, json_out=False).out
        self.assertRegex(out, r"2 line\(s\) could not be read as a glob and were not evaluated")
        self.assertEqual(self.row(self.report())["patterns"]["unread"], 2)

    def test_a_file_whose_only_other_lines_cannot_be_read_gets_no_row(self):
        self.put("methodology/**\n@(a|b).md\n")
        nr = self.report()
        self.assertIsNone(self.row(nr))
        self.assertEqual(nr["config"]["files"], 0)

    def test_the_text_prints_the_counts_and_the_versions_the_json_holds(self):
        self.put(self.LINES)
        p = self.row(self.report())["patterns"]
        out = run_migrate(self.project, json_out=False).out
        self.assertNotEqual(len(p["lines"]), len(p["exposed"]))
        self.assertIn("%d line(s) cover %d moved file(s)" % (len(p["lines"]), len(p["exposed"])), out)
        self.assertIn("vsce 3.9.2, minimatch 10.2.5", out)

    def test_a_pattern_list_for_another_program_is_listed_and_never_judged(self):
        self.put("SESSION_RUNNER.md\n", rel=".npmignore")
        self.assertNotIn("patterns", self.row(self.report(), ".npmignore"))

    def test_the_rbuildignore_text_is_the_one_it_was(self):
        self.put("^SESSION_RUNNER.*\\.md$\n", rel=".Rbuildignore")
        out = run_migrate(self.project, json_out=False).out
        for phrase in ("case-insensitive regular expression", "^methodology$", "Python's re, not R's engine"):
            self.assertIn(phrase, out)
        self.assertNotIn("minimatch", out)

    def test_listing_a_vscodeignore_never_edits_it(self):
        self.put(self.LINES)
        before = (self.project / ".vscodeignore").read_bytes()
        r = run_migrate(self.project, "--apply", json_out=False)
        self.assertEqual(r.returncode, 0, r.out)
        self.assertEqual((self.project / ".vscodeignore").read_bytes(), before)
        self.assertIn(".vscodeignore:", r.out, "an apply prints the list too")


class TestTheChecks(Adopter):
    """An apply verifies itself, before and after, with the read-only checks: bin/status, the two ledger
    checkers, check-links, every shard's proof (the exit histogram must not change) and the ledger's history across the
    move. A difference does not undo a commit that is made; it is reported, with the way back, and the exit is 4."""

    NAMES = ["handoff", "history", "ledger", "links", "proofs", "status"]

    def with_real_shard(self):
        """Trim the fixture's ledger with the project's own trimmer, so one shard has a real proof beside it."""
        r = subprocess.run([sys.executable, "-B", "methodology_trim.py", "--file", "CHANGELOG.md", "--cut", "25",
                            "--force", "--write"], cwd=self.project, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.commit("trim the ledger")

    def test_an_apply_runs_every_check_before_and_after_with_no_cell_left_blank(self):
        r = run_migrate(self.project, "--apply", checks=True)
        self.assertEqual(r.returncode, 0, r.out)
        checks = r.report["checks"]
        self.assertTrue(checks["ran"])
        for side in ("before", "after"):
            self.assertEqual(sorted(checks[side]), self.NAMES)
            for name in self.NAMES:
                self.assertTrue(checks[side][name], "%s %s is blank" % (side, name))
        self.assertEqual(checks["before"]["status"], {"exit": 0, "tracked": len(TRACKED_DESTS), "current": len(TRACKED_DESTS)})
        self.assertEqual(checks["after"]["status"], {"exit": 0, "tracked": len(TRACKED_DESTS), "current": len(TRACKED_DESTS)})
        self.assertTrue(checks["clean"])
        self.assertTrue(checks["ok"])
        self.assertEqual(checks["differences"], [])

    def test_the_proofs_of_the_moved_shards_give_the_same_histogram_and_the_real_one_still_holds(self):
        self.with_real_shard()
        r = run_migrate(self.project, "--apply", checks=True)
        self.assertEqual(r.returncode, 0, r.out)
        checks = r.report["checks"]
        self.assertEqual(checks["before"]["proofs"], {"count": 3, "histogram": {"0": 3}})
        self.assertEqual(checks["after"]["proofs"], {"count": 3, "histogram": {"0": 3}})
        proof = self.project / "methodology" / "archive" / "CHANGELOG-through-2026-09-28.md.verify.sh"
        again = subprocess.run(["bash", str(proof)], cwd=self.project, capture_output=True, text=True)
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)

    def test_a_proof_that_stops_holding_is_reported_exits_4_and_names_the_way_back(self):
        """The shard rehearsal catches a proof that reads its shard by the old path, so the proof here is one a rehearsal
        cannot predict: it depends on the newest commit's subject, which the rehearsal's commit does not share with the
        migration's. Whatever the cause, a check that differs after a commit is made is reported, not undone."""
        proof = self.project / "docs" / "archive" / "CHANGELOG-through-2026-08-01.md.verify.sh"
        proof.write_text("#!/bin/sh\ngit log -1 --format=%s | grep -q '^chore(methodology)' && exit 1\nexit 0\n", encoding="utf-8")
        self.commit("a proof that depends on the newest commit")
        r = run_migrate(self.project, "--apply", checks=True)
        self.assertEqual(r.returncode, 4, r.out)
        self.assertEqual(r.report["status"], "applied")
        self.assertEqual(r.report["rehearsal"]["excluded"], [], "the rehearsal could not have seen this")
        self.assertEqual(git(self.project, "status", "--porcelain"), "", "the commit was made and must stand")
        checks = r.report["checks"]
        self.assertFalse(checks["ok"])
        self.assertEqual(checks["differences"], ["proofs"])
        self.assertEqual(checks["before"]["proofs"]["histogram"], {"0": 2})
        self.assertEqual(checks["after"]["proofs"]["histogram"], {"0": 1, "1": 1})
        self.assertIn("git revert " + r.report["commit"]["sha"][:12], r.report["checks"]["way_back"])

    def test_a_tree_the_commit_leaves_dirty_is_reported_and_exits_4(self):
        """A post-commit hook that writes a file: the commit stands, and the tree is not clean. Nothing else differs."""
        hook = self.project / ".git" / "hooks" / "post-commit"
        hook.write_text("#!/bin/sh\ntouch stray.txt\n", encoding="utf-8")
        hook.chmod(0o755)
        r = run_migrate(self.project, "--apply", checks=True)
        self.assertEqual(r.returncode, 4, r.out)
        checks = r.report["checks"]
        self.assertFalse(checks["clean"])
        self.assertFalse(checks["ok"])
        self.assertEqual(checks["differences"], [], "only the tree differs")
        self.assertEqual(r.report["status"], "applied")

    def test_the_text_says_so_when_the_tree_is_not_clean(self):
        hook = self.project / ".git" / "hooks" / "post-commit"
        hook.write_text("#!/bin/sh\ntouch stray.txt\n", encoding="utf-8")
        hook.chmod(0o755)
        r = run_migrate(self.project, "--apply", json_out=False, checks=True)
        self.assertEqual(r.returncode, 4, r.out)
        self.assertIn("clean tree: NO", r.out)
        self.assertIn("CHECKS DIFFER (tree not clean)", r.out)

    def test_the_ledgers_history_is_reached_across_the_move(self):
        r = run_migrate(self.project, "--apply", checks=True)
        h = r.report["checks"]
        self.assertGreaterEqual(h["after"]["history"]["commits"], h["before"]["history"]["commits"] + 1)
        followed = git(self.project, "log", "--follow", "--format=%h", "--", "methodology/CHANGELOG.md").split()
        self.assertEqual(len(followed), h["after"]["history"]["commits"])
        self.assertIn(git(self.project, "rev-parse", "--short=7", "HEAD~1").strip(), [c[:7] for c in followed])

    def test_a_link_in_the_projects_own_ledger_that_the_move_leaves_dangling_is_reported_and_not_a_failure(self):
        """The fixture's ledger holds a committed entry that links docs/methodology/HOW_TO_USE.md, right where the ledger
        sat. The move leaves the entry alone (a committed entry is never edited), so the link dangles: the project's own
        file, counted beside the framework's, and no difference."""
        r = run_migrate(self.project, "--apply", checks=True)
        self.assertEqual(r.returncode, 0, r.out)
        checks = r.report["checks"]
        self.assertNotIn("informational", checks, "no check is exempt any more: the documents were rewritten")
        self.assertEqual((checks["before"]["links"]["exit"], checks["before"]["links"]["framework"], checks["before"]["links"]["project"]), (0, 0, 0))
        self.assertEqual((checks["after"]["links"]["exit"], checks["after"]["links"]["framework"], checks["after"]["links"]["project"]), (1, 0, 1))
        self.assertEqual(checks["differences"], [])

    def test_a_framework_document_that_dangles_after_the_move_is_a_difference_exits_4_and_the_commit_stands(self):
        """The after-checks run on the working tree, so a post-commit hook that writes a legacy-style link into a framework
        document stands in for a document authored for the old layout: the link resolved before, and does not now."""
        how = NEW_OF["docs/methodology/HOW_TO_USE.md"]
        hook = self.project / ".git" / "hooks" / "post-commit"
        hook.write_text("#!/bin/sh\nprintf '\\n[x](docs/methodology/ITERATIVE_METHODOLOGY.md)\\n' >> %s\n" % how, encoding="utf-8")
        hook.chmod(0o755)
        r = run_migrate(self.project, "--apply", checks=True)
        self.assertEqual(r.returncode, 4, r.out)
        self.assertEqual(r.report["status"], "applied")
        checks = r.report["checks"]
        self.assertIn("links", checks["differences"])
        self.assertEqual((checks["after"]["links"]["framework"], checks["after"]["links"]["project"]), (1, 1))
        self.assertIn("git revert " + r.report["commit"]["sha"][:12], checks["way_back"])

    def test_the_text_says_which_links_are_judged_and_which_only_reported(self):
        r = run_migrate(self.project, "--apply", json_out=False, checks=True)
        self.assertEqual(r.returncode, 0, r.out)
        self.assertRegex(r.out, r"(?m)^\s+links:\s+exit 0; 0 framework, 0 project dangling -> exit 1; 0 framework, 1 project dangling")
        self.assertNotIn("informational until P9", r.out)
        self.assertIn("framework documents are judged", r.out)

    def test_skip_checks_runs_none_and_says_so(self):
        r = run_migrate(self.project, "--apply", "--skip-checks")
        self.assertEqual(r.returncode, 0, r.out)
        self.assertEqual(r.report["checks"], {"ran": False})

    def test_a_dry_run_runs_no_check(self):
        r = run_migrate(self.project)
        self.assertIsNone(r.report["checks"])

    def test_the_text_a_person_reads_lists_each_check_before_and_after(self):
        r = run_migrate(self.project, "--apply", json_out=False, checks=True)
        self.assertEqual(r.returncode, 0, r.out)
        self.assertRegex(r.out, r"(?m)^checks \(before -> after\):")
        for name in self.NAMES:
            self.assertRegex(r.out, r"(?m)^\s+%s:" % name)


WORKING_TREE_PROOF = """#!/bin/sh
# an older-format proof: it reads its shard by the path it was written at, in the working tree
cd "$(git rev-parse --show-toplevel)" || exit 3
test -f docs/archive/HANDOFFS-through-2026-08-02.md || { echo "FAIL: docs/archive/HANDOFFS-through-2026-08-02.md not found" >&2; exit 2; }
"""


class TestTheShardRehearsal(Adopter):
    """Real data (an adopter's project): an older-format proof reads its shard by its working-tree path, so it exits 2 once
    the shard moves, while the trimmer's current proofs read git history and survive. The tool rehearses the shard moves
    in a throwaway clone, before the plan is shown, and leaves a shard whose proof would regress where it is."""

    def old_format_proof(self):
        (self.project / "docs" / "archive" / "HANDOFFS-through-2026-08-02.md.verify.sh").write_text(WORKING_TREE_PROOF, encoding="utf-8")
        self.commit("an older-format proof")

    def test_a_shard_whose_proof_would_regress_stays_with_its_proof_and_the_plan_says_why(self):
        self.old_format_proof()
        r = run_migrate(self.project)
        got = self.moves(r.report)
        self.assertNotIn("docs/archive/HANDOFFS-through-2026-08-02.md", got)
        self.assertNotIn("docs/archive/HANDOFFS-through-2026-08-02.md.verify.sh", got)
        self.assertIn("docs/archive/CHANGELOG-through-2026-08-01.md", got, "a shard whose proof holds must still move")
        left = {x["path"]: x["reason"] for x in r.report["left_in_place"]}
        for path in ("docs/archive/HANDOFFS-through-2026-08-02.md", "docs/archive/HANDOFFS-through-2026-08-02.md.verify.sh"):
            self.assertIn("proof", left[path])
            self.assertIn("exits 2", left[path])
        self.assertEqual(r.report["rehearsal"]["excluded"], ["docs/archive/HANDOFFS-through-2026-08-02.md"])

    def test_the_apply_leaves_them_where_they_are_and_the_proofs_histogram_is_unchanged(self):
        self.old_format_proof()
        r = run_migrate(self.project, "--apply", checks=True)
        self.assertEqual(r.returncode, 0, r.out)
        self.assertTrue((self.project / "docs" / "archive" / "HANDOFFS-through-2026-08-02.md").is_file())
        self.assertTrue((self.project / "docs" / "archive" / "HANDOFFS-through-2026-08-02.md.verify.sh").is_file())
        self.assertTrue((self.project / "methodology" / "archive" / "CHANGELOG-through-2026-08-01.md").is_file())
        proofs = r.report["checks"]
        self.assertEqual(proofs["before"]["proofs"]["histogram"], {"0": 1})
        self.assertEqual(proofs["before"]["proofs"], proofs["after"]["proofs"])
        again = subprocess.run(["bash", "docs/archive/HANDOFFS-through-2026-08-02.md.verify.sh"], cwd=self.project, capture_output=True, text=True)
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)

    def test_a_proof_that_failed_before_and_fails_the_same_way_after_still_moves(self):
        (self.project / "docs" / "archive" / "HANDOFFS-through-2026-08-02.md.verify.sh").write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        self.commit("a proof that always fails")
        r = run_migrate(self.project)
        self.assertIn("docs/archive/HANDOFFS-through-2026-08-02.md.verify.sh", self.moves(r.report))
        self.assertEqual(r.report["rehearsal"]["excluded"], [])

    def test_the_rehearsal_leaves_no_trace_in_the_project_or_in_the_temporary_directory(self):
        self.old_format_proof()
        before = tree_state(self.project)
        tmp = Path(tempfile.gettempdir())
        clones_before = {p.name for p in tmp.glob("migrate-rehearsal-*")}
        run_migrate(self.project)
        self.assertEqual(tree_state(self.project), before)
        self.assertEqual({p.name for p in tmp.glob("migrate-rehearsal-*")}, clones_before)

    def test_a_project_with_no_proofs_is_not_rehearsed(self):
        for name in ("CHANGELOG-through-2026-08-01.md.verify.sh", "HANDOFFS-through-2026-08-02.md.verify.sh"):
            git(self.project, "rm", "-q", "docs/archive/" + name)
        self.commit("no proofs")
        r = run_migrate(self.project)
        self.assertEqual(r.report["rehearsal"], {"ran": False, "proofs": 0, "excluded": []})

    def test_the_rehearsal_says_how_many_proofs_it_ran(self):
        r = run_migrate(self.project)
        self.assertEqual(r.report["rehearsal"], {"ran": True, "proofs": 2, "excluded": []})

    # --- the shard proofs run only on a run that can go on, so the list
    # a REFUSED run prints is the plan before them (3 moves listed refused, 1 once the refusal cleared). It says so. ---

    def test_a_refused_runs_moves_are_labelled_unrehearsed_in_both_modes(self):
        (self.project / "scratch.txt").write_text("x\n", encoding="utf-8")
        for mode in ((), ("--apply",)):
            r = run_migrate(self.project, *mode, json_out=False)
            self.assertEqual(r.returncode, 1, r.out)
            self.assertIn("dirty-tree", r.stdout)
            heading = [x for x in r.stdout.splitlines() if x.startswith("moves (")]
            self.assertEqual(len(heading), 1, r.stdout)
            self.assertIn("UNREHEARSED", heading[0], "mode %s" % (mode or "dry run"))
            self.assertIn("the shard proofs did not run in a clone", r.stdout)

    def test_a_refused_runs_report_says_in_data_that_the_rehearsal_was_skipped(self):
        (self.project / "scratch.txt").write_text("x\n", encoding="utf-8")
        r = run_migrate(self.project)
        self.assertEqual(r.report["status"], "refused", r.out)
        self.assertTrue(r.report["moves"], "the refused plan still lists its moves")
        self.assertEqual(r.report["rehearsal"], {"ran": False, "proofs": 0, "excluded": [], "skipped": "refused"})

    def test_the_same_project_with_the_refusal_cleared_is_rehearsed_and_not_labelled(self):
        (self.project / "scratch.txt").write_text("x\n", encoding="utf-8")
        (self.project / "scratch.txt").unlink()
        r = run_migrate(self.project, json_out=False)
        self.assertEqual(r.returncode, 0, r.out)
        self.assertNotIn("UNREHEARSED", r.stdout)
        self.assertNotIn("the shard proofs did not run", r.stdout)
        self.assertEqual(run_migrate(self.project).report["rehearsal"], {"ran": True, "proofs": 2, "excluded": []})

    def test_a_refused_run_with_nothing_to_move_has_no_moves_section_and_no_skipped_marker(self):
        applied = run_migrate(self.project, "--apply")
        self.assertEqual(applied.returncode, 0, applied.out)
        (self.project / "scratch.txt").write_text("x\n", encoding="utf-8")
        r = run_migrate(self.project, json_out=False)
        self.assertEqual(r.returncode, 1, r.out)
        self.assertIn("dirty-tree", r.stdout)
        self.assertEqual([x for x in r.stdout.splitlines() if x.startswith("moves (")], [], r.stdout)
        self.assertNotIn("UNREHEARSED", r.stdout)
        self.assertEqual(run_migrate(self.project).report["rehearsal"], {"ran": False, "proofs": 0, "excluded": []})

    def test_a_refusal_that_comes_after_the_rehearsal_does_not_label_a_list_that_was_rehearsed(self):
        marker = "<!-- Entries go below"
        text = (self.project / "CHANGELOG.md").read_text(encoding="utf-8")
        (self.project / "CHANGELOG.md").write_text(text.replace(marker, "```\n### 2026-01-15 · [ad hoc] example\n\n" + marker), encoding="utf-8")
        self.commit("a fence that never closes")
        r = run_migrate(self.project, json_out=False)
        self.assertEqual(r.returncode, 1, r.out)
        self.assertIn("rewrite-unsafe", r.stdout)
        heading = [x for x in r.stdout.splitlines() if x.startswith("moves (")]
        self.assertEqual(len(heading), 1, r.stdout)
        self.assertNotIn("UNREHEARSED", heading[0])
        report = run_migrate(self.project).report
        self.assertEqual(report["rehearsal"], {"ran": True, "proofs": 2, "excluded": []})


class TestWhatTheHitsSayAboutHooksAndDirectories(Adopter):
    """Real data: an adopter's pre-commit hook runs context_budget.py from the root, so it refuses the migration commit; and a
    CLAUDE.md that says `docs/methodology/` as a directory still says it after the paths in it are rewritten."""

    def test_a_hook_that_runs_a_moved_tool_is_flagged_and_one_that_only_names_a_file_is_not(self):
        (self.project / ".githooks" / "pre-push").write_text("#!/bin/sh\npython3 context_budget.py --status || exit 1\n", encoding="utf-8")
        self.commit("a hook that runs a methodology tool")
        r = run_migrate(self.project)
        sites = {s["file"]: s for s in r.report["not_rewritten"]["hooks"]["sites"]}
        self.assertTrue(sites[".githooks/pre-push"]["runs_tool"])
        self.assertFalse(sites[".githooks/pre-commit"]["runs_tool"])
        self.assertEqual(r.report["not_rewritten"]["hooks"]["runs_moved_tool"], 1)
        text = run_migrate(self.project, json_out=False).out
        self.assertIn("refuse the migration commit", text)

    def test_a_hook_line_that_says_it_tries_every_place_is_not_flagged_as_running_a_moved_tool(self):
        """Real data (an adopter's hook): the layout-aware ledger hook assigns the tool's name on a line marked
        `# layout: ok -- ...` and tries three places for it, so it works after the move; the warning that it would refuse the
        migration commit was false (the apply exited 0 in every arm). The site is still listed: a person may want to see it."""
        (self.project / ".githooks" / "pre-push").write_text(
            "#!/bin/sh\nrtool=context_budget.py    # layout: ok -- the tool's name; the places are tried below\n", encoding="utf-8")
        self.commit("a hook that tries every place")
        r = run_migrate(self.project)
        sites = [s for s in r.report["not_rewritten"]["hooks"]["sites"] if s["file"] == ".githooks/pre-push"]
        self.assertEqual([(s["line"], s["runs_tool"]) for s in sites], [(2, False)])
        self.assertEqual(r.report["not_rewritten"]["hooks"]["runs_moved_tool"], 0)
        self.assertNotIn("refuse the migration commit", run_migrate(self.project, json_out=False).out)

    def test_a_marker_with_no_reason_acknowledges_nothing(self):
        """The grammar bin/check-layout-literals reads: `# layout: ok` needs ` -- <reason>`, or it acknowledges nothing."""
        (self.project / ".githooks" / "pre-push").write_text(
            "#!/bin/sh\npython3 context_budget.py --status || exit 1    # layout: ok\n", encoding="utf-8")
        self.commit("a hook with a bare marker")
        r = run_migrate(self.project)
        sites = [s for s in r.report["not_rewritten"]["hooks"]["sites"] if s["file"] == ".githooks/pre-push"]
        self.assertEqual([(s["line"], s["runs_tool"]) for s in sites], [(2, True)])
        self.assertEqual(r.report["not_rewritten"]["hooks"]["runs_moved_tool"], 1)

    def test_this_repositorys_own_ledger_hook_raises_no_warning(self):
        """The reproduction: the hook an adopter is told to install, copied into a project as it is."""
        shutil.copy(REPO / ".githooks" / "pre-commit", self.project / ".githooks" / "pre-commit")
        self.commit("the layout-aware ledger hook")
        r = run_migrate(self.project)
        self.assertEqual(r.report["not_rewritten"]["hooks"]["runs_moved_tool"], 0)
        self.assertNotIn("refuse the migration commit", run_migrate(self.project, json_out=False).out)

    def test_the_marker_grammar_is_the_one_check_layout_literals_reads(self):
        """One grammar in two tools: a marker that acknowledges a literal there must acknowledge a hook line here."""
        m = _load_script("migrate_layout", MIGRATE)
        literals = _load_script("check_layout_literals", REPO / "bin" / "check-layout-literals")
        self.assertEqual(m.MARKER_RE.pattern, literals.MARKER_RE.pattern)

    def test_a_hook_in_the_hooks_directory_that_git_does_not_track_is_found_and_flagged(self):
        """Real data (an adopter's project): context_budget.py install-hook writes .git/hooks/pre-commit, which is per clone and not
        tracked, and which runs $top/context_budget.py: the scan of tracked files could not see the hook that refused."""
        hook = self.project / ".git" / "hooks" / "pre-commit"
        hook.write_text('#!/bin/sh\n# installed by context_budget.py\nexec python3 "$(git rev-parse --show-toplevel)/context_budget.py" --precommit\n', encoding="utf-8")
        hook.chmod(0o755)
        (self.project / ".git" / "hooks" / "commit-msg.sample").write_text("#!/bin/sh\n# CHANGELOG.md in a sample\n", encoding="utf-8")
        before = tree_state(self.project)
        r = run_migrate(self.project)
        self.assertEqual(tree_state(self.project), before)
        sites = [s for s in r.report["not_rewritten"]["hooks"]["sites"] if s["file"] == ".git/hooks/pre-commit"]
        self.assertEqual([(s["line"], s["runs_tool"], s["untracked"]) for s in sites], [(2, False, True), (3, True, True)],
                         "line 2 is a comment naming the tool, and a comment runs nothing; line 3 execs it")
        self.assertEqual(r.report["not_rewritten"]["hooks"]["runs_moved_tool"], 1)
        self.assertFalse([s for s in r.report["not_rewritten"]["hooks"]["sites"] if "sample" in s["file"]], "a .sample hook is not a hook")
        text = run_migrate(self.project, json_out=False).out
        self.assertIn("not tracked", text)
        self.assertIn("refuse the migration commit", text)

    def test_a_hook_directory_the_project_tracks_is_not_counted_twice(self):
        git(self.project, "config", "core.hooksPath", ".githooks")
        r = run_migrate(self.project)
        sites = [s for s in r.report["not_rewritten"]["hooks"]["sites"] if s["file"] == ".githooks/pre-commit"]
        self.assertEqual(len(sites), 1)
        self.assertEqual(r.report["not_rewritten"]["hooks"]["mentions"], 1)

    def test_a_hook_that_runs_a_moved_tool_refuses_the_commit_and_the_tool_rolls_back_and_says_so(self):
        hook = self.project / ".githooks" / "pre-commit"
        hook.write_text("#!/bin/sh\npython3 context_budget.py --status || exit 1\n", encoding="utf-8")
        hook.chmod(0o755)
        git(self.project, "add", "-A")
        git(self.project, "commit", "-q", "--no-verify", "-m", "a hook that runs a methodology tool")
        git(self.project, "config", "core.hooksPath", ".githooks")
        before = tree_state(self.project)
        r = run_migrate(self.project, "--apply")
        self.assertEqual(r.returncode, 3, r.out)
        self.assertEqual(r.report["status"], "rolled-back")
        self.assertIn("context_budget.py", r.report["commit"]["error"])
        self.assertEqual(tree_state(self.project), before)

    def test_a_directory_named_in_a_rewritten_file_is_reported_after_its_paths_are_rewritten(self):
        claude = self.project / "CLAUDE.md"
        claude.write_text(claude.read_text(encoding="utf-8") + "\nThe 13 files under `docs/methodology/` and the shards in docs/archive are the framework's.\n",
                          encoding="utf-8")
        self.commit("a directory mentioned in prose")
        r = run_migrate(self.project)
        sites = [s for s in r.report["not_rewritten"]["other"]["sites"] if s["file"] == "CLAUDE.md"]
        self.assertEqual(len(sites), 1)
        self.assertEqual(sites[0]["names"], ["docs/archive", "docs/methodology/"])
        self.assertIn("The 13 files under", sites[0]["text"])
        rewritten = next(x for x in r.report["rewrites"] if x["path"] == "CLAUDE.md")
        self.assertIn("+Read and follow `methodology/SESSION_RUNNER.md`", rewritten["diff"])

    def test_a_directory_mentioned_in_a_file_the_tool_does_not_edit_is_reported_and_a_full_path_is_not_counted_twice(self):
        (self.project / "README.md").write_text("Methodology lives in docs/methodology/ now.\nSee docs/methodology/HOW_TO_USE.md.\n", encoding="utf-8")
        self.commit("a readme")
        other = run_migrate(self.project).report["not_rewritten"]["other"]
        by_line = {s["line"]: s for s in other["sites"] if s["file"] == "README.md"}
        self.assertEqual(by_line[1]["names"], ["docs/methodology/"])
        self.assertEqual(by_line[2]["names"], ["docs/methodology/HOW_TO_USE.md"])


class TestALedgerSoSmallThatGitSeesNoRenameAtAll(Adopter):
    """Below 50% similarity git reports a delete and an add: the guard must say that, not only "below 90%"."""

    def test_the_rollback_says_it_is_not_a_rename_and_why(self):
        (self.project / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
        self.commit("a ledger of one line")
        before = tree_state(self.project)
        r = run_migrate(self.project, "--apply")
        self.assertEqual(r.returncode, 3, r.out)
        error = r.report["commit"]["error"]
        self.assertIn("CHANGELOG.md -> methodology/CHANGELOG.md (not a rename: the ledger is too small", error)
        self.assertIn("it holds 12 bytes", error)
        self.assertEqual(tree_state(self.project), before)


class TestASmallLedgerIsRefusedWithAReason(Adopter):
    """Real data (an adopter's project): a ledger that is only the seed cannot take its entry and stay a rename at 90%."""

    def test_the_rollback_says_the_ledger_is_too_small_and_how_big_it_is(self):
        seed = (REPO / "starter-kit" / "CHANGELOG.md").read_text(encoding="utf-8")
        (self.project / "CHANGELOG.md").write_text(seed, encoding="utf-8")
        self.commit("a ledger with no entries yet")
        r = run_migrate(self.project, "--apply")
        self.assertEqual(r.returncode, 3, r.out)
        error = r.report["commit"]["error"]
        self.assertIn("too small to take its entry", error)
        self.assertIn("%d bytes" % len(seed.encode("utf-8")), error)


# --- PROJECT_LEARNINGS.md joins the move as a companion ---

LEARNINGS = "PROJECT_LEARNINGS.md"
LEARNINGS_DEST = "methodology/PROJECT_LEARNINGS.md"
LEARNINGS_TEXT = "# Project learnings\n\n| # | Learning |\n|---|---|\n" + "".join(
    "| %d | Row %d. %s |\n" % (i, i, "What this project learned, in a sentence. " * 6) for i in range(1, 25))
POINTER = "Project learnings are kept in `PROJECT_LEARNINGS.md`.\n"


class WithALearningsFile(Adopter):
    """An adopter that keeps a PROJECT_LEARNINGS.md of its own at the root, names it in CLAUDE.md, in the budget config
    and in a gate: the three places a real project was found pointing at it."""

    def config(self, name):
        """A config where this tree keeps it: under methodology/ once migrated, at the root before."""
        new = self.project / "methodology" / name
        return new if new.is_file() else self.project / name

    def give_the_project_a_learnings_file(self):
        p = self.project
        (p / LEARNINGS).write_text(LEARNINGS_TEXT, encoding="utf-8")
        claude = p / "CLAUDE.md"
        claude.write_text(claude.read_text(encoding="utf-8") + POINTER, encoding="utf-8")
        budget = self.config(".context-budget.json")
        text = budget.read_text(encoding="utf-8")
        marker = '"files": ['
        self.assertEqual(text.count(marker), 1)
        budget.write_text(text.replace(marker, marker + '\n    {"path": "PROJECT_LEARNINGS.md", "class": "read-mandated", "max_bytes": 60000},'),
                          encoding="utf-8")
        gates_file = self.config(".quality-gates.json")
        cfg = json.loads(gates_file.read_text(encoding="utf-8"))
        cfg["gates"].append({"name": "learnings-size", "direction": "max", "threshold": 60000,
                             "command": "wc -c < PROJECT_LEARNINGS.md", "why": "The file stays readable."})
        gates_file.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        self.commit("the project keeps learnings of its own")

    def migrate_then_give_the_file(self):
        """A tree the tool calls migrated, with the file still at the root: a real project's state."""
        r = run_migrate(self.project, "--apply")
        self.assertEqual(r.returncode, 0, r.out)
        self.give_the_project_a_learnings_file()


class TestTheCompanionRule(WithALearningsFile):
    """The file joins the move with no manifest entry. It is the project's own state, so tier 2's."""

    def setUp(self):
        super().setUp()
        self.give_the_project_a_learnings_file()

    def test_the_file_is_planned_as_one_tracked_companion_move(self):
        r = run_migrate(self.project)
        self.assertEqual(r.returncode, 0, r.out)
        move = next((m for m in r.report["moves"] if m["src"] == LEARNINGS), None)
        self.assertIsNotNone(move, "no move planned for %s" % LEARNINGS)
        self.assertEqual(move, {"src": LEARNINGS, "dest": LEARNINGS_DEST, "kind": "companion", "tracked": True})

    def test_a_project_without_the_file_is_planned_as_it_always_was(self):
        git(self.project, "rm", "-q", LEARNINGS)
        self.commit("no learnings file")
        r = run_migrate(self.project)
        self.assertNotIn("companion", {m["kind"] for m in r.report["moves"]})
        self.assertNotIn(LEARNINGS, [x["path"] for x in r.report["left_in_place"]])

    def test_tier_1_leaves_it_at_the_root_and_names_nothing_of_it(self):
        r = run_migrate(self.project, "--apply", "--tier", "1")
        self.assertEqual(r.returncode, 0, r.out)
        self.assertNotIn(LEARNINGS, [m["src"] for m in r.report["moves"]])
        self.assertTrue((self.project / LEARNINGS).is_file())
        self.assertFalse((self.project / LEARNINGS_DEST).exists())
        self.assertTrue((self.project / "CLAUDE.md").read_text(encoding="utf-8").endswith(POINTER), "a pointer to a file that did not move was rewritten")

    def test_tier_1_then_tier_2_reaches_the_same_tree_as_all_at_once(self):
        a, b = self.project, Path(self._td.name) / "second"
        shutil.copytree(a, b, symlinks=True)
        self.assertEqual(run_migrate(a, "--apply", "--tier", "1").returncode, 0)
        self.assertEqual(run_migrate(a, "--apply", "--tier", "2").returncode, 0)
        self.assertEqual(run_migrate(b, "--apply").returncode, 0)
        self.assertEqual(files_of(a), files_of(b))
        self.assertIn(LEARNINGS_DEST, files_of(a))
        for rel in sorted(files_of(a)):
            if not configs_rewritten_by_layer_3(Path(rel).name):
                self.assertEqual((a / rel).read_bytes(), (b / rel).read_bytes(), rel)

    def test_it_arrives_unedited_as_a_rename_at_100_percent_in_one_commit(self):
        before = git(self.project, "rev-parse", "HEAD").strip()
        r = run_migrate(self.project, "--apply")
        self.assertEqual(r.returncode, 0, r.out)
        self.assertEqual(git(self.project, "rev-list", "--count", before + "..HEAD").strip(), "1")
        self.assertFalse((self.project / LEARNINGS).exists())
        self.assertEqual((self.project / LEARNINGS_DEST).read_text(encoding="utf-8"), LEARNINGS_TEXT)
        self.assertEqual(name_status(self.project)[(LEARNINGS, LEARNINGS_DEST)], 100)
        self.assertEqual(git(self.project, "status", "--porcelain"), "")

    def test_the_claude_md_pointer_the_budget_path_and_the_gate_command_follow(self):
        r = run_migrate(self.project, "--apply")
        self.assertEqual(r.returncode, 0, r.out)
        self.assertTrue((self.project / "CLAUDE.md").read_text(encoding="utf-8").endswith(
            "Project learnings are kept in `methodology/PROJECT_LEARNINGS.md`.\n"))
        budget = json.loads((self.project / "methodology" / ".context-budget.json").read_text(encoding="utf-8"))
        self.assertIn(LEARNINGS_DEST, [f["path"] for f in budget["files"]])
        self.assertNotIn(LEARNINGS, [f["path"] for f in budget["files"]])
        gates = json.loads((self.project / "methodology" / ".quality-gates.json").read_text(encoding="utf-8"))
        self.assertEqual(gates["gates"][-1]["command"], "wc -c < methodology/PROJECT_LEARNINGS.md")

    def test_the_ledger_entry_counts_it_among_the_files_it_moved(self):
        r = run_migrate(self.project)
        self.assertIn("39 files", r.report["ledger_entry"]["text"])
        self.assertIn("Layout migration", r.report["ledger_entry"]["text"])

    def test_a_copy_already_under_methodology_is_a_destination_that_exists(self):
        (self.project / "methodology").mkdir()
        (self.project / LEARNINGS_DEST).write_text("# someone else's\n", encoding="utf-8")
        self.commit("a file where the companion would land")
        before = tree_state(self.project)
        r = run_migrate(self.project, "--apply")
        self.assertEqual(r.returncode, 1, r.out)
        found = next(x for x in r.report["refusals"] if x["code"] == "destination-exists")
        self.assertIn(LEARNINGS_DEST, found["paths"])
        self.assertEqual(tree_state(self.project), before)

    def test_the_text_of_a_refused_run_is_printed_and_does_not_fail(self):
        (self.project / "scratch.txt").write_text("x\n", encoding="utf-8")
        r = run_migrate(self.project, json_out=False)
        self.assertEqual(r.returncode, 1, r.out)
        self.assertIn("REFUSED", r.out)
        self.assertNotIn("Traceback", r.out)

    def test_a_copy_git_does_not_track_stays_and_is_named(self):
        git(self.project, "rm", "-q", "--cached", LEARNINGS)
        gi = self.project / ".gitignore"
        gi.write_text(gi.read_text(encoding="utf-8") + "PROJECT_LEARNINGS.md\n", encoding="utf-8")
        self.commit("the file is kept out of git")
        r = run_migrate(self.project, "--apply")
        self.assertEqual(r.returncode, 0, r.out)
        self.assertNotIn(LEARNINGS, [m["src"] for m in r.report["moves"]])
        left = {x["path"]: x["reason"] for x in r.report["left_in_place"]}
        self.assertIn(LEARNINGS, left)
        self.assertIn("not tracked", left[LEARNINGS])
        self.assertTrue((self.project / LEARNINGS).is_file())
        self.assertTrue((self.project / "CLAUDE.md").read_text(encoding="utf-8").endswith(POINTER))

    def test_the_text_a_person_reads_prints_the_git_mv(self):
        r = run_migrate(self.project, json_out=False)
        self.assertIn("git mv PROJECT_LEARNINGS.md methodology/PROJECT_LEARNINGS.md", r.out)


class TestATopUpOnAMigratedTree(WithALearningsFile):
    """A tree the tool calls migrated has the file still at the root (the state of three real projects);
    before the top-up existed the tool said `nothing to migrate`. The configs are under
    methodology/ there, and the rewrite reads them where the layout puts them."""

    def setUp(self):
        super().setUp()
        self.migrate_then_give_the_file()

    def test_the_plan_is_the_companion_move_alone_and_the_status_is_ok(self):
        r = run_migrate(self.project)
        self.assertEqual(r.returncode, 0, r.out)
        self.assertEqual(r.report["layout"], "new")
        self.assertEqual(r.report["status"], "ok")
        self.assertEqual(r.report["moves"], [{"src": LEARNINGS, "dest": LEARNINGS_DEST, "kind": "companion", "tracked": True}])

    def test_the_configs_are_read_under_methodology_where_the_layout_puts_them(self):
        r = run_migrate(self.project)
        got = {x["path"]: (x["final"], x["replacements"]) for x in r.report["rewrites"]}
        self.assertEqual(got["methodology/.context-budget.json"], ("methodology/.context-budget.json", 1))
        self.assertEqual(got["methodology/.quality-gates.json"], ("methodology/.quality-gates.json", 1))
        self.assertEqual(got["CLAUDE.md"], ("CLAUDE.md", 1))
        self.assertNotIn(".context-budget.json", got, "a config was looked for at the root of a migrated tree")

    def test_a_dry_run_writes_nothing(self):
        before = tree_state(self.project)
        run_migrate(self.project)
        self.assertEqual(tree_state(self.project), before)

    def test_the_apply_is_one_commit_a_rename_at_100_percent_and_the_paths_follow(self):
        before = git(self.project, "rev-parse", "HEAD").strip()
        r = run_migrate(self.project, "--apply")
        self.assertEqual(r.returncode, 0, r.out)
        self.assertEqual(r.report["status"], "applied")
        self.assertEqual(git(self.project, "rev-list", "--count", before + "..HEAD").strip(), "1")
        self.assertEqual(name_status(self.project)[(LEARNINGS, LEARNINGS_DEST)], 100)
        self.assertEqual((self.project / LEARNINGS_DEST).read_text(encoding="utf-8"), LEARNINGS_TEXT)
        self.assertTrue((self.project / "CLAUDE.md").read_text(encoding="utf-8").endswith(
            "Project learnings are kept in `methodology/PROJECT_LEARNINGS.md`.\n"))
        budget = json.loads((self.project / "methodology" / ".context-budget.json").read_text(encoding="utf-8"))
        self.assertIn(LEARNINGS_DEST, [f["path"] for f in budget["files"]])
        gates = json.loads((self.project / "methodology" / ".quality-gates.json").read_text(encoding="utf-8"))
        self.assertEqual(gates["gates"][-1]["command"], "wc -c < methodology/PROJECT_LEARNINGS.md")
        self.assertEqual(git(self.project, "status", "--porcelain"), "")

    def test_the_commit_says_it_is_a_top_up_and_names_the_file(self):
        r = run_migrate(self.project, "--apply", "--trailer", "Co-Authored-By: A Tester <a@example.com>")
        message = git(self.project, "log", "-1", "--format=%B")
        subject = message.splitlines()[0]
        self.assertIn("PROJECT_LEARNINGS.md", subject)
        self.assertIn("(top-up, tier all, 1 file)", subject)
        self.assertNotIn("the methodology files", subject)
        self.assertIn("1 file(s) with git mv", message)
        self.assertIn("Co-Authored-By: A Tester <a@example.com>", message)

    def test_one_ledger_entry_is_added_where_the_ledger_is_and_no_older_line_changes(self):
        ledger = self.project / "methodology" / "CHANGELOG.md"
        before = ledger.read_text(encoding="utf-8")
        r = run_migrate(self.project, "--apply")
        self.assertEqual(r.returncode, 0, r.out)
        after = ledger.read_text(encoding="utf-8")
        self.assertEqual(entry_split(after)[1:], entry_split(before))
        self.assertRegex(entry_split(after)[0], r"^\d{4}-\d{2}-\d{2} · \[ad hoc\] Layout top-up: ")
        text = r.report["ledger_entry"]["text"]
        self.assertEqual(r.report["ledger_entry"]["path"], "methodology/CHANGELOG.md")
        self.assertIn("(tier all, 1 file)", text)
        self.assertIn("`PROJECT_LEARNINGS.md`", text)
        self.assertIn("`bin/migrate-layout`", text)
        for path in ("CLAUDE.md", "methodology/.context-budget.json", "methodology/.quality-gates.json"):
            self.assertIn("`%s`" % path, text)
        diff = git(self.project, "diff", "HEAD~1", "HEAD", "--", "methodology/CHANGELOG.md")
        self.assertEqual([l for l in diff.splitlines() if l.startswith("-") and not l.startswith("---")], [])
        check = subprocess.run([sys.executable, "-B", str(REPO / "bin" / "check-ledger"), "--file", "methodology/CHANGELOG.md"],
                               cwd=self.project, capture_output=True, text=True)
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

    def test_a_top_up_rewrites_the_names_of_the_companion_and_nothing_else(self):
        """In a migrated tree the generated files are under methodology/ already: a bare mention of one in CLAUDE.md is
        not a name the top-up moves."""
        claude = self.project / "CLAUDE.md"
        claude.write_text(claude.read_text(encoding="utf-8") + "The page is dashboard.html; the results are in .quality-gates-results.json.\n", encoding="utf-8")
        self.commit("a bare mention of two generated files")
        r = run_migrate(self.project)
        rw = next(x for x in r.report["rewrites"] if x["path"] == "CLAUDE.md")
        self.assertEqual(rw["replacements"], 1, rw["diff"])
        added = [l for l in rw["diff"].splitlines() if l.startswith("+") and not l.startswith("+++")]
        self.assertEqual(len(added), 1, added)
        self.assertNotIn("dashboard.html", added[0])

    def test_a_second_run_finds_nothing_to_do_and_adds_no_commit(self):
        run_migrate(self.project, "--apply")
        head = git(self.project, "rev-parse", "HEAD").strip()
        r = run_migrate(self.project, "--apply")
        self.assertEqual(r.returncode, 0, r.out)
        self.assertEqual(r.report["status"], "nothing-to-do")
        self.assertEqual(git(self.project, "rev-parse", "HEAD").strip(), head)

    def test_tier_1_has_nothing_to_do_on_a_migrated_tree_with_the_file_at_the_root(self):
        r = run_migrate(self.project, "--apply", "--tier", "1")
        self.assertEqual(r.report["status"], "nothing-to-do")
        self.assertTrue((self.project / LEARNINGS).is_file())

    def test_a_dirty_tree_is_refused_as_it_is_for_any_migration(self):
        (self.project / "scratch.txt").write_text("x\n", encoding="utf-8")
        r = run_migrate(self.project, "--apply")
        self.assertEqual(r.returncode, 1, r.out)
        self.assertIn("dirty-tree", [x["code"] for x in r.report["refusals"]])

    def test_a_copy_already_under_methodology_is_refused_and_named(self):
        (self.project / LEARNINGS_DEST).write_text("# someone else's\n", encoding="utf-8")
        self.commit("a file where the companion would land")
        r = run_migrate(self.project, "--apply")
        self.assertEqual(r.returncode, 1, r.out)
        found = next(x for x in r.report["refusals"] if x["code"] == "destination-exists")
        self.assertEqual(found["paths"], [LEARNINGS_DEST])

    def test_the_checks_run_before_and_after_and_agree(self):
        r = run_migrate(self.project, "--apply", checks=True)
        self.assertEqual(r.returncode, 0, r.out)
        self.assertTrue(r.report["checks"]["ran"])
        self.assertEqual(r.report["checks"]["differences"], [], r.out)
        self.assertTrue(r.report["checks"]["ok"])

    def test_the_text_a_person_reads_does_not_say_nothing_to_migrate(self):
        r = run_migrate(self.project, json_out=False)
        self.assertNotIn("nothing to migrate", r.out)
        self.assertIn("git mv PROJECT_LEARNINGS.md methodology/PROJECT_LEARNINGS.md", r.out)

    def test_a_migrated_tree_with_no_file_at_the_root_still_has_nothing_to_do(self):
        git(self.project, "rm", "-q", LEARNINGS)
        self.commit("no learnings file")
        r = run_migrate(self.project)
        self.assertEqual(r.report["status"], "nothing-to-do")


class TestTheLinkRules(unittest.TestCase):
    """The links a move breaks are read as the pure rules say, before any project is involved."""

    @classmethod
    def setUpClass(cls):
        cls.m = _load_script("migrate_layout", MIGRATE)

    def test_inline_image_and_reference_links_are_read_and_a_fenced_example_is_not(self):
        text = ("[a](x.md) and ![img](p/y.png \"t\") and [b](<z w.md>) and [sp]( s.md )\n"
                "[ref]: u.md \"title\"\n"
                "```\n[no](f.md)\n```\n"
                "~~~\n[no](g.md)\n~~~\n"
                "[c](h_(1).md#top)\n")
        self.assertEqual(self.m.link_targets(text), [(1, "x.md"), (1, "p/y.png"), (1, "z w.md"), (1, "s.md"), (2, "u.md"), (9, "h_(1).md#top")])

    def test_a_fence_that_never_closes_hides_the_rest_and_a_longer_fence_closes_only_on_its_own_length(self):
        self.assertEqual(self.m.link_targets("[a](a.md)\n```\n[b](b.md)\n"), [(1, "a.md")])
        self.assertEqual(self.m.link_targets("````\n```\n[b](b.md)\n```\n````\n[c](c.md)\n"), [(6, "c.md")])

    def test_a_target_is_resolved_against_the_directory_of_the_document_that_holds_it(self):
        want = {("docs/g.md", "../PROJECT_LEARNINGS.md#row-3"): "PROJECT_LEARNINGS.md",
                ("README.md", "./PROJECT_LEARNINGS.md"): "PROJECT_LEARNINGS.md",
                ("docs/g.md", "/PROJECT_LEARNINGS.md"): "PROJECT_LEARNINGS.md",
                ("docs/g.md", "a%20b.md?raw=1"): "docs/a b.md",
                ("a/b/c.md", "../../d.md"): "d.md",
                ("docs/g.md", "PROJECT_LEARNINGS.md"): "docs/PROJECT_LEARNINGS.md"}
        for (doc, target), resolved in want.items():
            self.assertEqual(self.m.resolve_link(doc, target), resolved, (doc, target))

    def test_what_is_not_a_path_in_the_project_resolves_to_nothing(self):
        for doc, target in (("docs/g.md", "https://example.org/PROJECT_LEARNINGS.md"), ("docs/g.md", "mailto:a@b.org"),
                            ("docs/g.md", "//cdn.example.org/x.md"), ("docs/g.md", "#top"), ("docs/g.md", ""),
                            ("docs/g.md", "../../x.md"), ("README.md", "../x.md")):
            self.assertIsNone(self.m.resolve_link(doc, target), (doc, target))


DOC = ("# Guide\n"                                                                                                  # 1
       "\n"                                                                                                         # 2
       "The file is [here](../PROJECT_LEARNINGS.md) and [row 3](../PROJECT_LEARNINGS.md#row-3 \"a title\").\n"      # 3
       "The method is [explained](methodology/HOW_TO_USE.md).\n"                                                    # 4
       "\n"                                                                                                         # 5
       "```\n"                                                                                                      # 6
       "[an example](../PROJECT_LEARNINGS.md)\n"                                                                    # 7
       "```\n"                                                                                                      # 8
       "\n"                                                                                                         # 9
       "Not the project's file: [site](https://example.org/PROJECT_LEARNINGS.md), [a sibling](PROJECT_LEARNINGS.md)"  # 10
       " and [other](other.md).\n"
       "\n"                                                                                                         # 11
       "[ref]: ../PROJECT_LEARNINGS.md\n")                                                                          # 12


class TestTheLiveLinksAMoveBreaks(WithALearningsFile):
    """A link from a project's live document to a file the move takes breaks and
    nothing read it: the tool lists each one, every one, and rewrites none."""

    def setUp(self):
        super().setUp()
        self.give_the_project_a_learnings_file()
        (self.project / "docs" / "guide.md").write_text(DOC, encoding="utf-8")
        (self.project / "README.md").write_text("The learnings: [PROJECT_LEARNINGS.md](PROJECT_LEARNINGS.md).\n", encoding="utf-8")
        (self.project / "docs" / "notes.md").write_text("Prose names PROJECT_LEARNINGS.md; the link is to [a sibling](PROJECT_LEARNINGS.md).\n", encoding="utf-8")
        shard = self.project / "docs" / "archive" / "HANDOFFS-through-2026-08-02.md"
        shard.write_text("# shard\n\nSee [the learnings](../../PROJECT_LEARNINGS.md) and [the guide](../methodology/HOW_TO_USE.md).\n", encoding="utf-8")
        self.commit("live documents that link to the files a move takes")

    def sites(self, report):
        return sorted((s["file"], s["line"], s["target"], s["resolves_to"], s["moves_to"]) for s in report["live_links"]["sites"])

    def test_every_live_link_to_a_moved_file_is_listed_with_where_it_goes(self):
        r = run_migrate(self.project)
        self.assertEqual(r.returncode, 0, r.out)
        self.assertEqual(self.sites(r.report), sorted([
            ("README.md", 1, "PROJECT_LEARNINGS.md", LEARNINGS, LEARNINGS_DEST),
            ("docs/guide.md", 3, "../PROJECT_LEARNINGS.md", LEARNINGS, LEARNINGS_DEST),
            ("docs/guide.md", 3, "../PROJECT_LEARNINGS.md#row-3", LEARNINGS, LEARNINGS_DEST),
            ("docs/guide.md", 4, "methodology/HOW_TO_USE.md", "docs/methodology/HOW_TO_USE.md", "methodology/HOW_TO_USE.md"),
            ("docs/guide.md", 12, "../PROJECT_LEARNINGS.md", LEARNINGS, LEARNINGS_DEST)]))
        self.assertEqual((r.report["live_links"]["count"], r.report["live_links"]["files"]), (5, 2))
        texts = {(s["file"], s["line"]): s["text"] for s in r.report["live_links"]["sites"]}
        self.assertIn("[explained](methodology/HOW_TO_USE.md)", texts[("docs/guide.md", 4)])
        self.assertEqual(texts[("README.md", 1)], "The learnings: [PROJECT_LEARNINGS.md](PROJECT_LEARNINGS.md).")

    def test_a_link_in_a_fence_an_external_link_a_sibling_a_ledger_a_shard_a_rewritten_file_and_a_moved_document_are_not_listed(self):
        r = run_migrate(self.project)
        listed = {(s["file"], s["line"]) for s in r.report["live_links"]["sites"]}
        self.assertNotIn(("docs/guide.md", 7), listed, "a link in a fenced example was listed")
        self.assertNotIn(("docs/guide.md", 10), listed, "an external link, a sibling or an unmoved file was listed")
        self.assertFalse([f for f, _l in listed if f in ("CHANGELOG.md", "CLAUDE.md") or f.startswith("docs/archive/")], listed)
        self.assertFalse([f for f, _l in listed if f.startswith("docs/methodology/") or f in {m["src"] for m in r.report["moves"]}], listed)

    def test_a_ledger_and_a_shard_that_stay_where_they_are_are_not_listed_either(self):
        """Tier 1 moves the framework's documents and leaves the ledger and the shards at the root: a link in one of them
        to a moved document is a committed entry's, counted with the ledger's and never listed."""
        r = run_migrate(self.project, "--tier", "1")
        self.assertEqual(r.returncode, 0, r.out)
        listed = {s["file"] for s in r.report["live_links"]["sites"]}
        self.assertEqual(listed, {"docs/guide.md"}, "a ledger, a shard or a moved document was listed")
        self.assertEqual({s["target"] for s in r.report["live_links"]["sites"]}, {"methodology/HOW_TO_USE.md"})
        self.assertGreater(r.report["not_rewritten"]["ledger"]["mentions"], 0)

    def test_the_apply_lists_the_links_and_edits_none_of_them(self):
        before = {rel: (self.project / rel).read_bytes() for rel in ("docs/guide.md", "README.md",
                                                                     "docs/archive/HANDOFFS-through-2026-08-02.md")}
        r = run_migrate(self.project, "--apply")
        self.assertEqual(r.returncode, 0, r.out)
        self.assertEqual(r.report["live_links"]["count"], 5)
        for rel, data in before.items():
            moved = ("methodology/archive/" + rel.rsplit("/", 1)[-1]) if rel.startswith("docs/archive/") else rel
            self.assertEqual((self.project / moved).read_bytes(), data, "%s was edited" % rel)

    def test_the_text_a_person_reads_names_each_link_where_it_is(self):
        r = run_migrate(self.project, json_out=False)
        self.assertRegex(r.out, r"(?i)live links")
        self.assertIn("docs/guide.md:3", r.out)
        self.assertIn("docs/guide.md:4", r.out)
        self.assertIn("README.md:1", r.out)
        self.assertIn("methodology/PROJECT_LEARNINGS.md", r.out)

    def test_a_project_with_no_such_link_has_an_empty_list(self):
        git(self.project, "rm", "-q", "docs/guide.md")
        (self.project / "README.md").write_text("No links here.\n", encoding="utf-8")
        self.commit("no live links")
        r = run_migrate(self.project, json_out=True)
        self.assertEqual(r.report["live_links"], {"count": 0, "files": 0, "sites": []})
        self.assertNotRegex(run_migrate(self.project, json_out=False).out, r"(?i)live links")

    def test_every_link_is_in_the_json_and_the_text_shows_the_first_25_and_says_how_many_more(self):
        many = "".join("Item %d: [x](../PROJECT_LEARNINGS.md#row-%d)\n" % (i, i) for i in range(1, 31))
        (self.project / "docs" / "many.md").write_text(many, encoding="utf-8")
        self.commit("thirty links")
        r = run_migrate(self.project)
        self.assertEqual(r.report["live_links"]["count"], 5 + 30)
        self.assertEqual(sum(1 for s in r.report["live_links"]["sites"] if s["file"] == "docs/many.md"), 30)
        lines = run_migrate(self.project, json_out=False).out.splitlines()
        head = next(i for i, l in enumerate(lines) if re.search(r"(?i)live links", l))
        section = []
        for l in lines[head + 1:]:
            if not l.strip():
                break
            section.append(l)
        self.assertEqual(len([l for l in section if re.match(r"^\s+\S+:\d+  ", l)]), 25)
        self.assertTrue(any("and 10 more" in l and "--json" in l for l in section), section)

    def test_exactly_25_links_are_all_shown_and_the_text_does_not_say_there_are_more(self):
        many = "".join("Item %d: [x](../PROJECT_LEARNINGS.md#row-%d)\n" % (i, i) for i in range(1, 21))
        (self.project / "docs" / "many.md").write_text(many, encoding="utf-8")
        self.commit("twenty links")
        self.assertEqual(run_migrate(self.project).report["live_links"]["count"], 25)
        text = run_migrate(self.project, json_out=False).out
        self.assertNotRegex(text, r"and \d+ more \(every one")

    def test_a_second_run_after_the_move_has_nothing_to_do_and_an_empty_list(self):
        run_migrate(self.project, "--apply")
        r = run_migrate(self.project)
        self.assertEqual(r.report["status"], "nothing-to-do")
        self.assertEqual(r.report["live_links"], {"count": 0, "files": 0, "sites": []})


class TestTheCompanionOfAProjectThatHasNotAdoptedTheMethodology(unittest.TestCase):
    """A file named PROJECT_LEARNINGS.md in a repository with no methodology file is the project's, and there is no
    methodology/ for it to join: the tool leaves it where it is, as it leaves the rest of such a project."""

    def test_the_file_stays_and_there_is_nothing_to_do(self):
        with tempfile.TemporaryDirectory(prefix="migrate-bare-") as td:
            project = Path(td) / "bare"
            project.mkdir()
            git(project, "init", "-q")
            (project / LEARNINGS).write_text(LEARNINGS_TEXT, encoding="utf-8")
            commit_all(project, "a project with a learnings file and no methodology")
            before = tree_state(project)
            r = run_migrate(project, "--apply")
            self.assertEqual(r.returncode, 0, r.out)
            self.assertEqual(r.report["status"], "nothing-to-do")
            self.assertEqual(r.report["moves"], [])
            self.assertEqual(tree_state(project), before)
            text = run_migrate(project, "--apply", json_out=False)
            self.assertEqual(text.returncode, 0, text.out)
            self.assertIn("nothing to migrate", text.out)


if __name__ == "__main__":
    unittest.main()
