
file_path = "CADDesign/HIAD_GeometryEngine.py"
with open(file_path, "r") as f:
    content = f.read()

target = """    # Target inflated radius (mm)
    r_target = (diameter_m * 1000.0) / 2.0
    
    # Derive nose radius if not provided (IRVE-3 ratio: ~123.7mm for 3m diameter)
    if nose_radius is None:
        nose_radius = r_target * (123.7 / 1500.0)
    else:
        nose_radius *= 1000.0
        
    # Derive toroid radius if not provided (IRVE-3: 135mm)
    if toroid_radius is None:
        toroid_radius = 135.0
    else:
        toroid_radius *= 1000.0"""

replacement = """    # Target inflated radius (mm)
    r_target = (diameter_m * 1000.0) / 2.0
    
    # Derive nose radius if not provided (IRVE-3 ratio: ~123.7mm for 3m diameter)
    if nose_radius is None:
        nose_radius = r_target * (123.7 / 1500.0)
    else:
        nose_radius *= 1000.0
        
    # Derive toroid radius if not provided (auto-calculate to hit r_target)
    if toroid_radius is None:
        r_tang = nose_radius * math.cos(theta_c_rad)
        L_cone = (r_target - r_tang) / math.sin(theta_c_rad)
        # L_cone is approx equal to (2 * toroids - 1) * toroid_radius + toroid_radius
        toroid_radius = L_cone / (2.0 * toroid_count)
    else:
        toroid_radius *= 1000.0"""

if target in content:
    content = content.replace(target, replacement)
    with open(file_path, "w") as f:
        f.write(content)
    print("Fixed toroid auto-scaling successfully!")
else:
    print("Target block not found.")
