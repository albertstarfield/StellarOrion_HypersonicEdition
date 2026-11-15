# Audit: `proofs/fourth_power.lean` and the deck's design point

Scope: the Lean file, the thesis appendix (§Radiative equilibrium of the hot face,
`appendix.tex:795-820`), and the Ada residual
(`stellarorion_physics.adb:2601-2618`). Numbers below are reproduced from
`logs/flux_arithmetic.log`, `logs/counterexamples.log`,
`logs/fourth_power*.log`, `logs/rocq_*.log`.

Commands (all logged):

```
lean proofs/fourth_power.lean            # exit 0
lean proofs/fourth_power_axioms.lean     # exit 0 (byte-identical copy + 10 #print axioms)
lean proofs/fourth_power_audit.lean      # exit 0 (Nat/Int gaps, counterexample)
rocq compile -q proofs/fourth_power_mono.v        # exit 0
rocq compile -q proofs/check_fourth_power_mono.v  # exit 0 (Print Assumptions)
```

## 1. Axioms

`lean proofs/fourth_power.lean` exits 0 with no warnings and prints five lines;
the file declares ten theorems, so five are never printed. The full list, from a
byte-identical copy with ten `#print axioms` lines appended:

| theorem | axioms |
|---|---|
| `single_count_closes` | none |
| `double_count_breaks` | none |
| `counts_are_distinguishable` | none |
| `slope_at_design` | none |
| `quartic_step_at_design` | none |
| `step_exceeds_slope` | none |
| `double_count_is_doubled_emissivity` | `propext` |
| **`doubled_term_is_larger`** | **`propext`, `Quot.sound`** |
| `residual_strictMono` | `propext` |
| `residual_injective` | `propext` |

`Quot.sound` is introduced by the `omega` tactic, not by the mathematics: a
one-line `omega` proof of `a < b + 1` from `a < b` also reports
`[propext, Quot.sound]` (`logs/probe_omega2.log`). No `sorryAx`,
`Classical.choice`, `funext`, or `Lean.ofReduceBool` appears; `grep -n
"sorry\|admit\|native_decide\|axiom "` over the file returns nothing.

**Verdict: FAIL as worded.** "Axiom-free or propext only" is false for
`doubled_term_is_larger`; it carries `Quot.sound`. The defect is in the file's
five-line print list, which omits exactly the theorem that has the extra axiom.

**Verified fix** (`proofs/fourth_power_audit.lean`, `doubled_term_is_larger_clean`,
exit 0, prints `[propext]`): replace the `omega` line with

```lean
  have hpos : 0 < b * T ^ 4 := Nat.mul_pos hb (Nat.pow_pos hT)
  have h := Nat.mul_lt_mul_of_pos_left (show (1 : Nat) < 2 by decide) hpos
  simpa [Nat.mul_comm, Nat.mul_left_comm, Nat.mul_assoc] using h
```

which drops `Quot.sound` and makes the file's claim true as written. Adding the
five missing `#print axioms` lines would then show ten clean entries.

## 2. Design-point arithmetic (Decimal, 50 digits)

| quantity | value | reference | disagreement |
|---|---|---|---|
| `eps*sigma*1348^4`, eps=0.75, sigma=5.670374419e-8 | 140421.164026 W/m² | `qRad` = 140399 | **+0.01579 %** (+22.164 W/m²) |
| `(140399/(eps*sigma))^0.25` | 1347.9468049 K | 1348 K | **−0.003946 %** (−0.0532 K) |
| `eps` that makes it exact at 1348 K | 0.74988162 | 0.75 | −0.0158 % |
| `4*eps*sigma*1348^3` | 416.680012 W m⁻²K⁻¹ | slide "417" | −0.077 % |
| `qRad/qCond` | 140399/3362 = 41.759 | slide "41.8" | −0.10 % |
| `417/3362` | 12.394 % | slide "12.4 %" | ok |

Closure: `143760 − (140399 + 3362) = −1`. The literal identity
`143760 = 140399 + 3362` is **false by 1 W/m²** (the sum is 143761); the file's
own theorem only asserts `|·| ≤ 2`, so it passes the stated tolerance. 1 W/m² is
0.000696 % of 143760.

Note that the Lean file contains no `eps` and no `sigma`: the σ-arithmetic above
is unformalized. Lean checks only `4*1348^3 = 9797824768`,
`1349^4 − 1348^4 = 9808732785`, and the integer closure.

**Verdict: PASS at the deck's precision (≤0.016 %), with the 1 W/m² caveat.**

σ is the code's literal: `stellarorion_types.ads:85` `SIGMA_BOLTZMANN : constant
Float := 5.670374419e-8`. (With a legacy 5.67e-8 the disagreement would be
+0.0092 % instead of +0.0158 %, so the conclusion does not hinge on the digit.)

Two provenance notes rather than errors:

* `qCond = 3362 W/m²` with the appendix's `R = 0.3056 m²K/W` implies a back face
  at `1348 − 3362·0.3056 = 320.6 K`, not 300 K. At `T_back = 300 K` the
  conducted flux would be 3429.3 W/m² and the closure would miss by −68.3 W/m²
  (−0.048 %), with the 41.8 ratio becoming 40.9. The deck's `T_back` is not
  stated in the sources read; the sum test in Lean cannot see this because it
  never evaluates the conduction law.
* The prose at `fourth_power.lean:63-64` says the quartic step exceeds the
  tangent "by less than a thousandth of it". It is 10 908 017/9 797 824 768 =
  1.1133×10⁻³ — 1.11 thousandths, i.e. just **over** a thousandth. The other
  phrasing ("about a tenth of a per cent", line 18-19) is right.

Cross-check of the appendix's own numbers (ε = 0.80, `appendix.tex:820`):
`1.5357e5 → 1356.4418 K` (stated 1356.4), `1.93154e5 → 1436.4830 K`
(stated 1436.5); closure at 1430.25 K: +0.1904 % at ε=0.80, −5.9518 % at 0.75,
+6.3326 % at 0.85 — all three match the printed +0.19 / −5.95 / +6.33 %.

Provenance of the deck's ε: the appendix uses **0.80** for the thermal runs;
the deck uses **0.75** (`tools/add_issue_slides.py:17-18,58`;
`tools/fix_issue_slides.py:58-59`) and the appendix says the 0.75 closure misses
by −5.95 %. The Lean constants match the deck (0.75), not the appendix (0.80).
Two emissivities coexist in the same document; the slide is internally
consistent but is not the appendix's thermal solve.

## 3. Does `residual_strictMono` say what the thesis says?

The thesis (`appendix.tex:820`): "The function T ↦ εσT⁴ is strictly increasing
on T>0, so (eq:app_tsurf) is the unique solution."

Lean: `def residual (c b T : Nat) : Nat := c*T + b*T^4`, monotone for
`0 < c`, `0 < b`. Differences:

1. **Nat, not Float/real.** Negatives are unrepresentable, so every
   counterexample with a wrong-signed coefficient is outside the type. Rocq
   (`proofs/fourth_power_mono.v`) proves the same claim on `R`:
   `0 < k → 0 < b → 0 ≤ T1 → T1 < T2 → k*T1 + b*T1^4 − q < k*T2 + b*T2^4 − q`.
2. **No constant terms.** Ada has `(T − T_back)/R + εσ(T⁴ − T_inf⁴) − q + G*T − S`;
   Lean has `c*T + b*T⁴`. Legitimate only because the dropped terms are
   T-independent — proved in `proofs/fourth_power_audit.lean`
   (`strictMono_add_const`) and then the Ada shape with a possibly negative
   `T − T_back` is proved over `Int` (`ada_shape_strictMono`).
3. **`G*T` is missing from Lean.** Ada passes `Lateral_G`, and the monotonicity
   argument needs `G ≥ 0`. That is enforced by contract:
   `stellarorion_physics.ads:1065` `Pre => ... Lateral_G >= 0.0`.
4. **Root at the wrong place.** Lean: `residual c b 0 = 0` for every `c, b`
   (proved, `residual_at_zero`), and `T = 0` is the only Nat root
   (`residual_eq_zero_iff`). Ada: `f(0) = −194480.15 W/m²` at the appendix's
   numbers, i.e. strictly negative, not a root, and the physical root is 1348 K.
   So the Lean `residual` is the *shape* of the balance, not the balance.
5. **"Unique" needs existence.** `residual_injective` gives at most one root.
   Existence comes from the closed form `(q/εσ)^{1/4}`, not from Lean. The
   comment at line 97 ("Hence the wall temperature that closes the balance is
   unique") overstates what is proved.
6. **Lean excludes the appendix's own case.** The thesis sentence is the
   *conduction-free* balance (`appendix.tex:815`: "If conduction is neglected"),
   i.e. `c = 0`. `residual_strictMono` requires `hc : 0 < c`, so it cannot be
   instantiated there; the pure-quartic statement exists only as an immediate
   corollary that Lean never draws. Rocq does prove it directly: `pow4_lt`
   (`0 ≤ x → x < y → x⁴ < y⁴`) is exactly `T ↦ εσT⁴` strictly increasing on
   `T > 0` after scaling by `εσ > 0`.

What the Ada side adds that Lean lacks: the contract enforces the hypotheses.
`stellarorion_physics.ads:1065` `Pre => ... Lateral_G >= 0.0` (the `G ≥ 0` the
monotonicity needs, and the reason the bracket at `.adb:2889-2893` can omit
`G`), and `.ads:1072-1073` `Layup.Emissivity >= 1.0e-3 and <= 1.0` — which makes
the double-count reading `2ε = 1.5` an illegal call, not merely a wrong number.
In `Long_Float` the strict inequality survives rounding: at 1348 K the flux is
1.4e5 and one ulp of binary64 is 3.1e-11 W/m², so monotonicity is granular to
~7e-14 K, far below the 1e-9 relative bisection tolerance.

**Verdict: PARTIAL.** Direction and algebra are right and transfer; the statement
is a weaker surrogate (Nat, no constants, no `G`), and the "unique" conclusion
lacks existence in Lean.

## 4. Counterexamples

**(a) Negative radiative coefficient** — machine-checked in Rocq
(`negative_coefficient_breaks_it`): `c = 1, b = −1, q = 0` gives `f(1) = 0`,
`f(2) = −14`, so `f` decreases and `q ∈ (−14, 0)` has two roots. Excluded in Ada
by `Emissivity >= 1.0e-3`, and in Lean by `hb : 0 < b` — but Lean cannot state
the counterexample at all, which is the point.

**(b) Emissivity that falls faster than T⁻⁴** — machine-checked in Rocq
(`flux_not_injective`, `two_roots_of_the_balance`): with `b*T^4` on `T ≤ 1` and
`b/T^4` above (continuous at 1, i.e. ε ∝ T⁻⁸), `b*(1/2)^4 = b/2^4 = b/16`: the
same flux at T = 0.5 and T = 2, so `q = b/16` has two roots. Numerically, with
the deck's ε = 0.75 and a piecewise `ε(T) = 0.75·(1348/T)^5` for T > 1348 K,
`q = 140000 W/m²` has roots at **1346.988 K** and **1352.055 K**, 5.07 K apart,
each reproducing q to 40 digits (`logs/counterexamples.log`).

**(c) Negative lateral coupling** — `f'(T) = 1/R + 4εσT³ + G`. At 1348 K,
ε=0.75, 1/R = 3.272 W m⁻²K⁻¹: `f' = 419.95 + G`, so any `G < −419.95` makes the
residual strictly decreasing (`G = −420 → f' = −0.05`; `G = −500 → −80.05`) and
the bisection's bracket `T_Hi` (`.adb:2889-2893`, which has no `G` term) can land
below the root. This is excluded by `Pre => Lateral_G >= 0.0`.

**(d) The Rosseland term is *not* a counterexample.** `k_rad = 16σT³/(3κ_R)`
(`fourth_power.lean:27`) is positive and adds to the slope, so it preserves
strict monotonicity — it changes the design-point *value*, not uniqueness:
740.76 W m⁻¹K⁻¹ at κ_R = 1 m⁻¹, 7.41 at κ_R = 100, against k_SiC ≈ 0.3. The
file's own hedge (lines 26-31) is therefore correctly aimed: the modelling
question is magnitude, not uniqueness.

## Rocq

`rocq compile -q proofs/fourth_power_mono.v` → **exit 0**, no warnings. Thirteen
declarations: `pow4_lt`, `pow3_nonneg`, `residual_strict_mono`, `slope_positive`,
`residual_root_unique`, `double_count_is_doubled_emissivity`,
`negative_coefficient_breaks_it`, `single_count_closes`, `double_count_breaks`,
`counts_are_distinguishable`, `design_point_residual_small`,
`flux_not_injective`, `two_roots_of_the_balance`.

`Print Assumptions` on all eleven: every theorem depends on
`ClassicalDedekindReals.sig_forall_dec` and
`FunctionalExtensionality.functional_extensionality_dep` — the standard axioms
of Coq's axiomatized `Reals`. Not axiom-free, and cannot be: `Reals` is a
classical complete ordered field. Rocq is a checker of the argument here, not an
axiom-free certificate, unlike the `decide`-only arithmetic in Lean.
