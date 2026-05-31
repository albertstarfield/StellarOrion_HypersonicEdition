import sys
from StellarOrionEngineMach5Up import Api
api = Api()
res = api.run_baseline_validation(solver='sparta', steps=1100, skip_diag=False, headless=True, env_fnum=2.5e17)
print(res)
