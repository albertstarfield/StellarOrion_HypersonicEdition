import StellarOrionProofs.Design
import StellarOrionProofs.Algorithm

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

The rational/real statements are proved in the Coq companion under
`proofs/coq/`.
-/
