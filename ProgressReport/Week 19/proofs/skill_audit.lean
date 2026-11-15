-- skill_audit.lean
-- Axiom test for the two library edits made in this turn, plus the
-- counterexample that killed the first draft of Claim B.
--
-- Claim A: a line-oriented scanner counts PLACEMENT, not vocabulary, so a
--          semantically complete paragraph contributes zero items.
-- Claim B (first draft, WRONG): "a label anchored at boxCentre - diamondHalf is
--          outside the diamond". Refuted: sharing a centre puts the anchor
--          exactly on the diamond's lower vertex, i.e. inside it. The true
--          statement needs the diamond's own centre above the box.
-- Claim B (repaired): with the diamond centred above the box, the anchor is
--          outside BOTH shapes -- it floats in the gap, which is what the
--          rendered artwork showed.

namespace SkillAudit

/-- One candidate line offered to the scanner: a marker at line start counts as
one item, a marker buried mid-sentence counts as none. -/
def counts (markerAtLineStart : Bool) : Nat :=
  if markerAtLineStart then 1 else 0

/-- Items found in a list of candidate lines. -/
def total : List Bool → Nat
  | [] => 0
  | b :: bs => counts b + total bs

/-- A prose paragraph arrives as one line whose marker is mid-sentence. -/
def inlineParagraph : List Bool := [false]

/-- A correctly shaped block: heading line plus three item lines. -/
def properBlock : List Bool := [true, true, true, true]

/-- COUNTEREXAMPLE to "well-phrased prose counts as hypotheses": the paragraph
is semantically complete and yields nothing. -/
theorem inline_prose_yields_zero : total inlineParagraph = 0 := by decide

/-- Marker words do not help when they are not at a line start. -/
theorem count_tracks_placement_only : total [false, false, false] = 0 := by decide

/-- The shaped block is seen: heading plus three items. -/
theorem proper_block_seen : total properBlock = 4 := by decide

/-- A paragraph can never be mistaken for N hypotheses, however many times the
word appears: items are bounded by lines. -/
theorem items_le_lines (ls : List Bool) : total ls ≤ ls.length := by
  induction ls with
  | nil => simp [total]
  | cons b bs ih =>
      cases b <;> simp [total, counts] <;> omega

/-! ### Claim B: the stray anchor -/

/-- Vertical span of a shape: lower edge and upper edge. -/
structure Span where
  lo : Int
  hi : Int
deriving DecidableEq, Repr

/-- A shape of half-height `h` centred at `c`. -/
def centred (c h : Int) : Span := ⟨c - h, c + h⟩

def inside (s : Span) (y : Int) : Prop := s.lo ≤ y ∧ y ≤ s.hi

/-- A label positioned from a BOX centre using the DIAMOND half-height. -/
def anchor (boxCentre diamondHalf : Int) : Int := boxCentre - diamondHalf

/-- First draft of the claim, kept as the recorded refutation: with one shared
centre the anchor is NOT outside the diamond -- it sits on the lower vertex. -/
theorem draft_claim_false (c hd : Int) (h : 0 < hd) :
    inside (centred c hd) (anchor c hd) := by
  simp [inside, centred, anchor]
  omega

/-- Repaired claim, part 1: if the diamond is taller than the box, the anchor
falls below the box it was measured from. -/
theorem anchor_below_box (cb hb hd : Int) (h : hb < hd) :
    ¬ inside (centred cb hb) (anchor cb hd) := by
  intro hin
  simp [inside, centred, anchor] at hin
  omega

/-- Repaired claim, part 2: if the diamond sits above the box -- the real
layout, decision at the higher y and process box below it -- the anchor also
falls below the diamond's lower vertex. So the string labels neither shape. -/
theorem anchor_below_diamond (cb cd _hb hd : Int) (hsep : cb < cd) :
    ¬ inside (centred cd hd) (anchor cb hd) := by
  intro hin
  simp [inside, centred, anchor] at hin
  omega

/-- Both at once: the duplicate label floats in the gap between the two shapes. -/
theorem anchor_in_the_gap (cb cd hb hd : Int) (hgt : hb < hd) (hsep : cb < cd) :
    ¬ inside (centred cb hb) (anchor cb hd) ∧
    ¬ inside (centred cd hd) (anchor cb hd) :=
  ⟨anchor_below_box cb hb hd hgt, anchor_below_diamond cb cd hb hd hsep⟩

/-- Two labels for one decision is provably not one. -/
theorem two_yes_labels_not_coherent : (2 : Nat) ≠ 1 := by decide

end SkillAudit
