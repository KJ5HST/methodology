# Session Runner

**This is your operating procedure. Follow it step by step. Do not improvise.**

Every session has exactly ONE deliverable. When it's done, you close out. You do not start the next thing.

---

## Phase 0: Orient

**Change nothing. Read only.**

1. Read `SAFEGUARDS.md` — **in full, not skimmed. Every section.**
2. Read `SESSION_NOTES.md` — focus on the ACTIVE TASK section at the top
3. Read `BACKLOG.md` — understand current milestone and priorities
4. Run: `git status`, `git log --oneline -5`, `git diff --stat`
5. Run: `python3 methodology_dashboard.py` — refresh the project health dashboard. Leave `dashboard.html` open in a browser; it auto-refreshes every 60 seconds.
6. **Check for ghost sessions:** Compare the session number in SESSION_NOTES.md against `git log`. If there are commits between the last documented session and now that don't correspond to any session notes, report: "Detected [N] undocumented session(s) between Session [X] and now. Commits: [list]. No session notes exist for this work."
7. **Report findings to the user:**
   - Current branch and clean/dirty state
   - What the last session was doing
   - Current milestone and active task from BACKLOG.md
   - Any uncommitted changes
   - Ghost session detection results (step 6)
   - Dashboard health score and any risk flags
   - Build status if known
8. **STOP. Wait for the user to give you a task.**

DO NOT skip the report. DO NOT start working. DO NOT assume you know what to do.

**Even if the user's first message contains a task** (e.g., "Implement the following plan"), Phase 0 is still mandatory. That phrase comes from Plan Mode's auto-generated preamble — it does NOT mean start coding. The orientation report exists for the user's benefit — it establishes shared understanding of the current state. The user needs to see the report and confirm before work begins. A task in the prompt does not mean Phase 0 is complete. Complete all 8 steps, then the user will re-state or confirm the task in Phase 1.

**Steps 1-3 are READS, not skims.** Every step exists because a session failed without it.

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
| Multi-phase plan appears in prompt (from Plan Mode or user) | Plan document written to `docs/planning/` with evidence-based inventory | Planning workstream |

**⚠ Plan Mode exit trap.** Plan Mode generates "Implement the following plan" as its preamble. **This does NOT mean "start coding."** When a multi-phase plan appears in the prompt — regardless of the preamble wording — the deliverable is writing the plan document with grep-based evidence and per-phase criteria. Orient first. The plan is a DRAFT until evidence-verified. See Planning Sessions below.

**If no workstream document exists for the task type, follow the master framework:** `docs/methodology/ITERATIVE_METHODOLOGY.md`, phases 1-6.

State your understanding back to the user: *"I'm going to [deliverable] following [workstream doc]. I'll close out when that's done."*

### 1B: Claim the Session (MANDATORY)

**Immediately after receiving a task — before any technical work — write a stub to `SESSION_NOTES.md`:**

```markdown
### What Session [N] Did
**Deliverable:** [task description] (IN PROGRESS)
**Started:** [date/time]
**Status:** Session claimed. Work beginning.
```

**Why this exists:** Ghost sessions — sessions that crash, hit context limits, or end without writing notes — leave zero trace. The next session has no idea what happened, what was attempted, or what state was left behind. By writing a stub FIRST, even a catastrophic failure leaves evidence. This stub is overwritten during Phase 3D with the full handoff.

---

## Phase 2: Execute

1. Read the workstream document identified in Phase 1
2. Follow its phases sequentially, respecting hard gates
3. Execute ONE deliverable only
4. If blocked, ask. Don't improvise around blockers.
5. If you catch yourself thinking "while I'm at it..." — STOP. That's scope creep. Commit what you have and note it for a future session.

### Planning Sessions

**⚠ The plan is the deliverable. Do not start implementing it.** Write the plan document to `docs/planning/`, commit it, close out. Implementation happens in a separate session.

**A plan is a deliverable, not a preamble.** When the session's deliverable is a plan (architecture doc, migration plan, multi-phase implementation plan), additional discipline applies:

#### Evidence-Based Inventory (MANDATORY for deletion/migration/rename plans)

For any plan that involves deleting, renaming, migrating, or moving code:

1. The plan MUST include a **grep-based inventory** of all references to the affected symbols, files, components, keys, imports, and type names.
2. Run the actual searches. List every matching file. The plan's "files to change" list comes from search results, not architectural knowledge.
3. Search terms should include: file names, class names, function names, import paths, key prefixes, component registration names, and any aliases.
4. The inventory IS the plan's verification step — equivalent to "grep for dangling references" in execution sessions.

**A plan that lists files to change without having searched for them is an assumption, not an inventory.** The executor will trust the plan. If it's wrong, they'll miss files — exactly the failure this requirement prevents.

#### Per-Phase Completion Criteria

Every phase in a multi-phase plan must state:
- **What DONE looks like** — concrete output, not "implement Phase N"
- **Verification commands** — how the executor confirms completion (build, test, grep)
- **Session boundary** — "This phase is one session. Close out when done."

Without explicit completion criteria, executors don't know when to stop and tend to bundle adjacent phases.

#### Planning Session Checklist

Before closing out a planning session, verify:

- [ ] Plan document written with file paths and line numbers
- [ ] Grep-based inventory completed for all affected symbols (if deletion/migration/rename)
- [ ] Each phase has explicit completion criteria and verification commands
- [ ] Each phase marked as "separate session" with a STOP point
- [ ] Close-out: evaluate predecessor, self-assess, commit, STOP

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

Update the workstream document and/or the Learnings table below:

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

#### Evidence requirement

**Never claim credit for work you didn't do.** If a plan was provided as input, say "Plan was input, not output." If you didn't produce a deliverable, say "No deliverable produced." Fabricating accomplishments or attributing quotes the user didn't say is a trust-destroying failure.

**Never write "need to verify" in a handoff gap.** If you don't know, read the file NOW. Deferred verification is deferred work — it belongs in your session, not the next one.

### 3E: Commit

Commit all changes with a descriptive message.

### 3F: Report and STOP

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
| 6 | **Skip close-out** | Self-assessment and prompt updates feel like cleanup, not real work | Close-out is the most valuable phase. It's how the system improves. |
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
| 17 | **Protocol erosion** | Each session shaves off "just one" protocol step. Individually minor. Over 5-10 sessions, the whole protocol collapses. Scores drift from 9/10 to 1/10. | The protocol is not optional, advisory, or improvable-by-subtraction during a session. Every step exists because a previous session failed without it. If you think a step is unnecessary, that's the erosion happening. Do the step. |
| 18 | **Planning-to-implementation bleed** | A session produces a plan, then immediately begins implementing it. Or the next session bundles multiple phases because "the plan is done, implementation is easy." | A planning session's deliverable IS the plan. Close out after the plan. The next session implements ONE phase. If a plan has N phases, expect N+1 sessions minimum (1 planning + N implementation). If a session's commit history shows both "docs: plan" and "feat: implement," it bundled. |
| 19 | **Plan-mode bypass** | Plan-mode output arrives in the prompt with "implement." Session treats it as an implementation task and starts coding, skipping the planning workstream entirely. The plan hasn't been evidence-verified. | Plan-mode output is a DRAFT. The first session writes it to `docs/planning/` with evidence-based inventory. Implementation is a separate session. If the prompt contains a multi-phase plan and says "implement," the deliverable is the plan document, not code. |

---

## Degradation Detection

**How to recognize the protocol is eroding — warning signs that predict ghost sessions and failed deliveries:**

| Warning Sign | What It Means | Response |
|--------------|---------------|----------|
| Handoff is <5 lines | Failure mode #15 (minimal handoff) is active | Expand to meet all 6 minimum requirements |
| No handoff evaluation of predecessor | Failure mode #10 (skip evaluation) is active | Stop. Write the evaluation before self-assessing |
| "I'll just skip the stub" | Failure mode #14 (ghost session) is imminent | Write the stub. It takes 30 seconds. |
| Self-assessment not written to file | Failure mode #6 (skip close-out) is active | Write to SESSION_NOTES.md before summarizing verbally |
| Session number gap in SESSION_NOTES.md | Ghost session already happened | Note it. Document what you can infer from git log. |
| Score dropping session-over-session | Multiple failure modes compounding | Re-read this entire document. Reset to full protocol. |
| "This step doesn't apply to my session" | Failure mode #17 (protocol erosion) is active | The step applies. Do it. Every step exists because a session failed without it. |
| Plan commit + implementation commit in same session | Failure mode #18 (planning-to-implementation bleed) is active | The plan was the deliverable. Close out. Implementation is a separate session. |
| Session starts coding from plan-mode output | Failure mode #19 (plan-mode bypass) is active | The plan is a draft. Write it to `docs/planning/` with evidence-based inventory first. |

**If you detect 2+ warning signs: STOP.** Re-read this document from the top. Do not continue until you've re-internalized the protocol. The cost of pausing to re-read is 2 minutes. The cost of a ghost session or failed delivery is the user's trust.

---

## Learnings (added by sessions)

*This table starts empty. Each session adds learnings here. Over time, this becomes the project's institutional memory.*

| # | Learning | Source | When to Apply |
|---|----------|--------|---------------|
| 1 | Plan-mode output is a draft, not a verified plan. When a prompt contains a multi-phase plan with "implement," the deliverable is a plan document with evidence-based inventory, not Phase 1 code. The gap: Phase 1's task mapping had no entry for plan-mode handoffs, so the session defaulted to "implement." Structural fix: new mapping row + FM #19. | FM #19 discovery | When a prompt contains a multi-phase plan with "implement" — recognize this as a planning workstream. |

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
