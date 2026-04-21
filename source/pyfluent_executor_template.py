import sys
import os
import json
import ansys.fluent.core as pyfluent

def run_simulation(config):
    # Parameters from config
    diameter = config.get("diameter", 3.0)
    velocity = config.get("velocity", 3000.0)
    pressure = config.get("pressure", 10.0)  # Pa (approx for high altitude)
    temperature = config.get("temperature", 250.0) # K
    
    # Launch Fluent in meshing mode
    session = pyfluent.launch_fluent(precision="double", processor_count=4, mode="meshing", show_gui=False)
    meshing = session.meshing
    
    # 1. Import Geometry
    cad_file = os.path.abspath("geometry.stl")
    if not os.path.exists(cad_file):
        cad_file = os.path.abspath("geometry.step")
        
    meshing.workflow.InitializeWorkflow(TopologyImportOptions={"FileName": cad_file})
    
    # 2. Simple Meshing Workflow (Simplified for example)
    # In a real scenario, this would involve detailed sizing and face meshing.
    # For now, we assume the remote machine has a working template or we use default automated meshing.
    
    # Switch to Solution mode
    solver = session.switch_to_solver()
    
    # 3. Setup Physics
    # Hypersonic flow typically uses Density-Based Solver
    solver.setup.models.energy.enabled = True
    solver.setup.models.viscous.model = "k-omega"
    solver.setup.models.viscous.k_omega_model = "sst"
    
    # Material: Ideal Gas Air
    solver.setup.materials.fluid["air"].density.type = "ideal-gas"
    
    # 4. Boundary Conditions
    # Inlet: Pressure Far-Field
    solver.setup.boundary_conditions.pressure_far_field["inlet"].m_number = velocity / 340.0 # Simplistic mach calc
    solver.setup.boundary_conditions.pressure_far_field["inlet"].gauge_pressure = pressure
    solver.setup.boundary_conditions.pressure_far_field["inlet"].t = temperature
    
    # Wall: Thermal boundary
    solver.setup.boundary_conditions.wall["shield"].thermal.t = config.get("wall_temp", 1000.0)
    
    # 5. Initialization & Solve
    solver.solution.initialization.hybrid_initialize()
    solver.solution.run_calculation.iter_count = config.get("iterations", 100)
    solver.solution.run_calculation.calculate()
    
    # 6. Post-processing
    # Get Force Report (Drag)
    # This is a conceptual API call; actual PyFluent calls for reports may vary by version
    drag_report = solver.solution.report_definitions.force["drag"]
    drag_val = drag_report.compute()
    
    # Get Heat Flux
    heat_report = solver.solution.report_definitions.flux["heat-flux"]
    heat_val = heat_report.compute()
    
    results = {
        "drag": drag_val,
        "heat": heat_val,
        "status": "success"
    }
    
    with open("results.json", "w") as f:
        json.dump(results, f)
        
    session.exit()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r") as f:
            config = json.load(f)
        run_simulation(config)
    else:
        print("No config file provided.")
