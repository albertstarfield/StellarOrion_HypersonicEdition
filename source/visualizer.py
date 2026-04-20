import numpy as np
import matplotlib.pyplot as plt
import os

# Use non-interactive backend for thread safety in GUI
plt.switch_backend('Agg')

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

    # Plot 1: Temperature Heatmap
    plt.figure(figsize=(10, 6))
    sc = plt.scatter(x_center, y_center, c=temp, cmap='hot', s=50, marker='s')
    plt.colorbar(sc, label='Temperature (K)')
    plt.title('Thermal Map (Temperature)')
    plt.xlabel('Axial (m)')
    plt.ylabel('Radial (m)')
    plt.savefig(os.path.join(output_dir, 'thermal_map.png'))
    plt.close()

    # Plot 2: Pressure Heatmap
    plt.figure(figsize=(10, 6))
    sc = plt.scatter(x_center, y_center, c=press, cmap='jet', s=50, marker='s')
    plt.colorbar(sc, label='Pressure (Pa)')
    plt.title('Pressure Distribution')
    plt.xlabel('Axial (m)')
    plt.ylabel('Radial (m)')
    plt.savefig(os.path.join(output_dir, 'pressure_map.png'))
    plt.close()

    # Plot 3: Velocity Vectors (Quiver)
    plt.figure(figsize=(10, 6))
    # Downsample for clearer vectors
    step = max(1, len(x_center) // 400)
    plt.quiver(x_center[::step], y_center[::step], u[::step], v[::step], 
               np.sqrt(u[::step]**2 + v[::step]**2), cmap='viridis')
    plt.colorbar(label='Velocity Magnitude (m/s)')
    plt.title('Velocity Vectors')
    plt.xlabel('Axial (m)')
    plt.ylabel('Radial (m)')
    plt.savefig(os.path.join(output_dir, 'velocity_vectors.png'))
    plt.close()

    print(f"Plots generated in {output_dir}")

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
        plt.savefig(output_path, dpi=120)
        plt.close()
        return True
    except Exception as e:
        print(f"Error generating preview: {e}")
        return False

import matplotlib.animation as animation

def generate_animation(grid_files, output_mp4):
    """Creates an MP4 animation from a sequence of SPARTA grid dump files."""
    if not grid_files: return
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Pre-parse first file to setup plot
    data = parse_grid_dump(grid_files[0])
    x_center = (data[:, 0] + data[:, 2]) / 2
    y_center = (data[:, 1] + data[:, 3]) / 2
    temp = data[:, 8]
    
    sc = ax.scatter(x_center, y_center, c=temp, cmap='hot', s=40, marker='s')
    cbar = fig.colorbar(sc)
    cbar.set_label('Temperature (K)')
    ax.set_title('Hypersonic Entry Thermal Evolution')
    ax.set_xlabel('Axial (m)')
    ax.set_ylabel('Radial (m)')

    def update(frame):
        file = grid_files[frame]
        d = parse_grid_dump(file)
        if len(d) > 0:
            t = d[:, 8]
            sc.set_array(t)
            ax.set_title(f'Thermal Evolution - Step {frame*1000}')
        return sc,

    ani = animation.FuncAnimation(fig, update, frames=len(grid_files), blit=True)
    
    # Save using ffmpeg
    writer = animation.FFMpegWriter(fps=5, metadata=dict(artist='StellarOrion'), bitrate=1800)
    ani.save(output_mp4, writer=writer)
    plt.close()
    print(f"Animation saved to {output_mp4}")

if __name__ == "__main__":
    # Test path
    test_file = "CADDesign/results_reference/grid.1000.out"
    if os.path.exists(test_file):
        generate_plots(test_file, "web/assets/plots")
