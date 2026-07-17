#!/bin/bash
sleep 600
cd "/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition"

mkdir -p Result

# 1. Run Baseline Validation with Multi-layer TPS
echo "[*] Running multi-layer TPS validation..."
python3 main.py --headless --validation --tps-material multi > validation_idle_run.log 2>&1

# 2. Save Validation Results
echo "[*] Saving validation results to Result/validationResultAfterLayerChanges/ ..."
mkdir -p Result/validationResultAfterLayerChanges
cp -r web/assets/plots Result/validationResultAfterLayerChanges/ 2>/dev/null
cp OPTIMIZATION_LOG.md Result/validationResultAfterLayerChanges/ 2>/dev/null
cp validation_idle_run.log Result/validationResultAfterLayerChanges/ 2>/dev/null

# 3. Run CCD Optimization Matrix
echo "[*] Starting full CCD optimization matrix..."
python3 main.py --headless --optimize --samples 25 --tps-material multi > optimization_idle_run.log 2>&1

# 4. Save Optimization Results
echo "[*] Saving optimization results to Result/OptimizationResult/ ..."
mkdir -p Result/OptimizationResult
cp -r web/assets/plots Result/OptimizationResult/ 2>/dev/null
cp OPTIMIZATION_LOG.md Result/OptimizationResult/ 2>/dev/null
cp optimization_history.db Result/OptimizationResult/ 2>/dev/null
cp StellarOrionIntentionLog.jsonl Result/OptimizationResult/ 2>/dev/null
cp optimization_idle_run.log Result/OptimizationResult/ 2>/dev/null

echo "[*] Idle background sequence complete."
