-- PROVE REFUTATION: concrete counterexample to the universal claim
-- "every figure caption in the canonical thesis chapters is short (<= 120 chars)".
-- Before the edit, Figure fig:tps_balance carried a 1508-char caption
-- (chapter_04_results.tex:384), refuting the claim.
namespace CaptionMoveRefutation

inductive Figure where
  | tpsBalance
  | flowchartCh1
deriving DecidableEq, Repr

def InCanonicalChapter : Figure -> Prop
  | .tpsBalance => True
  | .flowchartCh1 => True

def CaptionLength : Figure -> Nat
  | .tpsBalance => 1508
  | .flowchartCh1 => 448

def IsLong (f : Figure) : Prop := CaptionLength f > 120

def AllCaptionsShort : Prop :=
  ∀ f : Figure, InCanonicalChapter f -> ¬ IsLong f

def witness : Figure := .tpsBalance

theorem witness_in_canonical : InCanonicalChapter witness := by
  simp [witness, InCanonicalChapter]

theorem witness_is_long : IsLong witness := by
  simp [witness, IsLong, CaptionLength]

theorem refutation : ¬ AllCaptionsShort := by
  intro h
  exact (h witness witness_in_canonical) witness_is_long
end CaptionMoveRefutation
