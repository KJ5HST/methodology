# Session Runner

**This is your operating procedure. Follow it step by step. Do not improvise.**

Every session has exactly ONE deliverable. When it's done, you close out. You do not start the next thing.

---

## Phase 0: Orient

**Change nothing. Read only.**

1. Read `SAFEGUARDS.md`
2. Read `SESSION_NOTES.md` — focus on the ACTIVE TASK section at the top
3. Read `BACKLOG.md` — understand current milestone and priorities
4. Run: `git status`, `git log --oneline -5`, `git diff --stat`
5. **Report findings to the user:**
   - Current branch and clean/dirty state
   - What the last session was doing
   - Current milestone and active task from BACKLOG.md
   - Any uncommitted changes
   - Build status if known
6. **STOP. Wait for the user to give you a task.**

DO NOT skip the report. DO NOT start working. DO NOT assume you know what to do.

**Even if the user's first message contains a task** (e.g., "Implement the following plan"), Phase 0 is still mandatory. The orientation report exists for the user's benefit — it establishes shared understanding of the current state. The user needs to see the report and confirm before work begins. A task in the prompt does not mean Phase 0 is complete. Complete all 6 steps, then the user will re-state or confirm the task in Phase 1.

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

**If no workstream document exists for the task type, follow the master framework:** `docs/methodology/ITERATIVE_METHODOLOGY.md`, phases 1-6.

State your understanding back to the user: *"I'm going to [deliverable] following [workstream doc]. I'll close out when that's done."*

---

## Phase 2: Execute

1. Read the workstream document identified in Phase 1
2. Follow its phases sequentially, respecting hard gates
3. Execute ONE deliverable only
4. If blocked, ask. Don't improvise around blockers.
5. If you catch yourself thinking "while I'm at it..." — STOP. That's scope creep. Commit what you have and note it for a future session.

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

- ACTIVE TASK section updated with current state
- What was done (with commit hashes)
- What's next (specific, actionable)
- Any blockers or open questions
- Key files the next session should read (with line numbers where relevant)
- Gotchas or traps the next session should watch for
- What you would do differently if you could redo this session

**Write to files FIRST, then summarize verbally.** A verbal summary that isn't written down is worthless — the next session can't read the conversation.

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
| 9 | **Task-in-prompt bypass** | User's first message contains a task, so Phase 0 feels implicitly complete | Phase 0 exists for the USER, not the agent. Complete all 6 steps even when the task is obvious. |
| 10 | **Skip handoff evaluation** | Self-assessment feels sufficient; evaluating the previous session feels like extra work | Phase 3A is a mandatory structural step. The evaluation IS the compounding mechanism. |
| 11 | **Gaps from memory** | During close-out, write gap analysis from memory of files read earlier. Memory degrades. Claims turn out wrong. | Before writing ANY claim in close-out: "Have I read the file that confirms this in the last 5 minutes?" If no → read it now. |
| 12 | **Workstream transfer amnesia** | Build good discipline on one workstream, then switch and repeat old mistakes | Discipline doesn't auto-transfer. When switching workstreams, consciously re-apply the close-out checklist. |
| 13 | **Literal minimum** | When asked to do X, do exactly X and nothing logically implied by X | Before acting: "What is the user's UNDERLYING intent?" Do the complete job on the first pass. |

---

## Learnings (added by sessions)

*This table starts empty. Each session adds learnings here. Over time, this becomes the project's institutional memory.*

| # | Learning | Source | When to Apply |
|---|----------|--------|---------------|

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
