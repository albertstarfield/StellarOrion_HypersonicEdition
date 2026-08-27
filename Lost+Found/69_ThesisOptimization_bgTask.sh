#!/bin/bash
# 69_ThesisOptimization_bgTask.sh
# Runs the baseline validation and optimization sequence when CPU/system is idle.
# Creates flag files in workspace and system flags directory to notify flagMonitor.

WORK_DIR="/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition"
FLAG_FILE_1="$WORK_DIR/ThesisOpt.flag"
FLAG_FILE_2="/usr/local/AmaryllisIdleAutomode/MaintenanceTasks/flags/ThesisOpt.flag"

mkdir -p "$WORK_DIR"
mkdir -p "/usr/local/AmaryllisIdleAutomode/MaintenanceTasks/flags"

cd "$WORK_DIR" || exit 1

export DOCKER_HOST="unix:///Users/albertstarfield/.colima/default/docker.sock"

# Cleanup function to remove flag files on exit or interruption
cleanup() {
    echo "[*] Cleaning up: removing flag files..."
    rm -f "$FLAG_FILE_1" "$FLAG_FILE_2"
    echo "[*] Flag files removed. flagMonitor will return to sleep mode."
    exit
}
trap cleanup EXIT INT TERM

# Create flag files to signal flagMonitor to wake up
touch "$FLAG_FILE_1" "$FLAG_FILE_2"
echo "RUNNING" > "$FLAG_FILE_1"
echo "RUNNING" > "$FLAG_FILE_2"
echo "[*] Flag files created at $FLAG_FILE_1 and $FLAG_FILE_2. Starting idle run sequence..."

# Execute the idle run sequence script with full output piping
LOG_FILE="$WORK_DIR/idle_bg_task_execution.log"
echo "[*] Directing all background execution output to $LOG_FILE"

if [ -f "./ThesisOptimization_executeMeAtIdle.sh" ]; then
    chmod +x ./ThesisOptimization_executeMeAtIdle.sh
    ./ThesisOptimization_executeMeAtIdle.sh > "$LOG_FILE" 2>&1
else
    echo "[!] ThesisOptimization_executeMeAtIdle.sh not found! Running default idle sequence..." | tee -a "$LOG_FILE"
    mkdir -p Result
    python3 main.py --headless --validation --tps-material multi --target-vehicle irve3 > validation_idle_run.log 2>&1
    python3 main.py --headless --optimize --samples 2500 --tps-material multi --target-vehicle irve3 > optimization_idle_run.log 2>&1
fi
