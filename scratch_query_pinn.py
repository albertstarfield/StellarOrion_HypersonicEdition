import numpy as np
import os
import torch
import json
import deepxde as dde

from source.pinn_accelerator import PINNAccelerator

# Initialize accelerator
device = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
pinn = PINNAccelerator(device=device)

# Load checkpoint
checkpoint_path = "/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/CADDesign/results_reference/pinn_checkpoint_1100"
success = pinn.load(checkpoint_path)
print("Loaded successfully:", success)

if success:
    # Load some grid data
    grid_file = "/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/CADDesign/results_reference/grid.1100.out"
    data = []
    with open(grid_file, 'r') as f:
        lines = f.readlines()
    start_index = 0
    for i, line in enumerate(lines):
        if "ITEM: CELLS" in line:
            start_index = i + 1
            break
            
    for line in lines[start_index:]:
        parts = line.split()
        if len(parts) >= 11:
            row = [float(x) for x in parts[1:]]
            xc = (row[0] + row[2]) / 2.0
            yc = (row[1] + row[3]) / 2.0
            u = row[5]
            v = row[6]
            T = row[8]
            nrho = row[9]
            
            m_avg = 28.97e-3 / 6.022e23
            rho = nrho * m_avg
            k_B = 1.380649e-23
            p = nrho * k_B * T
            
            data.append([xc, yc, rho, u, v, T, p])
                
    data = np.array(data)
    
    # Sort by true pressure descending
    sorted_indices = np.argsort(data[:, 6])[::-1]
    high_p_pts = data[sorted_indices[:15]]
    
    # Predict
    preds = pinn.predict_gap_fill(high_p_pts[:, :2])
    
    print("\nComparison of SPARTA vs PINN at HIGH Pressure Cells:")
    print(f"{'X':<8} | {'Y':<8} | {'Var':<5} | {'SPARTA':<12} | {'PINN':<12} | {'Ratio':<8}")
    print("-" * 65)
    variables = ['rho', 'u', 'v', 'T', 'p']
    for idx, row in enumerate(high_p_pts):
        x, y = row[0], row[1]
        print(f"Cell {idx}: Coords = [{x:.3f}, {y:.3f}]")
        for v_idx, var_name in enumerate(variables):
            true_val = row[2 + v_idx]
            pred_val = preds[idx, v_idx]
            ratio = pred_val / true_val if true_val != 0 else float('nan')
            print(f"         |          | {var_name:<5} | {true_val:<12.4e} | {pred_val:<12.4e} | {ratio:<8.3f}")
        print("-" * 65)
