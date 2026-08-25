# project.adb Decomposition Assessment (Tier C2)

> Context: `docs/` | Tier: C2 of the code-quality compliance plan
> Scope facts: `stellarorion_project.adb` = 2896 lines, ~30 local procedures,
> 36 `Has_Flag` CLI dispatch sites, SPARK_Mode **Off** by design (process
> spawns via `GNAT.OS_Lib`, file locking, external tool orchestration).
> Status: assessment + staged plan, 2026-08-25 [ASWSS]

## Why it is a monolith today

`StellarOrion_Project` grew as the single entry unit: CLI parsing, runtime
guards (lock/GPU/Docker), the self-test suite, every named run mode
(`--validate`, `--test-pinn`, ...), optimization driving, and report
formatting all live in one body. The GPR compiles exactly the main closure,
so nothing forced separation. Tier A/B work added contracts *around* it
(physics/environment/geometry units) without needing to split it; its
SPARK_Off status means gnatprove places no obligations inside it.

## Risk profile

| Concern | Assessment |
|---|---|
| Proof impact of splitting | None direct — file is SPARK_Off; extracted units stay Off unless a piece is pure enough to turn On (CLI helpers are). |
| Behaviour risk | Moderate: mode dispatch order and banner/status output are load-bearing for the validation pipeline (`data/runs/*.status.json` consumers). |
| Regression safety net | Strong: 15-test self-test (18 checks) + independent harness (29 checks) + zero-warning gate + SabotageVerifier gate all must stay green after each extraction step. |

## Staged extraction plan (dependency-safe order)

Each stage is an independent commit; gates re-run after every stage.

1. **`StellarOrion_Cli`** ✅ DONE (2026-08-25): `Has_Flag`, `Get_Option`,
   `Get_Float`, `Clamp_Float`, `Get_Positive` extracted verbatim to
   `stellarorion_cli.ads/.adb`. SPARK_Mode On for package, `Has_Flag`,
   `Get_Option`, `Clamp_Float` (proved clean; L4 total 376→383 checks);
   `Get_Float`/`Get_Positive` bodies remain Off ('Value may raise
   Constraint_Error; Exceptional_Cases is procedure-only in this toolchain)
   with rationale in-source — flip-On candidates pending Coq remediation.
   Gates after extraction: build zero-warnings, self-test 15/15,
   harness 29/29, gnatprove 383/383, SabotageVerifier CLEAN,
   `--validate-only` dispatch smoke PASS.
2. **`StellarOrion_Runtime_Guard`** ✅ DONE (2026-08-25): `Get_Lock_File_Path`,
   `Check_And_Acquire_Lock`, `Release_Lock`, `Detect_Nvidia_GPU`,
   `Ensure_Docker_Running`, `Check_Amaryllis_Idle_Automode` extracted
   verbatim to `stellarorion_runtime_guard.ads/.adb` (SPARK_Mode Off —
   file I/O + GNAT.OS_Lib subprocess dispatch concentrated in one unit).
   150 lines removed from stellarorion_project.adb; 5 call sites resolve
   via use-clause. Proof skeleton added per SabotageVerifier convention.
   Gates: build zero-warnings, self-test 15/15, harness 29/29,
   gnatprove 383/383 (unchanged — moved code is Off), SabotageVerifier
   CLEAN, `--validate-only` dispatch smoke PASS.
3. **`StellarOrion_Self_Test`** ✅ DONE (2026-08-25): `Run_Self_Test`
   (476 lines, Tests 1-15 incl. parity/watchdog wiring) extracted
   verbatim to `stellarorion_self_test.ads/.adb` (SPARK_Mode Off with
   extern justification; STATUS_DIR local copy documented in-source).
   project.adb 2708→2236 lines; unused with/use pairs for Geometry,
   Atomic_Parity, Dual_Watchdog removed from project.adb (self-test was
   their only consumer). Proof skeleton added. Gates: build
   zero-warnings, self-test 15/15, harness 29/29, gnatprove 383/383,
   SabotageVerifier CLEAN, `--validate-only` smoke PASS.
4. **`StellarOrion_Test_Modes`** ✅ DONE (2026-08-25): all 12 test/demo mode
   procedures (`Run_GetIRVE3_Baseline`, `Run_CompareNoses`,
   `Run_GridIndep_Test`, `Run_Demo`, `Run_Validate_Only`, `Run_Test_Baseline`,
   `Run_Test_Sample`, `Run_Test_PINN_Calibration`, `Run_Test_Sparta_Integration`,
   `Run_Test_PyFluent_Integration`, `Run_Test_PyAnsys_Integration`,
   `Run_Test_OpenFOAM_Integration`) plus `Run_Validate_Full` and the exported
   `F6`/`Grade` formatting helpers extracted verbatim to
   `stellarorion_test_modes.ads/.adb` (SPARK_Mode Off with extern
   justification — sidecar-spawn surface per PYTHON_SIDECAR_EXCEPTIONS.md §2).
   Scope note: `Run_Validate_Full` moved here (not Stage 5) because test modes
   call it; its forward declaration moved with it. STATUS_DIR local copy
   documented in-source. project.adb 2236→~1240 lines; unused with/use pairs
   (Validation, Sparta, Ada.Directories) removed from project.adb.
   Proof skeleton added. Gates: build zero-warnings, self-test 15/15,
   harness 29/29, gnatprove 383/383, SabotageVerifier CLEAN,
   `--validate-only` smoke PASS.
6. **Remainder**: `Main_Program` keeps only argument interpretation +
   dispatch; target < 300 lines.

## Deferred items tied to this decomposition

- `Run_GridIndep_Test` retained-with-pragma-Unreferenced decision
  (ledger fcba "Key Decisions") resolves naturally at stage 5.
- Real-time watchdog tasking wrapper (B3 deferred piece) lands as
  `StellarOrion_Dual_Watchdog.Tasks` once Runtime_Guard exists, so heartbeat
  updates can be called from both monitors.
- Any stage may be executed without the others; stages are ordered so that no
  earlier stage depends on a later one.
