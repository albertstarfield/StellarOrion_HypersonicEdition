# StellarOrion results/ run index (numbered, latest first)

Read from top to bottom: **later = more recent / more trusted**, regardless of
file names. The SPARTA timestamp in each run is what matters, not the commit.

| # | Run folder | Role | Step-2200 alt / vel | Verdict | Use it when... |
|---|---|---|---|---|---|
| **4** | `00_reference` (was validation_scalloped) | **LATEST REFERENCE** (default) | 52.069 km / 3101.079 m/s (2026-10-06 dump) | validated base | every report and figure; tps_conduction sits on its `surf_2200.vtu`; HSFI model knob is this one |
| 3 | `validation_optimized` | round 1 *GATE RUN* (optimized morphology) | 52.033 km / 3094.193 m/s | **REMOVED ON DISK** — kept here so the audit trail and previous report notes still stand; the failed candidate produced VALIDATION FAILED (58.42/59.00/31.00) | historically cited only; not available for new runs |
| 2 | `01_smooth` (was validation_smooth) | finer-spool / variant | 51.818 km / 3378.671 m/s | observation | triage only; this is where `Snapshot_Vel_Ms = 3378` comes from |
| 1 | `02_early_window` (legacy `validation` now removed) | week-1 legacy (0..1000) | -- no step-2200 row | -- | not a candidate for any case which needs step-2200 resolution |
| — | `optimized_topology` | geometry + render output | — | — | design description figures and MP4; has no surf data |
| — | `results/99_shared/tps_conduction` (formerly `validation_scalloped`) | per-ply ADA/SPARK solve CSVs and JSON (note: per tree when prefixed with `/validation_*`) | — | — | inputs to `make_ply_heatflux_plots.py` (run `run.py --regenerate-plots tps-per-ply`) |

Default posture
---------------

* Use **#4** everywhere (00_reference).
* Run `\texttt{run.py --status}` first; it checks every folder for its
  `surf_2200.vtu`, timeseries, solve output, and per-ply artefacts. If a
  folder says `solve=n`, do not cite per-ply figures from it.
* NEVER present a `validation_optimized` number without its
  `VALIDATION FAILED` caveat.

Last update: 2026-10-14 (commit b6761033 after this refactor).
"""