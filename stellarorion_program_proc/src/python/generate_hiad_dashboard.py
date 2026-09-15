#!/usr/bin/env python3
"""
HIAD Geometry Dashboard Generator
Generates MP4 visualization of IRVE-3 HIAD cross-section geometry
with parameter dashboard overlay.
"""
import sys
import os
import ctypes
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import FancyArrowPatch
import matplotlib.gridspec as gridspec

# Add parent directory to path for the wrapper
sys.path.insert(0, os.path.dirname(__file__))
from ada_pinn_wrapper import get_hiad_cross_section

def create_geometry_dashboard(output_path='hiad_geometry_dashboard.mp4', fps=30, duration=10):
    """
    Create an MP4 dashboard showing the HIAD geometry with parameters.
    
    Args:
        output_path: Path for output MP4 file
        fps: Frames per second
        duration: Duration in seconds
    """
    # Get geometry data from Ada/SPARK via FFI
    print("Loading geometry from Ada/SPARK via FFI...")
    cs = get_hiad_cross_section()
    
    x = np.array(cs['x'])
    y = np.array(cs['y'])
    n_pts = cs['n']
    
    print(f"Loaded {n_pts} points")
    print(f"X range: [{x.min():.4f}, {x.max():.4f}] m")
    print(f"Y range: [{y.min():.4f}, {y.max():.4f}] m")
    
    # IRVE-3 parameters (from Ada/SPARK constants)
    params = {
        'R_N': 1.5,           # Nose radius (m)
        'r_tor': 0.135,       # Torus minor radius (m)
        'N_tori': 6,          # Number of tori
        'half_cone_deg': 60,  # Half-cone angle (deg)
        'half_cone_rad': np.radians(90.0 - 60),  # Ada Gamma_Rad = (90 - Half_Cone_Deg) * Pi/180
        'n_pts': n_pts,       # Number of cross-section points
        'max_radius': y.max(),  # Maximum radial extent
        'total_length': x.max(),  # Total axial length
    }
    
    # Calculate derived parameters
    gamma = params['half_cone_rad']
    r_tor = params['r_tor']
    N = params['N_tori']
    
    # Tangency point
    R_tang = params['R_N'] * np.cos(gamma)
    Z_tang = params['R_N'] * (1 - np.sin(gamma))
    
    # Last torus center
    S_last = (2 * N - 1) * r_tor
    R_target = R_tang + S_last * np.cos(gamma)
    Z_out = Z_tang + S_last * np.sin(gamma)
    
    # Outer torus
    R_C_out = R_target - r_tor * np.sin(gamma)
    Z_C_out = Z_out + r_tor * np.cos(gamma)
    
    # Back plane
    Z_back = Z_C_out + r_tor
    
    derived = {
        'R_tang': R_tang,
        'Z_tang': Z_tang,
        'S_last': S_last,
        'R_target': R_target,
        'Z_out': Z_out,
        'R_C_out': R_C_out,
        'Z_C_out': Z_C_out,
        'Z_back': Z_back,
    }
    
    print("\nDerived parameters:")
    for k, v in derived.items():
        print(f"  {k}: {v:.4f} m")
    
    # Setup figure with gridspec for dashboard layout
    fig = plt.figure(figsize=(16, 10))
    gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.3, wspace=0.3)
    
    # Main geometry plot (top-left, spans 2 columns)
    ax_main = fig.add_subplot(gs[0:2, 0:2])
    
    # Parameter panels
    ax_params1 = fig.add_subplot(gs[0, 2])
    ax_params2 = fig.add_subplot(gs[1, 2])
    
    # Bottom panel for animation timeline
    ax_timeline = fig.add_subplot(gs[2, :])
    
    # Color scheme
    colors = {
        'nose': '#FF6B6B',      # Red for nose arc
        'cone': '#4ECDC4',      # Teal for windward cone
        'toroid': '#45B7D1',    # Blue for toroid wrap
        'back': '#96CEB4',      # Green for flat back
        'param_text': '#2C3E50', # Dark blue for text
        'grid': '#ECF0F1',      # Light gray for grid
        'background': '#FAFAFA', # Off-white background
    }
    
    # Set background
    fig.patch.set_facecolor(colors['background'])
    ax_main.set_facecolor('white')
    
    # Animation function
    def animate(frame):
        # Clear axes
        ax_main.clear()
        ax_params1.clear()
        ax_params2.clear()
        ax_timeline.clear()
        
        # Calculate animation progress (0 to 1)
        progress = frame / (fps * duration)
        
        # Determine how many points to show (animate the profile drawing)
        n_show = max(1, int(n_pts * progress))
        x_show = x[:n_show]
        y_show = y[:n_show]
        
        # Mirror for full cross-section (upper + lower)
        x_full = np.concatenate([x_show, x_show[::-1]])
        y_full = np.concatenate([y_show, -y_show[::-1]])
        
        # Plot main geometry with fill
        ax_main.fill(x_full, y_full, color=colors['cone'], alpha=0.3, zorder=3)
        ax_main.plot(x_full, y_full, color=colors['cone'], linewidth=5, 
                    label='HIAD Cross-Section', zorder=5)
        
        # Color segments based on progress
        if n_show >= 15:  # Nose arc complete
            # Plot nose arc
            ax_main.plot(x[:15], y[:15], color=colors['nose'], linewidth=5, 
                        label='Nose Arc', zorder=6)
            ax_main.plot(x[:15], -y[:15], color=colors['nose'], linewidth=5, zorder=6)
        
        if n_show >= 29:  # Windward cone complete
            # Plot windward cone
            ax_main.plot(x[14:29], y[14:29], color=colors['cone'], linewidth=5, 
                        label='Windward Cone', zorder=6)
            ax_main.plot(x[14:29], -y[14:29], color=colors['cone'], linewidth=5, zorder=6)
        
        if n_show >= 43:  # Toroid wrap complete
            # Plot toroid wrap
            ax_main.plot(x[28:43], y[28:43], color=colors['toroid'], linewidth=5, 
                        label='Toroid Wrap', zorder=6)
            ax_main.plot(x[28:43], -y[28:43], color=colors['toroid'], linewidth=5, zorder=6)
        
        if n_show >= 57:  # Flat back complete
            # Plot flat back
            ax_main.plot(x[42:57], y[42:57], color=colors['back'], linewidth=5, 
                        label='Flat Back', zorder=6)
            ax_main.plot(x[42:57], -y[42:57], color=colors['back'], linewidth=5, zorder=6)
        
        # Add reference circles for tori
        if n_show >= 43:
            for i in range(N):
                # Torus center positions along the cone
                s_center = (2 * i + 1) * r_tor
                z_center = Z_tang + s_center * np.sin(gamma)
                r_center = R_tang + s_center * np.cos(gamma)
                
                # Draw torus cross-section (circle)
                theta = np.linspace(0, 2*np.pi, 50)
                x_torus = z_center + r_tor * np.cos(theta)
                y_torus = r_center + r_tor * np.sin(theta)
                ax_main.plot(x_torus, y_torus, color=colors['toroid'], 
                           linewidth=2.5, alpha=0.7, zorder=4)
                ax_main.plot(x_torus, -y_torus, color=colors['toroid'], 
                           linewidth=2.5, alpha=0.7, zorder=4)
        
        # Add reference lines
        ax_main.axhline(y=0, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)
        ax_main.axvline(x=0, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)
        
        # Add dimension arrows
        if n_show >= 57:
            # Total length
            ax_main.annotate('', xy=(x.max(), -y.max()-0.2), xytext=(0, -y.max()-0.2),
                           arrowprops=dict(arrowstyle='<->', color='black', lw=1.5))
            ax_main.text(x.max()/2, -y.max()-0.35, f'L = {x.max():.3f} m', 
                        ha='center', va='top', fontsize=10, fontweight='bold')
            
            # Max radius
            ax_main.annotate('', xy=(x.max()+0.2, y.max()), xytext=(x.max()+0.2, 0),
                           arrowprops=dict(arrowstyle='<->', color='black', lw=1.5))
            ax_main.text(x.max()+0.35, y.max()/2, f'R = {y.max():.3f} m', 
                        ha='left', va='center', fontsize=10, fontweight='bold', rotation=90)
        
        # Formatting
        ax_main.set_xlim(-0.2, x.max()+0.5)
        ax_main.set_ylim(-y.max()-0.5, y.max()+0.5)
        ax_main.set_xlabel('Axial Distance Z (m)', fontsize=12, fontweight='bold')
        ax_main.set_ylabel('Radial Distance R (m)', fontsize=12, fontweight='bold')
        ax_main.set_title('IRVE-3 HIAD Cross-Section Geometry', fontsize=14, fontweight='bold')
        ax_main.grid(True, alpha=0.3, color=colors['grid'])
        ax_main.set_aspect('equal')
        ax_main.legend(loc='upper left', fontsize=9)
        
        # Parameters panel 1 - Geometry
        ax_params1.text(0.05, 0.95, 'GEOMETRY PARAMETERS', fontsize=12, fontweight='bold',
                       transform=ax_params1.transAxes, verticalalignment='top')
        
        param_text1 = [
            f"R_N = {params['R_N']:.3f} m",
            f"r_tor = {params['r_tor']:.3f} m",
            f"N_tori = {params['N_tori']}",
            f"Half-Cone = {params['half_cone_deg']}°",
            f"N_Pts = {params['n_pts']}",
        ]
        
        for i, text in enumerate(param_text1):
            ax_params1.text(0.1, 0.85 - i*0.15, text, fontsize=11,
                           transform=ax_params1.transAxes, fontfamily='monospace')
        
        ax_params1.set_xlim(0, 1)
        ax_params1.set_ylim(0, 1)
        ax_params1.axis('off')
        ax_params1.set_facecolor('white')
        
        # Parameters panel 2 - Derived
        ax_params2.text(0.05, 0.95, 'DERIVED PARAMETERS', fontsize=12, fontweight='bold',
                       transform=ax_params2.transAxes, verticalalignment='top')
        
        param_text2 = [
            f"R_tang = {R_tang:.4f} m",
            f"Z_tang = {Z_tang:.4f} m",
            f"S_last = {S_last:.4f} m",
            f"R_target = {R_target:.4f} m",
            f"R_C_out = {R_C_out:.4f} m",
            f"Z_back = {Z_back:.4f} m",
        ]
        
        for i, text in enumerate(param_text2):
            ax_params2.text(0.1, 0.85 - i*0.12, text, fontsize=10,
                           transform=ax_params2.transAxes, fontfamily='monospace')
        
        ax_params2.set_xlim(0, 1)
        ax_params2.set_ylim(0, 1)
        ax_params2.axis('off')
        ax_params2.set_facecolor('white')
        
        # Timeline panel
        time_sec = frame / fps
        ax_timeline.barh(0, time_sec, height=0.5, color=colors['cone'], alpha=0.7)
        ax_timeline.barh(0, duration, height=0.5, color='lightgray', alpha=0.3, zorder=0)
        ax_timeline.set_xlim(0, duration)
        ax_timeline.set_ylim(-1, 1)
        ax_timeline.set_xlabel('Time (s)', fontsize=12, fontweight='bold')
        ax_timeline.set_title(f'Animation Progress: {time_sec:.1f}s / {duration}s', 
                             fontsize=11, fontweight='bold')
        ax_timeline.set_yticks([])
        ax_timeline.grid(True, axis='x', alpha=0.3)
        
        # Add percentage text
        ax_timeline.text(time_sec/2, 0, f'{progress*100:.1f}%', 
                        ha='center', va='center', fontsize=14, fontweight='bold', color='white')
        
        return []
    
    # Create animation
    print(f"\nCreating animation: {fps} fps, {duration} seconds...")
    anim = animation.FuncAnimation(fig, animate, frames=fps*duration, interval=1000/fps)
    
    # Save as MP4
    print(f"Saving to {output_path}...")
    anim.save(output_path, writer='ffmpeg', fps=fps, dpi=150,
             extra_args=['-vcodec', 'libx264', '-pix_fmt', 'yuv420p'])
    
    plt.close()
    print(f"Dashboard saved to: {output_path}")
    
    return output_path

if __name__ == "__main__":
    output = create_geometry_dashboard()
    print(f"\nDone! MP4 saved to: {output}")
