#!/usr/bin/env python3
"""The layout resolver: where do a project's methodology files live? (BL-101, phase P1.)

CANONICAL-ONLY reference copy. Contract: docs/planning/methodology-subdirectory-plan.md
section 4.3. A project keeps its methodology files either at its root (legacy) or one level
down in methodology/ (new). The answer is read from one anchor file, by the four-row table:

    R/methodology/<anchor>   R/<anchor>   kind      directory
    exists                   absent       new       R/methodology
    absent                   exists       legacy    R
    exists                   exists       half      None  -- stop, name both, never guess
    absent                   absent       none      None  -- the framework repo, or not an adopter

A fifth row, no request needed (decided 2026-10-06 for the ledger, 2026-10-07 for every file, plan
7.2a and 7.2b): a file found in BOTH places is the framework's under methodology/ when the runner is under
methodology/ and not at the root. The root copy is the project's own (a product CHANGELOG.md, a manifest of
its own) and the methodology tools leave it alone. The resolver takes no argument for the rule, so a tool
cannot forget to ask: the S276 build made it a request, and that is what he overruled. A tie the runner does
not decide (no runner under methodology/, a runner at the root, or at both) is still half, and the runner
cannot decide a tie about itself.

The anchor is the caller's choice, because a project can be part-way: the plan's tier 1 moves the
framework files (SESSION_RUNNER.md and the rest) and leaves the state files (CHANGELOG.md,
HANDOFFS.md, the two JSON configs) at the root until tier 2. A tool that reads a framework file
resolves with the default anchor; a tool that reads the ledger resolves with "CHANGELOG.md".
Resolving the ledger through the runner would point the ledger hook at a file that is not there,
which is the failure the plan's C5 measured: a gate that passes silently.

Shipped tools are single stdlib files adopters receive one by one, so none can import this module.
Each carries the marked block below, byte for byte, and its suite asserts that with
``embedded_block`` (the dashboard's twin test is the precedent). Everything between the markers
must run alone, importing only the standard library. This file is not in bin/_manifest.py.
"""

# --- layout resolver: BEGIN ---
import os as _os
from pathlib import Path as _Path


def resolve_layout(root, anchor="SESSION_RUNNER.md"):
    """Return (kind, directory, found): kind is new|legacy|half|none, directory a Path or None,
    found the anchor paths that exist. A half-migrated tree has no directory, by design.
    A file found in both places is the framework's under methodology/ when the runner is under
    methodology/ and not at the root: the root copy is the project's own and is left alone, kind new,
    and found still names both. Any other tie stays half, and the runner cannot decide a tie about itself."""
    root = _Path(root)
    new, old = root / "methodology" / anchor, root / anchor
    found = tuple(p for p in (new, old) if _os.path.isfile(p))
    if len(found) == 2:
        if _os.path.isfile(root / "methodology" / "SESSION_RUNNER.md") and not _os.path.isfile(root / "SESSION_RUNNER.md"):
            return "new", new.parent, found
        return "half", None, found
    if not found:
        return "none", None, ()
    return ("new", new.parent, found) if found[0] == new else ("legacy", root, found)
# --- layout resolver: END ---

# Built in two pieces so the marker text occurs once in this file, as the comment above and below
# the block; embedded_block counts occurrences, and a second one here would make it refuse this file.
BEGIN = "# --- layout resolver: " + "BEGIN ---"
END = "# --- layout resolver: " + "END ---"


def embedded_block(text):
    """The marked block inside ``text`` (this module's source, or a tool that embeds a copy), from
    its BEGIN line through its END line inclusive, or None when ``text`` carries no markers.
    Unbalanced or repeated markers raise ValueError: a copy that cannot be compared is a defect."""
    if text.count(BEGIN) != text.count(END) or text.count(BEGIN) > 1:
        raise ValueError("the layout-resolver markers are unbalanced or repeated")
    if not text.count(BEGIN):
        return None
    start = text.index(BEGIN)
    end = text.index(END, start)
    if end < start:
        raise ValueError("the layout-resolver END marker precedes its BEGIN")
    return text[start:end + len(END)] + "\n"
