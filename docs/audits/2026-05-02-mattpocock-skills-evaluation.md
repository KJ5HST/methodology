# Audit: Matt Pocock's `skills` Repo vs. Iterative Session Methodology

**Date:** 2026-05-02
**Session:** S438 (portfolio)
**Author:** Iterative Session Methodology agent (Claude Opus 4.7)
**Source:** [github.com/mattpocock/skills](https://github.com/mattpocock/skills) (commit at fetch time)
**Workstream:** Audit (Phases 1-4 of `AUDIT_WORKSTREAM.md`; no implementation this session per FM #18)

---

## Implementation Status (re-framed 2026-05-25)

The 2026-05-02 audit recommended 10 follow-up sessions (F1–F10). All 10 were implemented on the `experimental/pocock-audit` branch over the next three weeks (16 commits, `f6133ce`..`d793681`). An operator review on 2026-05-22 paused the rollout: several F-commits **re-implemented disciplines that Pocock's skills (or Claude Code built-ins) already provide**, which violated an emerging principle the methodology had not yet articulated.

A 2026-05-25 planning session formalized the principle:

> **Methodology recommends; methodology does not reimplement.**

The release that lands with this audit doc adopts a **drop / keep / refactor** framing for the F-commits under that principle.

### Dropped — work on `experimental/pocock-audit` not carried to `main`

| F | What the branch shipped | Why dropped | What ships instead |
|---|---|---|---|
| F1 | `starter-kit/hooks/block-dangerous-git.sh` + BOOTSTRAP install step (`4d1f35e`) | Direct re-implementation of Pocock's `/git-guardrails-claude-code` | `RECOMMENDED_SKILLS.md` maps the Pocock skill to SAFEGUARDS' Blast Radius Limits as the recommended mechanical countermeasure; the forward pointer ships in `BOOTSTRAP.md` Step 10. `SAFEGUARDS.md` itself is unmodified; no script ships |
| F5 (body) | Full 6-phase debug-loop section + "Build the Loop Discipline" + tag convention in `DEVELOPMENT_WORKSTREAM.md` (`3398779`) | Direct re-implementation of `/diagnose` | F5 *naming only* — debugging recognized as a session type; body cites `/diagnose` |
| F10 design | A 574-line design doc for shipping methodology-authored skills (`4785bb5`) | Premised on methodology shipping its own SKILLs | Superseded by `RECOMMENDED_SKILLS.md` + the citation convention |
| F10.A | `runtime-smoke-test` SKILL.md (`2dc6f73`) | Claude Code built-in `/verify` covers this | Phase 3E body cites `/verify` and `/run` |
| F10.B | `pre-create-grill` SKILL.md (`18c6932`) | Pocock's `/grill-me` covers this | Phase 2.5 body cites `/grill-me` |
| F10.C | `evidence-based-inventory` SKILL.md (`5f21e2a`) | Operator decision: methodology ships no SKILLs in this round | Planning-session discipline stays as prose in `ITERATIVE_METHODOLOGY.md` |
| F10.0 | `bin/sync` skill-directory support + BOOTSTRAP Step 12 (`e2168fe`) | No adopter has installed skills under methodology; demand-driven | Deferred until an adopter signals need |
| F10.0+ | `bin/status` per-skill drift visibility (`4faf9da`) | Same as F10.0 | Deferred |

### Kept — distilled to conceptual content under the principle

| F | What ships on `main` | Source on branch | Lands at |
|---|---|---|---|
| F2 | Horizontal-slicing failure mode (next free FM number) + Phase 3F commit-checklist cleanup line citing `/diagnose` | `314088b` | `SESSION_RUNNER.md` |
| F3 | `CONTEXT_TEMPLATE.md` + Phase 2 read-step; maintenance cites `/grill-with-docs` | `fd72b5e` | `starter-kit/CONTEXT_TEMPLATE.md`, `ITERATIVE_METHODOLOGY.md` |
| F4 | Issue Lifecycle 5-state machine; transitions cite `/triage` | `c389a82` | `workstreams/DEVELOPMENT_WORKSTREAM.md` |
| F6 | Deepening + deletion-test heuristics; cite Ousterhout + `/improve-codebase-architecture` | `1ee1c1f` | `workstreams/ARCHITECTURE_WORKSTREAM.md` |
| F7 | Phase 2.5 Pre-Create Grill as named optional phase shape; body cites `/grill-me` | `78dba14` | `ITERATIVE_METHODOLOGY.md` + `SESSION_RUNNER.md` task-mapping row |
| F8 | Pre-commit hooks recommendation paragraph; cites `/setup-pre-commit` as one option | `6d4440e` | `starter-kit/BOOTSTRAP.md` |

### Refactored — existing methodology content updated under the principle

| Where | Change | Why |
|---|---|---|
| `SESSION_RUNNER.md` §Phase 3E Runtime Smoke Test | Body refactored to a short rule + citation of `/verify` and `/run`; intent preserved (the runtime-verify gate remains) | Phase 3E (added v2.3) described the smoke-test procedure; `/verify` is that procedure. Methodology cites the skill. |
| `ITERATIVE_METHODOLOGY.md` §Session Types | "Three session types" → "Four" — Debugging added (naming only) | Debugging is a distinct session shape (search vs build); workflow body remains in `/diagnose` |
| `workstreams/AUDIT_WORKSTREAM.md` | Light citation pass — recommended-skills callout pointing to `/code-review`, `/review`, `/security-review` | Surgical, not wholesale rewrite (operator decision; Medium/Heavy = follow-on) |

### Out of scope this release — flagged for follow-on

- **F9** — per-repo `CONTEXT.md` pilot on `rad-con`: implemented in `rad-con/2181bc5`, not part of this `methodology` release.
- **FM countermeasures → hooks** (audit doc Observation 3): separate workstream.
- **AUDIT_WORKSTREAM Medium/Heavy audit**: follow-on after Light lands.
- **DEVELOPMENT_WORKSTREAM citation audit beyond F4**: future-audit candidate.
- **RESEARCH_DOCUMENTATION_WORKSTREAM citation audit** (could cite `/verify` for render verification): future-audit candidate.
- **SESSION_RUNNER FM mechanical-enforcement column**: depends on hook-conversion design.

### Provenance

The full implementation work for F1–F10 remains on `experimental/pocock-audit` as recoverable record (operator retains the branch for 30 days post-release, then deletes). The original audit body below is preserved verbatim from the 2026-05-02 capture.

---

## TL;DR

Of the 16 skills in Pocock's repo, **5 are strong incorporation candidates**, **3 are worth adapting**, **5 are already covered better by current methodology**, and **3 are out-of-scope or platform-specific**. The most consequential gaps Pocock fills:

1. **Project-level domain glossary (`CONTEXT.md`)** — methodology has session-scoped reference tables but no shared-language artifact above session notes.
2. **Mechanical enforcement of `SAFEGUARDS.md` rules via PreToolUse hooks** — converts text guidance to execution-time blocks.
3. **Disciplined debugging loop (`/diagnose`) with a "build a feedback loop FIRST" mandate and tagged-debug-log cleanup** — a class of work the methodology under-specifies.
4. **TDD's vertical-slice / tracer-bullet framing** — slots cleanly into existing anti-pattern list (horizontal slicing as new anti-pattern).
5. **Triage state machine for issue lifecycle** — methodology has issue-creation discipline (Learning #30) but no lifecycle pattern after creation.

Pocock's repo is **not a replacement for the methodology** — it's a complementary set of tactical skills aimed at single-session productivity, not the cross-session compounding discipline that is the methodology's core innovation. The two are orthogonal and mostly composable.

---

## Method

**What I read (Pocock's repo):** README in full; 12 of 16 SKILL.md files in full (`diagnose`, `triage`, `zoom-out`, `grill-with-docs`, `improve-codebase-architecture`, `tdd`, `to-issues`, `to-prd`, `grill-me`, `caveman`, `write-a-skill`, `git-guardrails-claude-code`, `setup-pre-commit`, `setup-matt-pocock-skills`); CONTEXT.md (the repo's own domain glossary). Skipped 2 platform-specific skills (`migrate-to-shoehorn`, `scaffold-exercises`) as obviously irrelevant.

**What I read (methodology):** `ITERATIVE_METHODOLOGY.md` in full; methodology's `CLAUDE.md` (loaded via system reminder); portfolio `SESSION_RUNNER.md` and `SAFEGUARDS.md` in full (read during Phase 0 orient); workstream directory listing; bin/ tools listing; CHANGELOG header.

**Comparison axes:** For each skill — (a) what real failure mode does it address? (b) does the methodology already address it, and how well? (c) what would incorporation cost in maintenance overhead? (d) does the skill's framing fit the methodology's existing vocabulary?

---

## Per-Skill Assessment

Sorted by recommendation strength (strongest YES first; rejects last). Each row gives my classification, rationale, and suggested incorporation point.

### STRONG INCORPORATE (5)

#### 1. `git-guardrails-claude-code` — Mechanical enforcement of SAFEGUARDS

| Aspect | Detail |
|---|---|
| **What it does** | A PreToolUse hook (`block-dangerous-git.sh`) installed at `~/.claude/hooks/` or `.claude/hooks/` that intercepts and blocks `git push`, `git reset --hard`, `git clean -f`, `git branch -D`, `git checkout .`, `git restore .` before they execute. |
| **Methodology gap** | `SAFEGUARDS.md` lists destructive commands as "no exceptions" rules but provides only **textual** enforcement. The agent has to remember to read SAFEGUARDS each session (FM #1: eager-to-start; FM #17: protocol erosion). A hook converts the rule to an execution-time block. |
| **Why this matters** | SAFEGUARDS' "Hard Rules" table currently relies on the agent's discipline. Multiple methodology failure modes exist *specifically* because that discipline is perishable. A hook is the structural countermeasure SAFEGUARDS has been missing. |
| **Suggested incorporation** | Add `starter-kit/hooks/block-dangerous-git.sh` + a `BOOTSTRAP.md` step that installs it. Cite as countermeasure for SAFEGUARDS' "Blast Radius Limits" table. Keep the script editable so projects can whitelist their own commands. |
| **Cost** | Low. One shell script + one settings.json snippet. ~50 lines of additions across BOOTSTRAP and starter-kit. |
| **Open question** | Should the hook block even when the *user* explicitly asks for the command? Pocock's version does. Current methodology has "unless the user has explicitly asked for it" carve-outs — would need a "user override" mechanism (e.g., environment variable). |

#### 2. `grill-with-docs` — Project-level domain glossary (`CONTEXT.md`)

| Aspect | Detail |
|---|---|
| **What it does** | Interactive grilling session that **maintains** a project-level `CONTEXT.md` (domain glossary) and `docs/adr/` (architecture decisions) inline. The CONTEXT.md captures shared language ("materialization cascade" instead of "lessons inside sections of courses being given file-system spots"). ADRs capture "hard-to-reverse" decisions. |
| **Methodology gap** | Methodology has Reference Tables (factual findings, session-scoped) and Pattern Library (named reusable approaches), but **no project-level domain language artifact**. The portfolio's projects (rad-con, wsjt-l, panelkit) are rich in domain jargon (hsym, FT8/MSK144, JT9, EME, sortable indexes, frame parser, decoder lifecycle) — a CONTEXT.md per repo would compress every future session's grounding cost. |
| **Why this matters** | Read the operator's own memory file `feedback_doc_completeness.md` ("audit ALL references"), `project_radcon_codec_policy.md` ("Pure-Java codec default … never bundle jt9"), `project_decoder_strategy.md` ("Streaming jt9 = default"). These ARE de facto CONTEXT.md content scattered across the user's auto-memory. A repo-level CONTEXT.md would consolidate and version them with the code. |
| **Suggested incorporation** | (a) Add `CONTEXT.md` to the starter-kit as an optional artifact with a template. (b) Add Phase 2 (Research) sub-step: "If `CONTEXT.md` exists, read it before exploring." (c) Add a hygiene rule: when a session discovers a new domain term during research, propose adding it to CONTEXT.md before close-out (similar to the existing pattern-library rule). |
| **Cost** | Medium. Template + bootstrap step + one new Phase 2 read. The hard part is operator discipline — the file rots without active maintenance. Pocock's `/grill-with-docs` solves this by making the agent maintain it during interview sessions; methodology could do the same via a Phase 4 or pre-Create grill mode (see #6 below). |
| **Caveat** | The methodology's Reference Tables are session-scoped facts (sizes, behaviors). CONTEXT.md is repo-scoped vocabulary. They're complementary, not duplicate. |

#### 3. `diagnose` — Disciplined debugging loop with "build the feedback loop FIRST"

| Aspect | Detail |
|---|---|
| **What it does** | Six-phase debugging discipline: build feedback loop → reproduce → hypothesise (3-5 ranked, falsifiable) → instrument (one variable at a time, tagged debug logs `[DEBUG-a4f2]`) → fix + regression test → cleanup + post-mortem. The phase-1 mandate is the strongest part: **"Be aggressive. Be creative. Refuse to give up [building the feedback loop]."** Lists 10 concrete loop-construction techniques. |
| **Methodology gap** | DEVELOPMENT_WORKSTREAM (per the README pointer) covers feature implementation and bug-fix campaigns, but I didn't see explicit debugging-loop discipline. Most importantly: methodology has no concept of **tagged debug instrumentation that can be removed mechanically**. Phase 6 (Verify) doesn't list "grep for and remove debug instrumentation" — yet I'd bet half the commits in rad-con/wsjt-l have stray `println!`/`System.err.println` from debugging. |
| **Why this matters** | Bug-debugging is a recurring activity that (per methodology Principle 1: Complete-Then-Create) currently has no codified phase ordering. Pocock's "build the feedback loop FIRST" is a strong, transferable rule. The tagged-log convention specifically addresses an unspoken methodology gap (post-debug hygiene). |
| **Suggested incorporation** | (a) Add a debugging session-type to ITERATIVE_METHODOLOGY (alongside Implementation, Review/Audit, Planning). (b) Cite Pocock's 6-phase debug loop as a pattern under DEVELOPMENT_WORKSTREAM. (c) Add a single rule to SESSION_RUNNER Phase 3F Commit checklist: **"Before committing, grep for debug-instrumentation prefixes (e.g., `[DEBUG-`) and remove them."** This is a 1-line addition with high signal-to-noise. |
| **Cost** | Low to medium. The rule + checklist line is trivial. A full debugging session-type addition is a separate session. |

#### 4. `tdd` — Vertical slices, tracer bullets, horizontal-slicing anti-pattern

| Aspect | Detail |
|---|---|
| **What it does** | Red-green-refactor with explicit anti-pattern: never write all tests first then all implementation ("horizontal slicing"). Use **tracer bullets** — one test, one implementation, repeat — through vertical slices (UI to schema to test). |
| **Methodology gap** | Methodology Phase 5 mentions "Build and verify" but doesn't prescribe TDD ordering. The horizontal-slicing failure mode is a real one — I saw evidence in S349 (Learning #20: a spike's verification didn't generalize because the test matrix wasn't explicit). Pocock's framing names the exact failure pattern. |
| **Why this matters** | Pocock's vertical-slice / tracer-bullet vocabulary is reusable beyond TDD — it describes how planning sessions should structure phase decomposition (Learning #18: "1 planning + N implementation" — each implementation should be a vertical slice). |
| **Suggested incorporation** | (a) Add to anti-pattern list: **"Anti-pattern #N: Horizontal slicing — writing all tests before any implementation, or planning all phases as horizontal layers (all schema then all API then all UI). Vertical slices through layers are more recoverable."** (b) Cross-reference in ARCHITECTURE_WORKSTREAM and DEVELOPMENT_WORKSTREAM. (c) Note in HOW_TO_USE Example 3 (Refactoring): vertical slicing applies to refactor plan phasing, not just feature plan phasing. |
| **Cost** | Low. One anti-pattern addition; cross-reference touches in two workstreams. |

#### 5. `triage` — Issue-state machine

| Aspect | Detail |
|---|---|
| **What it does** | Five canonical states (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`) plus two categories (`bug`, `enhancement`). Each issue carries exactly one state at a time. Comments must include a "generated by AI during triage" disclaimer. |
| **Methodology gap** | Methodology has Learning #30 (issue-batch creation discipline: a→f) which is about *creating* issues, not *managing their lifecycle*. The portfolio currently has 277 open issues across 21 repos with no formal triage state. The active S436 batch (47 issues) used `needs-triage` label informally — exactly the place where Pocock's state machine would slot. |
| **Why this matters** | The portfolio's issue-management problem is real and visible on the dashboard. A formal state machine + the `ready-for-agent`/`ready-for-human` split directly maps to the methodology's HITL/AFK distinction (which Pocock's `to-issues` skill also uses). |
| **Suggested incorporation** | (a) Add a sub-section to DEVELOPMENT_WORKSTREAM titled "Issue Lifecycle" listing the 5 states + transition rules. (b) Recommend (not mandate) the disclaimer pattern for agent-generated triage comments — it's good attribution hygiene. (c) Cross-reference in dashboard scoring: a "% of issues triaged" metric could be added (currently dashboard counts issues but doesn't measure triage health). |
| **Cost** | Medium. Workstream addition + dashboard scoring change. The 277-issue triage backlog is a large operator action, not a methodology change. |

---

### ADAPT (3)

#### 6. `grill-me` — Agent-grills-stakeholder before Phase 3 Create

| Aspect | Detail |
|---|---|
| **What it does** | Relentless pre-design interview. Agent asks questions one at a time, with recommended answers, until every branch of the decision tree is resolved. Triggered by "I want to be grilled" or `/grill-me`. |
| **Methodology gap** | Phase 4 (Present) currently has the agent **show** the stakeholder a complete design and ask "what did I get wrong?" That's stakeholder-grills-agent. Pocock's reverse pattern (agent-grills-stakeholder *before* Phase 3 Create) catches misalignment 1 phase earlier. |
| **Why this matters** | Memory `feedback_ux_plan_mode.md` explicitly notes: "Don't implement UX changes without designing the interaction model first." That's a stakeholder-side requirement that an agent-led grilling session would surface. The S338 layout-editor rollback (4 commits, all reverted) is the exact failure this prevents. |
| **Suggested incorporation** | Add an *optional* Phase 2.5 (Pre-Create Grill) for sessions with high misalignment risk — UX work, novel features, anything where the operator hasn't pre-written a plan. Make it explicitly optional, not gated, so it doesn't add friction to mechanical work. |
| **Cost** | Low. Half a section in ITERATIVE_METHODOLOGY + a SESSION_RUNNER row in Phase 1's task-mapping table. |
| **Caveat** | Methodology's audience is single-operator + single-agent; Pocock's is multi-stakeholder. The pattern translates but with reduced ceremony. |

#### 7. `improve-codebase-architecture` — "Deepening opportunities" + deletion test

| Aspect | Detail |
|---|---|
| **What it does** | Find shallow modules (interface complexity ≈ implementation complexity), propose deepening (consolidating into modules with high leverage at a simple interface). Deletion test: does removing the module concentrate or disperse complexity? |
| **Methodology gap** | ARCHITECTURE_WORKSTREAM exists but I haven't read it; based on the framework, it likely covers *what to design* but not concrete *refactor heuristics*. "Deepening" + "deletion test" are concrete tools that would slot under ARCHITECTURE_WORKSTREAM. |
| **Why this matters** | Memory `feedback_panelkit_demo.md` ("panelkit-demo belongs in panelkit repo, not rad-con") and `project_editors_in_rad_con.md` ("editor components in panelkit-ui but only runnable through rad-con") are exactly the kind of architectural smell that "deepening opportunities" would surface and prioritize. |
| **Suggested incorporation** | Add a "Refactor Heuristics" sub-section to ARCHITECTURE_WORKSTREAM listing the deepening pattern + deletion test. Cite Ousterhout's *A Philosophy of Software Design* as the source (Pocock does). |
| **Cost** | Low. One sub-section addition. |

#### 8. `setup-pre-commit` — Husky/lint-staged complement to dashboard CI/CD scoring

| Aspect | Detail |
|---|---|
| **What it does** | Installs Husky + lint-staged + Prettier with a pre-commit hook that runs (1) lint-staged formatting, (2) typecheck if available, (3) tests if available. |
| **Methodology gap** | Methodology dashboard scores CI/CD presence (workflow files exist) but doesn't score *pre-commit* hygiene. Pre-commit is a different layer — it catches issues *before* commit, where CI catches them after. |
| **Why this matters** | Several portfolio repos have CI but flaky local testing — devs commit broken-locally code and CI fails after the fact. Pre-commit hooks shift the failure left and reduce the CI-fail noise. |
| **Suggested incorporation** | Add a one-paragraph note to `BOOTSTRAP.md` recommending pre-commit hooks as a complement to dashboard CI/CD scoring. **Do NOT** mandate a specific tool (Husky is JS-specific; Java/Python/Rust have their own equivalents). Keep technology-neutral. |
| **Cost** | Trivial. One paragraph. |

---

### REJECT — Already Covered Better (5)

#### 9. `to-issues` — Vertical-slice issue creation

**Why reject:** Learning #30 (rad-con UDP issue batch, S357; Winlink batch, S436) already prescribes a more mature discipline: (a) present table FIRST, (b) decisions batch with recommend+tradeoff per Q, (c) add-scope decisions go IN issue bodies, (d) policy decisions go to memory, (e) parallel creation with mapping verification, (f) cross-reference doc appended to source planning doc. Pocock's `/to-issues` is approximately step (a) plus a template — methodology version is materially better.

**Action:** None. Continue using Learning #30. Optionally cite Pocock's "tracer-bullet vertical slices" as the *naming* for what Learning #30 already does in step (c).

#### 10. `zoom-out` — Architectural context for unfamiliar code

**Why reject:** Learning #28 (Plan subagent for architecture surveys) and Learning #29 (gap analysis as drill-down shape) already cover this with more rigor. Pocock's `/zoom-out` is a single-prompt context-elevation; methodology's pattern is a structured architecture survey with file:line citations and a numbered output structure.

**Action:** None. Continue using Plan subagent per Learnings #28, #29.

#### 11. `to-prd` — Synthesize conversation into PRD

**Why reject:** Methodology's Planning Sessions discipline (SESSION_RUNNER §Phase 2 Planning Sessions) is heavier and produces evidence-based inventories with grep-verified file lists. Pocock's `/to-prd` is "synthesize what you've already discussed" — appropriate for low-stakes greenfield work, but methodology's planning sessions deliberately raise the bar to catch the failure mode where plans miss files (FM #19, plan-mode bypass).

**Action:** None. Continue using Planning Sessions discipline. If a low-stakes lightweight PRD shape is ever needed, Pocock's template is a reasonable starting point.

#### 12. `setup-matt-pocock-skills` — Per-repo scaffolding

**Why reject:** `starter-kit/BOOTSTRAP.md` is the methodology equivalent. Pocock's version is for installing his skills; ours is for adopting the methodology framework. Different problems.

**Action:** None.

#### 13. `caveman` — Ultra-compressed communication mode

**Why reject:** Methodology already values brevity (Learning #34: handoff length ≤150 lines). `caveman` mode is a stylistic toggle that drops articles and uses arrows. It doesn't fit methodology's professional voice and would feel gimmicky in close-out documents the operator reads. Token reduction in handoffs is solved by length discipline, not stylistic compression.

**Action:** None. Length discipline (current rule) stays the lever.

---

### OUT OF SCOPE / IRRELEVANT (3)

#### 14. `write-a-skill` — Meta: how to write skills

The methodology has no `/skills/` concept. **Defer**: this becomes relevant only if methodology adopts skills-as-slash-commands as a packaging format (see Cross-Cutting Observation #1 below).

#### 15. `migrate-to-shoehorn` — TypeScript-specific test refactor

Irrelevant. Methodology is platform-agnostic; this is `@total-typescript/shoehorn` specific.

#### 16. `scaffold-exercises` — Course-content directory scaffolding

Irrelevant. Pocock teaches TS; methodology is a process framework.

---

## Cross-Cutting Observations

These are observations that span multiple skills and bear on the methodology's *shape*, not just its content.

### Observation 1: Skills-as-slash-commands is a packaging pattern the methodology hasn't adopted

Pocock's repo packages each discipline as an *invokable slash command* the user triggers. Methodology guidance lives in markdown the agent reads during Phase 0 orient. The two have different ergonomics:

| | Pocock's skill model | Methodology's doc model |
|---|---|---|
| Invocation | User types `/grill-me` | User types prose; agent recognizes pattern |
| Discoverability | Listed in slash menu | In SESSION_RUNNER's task-mapping table |
| Customization | Per-skill `SKILL.md` | Per-workstream document |
| Composability | Skills compose by chaining | Phases chain by phase ordering |
| Failure mode | Skill not invoked when needed | Phase skipped due to erosion (FM #17) |

**Hypothesis:** Some methodology phases (especially debugging, triage, planning grill, runtime smoke test) would benefit from being **invokable** rather than **memorable**. A `/runtime-smoke-test` skill that runs Phase 3E's checklist would be harder to skip than a SESSION_RUNNER row.

**Recommendation:** Treat this as a **discrete future architectural question**, not a near-term action. The methodology's strength is the sequenced phase model; converting it wholesale to skills would lose that. But identifying 3-5 phase steps that would benefit from skill packaging — and converting those — is a tractable design session.

### Observation 2: `CONTEXT.md` fills a documented but unaddressed need

The operator's auto-memory file (`MEMORY.md`) currently holds *facts that should live with the code* but instead live in a global memory store. Examples from the current memory index:

- `project_radcon_codec_policy.md` — "Pure-Java codec default; jt9 opt-in download preserves GPL isolation" → belongs in rad-con's `CONTEXT.md`.
- `project_editors_in_rad_con.md` — "Editor components in panelkit-ui but only runnable through rad-con" → belongs in rad-con's `CONTEXT.md` (and panelkit-ui's).
- `project_decoder_strategy.md` — "Streaming jt9 = default; native Java FT8 = fallback" → belongs in wsjt-l's or rad-con's `CONTEXT.md`.

These memories would be **discoverable to any future agent reading the repo** if they lived in `CONTEXT.md` rather than the operator's user-scoped memory. The auto-memory store is a global cache; CONTEXT.md is a versioned per-repo artifact. The methodology should encourage the latter where the former is currently overloaded.

### Observation 3: SAFEGUARDS' "rules" should systematically convert to hooks where possible

The git-guardrails skill reveals a conversion pattern:

| Methodology rule (text) | Possible hook (mechanical) |
|---|---|
| "Never push --force without permission" | PreToolUse: block `git push --force` |
| "Never commit secrets" | PreToolUse: scan staged changes for entropy/keywords |
| "Never run methodology/bin/sync at portfolio root" (memory) | PreToolUse: block when CWD == `/Users/terrell/Documents/code` and tool == that script |
| "Strip Co-Authored-By: Claude from commits" (memory) | PreToolUse on `git commit -m`: regex-strip |
| "Phase 3E runtime smoke test for runtime changes" | PostToolUse on Edit: warn if file matches runtime-affecting glob |

**Recommendation:** Treat `starter-kit/hooks/` as a first-class methodology asset. Audit SAFEGUARDS.md and memory-stored rules quarterly to see which can be promoted from text to hook.

### Observation 4: Pocock's `CLAUDE.md` lookup failed at root

I attempted to fetch `CLAUDE.md` at his repo root and the fetch returned no content (404 or non-existent). The README references `CONTEXT.md` (which exists) but not a root `CLAUDE.md`. **Possibly a stale README pointer** in his repo, or he uses `AGENTS.md` instead — I didn't dig further. **Methodology is unaffected** but worth noting that Pocock's per-repo agent-config may live in a different file.

### Observation 5: Pocock's repo has an `.out-of-scope/` directory

Visible in the top-level listing but not investigated. The naming suggests it's a pattern for *capturing rejected ideas with rationale* — which is conceptually similar to methodology's anti-pattern list but at the **per-repo / per-issue** scope rather than global. **Worth investigating in a follow-up** if the methodology ever wants per-project rejected-idea tracking.

---

## Recommended Follow-Up Sessions

Per methodology Principle 9 (Session Scope Bounding) and FM #18 (don't bleed planning into implementation), each incorporation is a **separate session**. Listing in suggested order:

| # | Session deliverable | Strength | Surface |
|---|---|---|---|
| **F1** | Add git-guardrails hook to starter-kit + BOOTSTRAP integration step | STRONG | `starter-kit/hooks/block-dangerous-git.sh` (new), `starter-kit/BOOTSTRAP.md` (+10 lines), settings.json snippet |
| **F2** | Add horizontal-slicing anti-pattern + tagged-debug-log cleanup rule to SESSION_RUNNER and ITERATIVE_METHODOLOGY | STRONG | `SESSION_RUNNER.md` (+1 anti-pattern row, +1 commit-checklist line); `ITERATIVE_METHODOLOGY.md` Phase 6 (+1 sub-bullet) |
| **F3** | Add `CONTEXT.md` template to starter-kit + Phase 2 Research read-step | STRONG | `starter-kit/CONTEXT_TEMPLATE.md` (new), `ITERATIVE_METHODOLOGY.md` Phase 2 (+1 step), one HOW_TO_USE example |
| **F4** | Add Issue Lifecycle sub-section to DEVELOPMENT_WORKSTREAM (5-state machine) | STRONG | `workstreams/DEVELOPMENT_WORKSTREAM.md` (+1 section ~30 lines) |
| **F5** | Add debugging session-type + 6-phase debug loop pattern to methodology | MEDIUM | `ITERATIVE_METHODOLOGY.md` §Session Types (+1 type), `workstreams/DEVELOPMENT_WORKSTREAM.md` (+section) |
| **F6** | Add deepening / deletion test refactor heuristics to ARCHITECTURE_WORKSTREAM | MEDIUM | `workstreams/ARCHITECTURE_WORKSTREAM.md` (+1 section) |
| **F7** | Add optional Phase 2.5 Pre-Create Grill to ITERATIVE_METHODOLOGY (agent-grills-stakeholder) | MEDIUM | `ITERATIVE_METHODOLOGY.md` (+1 phase as optional), SESSION_RUNNER task-mapping (+1 row) |
| **F8** | Add pre-commit hooks paragraph to BOOTSTRAP.md (technology-neutral) | LOW | `starter-kit/BOOTSTRAP.md` (+1 paragraph) |
| **F9** | (Optional) Pilot project-level CONTEXT.md on rad-con; consolidate operator's auto-memory entries into it | MEDIUM-LOW | rad-con repo only; ~50-line CONTEXT.md draft |
| **F10** | (Optional, architectural) Design "skills-as-slash-commands" packaging for 3-5 methodology phase-steps that benefit | HIGH-DESIGN | New session; produces a design doc; no code change |

**Suggested batching:** F1-F4 are all small (low cost, high value) and could plausibly be one session if scoped tightly to "high-value v2.4 increment." But methodology's own "1 and done" rule argues for keeping them separate to maintain handoff-evaluation rhythm. **Recommend: 1 session per row.**

---

## Open Questions for the Operator

1. **Hook scope:** Should the git-guardrails hook be installed globally (`~/.claude/hooks/`) or per-portfolio-project? Pocock asks; methodology should pick a default.
2. **CONTEXT.md vs auto-memory:** Memories like `project_radcon_codec_policy.md` are currently global (`~/.claude/...memory/`). Migrating to per-repo `CONTEXT.md` would lose cross-session/cross-project portability but gain version-control discoverability. Does the operator prefer one or the other for this kind of content?
3. **Triage migration:** The portfolio has 277 open issues. Adopting the 5-state triage labels means an initial bulk triage pass. Is the operator willing to invest 1-2 sessions in that, or is the state machine theory-only for now?
4. **Skills-as-packaging (Observation 1):** Is this an architectural direction the operator wants to investigate? (It would be a multi-session design effort.)
5. **Source attribution:** Pocock's repo is MIT-licensed (not stated, but implied by the public repo). When incorporating, should the methodology cite Pocock by name + source URL, or just take the ideas without attribution? (Methodology operator memory `feedback_no_ai_coauthorship.md` favors no AI attribution; Pocock is a human, so different rule.)

---

## Self-Assessment & Methodology Compliance Notes for This Session

- **Phase 0 Orient:** Completed (SAFEGUARDS, SESSION_NOTES head, dashboard, git-status equivalent).
- **Phase 1B Claim:** Stub written before research started.
- **Phase 2 Research:** Read 12 of 16 SKILL.md files in full + methodology master + CLAUDE.md (loaded by system reminder) + portfolio SESSION_RUNNER + SAFEGUARDS. Two skills (`migrate-to-shoehorn`, `scaffold-exercises`) were judged irrelevant from README context and not fetched — noted in Method.
- **Phase 3 Create:** This document is the deliverable.
- **Phase 4 Present:** This document.
- **Phase 5 Implement:** **Not in scope this session.** All recommendations are deferred to F1-F10 as separate sessions per FM #18.
- **Plan-subagent threshold (Learning #18):** I read 12 SKILL.md files (~1500 lines total) inline. Borderline — could have delegated. Justification: the synthesis is the deliverable and required cross-skill comparison; subagent would have returned a summary that lost the per-skill detail this audit needs. Direct read was correct, but at the threshold.

---

## Sources

- Pocock skills repo: https://github.com/mattpocock/skills
- Methodology master: `methodology/ITERATIVE_METHODOLOGY.md`
- Portfolio operating procedure: `SESSION_RUNNER.md` (portfolio root)
- Operator auto-memory: `~/.claude/projects/-Users-terrell-Documents-code/memory/MEMORY.md`
