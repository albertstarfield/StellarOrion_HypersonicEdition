import StellarOrionEngineMach5Up

engine = StellarOrionEngineMach5Up.Api()
opt_params = {
    'target_vehicle': 'ORION',
    'env_xmin': -1.69,
    'env_xmax': 4.5,
    'env_ymax': 3.976,
}
sample_dict = {'diameter': 3.0}

viz_metadata = engine._get_viz_params(opt_params, sample_dict)
print(viz_metadata)
