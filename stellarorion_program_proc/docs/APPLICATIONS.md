# APPLICATIONS — StellarOrion HypersonicEdition

> Where the axioms and theories (see `AXIOMS.md` / `THEORIES.md`) are
> applied at concrete sites in the codebase, and how each application is
> verified.

---

## AP-1. Structural envelope enforcement via subtypes (types.ads)

`Velocity_Range`, `Density_Range`, `Mass_Kg_Range`, `Diameter_Range`,
`Nose_Radius_Range`, `TPS_Density_Range`, `TPS_Cp_Range`,
`TPS_Emissivity_Range`, `TPS_Thickness_Range` mirror the physics Pres
(Q1/Q2/B1/T3/G2) **structurally**: any value stored in a record component
of these subtypes satisfies the corresponding Pre by construction — the
prover needs no extra argument at call sites.

Application sites: `Flight_Parameters.Velocity_Ms/Density_Kgm3`,
`Geometry_Parameters.Diameter_M/Nose_Radius_M/Mass_Kg`,
`TPS_Material.Density/Cp/Emissivity/Thickness`.

Deliberate exceptions:
* `Angle_Deg` left unconstrained so `Validate_Geometry` keeps rejecting
  out-of-table inputs (rejection-path testing stays armed; self-test
  exercises Angle = 39).
* `Simulation_Results.*` / `Flight_Metrics.*` components left unconstrained:
  defaults of 0.0 must stay legal and SPARTA dumps arbitrary values.

## AP-2. CLI chokepoint clamping (project.adb)

Single read site for `--mach`/`--alt`/`--altitude` funnels through
`Clamp_Float(Get_Float(...), Lo, Hi)` into E1/E2 envelopes before any
environment call can occur. Geometry CLI overrides (`--diameter`, `--nose`,
`--mass`) and TPS overrides (`--tps-density`, `--tps-cp`, emissivity) are
clamped likewise to their subtype bounds. Because project.adb is
SPARK_Mode Off, tightening function Pres creates zero new proof
obligations there — but runtime checks still fire, hence clamping at the
source (Murphy's Law).

## AP-3. Composite output clamps (physics.adb)

Where an analytic Post ceiling was unprovable without re-inlining helper
loops (Sutton-Graves), the caller clamps: `Stag_Q := Float'Min (Stag_Q,
2.0e15)` restores exactly the ceiling required by the downstream
Radiative/Backface Pres. Analytic max is 1.7415e15, so the clamp is a
no-op inside the physical envelope and only guards pathological inputs.

## AP-4. Guarded fallbacks at chain seams

* Ballistic coefficient: if SPARTA reports zero drag (< 1e-6 floor), β := 0
  instead of dividing.
* Mean free path: if number density < 5e13 (deep free-molecular regime),
  MFP saturates at 1e9 m (Knudsen Post-compatible) instead of forcing the
  bounded formula.

## AP-5. History CSV sanitisation (history.adb)

Fields parsed from restart/CSV rows (velocity, density, diameter, nose
radius, mass) pass through inline `Float'Min/Float'Max` clamps before
assignment to subtype components — corrupt rows are sanitised rather than
crashing on range checks.

## AP-6. GA sampling bounds (optimization.ads)

Design-variable bounds Dia[0.5,15], Ang[40,80], Nos[0.01,1], TRad[0.01,0.5],
Mass[10,1000] all sit strictly inside the A3b subtypes, so `Uniform_Rand`
writes can never violate a component constraint at runtime.

## AP-7. Self-test wiring (project.adb Run_Self_Test)

Tests 14 (parity roundtrip + single-bit corruption detection + recovery)
and 15 (watchdog starvation → degradation → failure → cross-recovery →
emergency latch) exercise T-6/T-7 in the production binary;
banner counts updated 13→15 tests. Independent harness
(`tests/test_main.adb`, 29 checks) covers deeper cases including boundary
values sitting exactly on subtype bounds.

## AP-8. Pipeline gates (scripts/)

| Gate | Command | Criterion |
|------|---------|-----------|
| Build | `alr clean && alr build` | exit 0, zero Ada warnings (-gnatwa); only benign clang deployment-version notices remain (documented GPR KNOWN EXCEPTION) |
| Proof | `scripts/prove.sh skip --level=4 --report=all --timeout=180` | "Success: all checks proved", 0 medium/high |
| Sabotage audit | `scripts/SabotageVerifier.sh` | CRITICAL = 0 |
| Self-test | `./bin/main --self-test` | All 15 tests PASSED |
| Unit harness | `alr exec -- gprbuild -P tests/stellarorion_tests.gpr -j0 && ./bin/test_main` | 29/29 PASS |

Final acceptance order: all gates green → simulation validation exec at
1100 steps runs LAST.

## AP-9. Known documented exceptions

* clang `-Woverriding-deployment-version` (~5–11×): emitted by gprbind's
  internal toolchain clang against the Xcode SDK; not controllable via GPR
  switches; upward override, harmless. Documented in the GPR Linker comment.
* `-gnatdAME` representation-information listing ("passed by copy"):
  informational compiler output, not diagnostics.
