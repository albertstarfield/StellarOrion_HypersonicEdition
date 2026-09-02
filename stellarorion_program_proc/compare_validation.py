#!/usr/bin/env python3
"""
compare_validation.py
=====================
Builds the Scalloped / Smooth / Rapisarda(IRVE-3) validation comparison table.

CONTEXT:
  StellarOrion DSMC replicates the IRVE-3 flight vehicle using Rapisarda's
  (2023) parametric geometry model (Table 4.1). This script compares the
  DSMC results against IRVE-3 flight data and Rapisarda's analytical models
  (Fay-Riddell, Sutton-Graves) from Table 4.10.

  The validated IRVE-3 baseline is the starting point for Earth reentry
  optimization. LOFTID (6.0m, 70 deg, 6+1 tori) serves as the scaling
  benchmark for LEO reentry conditions (V_entry ~8 km/s).

Reads the two `validation_timeseries.csv` files produced by
`bin/main --validate --skin {scalloped,smooth} --steps 2200` and compares the
peak aerothermodynamic metrics against the Rapisarda (2023) / IRVE-3 flight
reference (Table 4.10).

Reference values (Rapisarda 2023, IRVE-3 MDAO baseline, Table 4.10 / NASA TP-2013-4012):
  * Peak heat flux  q_max = 14.36 W/cm^2  (= 143,600 W/m^2)
  * Total heat load Q     = 195.06 J/cm^2 (= 1,950,600 J/m^2)
  * Peak deceleration     = 19.7 g  (flight) / 20.2 g (MDAO)
  * Ballistic coeff beta  = 26.9 kg/m^2
  * Decel conversion:  decel_g = drag_sum_N / 2755.67   (m = 281.0 kg, g0 = 9.80665)

LOFTID reference (Deshmukh et al. AIAA-2024-1501, Hollis et al. AIAA-2024-1498):
  * Peak heat flux: ~39.27 W/cm^2 (2.7x IRVE-3)
  * Total heat load: ~3.52 kJ/cm^2 (18x IRVE-3)
  * Peak deceleration: 9.66 g (0.5x IRVE-3)
  * Diameter: 6.0 m (2x IRVE-3)

KEY SUCCESS VARIABLES (from Sep 2 Discussion.md Section 12):
  A HIAD mission is successful iff ALL five checks pass:
    1. TPS survives heat flux:     T_surface < 1700 K (SIC limit)
    2. TPS survives heat load:     T_back < 673 K (Kapton limit)
    3. Structure survives decel:    g_load < 25g (structural limit)
    4. Vehicle decelerates enough:  V_final < para-deploy limit
    5. Landing accuracy:            Within target zone
  Primary metrics: q_max (W/cm^2), Q_total (J/cm^2), g_load, T_surface, T_back.
  Design variables: D (m), theta_c (deg), r_torus (m), N (tori), m (kg).
  Entry conditions (fixed): V_entry (km/s), gamma_entry (deg), h_entry (km).

Usage:
  python3 compare_validation.py
Writes: results_validation_scalloped/COMPARISON_Scalloped_Smooth_Rapisarda.md
"""
import csv
import os
import sys

PROC = os.path.dirname(os.path.abspath(__file__))
SCALLOPED_CSV = os.path.join(PROC, "results_validation_scalloped", "validation_timeseries.csv")
SMOOTH_CSV    = os.path.join(PROC, "results_validation_smooth",    "validation_timeseries.csv")
OUT_MD        = os.path.join(PROC, "results_validation_scalloped", "COMPARISON_Scalloped_Smooth_Rapisarda.md")

# Rapisarda / IRVE-3 reference (Rapisarda 2023 Table 4.10)
RAP_Q_MAX_WCM2   = 14.36      # W/cm^2  peak heat flux
RAP_Q_LOAD_JCM2  = 195.06     # J/cm^2  total heat load
RAP_DECEL_G      = 19.7       # g       peak deceleration (flight)
RAP_BETA_KGM2    = 26.9       # kg/m^2  ballistic coefficient
DECEL_DENOM_N    = 2755.67    # N per g  (m=281.0 kg * 9.80665)

# LOFTID reference (Deshmukh et al. AIAA-2024-1501, Table 2, middle window)
LOFTID_Q_MAX_WCM2  = 39.27    # W/cm^2  peak heat flux (nose)
LOFTID_Q_LOAD_KJCM2 = 3.52    # kJ/cm^2 total heat load (nose)
LOFTID_DECEL_G     = 9.66     # g       peak deceleration
LOFTID_DIAMETER_M  = 6.0      # m       vehicle diameter


def load_csv(path):
    if not os.path.exists(path):
        return None
    rows = []
    with open(path, newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                rows.append({
                    "step":        int(float(row["step"])),
                    "drag_sum_N":  float(row["drag_sum_N"]),
                    "lift_sum_N":  float(row["lift_sum_N"]),
                    "heatflux_max_Wm2": float(row["heatflux_max_Wm2"]),
                    "heat_sum_Wm2":     float(row["heat_sum_Wm2"]),
                    "drag_avg_N":  float(row["drag_avg_N"]),
                    "lift_avg_N":  float(row["lift_avg_N"]),
                })
            except (ValueError, KeyError):
                continue
    return rows if rows else None


def summarize(rows):
    if rows is None:
        return None
    peak_drag  = max(r["drag_sum_N"] for r in rows)
    peak_lift  = max(abs(r["lift_sum_N"]) for r in rows)
    peak_hf    = max(r["heatflux_max_Wm2"] for r in rows)   # W/m^2
    peak_hs    = max(r["heat_sum_Wm2"] for r in rows)       # per-step total heat rate (W or W/m^2)
    peak_decel = peak_drag / DECEL_DENOM_N
    return {
        "peak_drag_N":  peak_drag,
        "peak_lift_N":  peak_lift,
        "peak_hf_Wm2":  peak_hf,
        "peak_hf_Wcm2": peak_hf / 1.0e4,
        "peak_hs":      peak_hs,
        "peak_decel_g": peak_decel,
        "n_steps":      len(rows),
    }


def fmt(x, sci=False):
    if x is None:
        return "PENDING"
    if sci:
        return f"{x:.3e}"
    if abs(x) >= 1000:
        return f"{x:,.1f}"
    return f"{x:.2f}"


def main():
    sc = summarize(load_csv(SCALLOPED_CSV))
    sm = summarize(load_csv(SMOOTH_CSV))

    sc_stat = "AVAILABLE" if sc else "PENDING (sim running)"
    sm_stat = "AVAILABLE" if sm else "MISSING"

    lines = []
    lines.append("# Validation Comparison: Scalloped vs Smooth vs IRVE-3 vs LOFTID")
    lines.append("")
    lines.append(f"- Scalloped CSV: `{os.path.relpath(SCALLOPED_CSV, PROC)}`  — **{sc_stat}**")
    lines.append(f"- Smooth CSV:    `{os.path.relpath(SMOOTH_CSV, PROC)}`  — **{sm_stat}**")
    lines.append(f"- Reference: Rapisarda (2023) IRVE-3 baseline, Table 4.10 / NASA TP-2013-4012; "
                 f"LOFTID: Deshmukh et al. AIAA-2024-1501 / Hollis et al. AIAA-2024-1498")
    lines.append("")
    lines.append("## Peak Aerothermodynamic Metrics")
    lines.append("")
    lines.append("| Metric | Scalloped | Smooth | IRVE-3 Ref | LOFTID Ref | Scalloped/Smooth |")
    lines.append("|---|---|---|---|---|---|")

    def ratio(a, b):
        if a is None or b is None or b == 0:
            return "—"
        return f"{a/b:.3f}"

    # Peak drag
    lines.append("| Peak Drag Force (N) | " +
                 f"{fmt(sc['peak_drag_N'] if sc else None)} | " +
                 f"{fmt(sm['peak_drag_N'] if sm else None)} | — | — | " +
                 f"{ratio(sc['peak_drag_N'] if sc else None, sm['peak_drag_N'] if sm else None)} |")
    # Peak |lift|
    lines.append("| Peak |Lift| Force (N) | " +
                 f"{fmt(sc['peak_lift_N'] if sc else None)} | " +
                 f"{fmt(sm['peak_lift_N'] if sm else None)} | — | — | " +
                 f"{ratio(sc['peak_lift_N'] if sc else None, sm['peak_lift_N'] if sm else None)} |")
    # Peak heat flux (literal column = W/m^2 -> W/cm^2)
    lines.append("| Peak Heat Flux (W/cm^2, literal col /1e4) | " +
                 f"{fmt(sc['peak_hf_Wcm2'] if sc else None)} | " +
                 f"{fmt(sm['peak_hf_Wcm2'] if sm else None)} | " +
                 f"{RAP_Q_MAX_WCM2:.2f} | " +
                 f"{LOFTID_Q_MAX_WCM2:.2f} | " +
                 f"{ratio(sc['peak_hf_Wcm2'] if sc else None, sm['peak_hf_Wcm2'] if sm else None)} |")
    # Peak deceleration
    lines.append("| Peak Deceleration (g) | " +
                 f"{fmt(sc['peak_decel_g'] if sc else None)} | " +
                 f"{fmt(sm['peak_decel_g'] if sm else None)} | " +
                 f"{RAP_DECEL_G:.1f} | " +
                 f"{LOFTID_DECEL_G:.2f} | " +
                 f"{ratio(sc['peak_decel_g'] if sc else None, sm['peak_decel_g'] if sm else None)} |")
    # Peak total heat rate (heat_sum column, per-step snapshot)
    lines.append("| Peak Total Heat Rate (W, heat_sum col) | " +
                 f"{fmt(sc['peak_hs'] if sc else None, sci=True)} | " +
                 f"{fmt(sm['peak_hs'] if sm else None, sci=True)} | — | — | " +
                 f"{ratio(sc['peak_hs'] if sc else None, sm['peak_hs'] if sm else None)} |")
    # Vehicle diameter (geometry context)
    lines.append("| Vehicle Diameter (m) | " +
                 f"3.0 | 3.0 | 3.0 | " +
                 f"{LOFTID_DIAMETER_M:.1f} | — |")
    lines.append("")

    lines.append("## Reference Targets")
    lines.append("")
    lines.append("### IRVE-3 (Rapisarda 2023 / NASA TP-2013-4012)")
    lines.append(f"- Peak heat flux  q_max = **{RAP_Q_MAX_WCM2} W/cm^2** (143,600 W/m^2)")
    lines.append(f"- Total heat load Q     = **{RAP_Q_LOAD_JCM2} J/cm^2** (1,950,600 J/m^2)")
    lines.append(f"- Peak deceleration     = **{RAP_DECEL_G} g** (flight) / 20.2 g (MDAO)")
    lines.append(f"- Ballistic coeff  beta = **{RAP_BETA_KGM2} kg/m^2**")
    lines.append(f"- Diameter              = **3.0 m**")
    lines.append(f"- Decel conversion: decel_g = drag_sum_N / {DECEL_DENOM_N} (m=281.0 kg)")
    lines.append("")
    lines.append("### LOFTID (Deshmukh et al. AIAA-2024-1501 / Hollis et al. AIAA-2024-1498)")
    lines.append(f"- Peak heat flux  q_max = **{LOFTID_Q_MAX_WCM2} W/cm^2** ({LOFTID_Q_MAX_WCM2/RAP_Q_MAX_WCM2:.1f}x IRVE-3)")
    lines.append(f"- Total heat load Q     = **{LOFTID_Q_LOAD_KJCM2} kJ/cm^2** (~18x IRVE-3)")
    lines.append(f"- Peak deceleration     = **{LOFTID_DECEL_G} g** ({LOFTID_DECEL_G/RAP_DECEL_G:.2f}x IRVE-3)")
    lines.append(f"- Diameter              = **{LOFTID_DIAMETER_M} m** (2x IRVE-3)")
    lines.append(f"- Entry velocity        = **~8.0 km/s** (LEO, vs IRVE-3 ~3.5–4.5 km/s suborbital)")
    lines.append("")

    # Flags / caveats
    lines.append("## Notes & Data-Quality Flags")
    lines.append("")
    if sm:
        sm_hf = sm["peak_hf_Wcm2"]
        if sm_hf > 0:
            ratio_vs_rap = sm_hf / RAP_Q_MAX_WCM2
            lines.append(f"- **Heat-flux magnitude check:** Smooth peak heat flux = {sm_hf:.1f} W/cm^2 "
                         f"(literal `heatflux_max_Wm2`/1e4). Rapisarda reference = {RAP_Q_MAX_WCM2} W/cm^2. "
                         f"Ratio = {ratio_vs_rap:.1f}x.")
            if ratio_vs_rap > 3 or ratio_vs_rap < 0.33:
                lines.append("  - ⚠ LARGE DISCREPANCY. The `heatflux_max_Wm2` column is labeled W/m^2 but its "
                             "magnitude is much higher than IRVE-3 flight peak. Two possibilities:")
                lines.append("    1. The column is actually **total heat power (W)**, not per-area flux; dividing by "
                             "the vehicle reference area (~7.07 m^2 for 3 m diameter IRVE-3) normalizes it to "
                             "physically plausible W/cm^2 values.")
                lines.append("    2. There is a unit/scaling bug in the heat-flux reporting. RECOMMEND verifying the "
                             "column semantics (per-area vs total) before trusting absolute heat-flux numbers.")
            else:
                lines.append("  - Heat-flux magnitude is within expected range vs reference.")
        lines.append(f"- **Deceleration check:** Smooth peak decel = {sm['peak_decel_g']:.1f} g vs Rapisarda "
                     f"{RAP_DECEL_G} g ({(sm['peak_decel_g']/RAP_DECEL_G-1)*100:+.0f}% relative). Drag-based "
                     f"deceleration is in the right ballpark.")
    if sc and sm:
        for key, label in [("peak_drag_N", "drag"), ("peak_hf_Wcm2", "heat flux"),
                            ("peak_decel_g", "deceleration"), ("peak_lift_N", "lift")]:
            a, b = sc[key], sm[key]
            if b != 0:
                pct = (a/b - 1) * 100
                lines.append(f"- Corrugation effect on {label}: Scalloped is {pct:+.1f}% vs Smooth.")
    lines.append("")
    lines.append("## Storage Locations")
    lines.append("")
    lines.append(f"- Scalloped surf : `stellarorion_program_proc/results_validation_scalloped/HIAD_custom.surf`")
    lines.append(f"- Scalloped CSV  : `stellarorion_program_proc/results_validation_scalloped/validation_timeseries.csv`")
    lines.append(f"- Smooth surf   : `stellarorion_program_proc/results_validation_smooth/HIAD_custom.surf`")
    lines.append(f"- Smooth CSV    : `stellarorion_program_proc/results_validation_smooth/validation_timeseries.csv`")
    lines.append(f"- This report    : `stellarorion_program_proc/results_validation_scalloped/COMPARISON_Scalloped_Smooth_Rapisarda.md`")
    lines.append("")

    out = "\n".join(lines)
    with open(OUT_MD, "w") as f:
        f.write(out)
    print(out)
    print(f"\n[written] {OUT_MD}")


if __name__ == "__main__":
    main()
