import numpy as np
import os
import deepxde as dde

from source.pinn_accelerator import parse_sparta_grid, pde_navier_stokes_2d

os.environ["DDE_BACKEND"] = "pytorch"

# 1. Load grid data
grid_file = "/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/CADDesign/results_reference/grid.1100.out"
X_data, Y_data = parse_sparta_grid(grid_file)

# 2. Scale calculations
u_max = np.max(np.abs(Y_data[:, 1])) if np.max(np.abs(Y_data[:, 1])) > 0 else 10000.0
v_max = np.max(np.abs(Y_data[:, 2])) if np.max(np.abs(Y_data[:, 2])) > 0 else 1000.0
u_scale = max(u_max, v_max)

domain_bounds = [-5.0, 9.0, 3.938]
scales = {
    "rho": np.max(Y_data[:, 0]) if np.max(Y_data[:, 0]) > 0 else 1e-5,
    "u": u_scale,
    "v": u_scale,
    "T": np.max(Y_data[:, 3]) if np.max(Y_data[:, 3]) > 0 else 5000.0,
    "p": np.max(Y_data[:, 4]) if np.max(Y_data[:, 4]) > 0 else 1000.0,
    "L": max(abs(domain_bounds[0]), abs(domain_bounds[1]), abs(domain_bounds[2]))
}

X_scaled = X_data / scales["L"]
Y_scaled = Y_data / np.array([scales["rho"], scales["u"], scales["v"], scales["T"], scales["p"]])
bounds_scaled = [domain_bounds[0]/scales["L"], domain_bounds[1]/scales["L"], domain_bounds[2]/scales["L"]]

# 3. Smart Sampling
p_vals = Y_data[:, 4]
T_vals = Y_data[:, 3]

high_val_idx = np.where((p_vals > 200.0) | (T_vals > 500.0))[0]

if len(high_val_idx) > 2500:
    high_val_idx = np.random.choice(high_val_idx, 2500, replace=False)
    
other_idx = np.setdiff1d(np.arange(len(X_scaled)), high_val_idx)
num_other = 5000 - len(high_val_idx)
other_idx = np.random.choice(other_idx, num_other, replace=False)

idx = np.concatenate([high_val_idx, other_idx])
X_anchors = X_scaled[idx]
Y_anchors = Y_scaled[idx]

# 4. Set up DeepXDE model
geom = dde.geometry.Rectangle([bounds_scaled[0], 0], [bounds_scaled[1], bounds_scaled[2]])

observe_y0 = dde.icbc.PointSetBC(X_anchors, Y_anchors[:, 0:1], component=0)
observe_y1 = dde.icbc.PointSetBC(X_anchors, Y_anchors[:, 1:2], component=1)
observe_y2 = dde.icbc.PointSetBC(X_anchors, Y_anchors[:, 2:3], component=2)
observe_y3 = dde.icbc.PointSetBC(X_anchors, Y_anchors[:, 3:4], component=3)
observe_y4 = dde.icbc.PointSetBC(X_anchors, Y_anchors[:, 4:5], component=4)

pde_fn = lambda x, y: pde_navier_stokes_2d(x, y, scales=scales)

data = dde.data.PDE(
    geom,
    pde_fn,
    [observe_y0, observe_y1, observe_y2, observe_y3, observe_y4],
    num_domain=2500,
    num_boundary=500,
    anchors=X_anchors
)

net = dde.nn.FNN([2] + [128] * 5 + [5], "tanh", "Glorot uniform")
model = dde.Model(data, net)

# 5. Train for 300 + 300 iterations for slightly better convergence
stage1_weights = [0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0]
model.compile("adam", lr=1e-3, loss_weights=stage1_weights)
model.train(iterations=300, display_every=100)

stage2_weights = [1e-4, 1e-4, 1e-4, 1e-4, 1e-4, 1.0, 1.0, 1.0, 1.0, 1.0]
model.compile("adam", lr=5e-4, loss_weights=stage2_weights)
model.train(iterations=300, display_every=100)

# 6. Query along stagnation line (y = 0.0) from x = -5.0 to 0.1
x_nose = np.linspace(-5.0, 0.1, 100)
q_pts = np.zeros((100, 2))
q_pts[:, 0] = x_nose
q_pts_scaled = q_pts / scales["L"]

preds_scaled = model.predict(q_pts_scaled)
preds = preds_scaled * np.array([scales["rho"], scales["u"], scales["v"], scales["T"], scales["p"]])

p_refined_max = np.max(preds[:, 4])
t_refined_max = np.max(preds[:, 3])

print("\nCenterline (y = 0.0) Refined Predictions:")
print(f"Max Refined Pressure along y=0: {p_refined_max:.1f} Pa")
print(f"Max Refined Temperature along y=0: {t_refined_max:.1f} K")

# Let's find the location of maximum pressure along y=0
max_idx = np.argmax(preds[:, 4])
print(f"Location of Max Refined Pressure along y=0: x = {x_nose[max_idx]:.4f} m")
