# Overnight goal — thesis revision, simulation and re-audit

Set: 2026-11-27 23:00 WIB. Owner: Amaryllis (default profile).

## Goal statement

Drive `Rev_Nov27_2026.md` to a state where every item is either **checked with evidence** or **explicitly left unchecked with a reason**, while the LaTeX thesis Chapters 1–5 are revised accordingly, the optimization/DSMC/plot pipeline is re-executed, and the result is re-audited against the 100-page target.

## Acceptance criteria

1. Checklist: checked items each carry a log reference; unchecked items each carry a blocker note. No item silently dropped.
2. LaTeX: `latexmk -pdf main.tex` exits 0 with 0 undefined refs, 0 overfull, 0 underfull.
3. Page budget: Chapters 1–5 end at or before printed page 100 (REFERENCES p.101), measured from `main.toc` after the rebuild; if not met, the remaining gap is recorded explicitly.
4. Simulation: optimization + DSMC re-run completed, with trajectory campaign for the IRVE-3 comparison where feasible; artifacts written under `stellarorion_program_proc/results/`.
5. Plots: regenerated from the new artifacts, no figure still pointing at the superseded campaign.
6. Re-audit: a written PASS/FAIL sweep over all six criteria with exact file:line and log evidence.

## Phase order

- P0 Back up all `.tex` sources and the checklist before editing.
- P1 Start the long-running `run.py --trajectory-campaign` job in the background with full stdout/stderr logging; babysit it.
- P2 Execute low-risk LaTeX items: after-caption pruning (with the numeric exception), duplicate figure/table removal with `\ref` repair, Ada/SPARK statement, two-fidelity statement, analytic-vs-flight validation table, tolerance language, acknowledgement placeholder decision.
- P3 Execute page-budget section cuts chapter by chapter, rebuilding and measuring after each.
- P4 When simulation artifacts land, regenerate plots and replace result-derived figures/tables/numbers.
- P5 Check off completed items with evidence, re-audit, report the remaining gap honestly.

## Hard constraints

- Never weaken a scientific claim to make a tolerance pass.
- Never change a number without regenerating its artifact.
- No item is marked done on assertion alone; each needs a log path or a file:line.
- Do not declare the goal finished until P5 produces the written re-audit.

## Runtime state at handoff (2026-11-27 23:18 WIB)

- Goal card `t_9f773f45` is running in goal_mode (40-turn budget), workspace = this repo.
- Thesis backup: `ProgressReport/CurrentThesisFinalReport/backup_overnight_20261127_231830.tar.gz` (10 files, 148K).
- Long simulation job started: `python3 -u run.py --trajectory-campaign --skip-pinn`, PID 93622, session `proc_0021342e0558`, log `~/.hermes/logs/audit/overnight_campaign.log`, heartbeat 3600s, notify on completion, persist_on_release=true.
- **Do not start a second campaign.** Monitor the existing PID and log; read its tail before any plot regeneration to avoid concurrent writes into `stellarorion_program_proc/results/`.
- Checklist state at handoff: 191 unchecked, 0 checked, 356 lines.
- Preflight: Docker 29.5.2 up, `bin/main` present, 15 GiB free on the data volume.
