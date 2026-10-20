-- AXIOMS
--   A1  The composite cost J is a sum of two non-negative weighted squares:
--       J = w_beta * d_beta^2 + w_target * d_y^2 with w >= 0.
--   A2  J vanishes exactly when both weighted terms vanish.
--   A3  Elitism: the next generation carries the current best individual, so
--       the best cost of an elitist run never increases.
--
-- THEORIES
--   T1  (Gauss 1809) A sum of non-negative terms is non-negative, and it
--       vanishes only when every term vanishes.
--   T2  (Goldberg 1989, Ch. 3, "Elitism") Copying the best individual into the
--       next generation makes the sequence of best costs monotonically
--       non-increasing, so the search cannot regress.
--
-- CITATIONS
--   - Goldberg, D.E. (1989), "Genetic Algorithms in Search, Optimization and
--     Machine Learning", Addison-Wesley, Ch. 3.
--   - Holland, J.H. (1975), "Adaptation in Natural and Artificial Systems".
--   - Eshelman, L.J. & Schaffer, J.D. (1993), "Real-coded genetic algorithms
--     and fitness landscapes", in "Foundations of Genetic Algorithms".
--
-- MODEL NOTE
--   The Ada/SPARK implementation evaluates J on bounded Float values.  The
--   theorem below is stated over the NON-NEGATIVE INTEGERS, which is the
--   exact algebraic core of the floating-point statement: the weights and the
--   squared deltas are non-negative reals, and the rational/real statements
--   are proved in the Coq companion (`CostModel.v`).
import Lean

namespace StellarOrionProofs

/-! ## The composite cost -/

/-- The composite cost of the Ada optimiser in the non-negative integer model:
`wBeta * dBeta^2 + wTarget * dY^2`.  The Ada version divides the beta delta
by 10 before squaring; that positive scaling does not affect the sign or the
vanishing condition, so it is folded into `dBeta` here. -/
def cost (wBeta wTarget dBeta dY : Nat) : Nat :=
  wBeta * (dBeta * dBeta) + wTarget * (dY * dY)

/-- AXIOM A1: the cost is never negative. -/
theorem cost_nonneg (w1 w2 d1 d2 : Nat) : 0 ≤ cost w1 w2 d1 d2 := Nat.zero_le _

/-- Auxiliary: a sum of naturals vanishes only when both summands vanish. -/
theorem nat_add_eq_zero_iff (n m : Nat) : n + m = 0 ↔ n = 0 ∧ m = 0 :=
  Nat.add_eq_zero_iff

/-- Auxiliary: a product of naturals vanishes only when a factor vanishes. -/
theorem nat_mul_eq_zero_iff (n m : Nat) : n * m = 0 ↔ n = 0 ∨ m = 0 :=
  Nat.mul_eq_zero

/-- AXIOM A2: the cost vanishes exactly when both weighted square terms
vanish. -/
theorem cost_zero_iff (w1 w2 d1 d2 : Nat) :
    cost w1 w2 d1 d2 = 0 ↔ (w1 * (d1 * d1) = 0 ∧ w2 * (d2 * d2) = 0) := by
  unfold cost
  rw [Nat.add_eq_zero_iff]

/-- The vanishing condition of the cost, in the form used by the optimiser:
a weighted square term vanishes only if its weight or its delta is zero. -/
theorem cost_zero_weight_or_delta (w1 w2 d1 d2 : Nat)
    (h : cost w1 w2 d1 d2 = 0) :
    (w1 = 0 ∨ d1 = 0) ∧ (w2 = 0 ∨ d2 = 0) := by
  have hz := (cost_zero_iff w1 w2 d1 d2).mp h
  constructor
  · rcases (Nat.mul_eq_zero).mp hz.1 with h1 | h1
    · exact Or.inl h1
    · rcases (Nat.mul_eq_zero).mp h1 with h2 | h2
      · exact Or.inr h2
      · exact Or.inr h2
  · rcases (Nat.mul_eq_zero).mp hz.2 with h1 | h1
    · exact Or.inl h1
    · rcases (Nat.mul_eq_zero).mp h1 with h2 | h2
      · exact Or.inr h2
      · exact Or.inr h2

/-- The converse: both deltas vanishing makes the cost vanish. -/
theorem cost_zero_of_zero_deltas (w1 w2 d1 d2 : Nat) (h1 : d1 = 0) (h2 : d2 = 0) :
    cost w1 w2 d1 d2 = 0 := by
  simp [cost, h1, h2]

/-! ## Elitism -/

/-- The running minimum of a cost list, starting from `acc`. -/
def listMin : List Nat → Nat → Nat
  | [], acc => acc
  | a :: t, acc => listMin t (Nat.min acc a)

/-- A running minimum that starts at the smallest possible value keeps it. -/
theorem listMin_eq_of_ge (best : Nat) (l : List Nat) (h : ∀ c ∈ l, best ≤ c) :
    listMin l best = best := by
  induction l with
  | nil => rfl
  | cons a t ih =>
      have ha : best ≤ a := h a (by simp)
      have ht : ∀ c ∈ t, best ≤ c := fun c hc => h c (by simp [hc])
      have hfold : listMin t best = best := ih ht
      simp [listMin, Nat.min_eq_left ha, hfold]

/-- AXIOM A3 / THEORY T2: elitism.  The next generation starts with the
current best individual (so the head of its cost list is the current best)
and no individual is cheaper than the current best (so the best is not
improved) — hence the best cost of the next generation is exactly the
current best, and in particular it never increases. -/
theorem elitism_preserves_best (best : Nat) (costs : List Nat)
    (hhead : costs.head? = some best)
    (htail : ∀ c ∈ costs.tail, best ≤ c) :
    listMin costs best = best := by
  cases costs with
  | nil => simp at hhead
  | cons a rest =>
      have ha : a = best := Option.some.inj hhead
      rw [ha] at *
      have hrest : ∀ c ∈ rest, best ≤ c := fun c hc => htail c (by simp [hc])
      have hmin : Nat.min best best = best := Nat.min_eq_left (Nat.le_refl best)
      simp [listMin, hmin, listMin_eq_of_ge best rest hrest]

/-- The best-cost sequence of an elitist run is non-increasing. -/
theorem elitism_best_nonincreasing (best : Nat) (costs : List Nat)
    (hhead : costs.head? = some best)
    (htail : ∀ c ∈ costs.tail, best ≤ c) :
    listMin costs best ≤ best := by
  rw [elitism_preserves_best best costs hhead htail]
  exact Nat.le_refl best

end StellarOrionProofs
