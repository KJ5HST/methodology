# Changelog — Authoritative Action Ledger

The cumulative, append-only record of **actions taken** in this repository — across backlog
items, repository issues, and ad-hoc work. It is the authoritative answer to *"what was done
here, ever?"* Every session records its actions here at close-out (`SESSION_RUNNER.md`
Phase 3F); Phase 0 reconciles it against `git log` and backfills anything a crashed or
out-of-band session missed. Taking an action — any commit, or any non-commit action — and
not recording it is failure mode #27. Old entries may be archived, never deleted.

**The rules** — how to add an entry, source tags, reading and archiving — are in
`FRAMEWORK_APPARATUS.md` §The Action Ledger, which `bin/sync`
keeps current. ledger-format: 2 — keep this marker; `bin/status` reads it.

<!-- METHODOLOGY-SEED-SENTINEL: fresh ledger, no entries yet. While this line is present AND
     there are no dated (### YYYY-MM-DD) entries below, this is a freshly-seeded ledger, not a
     stale or abandoned one — the freshness check keys on this exact token plus the absence of
     any `### <real-date>` header. Delete this line when you add your first real entry. -->

---

<!-- Entries go below, newest on top. Delete the seed-sentinel line near the top when you add the first one. -->
