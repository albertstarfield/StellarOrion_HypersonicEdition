#!/bin/bash
# flagMonitor_bgTask.sh - Baby-sits the thesis optimization background task
# Location: ~/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/flagMonitor_bgTask.sh
# Sleeps when no flag exists (10s polling), wakes to monitor every 3600s when flag exists.
# Returns to sleep mode immediately when flag disappears (user active/colima stopped).

WORK_DIR="/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition"
FLAG_FILE_1="$WORK_DIR/ThesisOpt.flag"
FLAG_FILE_2="/usr/local/AmaryllisIdleAutomode/MaintenanceTasks/flags/ThesisOpt.flag"
LOG_DIR="$WORK_DIR"
MONITOR_INTERVAL=3600  # 1 hour between detailed checks
SLEEP_POLL=10          # 10s polling when asleep or checking flag presence

echo "[*] flagMonitor_bgTask: Started at $(date '+%Y-%m-%d %H:%M:%S')"
echo "[*] flagMonitor_bgTask: Workspace directory: $WORK_DIR"

# Helper function to check if flag exists in either location
flag_exists() {
    if [ -f "$FLAG_FILE_1" ] || [ -f "$FLAG_FILE_2" ]; then
        return 0
    else
        return 1
    fi
}

while true; do
    # === ASLEEP MODE: Deep sleep, polling every 10s for flag ===
    echo "[*] flagMonitor_bgTask: Entering ASLEEP mode (polling every ${SLEEP_POLL}s for flag)..."
    while ! flag_exists; do
        sleep $SLEEP_POLL
    done

    echo "[*] flagMonitor_bgTask: FLAG DETECTED! Waking up into AWAKE monitoring mode..."
    echo "[*] flagMonitor_bgTask: Log monitoring cycle interval: ${MONITOR_INTERVAL}s"

    PREV_SIZE_OPT=0
    PREV_SIZE_VAL=0

    # === AWAKE MODE: Monitor optimization, validation, and logs ===
    while flag_exists; do
        TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
        NOW=$(date +%s)
        echo "=========================================================="
        echo "[*] flagMonitor_bgTask: === Monitor Cycle at $TIMESTAMP ==="
        echo "=========================================================="

        cd "$WORK_DIR" || { echo "[!] Cannot cd to $WORK_DIR"; break; }

        mkdir -p "$WORK_DIR/Result/bgMonitor"

        # ----------------------------------------------------
        # 0. SYSTEM LOAD & PROCESS MONITORING
        # ----------------------------------------------------
        echo "[0] Checking System Load & Process Status..."
        MAIN_PID=$(pgrep -f "python.*main.py" || echo "")
        if [ -n "$MAIN_PID" ]; then
            # Sum up CPU usage in case of multiple processes
            CPU_USAGE=$(ps -p $(pgrep -f "python.*main.py") -o %cpu= | awk '{sum+=$1} END {print sum}')
            echo "[+] main.py is RUNNING (PID: $MAIN_PID) with CPU Usage: ${CPU_USAGE}%"
            if [ "$(echo "$CPU_USAGE < 5.0" | bc -l 2>/dev/null || echo 0)" == "1" ]; then
                echo "[!] WARNING: main.py CPU usage is very low ($CPU_USAGE%). It might be STALLED or waiting for Docker."
            fi
        else
            echo "[-] main.py process NOT FOUND. Is the optimization script running?"
        fi
        
        # Check Docker container load
        export DOCKER_HOST="unix:///Users/albertstarfield/.colima/default/docker.sock"
        if docker ps &>/dev/null; then
            RUNNING_CONTAINERS=$(docker ps -q | wc -l | awk '{print $1}')
            echo "[+] Docker is reachable. $RUNNING_CONTAINERS containers running."
            if [ "$RUNNING_CONTAINERS" -gt 0 ]; then
                docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | sed 's/^/    - /'
            else
                echo "    - No active containers. If optimization is running, it might be in a non-compute phase."
            fi
        else
            echo "[-] Docker is NOT reachable or Colima is down."
        fi

        # ----------------------------------------------------
        # 1. LOG ACTIVITY & STALENESS MONITORING
        # ----------------------------------------------------
        echo "[1] Checking Log Activity & Staleness..."

        # Check optimization log
        if [ -f "$LOG_DIR/optimization_idle_run.log" ]; then
            LAST_MOD=$(stat -f "%m" "$LOG_DIR/optimization_idle_run.log" 2>/dev/null || echo "0")
            AGE=$((NOW - LAST_MOD))
            CUR_SIZE_OPT=$(stat -f "%z" "$LOG_DIR/optimization_idle_run.log" 2>/dev/null || echo "0")

            echo "    - optimization_idle_run.log: Size=${CUR_SIZE_OPT} bytes, Age=${AGE}s"

            if [ "$AGE" -gt 3600 ]; then
                echo "[!] ALERT: optimization_idle_run.log has not been updated in ${AGE}s (> 3600s)! Log may be STALE/STALLED."
            else
                echo "[+] Log modified recently (${AGE}s ago < 3600s)."
            fi

            if [ "$CUR_SIZE_OPT" -gt "$PREV_SIZE_OPT" ]; then
                echo "[+] Log file is GROWING (+ $((CUR_SIZE_OPT - PREV_SIZE_OPT)) bytes)."
            elif [ "$PREV_SIZE_OPT" -gt 0 ] && [ "$CUR_SIZE_OPT" -eq "$PREV_SIZE_OPT" ]; then
                echo "[!] Log file size UNCHANGED since last check (${CUR_SIZE_OPT} bytes)."
            fi
            PREV_SIZE_OPT=$CUR_SIZE_OPT
        else
            echo "    - optimization_idle_run.log: Not found yet."
        fi

        # Check validation log
        if [ -f "$LOG_DIR/validation_idle_run.log" ]; then
            LAST_MOD_VAL=$(stat -f "%m" "$LOG_DIR/validation_idle_run.log" 2>/dev/null || echo "0")
            AGE_VAL=$((NOW - LAST_MOD_VAL))
            CUR_SIZE_VAL=$(stat -f "%z" "$LOG_DIR/validation_idle_run.log" 2>/dev/null || echo "0")

            echo "    - validation_idle_run.log: Size=${CUR_SIZE_VAL} bytes, Age=${AGE_VAL}s"

            if [ "$CUR_SIZE_VAL" -gt "$PREV_SIZE_VAL" ]; then
                echo "[+] Validation log file is GROWING (+ $((CUR_SIZE_VAL - PREV_SIZE_VAL)) bytes)."
            fi
            PREV_SIZE_VAL=$CUR_SIZE_VAL
        else
            echo "    - validation_idle_run.log: Not found yet."
        fi

        # Check background execution wrapper log
        if [ -f "$LOG_DIR/idle_bg_task_execution.log" ]; then
            LAST_MOD_BG=$(stat -f "%m" "$LOG_DIR/idle_bg_task_execution.log" 2>/dev/null || echo "0")
            AGE_BG=$((NOW - LAST_MOD_BG))
            CUR_SIZE_BG=$(stat -f "%z" "$LOG_DIR/idle_bg_task_execution.log" 2>/dev/null || echo "0")
            echo "    - idle_bg_task_execution.log: Size=${CUR_SIZE_BG} bytes, Age=${AGE_BG}s"
            if [ "$AGE_BG" -gt 3600 ]; then
                echo "[!] ALERT: idle_bg_task_execution.log has not been updated in ${AGE_BG}s (> 3600s)!"
            fi
        fi

        # ----------------------------------------------------
        # 2. CRASH & ERROR MONITORING AND AUTONOMOUS RECOVERY
        # ----------------------------------------------------
        echo "[2] Scanning for Crashes & Errors..."

        CRASH_FOUND=0

        if [ -f "$LOG_DIR/validation_idle_run.log" ]; then
            CRASH_VAL=$(grep -iE "error|exception|traceback|killed|segfault" "$LOG_DIR/validation_idle_run.log" 2>/dev/null | grep -viE "No critical type errors|error waiting for container|Cannot connect to the Docker daemon|0 errors|trapFpe|FOAM_SIGFPE|Floating point exception|grid partition is not clumped|error calculations" | wc -l | awk '{print $1}')
            if [ -n "$CRASH_VAL" ] && [ "$CRASH_VAL" -gt 0 ]; then
                echo "[!] CRASH DETECTED in validation_idle_run.log ($CRASH_VAL error matches)!"
                echo "--- Tail of validation_idle_run.log ---"
                tail -n 25 "$LOG_DIR/validation_idle_run.log"
                echo "---------------------------------------"
                CRASH_FOUND=1
                
                # Attempt recovery re-run
                echo "[*] Attempting validation recovery re-run..."
                export DOCKER_HOST="unix:///Users/albertstarfield/.colima/default/docker.sock"
                PY_CMD="./.venv/bin/python"
                if [ ! -f "$PY_CMD" ]; then PY_CMD="python3"; fi
                $PY_CMD main.py --headless --validation --tps-material multi --target-vehicle irve3 > validation_idle_run_rerun.log 2>&1
                if [ $? -eq 0 ]; then
                    echo "[+] Validation recovery re-run SUCCEEDED!"
                    cp validation_idle_run_rerun.log validation_idle_run.log
                else
                    echo "[-] Validation recovery re-run failed."
                fi
            else
                echo "[+] Validation log clean (no critical errors)."
            fi
        fi

        if [ -f "$LOG_DIR/optimization_idle_run.log" ]; then
            CRASH_OPT=$(grep -iE "error|exception|traceback|killed|segfault" "$LOG_DIR/optimization_idle_run.log" 2>/dev/null | grep -viE "No critical type errors|error waiting for container|Cannot connect to the Docker daemon|0 errors|trapFpe|FOAM_SIGFPE|Floating point exception|grid partition is not clumped|error calculations" | wc -l | awk '{print $1}')
            if [ -n "$CRASH_OPT" ] && [ "$CRASH_OPT" -gt 0 ]; then
                echo "[!] CRASH DETECTED in optimization_idle_run.log ($CRASH_OPT error matches)!"
                echo "--- Tail of optimization_idle_run.log ---"
                tail -n 25 "$LOG_DIR/optimization_idle_run.log"
                echo "----------------------------------------"
                CRASH_FOUND=1
                
                # Attempt recovery re-run
                echo "[*] Attempting optimization recovery re-run..."
                export DOCKER_HOST="unix:///Users/albertstarfield/.colima/default/docker.sock"
                PY_CMD="./.venv/bin/python"
                if [ ! -f "$PY_CMD" ]; then PY_CMD="python3"; fi
                $PY_CMD main.py --headless --optimize --samples 2500 --tps-material multi --target-vehicle irve3 > optimization_idle_run_rerun.log 2>&1
                if [ $? -eq 0 ]; then
                    echo "[+] Optimization recovery re-run SUCCEEDED!"
                    cp optimization_idle_run_rerun.log optimization_idle_run.log
                else
                    echo "[-] Optimization recovery re-run failed."
                fi
            else
                echo "[+] Optimization log clean (no critical errors)."
            fi
        fi

        # ----------------------------------------------------
        # 3. VALIDATION RESULT INTEGRITY CHECK
        # ----------------------------------------------------
        echo "[3] Checking Validation Results..."
        VAL_DIR="$WORK_DIR/Result/validationResultAfterLayerChanges"
        if [ -d "$VAL_DIR" ]; then
            PLOT_COUNT=$(find "$VAL_DIR" -name "*.png" -o -name "*.jpg" 2>/dev/null | wc -l | awk '{print $1}')
            echo "[+] Validation result directory exists. Generated plots count: $PLOT_COUNT"
            if [ "$PLOT_COUNT" -lt 3 ]; then
                echo "[!] WARNING: Plot count ($PLOT_COUNT) is low. Check if graphics generation completed."
            else
                echo "[+] Validation plot output looks valid and reasonable."
            fi
        else
            echo "    - Validation result directory not populated yet."
        fi

        # ----------------------------------------------------
        # 4. OPTIMIZATION RESULT INTEGRITY CHECK
        # ----------------------------------------------------
        echo "[4] Checking Optimization Results..."
        DB_FILE="$WORK_DIR/optimization_history.db"
        if [ -f "$DB_FILE" ]; then
            DB_SIZE=$(stat -f%z "$DB_FILE" 2>/dev/null || echo "0")
            echo "[+] Optimization DB exists (Size: $DB_SIZE bytes)."
            if [ "$DB_SIZE" -gt 1000 ]; then
                REC_COUNT=$(python3 -c "import sqlite3; conn=sqlite3.connect('$DB_FILE'); c=conn.cursor(); c.execute('SELECT COUNT(*) FROM optimization_runs'); print(c.fetchone()[0])" 2>/dev/null || echo "N/A")
                echo "[+] Optimization DB contains $REC_COUNT recorded samples."
            fi
        else
            echo "    - Optimization database ($DB_FILE) not found yet."
        fi

        if [ -f "$WORK_DIR/OPTIMIZATION_LOG.md" ]; then
            LOG_MD_SIZE=$(stat -f%z "$WORK_DIR/OPTIMIZATION_LOG.md" 2>/dev/null || echo "0")
            echo "[+] OPTIMIZATION_LOG.md size: $LOG_MD_SIZE bytes."
        fi

        # Log status entry
        echo "$TIMESTAMP | LogSizeOpt: $CUR_SIZE_OPT | LogSizeVal: $CUR_SIZE_VAL | CrashFound: $CRASH_FOUND" >> "$WORK_DIR/Result/bgMonitor/monitor.log"

        echo "[*] Monitor cycle complete. Next cycle in ${MONITOR_INTERVAL}s (or immediate exit if flag removed)..."

        # ----------------------------------------------------
        # SLEEP LOOP WITH FAST FLAG DISAPPEARANCE DETECTION
        # ----------------------------------------------------
        REMAINING=$MONITOR_INTERVAL
        while [ $REMAINING -gt 0 ] && flag_exists; do
            SLEEP_CHUNK=10
            if [ $REMAINING -lt $SLEEP_CHUNK ]; then
                SLEEP_CHUNK=$REMAINING
            fi
            sleep $SLEEP_CHUNK
            REMAINING=$((REMAINING - SLEEP_CHUNK))
        done
    done

    echo "[*] flagMonitor_bgTask: Flag removed! User active or Colima stopped."
    echo "[*] Returning to ASLEEP mode..."
done
