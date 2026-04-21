# CLAUDE.md

*Template: copy this file to your project root as `CLAUDE.md` (or merge the SESSION PROTOCOL block into an existing one). Customize the marked sections; leave the rest verbatim.*

---

## SESSION PROTOCOL — FOLLOW BEFORE DOING ANYTHING

Read and follow `SESSION_RUNNER.md` step by step. It is your operating procedure for every session. It tells you what to read, when to stop, and how to close out.

**Three rules you will be tempted to violate:**
1. **Orient first** — Read SAFEGUARDS.md → SESSION_NOTES.md → run `methodology_dashboard.py` → git status → report findings → WAIT FOR THE USER TO SPEAK
2. **1 and done** — One deliverable per session. When it's complete, close out. Do not start the next thing.
3. **Auto-close** — When done: evaluate previous handoff, self-assess, document learnings, write handoff notes, commit, report, STOP.

`SESSION_RUNNER.md` documents known failure modes and their countermeasures. The protocol compensates for documented tendencies to skip orientation, skip close-out, and continue past the deliverable.

---

## Purpose

<!-- Customize: one-paragraph description of what this project is and what it's for. -->

This is the `<project-name>` project. It does `<what>`. The primary deliverable is `<what>`.

---

## Tech Stack

<!-- Customize: languages, frameworks, key dependencies. -->

- `<language/runtime>`
- `<framework>`
- `<key libraries>`

---

## Build / Test / Verify

<!-- Customize: the command(s) that confirm the deliverable is not broken. See SAFEGUARDS.md "Verify the Build Equivalent". -->

```bash
<build command>
<test command>
```

---

## Project-Specific Methodology Adaptations

*Additions and overrides to the base methodology at `SESSION_RUNNER.md` and `SAFEGUARDS.md` (synced from the methodology repo, not project-owned). The base files govern unless explicitly overridden here.*

*Populate these subsections only where real customizations exist — empty subsections can be deleted. Do not edit the synced files themselves.*

### Additional Phase 0 steps

<!-- Example:
- Before reporting findings: run `<project>/scripts/check-env.sh` and include status in the report.
-->

(none)

### Additional task-to-workstream mappings

<!-- Example:
| If the user says... | Deliverable | Workstream doc |
|---|---|---|
| "Design the X profile" | One profile design doc | `docs/internal/PROFILE_DESIGN.md` |
-->

(none)

### Project-specific Learnings

<!-- Example:
| # | Lesson | From | When to apply |
|---|---|---|---|
| 1 | Plans must include grep inventory for deletion/migration | Session 93 | Any multi-phase plan that removes or renames symbols |
-->

(none)

### Project-specific Failure Modes

<!-- Extends the base failure modes in SESSION_RUNNER.md. Number continues from the base table. -->

(none)
