file_path = "CADDesign/HIAD_GeometryEngine.py"
with open(file_path, "r") as f:
    content = f.read()

target = """        # D. Back Cap (Docking port area)
        z_back = z_last_outer + payload_height
        skin_data.append((1e-4, z_back, 0.0))"""

replacement = """        # D. Back Cap (Now the Spherical Heat Shield)
        z_back = z_last_outer + payload_height
        R_curv = 6000.0
        sphere_z = z_back - (R_curv - 545.6)
        n_arc_pts = 15
        for alpha in np.linspace(math.asin(payload_radius/R_curv), 0.0, n_arc_pts):
            curr_r = R_curv * math.sin(alpha)
            curr_z = sphere_z + R_curv * math.cos(alpha) # Convex bulge facing back (+z)
            skin_data.append((max(1e-4, curr_r), curr_z, 0.0))
        skin_data.append((1e-4, curr_z, 0.0))"""

if target in content:
    content = content.replace(target, replacement)
    with open(file_path, "w") as f:
        f.write(content)
    print("Fixed Orion back cap in HIAD_GeometryEngine.py")
else:
    print("Could not find target in HIAD_GeometryEngine.py")
