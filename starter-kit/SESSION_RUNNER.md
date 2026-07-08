# Session Runner

**This is your operating procedure. Follow it step by step. Do not improvise.**

Every session has exactly ONE deliverable. When it's done, you close out. You do not start the next thing. The deliverable MAY be a **verified vertical slice** — one capability end to end — but only under the gates in §Vertical Slice Sessions below. One capability never means a second capability.

---

## Phase 0: Orient

**Change nothing — read only, except the single append-only ledger backfill defined in step 6 (it records commits that already exist).**

1. Read `SAFEGUARDS.md` — **in full, not skimmed. Every section.**
2. **Confirm `pwd` and which `SESSION_NOTES.md` you are about to read/write** (see the session-notes boundary rule below), then read it — focus on the ACTIVE TASK section at the top
3. Check GitHub Issues (`gh issue list`) if the project has a repo — understand current priorities. Fall back to `BACKLOG.md` if no repo exists. (BACKLOG.md should contain only open work items — for history see `CHANGELOG.md`, for feature inventory see `ROADMAP.md`.)
4. Run: `git status`, `git log --oneline -5`, `git diff --stat`
5. Run: `python3 methodology_dashboard.py` — refresh the project health dashboard. Leave `dashboard.html` open in a browser; it auto-refreshes every 60 seconds.
6. **Check for ghost sessions, then reconcile the ledger:** Compare the session number in SESSION_NOTES.md against `git log`. If there are commits between the last documented session and now that don't correspond to any session notes, report: "Detected [N] undocumented session(s) between Session [X] and now. Commits: [list]. No session notes exist for this work." **Then reconcile `CHANGELOG.md` against `git log`** — the authoritative-ledger backstop for commits a close-out gate never reached (a crash before Phase 3F, an out-of-band commit, a prior in-progress hand-off). Reconcile the ledger of the repo you confirmed in step 2 (one per repo when a session spans several — see the session-notes boundary rule below). Compute the undocumented set (mechanics in the ledger-reconcile note below); any commit in it — or a prior stub still marked `CHANGELOG: pending` (Phase 1B) — is an unrecorded action (failure mode #27). **Backfill it now, during this step, before the report and the STOP** — the one write Phase 0 permits (see the note below). **Also reconcile `HANDOFFS.md` the same way:** compute its frontier (`git log -1 --format=%H -- HANDOFFS.md`) against the same commit history; the newest receipt missing for a session that left commits, or still marked `status: pending` (an unfinished Phase 1B stub), is the same kind of unrecorded action. Reconstruct a best-effort block from `git log` (plus `SESSION_NOTES.md` if it survived) marked `status: reconciled`, and note the gap in the report — during this step, before the report and STOP (mechanics in the note below).
7. **Report findings to the user:**
   - Current branch and clean/dirty state
   - What the last session was doing
   - Current milestone and active task from GitHub Issues (or BACKLOG.md if no repo)
   - Any uncommitted changes
   - Ghost session detection **and ledger-reconcile** results (step 6) — any undocumented commits since the `CHANGELOG.md` frontier, and the backfill entry made (or the recorded "no CHANGELOG" opt-out)
   - Dashboard health score and any risk flags
   - Build status if known
8. **STOP. Wait for the user to give you a task.**

DO NOT skip the report. DO NOT start working. DO NOT assume you know what to do.

**Even if the user's first message contains a task** (e.g., "Implement the following plan"), Phase 0 is still mandatory. That phrase comes from Plan Mode's auto-generated preamble — it does NOT mean start coding. The orientation report exists for the user's benefit — it establishes shared understanding of the current state. The user needs to see the report and confirm before work begins. A task in the prompt does not mean Phase 0 is complete. Complete all 8 steps, then the user will re-state or confirm the task in Phase 1.

**Steps 1-3 are READS, not skims.** Every step exists because a session failed without it.

**⚠ Ledger reconcile — the one write Phase 0 permits.** Phase 0 is otherwise read-only, but an authoritative ledger that is *true when you read it* needs one exception: backfilling history that already happened. This is a repair of the record — append-only documentation of commits that already exist — done **during step 6, before the Phase 0 report and STOP** (it needs no assigned task; it only records existing commits) and surfaced in that report. If step 6 finds undocumented commits:

1. **Check for a committed ledger first** — `git log -1 --format=%H -- CHANGELOG.md`. If this is **empty**, no commit has ever recorded the ledger: self-provision (step 4) and reconcile from the repo root — do **not** treat an empty result as "current" (that is the original hole). If it returns a commit, that is the **frontier**.
2. **List the gap** — commits since the frontier with no entry: `git log --no-merges <frontier>..HEAD` (the same count `git rev-list --count --no-merges <frontier>..HEAD` drives the dashboard's ledger-lag signal).
3. **Backfill** — prepend one entry per undocumented span, **source-tagged so the audit `grep -E '\[(issue #|BL-|ad hoc)' CHANGELOG.md` still enumerates it** (best-recoverable source; default `[ad hoc]`), noting provenance and the commit range: `### YYYY-MM-DD · [ad hoc] Backfilled (reconcile-on-read): undocumented commits <X>..<Y> — <summary>`. Commit it on its own (`docs(changelog): backfill …`), separate from this session's later deliverable. If a commit's intent is unclear, report it and ask before summarizing.
4. **Self-provision if absent (D3)** — if step 1 found no committed ledger and `CLAUDE.md` records no "no CHANGELOG" opt-out, create `CHANGELOG.md` from the bootstrap seed (or commit an existing uncommitted seed), record pre-ledger history as a single pointer line, and reconcile forward. A missing ledger on a repo with real history is a defect, never a silent skip.

Two no-ops only: a **non-empty** frontier with an empty `<frontier>..HEAD` (no undocumented commits — note that non-commit actions such as releases, tags, PR opens, issue closes, and access grants leave no commit and so are the Phase 3F write-gate's / failure-mode-#27 responsibility, not reconcile's), or a project that records a "no CHANGELOG" decision in `CLAUDE.md`. The backfill records what past sessions did; it does not become this session's deliverable or license work beyond the one assigned task (failure mode #17).

**The same mechanics reconcile `HANDOFFS.md` in parallel — the receipt is folded into the one write Phase 0 permits, not a second write.** Compute its frontier the same way (`git log -1 --format=%H -- HANDOFFS.md`); a frontier block still marked `status: pending` (an unfinished Phase 1B crash breadcrumb) or a commit in the undocumented set (item 2 above) with no receipt at all is the unrecorded counterpart. Reconstruct a best-effort block from `git log` (plus `SESSION_NOTES.md` if it is still present), mark it `status: reconciled` — never `complete`, since this session did not do that work — and note the gap in the report. As with the ledger, this only catches sessions that left a commit or a 1B stub; a session with no commit and no claim leaves nothing to reconcile.

**⚠ Session-notes boundary — which `SESSION_NOTES.md` do you write?** A session writes notes to the `SESSION_NOTES.md` of the directory it runs in. **This project's `SESSION_NOTES.md` records work done in THIS project.** A portfolio-oversight / methodology session (run from the oversight directory above the project repos) records its work in the **portfolio-oversight** dir's own `SESSION_NOTES.md`, never in a project's — and vice versa: project engineering run from a project directory writes that project's notes, full stop. Before step 2, confirm `pwd` and which `SESSION_NOTES.md` you are reading/writing. This boundary exists because same-named methodology artifacts (`SESSION_NOTES.md`, `methodology_dashboard.py`) are copied per-project with no canonical owner; logging project work at the portfolio level (or vice versa) is misfiling, and the next session inherits a stale, cross-contaminated log.

---

## Phase 1: Receive Task

The user will direct you. Interpret their prompt and identify:

- **The deliverable:** What ONE thing are you producing this session?
- **The workstream doc:** Which methodology document governs this work?

Common task-to-workstream mappings:

| User Says | Deliverable | Workstream Document |
|-----------|-------------|---------------------|
| "Design the [X]" | One design document | `docs/methodology/workstreams/DESIGN_WORKSTREAM.md` |
| "Implement [feature/plan]" | One implementation | `docs/methodology/workstreams/DEVELOPMENT_WORKSTREAM.md` |
| "Audit [X]" | One audit report | `docs/methodology/workstreams/AUDIT_WORKSTREAM.md` |
| "Plan [feature/migration]" | One architecture document | `docs/methodology/workstreams/ARCHITECTURE_WORKSTREAM.md` |
| "Fix [bug campaign]" | One fix campaign pass | `docs/methodology/workstreams/DEVELOPMENT_WORKSTREAM.md` |
| "Review [code/PR]" | One review document | The review produces a plan; follow DEVELOPMENT_WORKSTREAM for structure |
| "Write/draft/audit [paper/section/dimension]" | One paper section, one audit pass, or one corpus retrieval pass | `docs/methodology/workstreams/RESEARCH_DOCUMENTATION_WORKSTREAM.md` |
| "Grill me" / "I want to be grilled" / "Decide before designing" | A decisions list with stakeholder answers, then the Phase 3 design | `docs/methodology/ITERATIVE_METHODOLOGY.md` §Phase 2B (then continue in the relevant workstream — typically DESIGN or ARCHITECTURE). The grill itself is run via `/grill-me` — see [`RECOMMENDED_SKILLS.md`](RECOMMENDED_SKILLS.md). |
| Multi-phase plan appears in prompt (from Plan Mode or user) | Plan document written to `docs/planning/` with evidence-based inventory | Planning workstream |

**⚠ Plan Mode exit trap.** Plan Mode generates "Implement the following plan" as its preamble. **This does NOT mean "start coding."** When a multi-phase plan appears in the prompt — regardless of the preamble wording — the deliverable is writing the plan document with grep-based evidence and per-phase criteria. Orient first. The plan is a DRAFT until evidence-verified. See Planning Sessions below.

**⚠ Multi-session campaign check.** If your work cannot be produced cleanly in one session even after correct decomposition — paper-wide verification, repository-wide hardening, multi-module familiarization — look for a matching `*_CAMPAIGN.md` in `workstreams/`. If one exists, your session is one unit within its campaign: read the campaign template and follow its planning → execution → consolidation sequence. If none exists but the work has that shape, raise it before starting work — a planning session may be needed to either adopt an existing campaign or draft one. See [`ITERATIVE_METHODOLOGY.md` §Multi-Session Campaigns](docs/methodology/ITERATIVE_METHODOLOGY.md#multi-session-campaigns).

**If no workstream document exists for the task type, follow the master framework:** `docs/methodology/ITERATIVE_METHODOLOGY.md`, phases 1-6.

State your understanding back to the user: *"I'm going to [deliverable] following [workstream doc]. I'll close out when that's done."*

### 1B: Claim the Session (MANDATORY)

**Immediately after receiving a task — before any technical work — write a stub to `SESSION_NOTES.md`:**

```markdown
### What Session [N] Did
**Deliverable:** [task description] (IN PROGRESS)
**Started:** [date/time]
**Status:** Session claimed. Work beginning.
**Ledger:** `CHANGELOG: pending` — set at claim; this session's actions are recorded in `CHANGELOG.md` at Phase 3F. Until close-out, this line is the crash breadcrumb for the next session's reconcile.
```

**Also open the close-out receipt in `HANDOFFS.md`.** Prepend a ` ```handoff ` block with `status: pending` and the fields you can fill now (`session`, `date`, `active_task`), and commit it with this claim. A committed `status: pending` receipt is a durable crash breadcrumb — like `CHANGELOG: pending`, but one the next session's Phase 0 reconcile finds even from a fresh clone. Phase 3D overwrites it to `status: complete`. See the block format in `HANDOFFS.md` itself.

**Why this exists:** Ghost sessions — sessions that crash, hit context limits, or end without writing notes — leave zero trace. The next session has no idea what happened, what was attempted, or what state was left behind. By writing a stub FIRST, even a catastrophic failure leaves evidence. This stub is overwritten during Phase 3D with the full handoff. The `CHANGELOG: pending` marker is a best-effort ledger breadcrumb: a session that crashes *before* close-out leaves it in place, so the next session's Phase 0 reconcile (step 6) sees both the `git log` gap and the explicit marker. The always-reliable backstop is the `git log` gap itself — it catches a crash even in the Phase 3D→3F window, after the handoff has overwritten the stub but before the ledger entry is written.

**This is a structural control, not a suggestion.** Mandatory close-out steps are how clean-delivery streaks don't collapse: each protocol step that gets shaved off makes the next step easier to shave off.

---

## Phase 2: Execute

1. Read the workstream document identified in Phase 1
2. Follow its phases sequentially, respecting hard gates
3. Execute ONE deliverable only
4. If blocked, ask. Don't improvise around blockers.
5. If you catch yourself thinking "while I'm at it..." — STOP. That's scope creep. Commit what you have and note it for a future session.

### Planning Sessions

**⚠ The plan is the deliverable. Do not start implementing it.** Write the plan document to `docs/planning/`, commit it, close out. Implementation happens in a separate session.

**Set your agent's deepest available reasoning mode at session start** (capability: maximum reasoning depth — e.g. `/effort max` where supported). A plan is low-reversibility and high-compounding: its errors propagate into every executor session that trusts it (`ITERATIVE_METHODOLOGY.md` §Matching Reasoning Effort to Stakes).

**A plan is a deliverable, not a preamble.** When the session's deliverable is a plan (architecture doc, migration plan, multi-phase implementation plan), additional discipline applies:

#### Evidence-Based Inventory (MANDATORY for deletion/migration/rename plans)

For any plan that involves deleting, renaming, migrating, or moving code:

1. The plan MUST include a **grep-based inventory** of all references to the affected symbols, files, components, keys, imports, and type names.
2. Run the actual searches. List every matching file. The plan's "files to change" list comes from search results, not architectural knowledge.
3. Search terms should include: file names, class names, function names, import paths, key prefixes, component registration names, and any aliases.
4. The inventory IS the plan's verification step — equivalent to "grep for dangling references" in execution sessions.

**A plan that lists files to change without having searched for them is an assumption, not an inventory.** The executor will trust the plan. If it's wrong, they'll miss files — exactly the failure this requirement prevents.

**In practice:** a planning session wrote a deletion plan listing the "obviously named" files but missed 10+ scattered references — because it never ran `grep` across the codebase. The executor session had to discover all of them independently. Two grep commands during the planning session would have found them all.

#### Per-Phase Completion Criteria

Every phase in a multi-phase plan must state:
- **What DONE looks like** — concrete output, not "implement Phase N"
- **Verification commands** — how the executor confirms completion (build, test, grep)
- **Session boundary** — "This phase is one session. Close out when done."

Without explicit completion criteria, executors don't know when to stop and tend to bundle adjacent phases.

#### Planning Session Checklist

Before closing out a planning session, verify:

- [ ] Deepest available reasoning mode set at session start
- [ ] Plan document written with file paths and line numbers
- [ ] Grep-based inventory completed for all affected symbols (if deletion/migration/rename)
- [ ] Each phase has explicit completion criteria and verification commands
- [ ] Each phase marked as "separate session" with a STOP point
- [ ] Close-out: evaluate predecessor, self-assess, write the `HANDOFFS.md` receipt (Phase 3D), record the `CHANGELOG.md` ledger entry (Phase 3F, failure mode #27), commit, STOP

### Vertical Slice Sessions

The unit of "1 and done" is one **intent**, not one layer. When ALL four gates below are satisfied, the session's ONE deliverable may be a **verified vertical slice** — one capability end to end (e.g., data + service + client + tests) — instead of one horizontal layer. The allowance ADDS a gate; it removes no step: Phase 0 orientation, the Phase 1B stub, and all Phase 3 close-out steps are unchanged and non-negotiable (see FM #17's anti-erosion clause).

**Gates — all four, no substitutions:**

- **(a) Pre-declared contract.** The full layer set is enumerated in a plan-mode contract approved BEFORE any code — normally in a prior planning session, which satisfies the gate. The implementing session re-verifies the contract at Orient (state unchanged since approval); drift voids the contract and the slice reverts to a new plan-mode round.
- **(b) Checkpoint commit at every layer boundary.** The 5-file cap (`SAFEGUARDS.md` §Blast Radius Limits) is *per-commit* and unchanged — a slice may touch more than 5 files across the session, never more than 5 between checkpoint commits.
- **(c) Full verification at every layer boundary.** The complete build/test matrix plus the exhaustive grep inventory runs at EACH boundary, not once at the end.
- **(d) Faithful verification, per surface.** "All tests ran" is not automatically faithful: a suite that runs with privileges the production path doesn't have (e.g., bypassing row-level security), or a layer that hand-maintains a duplicate enum/DTO, passes green while broken. Each surface in the slice must establish that its verification actually exercises the behavior being claimed. Faithfulness is established, never assumed.

**The allowance is evidence-gated, not self-certified.** It holds only while the gate (c) artifacts actually land in-session. If a layer boundary's evidence is missing, the session reverts to horizontal scope at the last clean checkpoint commit and closes out there. That revert still closes out in full: the work that *did* land is an action, so its `HANDOFFS.md` receipt and its Phase 3F `CHANGELOG.md` ledger entry are owed exactly as in any close-out — mark the reverted remainder in-progress, do not silently drop it (failure mode #27). Declaring that high-parallelism verification is available is not the gate; the per-boundary artifacts are.

**Recoverability — not verifiability — is the ceiling on slice size.** Parallel verification does nothing for crash/reversal recovery, and larger slices make it worse: a crash mid-slice strands N layers, not 1. The slice must map to ONE reversible intent with per-layer commits.

**Boundaries that stay separate sessions (never collapsible into a slice):**

- Irreversible prod/DB migration gates
- Operator-approval gates (designs, data models, plans)
- Live verification requiring real accounts or physical devices
- Cross-toolchain cutover atomicity (two build toolchains flipping at once)
- The recoverability/reversal-rollback ceiling above
- Faithful-verification gates that cannot be established in-session (gate d)
- The plan ↔ implementation boundary (FM #18) — bundling *layers of one slice* is fine; bundling a *plan with its code* is not

**The slice test (FM #26):** does a single plan-mode contract from a prior session enumerate exactly this layer set, all of the same capability? If the layers span two capabilities, two platform cutovers, or a plan + code — it is not a slice. Split it.

High-parallelism verification introduces its own regression vector: sub-agents emit confident-but-wrong claims. Apply adversarial refutation to your own agents' output, not only to the primary work.

*(Adopted via issues [#20](https://github.com/KJ5HST/methodology/issues/20) and [#21](https://github.com/KJ5HST/methodology/issues/21).)*

---

## Phase 3: Close Out

**This phase is AUTOMATIC. When your deliverable is complete, execute ALL of these steps without being asked.**

**Do not ask "shall I continue?" Do not offer to start the next thing.**

**The close-out is not cleanup — it is the compounding mechanism.** The quality of your close-out directly determines the quality of the next session. You will be judged on how well you set up your successor, just as you judged your predecessor in step 3A.

### 3A: Evaluate the Previous Session's Handoff

**This step comes FIRST, before self-assessment.** Read what the previous session left you in `SESSION_NOTES.md` and score it:

- **Score (1-10):** How well did the previous session's handoff prepare you for success?
- **What helped:** Which specific notes, file references, or warnings saved you time?
- **What was missing:** What did you have to figure out that should have been documented?
- **What was wrong:** Any claims in the handoff that turned out to be inaccurate?
- **ROI:** Did reading the handoff save more time than it cost?

**Write this evaluation to `SESSION_NOTES.md`** under a "Session N Handoff Evaluation (by Session N+1)" heading. The previous session's author cannot improve if they never see the score.

**Re-read the actual files before writing claims.** Do not write gap analysis from memory of files you read earlier in the session. Memory degrades across a long session. If you haven't read the file in the last 5 minutes, read it again now.

*Note: Skip this step on Session 1 — there is no previous handoff to evaluate.*

### 3B: Self-Assess

Compare your work to the standard set by previous sessions in this workstream:

- Did you complete all research before creative work?
- Did you read implementations, not just descriptions?
- How many stakeholder corrections were needed?
- What did you get right? What did you get wrong?
- Did you meet or exceed the quality bar of previous sessions?

### 3C: Document Learnings

Capture what this session learned so the next session inherits it. Always update the relevant workstream document for any workstream-level pattern or anti-pattern. Then record session learnings in the right place for your audience:

- **Adopter project** (you copied this `SESSION_RUNNER.md` from the methodology repo): put project learnings in your `CLAUDE.md` → **Project-Specific Methodology Adaptations** → **Project-specific Learnings** subsection. Do NOT edit the "Learnings (added by sessions)" table further down in this file — `SESSION_RUNNER.md` is synced from canonical and must stay byte-identical, or local edits will block future syncs (see BOOTSTRAP, "Customizations Go in CLAUDE.md, Not in Synced Files"). Agents read `CLAUDE.md` at session start, so a learning recorded there is applied on top of the base protocol.
- **Canonical methodology repo** (you are dogfooding the framework on itself): record framework-level learnings by appending a new row to the "Learnings (added by sessions)" table further down in this file. This repo has no `CLAUDE.md` Adaptations section because the SESSION_RUNNER table is its learnings home; the seed rows there are real framework learnings, not placeholders. Append new rows — do not edit or overwrite existing ones.

Capture, wherever it lands:

- What you did, how you did it, and why
- Files referenced during this session
- Initial mistakes and how you recovered
- New patterns discovered (named, with "when to use")
- New anti-patterns discovered (numbered, with root cause)
- Performance metrics compared to previous sessions

**The goal: the next session performs better by learning from yours.**

### 3D: Write Handoff Notes

Update `SESSION_NOTES.md`. **You will be judged on this.** The next session will score your handoff in their Phase 3A, just as you scored your predecessor's. Write notes that would earn a 9 or 10.

**Write to files FIRST, then summarize verbally.** A verbal summary that isn't written down is worthless — the next session can't read the conversation.

#### Minimum Handoff Requirements (ALL mandatory)

A handoff that doesn't include ALL of the following is a protocol violation. "Pick next from backlog" is not a handoff — it's an abdication.

| # | Requirement | Bad Example | Good Example |
|---|-------------|-------------|--------------|
| 1 | **ACTIVE TASK updated** with current state | "Done." | "Task: Auth refactor. Status: Phase 1 complete. Phase 2 not started." |
| 2 | **What was done** with commit hashes | "Fixed stuff" | "Fixed 3 auth bugs (token refresh, session expiry, CORS). Commit `a1b2c3d`." |
| 3 | **What's next** — specific and actionable | "Pick next from backlog" | "Implement Phase 2 of auth-plan.md. Start with `SessionManager.java:245`." |
| 4 | **Key files** with full paths and line numbers | (none) | "SessionManager.java:245-320 (token logic), AuthFilter.java:88-95 (CORS)" |
| 5 | **Gotchas** the next session should watch for | (none) | "Token refresh has a 5s race window — see SessionManager.java:267" |
| 6 | **Self-assessment score** written to file | (verbal only) | Written to SESSION_NOTES.md with +/- breakdown |

**A handoff missing items 1-5 will score ≤4/10 by the next session.** This directly causes the next session to waste time on discovery that should have been documented.

#### Write the six as a durable receipt

Complete this session's ` ```handoff ` block in `HANDOFFS.md` (opened as a `status: pending` stub in 1B): set `status: complete` and fill the six requirements as its fields (the sixth *is* `self_score`), plus `predecessor_score` from the Phase 3A evaluation. `SESSION_NOTES.md` is the transient scratchpad (overwritten next session); the `HANDOFFS.md` receipt is the **durable, machine-checkable proof the handoff was written** — the canonical-only `bin/check-handoff` (copy it into your `bin/` if you want the structural check) asserts its presence and completeness, never its quality (a green check is not a good handoff — that stays the next session's 3A score). The dependable backstop is Phase 0 reconcile, which catches a skipped receipt at the next Orient with no tooling at all.

**Never claim credit for work you didn't do.** If a plan was provided as input, say "Plan was input, not output." If you didn't produce a deliverable, say "No deliverable produced." Fabricating accomplishments or attributing quotes the user didn't say is a trust-destroying failure.

**Never write "need to verify" in a handoff gap.** If you don't know, read the file NOW. Deferred verification is deferred work — it belongs in your session, not the next one.

### 3E: Runtime Smoke Test

**If your deliverable changes runtime behavior** — startup configuration, service registration, integration wiring, dispatch, plugin loading, config resolution — launch the application before committing and confirm the change is active. **"Build clean" is necessary but not sufficient for runtime changes.**

Run `/verify` (Claude Code built-in) for the smoke test, or `/run` to drive the application directly — see [`RECOMMENDED_SKILLS.md`](RECOMMENDED_SKILLS.md). When the skills are unavailable, the rule applies manually: start the application, scan startup logs for errors or unexpected fallback paths, confirm your deliverable is active and not silently overridden.

If you cannot runtime-verify (requires hardware, external service, CI), state this explicitly in session notes. Do not silently skip. A self-assessment that notes "no runtime verification" without treating it as a defect is failure mode #24 (build-passes-ship-it) in action.

### 3F: Commit

Before committing:

- **Record every action in the authoritative ledger.** Append a dated, source-tagged entry to `CHANGELOG.md` for **each action this session took** — one per commit *and* per non-commit action (release, tag/branch op, PR open, upstream issue close, access grant, decline/grooming decision): `### YYYY-MM-DD · [issue #<N>] | [BL-<N>] | [ad hoc]` + a one-line outcome, newest on top. For a completed backlog item, remove it from `BACKLOG.md` in the same commit. If `CHANGELOG.md` is absent, create it from the bootstrap seed — the only exemptions are a project that records "no CHANGELOG" in `CLAUDE.md` and a session whose diff is empty with no action taken. "Too small to log" is failure mode #27, not an exception (FM #17: the ledger records what the session did; it does not authorize a second deliverable).
- **Remove debug instrumentation added during this session.** Tagged debug logs (per `/diagnose` — see [`RECOMMENDED_SKILLS.md`](RECOMMENDED_SKILLS.md)) make this a single grep; ad-hoc prints make it manual. Either way, do not commit instrumentation that was meant to be temporary.
- **Verify cross-references added or changed this session.** If you added a citation, index entry, glossary term, or cross-reference between files, or modified a numbered set (FMs, principles, phases, anti-patterns, learnings), grep each cited destination to confirm it resolves and grep nearby prose for set-size claims that may have drifted. `git diff` shows the present-side edit, not the missing destination (Learning #7).

Then commit all changes with a descriptive message.

### 3G: Report and STOP

Tell the user:

- Summary of the deliverable
- Self-assessment highlights (what went well, what didn't)
- Previous session's handoff score and key findings
- What the next session should do

**Then STOP. The session is over.**

---

## Known Failure Modes

These are documented tendencies. The agent must actively guard against them.

| # | Tendency | What Happens | Countermeasure |
|---|----------|-------------|----------------|
| 1 | **Eager to start** | Skip Orient and jump to doing things | Phase 0 is mandatory. The user must speak before work begins. |
| 2 | **Keep going** | Finish the deliverable and immediately start the next thing | "1 and done." Close-out fires when the deliverable is complete. |
| 3 | **Skim documents** | Read 500 lines and retain the gist, not the steps | Follow the checklist step by step, not from memory of the gist. |
| 4 | **Assume context after compaction** | Think "I remember what I was doing." Don't. | Trust SESSION_NOTES.md, not memory. Re-read the files. |
| 5 | **Equate helpfulness with volume** | Do more because more feels more helpful | Quality > quantity. One excellent deliverable beats two mediocre ones. |
| 6 | **Skip close-out** | Self-assessment and prompt updates feel like cleanup, not real work | Close-out is the most valuable phase — it's how the system improves. It is **not done until the durable `HANDOFFS.md` receipt is written** (Phase 3D): a report you only speak leaves no evidence of its own absence, whereas a missing or `status: pending` receipt is caught at the next Orient's reconcile. |
| 7 | **Ask the user to solve process problems** | "What should I do?" instead of reading the docs | Read the docs. Follow the process. Only ask when genuinely blocked on content. |
| 8 | **Redesign during implementation** | See something to improve and act on it mid-task | Commit first. Note it for a future session. Stay on the approved plan. |
| 9 | **Task-in-prompt bypass** | User's first message contains a task, so Phase 0 feels implicitly complete | Phase 0 exists for the USER, not the agent. Complete all 8 steps even when the task is obvious. |
| 10 | **Skip handoff evaluation** | Self-assessment feels sufficient; evaluating the previous session feels like extra work | Phase 3A is a mandatory structural step. The evaluation IS the compounding mechanism. |
| 11 | **Gaps from memory** | During close-out, write gap analysis from memory of files read earlier. Memory degrades. Claims turn out wrong. | Before writing ANY claim in close-out: "Have I read the file that confirms this in the last 5 minutes?" If no → read it now. |
| 12 | **Workstream transfer amnesia** | Build good discipline on one workstream, then switch and repeat old mistakes | Discipline doesn't auto-transfer. When switching workstreams, consciously re-apply the close-out checklist. |
| 13 | **Literal minimum** | When asked to do X, do exactly X and nothing logically implied by X | Before acting: "What is the user's UNDERLYING intent?" Do the complete job on the first pass. |
| 14 | **Ghost session** | Session crashes, hits context limits, or ends without writing ANY session notes. Next session has zero context. | Phase 1B (Claim the Session) is mandatory — write a stub to SESSION_NOTES.md BEFORE starting technical work. Even catastrophic failures leave a trace. |
| 15 | **Minimal handoff** | Session writes "Done. Pick next from backlog." — technically a handoff, functionally useless. Next session starts blind. | Phase 3D has 6 minimum requirements. A handoff missing key files, specific next steps, or gotchas is a protocol violation that will score ≤4/10. |
| 16 | **False credit / fabrication** | Session claims credit for work it didn't do, or attributes quotes the user never said. Trust destruction. | Never claim deliverables you didn't produce. If a plan was input, say so. If you produced nothing, say so. |
| 17 | **Protocol erosion** | Each session shaves off "just one" protocol step. Individually minor. Over 5-10 sessions, the whole protocol collapses. Scores drift from 9/10 to 1/10. | The protocol is not optional, advisory, or improvable-by-subtraction during a session. Every step exists because a previous session failed without it. If you think a step is unnecessary, that's the erosion happening. Do the step. Citing a "deeper dive" or any high-parallelism mode to skip an orientation, stub, or close-out step — OR to bundle multiple capabilities — is protocol erosion (FM #17), not the vertical-slice model. The vertical-slice allowance ADDS a gate; it removes no step. Phase 0 orientation, the Phase 1B stub, and all Phase 3 close-out steps are unchanged and non-negotiable. |
| 18 | **Planning-to-implementation bleed** | A session produces a plan, then immediately begins implementing it. Or the next session bundles multiple phases because "the plan is done, implementation is easy." | A planning session's deliverable IS the plan. Close out after the plan. The next session implements ONE phase. If a plan has N phases, expect N+1 sessions minimum (1 planning + N implementation). If a session's commit history shows both "docs: plan" and "feat: implement," it bundled. Implementing multiple LAYERS of ONE phase's pre-declared vertical slice is NOT bundling — bundling is implementing two DIFFERENT capabilities, or a plan + its code. The test: did a single plan-mode contract pre-declare this exact layer set, all of the same capability? |
| 19 | **Plan-mode bypass** | Plan-mode output arrives in the prompt with "implement." Session treats it as an implementation task and starts coding, skipping the planning workstream entirely. The plan hasn't been evidence-verified. | Plan-mode output is a DRAFT. The first session writes it to `docs/planning/` with evidence-based inventory. Implementation is a separate session. If the prompt contains a multi-phase plan and says "implement," the deliverable is the plan document, not code. |
| 20 | **Edit from memory** | Modify a file based on memory of what it contains rather than re-reading it. Memory degrades over long sessions; edits silently corrupt content. | Re-read the target section immediately before editing. If you haven't read the file in the last 5 minutes, read it now. This applies to code AND documents. |
| 21 | **Greenfield assumption** | Write as if the project has no existing capabilities, infrastructure, or history. Destroys credibility with stakeholders who know what they already have. | Assume existing capabilities unless told otherwise. Read the project's baseline/current-state documentation during Orient. Frame work as extending, standardizing, or automating what exists — not building from scratch. |
| 22 | **Overwrite user edits** | Regenerate or modify content the user edited outside the agent's control (between sessions, in another editor, or manually). Destroys the user's work. | Check git blame or system-reminders before modifying any artifact that might have been user-edited. When in doubt, ask. Never regenerate generated artifacts (figures, tables, templates) without confirming the user hasn't customized them. |
| 23 | **Question-as-instruction** | User asks a question or makes an observation; agent treats it as an instruction to modify files. | Present options and wait for direction. A question is not a go-ahead. "How could we improve X?" means discuss, not implement. |
| 24 | **Build-passes-ship-it** | Session confirms `mvn clean package` / `npm run build` / equivalent succeeds and treats that as verification of correctness. But the deliverable involves runtime behavior (startup, service registration, config resolution, handler dispatch) that only executes when the application starts. Build tools verify compilation, not integration. | If your deliverable changes runtime behavior, launch the application before close-out and verify (Phase 3E). "Build clean" is necessary but not sufficient. A self-assessment that notes "no runtime verification" without treating it as a defect is this failure mode in action. |
| 25 | **Horizontal slicing** | Plan or implementation structured as horizontal layers: write all tests first, THEN all implementation; or finish all schema changes, THEN all API changes, THEN all UI. Each layer "feels complete" independently but no slice is end-to-end working until the very end. A blocker mid-stack means rework across every prior layer. Symptom in plans: phase names like "Phase 1: schemas / Phase 2: APIs / Phase 3: UI". Symptom in code: `tests/*` ships green for weeks while `src/*` is empty. | Vertical slices ("tracer bullets"): one feature end-to-end through every layer at once, then the next feature. Each slice ships a working narrow path; rework cost is bounded by one slice. Test: "If I stop here, is something working?" If no — you horizontally sliced. (Pattern named by Matt Pocock's `/tdd` skill at https://github.com/mattpocock/skills; the discipline applies more broadly than TDD.) |
| 26 | **Mega-session masquerading as a vertical slice** | Under the vertical-slice allowance (§Vertical Slice Sessions), a session bundles two or more DIFFERENT capabilities — or a plan + its implementation, or two platform cutovers — and justifies it as "one vertical slice." The slice-contract gate is cited as authorization while the actual unit is N intents: a crash or operator reversal rolls back N entangled intents, and an off-CI surface can ship falsely-green because "build-all attested the slice done." | A slice is ONE capability mapped to ONE pre-declared, operator-approved layer list. Test: does a single plan-mode contract from a prior session enumerate exactly this layer set, all of the same capability? If the layers span two capabilities, two platform cutovers, or a plan + code — it is this failure mode. Split it. (The high-parallelism-era composite of FM #2 keep-going, #5 volume, #8 redesign mid-task, and #18 planning-to-impl bleed.) |
| 27 | **Unrecorded action** | Complete an action and commit it, then close out without recording it in the authoritative ledger (`CHANGELOG.md`) because the work already feels captured in the session notes and the commit message. But `SESSION_NOTES.md` is overwritten next session and raw `git log` is not a per-action summary, so the durable record silently never lands. "Too small to log" or "I'll batch it next time" **is** this failure mode, not an exception. "Action" is broader than a commit — a release, a tag/branch op, a PR open, an upstream issue close, an access grant, or a decline/wontfix/grooming decision all escape a commit-only reflex. | Phase 3F appends one dated, source-tagged entry per action before commit — `[issue #<N>]` · `[BL-<N>]` · `[ad hoc]`, newest on top; for a backlog item, remove it from `BACKLOG.md` in the same commit. Keyed to a mechanical fact, not judgment: *did this session author or retain any commit, or take any non-commit action?* If yes, an entry is owed. If `CHANGELOG.md` is absent, create it from the bootstrap seed — never silently no-op; the ONE opt-out is a project that deletes the file **and** records that decision in `CLAUDE.md`. Two no-ops only: that recorded opt-out, and a session with an empty diff and no action. Anti-erosion (FM #17): the ledger records what the session did; it does not authorize what it produced — 1-and-done still bounds scope; N blocks = N layers of ONE deliverable, never N deliverables. |

---

## Degradation Detection

**How to recognize the protocol is eroding — warning signs that predict ghost sessions and failed deliveries:**

| Warning Sign | What It Means | Response |
|--------------|---------------|----------|
| Handoff is <5 lines | Failure mode #15 (minimal handoff) is active | Expand to meet all 6 minimum requirements |
| No handoff evaluation of predecessor | Failure mode #10 (skip evaluation) is active | Stop. Write the evaluation before self-assessing |
| "I'll just skip the stub" | Failure mode #14 (ghost session) is imminent | Write the stub. It takes 30 seconds. |
| Self-assessment not written to file | Failure mode #6 (skip close-out) is active | Write to SESSION_NOTES.md before summarizing verbally |
| Commits landed this session but the `HANDOFFS.md` receipt was never completed (still `status: pending`, or absent) | Failure mode #6 (skip close-out) is active — the handoff report was skipped | Complete the receipt (Phase 3D) before the final commit; otherwise a later Orient reconciles it `status: reconciled` and the skipped report is on the record |
| Session number gap in SESSION_NOTES.md | Ghost session already happened | Note it. Document what you can infer from git log. |
| Score dropping session-over-session | Multiple failure modes compounding | Re-read this entire document. Reset to full protocol. |
| "This step doesn't apply to my session" | Failure mode #17 (protocol erosion) is active | The step applies. Do it. Every step exists because a session failed without it. |
| Plan commit + implementation commit in same session | Failure mode #18 (planning-to-implementation bleed) is active — UNLESS the session is a pre-declared vertical slice whose plan was committed in a PRIOR session | The plan was the deliverable. Close out. Implementation is a separate session. |
| Session starts coding from plan-mode output | Failure mode #19 (plan-mode bypass) is active | The plan is a draft. Write it to `docs/planning/` with evidence-based inventory first. |
| File edited without re-reading it first | Failure mode #20 (edit from memory) is active | Re-read the file now. Do not edit from memory. |
| Document describes a blank-slate starting point when existing infrastructure exists | Failure mode #21 (greenfield assumption) is active | Re-read the project's baseline documentation. Rewrite to acknowledge what exists. |
| User says "I edited X" and the agent regenerates X | Failure mode #22 (overwrite user edits) is active | Check git blame. Preserve user modifications. |
| User asks a question and the agent starts modifying files | Failure mode #23 (question-as-instruction) is active | Stop modifying. Present options. Wait for explicit direction. |
| Self-assessment notes "no runtime verification" but treats it as incidental | Failure mode #24 (build-passes-ship-it) is active | Phase 3E was skipped. Launch the application before committing. If verification is impossible in this environment, state that explicitly — do not silently treat build-clean as runtime-clean. |
| Plan phases or commits map to horizontal layers (all tests, then all impl; all schema, then all API, then all UI) | Failure mode #25 (horizontal slicing) is active | Restructure as vertical slices: one end-to-end feature at a time. Apply the "if I stop here, does something work?" test to each phase. |
| Commit history shows two unrelated capabilities in one session | Failure mode #26 (mega-session masquerading as a vertical slice) is active | Apply the slice test: one prior-session contract, one capability, exactly this layer set. If it fails, close out at the last clean checkpoint commit and split the remainder. |
| Session authored or retained a commit — or took a release / tag / PR-open / issue-close / access-grant action — but `CHANGELOG.md` was not touched this session | Failure mode #27 (unrecorded action) is active | Append the owed entry before the final commit. If `CHANGELOG.md` is absent and no `CLAUDE.md` opt-out is recorded, create it from the bootstrap seed. "Too small to log" is the failure mode, not an exception. |

**If you detect 2+ warning signs: STOP.** Re-read this document from the top. Do not continue until you've re-internalized the protocol. The cost of pausing to re-read is 2 minutes. The cost of a ghost session or failed delivery is the user's trust.

---

## Learnings (added by sessions)

*These rows are the methodology's own framework learnings, recorded as the canonical repo dogfoods itself — canonical sessions append new rows here (append only; do not edit existing rows). Adopter projects do NOT edit this synced table — record project learnings in `CLAUDE.md` → Project-Specific Methodology Adaptations → Project-specific Learnings instead (see 3C).*

| # | Learning | Source | When to Apply |
|---|----------|--------|---------------|
| 1 | Plan-mode output is a draft, not a verified plan. When a prompt contains a multi-phase plan with "implement," the deliverable is a plan document with evidence-based inventory, not Phase 1 code. The gap: Phase 1's task mapping had no entry for plan-mode handoffs, so the session defaulted to "implement." Structural fix: new mapping row + FM #19. | FM #19 discovery | When a prompt contains a multi-phase plan with "implement" — recognize this as a planning workstream. |
| 2 | **Protocol discipline is perishable.** 14 consecutive clean sessions can collapse to 1/10 deliveries within 12 hours of relaxed discipline. The protocol is perishable — it doesn't maintain itself. Each session must actively re-internalize it, not assume it's "already known." The compounding loop works only when every link in the chain is complete. | Field observation | Whenever you catch yourself thinking "I know the protocol, I don't need to re-read it" — re-read it. The fast-collapse case (FM #17 slow-drip's sibling) is real. |
| 3 | Plans should flag "here be dragons" areas where implementation is non-obvious — not all phases are equally risky. Call out which phases need extra caution, what assumptions are load-bearing, and where the executor should stop and re-orient. | Field observation | When writing any multi-phase plan. A plan that presents all phases as equally tractable lies to the executor about where the cost actually lives. |
| 4 | **Verify a plan's output against its completion criteria — not against session duration or count.** Execution speed is not evidence of plan quality, and "fits in one session" is not a planning goal. A plan whose phases each fit cleanly in one session and produce work that matches the completion criteria is high-quality; a plan that tempts the executor to bundle phases or skip close-out to "finish faster" is not. The "1 and done" rule does not bend for high-quality plans. | Field observation (refined from rmsharp feedback on issue #7) | When evaluating a plan or judging plan quality. Resist the temptation to read execution speed as plan quality — they are uncorrelated when the protocol holds. |
| 5 | Code review is a distinct deliverable, not overhead. Reviews that produce actionable plans (exact code snippets, line numbers, implementation order) have higher ROI than vague "this needs improvement" feedback. A review that doesn't identify specific changes a future session can execute is incomplete. | Field observation | When the session deliverable is a code review. Output an actionable plan, not a critique. |
| 6 | A plan written from memory of a file read is an assumption-level claim. Reading implementations before estimating complexity catches wrong assumptions early — estimating from a backlog description alone is unreliable. This is a special case of FM #11 (gaps from memory) and FM #20 (edit from memory) applied to planning. | Field observation | Before estimating effort or scope for any phase, read the actual implementation file. The backlog description is a hint, not a spec. |
| 7 | **Cross-reference completeness at self-review.** When a change adds a citation, an index entry, a glossary term, or any cross-reference between files — and especially when it modifies a numbered set (FMs, principles, phases, anti-patterns, learnings) — `git diff` confirms only the present-side edit; the defect is the *absence* on the destination side, which the diff cannot surface. Grep each cited destination to confirm the citation resolves, and grep nearby prose for set-size or named-membership assertions ("N failure modes", "the three workstreams") that may have drifted. Bidirectional: a new index entry needs its destination to cite back; a grown numbered set needs its size claims re-counted. | Three v2.6 instances: stale "24 failure modes" count, understated `/diagnose` + `/grill-with-docs` citation rows, aspirational `/init` citation (issue #19) | When a change touches any cross-file citation, index, glossary term, or numbered set. At self-review, grep destinations and size claims before committing — do not rely on `git diff` alone. |
| 8 | **A close-out gate is only as strong as the weakest checklist that summarizes close-out.** Session-type procedures (Planning, Review/Audit, Debugging, the vertical-slice revert, and campaign per-session checklists) each restate the close-out in condensed form. An agent following a condensed checklist never re-reads the full phase, so any cross-cutting gate the summary omits is silently exempted for that session type — exactly how an "authoritative" ledger acquires holes. When you add or change a close-out step, reconcile it into *every* checklist that restates close-out, not only the canonical Phase 3/Phase 6 text. This is Learning #7 applied to procedure summaries rather than citations. | FM #27 / escape #8 (CHANGELOG-ledger campaign, S7) | When adding or modifying any close-out or other cross-cutting gate: grep every session-type and campaign checklist that restates close-out and confirm the new step appears in each. |
| 9 | **A handoff is only dependable when it is a durable, machine-checkable artifact.** A transient narrative — spoken, or written only to the wholesale-overwritten `SESSION_NOTES.md` — leaves no evidence of its own absence, so a skipped close-out report is invisible until a human notices (the failure that motivated the receipt: an agent had to be *prompted* for its report). The fix mirrors the ledger (FM #27) exactly: **gate-on-write** (a `HANDOFFS.md` receipt whose structure `bin/check-handoff` verifies) **AND reconcile-on-read** (Phase 0 greps for a missing/`status: pending` receipt and backfills it `status: reconciled`) — neither is dependable alone. The honest ceiling is the same too: the check verifies presence and structure, never quality (a green check is not a good handoff), and a session that leaves no commit and no 1B stub still escapes. This is Learning #8 applied to the report itself, not just the ledger. | Close-out receipt slice (this session) | When adding any close-out artifact or gate: make it a durable, greppable artifact with a write-gate AND a reconcile-on-read backstop — never a transient note or a spoken summary. |

---

## Launch Prompt Templates

The user can paste any of these to start a session reliably. The session runner handles the rest — the user does not need to include methodology instructions, close-out instructions, or stop conditions.

**Design:**
> Design the [name/component].

**Implementation:**
> Implement [feature/phase N of plan].

**Continuation:**
> Continue where last session stopped.

**Audit:**
> Audit [target].

**Free-form:**
> [Description of task]. *(Session runner will assess scope and pick the right workstream.)*
