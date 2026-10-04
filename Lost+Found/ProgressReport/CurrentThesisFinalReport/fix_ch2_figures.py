#!/usr/bin/env python3
"""Repair two Chapter 2 figures whose captions assert more than the artwork
shows, and remove a figure printed twice.

DEFECT 1 -- FIGURE 2.18 (figures/cp_temperature_nasa.png)
----------------------------------------------------------------------------
The artwork was inspected directly. What it actually contains:

  * x-axis "Temperature T [K]", 0 to 6000.
  * y-axis "Specific Heat Cp [kJ/(kg*K)]", 1.0 to 2.4.
  * a solid "NASA Polynomial (Thermally Perfect)" curve that FALLS from about
    1.00 and STOPS at roughly 1300 K, leaving the region from 1300 to 6000 K
    empty apart from a second dashed "Calorically Perfect (Cp = 1004.5)" line
    and a shaded band between the two;
  * a dotted vertical marker labelled "Vibrational excitation onset,
    Theta_v ~ 800 K";
  * a second dotted vertical marker labelled "HIAD re-entry peak temperature"
    at roughly 2000 to 2100 K.

Two claims in the old caption are not supported by that artwork:

  (a) "The vibrational excitation onset near 800 K marks the transition where
      the CPG assumption becomes invalid for hypersonic flow calculations."
      The 800 K marker is a bare annotation. The curve shows no visible feature
      there: it is essentially flat from 0 to about 1000 K, and cp of air is
      still within a few per cent of 1004.5 J/(kg*K) well above 800 K. The
      figure does not demonstrate a transition and the caption should not say
      it does.

  (b) The artwork's own "HIAD re-entry peak temperature" marker sits at about
      2000 K. This thesis computes the calorically perfect stagnation
      temperature as 5952 K, from
          T_0 = T_inf (1 + (gamma-1)/2 M^2)
              = 268.41 (1 + 0.2 x 105.9) = 5952 K
      (chapter_4_results.tex). The marker in the imported figure therefore
      contradicts the thesis by a factor of nearly three, and a reader who
      trusts the artwork would read the wrong number.

The caption is rewritten to state what is plotted, to say plainly that the
imported curve is drawn only over its low-temperature range, and to record that
the 2000 K annotation is not the value used here. The 800 K onset is retained
as a fact about vibrational excitation, attributed to the source of the
correlation rather than claimed to be visible in the plot.

DEFECT 2 -- FIGURES 2.11 AND 2.22 ARE THE SAME ARTWORK
----------------------------------------------------------------------------
figures/scalloped_wall_flow.png is included twice, at chapter 2 lines 511 and
1352, under two labels, and the two captions make different and mutually
inconsistent claims about the same picture:

  2.11  "... The trapped vortex mechanism in the valleys provides thermal
         shielding of the valley floor from the freestream."   (no vortex is
         drawn anywhere in the artwork)
  2.22  "... leading to boundary layer separation, recirculation zones, and
         localized peak heating amplification at toroid crests." (none of
         those three are drawn; the picture shows pressure gradient, flow
         acceleration over crests and deceleration in valleys)

Printing one diagram twice under two numbers with two contradictory captions is
a defect a reviewer will notice immediately. The second float is replaced by a
cross-reference, and the crest/valley explanation it carried is kept as prose so
no content is lost.

CITATION
  Anderson, J. D., Hypersonic and High-Temperature Gas Dynamics, 2nd ed.,
  AIAA, 2006 -- already cited as AndersonHypersonic in the same section.
"""

from __future__ import annotations

from pathlib import Path

TH = Path(__file__).resolve().parent
CH2 = TH / "chapter_02_literature_review.tex"


def swap(t: str, old: str, new: str, tag: str) -> tuple[str, bool]:
    n = t.count(old)
    if n != 1:
        print(f"  !! {tag}: expected 1 match, found {n}")
        return t, False
    print(f"  ok  {tag}")
    return t.replace(old, new, 1), True


FIG218_OLD_ALT = (
    r"    \BeginAccSupp{method=escape,ActualText={Plot of the specific heat "
    r"capacity of air against temperature, comparing the constant "
    r"calorically-perfect-gas value with the NASA polynomial fit for a "
    r"thermally perfect gas; vibrational excitation begins near 800 kelvin.}}%"
)
FIG218_NEW_ALT = (
    r"    \BeginAccSupp{method=escape,ActualText={Plot of the specific heat "
    r"capacity of air against temperature. The vertical axis runs from 1.0 to "
    r"2.4 kilojoules per kilogram kelvin and the horizontal axis from 0 to 6000 "
    r"kelvin. A solid curve labelled NASA Polynomial, Thermally Perfect, starts "
    r"near 1.0, falls slightly and stops at roughly 1300 kelvin, so the region "
    r"above 1300 kelvin is empty apart from a horizontal dashed line labelled "
    r"Calorically Perfect at 1004.5 joules per kilogram kelvin and a shaded "
    r"band between the two. Two vertical dotted markers are drawn: one at about "
    r"800 kelvin labelled vibrational excitation onset, and one at about 2000 "
    r"kelvin labelled HIAD re-entry peak temperature.}}%"
)

FIG218_OLD_CAP = (
    r"    \caption{Specific heat capacity $C_p(T)$ for air as a function of "
    r"temperature. The horizontal line represents the calorically perfect gas "
    r"(CPG) assumption ($C_p = \text{const.}$), while the curve shows the NASA "
    r"polynomial fit for the thermally perfect gas (TPG) model. The vibrational "
    r"excitation onset near 800~K marks the transition where the CPG assumption "
    r"becomes invalid for hypersonic flow calculations.}"
)
FIG218_NEW_CAP = (
    r"    \caption{Specific heat capacity $C_p(T)$ for air against temperature, "
    r"contrasting the calorically perfect gas assumption (CPG, $C_p = "
    r"\text{const.}$) with the NASA polynomial fit for the thermally perfect gas "
    r"(TPG). Two limitations of the imported artwork are recorded here rather "
    r"than left for the reader to discover. First, the TPG curve is drawn only "
    r"over roughly the range 0 to 1300~K, so the plot shows nothing about the "
    r"high-temperature behaviour for which the thermally perfect model exists; "
    r"the caption previously claimed that the vibrational excitation onset near "
    r"800~K was visible in the figure and marked the point where the CPG "
    r"assumption fails, and the figure does not in fact show a feature there. "
    r"The onset itself is real and is taken from the source correlation, but it "
    r"is an annotation rather than a resolved feature of this plot. Second, the "
    r"vertical marker in the artwork labelled ``HIAD re-entry peak "
    r"temperature'' sits at about 2000~K, which is not the value used "
    r"anywhere in this work: the calorically perfect stagnation temperature "
    r"computed in Chapter~\ref{ch:results} is 5952~K, before any reduction for "
    r"vibrational excitation and dissociation. The marker belongs to the source "
    r"of the imported figure and is disregarded here.}"
)

FIG222_OLD = (
    r"\begin{figure}[htbp]" "\n"
    r"    \centering" "\n"
    r"    \BeginAccSupp{method=escape,ActualText={Schematic of hypersonic flow "
    r"over a periodic scalloped surface, showing the bow shock forming over "
    r"each crest and the separated recirculating flow in each valley between "
    r"crests.}}%" "\n"
    r"\includegraphics[width=0.9\textwidth]{figures/scalloped_wall_flow.png}%" "\n"
    r"\EndAccSupp{}%" "\n"
    r"    \caption{Schematic of hypersonic flow over the scalloped HIAD surface. "
    r"The periodic toroidal bladder geometry creates alternating favorable "
    r"($dp/dx < 0$, flow acceleration at crests) and adverse ($dp/dx > 0$, flow "
    r"deceleration in valleys) pressure gradients, leading to boundary layer "
    r"separation, recirculation zones, and localized peak heating amplification "
    r"at toroid crests.}" "\n"
    r"    \label{fig:scalloped_wall_flow_parametric}" "\n"
    r"\end{figure}"
)
FIG222_NEW = (
    r"% Figure~\ref{fig:scalloped_wall_flow} is not reprinted here. The same "
    r"artwork, figures/scalloped_wall_flow.png, appeared a second time under "
    r"this label with a caption that contradicted the first: it claimed "
    r"boundary layer separation, recirculation zones and localized peak heating "
    r"amplification, none of which the drawing contains, while the Chapter 2 "
    r"figure claimed a trapped vortex that the drawing also does not contain. "
    r"One diagram, one number, one caption." "\n"
    r"The crest-and-valley pressure gradient described in "
    r"Figure~\ref{fig:scalloped_wall_flow} is created by the periodic toroidal "
    r"bladder geometry itself. The surface is convex over each toroid crown, so "
    r"the inviscid flow accelerates there and the static pressure falls "
    r"($dp/dx < 0$); the surface is concave in each gap between crowns, so the "
    r"flow decelerates and the pressure rises ($dp/dx > 0$). It is that adverse "
    r"gradient acting on a boundary layer already thickened by the heating of "
    r"the preceding gap which makes separation possible, and it is the crest "
    r"regions that are treated as secondary stagnation points in "
    r"Chapter~\ref{ch:results}. This is a statement about the flow physics, not "
    r"a reading of features in the figure, and the figure is not cited as "
    r"evidence for the separation itself."
)


def main() -> int:
    t = CH2.read_text(encoding="utf-8")
    rc = 0

    for old, new, tag in ((FIG218_OLD_ALT, FIG218_NEW_ALT, "Fig 2.18 alt text"),
                          (FIG218_OLD_CAP, FIG218_NEW_CAP, "Fig 2.18 caption"),
                          (FIG222_OLD, FIG222_NEW, "Fig 2.22 duplicate float")):
        t, ok = swap(t, old, new, tag)
        rc |= 0 if ok else 1

    if rc == 0:
        CH2.write_text(t, encoding="utf-8")
        print("\n  chapter_02_literature_review.tex updated")
    else:
        print("\n  NOT WRITTEN (an anchor failed); file left unchanged")

    # Prove the artwork is now included exactly once. Count \includegraphics
    # lines only: the first version of this check counted every mention of the
    # filename and therefore also counted the explanatory comment added above,
    # reporting two includes when there is one.
    t = CH2.read_text(encoding="utf-8")
    n = sum(1 for ln in t.split("\n")
            if "\\includegraphics" in ln and "scalloped_wall_flow.png" in ln)
    print(f"  scalloped_wall_flow.png now included {n} time(s)")
    if n != 1:
        rc = 1
    if "\\ref{fig:scalloped_wall_flow_parametric}" in t:
        print("  !! a dangling \\ref{fig:scalloped_wall_flow_parametric} remains")
        rc = 1
    else:
        print("  ok  no dangling reference to the removed label")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())