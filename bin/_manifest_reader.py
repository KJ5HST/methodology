"""Read a methodology repository's bin/_manifest.py as data, never by running it.

In github mode, bin/sync and bin/status iterate the SOURCE's own manifest, so the file list and
the file contents come from one ref (parallel-sessions plan, D8). That manifest sits in the clone,
so it is parsed here, not imported: nothing from the clone runs during a sync or a status run
(rmsharp's review of PR #91). _manifest.py promises to be a data-only module, which is what makes
this possible -- its rows are literals and its two disposition names are module-level strings.
Statements other than those assignments are never executed, only skipped. That makes one more
rule necessary: every name the reader uses is bound once, by one plain assignment, and never
changed. A manifest that adds to DISTRIBUTION later (`+=`, `.append(...)`, a second assignment) is
refused, because reading only its first binding would drop or swap rows without a word.

Every row is checked before either script acts on any of them. A disposition this checkout does
not know is refused: bin/sync tests `disp == SEED` against its own constant, so a source whose
seed label differed had its seeds written like tracked files, past the check that stops sync
overwriting an adopter's own copy. A src or dest that is absolute, carries a drive, climbs with
'..', names no file ('.'), lies inside .git, or holds a NUL byte is refused too: the source's
manifest now decides where files are read and written, and a write into .git/hooks would run.

Python 3 stdlib only.
"""
import ast
from pathlib import Path, PureWindowsPath


class ManifestError(Exception):
    """The manifest cannot be read, or names rows this checkout cannot act on safely."""


def _path_problem(path: str) -> str:
    """Why path cannot be joined to a tree safely, or "" when it can. PureWindowsPath splits on
    both separators and sees drives and roots, so one test covers POSIX and Windows spellings;
    .git is matched in any case, as a case-insensitive filesystem would."""
    if "\x00" in path:
        return "holds a NUL byte"
    parsed = PureWindowsPath(path)
    if parsed.drive or parsed.root:
        return "is absolute"
    if ".." in parsed.parts:
        return "climbs out with '..'"
    if not parsed.parts:
        return "names no file"
    if any(part.lower() == ".git" for part in parsed.parts):
        return "is inside .git"
    return ""


def _bindings(tree: ast.Module, name: str) -> list:
    """Every line that binds, deletes or changes `name`: assignment targets of any kind (=, +=, :=,
    annotated, for, with, del), item or slice assignment, any attribute use such as .append(...),
    an import, and a def or class. A manifest that is data has exactly one: its plain assignment."""
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == name and isinstance(node.ctx, (ast.Store, ast.Del)):
            lines.append(node.lineno)
        elif (isinstance(node, (ast.Attribute, ast.Subscript)) and isinstance(node.value, ast.Name)
              and node.value.id == name
              and (isinstance(node, ast.Attribute) or isinstance(node.ctx, (ast.Store, ast.Del)))):
            lines.append(node.lineno)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            lines.extend(node.lineno for alias in node.names
                         if (alias.asname or alias.name.split(".")[0]) == name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == name:
            lines.append(node.lineno)
    return sorted(lines)


def _bound_once(tree: ast.Module, name: str) -> None:
    lines = _bindings(tree, name)
    if len(lines) > 1:
        raise ManifestError(f"binds or changes {name} more than once (lines "
                            f"{', '.join(map(str, lines))}): only its one plain assignment is read, "
                            f"so the rest would be skipped without a word")


def _literal(node: ast.expr, strings: dict, used: set):
    """node as a literal, with names bound to module-level strings (TRACKED, SEED) resolved; the
    names resolved are added to used."""
    class Resolve(ast.NodeTransformer):
        def visit_Name(self, name: ast.Name) -> ast.Constant:
            if name.id not in strings:
                raise ManifestError(f"uses {name.id!r} (line {name.lineno}), which is not a "
                                    f"module-level string")
            used.add(name.id)
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
    _bound_once(tree, "DISTRIBUTION")
    used = set()
    rows = _literal(assigned["DISTRIBUTION"], strings, used)
    if not (isinstance(rows, list) and all(
            isinstance(row, tuple) and len(row) == 3 and all(isinstance(f, str) for f in row)
            for row in rows)):
        raise ManifestError("has a DISTRIBUTION that is not a list of (src, dest, disposition) "
                            "string rows")
    markers = None
    if "SEED_FORMAT_MARKERS" in assigned:
        _bound_once(tree, "SEED_FORMAT_MARKERS")
        markers = _literal(assigned["SEED_FORMAT_MARKERS"], strings, used)
        if not (isinstance(markers, dict)
                and all(isinstance(k, str) and isinstance(v, str) for k, v in markers.items())):
            raise ManifestError("has a SEED_FORMAT_MARKERS that is not a dict of strings")
    for name in sorted(used):
        _bound_once(tree, name)

    known = " or ".join(repr(d) for d in dispositions)
    refused = []
    for src, dest, disp in rows:
        why = []
        if disp not in dispositions:
            why.append(f"disposition {disp!r} is not one this checkout knows ({known})")
        for role, value in (("src", src), ("dest", dest)):
            problem = _path_problem(value)
            if problem:
                why.append(f"{role} {value!r} {problem}")
        if why:
            refused.append(f"    {src!r} -> {dest!r}: " + "; ".join(why))
    if refused:
        raise ManifestError(f"has {len(refused)} of {len(rows)} row(s) this checkout cannot act "
                            f"on safely:\n" + "\n".join(refused))
    return rows, markers
