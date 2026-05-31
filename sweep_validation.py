
import subprocess
import numpy as np
from concurrent.futures import ThreadPoolExecutor

def run_sample(mach, alt):
    suffix = f"M{int(mach)}_A{int(alt)}"
    print(f"[*] Starting {suffix}...")
    cmd = [
        "python3", "main.py", 
        "--headless", 
        "--validation", 
        "--mach", str(mach), 
        "--alt", str(alt),
        "--steps", "30" # Ultra fast for 400 sample sweep
    ]
    
    try:
        # Run and wait
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"[+] Completed {suffix}")
    except Exception as e:
        print(f"[-] Failed {suffix}: {e}")

def main():
    # 400 samples: 20 Mach x 20 Altitude
    machs = np.linspace(5, 25, 20)
    alts = np.linspace(40, 80, 20)
    
    print("[*] Starting 400 sample sweep (20x20)...")
    
    tasks = []
    for m in machs:
        for a in alts:
            tasks.append((m, a))
            
    # Use ThreadPool to run 4 simulations in parallel
    with ThreadPoolExecutor(max_workers=4) as executor:
        for m, a in tasks:
            executor.submit(run_sample, m, a)

if __name__ == "__main__":
    main()
