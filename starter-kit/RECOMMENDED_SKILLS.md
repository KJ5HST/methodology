# Recommended Skills

This file is the canonical index of Claude Code skills the methodology recommends. The recommendation is **citation**, not dependency: each entry names a skill that implements a discipline the methodology calls for at a specific phase or workstream. The methodology's rules remain the operative guidance when a skill is unavailable; the skill is a sharper instrument when present.

**Principle (from [`ITERATIVE_METHODOLOGY.md`](../ITERATIVE_METHODOLOGY.md#recommended-skills) §Recommended Skills):** *Methodology recommends; methodology does not reimplement.*

---

## How this index is used

- **From inside methodology docs.** Phase descriptions, workstreams, and `SESSION_RUNNER.md` cite skills by slash-command name (`/verify`, `/grill-me`) at the point of recommendation. They do not re-describe what the skill does.
- **From inside an adopting project.** The project's `CLAUDE.md` (per `starter-kit/CLAUDE_TEMPLATE.md`) and `BOOTSTRAP.md` procedures may pin specific skills as part of project setup. Adopters use this index to decide which skills to install.
- **As a pinning layer.** External skills change. Each external entry lists a **known-good commit SHA** (captured when methodology verified the skill). Adopters who want supply-chain stability should fork the skill at that SHA rather than tracking upstream `main`.

**Verification date for this index:** 2026-05-25.

---

## Skills from Matt Pocock's repository

**Source:** [`github.com/mattpocock/skills`](https://github.com/mattpocock/skills) — community-maintained skill library.

**Stability note.** Pocock's repo is community-maintained; the methodology has no control over its lifecycle. Each entry below pins a known-good commit SHA. **For production reliance, fork the skill** at that SHA into a repo under your control, or vendor it as a Claude Code plugin you administer. The pin protects against upstream API churn; the fork protects against deletion.

| Skill | Where methodology recommends it | Source path | Known-good SHA |
|---|---|---|---|
| [`/git-guardrails-claude-code`](https://github.com/mattpocock/skills/tree/main/skills/misc/git-guardrails-claude-code) | [`starter-kit/SAFEGUARDS.md`](SAFEGUARDS.md) — recommended mechanical enforcement of "Blast Radius Limits" | `skills/misc/git-guardrails-claude-code` | `62f43a18177b` (2026-04-28) |
| [`/grill-me`](https://github.com/mattpocock/skills/tree/main/skills/productivity/grill-me) | [`ITERATIVE_METHODOLOGY.md`](../ITERATIVE_METHODOLOGY.md) §Phase 2.5 (optional Pre-Create Grill) | `skills/productivity/grill-me` | `62f43a18177b` (2026-04-28) |
| [`/grill-with-docs`](https://github.com/mattpocock/skills/tree/main/skills/engineering/grill-with-docs) | [`ITERATIVE_METHODOLOGY.md`](../ITERATIVE_METHODOLOGY.md) §Phase 2 — `CONTEXT.md` read-step; [`CONTEXT_TEMPLATE.md`](CONTEXT_TEMPLATE.md) §Maintenance | `skills/engineering/grill-with-docs` | `e7df78bb81da` (2026-05-19) |
| [`/diagnose`](https://github.com/mattpocock/skills/tree/main/skills/engineering/diagnose) | [`ITERATIVE_METHODOLOGY.md`](../ITERATIVE_METHODOLOGY.md) §Debugging Sessions + Phase 6 step 8 commit-cleanup; [`SESSION_RUNNER.md`](SESSION_RUNNER.md) §Phase 3F (tagged debug-log cleanup) | `skills/engineering/diagnose` | `7afa86d3a5dd` (2026-04-28) |
| [`/triage`](https://github.com/mattpocock/skills/tree/main/skills/engineering/triage) | [`workstreams/DEVELOPMENT_WORKSTREAM.md`](../workstreams/DEVELOPMENT_WORKSTREAM.md) §Issue Lifecycle | `skills/engineering/triage` | `179a14e72103` (2026-04-28) |
| [`/improve-codebase-architecture`](https://github.com/mattpocock/skills/tree/main/skills/engineering/improve-codebase-architecture) | [`workstreams/ARCHITECTURE_WORKSTREAM.md`](../workstreams/ARCHITECTURE_WORKSTREAM.md) §Refactor Heuristics | `skills/engineering/improve-codebase-architecture` | `a36584e09eae` (2026-05-20) |
| [`/setup-pre-commit`](https://github.com/mattpocock/skills/tree/main/skills/misc/setup-pre-commit) | [`starter-kit/BOOTSTRAP.md`](BOOTSTRAP.md) Step 10 — one option for the pre-commit hooks recommendation | `skills/misc/setup-pre-commit` | `62f43a18177b` (2026-04-28) |

Repo HEAD at verification: `b8be62ffacb0` (2026-05-20).

---

## Skills from Claude Code (built-in or installable)

**Source:** Anthropic's Claude Code. Skill availability varies by Claude Code version and environment; cross-check against [Anthropic's Claude Code documentation](https://docs.claude.com/en/docs/claude-code) for the current authoritative list.

**Stability note.** Claude Code skills are maintained by Anthropic. Fork-for-stability is not the typical posture; tracking the official skill is appropriate. If a skill listed here disappears or is renamed in a future Claude Code release, treat that as a signal to update the methodology's citation, not as a reason to fork.

| Skill | Where methodology recommends it |
|---|---|
| `/verify` | [`SESSION_RUNNER.md`](SESSION_RUNNER.md) §Phase 3E Runtime Smoke Test — recommended procedure for runtime verification |
| `/run` | [`SESSION_RUNNER.md`](SESSION_RUNNER.md) §Phase 3E — companion to `/verify`; [`BOOTSTRAP.md`](BOOTSTRAP.md) — runtime drive guidance |
| `/init` | [`BOOTSTRAP.md`](BOOTSTRAP.md) Step 4 — initializing `CLAUDE.md` |
| `/code-review` | [`workstreams/AUDIT_WORKSTREAM.md`](../workstreams/AUDIT_WORKSTREAM.md) — correctness review |
| `/review` | [`workstreams/AUDIT_WORKSTREAM.md`](../workstreams/AUDIT_WORKSTREAM.md) — PR review |
| `/security-review` | [`workstreams/AUDIT_WORKSTREAM.md`](../workstreams/AUDIT_WORKSTREAM.md) — security review |
| `/fewer-permission-prompts` | [`BOOTSTRAP.md`](BOOTSTRAP.md) — permission setup |

---

## When a recommended skill is unavailable

The methodology's text remains the operative guidance. The skill is a sharper instrument; the underlying discipline does not depend on it. Examples:

- **`/verify` unavailable.** Phase 3E's rule — "launch the application before committing and verify the behavior" — applies. The agent runs the verification manually.
- **`/grill-me` unavailable.** Phase 2.5's procedure (list decisions, draft recommendations, present one at a time) applies. The session runs the grill manually.
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

*The audit that motivated this index is [`docs/audits/2026-05-02-mattpocock-skills-evaluation.md`](../docs/audits/2026-05-02-mattpocock-skills-evaluation.md).*
