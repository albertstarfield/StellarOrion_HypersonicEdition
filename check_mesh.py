import numpy as np
import matplotlib.pyplot as plt

def parse_surf(file_path):
    pts = []
    with open(file_path, 'r') as f:
        lines = f.readlines()
        
    start_idx = 0
    for i, l in enumerate(lines):
        if l.strip() == "Points":
            start_idx = i + 2
            break
            
    for l in lines[start_idx:]:
        if l.strip() == "" or l.strip() == "Lines": break
        parts = l.split()
        if len(parts) >= 3:
            pts.append((float(parts[1]), float(parts[2])))
    return pts

pts = parse_surf("HIAD_custom.surf")
# We will just print the min and max X, Y to see where the geometry sits!
if pts:
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    print(f"HIAD points: {len(pts)}")
    print(f"X range: {min(xs):.3f} to {max(xs):.3f}")
    print(f"Y range: {min(ys):.3f} to {max(ys):.3f}")
else:
    print("No points found in HIAD_custom.surf")

