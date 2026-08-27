import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def plot_irve3_validation_mesh():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, base_dir)

    print("================================================================================")
    print("      GENERATING HIGH-RESOLUTION IRVE-3 VALIDATION MESH PLOT")
    print("================================================================================")

    from CADDesign import HIAD_GeometryEngine
    import math

    d_m = 3.0
    angle = 60.0
    nose_radius_m = 0.55
    toroid_count = 6
    toroid_radius_m = 0.135
    shoulder_radius_m = 0.0508

    # Generate exact 6-toroid skin profile
    _, raw_skin_pts = HIAD_GeometryEngine.generate_hiad(
        diameter_m=d_m,
        angle=angle,
        nose_radius=nose_radius_m,
        toroid_count=toroid_count,
        toroid_radius=toroid_radius_m,
        shoulder_torus_radius=shoulder_radius_m,
        payload=True,
        payload_height=1700.0,
        payload_radius=500.0,
        payload_type='cylinder',
        debug_image=False,
        slice_angle=0
    )

    skin_pts_m = [(p[0]/1000.0, p[1]/1000.0) for p in raw_skin_pts]
    z_pts = np.array([p[0] for p in skin_pts_m])
    r_pts = np.array([p[1] for p in skin_pts_m])

    # Setup Plot Figure
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7), facecolor='#0B0F19')
    
    for ax in (ax1, ax2):
        ax.set_facecolor('#0F172A')
        ax.grid(True, color='#334155', linestyle='--', linewidth=0.5, alpha=0.6)
        ax.tick_params(colors='#94A3B8', labelsize=10)
        for spine in ax.spines.values():
            spine.set_color('#334155')

    # --- PANEL 1: Full Computational Domain Mesh ---
    x_min, x_max = -5.0, 9.0
    y_min, y_max = -4.0, 4.0
    
    # Coarse & Refined Grid lines
    x_grid = np.linspace(x_min, x_max, 141)
    y_grid = np.linspace(y_min, y_max, 81)

    for x in x_grid[::2]:
        ax1.axvline(x, color='#0EA5E9', linestyle='-', linewidth=0.25, alpha=0.3)
    for y in y_grid[::2]:
        ax1.axhline(y, color='#0EA5E9', linestyle='-', linewidth=0.25, alpha=0.3)

    # Dense shock refinement box
    for x in np.linspace(-1.0, 3.0, 81):
        ax1.axvline(x, color='#38BDF8', linestyle='-', linewidth=0.4, alpha=0.45)
    for y in np.linspace(-2.2, 2.2, 81):
        ax1.axhline(y, color='#38BDF8', linestyle='-', linewidth=0.4, alpha=0.45)

    # Plot vehicle profile (upper & lower mirrored)
    ax1.plot(z_pts, r_pts, color='#EC4899', linewidth=2.5, label='IRVE-3 6-Toroid Skin')
    ax1.plot(z_pts, -r_pts, color='#EC4899', linewidth=2.5)

    # Fill solid body interior
    ax1.fill_between(z_pts, -r_pts, r_pts, color='#020617', alpha=0.9, zorder=10)

    # Label toroids
    theta_rad = math.radians(angle)
    r_tang = nose_radius_m * math.cos(theta_rad)
    z_tang = nose_radius_m * (1.0 - math.sin(theta_rad))

    for i in range(toroid_count):
        center_dist = r_tang + (i + 0.5) * (2.0 * toroid_radius_m) * math.sin(theta_rad)
        cz = z_tang + (i + 0.5) * (2.0 * toroid_radius_m) * math.cos(theta_rad)
        cr = center_dist
        ax1.plot(cz, cr, 'o', color='#F59E0B', markersize=4, zorder=20)
        ax1.plot(cz, -cr, 'o', color='#F59E0B', markersize=4, zorder=20)
        ax1.text(cz + 0.1, cr + 0.08, f'T{i+1}', color='#F59E0B', fontweight='bold', fontsize=8, zorder=25)

    ax1.set_title('SPARTA 2D Axisymmetric Mesh Domain (Full Bounds)', color='white', fontsize=13, fontweight='bold', pad=12)
    ax1.set_xlabel('Axial Position X (m)', color='#94A3B8', fontsize=11)
    ax1.set_ylabel('Radial Position Y (m)', color='#94A3B8', fontsize=11)
    ax1.set_xlim(x_min, x_max)
    ax1.set_ylim(y_min, y_max)
    ax1.set_aspect('equal')

    # --- PANEL 2: High-Resolution Close-Up Mesh (6 Toroids Face) ---
    for x in np.linspace(-0.2, 1.8, 81):
        ax2.axvline(x, color='#38BDF8', linestyle='-', linewidth=0.4, alpha=0.5)
    for y in np.linspace(-1.8, 1.8, 81):
        ax2.axhline(y, color='#38BDF8', linestyle='-', linewidth=0.4, alpha=0.5)

    # Draw individual toroid circles
    for i in range(toroid_count):
        center_dist = r_tang + (i + 0.5) * (2.0 * toroid_radius_m) * math.sin(theta_rad)
        cz = z_tang + (i + 0.5) * (2.0 * toroid_radius_m) * math.cos(theta_rad)
        cr = center_dist

        # Toroid circle patches
        c_top = patches.Circle((cz, cr), toroid_radius_m, edgecolor='#F59E0B', facecolor='#F59E0B', alpha=0.2, linewidth=1.5, zorder=12)
        c_bot = patches.Circle((cz, -cr), toroid_radius_m, edgecolor='#F59E0B', facecolor='#F59E0B', alpha=0.2, linewidth=1.5, zorder=12)
        ax2.add_patch(c_top)
        ax2.add_patch(c_bot)

        ax2.text(cz, cr, f'T{i+1}', color='white', fontweight='bold', fontsize=9, ha='center', va='center', zorder=25)
        ax2.text(cz, -cr, f'T{i+1}', color='white', fontweight='bold', fontsize=9, ha='center', va='center', zorder=25)

    ax2.plot(z_pts, r_pts, color='#EC4899', linewidth=3.0, label='Scalloped F-TPS Fabric')
    ax2.plot(z_pts, -r_pts, color='#EC4899', linewidth=3.0)
    ax2.fill_between(z_pts, -r_pts, r_pts, color='#020617', alpha=0.95, zorder=10)

    # Highlight Nose Cap
    ax2.plot(z_pts[:30], r_pts[:30], color='#10B981', linewidth=3.5, label='Nose Cap (Rn=0.55m)')
    ax2.plot(z_pts[:30], -r_pts[:30], color='#10B981', linewidth=3.5)

    ax2.set_title('High-Resolution Zoom: 6-Toroid Scalloped Mesh Surface', color='white', fontsize=13, fontweight='bold', pad=12)
    ax2.set_xlabel('Axial Position X (m)', color='#94A3B8', fontsize=11)
    ax2.set_ylabel('Radial Position Y (m)', color='#94A3B8', fontsize=11)
    ax2.set_xlim(-0.2, 1.8)
    ax2.set_ylim(-1.8, 1.8)
    ax2.set_aspect('equal')
    ax2.legend(facecolor='#0F172A', edgecolor='#334155', labelcolor='white', loc='upper left', fontsize=9)

    plt.tight_layout()
    out_png = "validation_mesh_detailed.png"
    plt.savefig(out_png, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.savefig(os.path.join(base_dir, "web", "assets", "plots", "validation_mesh_detailed.png"), dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
    print(f"[+] Saved high-res validation mesh plot to: {out_png}")

if __name__ == '__main__':
    plot_irve3_validation_mesh()
