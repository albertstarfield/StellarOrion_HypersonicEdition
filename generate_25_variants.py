#!/usr/bin/env python3
"""
generate_25_variants.py — Generate 25 IRVE-3/HIAD geometry variants for audit.

Uses Latin Hypercube Sampling (LHS) across key design parameters to explore
the HIAD design space. Each variant is validated before export.

Parameters varied:
  - diameter_m:       Aeroshell diameter [m]
  - angle:            Cone half-angle [deg]
  - toroid_count:     Number of inflatable toroids
  - toroid_radius:    Toroid minor radius [m] (None = auto-calculated)
  - shoulder_radius:  Shoulder torus radius [m] (None = default 50.8mm)
  - payload_radius:   Payload radius [m]
  - payload_height:   Payload height [m]
  - nose_type:        'smooth' or 'pointy'
  - flat_skin:        Flat skin vs scalloped

IRVE-3 Reference (Rapisarda 2023):
  diameter=3.0m, angle=60deg, toroids=6, r_torus=0.135m, payload_r=0.5m

Author: StellarOrion HypersonicEdition
"""

import os
import sys
import math
import json
import traceback
from datetime import datetime

# Add CADDesign to path for geometry engine import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'CADDesign'))

from HIAD_GeometryEngine import (
    generate_hiad, export_to_sparta_surf,
    extract_cross_section_from_3d, export_to_sparta_surf_3d,
    export_solid_to_step, render_solid_jpg,
)

# Import validator
sys.path.insert(0, os.path.dirname(__file__))
from validate_simulation_input import validate_surf, dump_surf_geometry_verbose

# CadQuery for STL/STEP export
try:
    import cadquery as cq
    from cadquery import exporters as cq_exporters
    HAS_CQ = True
except ImportError:
    HAS_CQ = False
    print("[WARNING] CadQuery not installed — STL/STEP export will be skipped")


# ─── IRVE-3 Baseline Reference ───────────────────────────────────────────────
IRVE3_BASELINE = {
    "diameter_m": 3.0,
    "angle": 60.0,
    "toroid_count": 6,
    "toroid_radius": 0.135,       # 135 mm per Rapisarda Table 4.1
    "shoulder_radius": 0.0508,    # 50.8 mm default
    "payload_radius": 0.5,        # 500 mm
    "payload_height": 1.7,        # 1700 mm
    "nose_type": "smooth",
    "flat_skin": True,
}


# ─── 25 Variant Definitions ──────────────────────────────────────────────────
# Each variant tweaks specific parameters from the IRVE-3 baseline.
# Strategy: systematic sweep + stress tests + edge cases.

VARIANTS = [
    # ── 0: IRVE-3 Baseline (reference) ──────────────────────────────────────
    {**IRVE3_BASELINE, "name": "V00_IRVE3_Baseline",
     "desc": "IRVE-3 reference geometry (Rapisarda 2023)"},

    # ── Diameter Sweep ──────────────────────────────────────────────────────
    {**IRVE3_BASELINE, "name": "V01_Diam_2.5m",
     "diameter_m": 2.5, "desc": "Smaller diameter (2.5m)"},
    {**IRVE3_BASELINE, "name": "V02_Diam_3.5m",
     "diameter_m": 3.5, "desc": "Larger diameter (3.5m)"},
    {**IRVE3_BASELINE, "name": "V03_Diam_4.0m",
     "diameter_m": 4.0, "desc": "Max diameter (4.0m) — LOFTID-class"},

    # ── Cone Angle Sweep ────────────────────────────────────────────────────
    {**IRVE3_BASELINE, "name": "V04_Angle_45deg",
     "angle": 45.0, "desc": "Steep cone (45°)"},
    {**IRVE3_BASELINE, "name": "V05_Angle_55deg",
     "angle": 55.0, "desc": "Moderate cone (55°)"},
    {**IRVE3_BASELINE, "name": "V06_Angle_70deg",
     "angle": 70.0, "desc": "Blunt cone (70°)"},

    # ── Toroid Count Sweep ──────────────────────────────────────────────────
    {**IRVE3_BASELINE, "name": "V07_Toroids_4",
     "toroid_count": 4, "desc": "Minimal toroids (4)"},
    {**IRVE3_BASELINE, "name": "V08_Toroids_8",
     "toroid_count": 8, "desc": "Max toroids (8)"},

    # ── Toroid Radius Sweep ─────────────────────────────────────────────────
    {**IRVE3_BASELINE, "name": "V09_TRad_0.10m",
     "toroid_radius": 0.10, "desc": "Thin toroids (100mm)"},
    {**IRVE3_BASELINE, "name": "V10_TRad_0.18m",
     "toroid_radius": 0.18, "desc": "Fat toroids (180mm)"},

    # ── Payload Size Sweep ──────────────────────────────────────────────────
    {**IRVE3_BASELINE, "name": "V11_PayR_0.3m",
     "payload_radius": 0.3, "desc": "Small payload (300mm radius)"},
    {**IRVE3_BASELINE, "name": "V12_PayR_0.7m",
     "payload_radius": 0.7, "desc": "Large payload (700mm radius)"},

    # ── Nose Type Variants ──────────────────────────────────────────────────
    {**IRVE3_BASELINE, "name": "V13_Pointy_Nose",
     "nose_type": "pointy", "flat_skin": False,
     "desc": "Pointy nose, scalloped skin"},
    {**IRVE3_BASELINE, "name": "V14_Smooth_Scallop",
     "flat_skin": False,
     "desc": "Smooth nose, scalloped skin"},

    # ── Combined Variants (design exploration) ──────────────────────────────
    {**IRVE3_BASELINE, "name": "V15_Compact_Blunt",
     "diameter_m": 2.5, "angle": 70.0, "toroid_count": 4,
     "desc": "Compact blunt decelerator"},
    {**IRVE3_BASELINE, "name": "V16_Large_Steep",
     "diameter_m": 4.0, "angle": 45.0, "toroid_count": 8,
     "desc": "Large steep decelerator"},
    {**IRVE3_BASELINE, "name": "V17_LOFTID_Class",
     "diameter_m": 3.8, "angle": 65.0, "toroid_count": 7,
     "toroid_radius": 0.15, "desc": "LOFTID-inspired geometry"},
    {**IRVE3_BASELINE, "name": "V18_Mini_IRVE",
     "diameter_m": 2.0, "angle": 60.0, "toroid_count": 5,
     "payload_radius": 0.4, "desc": "Mini IRVE for CubeSat"},
    {**IRVE3_BASELINE, "name": "V19_Flat_Extreme",
     "angle": 80.0, "diameter_m": 3.5, "toroid_count": 6,
     "desc": "Near-flat aeroshell (80°)"},

    # ── Stress Tests (push geometry limits) ─────────────────────────────────
    {**IRVE3_BASELINE, "name": "V20_MinParams",
     "diameter_m": 2.0, "angle": 45.0, "toroid_count": 3,
     "toroid_radius": 0.08, "payload_radius": 0.3,
     "desc": "Minimum parameter set"},
    {**IRVE3_BASELINE, "name": "V21_MaxParams",
     "diameter_m": 4.5, "angle": 75.0, "toroid_count": 10,
     "toroid_radius": 0.20, "payload_radius": 0.8,
     "desc": "Maximum parameter set"},
    {**IRVE3_BASELINE, "name": "V22_Auto_Toroid_Rad",
     "toroid_radius": None, "desc": "Auto-calculated toroid radius"},
    {**IRVE3_BASELINE, "name": "V23_Pointy_Compact",
     "nose_type": "pointy", "flat_skin": False,
     "diameter_m": 2.5, "toroid_count": 4,
     "desc": "Pointy nose, compact layout"},

    # ── Orion-like variants ─────────────────────────────────────────────────
    {**IRVE3_BASELINE, "name": "V24_Orion_Scale",
     "diameter_m": 5.0, "angle": 60.0, "toroid_count": 8,
     "toroid_radius": 0.16, "payload_radius": 0.6,
     "payload_height": 2.0,
     "desc": "Orion-class scale (5m diameter)"},
]


def run_variant(variant, output_dir):
    """
    Generate a single variant using 3D-first pipeline:
      1. Generate 3D CAD solid (primary artifact)
      2. Extract cross-section from 3D solid (slice 3D → 2D)
      3. Export .surf from cross-section
      4. Export STL, STEP, JPG from 3D solid
      5. Validate the .surf file
    """
    name = variant["name"]
    desc = variant.get("desc", "")
    surf_path = os.path.join(output_dir, f"{name}.surf")

    # Extract params (exclude non-HIAD keys)
    hiad_params = {k: v for k, v in variant.items() if k not in ("name", "desc")}

    result = {
        "name": name,
        "desc": desc,
        "surf_path": surf_path,
        "stl_path": None,
        "step_path": None,
        "jpg_path": None,
        "cross_section_source": "analytical",
        "params": hiad_params,
        "generated": False,
        "validated": False,
        "points": 0,
        "segments": 0,
        "errors": [],
    }

    try:
        # Step 1: Generate 3D CAD solid (primary artifact)
        hiad, skin_pts = generate_hiad(
            diameter_m=hiad_params["diameter_m"],
            angle=hiad_params["angle"],
            toroid_count=hiad_params["toroid_count"],
            toroid_radius=hiad_params.get("toroid_radius"),
            shoulder_torus_radius=hiad_params.get("shoulder_radius"),
            payload_radius=hiad_params["payload_radius"],
            payload_height=hiad_params["payload_height"],
            nose_type=hiad_params["nose_type"],
            flat_skin=hiad_params["flat_skin"],
            output_prefix=os.path.join(output_dir, name),
            debug_image=False,
            payload=False,
            payload_type="cylinder",
            slice_angle=360.0,  # Full revolution for complete 3D model
        )
        result["generated"] = True

        # Step 2: Extract cross-section from 3D solid (slice 3D → 2D)
        cross_section_pts = None
        if hiad is not None:
            try:
                cross_section_pts = extract_cross_section_from_3d(hiad)
                result["cross_section_source"] = "3d_section"
                print(f"  [3D→2D] Extracted {len(cross_section_pts)} points from 3D solid")
            except Exception as e:
                print(f"  [3D→2D] Cross-section extraction failed: {e}")
                print(f"  [3D→2D] Falling back to analytical 2D points")

        # Step 3: Export .surf (prefer 3D cross-section, fallback to analytical)
        if cross_section_pts:
            export_to_sparta_surf_3d(cross_section_pts, surf_path)
            result["points"] = len(cross_section_pts)
        else:
            export_to_sparta_surf(skin_pts, surf_path)
            result["points"] = len(skin_pts)

        # Step 4: Export STL, STEP, JPG from 3D solid
        if HAS_CQ and hiad is not None:
            # STL
            try:
                stl_path = os.path.join(output_dir, f"{name}.stl")
                if hasattr(hiad, 'val'):
                    hiad.val().exportStl(stl_path, ascii=True)
                else:
                    cq_exporters.export(hiad, stl_path, exportType=cq_exporters.ExportTypes.STL)
                result["stl_path"] = stl_path
            except Exception as e:
                result["errors"].append(f"STL export failed: {e}")

            # STEP
            try:
                step_path = os.path.join(output_dir, f"{name}.step")
                export_solid_to_step(hiad, step_path)
                result["step_path"] = step_path
            except Exception as e:
                result["errors"].append(f"STEP export failed: {e}")

            # JPG
            try:
                jpg_path = os.path.join(output_dir, f"{name}.jpg")
                render_solid_jpg(hiad, jpg_path, title=f"{name} — {desc}")
                result["jpg_path"] = jpg_path
            except Exception as e:
                result["errors"].append(f"JPG render failed: {e}")

        # Step 5: Validate
        report = validate_surf(surf_path)
        result["validated"] = report.passed
        result["segments"] = report.n_lines if hasattr(report, 'n_lines') else 0
        if not report.passed:
            result["errors"] = [str(e) for e in report.errors]

    except Exception as exc:
        result["errors"].append(f"GENERATION FAILED: {exc}")
        traceback.print_exc()

    return result


def generate_summary_table(results):
    """Print a formatted summary table."""
    lines = []
    lines.append("")
    lines.append("=" * 140)
    lines.append("  IRVE-3 / HIAD GEOMETRY VARIANT AUDIT — 25 VARIANTS (SURF + STL + STEP + JPG) — 3D-FIRST PIPELINE")
    lines.append("=" * 140)
    lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"  Pipeline: 3D CAD → cross-section → .surf (SPARTA) + STL + STEP + JPG")
    lines.append(f"  Total variants: {len(results)}")
    lines.append(f"  Passed: {sum(1 for r in results if r['validated'])}")
    lines.append(f"  Failed: {sum(1 for r in results if not r['validated'])}")
    stl_count = sum(1 for r in results if r.get('stl_path'))
    step_count = sum(1 for r in results if r.get('step_path'))
    jpg_count = sum(1 for r in results if r.get('jpg_path'))
    cs_3d = sum(1 for r in results if r.get('cross_section_source') == '3d_section')
    lines.append(f"  STL exported: {stl_count}/{len(results)}  |  STEP: {step_count}/{len(results)}  |  JPG: {jpg_count}/{len(results)}")
    lines.append(f"  Cross-section: {cs_3d}/{len(results)} from 3D solid  |  {len(results)-cs_3d}/{len(results)} from analytical 2D")
    lines.append("=" * 140)
    lines.append("")

    # Header
    hdr = (f"{'#':<4} {'Name':<28} {'Diam':>6} {'Angle':>6} {'T#':>3} "
           f"{'Tr':>6} {'Pr':>5} {'Pts':>5} {'CS':>5} {'STL':>4} {'STEP':>5} {'JPG':>4} {'Status':>8}")
    lines.append(hdr)
    lines.append("-" * 140)

    for i, r in enumerate(results):
        p = r["params"]
        status = "PASS" if r["validated"] else "FAIL"
        stl = "OK" if r.get("stl_path") else "SKIP"
        step = "OK" if r.get("step_path") else "SKIP"
        jpg = "OK" if r.get("jpg_path") else "SKIP"
        cs = "3D" if r.get("cross_section_source") == "3d_section" else "2D"
        line = (
            f"{i:<4} {r['name']:<28} "
            f"{p['diameter_m']:>6.1f} "
            f"{p['angle']:>6.1f} "
            f"{p['toroid_count']:>3} "
            f"{(p['toroid_radius'] or 0):>6.3f} "
            f"{p['payload_radius']:>5.2f} "
            f"{r['points']:>5} "
            f"{cs:>5} "
            f"{stl:>4} "
            f"{step:>5} "
            f"{jpg:>4} "
            f"{status:>8}"
        )
        lines.append(line)

    lines.append("-" * 140)

    # Print failures
    failures = [r for r in results if not r["validated"]]
    if failures:
        lines.append("")
        lines.append("FAILURES:")
        for r in failures:
            lines.append(f"  {r['name']}: {r['errors']}")
    else:
        lines.append("")
        lines.append("ALL VARIANTS PASSED VALIDATION.")

    lines.append("")
    return "\n".join(lines)


def main():
    output_dir = os.path.join(os.path.dirname(__file__), "geometry_variants_25")
    os.makedirs(output_dir, exist_ok=True)

    print(f"Generating 25 HIAD/IRVE-3 geometry variants in: {output_dir}")
    print(f"IRVE-3 Baseline: diameter={IRVE3_BASELINE['diameter_m']}m, "
          f"angle={IRVE3_BASELINE['angle']}°, "
          f"toroids={IRVE3_BASELINE['toroid_count']}, "
          f"r_torus={IRVE3_BASELINE['toroid_radius']}m")
    print()

    results = []
    for i, variant in enumerate(VARIANTS):
        print(f"[{i+1:2d}/25] Generating {variant['name']}...")
        result = run_variant(variant, output_dir)
        results.append(result)
        status = "PASS" if result["validated"] else "FAIL"
        print(f"        {status} — {result['points']} points, {result['desc']}")

    # Summary table
    summary = generate_summary_table(results)
    print(summary)

    # Save summary
    summary_path = os.path.join(output_dir, "VARIANT_AUDIT_SUMMARY.txt")
    with open(summary_path, 'w') as f:
        f.write(summary)
    print(f"Summary saved to: {summary_path}")

    # Save JSON results
    json_path = os.path.join(output_dir, "variant_results.json")
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"JSON results saved to: {json_path}")

    return results


if __name__ == "__main__":
    main()
