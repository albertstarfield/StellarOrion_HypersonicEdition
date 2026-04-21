import subprocess
import os

# Test script to reproduce SPARTA reaction error
cad_dir = "/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/CADDesign"
sparta_exe = "/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/sparta/src/spa_mac_arm" # Assuming it's built there

in_script = """# SPARTA Test Script
seed            12345
dimension       2
global          gridcut 0.0 comm/sort yes
boundary        o ar p

create_box      -1.0 1.0 0.0 3.0 -0.5 0.5
create_grid     10 10 1

species         air.species N2 O2 NO N O
mixture air N2 O2 NO N O
mixture air N2 frac 0.79
mixture air O2 frac 0.21
collide         vss air air.vss

# Correct react command (standard SPARTA syntax: react style file)
react           tce air.tce

timestep        1.0e-6
run             1
"""

# Copy the real air.tce to workspace
import shutil
shutil.copy("/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/sparta/data/air.tce", os.path.join(cad_dir, "air.tce"))



with open(os.path.join(cad_dir, "in.test"), "w") as f:
    f.write(in_script)

print("[*] Running SPARTA with test script...")
try:
    # Use docker since the user is using it
    # We need to make sure air.species, air.react, air.vss are in cad_dir
    # They should already be there from previous runs.
    
    cmd = ["docker", "run", "--rm", "-v", f"{cad_dir}:/workspace", "-w", "/workspace", "sparta-hysp", "spa", "-in", "in.test"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    print(result.stderr)
    if result.returncode != 0:
        print(f"[!] FAILURE detected (Return Code {result.returncode}).")
    else:
        print("[+] SUCCESS!")
except Exception as e:
    print(f"[-] Error: {e}")
