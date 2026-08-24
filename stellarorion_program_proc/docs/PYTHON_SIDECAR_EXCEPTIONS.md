# Python Sidecar Policy Exceptions (Tier C1)

> Context: `docs/` | Tier: C1 of the code-quality compliance plan
> Standard reference: code-quality.md — "CRITICAL ENFORCEMENT: Ada-First Policy"
> Status: 2026-08-25 [ASWSS]

The project standard mandates Ada 2012 / SPARK 2014 for all application code.
This document records the **audited exceptions** — Python components that exist
by necessity, the justification for each, and the containment mechanism that
keeps them outside the verified core.

---

## 1. Containment Architecture

The verified Ada core and the Python sidecar domain are separated by a
**process boundary**, not a shared-library FFI boundary:

- The Ada binary spawns sidecar scripts with `GNAT.OS_Lib.Spawn`
  (`stellarorion_project.adb`, SPARK_Mode Off region, ~L297–L1319).
- There is **no** GNATCOLL.Python / shared-memory coupling. An earlier audit
  hypothesis ("FFI via GNATCOLL.Python") does not match the implementation:
  the only crossing points are OS process spawns plus files on disk
  (`data/runs/*.status.json` written by `stellarorion_status_writer`).
- Consequence: a sidecar crash cannot corrupt Ada memory; failure surfaces as
  a non-zero exit status that the Ada side reports. This satisfies the
  standard's FFI rules (return-code check, isolation) by construction.

## 2. Component Inventory & Justification

| Component | External deps | Spawned by | Justification (why no Ada equivalent) |
|---|---|---|---|
| `src/python/pinn_test.py` | DeepXDE, PyTorch | `--validationPINN` mode (project.adb L1207) | Physics-informed neural-network training. No Ada ML framework exists; reimplementation is out of scope for this project (research surrogate, not flight logic). |
| `src/python/pinn_accelerator.py` | PyTorch, NumPy | library use (imported by pinn_test) | Same as above — PINN surrogate bridge. |
| `src/python/pyfluent_test.py` | ansys-fluent-core (PyFluent), paramiko | integration-test mode (project.adb L1268–1293) | Vendor SDK for ANSYS Fluent (proprietary CFD). Fluent itself is Windows-remote; only vendor Python bindings exist. |
| `src/python/pyansys_test.py` | PyAnsys | integration-test mode (project.adb L1317) | Vendor SDK, same rationale. |
| `src/python/visualizer.py` | matplotlib | manual / post-processing | Publication plotting. Ada has no maintained plotting stack; figures are deliverables, not control flow. |
| `src/python/sidecar_launcher.py` | stdlib only | user launch of monitoring UI | Web UI bridge (`http.server`) serving `src/sidecar_ui/` static assets. Stdlib-only; could be ported to Ada, but it sits entirely outside the verified simulation path and shares the UI stack's HTTP contract with the browser. |
| `src/python/sidecar_server.py` | stdlib only | launched by sidecar_launcher | Same rationale. |
| `src/utils/sabotage_verifier.py` | stdlib only (AST, re) | `scripts/SabotageVerifier.sh` gate (B1) | Meta-tool: audits both Python AND Ada sources. It must read Python ASTs natively; bootstrapping it in Ada would require a Python parser in Ada. Runs at build-audit time only, never in production. |

## 3. Audit Status of This Domain

- The SabotageVerifier gate (`scripts/SabotageVerifier.sh`, baseline
  `docs/AUDIT_BASELINE.md`) scans all `src/python/*.py`. Baseline findings:
  CRITICAL = 0. Residual HIGH/MEDIUM findings in these files
  (SMT_LOGIC_VERIFICATION, EXTERNAL_CALL_UNHANDLED, RESOURCE_LEAK,
  SILENT_FAILURE classes) are **accepted for the sidecar domain**: they flag
  patterns that would be intolerable in the SPARK core but are inherent to
  vendor-SDK glue and research tooling. Re-triage before any sidecar file is
  promoted into the critical path.
- None of these components participate in:
  - the SPARK proof surface (`obj/gnatprove` closure),
  - the physics/geometry/environment contracts (AXIOMS.md),
  - the survivability decision path.

## 4. Rules Going Forward

1. New sidecar functionality must be added under `src/python/` and registered
   in this table; nothing else may import Python from Ada except via
   `GNAT.OS_Lib.Spawn`.
2. Any data returned by a sidecar and consumed by Ada must pass through the
   sanitising readers already in place (see APPLICATIONS.md AP-5) or be
   clamped at the ingestion chokepoint (AP-2).
3. Promotion of any sidecar computation into the verified core requires a
   SPARK re-proof run (`scripts/prove.sh skip --level=4 --report=all
   --timeout=180`) plus parity/watchdog coverage review.
