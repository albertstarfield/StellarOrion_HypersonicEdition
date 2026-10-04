#!/usr/bin/env python3
"""Correct the thermal-constraint subsection of Chapter 4 against the code and
the recorded run output.

WHY EVERY EDIT HERE IS A CORRECTION, NOT A REWORDING
AXIOM: The subsection asserted four quantities. Three of them are contradicted
by artefacts in this repository, and each contradiction is traceable to a file
and line.

  1. "backface temperature consistently reaches 492.0 K"
     CONTRADICTED. README.md:238-244 records the actual output of the validation
     gate with the ACTIVE thermal protection system:
         Survivability: FAILED -- vehicle does not survive.
         Backface temp :  9.55662E+02 K      (KAPTON_MAX_TEMP = 673 K)
     492.0 K does not appear in any results artefact.

  2. "exceeds the 350 K payload thermal limit"
     CONTRADICTED. No 350 K limit exists in the engine. The implemented
     predicate is `Is_Survivable` in
     stellarorion_program_proc/src/simulation_engine/stellarorion_physics.adb,
     which is a four-way conjunction:
         Surface_Temp_K <= SIC_MAX_TEMP            (types.ads:97  = 2073.0 K)
         Backface_Temp_K <= KAPTON_MAX_TEMP        (types.ads:101 =  773.0 K)
         G_Load <= MAX_G_LOAD                      (types.ads:105 =   25.0)
         Decel_G <= MAX_G_LOAD                     (types.ads:105 =   25.0)
     The IRVE-3 F-TPS additionally carries a structural limit
     IRVE3_FTPS_STRUCT_LIMIT_K = 523.15 K (types.ads:590).
     (README.md:238 also prints "673 K" for the Kapton limit; that string is
     STALE. The compiled constant is 773.0 K, verified at types.ads:101. The
     773 K value is used here.)

  3. "baseline TPS parameters (delta_TPS = 25.4 mm)"
     CONTRADICTED. README.md:159-183 documents the ACTIVE system as the 5-ply
     IRVE-3 flexible TPS, total 6.35 mm, series resistance R = 0.25605
     m^2 K/W, outer emissivity 0.80. README.md:180-183 states the 25.4 mm
     homogeneous SiC slab was "the LOFTID baseline, 4x too thick for IRVE-3",
     was a "wrong-vehicle default", and that "--tps now defaults to irve3-ftps".
     So 25.4 mm is not the baseline; it is a superseded value.

  4. "Q ~ 11.38 MJ/m^2"
     CONTRADICTED BY ARITHMETIC ON THE THESIS'S OWN NUMBER. The thesis's own
     heat load is 165.72 J/cm^2 (chapter_04_results.tex:160, and
     validation_smooth/validation_timeseries.csv heat_load_jcm2 = 165.715973).
     1 J/cm^2 = 0.1 MJ/m^2, so 165.72 J/cm^2 = 1.657 MJ/m^2. The stated
     11.38 MJ/m^2 is 6.9x larger and matches no artefact.

THEORY: With the active 6.35 mm TPS the vehicle FAILS the gate. That is the
honest result and it strengthens rather than weakens the thesis, because it is
the quantitative justification for the TPS-thickness recommendation the
subsection was trying to make, and it follows from the real layup instead of a
superseded one.

Citations
---------
* Is_Survivable predicate: stellarorion_physics.adb (function Is_Survivable).
* Material limits: stellarorion_types.ads:97,101,105,590.
* F-TPS layup: README.md:159-183; stellarorion_types.ads:672 (TPS_Layup_IRVE3).
* Gate output: README.md:238-244.
"""

from __future__ import annotations

from pathlib import Path

CH4 = Path(__file__).resolve().parent / "chapter_04_results.tex"

EDITS: list[tuple[str, str]] = [
    # ---- 1 + 2 + 3: the finding sentence and the baseline it attributes to ----
    (
        "A critical finding across all optimization samples is that the "
        "backface temperature consistently reaches 492.0\\,K, which exceeds "
        "the 350\\,K payload thermal limit by 142\\,K. This indicates that the "
        "current 1D thermal model with the baseline TPS parameters "
        "($\\delta_{TPS} = 25.4$\\,mm, $\\rho_{TPS} = 322.94$\\,kg/m$^3$, "
        "$C_{p,TPS} = 1000$\\,J/(kg$\\cdot$K)) is insufficient for payload "
        "protection at the 51.8\\,km altitude flight condition.",
        "A critical finding is that the vehicle does not survive the thermal "
        "constraint. With the active thermal protection system the engine "
        "reports a backface temperature of 955.66\\,K, which exceeds the "
        "Kapton limit of 773\\,K by 182.7\\,K and the IRVE-3 flexible-TPS "
        "structural limit of 523.15\\,K by 432.5\\,K. The active system is "
        "not a homogeneous slab but the five-ply IRVE-3 flexible TPS: two "
        "0.60\\,mm Nextel BF-20 outer fabric plies, two 2.50\\,mm Pyrogel "
        "2250 insulation plies, and one 0.15\\,mm aluminized Kapton/Kevlar gas "
        "barrier, totalling 6.35\\,mm with a series thermal resistance of "
        "$R = 0.25605$\\,m$^2\\,K/W and an outer emissivity of 0.80. This "
        "supersedes the 25.4\\,mm homogeneous silicon-carbide slab used in "
        "earlier revisions of this work, which was the LOFTID baseline and was "
        "four times too thick for this vehicle. The survivability verdict is "
        "set by the four-way predicate implemented in the engine, which "
        "requires the surface temperature to stay below 2073\\,K, the "
        "backface temperature below 773\\,K, and both the measured and "
        "computed deceleration below 25\\,g. The thermal channel is therefore "
        "the binding constraint, while the deceleration channel passes with "
        "margin.",
    ),
    # ---- 4: the heat-load figure, in MJ/m^2 ----
    (
        "The consistent backface temperature across all samples suggests that "
        "the thermal soak is dominated by the total heat load "
        "($Q \\approx 11.38$\\,MJ/m$^2$) rather than the instantaneous heat "
        "flux, as the 1D transient model integrates the heat pulse over the "
        "full trajectory duration.",
        "The magnitude of the exceedance indicates that the thermal soak is "
        "dominated by the integrated heat load rather than by the instantaneous "
        "stagnation heat flux. The integrated load for this trajectory point "
        "is $Q = 165.72$\\,J/cm$^2$, which is $1.657$\\,MJ/m$^2$; the 1D "
        "transient model integrates the heat pulse over the exposure duration, "
        "so it is this accumulated quantity, and not the stagnation-point "
        "correlation value of Chapter~3, that sets the backface temperature.",
    ),
    # ---- recommendation 1: direction and baseline were both wrong ----
    (
        "    \\item The TPS thickness must be increased beyond 25.4\\,mm to "
        "provide sufficient thermal resistance.",
        "    \\item The active 6.35\\,mm layup is already insufficient, so "
        "the insulation must be thickened beyond its present Pyrogel content. "
        "The resistance requirement follows directly from the exceedance: "
        "reducing the backface temperature from 955.66\\,K to the 773\\,K "
        "Kapton limit requires the series resistance to rise by a factor of "
        "roughly 2.1 at the observed temperature difference, which for this "
        "stack means increasing the low-conductivity Pyrogel plies rather than "
        "the outer fabric.",
    ),
    # ---- recommendation 2: eta_lag was asserted with no source ----
    (
        "    \\item The thermal lag factor ($\\eta_{lag} = 0.15$) may need "
        "recalibration against higher-fidelity thermal analysis.",
        "    \\item The thermal lag factor "
        "($\\eta_{lag} = 0.15$) is a fixed lumped parameter rather than a "
        "fitted one, and it should be recalibrated against a higher-fidelity "
        "transient solution before the thickness recommendation above is "
        "treated as final.",
    ),
]


def main() -> int:
    text = CH4.read_text(encoding="utf-8")
    rc = 0
    for old, new in EDITS:
        n = text.count(old)
        if n != 1:
            print(f"  !! expected 1 match, found {n}: {old[:70]!r}")
            rc = 1
            continue
        text = text.replace(old, new, 1)
        print(f"  ok  {old[:70]!r}")
    if rc == 0:
        CH4.write_text(text, encoding="utf-8")
        print("\nchapter_04_results.tex thermal section corrected.")
    else:
        print("\nNOT WRITTEN (a replacement failed to match).")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
