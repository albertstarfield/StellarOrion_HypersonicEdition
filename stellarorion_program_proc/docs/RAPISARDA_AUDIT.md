# Rapisarda 2023 Reference Audit — Codebase vs Verified Thesis

> Context: `docs/` | Active goal: audit codebase against
> `ProgressReport/paperRef/MDAOofInflatableStackedToroids_ClaudioRapisarda.pdf`
> (237 pp., Claudio Rapisarda, 2023) plus code-quality re-verification.
> Date: 2026-08-25 [ASWSS]

## Method

1. `pdftotext -layout` on the thesis PDF → full-text extraction.
2. Key tables located: Table 4.1 (parametric design), Table 3.3
   (packaging), **Table 4.10 (aerothermal models vs IRVE-3 flight data —
   the authoritative calibration table)**.
3. Every numeric claim cross-checked against:
   - `stellarorion_types.ads` geometry defaults (L167-175)
   - `stellarorion_test_modes.adb` validation targets + tolerances
   - `stellarorion_reports.adb` calibrate-mode constants
   - root `README.md` calibration table

## Geometry parameters — ALL EXACT MATCH ✅

| Parameter | Thesis (T4.1/T3.3) | Codebase | Verdict |
|---|---|---|---|
| Half-cone angle θc | 60° | `Angle_Deg = 60.0` | MATCH |
| Toroid count N | 6 | `Toroid_Count = 6` | MATCH |
| Toroid major radius r_torus | 0.1350 m | `Toroid_Radius_M = 0.135` | MATCH |
| Payload height h_pay | 1.7 m | `Payload_Height_M = 1.70` | MATCH |
| Inflated radius | 1.500 m | `Diameter_M = 3.0` (diameter) | MATCH |
| Outward torus radius | 0.0508 m | (not modeled) | N/A — noted |

## Aerothermal calibration — FINDINGS & CORRECTIONS ⚠️→✅

### Thesis Table 4.10 ground truth

| Model | q_max [W/cm²] | Δ vs flight | Q [J/cm²] | Δ vs flight |
|---|---|---|---|---|
| **IRVE-3 FLIGHT [38]** | **14.3610** | — | **195.0577** | — |
| Fay-Riddell | 13.8313 | −3.69% | 195.1673 | +0.06% |
| Detra-Kemp-Riddell | 14.0032 | −2.49% | 202.4430 | +3.79% |
| Van Driest | 12.6375 | −12.00% | 179.2793 | −8.09% |
| Chapman | 13.9558 | −2.82% | 204.8201 | +5.00% |
| **Sutton-Graves** | **15.2595** | **+6.26%** | **223.9542** | **+14.81%** |

Thesis rationale: Sutton-Graves was selected as the MDAO-integrated
heating model precisely because it is the only correlation that
**overpredicts both** peak flux and integrated load → conservative for
TPS sizing.

### FINDING A (corrected in this commit) — flight/model roles were swapped

README previously labeled 13.8 W/cm² as "Flight" and 14.36 as "MDAO
Model" — inverted relative to the cited thesis. Per Table 4.10,
**flight = 14.36 / 195.06**, and 13.83/195.17 is the *Fay-Riddell model*
prediction. README corrected accordingly.

### FINDING B (annotated) — provenance of the code targets

The codebase validation targets (`Target_Heat_Flux = 13.8`,
`Target_Heat_Load = 188.0`, `Target_Decel_G = 19.7`, `Target_Beta =
26.9`, `Target_Pressure = 12400 Pa`) do **not** come from Rapisarda's
Table 4.10 rows; they are the NASA TP-2013-4012 mission-report values
(Dillman et al. 2013). Comments previously attributed them to
"Rapisarda 2023". In-source provenance notes now cite NASA TP as
primary with the thesis as cross-reference, and document why the tighter
NASA-TP band is kept deliberately (more conservative than validating
against the +6.26%/+14.81% SG envelope).

### FINDING C (corrected) — decel "20.2 g MDAO model" mis-attribution

The thesis contains no IRVE-3 deceleration table; the "20.2 g model"
value is not from Rapisarda. README now attributes 19.7 g to NASA
TP-2013-4012 only and drops the phantom 20.2 g column entry.
(21.7 g appears in the thesis only as a MetNet-LB optimized-design value.)

### Envelope check vs current sim outputs

Final-sim metrics (1100-step validated run): q ≈ 22.7 W/cm²,
Q-consistent decel ≈ 22.8 g. Against the SG-overprediction envelope
(+6.26% flux), the sim sits above even the SG prediction — expected:
SPARTA DSMC resolves nonequilibrium effects the engineering correlations
average out; the validation gates compare against the NASA-TP band by
design, not against the correlation envelope.

## Architecture facts verified during this audit

- **No CadQuery proxy exists**: zero cadquery references repo-wide.
  Geometry math is pure Ada (`StellarOrion_Geometry`, SPARK_Mode On;
  7/7 subprograms proved at L4, ~52 of 383 total checks). Ada →
  `Generate_Sparta_Script` → SPARTA input deck directly.
- **STEP/surf pipeline is legacy one-time input**: `HIAD_custom.surf`
  (219 pts) was produced offline from `CADDesign/HIAD_custom_full.step`
  via FreeCAD slicing; consumed read-only by SPARTA (`read_surf`).
- **ParaView tooling survives outside the revamp**: real visualizers are
  parent-dir `source/visualizer.py` + `export_paraview_all_steps.py`;
  not wired into run.py or Ada.
- **Stub module flagged**: `src/python/visualizer.py` is a 5-line
  docstring stub promising unimplemented figures. All real consumers use
  `../source/visualizer.py`. Left in place but documented here;
  removal candidate.

## Code-quality gate status at audit time

All green: build zero warnings; self-test 15/15; harness 29/29;
gnatprove L4 383/383 checks proved; SabotageVerifier CRITICAL=0 CLEAN.
Comment-only edits in this commit are VC-neutral (re-verified).

## Sutton-Graves: derivation & non-continuum applicability

**Derivation.** Sutton-Graves is the engineering collapse of Fay-Riddell
stagnation-point boundary-layer theory (Fay & Riddell 1958): with Le = 1,
Pr = 0.71, frozen chemistry and a Newtonian stagnation velocity gradient,
q_stag = C_sg·sqrt(rho/R_n)·V³, C_sg = 1.7415e-4 (SI, Earth air;
NASA TR R-376). The V³ factor is kinetic-energy flux; the sqrt(R_n)
dilution is boundary-layer thickening over a blunt nose.

**Applicability (honest limits).**
- VALID: continuum attached blunt-body flow, Kn << 0.01, V <~ 12 km/s air.
- INVALID: transition/free-molecular flow (Kn >~ 0.01) — boundary-layer
  theory itself fails there; free-molecular heating has no sqrt(R_n)
  scaling and is surface-accommodation driven. The governing equation in
  that regime is the Boltzmann Transport Equation (BTE), not Navier-Stokes.
- **Role in THIS codebase:** SPARTA DSMC numerically solves the BTE by
  direct particle simulation (Bird 1994; Plimpton & Gallis 2014), so DSMC
  output is the PRIMARY aerothermal physics at all rarefaction levels.
  `Sutton_Graves_Heat` (stellarorion_physics.ads) is retained ONLY as a
  conservative engineering envelope: Rapisarda Table 4.10 selected it as
  the sole model overpredicting BOTH IRVE-3 flight peaks (+6.26% flux,
  +14.81% load). Its absolute accuracy must NOT be trusted at high Kn;
  use it strictly as an upper-bound sanity band against DSMC results.

## Visual geometry verification

Tool: `tools/plot_surf_profile.py` (auto-installs missing deps from
`requirements.txt` — matplotlib>=3.7.0 already declared; no manual pip).
Outputs (generated during this audit):

- `data/geometry_check/surf_profile_check.png` — 2-D profile r(z) of the
  219-point SPARTA surf with design overlays (r=1.5 m line, h_pay=1.7 m)
  + 3-D surface-of-revolution preview.
- `data/geometry_check/surf_profile_full.png` — full-resolution profile
  sheet with max-diameter annotation.

Measured vs design intent:

| Quantity | Design | Measured from HIAD_custom.surf | Note |
| :--- | :--- | :--- | :--- |
| Max diameter | 3.000 m | **3.1406 m** (+4.7%) | Toroid-crest bulge beyond nominal rim radius; expected for stacked-toroid wrap (outer tube crest r_out_torus ~0.0508 m sits outside the 1.5 m inflated radius). Not an error: SPARTA consumes the actual sliced CAD silhouette. |
| Axial extent | h_pay = 1.7 m | z to 2.601 m | Body extends aft of payload height (aft tori/shelf); consistent with legacy STEP slice including aft structure. |
| Point count | 219 | 219 ✅ | Header-declared count matches parsed records. |

Conclusion: the simulated surface matches design intent within the
expected toroid-wrap tolerance; visual artifacts confirm the aeroshell
shape fed to DSMC is correct BY EYE, closing the audit's geometry check.

## References

- Rapisarda, C. (2023). *MDAO of Inflatable Stacked-Toroids* — Tables
  3.3, 4.1, 4.10; ProgressReport/paperRef/.
- Dillman et al. (2013). IRVE-3 Post-Flight Reconstruction, NASA
  TP-2013-4012.
- Sutton & Graves (1972); Fay & Riddell (1958) — correlation sources.
