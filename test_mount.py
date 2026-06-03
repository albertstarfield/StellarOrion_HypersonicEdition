import numpy as np
import matplotlib.pyplot as plt

R_start = 3782.0
payload_radius = 2510.0
z_last_outer = 600.0
z_orion = z_last_outer + 200.0

rs = []
zs = []

# Smooth W-shape mounting (2 ties)
n_pts = 50
for t in np.linspace(0, 1, n_pts):
    # t=0 -> Orion (payload_radius), t=1 -> HIAD edge (R_start)
    # We want to trace from HIAD edge down to Orion, so we go from t=1 down to t=0
    pass

for t in np.linspace(1, 0, n_pts):
    curr_r = payload_radius + t * (R_start - payload_radius)
    # Base Z line
    curr_z_base = z_orion + t * (z_last_outer - z_orion)
    
    # Add two ties (bulges in +Z direction)
    # 1 - cos(4 * pi * t) creates two bumps.
    # To make them look like distinct diagonal struts, let's make the bumps 400mm deep.
    bulge = 400.0 * (1.0 - np.cos(4 * np.pi * t)) / 2.0
    
    curr_z = curr_z_base + bulge
    rs.append(curr_r)
    zs.append(curr_z)

plt.figure(figsize=(8,4))
plt.plot(zs, rs, 'b-o', markersize=2)
plt.title("2 Ties Anchor Mounting (Blunt/Rounded)")
plt.xlabel("Z (mm)")
plt.ylabel("R (mm)")
plt.grid()
plt.savefig("test_mount.png")
