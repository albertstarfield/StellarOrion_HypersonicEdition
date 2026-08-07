import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def generate_flight_vs_sim_plot():
    BG = '#0f172a'
    TEXT = '#f8fafc'
    SUBTEXT = '#94a3b8'
    ACCENT1 = '#38bdf8' # Cyan (Flow)
    ACCENT2 = '#f43f5e' # Red (Scalloped Shell)
    ACCENT3 = '#22c55e' # Green (Solid/Payload)
    ACCENT4 = '#fbbf24' # Amber (BCs)

    plt.style.use('dark_background')
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8), facecolor=BG)

    for ax in [ax1, ax2]:
        ax.set_facecolor('#1e293b')
        ax.grid(True, linestyle='--', alpha=0.3, color='#334155')
        ax.tick_params(colors=TEXT, labelsize=10)
        for spine in ax.spines.values():
            spine.set_color('#475569')

    # ==============================================================================
    # PANEL 1: FLIGHT CONDITION ORIENTATION (Physical Geometry in Z-R Frame)
    # ==============================================================================
    # Geometry parameters
    r_nose = 250
    t_count = 6
    r_torus = 100
    theta_c = np.radians(60)

    # Generate synthetic analytical HIAD slice matching user image
    # Nose sphere
    beta = np.linspace(-np.pi/2, np.pi/2, 50)
    z_nose = r_nose * (1 - np.cos(beta))
    r_nose_pts = r_nose * np.sin(beta)

    # The cone generator is at 30 deg from horizontal (R-axis). 
    # Therefore, tangency point on the nose sphere is exactly at beta = 30 deg (pi/6).
    tangency_beta = np.pi/6
    beta_half = beta[25:]
    tangency_idx = np.argmin(np.abs(beta_half - tangency_beta))

    # [FIX]: Stop the nose shell exactly at the tangency point instead of drawing 
    # it all the way to 90 degrees (which caused it to overlap Toroid 1).
    z_shell = list(z_nose[25: 25 + tangency_idx + 1])
    r_shell = list(r_nose_pts[25: 25 + tangency_idx + 1])

    # [FIX]: Generate 6 toroids starting AT the tangency point, not at the nose tip (0,0).
    r_curr = r_shell[-1]
    z_curr = z_shell[-1]

    for i in range(1, t_count + 1):
        # [FIX]: Shift the toroid center INWARD from the tangency point. 
        # The inward normal points UP and LEFT (120 deg from R-axis, or 30 deg from Z-axis).
        cx = r_curr - r_torus * np.sin(np.pi/6)
        cz = z_curr + r_torus * np.cos(np.pi/6)
        
        # Circle for torus
        angles = np.linspace(0, 2*np.pi, 40)
        ax1.plot(cx + r_torus*np.cos(angles), cz + r_torus*np.sin(angles), color='#818cf8', alpha=0.4, linewidth=1.2)
        ax1.plot(-cx + r_torus*np.cos(angles), cz + r_torus*np.sin(angles), color='#818cf8', alpha=0.4, linewidth=1.2)
        ax1.text(cx, cz, str(i), color='#818cf8', fontsize=9, fontweight='bold', ha='center', va='center')
        ax1.text(-cx, cz, str(i), color='#818cf8', fontsize=9, fontweight='bold', ha='center', va='center')

        # Wavy shell curve over torus (scalloped F-TPS)
        # The toroid normal facing outward is theta_c - 90 deg (since it's placed outwards)
        outward_normal = theta_c - np.pi/2
        scallop_half_angle = np.radians(20)
        arc_angles = np.linspace(outward_normal - scallop_half_angle, outward_normal + scallop_half_angle, 15)
        
        arc_r = cx + r_torus * np.cos(arc_angles)
        arc_z = cz + r_torus * np.sin(arc_angles)
        z_shell.extend(arc_z)
        r_shell.extend(arc_r)

        # Move to next tangency point (along the cone generator)
        r_curr += 1.6 * r_torus * np.sin(theta_c)
        z_curr += 1.6 * r_torus * np.cos(theta_c)

    # Add Shoulder Toroid (N+1)
    r_torus_shoulder = 75 # slightly smaller
    cx_sh = r_curr - r_torus_shoulder * np.sin(np.pi/6)
    cz_sh = z_curr + r_torus_shoulder * np.cos(np.pi/6)
    
    # Circle for shoulder torus
    angles = np.linspace(0, 2*np.pi, 40)
    ax1.plot(cx_sh + r_torus_shoulder*np.cos(angles), cz_sh + r_torus_shoulder*np.sin(angles), color='#818cf8', alpha=0.4, linewidth=1.2)
    ax1.plot(-cx_sh + r_torus_shoulder*np.cos(angles), cz_sh + r_torus_shoulder*np.sin(angles), color='#818cf8', alpha=0.4, linewidth=1.2)
    ax1.text(cx_sh, cz_sh, "7 (S)", color='#818cf8', fontsize=8, fontweight='bold', ha='center', va='center')
    ax1.text(-cx_sh, cz_sh, "7 (S)", color='#818cf8', fontsize=8, fontweight='bold', ha='center', va='center')

    # Scallop for shoulder torus
    arc_r_sh = cx_sh + r_torus_shoulder * np.cos(arc_angles)
    arc_z_sh = cz_sh + r_torus_shoulder * np.sin(arc_angles)
    z_shell.extend(arc_z_sh)
    r_shell.extend(arc_r_sh)

    z_shell = np.array(z_shell)
    r_shell = np.array(r_shell)

    # Plot windward shell
    ax1.plot(r_shell, z_shell, color=ACCENT2, linewidth=3, label='Scalloped SPARTA Shell')
    ax1.plot(-r_shell, z_shell, color=ACCENT2, linewidth=3)

    import matplotlib.path as mpath
    Path = mpath.Path
    
    # 0. Blue flat disc (between nose shell and r_tank)
    disc = patches.Rectangle((-150, 100), 300, 40, fill=True, facecolor=ACCENT3, alpha=0.35, edgecolor=ACCENT3, linewidth=2)
    ax1.add_patch(disc)

    # 1. r_tank (Gray Circle at the center of the nose sphere Z=250)
    r_tank_radius = 80
    tank_circle = patches.Circle((0, 250), r_tank_radius, fill=True, facecolor='#94a3b8', alpha=0.8, edgecolor='#475569', linewidth=2, zorder=5)
    ax1.add_patch(tank_circle)
    ax1.text(0, 250, "r_tank", color='#0f172a', fontsize=9, ha='center', va='center', fontweight='bold', zorder=6)

    # 2. Payload Main Body (Starts at Z=250, behind the tank)
    r_pay = 200
    h_pay = 500
    z_base = 250
    top_rad = 50
    kappa = 0.55 * top_rad
    
    verts = [
        (-r_pay, z_base),
        (-r_pay, z_base + h_pay - top_rad),
        (-r_pay, z_base + h_pay - top_rad + kappa),
        (-r_pay + top_rad - kappa, z_base + h_pay),
        (-r_pay + top_rad, z_base + h_pay),
        (r_pay - top_rad, z_base + h_pay),
        (r_pay - top_rad + kappa, z_base + h_pay),
        (r_pay, z_base + h_pay - top_rad + kappa),
        (r_pay, z_base + h_pay - top_rad),
        (r_pay, z_base),
        (0, 0)
    ]
    codes = [
        Path.MOVETO,
        Path.LINETO,
        Path.CURVE4, Path.CURVE4, Path.CURVE4,
        Path.LINETO,
        Path.CURVE4, Path.CURVE4, Path.CURVE4,
        Path.LINETO,
        Path.CLOSEPOLY
    ]
    path = Path(verts, codes)
    pay_patch = patches.PathPatch(path, fill=True, facecolor=ACCENT3, alpha=0.25, edgecolor=ACCENT3, linewidth=2, zorder=4)
    ax1.add_patch(pay_patch)
    ax1.text(0, 500, "Payload Container\n(Centerbody)\nr_pay, h_pay", color=ACCENT3, fontsize=11, ha='center', va='center', fontweight='bold', zorder=6)

    # Incoming Flow Arrow
    ax1.arrow(0, -150, 0, 100, head_width=50, head_length=40, fc=ACCENT1, ec=ACCENT1, linewidth=3)
    ax1.text(0, -200, "Hypersonic Freestream Flow Direction (+Z)\n(Flight Angle of Attack α = 0°)", 
             color=ACCENT1, fontsize=11, ha='center', va='top', fontweight='bold')

    ax1.set_title("1. Physical Flight Condition Frame (R vs Z Physical Geometry)", color=TEXT, fontsize=13, fontweight='bold', pad=12)
    ax1.set_xlabel("Radius R [mm]", color=TEXT, fontsize=10)
    ax1.set_ylabel("Z Height (Axial Length) [mm]", color=TEXT, fontsize=10)
    ax1.set_xlim(-1600, 1600)
    ax1.set_ylim(-250, 1000)
    ax1.legend(facecolor='#0f172a', edgecolor='#475569', labelcolor=TEXT, loc='upper right')

    # ==============================================================================
    # PANEL 2: SPARTA 2D AXISYMMETRIC SIMULATION DOMAIN MAPPING
    # ==============================================================================
    # Why this mapping is critical: In physical flight, the vehicle travels 
    # downward into the atmosphere (often modeled as Z-axis). 
    # However, SPARTA DSMC specifically requires 2D axisymmetric flow to come 
    # from the 'xlo' boundary (X=0) moving in the +X direction. 
    # Therefore, we MUST orient the vehicle so the nose points LEFT.
    # We map coordinates: X_sim = Z_flight, Y_sim = R_flight
    # Flow moves along +X axis from Xlo to Xhi. Centerline is Ylo = 0.
    
    # Map coordinates: X_sim = Z_shell, Y_sim = R_shell
    x_sim = z_shell
    y_sim = r_shell

    ax2.plot(x_sim, y_sim, color=ACCENT2, linewidth=3, label='Scalloped Wall BC (Isothermal 1000K)')
    
    # Simulation Domain Boundary Box
    domain_box = patches.Rectangle((-150, 0), 1150, 1500, fill=False, edgecolor='#64748b', linestyle='--', linewidth=2)
    ax2.add_patch(domain_box)

    # Inflow Boundary (xlo)
    ax2.plot([-150, -150], [0, 1500], color=ACCENT1, linewidth=4)
    ax2.text(-170, 750, "Inflow (xlo emit/face)\nv = 2700 m/s, T = 270 K\nFreestream Air (N2, O2)", 
             color=ACCENT1, fontsize=10, ha='right', va='center', fontweight='bold')
    for y_in in [300, 750, 1200]:
        ax2.arrow(-140, y_in, 100, 0, head_width=40, head_length=30, fc=ACCENT1, ec=ACCENT1)

    # Axisymmetric Centerline (ylo = 0)
    ax2.plot([-150, 1000], [0, 0], color='#f43f5e', linewidth=3, linestyle='-.')
    ax2.text(425, -70, "Axisymmetric Centerline (ylo = 0, boundary 'a')", 
             color='#f43f5e', fontsize=10, ha='center', va='top', fontweight='bold')

    # Outflow Boundaries (xhi & yhi)
    ax2.plot([1000, 1000], [0, 1500], color=SUBTEXT, linewidth=3)
    ax2.text(1020, 750, "Outflow (xhi)\nVacuum Boundary (o)", color=SUBTEXT, fontsize=10, ha='left', va='center')

    ax2.plot([-150, 1000], [1500, 1500], color=SUBTEXT, linewidth=3)
    ax2.text(425, 1530, "Outflow (yhi) Vacuum Boundary (o)", color=SUBTEXT, fontsize=10, ha='center', va='bottom')

    ax2.set_title("2. SPARTA 2D Axisymmetric Solver Frame (Mapped X_sim vs Y_sim)", color=TEXT, fontsize=13, fontweight='bold', pad=12)
    ax2.set_xlabel("X_sim (Axial Position along Flow) [mm]", color=TEXT, fontsize=10)
    ax2.set_ylabel("Y_sim (Radial Distance R from Axis) [mm]", color=TEXT, fontsize=10)
    ax2.set_xlim(-400, 1300)
    ax2.set_ylim(-150, 1700)
    ax2.legend(facecolor='#0f172a', edgecolor='#475569', labelcolor=TEXT, loc='upper left')

    plt.suptitle("Flight Condition vs. SPARTA 2D Axisymmetric Simulation Boundary Mapping",
                 color=TEXT, fontsize=15, fontweight='bold', y=0.98)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    
    out_img = "flight_vs_simulation_bc_comparison.png"
    plt.savefig(out_img, dpi=200, facecolor=BG, edgecolor='none')
    print(f"[+] Saved comparison plot: {out_img}")

if __name__ == '__main__':
    generate_flight_vs_sim_plot()
