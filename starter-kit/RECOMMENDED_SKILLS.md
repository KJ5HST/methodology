# Recommended Skills

This file is the canonical index of Claude Code skills the methodology recommends. The recommendation is **citation**, not dependency: each entry names a skill that implements a discipline the methodology calls for at a specific phase or workstream. The methodology's rules remain the operative guidance when a skill is unavailable; the skill is a sharper instrument when present.

**Principle (from [`ITERATIVE_METHODOLOGY.md`](docs/methodology/ITERATIVE_METHODOLOGY.md#recommended-skills) §Recommended Skills):** *Methodology recommends; methodology does not reimplement.*

---

## How this index is used

- **From inside methodology docs.** Phase descriptions, workstreams, and `SESSION_RUNNER.md` cite skills by slash-command name (`/verify`, `/grill-me`) at the point of recommendation. They do not re-describe what the skill does. **Citation shape follows a count threshold:** when a doc recommends *one* skill, cite it inline at the point of recommendation (e.g. `DEVELOPMENT_WORKSTREAM.md` §Issue Lifecycle → `/triage`; `ARCHITECTURE_WORKSTREAM.md` §Refactor Heuristics → `/improve-codebase-architecture`); when *two or more* skills apply to the same workstream, promote them to a dedicated `## Recommended Skills` section near the top of the file — a short intro stating what the methodology owns vs. what the skill owns, then a purpose→skill table (e.g. `AUDIT_WORKSTREAM.md`, recommending `/code-review`, `/review`, and `/security-review`). The dedicated section earns its overhead only at ≥2 skills; a single-row table is heavier than the inline citation it would replace.
- **From inside an adopting project.** The project's `CLAUDE.md` (per `starter-kit/CLAUDE_TEMPLATE.md`) and `BOOTSTRAP.md` procedures may pin specific skills as part of project setup. Adopters use this index to decide which skills to install.
- **As a pinning layer.** External skills change. Each external entry lists a **known-good commit SHA** (captured when methodology verified the skill). Adopters who want supply-chain stability should fork the skill at that SHA rather than tracking upstream `main`.

**Verification date for this index:** 2026-05-25.

---

## Skills from Matt Pocock's repository

**Source:** [`github.com/mattpocock/skills`](https://github.com/mattpocock/skills) — community-maintained skill library.

**Stability note.** Pocock's repo is community-maintained; the methodology has no control over its lifecycle. Each entry below pins a known-good commit SHA. **For production reliance, fork the skill** at that SHA into a repo under your control, or vendor it as a Claude Code plugin you administer. The pin protects against upstream API churn; the fork protects against deletion.

| Skill | Where methodology recommends it | Phases spanned (compression risk) | Source path | Known-good SHA |
|---|---|---|---|---|
| [`/git-guardrails-claude-code`](https://github.com/mattpocock/skills/tree/main/skills/misc/git-guardrails-claude-code) | [`SAFEGUARDS.md`](SAFEGUARDS.md) — recommended mechanical enforcement of "Blast Radius Limits" | Setup only, not in-session (zero) | `skills/misc/git-guardrails-claude-code` | `62f43a18177b` (2026-04-28) |
| [`/grill-me`](https://github.com/mattpocock/skills/tree/main/skills/productivity/grill-me) | [`ITERATIVE_METHODOLOGY.md`](docs/methodology/ITERATIVE_METHODOLOGY.md) §Phase 2B (optional Pre-Create Grill) | Phase 2B only (low) | `skills/productivity/grill-me` | `62f43a18177b` (2026-04-28) |
| [`/grill-with-docs`](https://github.com/mattpocock/skills/tree/main/skills/engineering/grill-with-docs) | [`ITERATIVE_METHODOLOGY.md`](docs/methodology/ITERATIVE_METHODOLOGY.md) §Phase 2 — `CONTEXT.md` read-step; [`CONTEXT_TEMPLATE.md`](CONTEXT_TEMPLATE.md) §Maintenance | Phase 2 → 3 → 5, modifies `CONTEXT.md`/ADRs (**high**) | `skills/engineering/grill-with-docs` | `e7df78bb81da` (2026-05-19) |
| [`/diagnose`](https://github.com/mattpocock/skills/tree/main/skills/engineering/diagnose) | [`ITERATIVE_METHODOLOGY.md`](docs/methodology/ITERATIVE_METHODOLOGY.md) §Debugging Sessions + Phase 6 step 8 commit-cleanup; [`SESSION_RUNNER.md`](SESSION_RUNNER.md) §Phase 3F (tagged debug-log cleanup) | All 6 phases — debugging-session alignment is intentional (medium, by design) | `skills/engineering/diagnose` | `7afa86d3a5dd` (2026-04-28) |
| [`/triage`](https://github.com/mattpocock/skills/tree/main/skills/engineering/triage) | [`DEVELOPMENT_WORKSTREAM.md`](docs/methodology/workstreams/DEVELOPMENT_WORKSTREAM.md) §Issue Lifecycle — see prerequisite note below | Phase 1 + Issue Lifecycle (low) | `skills/engineering/triage` | `179a14e72103` (2026-04-28) |
| [`/improve-codebase-architecture`](https://github.com/mattpocock/skills/tree/main/skills/engineering/improve-codebase-architecture) | [`ARCHITECTURE_WORKSTREAM.md`](docs/methodology/workstreams/ARCHITECTURE_WORKSTREAM.md) §Refactor Heuristics | Phase 2 → 3 → 5, modifies `CONTEXT.md`/ADRs (**high**) | `skills/engineering/improve-codebase-architecture` | `a36584e09eae` (2026-05-20) |
| [`/setup-pre-commit`](https://github.com/mattpocock/skills/tree/main/skills/misc/setup-pre-commit) | [`BOOTSTRAP.md`](BOOTSTRAP.md) Step 10 — one option for the pre-commit hooks recommendation | Setup only (zero) | `skills/misc/setup-pre-commit` | `62f43a18177b` (2026-04-28) |

Repo HEAD at verification: `b8be62ffacb0` (2026-05-20).

**Reading the "Phases spanned" column.** A skill that spans multiple phases in one invocation can pull a session across a hard gate — the failure mode named by *"A skill is not a phase"* ([`ITERATIVE_METHODOLOGY.md`](docs/methodology/ITERATIVE_METHODOLOGY.md) §Recommended Skills). The column tells you *before invoking* which skills carry that risk. For the **high**-compression skills, plan the stop point first: invoke them where their span lies inside the session's declared deliverable, and close out rather than letting the skill's momentum carry the session past a gate. Under the vertical-slice model (issues [#20](https://github.com/KJ5HST/methodology/issues/20)/[#21](https://github.com/KJ5HST/methodology/issues/21), adopted v2.7), "declared deliverable" means the slice's pre-declared layer set: a multi-phase skill is safe only where its span stays within that contract, and a skill's span never *substitutes* for a contract — invoking a high-compression skill without one leaves the session under the plain horizontal rule (one layer, then close out). The allowance adds a gate; it removes no step (`SESSION_RUNNER.md` FM #17 anti-erosion clause). (`/diagnose` is the deliberate exception — a debugging session *is* its span, per §Debugging Sessions.) Phase spans are verbatim-verified against each skill's pinned SHA (issue [#22](https://github.com/KJ5HST/methodology/issues/22) investigation).

**`/triage` prerequisite note.** The skill's body (at the pinned SHA) says its issue-tracker label mapping *"should have been provided to you — run `/setup-matt-pocock-skills` if not"* — a skill this index deliberately declines (§Skills not recommended). Adopters using `/triage` should establish the label mapping themselves instead: map the skill's canonical states (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`) to their tracker's labels per [`DEVELOPMENT_WORKSTREAM.md`](docs/methodology/workstreams/DEVELOPMENT_WORKSTREAM.md) §Issue Lifecycle, or accept the canonical names as-is. The citation stands; the skill's setup recommendation does not.

---

## Skills from Claude Code (built-in or installable)

**Source:** Anthropic's Claude Code. Skill availability varies by Claude Code version and environment; cross-check against [Anthropic's Claude Code documentation](https://docs.claude.com/en/docs/claude-code) for the current authoritative list.

**Stability note.** Claude Code skills are maintained by Anthropic. Fork-for-stability is not the typical posture; tracking the official skill is appropriate. If a skill listed here disappears or is renamed in a future Claude Code release, treat that as a signal to update the methodology's citation, not as a reason to fork.

| Skill | Where methodology recommends it |
|---|---|
| `/verify` | [`SESSION_RUNNER.md`](SESSION_RUNNER.md) §Phase 3E Runtime Smoke Test — recommended procedure for runtime verification |
| `/run` | [`SESSION_RUNNER.md`](SESSION_RUNNER.md) §Phase 3E — companion to `/verify`; [`BOOTSTRAP.md`](BOOTSTRAP.md) — runtime drive guidance |
| `/init` | [`BOOTSTRAP.md`](BOOTSTRAP.md) Step 4 — initializing `CLAUDE.md` |
| `/code-review` | [`AUDIT_WORKSTREAM.md`](docs/methodology/workstreams/AUDIT_WORKSTREAM.md) — correctness review |
| `/review` | [`AUDIT_WORKSTREAM.md`](docs/methodology/workstreams/AUDIT_WORKSTREAM.md) — PR review |
| `/security-review` | [`AUDIT_WORKSTREAM.md`](docs/methodology/workstreams/AUDIT_WORKSTREAM.md) — security review |

---

## Skills not recommended (and why)

This index is a *vetted snapshot* of skills the methodology actively cites at specific phases or workstreams. Skills not listed in the tables above are either out of scope for the methodology's content, adequately covered by existing methodology discipline at higher rigor, or architecturally incompatible with the methodology's session-arc model.

The entries below name skills considered during the v2.6 audit (or surfaced after) that were *deliberately* not cited, with a one-line rationale each. This subsection exists to (a) close the door on future re-litigation and (b) make the audit decisions discoverable from this index rather than only from the underlying [`2026-05-02-mattpocock-skills-evaluation.md`](https://github.com/KJ5HST/methodology/blob/main/docs/audits/2026-05-02-mattpocock-skills-evaluation.md).

**See also: [`ITERATIVE_METHODOLOGY.md`](docs/methodology/ITERATIVE_METHODOLOGY.md) §Recommended Skills — "A skill is not a phase."** A recommended skill that pulls a session across a hard gate is failure mode #2 wearing a tool costume. That principle applies to *every* skill, recommended or not — including the ones below if an adopter installs them independently.

| Skill | Source | Why not cited |
|---|---|---|
| `/loop`, `/schedule` | Claude Code built-ins | Orchestration, not engineering. The methodology's phases are sequential and gated; loop/schedule belong above the session, not inside it. |
| `/to-issues` | Pocock (`engineering/to-issues`) | Covered by Learning #30 (table-first, decisions batch, parallel creation, cross-reference verification). The methodology version is materially more rigorous. |
| `/to-prd` | Pocock (`engineering/to-prd`) | Covered by Planning Sessions discipline. `/to-prd` synthesizes what's been discussed; methodology's planning sessions require grep-verified evidence inventories (per FM #19, plan-mode bypass). |
| `/tdd` | Pocock (`engineering/tdd`) | The vertical-slicing framing is incorporated as FM #25; the red-green-refactor workflow is left to adopter preference. |
| `/handoff` | Pocock (`productivity/handoff`) | Targets ephemeral single-arc compaction to OS temp; methodology requires repo-versioned cross-session handoff notes scored by the next session (Phase 3D). Different scope, not a substitute. |
| `/caveman` | Pocock (`productivity/caveman`) | Stylistic compression; the methodology's length discipline (Learning #34: ≤150 lines for handoffs) addresses token reduction without changing voice. |
| `/zoom-out` | Pocock (`engineering/zoom-out`) | Covered better by Learnings #28/#29 (Plan-subagent architecture surveys with file:line citations). |
| `/write-a-skill` | Pocock (`productivity/write-a-skill`) | The methodology doesn't ship its own skills (per the v2.6 principle). Becomes relevant only if that posture changes. |
| `/prototype` | Pocock (`engineering/prototype`) | Not yet audited (Pocock shipped this after the 2026-05-02 audit). Future-audit candidate. |
| `/setup-matt-pocock-skills` | Pocock (`engineering/setup-matt-pocock-skills`) | Out of scope — installs Pocock's skills; methodology's `BOOTSTRAP.md` is the equivalent for the methodology framework itself. Different concerns. |

If you encounter a skill that should be added to this section because it was considered and declined, open an issue or PR.

---

## When a recommended skill is unavailable

The methodology's text remains the operative guidance. The skill is a sharper instrument; the underlying discipline does not depend on it. Examples:

- **`/verify` unavailable.** Phase 3E's rule — "launch the application before committing and verify the behavior" — applies. The agent runs the verification manually.
- **`/grill-me` unavailable.** Phase 2B's procedure (list decisions, draft recommendations, present one at a time) applies. The session runs the grill manually.
- **`/git-guardrails-claude-code` unavailable.** SAFEGUARDS' "Blast Radius Limits" table applies as textual discipline. Without the hook there is no mechanical block; the rules still bind.

Adopters who routinely operate without these skills are operating the methodology as it was originally written. The recommendation makes the methodology sharper; it does not make the unrecommended version broken.

---

## Future-audit candidates

The methodology has additional content that could benefit from skill citations but was not in scope for the release that introduced this index. Flagged for follow-on workstream sessions:

- **`AUDIT_WORKSTREAM.md` Medium/Heavy pass.** Beyond the Light citation insertions shipped with this index, the workstream's per-phase audit framing and the 7-Dimension Audit Framework could be re-examined for skill-citation opportunities.
- **`workstreams/RESEARCH_DOCUMENTATION_WORKSTREAM.md`.** The Render Verification section and v2.5 anti-pattern #20 (Silent render-dependency fallback) could cite `/verify` for the post-render check.
- **`SESSION_RUNNER.md` FM countermeasures.** Several text rules in the Known Failure Modes table could be converted to Claude Code hooks (per the audit doc's Observation 3). When that conversion work happens, the FM table gains a "Mechanical enforcement" column citing the hook.
- **`workstreams/DEVELOPMENT_WORKSTREAM.md`.** Beyond Issue Lifecycle, the existing content can be audited for further skill-citation opportunities.

---

*The audit that motivated this index is [`2026-05-02-mattpocock-skills-evaluation.md`](https://github.com/KJ5HST/methodology/blob/main/docs/audits/2026-05-02-mattpocock-skills-evaluation.md).*
