file_path = "CADDesign/HIAD_GeometryEngine.py"
with open(file_path, "r") as f:
    content = f.read()

target = """        # C. Orion Truncated Cone Wall
        top_radius = 0.4 * payload_radius
        n_cap_pts = 10
        for alpha in np.linspace(0.0, 1.0, n_cap_pts):
            curr_r = payload_radius - (payload_radius - top_radius) * alpha
            curr_z = z_last_outer + payload_height * alpha
            skin_data.append((max(1e-4, curr_r), curr_z, 0.0))"""

replacement = """        # C. Orion Truncated Cone Wall
        top_radius = 0.4 * payload_radius
        n_cap_pts = 10
        for alpha in np.linspace(0.0, 1.0, n_cap_pts):
            # Flipped orientation: Narrow part (top_radius) at the front (closer to HIAD)
            # Wide part (payload_radius) at the back.
            curr_r = top_radius + (payload_radius - top_radius) * alpha
            curr_z = z_last_outer + payload_height * alpha
            skin_data.append((max(1e-4, curr_r), curr_z, 0.0))"""

if target in content:
    content = content.replace(target, replacement)
    with open(file_path, "w") as f:
        f.write(content)
    print("Fixed Orion orientation in HIAD_GeometryEngine.py")
else:
    print("Could not find target in HIAD_GeometryEngine.py")

