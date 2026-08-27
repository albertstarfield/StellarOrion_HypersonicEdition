file_path = "CADDesign/ORION_GeometryEngine.py"
with open(file_path, "r") as f:
    content = f.read()

target = """    # 3. Backshell (Straight drop down)
    skin_data.append((1e-4, z_cone_start, 0))"""

replacement = """    # 3. Backshell (Conical taper to docking port)
    # The backshell tapers down to 0.4 * r_max over a distance of h_total
    top_radius = 0.4 * r_max
    z_cone_end = z_cone_start + h_total
    
    n_pts_back = 10
    for alpha in np.linspace(0.0, 1.0, n_pts_back):
        curr_r = r_cone_start - (r_cone_start - top_radius) * alpha
        curr_z = z_cone_start + h_total * alpha
        skin_data.append((max(1e-4, curr_r), curr_z, 0))
        
    skin_data.append((1e-4, z_cone_end, 0))"""

if target in content:
    content = content.replace(target, replacement)
    with open(file_path, "w") as f:
        f.write(content)
    print("Fixed standalone Orion geometry!")
else:
    print("Could not find target in ORION_GeometryEngine.py!")
