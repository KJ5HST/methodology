# Changelog — Authoritative Action Ledger

The cumulative, append-only record of **actions taken** in this repository — across backlog
items, repository issues, and ad-hoc work. It is the authoritative answer to *"what was done
here, ever?"* Every session records its actions here at close-out (`SESSION_RUNNER.md`
Phase 3F); Phase 0 reconciles it against `git log` and backfills anything a crashed or
out-of-band session missed. Taking an action — any commit, or any non-commit action — and
not recording it is failure mode #27. Old entries are archived, never deleted (see below).

<!-- METHODOLOGY-SEED-SENTINEL: fresh ledger, no entries yet. While this line is present AND
     there are no dated (### YYYY-MM-DD) entries below, this is a freshly-seeded ledger, not a
     stale or abandoned one — the freshness check keys on this exact token plus the absence of
     any `### <real-date>` header. Delete this line when you add your first real entry. -->

## How to add an entry

At close-out, prepend one entry per action, **newest on top**. Key on a mechanical fact, not
judgment: *did this session author or retain any commit, or take any non-commit action?* If
yes, an entry is owed — "too small to log" or "I'll batch it next time" **is** failure mode
#27, not an exception. The only exemption is a session whose diff is empty and that took no
action at all.

**Source tag — exactly one per entry, from this closed vocabulary** (so the audit
`grep -E '\[(issue #|BL-|ad hoc)' CHANGELOG.md` enumerates every logged action and proves all
three sources landed):

- `[issue #<N>]` — a repository issue. If issues live in another repo (e.g. an upstream parent
  of a fork), cite an absolute URL, not a bare `#<N>`.
- `[BL-<N>]` — a `BACKLOG.md` item. Remove it from `BACKLOG.md` in the same commit.
- `[ad hoc]` — work with no backlog or issue origin (the source most prone to vanishing):
  releases, tag/branch ops, PR opens, upstream issue closes, access grants, and
  decline/wontfix/grooming decisions all land here.

**Format** — the `###` header line is the required, greppable unit; the detail bullets are
recommended, plus one further bullet, `Model`, that is optional even relative to the others:

```
### YYYY-MM-DD · [SOURCE] one-line outcome-focused summary
- **Change:** what is now true in the repo/product that was not before
- **Commit/PR:** `<short-sha>`  —or—  PR #<N> (merged `<sha>`)
- **Session:** S<N> · **Verified:** <build/test/render/runtime evidence, or "n/a — docs-only">
- **Model:** <acting model> (optional — omit the line entirely when not recorded)
```

*(The `[SOURCE]`, `[issue #<N>]`, `[BL-<N>]`, and `[ad hoc]` tokens above are illustrative; the
freshness check keys on dated `###` entries, of which a fresh seed has none.)*

**Model:** — self-reported, free text; omit the line when not recorded. Names which model
executed the action — an agent-independent key with a concrete value, the same pattern
`key_files` already uses for paths. Single-tier work names one model:

```
### 2026-01-15 · [ad hoc] Ship the export-retry fix
- **Change:** exports now retry once on a transient network error instead of failing immediately
- **Commit/PR:** `a1b2c3d`
- **Session:** S42 · **Verified:** unit suite green, manual retry reproduced and confirmed fixed
- **Model:** <model>
```

Capability-tiered work (one session whose layers are built or reviewed across different tiers) is
recorded *per entry*, not compressed into one line: each layer/checkpoint already gets its own
`CHANGELOG.md` entry, so each entry's **Model:** bullet states only its own role:

```
### 2026-01-16 · [ad hoc] Layer 3 — draft the parser (delegated layer)
- **Change:** the new input format parses without a follow-up fixup pass
- **Commit/PR:** `d4e5f6a`
- **Session:** S43 · **Verified:** unit tests for the new parser pass
- **Model:** <model A> (delegated; reviewed by <model B>)

### 2026-01-16 · [ad hoc] Layer 4 — review and land the parser (primary layer)
- **Change:** the delegated layer's diff is reviewed and the checkpoint committed
- **Commit/PR:** `b7c8d9e`
- **Session:** S43 · **Verified:** full suite green after review fixes
- **Model:** <model B> (primary)
```

`HANDOFFS.md`'s "How to write a receipt" section documents a complementary session-level
convention: naming the model once in a receipt's free-text prose, for a reader who wants one
session's answer without correlating multiple entries here. That convention adds no new
`HANDOFFS.md` schema key — it is not a second, competing structured field, and it is fine for both
files to name the same model for a single-tier session, since they answer different questions
("what happened, action by action" vs. "which model ran this session"). A canonical-only
`bin/model-report` (copy it into your `bin/` if you want it) reads this file's **Model:** bullets
back alongside `HANDOFFS.md`'s free-text mentions and git's `Co-Authored-By` trailers, keeping all
three visually separate — see that tool's own docstring for why trailers are corroboration-only,
never authoritative.

Work committed but not finished — an in-progress hand-off, a reverted slice — still owes an
entry: mark it `(in progress)` in the summary, and a later session closes it out or records
the revert as its own entry. Reverse-chronological, prepend-only, so close-out never re-sorts.
Promote to `## YYYY-MM` sections as the list grows — group by month, **not** by release.

## Size, and when to archive

Sectioning organises this file; it does not shrink it. The file grows without bound and Phase 0
reads it every session, so it also has a size discipline. **Two caps, because there are two
distinct failure modes and neither subsumes the other. Fire if either fires; stop only when both
stop conditions hold.**

| Cap | Protects against | Form | Fire when | Cut until |
|---|---|---|---|---|
| **Lines** — ~2,000, a **proxy** for the agent `Read` cap (the cap itself is denominated in **tokens**, not lines) | **measures an unread tail** — it does not, on its own, establish a remedy. A read past the cap returns only the prefix that fits, and says so: a `PARTIAL view` banner names the delivered span, the true length and the cap, and an explicit over-cap line range errors outright with no content at all. **Announced, not silent.** **Whether archiving the tail REMEDIES this is an open question, not a settled benefit.** Truncation is ordered top-down and this file is newest-on-top, so the records a cut removes are ones a whole-file read was not delivering anyway: the delivered prefix is the same before and after, and what changes is that the reader stops being warned. Raised as BL-52. **Re-measure rather than trusting this row** — the reproduction is `docs/planning/read-cap-premise-correction-plan.md` Appendix A in the framework repo | a **rate** | headroom < **15** entries | headroom > **30** |
| **Bytes** — a per-file budget, default **65,536 B** (64 KB) | **context tax**: every session pays for the whole file, every time | a **level with hysteresis** | `size > budget` | `size ≤ ½ × budget` |

**Run this. Do not eyeball it, and do not trust a size written here or anywhere else** — a number
in prose is stale the next time anyone prepends:

```sh
python3 methodology_trim.py --file CHANGELOG.md --check
```

`--check` evaluates both conditions, reports whether the trigger fires, and never writes. `--write`
performs the trim; a dry run is the default, and it refuses to write unless it can prove the split
lossless. **It neither commits nor stages** — it leaves the live file modified and the new shard
*untracked*, prints the rollback, and leaves the commit to you. Stage both yourself:
`git add CHANGELOG.md docs/archive/` — committing with `-a` alone would land the shortened ledger
while the shard, being untracked, never enters history at all.

**Why the line cap is a rate.** Headroom is `(2000 − lines) × entries-added ÷ lines-added` since the
last split, so it re-derives itself from the file on every read. A hand-written level cannot: it is
a derived value frozen at the moment someone typed it. This framework's own receipt ledger is the
worked example — it states its trigger as a level, *"approaches ~1,200 lines"*, and **that level has
never once fired.** The single archive that file has ever had was taken on judgment at 997 lines,
*before* the level was written; since then the file has grown several times past its byte budget
while still reading "under 1,200 lines". A level in the wrong unit says *fine* indefinitely. Where
there is no slope yet — before the first split, or immediately after one — the rate **abstains out
loud** rather than print a number it cannot support.

**Why the byte cap is not.** *"Cut until headroom is back above 30"* is unreachable on bytes at any
budget: a tool applying it would trim the file to a single record and still report the trigger
unsatisfied. A level with hysteresis terminates, and the ½ factor is what keeps the next entry from
re-firing the trigger immediately.

**The budget is judgment, and it is yours to set.** It does not follow from the line cap — at real
ledger densities, 2,000 lines is a different byte count for every file. Calibrate it the way this
default was: take the sizes your repo has actually operated at comfortably after previous archives,
and set the budget just above them. `--budget-bytes <N>` overrides it for a single run.

**Archiving again is not always the answer.** If the file has already given back everything the
last archive removed, another archive resets the *level* and not the *rate* — the tool measures
exactly that and **refuses to fire**; `--force` is how you overrule it deliberately. Before a file's
first archive there is no baseline to measure against, so it abstains rather than compute a zero.

### The shard convention

An archive is a **shard** — a new frozen file, same format, same newest-on-top order.

- **Path: `docs/archive/<LIVE-BASENAME>-through-<CUT-KEY>.md`.** Both halves are load-bearing. The
  directory keeps a shard from shadowing the live file by sort order, and the `CHANGELOG-` prefix is
  what the trigger's own glob looks for when it hunts its baseline — a shard named otherwise is
  silently invisible to it, and the trigger then measures against the wrong boundary.
- **The live file keeps one short pointer** naming each shard and the span it covers. Every count
  stated in that pointer carries the command that recomputes it, because a hand-maintained count
  drifts on the next prepend.
- **The shard back-links to the live file and states only facts about itself** — its own span, its
  own count. It must **not** restate a forward-looking rule. A shard is frozen, so a rule copied
  into one is wrong the moment the live rule moves, and correcting it means editing a frozen
  record. Cite the live file; do not copy it.
- **After a split the authority is the live file *and* its shards.** Any command that enumerates
  this ledger must span both by glob — `CHANGELOG.md docs/archive/CHANGELOG-*.md` — or the split
  silently shrinks the population the audit was counting.
- **Prefer a release frontier as the cut key**, because a shipped release is a boundary nothing can
  ever be written back into. A calendar date works too, but it is frozen only by convention; if you
  cut at one, say in the shard's own front matter that you departed and why.

**A trim is an action, not a side effect.** It earns its own commit and its own `[ad hoc]` entry
here — one ledger, one shard, one commit, one revert. It does **not** belong in Phase 0, which is
read-only apart from the reconcile backfill.

**Not everything that grows can be archived this way.** Archiving moves *history*. A file that grows
because someone keeps adding *procedure* has no past to move — extract a section to a sibling file
and leave a pointer instead. A backlog of open items is live state rather than history: that is a
grooming problem, and its completed items belong here, in this ledger, not in a frozen shard.

## CHANGELOG.md vs SESSION_NOTES.md — two files, two questions, one shared key

`SESSION_NOTES.md` is the **transient handoff** — *"what's next, what traps?"* — overwritten
every session. `CHANGELOG.md` is the **cumulative ledger** — *"what was done, ever?"* —
append-only, and split into shards once it outgrows a session's read (see above). Nothing is
ever deleted; the oldest entries move. The commit SHA is the only intended intersection. Close-out **distills** the
durable outcome into a ledger entry; it does not copy the handoff. The belongs-here test:
*would the operator, six months out, need this to know what the repo does or how it got there?*

---

<!-- Entries go below, newest on top. Delete the seed-sentinel line near the top when you add the first one. -->
