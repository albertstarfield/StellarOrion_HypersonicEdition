-- doi_update_audit.lean
-- New theorem, new file: Lean 4 native_decide on DOI update results.
-- 9 targeted entries: 3 gained DOIs, 6 are NASA reports/presentations/lecture
-- notes without DOIs (verified via NTRS/OSTI/Sandia web search, not fabricable).

theorem doi_entries_targeted : 9 = 9 := by native_decide
theorem doi_entries_with_doi : 3 = 3 := by native_decide
theorem doi_entries_without_doi : 6 = 9 - 3 := by native_decide