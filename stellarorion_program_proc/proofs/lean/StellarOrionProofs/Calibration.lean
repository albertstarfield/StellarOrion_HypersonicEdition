-- =====================================================================
-- StellarOrion CALIBRATION — Lean 4 companion proofs (no Mathlib).
--
-- PURPOSE
--   Prove the algebraic core of the Stage-1/Stage-2 calibration of the
--   StellarOrion screening model (CALIBRATION_DESIGN.md §2.6, §2.6.1,
--   §2.7): the 7-term orthogonal residual model
--       {1, x1, x2, x3, x1*x2, x1*x3, x2*x3}
--   fitted over the 2^3 factorial layout is EXACT for every response that
--   lies in the model span, and the design's orthogonality is what makes the
--   closed-form contrast fit the exact least-squares solution.
--
-- AXIOMS
--   A1  The coded 2^3 factorial design is the 8 sign vectors of {+1,-1}^3.
--       The design, its columns and its cross-products are REUSED from
--       `StellarOrionProofs.Design` (not restated here).
--   A2  The design is ORTHOGONAL: every factor column sums to zero, the
--       cross-product of two distinct factor columns sums to zero, and the
--       self-product of a factor column sums to 8.
--   A3  The seven MONOMIAL basis functions {1, x1, x2, x3, x1*x2, x1*x3,
--       x2*x3} are mutually orthogonal on the design: the Gram matrix of
--       the basis is 8*I.
--   A4  The closed-form contrast fit is
--         b0   = (1/8) * sum(y),
--         b_k  = (1/8) * sum(x_k * y),
--         b_ij = (1/8) * sum(x_k * x_j * y),
--       and the 7-term evaluation is
--         b0 + b1*x1 + b2*x2 + b3*x3 + b4*x1*x2 + b5*x1*x3 + b6*x2*x3.
--   A5  The contrast fit reproduces EXACTLY every response that lies in the
--       span of the seven basis monomials.
--   A6  The fit preserves the sample mean and every one of the seven
--       contrasts (it changes nothing the design cannot see).
--
-- THEORIES
--   T1  (Gauss 1809; Montgomery 2017 Ch. 6/7) A centred orthogonal design
--       decouples the mean from the contrasts: the Gram matrix is diagonal,
--       so the closed-form contrast fit IS the exact least-squares solution.
--   T2  (Kennedy & O'Hagan 2000, Biometrika 87(1)) An additive residual
--       correction fitted on an orthogonal basis is exact for responses in
--       the model span and vanishes identically when the model is right.
--   T3  (Montgomery 2017, Ch. 5) The grand-mean coefficient of a contrast
--       fit is the sample mean and the k-th coefficient is the k-th
--       orthogonal contrast, so the fit reproduces both.
--
-- APPLICATIONS
--   * The Stage-2 refit of the drag law and the heat scale factor against
--     the 9 DSMC responses of the Stage-1 local CCD (CALIBRATION_DESIGN
--     §2.7/§2.8); the fitted coefficients land in
--     `src/python/hiad_calibration.txt`.
--   * The SPARK-provable fit primitives of `StellarOrion_Optimizer_Core`
--     (`Fit_Orthogonal_Factorial`, `Evaluate_Residual_Model`).
--
-- CITATIONS
--   - McKay, D. et al. (1979), "A comparison of three methods for selecting
--     values of input variables", Technometrics 21(2), 239-248.
--   - Montgomery, D.C. (2017), "Design and Analysis of Experiments", 9th ed.
--   - Gauss, C.F. (1809), "Theoria Motus Corporum Coelestium".
--   - Kennedy, M.C. & O'Hagan, A. (2000), "Bayesian calibration of computer
--     models", Biometrika 87(1), 65-82.
--
-- MODEL NOTE
--   The Ada/SPARK implementation fits in Float.  The exact statements here
--   are over the INTEGERS with every fitted coefficient SCALED BY 8 (the
--   2^3 factorial has norm 8, so 8*b_k is an exact integer and no division
--   by a possibly-zero quantity is needed).  The rational statements
--   (b_k = (1/8)*sum(...)) are proved over the reals in the Coq companion
--   `proofs/coq/Calibration.v`.
--
-- The design and the orthogonality identities are FINITE and therefore
-- decided by the kernel (`decide`); the fit identities are linear in the
-- fitted coefficients and are discharged by `omega` after `simp` has
-- unfolded the concrete design.
-- =====================================================================
import Lean
import StellarOrionProofs.Design

namespace StellarOrionProofs

/-! ## The design, the factor columns and the monomial basis -/

/-- The k-th FACTOR coordinate (0 → x1, 1 → x2, 2 → x3) of the coded design
point `i`.  The factor columns are the design columns of `Design.lean`;
`colSum_eq_factorSum` and `colCross_eq_factorCross` tie the two together. -/
def factorAt (k i : Nat) : Int :=
  match k with
  | 0 => (designPoint i).x1
  | 1 => (designPoint i).x2
  | 2 => (designPoint i).x3
  | _ => 0

/-- The k-th MONOMIAL basis function (0-based) of the calibration model at
the coded design point `i`:
    0 → 1, 1 → x1, 2 → x2, 3 → x3,
    4 → x1*x2, 5 → x1*x3, 6 → x2*x3.
This is the basis `{1, x1, x2, x3, x1*x2, x1*x3, x2*x3}` of CALIBRATION_DESIGN
§2.6. -/
def basisAt (k i : Nat) : Int :=
  match k with
  | 0 => 1
  | 1 => (designPoint i).x1
  | 2 => (designPoint i).x2
  | 3 => (designPoint i).x3
  | 4 => (designPoint i).x1 * (designPoint i).x2
  | 5 => (designPoint i).x1 * (designPoint i).x3
  | 6 => (designPoint i).x2 * (designPoint i).x3
  | _ => 0

/-- The sum of a function over the eight coded design points. -/
def dsum (f : Nat → Int) : Int :=
  f 0 + f 1 + f 2 + f 3 + f 4 + f 5 + f 6 + f 7

/-- The Gram entry of the seven monomial basis functions. -/
def gramEntry (k l : Fin 7) : Int :=
  dsum (fun i => basisAt k.val i * basisAt l.val i)

/-! ## AXIOM A2 — the factor design is centred and orthogonal -/

/-- AXIOM A2: the Gram matrix of the three factor columns is 8*I₃, i.e.
`sum_i x_ik = 0` for every k, `sum_i x_ik^2 = 8` for every k and
`sum_i x_ik x_jl = 0` for every k ≠ l.  The hypothesis `k ≠ l` selects the
off-diagonal (cross) case; the diagonal case is `k = l`. -/
theorem factor_gram : ∀ k l : Fin 3,
    dsum (fun i => factorAt k.val i * factorAt l.val i) = if k = l then 8 else 0 := by
  decide

/-- AXIOM A2: the cross-product of two DISTINCT factor columns sums to zero
(`sum_i x_ik x_jk = 0` for k ≠ j). -/
theorem factor_cross_zero (k l : Fin 3) (h : k ≠ l) :
    dsum (fun i => factorAt k.val i * factorAt l.val i) = 0 := by
  have := factor_gram k l
  simp [h] at this
  exact this

/-- AXIOM A2: the self-product of a factor column sums to 8
(`sum_i x_ik^2 = 8` for every k). -/
theorem factor_self_eight (k : Fin 3) :
    dsum (fun i => factorAt k.val i * factorAt k.val i) = 8 := by
  have := factor_gram k k
  simp at this
  exact this

/-- The factor-column sum agrees with the design-column sum of `Design.lean`
(`factorial_centred`), so the two formulations are the same object. -/
theorem colSum_eq_factorSum : ∀ k : Fin 3,
    colSum k.val = dsum (fun i => factorAt k.val i) := by
  decide

/-- The factor-column cross-product agrees with the design cross-product of
`Design.lean` (`factorial_orthogonal`). -/
theorem colCross_eq_factorCross : ∀ k l : Fin 3,
    colCross k.val l.val = dsum (fun i => factorAt k.val i * factorAt l.val i) := by
  decide

/-! ## AXIOM A3 — the seven monomial basis functions are orthogonal -/

/-- AXIOM A3: the Gram matrix of the seven monomial basis functions is 8*I₇
— the basis is mutually orthogonal with squared norm 8. -/
theorem basis_gram : ∀ k l : Fin 7,
    gramEntry k l = if k = l then 8 else 0 := by
  decide

/-- AXIOM A3, cross case: the cross-product of two DISTINCT basis functions
sums to zero. -/
theorem basis_cross_zero (k l : Fin 7) (h : k ≠ l) : gramEntry k l = 0 := by
  have := basis_gram k l
  simp [h] at this
  exact this

/-- AXIOM A3, diagonal case: the squared norm of a basis function is 8. -/
theorem basis_self_eight (k : Fin 7) : gramEntry k k = 8 := by
  have := basis_gram k k
  simp at this
  exact this

/-! ## AXIOM A4 — the closed-form contrast fit -/

/-- The seven coefficients of the orthogonal residual model
(CALIBRATION_DESIGN §2.6.1, `Residual_Coefficient_Array`). -/
structure Coefficients where
  /-- b0 — the grand-mean coefficient -/
  b0 : Int
  /-- b1 — the x1 contrast -/
  b1 : Int
  /-- b2 — the x2 contrast -/
  b2 : Int
  /-- b3 — the x3 contrast -/
  b3 : Int
  /-- b4 — the x1*x2 interaction -/
  b4 : Int
  /-- b5 — the x1*x3 interaction -/
  b5 : Int
  /-- b6 — the x2*x3 interaction -/
  b6 : Int
  deriving Repr, BEq, DecidableEq

/-- The k-th fitted coefficient (0-based). -/
def coefficient (c : Coefficients) (k : Nat) : Int :=
  match k with
  | 0 => c.b0
  | 1 => c.b1
  | 2 => c.b2
  | 3 => c.b3
  | 4 => c.b4
  | 5 => c.b5
  | 6 => c.b6
  | _ => 0

/-- The closed-form contrast fit, SCALED BY 8: `fitCoefficient y k` is the
numerator of the k-th contrast, so the fitted coefficient is
`b_k = fitCoefficient y k / 8`.  The 2^3 factorial has norm 8, so the
divisor is never zero (CALIBRATION_DESIGN §2.6.1). -/
def fitCoefficient (y : Nat → Int) (k : Nat) : Int :=
  match k with
  | 0 => dsum (fun i => y i)
  | 1 => dsum (fun i => factorAt 0 i * y i)
  | 2 => dsum (fun i => factorAt 1 i * y i)
  | 3 => dsum (fun i => factorAt 2 i * y i)
  | 4 => dsum (fun i => factorAt 0 i * factorAt 1 i * y i)
  | 5 => dsum (fun i => factorAt 0 i * factorAt 2 i * y i)
  | 6 => dsum (fun i => factorAt 1 i * factorAt 2 i * y i)
  | _ => 0

/-- AXIOM A4: the grand-mean coefficient is `(1/8)*sum(y)` — in the scaled
(integer) form, `8*b0 = sum(y)`. -/
theorem fitCoefficient_mean (y : Nat → Int) :
    fitCoefficient y 0 = dsum (fun i => y i) := rfl

/-- AXIOM A4: the x1 coefficient is `(1/8)*sum(x1*y)`. -/
theorem fitCoefficient_x1 (y : Nat → Int) :
    fitCoefficient y 1 = dsum (fun i => factorAt 0 i * y i) := rfl

/-- AXIOM A4: the x2 coefficient is `(1/8)*sum(x2*y)`. -/
theorem fitCoefficient_x2 (y : Nat → Int) :
    fitCoefficient y 2 = dsum (fun i => factorAt 1 i * y i) := rfl

/-- AXIOM A4: the x3 coefficient is `(1/8)*sum(x3*y)`. -/
theorem fitCoefficient_x3 (y : Nat → Int) :
    fitCoefficient y 3 = dsum (fun i => factorAt 2 i * y i) := rfl

/-- AXIOM A4: the x1*x2 interaction coefficient is `(1/8)*sum(x1*x2*y)`. -/
theorem fitCoefficient_x12 (y : Nat → Int) :
    fitCoefficient y 4 = dsum (fun i => factorAt 0 i * factorAt 1 i * y i) := rfl

/-- AXIOM A4: the x1*x3 interaction coefficient is `(1/8)*sum(x1*x3*y)`. -/
theorem fitCoefficient_x13 (y : Nat → Int) :
    fitCoefficient y 5 = dsum (fun i => factorAt 0 i * factorAt 2 i * y i) := rfl

/-- AXIOM A4: the x2*x3 interaction coefficient is `(1/8)*sum(x2*x3*y)`. -/
theorem fitCoefficient_x23 (y : Nat → Int) :
    fitCoefficient y 6 = dsum (fun i => factorAt 1 i * factorAt 2 i * y i) := rfl

/-! ## The fitted model -/

/-- The scaled (8×) fitted value at the coded design point `i`: the sum of
the seven fitted coefficients weighted by the seven basis monomials. -/
def scaledModelFit (y : Nat → Int) (i : Nat) : Int :=
  fitCoefficient y 0 * basisAt 0 i
    + fitCoefficient y 1 * basisAt 1 i
    + fitCoefficient y 2 * basisAt 2 i
    + fitCoefficient y 3 * basisAt 3 i
    + fitCoefficient y 4 * basisAt 4 i
    + fitCoefficient y 5 * basisAt 5 i
    + fitCoefficient y 6 * basisAt 6 i

/-- A response lying in the SPAN of the seven basis monomials: the model
response generated by the coefficients `c`. -/
def modelResponse (c : Coefficients) (i : Nat) : Int :=
  coefficient c 0 * basisAt 0 i
    + coefficient c 1 * basisAt 1 i
    + coefficient c 2 * basisAt 2 i
    + coefficient c 3 * basisAt 3 i
    + coefficient c 4 * basisAt 4 i
    + coefficient c 5 * basisAt 5 i
    + coefficient c 6 * basisAt 6 i

/-- The 7-term orthogonal model evaluated at a coded design point. -/
def evaluate (c : Coefficients) (p : Point) : Int :=
  c.b0 + c.b1 * p.x1 + c.b2 * p.x2 + c.b3 * p.x3
    + c.b4 * (p.x1 * p.x2) + c.b5 * (p.x1 * p.x3) + c.b6 * (p.x2 * p.x3)

/-- AXIOM A4: the evaluation IS the 7-term expansion — the identity holds
by `rfl` because the function is defined by that expansion. -/
theorem evaluate_eq_expansion (c : Coefficients) (p : Point) :
    evaluate c p = c.b0 + c.b1 * p.x1 + c.b2 * p.x2 + c.b3 * p.x3
      + c.b4 * (p.x1 * p.x2) + c.b5 * (p.x1 * p.x3) + c.b6 * (p.x2 * p.x3) := rfl

/-- The evaluation at a coded design point is the basis expansion of the
same seven coefficients. -/
theorem evaluate_eq_basis (c : Coefficients) (i : Nat) :
    evaluate c (designPoint i)
      = coefficient c 0 * basisAt 0 i
        + coefficient c 1 * basisAt 1 i
        + coefficient c 2 * basisAt 2 i
        + coefficient c 3 * basisAt 3 i
        + coefficient c 4 * basisAt 4 i
        + coefficient c 5 * basisAt 5 i
        + coefficient c 6 * basisAt 6 i := by
  simp [evaluate, coefficient, basisAt, designPoint]

/-! ## AXIOM A5 — the contrast fit is exact on the model span -/

/-- The grand-mean contrast of a model response is 8 times the fitted
coefficient (the scaled form of `b0 = (1/8)*sum(y)`). -/
theorem contrast_model_0 (c : Coefficients) :
    fitCoefficient (modelResponse c) 0 = 8 * coefficient c 0 := by
  simp [fitCoefficient, dsum, modelResponse, basisAt, designPoint]
  omega

/-- The x1 contrast of a model response is 8 times the fitted coefficient. -/
theorem contrast_model_1 (c : Coefficients) :
    fitCoefficient (modelResponse c) 1 = 8 * coefficient c 1 := by
  simp [fitCoefficient, dsum, modelResponse, basisAt, factorAt, designPoint]
  omega

/-- The x2 contrast of a model response is 8 times the fitted coefficient. -/
theorem contrast_model_2 (c : Coefficients) :
    fitCoefficient (modelResponse c) 2 = 8 * coefficient c 2 := by
  simp [fitCoefficient, dsum, modelResponse, basisAt, factorAt, designPoint]
  omega

/-- The x3 contrast of a model response is 8 times the fitted coefficient. -/
theorem contrast_model_3 (c : Coefficients) :
    fitCoefficient (modelResponse c) 3 = 8 * coefficient c 3 := by
  simp [fitCoefficient, dsum, modelResponse, basisAt, factorAt, designPoint]
  omega

/-- The x1*x2 interaction contrast of a model response is 8 times the
fitted coefficient. -/
theorem contrast_model_4 (c : Coefficients) :
    fitCoefficient (modelResponse c) 4 = 8 * coefficient c 4 := by
  simp [fitCoefficient, dsum, modelResponse, basisAt, factorAt, designPoint]
  omega

/-- The x1*x3 interaction contrast of a model response is 8 times the
fitted coefficient. -/
theorem contrast_model_5 (c : Coefficients) :
    fitCoefficient (modelResponse c) 5 = 8 * coefficient c 5 := by
  simp [fitCoefficient, dsum, modelResponse, basisAt, factorAt, designPoint]
  omega

/-- The x2*x3 interaction contrast of a model response is 8 times the
fitted coefficient. -/
theorem contrast_model_6 (c : Coefficients) :
    fitCoefficient (modelResponse c) 6 = 8 * coefficient c 6 := by
  simp [fitCoefficient, dsum, modelResponse, basisAt, factorAt, designPoint]
  omega

/-- AXIOM A5 / THEORY T1: the closed-form contrast fit reproduces EXACTLY
every response that lies in the span of the seven basis monomials.  In the
scaled (integer) form: `8*yhat_i = 8*y_i`. -/
theorem fit_reproduces_model_span (c : Coefficients) (i : Nat) :
    scaledModelFit (modelResponse c) i = 8 * modelResponse c i := by
  simp only [scaledModelFit, modelResponse]
  rw [contrast_model_0, contrast_model_1, contrast_model_2, contrast_model_3,
    contrast_model_4, contrast_model_5, contrast_model_6]
  simp [Int.mul_comm, Int.mul_left_comm, Int.add_assoc, Int.mul_add]

/-! ## AXIOM A6 — the fit preserves the sample mean and the contrasts -/

/-- AXIOM A6 / THEORY T3: the fit preserves the sample mean — the sum of
the scaled fitted values is 8 times the fitted grand-mean coefficient
(which is the sum of the responses). -/
theorem fit_preserves_mean (y : Nat → Int) :
    dsum (fun i => scaledModelFit y i) = 8 * fitCoefficient y 0 := by
  simp [dsum, scaledModelFit, basisAt, designPoint]
  omega

/-- AXIOM A6 / THEORY T3: the fit preserves all seven contrasts — the k-th
contrast of the scaled fitted values is 8 times the k-th fitted contrast
(which is the k-th contrast of the responses). -/
theorem fit_preserves_contrasts (y : Nat → Int) :
    (dsum (fun i => basisAt 0 i * scaledModelFit y i) = 8 * fitCoefficient y 0)
      ∧ (dsum (fun i => basisAt 1 i * scaledModelFit y i) = 8 * fitCoefficient y 1)
      ∧ (dsum (fun i => basisAt 2 i * scaledModelFit y i) = 8 * fitCoefficient y 2)
      ∧ (dsum (fun i => basisAt 3 i * scaledModelFit y i) = 8 * fitCoefficient y 3)
      ∧ (dsum (fun i => basisAt 4 i * scaledModelFit y i) = 8 * fitCoefficient y 4)
      ∧ (dsum (fun i => basisAt 5 i * scaledModelFit y i) = 8 * fitCoefficient y 5)
      ∧ (dsum (fun i => basisAt 6 i * scaledModelFit y i) = 8 * fitCoefficient y 6) := by
  simp [dsum, scaledModelFit, basisAt, designPoint]
  omega

end StellarOrionProofs
