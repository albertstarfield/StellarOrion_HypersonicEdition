from StellarOrionEngineMach5Up import Api
api = Api()
# Force env_cores=1 to bypass MPI shared memory issues
res = api.run_baseline_validation(solver='sparta', steps=110, skip_diag=True, headless=True, env_fnum=1e21, env_cores=1)
print(res)
