@echo off
setlocal enabledelayedexpansion

:: Usage: 69_ThesisOptimization_bgTask.bat [num_samples] [tps_material]
set SAMPLES=%~1
if "%SAMPLES%"=="" set SAMPLES=25

set TPS_MATERIAL=%~2
if "%TPS_MATERIAL%"=="" set TPS_MATERIAL=multi

set FLAG_FILE=ThesisOpt.flag

echo RUNNING > %FLAG_FILE%
echo [*] Flag file created at %FLAG_FILE%. Starting Windows background task...
echo [*] Parameters -> Samples: %SAMPLES%, TPS Material: %TPS_MATERIAL%

if exist ThesisOptimization_executeMeAtIdle.bat (
    call ThesisOptimization_executeMeAtIdle.bat %SAMPLES% %TPS_MATERIAL%
) else (
    echo [*] Running direct sampling execution...
    if not exist Result mkdir Result
    python main.py --headless --validation --tps-material %TPS_MATERIAL% > validation_idle_run.log 2>&1
    python main.py --headless --optimize --samples %SAMPLES% --tps-material %TPS_MATERIAL% > optimization_idle_run.log 2>&1
)

if exist %FLAG_FILE% del /F /Q %FLAG_FILE%
echo [*] Task complete. Flag file removed.
endlocal
