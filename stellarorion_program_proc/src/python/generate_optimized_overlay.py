#!/usr/bin/env python3
"""
HIAD Geometry Optimized Dashboard with Default vs Optimized Overlay
Generates MP4 comparing default and optimized HIAD geometries.
"""
import sys
import os
import json
import ctypes
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyArrowPatch
from matplotlib.lines import Line2D

# Add parent directory to path for the wrapper
sys.path.insert(0, os.path.dirname(__file__))
from ada_pinn_wrapper import get_hiad_cross_section

def generate_cross_section(R_N, r_tor, half_cone_deg, n_per_segment=15):
    """Generate HIAD cross-section from parameters (pure Python).
    
    EXACT copy of Ada/SPARK stellarorion_pinn_trajectory.adb Get_HIAD_Cross_Section.
    All formulas match the Ada body line-for-line.
    [Citation: stellarorion_pinn_trajectory.adb lines 425-479]
    """
    pi = np.pi
    # Ada uses Gamma_Rad = (90 - Half_Cone_Deg) * Pi / 180 (the complement angle)
    # [Citation: stellarorion_pinn_trajectory.adb line 393]
    gamma = np.radians(90.0 - half_cone_deg)
    tan_g = np.tan(gamma)
    
    # Tangency point (same as Ada: R_Tang = R_N * Cos_Rad(Gamma_Rad))
    # [Citation: stellarorion_pinn_trajectory.adb lines 397-398]
    R_tang = R_N * np.cos(gamma)
    Z_tang = R_N * (1.0 - np.sin(gamma))
    
    # Conical shell max axial length
    N_tori = 6
    S_max = (2 * N_tori - 1) * r_tor
    R_target = R_tang + S_max * np.cos(gamma)
    
    # Toroid outer center (same as Ada lines 393-394)
    R_C_out = R_target - r_tor * np.sin(gamma)
    Z_C_out = (Z_tang + S_max * np.sin(gamma)) + r_tor * np.cos(gamma)
    Z_back = Z_C_out + r_tor
    
    x_pts = []  # axial (PZ in Ada)
    y_pts = []  # radial (PR in Ada)
    
    # Segment 1: Nose Arc (theta: -Pi/2 to -gamma)
    # Ada: PR = R_N * Cos_Rad(Alpha), PZ = R_N + R_N * Sin_Rad(Alpha)
    # [Citation: stellarorion_pinn_trajectory.adb lines 429-440]
    for i in range(n_per_segment):
        t = i / (n_per_segment - 1)
        alpha = (-pi / 2.0) * (1.0 - t) + (-gamma) * t
        pr = R_N * np.cos(alpha)   # radial
        pz = R_N + R_N * np.sin(alpha)  # axial
        x_pts.append(max(0.0, pz))
        y_pts.append(max(0.0, pr))
    
    # Segment 2: Windward Straight (conical shell)
    # Ada: R = R_Tang + T * (R_Target - R_Tang), Z = Z_Tang + (R - R_Tang) * tan(gamma)
    # [Citation: stellarorion_pinn_trajectory.adb lines 444-453]
    for i in range(1, n_per_segment):
        t = i / (n_per_segment - 1)
        r = R_tang + t * (R_target - R_tang)
        z = Z_tang + (r - R_tang) * tan_g
        x_pts.append(z)
        y_pts.append(r)
    
    # Segment 3: Toroid Wrap (theta: -gamma to Pi/2)
    # Ada: PR = R_C_Out + r_tor * Cos_Rad(Theta), PZ = Z_C_Out + r_tor * Sin_Rad(Theta)
    # [Citation: stellarorion_pinn_trajectory.adb lines 457-468]
    for i in range(1, n_per_segment):
        t = i / (n_per_segment - 1)
        theta = (-gamma) * (1.0 - t) + (pi / 2.0) * t
        pr = R_C_out + r_tor * np.cos(theta)   # radial
        pz = Z_C_out + r_tor * np.sin(theta)   # axial
        x_pts.append(pz)
        y_pts.append(pr)
    
    # Segment 4: Flat Back (r from R_C_Out to 0, z = Z_Back)
    # Ada: R = R_C_Out * (1.0 - T), Z = Z_Back
    # [Citation: stellarorion_pinn_trajectory.adb lines 471-478]
    for i in range(1, n_per_segment):
        t = i / (n_per_segment - 1)
        r = R_C_out * (1.0 - t)
        z = Z_back
        x_pts.append(z)
        y_pts.append(r)
    
    return np.array(x_pts), np.array(y_pts)

def create_optimized_overlay_dashboard(output_path='hiad_optimized_overlay.mp4', fps=30, duration=10):
    """Create MP4 with default vs optimized geometry overlay."""
    
    # Load optimization results
    results_path = os.path.join(os.path.dirname(__file__), 'hiad_optimization_results.json')
    with open(results_path, 'r') as f:
        results = json.load(f)
    
    default_params = results['default']
    optimized_params = results['optimized']
    
    print("Default parameters:")
    print(f"  R_N = {default_params['R_N']:.4f} m")
    print(f"  r_tor = {default_params['r_tor']:.4f} m")
    print(f"  half_cone = {default_params['half_cone_deg']:.2f} deg")
    print(f"  Cd = {default_params['Cd']:.6f}")
    
    print("\nOptimized parameters:")
    print(f"  R_N = {optimized_params['R_N']:.4f} m")
    print(f"  r_tor = {optimized_params['r_tor']:.4f} m")
    print(f"  half_cone = {optimized_params['half_cone_deg']:.2f} deg")
    print(f"  Cd = {optimized_params['Cd']:.6f}")
    
    # Generate cross-sections
    x_default, y_default = generate_cross_section(
        default_params['R_N'], default_params['r_tor'], default_params['half_cone_deg']
    )
    x_optimized, y_optimized = generate_cross_section(
        optimized_params['R_N'], optimized_params['r_tor'], optimized_params['half_cone_deg']
    )
    
    # Color scheme
    colors = {
        'default': '#3498db',      # Blue for default
        'optimized': '#e74c3c',    # Red for optimized
        'param_text': '#2C3E50',
        'grid': '#ECF0F1',
        'background': '#FAFAFA',
        'improvement': '#27ae60',  # Green for improvement
    }
    
    # Setup figure
    fig = plt.figure(figsize=(16, 10))
    gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.3, wspace=0.3)
    
    # Main geometry plot
    ax_main = fig.add_subplot(gs[0:2, 0:2])
    
    # Parameter panels
    ax_params1 = fig.add_subplot(gs[0, 2])
    ax_params2 = fig.add_subplot(gs[1, 2])
    
    # Timeline
    ax_timeline = fig.add_subplot(gs[2, :])
    
    fig.patch.set_facecolor(colors['background'])
    ax_main.set_facecolor('white')
    
    improvement_pct = results.get('improvement', {}).get('cost_pct', 0)
    
    def animate(frame):
        ax_main.clear()
        ax_params1.clear()
        ax_params2.clear()
        ax_timeline.clear()
        
        progress = frame / (fps * duration)
        
        # Animate: first show default, then overlay optimized
        if progress < 0.5:
            # Phase 1: Draw default (0 to 50%)
            phase1_progress = progress * 2  # 0 to 1
            n_show = max(1, int(len(x_default) * phase1_progress))
            
            # Default geometry (full cross-section with fill)
            x_full = np.concatenate([x_default[:n_show], x_default[:n_show][::-1]])
            y_full = np.concatenate([y_default[:n_show], -y_default[:n_show][::-1]])
            ax_main.fill(x_full, y_full, color=colors['default'], alpha=0.5, zorder=3)
            ax_main.plot(x_full, y_full, color=colors['default'], linewidth=5, 
                        label='Default', zorder=5)
            
            # Add dimension arrows for default
            if n_show >= len(x_default):
                ax_main.annotate('', xy=(x_default.max(), -y_default.max()-0.3), 
                               xytext=(0, -y_default.max()-0.3),
                               arrowprops=dict(arrowstyle='<->', color=colors['default'], lw=1.5))
                ax_main.text(x_default.max()/2, -y_default.max()-0.45, 
                           f'Default L={x_default.max():.3f}m', 
                           ha='center', va='top', fontsize=9, color=colors['default'])
            
            ax_main.set_title('Phase 1: Default IRVE-3 Geometry', fontsize=13, fontweight='bold')
            
        else:
            # Phase 2: Overlay optimized (50% to 100%)
            phase2_progress = (progress - 0.5) * 2  # 0 to 1
            n_show_opt = max(1, int(len(x_optimized) * phase2_progress))
            
            # Default (full, with fill)
            x_full_def = np.concatenate([x_default, x_default[::-1]])
            y_full_def = np.concatenate([y_default, -y_default[::-1]])
            ax_main.fill(x_full_def, y_full_def, color=colors['default'], alpha=0.3, zorder=3)
            ax_main.plot(x_full_def, y_full_def, color=colors['default'], linewidth=5, 
                        alpha=0.6, label='Default', zorder=4)
            
            # Optimized (animated, with fill)
            x_full_opt = np.concatenate([x_optimized[:n_show_opt], x_optimized[:n_show_opt][::-1]])
            y_full_opt = np.concatenate([y_optimized[:n_show_opt], -y_optimized[:n_show_opt][::-1]])
            ax_main.fill(x_full_opt, y_full_opt, color=colors['optimized'], alpha=0.5, zorder=4)
            ax_main.plot(x_full_opt, y_full_opt, color=colors['optimized'], linewidth=5, 
                        label='Optimized', zorder=5)
            
            # Add dimension arrows for optimized
            if n_show_opt >= len(x_optimized):
                ax_main.annotate('', xy=(x_optimized.max(), -y_optimized.max()-0.3), 
                               xytext=(0, -y_optimized.max()-0.3),
                               arrowprops=dict(arrowstyle='<->', color=colors['optimized'], lw=1.5))
                ax_main.text(x_optimized.max()/2, -y_optimized.max()-0.45, 
                           f'Optimized L={x_optimized.max():.3f}m', 
                           ha='center', va='top', fontsize=9, color=colors['optimized'])
                
                # Improvement badge
                ax_main.text(0.02, 0.98, f'Improvement: {improvement_pct:.2f}%', 
                           transform=ax_main.transAxes, fontsize=12, fontweight='bold',
                           color=colors['improvement'], verticalalignment='top',
                           bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            ax_main.set_title('Phase 2: Default vs Optimized Overlay', fontsize=13, fontweight='bold')
        
        # Reference lines
        ax_main.axhline(y=0, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)
        ax_main.axvline(x=0, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)
        
        # Axis formatting
        max_xlim = max(x_default.max(), x_optimized.max()) + 0.5
        max_ylim = max(y_default.max(), y_optimized.max()) + 0.5
        ax_main.set_xlim(-0.2, max_xlim)
        ax_main.set_ylim(-max_ylim, max_ylim)
        ax_main.set_xlabel('Axial Distance Z (m)', fontsize=12, fontweight='bold')
        ax_main.set_ylabel('Radial Distance R (m)', fontsize=12, fontweight='bold')
        ax_main.grid(True, alpha=0.3, color=colors['grid'])
        ax_main.set_aspect('equal')
        ax_main.legend(loc='upper left', fontsize=10)
        
        # Parameters panel 1 - Default
        ax_params1.text(0.05, 0.95, 'DEFAULT PARAMETERS', fontsize=11, fontweight='bold',
                       transform=ax_params1.transAxes, verticalalignment='top', color=colors['default'])
        
        param_text1 = [
            f"R_N = {default_params['R_N']:.3f} m",
            f"r_tor = {default_params['r_tor']:.3f} m",
            f"half_cone = {default_params['half_cone_deg']:.1f}°",
            f"Cd = {default_params['Cd']:.4f}",
            f"Cost = {default_params['cost']:.4f}",
        ]
        
        for i, text in enumerate(param_text1):
            ax_params1.text(0.1, 0.85 - i*0.15, text, fontsize=10,
                           transform=ax_params1.transAxes, fontfamily='monospace')
        
        ax_params1.set_xlim(0, 1)
        ax_params1.set_ylim(0, 1)
        ax_params1.axis('off')
        ax_params1.set_facecolor('white')
        
        # Parameters panel 2 - Optimized
        ax_params2.text(0.05, 0.95, 'OPTIMIZED PARAMETERS', fontsize=11, fontweight='bold',
                       transform=ax_params2.transAxes, verticalalignment='top', color=colors['optimized'])
        
        param_text2 = [
            f"R_N = {optimized_params['R_N']:.3f} m",
            f"r_tor = {optimized_params['r_tor']:.3f} m",
            f"half_cone = {optimized_params['half_cone_deg']:.1f}°",
            f"Cd = {optimized_params['Cd']:.4f}",
            f"Cost = {optimized_params['cost']:.4f}",
            f"Improvement: {improvement_pct:.2f}%",
        ]
        
        for i, text in enumerate(param_text2):
            color = colors['improvement'] if i == 5 else colors['param_text']
            ax_params2.text(0.1, 0.85 - i*0.12, text, fontsize=10,
                           transform=ax_params2.transAxes, fontfamily='monospace', color=color)
        
        ax_params2.set_xlim(0, 1)
        ax_params2.set_ylim(0, 1)
        ax_params2.axis('off')
        ax_params2.set_facecolor('white')
        
        # Timeline
        time_sec = frame / fps
        ax_timeline.barh(0, time_sec, height=0.5, color=colors['optimized'], alpha=0.7)
        ax_timeline.barh(0, duration, height=0.5, color='lightgray', alpha=0.3, zorder=0)
        ax_timeline.set_xlim(0, duration)
        ax_timeline.set_ylim(-1, 1)
        ax_timeline.set_xlabel('Time (s)', fontsize=12, fontweight='bold')
        ax_timeline.set_title(f'Animation: {time_sec:.1f}s / {duration}s (Default→Optimized)', 
                             fontsize=11, fontweight='bold')
        ax_timeline.set_yticks([])
        ax_timeline.grid(True, axis='x', alpha=0.3)
        
        # Phase indicator
        if progress < 0.5:
            phase_text = "DEFAULT"
            phase_color = colors['default']
        else:
            phase_text = "OPTIMIZED"
            phase_color = colors['optimized']
        
        ax_timeline.text(time_sec/2, 0, f'{phase_text} {progress*100:.0f}%', 
                        ha='center', va='center', fontsize=12, fontweight='bold', color='white')
        
        return []
    
    # Create animation
    print(f"\nCreating overlay animation: {fps} fps, {duration} seconds...")
    anim = animation.FuncAnimation(fig, animate, frames=fps*duration, interval=1000/fps)
    
    # Save
    print(f"Saving to {output_path}...")
    anim.save(output_path, writer='ffmpeg', fps=fps, dpi=150,
             extra_args=['-vcodec', 'libx264', '-pix_fmt', 'yuv420p'])
    
    plt.close()
    print(f"Overlay dashboard saved to: {output_path}")
    return output_path

if __name__ == "__main__":
    output = create_optimized_overlay_dashboard()
    print(f"\nDone! Overlay MP4 saved to: {output}")
