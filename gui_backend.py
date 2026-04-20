import os
import sys
import subprocess
import threading
import json
import shutil
import time
import numpy as np

class Api:
    def __init__(self):
        self.window = None
        self.cwd = os.getcwd()
        self.reference_data = None

    def _get_python_exec(self):
        """Finds a cadquery-enabled python interpreter."""
        cad_dir = os.path.join(self.cwd, "CADDesign")
        cad_venv_python = os.path.join(cad_dir, "venv", "bin", "python")
        root_venv_gui = os.path.join(self.cwd, ".venv_gui", "bin", "python")
        
        if os.path.exists(cad_venv_python):
            return cad_venv_python
        elif os.path.exists(root_venv_gui):
            return root_venv_gui
        return sys.executable

    def set_window(self, window):
        self.window = window

    def log_to_gui(self, message):
        timestamp = time.strftime("%H:%M:%S")
        # Clean message for terminal (remove <br>)
        term_msg = message.replace("<br>", "\n")
        print(f"[{timestamp}] {term_msg}") 
        if self.window:
            safe_msg = message.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "<br>")
            self.window.evaluate_js(f"appendLog('{safe_msg}')")

    def request_domain_preview(self, params):
        """Called from JS when domain params change"""
        cad_dir = os.path.join(self.cwd, "CADDesign")
        surf_file = os.path.join(cad_dir, "HIAD_custom.surf")
        preview_path = os.path.join(self.cwd, "web", "assets", "plots", "domain_preview.png")
        from source import visualizer
        success = visualizer.generate_preview(surf_file, preview_path, params=params)
        if success:
            self.window.evaluate_js("onDomainPreviewReady()")

    def generate_cad_preview(self, params):
        """Step 2: Generate 3D Geometry only (Fast)"""
        def run():
            try:
                self.log_to_gui("[*] Initializing Geometry Generation...")
                cad_dir = os.path.join(self.cwd, "CADDesign")
                self.window.evaluate_js("updateProgress(20)")
                
                python_exec = self._get_python_exec()
                cad_cmd = [
                    python_exec, "make_HIAD.py",
                    "--diameter", str(params.get('diameter', 3.0)),
                    "--angle", str(params.get('angle', 60.0)),
                    "--nose", str(params.get('nose_radius', 0.191)),
                    "--toroids", str(params.get('toroids', 7)),
                    "--thickness", str(params.get('thickness', 0.02)),
                    "--scallop_pts", str(params.get('scallop_pts', 5)),
                    "--scallop_angle", str(params.get('scallop_angle', 90.0)),
                    "--nose_type", str(params.get('nose_type', 'smooth'))
                ]
                if params.get('flat_skin'):
                    cad_cmd.append("--flat_skin")
                
                self.log_to_gui(f"    [+] Executing CAD Engine: {' '.join(cad_cmd)}")
                process = subprocess.Popen(cad_cmd, cwd=cad_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for line in process.stdout:
                    self.log_to_gui(f"    [CAD] {line.strip()}")
                process.wait()
                
                if process.returncode == 0:
                    self.log_to_gui("[+] Geometry generated successfully.")
                    
                    # Generate Preview Plots (Domain only)
                    surf_file = os.path.join(cad_dir, "HIAD_custom.surf")
                    from source import visualizer
                    preview_path = os.path.join(self.cwd, "web", "assets", "plots", "domain_preview.png")
                    os.makedirs(os.path.dirname(preview_path), exist_ok=True)
                    visualizer.generate_preview(surf_file, preview_path, params=params)

                    self.window.evaluate_js("updateProgress(100)")
                    self.log_to_gui("[+] CAD Verification unlocked.")
                    self.window.evaluate_js("nextStep(4)")
                else:
                    self.log_to_gui("[-] Error: CAD Generation failed.")
            except Exception as e:
                self.log_to_gui(f"[-] Exception: {str(e)}")

        threading.Thread(target=run).start()

    def get_model_paths(self):
        """Page 4: Get paths for 3D rendering"""
        cad_dir = os.path.join(self.cwd, "CADDesign")
        # Assuming default output name is HIAD_custom
        stl_path = os.path.join(cad_dir, "HIAD_custom.stl")
        if os.path.exists(stl_path):
            # We need to serve this or copy to web/assets
            assets_dir = os.path.join(self.cwd, "web", "assets")
            os.makedirs(assets_dir, exist_ok=True)
            self._safe_copy(stl_path, os.path.join(assets_dir, "model.stl"))
            return {"stl": "assets/model.stl"}
        return {"error": "Model not found"}

    def parse_sparta_results(self):
        """Parses the SPARTA surface output files to extract metrics."""
        try:
            results_dir = os.path.join(self.cwd, "CADDesign", "results_reference")
            if not os.path.exists(results_dir):
                self.log_to_gui(f"    [!] Error: Results directory {results_dir} missing!")
                return {'drag': 1.0, 'heat': 1.0}
            
            # Find the latest surf output file
            surf_files = [f for f in os.listdir(results_dir) if f.startswith("surf.") and f.endswith(".out")]
            if not surf_files:
                return {'drag': 1.0, 'heat': 1.0}
            
            latest_file = os.path.join(results_dir, sorted(surf_files)[-1])
            
            drag_vals = []
            heat_vals = []
            with open(latest_file, 'r') as f:
                lines = f.readlines()
                start = False
                for line in lines:
                    if "ITEM: ENTRIES" in line:
                        start = True
                        continue
                    if start:
                        parts = line.split()
                        if len(parts) >= 6:
                            # col 1: id, 2: nflux, 3: mflux, 4: ke, 5: fx, 6: fy, 7: fz
                            heat_vals.append(float(parts[3])) # ke is col 4 (index 3)
                            drag_vals.append(float(parts[4])) # fx is col 5 (index 4)
                
                metrics = {
                    'drag': abs(np.sum(drag_vals)) if drag_vals else 1.0,
                    'heat': abs(np.sum(heat_vals)) if heat_vals else 1.0
                }
                return metrics
        except Exception:
            return {'drag': 1.0, 'heat': 1.0}

    def calculate_flight_metrics(self, sparta_res, opt_params, sample_dict):
        """Calculates derived flight metrics from DSMC results."""
        mass = float(sample_dict.get('mass', opt_params.get('base_mass', 281.0)))
        diameter = float(sample_dict.get('diameter', 3.0))
        area = np.pi * (diameter / 2)**2
        
        drag_force = sparta_res['drag']
        heat_flux = sparta_res['heat'] 
        
        # Ballistic Coefficient (beta)
        vstream = 10500.0 
        nrho = float(opt_params.get('env_nrho', 3.9e20))
        rho = nrho * (28.97e-3 / 6.022e23) 
        
        q = 0.5 * rho * (vstream**2)
        beta = mass * q / drag_force if drag_force > 0 else 0
        
        # Stagnation Heat Proxy (W/m^2)
        stag_heat = heat_flux / area if area > 0 else 0
        
        # Instantaneous g-load
        g_load = drag_force / (mass * 9.81) if mass > 0 else 0
        
        # 1D Thermal Model (Transient approximation for LOFTID/IRVE-3 F-TPS)
        # T_back = T_init + (q_stag * duration) / (rho * Cp * thickness)
        t_initial = 300.0 # K
        duration = 450.0  # s (Approx reentry pulse duration)
        tps_thickness = float(sample_dict.get('thickness', 0.02)) # m
        
        # F-TPS Properties (Flexible Thermal Protection System like LOFTID)
        # Using a composite density/Cp for Nextel/Pyrogel/Kapton layers
        rho_tps = 250.0  # kg/m^3
        cp_tps = 1100.0  # J/kg-K
        
        # Heat load (total energy per m^2)
        heat_load = stag_heat * duration
        
        # Temperature rise (Simplified 1D adiabatic backface estimate)
        # We assume a thermal diffusivity lag; only a fraction of energy reaches backface during pulse
        thermal_lag_factor = 0.15 
        t_rise = (heat_load * thermal_lag_factor) / (rho_tps * cp_tps * tps_thickness)
        
        t_backface = t_initial + t_rise
        
        # Surface Temperature (Radiative Equilibrium)
        sigma = 5.67e-8
        epsilon = 0.88 # High-temp SiC fabric
        t_surface = (stag_heat / (sigma * epsilon))**0.25 if stag_heat > 0 else 300
        
        return {
            'beta': beta,
            'stag_heat': stag_heat,
            'g_load': g_load,
            'surface_temp': t_surface,
            'backface_temp': t_backface
        }



    def get_msis_atmosphere(self, params):
        """Uses pymsis to fetch NRLMSIS 2.1 data."""
        try:
            from pymsis import msis
            import datetime
            import os
            import pymsis
            
            # Check for MSIS parameter file existence to prevent hard crash
            msis_data_path = os.path.join(os.path.dirname(pymsis.__file__), "pmsis21.parm")
            if not os.path.exists(msis_data_path):
                self.log_to_gui("[-] WARNING: NRLMSIS 2.1 data files missing. Falling back to Standard Earth.")
                return 3.9e20, 200.0

            alt = float(params.get('msis_alt', 80.0))
            lat = float(params.get('msis_lat', 0.0))
            lon = float(params.get('msis_lon', 0.0))
            f107 = float(params.get('msis_f107', 150.0))
            ap = float(params.get('msis_ap', 4.0))
            
            # Simplified date
            date = datetime.datetime(2026, 1, 1, 12, 0)
            
            # pymsis.msis.run(dates, lons, lats, alts, f107s, f107as, aps)
            output = msis.run(date, lon, lat, alt, f107, f107, ap, version=2.1)
            
            res = output.flatten()
            n_rho = np.sum(res[:9]) # Total number density
            temp = res[10] # Temperature at altitude
            
            return n_rho, temp
        except Exception as e:
            self.log_to_gui(f"[-] NRLMSIS Error: {e}. Using fallback.")
            return 3.9e20, 200.0 # Default fallback

    def get_atmosphere_data(self, params):
        """Returns calculated n_rho and temp for the UI."""
        preset = params.get('env_preset', 'artemis')
        if preset == 'nrlmsis':
            n_rho, temp = self.get_msis_atmosphere(params)
        elif preset == 'mars':
            n_rho, temp = 1.0e21, 150.0 # Mars baseline
        else:
            n_rho, temp = 3.9e20, 200.0 # Earth baseline
        return {"nrho": n_rho, "temp": temp}

    def get_chemistry_data(self, preset):
        """Returns (species_file, react_file, species_list, mixture_cmd) for the selected planet.
        Uses SPARTA's own bundled data files to guarantee format compatibility."""
        data_dir = os.path.join(self.cwd, "sparta", "data")
        
        if preset == 'mars':
            species_src = os.path.join(data_dir, "mars.species")
            react_src = os.path.join(data_dir, "mars.tce")
            vss_src = os.path.join(data_dir, "mars.vss")
            species_list = ["CO2", "N2", "CO", "O", "C", "N"]
            mixture = "mixture air CO2 N2 CO O C N\nmixture air CO2 frac 0.95\nmixture air N2 frac 0.03\nmixture air CO frac 0.01\nmixture air O frac 0.01"
        else: # Default Earth
            species_src = os.path.join(data_dir, "air.species")
            react_src = os.path.join(data_dir, "air.tce")
            vss_src = os.path.join(data_dir, "air.vss")
            species_list = ["N2", "O2", "NO", "N", "O"]
            mixture = "mixture air N2 O2 NO N O\nmixture air N2 frac 0.79\nmixture air O2 frac 0.21"
            
        return species_src, react_src, vss_src, species_list, mixture

    def _safe_copy(self, src, dst):
        """Copies a file only if it is not already the same file (handles hard links)."""
        if os.path.exists(dst) and os.path.samefile(src, dst):
            return
        shutil.copy(src, dst)

    def generate_sparta_script(self, opt_params, **kwargs):
        """Generates a complete SPARTA input script with dynamic geometry."""
        preset = opt_params.get('env_preset', 'artemis')
        species_src, react_src, vss_src, species_list, mixture_txt = self.get_chemistry_data(preset)
        
        # Current Physics State
        n_rho = opt_params.get('env_nrho', '3.9e20')
        temp_inf = opt_params.get('env_temp_inf', '200.0')

        # Current Geometry (varied or base)
        d_val = float(kwargs.get('diameter', opt_params.get('base_diameter', 3.0)))
        a_val = float(kwargs.get('angle', opt_params.get('base_angle', 60.0)))
        
        # Domain scaling (Honor GUI overrides if present)
        xmin = float(opt_params.get('env_xmin', -0.5 * d_val))
        xmax = float(opt_params.get('env_xmax', 1.2 * d_val))
        ymax = float(opt_params.get('env_ymax', 0.8 * d_val))
        
        react_model = opt_params.get('env_react', 'tce')
        react_cmd = f"react           {react_model} air.react" if react_model != 'none' else "# No reaction model"
        
        script = f"""# SPARTA Input Script - 8D Optimized
seed            12345
dimension       2
global          gridcut 0.0 comm/sort yes
boundary        o ar p

create_box      {xmin:.2f} {xmax:.2f} 0.0 {ymax:.2f} -0.5 0.5
create_grid     100 100 1
balance_grid    rcb cell

global          nrho {n_rho} fnum {opt_params.get('env_fnum', '1e16')}

species         air.species {" ".join(species_list)}
# Mixture Definition
{mixture_txt}
# Physical State
mixture         air vstream 10500.0 0.0 0.0
mixture         air temp {temp_inf}

fix             in emit/face air xlo twopass
collide         vss air air.vss
{react_cmd}

read_surf       {kwargs.get('surf_name', 'HIAD_opt')}.surf clip
surf_collide    1 diffuse {opt_params.get('env_temp', '1000.0')} 1.0
surf_modify     all collide 1

compute         1 surf all air nflux mflux ke
fix             1 ave/surf all 10 100 1000 c_1[*]

compute         surfF surf all air fx fy fz
fix             surfavg ave/surf all 10 100 1000 c_surfF[*]
compute         drag reduce sum f_surfavg[1]

compute         2 grid all air n u v w
fix             2 ave/grid all 10 100 1000 c_2[*]

compute         3 thermal/grid all air temp press
fix             3 ave/grid all 10 100 1000 c_3[*]

timestep        {opt_params.get('env_step', '1e-6')}

dump            1 surf all 1000 results_reference/surf.*.out id f_1[*] f_surfavg[*]
dump            2 grid all 1000 results_reference/grid.*.out id xlo ylo xhi yhi f_2[*] f_3[*]

stats           100
stats_style     step cpu np nattempt ncoll nscoll nscheck
run             {opt_params.get('env_run', '1000')}
"""
        return script

    def run_optimization(self, opt_params):
        """Page 7: Real Survivability Optimization using SPARTA DSMC (GUI Threaded)"""
        def run():
            try:
                self.log_to_gui("[*] INITIALIZING SURVIVABILITY OPTIMIZATION...")
                self.execute_optimization(opt_params, is_gui=True)
            except Exception as e:
                self.log_to_gui(f"[-] FATAL ERROR: {str(e)}")
                import traceback
                self.log_to_gui(f"    {traceback.format_exc()}")

        threading.Thread(target=run).start()

    def execute_optimization(self, opt_params, is_gui=False):
        """Core optimization logic, usable by both GUI and Headless runners."""
        if is_gui:
            self.window.evaluate_js("updateProgress(0)")
        
        samples_n = int(opt_params.get('samples', 5)) 
        d_min = float(opt_params.get('d_min', 2.5))
        d_max = float(opt_params.get('d_max', 4.5))
        goal = opt_params.get('goal', 'drag')

        self.log_to_gui(f"[*] OPTIMIZATION TARGET: {goal.upper()}")
        self.log_to_gui(f"[*] ------------------------------------------------")
        self.log_to_gui(f"[*] TOTAL SIMULATION SAMPLES TO RUN: {samples_n}")
        self.log_to_gui(f"[*] TOTAL STEPS PER SIMULATION:      {opt_params.get('env_run', '1000')}")
        self.log_to_gui(f"[*] ------------------------------------------------")
        
        # Gas & Environment Logging
        preset = opt_params.get('env_preset', 'artemis')
        self.log_to_gui(f"[*] ENVIRONMENT PRESET: {preset.upper()}")
        self.log_to_gui(f"    - Density (nrho): {opt_params.get('env_nrho', '3.9e20')} m^-3")
        self.log_to_gui(f"    - Temperature: {opt_params.get('env_temp_inf', '200.0')} K")
        self.log_to_gui(f"    - Particle Weight (fnum): {opt_params.get('env_fnum', '1e16')}")
        self.log_to_gui(f"    - Timestep: {opt_params.get('env_step', '1e-6')} s")
        self.log_to_gui(f"    - Surface Temp: {opt_params.get('env_temp', '1000.0')} K")
        
        _, _, _, species_list, _ = self.get_chemistry_data(preset)
        self.log_to_gui(f"    - Chemistry Species: {', '.join(species_list)}")

        # Domain info
        self.log_to_gui(f"    - Domain (X): [{opt_params.get('env_xmin', 'scaled')}, {opt_params.get('env_xmax', 'scaled')}]")
        self.log_to_gui(f"    - Domain (Y): [0, {opt_params.get('env_ymax', 'scaled')}]")

        cad_dir = os.path.join(self.cwd, "CADDesign")
        
        python_exec = self._get_python_exec()
        
        # 1. Establish Physics Baseline
        self.log_to_gui(f"[*] PHASE 1: ESTABLISHING PHYSICS BASELINE...")
        
        n_cores = os.cpu_count() or 1
        self.log_to_gui(f"[*] Detected {n_cores} CPU cores. Enabling parallel execution...")
        
        base_d = float(opt_params.get('base_diameter', 3.0))
        if is_gui: self.window.evaluate_js("updateProgress(5)")
        
        preset = opt_params.get('env_preset', 'artemis')
        species_src, react_src, vss_src, _, _ = self.get_chemistry_data(preset)
        self._safe_copy(species_src, os.path.join(cad_dir, "air.species"))
        self._safe_copy(react_src, os.path.join(cad_dir, "air.react"))
        self._safe_copy(vss_src, os.path.join(cad_dir, "air.vss"))

        base_d = float(opt_params.get('base_diameter', 3.0))
        script_baseline = self.generate_sparta_script(opt_params, surf_name="HIAD_custom", diameter=base_d)
        
        os.makedirs(os.path.join(cad_dir, "results_reference"), exist_ok=True)
        with open(os.path.join(cad_dir, "in.hiad"), 'w') as f: f.write(script_baseline)
        
        sim_start = time.time()
        self.log_to_gui(f"    [+] Running Baseline Simulation (D={base_d}m)...")
        subprocess.run(["docker", "rm", "-f", "hiad-runner"], capture_output=True)
        subprocess.run([
            "docker", "create", "--name", "hiad-runner",
            "-v", f"{cad_dir}:/workspace", "-e", "IN_DOCKER=1",
            "sparta-sim", "mpirun", "-np", str(n_cores), "--allow-run-as-root", "spa", "-in", "in.hiad"
        ], check=True)
        
        sim_proc = subprocess.Popen(["docker", "start", "-a", "hiad-runner"], cwd=self.cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in sim_proc.stdout:
            l = line.strip()
            if not l: continue
            if "Step" in l or "CPU time =" in l: self.log_to_gui(f"        {l}")
            # Log progress every 100 steps
            parts = l.split()
            if parts and parts[0].isdigit():
                step = int(parts[0])
                if step % 100 == 0: self.log_to_gui(f"        {l}")
        if sim_proc.wait() != 0:
            raise RuntimeError("Baseline SPARTA simulation failed! Check docker logs.")
        
        sim_end = time.time()
        baseline_time = sim_end - sim_start
        self.log_to_gui(f"    [+] Baseline established in {baseline_time:.2f}s.")
        
        ref_metric_dict = self.parse_sparta_results()
        ref_metric = ref_metric_dict[goal]
        
        base_sample = {k: v['base'] for k, v in search_map.items()}
        base_f_metrics = self.calculate_flight_metrics(ref_metric_dict, opt_params, base_sample)
        
        self.log_to_gui(f"    [+] BASELINE PHYSICS RESULT ({goal.upper()}): {ref_metric:.6f}")
        self.log_to_gui(f"    [+] FLIGHT METRICS:")
        self.log_to_gui(f"        - Ballistic Coeff (beta): {base_f_metrics['beta']:.2f} kg/m^2")
        self.log_to_gui(f"        - Peak Stagnation Heat:   {base_f_metrics['stag_heat']/1e3:.2f} kW/m^2")
        self.log_to_gui(f"        - Radiative Surf Temp:    {base_f_metrics['surface_temp']:.1f} K")
        self.log_to_gui(f"        - Instantaneous g-load:   {base_f_metrics['g_load']:.2f} g")
        self.log_to_gui(f"        - 1D Est. Backface Temp:  {base_f_metrics['backface_temp']:.1f} K")
        
        if is_gui: self.window.evaluate_js("updateProgress(10)")

        # 2. Define Search Space
        b_ang = float(opt_params.get('base_angle', 60.0))
        b_tor = int(opt_params.get('base_toroids', 7))
        b_nos = float(opt_params.get('base_nose', 0.191))
        b_thk = float(opt_params.get('base_thick', 0.02))
        b_spt = int(opt_params.get('base_scallop_pts', 5))
        b_san = float(opt_params.get('base_scallop_ang', 90.0))
        b_mas = float(opt_params.get('base_mass', 281.0))

        d_ang = float(opt_params.get('delta_angle', 15.0))
        d_tor = int(opt_params.get('delta_toroids', 3))
        d_nos = float(opt_params.get('delta_nose', 0.05))
        d_thk = float(opt_params.get('delta_thick', 0.01))
        d_spt = int(opt_params.get('delta_scallop_pts', 2))
        d_san = float(opt_params.get('delta_scallop_ang', 15.0))
        d_mas = float(opt_params.get('delta_mass', 50.0))

        search_map = {
            'diameter':      {'base': base_d,  'v': opt_params.get('v_diameter', True),    'min': d_min,               'max': d_max,               'type': float},
            'angle':         {'base': b_ang,   'v': opt_params.get('v_angle', True),       'min': max(10, b_ang-d_ang), 'max': min(85, b_ang+d_ang), 'type': float},
            'toroids':       {'base': b_tor,   'v': opt_params.get('v_toroids', True),     'min': max(3, b_tor-d_tor),  'max': b_tor+d_tor,         'type': int},
            'nose':          {'base': b_nos,   'v': opt_params.get('v_nose', True),        'min': max(0.05, b_nos-d_nos),'max': b_nos+d_nos,         'type': float},
            'thickness':     {'base': b_thk,   'v': opt_params.get('v_thick', False),      'min': max(0.001, b_thk-d_thk),'max': b_thk+d_thk,        'type': float},
            'scallop_pts':   {'base': b_spt,   'v': opt_params.get('v_scallop_pts', False),'min': max(2, b_spt-d_spt),  'max': b_spt+d_spt,         'type': int},
            'scallop_angle': {'base': b_san,   'v': opt_params.get('v_scallop_ang', False),'min': max(0, b_san-d_san),  'max': min(180, b_san+d_san), 'type': float},
            'mass':          {'base': b_mas,   'v': opt_params.get('v_mass', False),       'min': max(1, b_mas-d_mas),  'max': b_mas+d_mas,         'type': float},
        }

        active_params = [k for k, v in search_map.items() if v['v']]
        n_dim = len(active_params)
        if n_dim == 0:
            active_params = ['diameter']
            n_dim = 1
        
        self.log_to_gui(f"[*] SEARCH SPACE RANGES:")
        for p in active_params:
            p_info = search_map[p]
            self.log_to_gui(f"    - {p}: [{p_info['min']:.4f}, {p_info['max']:.4f}]")
            
        self.log_to_gui(f"[*] Search Space: {n_dim}D — [{', '.join(active_params)}]")

        # 3. LHS Sampling
        self.log_to_gui(f"[*] PHASE 2: GENERATING {samples_n} SBO SAMPLES (LHS)...")
        training_x = [] 
        training_y = [] 

        for i in range(samples_n):
            sample_dict = {k: v['base'] for k, v in search_map.items()}
            current_x_row = []
            for p_name in active_params:
                p_info = search_map[p_name]
                val = p_info['min'] + (p_info['max'] - p_info['min']) * (i + np.random.random()) / samples_n
                if p_info['type'] == int: val = int(round(val))
                sample_dict[p_name] = val
                current_x_row.append(val)
            
            self.log_to_gui(f"[*] SAMPLE {i+1}/{samples_n}: {', '.join([f'{k}={sample_dict[k]}' for k in active_params])}")
            script_content = self.generate_sparta_script(opt_params, surf_name="HIAD_opt", **sample_dict)
            with open(os.path.join(cad_dir, "in.hiad"), 'w') as f: f.write(script_content)

            cmd_cad = [python_exec, "make_HIAD.py", "--diameter", str(sample_dict['diameter']), "--angle", str(sample_dict['angle']), 
                       "--toroids", str(sample_dict['toroids']), "--nose", str(sample_dict['nose']), "--thickness", str(sample_dict['thickness']),
                       "--scallop_pts", str(sample_dict['scallop_pts']), "--scallop_angle", str(sample_dict['scallop_angle']), "--output", "HIAD_opt"]
            subprocess.run(cmd_cad, cwd=cad_dir, check=True)
            
            self.log_to_gui(f"    [*] Cleaning stale containers...")
            subprocess.run(["docker", "rm", "-f", "hiad-runner"], capture_output=True)
            self.log_to_gui(f"    [*] Initializing Docker runner...")
            subprocess.run(["docker", "create", "--name", "hiad-runner", "-v", f"{cad_dir}:/workspace", "-e", "IN_DOCKER=1", "sparta-sim", "mpirun", "-np", str(n_cores), "--allow-run-as-root", "spa", "-in", "in.hiad"], check=True)
            
            self.log_to_gui(f"    [*] Executing SPARTA solver (Sample {i+1})...")
            sample_start = time.time()
            sim_proc = subprocess.Popen(["docker", "start", "-a", "hiad-runner"], cwd=self.cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            
            last_cpu = ""
            for line in sim_proc.stdout:
                l = line.strip()
                if not l: continue
                if "CPU time =" in l: 
                    last_cpu = l
                    continue
                if "Step" in l: 
                    self.log_to_gui(f"        {l}")
                    continue
                    
                # Log progress every 100 steps
                parts = l.split()
                if parts and parts[0].isdigit():
                    step = int(parts[0])
                    if step % 100 == 0: self.log_to_gui(f"        {l}")
            
            if sim_proc.wait() != 0:
                self.log_to_gui(f"    [-] FATAL: SPARTA Solver Crash on Sample {i+1}!")
            else:
                if last_cpu: self.log_to_gui(f"        {last_cpu}")
            
            sample_end = time.time()
            sample_dur = sample_end - sample_start
            
            res_dict = self.parse_sparta_results()
            val = res_dict[goal]
            f_metrics = self.calculate_flight_metrics(res_dict, opt_params, sample_dict)
            
            training_x.append(current_x_row)
            training_y.append([val])
            
            remaining = samples_n - (i + 1)
            etr = remaining * sample_dur
            
            self.log_to_gui(f"[*] ------------------------------------------------")
            self.log_to_gui(f"[*] SAMPLE {i+1} COMPLETE (Duration: {sample_dur:.2f}s)")
            self.log_to_gui(f"[*] RESULT ({goal.upper()}): {val:.6f}")
            self.log_to_gui(f"[*] FLIGHT METRICS:")
            self.log_to_gui(f"    - Ballistic Coeff (beta): {f_metrics['beta']:.2f} kg/m^2")
            self.log_to_gui(f"    - Peak Stagnation Heat:   {f_metrics['stag_heat']/1e3:.2f} kW/m^2")
            self.log_to_gui(f"    - Radiative Surf Temp:    {f_metrics['surface_temp']:.1f} K")
            self.log_to_gui(f"    - Instantaneous g-load:   {f_metrics['g_load']:.2f} g")
            self.log_to_gui(f"    - 1D Est. Backface Temp:  {f_metrics['backface_temp']:.1f} K")
            self.log_to_gui(f"[*] PARAMS: {', '.join([f'{k}={sample_dict[k]}' for k in active_params])}")
            self.log_to_gui(f"[*] ------------------------------------------------")

            if remaining > 0:
                self.log_to_gui(f"    [*] Estimated Time Remaining: {etr/60:.1f} minutes")
            
            if is_gui: self.window.evaluate_js(f"updateProgress({10 + int((i+1)/samples_n * 50)})")

        # 4. Metamodel Training
        self.log_to_gui(f"[*] Training {n_dim}D Metamodel Prognosis (MoP) via PyTorch...")
        import torch
        import torch.nn as nn
        import torch.optim as optim
        device = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
        X_tensor = torch.tensor(training_x, dtype=torch.float32).to(device)
        Y_tensor = torch.tensor(training_y, dtype=torch.float32).to(device)
        model = nn.Sequential(nn.Linear(n_dim, 64), nn.ReLU(), nn.Linear(64, 64), nn.ReLU(), nn.Linear(64, 1)).to(device)
        optimizer = optim.Adam(model.parameters(), lr=0.01)
        for _ in range(500):
            optimizer.zero_grad()
            loss = nn.MSELoss()(model(X_tensor), Y_tensor)
            loss.backward(); optimizer.step()
            if loss.item() < 1e-6: break
        self.log_to_gui(f"    [+] Model Trained. Final Loss: {loss.item():.6f}")

        # 5. GA Optimization
        self.log_to_gui(f"[*] Steering {n_dim}D Survivability Optimization (GA)...")
        best_config = {k: v['base'] for k, v in search_map.items()}
        min_cost = 1e18
        targets = opt_params.get('targets', {})
        for _ in range(10000):
            test_row = []
            test_sample_dict = {k: v['base'] for k, v in search_map.items()}
            for p_name in active_params:
                p_info = search_map[p_name]
                val = p_info['min'] + (p_info['max'] - p_info['min']) * np.random.random()
                if p_info['type'] == int: val = int(round(val))
                test_sample_dict[p_name] = val
                test_row.append(val)
            t_val = torch.tensor([test_row], dtype=torch.float32).to(device)
            pred_val = model(t_val).item()
            area = np.pi * (test_sample_dict['diameter']/2)**2
            beta_calc = test_sample_dict['mass'] / (1.5 * area)
            cost = 0
            t_beta = float(targets.get('beta', {}).get('val', 150))
            cost += ((beta_calc - t_beta) / 10.0)**2
            target_val = float(targets.get(goal, {}).get('val', 100))
            cost += ((pred_val - target_val) / 1.0)**2
            if cost < min_cost:
                min_cost = cost
                best_config = test_sample_dict
                best_val = pred_val

        self.log_to_gui(f"    [!] Optimal: {', '.join([f'{k}={best_config[k]}' for k in active_params])}")
        if is_gui: self.window.evaluate_js("updateProgress(85)")

        # 6. Final Validation
        self.log_to_gui("[*] Executing Final Validation SPARTA Simulation...")
        cmd_final = [python_exec, "make_HIAD.py", "--diameter", str(best_config['diameter']), "--angle", str(best_config['angle']), 
                     "--toroids", str(best_config['toroids']), "--nose", str(best_config['nose']), "--thickness", str(best_config['thickness']),
                     "--scallop_pts", str(best_config['scallop_pts']), "--scallop_angle", str(best_config['scallop_angle']), "--output", "HIAD_final"]
        subprocess.run(cmd_final, cwd=cad_dir, check=True)
        
        final_script = self.generate_sparta_script(opt_params, surf_name="HIAD_final", **best_config)
        with open(os.path.join(cad_dir, "in.hiad"), 'w') as f: f.write(final_script)
        subprocess.run(["docker", "rm", "-f", "hiad-runner"], capture_output=True)
        subprocess.run(["docker", "create", "--name", "hiad-runner", "-v", f"{cad_dir}:/workspace", "-e", "IN_DOCKER=1", "sparta-sim", "spa", "-in", "in.hiad"], check=True)
        subprocess.run(["docker", "start", "-a", "hiad-runner"], cwd=self.cwd, check=True)

        if is_gui:
            self.log_to_gui("[*] Compiling Simulation Animation (GUI Post-process)...")
            from source import visualizer
            grid_dir = os.path.join(cad_dir, "results_reference")
            grid_files = sorted([os.path.join(grid_dir, f) for f in os.listdir(grid_dir) if f.startswith("grid.") and f.endswith(".out")])
            ani_path = os.path.join(self.cwd, "web", "assets", "plots", "simulation_anim.mp4")
            visualizer.generate_animation(grid_files, ani_path)
            visualizer.generate_plots(grid_files[-1], os.path.join(self.cwd, "web", "assets", "plots"))

            self.window.evaluate_js("updateProgress(100)")
            self.log_to_gui("[+] OPTIMIZATION LIFECYCLE COMPLETE.")
            res_data = {
                "ref": f"Base D: {training_x[0][0]:.2f}m\nDrag: {training_y[0][0]:.4f}",
                "opt": f"Opt D: {best_config['diameter']:.2f}m\nFinal Metric: {best_val:.4f}"
            }
            self.window.evaluate_js(f"document.getElementById('res-ref').innerText = `{res_data['ref']}`")
            self.window.evaluate_js(f"document.getElementById('res-opt').innerText = `{res_data['opt']}`")
            self.window.evaluate_js("document.getElementById('img-thermal').src = 'assets/plots/thermal_map.png?' + new Date().getTime()")
            self.window.evaluate_js("document.getElementById('img-pressure').src = 'assets/plots/pressure_map.png?' + new Date().getTime()")
            self.window.evaluate_js("document.getElementById('img-velocity').src = 'assets/plots/velocity_vectors.png?' + new Date().getTime()")
            time.sleep(1)
            self.window.evaluate_js("nextStep(8)")
        else:
            self.log_to_gui("[+] OPTIMIZATION COMPLETE (Headless). Result in results_reference/")
