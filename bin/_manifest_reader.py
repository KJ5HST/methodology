"""Read a methodology repository's bin/_manifest.py as data, never by running it.

In github mode, bin/sync and bin/status iterate the SOURCE's own manifest, so the file list and
the file contents come from one ref (parallel-sessions plan, D8). That manifest sits in the clone,
so it is parsed here, not imported: nothing from the clone runs during a sync or a status run
(rmsharp's review of PR #91). _manifest.py promises to be a data-only module, which is what makes
this possible -- its rows are literals and its two disposition names are module-level strings.
Statements other than those assignments are never executed, only skipped.

Every row is checked before either script acts on any of them. A disposition this checkout does
not know is refused: bin/sync tests `disp == SEED` against its own constant, so a source whose
seed label differed had its seeds written like tracked files, past the check that stops sync
overwriting an adopter's own copy. A src or dest that is absolute, carries a drive, or climbs
with '..' is refused too: the source's manifest now decides where files are read and written.

Python 3 stdlib only.
"""
import ast
from pathlib import Path, PureWindowsPath


class ManifestError(Exception):
    """The manifest cannot be read, or names rows this checkout cannot act on safely."""


def _contained(path: str) -> bool:
    """True when path stays inside the tree it is joined to. PureWindowsPath splits on both
    separators and sees drives and roots, so one test covers POSIX and Windows spellings."""
    parsed = PureWindowsPath(path)
    return bool(path) and not parsed.drive and not parsed.root and ".." not in parsed.parts


def _literal(node: ast.expr, strings: dict):
    """node as a literal, with names bound to module-level strings (TRACKED, SEED) resolved."""
    class Resolve(ast.NodeTransformer):
        def visit_Name(self, name: ast.Name) -> ast.Constant:
            if name.id not in strings:
                raise ManifestError(f"uses {name.id!r} (line {name.lineno}), which is not a "
                                    f"module-level string")
            return ast.copy_location(ast.Constant(strings[name.id]), name)
    try:
        return ast.literal_eval(Resolve().visit(node))
    except (ValueError, TypeError, SyntaxError, RecursionError) as e:
        raise ManifestError(f"is not literal data (line {node.lineno}): {e}") from None


def read_manifest(path: Path, dispositions: tuple) -> tuple:
    """(rows, seed_format_markers) from the manifest at path, read as data.

    rows is its DISTRIBUTION list of (src, dest, disposition); seed_format_markers is its
    SEED_FORMAT_MARKERS dict, or None when it defines none. dispositions are the labels the
    calling checkout acts on -- its own TRACKED and SEED. Raises ManifestError, whose message
    completes the sentence "the bin/_manifest.py in <source> ...", naming every row refused."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as e:
        raise ManifestError(f"cannot be read: {e.msg} (line {e.lineno})") from None
    except (OSError, UnicodeDecodeError, ValueError) as e:
        raise ManifestError(f"cannot be read: {e}") from None
    assigned = {node.targets[0].id: node.value for node in tree.body
                if isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)}
    strings = {name: value.value for name, value in assigned.items()
               if isinstance(value, ast.Constant) and isinstance(value.value, str)}
    if "DISTRIBUTION" not in assigned:
        raise ManifestError("defines no DISTRIBUTION list")
    rows = _literal(assigned["DISTRIBUTION"], strings)
    if not (isinstance(rows, list) and all(
            isinstance(row, tuple) and len(row) == 3 and all(isinstance(f, str) for f in row)
            for row in rows)):
        raise ManifestError("has a DISTRIBUTION that is not a list of (src, dest, disposition) "
                            "string rows")
    markers = None
    if "SEED_FORMAT_MARKERS" in assigned:
        markers = _literal(assigned["SEED_FORMAT_MARKERS"], strings)
        if not (isinstance(markers, dict)
                and all(isinstance(k, str) and isinstance(v, str) for k, v in markers.items())):
            raise ManifestError("has a SEED_FORMAT_MARKERS that is not a dict of strings")

    known = " or ".join(repr(d) for d in dispositions)
    refused = []
    for src, dest, disp in rows:
        why = []
        if disp not in dispositions:
            why.append(f"disposition {disp!r} is not one this checkout knows ({known})")
        if not _contained(src):
            why.append(f"src {src!r} is not a path inside the source")
        if not _contained(dest):
            why.append(f"dest {dest!r} is not a path inside the project")
        if why:
            refused.append(f"    {src} -> {dest}: " + "; ".join(why))
    if refused:
        raise ManifestError(f"has {len(refused)} of {len(rows)} row(s) this checkout cannot act "
                            f"on safely:\n" + "\n".join(refused))
    return rows, markers
