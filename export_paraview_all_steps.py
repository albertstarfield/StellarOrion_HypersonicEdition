#!/usr/bin/env python3
"""
Export ALL SPARTA grid dumps to ParaView VTU + generate unified state script.
Reads from CADDesign/results_reference/grid.*.out and writes to CADDesign/results_reference/paraview/.
"""
import os, sys, glob

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "source"))

from visualizer import parse_grid_dump, _write_single_vtu, export_sparta_vtk, export_sparta_vtk_3d, launch_paraview_for_sparta

RESULTS_DIR = os.path.join(PROJECT_ROOT, "CADDesign", "results_reference")
VTK_DIR = os.path.join(RESULTS_DIR, "paraview")
STL_FILE = os.path.join(PROJECT_ROOT, "CADDesign", "HIAD_custom.stl")

# Reference params for field labels
REF_PARAMS = {
    "vstream": 2700.0,
    "temp_inf": 270.0,
    "nrho": 3.47e22,
    "fnum": 1.5e20,
    "diameter": 3.0,
}

def main():
    os.makedirs(VTK_DIR, exist_ok=True)
    
    # Find all grid dump files, sorted by timestep
    grid_files = sorted(glob.glob(os.path.join(RESULTS_DIR, "grid.*.out")),
                        key=lambda f: int(os.path.basename(f).split('.')[1]))
    
    # Exclude sync-conflict files
    grid_files = [f for f in grid_files if 'sync-conflict' not in f]
    
    print(f"[*] Found {len(grid_files)} grid dump files:")
    for f in grid_files:
        print(f"    {os.path.basename(f)} ({os.path.getsize(f)} bytes)")
    
    if not grid_files:
        print("[!] No grid dump files found!")
        return False
    
    # Export 2D VTU time series
    print(f"\n[*] Exporting VTU time series to {VTK_DIR}...")
    vtu_result = export_sparta_vtk(grid_files, VTK_DIR, ref_params=REF_PARAMS)
    
    if vtu_result:
        print(f"[+] Exported {len(vtu_result)} VTU files")
        for f in vtu_result:
            print(f"    {os.path.basename(f)} ({os.path.getsize(f)} bytes)")
    else:
        print("[!] VTU export failed!")
        return False
    
    # Export 3D upscaled VTP from the LAST timestep
    vtp_3d_dir = os.path.join(VTK_DIR, "3d_upscaled")
    print(f"\n[*] Exporting 3D upscaled VTP from last timestep...")
    vtp_result = export_sparta_vtk_3d(grid_files[-1], vtp_3d_dir, ref_params=REF_PARAMS)
    
    if vtp_result:
        print(f"[+] Exported 3D VTP: {vtp_result}")
    else:
        print("[!] 3D VTP export failed (non-fatal)")
    
    # Generate ParaView state script
    print(f"\n[*] Generating ParaView state script...")
    stl_path = STL_FILE if os.path.isfile(STL_FILE) else None
    script_path = launch_paraview_for_sparta(
        vtu_result, output_dir=VTK_DIR,
        vtk_3d_file=vtp_result,
        geometry_stl=stl_path
    )
    
    if script_path:
        print(f"[+] ParaView state script: {script_path}")
    else:
        print("[!] ParaView script generation failed (non-fatal)")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"PARAVIEW EXPORT COMPLETE")
    print(f"{'='*60}")
    print(f"Steps: 0, 100, 200, ... 1100 ({len(vtu_result)} timesteps)")
    print(f"VTU files: {VTK_DIR}/")
    print(f"3D VTP:    {vtp_3d_dir}/ (last timestep only)")
    if script_path:
        print(f"Open with: paraview --script={script_path}")
    print(f"{'='*60}")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
