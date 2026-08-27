file_path = "CADDesign/HIAD_GeometryEngine.py"
with open(file_path, "r") as f:
    content = f.read()

target = """        # 2 Ties Anchor Mounting (Blunt/Rounded transition)
        n_drop_pts = 30
        r_start = skin_data[-1][0]
        z_orion = z_last_outer + 200.0
        
        for t in np.linspace(1.0, 0.0, n_drop_pts):
            curr_r = payload_radius + t * (r_start - payload_radius)
            curr_z_base = z_orion + t * (z_last_outer - z_orion)
            # Create two ties (bulges in +Z direction) using a cosine wave
            bulge = 400.0 * (1.0 - math.cos(4 * math.pi * t)) / 2.0
            curr_z = curr_z_base + bulge
            skin_data.append((max(1e-4, curr_r), curr_z, 0.0))
            
        # C. Orion Truncated Cone Wall
        top_radius = 0.4 * payload_radius
        n_cap_pts = 10
        for alpha in np.linspace(0.0, 1.0, n_cap_pts):
            # Wide part (payload_radius) at the front (touching HIAD)
            # Narrow part (top_radius) at the back.
            curr_r = payload_radius - (payload_radius - top_radius) * alpha
            curr_z = z_orion + payload_height * alpha
            skin_data.append((max(1e-4, curr_r), curr_z, 0.0))
        
        # D. Back Cap (Rounded/Blunt docking port)
        z_back = z_orion + payload_height
        n_back_pts = 10
        for t in np.linspace(1.0, 0.0, n_back_pts):
            curr_r = top_radius * t
            # Elliptical blunt cap
            curr_z = z_back + 100.0 * math.sqrt(1.0 - t**2)
            skin_data.append((max(1e-4, curr_r), curr_z, 0.0))"""

replacement = """        # Drop straight down to the Orion Shoulder (forming the straight fabric back of HIAD)
        n_drop_pts = 10
        for r in np.linspace(skin_data[-1][0], payload_radius, n_drop_pts):
            skin_data.append((max(1e-4, r), z_last_outer, 0.0))
            
        # C. Orion Truncated Cone Wall
        top_radius = 0.4 * payload_radius
        n_cap_pts = 10
        for alpha in np.linspace(0.0, 1.0, n_cap_pts):
            # Wide part (payload_radius) at the front (touching HIAD)
            # Narrow part (top_radius) at the back.
            curr_r = payload_radius - (payload_radius - top_radius) * alpha
            curr_z = z_last_outer + payload_height * alpha
            skin_data.append((max(1e-4, curr_r), curr_z, 0.0))
        
        # D. Back Cap (Flat/Narrow docking port)
        z_back = z_last_outer + payload_height
        skin_data.append((1e-4, z_back, 0.0))"""

if target in content:
    content = content.replace(target, replacement)
    with open(file_path, "w") as f:
        f.write(content)
    print("Reverted geometry successfully!")
else:
    print("Could not find target block to replace.")

