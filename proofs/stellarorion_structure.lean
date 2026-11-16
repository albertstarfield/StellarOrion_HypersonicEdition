/-
  Repository-root structure audit (Lean 4 core only).

  This file previously contained text that is not valid Lean: it imported the
  non-existent module `Data.Paths`, used `∃ (x : Path) | ...` binders, referenced
  free identifiers such as `for_someone/StellarOrion_HypersonicEdition/sparta`,
  and carried its own trailing comment `-- no, this is wrong`. Nothing in it could
  ever be checked, so it asserted nothing.

  It is replaced by an explicit finite model of the claimed subdirectories plus a
  proof that the original conjunction FAILS: `utils/` and `for_someone/` are not
  directories at the repository root. Presence values below are the observation
  recorded in ~/.hermes/logs/audit/repo_dirs_*.log (ls -d at the repo root,
  /Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition,
  2026-11-16): sparta, src, scripts, obj exist; utils and for_someone do not
  (`for_someone` is the PARENT directory of this repository, not a child).
-/

namespace RepoStructure

inductive Dir
  | sparta
  | src
  | utils
  | scripts
  | obj
  | forSomeone
  deriving DecidableEq, Repr

/-- Presence of each claimed child directory, as observed on disk. -/
def present : Dir → Bool
  | .sparta => true
  | .src => true
  | .utils => false
  | .scripts => true
  | .obj => true
  | .forSomeone => false

/-- The four directories the original file claimed and that really are there. -/
theorem confirmed_dirs_present :
    present .sparta = true ∧ present .src = true ∧
    present .scripts = true ∧ present .obj = true := by
  decide

/-- `utils/` is absent from the root, so that conjunct of the old claim is false. -/
theorem utils_absent : present .utils = false := rfl

/-- `for_someone/` is absent from the root (it is the repository's parent). -/
theorem for_someone_absent : present .forSomeone = false := rfl

/-- Hence the old statement `∀ d, present d = true` is refuted. -/
theorem original_claim_refuted : ¬ ∀ d : Dir, present d = true := by
  intro h
  have h' : present .utils = true := h .utils
  rw [utils_absent] at h'
  exact Bool.noConfusion h'

/-- The surviving part of the claim, restated honestly. -/
theorem confirmed_dirs_present' :
    ∀ d : Dir, d ≠ .utils → d ≠ .forSomeone → present d = true := by
  intro d h1 h2
  cases d
  · rfl
  · rfl
  · exact absurd rfl h1
  · rfl
  · rfl
  · exact absurd rfl h2

end RepoStructure

#check @RepoStructure.confirmed_dirs_present
#check @RepoStructure.original_claim_refuted
#check @RepoStructure.confirmed_dirs_present'
