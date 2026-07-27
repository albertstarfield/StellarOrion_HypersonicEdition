@echo off
setlocal enabledelayedexpansion

:: flagMonitor_bgTask.bat - Monitors thesis optimization background sampling on Windows
:: Usage: flagMonitor_bgTask.bat [num_samples] [tps_material]
:: Example: flagMonitor_bgTask.bat 1100 multi

set SAMPLES=%~1
if "%SAMPLES%"=="" set SAMPLES=1100

set TPS_MATERIAL=%~2
if "%TPS_MATERIAL%"=="" set TPS_MATERIAL=multi

set FLAG_FILE=ThesisOpt.flag
set MONITOR_INTERVAL=3600
set SLEEP_POLL=10

set PREV_OPT_SIZE=0
set PREV_VAL_SIZE=0

echo [*] flagMonitor_bgTask (Windows): Started at %date% %time%
echo [*] Monitoring target flag: %FLAG_FILE%
echo [*] Autonomous Recovery Parameters -> Samples: %SAMPLES%, TPS Material: %TPS_MATERIAL%

:asleep_loop
echo [*] Entering ASLEEP mode (polling every %SLEEP_POLL%s for %FLAG_FILE%)...
:poll_check
if not exist %FLAG_FILE% (
    powershell -Command "Start-Sleep -Seconds %SLEEP_POLL%" >nul 2>&1
    goto poll_check
)

echo [*] FLAG DETECTED! Waking up into AWAKE monitoring mode...

:awake_loop
if not exist %FLAG_FILE% (
    echo [*] %FLAG_FILE% removed! Returning to ASLEEP mode...
    goto asleep_loop
)

echo ==========================================================
echo [*] === Monitor Cycle at %date% %time% ===
echo ==========================================================

:: ----------------------------------------------------
:: 1. SYSTEM PROCESS MONITORING
:: ----------------------------------------------------
echo [1] Checking System Process Status...
tasklist /FI "IMAGENAME eq python.exe" 2>NUL | find /I "python.exe" >nul
if "!ERRORLEVEL!"=="0" (
    echo [+] Python process is RUNNING.
    tasklist /FI "IMAGENAME eq python.exe"
) else (
    echo [-] WARNING: Python process NOT FOUND. Is sampling active or finished?
)

:: ----------------------------------------------------
:: 2. LOG ACTIVITY & SIZE GROWTH CHECK
:: ----------------------------------------------------
echo [2] Checking Log Activity and Growth...

if exist optimization_idle_run.log (
    for %%F in (optimization_idle_run.log) do set CURR_OPT_SIZE=%%~zF
    echo     - optimization_idle_run.log: Size=!CURR_OPT_SIZE! bytes
    if !CURR_OPT_SIZE! GTR !PREV_OPT_SIZE! (
        echo [+] optimization_idle_run.log is GROWING.
    ) else if !PREV_OPT_SIZE! GTR 0 (
        echo [!] WARNING: optimization_idle_run.log size UNCHANGED since last check.
    )
    set PREV_OPT_SIZE=!CURR_OPT_SIZE!
) else (
    echo     - optimization_idle_run.log not found yet.
)

if exist validation_idle_run.log (
    for %%F in (validation_idle_run.log) do set CURR_VAL_SIZE=%%~zF
    echo     - validation_idle_run.log: Size=!CURR_VAL_SIZE! bytes
    if !CURR_VAL_SIZE! GTR !PREV_VAL_SIZE! (
        echo [+] validation_idle_run.log is GROWING.
    )
    set PREV_VAL_SIZE=!CURR_VAL_SIZE!
) else (
    echo     - validation_idle_run.log not found yet.
)

:: ----------------------------------------------------
:: 3. CRASH LOOKOUT & AUTONOMOUS RECOVERY
:: ----------------------------------------------------
echo [3] Scanning Logs for Crashes/Exceptions/Errors...

set CRASH_DETECTED=0

if exist optimization_idle_run.log (
    findstr /I /C:"error" /C:"exception" /C:"traceback" /C:"killed" /C:"segfault" optimization_idle_run.log | findstr /V /I /C:"0 errors" /C:"No critical type errors" /C:"Error loading" >nul
    if "!ERRORLEVEL!"=="0" (
        echo [!] CRASH / EXCEPTION DETECTED in optimization_idle_run.log!
        echo --- Log Tail ^(Recent Output^) ---
        powershell -Command "Get-Content optimization_idle_run.log -Tail 30" 2>nul || type optimization_idle_run.log
        echo --------------------------------
        set CRASH_DETECTED=1
        echo [*] AUTONOMOUS RECOVERY: Triggering recovery re-run...
        python main.py --skip-venv-bootstrap --headless --optimize --samples %SAMPLES% --tps-material %TPS_MATERIAL% > optimization_idle_run_rerun.log 2>&1
        if "!ERRORLEVEL!"=="0" (
            echo [+] Autonomous recovery re-run SUCCEEDED! Updating log file...
            copy /Y optimization_idle_run_rerun.log optimization_idle_run.log >nul
        ) else (
            echo [-] ERROR: Recovery re-run encountered issues.
        )
    ) else (
        echo [+] optimization_idle_run.log is clean ^(no critical crash errors^).
    )
)

if exist validation_idle_run.log (
    findstr /I /C:"error" /C:"exception" /C:"traceback" /C:"killed" /C:"segfault" validation_idle_run.log | findstr /V /I /C:"0 errors" /C:"No critical type errors" /C:"Error loading" >nul
    if "!ERRORLEVEL!"=="0" (
        echo [!] CRASH / EXCEPTION DETECTED in validation_idle_run.log!
        echo --- Validation Log Tail ---
        powershell -Command "Get-Content validation_idle_run.log -Tail 20" 2>nul || type validation_idle_run.log
        echo ---------------------------
        echo [*] Triggering validation recovery...
        python main.py --skip-venv-bootstrap --headless --validation --tps-material %TPS_MATERIAL% > validation_idle_run_rerun.log 2>&1
        if "!ERRORLEVEL!"=="0" (
            echo [+] Validation recovery SUCCEEDED!
            copy /Y validation_idle_run_rerun.log validation_idle_run.log >nul
        )
    ) else (
        echo [+] validation_idle_run.log is clean.
    )
)

:: Log monitor pulse record
if not exist Result\bgMonitor mkdir Result\bgMonitor
echo %date% %time% ^| OptSize: !PREV_OPT_SIZE! ^| ValSize: !PREV_VAL_SIZE! ^| CrashDetected: !CRASH_DETECTED! >> Result\bgMonitor\monitor.log

echo [*] Monitor cycle complete. Sleeping for %MONITOR_INTERVAL%s (with 10s flag check)...

:: ----------------------------------------------------
:: 4. SLEEP LOOP WITH FAST FLAG DISAPPEARANCE DETECTION (3600s)
:: ----------------------------------------------------
set /a REMAINING=%MONITOR_INTERVAL%
:sleep_chunk
if !REMAINING! LSS 1 goto awake_loop
if not exist %FLAG_FILE% (
    echo [*] %FLAG_FILE% removed during sleep! Returning to ASLEEP mode...
    goto asleep_loop
)

powershell -Command "Start-Sleep -Seconds %SLEEP_POLL%" >nul 2>&1
set /a REMAINING-=%SLEEP_POLL%
goto sleep_chunk


