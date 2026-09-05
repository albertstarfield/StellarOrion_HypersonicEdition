#!/bin/bash
# prove.sh -- gnatprove wrapper working around GCC 16.x -gnatR2js duplicate-location bug.
#
# ROOT CAUSE (see ledger CONTINUITY + /tmp/spark-src/src/why/gnat2why-data_decomposition.adb):
#   gnat2why keys data-representation entries by LOCATION only and raises
#   Program_Error "inconsistent data representation duplicate" when one source
#   declaration site emits multiple compiler itypes (base/subtype/packed
#   variants) with differing payloads. The catch-all handler misreports this
#   as "ill-formed JSON ... install more recent GNAT".
#
# WORKAROUND: pre-generate phase-1 rep-info JSONs exactly as gnatprove does,
# drop keep-first-per-location duplicates (semantically identical to the
# reader's Insert-if-absent behavior), then run gnatprove -- its gprbuild
# staleness check skips regeneration and consumes the sanitized files.
#
# Usage: scripts/prove.sh [LEVEL] [extra gnatprove args...]
#   e.g.: scripts/prove.sh 0 --report=all
#         scripts/prove.sh 4 -u stellarorion_geometry.adb
set -euo pipefail

LEVEL="${1:-4}"; shift || true
PROJ_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJ_DIR"

export PATH="$HOME/.alire/libexec/spark/bin:$HOME/.alire/bin:$PATH"

echo "== [1/3] regenerating data-representation info =="
# Retry rm -rf in case prior gprbuild holds open FDs on macOS
rm -rf obj/gnatprove 2>/dev/null || {
    sleep 2
    rm -rf obj/gnatprove 2>/dev/null || true
}
# Ensure obj/gnatprove does not exist before rebuilding
test ! -d obj/gnatprove || rm -rf obj/gnatprove || true
gprbuild --subdirs=gnatprove/data_representation --no-object-check \
         --restricted-to-languages=ada --target=aarch64-darwin -s -v -j10 -c \
         -cargs:Ada -S -gnatR2js -gnatws -gnatx -gnatis > /dev/null

echo "== [2/3] deduplicating rep-info JSONs (keep-first per location) =="
python3 - <<'EOF'
import json, glob
dropped = 0
for f in glob.glob('obj/gnatprove/data_representation/*.json'):
    d = json.load(open(f)); seen = set(); out = []
    for e in d:
        loc = e.get('location')
        if loc in seen:
            dropped += 1; continue
        seen.add(loc); out.append(e)
    open(f, 'w').write(json.dumps(out, indent=2))
print(f"dropped {dropped} duplicate-location entries")
EOF

echo "== [3/3] gnatprove ${LEVEL:+--level=$LEVEL }$* =="
if [ "$LEVEL" = "skip" ]; then
   #  LEVEL=skip: caller supplies its own effort flags (e.g. --timeout=90),
   #  since --level is mutually exclusive with --timeout/--steps.
   gnatprove -j0 "$@"
else
   gnatprove --level="$LEVEL" -j0 "$@"
fi
