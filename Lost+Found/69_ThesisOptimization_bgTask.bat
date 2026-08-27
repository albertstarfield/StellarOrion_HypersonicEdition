@echo off
setlocal enabledelayedexpansion

:: Usage: 69_ThesisOptimization_bgTask.bat [num_samples] [tps_material]
:: Example: 69_ThesisOptimization_bgTask.bat 1100 multi

set SAMPLES=%~1
if "%SAMPLES%"=="" set SAMPLES=1100

set TPS_MATERIAL=%~2
if "%TPS_MATERIAL%"=="" set TPS_MATERIAL=multi

set FLAG_FILE=ThesisOpt.flag

echo RUNNING > %FLAG_FILE%
echo [*] Flag file created at %FLAG_FILE%. Starting Windows background sampling task...
echo [*] Parameters -> Samples: %SAMPLES%, TPS Material: %TPS_MATERIAL%

if exist ThesisOptimization_executeMeAtIdle.bat (
    echo [*] Launching via ThesisOptimization_executeMeAtIdle.bat...
    call ThesisOptimization_executeMeAtIdle.bat %SAMPLES% %TPS_MATERIAL%
) else (
    echo [*] ThesisOptimization_executeMeAtIdle.bat not found. Running direct sampling execution...
    if not exist Result mkdir Result
    python main.py --skip-venv-bootstrap --headless --validation --tps-material %TPS_MATERIAL% --target-vehicle irve3 > validation_idle_run.log 2>&1
    python main.py --skip-venv-bootstrap --headless --optimize --samples %SAMPLES% --tps-material %TPS_MATERIAL% --target-vehicle irve3 > optimization_idle_run.log 2>&1
)

if exist %FLAG_FILE% del /F /Q %FLAG_FILE%
echo [*] Task complete. Flag file %FLAG_FILE% removed.
endlocal

