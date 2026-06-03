file_path = "source/visualizer.py"
with open(file_path, "r") as f:
    content = f.read()

target = "    if ref_params:\n        plt.xlim(float(ref_params.get('env_xmin', -0.6)), float(ref_params.get('env_xmax', 2.5)))"
replacement = target + "\n        if 'env_ymax' in ref_params:\n            plt.ylim(-float(ref_params['env_ymax']), float(ref_params['env_ymax']))"
content = content.replace(target, replacement)
target2 = "    if ref_params:\n        # Show from inlet to near end of domain to capture shock layer\n        plt.xlim(float(ref_params.get('env_xmin', -0.6)), float(ref_params.get('env_xmax', 2.5)))"
replacement2 = target2 + "\n        if 'env_ymax' in ref_params:\n            plt.ylim(-float(ref_params['env_ymax']), float(ref_params['env_ymax']))"
content = content.replace(target2, replacement2)

with open(file_path, "w") as f:
    f.write(content)
print("Replaced!")
