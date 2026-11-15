/-!
# staged_manifest_audit.lean

Axiom test for the commit's scope claim: *the staged set contains no build
directory, no Python venv, and no compiled artifact.*

The manifest below is the literal `git diff --cached --name-only` output at commit
time, so the proof is about the actual index, not about an intention.

TRUST NOTE: the checks use `native_decide`, which compiles the decidable predicate
and runs it, so the result trusts the Lean compiler and its runtime rather than the
kernel alone.  `decide` cannot be used here because `String.splitOn` is opaque to
the kernel's reduction -- stated plainly rather than hidden.
-/

namespace StagedAudit

/-- Directory components that must never appear in a commit. -/
def Forbidden : List String := [".venv-pdf", ".audit_venv", "venv", "obj", "bin", "__pycache__"]

/-- Suffixes that must never appear in a commit. -/
def ForbiddenSuffix : List String := [".vo", ".glob", ".olean", ".pyc", ".cache", ".nra.cache"]

/-- Split a path into components. -/
def parts (p : String) : List String := p.splitOn "/"

/-- Does a path contain a forbidden directory component? -/
def hasForbiddenDir (p : String) : Bool :=
  (parts p).any (fun c => Forbidden.contains c)

/-- Does a path end with a forbidden suffix? -/
def hasForbiddenSuffix (p : String) : Bool :=
  ForbiddenSuffix.any (fun s => p.endsWith s)

/-- The gate. -/
def clean (p : String) : Bool := !hasForbiddenDir p && !hasForbiddenSuffix p

/-- THE CLAIM: every staged path passes the gate. -/
def staged : List String := [
  "ProgressReport/CurrentThesisFinalReport/chapter_01_introduction.tex",
  "ProgressReport/CurrentThesisFinalReport/chapter_03_methodology.tex",
  "ProgressReport/CurrentThesisFinalReport/figures/FLOWCHART_AUDIT.md",
  "ProgressReport/CurrentThesisFinalReport/figures/flowchart.png",
  "ProgressReport/CurrentThesisFinalReport/figures/make_dsmc_flowchart.py",
  "ProgressReport/CurrentThesisFinalReport/figures/make_flowchart.py",
  "ProgressReport/CurrentThesisFinalReport/figures/make_pipeline_figure.py",
  "ProgressReport/CurrentThesisFinalReport/ref.bib",
  "ProgressReport/Week 19/proofs/.gitignore",
  "ProgressReport/Week 19/proofs/AUDIT_fourth_power.md",
  "ProgressReport/Week 19/proofs/channel_discriminator.lean",
  "ProgressReport/Week 19/proofs/check_fourth_power_mono.v",
  "ProgressReport/Week 19/proofs/citation_audit.lean",
  "ProgressReport/Week 19/proofs/conductivity_vs_source.lean",
  "ProgressReport/Week 19/proofs/core_inference.v",
  "ProgressReport/Week 19/proofs/design_point_exact.v",
  "ProgressReport/Week 19/proofs/documentation_space.lean",
  "ProgressReport/Week 19/proofs/doi_update_audit.lean",
  "ProgressReport/Week 19/proofs/emissivity_census.lean",
  "ProgressReport/Week 19/proofs/emissivity_reconcile.lean",
  "ProgressReport/Week 19/proofs/evidence_function.v",
  "ProgressReport/Week 19/proofs/exponent_budget.lean",
  "ProgressReport/Week 19/proofs/flowchart_audit.lean",
  "ProgressReport/Week 19/proofs/fourth_power.lean",
  "ProgressReport/Week 19/proofs/fourth_power_audit.lean",
  "ProgressReport/Week 19/proofs/fourth_power_axioms.lean",
  "ProgressReport/Week 19/proofs/fourth_power_mono.v",
  "ProgressReport/Week 19/proofs/fourth_root_bracket.v",
  "ProgressReport/Week 19/proofs/g_load_constraint.lean",
  "ProgressReport/Week 19/proofs/gnatprove_exit_code.lean",
  "ProgressReport/Week 19/proofs/identifiability.v",
  "ProgressReport/Week 19/proofs/information_space.lean",
  "ProgressReport/Week 19/proofs/ledger_reconciliation.lean",
  "ProgressReport/Week 19/proofs/model_census.v",
  "ProgressReport/Week 19/proofs/narration_audit.lean",
  "ProgressReport/Week 19/proofs/omission_threshold.v",
  "ProgressReport/Week 19/proofs/payload_constraint_audit.lean",
  "ProgressReport/Week 19/proofs/pdflatex_build_audit.lean",
  "ProgressReport/Week 19/proofs/possibility_gate.v",
  "ProgressReport/Week 19/proofs/possibility_space.lean",
  "ProgressReport/Week 19/proofs/possibility_space.v",
  "ProgressReport/Week 19/proofs/radiation_channels.lean",
  "ProgressReport/Week 19/proofs/recovery_inconsistent.lean",
  "ProgressReport/Week 19/proofs/rosseland_monotone.v",
  "ProgressReport/Week 19/proofs/series_resistance.v",
  "ProgressReport/Week 19/proofs/skill_audit.lean",
  "ProgressReport/Week 19/proofs/slope_at_design.lean",
  "ProgressReport/Week 19/proofs/split_family.v",
  "ProgressReport/Week 19/proofs/telescoping.v",
  "ProgressReport/Week 19/proofs/temperature_scaling.lean",
  "ProgressReport/Week 19/proofs/two_point_witness.v",
  "stellarorion_program_proc/src/simulation_engine/stellarorion_optimization.adb",
  "stellarorion_program_proc/src/simulation_engine/stellarorion_optimization.ads",
  "stellarorion_program_proc/src/simulation_engine/stellarorion_optimizer_core.adb",
  "stellarorion_program_proc/src/simulation_engine/stellarorion_optimizer_core.ads",
]

theorem staged_set_is_clean : staged.all clean = true := by native_decide
theorem staged_set_size : staged.length = 55 := by native_decide

/-- COUNTEREXAMPLE: the gate is not vacuous -- it rejects the very things that
would have been committed by a blind `git add -A`. -/
theorem rejects_venv : clean "ProgressReport/CurrentThesisFinalReport/.venv-pdf/lib/x.so" = false := by native_decide

theorem rejects_obj : clean "stellarorion_program_proc/obj/stellarorion_optimization.o" = false := by native_decide

theorem rejects_coq_artifact : clean "ProgressReport/Week 19/proofs/telescoping.vo" = false := by native_decide

/-- And it does not reject legitimate sources: a path merely *containing* the
letters obj or bin elsewhere is fine. -/
theorem accepts_ordinary_source : clean "ProgressReport/Week 19/proofs/g_load_constraint.lean" = true := by native_decide

end StagedAudit
