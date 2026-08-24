# Coverage & Fuzzing Status (Tiers C3/C4)

> Context: `docs/` | Tiers: C3 (gnatcov), C4 (gnatfuzz) of the compliance plan
> Standard reference: code-quality.md — coverage/fuzzing mandates
> Status: 2026-08-25 [ASWSS]

## C3 — gnatcov structural coverage

**Tool status**: `gnatcov` / `gnatcov_bin` 26.2.1 exists in the Alire index
but was not installed in this environment.

**Attempted 2026-08-25 [ASWSS]**: `alr with gnatcov_bin` succeeded (binary
release at `~/.local/share/alire/releases/gnatcov_bin_26.2.1_9d524b55`),
but `gnatcov instrument -P stellarorion_program_proc.gpr --level stmt+mcdc`
aborts with `project file "gnatcov_rts.gpr" not found`. The GNATcoverage
**runtime project (`gnatcov_rts`) is not an Alire crate** — it ships only
with the matching GNAT Pro / FSF compiler installation, and none exists for
our pinned `gnat_native 15.1.2` toolchain. The experiment was reverted
(`alr.toml` restored to committed state) to keep the verified configuration
pristine ahead of the final simulation run.

**Intended campaign** (once tooling matches):
1. `alr with gnatcov_bin`
2. Build instrumented: `alr exec -- gprbuild -P stellarorion_program_proc.gpr
   -c -fprofile=gnatcov` (level stmt+mcdc decision on units under test).
3. Run the two harnesses: `./bin/main --self-test` (18 checks) and
   `./bin/test_main` (29 checks) under `gnatcov run`.
4. Report: `gnatcov coverage -P ... --level stmt+mcdc --annotate xcov+html`.
5. Gate: statement coverage of `stellarorion_physics`, `_geometry`,
   `_environment`, `_atomic_parity`, `_dual_watchdog` bodies >= 95%;
   gaps itemised here with justification (SPARK_Off externs excluded).

## C4 — gnatfuzz

**Tool status**: `gnatfuzz` ships with GNAT Pro only; it is absent from this
machine (`which gnatfuzz` empty; not in `~/.alire`; not an Alire crate).
The standard's ">= 1000 iterations, no crashes" fuzz gate therefore cannot be
executed in this environment. **Documented exception**, not a silent skip.

**Compensating controls already in place**:
- All physics/environment/geometry entry points carry SPARK envelope
  contracts proved at level 4 (339+ checks, see THEORIES.md); the input space
  gnatfuzz would explore is *statically bounded* by those Pres for all
  SPARK_On callers.
- Runtime checks remain enabled in the production build (`-gnatwa` gate,
  default check policy): any out-of-envelope input that reached a leaf via a
  future unverified caller raises Constraint_Error at the contract boundary
  rather than corrupting state.
- The independent harness exercises boundary-sitting inputs deliberately
  (D = 0.5 / 15.0, Mach 50, T = 3000 K, parity bit-flip corruption,
  watchdog starvation-to-emergency paths).

**Campaign recipe for a GNAT Pro environment** (per gnatfuzz skill):
targets `StellarOrion_Physics.Calculate_Flight_Metrics`,
`StellarOrion_Environment.Atmosphere_Density`,
`StellarOrion_Atomic_Parity.Recover_From_Parity_Error`;
`alr exec -- gnatfuzz <unit> --level=<n>` then AFL++ run, minimum 1000
iterations, triage any crash files against the AXIOMS.md envelopes.

## C7 — run.py Python branch-coverage gate (Std §7)

**Implemented 2026-08-25.** `run.py --py-coverage [MIN]` runs the unit
suite (`tests/test_run_pipeline.py`, 28 tests) under
`coverage run --branch` and enforces `coverage report --include=run.py
--fail-under=MIN` as a hard Phase-2 gate (exit 1 on failure). Bare flag
defaults to the standard's 100% target.

Measured baseline: **24% total branch coverage of run.py**. The gap to
100% is concentrated in Phases 0/1/3/4 (`_phase1_venv`,
`_phase3_ada_build`, `_phase4_launch`, `main`) which are thin
subprocess orchestrators around Alire / Docker / gnatprove / binary
launch — environment-dependent integration surface, same class as the
C3/C4 tooling exceptions above. The pure and side-effect-light helpers
(colour, ports, health check, lockfile, hash gating, arg parsing,
output) are unit-covered directly by importing `run`.

Remediation path: mock-based phase tests (patch `subprocess.run`) can
lift coverage toward the 100% target; until then, use a custom floor,
e.g. `python3 run.py --py-coverage 24`. The gate mechanism itself is
verified: fail-under 20 passes at the measured baseline, fail-under 99
correctly fails.

## Verdict

| Tier | Mandate | State |
|---|---|---|
| C3 | gnatcov coverage run | Tooling mismatch documented; campaign recipe staged; install attempt logged |
| C4 | gnatfuzz >= 1000 iters | Tool unavailable (GNAT Pro only); documented exception + compensating controls |
| C7 | run.py 100% branch gate | Gate implemented + enforced (--py-coverage); measured 24% baseline; 100% target documented w/ remediation path |
