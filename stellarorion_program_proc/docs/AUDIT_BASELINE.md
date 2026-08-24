# Sabotage Audit Baseline — Known-Acceptable Findings

> **Scope**: documents why the SabotageVerifier.sh gate (Tier B1) passes with
> non-zero HIGH/MEDIUM counts. Gate criterion is **CRITICAL = 0** per the
> verifier's own severity contract (`main()` exits non-zero only on CRITICAL).
>
> Baseline established: 2026-08-25, commit series following `5512f3d`.
> Reference report: `data/audits/sabotage_20260825_*.json`.

## Gate verdict at baseline

| Severity | Count | Gate impact |
|----------|-------|-------------|
| CRITICAL | 0     | **PASSED** |
| HIGH     | 107   | reported; triaged below |
| MEDIUM   | 879   | reported; informational |
| LOW      | 91    | reported; informational |

## Accepted HIGH categories (triage)

### 1. ADA_FUNCTION_COVERAGE (~69) — false positive by design
The checker scans `.adb` **bodies** for missing Pre/Post contracts. In this
project all SPARK_Mode On units declare contracts in their **`.ads` specs**
(correct Ada style — bodies do not repeat aspect specifications). Examples
verified false-positive: `Deg_To_Rad`, `Sin_Deg`, `Frontal_Area`
(`stellarorion_geometry.ads` carry full AXIOM G1–G3 contracts),
`Is_Survivable` (`stellarorion_physics.ads`). The remaining hits are on
SPARK_Mode Off extern units (`project.adb`, `history.adb`, `sparta.adb`)
whose Off status carries in-file justifications the verifier itself
recognizes as "legitimate use case detected" (LOW SPARK_MODE_OFF finding).
**Stronger gate already in place**: gnatprove `--level=4` clean, 339/339
checks (`scripts/prove.sh skip --level=4 --report=all --timeout=180`).

### 2. SMT_LOGIC_VERIFICATION (~26) + EXTERNAL_CALL_UNHANDLED (8) +
### STALE_FLAG (2) + SILENT_FAILURE (1) + RESOURCE_LEAK (1) — Python sidecar
All located in `src/python/` and `src/ui/` (pinn_accelerator.py,
pyansys_test.py, pyfluent_test.py, pinn_test.py, sidecar_server.py,
sidecar_ui.py). Per the project's Ada-first policy these files exist only as
the run.py-launched Python sidecar (DeepXDE/PyFluent/PyAnsys ML frameworks
have no Ada equivalent). Their exception documentation is Tier C1 scope;
hardening them is out of B-tier scope and tracked there.

## Re-baselining rule

When the gate reports a **new category** or a CRITICAL, fix before merge.
Category-count drift within accepted categories does not block, but should
be noted in the commit message touching those files.

## Verification commands

```bash
scripts/SabotageVerifier.sh                 # full audit, exit 1 on CRITICAL
python3 src/utils/sabotage_verifier.py src/simulation_engine/ \
        --extensions .ads,.adb              # Ada-only quick check
```
