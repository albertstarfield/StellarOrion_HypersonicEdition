import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_orion(ax, z_offset=0.0, flip=False):
    # Orion geometry: base at z=0, tapers to z=3.3
    # Base radius = 2.51, top radius = 1.0
    z_base = z_offset
    z_top = z_offset + 3.3 if not flip else z_offset - 3.3
    
    # Heat shield (blunt)
    theta = np.linspace(-np.pi/2, np.pi/2, 50)
    # Shallow curve for heat shield
    hs_z = z_base - 0.2 * np.cos(theta) if not flip else z_base + 0.2 * np.cos(theta)
    hs_r = 2.51 * np.sin(theta)
    
    # Backshell
    bs_z = [hs_z[-1], z_top, z_top, hs_z[0]]
    bs_r = [hs_r[-1], 1.0, -1.0, hs_r[0]]
    
    ax.plot(hs_z, hs_r, 'k-', linewidth=2)
    ax.plot(bs_z, bs_r, 'k-', linewidth=2)
    ax.fill(hs_z, hs_r, color='#e2e8f0')
    ax.fill(bs_z, bs_r, color='#cbd5e1')
    ax.text(z_base + (1.5 if not flip else -1.5), 0, 'ORION\nCAPSULE', 
            ha='center', va='center', fontweight='bold', color='#475569')

def draw_deployed_hiad(ax, z_offset=0.0):
    # Deployed HIAD: 60 degree cone to R=3.78
    r_deployed = np.linspace(0, 3.78, 50)
    z_deployed = z_offset + r_deployed / np.tan(np.radians(60))
    ax.plot(z_deployed, r_deployed, 'r--', linewidth=2, alpha=0.7, label='Deployed HIAD (7.5m)')
    ax.plot(z_deployed, -r_deployed, 'r--', linewidth=2, alpha=0.7)

fig, axs = plt.subplots(3, 1, figsize=(10, 15))

# 1. Annular Skirt Stowage
ax = axs[0]
draw_orion(ax)
# Stowed volume: packed around the shoulder
stowed_z = [0, 0.5, 0.5, 0]
stowed_r = [2.3, 2.3, 2.9, 2.9]
ax.add_patch(patches.Rectangle((0, 2.3), 0.6, 0.6, linewidth=1, edgecolor='b', facecolor='#3b82f6', alpha=0.8, label='Stowed HIAD Volume'))
ax.add_patch(patches.Rectangle((0, -2.9), 0.6, 0.6, linewidth=1, edgecolor='b', facecolor='#3b82f6', alpha=0.8))
draw_deployed_hiad(ax)
ax.set_title('1. Annular Skirt Stowage (Radial Wrap)', fontsize=14, fontweight='bold')
ax.set_xlim(-1, 5)
ax.set_ylim(-4, 4)
ax.set_aspect('equal')
ax.legend(loc='upper right')
ax.grid(True, linestyle='--', alpha=0.5)

# 2. Jettisonable Forward Bay Module
ax = axs[1]
# For this concept, HIAD is on the narrow docking port. To fly blunt-forward, Orion flips.
# Let's draw Orion flying 'backwards' (docking port forward) to dock with the module
draw_orion(ax, z_offset=3.3, flip=True)
# Module is a cylinder at Z < 0
ax.add_patch(patches.Rectangle((-1.0, -1.2), 1.0, 2.4, linewidth=1, edgecolor='b', facecolor='#3b82f6', alpha=0.8, label='Stowed HIAD Module'))
draw_deployed_hiad(ax, z_offset=-1.0)
ax.set_title('2. Jettisonable Forward Bay Module (Docking Port Mount)', fontsize=14, fontweight='bold')
ax.set_xlim(-2, 5)
ax.set_ylim(-4, 4)
ax.set_aspect('equal')
ax.legend(loc='upper right')
ax.grid(True, linestyle='--', alpha=0.5)

# 3. Drop-In False Bottom
ax = axs[2]
draw_orion(ax)
# False bottom covers the entire heat shield, tightly packed
ax.add_patch(patches.Rectangle((-0.4, -2.51), 0.4, 5.02, linewidth=1, edgecolor='b', facecolor='#3b82f6', alpha=0.8, label='Stowed HIAD Pan'))
draw_deployed_hiad(ax, z_offset=-0.4)
ax.set_title('3. "Drop-In" False Bottom (Heat Shield Overlay)', fontsize=14, fontweight='bold')
ax.set_xlim(-1, 5)
ax.set_ylim(-4, 4)
ax.set_aspect('equal')
ax.legend(loc='upper right')
ax.grid(True, linestyle='--', alpha=0.5)

plt.tight_layout()
plt.savefig('/Users/albertstarfield/.gemini/antigravity-cli/brain/77b60d0c-74f8-4cfd-aa8e-67752de71148/stowage_concepts.png', dpi=150)
print('Plot saved successfully.')
