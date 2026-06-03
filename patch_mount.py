import re

file_path = "CADDesign/HIAD_GeometryEngine.py"
with open(file_path, "r") as f:
    content = f.read()

target = """        # Drop straight down to the Orion Shoulder (forming the straight fabric back of HIAD)
        n_drop_pts = 10
        for r in np.linspace(skin_data[-1][0], payload_radius, n_drop_pts):
            skin_data.append((max(1e-4, r), z_last_outer, 0.0))"""

replacement = """        # 2 Ties Anchor Mounting (Blunt/Rounded transition)
        n_drop_pts = 30
        r_start = skin_data[-1][0]
        z_orion = z_last_outer + 200.0
        
        for t in np.linspace(1.0, 0.0, n_drop_pts):
            curr_r = payload_radius + t * (r_start - payload_radius)
            curr_z_base = z_orion + t * (z_last_outer - z_orion)
            # Create two ties (bulges in +Z direction) using a cosine wave
            bulge = 400.0 * (1.0 - math.cos(4 * math.pi * t)) / 2.0
            curr_z = curr_z_base + bulge
            skin_data.append((max(1e-4, curr_r), curr_z, 0.0))"""

if target in content:
    content = content.replace(target, replacement)
    with open(file_path, "w") as f:
        f.write(content)
    print("Patched HIAD_GeometryEngine.py successfully!")
else:
    print("Could not find target block to replace.")

