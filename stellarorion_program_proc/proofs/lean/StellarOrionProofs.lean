import StellarOrionProofs.Design
import StellarOrionProofs.Algorithm
import StellarOrionProofs.Calibration

/-!
# StellarOrion formal verification package

Lean 4 companion proofs for the Ada/SPARK optimiser rewrite.

Modules:
* `StellarOrionProofs.Design` -- the coded 2^3 factorial design is centred and
  orthogonal, the 15-point CCD is centrally symmetric, and the closed-form
  contrast fit reproduces the design responses exactly.
* `StellarOrionProofs.Algorithm` -- the composite cost is non-negative and
  vanishes only when both weighted square terms vanish, and elitism makes the
  best-cost sequence non-increasing.
* `StellarOrionProofs.Calibration` -- the calibration DoE of
  CALIBRATION_DESIGN.md: the coded 2^3 design and its seven monomial basis
  functions are orthogonal, the closed-form contrast fit is
  `b_k = (1/8)*sum(...)`, and the fit reproduces every response that lies in
  the model span exactly.

The rational/real statements are proved in the Coq companion under
`proofs/coq/`.
-/
