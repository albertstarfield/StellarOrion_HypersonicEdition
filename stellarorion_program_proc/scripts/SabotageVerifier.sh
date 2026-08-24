#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
#  SabotageVerifier.sh — pre-build sabotage audit gate (Tier B1)
# ═══════════════════════════════════════════════════════════════════════════
#  Wraps src/utils/sabotage_verifier.py (already adapted from Zephy per the
#  root-level "ADAPT THIS" source) into the build pipeline as a PRE-AUDIT
#  gate per code-quality standard ("SabotageVerifier pre-audit").
#
#  Gate semantics (verifier's own contract):
#    - CRITICAL violations  -> exit 1 (gate BLOCKED)
#    - HIGH/MEDIUM findings -> reported; known-acceptable categories are
#      documented in docs/AUDIT_BASELINE.md (spec-contract FP + sidecar C1)
#    - LOW informational    -> reported, never blocking
#
#  Usage:
#    scripts/SabotageVerifier.sh              # audit all targets
#    scripts/SabotageVerifier.sh --quiet      # verdict line only
# ═══════════════════════════════════════════════════════════════════════════
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJ_DIR="$(dirname "$SCRIPT_DIR")"
VERIFIER="$PROJ_DIR/src/utils/sabotage_verifier.py"
REPORT_DIR="${SABOTAGE_REPORT_DIR:-$PROJ_DIR/data/audits}"
QUIET=0
[ "${1:-}" = "--quiet" ] && QUIET=1

log() { [ "$QUIET" -eq 0 ] && echo "$@" || true; }

# --- Murphy's Law: fail fast with clear diagnostics -----------------------
if ! command -v python3 >/dev/null 2>&1; then
    echo "GATE ERROR: python3 not found on PATH" >&2
    exit 2
fi
if [ ! -f "$VERIFIER" ]; then
    echo "GATE ERROR: verifier missing: $VERIFIER" >&2
    exit 2
fi

mkdir -p "$REPORT_DIR" 2>/dev/null || {
    echo "GATE ERROR: cannot create report dir $REPORT_DIR" >&2
    exit 2
}

STAMP="$(date +%Y%m%d_%H%M%S)"
OUT_JSON="$REPORT_DIR/sabotage_$STAMP.json"
OUT_TXT="$REPORT_DIR/sabotage_$STAMP.txt"

# --- Audit targets ---------------------------------------------------------
# Ada engine sources + Python sidecar + UI. Verifier itself excluded (it is
# the auditor, not auditee; self-scan produces recursive-noise FPs).
TARGETS=(
    "src/simulation_engine|.ads,.adb"
    "src/python|.py"
    "src/ui|.py"
)

TOTAL_CRITICAL=0
TOTAL_HIGH=0
TOTAL_MEDIUM=0
TOTAL_LOW=0

for entry in "${TARGETS[@]}"; do
    DIR="${entry%%|*}"
    EXTS="${entry##*|}"
    if [ ! -d "$PROJ_DIR/$DIR" ]; then
        log "WARN: target dir missing, skipped: $DIR"
        continue
    fi
    log "── Auditing $DIR ($EXTS) ──────────────────────────────"
    # --exclude-files guards against the verifier auditing itself when the
    # whole-tree patterns reach into src/utils via cross-file checks.
    if ! python3 "$VERIFIER" "$PROJ_DIR/$DIR" \
            --extensions "$EXTS" \
            --exclude-files sabotage_verifier.py \
            --json > "$OUT_JSON.tmp" 2>"$OUT_TXT.err"; then
        # Non-zero exit == CRITICAL found (verifier contract).
        TOTAL_CRITICAL=$((TOTAL_CRITICAL + 1))
    fi
    python3 - "$OUT_JSON.tmp" <<'PYEOF' >> "$OUT_TXT"
import json, sys, collections
try:
    vs = json.load(open(sys.argv[1]))
except Exception as e:
    print(f"REPORT ERROR: unreadable audit JSON ({e})", file=sys.stderr)
    sys.exit(0)
c = collections.Counter(v.get("severity", "?") for v in vs)
print(f"  CRITICAL={c.get('CRITICAL',0)} HIGH={c.get('HIGH',0)} "
      f"MEDIUM={c.get('MEDIUM',0)} LOW={c.get('LOW',0)}")
PYEOF
    # Aggregate counts from the same JSON.
    COUNTS="$(python3 -c "
import json,sys,collections
try:
    vs=json.load(open('$OUT_JSON.tmp'))
    c=collections.Counter(v.get('severity','?') for v in vs)
    print(c.get('CRITICAL',0), c.get('HIGH',0), c.get('MEDIUM',0), c.get('LOW',0))
except Exception:
    print('1 0 0 0')
")"
    TOTAL_CRITICAL=$((TOTAL_CRITICAL + $(echo "$COUNTS" | cut -d' ' -f1)))
    TOTAL_HIGH=$((TOTAL_HIGH + $(echo "$COUNTS" | cut -d' ' -f2)))
    TOTAL_MEDIUM=$((TOTAL_MEDIUM + $(echo "$COUNTS" | cut -d' ' -f3)))
    TOTAL_LOW=$((TOTAL_LOW + $(echo "$COUNTS" | cut -d' ' -f4)))
    cat "$OUT_JSON.tmp" >> "$OUT_JSON"
done

rm -f "$OUT_JSON.tmp" "$OUT_TXT.err"

# --- Verdict ----------------------------------------------------------------
echo "═══════════════════════════════════════════════════════════════════"
echo " SABOTAGE AUDIT GATE — CRITICAL=$TOTAL_CRITICAL HIGH=$TOTAL_HIGH MEDIUM=$TOTAL_MEDIUM LOW=$TOTAL_LOW"
if [ "$TOTAL_CRITICAL" -eq 0 ]; then
    echo " VERDICT: CLEAN — gate PASSED (no critical violations)"
    echo " Reports: $OUT_JSON"
    echo "═══════════════════════════════════════════════════════════════════"
    exit 0
else
    echo " VERDICT: CONTAMINATED — gate BLOCKED ($TOTAL_CRITICAL critical)"
    echo " Reports: $OUT_JSON / $OUT_TXT"
    echo "═══════════════════════════════════════════════════════════════════"
    exit 1
fi
