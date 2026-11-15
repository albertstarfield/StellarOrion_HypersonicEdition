/-
  narration_audit.lean

  The inference the Week 19 deck rests on, written down so it can be attacked.

  The deck's verification tool compares, for every frame, the body stored in the
  speaker notes with the text painted on the slide.  It reports "56 of 56
  frames match".  Two claims were made from that number in the report, and they
  are not the same claim:

    (1) the repair is sound: rewriting every recorded body from the visible
        text makes the audit pass, for any deck whatsoever;
    (2) the audit is not a truth test: agreement between notes and slide can
        hold while the sentence they share is false.

  (1) is proved below as `repair_passes`.  (2) is proved as
  `agreement_is_not_truth`, by exhibiting a deck whose single frame has
  recorded = visible = "206 pages" and an independent check that fails.
  `agreement_is_achievable` shows the predicate is not vacuously false: a deck
  that agrees and is also right exists.  `passCount_eq_length` connects the
  printed fraction to the predicate, so "56 of 56" means "the filter kept every
  frame", nothing more.

  What is NOT in here, and cannot be: that the fifty-six sentences on the
  slides are true of the world.  That step is empirical; its replacement check
  is the source cited on each frame and, for the page count, `pdfinfo` on
  CurrentThesisFinalReport/main.pdf.
-/

/-- One frame: what the notes say, what the slide shows, and whether the
sentence agrees with the source it cites.  The third field is the independent
check; the audit never reads it. -/
structure Frame where
  recorded : String
  visible : String
  matches_source : Bool
  deriving Repr

/-- The audit: every frame's recorded body equals its visible body. -/
def auditOK (d : List Frame) : Prop := ∀ f ∈ d, f.recorded = f.visible

/-- What the tool does to a frame: the notes are regenerated from the slide. -/
def repairFrame (f : Frame) : Frame := { f with recorded := f.visible }

/-- And to the whole deck. -/
def repair (d : List Frame) : List Frame := d.map repairFrame

/-- (1) The repair passes the audit on any deck, no assumption about content. -/
theorem repair_passes (d : List Frame) : auditOK (repair d) := by
  intro f hf
  obtain ⟨g, _hg, rfl⟩ := List.mem_map.mp hf
  simp [repairFrame]

/-- The number the tool prints: how many frames have equal strings. -/
def passCount : List Frame → Nat
  | [] => 0
  | f :: t => (if f.recorded = f.visible then 1 else 0) + passCount t

/-- "56 of 56" is exactly "the counter kept every frame". -/
theorem passCount_eq_length (d : List Frame) (h : auditOK d) : passCount d = d.length := by
  induction d with
  | nil => rfl
  | cons f t ih =>
      have hf : f.recorded = f.visible := h f (by simp)
      have ht : auditOK t := fun g hg => h g (List.mem_cons.mpr (Or.inr hg))
      have ih' := ih ht
      simp only [passCount, hf, ite_true, List.length_cons]
      omega

/-- (2a) Agreement can hold while the independent check fails.  This is the
counterexample to reading the audit as a truth test. -/
theorem agreement_is_not_truth :
    ∃ d : List Frame, auditOK d ∧ ∃ f ∈ d, f.matches_source = false := by
  refine ⟨[{ recorded := "206 pages", visible := "206 pages", matches_source := false }], ?_, ?_⟩
  · intro f hf
    rw [List.mem_singleton] at hf
    cases hf
    rfl
  · exact ⟨{ recorded := "206 pages", visible := "206 pages", matches_source := false }, by simp, rfl⟩

/-- (2b) The predicate is not vacuously false: a deck that agrees and is right
also exists, so the audit is silent about which of the two it is looking at. -/
theorem agreement_is_achievable :
    ∃ d : List Frame, auditOK d ∧ ∀ f ∈ d, f.matches_source = true := by
  refine ⟨[{ recorded := "236 pages", visible := "236 pages", matches_source := true }], ?_, ?_⟩
  · intro f hf
    rw [List.mem_singleton] at hf
    cases hf
    rfl
  · intro f hf
    rw [List.mem_singleton] at hf
    cases hf
    rfl

/-- The two decks of (2a) and (2b) are indistinguishable to the audit, which is
the whole point: the tool cannot separate them. -/
theorem audit_cannot_separate :
    ∃ d₁ d₂ : List Frame,
      auditOK d₁ ∧ auditOK d₂ ∧
      (∃ f ∈ d₁, f.matches_source = false) ∧
      (∀ f ∈ d₂, f.matches_source = true) := by
  obtain ⟨d₁, h₁, h₁'⟩ := agreement_is_not_truth
  obtain ⟨d₂, h₂, h₂'⟩ := agreement_is_achievable
  exact ⟨d₁, d₂, h₁, h₂, h₁', h₂'⟩

#print axioms repair_passes
#print axioms passCount_eq_length
#print axioms agreement_is_not_truth
#print axioms agreement_is_achievable
#print axioms audit_cannot_separate
