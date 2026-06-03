import re

file_path = "source/visualizer.py"
with open(file_path, "r") as f:
    content = f.read()

# Add ylim to all plots that have xlim
replacement = """    if ref_params:
        plt.xlim(float(ref_params.get('env_xmin', -0.6)), float(ref_params.get('env_xmax', 2.5)))
        if 'env_ymax' in ref_params:
            plt.ylim(-float(ref_params['env_ymax']), float(ref_params['env_ymax']))"""
            
content = re.sub(r"    if ref_params:\n\s+plt\.xlim\(.*?\)", replacement, content)

with open(file_path, "w") as f:
    f.write(content)
print("Fixed Visualizer")
