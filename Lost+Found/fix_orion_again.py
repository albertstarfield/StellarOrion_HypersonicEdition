file_path = "CADDesign/HIAD_GeometryEngine.py"
with open(file_path, "r") as f:
    content = f.read()

target = """        # C. Orion Truncated Cone Wall
        top_radius = 0.4 * payload_radius
        n_cap_pts = 10
        for alpha in np.linspace(0.0, 1.0, n_cap_pts):
            # Flipped orientation: Narrow part (top_radius) at the front (closer to HIAD)
            # Wide part (payload_radius) at the back.
            curr_r = top_radius + (payload_radius - top_radius) * alpha
            curr_z = z_last_outer + payload_height * alpha
            skin_data.append((max(1e-4, curr_r), curr_z, 0.0))"""

replacement = """        # C. Orion Truncated Cone Wall
        top_radius = 0.4 * payload_radius
        n_cap_pts = 10
        for alpha in np.linspace(0.0, 1.0, n_cap_pts):
            # Wide part (payload_radius) at the front (touching HIAD)
            # Narrow part (top_radius) at the back.
            curr_r = payload_radius - (payload_radius - top_radius) * alpha
            curr_z = z_last_outer + payload_height * alpha
            skin_data.append((max(1e-4, curr_r), curr_z, 0.0))"""

if target in content:
    content = content.replace(target, replacement)
    with open(file_path, "w") as f:
        f.write(content)
    print("Fixed cone orientation!")
else:
    print("Could not find target!")

target2 = """        # D. Back Cap (Now the Spherical Heat Shield)
        z_back = z_last_outer + payload_height
        R_curv = 6000.0
        sphere_z = z_back - (R_curv - 545.6)
        n_arc_pts = 15
        for alpha in np.linspace(math.asin(payload_radius/R_curv), 0.0, n_arc_pts):
            curr_r = R_curv * math.sin(alpha)
            curr_z = sphere_z + R_curv * math.cos(alpha) # Convex bulge facing back (+z)
            skin_data.append((max(1e-4, curr_r), curr_z, 0.0))
        skin_data.append((1e-4, curr_z, 0.0))"""

replacement2 = """        # D. Back Cap (Flat/Narrow docking port)
        z_back = z_last_outer + payload_height
        skin_data.append((1e-4, z_back, 0.0))"""

if target2 in content:
    content = content.replace(target2, replacement2)
    with open(file_path, "w") as f:
        f.write(content)
    print("Fixed back cap!")
else:
    print("Could not find target2!")

target3 = """        # B. Orion Nose (Narrow End touching HIAD)
        # Since it's upside down, the narrow part is at the front.
        # We just draw a small flat or rounded cap at the front.
        top_radius = 0.4 * payload_radius
        for r in np.linspace(0, top_radius, 5):
            skin_data.append((max(1e-4, r), z_last_outer, 0.0))"""

replacement3 = """        # B. Orion Heat Shield Base (Wide part touching HIAD)
        for r in np.linspace(0, payload_radius, 5):
            skin_data.append((max(1e-4, r), z_last_outer, 0.0))"""

if target3 in content:
    content = content.replace(target3, replacement3)
    with open(file_path, "w") as f:
        f.write(content)
    print("Fixed nose cap!")
else:
    print("Could not find target3!")

