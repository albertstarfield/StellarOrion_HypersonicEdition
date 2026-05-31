import sys
from StellarOrionEngineMach5Up import Api
api = Api()
res = api.run_baseline_validation(solver='sparta', steps=110, skip_diag=True, headless=True, env_fnum=1e21)
print(res)
