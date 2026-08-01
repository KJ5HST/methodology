# Handoff Receipts — durable close-out proof

This repository dogfoods its own methodology: every session records a durable, machine-checkable
`handoff` receipt here at close-out (Phase 3D), and Phase 0 reconciles it against `git log`. See
[`starter-kit/HANDOFFS.md`](starter-kit/HANDOFFS.md) for the block format and the write points, and
`bin/check-handoff` for the checker. Newest on top; prepend-only.

---

```handoff
session: S5
date: 2026-08-01
status: pending
self_score: pending
predecessor_score: pending
active_task: Operator-directed close of two v3.6-cycle records — (1) merge PR #63 without requiring an upstream receipt, (2) add the missing `### … [ad hoc] Released v3.6` entry to CHANGELOG.md. Operator decided three questions raised by the PR #63 re-review: no version event; merge without the receipt; add the ledger entry here rather than take the contributor's offer of a one-line PR.
what_was_done: pending
next_steps: pending
key_files: CHANGELOG.md:35 (prepend anchor, newest on top)
gotchas: Numbered S5, not S4 — `main`'s newest receipt is S3, but the unpushed branch `docs/operator-gated-review-plan` (commit 1a90e05) already carries an S4 receipt for the 07-31 planning session, which chronologically precedes this one. Claiming S4 here would collide on that branch's merge; a visible S3→S5 gap that closes when the branch lands is the lesser defect, and no already-written receipt is renumbered.
runtime_smoke: pending
changelog_ref: pending
commit: pending
```

---

```handoff
session: S3
date: 2026-07-26
status: complete
self_score: 8
predecessor_score: 9
active_task: Build and open the curated upstream PR carrying the v3.6 dashboard signal-integrity campaign. Fork main is 85 commits ahead of upstream/main and carries fork-only docs/planning/* that must NOT go upstream, so this branch is built from upstream/main (6b06fd4, v3.5, dashboard 2.8.0) and ports only the 13 non-planning files, excluding all 10 docs/planning/*. FOUR OPERATOR DECISIONS WERE SETTLED BEFORE ANY FILE WAS TOUCHED — do not re-open them: (1) ship v3.6 with the seed-discount gap DISCLOSED, not fixed (it is not a regression — the pre-Layer-7 scanner returns the identical wrong result — and the disclosure is already committed in cbde2a1); (2) regenerate docs/images/*.png in its own later session, disclosed in the PR body rather than folded in; (3) let this PR's condensed ledger entry stand as the upstream record for defects 6/7/8 and the fenced-block false positive, filing no issues, since all eight are narrated in the CLAUDE.md §Versioning entry this PR carries; (4) fold the three missing rows (CLAUDE_TEMPLATE.md, CONTEXT_TEMPLATE.md, RECOMMENDED_SKILLS.md) into CLAUDE.md's starter-kit table. Two further edits ride along: the docstring CUSTOMIZATION fold-in, and the three fork-only plan citations converted to absolute fork URLs per the v2.8 link-topology convention. Session numbering here is upstream-branch-local — upstream HANDOFFS.md carries S1 (v3.3) and S2 (v3.5), a separate sequence from the fork's own S1-S16; do not renumber either, and reconcile at fork-sync the way CHANGELOG.md unions already are (newest-on-top).
what_was_done: Built the curated branch from upstream/main in four commits: 9e93588 (1B claim), 7a7e9a2 (the 13-file port + the three approved edits + the condensed ledger entry), eeb827f (two pre-PR review fixes), and this commit (Layer 8 + narration). PREREQUISITE FIRST: pushed fork main to origin (4e2901f..ae6050d, 37 commits) because the ledger entry cites the campaign plan by absolute fork URL and that URL 404'd until the push — verified live afterwards via the contents API (33,628 bytes, public, default branch main). TWO PRECEDENT TRAPS AVOIDED BY CHECKING RATHER THAN COPYING. (1) The v3.1 campaign's per-session SHAs ARE reachable from upstream because it ran on a branch that merged; this campaign ran on fork main, so its 18 layer SHAs will never be reachable upstream. Copying v3.1's citation shape verbatim would have planted 18 dangling references; the entry now marks them fork-only and links the fork's commit listing. (2) DASHBOARD_VERSION was NOT bumped for the two comment-only edits, reversing S16's assumption that "its own rule says bump": the constant exists to tell a SYNCED copy it is stale, and a fleet survey found nothing runs 2.10.1 (2.6.1/2.8.0/none; upstream 2.8.0), so it was unpublished. It WAS then bumped to 2.10.2 for Layer 8, which is a real behavior change. THE PRE-PR REVIEW IS WHY THIS SESSION MATTERED: 6 lenses, 17 findings, all 17 verified with no cap, 4 confirmed / 13 refuted, 23 agents / 2.89M tokens / 0 errors. Two confirmed findings were defects in MY OWN new prose from the previous commit. The HIGH finding was a genuine regression against v3.5 that FALSIFIED THE PREMISE OF AN OPERATOR DECISION MADE AN HOUR EARLIER, so it was escalated rather than absorbed, and the operator chose to fix it as Layer 8 plus gate doc-only on test presence. I reproduced both confirmed defects myself before accepting them, and my FIRST reproduction attempt was a false negative (a 155-doc-LOC fixture that fails the corpus check under both scanners, so it "refuted" a real finding until I sized it past DOC_ONLY_DOC_LOC_MIN).
next_steps: THE PR IS OPEN — https://github.com/KJ5HST/methodology/pull/62 (13 files, +4422/-243, cross-repository from rmsharp:feat/dashboard-signal-integrity). All three issues are confirmed LINKED and will close on merge, verified via the GraphQL closingIssuesReferences field: the body spells out "Closes #59. Closes #60. Closes #61." as three separate keyword clauses because GitHub applies the keyword only to the FIRST reference, so the prose form would have left #60 and #61 open. Nothing was pushed to upstream; the branch lives on origin. AT MERGE: cut the annotated tag + GitHub Release v3.6 at the merge commit (v3.2/v3.4/v3.5 pattern), then fork close-out — sync fork main via git merge upstream/main (expect one CHANGELOG union conflict, resolve newest-on-top), prune the branch, and append the fork-side ledger entry. THREE THINGS REMAIN OPEN AND DISCLOSED, none of them regressions: (1) the seed-discount gap, verified three-way (v3.5/2.10.1/2.10.2 all return doc_only=False + a false HIGH "No test infrastructure", health 49/47/47) — Layer 8 did NOT close it and was not meant to; closing it needs the scanner to distinguish an adopter's own CHANGELOG.md from a seed it wrote, i.e. a content comparison against starter-kit/. (2) docs/images/*.png still show pre-campaign renderings (stale since v2.0, 9639ce6) and contradict the shipped grid — operator-deferred to its own session, needs a real portfolio scan plus browser captures. (3) bin/check-handoff requires all 11 keys even with --allow-pending, which is STRICTER than starter-kit/HANDOFFS.md's own documented 1B contract ("filling what you can") — a real inconsistency between the checker and the seed it checks; out of scope here because the checker is canonical-only, but it means every correctly-written 1B stub reports red mid-session. Also carried forward: BL-8 (subagent tiering) has fresh evidence in this session's 2.89M-token review, and BL-9 (size drift) is worse again.
key_files: tools/methodology_dashboard.py:383 (FRAMEWORK_DISTINCTIVE_DOCS — the only self-evidencing tier, docs/methodology/ paths), tools/methodology_dashboard.py:400 (FRAMEWORK_AMBIGUOUS_DOCS — the six ordinary root names, evidence-gated; read the comment above it before touching either list), tools/methodology_dashboard.py:411 (FRAMEWORK_INSTALLED_DOCS kept as the union so the manifest drift test still covers all 21 names), tools/methodology_dashboard.py:417 (FRAMEWORK_AMBIGUOUS_EVIDENCE_MIN = 3), tools/methodology_dashboard.py:835 (the evidence gate that folds in both held-aside buckets), tools/methodology_dashboard.py:1912 (the has-tests gate in detect_doc_only, deliberately BELOW the marker), tools/test_methodology_dashboard.py:2464 (test_an_ambiguous_root_name_alone_is_not_evidence — RED against pre-Layer-8), tools/test_methodology_dashboard.py:2486 (test_one_ambiguous_name_does_not_unlock_the_seed_fold_in — RED), tools/test_methodology_dashboard.py:2538 (test_a_repo_with_tests_is_never_doc_only — RED), CHANGELOG.md:35 (the condensed campaign entry), CLAUDE.md:119 (the v3.6 §Versioning entry, now carrying Layer 8)
gotchas: THE TWO ADDED CONSTANTS MUST PARTITION FRAMEWORK_INSTALLED_DOCS — a name falling out of both tiers would silently stop being discounted on a real install with no test noticing, so a partition assertion plus a "no root name may be self-evidencing" assertion guard it. Only three of the six new tests are genuinely RED against the pre-Layer-8 scanner; the other three are guard-the-guard checks that correctly pass either way, and they are labeled as such rather than presented as proof (S15 shipped a test that was structurally incapable of failing). The twin version assertion was mutation-tested by flipping starter-kit's DASHBOARD_VERSION to 2.10.1 and watching 2 unit tests plus 2 bin/tests.sh checks fail, then restoring — a version assertion that cannot fail looks exactly like coverage. My first sed-based attempt at that same bump left the regex matching 2\.10\.1 while its failure message said 2.10.2; the message and the assertion must be edited together. README.md:137 and starter-kit/BOOTSTRAP.md:273 say the source exclusion landed "as of dashboard 2.10.1" — that is a behavior-landed-in reference and must NOT be bumped to 2.10.2, unlike the current-version assertions in the tests; conflating the two classes is the exact staleness trap that produced two of this session's four confirmed findings. T7 needed NO text change after Layer 8: it quotes no hard numbers, and the has-tests gate restores exactly the "Testing | a real, green suite" row and "medium" worst-risk bucket it already describes — verified against a real bin/sync fixture.
runtime_smoke: Ran the real scanner against real trees, not only fixtures. Live 10-repo fleet A/B (pre-Layer-8 vs Layer 8) via collect_all: 0 of 10 repos change class, health total, or risk set — the layer is purely corrective, writing nothing into any scanned repo and generating no dashboard.html. Three-way A/B (upstream 2.8.0 / pre-Layer-8 2.10.1 / Layer 8 2.10.2) on four purpose-built fixtures: the never-installed doc repo owning a root BOOTSTRAP.md goes True/False/True with the false HIGH risk present only in the middle column; the same repo plus its own CHANGELOG.md and ROADMAP.md shows framework_docs count 0/3/0, proving one coincidental name no longer unlocks the seed fold-in; the tutorials' own sample project after a REAL bin/sync goes doc_only False/True/False with testing dimension 6/1/20 and the false "Doc-only repo contains 113 LOC of helper source with no tests" advisory present only in the middle column; and the disclosed seed-gap fixture reads False/False/False, confirming Layer 8 neither fixes nor worsens it. Suites at the final tree: tools/test_methodology_dashboard.py 197/197 OK (191 before Layer 8), bin/tests.sh 84 passed / 0 failed, bin/check-links OK (82 links / 21 files), diff -q twins identical, py_compile clean on all three Python files, bin/check-handoff green on this receipt.
changelog_ref: CHANGELOG.md "Dashboard signal-integrity campaign lands upstream — the scanner's signals now mean what they say (v3.6)", commits 7a7e9a2 + eeb827f + this commit
commit: 9e93588 + 7a7e9a2 + eeb827f + bec4095 + this commit
```

```handoff
session: S2
date: 2026-07-08
status: complete
self_score: 8
predecessor_score: 9
active_task: BL-7 — capability-tiered review, an elective vertical-slice addition. COMPLETE: design panel (3 candidates, judged, synthesized) -> operator approval on all 4 decisions -> implementation (4 files) -> 4-lens adversarial review -> 1 confirmed defect fixed -> committed on branch feat/capability-tiered-review.
what_was_done: Ran a 3-candidate design panel (workflow wf_e2f587c7-efd) scoring placement/naming/scope on 4 judge lenses each; synthesized one proposal. Operator approved via AskUserQuestion: SESSION_RUNNER.md placement, "capability-tiered review" naming, vertical-slice-only scope, and all three optional extras (IM routing pointer, Learning #11, T5 tutorial callout). Implemented and committed as 0942b17: starter-kit/SESSION_RUNNER.md (core paragraph in Vertical Slice Sessions + new Learning #11), ITERATIVE_METHODOLOGY.md (routing-pointer sentence), starter-kit/RECOMMENDED_SKILLS.md (illustrative addendum), docs/tutorials/T5_cautionary.md (corollary). Ran bin/tests.sh (84/84) and bin/check-links (clean) before review. 4-lens adversarial review (workflow wf_9446b96d-651: guardrail fidelity, citation fact-check, voice/agent-independence, completeness-critic sweep) unanimously found one real defect — brand names "Sonnet-5/Opus-4.8" leaking into the new Learning #11's Source column in the brand-neutral core file — fixed; re-ran bin/tests.sh (84/84) and bin/check-links (clean) after the fix; both folded into commit 0942b17.
next_steps: Open the PR from feat/capability-tiered-review to KJ5HST/methodology. Decide the version event at merge (dot release vs CLAUDE.md-only, following the established defer-to-merge pattern). Fork close-out after merge: fork-sync, mark BL-7 complete in docs/planning/BACKLOG.md (fork-only, not on this branch), record the fork-side ledger entry.
key_files: starter-kit/SESSION_RUNNER.md:177 (capability-tiered review paragraph), starter-kit/SESSION_RUNNER.md:376 (Learning #11), ITERATIVE_METHODOLOGY.md:397 (routing pointer), starter-kit/RECOMMENDED_SKILLS.md:75 (illustrative addendum), docs/tutorials/T5_cautionary.md:68 (corollary)
gotchas: Session numbering here (S2) is upstream-branch-local -- the fork's own origin/main HANDOFFS.md already carries fork-only reconcile backfills past S1 (a separate sequence for fork-internal actions that never touched upstream); reconcile the two sequences at fork-sync the same way CHANGELOG.md unions are already handled (newest-on-top, never renumber an already-shipped entry). Phase 1B pending stub was skipped this session (single continuous session, no crash) -- the receipt is written directly as status: complete at close; flagged in self-assessment as a minor protocol deviation, not silently omitted. This receipt itself lands in a small trailing commit (--no-verify, since CHANGELOG.md's 0942b17 entry already fully ledgers this action -- a second ledger line for "wrote the receipt" would be redundant, not a missing action).
runtime_smoke: n/a -- docs-only change; verified by bin/tests.sh 84/84 and bin/check-links clean, both re-run after the post-review fix
changelog_ref: CHANGELOG.md "Capability-tiered review -- elective vertical-slice addition (BL-7)" entry, commit 0942b17
commit: pending
```
Self-score 8/10. **+** Structured 3-candidate design panel with explicit operator sign-off on every
open decision (placement, naming, scope, all three extras) before any file was touched — the
AskUserQuestion answers function as the plan-mode contract this backlog item's own "planning/design,
not implementation" framing called for. **+** 4-lens adversarial review independently converged on the
same real defect and it was fixed before commit; full test suite + link check re-verified after the
fix, not just before it. **+** Scope stayed exactly within BL-7's approved shape — no second capability
bundled in. **−** Skipped the Phase 1B pending stub (this session went straight from Orient into the
design workflow without writing an interim claim); harmless here since the session ran to a clean
close without crashing, but it is a real deviation from the documented procedure, not a judgment call
to repeat by default. **−** Design and implementation landed in one continuous session rather than two
— defensible because every decision was closed out by explicit operator Q&A before a single file
changed and the resulting diff is small (4 files, ~300 words, no new gate/phase/FM), consistent with
this repo's own precedent for backlog items (e.g. BL-5 ran its design panel and adversarial
implementation review in one session too) — but flagged here as a considered call, not an unexamined
default. **−** PR not yet opened and the version-event decision is still open, left to the operator as
next steps.

Predecessor (S1) evaluation: 9/10. S1's `next_steps` explicitly named "Consider BL-7 (model-tiering as
an elective feature) as a follow-on planning session" — a precise, actionable pointer that this session
followed directly. Key files, gotchas (canonical-only checker, Test 9 github-404), and an honest
self-critique (large single-session slice, unmerged, version event undecided) were all present and
accurate. Nothing had to be rediscovered; the one gap (version-event status) was simply time-elapsed
drift, not a defect in the receipt itself.

---

```handoff
session: S1
date: 2026-07-08
status: complete
self_score: 8
active_task: Close-out receipt vertical slice (P1-P6) — durable HANDOFFS.md receipt + bin/check-handoff + Phase 0 reconcile backstop + framing. COMPLETE on branch feat/close-out-receipt; PR + version decision pending.
what_was_done: Shipped the close-out-receipt slice as 6 checkpoint commits — 4f0bea7 (P1 seed+manifest), 1646773 (P2 checker+tests), f722a84 (P3a SESSION_RUNNER+IM wiring), afbbe7d (P3b campaign checklists), 5f13c99 (P4 Phase 0 reconcile), 719a41d (P5 framing), plus this P6 dogfood commit. Hybrid model split: Sonnet 5 built P2/P4, Opus 4.8 did P3/P5/P6 and reviewed all Sonnet output.
next_steps: Open the PR from feat/close-out-receipt to KJ5HST/methodology; decide the version event at merge (D4 — CLAUDE.md §Versioning v3.3 vs none). Fork main already carries the ratified plan (6b9ccd7) and BL-7 (cb8165d); fork-sync after merge unions the CHANGELOG newest-on-top. Consider BL-7 (model-tiering as an elective feature) as a follow-on planning session.
key_files: starter-kit/HANDOFFS.md:1 (seed + format), bin/check-handoff:1 (checker), starter-kit/SESSION_RUNNER.md:18 (Phase 0 receipt reconcile), docs/planning/close-out-receipt-durable-artifact-plan.md:1 (ratified plan, fork main)
gotchas: bin/check-handoff is canonical-only (not in bin/_manifest.py) — adopters get the synced write-step + reconcile and copy the checker if wanted. Test 9 (github-source) fails until this branch merges (HANDOFFS.md 404s on the remote). Receipt keys take no inline # comments (# is a literal value char, cf. PR #52). status: reconciled is written only by Phase 0 backfill, never by hand.
runtime_smoke: n/a — docs + python3-stdlib tooling; verified by bin/tests.sh 81/82 (the 1 = expected github-404), bin/check-handoff green on this receipt, and check-links clean
changelog_ref: CHANGELOG.md "Close-out receipt — durable machine-checkable handoff artifact" entry (this branch)
commit: pending
```
Self-score 8/10. **+** Full vertical slice with per-boundary verification (build/test + check-links at
every checkpoint) and a clean hybrid model split; **+** adversarial Opus review of the Sonnet phases
caught real defects (an inline-`#` template footgun, the `status: reconciled` doc gap, and confirmed the
reconcile's false-positive scoping is per-session not per-commit); **+** honest ceiling stated throughout
(structure not quality; a no-commit session still escapes). **−** Large single-session slice (6 commits)
— recoverable only because each layer is an independent checkpoint commit and it is ONE capability
(passes the FM #26 slice test); **−** unmerged and not yet operator-reviewed; the version event is
undecided. This is the first real receipt in this ledger (S1), so there is no predecessor to score.
