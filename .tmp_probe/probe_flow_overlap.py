#!/usr/bin/env python3
"""Probe text-vs-text overlaps in flowchart generators lacking the guard.

AXIOM: make_pipeline_figure.py and make_dsmc_flowchart.py verify box-fit and
font floors but never call fig_metrics.text_overlaps_pt, so latent label
collisions (the exact class found in solver_coupling/result_extraction) can
ship unnoticed. This probe runs each generator's real main()/draw() with
Figure.savefig intercepted, then applies fm.text_overlaps_pt at the
conservative worst-case placement scale 1.0 (largest possible printed points,
so it flags a superset of real overlaps).

THEORIES: overlap pairs print as "A <> B (w x h pt)"; an empty list means the
figure would pass the guard used by the other generators.

APPLICATION: run from anywhere:  python3 .tmp_probe/probe_flow_overlap.py
Exit 0 always (diagnostic); inspect output.

CITATIONS: fig_metrics.text_overlaps_pt — see figures/fig_metrics.py L674.
"""
import importlib.util
import sys
from pathlib import Path

FIGDIR = Path(__file__).resolve().parents[1] / (
    "Lost+Found/ProgressReport/CurrentThesisFinalReport/figures")
sys.path.insert(0, str(FIGDIR))

import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure  # noqa: E402
import fig_metrics as fm  # noqa: E402

_real_savefig = Figure.savefig


def run_generator(label, module_path, entry):
    """Import the generator, intercept its first savefig, run the guard.

    :param label: display name for the report line.
    :param module_path: path to the generator .py file.
    :param entry: name of the callable to invoke (main or draw).
    :returns: None; prints the overlap report to stdout.
    :raises: none — generator exceptions are reported, not propagated.
    """
    state = {"checked": False}
    fig_module = importlib.util.spec_from_file_location(
        f"gen_{label}", module_path)
    mod = importlib.util.module_from_spec(fig_module)
    fig_module.loader.exec_module(mod)

    def probe(fig, *args, **kwargs):
        """Run the overlap guard once, then perform the real savefig."""
        if not state["checked"]:
            state["checked"] = True
            pairs = fm.text_overlaps_pt(fig, 1.0)
            print(f"== {label}: {len(pairs)} overlap pair(s) at scale 1.0")
            for a, b, w, h in pairs:
                print(f"   {w:.1f}x{h:.1f}pt  {a} <> {b}")
        return _real_savefig(fig, *args, **kwargs)

    Figure.savefig = probe
    try:
        getattr(mod, entry)()
    except SystemExit as exc:
        print(f"== {label}: SystemExit {exc}")
    except Exception as exc:  # noqa: BLE001 — diagnostic probe reports all
        print(f"== {label}: exception {type(exc).__name__}: {exc}")
    finally:
        Figure.savefig = _real_savefig


if __name__ == "__main__":
    run_generator("pipeline", FIGDIR / "make_pipeline_figure.py", "main")
    run_generator("dsmc", FIGDIR / "make_dsmc_flowchart.py", "draw")
