import re
with open('StellarOrionEngineMach5Up.py', 'r') as f:
    code = f.read()
code = re.sub(r'n_cores = max\(1, multiprocessing.cpu_count\(\) - 2\)', 'n_cores = 4', code)
with open('StellarOrionEngineMach5Up.py', 'w') as f:
    f.write(code)
