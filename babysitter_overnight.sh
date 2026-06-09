#!/usr/bin/env bash
# =============================================================================
# StellarOrion Overnight Babysitter
# Runs --validationPINN with colima health monitoring every 300s
# Usage: bash babysitter_overnight.sh
# =============================================================================
set -e

WORKDIR="/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition"
VENV="$WORKDIR/.venv_gui/bin/python"
LOG="$WORKDIR/overnight_run.log"
LOCK="$WORKDIR/.babysitter.lock"

cd "$WORKDIR"

echo "=============================================" | tee -a "$LOG"
echo " StellarOrion Overnight Babysitter Started" | tee -a "$LOG"
echo " $(date)" | tee -a "$LOG"
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

# Pre-flight checks
echo "[$(date +%H:%M:%S)] Pre-flight: checking colima..." | tee -a "$LOG"
check_and_restart_colima
docker info > /dev/null 2>&1 && echo "[$(date +%H:%M:%S)] Docker OK" | tee -a "$LOG"

# Background babysitter loop (checks every 300s independently)
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

# Run the full validationPINN pipeline
"$VENV" main.py --validationPINN --headless 2>&1 | tee -a "$LOG"
EXIT_CODE=${PIPESTATUS[0]}

echo "----------------------------------------------" | tee -a "$LOG"
echo "[$(date +%H:%M:%S)] Run finished. Exit code: $EXIT_CODE" | tee -a "$LOG"

if [ $EXIT_CODE -eq 0 ]; then
    echo "[$(date +%H:%M:%S)] [SUCCESS] validationPINN completed successfully!" | tee -a "$LOG"
else
    echo "[$(date +%H:%M:%S)] [WARN] validationPINN exited with code $EXIT_CODE - check $LOG" | tee -a "$LOG"
fi

kill $BABYSITTER_PID 2>/dev/null || true
echo "=============================================" | tee -a "$LOG"
echo " Babysitter finished at $(date)" | tee -a "$LOG"
echo "=============================================" | tee -a "$LOG"
