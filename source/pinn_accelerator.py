import numpy as np
import os
import sys

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

def pde_euler_2d(x, y, v_stream=None, scales=None):
    """2D Steady Compressible Euler Equations for PINN (Dimensionless form)."""
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
    
    # Dimensionless derivatives (w.r.t scaled x, y)
    drho_x = dde.grad.jacobian(y, x, i=0, j=0)
    drho_y = dde.grad.jacobian(y, x, i=0, j=1)
    du_x = dde.grad.jacobian(y, x, i=1, j=0)
    du_y = dde.grad.jacobian(y, x, i=1, j=1)
    dv_x = dde.grad.jacobian(y, x, i=2, j=0)
    dv_y = dde.grad.jacobian(y, x, i=2, j=1)
    dp_x = dde.grad.jacobian(y, x, i=4, j=0)
    dp_y = dde.grad.jacobian(y, x, i=4, j=1)
    
    # Non-dimensionalized residuals
    # 1. Continuity: div(rho * U) = 0
    # Axisymmetric form: d(rho*u)/dx + d(rho*v)/dy + (rho*v)/y = 0
    y_coord = x[:, 1:2]
    eps = 1e-6
    continuity = drho_x * u_bar + rho_bar * du_x + drho_y * v_bar + rho_bar * dv_y + (rho_bar * v_bar) / (y_coord + eps)
    
    # 2. Momentum X: rho*(u*ux + v*uy) + px = 0
    # Scaled by (rho_r * u_r^2 / L_r)
    mom_x = rho_bar * (u_bar * du_x + v_bar * du_y) + (p_r / (rho_r * u_r**2)) * dp_x
    
    # 3. Momentum Y: rho*(u*vx + v*vy) + py = 0
    mom_y = rho_bar * (u_bar * dv_x + v_bar * dv_y) + (p_r / (rho_r * u_r**2)) * dp_y
    
    # 4. Equation of State: p = rho * R * T
    # Scaled by p_r
    eos = p_bar - (rho_r * R * T_r / p_r) * rho_bar * T_bar
    
    return [continuity, mom_x, mom_y, eos]

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

    def train_from_checkpoint(self, grid_file, domain_bounds, iterations=2000, inverse=False):
        """Uses SPARTA data as anchor points for PINN refinement or inverse estimation."""
        import deepxde as dde
        X_data, Y_data = parse_sparta_grid(grid_file)
        if X_data is None:
            print("Error: Could not parse SPARTA grid file.")
            return

        # Calculate Scales based on freestream or mean data
        # Using max values to keep everything in [0, 1] range roughly
        self.scales = {
            "rho": np.max(Y_data[:, 0]) if np.max(Y_data[:, 0]) > 0 else 1e-5,
            "u": np.max(np.abs(Y_data[:, 1])) if np.max(np.abs(Y_data[:, 1])) > 0 else 10000.0,
            "v": np.max(np.abs(Y_data[:, 2])) if np.max(np.abs(Y_data[:, 2])) > 0 else 1000.0,
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

        pde_fn = lambda x, y: pde_euler_2d(x, y, v_stream=self.v_est if inverse else None, scales=self.scales)

        data = dde.data.PDE(
            geom,
            pde_fn,
            [observe_y0, observe_y1, observe_y2, observe_y3, observe_y4],
            num_domain=2500,
            num_boundary=500,
            anchors=X_anchors
        )

        # Deeper network for complex shock features
        net = dde.nn.FNN([2] + [128] * 5 + [5], "tanh", "Glorot uniform")
        self.model = dde.Model(data, net)

        # Optimization with higher iterations for convergence
        if inverse:
            self.model.compile("adam", lr=1e-3, external_trainable_variables=self.v_est)
        else:
            # Set PDE weights to 0 temporarily to stabilize training if Euler equations are stiff
            # Indices: 0-3 (PDEs), 4-8 (Observations)
            self.model.compile("adam", lr=1e-3, loss_weights=[0, 0, 0, 0, 1, 1, 1, 1, 1])
            
        self.model.train(iterations=iterations, display_every=100)
        
        if inverse:
            v_real = self.v_est.item() * self.scales["u"]
            print(f"Estimated v_stream: {v_real}")
        
        return self.model

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
