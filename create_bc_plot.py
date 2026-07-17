import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os

BG = '#0d1117'
TEXT = '#e6edf3'
SUBTEXT = '#8b949e'
ACCENT1 = '#4CC9F0' # Blue (Flow)
ACCENT2 = '#E63946' # Red (Heat)
ACCENT3 = '#2DC653' # Green (Solid)
ACCENT4 = '#FCA311' # Orange (Boundary)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7), facecolor=BG)
fig.patch.set_facecolor(BG)

# ==============================================================================
# SPARTA DSMC Boundary Conditions
# ==============================================================================
ax1.set_facecolor('#161b22')
ax1.set_xlim(-1, 9)
ax1.set_ylim(-1, 6)
ax1.axis('off')

# Domain box
domain_box = patches.Rectangle((0, 0), 8, 5, fill=False, edgecolor=SUBTEXT, linestyle='--', linewidth=1.5)
ax1.add_patch(domain_box)

# HIAD shape (simple curved line + straight lines)
# Stagnation at (3, 0), curves up to (2.5, 3)
theta = np.linspace(-np.pi/2, 0, 50)
x_hiad = 3.0 + 0.5 * np.cos(theta)
y_hiad = 0.5 + 0.5 * np.sin(theta)
# Add straight flank
x_hiad = np.concatenate((x_hiad, [1.5]))
y_hiad = np.concatenate((y_hiad, [3.5]))
# Add straight back
x_hiad = np.concatenate((x_hiad, [1.5, 3.0]))
y_hiad = np.concatenate((y_hiad, [0, 0]))

ax1.plot(x_hiad, y_hiad, color=ACCENT4, linewidth=4, zorder=5)
ax1.fill(x_hiad, y_hiad, color=ACCENT2, alpha=0.3, zorder=4)

# Left Boundary: Inflow
ax1.plot([0, 0], [0, 5], color=ACCENT1, linewidth=4)
ax1.text(-0.5, 2.5, "Inflow (xlo)\nemit/face\nv = 2700 m/s\nT = 250 K", 
         color=ACCENT1, fontsize=11, ha='right', va='center', fontweight='bold')
for y_arr in np.linspace(0.5, 4.5, 5):
    ax1.arrow(0.1, y_arr, 0.8, 0, head_width=0.2, head_length=0.2, fc=ACCENT1, ec=ACCENT1)

# Right Boundary: Outflow
ax1.plot([8, 8], [0, 5], color=SUBTEXT, linewidth=4)
ax1.text(8.5, 2.5, "Outflow (xhi)\nVacuum (o)", 
         color=SUBTEXT, fontsize=11, ha='left', va='center')
for y_arr in np.linspace(0.5, 4.5, 5):
    ax1.arrow(7.0, y_arr, 0.8, 0, head_width=0.2, head_length=0.2, fc=SUBTEXT, ec=SUBTEXT)

# Top Boundary: Outflow
ax1.plot([0, 8], [5, 5], color=SUBTEXT, linewidth=4)
ax1.text(4, 5.3, "Outflow (yhi)\nVacuum (o)", 
         color=SUBTEXT, fontsize=11, ha='center', va='bottom')

# Bottom Boundary: Axisymmetric
ax1.plot([0, 8], [0, 0], color=TEXT, linewidth=4, linestyle='-.')
ax1.text(4, -0.4, "Axisymmetric Centreline (ylo = 0)\nboundary 'a'", 
         color=TEXT, fontsize=11, ha='center', va='top', fontweight='bold')

# HIAD Surface BC
ax1.text(1.7, 4.0, "HIAD Surface\nDiffuse Isothermal Wall\n$T_{wall}$ = 1453 K\n(Captures $\dot{q}_{stag}$)", 
         color=ACCENT4, fontsize=11, ha='right', va='bottom', fontweight='bold')

ax1.set_title("1. SPARTA DSMC (External Aero / Gas Domain)", color=TEXT, fontsize=14, fontweight='bold', pad=20)


# ==============================================================================
# OpenFOAM laplacianFoam Boundary Conditions
# ==============================================================================
ax2.set_facecolor('#161b22')
ax2.set_xlim(-1, 9)
ax2.set_ylim(-1, 6)
ax2.axis('off')

# Zoomed in section of the F-TPS (solid)
# Draw a thick block representing the F-TPS
tps_x = [3, 7, 7, 3, 3]
tps_y = [1, 1, 4, 4, 1]

ax2.fill(tps_x, tps_y, color=ACCENT3, alpha=0.3, zorder=1)
ax2.plot([3, 3], [1, 4], color=ACCENT2, linewidth=5, zorder=2) # Outer surface
ax2.plot([7, 7], [1, 4], color=ACCENT1, linewidth=5, zorder=2) # Inner surface
ax2.plot([3, 7], [4, 4], color=SUBTEXT, linewidth=3, linestyle='--', zorder=2) # Top
ax2.plot([3, 7], [1, 1], color=SUBTEXT, linewidth=3, linestyle='--', zorder=2) # Bottom

# Annotations for OpenFOAM
ax2.text(2.6, 2.5, "Outer Surface (shield)\nfixedGradient\n$\\nabla T = \dot{q}_{stag} / k$", 
         color=ACCENT2, fontsize=11, ha='right', va='center', fontweight='bold')

ax2.text(7.4, 2.5, "Inner Backface (payload)\nzeroGradient\n(Adiabatic, worst-case T)", 
         color=ACCENT1, fontsize=11, ha='left', va='center', fontweight='bold')

ax2.text(5, 4.3, "Edges (.*)\nzeroGradient", 
         color=SUBTEXT, fontsize=11, ha='center', va='bottom')

# Internal equation
ax2.text(5, 2.5, "Solid Conduction\n$\\frac{\partial T}{\partial t} = D_T \\nabla^2 T$\n\nMulti-layer F-TPS\n(SiC + Pyrogel + Kapton)", 
         color=TEXT, fontsize=11, ha='center', va='center', bbox=dict(facecolor=BG, edgecolor=ACCENT3, boxstyle='round,pad=0.5'))

ax2.set_title("2. OpenFOAM (Internal Heat Conduction / Solid Domain)", color=TEXT, fontsize=14, fontweight='bold', pad=20)

plt.suptitle("Sequential Hybrid Pipeline: Boundary Condition Definitions", color=TEXT, fontsize=18, fontweight='bold', y=0.95)

out_dir = "ProgressReport/Week 10/figures/Result"
os.makedirs(out_dir, exist_ok=True)
plt.savefig(os.path.join(out_dir, "boundary_conditions.jpeg"), dpi=150, format='jpeg', bbox_inches='tight', facecolor=BG)
print("Saved JPEG")
