-- Dependency order for Chapter 2: Knudsen classification must precede the methods it justifies.
-- Line numbers are the VERIFIED post-move \section line numbers in
-- ProgressReport/CurrentThesisFinalReport/chapter_02_literature_review.tex
-- and the pre-move numbers from canonical_chapter_02.pre.tex (scratch backup).
namespace Chapter2Order

abbrev Pos := Nat

def Precedes (a b : Pos) : Prop := a < b

-- Pre-move section lines (HEAD working copy before the relocation).
def old_fundamentals : Pos := 42
def old_cfd          : Pos := 633
def old_kinetic      : Pos := 884
def old_dsmc         : Pos := 960
def old_knudsen      : Pos := 1037

-- Post-move section lines (canonical file after the relocation).
def new_fundamentals : Pos := 42
def new_knudsen      : Pos := 138
def new_aerothermo   : Pos := 165
def new_cfd          : Pos := 660
def new_kinetic      : Pos := 911
def new_dsmc         : Pos := 987

-- Dependency contract: fundamentals first; Kn classifies the regime and
-- therefore precedes both continuum CFD and the kinetic/DSMC treatment.
def ValidOrder (fund kn cfd kin dsmc : Pos) : Prop :=
  Precedes fund kn ∧ Precedes kn cfd ∧ Precedes kn kin ∧ Precedes kn dsmc ∧ Precedes kin dsmc

-- CONCRETE COUNTEREXAMPLE (PROVE REFUTATION):
-- The original order violates the Kn-before-CFD/kinetic/DSMC dependencies.
-- At line 1037 Kn came AFTER CFD (633), kinetic theory (884) and DSMC (960).
theorem old_order_is_not_dependency_correct : ¬ ValidOrder old_fundamentals old_knudsen old_cfd old_kinetic old_dsmc := by
  unfold ValidOrder Precedes old_fundamentals old_knudsen old_cfd old_kinetic old_dsmc
  decide

theorem concrete_pair_violation : ¬ Precedes old_knudsen old_dsmc := by
  unfold Precedes old_knudsen old_dsmc
  decide

-- The relocated order satisfies every dependency, checked by decision procedure.
theorem new_order_is_dependency_correct : ValidOrder new_fundamentals new_knudsen new_cfd new_kinetic new_dsmc := by
  unfold ValidOrder Precedes new_fundamentals new_knudsen new_cfd new_kinetic new_dsmc
  decide

-- The move strictly repairs the broken Kn-vs-DSMC relation.
theorem repair_flips_the_relation :
    (¬ Precedes old_knudsen old_dsmc) ∧ Precedes new_knudsen new_dsmc := by
  constructor
  · exact concrete_pair_violation
  · unfold Precedes new_knudsen new_dsmc
    decide

end Chapter2Order
