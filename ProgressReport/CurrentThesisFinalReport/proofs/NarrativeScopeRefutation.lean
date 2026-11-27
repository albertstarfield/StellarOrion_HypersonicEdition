-- PROVE REFUTATION: concrete counterexample to the universal claim
-- "every appendix section is described in Chapter 2 first".
namespace NarrativeScopeRefutation

inductive Section where
  | ch2Knudsen
  | appB3GnatproveDischarge
deriving DecidableEq, Repr

def InAppendix : Section -> Prop
  | .appB3GnatproveDischarge => True
  | _ => False

def DescribedInCh2 : Section -> Prop
  | .ch2Knudsen => True
  | .appB3GnatproveDischarge => False

def AllAppendixDescribed : Prop :=
  ∀ s : Section, InAppendix s -> DescribedInCh2 s

-- Concrete counterexample: Appendix B.3 (GNATprove discharge tables,
-- appendix.tex:196-234) is not described or motivated in Chapter 2.
def witness : Section := .appB3GnatproveDischarge

theorem witness_in_appendix : InAppendix witness := by
  simp [witness, InAppendix]

theorem witness_not_described : ¬ DescribedInCh2 witness := by
  simp [witness, DescribedInCh2]

theorem refutation : ¬ AllAppendixDescribed := by
  intro h
  exact witness_not_described (h witness witness_in_appendix)
end NarrativeScopeRefutation