file_path = "run_baselines.py"
with open(file_path, "r") as f:
    content = f.read()

target = """    "payload_file": "CADDesign/ORION_custom_full.step",
    "payload_type": "orion","""

replacement = """    "payload_file": "CADDesign/ORION_custom_full.step",
    "payload_type": "orion",
    "env_xmin": -2.0,
    "env_xmax": 8.0,
    "env_ymax": 5.0,"""

if target in content:
    content = content.replace(target, replacement)
    with open(file_path, "w") as f:
        f.write(content)
    print("Fixed bounds!")
else:
    print("Not found!")

