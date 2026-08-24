# THEORIES — StellarOrion HypersonicEdition

> Logical consequences derived from the registered axioms (see
> `docs/AXIOMS.md`). Each theory is a proof obligation that GNATprove
> discharges at `--level=4 --report=all --timeout=180` (gate command:
> `scripts/prove.sh skip --level=4 --report=all --timeout=180`,
> 339+ checks proved, zero findings).

---

## T-1. Overflow safety of the physics chain

**From:** A1–A2, Q1–Q2, B1–B3, S1–S3, R1–R2, T1–T3, D1–D2.

Every intermediate result in the physics pipeline is bounded by hand
interval arithmetic *before* implementation, and the bounds are restated
as SPARK `Post` conditions that the prover checks:

| Function | Worst-case intermediate | Bound |
|----------|------------------------|-------|
| Mean_Free_Path | denom = √2·π·d²·n ∈ [2.2e-6, 4.5e18] | λ ≤ 4.5e8 ≪ Float'Last |
| Knudsen_Number | Kn = MFP/Char_Length ≤ 1e9/1e-3 | ≤ 1e12 |
| Dynamic_Pressure | q = ½ρV² ≤ 0.5·1e4·(1e5)² | ≤ 5.0e13 (Post) |
| Ballistic_Coefficient | β = m·q/F; worst m·q ≤ 1e21, F ≥ 1e-6 | ≤ 1e27 |
| Sutton_Graves_Heat | ρ/R_n ≤ 1e8 → √ ≤ 1e4; C_sg√ ≤ 1.75; V³ ≤ 1e15 | ≤ 1.75e15 (clamped to 2.0e15 at call site) |
| Radiative_Eq_Temp | denominator ≥ 5.67e-11 → ratio ≤ 3.6e25; double √ | T ≤ 4.9e6 K |
| Backface_Temperature | numerator ≤ 2e19; thermal capacitance ≥ 0.1 → ratio ≤ 2e20 | |
| Deceleration_G_Load | n = F/(m·g₀); m·g₀ ∈ [9.81e-3, 9.81e7] | ≤ 1.02e20 |
| Density_From_Number | n·M_air ≤ 2.9e28; /N_A | ρ ≤ 4.8e4 |

**Theory:** envelope composition is closed — the Post of each function is
exactly the Pre of its consumer (checked mechanically; any mismatch is a
proof failure, as happened with B3/R1/T2 before the A3b widening).

## T-2. Newton–Raphson square root band invariant

**From:** non-negativity of inputs; AM-GM inequality.

The custom `Sqrt` (Ada.Numerics unavailable in SPARK) starts at
`Y := Float'Max (X/2, 1)` and iterates `Y := (Y + X/Y)/2`. The two-sided
loop invariants

```
Y >= Float'Min (X, 1)   and   Y <= Float'Max (X, 1)
```

hold initially and are preserved by the iteration (AM-GM: the midpoint of
a point above the band and one below stays inside). Consequences:

* division X/Y never overflows (Y ≥ min(X,1) > 0 for X > 0);
* `Post => Result >= 0.0 and (if X > 0.0 then Result <= Float'Max (X, 1))`
  discharges every caller-side bound without re-inlining the loop.

The same pattern is applied to `Sqrt_Approx` in the environment unit.

## T-3. Taylor exponential bound (Exp_Approx)

**From:** E5 (\|X\| ≤ 120).

term_k = \|X\|^k/k! grows monotonically for k ≤ 20 when \|X\| = 120
(ratio 120/(k+1) > 1 throughout), so max partial sum ≤ 21·term₂₀ =
21·120²⁰/20! ≈ O(1e24) ≪ Float'Last. Loop invariants `Term >= 0` and
`Sum >= 1` discharge the negative-branch division `1/Sum` and the
`Post => Exp_Approx'Result >= 0`.

## T-4. Geometric-series logarithm (Ln_Approx)

**From:** E7 (domain [0.5, 2.0]).

On the domain, Y = (X−1)/(X+1) satisfies \|Y\| ≤ 1/3, hence Y² ≤ 1/9 and
each series term satisfies \|Term_k\| ≤ \|Y\|·(1/9)^k: an absolutely
convergent geometric tail. Band loop invariants

```
abs Term <= abs Y      and      abs Sum <= Float(K) * abs Y
```

bound the result by \|R\| ≤ 32/3 directly — no Post needed beyond the
domain restriction. **Lesson recorded:** outside [0.5, 2] the series
converges too slowly to bound (prover counterexample \|Result\| ≈ 4.7);
the correct fix was restricting the Pre, not weakening a Post.

## T-5. ISA piecewise post band (Atmosphere_Temperature)

**From:** E2 (altitude ∈ [0, 500] km).

Branch-by-branch interval arithmetic on constants and H:
troposphere T₀−6.5H with H ∈ [0,11] → [216.65, 288.15]; isothermal layers
return constants; gradient layers are linear on their bracketing constants;
mesosphere floor 186.946. Union ⇒ `Post => Result in 186.86 .. 288.15`.
Per-path `pragma Assert` bands let the prover discharge each branch.

## T-6. Parity algebra (Atomic_Parity)

**From:** P1, P2.

* Even parity ⇔ XOR-fold checksum of the payload has an even popcount;
  odd parity ⇔ odd. The Post of `Calculate_Parity` mirrors the standard's
  formula exactly: `Result = (Count_Set_Bits(Value) mod 2 = (if Kind = Even then 0 else 1))`.
* `Verify_Input_Parity` recomputes the checksum from the frame payload:
  equality with the stored checksum is decidable and total.
* Recovery: with retry budget left → redeliver original frame (`Success`);
  budget exhausted → substitute the safe all-zero frame (checksum 0,
  which verifies) and report `Recovered`. No code path returns without a
  verifiable frame.

## T-7. Watchdog state machine (Dual_Watchdog)

**From:** W1 (monotone ticks).

Deterministic tick-based core:

```
Healthy ──(stale: Now-Last > Timeout)──► Degraded ──(still stale)──► Failed
Failed ──Cross_Check from live peer──► Recovering ──Advance_Recovery──► Healthy
Both Failed ──Emergency_Safe_State──► Dead (latched, sticky)
```

Properties (all proved or asserted):

* Failure_Count monotone non-decreasing across Evaluate calls.
* Failed/Dead components ignore heartbeats (no silent resurrection).
* Age computation guarded by `Now >= Last`, so subtraction cannot go negative.
* Emergency latch is sticky: once latched, only process restart clears it.
* Cross-monitoring gives no single point of failure: A recovers B and vice
  versa; both-failed converges to the emergency safe state.

## T-8. Sabotage audit gate

**From:** code-quality standard pre-audit mandate.

`scripts/SabotageVerifier.sh` runs the pattern registry
(`src/utils/sabotage_verifier.py`, adapted from Zephy) over Ada specs/bodies,
Python sidecar, and UI sources. Gate criterion: **zero CRITICAL violations**
(the verifier exits nonzero only on CRITICAL). Baseline: CRITICAL=0 → PASSED
(107 HIGH triaged in `docs/AUDIT_BASELINE.md`: ~69 ADA_FUNCTION_COVERAGE are
checker false positives — it scans .adb bodies while contracts live in .ads
specs — and the remainder sit in Python sidecar files documented under Tier C1).
