# CITATIONS — StellarOrion HypersonicEdition

> Master reference list. In-code citation tags (e.g. `[Rap23]`, `[TR-376]`)
> resolve to the entries below.

## Aerothermodynamics & entry physics

* **[TR-376]** Sutton, K. & Graves, R. A., *"A General Stagnation-Point
  Convective Heating Equation for Arbitrary Gas Mixtures"*, NASA TR R-376,
  1972. — Source of the Sutton–Graves coefficient `C_SG = 1.7415e-4`
  (Table 1) and the stagnation heating law used in
  `Sutton_Graves_Heat`.
* **[US76]** U.S. Standard Atmosphere, 1976, NOAA/NASA/USAF.
  — Layer structure and lapse rates of the ISA model implemented in
  `stellarorion_environment.adb` (troposphere → mesosphere + exponential tail).
* **[ISA]** International Standard Atmosphere, ISO 2533:1975.
  — Temperature/density profile bands (E1/E2 axioms: 186.87–288.15 K).

## Rarefied gas dynamics

* **[Bird94]** Bird, G. A., *"Molecular Gas Dynamics and the Direct
  Simulation of Gas Flows"*, Oxford University Press, 1994.
  — Mean-free-path formula λ = 1/(√2·π·d²·n) (A1/A2), Knudsen-number
  regime classification (K1/K2), continuum/free-molecular transition.
* **[Plimpton2014]** Plimpton, S. & Gallis, M., *SPARTA*
  (Stochastic PArallel Rarefied-gas Time-accurate Analysis), 2014.
  — The external DSMC solver bridged by `stellarorion_sparta.adb`
  (SPARK_Mode Off subprocess/Docker bridge).

## Design references

* **[Rap23]** Rapisarda, V., *"Multidisciplinary Design Analysis and
  Optimization of HIAD"*, Ph.D. thesis, 2023.
  — Table 5.4 design-variable ranges mirrored by AXIOM G2/G3 and the
  geometry subtypes: Diameter [0.5, 15] m, cone half-angle [40, 80]°,
  Toroid_Count ≤ 12.
* **[IRVE3]** NASA Inflatable Reentry Vehicle Experiment3 mission data.
  — Reference entry state (~Mach 25, apogee ≈ 10 km) used in envelope and
  self-test arguments.
* Mission headroom anchors: LOFTID (~6 m radius HIAD), Venus-surface
  density (~65 kg/m³) for Q1/S1 envelopes.

## Constants

* **[CODATA]** CODATA 2018 recommended values (https://physics.nist.gov).
  — Stefan–Boltzmann constant σ = 5.670374419e-8 W/(m²·K⁴),
    Avogadro N_A = 6.02214076e23 mol⁻¹, molar mass of air M = 28.97e-3 kg/mol.

## Software assurance

* **[STD]** IEEE Std 1364-style parity conventions / classic even–odd
  parity detection theory (single-bit error detection at data boundaries)
  — basis of the Atomic_Parity package contract shape mandated by the
  project code-quality standard ("Atomic Parity Check & Recovery").
* **[HAM]** Hamming, R. W., *"Error Detecting and Error Correcting Codes"*,
  Bell System Technical Journal, 1950. — Parity/checksum lineage behind P1/P2
  and the XOR-fold block checksum.
* **[DO178C]** RTCA DO-178C / ED-12C, *Software Considerations in Airborne
  Systems and Equipment Certification*, 2011. — Recovery-strategy and
  traceability discipline referenced by the watchdog recovery matrix.
* **[SPARK]** SPARK 2014 Reference Manual & GNATprove User's Guide
  (AdaCore; sources mirrored at github.com/AdaCore/spark2014).
  — Contract/aspect semantics (`Pre`/`Post`/`Loop_Invariant`/
  `pragma Annotate` justification syntax), proof effort levels.
* **[IEEE754]** IEEE Std 754-2019, *Floating-Point Arithmetic*.
  — Single-precision bounds underpinning every overflow-proof comment
  (Float'Last ≈ 3.4028235e38, Model_Small ≈ 1.18e-38).

## Tooling

* Alire / GNAT FSF 16.1.0 toolchain (gnat_native_15.1.2_60748c54 build);
  gnatprove 16.1.0 with alt-ergo/cvc5/z3 backends via gnatwhy3.
* Sabotage verifier adapted from the Zephy-project audit pipeline
  (`src/utils/sabotage_verifier.py`; provenance file preserved at repo root).

---

*When adding an axiom or theory, add its source here and use the bracketed
tag consistently in code comments.*
