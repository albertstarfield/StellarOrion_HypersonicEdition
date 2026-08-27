import subprocess
import os

script1 = """seed 12345
dimension 2
global gridcut 0.0 comm/sort yes
boundary o ao p
create_box -4.2 4.2 0.0 7.5 -0.5 0.5
create_grid 50 50 1
region exclude_craft block -0.5 3.5 -0.1 2.6 -0.5 0.5 side out
group free_stream grid region exclude_craft all
species air.species N2
mixture air N2
mixture air vstream 10000.0 0.0 0.0
read_surf ORION_custom.surf group hiad_surf
surf_collide 1 diffuse 1000.0 1.0
surf_modify all collide 1
create_particles air n 0
compute 1 grid all air n
fix adapt_grid adapt 10 free_stream refine coarsen particle 50 10 maxlevel 2
run 10
write_restart restart.10
"""

script2 = """read_restart restart.10
seed 12345
surf_collide 1 diffuse 1000.0 1.0
surf_modify all collide 1
compute 1 grid all air n
fix adapt_grid adapt 10 free_stream refine coarsen particle 50 10 maxlevel 2
run 10
"""

with open("CADDesign/test1.in", "w") as f: f.write(script1)
with open("CADDesign/test2.in", "w") as f: f.write(script2)

print("Running Step 1")
res1 = subprocess.run(["docker", "run", "--rm", "-v", f"{os.getcwd()}/CADDesign:/app/CADDesign", "-w", "/app/CADDesign", "sparta-hysp", "spa", "-in", "test1.in"], capture_output=True, text=True)
if "ERROR" in res1.stdout or "ERROR" in res1.stderr:
    print(res1.stdout)
    print(res1.stderr)
    exit()

print("Running Step 2")
res2 = subprocess.run(["docker", "run", "--rm", "-v", f"{os.getcwd()}/CADDesign:/app/CADDesign", "-w", "/app/CADDesign", "sparta-hysp", "spa", "-in", "test2.in"], capture_output=True, text=True)
if "ERROR" in res2.stdout or "ERROR" in res2.stderr:
    print(res2.stdout)
    print(res2.stderr)
else:
    print("SUCCESS")
