-- Page arithmetic for the explicit-author-decision record dated 2026-11-28 WIB.
-- Scope: this file proves ONLY the integer/rational arithmetic behind the page
-- budget. The claim that closing the gap would delete artifact-backed numbers is
-- an audit finding grounded in chapter file:line citations in the decision
-- records, NOT in this proof (prover credit is name-only, not claim identity).
--
-- Source constants re-read this turn from the canonical root's main.toc
-- (built 2026-11-28 01:04:34, same bytes as scratch thesis_strict_p6/main.toc):
--   contentsline chapter: Ch1 1, Ch2 12, Ch3 67, Ch4 99, Ch5 143, REFERENCES 148.

-- Ch1..Ch5 body span = REFERENCES folio - Ch1 folio = 148 - 1 = 147 pages.
example : (148 - 1 : Nat) = 147 := by decide

-- Residual above the <=100-page body target = 147 - 100 = 47 pages.
example : (147 - 100 : Nat) = 47 := by decide

-- Chapter spans sum to the same 147 pages (no double counting of boundaries).
example : (12 - 1) + (67 - 12) + (99 - 67) + (143 - 99) + (148 - 143) = (147 : Nat) := by decide

-- Individual spans: Ch1 11, Ch2 55, Ch3 32, Ch4 44, Ch5 5.
example : (12 - 1 : Nat) = 11 := by decide
example : (67 - 12 : Nat) = 55 := by decide
example : (99 - 67 : Nat) = 32 := by decide
example : (143 - 99 : Nat) = 44 := by decide
example : (148 - 143 : Nat) = 5 := by decide
example : (11 + 55 + 32 + 44 + 5 : Nat) = 147 := by decide

-- Feasibility bound: 47/147 ~= 32% of the body must be removed.
-- 32% of 147 is 47.04 pages, so removing 47 pages is (just) within 32%;
-- 31% of 147 is 45.57 pages, so 31% is NOT enough. Hence "~32%".
example : (47 * 100 : Nat) <= 147 * 32 := by decide
example : (147 * 31 : Nat) < 47 * 100 := by decide

-- Same bound over exact rationals: 47/147 lies strictly between 31% and 32%.
example : (31 / 100 : Rat) < 47 / 147 := by native_decide
example : (47 / 147 : Rat) < 32 / 100 := by native_decide

-- No single chapter below 47 pages can be removed alone to close the gap;
-- Ch4 is 44 pages, so deleting all of Results still leaves 3 pages over target.
example : (147 - 44 : Nat) = 103 := by decide
example : (103 - 100 : Nat) = 3 := by decide
-- Ch2 is the only chapter with >= 47 pages; removing it overshoots to 92.
example : (147 - 55 : Nat) = 92 := by decide
example : (92 < 100 : Prop) := by decide

-- Section sacrifice menu arithmetic (whole-chapter options).
example : (147 - 32 : Nat) = 115 := by decide   -- remove all Ch3
example : (147 - 11 - 5 : Nat) = 131 := by decide -- remove Ch1 + Ch5
example : (11 + 32 + 5 : Nat) = 48 := by decide  -- Ch1 + Ch3 + Ch5
example : (147 - 48 : Nat) = 99 := by decide     -- only whole-chapter triple <= target


-- Amendment 02:01:02 WIB: sibling t_af4a4b4e added reader-facing gate
-- disclosure and forced a rebuild; fresh main.toc folios are
-- Ch1 1, Ch2 12, Ch3 67, Ch4 99, Ch5 144, REFERENCES 149.
example : (149 - 1 : Nat) = 148 := by decide
example : (148 - 100 : Nat) = 48 := by decide
example : (12 - 1) + (67 - 12) + (99 - 67) + (144 - 99) + (149 - 144) = (148 : Nat) := by decide
example : (144 - 99 : Nat) = 45 := by decide
example : (149 - 144 : Nat) = 5 := by decide
example : (11 + 55 + 32 + 45 + 5 : Nat) = 148 := by decide

-- 48/148 = 32.43..% lies strictly between 32% and 33%; "~32.4%" is honest.
example : (148 * 32 : Nat) < 48 * 100 := by decide
example : (48 * 100 : Nat) <= 148 * 33 := by decide
example : (32 / 100 : Rat) < 48 / 148 := by native_decide
example : (48 / 148 : Rat) < 33 / 100 := by native_decide

-- Fresh section sacrifice menu arithmetic.
example : (148 - 45 : Nat) = 103 := by decide  -- remove all Ch4
example : (103 - 100 : Nat) = 3 := by decide
example : (148 - 55 : Nat) = 93 := by decide   -- remove all Ch2
example : (93 < 100 : Prop) := by decide
example : (148 - 32 : Nat) = 116 := by decide  -- remove all Ch3
example : (148 - 11 - 5 : Nat) = 132 := by decide -- remove Ch1 + Ch5
example : (11 + 32 + 5 : Nat) = 48 := by decide  -- Ch1 + Ch3 + Ch5
example : (148 - 48 : Nat) = 100 := by decide    -- smallest triple <= target
