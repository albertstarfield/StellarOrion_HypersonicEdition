import subprocess
import os

configs = [
    ("region exclude_craft block -0.5 3.5 -0.1 2.6 -0.5 0.5 side out\ngroup free_stream grid region exclude_craft", "test side out"),
    ("region exclude_craft block -0.5 3.5 -0.1 2.6 -0.5 0.5\ngroup free_stream grid subtract all exclude_craft", "test subtract"),
    ("group exclude_craft surf hiad_surf\ngroup free_stream grid subtract all exclude_craft", "test surf subtract")
]

for cfg, name in configs:
    script = f"""seed 12345
dimension 2
global gridcut 0.0 comm/sort yes
boundary o ao p
create_box -4.2 4.2 0.0 7.5 -0.5 0.5
create_grid 50 50 1
species air.species N2
mixture air N2
mixture air vstream 10000.0 0.0 0.0
read_surf ORION_custom.surf group hiad_surf
surf_collide 1 diffuse 1000.0 1.0
surf_modify all collide 1
{cfg}
run 0
"""
    with open("CADDesign/test_adapt.in", "w") as f:
        f.write(script)
    print(f"--- Running {name} ---")
    res = subprocess.run(["docker", "run", "--rm", "-v", f"{os.getcwd()}/CADDesign:/app/CADDesign", "-w", "/app/CADDesign", "sparta-hysp", "spa", "-in", "test_adapt.in"], capture_output=True, text=True)
    if "ERROR" in res.stdout or "ERROR" in res.stderr:
        for line in res.stdout.splitlines():
            if "ERROR" in line: print(line)
        for line in res.stderr.splitlines():
            if "ERROR" in line: print(line)
    else:
        print("SUCCESS")
