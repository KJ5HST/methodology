# CONTEXT.md — [Project Name]

**This file is the project's shared vocabulary and load-bearing context.** Agents read it during Phase 2 (Research) before exploring code. Contributors maintain it as they work.

If you are reading this template literally, replace each section's placeholder content with project-specific content. Delete sections that do not apply. The template is a starting point, not a checklist.

---

## What This Project Is

A 1–2 paragraph summary of what the project does, who it is for, and the dominant architectural shape. Treat this as the elevator pitch for someone with no prior exposure.

*Example: "rad-con is a desktop ham-radio control suite (Java 17 + Vue 3 + optional Tauri shell) that pairs a hardware-CAT layer with a digital-modes pipeline. Three coexisting decoder strategies (in-process Java, JNI, jt9 subprocess) trade off licensing and performance differently."*

---

## Domain Vocabulary

Project-specific terms a new reader needs to know. **Do not** define general industry terms; only terms that carry non-obvious meaning *here*.

| Term | Meaning in this project | Notes |
|------|------------------------|-------|
| `nzhsym` | Number of half-symbols in an FT8 decoder pass. Tuned per mode (FT8=50). | Hardcoded constant; do not generalize without reading prior session learnings. |
| `materialization cascade` | Project-coined term for the cascade order of derived state. | See `docs/adr/0007-materialization.md`. |

**Adding a term:** when a session encounters a project-specific name during research that would have helped to know up front, propose an entry here in close-out.

---

## Load-Bearing Constraints

External constraints that shape design decisions. These are typically discovered the hard way; capturing them early saves rediscovery cost.

- **Constraint:** *(name)* — *(one-line description)* — *(why it matters)* — *(source: regulation, hardware datasheet, vendor doc, or memory of past incident)*.
- *Example: GPL-3.0 boundaries — jt9 is GPLv3, project is Apache-2.0; decoder strategies isolate the GPL boundary by running jt9 as a subprocess, never linked.*

---

## Architecture Decision Pointers

Brief pointers to major decisions, not the decisions themselves. Detailed ADRs go in `docs/adr/` (or equivalent) if the project uses them.

- **Decision:** *(name)* — **Status:** *(active / superseded / under-review)* — **Why:** *(one line)* — **Where:** *(file path or ADR number)*.

---

## Common Pitfalls

Project-specific traps that have bitten previous sessions. Mirrors the methodology's anti-pattern list, but at the project layer.

- **Pitfall:** *(one-line description)* — **Why it happens:** *(cause)* — **Recovery:** *(how to avoid or recover)*.

---

## CONTEXT.md vs agent-level memory: when to use which

Methodology supports two complementary persistence layers. They are **additive**, not exclusive. The second layer — *agent-level memory* — is persistence scoped to the agent across all projects rather than to one repository; agents implement it under different names (Claude Code's auto-memory, Cursor's memories, Cody's preferences), so this template names the capability generically.

| Use **CONTEXT.md** for… | Use **agent-level memory** for… |
|------------------------|--------------------------|
| Domain vocabulary a fresh reader needs on a clean clone | Operator preferences and feedback that apply across all projects |
| Decisions that should travel with the code under version control | Cross-project policy ("no AI coauthorship", "verify CI before close-out") |
| Constraints that constrain *the project's* design (licensing, hardware, regulation) | The operator's role, expertise, and collaboration style |
| Things a contributor should learn before opening a PR | Things the agent should remember across many sessions in many repos |

**Practical rule:** if the artifact would be useful to a contributor who only opened *this* repo without operator context, it belongs in CONTEXT.md. If it is about how the operator works, or it applies across repos, it belongs in agent-level memory.

Some content (e.g., a project's licensing policy) reasonably lives in both layers — repeating it across the layers is a feature, not a duplication bug, because the two audiences are different.

---

## Maintenance

The methodology recommends Pocock's `/grill-with-docs` skill for interactive CONTEXT.md maintenance during research sessions — see [`RECOMMENDED_SKILLS.md`](RECOMMENDED_SKILLS.md). When the skill is unavailable, the maintenance discipline is: at Phase 6 close-out, propose any new domain term, constraint, or pitfall discovered during this session, and either add it inline or leave a note for the next session.
