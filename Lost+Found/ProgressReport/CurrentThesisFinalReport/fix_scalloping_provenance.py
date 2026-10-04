#!/usr/bin/env python3
"""Correct the provenance claims in the Chapter 4 scalloping comparison.

The reported VALUES are left untouched, because which dataset is authoritative
is a scientific decision for the thesis author, not something a text edit can
settle. What IS corrected here are claims that are false against the artefacts
regardless of which dataset is chosen, because each one is checkable now.

AXIOMS CHECKED AGAINST THE ARTEFACTS
------------------------------------
A1. "Comparing the scalloped and smooth DSMC solutions at the identical run
    condition (step 2200)"
    FALSE. The two time series in the same results tree are at DIFFERENT flight
    conditions and DIFFERENT lengths:
      validation_smooth/validation_timeseries.csv
          alt_km 51.818481 (constant), vel_ms 3378.671 (constant),
          mach 10.288205, steps 100..2200, 22 samples
      validation_scalloped/validation_timeseries.csv
          alt_km 52.032558 (constant), vel_ms 3094.193 (constant),
          mach 9.432495,  steps 100..1800, 18 samples
    The velocities differ by 8.4% and the Mach numbers by 8.3%. The scalloped
    series does not reach step 2200 at all. These two files are therefore NOT a
    controlled comparison and must not be described as one.

A2. "the peak g-load and the heat load are unchanged because both geometries
    are evaluated at the same trajectory point"
    FALSE for those files. At the last common step (1800):
        g_load      smooth 16.8334  scalloped 14.0059   (-16.8%)
        heat_load   smooth 165.716  scalloped 174.137   (+5.1%)
    Neither quantity is unchanged.

A3. The paired numbers come from TWO DIFFERENT FILES, not one comparison:
      182.5 W/cm^2, 56.6 W/cm^2, Cd 1.4625
        -> validation_scalloped/validation_pipeline_output/convergence_audit.csv
           (heatflux_max_Wm2 raw_final 1824880.0,
            heatflux_avg_Wm2 raw_final 565864.9375, cd raw_final 1.4625)
      158.4 W/cm^2, 54.4 W/cm^2, Cd 1.3358
        -> validation_smooth/validation_timeseries.csv at step 2200
           (heatflux_max_Wm2 1584280.0,
            heatflux_avg_Wm2 544008.875, cd 1.335816)
    Presenting these as the two halves of one controlled comparison is not
    supported. Note also that the scalloped convergence audit records
    g_load 16.8334 and heat_load_jcm2 165.7160, which are BIT-IDENTICAL to the
    smooth run's values, so that file cannot on its own distinguish the two
    geometries either.

A4. A third artefact disagrees on the SIGN of the mean-heat-flux change:
    validation_scalloped/COMPARISON_Scalloped_Smooth_Rapisarda.md (dated
    2026-09-01) tabulates both geometries at a COMMON condition
    (51.82 km, 3379 m/s, Mach 10.29, 2200 steps) and reports
        Mean Element Heat Flux   scalloped 69.12   smooth 71.92   -3.9%
        Mean Cd                  scalloped 1.5821  smooth 1.4544  +8.8%
        Mean Cl                  scalloped -0.5021 smooth -0.4935 +1.7%
        Peak Heat Flux           scalloped 428.80  smooth 424.91  +0.9%
    i.e. the mean element heat flux is 3.9% LOWER for the scalloped skin, the
    opposite sign to the +4.0% currently reported.

THEORY: Because A4 shows the repository holds three mutually inconsistent
scalloped datasets, the honest move is to state the provenance of each figure,
withdraw the "identical run condition" and "unchanged" claims, and disclose the
disagreement rather than silently picking a winner. The values themselves are
preserved so the author's decision is the only thing left to make.
"""

from __future__ import annotations

from pathlib import Path

CH4 = Path(__file__).resolve().parent / "chapter_04_results.tex"

OLD = (
    "Comparing the scalloped and smooth DSMC solutions at the identical run "
    "condition (step 2200) gives a peak kinetic energy flux of 182.5 against "
    "158.4~W/cm\\textsuperscript{2} and a per-element average of 56.6 against "
    "54.4~W/cm\\textsuperscript{2}, i.e.\\ increases of $15.2\\%$ and $4.0\\%$ "
    "respectively, consistent in sign and in ordering with the geometric bound, "
    "and roughly a factor of five below it. The same comparison gives a $9.5\\%$ "
    "increase in $C_d$ (1.4625 against 1.3358) and a $5.5\\%$ increase in "
    "$|C_l|$, while the peak $g$-load and the heat load are unchanged because "
    "both geometries are evaluated at the same trajectory point."
)

NEW = (
    "The augmentation reported here is assembled from two separate recorded "
    "exports rather than from a single controlled pair, and the distinction is "
    "material. The scalloped figures, a peak kinetic energy flux of "
    "182.5~W/cm\\textsuperscript{2}, a per-element average of "
    "56.6~W/cm\\textsuperscript{2} and $C_d = 1.4625$, are the "
    "\\texttt{raw\\_final} entries of the scalloped run's convergence audit, "
    "whereas the smooth figures, 158.4~W/cm\\textsuperscript{2}, "
    "54.4~W/cm\\textsuperscript{2} and $C_d = 1.3358$, are the step-2200 "
    "entries of the smooth run's time series. These are increases of $15.2\\%$ "
    "and $4.0\\%$ on the flux quantities and $9.5\\%$ on $C_d$: consistent in "
    "sign and in ordering with the geometric bound, and roughly a factor of "
    "five below it.\n\n"
    "This comparison is not, however, a controlled one, and two limitations "
    "must be stated rather than glossed. First, the two recorded time series "
    "are not at the same flight condition: the smooth series is held at "
    "51.82~km and 3378.7~m/s (Mach 10.29) while the scalloped series is held at "
    "52.03~km and 3094.2~m/s (Mach 9.43), a velocity difference of 8.4\\%, and "
    "the scalloped series terminates at step 1800 rather than 2200. Over the "
    "last common step of 1800 the peak $g$-load falls from 16.83 to "
    "14.01\\,g and the integrated heat load rises from 165.72 to "
    "174.14~J/cm\\textsuperscript{2}, so neither quantity is invariant between "
    "the two series and neither can be attributed to scalloping alone. Second, "
    "a separate comparison record in the repository, which tabulates both "
    "geometries at a common condition of 51.82~km and 3379~m/s over 2200 "
    "steps, reports the mean element heat flux as 3.9\\% \\emph{lower} for the "
    "scalloped skin (69.12 against 71.92~W/cm\\textsuperscript{2}) while "
    "reporting $C_d$ 8.8\\% higher and $|C_l|$ 1.7\\% higher. The direction of "
    "the mean-flux change is therefore not settled by the present evidence, "
    "and the drag increase is the one scalloping effect on which the records "
    "agree. Isolating the scalloping effect from the flight-condition "
    "difference requires a re-run of both skins at a single shared state, "
    "which is identified as future work in "
    "Sec.~\\ref{sec:optimization_results}."
)


def main() -> int:
    text = CH4.read_text(encoding="utf-8")
    n = text.count(OLD)
    if n != 1:
        print(f"!! expected exactly 1 match, found {n}")
        return 1
    CH4.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print("ok  scalloping provenance corrected (values preserved, false claims withdrawn)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
