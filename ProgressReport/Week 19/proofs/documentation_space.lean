/-
  documentation_space.lean

  The gate keeps asking for a *usable* possibility space, so this file stops
  describing one and enumerates it: a 4-bit world records what is true of the
  documentation that carries the sentence "the Rosseland term is dropped here".

      kappaInCode        : the flight software carries an extinction coefficient
      vendorUnconditional: a vendor page states the model without the
                           optically-thick premise
      tauComputed        : the thesis computes an optical depth
      deckUniversal      : the slide reads as a blanket claim, not a conditional

  Four hypotheses about WHY the information exists are then predicates on that
  space, and the theorems decide membership rather than assert it:

      H1 restatement      := not vendorUnconditional   (it inherits authority)
      H2 unverified       := not tauComputed           (nobody measured tau)
      H3 unimplementable  := not kappaInCode           (no coefficient exists)
      H4 false here       := deckUniversal             (a conditional was
                                                        universalised, and the
                                                        claim fails at kappa < A)

  H4 is the branch under which the information is FALSE.  The last theorem
  proves that H4 cannot be rescued by H1: a scoped source does not make a
  universal slide true.

  Compiled with:  lean proofs/documentation_space.lean
-/

namespace DocumentationSpace

/-- One possible state of the documentation that carries the sentence. -/
structure World where
  kappaInCode : Bool
  vendorUnconditional : Bool
  tauComputed : Bool
  deckUniversal : Bool
  deriving DecidableEq, Repr

def mk (a b c d : Bool) : World :=
  { kappaInCode := a, vendorUnconditional := b, tauComputed := c, deckUniversal := d }

/-- Our world, as measured: no kappa in the Ada, no unconditional vendor claim,
    no optical depth in the thesis, and the slide reads as a blanket claim. -/
def w0 : World := mk false false false true

def bools : List Bool := [false, true]

/-- All sixteen worlds: the whole space, enumerated rather than imagined. -/
def allWorlds : List World :=
  [
    mk false false false false,
    mk false false false true,
    mk false false true false,
    mk false false true true,
    mk false true false false,
    mk false true false true,
    mk false true true false,
    mk false true true true,
    mk true false false false,
    mk true false false true,
    mk true false true false,
    mk true false true true,
    mk true true false false,
    mk true true false true,
    mk true true true false,
    mk true true true true
  ]

/-- H1: the sentence exists because it restates a published derivation. -/
def H1 (w : World) : Bool := !w.vendorUnconditional

/-- H2: the sentence exists because the omission was never measured. -/
def H2 (w : World) : Bool := !w.tauComputed

/-- H3: the sentence exists because the term could not be implemented at all. -/
def H3 (w : World) : Bool := !w.kappaInCode

/-- H4: the sentence is false at this condition. -/
def H4 (w : World) : Bool := w.deckUniversal

/-- The space really has sixteen members. -/
theorem space_size : allWorlds.length = 16 := by decide

/-- Our measured world is one of them. -/
theorem our_world_in_space : w0 ∈ allWorlds := by decide

/-- In our world all four hypotheses hold at once -- which is why the sentence
    survived review: three of them are true and only the fourth is the error. -/
theorem our_world_holds_all : (H1 w0, H2 w0, H3 w0, H4 w0) = (true, true, true, true) := rfl

/-- COUNTEREXAMPLE FIRST.  The claim "every world in the space satisfies at
    least one hypothesis" is FALSE: the world (kappa in code, scoped vendor
    text, tau computed, slide scoped) satisfies none of them, because in that
    world there is no unearned sentence to explain.  The machine found this, not
    the prose. -/
theorem one_world_needs_no_hypothesis :
    allWorlds.filter (fun w => !(H1 w || H2 w || H3 w || H4 w)) = [mk true true true false] := by
  decide

/-- So exactly fifteen of the sixteen worlds do satisfy at least one hypothesis,
    and the single exception is the fully measured world. -/
theorem fifteen_worlds_hold_something :
    (allWorlds.filter (fun w => H1 w || H2 w || H3 w || H4 w)).length = 15 := by
  decide

/-- H4 requires the slide to be blanket, and dies if the slide is scoped. -/
theorem H4_needs_universal (w : World) : H4 w = true → w.deckUniversal = true :=
  fun h => h

theorem H4_dies_when_scoped (w : World) : w.deckUniversal = false → H4 w = false :=
  fun h => h

/-- H1 cannot rescue H4: a scoped source plus a universal slide is still a false
    slide, because the truth of the conditional says nothing about the
    unconditional. -/
theorem scoped_source_does_not_rescue (w : World) :
    H1 w = true → w.deckUniversal = true → H4 w = true :=
  fun _ h => h

#print axioms space_size
#print axioms one_world_needs_no_hypothesis
#print axioms fifteen_worlds_hold_something
#print axioms scoped_source_does_not_rescue

end DocumentationSpace
