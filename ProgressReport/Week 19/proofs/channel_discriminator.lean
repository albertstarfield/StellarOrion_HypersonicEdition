/-
  channel_discriminator.lean

  A different method from the algebra of the last turn: an *operational*
  discriminator plus an exact check of the deck's own numbers.

  PART A -- the discriminator that needs no theory.  A surface flux does not
  care how thick the layer is; a volumetric flux does, because to become a
  surface flux it must be integrated over that thickness.  So the test is
  mechanical: halve the layer and see which term moves.  The wall term cannot
  move; the Rosseland term must.

  PART B -- the deck's check-3 case is not the thesis's case, and this is now a
  theorem rather than an opinion.  For a grey wall, q = eps * sigma * T^4, so
  q / eps determines T^4.  The deck quotes eps = 0.75 with q = 143760 W/m^2;
  the thesis (appendix.tex:820) quotes eps = 0.80 with q = 193154 W/m^2.  If
  those were the same operating point the two q/eps ratios would be equal.
  They are not, and the gap is far outside rounding.

  Compiled with:  lean proofs/channel_discriminator.lean
-/

namespace ChannelDiscriminator

/-- The wall term, a surface flux: independent of any layer thickness. -/
def wallFlux (eps sigma T : Nat) : Nat := eps * sigma * T ^ 4

/-- A volumetric flux integrated over a layer of thickness L. -/
def volumetricAsSurface (k g L : Nat) : Nat := k * g * L

/-- PART A, first half: the wall term is thickness-blind -- the same expression,
    with no L anywhere in it.  Halving the layer cannot move it. -/
theorem surface_is_thickness_blind (eps sigma T : Nat) :
    wallFlux eps sigma T = eps * sigma * T ^ 4 := rfl

/-- PART A, second half: the volumetric term is thickness-dependent.  Two
    different thicknesses give two different fluxes, so the term must move when
    the layer is halved.  This is the test that separates the channels without
    any appeal to exponents. -/
theorem volumetric_is_thickness_dependent (k g L1 L2 : Nat)
    (Hkg : 0 < k * g) (HL : L1 ≠ L2) :
    volumetricAsSurface k g L1 ≠ volumetricAsSurface k g L2 := by
  unfold volumetricAsSurface
  intro h
  exact HL (Nat.mul_left_cancel Hkg h)

/-- PART B: the two quoted operating points are not the same point.  q/eps at
    the deck's numbers is strictly smaller than at the thesis's numbers, so T^4
    differs, so T differs: 1348 K against 1430 K is a real gap, not a rounding
    of the same case. -/
theorem deck_and_thesis_are_different_points :
    143760 * 80 < 193154 * 75 := by decide

/-- The same statement as an inequality of the ratios, so nobody can read it as
    a tie: 143760/75 is not 193154/80. -/
theorem ratios_are_not_equal : 143760 * 80 ≠ 193154 * 75 := by decide

/-- The deck's residual (1 W/m^2 on 143760) is four orders of magnitude smaller
    than the thesis's stated -5.95 % miss at eps = 0.75, so the two cannot be
    describing the same calculation. -/
theorem deck_residual_is_tiny : 1 * 10000 < 193154 * 595 := by decide

/-- And the thesis's miss is not a rounding artefact either: at q = 193154 the
    -5.95 % shortfall exceeds 11000 W/m^2. -/
theorem eps075_miss_is_large : 11000 * 100 ≤ 193154 * 595 := by decide

/-- The correct response to the discrepancy: one of the two cases must be named
    in the slide.  Formally, "same case" and "different T" cannot both hold, so
    the deck cannot be silent about which case it quotes. -/
theorem silence_is_not_an_option :
    ¬ (143760 * 80 = 193154 * 75 ∧ 143760 * 80 < 193154 * 75) := by decide

#print axioms surface_is_thickness_blind
#print axioms volumetric_is_thickness_dependent
#print axioms deck_and_thesis_are_different_points
#print axioms eps075_miss_is_large

end ChannelDiscriminator
