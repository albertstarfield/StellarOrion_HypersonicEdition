# Flowchart revision v2 — recommendation and rationale

## What changed
- Removed the duplicate validation diamond "Replicate Axisymmetric Slice Model Design?" and its "Adjustment Needed" feedback loop. Model replication is folded into the "Data Retrieval and Familiar Study Collection" stage as a sub-step ("replicate axisymmetric slice; adjust if replication fails").
- Added a "Survivability Optimization (Genetic Algorithm)" stage between the simulation-validity decision and "Data Analysis Simulation".
- Retained a single validation gate: "Theoretically valid? or within error range?" with its "Invalid" feedback loop to the simulation stage.
- Stage order now matches the five primary stages enumerated in the thesis (chapter 3): parametric geometry -> DSMC setup -> simulation -> optimization -> validation/analysis.

## Why (owner notes)
- Slide 5 note: "Duplicate detected on Theoretically Valid, thus remove from here"; "Optimization Pipeline before Data Analysis Simulation".
- Slide 6 note: "Stage Missing on the flowchart"; "Duplicates on Slide 5 Stage 5 and Stage 4 (swap)".
- Thesis enumerates five stages including "Survivability Optimization", which the old flowchart omitted.

## Alternatives considered
1. Keep both validation diamonds but relabel them (model replication vs. simulation validity). Rejected: the owner explicitly called the second a duplicate and the first is a setup check, not a separate stage; keeping it inflates the diagram without information.
2. Remove the simulation-validity diamond instead. Rejected: the "Invalid -> re-simulate" loop is the only iteration that feeds solver results back, which the thesis relies on for the validation gate.
3. Add optimization after Data Analysis. Rejected: contradicts the owner's "Optimization Pipeline before Data Analysis Simulation" and the thesis stage order.

## Files
- Generator: figures/make_flowchart.py (v2); backup of v1 at ../CurrentThesisFinalReport/figures/make_flowchart_v1_backup.py
- Output: figures/thesis_flowchart.png (1760x3600), figures/thesis_flowchart_halves.png (3600x1863)
- Thesis: CurrentThesisFinalReport/figures/flowchart.png regenerated; chapter_03_methodology.tex caption/ActualText updated.
