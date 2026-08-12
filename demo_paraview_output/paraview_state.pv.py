# Auto-generated ParaView state script -- StellarOrion
# Open with: paraview --script=paraview_state.pv.py
# Or load manually: File > Open > vtu_output_t0000.vtu

from paraview.simple import *

# --- Load VTU (3 timesteps) ---
reader = XMLUnstructuredGridReader(FileName=['/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/demo_paraview_output/vtu_output_t0000.vtu', '/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/demo_paraview_output/vtu_output_t0001.vtu', '/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/demo_paraview_output/vtu_output_t0002.vtu'])
# ── Time series: 3 timesteps ──────────────────────────────
# ParaView 6.x: TimestepValues is a VectorProperty on XMLUnstructuredGridReader
ts = list(reader.TimestepValues)
print(f"[ParaView] Time series loaded: {len(ts)} timesteps")
if ts:
    reader.UpdatePipeline(ts[-1])  # jump to last timestep for initial view
else:
    reader.UpdatePipeline()
print("[ParaView] Use VCR controls (Play/Pause) to animate timesteps.")

# --- Default colouring: Temperature ---
view = CreateRenderView()
view.ViewSize = [1920, 1080]
view.Background = [0.06, 0.07, 0.11]  # StellarOrion dark theme

display = Show(reader, view)
ColorBy(display, ('CELLS', 'Temperature'))
display.RescaleTransferFunctionToDataRange(True)

# Temperature colour map (hot)
tf = GetColorTransferFunction('Temperature')
tf.ApplyPreset('Black-Body Radiation', True)

# --- Load 3D upscaled geometry (3 VTP) ---
reader_3d = XMLPolyDataReader(FileName=['/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/demo_paraview_output/vtp_output/vtp_output_t0000.vtp', '/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/demo_paraview_output/vtp_output/vtp_output_t0001.vtp', '/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/demo_paraview_output/vtp_output/vtp_output_t0002.vtp'])
reader_3d.UpdatePipeline()
display_3d = Show(reader_3d, view)
ColorBy(display_3d, ('POINTS', 'Temperature'))
display_3d.RescaleTransferFunctionToDataRange(True)
display_3d.Opacity = 0.6

# 3D temperature colour map (distinct from 2D)
tf_3d = GetColorTransferFunction('Temperature')
tf_3d.ApplyPreset('Jet', True)
print(f"[ParaView] 3D upscaled geometry loaded: 3 file(s)")

# --- Load HIAD STL geometry ---
reader_stl = STLReader(FileNames='/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/HIAD_custom.stl')
reader_stl.UpdatePipeline()
display_stl = Show(reader_stl, view)
display_stl.DiffuseColor = [0.85, 0.85, 0.85]  # light grey
display_stl.Opacity = 0.85
print(f"[ParaView] HIAD STL geometry loaded: /Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/HIAD_custom.stl")

# --- Reset camera ---
view.ResetCamera()
Render()

print("[ParaView] Loaded: 3 2D timestep(s) from /Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/demo_paraview_output")
print('[ParaView] 3D upscaled geometry also loaded (rotate to see full revolution).')
print("[ParaView] Use the VCR controls to animate through timesteps.")
print("[ParaView] Switch arrays in the Properties panel.")

# Uncomment to save a screenshot:
# SaveScreenshot('/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/demo_paraview_output/paraview_screenshot.png', view)
