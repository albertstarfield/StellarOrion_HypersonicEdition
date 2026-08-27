file_path = "CADDesign/HIAD_GeometryEngine.py"
with open(file_path, "r") as f:
    content = f.read()

target = """        # Drop straight to Orion nose (forming the straight fabric back of HIAD)
        z_orion_nose = z_last_outer - 545.6
        skin_data.append((1e-4, z_orion_nose, 0.0))
        
        # B. Orion Heat Shield Base (Wide part touching HIAD)
        for r in np.linspace(0, payload_radius, 5):
            skin_data.append((max(1e-4, r), z_last_outer, 0.0))"""

replacement = """        # Drop straight down to the Orion Shoulder (forming the straight fabric back of HIAD)
        n_drop_pts = 10
        for r in np.linspace(r_last_outer, payload_radius, n_drop_pts):
            skin_data.append((max(1e-4, r), z_last_outer, 0.0))"""

if target in content:
    content = content.replace(target, replacement)
    with open(file_path, "w") as f:
        f.write(content)
    print("Fixed overlapping lines!")
else:
    print("Could not find target!")

