# Research Documentation Workstream

Adaptation of the [Iterative Session Methodology](../ITERATIVE_METHODOLOGY.md) for research papers, technical reports, dissertations, regulatory analyses, and other long-form documents whose deliverable is an argumentative artifact backed by cited primary sources.

---

## When to Use

Use this workstream when:
- Producing a research paper, white paper, dissertation chapter, or scientific synthesis
- Writing a regulatory analysis or technical report that cites primary sources
- Maintaining a multi-paper series where citations and figures cross-pollinate
- Working in Quarto, LaTeX, Sphinx, or any toolchain that renders source files into PDF/HTML/DOCX
- The deliverable's correctness depends on each numeric, dated, or attributed claim tracing to a verifiable source
- Auditing an existing research-documentation repository with fresh eyes against this workstream's procedures (see *Audit Mode* below)

**Not for casual documentation.** API docs, READMEs, and runbooks belong in the Development workstream's documentation sub-tasks. This workstream's machinery (corpus management, claim-source audit, citation discipline) is overhead unless the deliverable is evaluated on the strength of its citations.

**Distinct from the Audit workstream.** `AUDIT_WORKSTREAM.md` produces analysis *about* an artifact; this workstream's standard mode produces an artifact *with* embedded analysis. The claim-source audit (Phase 6) borrows from Audit but is internal to the writing loop, not the deliverable. When you specifically want to audit an existing research-documentation repository — finding-list deliverable, no paper modifications — use *Audit Mode* below, which adapts this workstream's machinery into the review-session pattern from `AUDIT_WORKSTREAM.md`.

---

## Recommended Operating Mode

Sloppy research is worse than valueless — credible-looking citations that fail under scrutiny damage reader trust more than missing citations would. Documentation errors surface as plausible text that passes casual review and only breaks under hostile scrutiny; by then the reputational damage is done.

This workstream benefits materially from your agent's deepest-reasoning mode (max-effort, deep-thinking, or extended-reasoning settings, depending on the toolchain). The marginal cost is latency and tokens; the cost of an undetected misattribution is reputational. Set the mode at session start — not after a problem appears.

The same logic applies to a human author working without an agent: the chapters of this workstream that demand the most attention are claim-source mapping, framing-language distinctions, and dedup logic across parallel work streams. Slow down on those. Speed elsewhere is fine.

---

## Audit Mode (Reviewing an Existing Repository)

The procedures below are forward-looking — they assume you are writing or extending a paper. The same procedures double as **audit criteria** for a repository where prior work was done without this workstream's discipline. Use Audit Mode when the deliverable is a finding list, not modifications to the papers.

Follow the **review-session pattern** from [`AUDIT_WORKSTREAM.md`](AUDIT_WORKSTREAM.md): Phases 1–4 (Pre-Flight, Research, Create the analysis, Present), skipping Phase 5 (Implement). The deliverable is the audit report; remediation is a follow-on session that re-enters this workstream's standard mode.

### Map this workstream's machinery into audit deliverables

| This workstream's section | Audit role |
|---|---|
| Phase 2 Steps 2–5 (corpus inventory, pre-flag, retrieval, filename verification) | Inventory the existing corpus; flag missing primary sources, format mismatches, internal duplicates, stub files |
| Phase 3 Claim-Source Map | Sample 20–40 high-stakes claims (numeric, dated, attributed). If the unsupported rate exceeds the ~22% baseline, expand the sample. |
| Phase 6 Cleanup procedures | Identify search artifacts, bogus retrievals, and pre-existing duplicates to remove |
| Verification Checklist | Per-paper pass/fail grid |
| The 13 anti-patterns | Finding categories — every finding cites a numbered anti-pattern |

### Audit report structure

```
## Coverage
- Papers audited: X of Y (with reason for any exclusions)
- Claim sample size: N (per-paper breakdown)
- Anti-pattern dimensions evaluated: [list, or "all 13"]

## Findings
For each finding:
- Severity: critical / moderate / minor
- Anti-pattern: #N (from this workstream)
- Location: file:line or section
- Evidence: quoted passage from source, file-inspection result, or citation key
- Recommendation: specific action

## Structural observations
- Patterns across multiple findings (systemic vs. one-off)
- Sections or papers that pass cleanly (use as reference implementations)

## Remediation plan
- Prioritized punch list for follow-on implementation sessions
- Estimated session count
```

### Severity calibration

| Severity | Example findings |
|----------|-----------------|
| **Critical** | Unsupported numeric claim cited as fact; citation key resolves to the wrong source; primary-source file is actually an HTML stub or 403 page; framing language asserts a constraint as a goal in a load-bearing section |
| **Moderate** | Descriptive-page citation where the primary source is available locally; redundant restatement across sections; figure with no provenance; misattribution that can be re-attributed without removing the claim |
| **Minor** | Search artifact in corpus folder; abstract length out of target range; bibliography entry style inconsistent with project convention |

If a single repository would generate >40 critical findings, scope the audit by paper or by dimension and produce one report per scope. A 200-finding monolithic report is not actionable.

---

## Phase 2: Research (Research-Documentation-Specific)

### Step 1: Study the Deliverable's Purpose and Audience

Before opening any source, define:
- **Who reads this?** Domain experts, regulators, lay readers, peer reviewers.
- **What standard of evidence is required?** Quoted primary sources, peer-reviewed citations, regulatory filings, or self-evident claims.
- **What is the claim density?** A 20-page synthesis paper may carry 100+ numeric or dated claims. Estimate early — the audit workload scales linearly.
- **What is OUT of scope?** Adjacent topics that will tempt scope creep but do not belong in this paper.

### Step 2: Inventory the Source Corpus

Build a reference table of every source you might cite:

| Source | Type | Local Path | Format | Primary or Secondary | Content Verified? |
|--------|------|-----------|--------|---------------------|-------------------|
| (citation key) | (journal / regulation / law-firm note / vendor commentary) | (path or URL) | (PDF / HTML / DOCX) | (primary / secondary) | (yes / no / stub) |

**Primary vs. secondary matters more than convenience.** A consulting-firm summary citing a regulator's statement is secondary; the regulator's actual filing is primary. Default to primary; cite secondary only when primary is unavailable.

### Step 3: Pre-Flag Completeness and Run a Post-Hoc Dedup

Before retrieval, audit the corpus for:
- **Missing sources** flagged by the previous session as "not retrievable"
- **Pre-existing duplicates** in the corpus folder (same paper, different filename or format)
- **Stub files** masquerading as content (HTML 403 pages saved as PDF, search-result pages, error responses)

**Race conditions survive accurate pre-flagging.** Parallel agents sharing a download target can each retrieve the same item under different names, so a post-hoc dedup pass is required even if pre-flagging was correct. MD5 plus content-equivalence comparison is the minimum.

### Step 4: Retrieve Missing Sources via the WAF Hierarchy

When primary sources block automated retrieval, escalate in order:

| # | Method | When It Helps |
|---|--------|---------------|
| 1 | Direct `curl` | Most public documents |
| 2 | WebFetch (different ingress IP) | When the host blocks scripted user-agents from one network |
| 3 | `curl` with browser User-Agent | When the host inspects UA strings |
| 4 | Wayback Machine | When the live URL is dead, moved, or actively blocking |
| 5 | User's own browser | Last resort — cookies, captchas, paywalls, SSRN downloads |

Stop at the first method that succeeds. Document the method used in the retrieval log so the next session does not re-derive the workaround.

### Step 5: Verify File Content Matches Filename

**Agent-named filenames reflect agent assumptions, not content.** A file named `xin_huang2024_arxiv.pdf` may actually be Lindholm et al. 2022; a `*.pdf` extension may wrap an HTML challenge page. For every retrieved or pre-existing source:
- Run `pdfinfo` (PDFs) or `file` (general) to confirm the format
- Open `pdftotext`'s first-page output and confirm title/authors/date match the filename
- For HTML files, inspect `<title>` and the first heading

Filename trust is the single most common source of citation drift in agent-driven research.

### Step 6: Review Prior Sessions in This Series

Read every previous session's outputs:
- What patterns were established? (citation key conventions, figure naming, section ordering)
- What claims were already verified? (don't re-audit them)
- What corrections were applied? (stale claims may still appear in copy elsewhere)
- What was the per-session claim-audit accuracy? (the trend predicts this session's audit workload)

### Step 7: Challenge Scope

Apply the Splitting Test at the paper level:
- Is this one paper or two? (Different audiences, different evidence bases, different argumentative structures all suggest splitting.)
- Should this dimension be a section or a standalone paper?
- Is the synthesis trying to do work that belongs in a separate methods or appendix paper?

Signal phrases that suggest a split: *"the paper also covers..."*, *"as a brief aside..."*, *"in addition to the main argument..."*. If you write these, evaluate whether the addition has its own argumentative spine.

---

## Phase 3: Create (Research-Documentation-Specific)

### The Paper Structure

For each paper, draft and align:
- **YAML / preamble** — title, authors, abstract, JEL codes or keywords, output formats
- **Abstract** — 150-250 words, written *after* the body is complete enough to summarize honestly
- **Introduction** — establishes the question and why it matters; framing language must match the semantic role of the concepts (a *constraint* is not a *goal*)
- **Body sections** — each section has a single argumentative spine; cross-references resolve
- **Verification flags** — explicit markers for claims still requiring primary-source confirmation
- **Bibliography** — every citation key used in the body has a matching entry; entries match the source on disk

### The Claim-Source Map

Before drafting any body section, build a working map:

| Claim | Cited Source | Source on Disk? | Verification Status | Quoted Passage (≤40 words) |
|-------|-------------|-----------------|---------------------|---------------------------|
| (numeric / dated / attributed claim) | (citation key) | (yes / no) | (verified / pending / re-attribute / remove) | (exact quote that supports the claim) |

The quoted passage column is non-negotiable. *"The source exists"* and *"the source contains relevant material"* are not the same as *"the source supports this specific claim."* The audit in Phase 6 grades against this column.

### Figure and Table Provenance

For every figure or table:
- **Source of the data** — citation, computation script, or original construction
- **Reproducibility** — for computed figures, the script must be in version control and the figure regeneratable from it
- **User-edited?** — flag any figure the stakeholder manually refined; do not regenerate it without confirmation

### Citation Discipline

- Use a single bibliography file for the project. Multiple `.bib` files invite divergence.
- Citation keys follow a stable convention (`author{year}{shortname}` is one defensible choice). Pick once, apply everywhere.
- Render after every batch of edits. Citation drift compounds silently — a key swap that produces no visible warning today produces a missing citation tomorrow.
- For consolidating sub-papers into a synthesis, verify the local `.bib` is a subset of the project bibliography before deletion.

---

## Phase 4: Present (Research-Documentation-Specific)

When presenting drafts to the stakeholder:
- Render to the target format (PDF preferred — surfaces missing citations, broken cross-refs, layout issues that HTML hides)
- Highlight verification flags explicitly: *"Section 2.4 has three numeric claims I have not yet sourced to primary."*
- Surface framing decisions the stakeholder should ratify before they ossify (e.g., constraint-vs-goal, scope splits, dimension-vs-section)
- Do **not** present a paper as "complete" while audit-flagged claims remain. Either resolve them or list them as open items.

---

## Phase 6: Verify and Close (Research-Documentation-Specific)

### The Claim-Source Audit

For each new or modified body section, run the audit:
- For every numeric, dated, or attributed claim: confirm a quoted passage from the cited source supports it
- Per-claim verdict: **verified** / **re-attribute to X** / **remove**
- Track the audit's accuracy as a session metric. (Empirical baseline from a real-world session: ~22% of claims unsupported by their cited source, ~12% needing re-attribution. Deviation from this range is a signal — either the corpus or the audit is unusually clean or unusually compromised.)

**Audit-failed claims may still be true.** A claim flagged as unsupported in the local corpus may still be correct — the cited file may be wrong, missing, or a stub while the claim is verifiable against a different primary source. Always do one round of primary-source retrieval before removing a flagged claim.

### Cleanup

Before closing the session, sweep the corpus for:
- **Search artifacts** — intermediate `.html` and `.json` files agents save during retrieval. These are workspace pollution and should never be committed.
- **Confirmed duplicates and stubs** identified in Step 3
- **Bogus retrievals** — files retrieved under one name that turned out to be a different document

**Verify before destroying.** A prior agent's "delete me" classification can be wrong. Re-verify file content (open it, read the meta-title, run `pdftotext`) before deletion. The cost of verifying is seconds; the cost of deleting a primary source you needed is hours of re-retrieval.

### Sub-Agent Permission Asymmetry

When dispatching parallel sub-agents (e.g., one per paper or one per section):
- Sub-agents may have **read access but not write/edit access**, even when the parent agent has both
- Useful pattern: have sub-agents do reading, claim extraction, and analysis; capture their findings (line numbers, supporting passages, recommended changes); apply edits with the parent agent's permissions
- This pattern preserves the parallelism benefit even when sub-agents cannot directly modify files

### Render Verification

Before committing:
- Render to every target format the project produces (PDF, HTML, DOCX, revealjs)
- Resolve every citation key — *no missing or undefined references*
- Resolve every cross-reference — `?@fig-x` rendered output means the cross-ref is broken
- Spot-check 2-3 sections that were NOT modified — citation re-numbering and bibliography reordering can break adjacent sections silently

---

## Scope Validation Questions (Research-Documentation-Specific)

1. Is this one paper or two? Do the sections share an argumentative spine, or are they peers that should stand alone?
2. Are the framing nouns being introduced as goals, constraints, methods, or properties? Do my verbs and prepositions match?
3. Am I synthesizing across primary sources, or am I aggregating secondary commentary that aggregated primary sources?
4. Are my claims sourced to the most authoritative document, or to the most convenient summary of it?
5. Have I let the corpus determine the argument, or am I building the argument and then cherry-picking the corpus?

---

## Verification Checklist (Research-Documentation-Specific)

Before presenting:

- [ ] Every numeric, dated, or attributed claim has a verified quoted passage from a primary source
- [ ] Every citation key in the body has a matching entry in the bibliography
- [ ] Every cross-reference resolves in the rendered output (no `?@fig-x` artifacts)
- [ ] Every figure has known provenance (data source, generation script, or original construction)
- [ ] Filename verification has been run for every cited source
- [ ] No search artifacts (`*_search.html`, `ss_*.json`, etc.) remain in the corpus folder
- [ ] The paper renders cleanly to every target format
- [ ] Adjacent papers in the series still render and still cite consistently
- [ ] Framing language (verbs, prepositions) matches the semantic role of the nouns being introduced

---

## Reference Table Formats (Research-Documentation)

### Source Corpus Tracker
| Citation Key | Local Path | Type | Primary? | Content-Verified | First Cited In | Notes |
|--------------|-----------|------|---------|-----------------|----------------|-------|

### Claim-Source Audit Log
| Section | Claim | Cited Source | Verdict | Quoted Passage | Action Taken |
|---------|-------|-------------|---------|----------------|--------------|

### Retrieval Log
| Source | Target URL | Method Used | Status | Fallback | Session |
|--------|-----------|-------------|--------|---------|---------|

### Render Status Grid
| Paper | PDF | HTML | DOCX | Citation Resolution | Cross-Refs | Last Rendered |
|-------|-----|------|------|--------------------|------------| --------------|

---

## Common Anti-Patterns (Research Documentation)

1. **Citation drift** — Referencing citation keys that do not exist in the bibliography, or whose entries no longer match the source file. Render after every edit batch to catch immediately.
2. **Filename trust** — Treating an agent-assigned filename as evidence of file content. Always verify with `pdfinfo`, `pdftotext`, or `file`.
3. **Race-condition duplication** — Parallel agents sharing a download target each retrieve the same source under a different name. Run a post-hoc dedup even when pre-flagging was correct.
4. **Search-artifact accumulation** — Saving intermediate `.html` and `.json` files from retrieval into the corpus folder, then committing them. Instruct agents to return a final deliverable list, not save exploration files.
5. **Pre-existing-corpus blindness** — Only deduping newly-retrieved items, missing duplicates that pre-existed. The pre-existing corpus is part of the dedup scope.
6. **Descriptive-page substitution** — Citing the landing page that lists a committee's work instead of the specific document. Target the document, not the index that points to it.
7. **Premature delete on audit-flagged claim** — Removing a claim because the local corpus does not support it, when a primary-source retrieval would have confirmed the claim and pointed to the correct source.
8. **Premature delete on audit-flagged file** — Deleting a file based on a prior agent's classification without re-verifying its content.
9. **Edit from memory** — Modifying a section based on a stale mental model rather than re-reading the section. Particularly dangerous after context compaction.
10. **Greenfield framing** — Writing as if the prior literature, prior sessions, or prior policy environment did not exist. Destroys credibility with domain-expert readers.
11. **Overwriting user edits** — Regenerating figures, tables, or sections the stakeholder manually refined. Always confirm before regeneration if the artifact has been touched by hand.
12. **Redundant restatement** — Repeating the same argument or evidence in multiple sections during incremental drafting. Conduct a structural review after major additions.
13. **Goal-language for constraints** — Using verbs and prepositions that imply intent (*"organize for"*, *"aim at"*) when the noun being introduced is a constraint, envelope, or boundary. The category error is subtle but reads as imprecise to domain experts.

---

## Adaptation Notes for Toolchains

Find your toolchain row and substitute the toolchain-specific equivalent for each generic concept used in this workstream:

| Toolchain | Source File | Bibliography | Render Command | Citation Key Check | Cross-Reference Check | Figure Script |
|-----------|-------------|--------------|----------------|--------------------|-----------------------|---------------|
| **Quarto** | `.qmd` | `references.bib` (BibTeX/CSL) | `quarto render` | `quarto render` warnings | `?@fig-x` in output | R / Python chunk in document or external |
| **LaTeX** | `.tex` | `references.bib` (BibLaTeX) | `latexmk` / `pdflatex` | `biber` / `bibtex` warnings | `??` in output | TikZ or external |
| **Sphinx** | `.rst` / `.md` | `references.bib` via `bibtex` directives | `sphinx-build` | `sphinxcontrib-bibtex` warnings | `:ref:` failures in build log | matplotlib or external |
| **Pandoc** | `.md` (Pandoc flavor) | `.bib` via `--citeproc` | `pandoc input.md -o output.pdf --citeproc` | `--citeproc` warnings | `pandoc-crossref` warnings | External script + `![...](...)` |
| **AsciiDoc** | `.adoc` | `.bib` via `asciidoctor-bibtex` | `asciidoctor` / `asciidoctor-pdf` | `asciidoctor-bibtex` warnings | Anchor-resolution warnings in build log | External script + `image::` directive |
| **Markdown (vanilla)** | `.md` (CommonMark) | None native — pipe through Pandoc for citations | `cmark` (limited) or external renderer | Manual or via Pandoc | Manual reference-style links | External script + `![...](...)` |

**Note on vanilla Markdown.** CommonMark and GitHub-Flavored Markdown have no native citation system. For any research-documentation use case, either render through Pandoc (which adds CSL/BibTeX support) or pick one of the other toolchains. The Markdown row is included so readers know what they're missing — not as a recommended path.

---

## Example Session Outline

```
Session 5: Synthesis Paper — Integrate External Dimensions

Pre-Flight: Read SESSION_NOTES.md and prior phase handoff. Workspace clean.
            All four dimension papers render cleanly. Bibliography has 155 entries.
            Spot-checked synthesis paper render — no citation warnings.

Research:   Read 4 dimension papers (regulatory, fairness, capital, resilience)
            in full. Built claim-source map for new synthesis sections (37 claims).
            Pre-flagged 2 missing primary sources; retrieved both via WebFetch
            (curl direct was blocked).
            Verified 8 newly-cited sources by content (pdftotext title + authors).
            Caught 1 filename mismatch: file labeled as 2024 was actually 2022.

Create:     Drafted 3 new synthesis sections integrating the 4 external dimensions.
            Decision: capability-vs-external split rather than 8 peer dimensions.
            Framing: "answers to" (constraint language), not "organizes for" (goal language).
            Built section-level claim-source map; 37 of 37 claims have quoted passages.

Present:    Stakeholder approved framing decision. Flagged 2 numeric claims as
            "verify primary before next render."

Implement:  Safety commit. Wrote sections to synthesis.qmd. Updated cross-refs.
            Rendered to PDF, HTML, DOCX — all clean. No missing citations.
            Spot-checked 2 unrelated dimension papers — still rendering.

Close:      Claim audit: 35 verified, 2 re-attributed (one Oliver Wyman → Cytora
            press release, one Milliman Part 3 → EIOPA Opinion). 0 removed.
            Audit accuracy ~5% re-attribution rate (below the 12% baseline —
            credit goes to upstream pre-verification by the dimension papers).
            Cleanup: deleted 3 search artifacts, 1 duplicate.
            Pattern: "claim-source map before drafting" — every claim was already
            sourced before being written, so no post-hoc audit corrections needed.
            Recommendation: Session 6 should polish abstracts (currently >300 words
            in 3 of 4 dimension papers; target 150-250).
```
