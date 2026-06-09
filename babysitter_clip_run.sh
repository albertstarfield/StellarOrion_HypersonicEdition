#!/usr/bin/env bash
# =============================================================================
# StellarOrion Second Run Babysitter (clip fix)
# Uses 'clip' instead of 'invert' in read_surf for correct axisymmetric BCs
# Usage: bash babysitter_clip_run.sh
# =============================================================================
set -e

WORKDIR="/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition"
VENV="$WORKDIR/.venv_gui/bin/python"
LOG="$WORKDIR/clip_run.log"
LOCK="$WORKDIR/.babysitter2.lock"

cd "$WORKDIR"

echo "=============================================" | tee -a "$LOG"
echo " StellarOrion Clip-Fix Run Started" | tee -a "$LOG"
echo " $(date)" | tee -a "$LOG"
echo " Fix: read_surf ... clip (correct axisymmetric axis handling)" | tee -a "$LOG"
echo "=============================================" | tee -a "$LOG"

# Prevent duplicate runs
if [ -f "$LOCK" ]; then
    OLD_PID=$(cat "$LOCK")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "[WARN] Babysitter already running (PID $OLD_PID). Exiting." | tee -a "$LOG"
        exit 1
    fi
fi
echo $$ > "$LOCK"
trap "rm -f '$LOCK'" EXIT

check_and_restart_colima() {
    STATUS=$(colima status 2>&1)
    if echo "$STATUS" | grep -q "is running"; then
        echo "[$(date +%H:%M:%S)] [BABYSITTER] Colima OK" | tee -a "$LOG"
        return 0
    else
        echo "[$(date +%H:%M:%S)] [BABYSITTER] WARNING: Colima DOWN! Restarting..." | tee -a "$LOG"
        colima start 2>&1 | tee -a "$LOG"
        sleep 20
        echo "[$(date +%H:%M:%S)] [BABYSITTER] Colima restart done." | tee -a "$LOG"
        return 1
    fi
}

# Verify clip fix is in place before running
CLIP_CHECK=$(grep "read_surf" "$WORKDIR/CADDesign/in.hiad" 2>/dev/null | head -1 || echo "in.hiad not generated yet")
echo "[$(date +%H:%M:%S)] Current in.hiad read_surf: $CLIP_CHECK" | tee -a "$LOG"
echo "[$(date +%H:%M:%S)] Will regenerate with clip fix on run start" | tee -a "$LOG"

# Pre-flight
check_and_restart_colima
docker info > /dev/null 2>&1 && echo "[$(date +%H:%M:%S)] Docker OK" | tee -a "$LOG"

# Background babysitter (every 300s)
(
    while true; do
        sleep 300
        check_and_restart_colima
    done
) &
BABYSITTER_PID=$!
trap "kill $BABYSITTER_PID 2>/dev/null; rm -f '$LOCK'" EXIT

echo "[$(date +%H:%M:%S)] Starting: python main.py --validationPINN --headless" | tee -a "$LOG"
echo "----------------------------------------------" | tee -a "$LOG"

"$VENV" main.py --validationPINN --headless 2>&1 | tee -a "$LOG"
EXIT_CODE=${PIPESTATUS[0]}

echo "----------------------------------------------" | tee -a "$LOG"
echo "[$(date +%H:%M:%S)] Clip-fix run finished. Exit code: $EXIT_CODE" | tee -a "$LOG"

# Check result for cell classification
OUTSIDE=$(grep "cells outside/inside" "$LOG" | tail -1 | awk '{print $1}')
echo "[$(date +%H:%M:%S)] Fluid cells (outside): $OUTSIDE (expect ~76000 with clip fix)" | tee -a "$LOG"

if [ $EXIT_CODE -eq 0 ]; then
    echo "[$(date +%H:%M:%S)] [SUCCESS] clip-fix validationPINN completed!" | tee -a "$LOG"
else
    echo "[$(date +%H:%M:%S)] [WARN] Exit code $EXIT_CODE - check $LOG" | tee -a "$LOG"
fi

kill $BABYSITTER_PID 2>/dev/null || true
echo "=============================================" | tee -a "$LOG"
echo " Clip-fix run finished at $(date)" | tee -a "$LOG"
echo "=============================================" | tee -a "$LOG"
