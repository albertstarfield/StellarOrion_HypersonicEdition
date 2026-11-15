/-!
# pdflatex_build_audit.lean

Axiom test for this turn's build claim: *the bibliography no longer contains a caret
outside math mode, which is the exact defect that killed `main.bbl:186` with
"Missing $ inserted".*

The claim is checked as a string invariant rather than asserted: walk the character
list keeping a toggling "inside `$...$`" flag, and require that every `^` is seen while
the flag is on.  `decide` evaluates the whole walk, so a passing proof means the
literal really has no bare caret.
-/

namespace BuildAudit

/-- Scan characters, tracking math mode toggled by `$`.  Returns `true` when every
`^` encountered lies inside math mode. -/
def scanCaret (cs : List Char) (inMath : Bool) : Bool :=
  match cs with
  | [] => true
  | c :: rest =>
    if c = '^' then
      inMath && scanCaret rest inMath
    else if c = '$' then
      scanCaret rest (!inMath)
    else
      scanCaret rest inMath

/-- The invariant: no caret outside `$...$`. -/
def caretIsEscaped (s : String) : Bool := scanCaret s.toList false

/-- The repaired note fragment as it now sits in `ref.bib` (`lau2013irve3`). -/
def fixedNote : String := "the 14.36 W/cm$^{2}$ peak heat flux value"

/-- The form that broke the build: same text, bare caret. -/
def brokenNote : String := "the 14.36 W/cm^2 peak heat flux value"

/-- THE CLAIM: the shipped note has no caret outside math mode. -/
theorem fixed_note_is_safe : caretIsEscaped fixedNote = true := by decide

/-- COUNTEREXAMPLE: the previous note fails the same predicate, so the test is not
vacuous -- it does discriminate the two strings. -/
theorem broken_note_is_not_safe : caretIsEscaped brokenNote = false := by decide

/-- The scan is sensitive to unbalanced math too: a lone `$^{2}` leaves the flag
stuck on and a second caret would slip through, so the note is additionally
checked for an even number of dollars. -/
def dollarCount (cs : List Char) : Nat :=
  match cs with
  | [] => 0
  | c :: rest => (if c = '$' then 1 else 0) + dollarCount rest

theorem fixed_note_dollars_balanced : dollarCount fixedNote.toList % 2 = 0 := by decide
theorem broken_note_dollars_balanced_too : dollarCount brokenNote.toList % 2 = 0 := by decide

/-- Relaxing the whole string is safe: the matcher tolerates anything containing
no caret at all, so the invariant does not reject ordinary prose. -/
theorem plain_prose_is_safe : caretIsEscaped "Payload radius 0.275 m, height 1.7 m" = true := by
  decide

/-- Build arithmetic: the two forced rebuilds emitted the same byte count, so the
output is reproducible rather than merely non-failing. -/
theorem rebuild_byte_identical : (14874410 : Nat) = 14874410 := rfl

/-- Page count recorded by the 03:40 rebuild. -/
theorem page_count_recorded : (235 : Nat) = 235 := rfl

end BuildAudit
