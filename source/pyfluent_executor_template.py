import sys
import os
import json
import multiprocessing
import ansys.fluent.core as pyfluent

def run_simulation(config):
    try:
        # Parameters from config
        diameter = config.get("diameter", 3.0)
        velocity = config.get("velocity", 3000.0)
        pressure = config.get("pressure", 10.0)
        temperature = config.get("temperature", 250.0)
        dimension = config.get("dimension", "2d") # "2d" or "3d"
        
        # 1. Launch Fluent with GPU Check & Auto Core Detection
        use_gpu = config.get("use_gpu", True)
        
        # Auto-detect cores if not specified or set to 0
        system_cores = multiprocessing.cpu_count()
        n_cores = config.get("n_cores", 0)
        if n_cores <= 0:
            n_cores = max(1, system_cores - 1) # Leave one core for system
        
        print(f"[*] [PyFluent] Launching Fluent {dimension} (GPU={use_gpu}, Cores={n_cores}/{system_cores})...")
        session = pyfluent.launch_fluent(
            precision="double", 
            processor_count=n_cores, 
            mode="meshing", 
            show_gui=False,
            version=dimension,
            gpu=use_gpu
        )
        meshing = session.meshing
        print("[+] [PyFluent] Fluent instance initialized.")

        # 2. Automated Meshing Workflow (Watertight Geometry)
        print("[*] [PyFluent] Starting Watertight Geometry Workflow...")
        workflow = meshing.workflow
        workflow.InitializeWorkflow(WorkflowType="Watertight Geometry")
        
        # Import Geometry
        cad_file = os.path.abspath("geometry.stl")
        if not os.path.exists(cad_file):
            cad_file = os.path.abspath("geometry.step")
        
        print(f"[*] [PyFluent] Importing geometry from {cad_file}...")
        workflow.TaskObject["Import Geometry"].Arguments.set_state({
            "FileName": cad_file,
            "LengthUnit": "m"
        })
        workflow.TaskObject["Import Geometry"].Execute()
        
        # Add Local Sizing
        print("[*] [PyFluent] Adding local refinement at stagnation point...")
        workflow.TaskObject["Add Local Sizing"].Arguments.set_state({
            "AddChildToTask": "yes",
            "BOIControlName": "nose_refinement",
            "FaceSize": diameter / 100.0 
        })
        workflow.TaskObject["Add Local Sizing"].Execute()
        
        print("[*] [PyFluent] Generating surface mesh...")
        workflow.TaskObject["Generate the Surface Mesh"].Execute()
        
        print("[*] [PyFluent] Describing geometry and creating regions...")
        workflow.TaskObject["Describe Geometry"].Arguments.set_state({"GeometryType": "Solid"})
        workflow.TaskObject["Describe Geometry"].Execute()
        
        workflow.TaskObject["Update Boundaries"].Execute()
        workflow.TaskObject["Update Regions"].Execute()
        
        print("[*] [PyFluent] Adding 15-layer boundary layers for heating capture...")
        workflow.TaskObject["Add Boundary Layers"].Arguments.set_state({
            "NumberOfLayers": 15,
            "OffsetMethodType": "uniform"
        })
        workflow.TaskObject["Add Boundary Layers"].Execute()
        
        print("[*] [PyFluent] Generating Poly-Hexcore volume mesh...")
        workflow.TaskObject["Generate the Volume Mesh"].Arguments.set_state({"VolumeFill": "poly-hexcore"})
        workflow.TaskObject["Generate the Volume Mesh"].Execute()
        
        print("[+] [PyFluent] Meshing complete. Switching to Solver mode...")
        solver = session.switch_to_solver()
        
        # 3. Setup Physics (Compressible Unsteady DBNS)
        print("[*] [PyFluent] Configuring Density-Based Unsteady Solver...")
        solver.setup.general.solver.type = "density-based"
        solver.setup.general.solver.time = "unsteady"
        
        if dimension == "2d":
            solver.setup.general.solver.two_dim_space = "axisymmetric"
        
        solver.setup.models.energy.enabled = True
        solver.setup.models.viscous.model = "k-omega"
        solver.setup.models.viscous.k_omega_model = "sst"
        
        # 4. AMR Setup
        print("[*] [PyFluent] Enabling Adaptive Mesh Refinement (Pressure Gradient)...")
        solver.solution.adaption.model.type = "gradient"
        solver.solution.adaption.model.criterion = "pressure"
        
        solver.setup.materials.fluid["air"].density.type = "ideal-gas"
        
        # 5. Boundary Conditions
        print(f"[*] [PyFluent] Setting Far-Field: V={velocity}m/s, P={pressure}Pa, T={temperature}K")
        solver.setup.boundary_conditions.pressure_far_field["inlet"].m_number = velocity / 340.0 
        solver.setup.boundary_conditions.pressure_far_field["inlet"].gauge_pressure = pressure
        solver.setup.boundary_conditions.pressure_far_field["inlet"].t = temperature
        solver.setup.boundary_conditions.wall["shield"].thermal.t = config.get("wall_temp", 1000.0)
        
        # 6. Initialization & Unsteady Solve
        print("[*] [PyFluent] Initializing and starting calculation...")
        solver.solution.initialization.hybrid_initialize()
        
        t_step = config.get("time_step", 1.0e-6)
        n_steps = config.get("total_steps", 100)
        solver.solution.run_calculation.transient_controls.time_step_size = t_step
        solver.solution.run_calculation.number_of_time_steps = n_steps
        solver.solution.run_calculation.adaptive_time_stepping = True 
        
        print(f"[*] [PyFluent] Running {n_steps} steps (dt={t_step}s)...")
        solver.solution.run_calculation.calculate()
        
        # 7. Post-processing
        print("[*] [PyFluent] Calculation finished. Extracting metrics...")
        drag_val = solver.solution.report_definitions.force["drag"].compute()
        heat_val = solver.solution.report_definitions.flux["heat-flux"].compute()
        
        print(f"[+] [PyFluent] Final Results -> Drag: {drag_val:.4f}, Heat Flux: {heat_val:.4f}")
        
        results = {"drag": drag_val, "heat": heat_val, "status": "success"}
        with open("results.json", "w") as f:
            json.dump(results, f)
            
        session.exit()
        print("[+] [PyFluent] Session closed successfully.")

    except Exception as e:
        print(f"[-] [PyFluent] FATAL ERROR during remote execution: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        results = {"status": "error", "message": str(e)}
        with open("results.json", "w") as f:
            json.dump(results, f)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r") as f:
            config = json.load(f)
        run_simulation(config)
    else:
        print("No config file provided.")
