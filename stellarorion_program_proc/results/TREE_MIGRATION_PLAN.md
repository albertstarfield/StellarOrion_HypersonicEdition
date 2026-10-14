# StellarOrion results/ tree migration plan (canonical end-state)

## 0. Why
Today's layout has three parallel truths (legacy per-tree `plots/`, canonical
`results/plots/`, and shared `tps_conduction/`), plus descriptive names that do
not express order or verdict. This plan converges everything to **one tree per
run, owned by the run** — no root-level `results/plots/`.

## 1. Target root layout (run folders are numbered, latest first)

```
results/
├── RUNS.md                      # human index (exists)
├── 00_reference/                # was validation_scalloped (LATEST, validated)
│   ├── paraview/surf_*.vtu, validation_timeseries.csv, in.hiad, HIAD_custom.surf
│   ├── validation_pipeline_output/{plots,interactive,vtu}
│   ├── optimization_output/{*.csv,*.json,plots}
│   ├── .parity/, vtu/, mp4_frames/
│   ├── plots/                   # ALL media of this run lives here
│   │   ├── short_window/  derived/  rapisarda/  vtu_snapshots/
│   │   ├── full_300M_dsmc_pinn/  mp4/
│   │   └── tps_per_ply/          # 6 per-ply artefacts incl. animation
│   └── README.md                # per-run, auto-generated
├── 01_smooth/                   # was validation_smooth (3378 m/s home)
│   ├── paraview/, validation_timeseries.csv, in.hiad
│   ├── plots/{short_window,derived,rapisarda,vtu_snapshots}/
│   └── README.md
├── 02_early_window/             # was validation (0..1000, no step-2200)
│   ├── paraview/, validation_timeseries.csv, grid.*.out, in.hiad
│   └── plots/{short_window,derived,rapisarda,vtu_snapshots}/
├── 03_opt_geometry/             # was OptimizedTopology (geometry + renders)
│   ├── geometry/, paraview/ (if a future run produces VTUs)
│   ├── plots/                   # turntables / comparison figures
│   └── mp4/                     # hybrid animation
├── 99_shared/
│   ├── cfd_fields/  kriging/  bo_figures/  geometry/
│   └── tps_conduction/00_reference/{elements,layers,profiles,summary}
└── README.md                    # report guide (auto-generated)
```

**Rule:** every number prefix ascending = newest / preferred; `00_` is always
the number you quote in a report. There is no round-1 gate folder because it
was removed (verified: no `validation_optimized` anywhere in the tree).

## 2. Migration steps (pathspec-scoped, reversible)

1. `git mv stellarorion_program_proc/results/validation_scalloped results/.../00_reference` (same for the other three, using the mapping above).
2. `git mv results/plots/<tree>/...  results/<run>/plots/...` (move canonical media into its run folder); delete empty root `results/plots/` afterwards (nothing else writes there).
3. `git mv results/tps_conduction/validation_scalloped results/99_shared/tps_conduction/00_reference`.
4. Update every path constant and CLI default in:
   - `run.py` (`_phase2c`, `_sync_media_into_canonical_tree`, `_write_results_readme`, `--regenerate-plots`, `_print_plot_status`)
   - `scripts/run_tps_conduction_step2200.py` (`DEFAULT_VTU`, `PER_PLY_TREES`)
   - `scripts/make_ply_heatflux_plots.py` (defaults, `--tree` choices, `STAGE_TEXT_INFO`)
   - `scripts/make_validation_plots.py`, `make_derived_plots.py`, `make_vtu_visualization.py`, `plot_rapisarda_comparison.py`, `generate_field_panels.py` (they take the tree dir as argv, so only the *call sites* in run.py change).
5. Rewrite `results/RUNS.md` table to the numbered folder names (same rows, new column `folder`).
6. Regenerate per-ply with the new defaults:
   `run.py --regenerate-plots all` then `run.py --status` (must show
   `00_reference ... solve=Y per_ply=Y (6 files)`, `01_smooth ...`).
7. Full verification before commit:
   - ruff on BOTH venvs (`venv_validation/bin/ruff`, `venv/python/bin/ruff`) for run.py + the three scripts;
   - MP4 machine check (ffmpeg frame extraction + pixel count, 240/240 frames);
   - `git status --short` reviewed file-by-file, commit with explicit pathspecs, never `git add <dir>`.

## 3. What stays where it is
- `results/README.md` generator: still generated, just points at run folders.
- `FAILURES_AND_FIXES.md`, `paperRef/`, `refs4/`: untouched.
- Root `README.md` and `Lost+Found/...`: user-owned, untouched.

## 4. Acceptance criteria
- A report author opens `results/` and, without reading code, sees
  `00_reference … 03_opt_geometry` and knows `00` is latest/validated.
- No artefact exists in two locations.
- `run.py --status` reflects the same numbering.
