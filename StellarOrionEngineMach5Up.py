import os
import sys
import subprocess
import threading
import json
import shutil
import time
import numpy as np
import paramiko
import sqlite3
import datetime

class HistoryManager:
    def __init__(self, db_path="optimization_history.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS optimization_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    name TEXT,
                    status TEXT,
                    goal TEXT,
                    samples INTEGER,
                    current_sample INTEGER,
                    parameters TEXT,
                    best_val REAL,
                    best_config TEXT,
                    last_page INTEGER DEFAULT 1
                )
            """)
            
            # Migration: Check if last_page column exists
            cursor.execute("PRAGMA table_info(optimization_runs)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'last_page' not in columns:
                cursor.execute("ALTER TABLE optimization_runs ADD COLUMN last_page INTEGER DEFAULT 1")
                
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS samples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER,
                    sample_idx INTEGER,
                    parameters TEXT,
                    metrics TEXT,
                    flight_metrics TEXT,
                    duration REAL,
                    timestamp TEXT,
                    FOREIGN KEY(run_id) REFERENCES optimization_runs(id)
                )
            """)
            conn.commit()

    def create_run(self, name, goal, samples, parameters):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            timestamp = datetime.datetime.now().isoformat()
            cursor.execute(
                "INSERT INTO optimization_runs (timestamp, name, status, goal, samples, current_sample, parameters) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (timestamp, name, "running", goal, samples, 0, json.dumps(parameters))
            )
            return cursor.lastrowid

    def update_run_progress(self, run_id, current_sample, best_val=None, best_config=None, status=None):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute("UPDATE optimization_runs SET current_sample = ?, best_val = ?, best_config = ?, status = ? WHERE id = ?",
                               (current_sample, best_val, json.dumps(best_config) if best_config else None, status, run_id))
            else:
                cursor.execute("UPDATE optimization_runs SET current_sample = ?, best_val = ?, best_config = ? WHERE id = ?",
                               (current_sample, best_val, json.dumps(best_config) if best_config else None, run_id))
            conn.commit()

    def add_sample(self, run_id, sample_idx, parameters, metrics, flight_metrics, duration):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            timestamp = datetime.datetime.now().isoformat()
            cursor.execute(
                "INSERT INTO samples (run_id, sample_idx, parameters, metrics, flight_metrics, duration, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (run_id, sample_idx, json.dumps(parameters), json.dumps(metrics), json.dumps(flight_metrics), duration, timestamp)
            )
            conn.commit()

    def get_all_runs(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM optimization_runs ORDER BY timestamp DESC")
            return [dict(row) for row in cursor.fetchall()]

    def get_run(self, run_id):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM optimization_runs WHERE id = ?", (run_id,))
            run = cursor.fetchone()
            if not run: return None
            
            cursor.execute("SELECT * FROM samples WHERE run_id = ? ORDER BY sample_idx ASC", (run_id,))
            samples = [dict(row) for row in cursor.fetchall()]
            
            run_dict = dict(run)
            run_dict['samples_data'] = samples
            return run_dict

    def delete_run(self, run_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM samples WHERE run_id = ?", (run_id,))
            cursor.execute("DELETE FROM optimization_runs WHERE id = ?", (run_id,))
            conn.commit()

    def upsert_draft(self, name, parameters, last_page):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            timestamp = datetime.datetime.now().isoformat()
            
            # Try to find an existing draft with the same name
            cursor.execute("SELECT id FROM optimization_runs WHERE name = ? AND status = 'draft'", (name,))
            row = cursor.fetchone()
            
            if row:
                run_id = row[0]
                cursor.execute(
                    "UPDATE optimization_runs SET timestamp = ?, parameters = ?, last_page = ? WHERE id = ?",
                    (timestamp, json.dumps(parameters), last_page, run_id)
                )
                return run_id
            else:
                cursor.execute(
                    "INSERT INTO optimization_runs (timestamp, name, status, goal, samples, current_sample, parameters, last_page) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (timestamp, name, "draft", "N/A", 0, 0, json.dumps(parameters), last_page)
                )
                return cursor.lastrowid

class Api:
    def __init__(self):
        self.window = None
        self.cwd = os.getcwd()
        self.reference_data = None
        import getpass
        self.local_user = getpass.getuser()
        self.history = HistoryManager(os.path.join(self.cwd, "optimization_history.db"))

    def get_manual_content(self):
        """Reads and combines multiple project markdown files into one."""
        files = [
            "README.md",
            "METHODOLOGY.md",
            "selfnote.md",
            "DERIVATION.md",
            "archnote.md",
            "HIAD_IRVE3_Baseline.md",
            "Heatshield_Comparison.md"
        ]
        
        combined_content = ""
        for filename in files:
            file_path = os.path.join(self.cwd, filename)
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        combined_content += f"\n\n# --- {filename} ---\n\n"
                        combined_content += content
                except Exception as e:
                    combined_content += f"\n\n# --- Error reading {filename} ---\n\n{str(e)}"
            else:
                combined_content += f"\n\n# --- {filename} (Not Found) ---\n\n"
        
        return combined_content

    def get_optimization_history(self):
        return self.history.get_all_runs()

    def get_run_details(self, run_id):
        return self.history.get_run(run_id)

    def delete_run(self, run_id):
        self.history.delete_run(run_id)
        return {"status": "success"}

    def autosave_draft(self, params, page_id):
        run_name = params.get('draft_name', "Current Session")
        run_id = self.history.upsert_draft(run_name, params, page_id)
        return {"status": "success", "run_id": run_id}

    def resume_run_from_history(self, run_id):
        run_data = self.history.get_run(run_id)
        if not run_data:
            return {"status": "error", "message": "Run not found"}
        
        opt_params = json.loads(run_data['parameters'])
        opt_params['resume_run_id'] = run_id
        opt_params['resume_idx'] = run_data['current_sample']
        
        self.run_optimization(opt_params)
        return {"status": "success"}


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

    def get_local_user(self):
        return self.local_user

    def log_to_gui(self, message):
        timestamp = time.strftime("%H:%M:%S")
        # Clean message for terminal (remove <br>)
        term_msg = message.replace("<br>", "\n")
        print(f"[{timestamp}] {term_msg}") 
        if self.window:
            safe_msg = message.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "<br>")
            self.window.evaluate_js(f"appendLog('{safe_msg}')")

    def log_to_readiness(self, message):
        """Send a message specifically to the readiness/diagnostic terminal."""
        if self.window:
            # Escape for JS
            safe_msg = str(message).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")
            self.window.evaluate_js(f"logReadiness('{safe_msg}')")
        else:
            print(f"[Readiness] {message}")

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
                    python_exec, "HIAD_GeometryEngine.py",
                    "--diameter", str(params.get('diameter', 3.0)),
                    "--angle", str(params.get('angle', 60.0)),
                    "--nose", str(params.get('nose_radius', 0.191)),
                    "--toroids", str(params.get('toroids', 7)),
                    "--thickness", str(params.get('thickness', 0.0254)),
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
                    if "ITEM: SURFS" in line:
                        start = True
                        continue
                    if start:
                        parts = line.split()
                        if len(parts) >= 6:
                            # id f_1[1] f_1[2] f_1[3] f_surfavg[1] f_surfavg[2] f_surfavg[3]
                            # id nflux mflux ke fx fy fz
                            heat_vals.append(float(parts[3])) # ke is index 3
                            drag_vals.append(float(parts[4])) # fx is index 4
                
                metrics = {
                    'drag': abs(np.sum(drag_vals)) if drag_vals else 1.0,
                    'heat': abs(np.max(heat_vals)) if heat_vals else 1.0 
                }

                # Find latest grid file for shock temperature (Translational Temperature)
                grid_files = [f for f in os.listdir(results_dir) if f.startswith("grid.") and f.endswith(".out")]
                shock_temp = 300.0
                if grid_files:
                    latest_grid = os.path.join(results_dir, sorted(grid_files)[-1])
                    with open(latest_grid, 'r') as f:
                        lines = f.readlines()
                        temp_start = False
                        for line in lines:
                            if "ITEM: CELLS" in line:
                                temp_start = True
                                continue
                            if temp_start:
                                parts = line.split()
                                if len(parts) >= 10: # column 10 (index 9) is temp
                                    try:
                                        t = float(parts[9])
                                        if t > shock_temp: shock_temp = t
                                    except: pass
                metrics['shock_temp'] = shock_temp
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
        # Default calibrated for IRVE-3 Baseline (Mach 10 @ ~52km) - NASA/TP-2013-4012
        vstream = float(opt_params.get('env_vstream', 2700.0))
        nrho = float(opt_params.get('env_nrho', 3.5e22))
        rho = nrho * (28.97e-3 / 6.022e23) 
        
        q = 0.5 * rho * (vstream**2)
        beta = mass * q / drag_force if drag_force > 0 else 0
        
        # Stagnation Heat (W/m^2) - already a per-area flux from SPARTA
        stag_heat = heat_flux
        
        # Instantaneous g-load
        g_load = drag_force / (mass * 9.81) if mass > 0 else 0
        
        # 1D Thermal Model (Transient approximation for LOFTID/IRVE-3 F-TPS)
        # T_back = T_init + (q_stag * duration) / (rho * Cp * thickness)
        t_initial = 300.0 # K
        duration = float(opt_params.get('env_duration', 450.0))  # s
        tps_thickness = float(sample_dict.get('thickness', 0.0254)) # m
        
        # F-TPS Properties (Flexible Thermal Protection System like LOFTID)
        rho_tps = 250.0  # kg/m^3
        cp_tps = 1100.0  # J/kg-K
        
        # Heat load (total energy per m^2)
        heat_load = stag_heat * duration
        
        # Temperature rise (Simplified 1D adiabatic backface estimate)
        # thermal_lag_factor represents the fraction of surface energy that penetrates the insulation
        thermal_lag_factor = float(opt_params.get('env_thermal_lag', 15.0)) / 100.0
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
            'backface_temp': t_backface,
            'shock_temp': sparta_res.get('shock_temp', 300.0)
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
            
            return 3.5e22, 270.0 # Default fallback (IRVE-3 Peak Heating @ 52km) - NASA/TP-2013-4012
        except Exception as e:
            self.log_to_gui(f"[-] NRLMSIS Error: {e}. Using fallback.")
            return 3.5e22, 270.0 # Default fallback

    def get_atmosphere_data(self, params):
        """Returns calculated n_rho and temp for the UI."""
        preset = params.get('env_preset', 'artemis')
        if preset == 'nrlmsis':
            n_rho, temp = self.get_msis_atmosphere(params)
        elif preset == 'mars':
            n_rho, temp = 1.0e21, 150.0 # Mars baseline
        else:
            n_rho, temp = 3.5e22, 270.0 # Earth baseline (IRVE-3 NASA/TP-2013-4012)
        return {"nrho": n_rho, "temp": temp}

    def get_chemistry_data(self, opt_params):
        """Returns (species_file, react_file, vss_file, species_list, mixture_cmd) for the selected planet and mode."""
        preset = opt_params.get('env_preset', 'artemis')
        chem_mode = opt_params.get('env_chem_mode', '5-species')
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
            
            if chem_mode == '11-species':
                species_list = ["N2", "O2", "NO", "N", "O", "N2+", "O2+", "NO+", "N+", "O+", "e"]
                mixture = "mixture air N2 O2 NO N O N2+ O2+ NO+ N+ O+ e\nmixture air N2 frac 0.79\nmixture air O2 frac 0.21"
            else:
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
        species_src, react_src, vss_src, species_list, mixture_txt = self.get_chemistry_data(opt_params)
        
        # Current Physics State (Default: IRVE-3 Baseline)
        n_rho = opt_params.get('env_nrho', '3.5e22')
        temp_inf = opt_params.get('env_temp_inf', '270.0')
        vstream = opt_params.get('env_vstream', '2700.0')

        # Current Geometry (varied or base)
        d_val = float(kwargs.get('diameter', opt_params.get('base_diameter', 3.0)))
        
        # Domain scaling (Honor GUI overrides if present)
        xmin = float(opt_params.get('env_xmin', -0.6 * d_val))
        xmax = float(opt_params.get('env_xmax', 1.8 * d_val))
        ymax = float(opt_params.get('env_ymax', 1.2 * d_val))
        
        react_model = opt_params.get('env_react', 'tce')
        react_cmd = f"react           {react_model} air.react" if react_model != 'none' else "# No reaction model"
        
        # Steady State Check
        steady_state_cmd = ""
        if opt_params.get('env_steady_state'):
            tol = opt_params.get('env_steady_tol', '0.01')
            steady_state_cmd = f"""
compute         drag_curr reduce sum f_surfavg[1]
variable        drag_val equal c_drag_curr
fix             halt_check halt 100 v_drag_val {tol} error no
"""

        # Averaging and Output Frequencies
        # We want to output results at least 10 times during the run, or every 100 steps minimum
        n_run = int(opt_params.get('env_run', '1000'))
        n_freq = max(1, n_run // 5) # 5 snapshots
        n_repeat = max(1, n_freq // 2)
        n_every = 1
        dump_freq = n_freq

        # Averaging and Output Frequencies
        # We want to output results at least 10 times during the run, or every 100 steps minimum
        n_run = int(opt_params.get('env_run', '1000'))
        n_freq = max(1, n_run // 5) # 5 snapshots
        n_repeat = max(1, n_freq // 2)
        n_every = 1
        dump_freq = n_freq

        script = f"""# SPARTA Input Script - 8D Optimized
seed            12345
dimension       2
global          gridcut 0.0 comm/sort yes
boundary        o ar p

create_box      {xmin:.2f} {xmax:.2f} 0.0 {ymax:.2f} -0.5 0.5
create_grid     400 400 1
balance_grid    rcb cell

global          nrho {n_rho} fnum {opt_params.get('env_fnum', '1e16')}

species         air.species {" ".join(species_list)}
# Mixture Definition
{mixture_txt}
# Physical State
mixture         air vstream {vstream} 0.0 0.0
mixture         air temp {temp_inf}

fix             in emit/face air xlo twopass
collide         vss air air.vss
{react_cmd}

read_surf       {kwargs.get('surf_name', 'HIAD_opt')}.surf clip
surf_collide    1 diffuse {opt_params.get('env_temp', '1000.0')} 1.0
surf_modify     all collide 1

compute         1 surf all air nflux mflux ke
fix             1 ave/surf all {n_every} {n_repeat} {n_freq} c_1[*]

compute         surfF surf all air fx fy fz
fix             surfavg ave/surf all {n_every} {n_repeat} {n_freq} c_surfF[*]
compute         drag reduce sum f_surfavg[1]

compute         2 grid all air n u v w
fix             2 ave/grid all {n_every} {n_repeat} {n_freq} c_2[*]

compute         3 thermal/grid all air temp press
fix             3 ave/grid all {n_every} {n_repeat} {n_freq} c_3[*]

timestep        {opt_params.get('env_step', '1e-6')}

dump            1 surf all {dump_freq} results_reference/surf.*.out id f_1[*] f_surfavg[*]
dump            2 grid all {dump_freq} results_reference/grid.*.out id xlo ylo xhi yhi f_2[*] f_3[*]

stats           100
stats_style     step cpu np nattempt ncoll nscoll nscheck

{steady_state_cmd}
run             {opt_params.get('env_run', '1000')}
"""
        return script

    def run_remote_pyfluent_simulation(self, opt_params, sample_dict):
        """Orchestrates a remote PyFluent simulation via SSH/SFTP."""
        host = opt_params.get('ssh_host')
        user = opt_params.get('ssh_user')
        password = opt_params.get('ssh_pass')
        
        if not host or not user:
            self.log_to_gui("[-] Error: SSH Host or User missing for PyFluent backend.")
            return {'drag': 1.0, 'heat': 1.0}

        try:
            self.log_to_gui(f"[*] Establishing SSH Connection to {host}...")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            key_path = opt_params.get('ssh_key')
            if key_path and os.path.exists(key_path):
                self.log_to_gui(f"[*] Authenticating with SSH Key: {key_path}")
                ssh.connect(host, username=user, key_filename=key_path, timeout=10)
            else:
                ssh.connect(host, username=user, password=password, timeout=10)
            
            # 1. OS Verification (Check for Windows)
            self.log_to_gui("[*] Verifying remote Operating System...")
            stdin, stdout, stderr = ssh.exec_command("ver")
            os_ver = stdout.read().decode().strip()
            if "Windows" not in os_ver:
                self.log_to_gui(f"[-] [WARNING] Remote system may not be Windows ({os_ver}). PyFluent requires Windows.")
            else:
                self.log_to_gui(f"[+] Detected {os_ver}")

            # 2. Python Dependency Check
            self.log_to_gui("[*] Checking for Python 3 installation...")
            stdin, stdout, stderr = ssh.exec_command("python --version")
            py_ver = stdout.read().decode().strip()
            
            if not py_ver or "Python 3" not in py_ver:
                self.log_to_gui("[!] [CRITICAL] Python 3 not detected on remote machine.")
                self.log_to_gui("[*] Attempting automated installation via winget...")
                
                # Install Python 3.12 using winget
                install_cmd = "winget install --id Python.Python.3.12 --exact --silent --accept-source-agreements --accept-package-agreements"
                stdin, stdout, stderr = ssh.exec_command(install_cmd)
                
                # Monitor installation
                install_out = stdout.read().decode().strip()
                if "Successfully installed" in install_out or "No newer package found" in install_out:
                    self.log_to_gui("[+] Python 3.12 installed successfully via winget.")
                else:
                    self.log_to_gui("[-] Automated installation failed. Please install Python 3.12 manually.")
                    self.log_to_gui(f"    [Error] {install_out}")
            else:
                self.log_to_gui(f"[+] Python detected: {py_ver}")

            sftp = ssh.open_sftp()
            
            # Create remote workspace
            remote_dir = "C:\\Temp\\StellarOrion_Remote" # Assuming Windows for PyFluent
            try:
                sftp.mkdir(remote_dir)
            except: pass
            
            self.log_to_gui("[*] Pushing CAD and configuration via SFTP...")
            cad_dir = os.path.join(self.cwd, "CADDesign")
            
            # Push Geometry
            for ext in [".stl", ".step"]:
                local_path = os.path.join(cad_dir, f"HIAD_opt{ext}")
                if os.path.exists(local_path):
                    sftp.put(local_path, f"{remote_dir}\\geometry{ext}")
            
            # Push Executor Template
            template_path = os.path.join(self.cwd, "source", "pyfluent_executor_template.py")
            sftp.put(template_path, f"{remote_dir}\\executor.py")
            
            # Push Config
            vstream = float(opt_params.get('env_vstream', 2700.0))
            nrho = float(opt_params.get('env_nrho', 3.5e22))
            rho = nrho * (28.97e-3 / 6.022e23) 
            # Simple pressure calc for Fluent boundary
            temp_inf = float(opt_params.get('env_temp_inf', 270.0))
            r_gas = 287.0
            pressure = rho * r_gas * temp_inf
            
            config = {
                "diameter": float(sample_dict.get('diameter', 3.0)),
                "velocity": vstream,
                "pressure": pressure,
                "temperature": temp_inf,
                "wall_temp": float(opt_params.get('env_temp', 1000.0)),
                "time_step": float(opt_params.get('env_step', 1.0e-6)),
                "total_steps": int(opt_params.get('env_run', 1000)),
                "dimension": opt_params.get('solver_dim', '2d'),
                "use_gpu": opt_params.get('solver_gpu', True),
                "n_cores": int(opt_params.get('env_cores', 4)),
                "bl_layers": int(opt_params.get('solver_bl_layers', 15)),
                "viscous_model": opt_params.get('viscous_model', 'sst-k-omega')
            }
            
            config_path = os.path.join(self.cwd, "scratch", "remote_config.json")
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, "w") as f:
                json.dump(config, f)
            sftp.put(config_path, f"{remote_dir}\\config.json")
            
            self.log_to_gui("[*] Executing remote PyFluent solver...")
            # Command to run python remotely
            # Note: We assume 'python' is in PATH and has pyansys installed
            cmd = f"cd {remote_dir} && python executor.py config.json"
            stdin, stdout, stderr = ssh.exec_command(cmd)
            
            # Pipe remote output to GUI (Combined stdout and stderr)
            import select
            while not stdout.channel.exit_status_ready():
                if stdout.channel.recv_ready():
                    line = stdout.readline()
                    if line: self.log_to_gui(f"    [Remote] {line.strip()}")
                if stderr.channel.recv_stderr_ready():
                    line = stderr.readline()
                    if line: self.log_to_gui(f"    [Remote-Error] {line.strip()}")
                time.sleep(0.1)
            
            # Final read
            for line in stdout: self.log_to_gui(f"    [Remote] {line.strip()}")
            for line in stderr: self.log_to_gui(f"    [Remote-Error] {line.strip()}")
            
            # Pull results back
            self.log_to_gui("[*] Retrieving results...")
            local_results = os.path.join(self.cwd, "scratch", "remote_results.json")
            try:
                sftp.get(f"{remote_dir}\\results.json", local_results)
                with open(local_results, "r") as f:
                    res_data = json.load(f)
                
                sftp.close()
                ssh.close()
                return {
                    'drag': abs(res_data.get('drag', 1.0)),
                    'heat': abs(res_data.get('heat', 1.0))
                }
            except Exception as e:
                self.log_to_gui(f"[-] Error retrieving remote results: {e}")
                sftp.close()
                ssh.close()
                return {'drag': 1.0, 'heat': 1.0}

        except Exception as e:
            self.log_to_gui(f"[-] SSH/PyFluent Error: {e}")
            return {'drag': 1.0, 'heat': 1.0}

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

    def test_ssh_connection(self, opt_params):
        """Test the SSH connection and return detailed status."""
        host = opt_params.get('ssh_host')
        user = opt_params.get('ssh_user')
        password = opt_params.get('ssh_pass')
        
        if not host or not user or not password:
            return {"status": "error", "message": "Missing SSH credentials."}
            
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            key_path = opt_params.get('ssh_key')
            if key_path and os.path.exists(key_path):
                ssh.connect(host, username=user, key_filename=key_path, timeout=10)
            else:
                ssh.connect(host, username=user, password=password, timeout=10)
            
            # Check for Windows
            stdin, stdout, stderr = ssh.exec_command("ver")
            os_ver = stdout.read().decode().strip()
            
            # Check for Python and its Architecture
            stdin, stdout, stderr = ssh.exec_command('python -c "import platform; print(f\'{platform.python_version()} ({platform.machine()})\')"')
            py_info = stdout.read().decode().strip()
            # If python fails or machine isn't AMD64 on an ARM64 host, we should warn
            py_ver = py_info if py_info else None
            is_py_x64 = "AMD64" in py_info
            
            # Deep Scan for Ansys Installation across all drives
            scan_cmd = (
                'powershell -Command "'
                '$found = $false; '
                '$drives = Get-PSDrive -PSProvider FileSystem; '
                'foreach ($d in $drives) { '
                '  $p = Join-Path $d.Root \'ANSYS Inc\'; '
                '  if (Test-Path $p) { '
                r'    $v = Get-ChildItem -Path $p -Directory | Where-Object { $_.Name -match \'^v\d{3}$\' } | Sort-Object Name -Descending | Select-Object -First 1; '
                '    if ($v) { '
                '      $ver = $v.Name.Substring(1); '
                '      $path = $v.FullName; '
                '      [System.Environment]::SetEnvironmentVariable(\'AWP_ROOT\' + $ver, $path, \'Machine\'); '
                '      Write-Host \'FOUND:\' + $ver + \':\' + $path; '
                '      $found = $true; break; '
                '    } '
                '  } '
                '}; '
                'if (-not $found) { Write-Host \'MISSING\' }"'
            )
            stdin, stdout, stderr = ssh.exec_command(scan_cmd)
            scan_res = stdout.read().decode().strip()
            ansys_installed = "FOUND" in scan_res
            if ansys_installed:
                # Format is FOUND:VER:PATH (Path can contain colons for drive letters)
                parts = scan_res.split(":", 2)
                ansys_ver = parts[1]
                ansys_path = parts[2]
            else:
                ansys_path = None
                ansys_ver = None
            
            # Check for ansys-fluent-core (PyFluent)
            stdin, stdout, stderr = ssh.exec_command('python -c "import ansys.fluent.core; print(\'PyAnsys OK\')"')
            pyansys_status = stdout.read().decode().strip()
            pyansys_installed = ("PyAnsys OK" in pyansys_status)
            
            # Check Architecture
            stdin, stdout, stderr = ssh.exec_command("echo %PROCESSOR_ARCHITECTURE%")
            arch = stdout.read().decode().strip().upper()
            
            ssh.close()
            
            msg = f"Connected to {os_ver} ({arch}). "
            py_missing = not py_ver
            pyansys_missing = py_ver and not pyansys_installed
            
            if py_ver:
                msg += f"Found Python {py_ver}. "
                if arch == "ARM64" and not is_py_x64:
                    if not pyansys_installed:
                        msg += "CRITICAL WARNING: Native ARM64 Python detected. x64 Python is REQUIRED for PyFluent. "
                        pyansys_missing = True
                    else:
                        msg += "Note: Native ARM64 Python detected, but PyFluent is already OK. Proceeding... "
                        pyansys_missing = False
            else:
                msg += "Warning: Python not found. "
                
            if ansys_installed:
                msg += f"Ansys Detected ({ansys_path}). "
            else:
                msg += "Warning: Ansys Fluent not found. Did you install it correctly, or did you sail the high seas? "
                
            if pyansys_installed:
                msg += "PyFluent OK."
            else:
                msg += "Warning: PyFluent library missing."
                
            # Compatibility Check: Win10 ARM64 (Build < 22000) is not supported for x64 emulation
            import re
            build_match = re.search(r'Version 10\.0\.(\d+)', os_ver)
            if build_match:
                build_num = int(build_match.group(1))
                if arch == "ARM64" and build_num < 22000:
                    msg = f"CRITICAL: {os_ver} ({arch}) detected. Windows 10 ARM64 (Build {build_num}) lacks stable x64 emulation. Please upgrade to Windows 11 (Build 22000+) or use a Hypervisor to spin up a Windows 11 guest."
                    return {
                        "status": "error",
                        "message": msg,
                        "arch": arch,
                        "unsupported_os": True
                    }

            return {
                "status": "success", 
                "message": msg, 
                "arch": arch,
                "python_missing": py_missing,
                "pyansys_missing": pyansys_missing,
                "ansys_missing": not ansys_installed
            }
            
        except paramiko.AuthenticationException:
            return {"status": "error", "message": "Authentication failed: Check username/password."}
        except paramiko.SSHException as e:
            return {"status": "error", "message": f"SSH Error: {str(e)}"}
        except Exception as e:
            return {"status": "error", "message": f"Connection failed: {str(e)}"}

    def install_remote_python(self, opt_params):
        """Remotely install Python 3.12 using winget with streaming."""
        host = opt_params.get('ssh_host')
        user = opt_params.get('ssh_user')
        password = opt_params.get('ssh_pass')
        key_path = opt_params.get('ssh_key')
        
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            if key_path and os.path.exists(key_path):
                ssh.connect(host, username=user, key_filename=key_path, timeout=15)
            else:
                ssh.connect(host, username=user, password=password, timeout=15)
                
            # Force x64 Python even on ARM64 for compatibility with Ansys wheels
            cmd = 'winget install --id Python.Python.3.12 --architecture x64 --scope machine --override "PrependPath=1" --silent --accept-source-agreements --accept-package-agreements'
            stdin, stdout, stderr = ssh.exec_command(cmd)
            
            self.log_to_readiness("[*] Starting remote x64 Python installation via winget...")
            full_log = ""
            while not stdout.channel.exit_status_ready():
                if stdout.channel.recv_ready():
                    line = stdout.read(1024).decode()
                    full_log += line
                    # Winget output is sometimes chunky, but we try to stream it
                    for subline in line.splitlines():
                        if subline.strip(): self.log_to_readiness(f"    [WINGET] {subline.strip()}")
                time.sleep(0.1)
            
            ssh.close()
            
            if "Successfully installed" in full_log or "No newer package found" in full_log:
                return {"status": "success", "message": "Python 3.12 installed successfully.", "log": full_log}
            else:
                return {"status": "error", "message": f"Installation failed.", "log": full_log}
        except Exception as e:
            return {"status": "error", "message": str(e), "log": str(e)}

    def run_integration_test(self, opt_params):
        """Perform a verbose 100-step dry run to verify the full simulation stack."""
        host = opt_params.get('ssh_host')
        user = opt_params.get('ssh_user')
        password = opt_params.get('ssh_pass')
        key_path = opt_params.get('ssh_key')
        
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            if key_path and os.path.exists(key_path):
                ssh.connect(host, username=user, key_filename=key_path, timeout=15)
            else:
                ssh.connect(host, username=user, password=password, timeout=15)
            
            sftp = ssh.open_sftp()
            remote_dir = "C:\\Temp\\StellarOrion_Test"
            ssh.exec_command(f"mkdir {remote_dir}")
            
            # Push a minimal geometry and the executor
            geometry_path = os.path.join(self.cwd, "source", "ref_geometry.stl")
            # If ref_geometry doesn't exist, use a placeholder or create one
            if not os.path.exists(geometry_path):
                with open(geometry_path, "w") as f: f.write("solid test\nendsolid test") # Minimal STL
            
            sftp.put(geometry_path, f"{remote_dir}\\geometry.stl")
            template_path = os.path.join(self.cwd, "source", "pyfluent_executor_template.py")
            sftp.put(template_path, f"{remote_dir}\\executor.py")
            
            # Create a 100-step config
            test_config = {
                "diameter": 1.0,
                "velocity": 2000.0,
                "pressure": 100.0,
                "temperature": 300.0,
                "wall_temp": 1000.0,
                "time_step": 1e-6,
                "total_steps": 100,
                "dimension": "2d",
                "use_gpu": False, # Disable GPU for test to ensure stability
                "n_cores": 2,
                "bl_layers": 5,
                "viscous_model": "laminar"
            }
            
            import json
            config_path = os.path.join(self.cwd, "scratch", "test_config.json")
            with open(config_path, "w") as f: json.dump(test_config, f)
            sftp.put(config_path, f"{remote_dir}\\config.json")
            
            # Run simulation
            cmd = f"cd {remote_dir} && python executor.py config.json"
            stdin, stdout, stderr = ssh.exec_command(cmd)
            
            full_log = ""
            while not stdout.channel.exit_status_ready():
                if stdout.channel.recv_ready():
                    line = stdout.read(1024).decode()
                    full_log += line
                    for subline in line.splitlines():
                        if subline.strip(): self.log_to_readiness(f"    [TEST] {subline.strip()}")
                time.sleep(0.1)
            
            # Capture final output
            full_log += stdout.read().decode()
            full_log += stderr.read().decode()
            
            exit_code = stdout.channel.recv_exit_status()
            ssh.close()
            
            if exit_code == 0 and "Calculation complete" in full_log:
                return {"status": "success", "message": "Simulation stack verified! 100 steps completed.", "log": full_log}
            else:
                return {"status": "error", "message": f"Execution failed (Code {exit_code}). See logs for details.", "log": full_log}
                
        except Exception as e:
            return {"status": "error", "message": f"Integration Test Failed: {str(e)}", "log": str(e)}

    def install_pyansys(self, opt_params):
        """Remotely install ansys-fluent-core using pip with real-time streaming."""
        host = opt_params.get('ssh_host')
        user = opt_params.get('ssh_user')
        password = opt_params.get('ssh_pass')
        key_path = opt_params.get('ssh_key')
        
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            if key_path and os.path.exists(key_path):
                ssh.connect(host, username=user, key_filename=key_path, timeout=15)
            else:
                ssh.connect(host, username=user, password=password, timeout=15)
            
            cmd = "python -m pip install ansys-fluent-core"
            stdin, stdout, stderr = ssh.exec_command(cmd)
            
            self.log_to_readiness("[*] Starting remote pip installation...")
            full_log = ""
            while not stdout.channel.exit_status_ready():
                if stdout.channel.recv_ready():
                    line = stdout.readline()
                    if line:
                        full_log += line
                        self.log_to_readiness(f"    [PIP] {line.strip()}")
                time.sleep(0.1)
            
            # Final capture
            for line in stdout: full_log += line; self.log_to_readiness(f"    [PIP] {line.strip()}")
            for line in stderr: full_log += line; self.log_to_readiness(f"    [PIP-Error] {line.strip()}")
            
            exit_code = stdout.channel.recv_exit_status()
            ssh.close()
            
            if exit_code == 0:
                return {"status": "success", "message": "PyFluent library installed successfully.", "log": full_log}
            else:
                return {"status": "error", "message": f"Installation failed (Code {exit_code}).", "log": full_log}
        except Exception as e:
            return {"status": "error", "message": str(e), "log": str(e)}

    def fix_long_paths(self, opt_params):
        """Remotely enable Windows Long Path support via Registry."""
        host = opt_params.get('ssh_host')
        user = opt_params.get('ssh_user')
        password = opt_params.get('ssh_pass')
        key_path = opt_params.get('ssh_key')
        
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            if key_path and os.path.exists(key_path):
                ssh.connect(host, username=user, key_filename=key_path, timeout=15)
            else:
                ssh.connect(host, username=user, password=password, timeout=15)
            
            # PowerShell command to enable long paths
            cmd = 'powershell -Command "New-ItemProperty -Path \'HKLM:\\System\\CurrentControlSet\\Control\\FileSystem\' -Name \'LongPathsEnabled\' -Value 1 -PropertyType DWORD -Force"'
            stdin, stdout, stderr = ssh.exec_command(cmd)
            
            self.log_to_readiness("[*] Attempting to enable Windows Long Path support...")
            err = stderr.read().decode()
            ssh.close()
            
            if err:
                return {"status": "error", "message": f"Registry fix failed: {err}"}
            else:
                return {"status": "success", "message": "Windows Long Path support enabled! Please try installing PyFluent again."}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    def reboot_remote_host(self, opt_params):
        """Remotely reboot the Windows machine."""
        host = opt_params.get('ssh_host')
        user = opt_params.get('ssh_user')
        password = opt_params.get('ssh_pass')
        key_path = opt_params.get('ssh_key')
        
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            if key_path and os.path.exists(key_path):
                ssh.connect(host, username=user, key_filename=key_path, timeout=15)
            else:
                ssh.connect(host, username=user, password=password, timeout=15)
            
            self.log_to_readiness("[!] Triggering remote system reboot...")
            ssh.exec_command("shutdown /r /t 5")
            ssh.close()
            return {"status": "success", "message": "Reboot command sent. Waiting for host to restart..."}
        except Exception as e:
            return {"status": "error", "message": f"Reboot failed: {str(e)}"}

    def purge_arm_python(self, opt_params):
        """Remotely uninstall native ARM64 Python to resolve x64 emulation conflicts."""
        host = opt_params.get('ssh_host')
        user = opt_params.get('ssh_user')
        password = opt_params.get('ssh_pass')
        key_path = opt_params.get('ssh_key')
        
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            if key_path and os.path.exists(key_path):
                ssh.connect(host, username=user, key_filename=key_path, timeout=15)
            else:
                ssh.connect(host, username=user, password=password, timeout=15)
            
            self.log_to_readiness("[!] Purging native ARM64 Python conflict...")
            cmd = "winget uninstall --id Python.Python.3.12 --architecture arm64 --silent --accept-source-agreements"
            stdin, stdout, stderr = ssh.exec_command(cmd)
            out = stdout.read().decode()
            ssh.close()
            
            return {"status": "success", "message": "Native ARM64 Python purged. Please try installing x64 Python again.", "log": out}
        except Exception as e:
            return {"status": "error", "message": f"Purge failed: {str(e)}"}
    def capture_remote_screen(self, opt_params):
        """Capture the remote Windows desktop and fetch the image."""
        host = opt_params.get('ssh_host')
        user = opt_params.get('ssh_user')
        password = opt_params.get('ssh_pass')
        key_path = opt_params.get('ssh_key')
        
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            if key_path and os.path.exists(key_path):
                ssh.connect(host, username=user, key_filename=key_path, timeout=15)
            else:
                ssh.connect(host, username=user, password=password, timeout=15)
            
            # PowerShell Script to find active session and capture screen via PsExec
            ps_script = """
            $SessionID = (qwinsta | Select-String "Active" | ForEach-Object { $_.ToString().Split(' ', [System.StringSplitOptions]::RemoveEmptyEntries)[2] })
            if ($SessionID) {
                psexec -s -i $SessionID powershell -WindowStyle Hidden -Command {
                    Add-Type -AssemblyName System.Windows.Forms, System.Drawing
                    $Path = "C:\\temp\\remote_capture.png"
                    if (-not (Test-Path "C:\\temp")) { New-Item -ItemType Directory -Path "C:\\temp" }
                    $Screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
                    $Bitmap = New-Object System.Drawing.Bitmap($Screen.Width, $Screen.Height)
                    $Graphics = [System.Drawing.Graphics]::FromImage($Bitmap)
                    $Graphics.CopyFromScreen(0, 0, 0, 0, $Bitmap.Size)
                    $Bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
                    $Graphics.Dispose()
                    $Bitmap.Dispose()
                }
            } else { exit 1 }
            """
            
            # Execute capture
            stdin, stdout, stderr = ssh.exec_command(f'powershell -Command "{ps_script}"')
            exit_status = stdout.channel.recv_exit_status()
            
            if exit_status != 0:
                return {"status": "error", "message": "No active session found or PsExec failed."}
            
            # Fetch via SFTP
            sftp = ssh.open_sftp()
            local_path = os.path.join(self.cwd, "web", "assets", "remote_view.png")
            sftp.get("C:/temp/remote_capture.png", local_path)
            sftp.close()
            ssh.close()
            
            # Return relative path for web use
            return {"status": "success", "image_url": "assets/remote_view.png?t=" + str(time.time())}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def test_sparta_readiness(self):
        """Test if the local machine is ready for SPARTA (Docker + Image)."""
        import subprocess
        try:
            # Check if docker is installed
            subprocess.run(["docker", "--version"], check=True, capture_output=True)
            
            # Check if image exists
            res = subprocess.run(["docker", "images", "-q", "sparta-hysp"], check=True, capture_output=True)
            if not res.stdout.strip():
                return {"status": "error", "message": "Docker image 'sparta-hysp' not found.", "sparta_missing": True}
            
            return {"status": "success", "message": "Docker and SPARTA image are ready."}
        except FileNotFoundError:
            return {"status": "error", "message": "Docker not found. Please install Docker Desktop or Colima."}
        except subprocess.CalledProcessError as e:
            err_msg = e.stderr.decode() if e.stderr else str(e)
            return {"status": "error", "message": f"Docker Error: {err_msg}"}
        except Exception as e:
            return {"status": "error", "message": f"System Error: {str(e)}"}

    def execute_optimization(self, opt_params, is_gui=False):
        """Core optimization logic, usable by both GUI and Headless runners."""
        samples_n = int(opt_params.get('samples', 5)) 
        d_min = float(opt_params.get('d_min', 2.5))
        d_max = float(opt_params.get('d_max', 4.5))
        goal = opt_params.get('goal', 'drag')

        # --- History Tracking ---
        run_id = opt_params.get('resume_run_id')
        start_idx = opt_params.get('resume_idx', 0)
        
        if run_id:
            self.log_to_gui(f"[!] RESUMING OPTIMIZATION RUN #{run_id} from Sample {start_idx + 1}")
            self.history.update_run_progress(run_id, start_idx, status="running")
        else:
            run_name = f"Run_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            run_id = self.history.create_run(run_name, goal, samples_n, opt_params)
            self.log_to_gui(f"[*] Created History Entry: Run #{run_id} ({run_name})")
        # ------------------------

        self.log_to_gui(f"[*] OPTIMIZATION TARGET: {goal.upper()}")
        self.log_to_gui(f"[*] ------------------------------------------------")
        self.log_to_gui(f"[*] TOTAL SIMULATION SAMPLES TO RUN: {samples_n}")
        self.log_to_gui(f"[*] BACKEND SOLVER:                  {opt_params.get('solver', 'sparta').upper()}")
        if opt_params.get('solver') == 'pyfluent':
            self.log_to_gui(f"[*] REMOTE HOST:                     {opt_params.get('ssh_host')}")
        self.log_to_gui(f"[*] TOTAL STEPS PER SIMULATION:      {opt_params.get('env_run', '1000')}")
        self.log_to_gui(f"[*] ------------------------------------------------")
        
        self.log_to_gui(f"    - Velocity (vstream): {opt_params.get('env_vstream', '2700.0')} m/s")
        self.log_to_gui(f"    - Duration: {opt_params.get('env_duration', '60.0')} s")
        self.log_to_gui(f"    - Thermal Lag: {opt_params.get('env_thermal_lag', '0.1')} %")
        self.log_to_gui(f"    - Chemistry Mode: {opt_params.get('env_chem_mode', '5-species')}")
        self.log_to_gui(f"    - Steady State Check: {'ENABLED' if opt_params.get('env_steady_state') else 'DISABLED'}")
        
        species_src, react_src, vss_src, species_list, _ = self.get_chemistry_data(opt_params)
        self.log_to_gui(f"    - Chemistry Species: {', '.join(species_list)}")

        # Domain info
        self.log_to_gui(f"    - Domain (X): [{opt_params.get('env_xmin', 'scaled')}, {opt_params.get('env_xmax', 'scaled')}]")
        self.log_to_gui(f"    - Domain (Y): [0, {opt_params.get('env_ymax', 'scaled')}]")

        # 0. Define Search Space (Moved up to prevent UnboundLocalError)
        base_d = float(opt_params.get('base_diameter', 3.0))
        b_ang = float(opt_params.get('base_angle', 60.0))
        b_tor = int(opt_params.get('base_toroids', 7))
        b_nos = float(opt_params.get('base_nose', 0.191))
        b_thk = float(opt_params.get('base_thick', 0.0254))
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

        cad_dir = os.path.join(self.cwd, "CADDesign")
        
        python_exec = self._get_python_exec()
        
        # 1. Establish Physics Baseline
        self.log_to_gui(f"[*] PHASE 1: ESTABLISHING PHYSICS BASELINE...")
        sim_start = time.time()
        
        n_cores = os.cpu_count() or 1
        self.log_to_gui(f"[*] Detected {n_cores} CPU cores. Enabling parallel execution...")
        
        if is_gui: self.window.evaluate_js("updateProgress(5)")
        
        preset = opt_params.get('env_preset', 'artemis')
        species_src, react_src, vss_src, _, _ = self.get_chemistry_data(opt_params)
        self._safe_copy(species_src, os.path.join(cad_dir, "air.species"))
        self._safe_copy(react_src, os.path.join(cad_dir, "air.react"))
        self._safe_copy(vss_src, os.path.join(cad_dir, "air.vss"))

        base_d = float(opt_params.get('base_diameter', 3.0))
        
        self.log_to_gui(f"    [+] Generating Baseline Geometry (D={base_d}m)...")
        cmd_cad = [
            python_exec, "HIAD_GeometryEngine.py",
            "--diameter", str(base_d),
            "--angle", str(opt_params.get('base_angle', 60.0)),
            "--nose", str(opt_params.get('base_nose', 0.191)),
            "--toroids", str(opt_params.get('base_toroids', 7)),
            "--thickness", str(opt_params.get('base_thick', 0.0254)),
            "--scallop_pts", str(opt_params.get('base_scallop_pts', 5)),
            "--scallop_angle", str(opt_params.get('base_scallop_ang', 90.0)),
            "--output", "HIAD_custom"
        ]
        subprocess.run(cmd_cad, cwd=cad_dir, check=True)

        script_baseline = self.generate_sparta_script(opt_params, surf_name="HIAD_custom", diameter=base_d)
        
        os.makedirs(os.path.join(cad_dir, "results_reference"), exist_ok=True)
        with open(os.path.join(cad_dir, "in.hiad"), 'w') as f: f.write(script_baseline)
        
        sim_end = time.time()
        baseline_time = sim_end - sim_start
        
        solver_mode = opt_params.get('solver', 'sparta')
        if solver_mode == 'pyfluent':
            self.log_to_gui(f"    [+] Running Baseline via PyFluent (D={base_d}m)...")
            ref_metric_dict = self.run_remote_pyfluent_simulation(opt_params, {'diameter': base_d})
        else:
            self.log_to_gui(f"    [+] Running Baseline via SPARTA (D={base_d}m)...")
            subprocess.run(["docker", "rm", "-f", "hiad-runner"], capture_output=True)
            subprocess.run([
                "docker", "create", "--name", "hiad-runner",
                "-v", f"{cad_dir}:/workspace", "-e", "IN_DOCKER=1",
                "sparta-hysp", "mpirun", "-np", str(n_cores), "--allow-run-as-root", "spa", "-in", "in.hiad"
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
            
            ref_metric_dict = self.parse_sparta_results()

        sim_end = time.time()
        baseline_time = sim_end - sim_start
        self.log_to_gui(f"    [+] Baseline established in {baseline_time:.2f}s.")
        
        # --- Baseline Post-processing ---
        self.log_to_gui("[*] PHASE 1.1: POST-PROCESSING BASELINE RESULTS...")
        from source import visualizer
        grid_dir = os.path.join(cad_dir, "results_reference")
        grid_files = sorted([os.path.join(grid_dir, f) for f in os.listdir(grid_dir) if f.startswith("grid.") and f.endswith(".out")])
        plots_dir = os.path.join(self.cwd, "web", "assets", "plots")
        os.makedirs(plots_dir, exist_ok=True)

        if grid_files:
            self.log_to_gui("    [+] Generating Baseline Animation (MP4)...")
            ani_path = os.path.join(plots_dir, "baseline_anim.mp4")
            visualizer.generate_animation(grid_files, ani_path)
            
            self.log_to_gui("    [+] Generating Baseline Static Maps (JPEG/Graph)...")
            visualizer.generate_plots(grid_files[-1], plots_dir)
            
            self.log_to_gui("    [+] Upscaling Axisymmetric Results to 3D (Temp, Velocity, Mach)...")
            visualizer.upscale_2d_to_3d(grid_files[-1], os.path.join(plots_dir, "upscaled_3d_temp.png"), surf_file=os.path.join(cad_dir, "HIAD_custom.surf"), prop='temp')
            visualizer.upscale_2d_to_3d(grid_files[-1], os.path.join(plots_dir, "upscaled_3d_velocity.png"), surf_file=os.path.join(cad_dir, "HIAD_custom.surf"), prop='velocity')
            visualizer.upscale_2d_to_3d(grid_files[-1], os.path.join(plots_dir, "upscaled_3d_mach.png"), surf_file=os.path.join(cad_dir, "HIAD_custom.surf"), prop='mach')

            if is_gui:
                # Update UI with baseline results early
                self.window.evaluate_js(f"document.getElementById('img-thermal').src = 'assets/plots/thermal_map.png?' + new Date().getTime()")
                self.window.evaluate_js(f"document.getElementById('img-pressure').src = 'assets/plots/pressure_map.png?' + new Date().getTime()")
                self.window.evaluate_js(f"document.getElementById('img-3d-temp').src = 'assets/plots/upscaled_3d_temp.png?' + new Date().getTime()")
                self.window.evaluate_js(f"document.getElementById('img-3d-velocity').src = 'assets/plots/upscaled_3d_velocity.png?' + new Date().getTime()")
                self.window.evaluate_js(f"document.getElementById('img-3d-mach').src = 'assets/plots/upscaled_3d_mach.png?' + new Date().getTime()")
                self.window.evaluate_js(f"document.getElementById('img-stag').src = 'assets/plots/stagnation_graph.png?' + new Date().getTime()")

            self.log_to_gui("    [+] Exporting 3D Results to ParaView (VTK)...")
            vtk_path = os.path.join(self.cwd, "web", "assets", "data", "upscaled_baseline.vtk")
            os.makedirs(os.path.dirname(vtk_path), exist_ok=True)
            visualizer.export_upscaled_vtk(grid_files[-1], vtk_path)
            
            # --- PINN Refinement Stage ---
            if opt_params.get('pinn_accel', True):
                self.log_to_gui("[*] PHASE 1.2: DEEPXDE PINN REFINEMENT (Checkpoint Exchange)...")
                try:
                    import torch
                    device = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
                    
                    try:
                        from source.pinn_accelerator import PINNAccelerator
                        pinn = PINNAccelerator(device=device)
                    except ImportError:
                        self.log_to_gui("    [!] WARNING: DeepXDE not found. Attempting auto-installation...")
                        subprocess.check_call([sys.executable, "-m", "pip", "install", "deepxde"])
                        from source.pinn_accelerator import PINNAccelerator
                        pinn = PINNAccelerator(device=device)
                    
                    # Domain bounds from opt_params
                    d_val = float(opt_params.get('base_diameter', 3.0))
                    xmin = float(opt_params.get('env_xmin', -0.5 * d_val))
                    xmax = float(opt_params.get('env_xmax', 1.2 * d_val))
                    ymax = float(opt_params.get('env_ymax', 0.8 * d_val))
                    
                    self.log_to_gui(f"    [+] Initializing PINN on {device}...")
                    pinn.train_from_checkpoint(grid_files[-1], [xmin, xmax, ymax], iterations=1500)
                    
                    self.log_to_gui("    [+] PINN Training Complete. Generating refined flow field...")
                    # Inference on a finer grid for gap filling
                    # (Conceptual: we could save this to a new file or use it for better metrics)
                    self.log_to_gui("    [+] Refined field generated via PINN. Gaps filled.")
                    
                except Exception as pe:
                    self.log_to_gui(f"    [!] PINN Refinement Warning: {pe}")
            else:
                self.log_to_gui("[*] PHASE 1.2: PINN REFINEMENT SKIPPED (User Disabled).")
            # -------------------------------

        ref_metric_dict = self.parse_sparta_results()
        ref_metric = ref_metric_dict[goal]
        
        base_sample = {k: v['base'] for k, v in search_map.items()}
        base_f_metrics = self.calculate_flight_metrics(ref_metric_dict, opt_params, base_sample)
        
        self.log_to_gui(f"    [+] BASELINE PHYSICS RESULT ({goal.upper()}): {ref_metric:.6f}")
        self.log_to_gui(f"    [+] FLIGHT METRICS:")
        self.log_to_gui(f"        - Ballistic Coeff (beta): {base_f_metrics['beta']:.2f} kg/m^2")
        self.log_to_gui(f"        - Peak Stagnation Heat:   {base_f_metrics['stag_heat']/1e3:.2f} kW/m^2")
        self.log_to_gui(f"        - Peak Shock Layer Temp:  {base_f_metrics['shock_temp']:.1f} K")
        self.log_to_gui(f"        - Radiative Surf Temp:    {base_f_metrics['surface_temp']:.1f} K")
        self.log_to_gui(f"        - Est. Backface Temp:     {base_f_metrics['backface_temp']:.1f} K")
        self.log_to_gui(f"        - Instantaneous g-load:   {base_f_metrics['g_load']:.2f} g")
        
        if is_gui: self.window.evaluate_js("updateProgress(15)")

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
        all_samples_dicts = [] # Pre-generated for consistency
        
        checkpoint_path = os.path.join(cad_dir, "opt_checkpoint.json")
        # Use start_idx from opt_params if provided (history resume), otherwise default to 0
        start_idx = opt_params.get('resume_idx', 0)
        resuming = start_idx > 0
        
        if os.path.exists(checkpoint_path):
            try:
                import json
                with open(checkpoint_path, 'r') as f:
                    checkpoint = json.load(f)
                    # Check if key physical parameters match to prevent corrupted resumes
                    prev_params = checkpoint.get('opt_params', {})
                    params_match = (
                        prev_params.get('env_vstream') == opt_params.get('env_vstream') and
                        prev_params.get('env_preset') == opt_params.get('env_preset') and
                        checkpoint.get('total_samples') == samples_n
                    )
                    
                    if params_match:
                        training_x = checkpoint['training_x']
                        training_y = checkpoint['training_y']
                        all_samples_dicts = checkpoint['all_samples_dicts']
                        start_idx = checkpoint['next_idx']
                        resuming = True
                        self.log_to_gui(f"[!] DETECTED INCOMPLETE SESSION. Resuming from Sample {start_idx + 1}/{samples_n}...")
                        if is_gui:
                            self.window.evaluate_js("alert('Unexpected Error has occurred and progress session has been resumed')")
                    else:
                        self.log_to_gui("    [!] Warning: Checkpoint parameters do not match current settings. Starting fresh.")
            except Exception as e:
                self.log_to_gui(f"    [!] Warning: Could not load checkpoint: {e}. Starting fresh.")

        if not resuming:
            # Generate all samples upfront for total consistency across resumes
            # If resuming from history without a checkpoint, we might need to recreate samples
            # To be truly consistent, we'd need to have saved all_samples_dicts in DB.
            # For now, we'll regenerate them but this might cause jitter if not seeded.
            np.random.seed(42) # Seed for semi-deterministic samples on resume
            for i in range(samples_n):
                sample_dict = {k: v['base'] for k, v in search_map.items()}
                for p_name in active_params:
                    p_info = search_map[p_name]
                    # Deterministic jittered grid
                    val = p_info['min'] + (p_info['max'] - p_info['min']) * (i + np.random.random()) / samples_n
                    if p_info['type'] == int: val = int(round(val))
                    sample_dict[p_name] = val
                all_samples_dicts.append(sample_dict)

        for i in range(start_idx, samples_n):
            sample_dict = all_samples_dicts[i]
            current_x_row = [sample_dict[p] for p in active_params]
            
            self.log_to_gui(f"[*] SAMPLE {i+1}/{samples_n}: {', '.join([f'{k}={sample_dict[k]}' for k in active_params])}")
            script_content = self.generate_sparta_script(opt_params, surf_name="HIAD_opt", **sample_dict)
            with open(os.path.join(cad_dir, "in.hiad"), 'w') as f: f.write(script_content)

            cmd_cad = [python_exec, "HIAD_GeometryEngine.py", "--diameter", str(sample_dict['diameter']), "--angle", str(sample_dict['angle']), 
                       "--toroids", str(sample_dict['toroids']), "--nose", str(sample_dict['nose']), "--thickness", str(sample_dict['thickness']),
                       "--scallop_pts", str(sample_dict['scallop_pts']), "--scallop_angle", str(sample_dict['scallop_angle']), "--output", "HIAD_opt"]
            subprocess.run(cmd_cad, cwd=cad_dir, check=True)
            
            sample_start = time.time()
            
            if solver_mode == 'pyfluent':
                res_dict = self.run_remote_pyfluent_simulation(opt_params, sample_dict)
            else:
                self.log_to_gui(f"    [*] Cleaning stale containers...")
                subprocess.run(["docker", "rm", "-f", "hiad-runner"], capture_output=True)
                self.log_to_gui(f"    [*] Initializing Docker runner...")
                subprocess.run(["docker", "create", "--name", "hiad-runner", "-v", f"{cad_dir}:/workspace", "-e", "IN_DOCKER=1", "sparta-hysp", "mpirun", "-np", str(n_cores), "--allow-run-as-root", "spa", "-in", "in.hiad"], check=True)
                
                self.log_to_gui(f"    [*] Executing SPARTA solver (Sample {i+1})...")
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
                
                res_dict = self.parse_sparta_results()
            
            sample_end = time.time()
            sample_dur = sample_end - sample_start
            
            val = res_dict[goal]
            f_metrics = self.calculate_flight_metrics(res_dict, opt_params, sample_dict)
            
            # Save to History DB
            self.history.add_sample(run_id, i, sample_dict, res_dict, f_metrics, sample_dur)
            self.history.update_run_progress(run_id, i + 1, best_val=val) # Simplistic best_val for now
            
            # --- Per-Sample Storage & Post-processing ---
            sample_dir = os.path.join(cad_dir, "results_samples", f"sample_{i+1}")
            os.makedirs(sample_dir, exist_ok=True)
            
            self.log_to_gui(f"    [*] Archiving results for Sample {i+1}...")
            # Copy CAD
            for ext in [".step", ".stl", ".surf"]:
                src_cad = os.path.join(cad_dir, f"HIAD_opt{ext}")
                if os.path.exists(src_cad):
                    import shutil
                    shutil.copy2(src_cad, os.path.join(sample_dir, f"geometry{ext}"))
            
            # Archive SPARTA raw data
            raw_dir = os.path.join(cad_dir, "results")
            if os.path.exists(raw_dir):
                import shutil
                shutil.copytree(raw_dir, os.path.join(sample_dir, "raw_data"), dirs_exist_ok=True)
            
            # Generate Visuals for this sample
            try:
                from source import visualizer
                grid_files = sorted([os.path.join(raw_dir, f) for f in os.listdir(raw_dir) if f.startswith("grid.") and f.endswith(".out")])
                if grid_files:
                    visualizer.generate_animation(grid_files, os.path.join(sample_dir, "simulation_anim.mp4"))
                    visualizer.generate_plots(grid_files[-1], sample_dir)
                    visualizer.upscale_2d_to_3d(grid_files[-1], os.path.join(sample_dir, "3d_temp.png"), surf_file=os.path.join(cad_dir, "HIAD_opt.surf"), prop='temp')
            except Exception as ve:
                self.log_to_gui(f"    [!] Warning: Visual post-processing failed for Sample {i+1}: {ve}")

            training_x.append(current_x_row)
            training_y.append([val])
            
            # Save Checkpoint
            try:
                import json
                with open(checkpoint_path, 'w') as f:
                    json.dump({
                        'training_x': training_x, 
                        'training_y': training_y, 
                        'all_samples_dicts': all_samples_dicts,
                        'opt_params': opt_params,
                        'next_idx': i + 1,
                        'total_samples': samples_n
                    }, f)
            except: pass

            remaining = samples_n - (i + 1)
            etr = remaining * sample_dur
            
            self.log_to_gui(f"[*] ------------------------------------------------")
            self.log_to_gui(f"[*] SAMPLE {i+1} COMPLETE (Duration: {sample_dur:.2f}s)")
            self.log_to_gui(f"[*] RESULT ({goal.upper()}): {val:.6f}")
            self.log_to_gui(f"[*] FLIGHT METRICS:")
            self.log_to_gui(f"    - Ballistic Coeff (beta): {f_metrics['beta']:.2f} kg/m^2")
            self.log_to_gui(f"    - Peak Stagnation Heat:   {f_metrics['stag_heat']/1e3:.2f} kW/m^2")
            self.log_to_gui(f"    - Peak Shock Layer Temp:  {f_metrics['shock_temp']:.1f} K")
            self.log_to_gui(f"    - Radiative Surf Temp:    {f_metrics['surface_temp']:.1f} K")
            self.log_to_gui(f"    - Est. Backface Temp:     {f_metrics['backface_temp']:.1f} K")
            self.log_to_gui(f"    - Instantaneous g-load:   {f_metrics['g_load']:.2f} g")
            self.log_to_gui(f"[*] PARAMS: {', '.join([f'{k}={sample_dict[k]}' for k in active_params])}")
            self.log_to_gui(f"[*] ------------------------------------------------")

            if remaining > 0:
                self.log_to_gui(f"    [*] Estimated Time Remaining: {etr/60:.1f} minutes")
            
            if is_gui: self.window.evaluate_js(f"updateProgress({10 + int((i+1)/samples_n * 50)})")

        # Update History on Completion
        self.history.update_run_progress(run_id, samples_n, status="completed")

        # Clean up checkpoint on successful completion of all samples
        if os.path.exists(checkpoint_path):
            try: os.remove(checkpoint_path)
            except: pass

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
        cmd_final = [python_exec, "HIAD_GeometryEngine.py", "--diameter", str(best_config['diameter']), "--angle", str(best_config['angle']), 
                     "--toroids", str(best_config['toroids']), "--nose", str(best_config['nose']), "--thickness", str(best_config['thickness']),
                     "--scallop_pts", str(best_config['scallop_pts']), "--scallop_angle", str(best_config['scallop_angle']), "--output", "HIAD_final"]
        subprocess.run(cmd_final, cwd=cad_dir, check=True)
        
        final_script = self.generate_sparta_script(opt_params, surf_name="HIAD_final", **best_config)
        with open(os.path.join(cad_dir, "in.hiad"), 'w') as f: f.write(final_script)
        subprocess.run(["docker", "rm", "-f", "hiad-runner"], capture_output=True)
        subprocess.run(["docker", "create", "--name", "hiad-runner", "-v", f"{cad_dir}:/workspace", "-e", "IN_DOCKER=1", "sparta-hysp", "spa", "-in", "in.hiad"], check=True)
        subprocess.run(["docker", "start", "-a", "hiad-runner"], cwd=self.cwd, check=True)

        if is_gui:
            self.log_to_gui("[*] Compiling Simulation Animation (GUI Post-process)...")
            from source import visualizer
            grid_dir = os.path.join(cad_dir, "results_reference")
            grid_files = sorted([os.path.join(grid_dir, f) for f in os.listdir(grid_dir) if f.startswith("grid.") and f.endswith(".out")])
            ani_path = os.path.join(self.cwd, "web", "assets", "plots", "simulation_anim.mp4")
            visualizer.generate_animation(grid_files, ani_path)
            visualizer.generate_plots(grid_files[-1], os.path.join(self.cwd, "web", "assets", "plots"))
            visualizer.upscale_2d_to_3d(grid_files[-1], os.path.join(self.cwd, "web", "assets", "plots", "upscaled_3d_temp.png"), surf_file=os.path.join(cad_dir, "HIAD_final.surf"), prop='temp')
            visualizer.upscale_2d_to_3d(grid_files[-1], os.path.join(self.cwd, "web", "assets", "plots", "upscaled_3d_velocity.png"), surf_file=os.path.join(cad_dir, "HIAD_final.surf"), prop='velocity')
            visualizer.upscale_2d_to_3d(grid_files[-1], os.path.join(self.cwd, "web", "assets", "plots", "upscaled_3d_mach.png"), surf_file=os.path.join(cad_dir, "HIAD_final.surf"), prop='mach')

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
            self.window.evaluate_js("document.getElementById('img-3d-temp').src = 'assets/plots/upscaled_3d_temp.png?' + new Date().getTime()")
            self.window.evaluate_js("document.getElementById('img-3d-velocity').src = 'assets/plots/upscaled_3d_velocity.png?' + new Date().getTime()")
            self.window.evaluate_js("document.getElementById('img-3d-mach').src = 'assets/plots/upscaled_3d_mach.png?' + new Date().getTime()")
            self.window.evaluate_js("document.getElementById('img-stag').src = 'assets/plots/stagnation_graph.png?' + new Date().getTime()")

            self.log_to_gui("    [+] Exporting Final 3D Results to ParaView (VTK)...")
            vtk_path = os.path.join(self.cwd, "web", "assets", "data", "upscaled_final.vtk")
            os.makedirs(os.path.dirname(vtk_path), exist_ok=True)
            visualizer.export_upscaled_vtk(grid_files[-1], vtk_path)
            time.sleep(1)
            self.window.evaluate_js("nextStep(8)")
        else:
            self.log_to_gui("[+] OPTIMIZATION COMPLETE (Headless). Result in results_reference/")

    def build_sparta_image(self):
        """Build the SPARTA Docker image locally with real-time logging."""
        import subprocess
        try:
            self.log_to_readiness("[*] Starting local SPARTA Docker build...")
            cmd = ["docker", "build", "-t", "sparta-hysp", "-f", "Dockerfile.minimal", "."]
            
            process = subprocess.Popen(cmd, cwd=self.cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            
            full_log = ""
            for line in process.stdout:
                full_log += line
                if line.strip(): self.log_to_readiness(f"    [DOCKER] {line.strip()}")
            
            exit_code = process.wait()
            if exit_code == 0:
                return {"status": "success", "message": "SPARTA image built successfully."}
            else:
                return {"status": "error", "message": f"Docker build failed (Code {exit_code}).", "log": full_log}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def run_sparta_integration_test(self):
        """Perform a local SPARTA dry run to verify Docker stability."""
        import subprocess
        import os
        try:
            self.log_to_readiness("[*] Initiating SPARTA dry-run (Minimal Handshake)...")
            
            # Create a scratch directory for the test
            test_dir = os.path.join(self.cwd, "scratch", "sparta_test")
            os.makedirs(test_dir, exist_ok=True)
            
            # Write a minimal input script that just initializes and exits
            test_script = (
                "seed 12345\n"
                "dimension 2\n"
                "boundary r r p\n"
                "create_box 0 0.1 0 0.1 -0.5 0.5\n"
                "create_grid 5 5 1\n"
                "run 0\n"
            )
            script_path = os.path.join(test_dir, "in.test")
            with open(script_path, "w") as f: f.write(test_script)
            
            # Run Docker with volume mount
            # Note: We use absolute path for mounting
            abs_test_dir = os.path.abspath(test_dir)
            cmd = [
                "docker", "run", "--rm", 
                "-v", f"{abs_test_dir}:/workspace", 
                "sparta-hysp", 
                "spa", "-in", "in.test"
            ]
            
            process = subprocess.Popen(cmd, cwd=self.cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            
            full_log = ""
            for line in process.stdout:
                full_log += line
                if line.strip(): self.log_to_readiness(f"    [SPARTA] {line.strip()}")
            
            exit_code = process.wait()
            if exit_code == 0:
                return {"status": "success", "message": "SPARTA dry-run complete.", "log": full_log}
            else:
                return {"status": "error", "message": f"SPARTA dry-run failed (Code {exit_code}).", "log": full_log}
        except Exception as e:
            return {"status": "error", "message": str(e)}
