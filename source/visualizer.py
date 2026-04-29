import numpy as np
import matplotlib.pyplot as plt
import os

# Use non-interactive backend for thread safety in GUI
plt.switch_backend('Agg')

def find_ffmpeg():
    """Attempts to locate ffmpeg executable on Windows if not in PATH."""
    import shutil
    import os
    exe = shutil.which("ffmpeg")
    if exe: return exe
    
    # Check WinGet default location for Windows
    if os.name == 'nt':
        local_app_data = os.environ.get('LOCALAPPDATA', '')
        if local_app_data:
            winget_base = os.path.join(local_app_data, 'Microsoft', 'WinGet', 'Packages')
            if os.path.exists(winget_base):
                # Search for ffmpeg.exe in winget packages
                for root, dirs, files in os.walk(winget_base):
                    if 'ffmpeg.exe' in files:
                        return os.path.join(root, 'ffmpeg.exe')
    return "ffmpeg" # Fallback to default

def parse_grid_dump(filepath):
    data = []
    with open(filepath, 'r') as f:
        lines = f.readlines()
        start_index = 0
        for i, line in enumerate(lines):
            if "ITEM: CELLS" in line:
                start_index = i + 1
                break
        
        for line in lines[start_index:]:
            parts = line.split()
            if len(parts) >= 11:
                # id xlo ylo xhi yhi n u v w temp press
                data.append([float(x) for x in parts[1:]])
    return np.array(data)

def generate_plots(grid_file, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    data = parse_grid_dump(grid_file)
    if len(data) == 0:
        print(f"Error: No data found in {grid_file}")
        return

    # x_center, y_center calculations
    x_center = (data[:, 0] + data[:, 2]) / 2
    y_center = (data[:, 1] + data[:, 3]) / 2
    
    n = data[:, 4]
    u = data[:, 5]
    v = data[:, 6]
    w = data[:, 7]
    temp = data[:, 8]
    press = data[:, 9]

    # Plot 1: Temperature Contour Heatmap
    plt.figure(figsize=(10, 6))
    plt.gca().set_facecolor('#0f172a')
    # Use tricontourf for smooth "heatmap" appearance
    sc = plt.tricontourf(x_center, y_center, np.nan_to_num(temp), levels=50, cmap='hot')
    plt.colorbar(sc, label='Temperature (K)')
    plt.title('Thermal Map (Temperature)', color='white', fontweight='bold')
    plt.xlabel('Axial (m)', color='#94a3b8')
    plt.ylabel('Radial (m)', color='#94a3b8')
    plt.tick_params(colors='#94a3b8')
    plt.savefig(os.path.join(output_dir, 'thermal_map.png'), dpi=300)
    plt.savefig(os.path.join(output_dir, 'thermal_map.jpg'), pil_kwargs={'quality': 85}, dpi=300)
    plt.close()

    # Plot 2: Pressure Contour Heatmap
    plt.figure(figsize=(10, 6))
    plt.gca().set_facecolor('#0f172a')
    sc = plt.tricontourf(x_center, y_center, np.nan_to_num(press), levels=50, cmap='jet')
    plt.colorbar(sc, label='Pressure (Pa)')
    plt.title('Pressure Distribution', color='white', fontweight='bold')
    plt.xlabel('Axial (m)', color='#94a3b8')
    plt.ylabel('Radial (m)', color='#94a3b8')
    plt.tick_params(colors='#94a3b8')
    plt.savefig(os.path.join(output_dir, 'pressure_map.png'), dpi=300)
    plt.savefig(os.path.join(output_dir, 'pressure_map.jpg'), pil_kwargs={'quality': 85}, dpi=300)
    plt.close()

    # Plot 3: Velocity Vectors (Quiver)
    plt.figure(figsize=(10, 6))
    plt.gca().set_facecolor('#0f172a')
    # Downsample for clearer vectors
    step = max(1, len(x_center) // 400)
    plt.quiver(x_center[::step], y_center[::step], u[::step], v[::step], 
               np.sqrt(u[::step]**2 + v[::step]**2), cmap='viridis')
    plt.colorbar(label='Velocity Magnitude (m/s)')
    plt.title('Velocity Vectors', color='white', fontweight='bold')
    plt.xlabel('Axial (m)', color='#94a3b8')
    plt.ylabel('Radial (m)', color='#94a3b8')
    plt.tick_params(colors='#94a3b8')
    plt.savefig(os.path.join(output_dir, 'velocity_vectors.png'), dpi=300)
    plt.savefig(os.path.join(output_dir, 'velocity_vectors.jpg'), pil_kwargs={'quality': 85}, dpi=300)
    plt.close()

    # Plot 4: Mach Number Contour
    plt.figure(figsize=(10, 6))
    plt.gca().set_facecolor('#0f172a')
    vel = np.sqrt(u**2 + v**2 + w**2)
    # Speed of sound a = sqrt(gamma * R * T)
    gamma = 1.4
    R = 287.05
    # Ensure temp is positive to avoid sqrt of negative or div by zero
    safe_temp = np.maximum(temp, 1.0) 
    sound_speed = np.sqrt(gamma * R * safe_temp)
    mach = np.nan_to_num(vel / sound_speed, nan=0.0, posinf=0.0, neginf=0.0)
    sc = plt.tricontourf(x_center, y_center, mach, levels=50, cmap='plasma')
    plt.colorbar(sc, label='Mach Number')
    plt.title('Mach Number Distribution', color='white', fontweight='bold')
    plt.xlabel('Axial (m)', color='#94a3b8')
    plt.ylabel('Radial (m)', color='#94a3b8')
    plt.tick_params(colors='#94a3b8')
    plt.savefig(os.path.join(output_dir, 'mach_map.png'), dpi=300)
    plt.savefig(os.path.join(output_dir, 'mach_map.jpg'), pil_kwargs={'quality': 85}, dpi=300)
    plt.close()

    # Plot 5: Stagnation Streamline Graph (1D)
    generate_stagnation_graph(data, output_dir)

    print(f"Plots generated in {output_dir}")

def generate_stagnation_graph(data, output_dir):
    """Generates a 1D graph of properties along the stagnation streamline (y=0)."""
    # x_center, y_center calculations
    x_center = (data[:, 0] + data[:, 2]) / 2
    y_center = (data[:, 1] + data[:, 3]) / 2
    temp = data[:, 8]
    press = data[:, 9]

    # Filter for points near symmetry axis (y=0)
    # Since it's a grid, we look for the smallest y values
    min_y = np.min(np.abs(y_center))
    mask = np.abs(y_center) < (min_y + 0.05) # Small tolerance
    
    x_stag = x_center[mask]
    t_stag = temp[mask]
    p_stag = press[mask]

    # Sort by X
    idx = np.argsort(x_stag)
    x_stag = x_stag[idx]
    t_stag = t_stag[idx]
    p_stag = p_stag[idx]

    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax1.set_facecolor('#0f172a')
    fig.patch.set_facecolor('#0f172a')

    color = '#f43f5e'
    ax1.set_xlabel('Axial Position (m)', color='#94a3b8')
    ax1.set_ylabel('Temperature (K)', color=color)
    ax1.plot(x_stag, t_stag, color=color, linewidth=2.5, label='Temperature')
    ax1.tick_params(axis='y', labelcolor=color, colors='#94a3b8')
    ax1.tick_params(axis='x', colors='#94a3b8')

    ax2 = ax1.twinx()
    color = '#38bdf8'
    ax2.set_ylabel('Pressure (Pa)', color=color)
    ax2.plot(x_stag, p_stag, color=color, linewidth=2, linestyle='--', label='Pressure')
    ax2.tick_params(axis='y', labelcolor=color, colors='#94a3b8')

    plt.title('Stagnation Streamline Profile (y ≈ 0)', color='white', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.1, color='white')
    
    fig.tight_layout()
    plt.savefig(os.path.join(output_dir, 'stagnation_graph.png'), facecolor=fig.get_facecolor(), dpi=300)
    plt.savefig(os.path.join(output_dir, 'stagnation_graph.jpg'), pil_kwargs={'quality': 85}, facecolor=fig.get_facecolor(), dpi=300)
    plt.close()

def upscale_2d_to_3d(grid_file, output_path, surf_file=None, prop='temp'):
    """Upscales 2D axisymmetric results to a 3D visualization by rotating the slice.
    Supported props: 'temp', 'velocity', 'mach'
    """
    print(f"[*] Upscaling 2D axisymmetric results ({prop}) to 3D: {grid_file}")
    data = parse_grid_dump(grid_file)
    if len(data) == 0: return
    
    # x_center, y_center calculations
    x = (data[:, 0] + data[:, 2]) / 2
    y = (data[:, 1] + data[:, 3]) / 2
    
    # Property mapping
    if prop == 'velocity':
        u, v, w = data[:, 5], data[:, 6], data[:, 7]
        vals = np.sqrt(u**2 + v**2 + w**2)
        label = "Velocity (m/s)"
        cmap = 'viridis'
    elif prop == 'mach':
        u, v, w = data[:, 5], data[:, 6], data[:, 7]
        temp = data[:, 8]
        vel = np.sqrt(u**2 + v**2 + w**2)
        safe_temp = np.maximum(temp, 1.0)
        sound_speed = np.sqrt(1.4 * 287.05 * safe_temp)
        vals = np.nan_to_num(vel / sound_speed, nan=0.0, posinf=0.0, neginf=0.0)
        label = "Mach Number"
        cmap = 'plasma'
    else: # Default temp
        vals = data[:, 8]
        label = "Temperature (K)"
        cmap = 'hot'

    # 5x Resolution boost: Sample ~5000 points instead of 1000
    step = max(1, len(x) // 5000)
    x = x[::step]
    y = y[::step]
    vals = vals[::step]
    
    # 5x Radial resolution boost: 80 slices instead of 16
    n_slices = 80
    thetas = np.linspace(0, 2*np.pi, n_slices)
    
    from mpl_toolkits.mplot3d import Axes3D
    fig = plt.figure(figsize=(16, 14), facecolor='#0f172a')
    
    # Define angles and titles
    views = [
        {'elev': 20, 'azim': -45, 'title': 'Isometric View', 'zoom': False},
        {'elev': 0,  'azim': -90, 'title': 'Side View (Axial Profile)', 'zoom': False},
        {'elev': 0,  'azim': 0,   'title': 'Front View (Cross Section)', 'zoom': False},
        {'elev': 30, 'azim': -30, 'title': 'Stagnation Region Zoom', 'zoom': True}
    ]
    
    # 1. Parse Shield Surface once
    pts = None
    if surf_file and os.path.exists(surf_file):
        points = []
        with open(surf_file, 'r') as f:
            mode = None
            for line in f:
                if "Points" in line: mode = "pts"; continue
                if "Lines" in line: mode = "lines"; continue
                parts = line.split()
                if not parts or parts[0].isalpha(): continue
                if mode == "pts" and len(parts) >= 3:
                    points.append([float(parts[1]), float(parts[2])])
        if points: pts = np.array(points)

    # 2. Collect Fluid Data once
    all_x = []
    all_y = []
    all_z = []
    all_vals = []
    for theta in thetas:
        all_x.extend(x)
        all_y.extend(y * np.cos(theta))
        all_z.extend(y * np.sin(theta))
        all_vals.extend(vals)
    
    all_x = np.array(all_x)
    all_y = np.array(all_y)
    all_z = np.array(all_z)
    all_vals = np.array(all_vals)

    for i, v in enumerate(views):
        ax = fig.add_subplot(2, 2, i+1, projection='3d')
        ax.set_facecolor('#0f172a')
        
        # Plot Shield
        if pts is not None:
            for theta in np.linspace(0, 2*np.pi, 30):
                xs = pts[:, 0]
                ys = pts[:, 1] * np.cos(theta)
                zs = pts[:, 1] * np.sin(theta)
                ax.plot(xs, ys, zs, color='#f43f5e', alpha=0.3, linewidth=0.8)
        
        # Plot Fluid
        sc = ax.scatter(all_x, all_y, all_z, c=all_vals, cmap=cmap, s=1.5, alpha=0.08, edgecolors='none')
        
        # Axis Labels
        ax.set_xlabel('X (m)', color='#64748b', fontsize=8)
        ax.set_ylabel('Y (m)', color='#64748b', fontsize=8)
        ax.set_zlabel('Z (m)', color='#64748b', fontsize=8)
        ax.tick_params(colors='#475569', labelsize=7)
        
        # View & Zoom
        ax.view_init(elev=v['elev'], azim=v['azim'])
        if v['zoom']:
            # Zoom into stagnation point (usually around x=0, y=0)
            x_nose = np.min(all_x)
            ax.set_xlim(x_nose - 0.2, x_nose + 0.5)
            ax.set_ylim(-0.5, 0.5)
            ax.set_zlim(-0.5, 0.5)
        else:
            ax.set_xlim(np.min(all_x), np.max(all_x))
            ax.set_ylim(np.min(all_y), np.max(all_y))
            ax.set_zlim(np.min(all_z), np.max(all_z))
            
        ax.set_title(v['title'], color='#94a3b8', fontsize=10, fontweight='bold')

    # Colorbar at the bottom
    cbar_ax = fig.add_axes([0.15, 0.05, 0.7, 0.02])
    cbar = fig.colorbar(sc, cax=cbar_ax, orientation='horizontal')
    cbar.set_label(label, color='#94a3b8', fontweight='bold')
    cbar.ax.xaxis.set_tick_params(color='#94a3b8', labelcolor='#94a3b8')
    
    plt.suptitle(f'3D Axisymmetric Upscaling Multi-Angle: {label}', color='white', fontsize=18, fontweight='800', y=0.98)
    plt.subplots_adjust(left=0.05, right=0.95, bottom=0.1, top=0.9, wspace=0.1, hspace=0.1)
    
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor())
    plt.close()
    print(f"[+] 3D Multi-angle montage ({prop}) saved to {output_path}")

def export_upscaled_vtk(grid_file, output_path):
    """Exports the 3D upscaled data to a VTK file readable by ParaView."""
    print(f"[*] Exporting 3D upscaled data to ParaView VTK: {output_path}")
    data = parse_grid_dump(grid_file)
    if len(data) == 0: return
    
    x_2d = (data[:, 0] + data[:, 2]) / 2
    y_2d = (data[:, 1] + data[:, 3]) / 2
    u_2d = data[:, 5]
    v_2d = data[:, 6]
    w_2d = data[:, 7]
    temp_2d = data[:, 8]
    
    # 5x Radial resolution (consistent with visualizer)
    n_slices = 80
    thetas = np.linspace(0, 2*np.pi, n_slices)
    
    with open(output_path, 'w') as f:
        f.write("# vtk DataFile Version 3.0\n")
        f.write("StellarOrion 3D Upscaled Flow Field\n")
        f.write("ASCII\n")
        f.write("DATASET UNSTRUCTURED_GRID\n")
        
        n_pts_2d = len(x_2d)
        total_pts = n_pts_2d * n_slices
        f.write(f"POINTS {total_pts} float\n")
        
        # Calculate all points
        for theta in thetas:
            for i in range(n_pts_2d):
                px = x_2d[i]
                py = y_2d[i] * np.cos(theta)
                pz = y_2d[i] * np.sin(theta)
                f.write(f"{px} {py} {pz}\n")
        
        f.write(f"POINT_DATA {total_pts}\n")
        
        # Temperature
        f.write("SCALARS Temperature float 1\n")
        f.write("LOOKUP_TABLE default\n")
        for _ in range(n_slices):
            for t in temp_2d:
                f.write(f"{t}\n")
                
        # Velocity
        f.write("SCALARS Velocity float 1\n")
        f.write("LOOKUP_TABLE default\n")
        for _ in range(n_slices):
            for i in range(n_pts_2d):
                vel = np.sqrt(u_2d[i]**2 + v_2d[i]**2 + w_2d[i]**2)
                f.write(f"{vel}\n")

        # Mach
        f.write("SCALARS Mach float 1\n")
        f.write("LOOKUP_TABLE default\n")
        for _ in range(n_slices):
            for i in range(n_pts_2d):
                vel = np.sqrt(u_2d[i]**2 + v_2d[i]**2 + w_2d[i]**2)
                safe_temp = max(temp_2d[i], 1.0)
                sound = np.sqrt(1.4 * 287.05 * safe_temp)
                m_val = vel / sound
                if not np.isfinite(m_val): m_val = 0.0
                f.write(f"{m_val}\n")
                
    print(f"[+] VTK Export complete: {output_path}")

def generate_preview(surf_file, output_path, params=None):
    """Generates a 2D preview of the HIAD wall and domain bounds with parameter annotations."""
    print(f"DEBUG: Generating preview from {surf_file}")
    try:
        points = []
        lines = []
        if os.path.exists(surf_file):
            with open(surf_file, 'r') as f:
                content = f.readlines()
                mode = None
                for line in content:
                    if "Points" in line: mode = "pts"; continue
                    if "Lines" in line: mode = "lines"; continue
                    parts = line.split()
                    if not parts or parts[0].isalpha(): continue
                    if mode == "pts" and len(parts) >= 3:
                        points.append([float(parts[1]), float(parts[2])])
                    if mode == "lines" and len(parts) >= 3:
                        lines.append([int(parts[1])-1, int(parts[2])-1])
            print(f"DEBUG: Parsed {len(points)} points and {len(lines)} lines.")
        else:
            print(f"DEBUG: Surf file not found at {surf_file}")
        
        plt.figure(figsize=(10, 6), facecolor='#0f172a')
        ax = plt.gca()
        ax.set_facecolor('#0f172a')
        
        # Plot wall (Full cross-section by reflecting axisymmetry)
        if points and lines:
            for l in lines:
                p1, p2 = points[l[0]], points[l[1]]
                # Upper half
                plt.plot([p1[0], p2[0]], [p1[1], p2[1]], color='#f43f5e', linewidth=3, label='HIAD Wall' if l == lines[0] else "")
                # Lower half reflection
                plt.plot([p1[0], p2[0]], [-p1[1], -p2[1]], color='#f43f5e', linewidth=3)
        else:
            plt.text(0.5, 0.0, "CAD MESH PENDING", color='white', ha='center')
        
        # Domain schematic based on parameters
        xmin = float(params.get('env_xmin', -0.5)) if params else -0.5
        xmax = float(params.get('env_xmax', 1.5)) if params else 1.5
        ymax = float(params.get('env_ymax', 2.0)) if params else 2.0
        
        plt.axvline(x=xmin, color='#38bdf8', linestyle='--', linewidth=2, label='Inlet')
        plt.axvline(x=xmax, color='#10b981', linestyle='--', linewidth=2, label='Outlet')
        plt.axhline(y=0, color='gray', linestyle=':', label='Symmetry Axis')
        
        # Boundary lines for radial extent
        plt.axhline(y=ymax, color='#94a3b8', linestyle='--', alpha=0.5)
        plt.axhline(y=-ymax, color='#94a3b8', linestyle='--', alpha=0.5)
        
        # Add parameter text box
        if params:
            param_text = f"DOMAIN PARAMETERS\n"
            param_text += f"-----------------\n"
            param_text += f"Mass: {params.get('mass', '5000')} kg\n"
            param_text += f"Diameter: {params.get('diameter', '3.0')} m\n"
            param_text += f"Angle: {params.get('angle', '60')} deg\n"
            param_text += f"Preset: {params.get('env_preset', 'Artemis I')}\n"
            
            props = dict(boxstyle='round', facecolor='#1e293b', alpha=0.8, edgecolor='#38bdf8')
            plt.text(0.05, 0.95, param_text, transform=ax.transAxes, fontsize=9,
                     verticalalignment='top', bbox=props, color='white', fontfamily='monospace')

        plt.title("SPARTA DSMC - HIAD Simulation Domain", color='white', fontsize=14, fontweight='bold')
        plt.xlabel("Axial Position (m)", color='#94a3b8')
        plt.ylabel("Radial Position (m)", color='#94a3b8')
        
        legend = plt.legend(facecolor='#1e293b', edgecolor='#38bdf8')
        plt.setp(legend.get_texts(), color='white')
        
        plt.grid(True, alpha=0.1, color='white')
        plt.axis('equal')
        plt.tight_layout()
        plt.savefig(output_path, dpi=300)
        plt.close()
        return True
    except Exception as e:
        print(f"Error generating preview: {e}")
        return False

import matplotlib.animation as animation

def generate_animation(grid_files, output_mp4):
    """Creates an MP4 animation from a sequence of SPARTA grid dump files with smooth contours."""
    if not grid_files: return
    
    # Pre-scan for global temperature range to fix scale
    global_max_temp = 300.0
    for file in grid_files:
        data = parse_grid_dump(file)
        if len(data) > 0:
            global_max_temp = max(global_max_temp, np.nanmax(data[:, 8]))
    
    # Round up to nearest 500 for clean scale
    global_max_temp = (int(global_max_temp // 500) + 1) * 500

    fig, ax = plt.subplots(figsize=(10, 6), facecolor='#0f172a')
    ax.set_facecolor('#0f172a')

    def update(frame):
        ax.clear()
        file = grid_files[frame]
        data = parse_grid_dump(file)
        if len(data) > 0:
            x_center = (data[:, 0] + data[:, 2]) / 2
            y_center = (data[:, 1] + data[:, 3]) / 2
            
            temp = np.maximum(data[:, 8], 0.0) # Ensure no negative Kelvin
            
            # Use fixed levels for consistent color scale across frames
            levels = np.linspace(0, global_max_temp, 50)
            cp = ax.tricontourf(x_center, y_center, np.nan_to_num(temp), levels=levels, cmap='hot', extend='both')
            
            sim_step = frame * 100
            flow_time_ms = sim_step * 1e-6 * 1000 # Assuming 1e-6 timestep
            ax.set_title(f'Thermal Evolution - Step {sim_step} ({flow_time_ms:.2f} ms)', color='white', fontweight='bold')
            ax.set_xlabel('Axial (m)', color='#94a3b8')
            ax.set_ylabel('Radial (m)', color='#94a3b8')
            ax.tick_params(colors='#94a3b8')
            
            # Add colorbar only on first frame or if it doesn't exist
            if not hasattr(update, "cbar"):
                update.cbar = fig.colorbar(cp, ax=ax)
                update.cbar.set_label('Temperature (K)', color='#94a3b8')
                update.cbar.ax.yaxis.set_tick_params(color='#94a3b8', labelcolor='#94a3b8')
            else:
                # Update colorbar with current collection
                update.cbar.update_normal(cp)
        return []

    ani = animation.FuncAnimation(fig, update, frames=len(grid_files), blit=False)
    
    # Save using ffmpeg (with auto-detection)
    ffmpeg_exe = find_ffmpeg()
    writer = animation.FFMpegWriter(fps=5, metadata=dict(artist='StellarOrion'), bitrate=1800, executable=ffmpeg_exe)
    ani.save(output_mp4, writer=writer, dpi=300)
    plt.close()
    print(f"Smooth animation saved to {output_mp4}")

if __name__ == "__main__":
    # Test path
    test_file = "CADDesign/results_reference/grid.1000.out"
    if os.path.exists(test_file):
        generate_plots(test_file, "web/assets/plots")
        upscale_2d_to_3d(test_file, "web/assets/plots/upscaled_3d.png")
