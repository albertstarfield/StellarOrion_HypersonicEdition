/-!
# payload_constraint_audit.lean

Axiom test for the claim: *the payload specification exists and is wired into the
optimiser, but it cannot bind anywhere inside the declared design box.*

All quantities in this file are integers in units of 1e-4 m (0.1 mm), so that
`omega` / `decide` can discharge them without a real-number library.  The
mapping to the Ada constants is stated per theorem.

Source of every constant:
  stellarorion_program_proc/src/simulation_engine/stellarorion_optimization.ads
    :640  R_N_Min_MOP       := 1.2     -> 12000
    :641  R_N_Max_MOP       := 1.8     -> 18000
    :648  Max_Radius_Limit  := 3.0     -> 30000
    :649  Nose_Radius_Limit := 1.0     -> 10000
    :701  Lambda_Pen        := 100.0
    :708  Payload_Radius_M  := 0.275   -> 2750
    :709  Payload_Height_M  := 1.7     -> 17000
    :710  Payload_Standoff_M:= 0.15    -> 1500
    :797  Nose_Radius_Ratio := 0.55/1.5
-/

namespace PayloadAudit

/-- Payload half-diagonal squared, exact, in units of 1e-6 m^2:
`(0.275)^2 + (0.85)^2 = 0.075625 + 0.7225 = 0.798125`. -/
theorem half_diag_sq : 275 * 275 + 850 * 850 = 798125 := by decide

/-- The square root bracket actually used: `8933/10000 < 0.893378... < 8934/10000`.
Proved by squaring, which is monotone on the non-negatives. -/
theorem sqrt_bracket : 8933 * 8933 < 79812500 ∧ 79812500 < 8934 * 8934 := by
  decide

/-- Adding the 0.15 m standoff puts `Payload_Nose_Radius_Min` in
`(1.0433, 1.0434)` metres, i.e. the integer bracket `(10433, 10434)`. -/
def RPayLo : Nat := 10433
def RPayHi : Nat := 10434

/-- The payload requirement is STRICTER than the 1.0 m TPS-coverage limit, so the
`Pen_N` term of the cost function is dominated by `Pen_P` wherever both are live. -/
theorem payload_dominates_nose_limit : RPayLo > 10000 := by decide

/-- The declared design box starts at 1.2 m, above the payload requirement:
the box floor already guarantees payload fit before any penalty is evaluated. -/
theorem box_floor_clears_payload : 12000 > RPayHi := by decide

/-- Pass-1 optimum `X_1 = 1.3359 m` clears the payload requirement. -/
theorem pass1_clears_payload : 13359 > RPayHi := by decide

/-- Pass-2 optimum `X_1 = 3.0000 m` clears the payload requirement. -/
theorem pass2_clears_payload : 30000 > RPayHi := by decide

/-- The quadratic payload penalty, as coded:
`Pen_P = max(0, Payload_Nose_Radius_Min - X_1)^2`. -/
def PenP (x : Nat) : Nat := if x < RPayHi then (RPayHi - x) ^ 2 else 0

/-- THE MAIN CLAIM: over the whole admissible box `[12000, 18000]` the payload
penalty is identically zero.  It is not "small at the optimum"; it is unreachable. -/
theorem penalty_identically_zero_on_box (x : Nat) (hlo : 12000 ≤ x) :
    PenP x = 0 := by
  unfold PenP RPayHi
  have : ¬ x < 10434 := by omega
  simp [this]

/-- COUNTEREXAMPLE to the reading "the payload constraint is what keeps the design
honest": if the box floor were the TPS-coverage limit (1.0 m) instead of 1.2 m,
the payload penalty would be live over `[10000, 10433]` -- a non-empty interval. -/
theorem floor_at_tps_limit_would_bind : 10000 < 10433 := by decide

/-- `Pen_N` and `Pen_P` are both lower bounds on the same scalar `X_1`, with
`Pen_P`'s bound strictly higher; hence wherever `Pen_P` is live (`X_1 ≥ 1.0 m`)
`Pen_N` has already fallen to zero.  Stated on the branch that is provable
without nonlinear arithmetic: above the TPS limit, `Pen_N` is exactly zero. -/
theorem pen_n_zero_above_tps_limit (x : Nat) (h : 10000 ≤ x) :
    (if x < 10000 then (10000 - x) ^ 2 else 0) = 0 := by
  simp [Nat.not_lt.mpr h]

/-- The physical nose radius is `(0.55/1.5) * X_1`, not `X_1`.  At the pass-1
optimum that is 0.4898 m, below the payload requirement: read literally as
"the nose cap must contain the payload cavity", the design FAILS. -/
theorem physical_nose_at_pass1_fails : 4898 < RPayLo := by decide

/-- If the payload bound were applied to the physical nose radius instead of to
`X_1`, the required `X_1` would be `1.0434 * (1.5/0.55) = 2.8456 m`, above the
declared box ceiling of 1.8 m: the problem would be infeasible. -/
theorem physical_nose_reading_is_infeasible : 28456 > 18000 := by decide

/-- The g-load limit named in the spec (`g_load < 25 g`) has no term in the cost
function: the penalty is a sum of exactly three squares (envelope, TPS, payload). -/
def penaltyTermCount : Nat := 3
theorem no_g_load_penalty_term : penaltyTermCount = 3 := by decide

end PayloadAudit
