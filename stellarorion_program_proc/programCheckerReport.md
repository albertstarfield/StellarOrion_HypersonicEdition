# Program Checker Report

Full validation sweep of `stellarorion_program_proc` at commit `34007e11`
(the state immediately after the lateral-conduction work in `fdb39b95` /
`2b30f313`).

Generated 2026-10-15 (UTC 2026-10-15T23:14Z). Every command below was run
from `stellarorion_program_proc/`; exit codes and tool versions are the
measured values, not descriptions.

## Environment

| Tool | Version | Invocation |
| :--- | :--- | :--- |
| Python (validation venv) | 3.12.15 | `./venv_validation/bin/python` |
| ruff | 0.16.10 | `./venv_validation/bin/ruff check .` |
| pyrefly | 1.3.2 | see per-check section for the full flag set |
| crosshair | crosshair-tool | `./venv_validation/bin/crosshair check` |
| GNAT | 16.1.0 | `alr exec -- gnat` |
| GNATprove | FSF 16.1.0 | via `prove.sh --level 4` |

Note on the validation venv: `run.py`'s own pyrefly gate uses
`venv_validation/bin/pyrefly` **with `--python-interpreter-path` pointing at
the venv interpreter**. Without that flag pyrefly resolves scipy/sklearn
against the homebrew 3.15 interpreter and reports three spurious
`missing-import` errors at `ada_pinn_wrapper.py:971/1008/1009`. Those are an
artifact of the invocation, not of the code; the flag set below is the one
the pipeline actually uses.

## Summary

| # | Check | Exit | Verdict |
| :-- | :--- | :--: | :--- |
| 1 | ruff | 0 | **PASS** — All checks passed |
| 2 | pyrefly | 0 | **PASS** — 0 errors |
| 3 | crosshair | 0 | **PASS (vacuous)** — no checkable functions found |
| 4 | sabotage_verifier | 1 | **TAINTED** — 1 CRITICAL, 0 HIGH, 39 MEDIUM, 144 LOW |
| 5 | gnatprove --level=4 | 1* | **PROOF INCOMPLETE** — 474/533 discharged, **31 unproved**; wrapper crashed on an unbound variable |
| 6 | Ada unit tests (`bin/test_main`) | 0 | **PASS** — 29/29 |

---

## 1. ruff

```
./venv_validation/bin/ruff check .
```

**Exit 0. All checks passed.**

Scope is the whole project tree (not only `src/`), so `scripts/`, `src/`,
and `run.py` are all included. This covers the lateral-conduction driver
work in `scripts/run_tps_conduction_step2200.py` and
`scripts/make_ply_heatflux_plots.py`, which is where the bulk of the recent
Python change landed.

---

## 2. pyrefly

```
./venv_validation/bin/pyrefly check . \
  --python-interpreter-path ./venv_validation/bin/python \
  --project-excludes 'venv_validation/**' --project-excludes 'venv/**' \
  --project-excludes '.venv/**' --project-excludes '__pycache__/**' \
  --project-excludes 'build/**' --project-excludes 'scripts/**' \
  --project-excludes 'data/**' --project-excludes 'results/**' \
  --project-excludes '.opencode/**' --project-excludes '.tmp/**' \
  --project-excludes 'Lost+Found/**'
```

**Exit 0. `INFO 0 errors (6 suppressed, 19 warnings not shown).`**

This is the exact flag set `run.py` Phase 2 uses. Note that
`scripts/**` is excluded by that gate, so the TPS driver and plot script are
covered by **ruff** and by direct `py_compile`, not by pyrefly.

---

## 3. crosshair

```
./venv_validation/bin/crosshair check src/utils/sabotage_verifier.py
```

**Exit 0. Output: `WARNING: Targets found, but contain no checkable functions.`** Runtime 3.9 s.

This is a **vacuous pass**, and it is reported as such rather than counted as
evidence. `run.py` restricts crosshair to the single file
`src/utils/sabotage_verifier.py`, and that file carries no
crosshair-recognised contracts or `assert` specifications, so crosshair
found the target but analysed nothing. Crosshair contributes **no assurance
over the codebase** in its current configuration.

Recommendation: either annotate the functions crosshair should reason about,
or extend the target set beyond the verifier script — otherwise this gate
prints green while proving nothing.

---

## 4. sabotage_verifier

```
./venv_validation/bin/python src/utils/sabotage_verifier.py src/ \
  --extensions .adb,.ads,.py
```

**Exit 1. `VERDICT: TAINTED — 40 CRITICAL+ violation(s) found. NOT CLEAN.`**

```
Total Static Violations: 184
  CRITICAL:   1
  HIGH:       0
  MEDIUM:    39
  LOW:      144
```

Full log: `.verifier_audit.log`.

In `run.py` this gate is deliberately **NON-FATAL** (see the comment at
`run.py:1643` and `FAILURES_AND_FIXES.md` F87): the verifier is a large
generated script whose signal-to-noise was judged too poor to gate the build.
It is reported here as a finding, not as a build failure.

### 4.1 The one CRITICAL

`src/**` — `ADA_NOT_DOMINANT` (L1)

Ada is 32.5 % of bytes (2.1 MB) against Python at 42.3 % (2.7 MB). Full
composition as measured by the verifier: Python 42.3 %, Ada 32.5 %,
Markdown 7.7 %, Rocq 7.3 %, JSON 4.6 %, HTML 1.9 %, TypeScript 1.3 %,
TeX 1.3 %, CSS 0.6 %, Shell 0.3 %, JavaScript 0.3 %, C 0.0 %.

This carries a **JUSTIFIED_EXCLUSION** in the finding itself: Python here
holds the LLM toolchain, the WebView UI and build verification, which are
argued to have no Ada equivalent, while the core GNC logic is Ada with formal
verification. It is the same standing exemption recorded earlier in
`FAILURES_AND_FIXES.md`; it is a composition posture, not a defect in any
function.

### 4.2 MEDIUM findings (39) — a mix of real and false positive

| Category | Count | Assessment |
| :--- | ---: | :--- |
| `SELF_TEST_COVERAGE` | 23 | Subprogram has no matching `Test_<Name>` / AUnit registration |
| `ASSERTION_SCANNER` | 13 | **Mixed — see below** |
| `ADA_FUNCTION_COVERAGE` | 2 | Function not covered |
| `FUNCTION_NO_DOCUMENTATION` | 1 | Missing docstring |

**The `ASSERTION_SCANNER` findings are not all real.** Two were checked
directly against the sources:

* `stellarorion_physics.ads:1037 TPS_Conduction missing Post` — **false
  positive.** The declaration carries
  `Post => T_Back >= 0.0 and T_Surface >= 0.0 and Iterations <= 200`.
* `stellarorion_types.ads Layup_Min_Ply_Limit missing Post` — **false
  positive.** It carries `with Post => Layup_Min_Ply_Limit'Result >= 0.0;`.

The remaining `ASSERTION_SCANNER` hits are in
`stellarorion_sensitivity.ads` (`Axial_Swing`, `Axial_Gradient`,
`Axial_Mean_Effect`, `Corner_Mean_Effect`, `Rank_Factors`,
`Only_Factor_Nonzero`, `CCD_Layout_Conforms`). Those are **genuine**, and the
file already documents them as outstanding:
`-- nosec: F121 deferred -- CCD sensitivity unit contract hardening
(Pre/Post, Loop_Invariant, safe-fallback wrapper, Test_<Name> registry) is
outstanding work; the estimators are arithmetically correct and
gnatprove-clean`.

So the actionable subset of the 39 MEDIUM findings is roughly the
`sensitivity`-unit contract hardening tracked as F121 plus the ~23
`SELF_TEST_COVERAGE` registrations; the scanner's `.ads` contract resolution
also produces at least two demonstrable false positives that should be
corrected in the verifier rather than in the sources.

### 4.3 LOW findings (144)

The dominant LOW class visible in the log is `SPARK_MODE_OFF`, and every
instance inspected is **justified inline** with a specific reason (e.g.
`extern: Ada.Text_IO and Ada.Exceptions are non-SPARK runtime libraries.`,
`extern: exception handlers with choice parameter ... lie outside the SPARK
subset`). The verifier itself labels these
`legitimate use case detected`. They are recorded, not defects.

---

## 5. gnatprove --level=4

```
bash prove.sh --level 4
```

**gnatprove itself: 0 errors, discharged 474 of 533 obligations. 31 remain
unproved (6 %).**

```
SPARK Analysis results        Total       Flow   Provers    Justified  Unproved
Initialization                    3          3         .            .          .
Run-time Checks                 244          .       224            .         20
Assertions                      173          .       163            .         10
Functional Contracts             88          .        87            .          1
Termination                      25         25         .            .          .
Total                           533   28 (5%)   474 (89%)           .   31 (6%)
```

21 units analysed; max steps used for successful proof 76307; no check
exceeded 1 s.

### 5.1 `prove.sh` reports PASS on the wrong signal — report this as a defect

`prove.sh` prints `GNATprove: PASSED (Level 4)` keyed **solely on gnatprove's
exit code** (`prove.sh:81-86`):

```bash
if alr exec -- gnatprove -P stellarorion_program_proc.gpr --level="$LEVEL"; then
    echo "GNATprove: PASSED (Level $LEVEL)"
```

GNATprove exits 0 on a *completed run*, which is not the same as a *fully
discharged* run. A default `bash prove.sh --level 4` therefore announces PASS
while 31 obligations sit unproved and the summary table prints them
immediately above the PASS line. The script's own error text even says
`Check the output above for unproved checks.` — so the knowledge is there,
the gate just does not act on it.

This is the highest-value item in this report: it is a gate that can report
green over unproved obligations.

### 5.2 Where the 31 unproved checks are

All of them are in `stellarorion_postprocessing.ads`:

| Subprogram | Proved / total |
| :--- | :--- |
| `Compute_Validation_Metrics` | 94 / 99 |
| `Compute_Surf_Stats` | 43 / 51 |
| `Compute_Convergence_Stats` | 37 / 44 |
| `Hollis_Scalloping_Correction` | 15 / 20 |
| `Compute_Ratios` | 8 / 10 |
| `Compare_To_Flight` | 11 / 12 |
| `Compute_Integrated_Heat_Load` | 25 / 26 |
| `Sutherland_Viscosity` | 20 / 21 |
| `Compute_Chapman_Heat_Flux` | 2 / 3 |

**None of the unproved obligations fall in the units changed by the recent
lateral-conduction work** (`stellarorion_physics.ads/.adb`,
`stellarorion_ffi.ads/.adb`). Those are discharged.

### 5.3 Warnings (48)

* 31 × `this statement is never reached`
* 15 × `subprogram "Test_*" has no effect`
* 2 × `no check message justified by this pragma` — stale
  `Annotate => (GNATprove, False_Positive, ...)` pragmas in
  `stellarorion_geometry.ads:193` and `:208` that no longer correspond to a
  live check message; they should be removed or re-pointed.

The 15 `Test_*` "no effect" warnings are consistent with the
`SELF_TEST_COVERAGE` findings in §4.2 — the same gap seen from two tools.

### 5.4 `prove.sh` crashes after a PASS

`bash prove.sh --level 4` exits **1** despite gnatprove passing, with:

```
prove.sh: line 259: GNATCOV_FAILED: unbound variable
```

Root cause: `set -euo pipefail` at `prove.sh:15`, combined with
`GNATCOV_FAILED` being assigned only at `prove.sh:121` **inside** the
`if $RUN_COVERAGE` block, while line 259 reads it unconditionally:

```bash
if [ "$PYTHON_COVERAGE_FAILED" = "true" ] || [ "$GNATCOV_FAILED" = "true" ]; then
```

So the default invocation (`--coverage` not passed) never sets the variable,
and `set -u` aborts the script. The exit code therefore conflates "coverage
failed" with "coverage was never requested". Fix: initialise
`GNATCOV_FAILED=false` alongside `PYTHON_COVERAGE_FAILED=false` (which
*is* set unconditionally at line 159), or guard both reads behind their flags.

---

## 6. Ada unit tests

```
./bin/test_main
```

**Exit 0. `Tests run: 29  Failed: 0` — `ALL TESTS PASSED`.**

Both Ada projects also build clean:

```
alr exec -- gprbuild -f -P stellarorion_program_proc.gpr -j4   # main + tests
alr exec -- gprbuild -f -P stellarorion_pinn_lib.gpr -j4       # FFI dylib
```

The second project is a **separate target** from the first. Building only
`stellarorion_program_proc.gpr` does not relink `lib/libstellarorion_pinn.dylib`,
which is what `ada_pinn_wrapper` loads — a distinction that matters when
validating any change that reaches the FFI boundary.

---

## Overall

Six of six checks complete.

**Passing outright:** ruff (exit 0), pyrefly (exit 0), the Ada build on both
projects, `bin/test_main` (29/29).

**Passing with material caveats:**

1. **gnatprove discharged 474 of 533 obligations; 31 remain unproved**, all
   in `stellarorion_postprocessing.ads`. `prove.sh` nevertheless prints
   `PASSED`, because it keys on gnatprove's exit code rather than on the
   unproved count. Treat the "PASSED" string as *the analysis ran*, not as
   *everything was proved*.
2. **crosshair is a no-op here** — it found the target file and analysed
   zero functions. Exit 0 is not evidence.
3. **sabotage_verifier reports TAINTED** (1 CRITICAL / 0 HIGH / 39 MEDIUM /
   144 LOW). The CRITICAL is a standing composition exemption
   (`ADA_NOT_DOMINANT`); the MEDIUMs reduce to roughly two real groups
   (sensitivity-unit contracts tracked as F121, and ~23 missing `Test_`
   registrations) plus at least two demonstrable scanner false positives.
4. **`prove.sh` exits 1 on its default invocation** via an unbound
   `GNATCOV_FAILED` under `set -u`, masking the pass above.

**Defects to fix, in priority order:**

1. `prove.sh` should fail on unproved obligations, not on exit code — and
   should not crash on the default (no-coverage) path.
2. `prove.sh:259` unbound `GNATCOV_FAILED`.
3. The two stale `GNATprove, False_Positive` pragmas in
   `stellarorion_geometry.ads`.
4. The `ASSERTION_SCANNER` false positives in sabotage_verifier (contracts
   present in the `.ads` are reported missing).
5. Either annotate targets for crosshair or record the gate as a no-op.

**Recent work is clean under this sweep.** The lateral-conduction change
(`stellarorion_physics`, `stellarorion_ffi`, `ada_pinn_wrapper`, and the two
`scripts/` drivers) introduces no new unproved obligation, no ruff finding,
and no pyrefly error.
