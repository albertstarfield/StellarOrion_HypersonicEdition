from StellarOrionEngineMach5Up import Api
api = Api()
res = api.run_baseline_validation(solver='sparta', steps=1100, skip_diag=True, headless=True)
print(res)
