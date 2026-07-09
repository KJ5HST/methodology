#!/usr/bin/env bash
# Smoke tests for bin/sync and bin/status.
# Run: ./bin/tests.sh  (from methodology repo root)
set -uo pipefail

BIN="$(cd "$(dirname "$0")" && pwd)"
METHODOLOGY="$(dirname "$BIN")"
STARTER="$METHODOLOGY/starter-kit"
PASS=0
FAIL=0

pass() { echo "  PASS: $*"; PASS=$((PASS+1)); }
fail() { echo "  FAIL: $*"; FAIL=$((FAIL+1)); }

mktemp_project() {
    local dir
    dir="$(mktemp -d)"
    git -C "$dir" init -q
    echo "$dir"
}

echo "== Test 1: commit mode + local source (baseline) =="
P="$(mktemp_project)"
"$BIN/sync" "$P" --mode=commit --source=local >/dev/null
diff -q "$P/SESSION_RUNNER.md" "$STARTER/SESSION_RUNNER.md" >/dev/null && pass "SESSION_RUNNER matches canonical" || fail "SESSION_RUNNER drift"
diff -q "$P/SAFEGUARDS.md" "$STARTER/SAFEGUARDS.md" >/dev/null && pass "SAFEGUARDS matches canonical" || fail "SAFEGUARDS drift"
diff -q "$P/methodology_dashboard.py" "$STARTER/methodology_dashboard.py" >/dev/null && pass "dashboard matches canonical" || fail "dashboard drift"
[ -x "$P/methodology_dashboard.py" ] && pass "dashboard is executable" || fail "dashboard not executable"
[ ! -f "$P/.gitignore" ] && pass "commit mode leaves .gitignore alone" || fail "commit mode created .gitignore"
rm -rf "$P"

echo "== Test 2: dry-run doesn't modify =="
P="$(mktemp_project)"
"$BIN/sync" "$P" --dry-run >/dev/null
[ ! -f "$P/SESSION_RUNNER.md" ] && pass "dry-run skipped SESSION_RUNNER" || fail "dry-run wrote SESSION_RUNNER"
[ ! -f "$P/.gitignore" ] && pass "dry-run skipped .gitignore" || fail "dry-run wrote .gitignore"
rm -rf "$P"

echo "== Test 3: ignore mode adds .gitignore + warns on tracked files =="
P="$(mktemp_project)"
"$BIN/sync" "$P" --mode=commit --source=local >/dev/null
(cd "$P" && git add -A && git -c user.email=t@t -c user.name=t commit -q -m "baseline")
OUTPUT="$("$BIN/sync" "$P" --mode=ignore 2>&1)"
grep -q "^/SESSION_RUNNER.md$" "$P/.gitignore" && pass "gitignore has SESSION_RUNNER" || fail "gitignore missing SESSION_RUNNER"
grep -q "^/SAFEGUARDS.md$" "$P/.gitignore" && pass "gitignore has SAFEGUARDS" || fail "gitignore missing SAFEGUARDS"
grep -q "^/methodology_dashboard.py$" "$P/.gitignore" && pass "gitignore has dashboard" || fail "gitignore missing dashboard"
echo "$OUTPUT" | grep -q "WARNING" && pass "ignore mode warns on tracked files" || fail "ignore mode silent on tracked files"
echo "$OUTPUT" | grep -q "git -C .* rm --cached" && pass "warning includes rm --cached command" || fail "warning missing rm command"
# Idempotent on second run
"$BIN/sync" "$P" --mode=ignore >/dev/null
[ "$(grep -c '^/SESSION_RUNNER.md$' "$P/.gitignore")" = "1" ] && pass "idempotent gitignore" || fail "gitignore duplicated"
rm -rf "$P"

echo "== Test 4: auto-detect mode from .gitignore =="
P="$(mktemp_project)"
printf "/SESSION_RUNNER.md\n/SAFEGUARDS.md\n/methodology_dashboard.py\n" > "$P/.gitignore"
OUTPUT="$("$BIN/sync" "$P" 2>&1)"
echo "$OUTPUT" | grep -q "mode:    ignore" && pass "auto-detected ignore mode" || fail "mode auto-detect wrong: $OUTPUT"
rm -rf "$P"

echo "== Test 5: auto-detect source prefers local sibling =="
P="$(mktemp_project)"
OUTPUT="$("$BIN/sync" "$P" --dry-run 2>&1)"
echo "$OUTPUT" | grep -q "source:  local" && pass "auto-detected local source" || fail "source auto-detect wrong"
rm -rf "$P"

echo "== Test 6: status reports current / modified / N-behind / missing =="
P="$(mktemp_project)"
"$BIN/sync" "$P" --mode=commit >/dev/null
OUT="$("$BIN/status" "$P")"
echo "$OUT" | grep -q "current" && pass "status: current" || fail "status: current missing"

echo "# local edit" >> "$P/SESSION_RUNNER.md"
OUT="$("$BIN/status" "$P")"
echo "$OUT" | grep -q "locally modified" && pass "status: locally modified" || fail "status: locally modified missing"

# Revert to an older blob from methodology history
OLDER_COMMIT="$(git -C "$METHODOLOGY" log --format=%H -- starter-kit/SESSION_RUNNER.md | sed -n '2p')"
if [ -n "$OLDER_COMMIT" ]; then
    git -C "$METHODOLOGY" show "$OLDER_COMMIT:starter-kit/SESSION_RUNNER.md" > "$P/SESSION_RUNNER.md"
    OUT="$("$BIN/status" "$P")"
    echo "$OUT" | grep -Eq "[0-9]+ version" && pass "status: N versions behind detected" || fail "status: N-behind not detected"
fi

rm "$P/SAFEGUARDS.md"
OUT="$("$BIN/status" "$P")"
echo "$OUT" | grep -q "missing" && pass "status: missing" || fail "status: missing not detected"
rm -rf "$P"

echo "== Test 7: sync refuses to overwrite locally-modified files without --force =="
P="$(mktemp_project)"
"$BIN/sync" "$P" --mode=commit >/dev/null
echo "# LOCAL CUSTOMIZATION" >> "$P/SESSION_RUNNER.md"
BEFORE="$(cat "$P/SESSION_RUNNER.md")"
OUTPUT="$("$BIN/sync" "$P" 2>&1)"; RC=$?
[ "$RC" != "0" ] && pass "sync exits non-zero when local drift present" || fail "sync exited 0 despite local drift"
echo "$OUTPUT" | grep -q "ERROR" && pass "sync prints ERROR on local drift" || fail "no ERROR printed"
echo "$OUTPUT" | grep -q -- "--force" && pass "ERROR mentions --force" || fail "ERROR missing --force hint"
[ "$(cat "$P/SESSION_RUNNER.md")" = "$BEFORE" ] && pass "file unchanged when blocked" || fail "file modified despite block"

# --force proceeds
"$BIN/sync" "$P" --force >/dev/null && pass "--force overrides block" || fail "--force did not override"
diff -q "$P/SESSION_RUNNER.md" "$STARTER/SESSION_RUNNER.md" >/dev/null && pass "--force restores canonical" || fail "--force did not restore canonical"
rm -rf "$P"

echo "== Test 8: sync upgrades N-versions-behind without --force =="
P="$(mktemp_project)"
"$BIN/sync" "$P" --mode=commit >/dev/null
OLDER_COMMIT="$(git -C "$METHODOLOGY" log --format=%H -- starter-kit/SESSION_RUNNER.md | sed -n '2p')"
if [ -n "$OLDER_COMMIT" ]; then
    git -C "$METHODOLOGY" show "$OLDER_COMMIT:starter-kit/SESSION_RUNNER.md" > "$P/SESSION_RUNNER.md"
    "$BIN/sync" "$P" >/dev/null && pass "upgrade from older version proceeds without --force" || fail "upgrade blocked incorrectly"
    diff -q "$P/SESSION_RUNNER.md" "$STARTER/SESSION_RUNNER.md" >/dev/null && pass "upgraded to canonical" || fail "not upgraded"
fi
rm -rf "$P"

echo "== Test 9: github source (requires gh auth; skipped if unauthenticated) =="
if gh auth status >/dev/null 2>&1; then
    P="$(mktemp_project)"
    "$BIN/sync" "$P" --source=github --dry-run >/dev/null && pass "github source dry-run works" || fail "github source dry-run failed"
    rm -rf "$P"
else
    echo "  SKIP: gh unauthenticated"
fi

echo "== Test 10: distributed-file links resolve in the simulated adopter tree =="
if "$BIN/check-links" >/dev/null 2>&1; then
    pass "check-links: all relative links resolve in adopter layout"
else
    "$BIN/check-links" 2>&1 | sed 's/^/    /'
    fail "check-links: dangling link(s) in adopter layout (see above)"
fi

echo "== Test 11: sync produces the full manifest tree (faithful, per-file) =="
P="$(mktemp_project)"
"$BIN/sync" "$P" --mode=commit >/dev/null
MANIFEST_OK=1
COUNT=0
while IFS='|' read -r src dest disp; do
    [ -z "$dest" ] && continue
    COUNT=$((COUNT+1))
    if [ ! -f "$P/$dest" ]; then MANIFEST_OK=0; echo "    MISSING: $dest"; continue; fi
    if [ "$disp" = "tracked" ]; then
        diff -q "$P/$dest" "$METHODOLOGY/$src" >/dev/null || { MANIFEST_OK=0; echo "    DRIFT: $dest"; }
    fi
done < <(python3 -c "import sys; sys.path.insert(0, '$BIN'); import _manifest; [print('%s|%s|%s' % (s, d, x)) for s, d, x in _manifest.DISTRIBUTION]")
[ "$MANIFEST_OK" = "1" ] && pass "all $COUNT manifest files present; tracked files match canonical" || fail "manifest tree incomplete/drifted"
# subdir dest spot-check (the multi-dir tree, not just root files)
[ -f "$P/docs/methodology/ITERATIVE_METHODOLOGY.md" ] && pass "framework doc landed under docs/methodology/" || fail "docs/methodology/ doc missing"
[ -f "$P/docs/methodology/workstreams/AUDIT_WORKSTREAM.md" ] && pass "workstream landed under docs/methodology/workstreams/" || fail "workstreams/ doc missing"
rm -rf "$P"

echo "== Test 12: seed files created once, never clobbered (even --force) =="
P="$(mktemp_project)"
"$BIN/sync" "$P" >/dev/null
[ -f "$P/SESSION_NOTES.md" ] && pass "seed SESSION_NOTES created when absent" || fail "seed not created"
echo "ADOPTER LOG ENTRY" > "$P/SESSION_NOTES.md"
"$BIN/sync" "$P" >/dev/null
grep -q "ADOPTER LOG ENTRY" "$P/SESSION_NOTES.md" && pass "seed not overwritten on normal sync" || fail "seed overwritten on sync"
"$BIN/sync" "$P" --force >/dev/null
grep -q "ADOPTER LOG ENTRY" "$P/SESSION_NOTES.md" && pass "seed not overwritten even with --force" || fail "seed overwritten by --force"
rm -rf "$P"

echo "== Test 13: adopter-owned instances are never sync targets =="
P="$(mktemp_project)"
"$BIN/sync" "$P" >/dev/null
[ ! -f "$P/CONTEXT.md" ] && pass "sync did not create instance CONTEXT.md" || fail "sync created instance CONTEXT.md"
[ ! -f "$P/CLAUDE.md" ] && pass "sync did not create instance CLAUDE.md" || fail "sync created instance CLAUDE.md"
[ -f "$P/CONTEXT_TEMPLATE.md" ] && pass "template CONTEXT_TEMPLATE.md is present" || fail "template CONTEXT_TEMPLATE.md missing"
rm -rf "$P"

echo "== Test 14: check-links validates the sync-produced tree without mutating it (issue #36) =="
P="$(mktemp_project)"
"$BIN/sync" "$P" >/dev/null
BEFORE="$(cd "$P" && find . -type f | sort)"
if "$BIN/check-links" --tree "$P" >/dev/null 2>&1; then
    pass "check-links --tree: links resolve in the sync-produced tree"
else
    "$BIN/check-links" --tree "$P" 2>&1 | sed 's/^/    /'
    fail "check-links --tree: dangling link(s) in sync-produced tree"
fi
# A checker must not write to the tree it validates (issue #36): it must not
# fabricate the adopter-owned placeholder files (CONTEXT.md, CLAUDE.md, …) that a
# sync-produced tree legitimately lacks.
AFTER="$(cd "$P" && find . -type f | sort)"
if [ "$BEFORE" = "$AFTER" ]; then
    pass "check-links --tree: left the validated tree unmodified (issue #36)"
else
    fail "check-links --tree: mutated the tree it validated (issue #36)"
    diff <(printf '%s\n' "$BEFORE") <(printf '%s\n' "$AFTER") | sed 's/^/    /'
fi
rm -rf "$P"

echo "== Test 15: status emits per-file rows with a disposition column (Phase 4) =="
P="$(mktemp_project)"
"$BIN/sync" "$P" --mode=commit >/dev/null
OUT="$("$BIN/status" "$P")"
echo "$OUT" | grep -q "Disposition" && pass "status: Disposition column present" || fail "status: no Disposition column"
echo "$OUT" | grep -q "tracked" && pass "status: tracked disposition shown" || fail "status: no tracked rows"
echo "$OUT" | grep -q "seed" && pass "status: seed disposition shown" || fail "status: no seed rows"
# One data row per manifest entry (full Option-B corpus, not a fixed three)
EXPECTED="$(python3 -c "import sys; sys.path.insert(0, '$BIN'); import _manifest; print(len(_manifest.DISTRIBUTION))")"
GOT="$(echo "$OUT" | grep -c "$(basename "$P")")"
[ "$GOT" = "$EXPECTED" ] && pass "status: one row per manifest file ($GOT == $EXPECTED)" || fail "status: row count $GOT != manifest $EXPECTED"
# Freshly-synced tree: every tracked file current, nothing flagged as drift
echo "$OUT" | grep -q "current" && pass "status: fresh tree shows current" || fail "status: fresh tree missing current"
if echo "$OUT" | grep -Eq "locally modified|versions? behind"; then fail "status: fresh tree shows spurious drift"; else pass "status: fresh tree shows no drift"; fi
rm -rf "$P"

echo "== Test 16: an absent seed file is reported, never flagged as drift (Phase 4 DONE) =="
P="$(mktemp_project)"
"$BIN/sync" "$P" >/dev/null
rm -f "$P/CHANGELOG.md"   # CHANGELOG.md is a SEED file (adopter-owned)
SEEDLINE="$("$BIN/status" "$P" | grep "CHANGELOG.md")"
echo "$SEEDLINE" | grep -q "seed" && pass "status: CHANGELOG shown with seed disposition" || fail "status: CHANGELOG not marked seed"
echo "$SEEDLINE" | grep -q "absent" && pass "status: absent seed shown as 'absent'" || fail "status: absent seed not 'absent'"
if echo "$SEEDLINE" | grep -q "missing"; then fail "status: absent seed mislabeled as drift (missing)"; else pass "status: absent seed NOT flagged as drift"; fi
rm -rf "$P"

echo "== Test 17: a partially-stale tree flags only the stale file (Phase 4) =="
P="$(mktemp_project)"
"$BIN/sync" "$P" >/dev/null
echo "# local edit" >> "$P/SESSION_RUNNER.md"
OUT="$("$BIN/status" "$P")"
NMOD="$(echo "$OUT" | grep -c "locally modified")"
[ "$NMOD" = "1" ] && pass "status: exactly one file locally modified" || fail "status: expected 1 modified, got $NMOD"
echo "$OUT" | grep "SESSION_RUNNER.md" | grep -q "locally modified" && pass "status: the stale file is SESSION_RUNNER" || fail "status: wrong file flagged stale"
rm -rf "$P"

echo "== Test 18: dashboard scoring unit tests (BL-5 doc-only reshape) =="
if python3 "$METHODOLOGY/tools/test_methodology_dashboard.py" >/dev/null 2>&1; then
    pass "dashboard scoring unit tests green"
else
    fail "dashboard scoring unit tests failed"
fi

echo "== Test 19: dashboard twins byte-identical + same DASHBOARD_VERSION =="
diff -q "$METHODOLOGY/tools/methodology_dashboard.py" "$STARTER/methodology_dashboard.py" >/dev/null \
    && pass "dashboard twins byte-identical" || fail "dashboard twins differ"
TV="$(grep -E '^DASHBOARD_VERSION' "$METHODOLOGY/tools/methodology_dashboard.py")"
SV="$(grep -E '^DASHBOARD_VERSION' "$STARTER/methodology_dashboard.py")"
[ "$TV" = "$SV" ] && pass "dashboard twins carry the same DASHBOARD_VERSION" || fail "DASHBOARD_VERSION mismatch across twins"

echo "== Test 20: a seed whose format predates canonical is flagged advisory-only (BL-6 item 2) =="
P="$(mktemp_project)"
"$BIN/sync" "$P" >/dev/null
# Row-vs-note isolation: the migration note also names CHANGELOG.md and contains the tokens 'seed'
# and 'stale format', so any row-specific assertion must exclude the note line (`grep -v '^note:'`)
# or it is vacuous — it would pass on the prose note regardless of the table row (adversarial-review fix).
# (a) Freshly-seeded CHANGELOG carries the current action-ledger format → plain 'present', no note.
OUT="$("$BIN/status" "$P")"
echo "$OUT" | grep "CHANGELOG.md" | grep -v '^note:' | grep -q "stale format" && fail "status: current-format (fresh) seed mis-flagged stale" || pass "status: current-format (fresh) seed not flagged"
echo "$OUT" | grep -q "^note:" && fail "status: spurious stale-format note on fresh tree" || pass "status: no stale-format note on fresh tree"
# (b) In-use current-format ledger: the METHODOLOGY-SEED-SENTINEL is deleted (as the adopter does on its
# first real entry) and a dated entry appended, but the ledger TITLE is retained. This is the exact case
# the marker choice is engineered around (key on the lifetime-stable title, NOT the deletable sentinel);
# it must NOT be flagged, or binding constraint #2 (no false positive on a current-format seed) breaks.
printf '# Changelog — Authoritative Action Ledger\n\nThe action ledger.\n\n---\n\n### 2026-01-01 · [ad hoc] a real entry\n- Change: something real.\n' > "$P/CHANGELOG.md"
grep -q "METHODOLOGY-SEED-SENTINEL" "$P/CHANGELOG.md" && fail "test-bug: in-use fixture still carries the sentinel" || pass "test: in-use fixture is title-only (sentinel deleted)"
OUT="$("$BIN/status" "$P")"
echo "$OUT" | grep "CHANGELOG.md" | grep -v '^note:' | grep -q "stale format" && fail "status: in-use current-format ledger mis-flagged stale (constraint #2)" || pass "status: in-use current-format ledger not flagged"
echo "$OUT" | grep -q "^note:" && fail "status: spurious note on in-use current-format ledger" || pass "status: no note on in-use current-format ledger"
# (c) Replace the seed with a pre-v3.1 (Keep-a-Changelog) shape lacking the ledger-title marker.
printf '# Changelog\n\nAll notable changes to this project.\n\n## [Unreleased]\n' > "$P/CHANGELOG.md"
OUT="$("$BIN/status" "$P")"
ROW="$(echo "$OUT" | grep "CHANGELOG.md" | grep -v '^note:')"   # table row only, note excluded
echo "$ROW" | grep -q "seed" && pass "status: stale seed keeps its seed disposition" || fail "status: stale seed lost seed disposition"
echo "$ROW" | grep -q "stale format" && pass "status: pre-v3.1 seed flagged 'present (stale format)'" || fail "status: stale seed not flagged"
# Advisory only — never reclassified as drift.
if echo "$ROW" | grep -Eq "missing|locally modified|versions? behind"; then fail "status: stale seed mislabeled as drift"; else pass "status: stale seed NOT treated as drift"; fi
echo "$OUT" | grep -q "^note:" && pass "status: emits the migration note beneath the table" || fail "status: no migration note for stale seed"
# (d) A seed without a format marker (SESSION_NOTES.md) is never format-checked → never stale.
echo "arbitrary adopter content" > "$P/SESSION_NOTES.md"
"$BIN/status" "$P" | grep "SESSION_NOTES.md" | grep -v '^note:' | grep -q "stale format" && fail "status: markerless seed mis-flagged" || pass "status: markerless seed never flagged stale"
# (e) The flag never triggers an overwrite: sync leaves the adopter-owned stale seed untouched.
"$BIN/sync" "$P" >/dev/null
grep -q "\[Unreleased\]" "$P/CHANGELOG.md" && pass "sync: stale seed left untouched (still adopter-owned)" || fail "sync: stale seed was overwritten"
"$BIN/status" "$P" | grep "CHANGELOG.md" | grep -v '^note:' | grep -q "stale format" && pass "status: still flags stale after a re-sync" || fail "status: stale flag lost after re-sync"
# (f) Multi-project scan: the note headline counts stale INSTANCES (one per project), matching the number
# of flagged table rows — not distinct file types (adversarial-review fix). P is still stale from (c/e).
P2="$(mktemp_project)"
"$BIN/sync" "$P2" >/dev/null
printf '# Changelog\n\n## [Unreleased]\n' > "$P2/CHANGELOG.md"
MULTI="$("$BIN/status" "$P" "$P2")"
NROWS="$(echo "$MULTI" | grep -v '^note:' | grep -c "stale format")"
[ "$NROWS" = "2" ] && pass "status: two stale rows across two projects" || fail "status: expected 2 stale rows, got $NROWS"
echo "$MULTI" | grep '^note:' | grep -q "2 seeds predate" && pass "status: note count matches flagged rows (2), not deduped file types" || fail "status: note count != flagged rows"
rm -rf "$P" "$P2"

# Shared fixture builder for Tests 21-22: a fully well-formed, status: complete
# `handoff` receipt (starter-kit/HANDOFFS.md field list). Each variant below pipes
# this through sed/grep to break exactly one thing.
good_handoff() {
    cat <<'EOF'
```handoff
session: S12
date: 2026-07-08
status: complete
self_score: 8
predecessor_score: 7
active_task: Implementing bin/check-handoff (Phase P2)
what_was_done: Wrote bin/check-handoff and Tests 21-22; commit a1b2c3d
next_steps: Wire bin/check-handoff into SESSION_RUNNER.md Phase 3D close-out gate
key_files: bin/check-handoff:1, bin/tests.sh:230
gotchas: A bare-backtick wrapper around an example must not parse as a real block
runtime_smoke: n/a — docs-only
changelog_ref: PR #52
commit: a1b2c3d
```
Free-text prose: implemented the checker end to end, self-score +8/-2 (docstring could be tighter).
EOF
}

echo "== Test 21: check-handoff — well-formed receipt passes; field/value defects are caught =="
F="$(mktemp)"
good_handoff > "$F"
"$BIN/check-handoff" --file "$F" >/dev/null 2>&1 && pass "well-formed complete receipt passes" || fail "well-formed complete receipt should pass"
rm -f "$F"

F="$(mktemp)"
good_handoff | grep -v '^gotchas:' > "$F"
"$BIN/check-handoff" --file "$F" >/dev/null 2>&1 && fail "missing required key (gotchas) not caught" || pass "missing required key (gotchas) caught"
rm -f "$F"

F="$(mktemp)"
good_handoff | sed 's/^next_steps:.*/next_steps: /' > "$F"
"$BIN/check-handoff" --file "$F" >/dev/null 2>&1 && fail "empty required field (next_steps) not caught" || pass "empty required field (next_steps) caught"
rm -f "$F"

F="$(mktemp)"
good_handoff | sed 's/^self_score:.*/self_score: 11/' > "$F"
"$BIN/check-handoff" --file "$F" >/dev/null 2>&1 && fail "self_score out of 1..10 not caught" || pass "self_score out of 1..10 caught"
rm -f "$F"

F="$(mktemp)"
good_handoff | sed 's#^key_files:.*#key_files: bin/check-handoff, bin/tests.sh#' > "$F"
"$BIN/check-handoff" --file "$F" >/dev/null 2>&1 && fail "key_files missing path:line token not caught" || pass "key_files missing path:line token caught"
rm -f "$F"

# Regression (final-review C1): an incidental colon-digit run in prose (a scripture
# ref, a time, a ratio) must NOT satisfy key_files — the pre-colon token must be path-like.
F="$(mktemp)"
good_handoff | sed 's#^key_files:.*#key_files: reviewed the citation John 3:16, no files edited#' > "$F"
"$BIN/check-handoff" --file "$F" >/dev/null 2>&1 && fail "key_files incidental colon-digit (John 3:16) wrongly passed" || pass "key_files incidental colon-digit (no path) caught"
rm -f "$F"

# Regression (final-review C2): a bare 7+ digit decimal (a count/timestamp) must NOT
# satisfy what_was_done's sha-shape check — a real sha carries a hex letter.
F="$(mktemp)"
good_handoff | sed 's#^what_was_done:.*#what_was_done: processed 12345678 records, forgot to note the sha#' > "$F"
"$BIN/check-handoff" --file "$F" >/dev/null 2>&1 && fail "what_was_done decimal-only (12345678, no sha) wrongly passed" || pass "what_was_done decimal-only (no hex letter) caught"
rm -f "$F"

echo "== Test 22: check-handoff — anti-pattern lints, modes (--allow-pending), fresh-seed, block isolation =="
F="$(mktemp)"
good_handoff | sed 's/^next_steps:.*/next_steps: pick next from backlog/' > "$F"
"$BIN/check-handoff" --file "$F" >/dev/null 2>&1 && fail "'pick next from backlog' not caught" || pass "'pick next from backlog' caught"
rm -f "$F"

F="$(mktemp)"
good_handoff | sed 's/^gotchas:.*/gotchas: need to verify this later/' > "$F"
"$BIN/check-handoff" --file "$F" >/dev/null 2>&1 && fail "'need to verify' placeholder not caught" || pass "'need to verify' placeholder caught"
rm -f "$F"

F="$(mktemp)"
good_handoff | sed 's/^commit:.*/commit: pending/' > "$F"
"$BIN/check-handoff" --file "$F" >/dev/null 2>&1 && pass "commit: pending is accepted" || fail "commit: pending should be accepted"
rm -f "$F"

F="$(mktemp)"
good_handoff | sed 's/^session:.*/session: S1/' | grep -v '^predecessor_score:' > "$F"
"$BIN/check-handoff" --file "$F" >/dev/null 2>&1 && pass "Session-1 fixture without predecessor_score passes" || fail "Session-1 exemption not honored"
rm -f "$F"

F="$(mktemp)"
good_handoff | sed 's/^status:.*/status: pending/' > "$F"
"$BIN/check-handoff" --file "$F" >/dev/null 2>&1 && fail "status: pending should fail by default" || pass "status: pending fails by default"
"$BIN/check-handoff" --file "$F" --allow-pending >/dev/null 2>&1 && pass "status: pending passes with --allow-pending" || fail "--allow-pending did not accept status: pending"
rm -f "$F"

F="$(mktemp)"
good_handoff | sed 's/^status:.*/status: reconciled/' > "$F"
"$BIN/check-handoff" --file "$F" >/dev/null 2>&1 && pass "status: reconciled (Phase 0 backfill) is accepted" || fail "status: reconciled should be accepted"
rm -f "$F"

F="$(mktemp)"
cat > "$F" <<'EOF'
# Handoff Receipts

<!-- METHODOLOGY-SEED-SENTINEL: fresh receipt ledger, no receipts yet. -->

Receipts go below, newest on top.
EOF
"$BIN/check-handoff" --file "$F" >/dev/null 2>&1 && pass "fresh-seed fixture (sentinel, no blocks) passes" || fail "fresh-seed fixture should pass"
rm -f "$F"

# Block isolation: a prose line OUTSIDE the fenced block contains the exact
# anti-pattern text, and does not satisfy any field either — the real block below
# it is well-formed, so the outside noise must not affect the verdict either way.
F="$(mktemp)"
{
    echo 'NOTE: a bad example looks like "next_steps: pick next from backlog" - avoid it.'
    echo
    good_handoff
} > "$F"
"$BIN/check-handoff" --file "$F" >/dev/null 2>&1 && pass "prose outside the fenced block does not trigger the lint (block isolation)" || fail "block isolation: outside prose leaked into the check"
rm -f "$F"

echo ""
echo "== Summary: $PASS passed, $FAIL failed =="
[ "$FAIL" = "0" ]
