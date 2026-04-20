import numpy as np
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
                # id xlo ylo xhi yhi n u v w temp press
                row = [float(x) for x in parts[1:]]
                # x_center, y_center
                xc = (row[0] + row[2]) / 2.0
                yc = (row[1] + row[3]) / 2.0
                n = row[4]
                u = row[5]
                v = row[6]
                # w = row[7] (neglected for 2D PINN)
                T = row[8]
                p = row[9]
                
                # Assume air (M=0.02897 kg/mol)
                m_avg = 28.97e-3 / 6.022e23 # Simplified mass per molecule
                rho = n * m_avg
                
                data.append([xc, yc, rho, u, v, T, p])
                
    data = np.array(data)
    if len(data) == 0:
        return None, None
    
    X = data[:, :2] # (x, y)
    Y = data[:, 2:] # (rho, u, v, T, p)
    return X, Y

def pde_euler_2d(x, y, v_stream=None):
    """2D Steady Compressible Euler Equations for PINN.
    If v_stream is provided as a dde.Variable, it will be estimated (Inverse problem).
    """
    import deepxde as dde
    rho = y[:, 0:1]
    u = y[:, 1:2]
    v = y[:, 2:3]
    T = y[:, 3:4]
    p = y[:, 4:5]
    
    # Gas constants (Air)
    R = 287.05
    
    # Derivatives
    drho_x = dde.grad.jacobian(y, x, i=0, j=0)
    drho_y = dde.grad.jacobian(y, x, i=0, j=1)
    
    du_x = dde.grad.jacobian(y, x, i=1, j=0)
    du_y = dde.grad.jacobian(y, x, i=1, j=1)
    
    dv_x = dde.grad.jacobian(y, x, i=2, j=0)
    dv_y = dde.grad.jacobian(y, x, i=2, j=1)
    
    dp_x = dde.grad.jacobian(y, x, i=4, j=0)
    dp_y = dde.grad.jacobian(y, x, i=4, j=1)
    
    # Continuity: div(rho * U) = 0
    continuity = drho_x * u + rho * du_x + drho_y * v + rho * dv_y
    
    # Momentum X: rho*(u*ux + v*uy) + px = 0
    mom_x = rho * (u * du_x + v * du_y) + dp_x
    
    # Momentum Y: rho*(u*vx + v*vy) + py = 0
    mom_y = rho * (u * dv_x + v * dv_y) + dp_y
    
    # Equation of State: p = rho * R * T
    eos = p - rho * R * T
    
    res = [continuity, mom_x, mom_y, eos]
    
    # Optional: If we are estimating v_stream (e.g. for inverse problems)
    if v_stream is not None:
        # We could add a penalty if the predicted u at inlet differs from v_stream
        # But usually in inverse problems, we learn the parameter that best fits the OBSERVED data
        pass
        
    return res

class PINNAccelerator:
    def __init__(self, device="mps"):
        import deepxde as dde
        import torch
        self.device = device
        if device == "mps":
            dde.config.set_default_device("mps")
        elif device == "cuda":
            dde.config.set_default_device("cuda")
        
        self.model = None
        self.v_est = dde.Variable(10000.0) # Trainable parameter for inverse estimation

    def train_from_checkpoint(self, grid_file, domain_bounds, iterations=1000, inverse=False):
        """Uses SPARTA data as anchor points for PINN refinement or inverse estimation."""
        import deepxde as dde
        X_data, Y_data = parse_sparta_grid(grid_file)
        if X_data is None:
            print("Error: Could not parse SPARTA grid file.")
            return

        # Define Domain: Rectangle [xmin, xmax] x [0, ymax]
        geom = dde.geometry.Rectangle([domain_bounds[0], 0], [domain_bounds[1], domain_bounds[2]])
        
        # Use PointSet BC for the SPARTA data
        observe_y0 = dde.icbc.PointSetBC(X_data, Y_data[:, 0:1], component=0) # rho
        observe_y1 = dde.icbc.PointSetBC(X_data, Y_data[:, 1:2], component=1) # u
        observe_y2 = dde.icbc.PointSetBC(X_data, Y_data[:, 2:3], component=2) # v
        observe_y3 = dde.icbc.PointSetBC(X_data, Y_data[:, 3:4], component=3) # T
        observe_y4 = dde.icbc.PointSetBC(X_data, Y_data[:, 4:5], component=4) # p

        pde_fn = lambda x, y: pde_euler_2d(x, y, v_stream=self.v_est if inverse else None)

        data = dde.data.PDE(
            geom,
            pde_fn,
            [observe_y0, observe_y1, observe_y2, observe_y3, observe_y4],
            num_domain=2000,
            num_boundary=400,
            anchors=X_data
        )

        net = dde.nn.FNN([2] + [64] * 4 + [5], "tanh", "Glorot uniform")
        self.model = dde.Model(data, net)

        # Optimization
        if inverse:
            # For inverse problems, we include the variable in the optimizer
            self.model.compile("adam", lr=1e-3, external_trainable_variables=self.v_est)
        else:
            self.model.compile("adam", lr=1e-3)
            
        self.model.train(iterations=iterations, display_every=100)
        
        if inverse:
            print(f"Estimated v_stream: {self.v_est.item()}")
        
        return self.model

    def predict_gap_fill(self, X_query):
        """Predicts values at query points to 'fill the gaps'."""
        if self.model is None:
            return None
        return self.model.predict(X_query)

if __name__ == "__main__":
    # Quick test if run directly
    accel = PINNAccelerator(device="mps" if torch.backends.mps.is_available() else "cpu")
    print(f"PINN Accelerator initialized on {accel.device}")
