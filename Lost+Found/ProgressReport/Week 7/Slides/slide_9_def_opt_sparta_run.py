def get_slide_data() -> dict:
    return {
        'title': 'SPARTA DSMC Simulation',
        'content': '\n## SPARTA DSMC Execution Interface\n\nThe function `run_sparta_simulation(geom_coords, flow_regime)` orchestrates high-fidelity rarefied flow simulations.\n\n**Pipeline Flow:**\n1. Writes the geometric coordinates to SPARTA configuration files.\n2. Scales collision properties using the Variable Soft Sphere (VSS) parameters.\n3. Automatically partitions the simulation domain using spatial decomposition for parallel processing.\n4. Executes the SPARTA binary and extracts force/pressure distributions along the HIAD outer fabric.\n'
    }
