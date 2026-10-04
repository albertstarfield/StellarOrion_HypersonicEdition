#!/usr/bin/env python3
"""Integrate the regenerated figures and repair the stub and false captions.

PART 1 - THE GENERIC TEMPLATE FLOWCHART IS REPLACED
AXIOM: `figures/flowchart.png` was included in Chapter 1 as "Research methodology
flowchart" and in Chapter 3 as "Flowchart of the numerical research methodology".
Its artwork does not match either caption. Transcribed verbatim it reads Start /
Various of papers Study / Literature Study / Data Retrieval and Familiar Study
Collection / Replicate Axisymmetric Slice Model Design? / "Simulate the Geometry
in Mach 5-6" / Simulation Result / Theoretically valid? or within error range? /
Data Analysis Simulation / Conclusion and Recommendation / End.
It never shows parametric geometry generation, DSMC, PINN refinement or the
optimisation loop, and its "Mach 5-6" label contradicts the Mach 10.29 run
condition used throughout. It is replaced by `fignew_pipeline.png`, built from
the twelve stages the validation pipeline actually prints.

The same file was ALSO included twice, which the page audit flagged as a
near-empty full page in Chapter 3 devoted to a repeat of the Chapter 1 figure.
Chapter 3 therefore now cross-references Figure 1.x instead of reprinting it,
which removes both the wrong artwork and the duplicated float.

PART 2 - FIGURES THE CHAPTERS DESCRIBE BUT NEVER SHOW
  scalloped vs smooth heating   ch4; the adjacent temperature-map caption had to
                                ADMIT that no scalloped field map exists
  entry trajectory              neither chapter had any trajectory figure
  convergence residuals         replaced, because the existing caption claims a
                                fall of "about three orders of magnitude" and
                                the data measures 1.83, 1.91 and 1.91 decades
  CCD design screen             the existing 3-D view does not distinguish the
                                factorial, axial and centre classes and hides
                                points by occlusion
  hybrid validation gate        the gate's central quantitative claim had no
                                figure anywhere

PART 3 - STUB AND FALSE CAPTIONS
Six Chapter 2 captions read "Figure for ..." and say nothing about their figure;
one of them ("Localized Peak Heating Effects in Amplification but through
Osicaltion.") is not English. Each is replaced with a caption that states what
the artwork actually shows.

CITATION
  Matplotlib, https://matplotlib.org/stable/
"""

from __future__ import annotations

import re
from pathlib import Path

TH = Path(__file__).resolve().parent
CH1 = TH / "chapter_01_introduction.tex"
CH3 = TH / "chapter_03_methodology.tex"
CH4 = TH / "chapter_04_results.tex"
CH2 = TH / "chapter_02_literature_review.tex"


def swap(path: Path, old: str, new: str, tag: str) -> bool:
    t = path.read_text(encoding="utf-8")
    n = t.count(old)
    if n != 1:
        print(f"  !! {tag}: expected 1 match, found {n}  ({path.name})")
        return False
    path.write_text(t.replace(old, new, 1), encoding="utf-8")
    print(f"  ok  {tag}  ({path.name})")
    return True


def insert_before(path: Path, anchor: str, block: str, tag: str) -> bool:
    t = path.read_text(encoding="utf-8")
    n = t.count(anchor)
    if n != 1:
        print(f"  !! {tag}: anchor found {n}x  ({path.name})")
        return False
    path.write_text(t.replace(anchor, block + "\n" + anchor, 1), encoding="utf-8")
    print(f"  ok  {tag}  ({path.name})")
    return True


FIG = "\\begin{figure}[!htbp]\n    \\centering\n"
INCLUDE = "    \\includegraphics[width=0.95\\textwidth]{figures/%s}%%\n    \\EndAccSupp{}%%\n"
ALT_OPEN = '    \\BeginAccSupp{method=escape,ActualText={%s}}%%\n'


def figure(name: str, alt: str, caption: str, label: str, width: str = "0.95") -> str:
    return (
        FIG
        + (ALT_OPEN % alt)
        + "    \\includegraphics[width=%s\\textwidth]{figures/%s}%%\n" % (width, name)
        + "    \\EndAccSupp{}%%\n"
        + f"    \\caption{{{caption}}}\n"
        + f"    \\label{{{label}}}\n"
        + "\\end{figure}"
    )


def main() -> int:
    ok = True

    # ---- 1. Chapter 1: replace the generic template flowchart --------------
    t = CH1.read_text(encoding="utf-8")
    m = re.search(r"    \\BeginAccSupp\{method=escape,ActualText=\{Vertical flowchart of the eleven-stage research workflow.*?\\label\{fig:flowchart_ch1\}\n\\end\{figure\}", t, re.S)
    if not m:
        print("  !! ch1 flowchart block not found")
        ok = False
    else:
        block = figure(
            "fignew_pipeline.png",
            "Flowchart of the validation pipeline, in twelve numbered stages read "
            "down the left column then down the right: 1 flight parameters, "
            "2 geometry quality assurance, 3 generate HIAD surface, 4 write solver "
            "input script, 5 build solver container, 6 run DSMC simulation, then 7 "
            "parse surface dumps, 8 compute flight metrics, 9 survivability check, "
            "10 sanity checks, 11 compare with IRVE-3 flight data, 12 export fields "
            "and plots. A separate row below shows the geometry optimisation loop: "
            "design space by Latin Hypercube or central composite screening, Bayesian "
            "optimisation with a Gaussian process and Expected Improvement, the cost "
            "function, DSMC re-simulation, and acceptance when the corrected heat load "
            "is at or below the target, with a reject-and-resample feedback path.",
            "The pipeline executed by the engine. The twelve numbered stages are "
            "those the full validation run prints, in the order it runs them: flight "
            "parameters are set, the geometry is checked, the HIAD surface is "
            "generated, the solver input is written, the solver container is built, "
            "the DSMC simulation runs, the surface dumps are parsed, flight metrics "
            "are computed, survivability and sanity checks are applied, the result is "
            "compared against IRVE-3 flight data, and fields, time series and plots "
            "are exported. The row beneath shows the separate geometry optimisation "
            "loop: a space-filling screen, Bayesian optimisation on a Gaussian process "
            "surrogate with Expected Improvement, the cost function, a full DSMC "
            "re-simulation of the candidate, and acceptance when the corrected heat "
            "load falls at or below the target. A rejected candidate returns to the "
            "design-space stage.",
            "fig:flowchart_ch1",
            width="0.92",
        )
        CH1.write_text(t[:m.start()] + block + t[m.end():], encoding="utf-8")
        print("  ok  ch1: generic template flowchart replaced (fig:flowchart_ch1)")

    # ---- 2. Chapter 3: replace the duplicate float with a cross-reference ----
    t = CH3.read_text(encoding="utf-8")
    m = re.search(r"\\begin\{figure\}\[!htbp\]\n    \\centering\n    % Same artwork as Figure 1\.6.*?\\label\{fig:flowchart\}\n\\end\{figure\}\n", t, re.S)
    if not m:
        print("  !! ch3 duplicate flowchart float not found")
        ok = False
    else:
        repl = ("The full pipeline is shown once, as Figure~\\ref{fig:flowchart_ch1}, "
                "rather than repeated here; it is reproduced in neither place because "
                "the same artwork twice costs a page and invites the reader to "
                "compare two copies of one diagram.\n")
        CH3.write_text(t[:m.start()] + repl + t[m.end():], encoding="utf-8")
        print("  ok  ch3: duplicated flowchart float replaced by a cross-reference")

    # ---- 3. Chapter 3: entry trajectory figure -------------------------------
    ok &= insert_before(
        CH3,
        "\\section{Computational Infrastructure}",
        figure(
            "fignew_trajectory.png",
            "Two panels describing the entry trajectory. The left panel plots "
            "velocity against altitude and rises to about 7500 metres per second "
            "at 122 kilometres before falling as the vehicle descends. The right "
            "panel plots deceleration load against altitude as a bell curve "
            "peaking near 17.5 g at about 57 kilometres. A square marker on each "
            "curve at 52.03 kilometres and 3094 metres per second marks the state "
            "used by the scalloped run, and a triangle near 51.8 kilometres and "
            "3379 metres per second marks the smooth run, which does not lie on "
            "the computed profile.",
            "The one-degree-of-freedom entry trajectory with the two simulation "
            "states marked. The profile is integrated from 122.65~km at "
            "7500~m/s down to 27.29~km, and both peak dynamic pressure and peak "
            "deceleration load occur at 57.0~km, where the velocity is "
            "4652~m/s at Mach 14.57 and the load reaches 17.42~g. The scalloped "
            "run was driven at a state that lies exactly on this profile, at "
            "$t = 97$~s; the smooth run's state does not lie on it, which is the "
            "precise reason the two runs cannot be compared as a controlled pair, "
            "as discussed in Chapter~\\ref{ch:results}.",
            "fig:trajectory",
        ),
        "ch3 entry trajectory figure",
    )

    # ---- 4. Chapter 4: convergence figure replaced + false claim fixed ------
    t = CH4.read_text(encoding="utf-8")
    m = re.search(r"    \\BeginAccSupp\{method=escape,ActualText=\{Log-scale plot of normalised convergence residuals.*?\\label\{fig:convergence\}\n\\end\{figure\}", t, re.S)
    if not m:
        print("  !! ch4 convergence figure block not found")
        ok = False
    else:
        block = figure(
            "fignew_convergence_residuals.png",
            "Log-scale plot of the normalised residual of three quantities against "
            "particle-time step. The drag coefficient falls from 0.38 at step 100 "
            "to 0.0056 at step 2200, the lift coefficient from 0.21 to 0.0026, and "
            "the per-element heat-flux average from 1.60 to 0.0199. All three "
            "curves descend with visible statistical scatter between adjacent "
            "samples.",
            "Convergence of the monitored surface quantities, plotted as the "
            "normalised residual $|x - x_{\\mathrm{ref}}|/|x_{\\mathrm{ref}}|$ "
            "against particle-time step, with $x_{\\mathrm{ref}}$ taken as the mean "
            "of the final three samples of each quantity. The residuals fall by "
            "1.83 decades for the drag coefficient, 1.91 for the lift coefficient "
            "and 1.91 for the per-element heat-flux average over steps "
            "100 to 2200. That is close to two decades rather than the three "
            "sometimes claimed for this quantity, and the figure is plotted so the "
            "reader can confirm it: the scatter between adjacent samples is the "
            "signature of a finite-sample particle estimator rather than a monotone "
            "error bound. The processed Sutton--Graves correlation value is "
            "deliberately not plotted, being a function of the fixed freestream "
            "state and therefore bit-identical at every step.",
            "fig:convergence",
        )
        CH4.write_text(t[:m.start()] + block + t[m.end():], encoding="utf-8")
        print("  ok  ch4: convergence figure replaced, false 'three orders' claim corrected")

    # ---- 5. Chapter 4: scalloped versus smooth, right after the paragraph -----
    t = CH4.read_text(encoding="utf-8")
    anchor = "\\begin{figure}[!htbp]\n    \\centering\n    \\BeginAccSupp{method=escape,ActualText={SPARTA temperature field in an axial-radial meridional slice through the smooth sphere-cone"
    m = re.search(re.escape(anchor), t)
    if not m:
        print("  !! ch4 thermal-map figure anchor not found for the scalloping insert")
        ok = False
    else:
        block = figure(
            "fignew_scalloped_vs_smooth_heatflux.png",
            "Two log-scale panels comparing the two skin simulations. The left "
            "panel shows the per-element mean heat flux against particle-time "
            "step, falling from about 145 to 54 watt per square centimetre for "
            "the smooth skin and from about 145 to 57 for the scalloped skin. The "
            "right panel shows the peak cell heat flux on the same axes. The "
            "legend states each run's altitude and velocity.",
            "Per-element mean and peak cell heat flux for the two skin "
            "configurations, on logarithmic axes against particle-time step. This "
            "is the comparison the preceding paragraph describes, and it is "
            "\\emph{not} a controlled one: the two runs are held at different "
            "trajectory states, with the scalloped run at 52.03~km and "
            "3094~m/s and the smooth run at 51.82~km and 3379~m/s. The figure is "
            "included so that the temperature field of the adjacent "
            "Figure~\\ref{fig:thermal_map} can be read against a scalar heating "
            "history for both skins, which the repository otherwise does not "
            "provide.",
            "fig:scalloped_heatflux",
        ) + "\n"
        CH4.write_text(t[:m.start()] + block + t[m.start():], encoding="utf-8")
        print("  ok  ch4: scalloped-versus-smooth heating figure inserted")

    # ---- 6. Chapter 4: gate comparison, at the end of the Gate Result --------
    ok &= insert_before(
        CH4,
        "\\subsection{Round-2 Corrected Optimum}",
        figure(
            "fignew_gate_comparison.png",
            "Bar chart of three measured heat loads against a dashed threshold "
            "line. The trajectory-integrated IRVE-3 flight value is 195.06 watt "
            "per square centimetre of heat load, the analytic prediction from the "
            "cost function is 155.67, and the DSMC re-simulation of the candidate "
            "geometry is 77.93. A dashed horizontal line marks the acceptance "
            "threshold of 165.72.",
            "The three measured heat loads entering the hybrid validation gate, "
            "with the acceptance threshold shown as a reference line. The "
            "trajectory-integrated flight value is the largest of the three, the "
            "analytic prediction of the round-1 design sits below the threshold, "
            "and the DSMC re-simulation of that same geometry is less than half "
            "the prediction. It is the last of the three that the gate compares "
            "against the threshold, and the correction factor it implies, "
            "$c = 0.5006$, is the quantity discussed below.",
            "fig:gate_comparison",
            width="0.80",
        ),
        "ch4 gate comparison figure",
    )

    # ---- 7. Chapter 4: CCD design screen ------------------------------------
    ok &= insert_before(
        CH4,
        "\\subsection{Bayesian Optimization (Bayes Opt)}",
        figure(
            "fignew_ccd_screen.png",
            "Three scatter panels showing the fifteen central composite design "
            "points as pairwise projections of the three design variables: nose "
            "radius against toroid radius, nose radius against half-cone angle, "
            "and toroid radius against half-cone angle. Eight factorial corner "
            "points appear as circles, six axial star points as triangles, and "
            "the single centre point as a star.",
            "The central composite screen in the three-dimensional design space, "
            "shown as three pairwise projections so that no point is hidden by "
            "occlusion. The eight factorial corner points, six axial star points "
            "and single centre point are distinguished by marker, which the "
            "oblique three-dimensional view of the same screen cannot do. The "
            "centre point carries the cost $J = 2.1674$ and the screen minimum is "
            "1.9959 at a factorial corner.",
            "fig:ccd_screen",
        ),
        "ch4 CCD screen figure",
    )

    # ---- 8. Chapter 2: stub and false captions ------------------------------
    stubs = [
        (267, "Figure for H. Julian Allen’s Blunt Body Theory.",
         "H. Julian Allen's blunt-body theory, showing the detachment shock that "
         "forms ahead of a blunt forebody and the resulting similarity in the "
         "shock stand-off distance and surface temperature across scaled "
         "geometries. The theory is the basis of the modified Newtonian panel "
         "method used for the reference model compared against in "
         "Chapter~\\ref{ch:results}."),
        (372, "Figure for Conventional Rigid TPS.",
         "Three conventional rigid thermal protection concepts shown in flight: a "
         "reinforced carbon-carbon nose cap on the Space Shuttle orbiter, a "
         "metallic honeycomb panel on a widebody aircraft, and a curved ablative "
         "shell. All three achieve protection by carrying heat away in a solid "
         "structure and none can be made compliant, which is the limitation the "
         "inflatable concept of the following section removes."),
        (411, "Figure for HIAD/LOFTID.",
         "The Low-Earth Orbit Flight Test of an Inflatable Decelerator, showing a "
         "stack of inflated toroidal rings at the centre of a rigid, stowable "
         "carrier. Each ring is a pressure-supported structural member, so the "
         "package is thin enough to fold inside the carrier and wide enough to "
         "deploy to a diameter of about 3~m."),
        (531, "Figure for Shock-Boundary Layer Interaction (SBLI) or (SWBLI) on Rough Surfaces.",
         "Shock and boundary-layer interaction over a rough surface. The separated "
         "boundary layer thickens where the shock stands off from the surface and "
         "thins where the shock reattaches, so the near-wall heating is "
         "redistributed rather than simply scaled. Scalloping produces exactly "
         "this redistribution, which is why the toroid crests of this vehicle are "
         "treated as secondary stagnation regions."),
        (560, "Figure for Recirculation Zones and Stagnation Valleys Example on different scenarios.",
         "Recirculation in the valleys between adjacent toroids, shown for "
         "several inflow conditions. Each toroid casts a separated shear layer "
         "into the valley behind it, producing a trapped recirculating region in "
         "which the flow is slow and poorly swept; the pockets between toroids "
         "are therefore regions of both reduced convective heating and increased "
         "backface temperature, which Chapter~\\ref{ch:results} quantifies."),
        (605, "Figure for Localized Peak Heating Effects in Amplification but through Osicaltion.",
         "Localized amplification of peak heating. Where a shock impinges on the "
         "cusp formed by the transition between two toroids, the local curvature "
         "is small and the heating scales as the inverse square root of that "
         "curvature, so a modest change in surface radius produces a "
         "disproportionate increase in local heat flux at the crest."),
    ]
    lines = CH2.read_text(encoding="utf-8").split("\n")
    for lineno, old, new in stubs:
        i = lineno - 1
        if i >= len(lines) or old not in lines[i]:
            print(f"  !! ch2 caption at line {lineno} no longer matches: {old[:50]!r}")
            ok = False
            continue
        lines[i] = f"    \\caption{{{new}}}"
        print(f"  ok  ch2 caption line {lineno} rewritten")
    CH2.write_text("\n".join(lines), encoding="utf-8")

    print("\nALL APPLIED" if ok else "\nSOME ITEMS FAILED (see !! above)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
