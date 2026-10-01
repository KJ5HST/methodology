"""Distribution manifest — the single source of truth for what the methodology
ships into an adopter project, where each file lands, and how sync treats it.

Imported by bin/sync, bin/status, and bin/check-links so the mapping is defined
exactly once (B1 plan Decision 5; Ousterhout deepening — the three scripts
previously each carried their own copy of the file list).

Each entry is ``(src, dest, disposition)``:
  * ``src``         path relative to the canonical methodology repo root.
  * ``dest``        path relative to the ADOPTER project root (README Option B
                    layout: starter-kit root-files at the project root, the
                    framework under docs/methodology/). Cross-references inside
                    distributed files are authored for this layout — see
                    bin/check-links and B1 plan section 4 ("link-topology paradox").
  * ``disposition`` how sync reconciles the dest (see below).

Dispositions:
  TRACKED  canonical owns it; sync keeps it current and the existing
           drift / --force / upgrade machinery applies. Overwrites toward
           canonical (never silently clobbering unrecognized local edits).
  SEED     adopter owns it after first creation; sync writes it ONLY when the
           dest is absent and never overwrites it afterward (B1 plan Decision 2a).

Adopter-owned *instances* (CONTEXT.md, CLAUDE.md, BACKLOG.md, …) are deliberately
NOT listed: the template ships under a different name (CONTEXT_TEMPLATE.md →
TRACKED), and the instance simply never appears as a dest, so it can never be a
sync target — no special-case guard needed (B1 plan Decision 2).

Python 3 stdlib only; data-only module (no imports, no side effects).
"""

TRACKED = "tracked"
SEED = "seed"

DISTRIBUTION = [
    # starter-kit root-files -> adopter project root
    ("starter-kit/SESSION_RUNNER.md", "SESSION_RUNNER.md", TRACKED),
    ("starter-kit/FRAMEWORK_LEARNINGS.md", "FRAMEWORK_LEARNINGS.md", TRACKED),
    ("starter-kit/SAFEGUARDS.md", "SAFEGUARDS.md", TRACKED),
    ("starter-kit/RECOMMENDED_SKILLS.md", "RECOMMENDED_SKILLS.md", TRACKED),
    ("starter-kit/CONTEXT_TEMPLATE.md", "CONTEXT_TEMPLATE.md", TRACKED),
    ("starter-kit/CLAUDE_TEMPLATE.md", "CLAUDE_TEMPLATE.md", TRACKED),
    ("starter-kit/BOOTSTRAP.md", "BOOTSTRAP.md", TRACKED),
    ("starter-kit/methodology_dashboard.py", "methodology_dashboard.py", TRACKED),
    ("starter-kit/methodology_trim.py", "methodology_trim.py", TRACKED),
    ("starter-kit/context_budget.py", "context_budget.py", TRACKED),
    ("starter-kit/quality_ratchet.py", "quality_ratchet.py", TRACKED),
    # seed-once root-files: created if absent, then adopter-owned (never clobbered)
    ("starter-kit/SESSION_NOTES.md", "SESSION_NOTES.md", SEED),
    ("starter-kit/CHANGELOG.md", "CHANGELOG.md", SEED),
    ("starter-kit/HANDOFFS.md", "HANDOFFS.md", SEED),
    ("starter-kit/ROADMAP.md", "ROADMAP.md", SEED),
    ("starter-kit/context-budget.json", ".context-budget.json", SEED),
    ("starter-kit/quality-gates.json", ".quality-gates.json", SEED),
    # framework docs -> docs/methodology/
    ("ITERATIVE_METHODOLOGY.md", "docs/methodology/ITERATIVE_METHODOLOGY.md", TRACKED),
    ("HOW_TO_USE.md", "docs/methodology/HOW_TO_USE.md", TRACKED),
    ("FRAMEWORK_APPARATUS.md", "docs/methodology/FRAMEWORK_APPARATUS.md", TRACKED),
    # workstreams + campaigns + templates -> docs/methodology/workstreams/
    ("workstreams/DESIGN_WORKSTREAM.md",
     "docs/methodology/workstreams/DESIGN_WORKSTREAM.md", TRACKED),
    ("workstreams/ARCHITECTURE_WORKSTREAM.md",
     "docs/methodology/workstreams/ARCHITECTURE_WORKSTREAM.md", TRACKED),
    ("workstreams/DEVELOPMENT_WORKSTREAM.md",
     "docs/methodology/workstreams/DEVELOPMENT_WORKSTREAM.md", TRACKED),
    ("workstreams/AUDIT_WORKSTREAM.md",
     "docs/methodology/workstreams/AUDIT_WORKSTREAM.md", TRACKED),
    ("workstreams/RESEARCH_DOCUMENTATION_WORKSTREAM.md",
     "docs/methodology/workstreams/RESEARCH_DOCUMENTATION_WORKSTREAM.md", TRACKED),
    ("workstreams/TEMPLATE_WORKSTREAM.md",
     "docs/methodology/workstreams/TEMPLATE_WORKSTREAM.md", TRACKED),
    ("workstreams/RESEARCH_EXHAUSTIVE_VERIFICATION_CAMPAIGN.md",
     "docs/methodology/workstreams/RESEARCH_EXHAUSTIVE_VERIFICATION_CAMPAIGN.md", TRACKED),
    ("workstreams/INHERITED_CODEBASE_FAMILIARIZATION_CAMPAIGN.md",
     "docs/methodology/workstreams/INHERITED_CODEBASE_FAMILIARIZATION_CAMPAIGN.md", TRACKED),
    ("workstreams/TEMPLATE_CAMPAIGN.md",
     "docs/methodology/workstreams/TEMPLATE_CAMPAIGN.md", TRACKED),
]

# Optional "current-format" markers for SEED dests, keyed by adopter-relative dest path.
#
# A SEED is adopter-owned and never overwritten (Decision 2a), so an adopter upgrading from an
# earlier methodology keeps its OLD-shaped seed: it gains the new behavior (the synced files) but
# silently misses the new seed FORMAT. When a seed listed here is PRESENT but its content lacks the
# marker string, bin/status reports it advisory-only as "present (stale format)" so the migration
# is DISCOVERABLE. sync still never auto-overwrites it — the adopter migrates it by hand
# (BOOTSTRAP.md "Updating an existing project…"; BL-6 item 2).
#
# A marker needs two properties:
#   1. LIFETIME-STABLE — it survives every prepend, trim and close-out, so an in-use current-format
#      seed is never mis-flagged. That rules out the METHODOLOGY-SEED-SENTINEL, which the adopter
#      deletes on its first real entry. A marker in the front matter survives, because
#      methodology_trim.py pins that zone and never archives it.
#   2. VERSION-DISCRIMINATING — absent from every earlier format it must detect, or it can never
#      fire. A marker keyed to something that never changes across versions, such as a title,
#      reports every old seed as current.
#
#   * CHANGELOG.md keys on "ledger-format: 2", on the seed's pointer to FRAMEWORK_APPARATUS.md
#     §The Action Ledger, which holds the rules the seed used to carry; the seed asks adopters to
#     keep that line. Bump the number whenever the seed's format changes again, and drive the stale
#     case in bin/tests.sh Test 20 red before trusting it — a marker that never moves never fires.
#   * HANDOFFS.md keys on "handoffs-format: 2", the first line of the seed's "Size, and when to
#     archive" section, so bringing that section across (the documented migration) carries it. It
#     used to key on the heading itself, which failed property 2: the seed that shipped with the
#     trimmer already had the heading, over the size premise this format replaced.
#   * SESSION_NOTES.md is deliberately omitted: it is rewritten wholesale every session, so no
#     token is stable enough to detect its format without false positives. Add an entry here only
#     when a seed gains a marker with both properties.
SEED_FORMAT_MARKERS = {
    "CHANGELOG.md": "ledger-format: 2",
    "HANDOFFS.md": "handoffs-format: 2",
}
