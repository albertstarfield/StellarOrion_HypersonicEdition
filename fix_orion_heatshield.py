file_path = "CADDesign/HIAD_GeometryEngine.py"
with open(file_path, "r") as f:
    content = f.read()

target = """        # B. Orion Spherical Heat Shield (Cyan curve)
        R_curv = 6000.0
        sphere_z = z_last_outer + (R_curv - 545.6)
        n_arc_pts = 15
        for alpha in np.linspace(0.0, math.asin(payload_radius/R_curv), n_arc_pts):
            curr_r = R_curv * math.sin(alpha)
            curr_z = sphere_z - R_curv * math.cos(alpha)
            skin_data.append((max(1e-4, curr_r), curr_z, 0.0))"""

replacement = """        # B. Orion Nose (Narrow End touching HIAD)
        # Since it's upside down, the narrow part is at the front.
        # We just draw a small flat or rounded cap at the front.
        top_radius = 0.4 * payload_radius
        for r in np.linspace(0, top_radius, 5):
            skin_data.append((max(1e-4, r), z_last_outer, 0.0))"""

if target in content:
    content = content.replace(target, replacement)
    with open(file_path, "w") as f:
        f.write(content)
    print("Fixed Orion heatshield in HIAD_GeometryEngine.py")
else:
    print("Could not find target in HIAD_GeometryEngine.py")
