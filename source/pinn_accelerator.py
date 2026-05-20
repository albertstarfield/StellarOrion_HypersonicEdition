import numpy as np
import os
import sys
from typing import Any

# Set backend to pytorch
os.environ["DDE_BACKEND"] = "pytorch"

def parse_sparta_grid(filepath):
    """Parses SPARTA grid dump and returns data for PINN training.
    Returns: X (coords), Y (rho, u, v, T, p)
    """
    data = []
    with open(filepath, 'r') as f:
        lines = f.readlines()
        start_index = 0
        for i, line in enumerate(lines):
            if "ITEM: CELLS" in line:
                start_index = i + 1
                break
        
        for line in lines[start_index:]:
            parts = line.split()
            if len(parts) >= 11:
                # id xlo ylo xhi yhi f_2[1] f_2[2] f_2[3] f_2[4] f_3[1] f_4[1]
                # row indices:
                # 0: xlo, 1: ylo, 2: xhi, 3: yhi,
                # 4: f_2[1] (n), 5: f_2[2] (u), 6: f_2[3] (v), 7: f_2[4] (w)
                # 8: f_3[1] (temp), 9: f_4[1] (nrho)
                row = [float(x) for x in parts[1:]]
                # x_center, y_center
                xc = (row[0] + row[2]) / 2.0
                yc = (row[1] + row[3]) / 2.0
                u = row[5]
                v = row[6]
                T = row[8]
                nrho = row[9]
                
                # Assume air (M=0.02897 kg/mol)
                m_avg = 28.97e-3 / 6.022e23 # Simplified mass per molecule
                rho = nrho * m_avg
                
                # Pressure = nrho * k_B * T
                k_B = 1.380649e-23
                p = nrho * k_B * T
                
                data.append([xc, yc, rho, u, v, T, p])
                
    data = np.array(data)
    if len(data) == 0:
        return None, None
    
    X = data[:, :2] # (x, y)
    Y = data[:, 2:] # (rho, u, v, T, p)
    return X, Y

def pde_navier_stokes_2d(x, y, v_stream=None, scales=None):
    """2D Compressible Navier-Stokes Equations for PINN (Axisymmetric form)."""
    import deepxde as dde
    # If no scales provided, use 1.0 (Dimensional form)
    if scales is None:
        scales = {"rho": 1.0, "u": 1.0, "v": 1.0, "T": 1.0, "p": 1.0, "L": 1.0}
    
    rho_r, u_r, v_r, T_r, p_r, L_r = scales["rho"], scales["u"], scales["v"], scales["T"], scales["p"], scales["L"]
    
    rho_bar = y[:, 0:1]
    u_bar = y[:, 1:2]
    v_bar = y[:, 2:3]
    T_bar = y[:, 3:4]
    p_bar = y[:, 4:5]
    
    # Gas constants (Air)
    R = 287.05
    
    # Temperature-dependent viscosity using Sutherland's Law (Dimensional T)
    # Clamp temperature to positive values to avoid NaN when raising to fractional power 1.5
    import torch
    T_dim = torch.clamp(T_bar * T_r, min=10.0)
    # Sutherland constants for air: mu_ref = 1.716e-5 Pa s at T_ref = 273.15 K, S = 110.4 K
    mu_dim = 1.716e-5 * (T_dim / 273.15)**1.5 * (273.15 + 110.4) / (T_dim + 110.4)
    # Dimensionless viscous coefficient
    visc_coeff = mu_dim / (rho_r * u_r * L_r)
    
    # Dimensionless derivatives (w.r.t scaled x, y)
    drho_x: Any = dde.grad.jacobian(y, x, i=0, j=0)
    drho_y: Any = dde.grad.jacobian(y, x, i=0, j=1)
    du_x: Any = dde.grad.jacobian(y, x, i=1, j=0)
    du_y: Any = dde.grad.jacobian(y, x, i=1, j=1)
    dv_x: Any = dde.grad.jacobian(y, x, i=2, j=0)
    dv_y: Any = dde.grad.jacobian(y, x, i=2, j=1)
    dp_x: Any = dde.grad.jacobian(y, x, i=4, j=0)
    dp_y: Any = dde.grad.jacobian(y, x, i=4, j=1)
    
    # Second derivatives for viscous terms
    du_xx: Any = dde.grad.hessian(y, x, component=1, i=0, j=0)
    du_yy: Any = dde.grad.hessian(y, x, component=1, i=1, j=1)
    du_xy: Any = dde.grad.hessian(y, x, component=1, i=0, j=1)
    
    dv_xx: Any = dde.grad.hessian(y, x, component=2, i=0, j=0)
    dv_yy: Any = dde.grad.hessian(y, x, component=2, i=1, j=1)
    dv_xy: Any = dde.grad.hessian(y, x, component=2, i=0, j=1)
    du_xy_2: Any = dde.grad.hessian(y, x, component=1, i=0, j=1)

    # 1. Continuity: Axisymmetric form d(rho*u)/dx + d(rho*v)/dy + (rho*v)/y = 0
    y_coord = x[:, 1:2]
    eps_y = 1e-3
    eps_y2 = 1e-4
    continuity = drho_x * u_bar + rho_bar * du_x + drho_y * v_bar + rho_bar * dv_y + (rho_bar * v_bar) / (y_coord + eps_y)
    
    # Axisymmetric viscous terms
    visc_x_axisym = (1.0 / (y_coord + eps_y)) * du_y + (1.0 / 3.0) * (1.0 / (y_coord + eps_y)) * dv_x
    visc_x_total = (4.0/3.0)*du_xx + du_yy + (1.0/3.0)*dv_xy + visc_x_axisym
    
    visc_y_axisym = (4.0 / 3.0) * (1.0 / (y_coord + eps_y)) * dv_y - (4.0 / 3.0) * v_bar / (y_coord**2 + eps_y2)
    visc_y_total = (4.0/3.0)*dv_yy + dv_xx + (1.0/3.0)*du_xy_2 + visc_y_axisym
    
    # 2. Momentum X: rho*(u*ux + v*uy) + px - visc = 0
    mom_x = rho_bar * (u_bar * du_x + v_bar * du_y) + (p_r / (rho_r * u_r**2)) * dp_x - visc_coeff * visc_x_total
    
    # 3. Momentum Y: rho*(u*vx + v*vy) + py - visc = 0
    mom_y = rho_bar * (u_bar * dv_x + v_bar * dv_y) + (p_r / (rho_r * u_r**2)) * dp_y - visc_coeff * visc_y_total
    
    # 4. Equation of State: p = rho * R * T
    eos = p_bar - (rho_r * R * T_r / p_r) * rho_bar * T_bar
    
    # 5. Energy Equation: Axisymmetric compressible form
    dT_x: Any = dde.grad.jacobian(y, x, i=3, j=0)
    dT_y: Any = dde.grad.jacobian(y, x, i=3, j=1)
    dT_xx: Any = dde.grad.hessian(y, x, component=3, i=0, j=0)
    dT_yy: Any = dde.grad.hessian(y, x, component=3, i=1, j=1)
    
    # Heat conduction (with axisymmetric term)
    Pr = 0.71
    energy_cond = (visc_coeff / Pr) * (dT_xx + dT_yy + dT_y / (y_coord + eps_y))
    
    # Convection
    energy_conv = rho_bar * (u_bar * dT_x + v_bar * dT_y)
    
    # Pressure work: +u*dp/dx + v*dp/dy (energy added by compression work)
    coeff_work = p_r / (rho_r * 1005.0 * T_r)
    energy_work = coeff_work * (u_bar * dp_x + v_bar * dp_y)
    
    # Viscous dissipation (Eckert / Reynolds coupling)
    Ec_over_Re = (u_r**2 / (1005.0 * T_r)) * visc_coeff
    div_u = du_x + dv_y + v_bar / (y_coord + eps_y)
    phi_visc = 2.0 * (du_x**2 + dv_y**2 + (v_bar / (y_coord + eps_y))**2) + (du_y + dv_x)**2 - (2.0/3.0) * (div_u**2)
    energy_visc = Ec_over_Re * phi_visc
    
    # Energy equation: rho*cp*(u*dT/dx + v*dT/dy) = k*nabla^2(T) + u*dp/dx + v*dp/dy + Phi
    # Residual form: LHS - RHS = 0
    energy = energy_conv - energy_cond - energy_work - energy_visc
    
    return [continuity, mom_x, mom_y, eos, energy]

class PINNAccelerator:
    def __init__(self, device="mps"):
        import deepxde as dde
        import torch
        self.device = device
        # Some versions of DeepXDE might not have set_default_device
        if hasattr(dde.config, "set_default_device"):
            try:
                if device == "mps":
                    dde.config.set_default_device("mps")
                elif device == "cuda":
                    dde.config.set_default_device("cuda")
            except Exception as e:
                print(f"Warning: Could not set DeepXDE default device to {device}: {e}")
        else:
            print(f"Note: deepxde.config.set_default_device not found. DeepXDE will use its internal defaults for {os.environ.get('DDE_BACKEND', 'pytorch')}.")
        
        self.model = None
        self.scales = None
        self.v_est = dde.Variable(1.0) # Scaled variable
        self.loss_history = []  # Track loss per training stage for convergence analysis

    def train_from_checkpoint(self, grid_file, domain_bounds, iterations=2000, inverse=False, save_path=None, loss_weights=None):
        """Uses SPARTA data as anchor points for PINN refinement or inverse estimation."""
        import deepxde as dde
        import torch
        
        X_data, Y_data = parse_sparta_grid(grid_file)
        if X_data is None or Y_data is None:
            print("Error: Could not parse SPARTA grid file.")
            return

        # Calculate Scales based on freestream or mean data
        # Scale u and v by a common velocity scale to simplify physical equations
        u_max = np.max(np.abs(Y_data[:, 1])) if np.max(np.abs(Y_data[:, 1])) > 0 else 10000.0
        v_max = np.max(np.abs(Y_data[:, 2])) if np.max(np.abs(Y_data[:, 2])) > 0 else 1000.0
        u_scale = max(u_max, v_max)
        
        self.scales = {
            "rho": np.max(Y_data[:, 0]) if np.max(Y_data[:, 0]) > 0 else 1e-5,
            "u": u_scale,
            "v": u_scale,
            "T": np.max(Y_data[:, 3]) if np.max(Y_data[:, 3]) > 0 else 5000.0,
            "p": np.max(Y_data[:, 4]) if np.max(Y_data[:, 4]) > 0 else 1000.0,
            "L": max(abs(domain_bounds[0]), abs(domain_bounds[1]), abs(domain_bounds[2]))
        }
        
        # Scale Data
        X_scaled = X_data / self.scales["L"]
        Y_scaled = Y_data / np.array([self.scales["rho"], self.scales["u"], self.scales["v"], self.scales["T"], self.scales["p"]])
        bounds_scaled = [domain_bounds[0]/self.scales["L"], domain_bounds[1]/self.scales["L"], domain_bounds[2]/self.scales["L"]]

        # Define Domain
        geom = dde.geometry.Rectangle([bounds_scaled[0], 0], [bounds_scaled[1], bounds_scaled[2]])
        
        # Subsample anchor points if too many (for performance on CPU)
        if len(X_scaled) > 5000:
            idx = np.random.choice(len(X_scaled), 5000, replace=False)
            X_anchors = X_scaled[idx]
            Y_anchors = Y_scaled[idx]
        else:
            X_anchors = X_scaled
            Y_anchors = Y_scaled

        # Observation BCs (Scaled) - Use subsampled points
        observe_y0 = dde.icbc.PointSetBC(X_anchors, Y_anchors[:, 0:1], component=0) # rho
        observe_y1 = dde.icbc.PointSetBC(X_anchors, Y_anchors[:, 1:2], component=1) # u
        observe_y2 = dde.icbc.PointSetBC(X_anchors, Y_anchors[:, 2:3], component=2) # v
        observe_y3 = dde.icbc.PointSetBC(X_anchors, Y_anchors[:, 3:4], component=3) # T
        observe_y4 = dde.icbc.PointSetBC(X_anchors, Y_anchors[:, 4:5], component=4) # p

        pde_fn = lambda x, y: pde_navier_stokes_2d(x, y, v_stream=self.v_est if inverse else None, scales=self.scales)

        data = dde.data.PDE(
            geom,
            pde_fn,
            [observe_y0, observe_y1, observe_y2, observe_y3, observe_y4],
            num_domain=2500,
            num_boundary=500,
            anchors=X_anchors
        )

        # Deeper network for complex shock features
        net = dde.nn.FNN([2] + [128] * 5 + [5], "tanh", "Glorot uniform")  # type: ignore
        self.model = dde.Model(data, net)

        # Optimization with higher iterations for convergence
        if inverse:
            self.model.compile("adam", lr=1e-3, external_trainable_variables=self.v_est)
        else:
            # Activate PDE losses as physical regularizers
            if loss_weights is None or len(loss_weights) != 10:
                loss_weights = [1e-4, 1e-4, 1e-4, 1e-4, 1e-4, 1.0, 1.0, 1.0, 1.0, 1.0]
            self.model.compile("adam", lr=1e-3, loss_weights=loss_weights)

        # Restore checkpoint if it exists and we want to load it
        checkpoint_loaded = False
        if save_path:
            # Try to load both weights and scales
            checkpoint_loaded = self.load(save_path, geom=geom)
            if not checkpoint_loaded and os.path.exists(save_path):
                # Fallback to direct weight loading if only weight file exists
                try:
                    self.model.net.load_state_dict(torch.load(save_path, map_location=torch.device(self.device)))
                    print(f"[PINN] Successfully restored weights from {save_path}")
                    checkpoint_loaded = True
                except Exception as restore_err:
                    print(f"[PINN] Warning: Could not restore weights fallback: {restore_err}. Training from scratch.")

        if not checkpoint_loaded:
            print(f"[PINN] Starting training for {iterations} iterations...")
            if not inverse:
                print(f"[PINN] Stage 1: Data Pre-training (fitting observation constraints)...")
                stage1_weights = [0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0]
                self.model.compile("adam", lr=1e-3, loss_weights=stage1_weights)
                losshistory1, _ = self.model.train(iterations=iterations // 2, display_every=100)
                # Store ONLY data-term loss (last 5 components, indices 5-9)
                # NOT float(sum(l)) which includes 5 zero PDE terms in Stage 1
                # and triggers false-plateau at step 9.
                self.loss_history.extend([
                    (i * 100, float(sum(l[5:])))  # data terms only, actual iter number
                    for i, l in enumerate(losshistory1.loss_train)
                ])
                
                print(f"[PINN] Stage 2: Physics-Regularized Fine-tuning...")
                if loss_weights is None or len(loss_weights) != 10:
                    stage2_weights = [1e-4, 1e-4, 1e-4, 1e-4, 1e-4, 1.0, 1.0, 1.0, 1.0, 1.0]
                else:
                    stage2_weights = loss_weights
                self.model.compile("adam", lr=5e-4, loss_weights=stage2_weights)  # Reduced LR for fine-tuning
                losshistory2, _ = self.model.train(iterations=iterations - (iterations // 2), display_every=100)
                offset = len(self.loss_history)
                self.loss_history.extend([
                    (offset * 100 + i * 100, float(sum(l[5:])))  # data terms only, actual iter number
                    for i, l in enumerate(losshistory2.loss_train)
                ])
                
                # Report convergence quality
                final_loss = self.loss_history[-1][1] if self.loss_history else float('nan')
                plateau_iter = self.find_optimal_iterations()
                print(f"[PINN] Training complete. Final loss: {final_loss:.4e}. Plateau detected at: {plateau_iter} iterations.")
            else:
                self.model.train(iterations=iterations, display_every=100)
            
            # Save checkpoint after successful training
            if save_path:
                try:
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    self.save(save_path)
                except Exception as save_err:
                    print(f"[PINN] Warning: Could not save checkpoint: {save_err}")
        
        if inverse:
            v_real = self.v_est.item() * self.scales["u"]
            print(f"Estimated v_stream: {v_real}")
        
        return self.model

    def find_optimal_iterations(self, plateau_threshold=0.01):
        """Analyzes data-term loss history to find the optimal (plateau) training iteration.
        
        Returns the iteration where relative improvement in DATA losses (not PDE residuals)
        drops below plateau_threshold. Requires at least 20% of total steps to have passed
        to prevent false early-plateau triggers (e.g. the step-9 false positive from run 1
        where Stage 1 zero PDE terms made total sum appear unchanged).
        
        Answers AgenticInst.txt: 'find out at what steps it is most optimal to train PINN'.
        """
        if not self.loss_history or len(self.loss_history) < 10:
            return -1  # Not enough data
        
        losses = [l for _, l in self.loss_history]
        
        # Smooth with a rolling window to reduce noise
        window = max(5, len(losses) // 20)
        smoothed = []
        for i in range(len(losses)):
            start = max(0, i - window)
            smoothed.append(sum(losses[start:i+1]) / (i - start + 1))
        
        # Require at least 20% of total steps before allowing plateau declaration
        # Prevents false positives at early steps where loss is still rapidly changing
        min_plateau_idx = max(1, len(smoothed) // 5)
        
        # Find where relative improvement < threshold (after min_plateau_idx)
        plateau_idx = len(smoothed) - 1  # default: last iteration
        for i in range(min_plateau_idx, len(smoothed)):
            if smoothed[i-1] > 0:
                rel_improvement = abs(smoothed[i-1] - smoothed[i]) / smoothed[i-1]
                if rel_improvement < plateau_threshold:
                    plateau_idx = i
                    break
        
        optimal_iter = self.loss_history[plateau_idx][0]
        print(f"[PINN] Convergence plateau detected at iteration {optimal_iter} "
              f"(data_loss={smoothed[plateau_idx]:.4e}, rel_improve<{plateau_threshold:.1%})")
        return optimal_iter

    def save(self, filepath):

        """Saves both model weights and normalization scales."""
        import torch
        import json
        if self.model is None or self.scales is None:
            print("[PINN] Error: Model is not trained yet.")
            return False
        
        base_path, ext = os.path.splitext(filepath)
        weights_path = base_path + ".pt"
        scales_path = base_path + "_scales.json"
        
        try:
            torch.save(self.model.net.state_dict(), weights_path)
            # Standard copy of weights_path to the exact filepath requested so direct checks pass
            torch.save(self.model.net.state_dict(), filepath)
            with open(scales_path, "w") as f:
                json.dump(self.scales, f, indent=4)
            print(f"[PINN] Model and scales saved to {base_path}")
            return True
        except Exception as e:
            print(f"[PINN] Error saving model: {e}")
            return False

    def load(self, filepath, geom=None):
        """Loads both model weights and normalization scales."""
        import torch
        import json
        import deepxde as dde
        
        base_path, ext = os.path.splitext(filepath)
        weights_path = base_path + ".pt"
        scales_path = base_path + "_scales.json"
        
        # Check standard paths
        if not os.path.exists(weights_path) and os.path.exists(filepath):
            weights_path = filepath
            
        if not os.path.exists(weights_path) or not os.path.exists(scales_path):
            return False
            
        try:
            with open(scales_path, "r") as f:
                self.scales = json.load(f)
                
            if geom is None:
                # Approximate geometry using standard bounds or scales
                L = self.scales.get("L", 1.0)
                geom = dde.geometry.Rectangle([-1.0, 0], [1.0, 1.0])
                
            pde_fn = lambda x, y: pde_navier_stokes_2d(x, y, scales=self.scales)
            dummy_data = dde.data.PDE(geom, pde_fn, [], num_domain=100)
            net = dde.nn.FNN([2] + [128] * 5 + [5], "tanh", "Glorot uniform")
            self.model = dde.Model(dummy_data, net)
            
            self.model.net.load_state_dict(torch.load(weights_path, map_location=torch.device(self.device)))
            self.model.compile("adam", lr=1e-3) # Compile required for prediction
            print(f"[PINN] Model loaded and compiled successfully from {base_path}")
            return True
        except Exception as e:
            print(f"[PINN] Error loading model: {e}")
            return False

    def predict_gap_fill(self, X_query):
        """Predicts values at query points and un-scales them."""
        if self.model is None or self.scales is None:
            return None
        
        X_scaled = X_query / self.scales["L"]
        Y_scaled = self.model.predict(X_scaled)
        
        # Un-scale
        Y_unscaled = Y_scaled * np.array([self.scales["rho"], self.scales["u"], self.scales["v"], self.scales["T"], self.scales["p"]])
        return Y_unscaled

import torch
if __name__ == "__main__":
    # Quick test if run directly
    accel = PINNAccelerator(device="mps" if torch.backends.mps.is_available() else "cpu")
    print(f"PINN Accelerator initialized on {accel.device}")

