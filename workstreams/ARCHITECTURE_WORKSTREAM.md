# Architecture Workstream

Adaptation of the [Iterative Session Methodology](../ITERATIVE_METHODOLOGY.md) for system architecture, API design, data modeling, and technical design decisions.

---

## When to Use

Use this workstream when designing:
- System architecture for new modules or services
- API contracts (REST, WebSocket, gRPC, message protocols)
- Data models and database schemas
- Integration patterns between systems
- Migration strategies for existing systems
- Performance or scalability improvements

---

## Phase 2: Research (Architecture-Specific)

### Step 1: Study the Requirements

Read requirements, technical constraints, and existing system documentation. Extract:
- **What problem does this solve?** Business need, user need, or technical need.
- **What are the hard constraints?** Performance targets, compatibility requirements, resource limits, existing contracts.
- **What systems does this interact with?** Upstream producers, downstream consumers, shared resources.
- **What is the expected scale?** Current load, projected growth, peak patterns.
- **What can change later vs. what is locked now?** Identify decisions that are reversible vs. irreversible.

### Step 2: Inventory Existing Architecture

Map the current system:

| Component | Responsibility | Interfaces | Dependencies | Health |
|-----------|---------------|------------|--------------|--------|
| (service) | (what it does) | (APIs exposed) | (what it calls) | (stable/fragile/unknown) |

**Dependency graph:** Draw or describe the dependency flow. Identify:
- Circular dependencies
- Single points of failure
- Components that are candidates for change vs. components that are stable

### Step 3: Read Implementations

**Architecture documents describe INTENT. Code describes REALITY.** When they conflict, code wins.

For each component in scope:
- Read the actual interface contracts (not the documentation — the code)
- Identify implicit assumptions (e.g., ordering guarantees, idempotency, thread safety)
- Note technical debt and workarounds that the architecture doc doesn't mention

### Step 4: Review Prior Architectural Decisions

Read all ADRs (Architecture Decision Records), prior design documents, or session outputs in this series:
- What patterns were established?
- What was tried and rejected? (Rejected alternatives are as valuable as accepted ones.)
- What trade-offs were made, and have conditions changed?

### Step 5: Challenge Scope

Apply the Splitting Test at the architectural level:
- Does this design encompass multiple bounded contexts?
- Would changes to one part require changes to another? (Coupling test)
- Could this be delivered incrementally, or must it be all-or-nothing?

### Step 6: Validate Technology Fit

For each technology or pattern being proposed:
- Is this the standard tool for this problem domain?
- Or are we using a familiar tool instead of the right tool?
- What does the broader industry use for this class of problem?
- What are the 3-year maintenance implications?

### Step 7: Verify Assumptions

For each critical assumption:
- "This API returns data in X format" — verify by reading the code
- "This database can handle Y queries/second" — verify by testing or reading benchmarks
- "This library supports Z" — verify by reading the library source, not the README

---

## Phase 3: Create (Architecture-Specific)

### The Architecture Document

Structure:

```markdown
## Context
- Problem statement
- Constraints
- Current state (diagram)

## Decision
- Proposed architecture (diagram)
- Key components and their responsibilities
- Interface contracts
- Data flow

## Rationale
- Why this approach over alternatives
- Trade-offs accepted
- Risks identified

## Alternatives Considered
| Alternative | Pros | Cons | Why Rejected |

## Migration Path (if modifying existing system)
- Step-by-step transition plan
- Rollback strategy at each step
- What can be done incrementally vs. what requires a cutover

## Impact Analysis
| System | Impact | Action Required |
- What changes
- What doesn't change (explicit scope boundary)
- What might break (risk assessment)

## Verification Plan
- How will we know this works?
- Performance targets and how to measure them
- Integration test strategy
```

### Interface-First Design

Design interfaces (API contracts, message formats, data schemas) before implementation. The interface IS the architecture — implementation is a detail.

For each interface:
- Input contract (what the caller provides)
- Output contract (what the caller receives)
- Error contract (what happens when things go wrong)
- Versioning strategy (how the interface evolves without breaking consumers)

### Failure Mode Analysis

For each component and interface:
- What happens if this component is unavailable?
- What happens if this interface returns an error?
- What happens if latency doubles?
- What is the blast radius of a failure here?

---

## Scope Validation Questions (Architecture-Specific)

1. Am I designing one bounded context or multiple? If multiple, should they be separate designs?
2. Can this be delivered incrementally, or does it require a big-bang cutover?
3. Am I using the right tool for this domain, or a familiar tool that's "close enough"?
4. What are the irreversible decisions in this design? Have I given them proportional scrutiny?
5. Who are the consumers of these interfaces? Have I verified their actual needs (not assumed)?

---

## Verification Checklist (Architecture-Specific)

Before presenting the architecture:

- [ ] Every component has a defined responsibility (single responsibility, clearly bounded)
- [ ] Every interface has input, output, and error contracts defined
- [ ] Dependency graph has no circular dependencies (or they are explicitly justified)
- [ ] Failure modes are analyzed for each critical component
- [ ] Migration path exists with rollback strategy at each step (if modifying existing system)
- [ ] Performance assumptions are verified against actual measurements or credible benchmarks
- [ ] Alternatives are documented with honest pros/cons (not straw-man alternatives)
- [ ] The scope boundary is explicit — what this design changes AND what it does not change

---

## Reference Table Formats (Architecture)

### Interface Catalog
| Interface | Protocol | Input | Output | Error | Versioned? | Consumers |
|-----------|----------|-------|--------|-------|------------|-----------|

### Dependency Matrix
| Component | Depends On | Depended On By | Coupling Level |
|-----------|-----------|----------------|----------------|

### Performance Budget
| Operation | Target Latency | Target Throughput | Current Measured | Headroom |
|-----------|---------------|-------------------|-----------------|----------|

---

## Common Anti-Patterns (Architecture)

1. **Resume-driven architecture** — Choosing technologies because they're interesting or trendy, not because they're the right fit for the problem.
2. **Astronaut architecture** — Designing for hypothetical future requirements that may never materialize. The right amount of abstraction is the minimum needed now.
3. **Documentation-level verification** — Trusting API documentation or README claims without reading the actual implementation or running actual tests.
4. **Big-bang migration** — Designing a migration that requires everything to change at once with no rollback. Every migration should have incremental steps with rollback points.
5. **Implicit assumptions** — Relying on ordering guarantees, idempotency, or thread safety without explicitly verifying and documenting them.
6. **Scope bleed** — Starting with one bounded context and gradually absorbing adjacent concerns. If the scope grows during design, stop and re-evaluate with the Splitting Test.
7. **Straw-man alternatives** — Documenting alternatives that are obviously worse to make the preferred option look good. Honest alternatives have real trade-offs.

---

## Example Session Outline

```
Session 3: Audio Routing Architecture

Pre-Flight: Read prior ADRs. Current audio system uses direct device capture.
            AudioBridge component works but conflicts with streaming.
            Spot-checked WebSocket and CAT subsystems — healthy.

Research:   Requirements: support both local device capture AND remote TCP streaming
            from the same audio source, without device contention.
            Inventoried 6 audio components. Read all implementations.
            Prior sessions established AudioStreamServer/Client (TCP streaming).
            Identified core conflict: AudioBridge and AudioStreamBridge both
            try to own the USB audio device.

Create:     Proposed AudioSourceManager as unified routing hub.
            All consumers register with the manager, not individual sources.
            Interface contract: AudioSourceListener with onAudioData(float[], int).
            Migration: 3-step incremental (add manager → migrate consumers → remove direct capture).
            Rollback: each step is independently reversible.

Present:    Architecture approved. User confirmed both local and remote scenarios
            are required.

Implement:  Safety commit. Created AudioSourceManager.java.
            Migrated 4 consumers. Removed direct AudioBridge capture.
            All audio tests passing.

Close:      0 stakeholder corrections. Clean migration in 3 steps.
            Pattern discovered: "Unified routing hub" — when multiple producers
            feed multiple consumers, insert a manager rather than N*M direct connections.
```
