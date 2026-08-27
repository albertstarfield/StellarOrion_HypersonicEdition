import re

file_path = "StellarOrionEngineMach5Up.py"
with open(file_path, "r") as f:
    content = f.read()

# Add missing parameters to viz_metadata
replacement = """            return {
                'target_vehicle': opt_params.get('target_vehicle', 'IRVE-3'),
                'env_xmin': opt_params.get('env_xmin', -5.0),
                'env_xmax': opt_params.get('env_xmax', 9.0),
                'env_ymax': opt_params.get('env_ymax', 5.0),
                'v_inf': round(vstream, 1),"""
                
content = re.sub(r"            return \{\n                'v_inf': round\(vstream, 1\),", replacement, content)

with open(file_path, "w") as f:
    f.write(content)
print("Fixed Engine")
