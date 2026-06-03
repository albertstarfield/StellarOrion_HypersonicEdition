import matplotlib.pyplot as plt
import numpy as np

def plot_surf(file_path, out_file):
    pts = []
    with open(file_path, 'r') as f:
        mode = None
        for line in f:
            if "Points" in line:
                mode = "pts"
                continue
            elif "Lines" in line:
                mode = "lines"
                continue
            
            parts = line.split()
            if not parts or parts[0].isalpha(): continue
            
            if mode == "pts" and len(parts) >= 3:
                pts.append([float(parts[1]), float(parts[2])])

    pts = np.array(pts)
    
    plt.figure(figsize=(10, 6))
    plt.plot(pts[:, 0], pts[:, 1], 'o-', label='Upper Half', markersize=3, color='cyan')
    plt.plot(pts[:, 0], -pts[:, 1], 'o-', label='Lower Half', markersize=3, color='cyan')
    
    plt.title('ORION-HIAD Geometry Preview (Flow direction: Left -> Right)')
    plt.xlabel('Z (Axial) / mm')
    plt.ylabel('R (Radial) / mm')
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.axis('equal')
    plt.legend()
    plt.savefig(out_file)
    print(f"Saved preview to {out_file}")

if __name__ == "__main__":
    plot_surf("HIAD_test_orion.surf", "/Users/albertstarfield/.gemini/antigravity-cli/brain/77b60d0c-74f8-4cfd-aa8e-67752de71148/hiad_hiad_hiad_hiad_hiad_orion_preview.png")
