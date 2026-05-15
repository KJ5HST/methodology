# Font / Render-Dependency Completeness Discipline

**Date:** 2026-05-15
**Status:** Proposal for review by the methodology lead
**Author context:** Drafted from a joy/ project session (Session 50). Evidence is one concrete case (joy/ Session 48); the proposal generalizes from it. The methodology session is the right place to decide placement, verification scope, and tooling — this document supplies evidence and design space, not pre-decided answers.

---

## Summary

The methodology's existing render-verification language (`SAFEGUARDS.md` "Verify the Build Equivalent"; `RESEARCH_DOCUMENTATION_WORKSTREAM.md` "Render Verification"; `RESEARCH_EXHAUSTIVE_VERIFICATION_PROTOCOL.md` "Render Verification") treats rendering as a binary correctness check: did it succeed, did citations resolve, did cross-references resolve, did figures generate. That coverage misses a class of failure where rendering **succeeds silently while the output is wrong** — most concretely, when a configured font is registered (the build engine finds *something* named that family) but does not actually ship the requested faces, and the engine falls back to a default without erroring.

The joy/ project has one concrete instance of this failure (SBL BibLit, ships Regular-only, italics rendered as upright Latin glyphs for 47 sessions before being noticed). The fix is project-specific. The methodology gap it exposes is general: **render-dependency completeness is a build-correctness property, not just a build-success property**, and the current methodology does not require checking it.

This proposal documents the gap, supplies the joy/ evidence, and frames the placement / scope / tooling decisions that the methodology session would need to settle to close it.

---

## The gap

`SAFEGUARDS.md` lines 80–93 ("Verify the Build Equivalent") defines render-verification as: compilation succeeds, citations resolve, cross-references resolve, figures generate. Each is a *did it produce output* check.

`RESEARCH_DOCUMENTATION_WORKSTREAM.md` lines 236–242 ("Render Verification") elaborates the same shape: render to every target format, resolve every citation key, resolve every cross-reference, spot-check unmodified sections.

What none of those say: verify the rendered output **actually used the assets it was configured to use**. The implicit assumption is that asset configuration is self-checking — if you wrote `mainfont: "X"` and the build succeeded, X is in the output. That assumption holds for compilation-style errors (XeTeX raises `Package fontspec Error: The font "X" cannot be found` when the family doesn't resolve at all) but fails for *partial-resolution* errors:

- A font family resolves (engine finds a Regular face) but missing Italic / Bold / BoldItalic faces silently fall back to a default
- A CSL file resolves but is the wrong style version, producing valid-looking but non-spec citations
- A LaTeX template resolves but a missing class option is silently ignored
- A figure-generation script imports a library version different from the one specified, producing valid output with different defaults

The class is: **render-dependency partial-resolution produces valid-looking output**. The current methodology assumes valid-looking output is correct output. The joy/ case shows that assumption can be wrong for ~47 sessions before anyone notices.

---

## Evidence: joy/ Session 48 case

**Configuration in `_quarto.yml` (pre-Session 48):**

```yaml
mainfont: "SBL BibLit"
```

**What XeTeX did at render time:**

- Resolved "SBL BibLit" to `SBLBibLit.ttf` (Regular face). Present.
- Resolved italic markup (`*foo*` → `\emph{foo}`) to "SBL BibLit Italic." Not present in the SBL BibLit family.
- Silently fell back to upright Latin glyphs. **No error, no warning, no log entry visible during render.**

**How long it persisted:** Session 1 (2026-04-15) → Session 47 (2026-05-13). 47 sessions, all of which ran `quarto render` cleanly, none of which detected the silent italic fallback. The defect was caught only when the user noticed visually in the rendered PDF during Session 47 close-out.

**Why the standard render-verification didn't catch it:** the render succeeded; every citation resolved; every cross-reference resolved; every figure generated. The PDF was structurally correct. Italic-marked text simply appeared upright.

**Verification command that *would* have caught it:** `pdffonts _book/Joy.pdf` shows which fonts actually got embedded. Before the fix, italic face was absent from the embedded-font table. After the Session 48 fix (Libertinus Serif via kpathsea-based fontspec config), all four faces (Regular / Italic / Bold / BoldItalic) embed.

**Pre-render verification commands that *would* have caught it:**

- `fc-list "SBL BibLit" | wc -l` returns 1 (only Regular face is registered with fontconfig)
- `kpsewhich SBLBibLit-Italic.otf` returns empty (no italic file in TeX Live's font path)
- A minimal xelatex test document with `\textit{foo}` would have rendered as upright on inspection

**Why even the static checks weren't run:** they aren't part of any documented Phase 0, build-equivalent verification, or workstream checklist. There was no protocol step that prompted them. The defect was a font-package property the project's setup never tested for.

**Project-specific fix (already shipped, not part of this proposal):** Session 48 switched to Libertinus Serif via kpathsea path-based fontspec config (`mainfont: "LibertinusSerif-Regular.otf"` + `mainfontoptions: [ItalicFont=..., BoldFont=..., BoldItalicFont=...]`). The project-specific Learning is in joy/`CLAUDE.md` (Session 48 entry).

**Methodology-relevant takeaway:** the fix is local; the gap that allowed the latent defect is methodology-shaped. No project running this methodology has a documented prompt to check render-dependency completeness.

---

## Design space (decisions for the methodology session)

The methodology session has at least three coupled decisions. Each option below is sketched with what it commits to and what it leaves open; the methodology session is the right venue to settle them.

### Decision 1: Placement

Where in the methodology corpus does the discipline live?

| Option | What it commits to | Tradeoff |
|---|---|---|
| **A. `SAFEGUARDS.md` "Verify the Build Equivalent"** as a sub-section or expanded clause | Universal: every project using this methodology must check render-dep completeness at the build-equivalent boundary | Strongest reach; risks adding obligation to projects with trivial render pipelines (single Markdown file → PDF with default fonts) where the check is overkill |
| **B. `RESEARCH_DOCUMENTATION_WORKSTREAM.md` "Render Verification"** as an additional verification item | Domain-scoped: research-doc projects with custom fonts / Unicode scripts / CSL pipelines get the check; software projects don't inherit it | Narrower; misses non-research projects that have the same gap (e.g., a software project with branded PDF reports) |
| **C. Both, with cross-reference** | SAFEGUARDS states the universal principle; workstream adds research-doc-specific verification commands (`pdffonts`, `fc-list`, etc.) | More text; clearest separation between universal rule and domain implementation |
| **D. New methodology document** (e.g., `RENDER_DEPENDENCY_COMPLETENESS.md`) | Treats render-dep completeness as a first-class concern alongside SAFEGUARDS | Heaviest; only worth it if the discipline generalizes to ≥3 render-dep classes (fonts, CSL, templates, ...) |

A note on the existing `SAFEGUARDS.md` "Verify the Build Equivalent" table (lines 84–89): adding a "Verify render dependencies" column or row to that table is a low-friction option C variant.

### Decision 2: Verification scope

What does the discipline actually require checking?

| Option | What runs | Catches the SBL BibLit case? | Cost |
|---|---|---|---|
| **Static (pre-render) only** | For each configured font: verify all expected faces resolve (e.g., `fc-list "<family>"` count ≥ 4; or `kpsewhich` per face filename for TeX Live + path-based fontspec) | Yes (the Regular-only character of SBL BibLit is visible in `fc-list` before render) | One check per font config; can be a Phase 0 / setup-time step |
| **Post-render only** | `pdffonts` (or equivalent for HTML/DOCX) confirms expected faces are embedded in the output | Yes (italic face is absent from the embedded table) | One check per render; tied to the build-equivalent step |
| **Both** | Static at Phase 0 / setup; post-render at build-equivalent | Yes, with belt-and-suspenders | Two checks; static catches mis-config without rendering, post-render catches silent fallback the static check missed |
| **Asset-class-agnostic** | Generalize beyond fonts: a manifest of expected render dependencies (fonts, CSL files, templates) checked at Phase 0 and after render | Yes, plus other classes | Most flexible; requires the project to maintain the manifest |

The methodology session should also consider whether the discipline is a *hard rule* (must run before commit) or a *soft prompt* (Phase 0 surfaces it; project decides). The current `SAFEGUARDS.md` build-equivalent clause is in hard-rule shape.

### Decision 3: Tooling

Does the methodology starter-kit ship a reference implementation?

| Option | What ships | Tradeoff |
|---|---|---|
| **Prose discipline only** | The methodology document states the rule; each project implements the check however suits its toolchain | Lightest; relies on per-project diligence; risks "I'll do it later" drift |
| **Reference `scripts/verify-render-deps.py`** in starter-kit | A small Python script with documented inputs (font list from `_quarto.yml` or equivalent) and outputs (per-face presence + a non-zero exit code on failure) | Concrete; one toolchain (Quarto + XeLaTeX) gets a working starting point; other toolchains adapt |
| **Hook into existing toolchain matrix** at `RESEARCH_DOCUMENTATION_WORKSTREAM.md` line 318 | Add a per-toolchain "verify render deps" column to the toolchain matrix, with the canonical command for each | Most reusable; aligns with the existing toolchain abstraction in the workstream |

If the methodology session wants a draft script to iterate from, Session 50 (this joy/ session) can produce one as a follow-up; this proposal does not preempt that decision.

---

## Suggested acceptance criteria (for whatever the methodology session lands on)

Whatever the eventual shape, the proposal recommends the methodology session check the discipline against these:

1. **Catches the SBL BibLit case.** A retrospective application to joy/ pre-Session 48 should flag the defect at Phase 0 or at the build-equivalent boundary. If the proposed discipline wouldn't have caught the known case, it isn't strong enough.
2. **Doesn't add unbounded overhead to every session.** If the check runs at every Phase 0 for every project regardless of whether anything changed, it will erode (FM #17 protocol erosion). Consider scoping by "fires when font / CSL / template config changes" or "fires at setup + post-render."
3. **Generalizes beyond fonts.** Fonts are the load-bearing example because the joy/ case is concrete. The principle is render-dependency completeness. If the discipline can't extend to CSL files, LaTeX templates, or figure-generation library versions, it solves the joy/ case but doesn't earn its place in `SAFEGUARDS.md`.
4. **Works across the toolchain matrix.** `RESEARCH_DOCUMENTATION_WORKSTREAM.md` line 318 documents toolchain variants (Quarto / LaTeX / Sphinx / vanilla Markdown). The check command differs per toolchain; the principle should not.
5. **Specifies how a failure is handled.** Hard rule (must fix before commit) vs soft prompt (surface to user, project decides) is a real choice; the methodology session should make it explicit.

---

## References

- `SAFEGUARDS.md` lines 80–93 — current "Verify the Build Equivalent" section, the most likely placement target for the universal principle.
- `workstreams/RESEARCH_DOCUMENTATION_WORKSTREAM.md` lines 236–242 — current "Render Verification" section; line 318 — toolchain matrix; either is a candidate for domain-specific verification commands.
- `workstreams/RESEARCH_EXHAUSTIVE_VERIFICATION_PROTOCOL.md` line 217 onward — render-verification language in the protocol; check for consistency if the discipline lands in SAFEGUARDS.
- joy/ `CLAUDE.md` Session 48 Learning ("macOS CoreText silently ignores fonts installed into `~/Library/Fonts/` for XeTeX rendering; kpathsea-based fontspec config is the portable workaround") — the project-specific Learning derived from the same case.
- joy/ memory `project_toolchain.md` (Session 48 update) — documents the SBL BibLit Regular-only limitation and the kpathsea-based fix, including an explicit "Do NOT propose installing fonts via Font Book or `~/Library/Fonts/`" note.
- joy/ `BACKLOG.md` — open item: "Methodology workstream — font availability + face-completeness discipline." This proposal is the response to that backlog item.

---

## What the methodology session is expected to produce

This is a proposal, not a patch. The methodology session is the right venue to:

- Decide placement (Decision 1)
- Decide verification scope and hard-rule-vs-soft-prompt (Decision 2)
- Decide tooling (Decision 3)
- Write the actual additions / edits to `SAFEGUARDS.md`, the workstream, or a new document
- (Optionally) draft the reference script
- (Optionally) update the starter-kit sync list if a new script is added

After the methodology session, joy/ will inherit the change via the next `bin/sync` run and can either drop its open backlog item or add a project-specific Phase 0 step in `CLAUDE.md` if the methodology landing is soft-prompt rather than hard-rule.
