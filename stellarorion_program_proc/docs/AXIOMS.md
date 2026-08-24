# AXIOMS — StellarOrion HypersonicEdition

> Consolidated register of every axiom stated in the Ada/SPARK sources
> (`src/simulation_engine/`). Per the code-quality standard, all
> implementations derive from axioms first; each axiom below is also
> documented in-place next to the contract it justifies.
>
> Envelope philosophy: every float input is constrained to a physical
> envelope chosen so that (a) all real missions of interest are covered with
> margin and (b) every intermediate result stays far inside IEEE-754 single
> precision (`Float'Last ≈ 3.40e38`, `Float'Model_Small ≈ 1.18e-38`).

---

## 1. Physics (`stellarorion_physics.ads`)

### Mean_Free_Path
| Axiom | Statement | Rationale |
|-------|-----------|-----------|
| **A1** | number density n ∈ [5e13, 1e30] m⁻³ | thermosphere at 500 km ≈ 3e14; floor keeps λ bounded |
| **A2** | molecular diameter d ∈ [1e-10, 1e-6] m | air ≈ 3.7e-10; helium 2.6e-10; large organics ≈ 1e-9 |

### Knudsen_Number
| Axiom | Statement | Rationale |
|-------|-----------|-----------|
| **K1** | MFP ∈ [0, 1e9] m | discharged by `Mean_Free_Path`'s Post at the sole call site; interplanetary limit ≈ 4.5e8 m |
| **K2** | Char_Length ≥ 1e-3 m | vehicle scale, millimetre floor |

### Dynamic_Pressure
| Axiom | Statement | Rationale |
|-------|-----------|-----------|
| **Q1** | ρ ∈ [0, 1e4] kg/m³ | Venus surface ≈ 65; 1e4 margin |
| **Q2** | V ∈ [0, 1e5] m/s | Earth escape 11.2e3; solar-system entry worst case ≈ 7e4; 1e5 margin |

### Ballistic_Coefficient
| Axiom | Statement | Rationale |
|-------|-----------|-----------|
| **B1** | m ∈ (0, 1e7] kg | largest launch vehicles ≈ 1e6 |
| **B2** | q ∈ [0, 1e14] Pa | WIDENED in A3b: within the input subtypes Dynamic_Pressure legitimately reaches 5.0e13; former 1e6 ceiling was unreachable-by-proof and contradicted the caller chain |
| **B3** | F_drag ∈ [1e-6, 1e18] N | WIDENED in A3-final: analytic drag estimators legitimately reach ~2.5e17; floor avoids division blowup (β = m·q/F decreases in F, so widening is overflow-neutral) |

### Sutton_Graves_Heat
| Axiom | Statement | Rationale |
|-------|-----------|-----------|
| **S1** | ρ ∈ (0, 1e4] kg/m³ | as Q1 |
| **S2** | R_n ∈ [1e-4, 100] m | sounding probes ~1 cm to HIAD |
| **S3** | V ∈ [0, 1e5] m/s | as Q2 |

### Radiative_Eq_Temp
| Axiom | Statement | Rationale |
|-------|-----------|-----------|
| **R1** | q ∈ [0, 2e15] W/m² | WIDENED in A3b: Sutton-Graves legitimately reaches 1.75e15 within its input envelope; former 1e9 ceiling contradicted that chain |
| **R2** | ε ∈ [1e-3, 1] | emissivity of engineered TPS surfaces |

### Backface_Temperature
| Axiom | Statement | Rationale |
|-------|-----------|-----------|
| **T1** | T_init ∈ [0, 3000] K | soak-back ceiling of stack |
| **T2** | q ∈ [0, 2e15] W/m² (widened per R1); dt ∈ [0, 1e4] s (2.8 h pulse); η_lag ∈ (0, 1] | |
| **T3** | ρ_TPS ∈ [10, 1e4] kg/m³ (aerogel ≈ 10; C-C ≈ 1600); Cp ∈ [100, 1e4] J/(kg·K); thickness ∈ [1e-4, 1] m | mirrors `TPS_*` subtypes in types.ads |

### Deceleration_G_Load
| Axiom | Statement | Rationale |
|-------|-----------|-----------|
| **D1** | F_drag ∈ [0, 1e18] N | widened per B3 chain |
| **D2** | m ∈ [1e-3, 1e7] kg | gram-scale probe to super-heavy |

### Density_From_Number
Same n range as A1.

---

## 2. Geometry (`stellarorion_geometry.ads`)

| Axiom | Statement | Rationale |
|-------|-----------|-----------|
| **G1** | Frontal_Area radius envelope Y_max ∈ [1e-6, 1e3] m | Lower bound: below Y_max ≈ 2.3e-23 the square underflows Float to exactly 0.0, breaking Post (> 0); 1e-6 keeps Y² ≥ 1e-12 ≫ Model_Small. Upper: LOFTID ≈ 6 m radius; 1e3 gives >100× headroom. |
| **G2** | Diameter ∈ [0.5, 15.0] m; Angle_Deg ∈ [40.0, 80.0]; Toroid_Radius ∈ (0, 5] m; TPS_Thickness ∈ (0, 1] m; TPS_Density ∈ [10, 1e4] kg/m³ | Rapisarda 2023 Table 5.4 mirrors + Taylor-trig validity band (the former [0,180]° Pre admitted angles where the series degrade silently) |
| **G3** | Diameter ∈ [0.5, 15.0]; Toroid_Radius ∈ (0, 5]; Num_Toroids ≤ 12 (lower bound = Positive subtype); Density ∈ [10, 1e4] kg/m³ | Rap23 Tab 5.4 + GA-bound headroom |

---

## 3. Environment (`stellarorion_environment.ads/.adb`)

| Axiom | Statement | Rationale |
|-------|-----------|-----------|
| **E1** [ISA] | Mach ∈ [0, 50]; Temperature ∈ [1, 3000] K | IRVE-3 entry ≈ M25; escape velocity at sea level ≈ M50.2; ISA profile 186.87–288.15 K plus hot-wall recovery headroom |
| **E2** [ISA] | Altitude ∈ [0, 500] km; Temperature Post band [186.86, 288.15] K | ISA definition (layered + exponential tail); post band proved branch-by-branch by interval arithmetic |
| **E3** | Mach_Alt_To_Flight inherits E1+E2 envelopes; body clamps outputs to Velocity_Range/Density_Range | CLI chokepoint clamps --mach/--alt before any call |
| **E4** | MSIS_Atmosphere altitude envelope mirrors E2 | dead ISA-fallback placeholder (NRLMSIS 2.1 needs Python sidecar); contract declared for future wiring |
| **E5** | Exp_Approx argument \|X\| ≤ 120 | barometric exponents ≤ 77.2; Pow_Float product ≤ 35 |
| **E6** | Pow_Float Base ∈ [0.5, 2.0], Exponent ∈ [-35, 35] | ISA layer temperature ratios ∈ [0.648, 1.056]; barometric exponents G/(R·L)±1 ∈ [4.26, 34.17] |
| **E7** | Ln_Approx contractual domain X ∈ [0.5, 2.0] | exactly the Pow_Float call-site domain; outside this band the series converges too slowly to bound (prover counterexample \|Result\| ≈ 4.7 at large X), so the envelope is part of the Pre rather than a Post |

---

## 4. Atomic Parity (`stellarorion_atomic_parity.ads/.adb`)

| Axiom | Statement | Rationale |
|-------|-----------|-----------|
| **P1** | an 8-bit value has at most 8 set bits | shift-and-mask loop inspects exactly 8 positions, incrementing C at most once per position (`Loop_Invariant C <= I` discharges formally) |
| **P2** | XOR is closed on Unsigned_8 | modular-2^8 arithmetic; XOR-fold checksum cannot overflow or leave the subtype |

---

## 5. Dual Watchdog (`stellarorion_dual_watchdog.ads/.adb`)

| Axiom | Statement | Rationale |
|-------|-----------|-----------|
| **W1** | logical tick time is monotone non-decreasing (Tick_Type = Natural) | guarded age computation `Now - Last` only evaluated when `Now >= Last`, so no negative subtraction can occur; no wall-clock dependency |

---

*Source of truth: the in-code comment blocks cited above. Update both places together.*
