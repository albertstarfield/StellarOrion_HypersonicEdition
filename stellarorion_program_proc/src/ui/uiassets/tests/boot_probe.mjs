import sys

path = "src/ui/sidecar_ui.py"
src = open(path).read()

# ---------------------------------------------------------------- helpers
helper_block = r'''
    @staticmethod
    def _newest_sop_csv(stem):
        best = None
        best_mtime = 0.0
        tree_label = ""
        try:
            root = RESULTS_DIR / "99_shared" / "sop"
            if root.exists():
                for candidate in root.glob("*_" + stem + ".csv"):
                    try:
                        mtime = candidate.stat().st_mtime
                    except OSError:
                        continue
                    if mtime > best_mtime:
                        best, best_mtime = candidate, mtime
                        tree_label = candidate.stem[:-(len(stem) + 1)] if candidate.stem.endswith(stem) else ""
        except OSError as exc:
            print(f"[sidecar-ui] SOP {stem} glob failed: {exc}")
        return best, tree_label

    @staticmethod
    def _evaluate_gate(value, gate):
        spec = (gate or "").strip().lower()
        if not spec or spec == "report":
            return "REPORT"
        clause = spec.split("/")[0].strip()
        if " " in clause:
            clause = clause.split()[0]
        if clause.startswith("<="):
            try: return "MET" if value <= float(clause[2:]) else "NOT_MET"
            except ValueError: return "REPORT"
        if clause.startswith(">="):
            try: return "MET" if value >= float(clause[2:]) else "NOT_MET"
            except ValueError: return "REPORT"
        if clause.startswith("<"):
            try: return "MET" if value < float(clause[1:]) else "NOT_MET"
            except ValueError: return "REPORT"
        if clause.startswith(">"):
            try: return "MET" if value > float(clause[1:]) else "NOT_MET"
            except ValueError: return "REPORT"
        return "REPORT"

'''

# Insert helpers right before _handle_convergence if not already there
if "_newest_sop_csv" not in src:
    anchor = "    def _handle_convergence(self)"
    src = src.replace(anchor, helper_block + anchor, 1)

# ---------------------------------------------------------------- convergence
conv_start = src.find("    def _handle_convergence(self)")
conv_end = src.find("    def _handle_mesh_quality(self)", conv_start)
new_conv = '''    def _handle_convergence(self):
        # --- PINN/extrapolation audit (per-metric) ---
        csv_path = self._newest_audit_csv()
        metrics = []
        convergence_audit_source = None
        if csv_path is not None:
            convergence_audit_source = (str(csv_path.relative_to(PROJECT_ROOT))
                if csv_path.is_relative_to(PROJECT_ROOT) else str(csv_path))
            try:
                with csv_path.open("r", encoding="utf-8") as fh:
                    for row in csv.DictReader(fh):
                        entry = {"metric": row.get("metric", "")}
                        for key in ("noise_std", "r2_score", "raw_final", "denoised_final",
                            "pinn_extrapolated", "raw_error_pct", "denoised_error_pct",
                            "pinn_error_pct", "snr_db", "noise_fraction"):
                            entry[key] = _as_float(row.get(key))
                        metrics.append(entry)
            except (OSError, csv.Error) as exc:
                print(f"[sidecar-ui] convergence csv parse failed for {csv_path}: {exc}")

        # --- DSMC residual / stationarity series ---
        res_path, res_tree = self._newest_sop_csv("residuals")
        residual_series = []
        residual_source = None
        if res_path is not None:
            residual_source = (str(res_path.relative_to(PROJECT_ROOT))
                if res_path.is_relative_to(PROJECT_ROOT) else str(res_path))
            try:
                with res_path.open("r", encoding="utf-8", newline="") as fh:
                    for row in csv.DictReader(fh):
                        residual_series.append({
                            "step": _as_float(row.get("step")),
                            "cpu_s": _as_float(row.get("cpu_s")),
                            "n_particles": _as_float(row.get("n_particles")),
                            "delta_particles": _as_float(row.get("delta_particles")),
                            "retention_frac": _as_float(row.get("retention_frac")),
                            "stationarity_indicator": _as_float(row.get("stationarity_indicator")),
                            "residual_kind": row.get("residual_kind", ""),
                        })
            except (OSError, csv.Error) as exc:
                print(f"[sidecar-ui] residuals csv parse failed for {res_path}: {exc}")

        mass_balance = None
        if residual_series:
            first = residual_series[0]; last = residual_series[-1]
            retained = [_as_float(r.get("retention_frac")) for r in residual_series]
            retained_valid = [x for x in retained if x is not None]
            mean_retain = (sum(retained_valid) / len(retained_valid)) if retained_valid else None
            losses_total = sum(abs(x) for x in (_as_float(r.get("delta_particles")) or 0.0 for r in residual_series))
            mass_balance = {
                "initial_n_particles": first.get("n_particles"),
                "final_n_particles": last.get("n_particles"),
                "retention_final": last.get("retention_frac"),
                "retention_mean": mean_retain,
                "particles_lost_total": losses_total,
                "samples": len(residual_series),
                "tree": res_tree,
            }
        kinds = sorted({r.get("residual_kind", "") for r in residual_series if r.get("residual_kind")})

        snap = self.api.state.snapshot()
        self._json_response({
            "status": "ok" if (metrics or residual_series) else "NOT_MET",
            "sources": {
                "convergence_audit_csv": convergence_audit_source,
                "residuals_csv": residual_source,
            },
            "metrics": metrics,
            "residual_series": residual_series,
            "residual_status": ("ok: sourced from " + (residual_source or "")) if residual_series else ("not_available: no residuals.csv in results/99_shared/sop/"),
            "mass_balance": mass_balance,
            "balance_status": ("ok: particle-retention series from " + (residual_source or "")) if mass_balance is not None else ("not_available: no residuals.csv in results/99_shared/sop/"),
            "live_metrics": snap["metrics"],
            "residual_kinds": kinds,
            "note": (
                "residual_series/balance come from a DSMC particle-stationarity "
                "record (retention_frac/delta_particles) -- a conservation/"
                "stationarity measure, not a CFD RMS-residual print-out. "
                "convergence_audit.csv is the per-metric PINN denoise/"
                "extrapolation quality report."
            ),
        })

'''
src = src[:conv_start] + new_conv + src[conv_end:]

# --- mesh quality rewrite ---
mq_start = src.index("    def _handle_mesh_quality(self)")
mq_end = src.index("    def _handle_setup_sheet(self)", mq_start)
new_mq = r'''    def _handle_mesh_quality(self):
        images = []
        try:
            pngs = sorted((RESULTS_DIR / "99_shared" / "cfd_fields").glob("mesh_statistics_*.png"))
        except OSError as exc:
            print(f"[sidecar-ui] mesh statistics glob failed: {exc}")
            pngs = []
        for png in pngs[:10]:
            images.append("/api/content/image?name=" + png.name)

        mq_path, mq_tree = self._newest_sop_csv("mesh_quality")
        rows = []
        if mq_path is not None:
            try:
                with mq_path.open("r", encoding="utf-8", newline="") as fh:
                    for raw in csv.DictReader(fh):
                        try:
                            val = float(raw.get("value", ""))
                        except (TypeError, ValueError):
                            val = None
                        gate = raw.get("gate", "")
                        status = "NO_DATA"
                        if val is not None:
                            status = self._evaluate_gate(val, gate)
                        rows.append({
                            "metric": raw.get("metric", ""),
                            "value": val,
                            "gate": gate,
                            "method": raw.get("method", ""),
                            "source": raw.get("source", ""),
                            "note": raw.get("note", ""),
                            "status": status,
                        })
            except (OSError, csv.Error, ValueError) as exc:
                print(f"[sidecar-ui] mesh quality csv parse failed for {mq_path}: {exc}")

        gate_names = (
            ("skewness_min", "<0.25"),
            ("skewness_mean", "<0.5"),
            ("ortho_min", ">0.1"),
            ("ortho_mean", ">0.2"),
            ("growth_rate", "<=1.2"),
            ("flow_volume_closure_rel_err", "<1.0e-6"),
        )
        gates_out = rows if rows else [
            {"metric": m, "gate": g, "value": None, "unit": None,
             "note": "no SOP mesh-quality CSV present", "status": "NO_DATA"}
            for m, g in gate_names
        ]

        overall = "NO_DATA"
        if rows:
            statuses = {r["status"] for r in rows}
            if "NOT_MET" in statuses:
                overall = "NOT_MET"
            elif all(s in ("MET", "REPORT", "NO_DATA") for s in statuses):
                overall = "MET"
            else:
                overall = "ok"

        self._json_response({
            "status": overall,
            "numeric_table": rows,
            "numeric_table_reason": None if rows else "no SOP mesh-quality CSV present: expected results/99_shared/sop/<tree>_mesh_quality.csv",
            "tree": mq_tree or None,
            "thresholds": {
                "skewness_min": "<0.25 (good) / <0.5 (acceptable) -- SOP Ch.5",
                "ortho_min": ">0.1 (min) / >0.2 (mean) -- SOP Ch.5",
                "growth_rate": "<=1.2 (good) / <=1.3 (max) -- SOP Ch.5",
                "flow_volume_closure_rel_err": "<1.0e-6 conservation check -- SOP Ch.5",
            },
            "gates": gates_out,
            "images": images,
        })

'''
src = src[:mq_start] + new_mq + src[mq_end:]

# --- grid independence rewrite ---
gi_start = src.find("    def _handle_grid_independence(self")
gi_end = src.find("    def _handle_draft_autosave(self)", gi_start)
new_gi = r'''    def _handle_grid_independence(self, payload=None):
        requested = payload if isinstance(payload, dict) else {}
        gi_path = RESULTS_DIR / "99_shared" / "sop" / "grid_independence.json"
        body = {}
        if gi_path.is_file():
            try:
                body = json.loads(gi_path.read_text(encoding="utf-8"))
                if not isinstance(body, dict):
                    body = {}
            except (OSError, json.JSONDecodeError) as exc:
                print(f"[sidecar-ui] grid_independence.json read failed: {exc}")
                body = {}
        levels = body.get("levels") if isinstance(body.get("levels"), list) else []
        self._json_response({
            "status": str(body.get("status", "NOT_MET")),
            "reason": body.get("reason") or "grid-independence report missing at results/99_shared/sop/grid_independence.json",
            "requested": {k: requested.get(k) for k in ("solver", "steps", "factors")},
            "levels": levels,
            "level_count": len(levels),
            "sop": body.get("sop", "Ch.6 / Ch.12#4 / Ch.15"),
            "source": str(gi_path.relative_to(PROJECT_ROOT)) if gi_path.is_relative_to(PROJECT_ROOT) else str(gi_path),
        })

'''
src = src[:gi_start] + new_gi + src[gi_end:]

open(path, "w").write(src)
open("/tmp/patch_log.txt", "w").write("conv=%d-%d mq=%d-%d gi=%d-%d\nsize=%d\n"
    % (conv_start, conv_end, mq_start, mq_end, gi_start, gi_end, len(src)))
print("patch applied")
PYEOF
