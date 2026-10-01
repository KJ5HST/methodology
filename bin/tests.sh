#!/usr/bin/env bash
# Smoke tests for the bin/ tooling: sync, status, check-links, check-handoff,
# check-learnings.
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
echo "$OUTPUT" | grep -q "local modifications" && pass "a full-history source blames local modifications" || fail "ERROR no longer names local modifications"
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

echo "== Test 9: github source (needs the network; skipped if the repository is unreachable) =="
# --source=github clones the repository over HTTPS, so the guard is reachability, not gh auth. The
# timeout keeps a machine with no route to GitHub from hanging the suite.
URL="${METHODOLOGY_SOURCE_URL:-https://github.com/KJ5HST/methodology.git}"
if python3 -c 'import subprocess, sys; sys.exit(subprocess.run(["git", "ls-remote", "--exit-code", "-h", sys.argv[1]], capture_output=True, timeout=30).returncode)' "$URL" >/dev/null 2>&1; then
    P="$(mktemp_project)"
    "$BIN/sync" "$P" --source=github --dry-run >/dev/null && pass "github source dry-run works" || fail "github source dry-run failed"
    rm -rf "$P"
else
    echo "  SKIP: $URL unreachable"
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
# The trimmer's own tests ran in NOTHING until this line. That was tolerable while the tool was
# canonical-only; it stops being tolerable once `bin/sync` installs it at adopter roots, because
# `bash bin/tests.sh` would stay green with a shipped executable arbitrarily broken.
if python3 "$METHODOLOGY/tools/test_methodology_trim.py" >/dev/null 2>&1; then
    pass "ledger trimmer unit tests green"
else
    fail "ledger trimmer unit tests failed"
fi
# Same argument as the trimmer's, one tool over. The context_budget.py block below covers the
# budget gate's install/sync/selftest surface; until this line its calibrate() had no test of
# its ARITHMETIC at all, and returned noise on any repo that had merged another lineage of
# its regressor while every row here stayed green.
if python3 "$METHODOLOGY/tools/test_context_budget.py" >/dev/null 2>&1; then
    pass "context budget gate unit tests green"
else
    fail "context budget gate unit tests failed"
fi
# The ratchet is the third shipped executable; same argument. Its --selftest below covers the
# install/hook surface in a scratch repo; the unit suite covers the arithmetic every rule rests on.
if python3 "$METHODOLOGY/tools/test_quality_ratchet.py" >/dev/null 2>&1; then
    pass "quality ratchet unit tests green"
else
    fail "quality ratchet unit tests failed"
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
# first real entry) and a dated entry appended, but the seed's marker line is retained. This is the exact
# case the marker choice is engineered around (key on a lifetime-stable line the seed tells adopters to
# keep, NOT the deletable sentinel); it must NOT be flagged, or binding constraint #2 (no false positive
# on a current-format seed) breaks.
printf '# Changelog — Authoritative Action Ledger\n\nThe action ledger. ledger-format: 2 — keep this marker.\n\n---\n\n### 2026-01-01 · [ad hoc] a real entry\n- Change: something real.\n' > "$P/CHANGELOG.md"
grep -q "METHODOLOGY-SEED-SENTINEL" "$P/CHANGELOG.md" && fail "test-bug: in-use fixture still carries the sentinel" || pass "test: in-use fixture is current-format with the sentinel deleted"
OUT="$("$BIN/status" "$P")"
echo "$OUT" | grep "CHANGELOG.md" | grep -v '^note:' | grep -q "stale format" && fail "status: in-use current-format ledger mis-flagged stale (constraint #2)" || pass "status: in-use current-format ledger not flagged"
echo "$OUT" | grep -q "^note:" && fail "status: spurious note on in-use current-format ledger" || pass "status: no note on in-use current-format ledger"
# (b2) The seed as shipped before ledger-format 2, frozen in tools/fixtures/: it carries the current TITLE
# and the full rules text, and must still read stale. BOOTSTRAP.md ("Updating an existing project…") promises status "flags any seed
# whose format predates the current methodology"; a marker present in any earlier format can never keep
# that promise. Driven RED against the title-keyed marker before the marker moved.
SEED1="$METHODOLOGY/tools/fixtures/seed-CHANGELOG-ledger-format-1.md"
grep -q "Authoritative Action Ledger" "$SEED1" && pass "test: the frozen pre-ledger-format-2 seed carries the current title" || fail "test-bug: the frozen seed lacks the title it stands for"
cp "$SEED1" "$P/CHANGELOG.md"
ROW="$("$BIN/status" "$P" | grep "CHANGELOG.md" | grep -v '^note:')"
echo "$ROW" | grep -q "stale format" && pass "status: the pre-ledger-format-2 seed flagged 'present (stale format)'" || fail "status: the pre-ledger-format-2 seed NOT flagged — BOOTSTRAP.md's "Updating an existing project" paragraph promises it is"
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
# (g) Each flagged file gets ITS OWN migration route. A stale CHANGELOG.md replaces its
# header with the seed's; a stale HANDOFFS.md only lacks the seed's size section, and replacing its front
# matter would delete what a trimmer wrote there (a pointer block, a count sentence). The note once gave
# the replace route for both. P is stale in CHANGELOG.md only (c/e); P2 gets a stale HANDOFFS.md alone.
NOTE="$("$BIN/status" "$P" | grep '^note:')"
echo "$NOTE" | grep -q "for CHANGELOG.md, replace the rules text or old header above the first entry" && pass "status: a stale CHANGELOG.md gets the replace-the-header route" || fail "status: the note lacks CHANGELOG.md's route"
# The trimmer writes an archive-pointer block and a month heading above the first entry; a route that
# replaced everything there would delete them (an adopter's migration hit exactly this).
echo "$NOTE" | grep -q "keeping any archive-pointer block and month heading" && pass "status: the CHANGELOG.md route keeps what the trimmer wrote" || fail "status: the CHANGELOG.md route would delete the trimmer's pointer block"
echo "$NOTE" | grep -q "Size, and when to archive" && fail "status: the note gives HANDOFFS.md's route when only CHANGELOG.md is stale" || pass "status: no HANDOFFS.md route when only CHANGELOG.md is stale"
cp "$STARTER/CHANGELOG.md" "$P2/CHANGELOG.md"   # P2's CHANGELOG.md was stale from (f): current seed again
printf '# Handoff Receipts\n\nNewest on top; prepend-only.\n\n```handoff\nsession: S1\ndate: 2026-01-01\nstatus: complete\n```\n' > "$P2/HANDOFFS.md"
OUT="$("$BIN/status" "$P2")"
echo "$OUT" | grep "HANDOFFS.md" | grep -v '^note:' | grep -q "stale format" && pass "status: a HANDOFFS.md without the size section flagged 'present (stale format)'" || fail "status: the stale HANDOFFS.md NOT flagged"
NOTE="$(echo "$OUT" | grep '^note:')"
echo "$NOTE" | grep -q "1 seed predates the current format (HANDOFFS.md," && pass "test: HANDOFFS.md is the only stale seed in P2" || fail "test-bug: P2 is not stale in HANDOFFS.md alone"
echo "$NOTE" | grep -q "for HANDOFFS.md, bring across the current starter-kit seed's '## Size, and when to archive' section" && pass "status: a stale HANDOFFS.md gets the bring-across-the-section route" || fail "status: the note lacks HANDOFFS.md's own route"
echo "$NOTE" | grep -qi "replace" && fail "status: the note tells a stale HANDOFFS.md to replace its front matter" || pass "status: no replace route for a stale HANDOFFS.md"
# The HANDOFFS.md seed as shipped before handoffs-format 2 already had the size section's heading, but
# with the old premise in it (a 65,536 B byte row priced as a "context tax"). Keyed on that heading, it read
# current in two of six real adopters that carry exactly that text. Keyed on the versioned marker, it is stale.
grep -q "handoffs-format: 2" "$STARTER/HANDOFFS.md" && pass "test: the shipped HANDOFFS.md seed carries its format marker" || fail "the shipped HANDOFFS.md seed lacks 'handoffs-format: 2'"
cp "$STARTER/CHANGELOG.md" "$P2/CHANGELOG.md"
printf '# Handoff Receipts\n\n## Size, and when to archive\n\n| **Bytes** — a per-file budget, default **65,536 B** (64 KB) | **context tax**: every session pays for the whole file |\n\n```handoff\nsession: S1\ndate: 2026-01-01\nstatus: complete\n```\n' > "$P2/HANDOFFS.md"
ROW="$("$BIN/status" "$P2" | grep "HANDOFFS.md" | grep -v '^note:')"
echo "$ROW" | grep -q "stale format" && pass "status: a HANDOFFS.md with the old size section but no format marker flagged stale" || fail "status: the pre-handoffs-format-2 seed read current — its heading alone is not a format marker"
# Both stale in one project: both routes, one each.
cp "$SEED1" "$P2/CHANGELOG.md"
NOTE="$("$BIN/status" "$P2" | grep '^note:')"
echo "$NOTE" | grep -q "for CHANGELOG.md, replace" && echo "$NOTE" | grep -q "for HANDOFFS.md, bring across" && pass "status: two stale seeds in one project get both routes" || fail "status: the note lacks a route when both seeds are stale"
# The section the note points to gives the same HANDOFFS.md route, so following the pointer cannot
# contradict the note (the note cites BOOTSTRAP.md's "Updating an existing project from an earlier
# methodology version" paragraph).
grep '^\*\*Updating an existing project from an earlier methodology version:\*\*' "$STARTER/BOOTSTRAP.md" | grep -q "Size, and when to archive" && pass "BOOTSTRAP.md: the paragraph the note cites gives HANDOFFS.md's route too" || fail "BOOTSTRAP.md: the paragraph the note cites has no HANDOFFS.md route"
grep '^\*\*Updating an existing project from an earlier methodology version:\*\*' "$STARTER/BOOTSTRAP.md" | grep -q "keeping any archive-pointer block and month heading" && pass "BOOTSTRAP.md: the paragraph the note cites keeps the trimmer's lines in CHANGELOG.md's route too" || fail "BOOTSTRAP.md: the cited paragraph's CHANGELOG.md route would delete the trimmer's pointer block"
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

# Fences with an info string. CommonMark opens a fence with three or more backticks and an
# optional info string (```sh), and closes it only with a bare run at least as long. The
# seed's "Size, and when to archive" section carries a ```sh block, so an adopter's ledger
# has one above its receipts. Read as prose, that block's closing fence was taken for a
# wrapper opener: everything up to the next bare fence was skipped, the newest receipt with
# it, and the check still reported OK. Most fixtures below put a receipt with a defect where
# a skip would hide it; the first assertion is the control that shows the defect is caught
# whenever the receipt is read.
receipt() {  # receipt SESSION [KEY] — good_handoff as SESSION, without KEY's line if given
    good_handoff | sed "s/^session:.*/session: $1/" | grep -v "^${2:-no-such-key}:"
}
seed_front() {  # the seed as an adopter keeps it: sentinel comment deleted, receipts to follow
    python3 - "$STARTER/HANDOFFS.md" <<'PY'
import re, sys
s = open(sys.argv[1], encoding="utf-8").read()
new = re.sub(r"<!-- METHODOLOGY-SEED-SENTINEL.*?-->\n", "", s, count=1, flags=re.S)
if new == s or not re.search(r"^```(?!handoff)[^`\s]", new, flags=re.M):
    sys.exit(2)  # no sentinel to delete, or no info-string fence left: the fixture is vacuous
sys.stdout.write(new)
PY
}
all_reads_two() {  # all_reads_two FILE — --all exits 0 and counts exactly two receipts
    local out rc
    out="$("$BIN/check-handoff" --file "$1" --all 2>&1)"; rc=$?
    [ "$rc" = 0 ] && [[ "$out" == *"— 2 receipt(s) in"* ]]
}

F="$(mktemp)"
{ receipt S13 gotchas; receipt S12; } > "$F"
"$BIN/check-handoff" --file "$F" >/dev/null 2>&1 && fail "control: a newest receipt missing gotchas passed" || pass "control: a newest receipt missing gotchas is caught"

{ printf 'Run this:\n\n```sh\npython3 methodology_trim.py --file HANDOFFS.md --check\n```\n\n'; receipt S13 gotchas; receipt S12; } > "$F"
"$BIN/check-handoff" --file "$F" >/dev/null 2>&1 && fail "a \`\`\`sh block above the receipts hid the newest one" || pass "a \`\`\`sh block above the receipts does not hide the newest"

if seed_front > "$F"; then
    { receipt S13 gotchas; receipt S12; } >> "$F"
    "$BIN/check-handoff" --file "$F" >/dev/null 2>&1 && fail "the seed's own front matter hid the newest receipt" || pass "the seed's front matter does not hide the newest receipt"
    seed_front > "$F"; { receipt S13; receipt S12; } >> "$F"
    all_reads_two "$F" && pass "--all reads both receipts below the seed's front matter" || fail "--all under the seed's front matter did not read exactly two receipts"
else
    fail "fixture: the seed has no sentinel comment or no info-string fence — the seed cases would test nothing"
fi

{ receipt S13; printf '\n```sh\nbin/check-handoff --all\n```\n\n'; receipt S12 gotchas; } > "$F"
"$BIN/check-handoff" --file "$F" --all >/dev/null 2>&1 && fail "a \`\`\`sh block in a receipt's prose hid the receipt below it from --all" || pass "a \`\`\`sh block in a receipt's prose does not hide the receipt below it"

{ printf '````\n```sh\necho example\n```\n```handoff\nsession: S0\n```\n````\n\n'; receipt S13 gotchas; receipt S12; } > "$F"
"$BIN/check-handoff" --file "$F" >/dev/null 2>&1 && fail "a \`\`\`sh block inside a 4-backtick wrapper hid the newest receipt" || pass "a \`\`\`sh block inside a 4-backtick wrapper stays inert"

# A line that starts with inline code quoting a fence is prose: an info string may not
# contain a backtick, so this line opens nothing.
{ printf '```` ```sh ```` is the fence the seed carries; this line is prose, not a fence.\n\n'; receipt S13; receipt S12; } > "$F"
all_reads_two "$F" && pass "a prose line quoting a fence in inline code opens no fence" || fail "a prose line quoting a fence in inline code was read as a fence"

# A longer fence closes only on a run at least as long: its inner ``` is content.
{ printf '````sh\n```\n````\n\n'; receipt S13; receipt S12; } > "$F"
all_reads_two "$F" && pass "a \`\`\`\`sh fence is closed only by a run of four" || fail "a \`\`\`\`sh fence was closed by a shorter run"

{ receipt S13; receipt S12; printf '\n```sh\necho never closed\n'; } > "$F"
"$BIN/check-handoff" --file "$F" --all >/dev/null 2>&1 && fail "an unclosed \`\`\`sh fence not caught by --all" || pass "an unclosed \`\`\`sh fence caught by --all"

# A receipt whose fence tag is misspelled is not a receipt, and its fields are still
# reported as orphaned, from its first field's own line: skipping the block must not
# hide what it holds.
{ receipt S13 | sed 's/^```handoff$/```handof/'; receipt S12; } > "$F"
out="$("$BIN/check-handoff" --file "$F" --all 2>&1)"; rc=$?
[ "$rc" != 0 ] && [[ "$out" == *"line 2: receipt field outside"* ]] && pass "a receipt under a misspelled fence tag is reported as orphaned, at its own line" || fail "a receipt under a misspelled fence tag went unreported, or was reported at the wrong line"
rm -f "$F"


# ---------------------------------------------------------------------------
# Tests 23-25 — structural invariants for the repo's OWN numbered sets (issue #65).
#
# Learning #12 pointed at the files Learning #12 lives in: before these, a Learning
# row could be renumbered, duplicated, malformed or deleted, and an older handoff
# receipt destroyed outright, with the whole suite still green.
#
# Every mutation below is driven RED first (issue #65 makes that precondition
# non-negotiable) AND guarded against vacuity: `mutate` aborts if the edit did not
# change the file, because a fixture that silently fails to break anything is a test
# that proves nothing. Two mutations were caught being vacuous exactly this way while
# these tests were written.
# ---------------------------------------------------------------------------

# mutate SRC DST PY — apply a python transform, failing loudly if it is a no-op.
mutate() {
    python3 - "$1" "$2" "$3" <<'PY'
import sys
src, dst, expr = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(src, encoding="utf-8").read()
new = eval(expr, {"s": s, "re": __import__("re")})
if new == s:
    sys.stderr.write("MUTATION VACUOUS: %s\n" % expr)
    sys.exit(2)
open(dst, "w", encoding="utf-8").write(new)
PY
}

echo "== Test 23: check-learnings — Learnings table shape (issue #65 Evidence A) =="
# The table now lives in its own file (S34, BL-9); check-learnings' default_path follows it,
# so this test mutates FRAMEWORK_LEARNINGS.md rather than SESSION_RUNNER.md, which no longer
# carries the table at all.
RUNNER="$STARTER/FRAMEWORK_LEARNINGS.md"
F="$(mktemp)"

# Presence control: the real table must pass, or every RED below is meaningless.
OUT23="$("$BIN/check-learnings" --file "$RUNNER" --no-citations 2>&1)"
if echo "$OUT23" | grep -q '^check-learnings: OK'; then
    pass "canonical Learnings table passes (presence control)"
else
    fail "canonical Learnings table presence control: expected clean, got: $OUT23"
fi

# The canonical table and the citation sweep together, against the live corpus.
OUTALL="$("$BIN/check-learnings" 2>&1)"
if echo "$OUTALL" | grep -q '^check-learnings: OK'; then
    pass "canonical table + distributed-corpus citations all resolve"
else
    fail "canonical citation sweep: expected clean, got: $OUTALL"
fi

# The 4 mutation tests below assert on the SPECIFIC finding text each mutation should produce,
# not merely "any failure". check-learnings' exit code is a UNION over every check it runs, so
# an exit-code assertion passes against any unrelated finding the corpus happens to carry —
# and it grew a second arm (the per-row byte budget) that would satisfy every one of them.

# A malformed 3-column row. Anchored on the LEARNINGS row 13's own text, not the bare
# string "| 13 |". The hazard that forced this is now historical — SESSION_RUNNER.md's
# failure-mode table also numbered a row 13, and anchoring there mutated the wrong set
# and proved nothing (this happened) — but the content anchor is kept: it is what makes
# the mutation provably hit the row named in the assertion.
if mutate "$RUNNER" "$F" 's.replace("| 13 | **A forward-looking", "| 14 | three | columns |\n| 13 | **A forward-looking", 1)'; then
    OUT="$("$BIN/check-learnings" --file "$F" --no-citations 2>&1)"
    echo "$OUT" | grep -q "has 3 column" \
        && pass "malformed 3-column row caught" || fail "malformed 3-column row not caught: $OUT"
else fail "3-column mutation was vacuous"; fi

# Renumbering row 13 to a duplicate 12 — the regression CLAUDE.md forbids outright.
if mutate "$RUNNER" "$F" 's.replace("| 13 | **A forward-looking", "| 12 | **A forward-looking", 1)'; then
    OUT="$("$BIN/check-learnings" --file "$F" --no-citations 2>&1)"
    echo "$OUT" | grep -q "duplicate Learning number #12" \
        && pass "duplicate row number caught" || fail "duplicate row number not caught: $OUT"
else fail "duplicate-number mutation was vacuous"; fi

# Deleting a row outright — leaves a gap in the numbering. Anchored on Learning #11's
# own text for the reason above: a wrong-target mutation is NOT vacuous — it really does
# change the file — so the vacuity guard cannot catch it, and only the RED run exposes it.
if mutate "$RUNNER" "$F" 're.sub(r"(?m)^\| 11 \| \*\*Heterogeneous.*\n", "", s, count=1)'; then
    OUT="$("$BIN/check-learnings" --file "$F" --no-citations 2>&1)"
    echo "$OUT" | grep -q "missing #11" \
        && pass "deleted row (numbering gap) caught" || fail "deleted row (numbering gap) not caught: $OUT"
else fail "row-deletion mutation was vacuous"; fi

# A row wrapped onto a second physical line.
if mutate "$RUNNER" "$F" 's.replace("mechanical, encode it as a test", "mechanical,\nencode it as a test", 1)'; then
    OUT="$("$BIN/check-learnings" --file "$F" --no-citations 2>&1)"
    echo "$OUT" | grep -q "non-table line inside the Learnings table" \
        && pass "row split across two physical lines caught" || fail "row split across two physical lines not caught: $OUT"
else fail "line-wrap mutation was vacuous"; fi
rm -f "$F"

echo "== Test 24: check-learnings — citations into the distributed corpus resolve =="
# A distributed file citing a Learning that does not exist. Uses a scratch COPY of
# the corpus file so the real tree is never mutated; the sweep reads the live repo,
# so the assertion runs against a temporarily-modified working file and restores it.
SAFE="$STARTER/SAFEGUARDS.md"
BAK="$(mktemp)"
cp "$SAFE" "$BAK"
if mutate "$SAFE" "$SAFE" 's.replace("## Commit Discipline", "## Commit Discipline\n\nSee Learning #4242 for background.\n", 1)'; then
    "$BIN/check-learnings" >/dev/null 2>&1 \
        && fail "dangling Learning citation in a distributed file not caught" \
        || pass "dangling Learning citation in a distributed file caught"
else fail "dangling-citation mutation was vacuous"; fi
cp "$BAK" "$SAFE"; rm -f "$BAK"
# Restoration control: the tree must be clean again, or the test poisoned the repo.
"$BIN/check-learnings" >/dev/null 2>&1 \
    && pass "corpus restored after the citation mutation" \
    || fail "citation mutation left the corpus dirty"

echo "== Test 25: check-handoff --all — whole-ledger invariants (issue #65 Evidence B) =="
LEDGER="$METHODOLOGY/HANDOFFS.md"
F="$(mktemp)"

if [ -f "$LEDGER" ]; then
    # Presence control. --allow-pending because a session in flight legitimately has
    # a Phase 1B stub as its newest receipt; older ones must still be closed.
    "$BIN/check-handoff" --file "$LEDGER" --all --allow-pending >/dev/null 2>&1 \
        && pass "live receipt ledger passes --all (presence control)" \
        || fail "live receipt ledger should pass --all"

    # Evidence B: strip an older receipt's opening fence + its session/date lines.
    # The default newest-only mode reports OK on this file — that IS the blind spot.
    if mutate "$LEDGER" "$F" 're.sub(r"```handoff\nsession: S7\ndate: [0-9-]+\n", "", s, count=1)'; then
        "$BIN/check-handoff" --file "$F" --allow-pending >/dev/null 2>&1 \
            && pass "default mode still green on a destroyed older receipt (documents the gap)" \
            || fail "default mode unexpectedly changed behaviour"
        "$BIN/check-handoff" --file "$F" --all --allow-pending >/dev/null 2>&1 \
            && fail "orphaned receipt body not caught by --all" || pass "orphaned receipt body caught by --all"
    else fail "orphaned-receipt mutation was vacuous"; fi

    # Duplicate receipt identity — session AND date, the pair. The header is copied
    # from the S8 block rather than hardcoded, so the mutation cannot degrade into a
    # session-only collision if a date later changes and stop testing what it claims.
    if mutate "$LEDGER" "$F" 're.sub(r"session: S7\ndate: [0-9-]+", re.search(r"session: S8\ndate: [0-9-]+", s).group(0), s, count=1)'; then
        "$BIN/check-handoff" --file "$F" --all --allow-pending >/dev/null 2>&1 \
            && fail "duplicate session+date not caught" || pass "duplicate session+date caught"
    else fail "duplicate-identity mutation was vacuous"; fi

    # The paired NEGATIVE: a repeated session id on DIFFERENT dates is legitimate, not
    # corruption. `S<N>` is a per-sequence counter and one ledger may merge two
    # sequences (a fork and its upstream), so keying uniqueness on the id alone
    # false-positives on a valid file. Without this assertion the checker is free to
    # silently tighten back to session-only and no test would notice.
    if mutate "$LEDGER" "$F" 're.sub(r"session: S7\ndate: [0-9-]+", "session: S8\ndate: 2026-07-30", s, count=1)'; then
        "$BIN/check-handoff" --file "$F" --all --allow-pending >/dev/null 2>&1 \
            && pass "repeated session id on different dates is accepted (two merged sequences)" \
            || fail "repeated session id on different dates was wrongly flagged"
    else fail "merged-sequence mutation was vacuous"; fi

    # session:/date: must lead every block.
    if mutate "$LEDGER" "$F" 're.sub(r"session: S7\ndate: ([0-9-]+)\nstatus: complete", r"status: complete\nsession: S7\ndate: \1", s, count=1)'; then
        "$BIN/check-handoff" --file "$F" --all --allow-pending >/dev/null 2>&1 \
            && fail "session/date not leading a block was not caught" || pass "session/date must lead every block"
    else fail "key-order mutation was vacuous"; fi

    # An OLDER receipt left pending — --allow-pending exempts only the newest.
    if mutate "$LEDGER" "$F" 're.sub(r"(session: S7\ndate: [0-9-]+\n)status: complete", r"\1status: pending", s, count=1)'; then
        "$BIN/check-handoff" --file "$F" --all --allow-pending >/dev/null 2>&1 \
            && fail "older pending receipt not caught (--allow-pending over-applied)" \
            || pass "older pending receipt caught; --allow-pending exempts only the newest"
    else fail "older-pending mutation was vacuous"; fi

    # An unclosed fence.
    if mutate "$LEDGER" "$F" 's[:s.rindex("```")] + s[s.rindex("```")+3:]'; then
        "$BIN/check-handoff" --file "$F" --all --allow-pending >/dev/null 2>&1 \
            && fail "unclosed fence not caught" || pass "unclosed fence caught"
    else fail "unclosed-fence mutation was vacuous"; fi
else
    pass "no root HANDOFFS.md in this repo — --all ledger tests not applicable"
fi
rm -f "$F"

echo "== Test: context_budget.py =="
CB="$STARTER/context_budget.py"
[ -x "$CB" ] && pass "context_budget.py is executable" || fail "context_budget.py not executable"

# The tool's own gate tests: every ceiling observed FAILING as well as passing.
P="$(mktemp_project)"
cp "$STARTER/context-budget.json" "$P/.context-budget.json"
cp "$CB" "$P/context_budget.py"
(cd "$P" && python3 context_budget.py --selftest >/dev/null 2>&1) \
    && pass "context_budget --selftest: all gates observed failing and passing" \
    || fail "context_budget --selftest reported a failing gate"

# Seed config must be valid JSON and must not carry a --force escape hatch.
python3 -c "import json,sys; json.load(open('$STARTER/context-budget.json'))" 2>/dev/null \
    && pass "seed .context-budget.json parses as JSON" || fail "seed config is not valid JSON"
grep -q '"--force" in args' "$CB" && fail "context_budget.py accepts --force" \
    || pass "context_budget.py has no --force escape hatch (usage text may name it)"

# An over-budget resident file must exit 2, and shrinking it must clear.
printf 'x%.0s' $(seq 1 40000) > "$P/CLAUDE.md"
(cd "$P" && python3 context_budget.py >/dev/null 2>&1); [ "$?" = "2" ] \
    && pass "over-ceiling resident file exits 2" || fail "over-ceiling file did not exit 2"
printf '<!-- budget:protected -->\n%s\n<!-- /budget:protected -->\n' \
    "$(printf 'y%.0s' $(seq 1 900))" > "$P/CLAUDE.md"
(cd "$P" && python3 context_budget.py >/dev/null 2>&1); [ "$?" != "2" ] \
    && pass "shrinking below the ceiling clears the breach" || fail "shrunk file still exits 2"

# Removing the protected purpose block must be refused even when the file is small.
printf 'tiny\n' > "$P/CLAUDE.md"
(cd "$P" && python3 context_budget.py >/dev/null 2>&1); [ "$?" = "2" ] \
    && pass "removing the budget:protected block is refused" \
    || fail "protected-block removal was not caught"
rm -rf "$P"

# install-hook must write where git will actually LOOK. `core.hooksPath` redirects git
# away from <git-dir>/hooks, and BOOTSTRAP.md Step 10 tells adopters to set it — so a
# hook written to .git/hooks on such a repo is never run while "installed" is printed.
# Paired presence control below: the default path must keep working.
P="$(mktemp_project)"
cp "$STARTER/context-budget.json" "$P/.context-budget.json"
cp "$CB" "$P/context_budget.py"
mkdir -p "$P/.githooks"
git -C "$P" config core.hooksPath .githooks
(cd "$P" && python3 context_budget.py install-hook >/dev/null 2>&1)
[ -f "$P/.githooks/pre-commit" ] \
    && pass "install-hook honors core.hooksPath" \
    || fail "install-hook ignored core.hooksPath (hook git never runs)"
[ ! -f "$P/.git/hooks/pre-commit" ] \
    && pass "install-hook writes no dead hook under .git/hooks when redirected" \
    || fail "install-hook wrote to .git/hooks despite core.hooksPath"
# A foreign hook already in the redirected dir must be reported, never clobbered.
printf '#!/bin/sh\n# ledger co-staging gate\nexit 0\n' > "$P/.githooks/pre-commit"
(cd "$P" && python3 context_budget.py install-hook >/dev/null 2>&1)
grep -q 'ledger co-staging' "$P/.githooks/pre-commit" \
    && pass "install-hook never clobbers a foreign hook in the redirected dir" \
    || fail "install-hook overwrote an existing foreign hook"
rm -rf "$P"

# Presence control: with no core.hooksPath, the default target is unchanged.
P="$(mktemp_project)"
cp "$STARTER/context-budget.json" "$P/.context-budget.json"
cp "$CB" "$P/context_budget.py"
(cd "$P" && python3 context_budget.py install-hook >/dev/null 2>&1)
[ -f "$P/.git/hooks/pre-commit" ] \
    && pass "install-hook falls back to .git/hooks when core.hooksPath is unset" \
    || fail "install-hook did not write the default .git/hooks/pre-commit"
rm -rf "$P"

# --status measures and writes nothing; an argument the tool does not know is refused
# before the tree is read. Both used to run the default measurement, history append
# included. --ignored, because a project may leave the history file untracked or ignore
# it. The default run last is the presence control: this project DOES get written to, so
# an empty status after the others is a non-write rather than a run that stopped early.
# --check is --status under a second name: the same exit code, and no write.
P="$(mktemp_project)"
cp "$STARTER/context-budget.json" "$P/.context-budget.json"
cp "$CB" "$P/context_budget.py"
(cd "$P" && git add -A && git -c user.email=t@t -c user.name=t commit -q -m baseline)
(cd "$P" && python3 context_budget.py --status >/dev/null 2>&1); RC_STATUS=$?
AFTER_STATUS="$(git -C "$P" status --porcelain --ignored)"
(cd "$P" && python3 context_budget.py --check >/dev/null 2>&1); RC_CHECK=$?
AFTER_CHECK="$(git -C "$P" status --porcelain --ignored)"
(cd "$P" && python3 context_budget.py --zzz >/dev/null 2>&1); RC=$?
AFTER_UNKNOWN="$(git -C "$P" status --porcelain --ignored)"
(cd "$P" && python3 context_budget.py >/dev/null 2>&1)
[ -f "$P/.context-budget-history.jsonl" ] && WROTE=1 || WROTE=0
[ -z "$AFTER_STATUS" ] && [ "$WROTE" = "1" ] \
    && pass "context_budget --status writes nothing to the project" \
    || fail "context_budget --status wrote [$AFTER_STATUS] (default run wrote: $WROTE)"
[ -z "$AFTER_CHECK" ] && [ "$RC_CHECK" = "$RC_STATUS" ] && [ "$RC_CHECK" != "3" ] \
    && [ "$WROTE" = "1" ] \
    && pass "context_budget --check is --status: the same exit code, writing nothing" \
    || fail "context_budget --check exited $RC_CHECK (--status $RC_STATUS); left [$AFTER_CHECK]"
[ "$RC" = "3" ] && [ "$AFTER_UNKNOWN" = "$AFTER_STATUS" ] && [ "$WROTE" = "1" ] \
    && pass "context_budget refuses an unknown argument with exit 3, writing nothing" \
    || fail "context_budget --zzz exited $RC; left [$AFTER_UNKNOWN] after [$AFTER_STATUS]"
rm -rf "$P"

# sync must distribute the tool (TRACKED) and seed the config (SEED).
P="$(mktemp_project)"
"$BIN/sync" "$P" --mode=commit --source=local >/dev/null 2>&1
[ -f "$P/context_budget.py" ] && pass "sync distributes context_budget.py" \
    || fail "sync did not distribute context_budget.py"
[ -f "$P/.context-budget.json" ] && pass "sync seeds .context-budget.json" \
    || fail "sync did not seed .context-budget.json"
echo "changed" >> "$P/.context-budget.json"
BEFORE="$(md5 -q "$P/.context-budget.json" 2>/dev/null || md5sum "$P/.context-budget.json" | cut -d" " -f1)"
"$BIN/sync" "$P" --mode=commit --source=local >/dev/null 2>&1
AFTER="$(md5 -q "$P/.context-budget.json" 2>/dev/null || md5sum "$P/.context-budget.json" | cut -d" " -f1)"
[ "$BEFORE" = "$AFTER" ] && pass "re-sync does not clobber an adopter-owned config" \
    || fail "re-sync overwrote the adopter's .context-budget.json"
rm -rf "$P"

echo "== Test: quality_ratchet.py =="
QR="$STARTER/quality_ratchet.py"
[ -x "$QR" ] && pass "quality_ratchet.py is executable" || fail "quality_ratchet.py not executable"
python3 "$QR" --selftest >/dev/null 2>&1 \
    && pass "quality_ratchet --selftest: every gate observed failing and passing" \
    || fail "quality_ratchet --selftest reported a failing gate"
python3 -c "import json,sys; d=json.load(open('$STARTER/quality-gates.json')); sys.exit(0 if d['gates']==[] else 1)" 2>/dev/null \
    && pass "seed .quality-gates.json parses as JSON and starts empty (plan §8.4)" \
    || fail "seed quality-gates.json is invalid or not empty"
grep -q '"--force" in args and' "$QR" && fail "quality_ratchet.py honours --force" \
    || pass "quality_ratchet.py has no --force escape hatch (it refuses the flag by name)"

# The ratchet through a REAL install: sync a scratch adopter tree, declare one gate, install the
# hook, then try to commit a loosened threshold. Refused without --no-verify; passes with it
# (recorded, not exempt); a tightening passes without it. The seed must survive a re-sync.
P="$(mktemp_project)"
git -C "$P" config user.email t@t; git -C "$P" config user.name t
"$BIN/sync" "$P" --mode=commit --source=local >/dev/null 2>&1
[ -f "$P/quality_ratchet.py" ] && pass "sync distributes quality_ratchet.py" \
    || fail "sync did not distribute quality_ratchet.py"
[ -f "$P/.quality-gates.json" ] && pass "sync seeds .quality-gates.json" \
    || fail "sync did not seed .quality-gates.json"
printf '{"version":1,"gates":[{"name":"floor","direction":"min","threshold":80}]}\n' > "$P/.quality-gates.json"
git -C "$P" add -A >/dev/null 2>&1 && git -C "$P" commit -q -m "declare" >/dev/null 2>&1
(cd "$P" && python3 quality_ratchet.py install-hook >/dev/null 2>&1)
printf '{"version":1,"gates":[{"name":"floor","direction":"min","threshold":70}]}\n' > "$P/.quality-gates.json"
git -C "$P" add .quality-gates.json
git -C "$P" commit -q -m "loosen" >/dev/null 2>&1 \
    && fail "a loosened threshold was committed through the installed hook" \
    || pass "a loosened threshold cannot be committed without --no-verify"
git -C "$P" commit -q --no-verify -m "loosen anyway" >/dev/null 2>&1 \
    && pass "--no-verify bypasses the ratchet (recorded in history, not exempt)" \
    || fail "--no-verify did not bypass the ratchet"
printf '{"version":1,"gates":[{"name":"floor","direction":"min","threshold":85}]}\n' > "$P/.quality-gates.json"
git -C "$P" add .quality-gates.json
git -C "$P" commit -q -m "tighten" >/dev/null 2>&1 \
    && pass "a tightened threshold commits without --no-verify" \
    || fail "a tightened threshold was refused"
printf '{"version":1,"gates":[]}\n' > "$P/.quality-gates.json"
git -C "$P" add .quality-gates.json
git -C "$P" commit -q -m "remove" >/dev/null 2>&1 \
    && fail "removing a declared gate was committed through the hook" \
    || pass "removing a declared gate is refused like a loosening"
git -C "$P" checkout -q HEAD -- .quality-gates.json   # index AND worktree: the refused edit was staged
# The deletion hole (PR #82 review, 2a/4): removing the manifest is refused; a bypassed removal
# does not lock the repo; re-adding it lower than the removed version is still a loosening.
git -C "$P" rm -q .quality-gates.json
git -C "$P" commit -q -m "remove the manifest" >/dev/null 2>&1 \
    && fail "removing .quality-gates.json was committed through the installed hook" \
    || pass "removing .quality-gates.json is refused as the loosest loosening"
git -C "$P" commit -q --no-verify -m "remove anyway" >/dev/null 2>&1
echo x > "$P/unrelated.txt"; git -C "$P" add unrelated.txt
git -C "$P" commit -q -m "unrelated" >/dev/null 2>&1 \
    && pass "a repo that removed its manifest with --no-verify is not locked" \
    || fail "every commit after a bypassed removal is refused (the lockout)"
printf '{"version":1,"gates":[{"name":"floor","direction":"min","threshold":10}]}\n' > "$P/.quality-gates.json"
git -C "$P" add .quality-gates.json
git -C "$P" commit -q -m "re-add lower" >/dev/null 2>&1 \
    && fail "re-adding the manifest lower than the removed one was committed" \
    || pass "re-adding the manifest lower than the removed one is refused"
printf '{"version":1,"gates":[{"name":"floor","direction":"min","threshold":85}]}\n' > "$P/.quality-gates.json"
git -C "$P" add .quality-gates.json
git -C "$P" commit -q -m "re-add as it was" >/dev/null 2>&1 \
    && pass "re-adding the manifest at the removed thresholds passes" \
    || fail "re-adding the manifest at the removed thresholds was refused"
BEFORE="$(md5 -q "$P/.quality-gates.json" 2>/dev/null || md5sum "$P/.quality-gates.json" | cut -d" " -f1)"
"$BIN/sync" "$P" --mode=commit --source=local >/dev/null 2>&1
AFTER="$(md5 -q "$P/.quality-gates.json" 2>/dev/null || md5sum "$P/.quality-gates.json" | cut -d" " -f1)"
[ "$BEFORE" = "$AFTER" ] && pass "re-sync does not clobber an adopter-owned gate manifest" \
    || fail "re-sync overwrote the adopter's .quality-gates.json"
rm -rf "$P"

# This repo dogfoods the ratchet: its own manifest must parse with no defects and declare gates,
# and its ledger hook must chain the ratchet. (--run is NOT invoked here — it runs this script.)
python3 - "$METHODOLOGY" <<'PY' >/dev/null 2>&1 && pass "this repo's .quality-gates.json declares gates with no defects" \
    || fail "this repo's .quality-gates.json is missing, empty, or defective"
import importlib.util, json, sys
root = sys.argv[1]
spec = importlib.util.spec_from_file_location("qr", root + "/starter-kit/quality_ratchet.py")
qr = importlib.util.module_from_spec(spec); spec.loader.exec_module(qr)
cfg = json.load(open(root + "/.quality-gates.json"))
sys.exit(0 if cfg["gates"] and not qr.config_defects(cfg) else 1)
PY
grep -q 'quality_ratchet.py" --precommit' "$METHODOLOGY/.githooks/pre-commit" \
    && pass ".githooks/pre-commit chains the quality ratchet before the ledger gate" \
    || fail ".githooks/pre-commit does not run quality_ratchet.py --precommit"

# D9: check-handoff's gate-run citation lint, observed silent / failing / passing.
P="$(mktemp -d)"
cat > "$P/HANDOFFS.md" <<'EOF2'
# Handoff Receipts

```handoff
session: S2
date: 2026-09-15
status: complete
self_score: 8
predecessor_score: 7
active_task: did a thing
what_was_done: did it, commit a1b2c3d
next_steps: run bin/x at src/x.py:10 next
key_files: src/x.py:10
gotchas: none known
runtime_smoke: n/a — docs-only
changelog_ref: PR #1
commit: a1b2c3d
```
EOF2
"$BIN/check-handoff" --file "$P/HANDOFFS.md" >/dev/null 2>&1 \
    && pass "check-handoff: no manifest, no citation demanded" \
    || fail "check-handoff demanded a gate citation with no manifest present"
printf '{"version":1,"gates":[]}\n' > "$P/.quality-gates.json"
"$BIN/check-handoff" --file "$P/HANDOFFS.md" >/dev/null 2>&1 \
    && pass "check-handoff: the empty seed demands no citation" \
    || fail "check-handoff demanded a gate citation for an empty seed"
printf '{"version":1,"gates":[{"name":"t","direction":"max","threshold":0}]}\n' > "$P/.quality-gates.json"
"$BIN/check-handoff" --file "$P/HANDOFFS.md" >/dev/null 2>&1 \
    && fail "check-handoff passed a complete receipt that cites no gate run while a gate is declared" \
    || pass "check-handoff: a declared gate with no citation in the newest receipt is a finding"
"$BIN/check-handoff" --all --file "$P/HANDOFFS.md" >/dev/null 2>&1 \
    && fail "check-handoff --all missed the uncited gate run" \
    || pass "check-handoff --all: the same finding, on the newest receipt only"
sed -i.bak 's|runtime_smoke: n/a — docs-only|runtime_smoke: quality_ratchet: 1/1 pass · 0 fail · 0 unmeasured · results abc123def456 · manifest 0123456789ab|' "$P/HANDOFFS.md"
"$BIN/check-handoff" --file "$P/HANDOFFS.md" >/dev/null 2>&1 \
    && pass "check-handoff: a cited gate run satisfies the lint" \
    || fail "check-handoff rejected a receipt that cites its gate run"
rm -rf "$P"

echo "== Test 26: status and sync recognise a version a merge hid from the default walk (RED-first) =="
# Git's default history walk follows only a merge's TREESAME parent, so a version on the side a merge
# did not keep is never visited: bin/status read it as "locally modified" and bin/sync refused it.
# The fixture is a methodology repo with both shapes, on one tracked file:
#   B: main's own v2, then a merge that takes a side branch's v3a -> v3, hiding v2;
#   A: a side branch's v4side, then a merge that keeps main's v5, hiding v4side.
# Dates are fixed, because the full walk orders by commit date and ties would make it unstable.
# N counts the versions that landed on the checkout's first-parent line, so v1 is 3
# behind (v2, v3, v5), not 5 (every distinct version) or 7 (its position in the full walk).
F=starter-kit/SAFEGUARDS.md
D=SAFEGUARDS.md
T0=1700000000
mh_git() {  # mh_git <seconds after T0> <git args...>
    local t=$((T0 + $1)); shift
    GIT_AUTHOR_DATE="@$t +0000" GIT_COMMITTER_DATE="@$t +0000" \
        git -C "$M" -c user.email=t@t -c user.name=t -c commit.gpgsign=false "$@"
}
mh_fixture() {  # build the fixture in a fresh $M; Test 27 serves the same repo as its source
    M="$(mktemp -d)"
    git -C "$M" init -q -b main
    mkdir -p "$M/bin"
    cp "$BIN/sync" "$BIN/status" "$BIN/_manifest.py" "$M/bin/"
    python3 -c "import sys; sys.path.insert(0, '$BIN'); import _manifest; print('\n'.join(s for s, _d, _x in _manifest.DISTRIBUTION))" \
        | while read -r src; do mkdir -p "$M/$(dirname "$src")"; cp "$METHODOLOGY/$src" "$M/$src"; done
    printf 'v1\n' > "$M/$F"; git -C "$M" add -A; mh_git 1 commit -qm c1
    git -C "$M" checkout -qb side1
    printf 'v3a\n' > "$M/$F"; mh_git 3 commit -qam s1
    printf 'v3\n' > "$M/$F"; mh_git 4 commit -qam s2
    git -C "$M" checkout -q main
    printf 'v2\n' > "$M/$F"; mh_git 2 commit -qam c2
    mh_git 5 merge -q -X theirs side1 -m mB >/dev/null
    git -C "$M" checkout -qb side2
    printf 'v4side\n' > "$M/$F"; mh_git 6 commit -qam t1
    git -C "$M" checkout -q main
    printf 'v5\n' > "$M/$F"; mh_git 7 commit -qam c3
    mh_git 8 merge -q -s ours side2 -m mA >/dev/null
}
mh_fixture
# Prove the fixture before trusting it: v5 is canonical, and the default walk misses exactly c2 and t1.
N_DEFAULT="$(git -C "$M" log --format=%H -- "$F" | wc -l | tr -d ' ')"
N_FULL="$(git -C "$M" log --full-history --format=%H -- "$F" | wc -l | tr -d ' ')"
N_FP="$(git -C "$M" log --first-parent --format=%H -- "$F" | wc -l | tr -d ' ')"
[ "$(cat "$M/$F")" = "v5" ] && pass "fixture: canonical is v5 after both merges" || fail "fixture: canonical is '$(cat "$M/$F")', not v5"
[ "$N_DEFAULT/$N_FULL/$N_FP" = "4/8/4" ] \
    && pass "fixture: the walks visit 4 (default) / 8 (full history) / 4 (first parent) commits" \
    || fail "fixture: the walks visit $N_DEFAULT/$N_FULL/$N_FP commits, not 4/8/4 -- the merges lack the hiding shape"
P="$(mktemp_project)"
"$M/bin/sync" "$P" --mode=commit --source=local >/dev/null
mh_status() {
    "$M/bin/status" --source=local "$P" \
        | awk -v d="$D" '$2 == d { $1 = $2 = $3 = ""; sub(/^ +/, ""); sub(/ +$/, ""); print }'
}
mh_expect() {  # mh_expect <content> <expected status> <what>
    printf '%s\n' "$1" > "$P/$D"
    local got; got="$(mh_status)"
    [ "$got" = "$2" ] && pass "status: $1 ($3) reads '$2'" || fail "status: $1 ($3) reads '$got', not '$2'"
}
mh_expect v5 "current" "canonical"
mh_expect v2 "2 versions behind" "main's own version, hidden by merge B"
mh_expect v4side "1 version behind" "a side version merge A discarded; no main-line position, so the full walk counts"
mh_expect v3 "1 version behind" "landed by merge B; the side branch's two commits are one main-line version"
mh_expect v1 "3 versions behind" "the root; merged branches' own commits are not main-line versions"
mh_expect v2-local "locally modified" "never in history"
mh_sync() {  # mh_sync <content> <expected rc> <expected content after> <what>
    printf '%s\n' "$1" > "$P/$D"
    "$M/bin/sync" "$P" --source=local >/dev/null 2>&1; local rc=$?
    local after; after="$(cat "$P/$D")"
    [ "$rc/$after" = "$2/$3" ] && pass "sync: $1 ($4) exits $2 and leaves $3" \
        || fail "sync: $1 ($4) exits $rc and leaves $after, not $2 and $3"
}
mh_sync v2 0 v5 "hidden by merge B, upgraded without --force"
mh_sync v4side 0 v5 "hidden by merge A, upgraded without --force"
mh_sync v2-local 2 v2-local "a real local edit is still refused"
rm -rf "$M" "$P"

echo "== Test 27: --source=github clones its source, so it recognises every version Test 26 does (RED-first) =="
# --source=github read each file's contents alone, through the GitHub API, and classified the project's copy
# against an EMPTY history, so a file that was merely behind read "locally modified" and sync refused it:
# the one case an update exists for. It now clones the source into a temporary directory and runs the
# --source=local code over that clone. METHODOLOGY_SOURCE_URL points it at a bare clone of Test 26's
# fixture, so this test needs neither the network nor gh; TMPDIR is fresh so the clone's removal can be seen.
# The URL is file://, not a bare path: git clones a plain path by copying the repository and ignores
# --depth, so a shallow clone -- which would lose the history this route exists for -- would pass unseen.
mh_fixture
S="$(mktemp -d)/methodology.git"
git clone -q --bare "$M" "$S"
U="file://$S"
SHORT="$(git -C "$S" rev-parse --short=7 HEAD)"
TMPD="$(mktemp -d)"
P="$(mktemp_project)"
"$M/bin/sync" "$P" --mode=commit --source=local >/dev/null
gs_status() {
    TMPDIR="$TMPD" METHODOLOGY_SOURCE_URL="$U" "$BIN/status" --source=github "$P" 2>&1 \
        | awk -v d="$D" '$2 == d { $1 = $2 = $3 = ""; sub(/^ +/, ""); sub(/ +$/, ""); print }'
}
gs_expect() {  # gs_expect <content> <expected status> <what>
    printf '%s\n' "$1" > "$P/$D"
    local got; got="$(gs_status)"
    [ "$got" = "$2" ] && pass "github status: $1 ($3) reads '$2'" || fail "github status: $1 ($3) reads '$got', not '$2'"
}
gs_expect v5 "current" "canonical"
gs_expect v2 "2 versions behind" "hidden by merge B"
gs_expect v4side "1 version behind" "discarded by merge A; counted along the full walk"
gs_expect v3 "1 version behind" "landed by merge B"
gs_expect v1 "3 versions behind" "the root"
gs_expect v2-local "locally modified" "never in history"
gs_sync() {  # gs_sync <content> <expected rc> <expected content after> <what>
    printf '%s\n' "$1" > "$P/$D"
    TMPDIR="$TMPD" METHODOLOGY_SOURCE_URL="$U" "$BIN/sync" "$P" --source=github >/dev/null 2>&1; local rc=$?
    local after; after="$(cat "$P/$D")"
    [ "$rc/$after" = "$2/$3" ] && pass "github sync: $1 ($4) exits $2 and leaves $3" \
        || fail "github sync: $1 ($4) exits $rc and leaves $after, not $2 and $3"
}
gs_sync v2 0 v5 "hidden by merge B, upgraded without --force"
gs_sync v4side 0 v5 "hidden by merge A, upgraded without --force"
gs_sync v3 0 v5 "landed by merge B, upgraded"
gs_sync v1 0 v5 "the root, upgraded"
gs_sync v2-local 2 v2-local "a real local edit is still refused"
printf 'v2\n' > "$P/$D"
OUT="$(TMPDIR="$TMPD" METHODOLOGY_SOURCE_URL="$U" "$BIN/sync" "$P" --source=github --dry-run 2>&1)"; RC=$?
[ "$RC" = "0" ] && pass "github sync --dry-run: exit 0 on a file that is merely behind" || fail "github sync --dry-run: exit $RC"
printf '%s\n' "$OUT" | grep -qxF "  source:  github ($U)" \
    && pass "github sync names the URL it cloned" || fail "github sync's source line does not name $U"
printf '%s\n' "$OUT" | grep -q "^  version: .*$SHORT" && ! printf '%s\n' "$OUT" | grep -q '^  version: github:' \
    && pass "github sync reports the clone's own version ($SHORT)" || fail "github sync's version line is not the clone's"
[ "$(cat "$P/$D")" = "v2" ] && pass "github sync --dry-run wrote nothing" || fail "github sync --dry-run wrote $P/$D"
[ -z "$(ls -A "$TMPD")" ] && pass "every run removed its temporary clone" || fail "a temporary clone was left in $TMPD: $(ls -A "$TMPD")"
rm -rf "$M" "$(dirname "$S")" "$TMPD" "$P"

echo "== Test 28: --source=github names every distributed file its source lacks, before writing anything (RED-first) =="
# A source behind this checkout's manifest -- a file added here and not merged there -- is a version
# statement about the source, not a local fault: say so, list every missing file, and write nothing.
mh_fixture
GONE=starter-kit/RECOMMENDED_SKILLS.md
git -C "$M" rm -q "$GONE"; mh_git 9 commit -qm "drop one distributed file"
S="$(mktemp -d)/methodology.git"
git clone -q --bare "$M" "$S"
U="file://$S"
P="$(mktemp_project)"
OUT="$(METHODOLOGY_SOURCE_URL="$U" "$BIN/sync" "$P" --source=github 2>&1)"; RC=$?
[ "$RC" = "1" ] && pass "github sync: a source missing a distributed file exits 1" || fail "github sync: exit $RC, not 1"
printf '%s\n' "$OUT" | grep -qxF "    $GONE" && printf '%s\n' "$OUT" | grep -q "1 of [0-9]* distributed file(s) do not exist in $U" \
    && pass "github sync: the inventory names the missing file and its source" || fail "github sync: no inventory naming $GONE -- got: $OUT"
[ -z "$(ls -A "$P" | grep -vx .git)" ] && pass "github sync: nothing written before the inventory" \
    || fail "github sync wrote into the project before refusing: $(ls -A "$P" | tr '\n' ' ')"
OUT="$(METHODOLOGY_SOURCE_URL="$U" "$BIN/status" --source=github "$P" 2>&1)"; RC=$?
[ "$RC" = "1" ] && printf '%s\n' "$OUT" | grep -qxF "    $GONE" \
    && pass "github status: the same inventory, exit 1" || fail "github status: exit $RC, output: $OUT"
rm -rf "$M" "$(dirname "$S")" "$P"

echo "== Test 29: a source without its history is named as the cause, not the project's files (RED-first) =="
# A file that matches no version in the source's history is a local edit only if that history is all
# there. A shallow clone holds its last commits and a downloaded tree holds none, so an unmodified older
# copy was refused as "local modifications". The refusal now says what the source lacks. v1 is the
# fixture's root version, merely behind: a full-history source upgrades it (the control, last).
mh_fixture
P="$(mktemp_project)"
"$M/bin/sync" "$P" --mode=commit --source=local >/dev/null
printf 'v1\n' > "$P/$D"
H="$(cd "$(mktemp -d)" && pwd -P)"  # resolved, as bin/sync prints its own root (/var is /private/var on macOS)
git clone -q --depth 1 "file://$M" "$H/shallow"  # file://, or git copies the repository and ignores --depth
mkdir "$H/tarball"; git -C "$M" archive HEAD | tar -x -C "$H/tarball"
[ "$(git -C "$H/shallow" rev-parse --is-shallow-repository)" = "true" ] && [ ! -e "$H/tarball/.git" ] \
    && cmp -s "$H/shallow/bin/sync" "$BIN/sync" && cmp -s "$H/tarball/bin/sync" "$BIN/sync" \
    && pass "fixture: a shallow clone and a tree with no .git, each carrying the sync under test" \
    || fail "fixture: the clone is not shallow, the tree has a .git, or a copy of bin/sync differs"
hs_refuse() {  # hs_refuse <source tree> <sentence naming the cause> <what>
    local out rc
    out="$("$1/bin/sync" "$P" --source=local 2>&1)"; rc=$?
    [ "$rc" = "2" ] && pass "$3: exit 2" || fail "$3: exit $rc, not 2"
    grep -qF "$2" <<<"$out" && pass "$3: the refusal says '$2'" || fail "$3: no '$2' in the refusal: $out"
    ! grep -q "local modifications" <<<"$out" && pass "$3: no claim of local modifications" \
        || fail "$3: the refusal still blames local modifications"
    [ "$(cat "$P/$D")" = "v1" ] && pass "$3: nothing written" || fail "$3: $P/$D was rewritten"
}
hs_refuse "$H/shallow" "is shallow (1 commit)" "shallow source"
git clone -q --depth 2 "file://$M" "$H/shallow2"  # depth 2 reaches both of the merge's parents
N2="$(git -C "$H/shallow2" rev-list --count HEAD)"
hs_refuse "$H/shallow2" "is shallow ($N2 commits)" "a deeper shallow source"
hs_refuse "$H/tarball" "has no git history" "source with no .git"
OUT="$("$H/shallow/bin/sync" "$P" --source=local 2>&1)"
grep -qF "git -C $H/shallow fetch --unshallow" <<<"$OUT" \
    && pass "shallow source: the refusal gives the command that deepens it" || fail "shallow source: no fetch --unshallow command for $H/shallow"
OUT="$("$H/tarball/bin/sync" "$P" --source=local 2>&1)"
grep -qxF "    git clone ${METHODOLOGY_SOURCE_URL:-https://github.com/KJ5HST/methodology.git}" <<<"$OUT" \
    && pass "source with no .git: the refusal gives the clone command" || fail "source with no .git: no clone command in the refusal"
# --source=github: its clone is gone when the run ends, so the hint must work without it. Run the hint
# as printed, from an empty directory: diff exits 1 only if both files exist and differ (2 = missing).
git clone -q --bare "$M" "$H/methodology.git"
printf 'v2-local\n' > "$P/$D"
OUT="$(METHODOLOGY_SOURCE_URL="file://$H/methodology.git" "$BIN/sync" "$P" --source=github 2>&1)"
HINT="$(grep -A3 "To inspect the drift first" <<<"$OUT")"
mkdir "$H/inspect"
( cd "$H/inspect" && eval "$(grep '^    git clone ' <<<"$HINT")" ) >/dev/null 2>&1; RC_CLONE=$?
( cd "$H/inspect" && eval "$(grep '^    diff ' <<<"$HINT")" ) >/dev/null 2>&1; RC_DIFF=$?
grep -qF "git clone file://$H/methodology.git " <<<"$HINT" && [ "$RC_CLONE/$RC_DIFF" = "0/1" ] \
    && pass "github refusal: the inspect hint, run after the run, clones the source and diffs the edit" \
    || fail "github refusal: the inspect hint does not work once the run is over (clone $RC_CLONE, diff $RC_DIFF): $HINT"
printf 'v1\n' > "$P/$D"
"$M/bin/sync" "$P" --source=local >/dev/null 2>&1 && [ "$(cat "$P/$D")" = "v5" ] \
    && pass "control: the full-history source upgrades the same file" || fail "control: the full-history source did not upgrade v1"
rm -rf "$M" "$H" "$P"

echo "== Test 30: the .gitattributes seed merges CHANGELOG.md by union and keeps HANDOFFS.md visible (RED-first) =="
# Two sessions prepend at one anchor from one base -- the S21 conflict. Under the seed, CHANGELOG.md merges
# clean with both entries whole. HANDOFFS.md is deliberately NOT under union: union fuses two prepended
# receipts into one block at exit 0 (the RED control shows it), so it conflicts visibly and the seed's
# keep-both recipe resolves it with every receipt whole (parallel-sessions plan §8A, row 3').
l30_entry() { printf '### 2026-10-0%s · [ad hoc] entry %s\n\n- body of entry %s\n\n' "$1" "$2" "$2"; }
l30_rcpt() { # $1 session, $2 self_score, $3 predecessor_score
    printf '```handoff\nsession: %s\ndate: 2026-10-01\nstatus: complete\nself_score: %s\npredecessor_score: %s\nactive_task: the task of %s\nwhat_was_done: did it (abc1234)\nnext_steps: the next thing after %s\nkey_files: a.py:%s\ngotchas: none for %s\nruntime_smoke: n/a — docs-only\nchangelog_ref: abc1234\ncommit: abc1234\n```\n\n' \
        "$1" "$2" "$3" "$1" "$1" "$2" "$1"
}
l30_repo() { # a repo with the seed, a one-entry ledger and a one-receipt HANDOFFS.md, committed
    local u; u="$(mktemp -d)"
    git -C "$u" init -q -b main; git -C "$u" config user.email t@t; git -C "$u" config user.name t
    git -C "$u" config core.hooksPath /dev/null
    cp "$STARTER/gitattributes" "$u/.gitattributes"
    { printf '# Changelog\n\n---\n\n'; l30_entry 1 base; } > "$u/CHANGELOG.md"
    { printf '# Handoff Receipts\n\n---\n\n'; l30_rcpt S1 7 6; } > "$u/HANDOFFS.md"
    git -C "$u" add -A; git -C "$u" commit -qm base
    for side in alpha beta; do
        local n=2 s=8; [ "$side" = beta ] && n=3 s=9
        git -C "$u" checkout -q -b "$side" main
        { printf '# Changelog\n\n---\n\n'; l30_entry "$n" "$side"; l30_entry 1 base; } > "$u/CHANGELOG.md"
        { printf '# Handoff Receipts\n\n---\n\n'; l30_rcpt "S2-$side" "$s" 7; l30_rcpt S1 7 6; } > "$u/HANDOFFS.md"
        git -C "$u" commit -qam "$side"
    done
    git -C "$u" checkout -q alpha
    echo "$u"
}
U="$(l30_repo)"
git -C "$U" merge -q --no-edit beta >/dev/null 2>&1; RC=$?
CONFL="$(git -C "$U" diff --name-only --diff-filter=U | tr '\n' ' ')"
[ "$RC" = 1 ] && [ "$CONFL" = "HANDOFFS.md " ] \
    && pass "seed: a two-branch merge conflicts in HANDOFFS.md only" || fail "seed: merge exit $RC, conflicted: [$CONFL]"
[ "$(grep -c '^### ' "$U/CHANGELOG.md")" = 3 ] && grep -q 'entry alpha' "$U/CHANGELOG.md" && grep -q 'entry beta' "$U/CHANGELOG.md" \
    && ! grep -q '^<<<<<<<' "$U/CHANGELOG.md" \
    && pass "seed: CHANGELOG.md auto-merged by union, both new entries whole" || fail "seed: CHANGELOG.md did not keep both entries"
( cd "$U" && git show :1:HANDOFFS.md > base.tmp && git show :2:HANDOFFS.md > ours.tmp && git show :3:HANDOFFS.md > theirs.tmp \
    && git merge-file -p --union --diff3 ours.tmp base.tmp theirs.tmp > HANDOFFS.md; rm -f base.tmp ours.tmp theirs.tmp )
"$BIN/check-handoff" --all --file "$U/HANDOFFS.md" >/dev/null 2>&1 && [ "$(grep -c '^session:' "$U/HANDOFFS.md")" = 3 ] \
    && [ "$(grep -c '^```handoff' "$U/HANDOFFS.md")" = 3 ] \
    && pass "seed recipe: keep-both resolves HANDOFFS.md with all three receipts whole (check-handoff --all)" \
    || fail "seed recipe: HANDOFFS.md not resolved into three whole receipts"
rm -rf "$U"
U="$(l30_repo)"
printf 'HANDOFFS.md merge=union\n' >> "$U/.git/info/attributes"
git -C "$U" merge -q --no-edit beta >/dev/null 2>&1; RC=$?
[ "$RC" = 0 ] && [ "$(grep -c '^```handoff' "$U/HANDOFFS.md")" = 2 ] && [ "$(grep -c '^session:' "$U/HANDOFFS.md")" = 3 ] \
    && pass "RED control: HANDOFFS.md under union merges at exit 0 into ONE block holding two receipts" \
    || fail "RED control: union on HANDOFFS.md did not fuse (exit $RC) -- re-measure before keeping the exclusion"
# ...and the checker the recipe relies on must see it: parse_block once kept the last of a repeated key,
# so the fused block passed check-handoff --all as one clean receipt (found in S30; RED before the fix).
OUT="$("$BIN/check-handoff" --all --file "$U/HANDOFFS.md" 2>&1)"; RC=$?
[ "$RC" = 1 ] && grep -q 'appears more than once in one block' <<<"$OUT" \
    && pass "check-handoff --all rejects the fused block (a key repeated in one block)" \
    || fail "check-handoff --all accepted two receipts fused into one block"
rm -rf "$U"
# A trim on one branch against a new entry on the other, the real trimmer at a small cut: nothing archived returns.
U="$(mktemp -d)"
git -C "$U" init -q -b main; git -C "$U" config user.email t@t; git -C "$U" config user.name t
git -C "$U" config core.hooksPath /dev/null
cp "$STARTER/gitattributes" "$U/.gitattributes"
{ printf '# Changelog\n\nfront matter\n\n---\n\n'; for d in 9 8 7 6 5 4 3 2 1; do l30_entry "$d" "$d"; done; } > "$U/CHANGELOG.md"
git -C "$U" add -A; git -C "$U" commit -qm base
git -C "$U" checkout -q -b trim
( cd "$U" && python3 "$STARTER/methodology_trim.py" --file CHANGELOG.md --cut 2 --budget-bytes 100 --write ) >/dev/null 2>&1
git -C "$U" add -A; git -C "$U" commit -qm trim >/dev/null 2>&1
git -C "$U" checkout -q -b new main
python3 -c "import sys; p=sys.argv[1]; s=open(p).read(); a='---\n\n'; open(p,'w').write(s.replace(a, a+'### 2026-10-10 · [ad hoc] entry new\n\n- body of entry new\n\n', 1))" "$U/CHANGELOG.md"
git -C "$U" commit -qam new
git -C "$U" checkout -q trim
git -C "$U" merge -q --no-edit new >/dev/null 2>&1; RC=$?
[ "$RC" = 0 ] && grep -q 'body of entry new' "$U/CHANGELOG.md" && ! grep -q 'body of entry 3$' "$U/CHANGELOG.md" \
    && [ -f "$U"/docs/archive/CHANGELOG-through-*.md ] \
    && pass "trim vs prepend under union: clean merge, the new entry kept, no archived record back in the live file" \
    || fail "trim vs prepend under union: exit $RC, or an archived record returned"
rm -rf "$U"
P="$(mktemp_project)"
"$BIN/sync" "$P" --source=local >/dev/null 2>&1
cmp -s "$P/.gitattributes" "$STARTER/gitattributes" && pass "sync installs the .gitattributes seed" || fail "sync did not install .gitattributes"
printf 'mine\n' > "$P/.gitattributes"
"$BIN/sync" "$P" --source=local --force >/dev/null 2>&1
[ "$(cat "$P/.gitattributes")" = mine ] && pass "sync never overwrites an adopter's .gitattributes, even with --force" \
    || fail "sync clobbered an adopter's .gitattributes"
rm -rf "$P"

echo "== Test 31: check-ledger reads what a union merge leaves behind (RED-first against fixtures) =="
# union never asks, so a CHANGELOG.md merge that went wrong is caught only by a checker that reads the result.
L="$(mktemp -d)"
l31() { # $1 label, $2 wanted exit, $3 ledger body (printf format) after the front matter
    printf "# Changelog\n\nfront matter\n\n---\n\n$3" > "$L/CHANGELOG.md"
    "$BIN/check-ledger" --file "$L/CHANGELOG.md" >/dev/null 2>&1; local got=$?
    [ "$got" = "$2" ] && pass "check-ledger: $1" || fail "check-ledger: $1 (exit $got, wanted $2)"
}
E2='### 2026-10-02 · [ad hoc] two\n\n- body two\n\n'
E1='### 2026-10-01 · [issue #7] one\n\n- body one\n'
l31 "a clean ledger passes"                                  0 "## 2026-10\n\n$E2$E1"
l31 "a heading directly under the last body (union's lost blank line) passes" 0 "### 2026-10-02 · [ad hoc] two\n\n- body two\n$E1"
l31 "dates out of order across a merge pass (not checked)"   0 "$E1\n$E2"
l31 "a tag quoted in inline code is not a second tag"        0 "### 2026-10-03 · [BL-9] adopt \`[BL-<id>]\` here\n\n- b\n\n$E1"
l31 "a footer after a closing --- rule passes"               0 "$E2$E1\n---\n\nfooter text\n"
l31 "the sentinel mentioned in prose is not the sentinel"    0 "$E2- not the METHODOLOGY-SEED-SENTINEL line\n\n$E1"
l31 "a duplicated entry heading fails"                       1 "$E2$E2$E1"
l31 "a heading with no source tag fails"                     1 "### 2026-10-02 · two\n\n- b\n\n$E1"
l31 "a heading with two source tags fails"                   1 "### 2026-10-02 · [ad hoc] [issue #3] two\n\n- b\n\n$E1"
l31 "a heading without the date prefix fails"                1 "### two [ad hoc]\n\n- b\n\n$E1"
l31 "orphaned text under a month heading fails"              1 "## 2026-10\n\nstray line\n\n$E2$E1"
l31 "a surviving conflict marker fails"                      1 "<<<<<<< HEAD\n$E2=======\n$E1>>>>>>> beta\n"
l31 "the seed sentinel left in a ledger with entries fails"  1 "<!-- METHODOLOGY-SEED-SENTINEL: fresh ledger -->\n\n$E2$E1"
rm -rf "$L"
"$BIN/check-ledger" --all >/dev/null 2>&1 && pass "check-ledger --all: this repository's ledger and its archive shard are clean" \
    || fail "check-ledger --all: this repository's own ledger has findings"

echo ""
echo "== Summary: $PASS passed, $FAIL failed =="
[ "$FAIL" = "0" ]
