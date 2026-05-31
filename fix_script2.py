import re
with open('StellarOrionEngineMach5Up.py', 'r') as f:
    code = f.read()
code = re.sub(r"nproc = opt_params.get\('env_cores', os.cpu_count\(\) or 4\)", "nproc = 4", code)
with open('StellarOrionEngineMach5Up.py', 'w') as f:
    f.write(code)
