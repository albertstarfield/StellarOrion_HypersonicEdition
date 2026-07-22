@echo off
setlocal

:: Default parameters: %1 = sample count (default 25), %2 = tps-material (default multi)
set SAMPLES=%~1
if "%SAMPLES%"=="" set SAMPLES=25

set TPS_MATERIAL=%~2
if "%TPS_MATERIAL%"=="" set TPS_MATERIAL=multi

echo [*] Starting Windows sampling run sequence...
echo [*] Parameters -> Samples: %SAMPLES%, TPS Material: %TPS_MATERIAL%

if not exist Result mkdir Result

:: 1. Run Baseline Validation
echo [*] Running multi-layer TPS validation...
python main.py --headless --validation --tps-material %TPS_MATERIAL% > validation_idle_run.log 2>&1

:: 2. Save Validation Results
echo [*] Saving validation results to Result\validationResultAfterLayerChanges\ ...
if not exist Result\validationResultAfterLayerChanges mkdir Result\validationResultAfterLayerChanges
if exist web\assets\plots xcopy /E /I /Y web\assets\plots Result\validationResultAfterLayerChanges\plots
if exist OPTIMIZATION_LOG.md copy /Y OPTIMIZATION_LOG.md Result\validationResultAfterLayerChanges\
if exist validation_idle_run.log copy /Y validation_idle_run.log Result\validationResultAfterLayerChanges\

:: 3. Run Optimization Sampling Matrix
echo [*] Starting optimization sampling matrix...
python main.py --headless --optimize --samples %SAMPLES% --tps-material %TPS_MATERIAL% > optimization_idle_run.log 2>&1

:: 4. Save Optimization Results
echo [*] Saving optimization results to Result\OptimizationResult\ ...
if not exist Result\OptimizationResult mkdir Result\OptimizationResult
if exist web\assets\plots xcopy /E /I /Y web\assets\plots Result\OptimizationResult\plots
if exist OPTIMIZATION_LOG.md copy /Y OPTIMIZATION_LOG.md Result\OptimizationResult\
if exist optimization_history.db copy /Y optimization_history.db Result\OptimizationResult\
if exist StellarOrionIntentionLog.jsonl copy /Y StellarOrionIntentionLog.jsonl Result\OptimizationResult\
if exist optimization_idle_run.log copy /Y optimization_idle_run.log Result\OptimizationResult\

echo [*] Windows sampling background sequence complete.
endlocal
