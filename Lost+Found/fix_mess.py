file_path = "CADDesign/HIAD_GeometryEngine.py"
with open(file_path, "r") as f:
    content = f.read()

content = content.replace("skin_data[-1][0]_mm", "r_max_mm")
content = content.replace("c_r_last_mm", "r_max_mm")
content = content.replace("np.linspace(skin_data[-1][0], payload_radius", "np.linspace(skin_data[-1][0], payload_radius")

with open(file_path, "w") as f:
    f.write(content)
print("Fixed!")
