@echo off
setlocal enabledelayedexpansion

set FLAG_FILE=ThesisOpt.flag
set MONITOR_INTERVAL=3600
set SLEEP_POLL=10

:: Default recovery arguments if needed: %1 = samples (default 25), %2 = tps_material (default multi)
set SAMPLES=%~1
if "%SAMPLES%"=="" set SAMPLES=25

set TPS_MATERIAL=%~2
if "%TPS_MATERIAL%"=="" set TPS_MATERIAL=multi

echo [*] flagMonitor_bgTask (Windows): Started at %date% %time%
echo [*] Auto-recovery parameters -> Samples: %SAMPLES%, TPS Material: %TPS_MATERIAL%

:asleep_loop
echo [*] Entering ASLEEP mode (polling every %SLEEP_POLL%s for %FLAG_FILE%)...
:poll_check
if not exist %FLAG_FILE% (
    timeout /t %SLEEP_POLL% /nobreak >nul
    goto poll_check
)

echo [*] FLAG DETECTED! Waking up into AWAKE monitoring mode...

:awake_loop
if not exist %FLAG_FILE% (
    echo [*] Flag removed! Returning to ASLEEP mode...
    goto asleep_loop
)

echo ==========================================================
echo [*] === Monitor Cycle at %date% %time% ===
echo ==========================================================

:: 1. Check Python process status
tasklist /FI "IMAGENAME eq python.exe" 2>NUL | find /I /N "python.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo [+] Python sampling process is RUNNING.
) else (
    echo [-] WARNING: Python process NOT FOUND. Is sampling active or stalled?
)

:: 2. Check Log Activity & Crash/Error Scanning with Auto-Recovery
if exist optimization_idle_run.log (
    echo [+] Checking optimization_idle_run.log...
    findstr /I /C:"error" /C:"exception" /C:"traceback" /C:"killed" /C:"segfault" optimization_idle_run.log >nul
    if "!ERRORLEVEL!"=="0" (
        echo [!] CRASH / ERROR DETECTED in optimization_idle_run.log!
        echo [*] Initiating autonomous recovery re-run...
        python main.py --headless --optimize --samples %SAMPLES% --tps-material %TPS_MATERIAL% > optimization_idle_run_rerun.log 2>&1
        if "!ERRORLEVEL!"=="0" (
            echo [+] Autonomous recovery re-run SUCCEEDED! Resuming normal operation.
            copy /Y optimization_idle_run_rerun.log optimization_idle_run.log
        ) else (
            echo [-] WARNING: Recovery re-run failed. Inspecting stack trace...
        )
    ) else (
        echo [+] Log clean (no critical errors found).
    )
)

if exist validation_idle_run.log (
    echo [+] Checking validation_idle_run.log...
    findstr /I /C:"error" /C:"exception" /C:"traceback" validation_idle_run.log >nul
    if "!ERRORLEVEL!"=="0" (
        echo [!] CRASH / ERROR DETECTED in validation_idle_run.log!
        echo [*] Initiating autonomous validation recovery...
        python main.py --headless --validation --tps-material %TPS_MATERIAL% > validation_idle_run_rerun.log 2>&1
        if "!ERRORLEVEL!"=="0" (
            echo [+] Validation recovery SUCCEEDED!
            copy /Y validation_idle_run_rerun.log validation_idle_run.log
        )
    )
)

:: 3. Sleep loop checking flag presence every 10 seconds
set /a REMAINING=%MONITOR_INTERVAL%
:sleep_chunk
if !REMAINING! LSS 1 goto awake_loop
if not exist %FLAG_FILE% goto asleep_loop

timeout /t 10 /nobreak >nul
set /a REMAINING-=10
goto sleep_chunk
