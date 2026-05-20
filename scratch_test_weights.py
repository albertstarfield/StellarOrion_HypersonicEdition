import torch
import deepxde as dde
import os

os.environ["DDE_BACKEND"] = "pytorch"

geom = dde.geometry.Rectangle([-1, -1], [1, 1])
pde_fn = lambda x, y: [y]
dummy_data = dde.data.PDE(geom, pde_fn, [], num_domain=100)
net = dde.nn.FNN([2] + [128] * 5 + [5], "tanh", "Glorot uniform")
model = dde.Model(dummy_data, net)

# Save initial weights
w_before = {k: v.clone() for k, v in model.net.state_dict().items()}

# Compile model
model.compile("adam", lr=1e-3)

# Check if weights changed
w_after = model.net.state_dict()
changed = False
for k in w_before:
    if not torch.equal(w_before[k], w_after[k]):
        changed = True
        break

print("Did compile reset weights?", changed)
