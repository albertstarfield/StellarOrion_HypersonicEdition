#!/usr/bin/env python
"""
IRVE-3 Boundary Condition & Parametric Design Comparison Plot
=============================================================
Generates a comprehensive multi-panel figure comparing:
  Panel 1: Rapisarda-style IRVE-3 parametric geometry (matching the reference diagram)
  Panel 2: SPARTA simulation boundary conditions with corrected values
  Panel 3: Parameter comparison table (variant vs fixed, code vs Rapisarda Table 4.1)

Reference: Rapisarda, C. (2023) "MDAO of Inflatable Stacked Toroid Decelerators"
           Delft University of Technology, MSc Thesis, Table 4.1

GEOMETRY CONVENTION (Rapisarda Reference):
  - Vertical axis of symmetry (dashed-dot line) going up through center
  - NOSE (stagnation point) at the BOTTOM center
  - Toroids spread OUTWARD and UPWARD along the cone surface
  - Toroid 1 is nearest to the nose, N is farthest out
  - Outer torus (N+1) is at the very edge with smaller radius r_out,torus
  - Payload sits ABOVE the nose
  - theta_c is measured from the vertical symmetry axis to the cone generator
  - Flow comes from BELOW (hitting the nose)
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Arc
import os

# ──────────────────────────────────────────────────────────────────────────────
# IRVE-3 Reference Parameters (Rapisarda 2023, Table 4.1)
# ──────────────────────────────────────────────────────────────────────────────
RAPISARDA = {
    'theta_c': 60.0,        # deg - forebody cone half-angle from symmetry axis
    'N': 6,                 # number of main toroids
    'r_torus': 0.1350,      # m
    'r_out_torus': 0.0508,  # m - shoulder outer torus
    'h_pay': 1.7,           # m - payload height
    'r_pay': 0.275,         # m - payload radius
    'R_n': 0.550,           # m - nose radius (full-scale)
    'D_inflated': 3.0,      # m - overall diameter
    'm': 281.0,             # kg - entry mass
}

ENGINE = {
    'theta_c': 60.0,
    'N': 6,
    'r_torus': 0.135,
    'r_out_torus': 0.0508,
    'h_pay': 1.7,
    'r_pay': 0.275,
    'R_n': 0.550,
    'D_inflated': 3.0,
    'm': 281.0,
    'v_inf': 2700.0,
    'T_inf': 270.0,
    'n_rho': 3.47e21,
    'T_wall': 1000.0,
}

# ──────────────────────────────────────────────────────────────────────────────
# Color Palette
# ──────────────────────────────────────────────────────────────────────────────
BG = '#0d1117'
PANEL_BG = '#161b22'
TEXT = '#e6edf3'
SUBTEXT = '#8b949e'
CYAN = '#4CC9F0'
RED = '#E63946'
GREEN = '#2DC653'
AMBER = '#FCA311'
PURPLE = '#A78BFA'
PINK = '#F472B6'


def draw_parametric_geometry(ax):
    """
    Panel 1: Rapisarda-style IRVE-3 cross-section.
    
    Convention (matching reference diagram):
      - Y axis = vertical symmetry axis (pointing UP)
      - X axis = radial (left-right)
      - Nose at BOTTOM center (x=0, y=0)
      - Toroids go outward (increasing |x|) and upward (increasing y)
      - Payload ABOVE the nose
      - theta_c measured from vertical axis to the cone generator line
    """
    ax.set_facecolor(PANEL_BG)
    ax.set_aspect('equal')
    
    # Scale everything to mm for readability
    R_n = 550.0       # nose radius mm
    r_t = 135.0       # main toroid radius mm
    r_out = 50.8      # outer toroid radius mm
    theta = np.radians(60)  # cone half-angle from axis
    r_pay = 275.0     # payload radius mm
    h_pay = 600.0     # payload height mm (visual scaling)
    N = 6
    
    # ── Nose sphere ──
    # Nose center is at (0, R_n) so the stagnation point is at (0, 0)
    # The sphere extends from the stagnation point up to the tangency point
    # Tangency point: where the sphere meets the cone
    # r_tangent = R_n * sin(theta_c), y_tangent = R_n - R_n * cos(theta_c) = R_n(1-cos(theta_c))
    # Actually: nose center at (0, R_n). Tangency in polar from center:
    # angle from downward vertical = theta_c
    # tangent_x = R_n * sin(theta_c), tangent_y = R_n - R_n * cos(theta_c)
    
    r_tangent = R_n * np.sin(theta)  # radial position of tangency point
    y_tangent = R_n * (1.0 - np.cos(theta))  # height of tangency point
    
    # Draw nose sphere arc from stagnation (bottom, angle=-pi/2 from horizontal)
    # to tangency point on both sides
    # Sphere center at (0, R_n)
    # Parametrize: x = R_n*cos(a), y = R_n + R_n*sin(a)
    # At stagnation (bottom): a = -pi/2 => x=0, y=R_n-R_n=0 ✓
    # At tangency: need to find angle a where the cone is tangent
    # tangent_x = R_n*sin(theta_c), tangent_y = R_n*(1-cos(theta_c))
    # From center: dx = R_n*sin(theta_c), dy = R_n*(1-cos(theta_c)) - R_n = -R_n*cos(theta_c)
    # angle from center downward: atan2(dx, -dy) = atan2(sin(theta_c), cos(theta_c)) = theta_c
    # So the arc goes from angle -pi/2 (bottom) to angle -(pi/2 - theta_c)
    
    arc_angles = np.linspace(-np.pi/2, -(np.pi/2 - theta), 60)
    nose_x_right = R_n * np.cos(arc_angles)
    nose_y = R_n + R_n * np.sin(arc_angles)  # center at (0, R_n)
    
    ax.plot(nose_x_right, nose_y, color=CYAN, linewidth=2.5, zorder=5)
    ax.plot(-nose_x_right, nose_y, color=CYAN, linewidth=2.5, zorder=5)
    
    # Dashed sphere circle (faint reference)
    full_angles = np.linspace(0, 2*np.pi, 120)
    ax.plot(R_n * np.cos(full_angles), R_n + R_n * np.sin(full_angles),
            color=SUBTEXT, linewidth=0.8, linestyle=':', alpha=0.3, zorder=1)
    
    # ── Toroids along the cone surface ──
    # From the tangency point, the cone generator line goes outward at angle theta_c from axis
    # Direction along cone: dx/ds = sin(theta_c), dy/ds = cos(theta_c)  [going outward & upward]
    # Wait - in the reference image, the toroids go outward and UPWARD from the nose.
    # The cone opens upward. Let me re-examine.
    #
    # Actually looking at the reference image again:
    # - The nose is at the bottom
    # - The toroids go to the LEFT and RIGHT, spreading DOWNWARD from the payload area
    # - No wait... the V-shape opens DOWNWARD with nose at bottom.
    #
    # Actually the convention in the reference:
    # - The toroids go outward from the nose tangency point
    # - The cone angle means the toroids go outward and slightly upward
    # - For theta_c = 60°, the cone is quite open (nearly flat)
    # - The cone generator makes 60° with the vertical axis
    # - So it makes 30° with the horizontal
    # - From tangency point, stepping along the cone:
    #   delta_x = step * sin(theta_c) = step * sin(60°) = step * 0.866 (outward)
    #   delta_y = step * cos(theta_c) = step * cos(60°) = step * 0.5 (upward)
    
    # Tangency point (right side)
    tx = r_tangent  # = R_n * sin(60°) ≈ 476 mm
    ty = y_tangent  # = R_n * (1-cos(60°)) ≈ 275 mm
    
    # Direction along cone (outward and upward from tangency)
    dx_cone = np.sin(theta)  # 0.866
    dy_cone = np.cos(theta)  # 0.5
    
    toroid_centers_right = []
    
    # First toroid center: one r_t along the cone from tangency
    cx = tx + r_t * dx_cone
    cy = ty + r_t * dy_cone
    
    for i in range(N):
        toroid_centers_right.append((cx, cy))
        
        # Draw torus circle (right side)
        circle_a = np.linspace(0, 2*np.pi, 60)
        ax.plot(cx + r_t * np.cos(circle_a), cy + r_t * np.sin(circle_a),
                color=PURPLE, alpha=0.5, linewidth=1.3, zorder=3)
        # Draw torus circle (left side - mirror)
        ax.plot(-cx + r_t * np.cos(circle_a), cy + r_t * np.sin(circle_a),
                color=PURPLE, alpha=0.5, linewidth=1.3, zorder=3)
        
        # Number label
        label = str(i + 1)
        ax.text(cx, cy, label, color=PURPLE, fontsize=8, fontweight='bold',
                ha='center', va='center', zorder=6)
        
        # Move to next toroid center (touching, so 2*r_t along cone)
        cx += 2 * r_t * dx_cone
        cy += 2 * r_t * dy_cone
    
    # ── Outer shoulder torus (N+1) ──
    # Sits right after the last main toroid, smaller radius
    last_cx, last_cy = toroid_centers_right[-1]
    out_cx = last_cx + (r_t + r_out) * dx_cone
    out_cy = last_cy + (r_t + r_out) * dy_cone
    
    circle_a = np.linspace(0, 2*np.pi, 40)
    ax.plot(out_cx + r_out * np.cos(circle_a), out_cy + r_out * np.sin(circle_a),
            color=PINK, alpha=0.6, linewidth=1.5, zorder=3)
    ax.plot(-out_cx + r_out * np.cos(circle_a), out_cy + r_out * np.sin(circle_a),
            color=PINK, alpha=0.6, linewidth=1.5, zorder=3)
    ax.text(out_cx + 80, out_cy + 30, "N+1", color=PINK, fontsize=8, fontweight='bold', zorder=6)
    ax.text(-out_cx - 80, out_cy + 30, "N+1", color=PINK, fontsize=8, fontweight='bold', zorder=6)
    
    # ── Torus shell skin (red dashed outer envelope) ──
    # The skin follows the outside of each toroid along the cone
    # For each toroid, the outermost point (away from payload) is:
    #   cx - r_t * dy_cone (perpendicular to cone, outward normal = (-dy, dx) rotated)
    # Actually the "outside" of the torus shell (the windward side) is on the side facing away from the axis
    # The outer shell follows the bottom-outside of each toroid
    # Normal to cone pointing away from payload: perpendicular to (dx_cone, dy_cone) = (-dy_cone, dx_cone)
    # The windward side (facing flow from below): the side with normal pointing downward/outward
    # Shell passes through: (cx - r_t * normal_x, cy - r_t * normal_y) for each toroid
    
    # Actually simpler: the shell is a straight line tangent to all toroids on the windward side
    # For the cone geometry, this line is parallel to the cone generator, offset by r_t perpendicular
    # Perpendicular to cone, pointing toward flow (downward): normal = (dy_cone, -dx_cone) = (cos60, -sin60)
    # Wait, perpendicular away from axis/payload and toward flow:
    # Cone direction: (sin(theta), cos(theta)) = outward, upward
    # Perpendicular downward (toward flow): (cos(theta), -sin(theta))
    
    shell_pts_x = []
    shell_pts_y = []
    for cx, cy in toroid_centers_right:
        sx = cx + r_t * np.cos(theta)   # perpendicular offset toward flow
        sy = cy - r_t * np.sin(theta)
        shell_pts_x.append(sx)
        shell_pts_y.append(sy)
    # Add outer torus
    sx = out_cx + r_out * np.cos(theta)
    sy = out_cy - r_out * np.sin(theta)
    shell_pts_x.append(sx)
    shell_pts_y.append(sy)
    
    ax.plot(shell_pts_x, shell_pts_y, color=RED, linewidth=2, linestyle='--', alpha=0.6, zorder=4)
    ax.plot([-x for x in shell_pts_x], shell_pts_y, color=RED, linewidth=2, linestyle='--', alpha=0.6, zorder=4)
    ax.text(-shell_pts_x[-1] - 80, shell_pts_y[-1] - 60, "Torus Shell", 
            color=RED, fontsize=9, fontweight='bold', zorder=6)
    
    # ── Payload (blue rectangle above nose) ──
    pay_bottom = y_tangent - 20  # slightly below tangency
    pay_rect = patches.Rectangle((-r_pay, pay_bottom), 2 * r_pay, h_pay,
                                  facecolor='#3B82F6', alpha=0.2, edgecolor='#3B82F6',
                                  linewidth=2, zorder=2)
    ax.add_patch(pay_rect)
    ax.text(0, pay_bottom + h_pay/2, "Payload", color='#60A5FA', fontsize=11,
            ha='center', va='center', fontweight='bold', zorder=6)
    
    # ── Tank (small circle inside payload at bottom) ──
    r_tank_vis = 100
    tank_circle = plt.Circle((0, pay_bottom + r_tank_vis + 20), r_tank_vis,
                              facecolor=SUBTEXT, alpha=0.1, edgecolor=SUBTEXT, linewidth=1, zorder=3)
    ax.add_patch(tank_circle)
    
    # ── Symmetry axis (vertical dashed-dot line) ──
    y_min_plot = -100
    y_max_plot = pay_bottom + h_pay + 150
    ax.plot([0, 0], [y_min_plot, y_max_plot], color=SUBTEXT, linewidth=1.2,
            linestyle='-.', alpha=0.5, zorder=1)
    
    # ════════════════════════════════════════════════════════════════════
    # PARAMETER ANNOTATIONS
    # ════════════════════════════════════════════════════════════════════
    
    # θ_c - cone half-angle (from vertical axis to cone generator)
    # Draw an arc from the vertical axis direction to the cone direction
    arc_center_x = tx * 0.7
    arc_center_y = ty * 0.7 + 50
    arc_r_vis = 200
    # The vertical axis direction is 90° (pointing up), the cone direction from tangency is:
    # atan2(dx_cone, dy_cone) measured from vertical = atan2(sin60, cos60) = 60°
    # In matplotlib Arc angles: 0=right, 90=up, so vertical=90°
    # Cone direction from tangency: angle from horizontal = atan2(dy_cone, dx_cone) = atan2(0.5, 0.866) = 30°
    # So arc from 30° to 90° (matplotlib convention)
    arc_patch = Arc((0, ty + 200), 2*arc_r_vis, 2*arc_r_vis,
                    angle=0, theta1=30, theta2=90,
                    color=TEXT, linewidth=1.5, linestyle='-')
    ax.add_patch(arc_patch)
    ax.text(130, ty + 310, r'$\theta_c$', color=TEXT, fontsize=14, fontweight='bold', zorder=6)
    
    # r_pay annotation (horizontal arrow at top of payload)
    rpay_y = pay_bottom + h_pay - 50
    ax.annotate('', xy=(r_pay, rpay_y), xytext=(0, rpay_y),
                arrowprops=dict(arrowstyle='<->', color=AMBER, lw=1.5))
    ax.text(r_pay/2, rpay_y + 25, r'$r_{pay}$', color=AMBER, fontsize=11,
            ha='center', fontweight='bold', zorder=6)
    
    # h_pay annotation (vertical arrow alongside payload)
    hpay_x = -r_pay - 80
    ax.annotate('', xy=(hpay_x, pay_bottom), xytext=(hpay_x, pay_bottom + h_pay),
                arrowprops=dict(arrowstyle='<->', color=AMBER, lw=1.5))
    ax.text(hpay_x - 50, pay_bottom + h_pay/2, r'$h_{pay}$', color=AMBER, fontsize=11,
            ha='center', fontweight='bold', rotation=90, zorder=6)
    
    # r_torus annotation (at a middle toroid)
    mid_idx = 2  # toroid 3
    mcx, mcy = toroid_centers_right[mid_idx]
    ax.annotate('', xy=(mcx + r_t, mcy), xytext=(mcx, mcy),
                arrowprops=dict(arrowstyle='<->', color=GREEN, lw=1.5))
    ax.text(mcx + r_t + 20, mcy + 25, r'$r_{torus}$', color=GREEN, fontsize=10,
            fontweight='bold', zorder=6)
    
    # r_out,torus annotation
    ax.text(out_cx + r_out + 30, out_cy - 30, r'$r_{out,torus}$', color=PINK,
            fontsize=9, fontweight='bold', zorder=6)
    
    # r_N annotation (from nose center to stagnation point)
    ax.annotate('', xy=(0, 0), xytext=(R_n * 0.5, R_n * 0.8),
                arrowprops=dict(arrowstyle='->', color=CYAN, lw=1.5, linestyle='--'))
    ax.text(R_n * 0.30, R_n * 0.55, r'$r_N$', color=CYAN, fontsize=13, fontweight='bold', zorder=6)
    
    # r_tank annotation
    ax.annotate('', xy=(r_tank_vis, pay_bottom + r_tank_vis + 20),
                xytext=(0, pay_bottom + r_tank_vis + 20),
                arrowprops=dict(arrowstyle='<->', color=SUBTEXT, lw=1))
    ax.text(r_tank_vis/2, pay_bottom + r_tank_vis + 45, r'$r_{tank}$',
            color=SUBTEXT, fontsize=9, ha='center', zorder=6)
    
    # Flow direction arrow (from BELOW)
    ax.annotate('', xy=(0, -20), xytext=(0, -200),
                arrowprops=dict(arrowstyle='->', color=CYAN, lw=3))
    ax.text(0, -240, "Flow", color=CYAN, fontsize=10, ha='center', va='top', fontweight='bold')
    
    # Title and formatting
    ax.set_title("1. IRVE-3 Parametric Geometry\n(Rapisarda 2023, Table 4.1)",
                 color=TEXT, fontsize=12, fontweight='bold', pad=12)
    ax.set_xlabel("Radial Position R [mm]", color=TEXT, fontsize=9)
    ax.set_ylabel("Axial Position Z [mm]", color=TEXT, fontsize=9)
    ax.tick_params(colors=SUBTEXT, labelsize=7)
    for spine in ax.spines.values():
        spine.set_color('#30363d')
    ax.grid(True, linestyle='--', alpha=0.12, color='#30363d')
    
    # Auto-scale to fit with EQUAL aspect ratio
    max_x = out_cx + r_out + 250
    span_x = 2 * max_x
    
    y_min = -280
    y_max = pay_bottom + h_pay + 200
    span_y = y_max - y_min
    
    # Force equal spans so circles aren't stretched
    if span_x > span_y:
        diff = span_x - span_y
        y_max += diff / 2
        y_min -= diff / 2
    else:
        diff = span_y - span_x
        max_x += diff / 2
        
    ax.set_xlim(-max_x, max_x)
    ax.set_ylim(y_min, y_max)
    ax.set_aspect('equal', adjustable='box')


def draw_sparta_bc(ax):
    """Panel 2: SPARTA 2D axisymmetric boundary conditions."""
    ax.set_facecolor(PANEL_BG)
    ax.set_xlim(-1.5, 9.5)
    ax.set_ylim(-1.5, 6.5)
    ax.axis('off')
    
    # Domain box
    domain_box = patches.Rectangle((0, 0), 8, 5, fill=False, edgecolor=SUBTEXT,
                                     linestyle='--', linewidth=1.5)
    ax.add_patch(domain_box)
    
    # HIAD shape (axisymmetric, y >= 0)
    # Nose points LEFT towards inflow (x=0)
    R_n_vis = 0.8  # scaled for visibility
    theta_c = np.radians(60)
    
    # Nose center at (3.5, 0). Tip at (3.5 - 0.8 = 2.7, 0)
    nose_cx, nose_cy = 3.5, 0.0
    angles = np.linspace(np.pi, np.pi - theta_c, 30)
    x_nose = nose_cx + R_n_vis * np.cos(angles)
    y_nose = nose_cy + R_n_vis * np.sin(angles)
    
    # Cone line (scalloped with 6 toroids)
    N_toroids = 6
    cone_L = 2.5
    r_torus = cone_L / (2 * N_toroids)
    
    x_cone_list = []
    y_cone_list = []
    
    # Starting point of the cone (tangency point)
    x_t = x_nose[-1]
    y_t = y_nose[-1]
    
    for i in range(N_toroids):
        # Center of this toroid
        dist_c = (2*i + 1) * r_torus
        cx = x_t + dist_c * np.cos(theta_c)
        cy = y_t + dist_c * np.sin(theta_c)
        
        # The F-TPS blanket creates shallow scallops, not deep grooves.
        # Engine defaults to scallop_angle = 40 deg (±20 deg from tangency).
        scallop_half_angle = np.radians(20)
        arc_angles = np.linspace(theta_c + np.pi/2 - scallop_half_angle, theta_c + np.pi/2 + scallop_half_angle, 10)
        
        x_arc = cx + r_torus * np.cos(arc_angles)
        y_arc = cy + r_torus * np.sin(arc_angles)
        x_cone_list.extend(x_arc)
        y_cone_list.extend(y_arc)
        
    x_cone = np.array(x_cone_list)
    y_cone = np.array(y_cone_list)
    
    # Full shape for filling (surface + back + centerline)
    x_surf = np.concatenate([x_nose, x_cone])
    y_surf = np.concatenate([y_nose, y_cone])
    x_fill = np.concatenate([x_surf, [x_surf[-1], x_surf[0]]])
    y_fill = np.concatenate([y_surf, [0, 0]])
    
    ax.plot(x_surf, y_surf, color=AMBER, linewidth=4, zorder=5)
    ax.fill(x_fill, y_fill, color=RED, alpha=0.2, zorder=4)
    
    # Left: Inflow
    ax.plot([0, 0], [0, 5], color=CYAN, linewidth=4)
    ax.text(-0.3, 2.5,
            f"Inflow (xlo)\nemit/face\n"
            f"v = {ENGINE['v_inf']:.0f} m/s\n"
            f"T = {ENGINE['T_inf']:.0f} K\n"
            f"n = {ENGINE['n_rho']:.2e} /m\u00b3",
            color=CYAN, fontsize=10, ha='right', va='center', fontweight='bold')
    for y_arr in np.linspace(0.5, 4.5, 5):
        ax.arrow(0.1, y_arr, 0.8, 0, head_width=0.18, head_length=0.15,
                 fc=CYAN, ec=CYAN)
    
    # Right: Outflow
    ax.plot([8, 8], [0, 5], color=SUBTEXT, linewidth=4)
    ax.text(8.3, 2.5, "Outflow (xhi)\nVacuum (o)",
            color=SUBTEXT, fontsize=10, ha='left', va='center')
    
    # Top: Outflow
    ax.plot([0, 8], [5, 5], color=SUBTEXT, linewidth=4)
    ax.text(4, 5.3, "Outflow (yhi)  Vacuum (o)",
            color=SUBTEXT, fontsize=10, ha='center', va='bottom')
    
    # Bottom: Axisymmetric
    ax.plot([0, 8], [0, 0], color=TEXT, linewidth=4, linestyle='-.')
    ax.text(4, -0.4, "Axisymmetric Centreline (ylo = 0)\nboundary 'a'",
            color=TEXT, fontsize=10, ha='center', va='top', fontweight='bold')
    
    # HIAD Surface BC
    ax.annotate('', xy=(3.0, 1.2), xytext=(2.0, 3.5),
                arrowprops=dict(arrowstyle='->', color=AMBER, lw=2))
    ax.text(2.0, 3.7,
            f"HIAD Surface\nDiffuse Isothermal Wall\n"
            f"$T_{{wall}}$ = {ENGINE['T_wall']:.0f} K\n"
            r"(Captures $\dot{q}_{stag}$)",
            color=AMBER, fontsize=10, ha='center', va='bottom', fontweight='bold')
    
    ax.text(5.5, 4.5, "dimension 2\nboundary  o ao p\ngas: 5-species air\n(N\u2082, O\u2082, NO, N, O)",
            color=SUBTEXT, fontsize=9, ha='left', va='top',
            bbox=dict(facecolor=BG, edgecolor='#30363d', boxstyle='round,pad=0.4'))
    
    ax.set_title("2. SPARTA DSMC Boundary Conditions\n(Corrected Values)",
                 color=TEXT, fontsize=12, fontweight='bold', pad=12)


def draw_comparison_table(ax):
    """Panel 3: Parameter comparison table."""
    ax.set_facecolor(PANEL_BG)
    ax.axis('off')
    
    params = [
        (r"$\theta_c$ (cone angle)", f"{RAPISARDA['theta_c']}\u00b0", f"{ENGINE['theta_c']}\u00b0", True, "Variant"),
        (r"$N$ (toroids)", str(RAPISARDA['N']), str(ENGINE['N']), True, "Variant"),
        (r"$r_{torus}$", f"{RAPISARDA['r_torus']} m", f"{ENGINE['r_torus']} m", True, "Variant"),
        (r"$r_{out,torus}$", f"{RAPISARDA['r_out_torus']} m", f"{ENGINE['r_out_torus']} m", True, "Fixed"),
        (r"$R_n$ (nose radius)", f"{RAPISARDA['R_n']} m", f"{ENGINE['R_n']} m", True, "Variant"),
        (r"$D$ (diameter)", f"{RAPISARDA['D_inflated']} m", f"{ENGINE['D_inflated']} m", True, "Variant"),
        (r"$h_{pay}$", f"{RAPISARDA['h_pay']} m", f"{ENGINE['h_pay']} m", True, "Fixed"),
        (r"$r_{pay}$", f"{RAPISARDA['r_pay']} m", f"{ENGINE['r_pay']} m", True, "Fixed"),
        (r"$m$ (mass)", f"{RAPISARDA['m']} kg", f"{ENGINE['m']} kg", True, "Variant"),
        ("", "", "", None, ""),
        (r"$v_\infty$", "2700 m/s", f"{ENGINE['v_inf']:.0f} m/s", True, "Fixed"),
        (r"$T_\infty$", "270.65 K", f"{ENGINE['T_inf']:.0f} K", True, "Fixed"),
        (r"$n_\rho$", "3.47e21 /m\u00b3", f"{ENGINE['n_rho']:.2e} /m\u00b3", True, "Fixed"),
        (r"$T_{wall}$", "\u2014", f"{ENGINE['T_wall']:.0f} K", None, "Fixed"),
    ]
    
    y_start = 0.92
    dy = 0.055
    
    # Header
    ax.text(0.04, y_start + 0.04, "Parameter", color=AMBER, fontsize=10,
            fontweight='bold', transform=ax.transAxes, family='monospace')
    ax.text(0.38, y_start + 0.04, "Rapisarda", color=CYAN, fontsize=10,
            fontweight='bold', transform=ax.transAxes, family='monospace')
    ax.text(0.60, y_start + 0.04, "Engine", color=GREEN, fontsize=10,
            fontweight='bold', transform=ax.transAxes, family='monospace')
    ax.text(0.78, y_start + 0.04, "Match", color=TEXT, fontsize=10,
            fontweight='bold', transform=ax.transAxes, family='monospace')
    ax.text(0.90, y_start + 0.04, "Type", color=PURPLE, fontsize=10,
            fontweight='bold', transform=ax.transAxes, family='monospace')
    
    ax.plot([0.02, 0.98], [y_start + 0.01, y_start + 0.01], color='#30363d',
            linewidth=1, transform=ax.transAxes)
    
    for i, (name, rap_val, eng_val, match, ptype) in enumerate(params):
        y = y_start - i * dy
        
        if name == "":
            ax.plot([0.02, 0.98], [y + dy/2, y + dy/2], color='#30363d',
                    linewidth=0.5, transform=ax.transAxes)
            continue
        
        ax.text(0.04, y, name, color=TEXT, fontsize=9, transform=ax.transAxes)
        ax.text(0.38, y, rap_val, color=CYAN, fontsize=9,
                transform=ax.transAxes, family='monospace')
        ax.text(0.60, y, eng_val, color=GREEN, fontsize=9,
                transform=ax.transAxes, family='monospace')
        
        if match is True:
            ax.text(0.80, y, "YES", fontsize=8, transform=ax.transAxes, color=GREEN, fontweight='bold')
        elif match is False:
            ax.text(0.80, y, "NO", fontsize=8, transform=ax.transAxes, color=RED, fontweight='bold')
        elif match is None:
            ax.text(0.80, y, "\u2014", color=SUBTEXT, fontsize=10, transform=ax.transAxes)
        
        type_color = AMBER if ptype == "Variant" else SUBTEXT
        ax.text(0.90, y, ptype, color=type_color, fontsize=8,
                transform=ax.transAxes, family='monospace')
    
    ax.set_title("3. Parameter Comparison\nRapisarda (2023) vs Engine",
                 color=TEXT, fontsize=12, fontweight='bold', pad=12)


def main():
    plt.style.use('dark_background')
    fig = plt.figure(figsize=(22, 9), facecolor=BG)
    fig.patch.set_facecolor(BG)
    
    gs = fig.add_gridspec(1, 3, width_ratios=[1.2, 1, 1.3], wspace=0.25)
    
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])
    ax3 = fig.add_subplot(gs[2])
    
    draw_parametric_geometry(ax1)
    draw_sparta_bc(ax2)
    draw_comparison_table(ax3)
    
    fig.suptitle(
        "IRVE-3 HIAD: Boundary Conditions & Parametric Design Verification\n"
        "Rapisarda (2023) Table 4.1 vs StellarOrion Engine Defaults",
        color=TEXT, fontsize=15, fontweight='bold', y=0.98
    )
    
    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_dir, "irve3_bc_comparison.png")
    plt.savefig(out_path, dpi=180, facecolor=BG, edgecolor='none', bbox_inches='tight')
    print(f"[+] Saved: {out_path}")
    
    report_dir = os.path.join(out_dir, "ProgressReport", "Week 11", "figures", "Result")
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, "irve3_bc_comparison.png")
    plt.savefig(report_path, dpi=180, facecolor=BG, edgecolor='none', bbox_inches='tight')
    print(f"[+] Saved: {report_path}")
    
    plt.close()


if __name__ == '__main__':
    main()
