-- A/B refutation model for the methodology_derivation.png rescale.
-- Retry refresh: receipts re-earned in the resumed subagent turn.
-- Both latexmk builds used identical sources except chapter_03_methodology.tex:13:
--   build A: width=\textwidth        -> Figure 3.1 image band 152-483pt (331pt)
--   build B: width=0.75\textwidth    -> Figure 3.1 image band 135-383pt (248pt)
-- In BOTH builds the chapter-opening page (Theory Anchors, page 103) has the
-- same 430.6pt gap between its last text band (288-298pt) and the folio (729pt).
-- Gap units below are tenths of a point; page widths are tenths of a point.

def textWidthTenths : Nat := 4136          -- 413.6pt letter text block
def aspectNum : Nat := 1855                -- PNG native height
def aspectDen : Nat := 1662                -- PNG native width

-- Included height in tenths of a point at an integer width percentage w.
def includedHeight (w : Nat) : Nat :=
  (textWidthTenths * w * aspectNum) / (100 * aspectDen)

def gapBeforeTenths : Nat := 4306          -- A build (width=\textwidth)
def gapAfterTenths : Nat := 4306           -- B build (width=0.75\textwidth)

-- The rescale narrows the figure, hence lowers its included height.
theorem figure_height_decreases :
    includedHeight 75 < includedHeight 100 := by
  decide

-- ...but the measured gap on the Theory Anchors page is unchanged and positive.
theorem gap_not_reclaimed :
    gapAfterTenths = gapBeforeTenths ∧ gapAfterTenths > 0 := by
  decide

-- Therefore a narrower figure alone does not reclaim the gap: a model that
-- only checks "width decreased" cannot conclude "dead space removed".
theorem width_decrease_does_not_imply_gap_closed :
    (includedHeight 75 < includedHeight 100) →
    gapAfterTenths ≠ 0 := by
  intro _h
  decide
