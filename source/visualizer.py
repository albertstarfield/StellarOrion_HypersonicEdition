import numpy as np
import matplotlib.pyplot as plt
import os
import sys
import math
import argparse
import struct

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
                # id xlo ylo xhi yhi f_2[1..4] f_3[1..2] ... f_4[1..N]
                data.append([float(x) for x in parts[1:]])
    return np.array(data)
    
def _add_metadata_overlay(ax, ref_params, extra_info=None):
    """Internal helper to add a metadata box to the top-left of any plot."""
    if not ref_params: return
    
    text_lines = []
    # Environment info
    if 'v_inf' in ref_params: text_lines.append(f"V_inf: {ref_params['v_inf']} m/s")
    if 'mach' in ref_params: text_lines.append(f"Mach: {ref_params['mach']}")
    if 'nrho' in ref_params: 
        try: text_lines.append(f"n_rho: {float(ref_params['nrho']):.1e}")
        except: text_lines.append(f"n_rho: {ref_params['nrho']}")
    if 'temp' in ref_params: text_lines.append(f"T_inf: {ref_params['temp']} K")
    
    # Mesh info
    if 'cells' in ref_params: text_lines.append(f"Cells: {ref_params['cells']}")
    if 'grid_factor' in ref_params: text_lines.append(f"Grid Factor: {ref_params['grid_factor']}")
    
    # Hash info
    if 'git_hash' in ref_params: text_lines.append(f"Build: {ref_params['git_hash']}")
    
    if extra_info:
        text_lines.append(f"[{extra_info}]")
        
    if not text_lines: return
    
    metadata_str = "\n".join(text_lines)
    # Using a semi-transparent slate box with a cyan border to match the StellarOrion theme
    props = dict(boxstyle='round,pad=0.5', facecolor='#0f172a', alpha=0.7, edgecolor='#06b6d4', linewidth=1)
    
    # Check if we are dealing with a 3D axis
    if hasattr(ax, 'get_zlim'):
        ax.text2D(0.02, 0.98, metadata_str, transform=ax.transAxes, fontsize=7,
                 verticalalignment='top', bbox=props, color='white', fontfamily='monospace')
    else:
        ax.text(0.02, 0.98, metadata_str, transform=ax.transAxes, fontsize=7,
                 verticalalignment='top', bbox=props, color='white', fontfamily='monospace', zorder=100)

try:
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'CADDesign'))
    from HIAD_GeometryEngine import draw_analytical_slice
except ImportError:
    def draw_analytical_slice(*args, **kwargs):
        print("Warning: HIAD_GeometryEngine not found. Analytical overlay disabled.")

def _parse_stl(file_path):
    """Parses an STL file (ASCII or Binary) and returns a list of triangles."""
    if not os.path.exists(file_path):
        return []
        
    triangles = []
    try:
        # Try ASCII first
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            idx = 0
            while idx < len(lines):
                line = lines[idx].strip()
                if line.startswith("facet normal"):
                    v_found = []
                    search_idx = idx + 1
                    while len(v_found) < 3 and search_idx < len(lines):
                        sub_line = lines[search_idx].strip()
                        if sub_line.startswith("vertex"):
                            parts = sub_line.split()
                            v_found.append([float(parts[1]), float(parts[2]), float(parts[3])])
                        search_idx += 1
                    if len(v_found) == 3:
                        triangles.append(v_found)
                    idx = search_idx
                else:
                    idx += 1
    except (UnicodeDecodeError, Exception):
        # Fallback to Binary STL parser
        try:
            with open(file_path, 'rb') as f:
                header = f.read(80)
                n_facets_raw = f.read(4)
                if len(n_facets_raw) < 4: return []
                n_facets = struct.unpack('<I', n_facets_raw)[0]
                
                for _ in range(n_facets):
                    # facet = normal (12) + 3 vertices (3*12=36) + attr (2) = 50 bytes
                    data = f.read(50)
                    if len(data) < 50: break
                    # Skip normal (0:12)
                    v1 = struct.unpack('<fff', data[12:24])
                    v2 = struct.unpack('<fff', data[24:36])
                    v3 = struct.unpack('<fff', data[36:48])
                    triangles.append([list(v1), list(v2), list(v3)])
        except Exception as e:
            print(f"[DEBUG] Binary STL Parse error: {e}")
            
    if not triangles:
        return None
            
    return np.array(triangles)

def _overlay_geometry(ax, surf_file, ref_params=None):
    """Overlays the full analytical HIAD slice on the current plot."""
    is_orion = ref_params and ref_params.get('target_vehicle', '').upper() == 'ORION'
    if not ref_params or is_orion:
        # Fallback to simple surf overlay
        if surf_file and os.path.exists(surf_file):
            points = []
            with open(surf_file, 'r') as f:
                mode = None
                for line in f:
                    if "Points" in line: mode = "pts"; continue
                    parts = line.split()
                    if not parts or parts[0].isalpha(): continue
                    if mode == "pts" and len(parts) >= 3:
                        points.append([float(parts[1]), float(parts[2])])
            if points:
                pts = np.array(points)
                ax.plot(pts[:, 0], pts[:, 1], color='#f43f5e', linewidth=2.5, label='HIAD Wall', zorder=10)
                ax.plot(pts[:, 0], -pts[:, 1], color='#f43f5e', linewidth=2.5, zorder=10)
        return
    
    # We need to reconstruct the parameters for draw_analytical_slice
    try:
        # Extract params (converting m to mm where needed for the drawing function)
        d_m = float(ref_params.get('diameter', 3.0))
        angle = float(ref_params.get('angle', 60.0))
        toroid_count = int(ref_params.get('toroids', 7))
        toroid_radius = float(ref_params.get('toroid_radius', 0.135)) * 1000.0
        shoulder_torus_radius = float(ref_params.get('shoulder_radius', 0.09)) * 1000.0
        nose_radius = float(ref_params.get('nose_radius', 0.55)) * 1000.0
        payload_height = float(ref_params.get('mass_center', 1700.0)) # Proxy for height if not present
        
        # Derived values needed for drawing
        theta_c_rad = math.radians(angle)
        z_tangency = nose_radius * (1.0 - math.sin(theta_c_rad))
        r_tangency = nose_radius * math.cos(theta_c_rad)
        r_target = (d_m * 1000.0) / 2.0
        z_nose_center = nose_radius
        z_back = payload_height # mm
        
        skin_data = []
        # Nose
        for beta in np.linspace(-math.pi/2.0, -theta_c_rad, 20):
            skin_data.append((nose_radius * math.cos(beta), nose_radius + nose_radius * math.sin(beta)))
        # Toroids
        scallop_angle = 140.0
        gamma = math.radians(scallop_angle / 2.0)
        for i in range(toroid_count + 1):
            if i < toroid_count:
                s_c = (2*i + 1) * toroid_radius
                rad = toroid_radius
            else:
                s_c = (2 * toroid_count - 1) * toroid_radius + toroid_radius + shoulder_torus_radius
                rad = shoulder_torus_radius
                
            rs = r_tangency + s_c * math.sin(theta_c_rad)
            zs = z_tangency + s_c * math.cos(theta_c_rad)
            cr = rs - rad * math.cos(theta_c_rad)
            cz = zs + rad * math.sin(theta_c_rad)
            
            for alpha in np.linspace(-theta_c_rad - gamma, -theta_c_rad + gamma, 24):
                skin_data.append((cr + rad * math.cos(alpha), cz + rad * math.sin(alpha)))
        
        payload_enabled = ref_params.get('payload', False)
        r_last, z_last = skin_data[-1]
        
        if payload_enabled:
            r_pay = float(ref_params.get('payload_radius', 0.5)) * 1000.0
            skin_data.append((r_pay, z_last))
            skin_data.append((r_pay, z_back))
            skin_data.append((0.0, z_back))
        else:
            thickness = 10.0 # mm
            for alpha in np.linspace(0, math.pi, 15):
                skin_data.append((r_last + thickness * math.sin(alpha), z_last + thickness * math.cos(alpha)))
            front_pts = skin_data[:len(skin_data)-15]
            for r, z in reversed(front_pts):
                skin_data.append((max(0.0, r), z - thickness))
            skin_data.append((0.0, -thickness))
            z_back = -thickness
        
        skin_data_m = [(p[0]/1000.0, p[1]/1000.0) for p in skin_data]
        
        draw_analytical_slice(ax, skin_data_m, toroid_count, toroid_radius/1000.0, shoulder_torus_radius/1000.0,
                              z_tangency/1000.0, r_tangency/1000.0, theta_c_rad, r_target/1000.0, 
                              z_nose_center/1000.0, nose_radius/1000.0, z_back/1000.0,
                              label_toroids=True)
                              
    except Exception as e:
        print(f"Warning: Analytical overlay failed: {e}")
        # Fallback to simple surf overlay
        if surf_file and os.path.exists(surf_file):
            points = []
            with open(surf_file, 'r') as f:
                mode = None
                for line in f:
                    if "Points" in line: mode = "pts"; continue
                    parts = line.split()
                    if not parts or parts[0].isalpha(): continue
                    if mode == "pts" and len(parts) >= 3:
                        points.append([float(parts[1]), float(parts[2])])
            if points:
                pts = np.array(points)
                ax.plot(pts[:, 0], pts[:, 1], color='#f43f5e', linewidth=2.5, label='HIAD Wall', zorder=10)
                ax.plot(pts[:, 0], -pts[:, 1], color='#f43f5e', linewidth=2.5, zorder=10)

def clean_for_tri(v):
    return np.nan_to_num(v, nan=0.0, posinf=0.0, neginf=0.0)

def _get_masked_triangulation(x, y, values, nrho=None, n_max=1.0, threshold_ratio=0.001):
    import matplotlib.tri as tri
    triang = tri.Triangulation(x, y)
    
    # Vertex is invalid if value is NaN or density is below threshold
    invalid = np.isnan(values)
    if nrho is not None and len(nrho) == len(x):
        invalid |= (nrho <= 0)
        
    mask = np.any(invalid[triang.triangles], axis=1)
    triang.set_mask(mask)
    return triang

def generate_plots(grid_file, output_dir, suffix="", ref_params=None, surf_file=None):
    os.makedirs(output_dir, exist_ok=True)
    data = parse_grid_dump(grid_file)
    if len(data) == 0:
        print(f"Error: No data found in {grid_file}")
        return

    # Filter out any rows with NaNs or Infs in core columns
    valid_mask = np.all(np.isfinite(data[:, :10]), axis=1)
    data = data[valid_mask]
    if len(data) == 0:
        print(f"Error: No valid finite data points in {grid_file}")
        return

    if ref_params is not None and 'cells' not in ref_params:
        ref_params['cells'] = len(data)

    x_center = (data[:, 0] + data[:, 2]) / 2
    y_center = (data[:, 1] + data[:, 3]) / 2
    
    n = data[:, 4]
    u = data[:, 5]
    v = data[:, 6]
    w = data[:, 7]
    temp = data[:, 8]
    nrho = data[:, 9] # data index 9 is f_4[1] which is nrho
    
    # Calculate physical pressure P = n * k * T
    # k_B = 1.380649e-23 J/K
    press = nrho * 1.380649e-23 * temp

    print(f"[DEBUG] Data ranges in {os.path.basename(grid_file)}:")
    print(f"    - N:    {np.min(n):.1f} to {np.max(n):.1f}")
    print(f"    - U:    {np.min(u):.1f} to {np.max(u):.1f} m/s (mean: {np.mean(u):.1f})")
    print(f"    - V:    {np.min(v):.1f} to {np.max(v):.1f} m/s")
    print(f"    - Temp: {np.min(temp):.1f} to {np.max(temp):.1f} K")
    print(f"    - Pres: {np.min(press):.1e} to {np.max(press):.1e} Pa")

    # --- Density Masking to prevent non-physical artifacts inside body/vacuum ---
    # Threshold: 0.1% of max density in the domain
    # Threshold: 1% of the 95th percentile density to prevent outlier-driven masking
    n_max = np.percentile(nrho, 95)
    density_mask = nrho < (n_max * 0.01) 
    
    # Apply masking (set to NaN to avoid "heat inside wall" interpolation bleeding)
    temp[density_mask] = np.nan
    press[density_mask] = np.nan
    u[density_mask] = np.nan
    v[density_mask] = np.nan

    # --- Axisymmetric Mirroring for Visualization ---
    eps = 1e-6
    mask_mirror = y_center > eps
    x_mirrored = np.concatenate([x_center, x_center[mask_mirror]])
    y_mirrored = np.concatenate([y_center, -y_center[mask_mirror]])
    temp_mirrored = np.concatenate([temp, temp[mask_mirror]])
    press_mirrored = np.concatenate([press, press[mask_mirror]])
    n_mirrored = np.concatenate([n, n[mask_mirror]])
    nrho_mirrored = np.concatenate([nrho, nrho[mask_mirror]])
    u_mirrored = np.concatenate([u, u[mask_mirror]])
    v_mirrored = np.concatenate([v, -v[mask_mirror]]) 
    w_mirrored = np.concatenate([w, w[mask_mirror]])

    # Plot 1: Thermal Map (Temperature)
    fig = plt.figure(figsize=(12, 7), facecolor='#0f172a')
    ax = plt.gca(); ax.set_facecolor('#0f172a')
    
    n_max_mirrored = np.nanmax(nrho_mirrored) if len(nrho_mirrored) > 0 else 1.0
    triang = _get_masked_triangulation(x_mirrored, y_mirrored, temp_mirrored, nrho_mirrored, n_max_mirrored, 0.001)
    
    if triang.mask is None or not np.all(triang.mask):
        sc = plt.tricontourf(triang, np.nan_to_num(temp_mirrored, nan=0.0), levels=50, cmap='hot')
        plt.colorbar(sc, label='Temperature (K)')
    else:
        print("Warning: No valid temperature data for contouring")
    plt.title('Thermal Map (Temperature)', color='white', fontweight='800', fontsize=16)
    plt.xlabel('Axial (m)', color='#94a3b8')
    plt.ylabel('Radial (m)', color='#94a3b8')
    plt.tick_params(colors='#94a3b8')
    if ref_params:
        # Show from inlet to near end of domain to capture shock layer
        plt.xlim(float(ref_params.get('env_xmin', -0.6)), float(ref_params.get('env_xmax', 2.5)))
        if 'env_ymax' in ref_params:
            plt.ylim(-float(ref_params['env_ymax']), float(ref_params['env_ymax']))

    _overlay_geometry(plt.gca(), surf_file, ref_params=ref_params)
    _add_metadata_overlay(plt.gca(), ref_params, extra_info="Thermal Map")
    plt.gca().set_aspect('equal', adjustable='box')
    plt.savefig(os.path.join(output_dir, f'thermal_map{suffix}.png'), facecolor=fig.get_facecolor(), edgecolor='none', dpi=300)
    plt.savefig(os.path.join(output_dir, f'thermal_map{suffix}.jpg'), facecolor=fig.get_facecolor(), edgecolor='none', pil_kwargs={'quality': 85}, dpi=300)
    plt.close()

    # Plot 2: Pressure Contour Heatmap
    fig = plt.figure(figsize=(12, 7), facecolor='#0f172a')
    ax = plt.gca(); ax.set_facecolor('#0f172a')
    
    triang = _get_masked_triangulation(x_mirrored, y_mirrored, press_mirrored, nrho_mirrored, n_max_mirrored, 0.001)
    if triang.mask is None or not np.all(triang.mask):
        sc = plt.tricontourf(triang, np.nan_to_num(press_mirrored, nan=0.0), levels=50, cmap='jet')
        plt.colorbar(sc, label='Pressure (Pa)')
    else:
        print("Warning: No valid pressure data for contouring")
    plt.title('Pressure Distribution', color='white', fontweight='800', fontsize=16)
    plt.xlabel('Axial (m)', color='#94a3b8')
    plt.ylabel('Radial (m)', color='#94a3b8')
    plt.tick_params(colors='#94a3b8')
    if ref_params:
        plt.xlim(float(ref_params.get('env_xmin', -0.6)), float(ref_params.get('env_xmax', 2.5)))
        if 'env_ymax' in ref_params:
            plt.ylim(-float(ref_params['env_ymax']), float(ref_params['env_ymax']))

    _overlay_geometry(plt.gca(), surf_file, ref_params=ref_params)
    _add_metadata_overlay(plt.gca(), ref_params, extra_info="Pressure Map")
    plt.gca().set_aspect('equal', adjustable='box')
    plt.savefig(os.path.join(output_dir, f'pressure_map{suffix}.png'), facecolor=fig.get_facecolor(), edgecolor='none', dpi=300)
    plt.savefig(os.path.join(output_dir, f'pressure_map{suffix}.jpg'), facecolor=fig.get_facecolor(), edgecolor='none', pil_kwargs={'quality': 85}, dpi=300)
    plt.close()

    # Plot 3: Velocity Vectors (Quiver)
    fig = plt.figure(figsize=(12, 7), facecolor='#0f172a')
    ax = plt.gca(); ax.set_facecolor('#0f172a')
    vel_mag_mirrored = np.sqrt(u_mirrored**2 + v_mirrored**2)
    valid_v = ~np.isnan(vel_mag_mirrored)
    if np.sum(valid_v) >= 4:
        from scipy.interpolate import griddata
        
        # Create a uniform grid for the quiver plot
        grid_x, grid_y = np.mgrid[x_mirrored.min():x_mirrored.max():40j, y_mirrored.min():y_mirrored.max():30j]
        
        # Interpolate U and V components onto the grid
        grid_u = griddata((x_mirrored[valid_v], y_mirrored[valid_v]), u_mirrored[valid_v], (grid_x, grid_y), method='linear')
        grid_v = griddata((x_mirrored[valid_v], y_mirrored[valid_v]), v_mirrored[valid_v], (grid_x, grid_y), method='linear')
        grid_mag = np.sqrt(grid_u**2 + grid_v**2)
        
        # Plot the interpolated quiver
        q = plt.quiver(grid_x, grid_y, grid_u, grid_v, grid_mag, cmap='viridis')
        plt.colorbar(q, label='Velocity Magnitude (m/s)')
    else:
        print("Warning: No valid velocity data for quiver")
    plt.title('Velocity Vectors', color='white', fontweight='800', fontsize=16)
    plt.xlabel('Axial (m)', color='#94a3b8')
    plt.ylabel('Radial (m)', color='#94a3b8')
    plt.tick_params(colors='#94a3b8')
    _overlay_geometry(plt.gca(), surf_file, ref_params=ref_params)
    _add_metadata_overlay(plt.gca(), ref_params, extra_info="Velocity Quiver")
    plt.gca().set_aspect('equal', adjustable='box')
    plt.savefig(os.path.join(output_dir, f'velocity_vectors{suffix}.png'), facecolor=fig.get_facecolor(), edgecolor='none', dpi=300)
    plt.savefig(os.path.join(output_dir, f'velocity_vectors{suffix}.jpg'), facecolor=fig.get_facecolor(), edgecolor='none', pil_kwargs={'quality': 85}, dpi=300)
    plt.close()

    # Plot 4: Mach Number Contour
    fig = plt.figure(figsize=(12, 7), facecolor='#0f172a')
    ax = plt.gca(); ax.set_facecolor('#0f172a')
    vel_total_mirrored = np.sqrt(u_mirrored**2 + v_mirrored**2 + w_mirrored**2)
    
    # Use physics-based parameters from ref_params or fallback to Mars
    preset = str(ref_params.get('env_preset', 'mars')).lower()
    if 'mars' in preset:
        gamma = 1.29
        R = 188.9
    else:
        gamma = 1.4
        R = 287.05
        
    safe_temp_mirrored = np.maximum(temp_mirrored, 1.0) 
    sound_speed_mirrored = np.sqrt(gamma * R * safe_temp_mirrored)
    mach_mirrored = vel_total_mirrored / sound_speed_mirrored
    
    # Mask out non-physical high Mach numbers in vacuum/low-density regions
    nrho_inf = float(ref_params.get('n_rho', 1e20))
    nrho_mirrored = np.concatenate([nrho, nrho[mask_mirror]])
    mach_mirrored[nrho_mirrored < 1e-4 * nrho_inf] = 0.0
    
    # Cap Mach number for visualization clarity (avoids extreme outliers)
    m_inf = float(ref_params.get('mach', 10.0))
    
    # Mask low density regions in Mach map too (using mirrored nrho)
    n_max_mirrored = np.nanmax(nrho_mirrored) if len(nrho_mirrored) > 0 else 1.0
    density_mask_mirrored = nrho_mirrored <= 0
    mach_mirrored[density_mask_mirrored] = np.nan
    
    # NaN-safe clipping
    mach_mirrored = np.where(np.isnan(mach_mirrored), np.nan, np.clip(mach_mirrored, 0, m_inf * 1.5))
    
    triang = _get_masked_triangulation(x_mirrored, y_mirrored, mach_mirrored, nrho_mirrored, n_max_mirrored, 0.01)
    if triang.mask is None or not np.all(triang.mask):
        sc = plt.tricontourf(triang, np.nan_to_num(mach_mirrored, nan=0.0), levels=50, cmap='plasma')
        plt.colorbar(sc, label='Mach Number')
        try:
            # Only plot sonic line if we have Mach > 1 and < 1
            if np.nanmax(mach_mirrored) > 1.0 and np.nanmin(mach_mirrored) < 1.0:
                plt.tricontour(triang, np.nan_to_num(mach_mirrored, nan=0.0), levels=[1.0], colors='white', linestyles='--', linewidths=1.5)
        except: pass
    else:
        print("Warning: No valid Mach data for contouring")
    plt.title('Mach Number Distribution', color='white', fontweight='800', fontsize=16)
    plt.xlabel('Axial (m)', color='#94a3b8')
    plt.ylabel('Radial (m)', color='#94a3b8')
    plt.tick_params(colors='#94a3b8')
    if ref_params:
        plt.xlim(float(ref_params.get('env_xmin', -0.6)), float(ref_params.get('env_xmax', 2.5)))
        if 'env_ymax' in ref_params:
            plt.ylim(-float(ref_params['env_ymax']), float(ref_params['env_ymax']))

    _overlay_geometry(plt.gca(), surf_file, ref_params=ref_params)
    _add_metadata_overlay(plt.gca(), ref_params, extra_info="Mach Number")
    plt.gca().set_aspect('equal', adjustable='box')
    plt.savefig(os.path.join(output_dir, f'mach_map{suffix}.png'), facecolor=fig.get_facecolor(), edgecolor='none', dpi=300)
    plt.savefig(os.path.join(output_dir, f'mach_map{suffix}.jpg'), facecolor=fig.get_facecolor(), edgecolor='none', pil_kwargs={'quality': 85}, dpi=300)
    plt.close()

    # Plot 5: Grid Visualization
    fig = plt.figure(figsize=(12, 7), facecolor='#0f172a')
    plt.gca().set_facecolor('#0f172a')
    plt.scatter(x_mirrored, y_mirrored, s=0.5, color='#38bdf8', alpha=0.3, label='Cell Centers')
    step = max(1, len(data) // 2000)
    for i in range(0, len(data), step):
        xlo, ylo, xhi, yhi = data[i, 0], data[i, 1], data[i, 2], data[i, 3]
        plt.gca().add_patch(plt.Rectangle((xlo, ylo), xhi-xlo, yhi-ylo, fill=False, edgecolor='#38bdf8', linewidth=0.3, alpha=0.4))
        plt.gca().add_patch(plt.Rectangle((xlo, -yhi), xhi-xlo, yhi-ylo, fill=False, edgecolor='#38bdf8', linewidth=0.3, alpha=0.4))
    plt.title('SPARTA Adaptive Mesh Grid', color='white', fontweight='800', fontsize=16)
    plt.xlabel('Axial (m)', color='#94a3b8')
    plt.ylabel('Radial (m)', color='#94a3b8')
    plt.tick_params(colors='#94a3b8')
    _overlay_geometry(plt.gca(), surf_file, ref_params=ref_params)
    plt.gca().set_aspect('equal', adjustable='box')
    plt.savefig(os.path.join(output_dir, f'grid_mesh_map{suffix}.png'), facecolor=fig.get_facecolor(), edgecolor='none', dpi=300)
    plt.close()

    # Plot 6: Local Knudsen Number
    generate_knudsen_plot(x_mirrored, y_mirrored, n_mirrored, nrho_mirrored, output_dir, suffix=suffix, ref_params=ref_params, surf_file=surf_file)

    # Plot 7: Species Concentrations
    if data.shape[1] > 10:
        species_data = data[:, 10:]
        species_mirrored = np.concatenate([species_data, species_data[mask_mirror]], axis=0)
        generate_species_plots(x_mirrored, y_mirrored, species_mirrored, nrho_mirrored, output_dir, suffix=suffix, ref_params=ref_params, surf_file=surf_file)

    # Plot 8: Scallop Pocket Profile
    generate_scallop_profile_plot(data, output_dir, suffix=suffix, ref_params=ref_params, surf_file=surf_file)

    # Plot 9: Stagnation Streamline Graph (1D)
    generate_stagnation_graph(data, output_dir, suffix=suffix, ref_params=ref_params)
    
    # Plot 10: Residence Time
    generate_residence_time_plot(x_mirrored, y_mirrored, u_mirrored, v_mirrored, output_dir, suffix=suffix, ref_params=ref_params, surf_file=surf_file)

    print(f"Plots generated in {output_dir}")

def generate_stagnation_graph(data, output_dir, suffix="", ref_params=None):
    """Generates a 1D graph of properties along the stagnation streamline (y=0) and detects the bow shock."""
    x_center = (data[:, 0] + data[:, 2]) / 2
    y_center = (data[:, 1] + data[:, 3]) / 2
    temp = data[:, 8]
    press = data[:, 9]

    if len(y_center) == 0: return
    min_y = np.min(np.abs(y_center))
    mask = np.abs(y_center) < (min_y + 0.05) 
    
    x_stag_raw = x_center[mask]
    t_stag_raw = temp[mask]
    p_stag_raw = press[mask]

    if len(x_stag_raw) < 5: return

    # Average properties for cells with the same X to avoid np.gradient divide-by-zero
    x_stag, unique_indices = np.unique(np.round(x_stag_raw, 6), return_inverse=True)
    t_stag = np.zeros_like(x_stag)
    p_stag = np.zeros_like(x_stag)
    for i in range(len(x_stag)):
        t_stag[i] = np.mean(t_stag_raw[unique_indices == i])
        p_stag[i] = np.mean(p_stag_raw[unique_indices == i])

    # Detect Shock Position: Max temperature gradient
    dt_dx = np.abs(np.gradient(t_stag, x_stag))
    shock_idx = np.argmax(dt_dx)
    x_shock = x_stag[shock_idx]
    t_shock = t_stag[shock_idx]

    x_nose = 0.0
    if ref_params and 'x_nose' in ref_params:
        x_nose = float(ref_params['x_nose'])
    else:
        valid_t_mask = ~np.isnan(t_stag)
        if np.any(valid_t_mask):
            t_max = np.nanmax(t_stag)
            eligible_x = x_stag[valid_t_mask & (t_stag > t_max * 0.8)]
            if len(eligible_x) > 0:
                x_nose = np.min(eligible_x)
            else:
                x_nose = 0.0
        else:
            x_nose = 0.0

    standoff = x_nose - x_shock
    
    fig, ax1 = plt.subplots(figsize=(12, 7))
    ax1.set_facecolor('#0f172a')
    fig.patch.set_facecolor('#0f172a')
    color_t = '#f43f5e'
    ax1.set_xlabel('Axial Position (m)', color='#94a3b8', fontsize=12)
    ax1.set_ylabel('Temperature (K)', color=color_t, fontsize=12)
    ax1.plot(x_stag, t_stag, color=color_t, linewidth=3, label='Temperature')
    ax1.tick_params(axis='y', labelcolor=color_t, colors='#94a3b8')
    ax1.tick_params(axis='x', colors='#94a3b8')
    ax2 = ax1.twinx()
    color_p = '#38bdf8'
    ax2.set_ylabel('Pressure (Pa)', color=color_p, fontsize=12)
    ax2.plot(x_stag, p_stag, color=color_p, linewidth=2, linestyle='--', alpha=0.8, label='Pressure')
    ax2.tick_params(axis='y', labelcolor=color_p, colors='#94a3b8')
    ax1.axvline(x=x_shock, color='yellow', linestyle=':', linewidth=2, alpha=0.8)
    ax1.annotate('BOW SHOCK', xy=(x_shock, t_shock), xytext=(x_shock - 0.2, t_shock + 2000),
                arrowprops=dict(facecolor='yellow', shrink=0.05, width=1, headwidth=5),
                color='yellow', fontsize=10, fontweight='bold', ha='center')
    if standoff > 0:
        ax1.annotate('', xy=(x_shock, 500), xytext=(x_nose, 500),
                    arrowprops=dict(arrowstyle='<->', color='#10b981', lw=1.5))
        ax1.text((x_shock + x_nose)/2, 600, f'Standoff: {standoff*1000:.1f} mm', 
                 color='#10b981', fontsize=9, ha='center', fontweight='bold')
    plt.title('Hypersonic Bow Shock Profile (Stagnation Line)', color='white', fontsize=16, fontweight='800')
    ax1.grid(True, alpha=0.1, color='white', linestyle='-')
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc='upper right', facecolor='#1e293b', edgecolor='#334155', labelcolor='white')
    _add_metadata_overlay(ax1, ref_params, extra_info="Shock Standoff Analysis")
    fig.tight_layout()
    plt.savefig(os.path.join(output_dir, f'shock_stagnation_profile{suffix}.png'), facecolor=fig.get_facecolor(), dpi=300)
    plt.close()

def generate_knudsen_plot(x, y, n, nrho, output_dir, suffix="", ref_params=None, surf_file=None):
    """Plots the local Knudsen number map to show kinetic vs continuum dominance."""
    fig = plt.figure(figsize=(10, 6), facecolor='#0f172a')
    plt.gca().set_facecolor('#0f172a')
    d_mol = 3.7e-10 # m (Air)
    n_safe = np.maximum(np.nan_to_num(n), 1.0)
    mfp = 1.0 / (np.sqrt(2) * np.pi * (d_mol**2) * n_safe)
    L = float(ref_params.get('nose_radius', 0.55)) if ref_params else 0.55
    kn_local = mfp / L
    import matplotlib.colors as mcolors
    kn_plot = np.clip(kn_local, 1e-5, 10.0)
    
    # Mask low density / vacuum regions
    n_max = np.nanmax(nrho) if len(nrho) > 0 else 1.0
    kn_plot[nrho < n_max * 0.001] = np.nan
    
    triang = _get_masked_triangulation(x, y, kn_plot, nrho, n_max, 0.001)
    
    levels = np.logspace(-5, 1, 50)
    if triang.mask is None or not np.all(triang.mask):
        sc = plt.tricontourf(triang, np.nan_to_num(kn_plot, nan=1e-5), levels=levels, norm=mcolors.LogNorm(), cmap='RdYlBu_r')
        plt.colorbar(sc, label='Local Knudsen Number (Kn)')
    else:
        print("Warning: No valid Knudsen data for contouring")
    plt.title('Rarefaction Map (Knudsen)', color='white', fontweight='bold')
    plt.text(0.05, 0.05, "Red: Kinetic Dominance (Kn > 0.1)\nBlue: Continuum (Kn < 0.01)", 
             transform=plt.gca().transAxes, color='white', fontsize=8, alpha=0.6)
    plt.xlabel('Axial (m)', color='#94a3b8')
    plt.ylabel('Radial (m)', color='#94a3b8')
    _overlay_geometry(plt.gca(), surf_file, ref_params=ref_params)
    _add_metadata_overlay(plt.gca(), ref_params, extra_info="Rarefaction Study")
    plt.gca().set_aspect('equal', adjustable='box')
    plt.savefig(os.path.join(output_dir, f'knudsen_map{suffix}.png'), facecolor=fig.get_facecolor(), edgecolor='none', dpi=300)
    plt.savefig(os.path.join(output_dir, f'knudsen_map{suffix}.jpg'), facecolor=fig.get_facecolor(), edgecolor='none', pil_kwargs={'quality': 85}, dpi=300)
    plt.close()

def generate_residence_time_plot(x, y, u, v, output_dir, suffix="", ref_params=None, surf_file=None):
    """Plots inverse velocity to identify flow stagnation and trapping zones."""
    fig = plt.figure(figsize=(10, 6), facecolor='#0f172a')
    plt.gca().set_facecolor('#0f172a')
    vel_mag = np.sqrt(u**2 + v**2)
    res_time = 1.0 / np.maximum(vel_mag, 10.0) 
    
    triang = _get_masked_triangulation(x, y, res_time)
    if triang.mask is None or not np.all(triang.mask):
        sc = plt.tricontourf(triang, np.nan_to_num(res_time, nan=0.0), levels=50, cmap='inferno')
        plt.colorbar(sc, label='Residence Time Proxy (s/m)')
    else:
        print("Warning: No valid residence time data for contouring")
    plt.title('Flow Stagnation / Trapping Zones', color='white', fontweight='bold')
    plt.xlabel('Axial (m)', color='#94a3b8')
    plt.ylabel('Radial (m)', color='#94a3b8')
    _overlay_geometry(plt.gca(), surf_file, ref_params=ref_params)
    _add_metadata_overlay(plt.gca(), ref_params, extra_info="Residence Time")
    plt.gca().set_aspect('equal', adjustable='box')
    plt.savefig(os.path.join(output_dir, f'residence_time_map{suffix}.png'), facecolor=fig.get_facecolor(), edgecolor='none', dpi=300)
    plt.close()

def generate_species_plots(x, y, species_nrho, nrho, output_dir, suffix="", ref_params=None, surf_file=None):
    """Plots concentration contours for all simulated species."""
    n_species = species_nrho.shape[1]
    species_names = ref_params.get('species_list', [f"Species_{i}" for i in range(n_species)])
    n_total = np.maximum(np.sum(species_nrho, axis=1), 1.0)
    n_max = np.nanmax(nrho) if len(nrho) > 0 else 1.0
    for i in range(min(n_species, 5)):
        fig = plt.figure(figsize=(10, 6), facecolor='#0f172a')
        plt.gca().set_facecolor('#0f172a')
        frac = species_nrho[:, i] / n_total
        
        # Mask vacuum
        frac[nrho < n_max * 0.001] = np.nan
        triang = _get_masked_triangulation(x, y, frac, nrho, n_max, 0.001)
        if triang.mask is None or not np.all(triang.mask):
            sc = plt.tricontourf(triang, np.nan_to_num(frac, nan=0.0), levels=50, cmap='viridis')
            plt.colorbar(sc, label=f'Mole Fraction (χ_{species_names[i]})')
        else:
            print(f"Warning: No valid species data for {species_names[i]}")
        plt.title(f'Species Distribution: {species_names[i]}', color='white', fontweight='bold')
        plt.xlabel('Axial (m)', color='#94a3b8')
        plt.ylabel('Radial (m)', color='#94a3b8')
        _overlay_geometry(plt.gca(), surf_file, ref_params=ref_params)
        _add_metadata_overlay(plt.gca(), ref_params, extra_info=f"Chemistry: {species_names[i]}")
        plt.gca().set_aspect('equal', adjustable='box')
        plt.savefig(os.path.join(output_dir, f'species_{species_names[i]}_map{suffix}.png'), facecolor=fig.get_facecolor(), edgecolor='none', dpi=300)
        plt.close()

def generate_scallop_profile_plot(data, output_dir, suffix="", ref_params=None, surf_file=None):
    """Plots temperature profile specifically comparing wall proximity vs scallop center."""
    x = (data[:, 0] + data[:, 2]) / 2
    y = (data[:, 1] + data[:, 3]) / 2
    temp = data[:, 8]
    mid_y = np.median(y)
    mask = (y > mid_y - 0.1) & (y < mid_y + 0.1)
    x_gap = x[mask]
    t_gap = temp[mask]
    if len(x_gap) == 0: return
    idx = np.argsort(x_gap)
    x_gap = x_gap[idx]
    t_gap = t_gap[idx]
    plt.figure(figsize=(10, 6))
    plt.gca().set_facecolor('#0f172a')
    plt.plot(x_gap, t_gap, color='#06b6d4', linewidth=2, label='Pocket Center Temp')
    plt.title('Scallop Pocket Thermal Probe', color='white', fontweight='bold')
    plt.xlabel('Axial Position (m)', color='#94a3b8')
    plt.ylabel('Temperature (K)', color='#94a3b8')
    plt.grid(True, alpha=0.1)
    plt.legend()
    _add_metadata_overlay(plt.gca(), ref_params, extra_info="Scallop Thermal Probe")
    plt.savefig(os.path.join(output_dir, f'scallop_pocket_temp{suffix}.png'), dpi=300)
    plt.close()

def generate_convergence_plot(log_lines, output_dir, suffix="", ref_params=None):
    """Generates graphs of global metrics and residuals."""
    steps, drag, lift, heat, np_part, ncoll, t_trans, t_rot, t_vib = [], [], [], [], [], [], [], [], []
    q, area, mass, duration, diameter, toroid_radius = 1.0, 1.0, 281.0, 450.0, 3.0, 0.135
    if ref_params:
        rho = ref_params.get('rho', 1.0); v = ref_params.get('v', 1.0)
        area = ref_params.get('area', 1.0); q = 0.5 * rho * v**2
        mass = ref_params.get('mass', 281.0); duration = ref_params.get('duration', 450.0)
        diameter = ref_params.get('diameter', 3.0); toroid_radius = ref_params.get('toroid_radius', 0.135)
    for line in log_lines:
        parts = line.split()
        if len(parts) >= 12 and parts[0].isdigit():
            try:
                steps.append(int(parts[0])); np_part.append(float(parts[2]))
                drag.append(float(parts[3])); lift.append(float(parts[4]))
                heat.append(float(parts[5])); t_trans.append(float(parts[6]))
                t_rot.append(float(parts[7])); t_vib.append(float(parts[8]))
                ncoll.append(float(parts[10]))
            except: continue
    if not steps: return
    os.makedirs(output_dir, exist_ok=True)
    def calc_residuals(data):
        res = [1.0]
        for i in range(1, len(data)):
            denom = abs(data[i]) if abs(data[i]) > 1e-10 else 1.0
            res.append(max(1e-7, abs(data[i] - data[i-1]) / denom))
        return res
    steps_arr = np.array(steps); drag_arr = np.array(drag)
    cd = drag_arr / (q * area) if q * area > 0 else np.zeros_like(drag_arr)
    cl = np.array(lift) / (q * area) if q * area > 0 else np.zeros_like(drag_arr)
    beta = np.nan_to_num(mass / (cd * area), nan=0.0, posinf=0.0, neginf=0.0) if area > 0 else np.zeros_like(cd)
    decel = drag_arr / (mass * 9.81) if mass > 0 else np.zeros_like(drag_arr)
    stag_press = cd * q
    heat_load_inst = np.array(heat) * duration * 1e-4
    
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.set_facecolor('#0f172a'); fig.patch.set_facecolor('#0f172a')
    ax.set_yscale('log')
    ax.plot(steps, calc_residuals(cd), color='#f59e0b', label='Drag Coeff (Cd)')
    ax.plot(steps, calc_residuals(cl), color='#38bdf8', label='Lift Coeff (Cl)', linestyle='--')
    ax.plot(steps, calc_residuals(heat), color='#ef4444', label='Heat Flux (q̇)')
    ax.legend(); plt.title('Multi-Variable Convergence Residuals', color='white')
    plt.savefig(os.path.join(output_dir, f'convergence_residuals_master{suffix}.png'), dpi=300)
    plt.close()

def generate_mesh_plot(grid_file, output_path, surf_file=None, ref_params=None):
    """Generates a plot showing the actual computational grid."""
    data = parse_grid_dump(grid_file)
    if len(data) == 0: return
    xlo, ylo, xhi, yhi = data[:, 0], data[:, 1], data[:, 2], data[:, 3]
    plt.figure(figsize=(12, 8), facecolor='#0f172a')
    ax = plt.gca(); ax.set_facecolor('#0f172a')
    from matplotlib.collections import PolyCollection
    verts = []
    indices = np.random.choice(len(data), min(len(data), 5000), replace=False)
    for i in indices:
        verts.append([(xlo[i], ylo[i]), (xhi[i], ylo[i]), (xhi[i], yhi[i]), (xlo[i], yhi[i])])
        verts.append([(xlo[i], -ylo[i]), (xhi[i], -ylo[i]), (xhi[i], -yhi[i]), (xlo[i], -yhi[i])])
    coll = PolyCollection(verts, facecolors='none', edgecolors='#475569', linewidths=0.3, alpha=0.4)
    ax.add_collection(coll)
    _overlay_geometry(ax, surf_file, ref_params=ref_params)
    plt.title('SPARTA DSMC - Computational Mesh Grid', color='white')
    plt.axis('equal'); plt.savefig(output_path, dpi=300); plt.close()

def upscale_2d_to_3d(grid_file, output_path, surf_file=None, prop='temp', ref_params=None):
    """Upscales 2D axisymmetric results to 3D."""
    data = parse_grid_dump(grid_file)
    if len(data) == 0: return
    
    valid_mask = np.all(np.isfinite(data[:, :10]), axis=1)
    data = data[valid_mask]
    if len(data) == 0: return
    
    x = (data[:, 0] + data[:, 2]) / 2; y = (data[:, 1] + data[:, 3]) / 2
    nrho = data[:, 9]
    n_max = np.nanmax(nrho) if len(nrho) > 0 else 1.0
    
    # Filter out empty/vacuum regions to keep the 3D visualization clean
    valid = nrho >= (n_max * 0.001)
    x = x[valid]
    y = y[valid]
    data = data[valid]
    nrho = nrho[valid]
    
    import matplotlib.colors as mcolors
    norm = None
    
    if prop == 'velocity':
        u, v, w = data[:, 5], data[:, 6], data[:, 7]
        vals = np.sqrt(u**2 + v**2 + w**2)
        label = "Velocity Magnitude (m/s)"
        cmap = 'viridis'
    elif prop == 'mach':
        vel = np.sqrt(data[:, 5]**2 + data[:, 6]**2 + data[:, 7]**2)
        preset = str(ref_params.get('env_preset', 'mars')).lower() if ref_params else 'mars'
        if 'mars' in preset:
            gamma = 1.29
            R = 188.9
        else:
            gamma = 1.4
            R = 287.05
        sound = np.sqrt(gamma * R * np.maximum(data[:, 8], 1.0))
        vals = np.nan_to_num(vel / sound)
        label = "Mach Number"
        cmap = 'plasma'
    elif prop == 'pressure':
        # press = nrho * k * temp
        temp_val = data[:, 8]
        vals = nrho * 1.380649e-23 * temp_val
        label = "Pressure (Pa)"
        cmap = 'jet'
    elif prop == 'knudsen':
        n_val = data[:, 4]
        d_mol = 3.7e-10 # m (Air)
        n_safe = np.maximum(np.nan_to_num(n_val), 1.0)
        mfp = 1.0 / (np.sqrt(2) * np.pi * (d_mol**2) * n_safe)
        L = float(ref_params.get('nose_radius', 0.55)) if (ref_params and ref_params.get('nose_radius')) else 0.55
        vals = mfp / L
        label = "Local Knudsen Number (Kn)"
        cmap = 'RdYlBu_r'
        norm = mcolors.LogNorm(vmin=1e-5, vmax=10.0)
    elif prop == 'grid':
        vals = np.ones_like(x)
        label = "Mesh Grid Centers"
        cmap = None
    else:
        vals = data[:, 8]
        label = "Temperature (K)"
        cmap = 'hot'
        
    step = max(1, len(x) // 5000)
    x, y, vals = x[::step], y[::step], vals[::step]
    thetas = np.linspace(0, 2*np.pi, 80)
    fig = plt.figure(figsize=(16, 14), facecolor='#0f172a')
    all_x, all_y, all_z, all_vals = [], [], [], []
    for theta in thetas:
        all_x.extend(x); all_y.extend(y * np.cos(theta))
        all_z.extend(y * np.sin(theta)); all_vals.extend(vals)
    ax = fig.add_subplot(111, projection='3d')
    ax.set_facecolor('#0f172a')
    
    # Hide grid and panes for a cleaner premium look
    ax.xaxis.pane.fill = False; ax.yaxis.pane.fill = False; ax.zaxis.pane.fill = False
    ax.xaxis.pane.set_edgecolor('#1e293b'); ax.yaxis.pane.set_edgecolor('#1e293b'); ax.zaxis.pane.set_edgecolor('#1e293b')
    ax.grid(color='#1e293b', linestyle='--', linewidth=0.3)
    ax.tick_params(colors='#94a3b8')
    
    if cmap is None:
        sc = ax.scatter(all_x, all_y, all_z, color='#38bdf8', s=1.5, alpha=0.08)
    elif norm is not None:
        sc = ax.scatter(all_x, all_y, all_z, c=all_vals, cmap=cmap, norm=norm, s=1.5, alpha=0.08)
    else:
        sc = ax.scatter(all_x, all_y, all_z, c=all_vals, cmap=cmap, s=1.5, alpha=0.08)
        
    if cmap is not None:
        cbar = fig.colorbar(sc, ax=ax, label=label, pad=0.05, shrink=0.6)
        cbar.ax.yaxis.label.set_color('white')
        cbar.ax.tick_params(colors='#94a3b8')
        
    ax.set_xlabel('Axial X (m)', color='#94a3b8', labelpad=15)
    ax.set_ylabel('Radial Y (m)', color='#94a3b8', labelpad=15)
    ax.set_zlabel('Radial Z (m)', color='#94a3b8', labelpad=15)
    ax.view_init(elev=20, azim=45)
    
    # Force box aspect ratio to prevent squashing/stretching of the physical geometry
    x_min, x_max = np.min(all_x), np.max(all_x)
    y_min, y_max = np.min(all_y), np.max(all_y)
    z_min, z_max = np.min(all_z), np.max(all_z)
    x_range = max(1e-3, x_max - x_min)
    y_range = max(1e-3, y_max - y_min)
    z_range = max(1e-3, z_max - z_min)
    max_range = max(x_range, y_range, z_range)
    ax.set_box_aspect((x_range / max_range, y_range / max_range, z_range / max_range))
    
    plt.title(f'3D Axisymmetric Upscaling: {label}', color='white', fontweight='bold', fontsize=18, pad=20)
    plt.savefig(output_path, facecolor=fig.get_facecolor(), edgecolor='none', dpi=300); plt.close()

def generate_animation(grid_files, output_mp4, ref_params=None, prop='temp'):
    """Creates a beautiful 2D MP4 animation of a specified physical property with glassmorphic overlays."""
    import matplotlib.animation as animation
    import matplotlib.colors as mcolors
    if not grid_files: return
    
    # 1. Retrieve Dynamic Git Commit
    try:
        git_commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        git_commit = "8c6b7ef"
        
    # 2. Pre-scan grid files to establish global normalization bounds
    vals_list = []
    for f in grid_files:
        d = parse_grid_dump(f)
        if len(d) == 0: continue
        xc, yc = (d[:, 0] + d[:, 2]) / 2, (d[:, 1] + d[:, 3]) / 2
        nrho_val = d[:, 9]
        n_max = np.max(nrho_val) if len(nrho_val) > 0 else 1.0
        
        if prop == 'velocity':
            u, v, w = d[:, 5], d[:, 6], d[:, 7]
            vals = np.sqrt(u**2 + v**2 + w**2)
            vals[nrho_val < n_max * 0.001] = np.nan
        elif prop == 'mach':
            vel = np.sqrt(d[:, 5]**2 + d[:, 6]**2 + d[:, 7]**2)
            preset = str(ref_params.get('env_preset', 'mars')).lower() if ref_params else 'mars'
            if 'mars' in preset:
                gamma = 1.29
                R = 188.9
            else:
                gamma = 1.4
                R = 287.05
            sound = np.sqrt(gamma * R * np.maximum(d[:, 8], 1.0))
            vals = np.nan_to_num(vel / sound)
            vals[nrho_val < n_max * 0.001] = np.nan
        elif prop == 'pressure':
            temp_val = d[:, 8]
            vals = nrho_val * 1.380649e-23 * temp_val
            vals[nrho_val < n_max * 0.001] = np.nan
        elif prop == 'knudsen':
            n_val = d[:, 4]
            d_mol = 3.7e-10
            n_safe = np.maximum(np.nan_to_num(n_val), 1.0)
            mfp = 1.0 / (np.sqrt(2) * np.pi * (d_mol**2) * n_safe)
            L = float(ref_params.get('nose_radius', 0.55)) if (ref_params and ref_params.get('nose_radius')) else 0.55
            vals = mfp / L
            vals = np.clip(vals, 1e-5, 10.0)
            vals[nrho_val < n_max * 0.001] = np.nan
        elif prop == 'grid':
            vals = np.ones_like(xc)
        else: # temp
            vals = d[:, 8].copy()
            vals[nrho_val < n_max * 0.001] = np.nan
            
        valid_vals = vals[~np.isnan(vals)]
        if len(valid_vals) > 0:
            vals_list.append((np.nanmin(valid_vals), np.nanmax(valid_vals)))
            
    global_min = min(v[0] for v in vals_list) if vals_list else 0.0
    global_max = max(v[1] for v in vals_list) if vals_list else 1.0
    if prop == 'mach':
        global_max = min(global_max, float(ref_params.get('mach', 10.0)) * 1.5 if ref_params else 15.0)
        
    # 3. Setup Plot Aesthetics
    fig, ax = plt.subplots(figsize=(12, 7), facecolor='#0f172a'); ax.set_facecolor('#0f172a')
    ax.tick_params(colors='#94a3b8')
    ax.set_aspect('equal', adjustable='box')
    
    # Establish dynamic labels and styling
    norm = None
    if prop == 'velocity':
        label = "Velocity Magnitude (m/s)"; cmap = 'viridis'
    elif prop == 'mach':
        label = "Mach Number"; cmap = 'plasma'
    elif prop == 'pressure':
        label = "Pressure (Pa)"; cmap = 'jet'
    elif prop == 'knudsen':
        label = "Local Knudsen Number (Kn)"; cmap = 'RdYlBu_r'
        norm = mcolors.LogNorm(vmin=1e-5, vmax=10.0)
    elif prop == 'grid':
        label = "Mesh Grid Centers"; cmap = None
    else:
        label = "Temperature (K)"; cmap = 'hot'
        
    cbar = None
    
    def update(frame):
        nonlocal cbar
        ax.clear()
        ax.set_facecolor('#0f172a')
        ax.set_aspect('equal', adjustable='box')
        
        # Load frame data
        d = parse_grid_dump(grid_files[frame])
        if len(d) == 0: return
        
        xc, yc = (d[:, 0] + d[:, 2]) / 2, (d[:, 1] + d[:, 3]) / 2
        nrho_val = d[:, 9]
        n_max = np.max(nrho_val) if len(nrho_val) > 0 else 1.0
        
        if prop == 'velocity':
            u, v, w = d[:, 5], d[:, 6], d[:, 7]
            vals = np.sqrt(u**2 + v**2 + w**2)
            vals[nrho_val < n_max * 0.001] = np.nan
        elif prop == 'mach':
            vel = np.sqrt(d[:, 5]**2 + d[:, 6]**2 + d[:, 7]**2)
            preset = str(ref_params.get('env_preset', 'mars')).lower() if ref_params else 'mars'
            if 'mars' in preset:
                gamma = 1.29
                R = 188.9
            else:
                gamma = 1.4
                R = 287.05
            sound = np.sqrt(gamma * R * np.maximum(d[:, 8], 1.0))
            vals = np.nan_to_num(vel / sound)
            vals[nrho_val < n_max * 0.001] = np.nan
        elif prop == 'pressure':
            temp_val = d[:, 8]
            vals = nrho_val * 1.380649e-23 * temp_val
            vals[nrho_val < n_max * 0.001] = np.nan
        elif prop == 'knudsen':
            n_val = d[:, 4]
            d_mol = 3.7e-10
            n_safe = np.maximum(np.nan_to_num(n_val), 1.0)
            mfp = 1.0 / (np.sqrt(2) * np.pi * (d_mol**2) * n_safe)
            L = float(ref_params.get('nose_radius', 0.55)) if (ref_params and ref_params.get('nose_radius')) else 0.55
            vals = mfp / L
            vals = np.clip(vals, 1e-5, 10.0)
            vals[nrho_val < n_max * 0.001] = np.nan
        elif prop == 'grid':
            vals = np.ones_like(xc)
        else: # temp
            vals = d[:, 8].copy()
            vals[nrho_val < n_max * 0.001] = np.nan
            
        # Symmetrical Mirroring
        mask_mirror = (yc > 1e-9)
        x_mirrored = np.concatenate([xc, xc[mask_mirror]])
        y_mirrored = np.concatenate([yc, -yc[mask_mirror]])
        vals_mirrored = np.concatenate([vals, vals[mask_mirror]])
        nrho_mirrored = np.concatenate([nrho_val, nrho_val[mask_mirror]])
        
        # Plot Frame
        if prop == 'grid':
            sc = ax.scatter(x_mirrored, y_mirrored, s=0.5, color='#38bdf8', alpha=0.3)
            # Add computational boxes
            step = max(1, len(d) // 1000)
            for i in range(0, len(d), step):
                xlo, ylo, xhi, yhi = d[i, 0], d[i, 1], d[i, 2], d[i, 3]
                ax.add_patch(plt.Rectangle((xlo, ylo), xhi-xlo, yhi-ylo, fill=False, edgecolor='#38bdf8', linewidth=0.3, alpha=0.4))
                ax.add_patch(plt.Rectangle((xlo, -yhi), xhi-xlo, yhi-ylo, fill=False, edgecolor='#38bdf8', linewidth=0.3, alpha=0.4))
        else:
            triang = _get_masked_triangulation(x_mirrored, y_mirrored, vals_mirrored, nrho_mirrored, np.max(nrho_mirrored), 0.001)
            if triang.mask is None or not np.all(triang.mask):
                if norm is not None:
                    levels = np.logspace(-5, 1, 50)
                    cp = ax.tricontourf(triang, np.nan_to_num(vals_mirrored, nan=1e-5), levels=levels, norm=norm, cmap=cmap)
                else:
                    levels = np.linspace(global_min, global_max, 50)
                    cp = ax.tricontourf(triang, np.nan_to_num(vals_mirrored, nan=0.0), levels=levels, cmap=cmap)
                    
                if cbar is None and cmap is not None:
                    cbar = fig.colorbar(cp, ax=ax, label=label)
                    cbar.ax.yaxis.label.set_color('white')
                    cbar.ax.tick_params(colors='#94a3b8')
                    
        ax.set_title(f'{label} Evolution - Step {frame*100}', color='white', fontweight='bold', fontsize=14)
        ax.set_xlabel('Axial (m)', color='#94a3b8')
        ax.set_ylabel('Radial (m)', color='#94a3b8')
        ax.tick_params(colors='#94a3b8')
        
        # Expand X axis to match simulation bounding box
        if ref_params:
            ax.set_xlim(float(ref_params.get('env_xmin', -0.6)), float(ref_params.get('env_xmax', 2.5)))
            
        # Draw vehicle surface boundary overlay
        veh_name = ref_params.get('target_vehicle', 'HIAD') if ref_params else 'HIAD'
        surf_file = os.path.join(os.path.dirname(grid_files[0]), f"../{veh_name}_custom.surf")
        if not os.path.exists(surf_file):
            surf_file = os.path.join(os.path.dirname(grid_files[0]), f"../{veh_name}_opt.surf")
        _overlay_geometry(ax, surf_file, ref_params=ref_params)
        
        # Add glassmorphic project overlay on the left part
        ax.text(0.03, 0.95, f"StellarOrion Hypersonic EditioN\nGit Commit: {git_commit}",
                transform=ax.transAxes, color='#38bdf8', fontsize=10,
                weight='bold', verticalalignment='top',
                bbox=dict(facecolor='#0f172a', alpha=0.85, edgecolor='#1e293b', boxstyle='round,pad=0.5'))
                
    ani = animation.FuncAnimation(fig, update, frames=len(grid_files), blit=False)
    plt.rcParams['animation.ffmpeg_path'] = find_ffmpeg()
    ani.save(output_mp4, writer='ffmpeg', dpi=300); plt.close()

def generate_preview(surf_file, output_path, params=None, ref_params=None):
    """Generates a 2D preview."""
    try:
        points, lines = [], []
        if os.path.exists(surf_file):
            with open(surf_file, 'r') as f:
                mode = None
                for line in f:
                    if "Points" in line: mode = "pts"; continue
                    if "Lines" in line: mode = "lines"; continue
                    parts = line.split()
                    if not parts or parts[0].isalpha(): continue
                    if mode == "pts": points.append([float(parts[1]), float(parts[2])])
                    if mode == "lines": lines.append([int(parts[1])-1, int(parts[2])-1])
        plt.figure(figsize=(10, 6), facecolor='#0f172a')
        ax = plt.gca(); ax.set_facecolor('#0f172a')
        for l in lines:
            p1, p2 = points[l[0]], points[l[1]]
            plt.plot([p1[0], p2[0]], [p1[1], p2[1]], color='#f43f5e', linewidth=3)
            plt.plot([p1[0], p2[0]], [-p1[1], -p2[1]], color='#f43f5e', linewidth=3)
        plt.axis('equal'); plt.savefig(output_path, dpi=300); plt.close()
        return True
    except: return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="StellarOrion Visualizer CLI")
    parser.add_argument("--grid", type=str, help="Path to grid.X.out file")
    parser.add_argument("--output", type=str, default="web/assets/plots", help="Output directory")
    parser.add_argument("--surf", type=str, help="Path to .surf file for overlay")
    parser.add_argument("--diameter", type=float, default=3.0)
    parser.add_argument("--angle", type=float, default=60.0)
    parser.add_argument("--toroids", type=int, default=7)
    parser.add_argument("--nose", type=float, default=0.55)
    args = parser.parse_args()
    if args.grid and os.path.exists(args.grid):
        ref = {'diameter': args.diameter, 'angle': args.angle, 'toroids': args.toroids, 'nose_radius': args.nose}
        generate_plots(args.grid, args.output, ref_params=ref, surf_file=args.surf)
        upscale_2d_to_3d(args.grid, os.path.join(args.output, "upscaled_3d.png"), surf_file=args.surf, ref_params=ref)
        print(f"[SUCCESS] Visuals generated in {args.output}")
    else:
        print("Usage: python visualizer.py --grid <file> [--surf <file>] ...")
